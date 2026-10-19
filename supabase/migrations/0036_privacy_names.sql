-- ═════════════════════════════════════════════════════════════════════
-- 0036 — private phone numbers, names a person can tell apart, Drugbox notices in the reader's language (phase 1b, round 2)
--   1. profiles.phone is private. Until now every signed-in member could read every member's phone through the API
--      (GET /rest/v1/profiles?select=name,phone), although the app never shows another person's phone. Members now read
--      every profile column EXCEPT phone (column privileges); their own row, phone included, comes from my_profile().
--      Consequence: select=* on profiles is refused for members (name the columns) — the app names them everywhere.
--      open_candidates() (security invoker, "returns setof profiles") lists its columns and returns phone as NULL.
--      A later migration must never "grant select on public.profiles" again without the column list.
--   2. Names are cleaned when they are written (sign-up, Edit Profile, SQL): invisible characters (zero-width space/joiners,
--      direction marks, soft hyphen, BOM, tag characters…) are removed, runs of spaces become one space, and the dot-like
--      separators the ✎ New message picker puts between a name and what tells it apart ("·", "•", "∙"…) become "-".
--      So "Dr. Zeina X" + U+200B is the same name as "Dr. Zeina X" (the picker then tells them apart), and nobody can be
--      called "Dr. Hala X · Pharco X" to pass for the Pharco Dr. Hala X. Existing names are cleaned once here.
--   3. post_report_decide() keeps only the data of its two notices (post_removed, report_closed) in notifications.data —
--      the post's words, the reason, the moderator's note, the outcome — and the app writes the sentence in the reader's
--      language (as 0034 did for company_message). Rows written before keep their English sentence (the app translates it).
-- Every new function has its own GRANT/REVOKE (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. phone stays with its owner ────────────────────────────────────
revoke select on table public.profiles from anon, authenticated;
grant select (id, name, headline, company, country, bio, avatar_url, cover_url, website, certs, role, verified, account_type,
              created_at, updated_at, location, experience, education, certifications, skills, languages, open_to_work, hiring,
              profile_views, followers_count, years_experience, desired_role, desired_type, remote_ok, available_since,
              intro_video, intents) on table public.profiles to anon, authenticated;

-- the signed-in member's own row, phone included (one call at sign-in instead of select=*)
create or replace function public.my_profile()
returns setof public.profiles language sql stable security definer set search_path = public as $$
  select * from public.profiles where id = auth.uid()
$$;
revoke all on function public.my_profile() from public, anon, authenticated, service_role;
grant execute on function public.my_profile() to authenticated, service_role;

create or replace function public.open_candidates(p_limit int default 40)
returns setof public.profiles language sql stable set search_path = public as $$
  select p.id, p.name, p.headline, p.company, p.country, p.bio, p.avatar_url, p.cover_url, p.website, null::text, p.certs, p.role,
         p.verified, p.account_type, p.created_at, p.updated_at, p.location, p.experience, p.education, p.certifications, p.skills,
         p.languages, p.open_to_work, p.hiring, p.profile_views, p.followers_count, p.years_experience, p.desired_role,
         p.desired_type, p.remote_ok, p.available_since, p.intro_video, p.intents
    from public.profiles p where p.open_to_work and p.id <> coalesce(auth.uid(), '00000000-0000-0000-0000-000000000000'::uuid)
     and p.id <> all (coalesce((select private.blocked_parties()), '{}'::uuid[]))
   order by p.created_at desc limit least(greatest(coalesce(p_limit, 40), 1), 100)
$$;
revoke all on function public.open_candidates(int) from public, anon, authenticated, service_role;
grant execute on function public.open_candidates(int) to authenticated, service_role;

-- ── 2. names a person can tell apart ─────────────────────────────────
create or replace function public.clean_person_name(s text)
returns text language sql immutable parallel safe as $$
  select nullif(btrim(regexp_replace(regexp_replace(regexp_replace(coalesce(s, ''),
    -- invisible / format characters (Unicode Cf and the blank fillers)
    U&'[!00AD!034F!061C!115F!1160!17B4!17B5!180B-!180F!200B-!200F!202A-!202E!2060-!206F!2800!3164!FE00-!FE0F!FEFF!FFA0!FFF9-!FFFB!+0E0000-!+0E007F!+0E0100-!+0E01EF]' uescape '!', '', 'g'),
    -- the separators the New message picker uses between a name and its facts
    U&'\s*[!00B7!0387!16EB!2022!2027!2219!22C5!2E31!30FB!FF65]+\s*' uescape '!', ' - ', 'g'),
    -- every kind of space, tab or line break: one space
    U&'[!0009-!000D!0020!0085!00A0!1680!2000-!200A!2028!2029!202F!205F!3000]+' uescape '!', ' ', 'g'), ' '), '')
$$;
revoke all on function public.clean_person_name(text) from public, anon, authenticated, service_role;
grant execute on function public.clean_person_name(text) to authenticated, service_role;   -- the trigger below runs as the writer

create or replace function public.profiles_clean_name() returns trigger language plpgsql set search_path = public as $$
begin
  new.name := left(coalesce(public.clean_person_name(new.name), 'Member'), 200);
  return new;
end $$;
revoke all on function public.profiles_clean_name() from public, anon, authenticated, service_role;
drop trigger if exists trg_profiles_clean_name on public.profiles;
create trigger trg_profiles_clean_name before insert or update of name on public.profiles
  for each row execute function public.profiles_clean_name();

update public.profiles set name = left(coalesce(public.clean_person_name(name), 'Member'), 200)
 where name is distinct from left(coalesce(public.clean_person_name(name), 'Member'), 200);

-- ── 3. Drugbox's notices keep their data, not an English sentence ────
alter table public.notifications add column if not exists data jsonb;
do $$ begin
  alter table public.notifications add constraint notifications_data_size check (data is null or (jsonb_typeof(data) = 'object' and pg_column_size(data) <= 4096));
exception when duplicate_object then null; end $$;

create or replace function public.post_report_decide(p_report bigint, p_remove boolean, p_note text default null)
returns int language plpgsql security definer set search_path = public as $$
declare r record; me uuid := auth.uid(); n int := 0; v_note text := nullif(left(trim(coalesce(p_note, '')), 500), '');
begin
  if me is null or not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  select * into r from public.post_reports where id = p_report;
  if r.id is null then raise exception 'This report does not exist' using errcode = 'P0002'; end if;
  if r.status <> 'open' then return 0; end if;                              -- already decided (another moderator, another tab)
  -- every open report on the same post is closed by the same decision (one row per post in the review queue)
  with done as (
    update public.post_reports set status = case when p_remove then 'removed' else 'dismissed' end,
           decided_by = me, decision_note = v_note, decided_at = now()
     where status = 'open' and ((r.post_id is not null and post_id = r.post_id) or id = r.id)
    returning reporter)
  insert into public.notifications (user_id, type, from_user, message, data)
  select distinct reporter, 'report_closed', null::uuid, null::text,
         jsonb_build_object('outcome', case when p_remove then 'removed' else 'dismissed' end)
    from done;
  get diagnostics n = row_count;
  if p_remove then
    if r.post_author is not null then
      insert into public.notifications (user_id, type, from_user, message, data)
      values (r.post_author, 'post_removed', null, null,
              jsonb_strip_nulls(jsonb_build_object('excerpt', left(coalesce(r.post_excerpt, ''), 80)
                || case when char_length(coalesce(r.post_excerpt, '')) > 80 then '…' else '' end,
                'reason', coalesce(r.reason, 'other'), 'note', v_note)));
    end if;
    if r.post_id is not null then delete from public.posts where id = r.post_id; end if;
  end if;
  return n;
end; $$;
revoke all on function public.post_report_decide(bigint, boolean, text) from public, anon, authenticated, service_role;
grant execute on function public.post_report_decide(bigint, boolean, text) to authenticated, service_role;

notify pgrst, 'reload schema';
