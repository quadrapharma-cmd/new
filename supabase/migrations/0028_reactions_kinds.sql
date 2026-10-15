-- 0028 — Home feed actions that used to end in a toast (P1 "stop the lying"): reactions with their kind, reports on posts.
--   1. reactions.kind: the six kinds of the approved reaction panel (like, support, celebrate, insightful, appreciation,
--      curious) — plus 'love', which older rows may hold. 0001 §2 already widened the check; it is asserted again here so a
--      database built from an older 0001 cannot refuse a kind the interface offers. Changing the kind is an UPDATE of the
--      same (post_id, user_id) row: the one like counter (trg_like_count, 0022) and the one notification (trg_notify_reaction)
--      ignore it, so a reaction is counted and notified once whatever kind it ends with. No new trigger on reactions.
--   2. post_reaction_summary(ids): how many of each kind on up to 100 posts the caller can read — the icons beside the
--      count on a post card. Runs as the caller (row-level security on reactions applies).
--   3. post_reports: a member reports a Home post (spam / counterfeit / misleading / abusive / other + a note), once per post.
--      The reporter reads their own reports, Drugbox moderators read all. Nobody edits or deletes a report through the API:
--      Drugbox decides with post_report_decide() — remove the post (the author is told why; every reporter is told the
--      outcome) or dismiss (the reporters are told the post stays up). Group posts are reported to their group's admins
--      (group_post_reports, 0027), not here.

-- ── 1. reaction kinds ──────────────────────────────────────────────────────────────────────────
alter table public.reactions drop constraint if exists reactions_kind_check;
alter table public.reactions add constraint reactions_kind_check
  check (kind in ('like','support','celebrate','insightful','appreciation','curious','love'));
alter table public.reactions alter column kind set default 'like';
update public.reactions set kind = 'like' where kind is null;
alter table public.reactions alter column kind set not null;

-- ── 2. reactions per kind, for the post cards ─────────────────────────────────────────────────
create or replace function public.post_reaction_summary(p_ids bigint[])
returns table (post_id bigint, kind text, n int)
language sql stable security invoker set search_path = public as $$
  select r.post_id, r.kind, count(*)::int
    from public.reactions r
   where r.post_id = any(p_ids[1:100])
   group by r.post_id, r.kind
$$;
revoke all on function public.post_reaction_summary(bigint[]) from public, anon, authenticated, service_role;
grant execute on function public.post_reaction_summary(bigint[]) to authenticated, service_role;

-- ── 3. reports on Home posts ──────────────────────────────────────────────────────────────────
create table if not exists public.post_reports (
  id           bigserial primary key,
  post_id      bigint references public.posts(id) on delete set null,       -- the post may be removed; the report stays as a record
  post_author  uuid references public.profiles(id) on delete set null,      -- filled by the database from the post
  post_excerpt text,                                                        -- filled by the database: what the moderator decides on
  reporter     uuid not null references public.profiles(id) on delete cascade,
  reason       text not null check (reason in ('spam','counterfeit','misleading','abusive','other')),
  note         text check (char_length(note) <= 500),
  status       text not null default 'open' check (status in ('open','removed','dismissed')),
  decided_by   uuid references public.profiles(id) on delete set null,
  decision_note text check (char_length(decision_note) <= 500),
  decided_at   timestamptz,
  created_at   timestamptz not null default now()
);
create unique index if not exists idx_post_reports_once on public.post_reports (post_id, reporter);   -- "You already reported this"
create index if not exists idx_post_reports_open on public.post_reports (status, created_at) where status = 'open';
create index if not exists idx_post_reports_reporter on public.post_reports (reporter);
create index if not exists idx_post_reports_author on public.post_reports (post_author) where post_author is not null;
create index if not exists idx_post_reports_decided_by on public.post_reports (decided_by) where decided_by is not null;
alter table public.post_reports enable row level security;

