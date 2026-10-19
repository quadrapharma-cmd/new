-- ═════════════════════════════════════════════════════════════════════
-- 0042 — profile (area social: S-06 photo and cover, S-14 experience / education / skills / languages, S-25 who viewed me)
--   1. avatars bucket        public, images only (JPEG, PNG, WebP), 5 MB; a member writes only in the folder named by their id
--                            (<uid>/avatar-….jpg, <uid>/cover-….jpg); profiles.avatar_url / cover_url keep the public address
--   2. profile lists         experience / education are arrays of small objects of text, skills and languages short texts —
--                            checked by the database whatever the browser sends
--   3. skill_endorsements    a member endorses a skill another member lists, once; never their own; the owner is told
--                            ('endorse'); a skill removed from the profile takes its endorsements with it
--   4. my_profile_viewers()  the members who viewed my profile (last 90 days) — only those who allow it in Settings → Privacy
--                            are named; the others are counted
-- Every table and function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. avatars ───────────────────────────────────────────────────────────────────────────────────────────
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('avatars', 'avatars', true, 5242880, array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do update set public = true, file_size_limit = 5242880, allowed_mime_types = array['image/jpeg', 'image/png', 'image/webp'];
drop policy if exists "avatars: anyone can see" on storage.objects;
create policy "avatars: anyone can see" on storage.objects for select using (bucket_id = 'avatars');
drop policy if exists "avatars: upload to your own folder" on storage.objects;
create policy "avatars: upload to your own folder" on storage.objects for insert to authenticated
  with check (bucket_id = 'avatars' and (storage.foldername(name))[1] = (select auth.uid())::text and array_length(storage.foldername(name), 1) = 1);
drop policy if exists "avatars: replace your own" on storage.objects;
create policy "avatars: replace your own" on storage.objects for update to authenticated
  using (bucket_id = 'avatars' and (storage.foldername(name))[1] = (select auth.uid())::text)
  with check (bucket_id = 'avatars' and (storage.foldername(name))[1] = (select auth.uid())::text and array_length(storage.foldername(name), 1) = 1);
drop policy if exists "avatars: delete your own" on storage.objects;
create policy "avatars: delete your own" on storage.objects for delete to authenticated using (bucket_id = 'avatars' and (storage.foldername(name))[1] = (select auth.uid())::text);

-- the photo and cover addresses a member saves are this project's avatars files in their own folder (never another site, never
-- someone else's picture); Drugbox (server calls) may set anything
create or replace function public.profiles_pictures_guard() returns trigger language plpgsql as $$
declare pre text := '/storage/v1/object/public/avatars/' || new.id::text || '/';
begin
  if public.is_server_call() then return new; end if;
  if new.avatar_url is distinct from (case when tg_op = 'UPDATE' then old.avatar_url end) and new.avatar_url is not null and position(pre in new.avatar_url) = 0 then
    raise exception 'The profile photo must be uploaded to Drugbox' using errcode = '22023';
  end if;
  if new.cover_url is distinct from (case when tg_op = 'UPDATE' then old.cover_url end) and new.cover_url is not null and position(pre in new.cover_url) = 0 then
    raise exception 'The cover image must be uploaded to Drugbox' using errcode = '22023';
  end if;
  if new.avatar_url !~ '^https?://[^\s"''<>()\\]+$' and new.avatar_url is not null then raise exception 'The profile photo must be uploaded to Drugbox' using errcode = '22023'; end if;
  if new.cover_url !~ '^https?://[^\s"''<>()\\]+$' and new.cover_url is not null then raise exception 'The cover image must be uploaded to Drugbox' using errcode = '22023'; end if;
  return new;
end $$;
revoke all on function public.profiles_pictures_guard() from public, anon, authenticated, service_role;
grant execute on function public.profiles_pictures_guard() to authenticated, service_role;
drop trigger if exists trg_profiles_pictures_guard on public.profiles;
create trigger trg_profiles_pictures_guard before insert or update of avatar_url, cover_url on public.profiles for each row execute function public.profiles_pictures_guard();

-- ── 2. the profile's lists ───────────────────────────────────────────────────────────────────────────────
create or replace function private.text_object_list_ok(v jsonb, max_items int) returns boolean language sql immutable as $$
  select v is null or (jsonb_typeof(v) = 'array' and jsonb_array_length(v) <= max_items and not exists (
    select 1 from jsonb_array_elements(v) e
     where jsonb_typeof(e) <> 'object'
        or exists (select 1 from jsonb_each(e) kv where jsonb_typeof(kv.value) not in ('string', 'boolean', 'number', 'null')
                                                     or length(kv.key) > 40 or (jsonb_typeof(kv.value) = 'string' and length(kv.value #>> '{}') > 2000))
        or (select count(*) from jsonb_object_keys(e)) > 12))
$$;
revoke all on function private.text_object_list_ok(jsonb, int) from public;
grant execute on function private.text_object_list_ok(jsonb, int) to anon, authenticated, service_role;
create or replace function public.profiles_lists_guard() returns trigger language plpgsql as $$
begin
  if not private.text_object_list_ok(new.experience, 40) then raise exception 'The experience list is not accepted' using errcode = '23514'; end if;
  if not private.text_object_list_ok(new.education, 20) then raise exception 'The education list is not accepted' using errcode = '23514'; end if;
  if exists (select 1 from unnest(coalesce(new.skills, '{}')) s where length(trim(s)) not between 1 and 60) then raise exception 'A skill is 1 to 60 characters' using errcode = '23514'; end if;
  if exists (select 1 from unnest(coalesce(new.languages, '{}')) s where length(trim(s)) not between 1 and 60) then raise exception 'A language is 1 to 60 characters' using errcode = '23514'; end if;
  return new;
end $$;
revoke all on function public.profiles_lists_guard() from public, anon, authenticated, service_role;
grant execute on function public.profiles_lists_guard() to authenticated, service_role;
drop trigger if exists trg_profiles_lists_guard on public.profiles;
create trigger trg_profiles_lists_guard before insert or update of experience, education, skills, languages on public.profiles for each row execute function public.profiles_lists_guard();

-- ── 3. endorsements ──────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.skill_endorsements (
  profile_id uuid not null references public.profiles(id) on delete cascade,
  skill      text not null,
  endorser   uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (profile_id, skill, endorser),
  constraint skill_endorsements_not_self check (profile_id <> endorser),
  constraint skill_endorsements_skill_len check (length(skill) between 1 and 60)
);
create index if not exists idx_skill_endorsements_endorser on public.skill_endorsements (endorser);
alter table public.skill_endorsements enable row level security;
do $$ begin
  create policy "endorsements: members read" on public.skill_endorsements for select to authenticated using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "endorsements: own add" on public.skill_endorsements for insert to authenticated
    with check (endorser = (select auth.uid()) and exists (select 1 from public.profiles p where p.id = skill_endorsements.profile_id and skill_endorsements.skill = any (p.skills)));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "endorsements: own remove" on public.skill_endorsements for delete to authenticated using (endorser = (select auth.uid()));
exception when duplicate_object then null; end $$;
revoke all on table public.skill_endorsements from public, anon, authenticated, service_role;
grant select, insert, delete on table public.skill_endorsements to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.skill_endorsements to service_role;
create or replace function public.skill_endorsed() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.created_at := now();
  if exists (select 1 from public.user_blocks b where (b.blocker = new.profile_id and b.blocked = new.endorser) or (b.blocker = new.endorser and b.blocked = new.profile_id)) then
    raise exception 'You can''t endorse this person' using errcode = '42501';
  end if;
  if not exists (select 1 from public.notifications n where n.user_id = new.profile_id and n.from_user = new.endorser and n.type = 'endorse' and n.message = 'endorsed you for ' || new.skill) then
    insert into public.notifications (user_id, type, from_user, message, data) values (new.profile_id, 'endorse', new.endorser, 'endorsed you for ' || new.skill, jsonb_build_object('skill', new.skill));
  end if;
  return new;
end $$;
revoke all on function public.skill_endorsed() from public, anon, authenticated, service_role;
grant execute on function public.skill_endorsed() to service_role;
drop trigger if exists trg_skill_endorsed on public.skill_endorsements;
create trigger trg_skill_endorsed before insert on public.skill_endorsements for each row execute function public.skill_endorsed();
create or replace function public.skills_removed() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  delete from public.skill_endorsements e where e.profile_id = new.id and not (e.skill = any (coalesce(new.skills, '{}')));
  return null;
end $$;
revoke all on function public.skills_removed() from public, anon, authenticated, service_role;
grant execute on function public.skills_removed() to service_role;
drop trigger if exists trg_profiles_skills_removed on public.profiles;
create trigger trg_profiles_skills_removed after update of skills on public.profiles for each row execute function public.skills_removed();

-- ── 4. who viewed my profile ─────────────────────────────────────────────────────────────────────────────
create index if not exists idx_profile_view_log_target_day on public.profile_view_log (target, day desc);
create or replace function public.my_profile_viewers(p_limit int default 20) returns jsonb
language sql stable security definer set search_path = public as $$
  with v as (
    select l.viewer, max(l.day) as day from public.profile_view_log l
     where l.target = auth.uid() and l.day > current_date - 90 group by l.viewer),
  named as (
    select v.viewer, v.day from v join public.profiles p on p.id = v.viewer and p.account_type is distinct from 'deleted'
     left join public.member_settings s on s.user_id = v.viewer
     where coalesce(s.show_visits, true)
       and not exists (select 1 from public.user_blocks b where (b.blocker = auth.uid() and b.blocked = v.viewer) or (b.blocker = v.viewer and b.blocked = auth.uid())))
  select jsonb_build_object(
    'total', (select count(*) from v),
    'private', (select count(*) from v) - (select count(*) from named),
    'viewers', coalesce((select jsonb_agg(jsonb_build_object('id', p.id, 'name', p.name, 'headline', p.headline, 'company', p.company, 'avatar_url', p.avatar_url, 'verified', p.verified, 'day', n.day) order by n.day desc)
      from (select * from named order by day desc limit least(greatest(coalesce(p_limit, 20), 1), 100)) n join public.profiles p on p.id = n.viewer), '[]'::jsonb))
  where auth.uid() is not null
$$;
revoke all on function public.my_profile_viewers(int) from public, anon, authenticated, service_role;
grant execute on function public.my_profile_viewers(int) to authenticated;

notify pgrst, 'reload schema';