-- what the browser sends is reporter, post, reason and note; the rest is the database's
create or replace function public.post_reports_before_insert() returns trigger
language plpgsql security definer set search_path = public as $$
declare p record;
begin
  select id, user_id, body, group_id into p from public.posts where id = new.post_id;
  if p.id is null then raise exception 'This post is no longer available' using errcode = 'P0002'; end if;
  if p.group_id is not null then raise exception 'Report group posts to the group admins' using errcode = '42501'; end if;
  if p.user_id = new.reporter then raise exception 'You cannot report your own post' using errcode = '42501'; end if;
  new.post_author := p.user_id;
  new.post_excerpt := left(coalesce(p.body, ''), 600);
  new.status := 'open'; new.decided_by := null; new.decision_note := null; new.decided_at := null; new.created_at := now();
  return new;
end; $$;
revoke all on function public.post_reports_before_insert() from public, anon, authenticated, service_role;
drop trigger if exists trg_post_reports_before_insert on public.post_reports;
create trigger trg_post_reports_before_insert before insert on public.post_reports
  for each row execute function public.post_reports_before_insert();

drop policy if exists "post reports: file as yourself" on public.post_reports;
create policy "post reports: file as yourself" on public.post_reports for insert to authenticated
  with check (reporter = (select auth.uid()) and exists (select 1 from public.posts p where p.id = post_reports.post_id));
drop policy if exists "post reports: the reporter and Drugbox read" on public.post_reports;
create policy "post reports: the reporter and Drugbox read" on public.post_reports for select to authenticated
  using (reporter = (select auth.uid()) or public.is_moderator());
revoke all on table public.post_reports from public, anon, authenticated, service_role;
grant select on table public.post_reports to anon;                        -- no policy for anon → an empty answer (F-26)
grant select on table public.post_reports to authenticated;
grant insert (post_id, reporter, reason, note) on table public.post_reports to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.post_reports to service_role;
revoke all on sequence public.post_reports_id_seq from public, anon, authenticated, service_role;
grant usage on sequence public.post_reports_id_seq to authenticated;
grant usage, select, update on sequence public.post_reports_id_seq to service_role;

-- Drugbox decides: p_remove = true removes the post (its comments, reactions, saves and files go with it) and closes every
-- open report on it; false dismisses them. The author and each reporter get one notification saying what happened.
create or replace function public.post_report_decide(p_report bigint, p_remove boolean, p_note text default null)
returns int language plpgsql security definer set search_path = public as $$
declare r record; me uuid := auth.uid(); n int := 0; why text; v_note text := nullif(left(trim(coalesce(p_note, '')), 500), '');
begin
  if me is null or not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  select * into r from public.post_reports where id = p_report;
  if r.id is null then raise exception 'This report does not exist' using errcode = 'P0002'; end if;
  if r.status <> 'open' then return 0; end if;                              -- already decided (another moderator, another tab)
  why := case r.reason when 'spam' then 'spam or an unrelated ad' when 'counterfeit' then 'an unverified or counterfeit product'
                       when 'misleading' then 'misleading information' when 'abusive' then 'harassment or hate' else 'it breaks the Drugbox rules' end;
  -- every open report on the same post is closed by the same decision (one row per post in the review queue)
  with done as (
    update public.post_reports set status = case when p_remove then 'removed' else 'dismissed' end,
           decided_by = me, decision_note = v_note, decided_at = now()
     where status = 'open' and ((r.post_id is not null and post_id = r.post_id) or id = r.id)
    returning reporter)
  insert into public.notifications (user_id, type, from_user, message)
  select distinct reporter, 'report_closed', null::uuid,
         case when p_remove then 'Drugbox reviewed your report and removed the post.' else 'Drugbox reviewed your report — the post stays up.' end
    from done;
  get diagnostics n = row_count;
  if p_remove then
    if r.post_author is not null then
      insert into public.notifications (user_id, type, from_user, message)
      values (r.post_author, 'post_removed', null,
              'Drugbox removed your post “' || left(coalesce(r.post_excerpt, ''), 80) || case when char_length(coalesce(r.post_excerpt, '')) > 80 then '…' else '' end
              || '” — reason: ' || why || '.' || coalesce(' Note: ' || v_note, ''));
    end if;
    if r.post_id is not null then delete from public.posts where id = r.post_id; end if;
  end if;
  return n;
end; $$;
revoke all on function public.post_report_decide(bigint, boolean, text) from public, anon, authenticated, service_role;
grant execute on function public.post_report_decide(bigint, boolean, text) to authenticated, service_role;

notify pgrst, 'reload schema';
