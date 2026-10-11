-- ═════════════════════════════════════════════════════════════════════
-- 0027 — groups you can actually use: a discussion inside every group
--   The owner opened a group and found only its header: the database had no group posts at all (posts had no group_id; only
--   groups, group_members and group_invites existed). This adds what a group needs to be a place people talk in:
--   1. group posts — posts.group_id. A group post IS a post, so likes, comments, photos/files, saves, views, shares and
--      their notifications keep working unchanged. Who sees one: the group's members; every signed-in member when the group
--      is public; its author; Drugbox moderators. Who writes one: the group's members only. The global feed must ask for
--      group_id IS NULL (no feed RPC or view exists; the adapter reads public.posts directly).
--   2. comments, reactions, photos/files and saves follow their post: you read/add them only on a post you can read.
--   3. the group's admins moderate inside the group: remove posts and comments, pin one post (groups.pinned_post_id /
--      group_pin_post()), and answer reports from members (group_post_reports — the approved Manage → Reports tab).
--   4. private groups: "Members must be approved or invited" (the approved Create window). A private group can now be LISTED
--      (groups.listed: its card — name, description, rules, member count — is visible to signed-in members; its posts and
--      member list stay members-only) and people ask to join (group_join_requests via group_request_join()); the group's
--      admins are notified and approve or decline (group_decide_request()). A private group is unlisted by default (as
--      before: only members and invited people see it — deal rooms stay secret); a public group is always listed.
--   5. groups.rules; any admin of the group (not only its creator) edits the group's settings.
--   6. group_activity(ids): posts today / this week and the last post time for the group cards ("2 new posts this week").
-- Policy names of 0001/0021 are kept on purpose (their conditions change): 0024's reversible "open to the public" instructions
-- and the test suites refer to them by name.
-- Every new table/function has its own GRANT/REVOKE (Supabase no longer grants new objects automatically — 0026).
-- Safe to run twice. Checked by supabase/tests/group_posts.rls.sql.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. columns ───────────────────────────────────────────────────────────────────────────────
alter table public.posts  add column if not exists group_id bigint references public.groups (id) on delete cascade;
alter table public.groups add column if not exists rules text;
alter table public.groups add column if not exists listed boolean not null default false;
alter table public.groups add column if not exists pinned_post_id bigint references public.posts (id) on delete set null;
do $$ begin
  alter table public.groups add constraint groups_rules_len check (length(rules) <= 4000);
exception when duplicate_object then null; end $$;
update public.groups set listed = true where type = 'public' and not listed;          -- a public group is always listed

-- the group feed: one group's posts newest first, one keyset page at a time
create index if not exists idx_posts_group_feed on public.posts (group_id, created_at desc, id desc) where group_id is not null;
-- the main feed skips group posts without reading them (a busy group would otherwise fill the main feed's index pages)
create index if not exists idx_posts_main_feed on public.posts (created_at desc, id desc) where group_id is null;
create index if not exists idx_groups_pinned_post on public.groups (pinned_post_id) where pinned_post_id is not null;   -- FK (post deleted → unpinned)

-- ── 2. who can read a group's posts ──────────────────────────────────────────────────────────
-- (the view/share counters below; the row policy uses readable_group_ids(), the same rule as a set)
create or replace function public.can_read_group(gid bigint) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.groups g where g.id = gid
                 and (g.type = 'public' or exists (select 1 from public.group_members m where m.group_id = gid and m.user_id = auth.uid())))
$$;
revoke all on function public.can_read_group(bigint) from public, anon, authenticated, service_role;
grant execute on function public.can_read_group(bigint) to authenticated, service_role;

-- the same rule as a set — every public group plus the caller's own groups — for the row policy below: "group_id in (select …)"
-- is built once per query as a hash, where can_read_group(group_id) ran once per row (someone who is not a member asking for
-- a private group's feed made the database check all of its posts one by one: 240 ms at 20,000 posts, now 10 ms)
create or replace function public.readable_group_ids() returns setof bigint
language sql stable security definer set search_path = public as $$
  select g.id from public.groups g where g.type = 'public'
  union
  select m.group_id from public.group_members m where m.user_id = auth.uid()
$$;
revoke all on function public.readable_group_ids() from public, anon, authenticated, service_role;
grant execute on function public.readable_group_ids() to authenticated, service_role;

-- posts: the main feed (group_id null), your own posts, posts of groups you can read, and Drugbox moderators
alter policy "posts: everyone can read" on public.posts
  using (group_id is null or user_id = (select auth.uid()) or group_id in (select public.readable_group_ids()) or (select public.is_moderator()));
-- only a group's members post in it
alter policy "posts: own insert" on public.posts
  with check ((select auth.uid()) = user_id and (group_id is null or public.is_group_member(group_id)));
-- a group's admins remove posts in their group
drop policy if exists "posts: group admins remove posts in their group" on public.posts;
create policy "posts: group admins remove posts in their group" on public.posts for delete to authenticated
  using (group_id is not null and public.is_group_member(group_id, array['admin']));

-- a post never moves into, out of or between groups (that would skip the membership check above)
create or replace function public.posts_group_guard() returns trigger language plpgsql set search_path = public as $$
begin
  if new.group_id is distinct from old.group_id and not public.is_server_call() then
    raise exception 'A post cannot be moved into or out of a group' using errcode = '42501';
  end if;
  return new;
end $$;
revoke all on function public.posts_group_guard() from public, anon, authenticated, service_role;
grant execute on function public.posts_group_guard() to authenticated, service_role;
drop trigger if exists trg_posts_group_guard on public.posts;
create trigger trg_posts_group_guard before update of group_id on public.posts for each row execute function public.posts_group_guard();

-- ── 3. comments, reactions, files and saves follow their post ────────────────────────────────
-- (the sub-select reads public.posts under ITS row policy as the caller: visible post ⇔ visible comment/like/file)
alter policy "comments: everyone can read" on public.comments
  using (exists (select 1 from public.posts p where p.id = comments.post_id));
alter policy "comments: own insert" on public.comments
  with check ((select auth.uid()) = user_id and exists (select 1 from public.posts p where p.id = comments.post_id));
drop policy if exists "comments: group admins remove comments in their group" on public.comments;
create policy "comments: group admins remove comments in their group" on public.comments for delete to authenticated
  using (exists (select 1 from public.posts p where p.id = comments.post_id and p.group_id is not null
                 and public.is_group_member(p.group_id, array['admin'])));

alter policy "reactions: everyone can read" on public.reactions
  using (exists (select 1 from public.posts p where p.id = reactions.post_id));
alter policy "reactions: own manage" on public.reactions
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id and exists (select 1 from public.posts p where p.id = reactions.post_id));

alter policy "post media rows: everyone reads" on public.post_media
  using (exists (select 1 from public.posts p where p.id = post_media.post_id));

alter policy "saved: own" on public.saved_posts
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id and exists (select 1 from public.posts p where p.id = saved_posts.post_id));

-- views and shares count only posts the caller can read (0020's versions counted any post id, and the share count of any post)
create or replace function public.increment_post_views(post_ids bigint[]) returns void
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid();
begin
  if me is null then return; end if;
  with seen as (
    insert into public.post_view_log (post_id, viewer, kind)
    select p.id, me, 'view' from public.posts p
     where p.id = any(post_ids) and (p.group_id is null or p.user_id = me or public.can_read_group(p.group_id))
    on conflict do nothing returning post_id)
  update public.posts p set view_count = view_count + 1 from seen where p.id = seen.post_id;
end $$;
create or replace function public.increment_post_share(p_id bigint) returns integer
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); n int;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if not exists (select 1 from public.posts p where p.id = p_id and (p.group_id is null or p.user_id = me or public.can_read_group(p.group_id))) then
    return null;
  end if;
  insert into public.post_view_log (post_id, viewer, kind) values (p_id, me, 'share') on conflict do nothing;
  if found then update public.posts set share_count = share_count + 1 where id = p_id returning share_count into n;
  else select share_count into n from public.posts where id = p_id; end if;
  return n;
end $$;
revoke all on function public.increment_post_views(bigint[]) from public, anon, authenticated, service_role;
grant execute on function public.increment_post_views(bigint[]) to authenticated, service_role;
revoke all on function public.increment_post_share(bigint) from public, anon, authenticated, service_role;
grant execute on function public.increment_post_share(bigint) to authenticated, service_role;

-- ── 4. groups: listed private groups, rules, pinned post; every admin edits the settings ─────
alter policy "groups: public, own, member or invited read" on public.groups
  using (type = 'public' or listed or created_by = (select auth.uid()) or public.is_group_member(id)
         or exists (select 1 from public.group_invites i where i.group_id = groups.id and i.user_id = (select auth.uid())));
drop policy if exists "groups: admins edit the settings" on public.groups;
create policy "groups: admins edit the settings" on public.groups for update to authenticated
  using (public.is_group_member(id, array['admin'])) with check (public.is_group_member(id, array['admin']));

create or replace function public.groups_before_write() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.type = 'public' then new.listed := true; end if;                          -- public means anyone can find and join it
  if tg_op = 'INSERT' then
    new.pinned_post_id := null;                                                    -- a new group has no posts yet
    if new.topic = 'DEAL ROOM' and new.type = 'private' then new.listed := false; end if;   -- deal rooms stay secret
  elsif new.pinned_post_id is distinct from old.pinned_post_id and new.pinned_post_id is not null
        and not exists (select 1 from public.posts p where p.id = new.pinned_post_id and p.group_id = new.id) then
    raise exception 'Only a post of this group can be pinned in it' using errcode = '42501';
  end if;
  return new;
end $$;
revoke all on function public.groups_before_write() from public, anon, authenticated, service_role;
grant execute on function public.groups_before_write() to service_role;
drop trigger if exists trg_groups_before_write on public.groups;
create trigger trg_groups_before_write before insert or update on public.groups for each row execute function public.groups_before_write();

-- pin (or unpin with p_post null) one post of the group — its admins or Drugbox
create or replace function public.group_pin_post(p_group bigint, p_post bigint) returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if not (public.is_group_member(p_group, array['admin']) or public.is_platform_admin()) then
    raise exception 'Only the group''s admins can pin a post' using errcode = '42501';
  end if;
  if p_post is not null and not exists (select 1 from public.posts p where p.id = p_post and p.group_id = p_group) then
    raise exception 'Only a post of this group can be pinned in it' using errcode = '42501';
  end if;
  update public.groups set pinned_post_id = p_post where id = p_group;
end $$;
revoke all on function public.group_pin_post(bigint, bigint) from public, anon, authenticated, service_role;
grant execute on function public.group_pin_post(bigint, bigint) to authenticated, service_role;

-- ── 5. join requests for private groups ──────────────────────────────────────────────────────
create table if not exists public.group_join_requests (
  group_id   bigint not null references public.groups (id) on delete cascade,
  user_id    uuid   not null references public.profiles (id) on delete cascade,
  message    text check (length(message) <= 500),
  status     text   not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  created_at timestamptz not null default now(),
  decided_at timestamptz,
  decided_by uuid references public.profiles (id) on delete set null,
  primary key (group_id, user_id)
);
create index if not exists idx_group_join_requests_pending on public.group_join_requests (group_id, created_at) where status = 'pending';
create index if not exists idx_group_join_requests_user on public.group_join_requests (user_id);
create index if not exists idx_group_join_requests_decided_by on public.group_join_requests (decided_by) where decided_by is not null;
alter table public.group_join_requests enable row level security;
drop policy if exists "join requests: the person and the group's admins read" on public.group_join_requests;
create policy "join requests: the person and the group's admins read" on public.group_join_requests for select to authenticated
  using (user_id = (select auth.uid()) or public.is_group_member(group_id, array['admin']));
-- writes only through the functions below (status and approvals never come from the browser)
revoke all on table public.group_join_requests from public, anon, authenticated, service_role;
grant select on table public.group_join_requests to anon, authenticated;   -- anon: no policy → an empty answer, never an error (F-26)
grant select, insert, update, delete, truncate, references, trigger on table public.group_join_requests to service_role;

-- one "asked to join" notice per admin and person (removed when the request is answered or withdrawn)
create unique index if not exists idx_notifs_group_request_once on public.notifications (user_id, from_user, group_id)
  where type = 'group_join_request' and group_id is not null;

-- ask to join: a public group (or one you were invited to) is joined at once → 'member'; a listed private group gets a
-- request → 'pending' and its admins are notified. A declined request can be repeated 30 days after the answer.
create or replace function public.group_request_join(p_group bigint, p_message text default null) returns text
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); g public.groups; req public.group_join_requests; msg text := nullif(left(btrim(coalesce(p_message, '')), 500), '');
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into g from public.groups where id = p_group;
  if g.id is null then raise exception 'Group not found' using errcode = 'P0002'; end if;
  if exists (select 1 from public.group_members m where m.group_id = p_group and m.user_id = me) then return 'member'; end if;
  if g.type = 'public' or exists (select 1 from public.group_invites i where i.group_id = p_group and i.user_id = me) then
    insert into public.group_members (group_id, user_id, role) values (p_group, me, 'member') on conflict do nothing;
    return 'member';
  end if;
  if not g.listed then raise exception 'Group not found' using errcode = 'P0002'; end if;   -- an unlisted group is invitation-only
  select * into req from public.group_join_requests where group_id = p_group and user_id = me for update;
  if req.status = 'pending' then return 'pending'; end if;
  if req.status = 'rejected' and req.decided_at > now() - interval '30 days' then
    raise exception 'The group''s admins declined your last request — you can ask again from %', to_char(req.decided_at + interval '30 days', 'YYYY-MM-DD')
      using errcode = '42501';
  end if;
  if (select count(*) from public.group_join_requests r where r.user_id = me and r.status = 'pending') >= 20 then
    raise exception 'You have 20 requests waiting for an answer — please wait for the groups to reply' using errcode = '42501';
  end if;
  insert into public.group_join_requests as r (group_id, user_id, message, status, created_at)
  values (p_group, me, msg, 'pending', now())
  on conflict (group_id, user_id) do update set message = excluded.message, status = 'pending', created_at = now(), decided_at = null, decided_by = null;
  insert into public.notifications (user_id, type, from_user, group_id, message)
  select m.user_id, 'group_join_request', me, p_group, 'asked to join the private group "' || left(g.name, 120) || '"'
    from public.group_members m where m.group_id = p_group and m.role = 'admin' and m.user_id <> me
  on conflict (user_id, from_user, group_id) where type = 'group_join_request' and group_id is not null do nothing;
  return 'pending';
end $$;
revoke all on function public.group_request_join(bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.group_request_join(bigint, text) to authenticated, service_role;

-- withdraw your own pending request (the admins' notices go with it)
create or replace function public.group_cancel_request(p_group bigint) returns void
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid();
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  delete from public.group_join_requests where group_id = p_group and user_id = me and status = 'pending';
  if found then
    delete from public.notifications where type = 'group_join_request' and group_id = p_group and from_user = me;
  end if;
end $$;
revoke all on function public.group_cancel_request(bigint) from public, anon, authenticated, service_role;
grant execute on function public.group_cancel_request(bigint) to authenticated, service_role;

-- an admin of the group approves (→ member, the person is notified) or declines a pending request → 'approved' | 'rejected'
create or replace function public.group_decide_request(p_group bigint, p_user uuid, p_approve boolean) returns text
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); st text := case when p_approve then 'approved' else 'rejected' end; gname text;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if p_approve is null then raise exception 'Approve or decline' using errcode = '22023'; end if;
  if not public.is_group_member(p_group, array['admin']) then
    raise exception 'Only the group''s admins can answer join requests' using errcode = '42501';
  end if;
  update public.group_join_requests set status = st, decided_at = now(), decided_by = me
   where group_id = p_group and user_id = p_user and status = 'pending';
  if not found then raise exception 'There is no pending request from this person' using errcode = 'P0002'; end if;
  delete from public.notifications where type = 'group_join_request' and group_id = p_group and from_user = p_user;
  if p_approve then
    insert into public.group_members (group_id, user_id, role) values (p_group, p_user, 'member') on conflict do nothing;
    select name into gname from public.groups where id = p_group;
    delete from public.notifications where user_id = p_user and group_id = p_group and type = 'group_join_approved';
    insert into public.notifications (user_id, type, from_user, group_id, message)
    values (p_user, 'group_join_approved', me, p_group, 'approved your request to join "' || left(coalesce(gname, ''), 120) || '"');
  end if;
  return st;
end $$;
revoke all on function public.group_decide_request(bigint, uuid, boolean) from public, anon, authenticated, service_role;
grant execute on function public.group_decide_request(bigint, uuid, boolean) to authenticated, service_role;

-- joining by any other way (an invitation) answers a pending request too
create or replace function public.group_members_close_request() returns trigger language plpgsql security definer set search_path = public as $$
begin
  update public.group_join_requests set status = 'approved', decided_at = now()
   where group_id = new.group_id and user_id = new.user_id and status = 'pending';
  if found then
    delete from public.notifications where type = 'group_join_request' and group_id = new.group_id and from_user = new.user_id;
  end if;
  return null;
end $$;
revoke all on function public.group_members_close_request() from public, anon, authenticated, service_role;
grant execute on function public.group_members_close_request() to service_role;
drop trigger if exists trg_group_members_close_request on public.group_members;
create trigger trg_group_members_close_request after insert on public.group_members for each row execute function public.group_members_close_request();

-- ── 6. members report a group post to the group's admins (Manage → Reports) ──────────────────
create table if not exists public.group_post_reports (
  post_id    bigint not null references public.posts (id) on delete cascade,      -- "Remove post" deletes the report with it
  reporter   uuid   not null references public.profiles (id) on delete cascade,
  group_id   bigint not null references public.groups (id) on delete cascade,     -- set by the database from the post
  reason     text   not null check (length(btrim(reason)) between 1 and 500),
  status     text   not null default 'open' check (status in ('open', 'dismissed')),
  created_at timestamptz not null default now(),
  primary key (post_id, reporter)
);
create index if not exists idx_group_post_reports_group on public.group_post_reports (group_id, status, created_at desc);
create index if not exists idx_group_post_reports_reporter on public.group_post_reports (reporter);
alter table public.group_post_reports enable row level security;

create or replace function public.group_post_reports_before_write() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then
    select p.group_id into new.group_id from public.posts p where p.id = new.post_id;
    if new.group_id is null then raise exception 'Only a post in a group can be reported to its admins' using errcode = '22023'; end if;
    new.status := 'open'; new.created_at := now();
  else
    new.post_id := old.post_id; new.reporter := old.reporter; new.group_id := old.group_id;
    new.reason := old.reason; new.created_at := old.created_at;
  end if;
  return new;
end $$;
revoke all on function public.group_post_reports_before_write() from public, anon, authenticated, service_role;
grant execute on function public.group_post_reports_before_write() to service_role;
drop trigger if exists trg_group_post_reports_before_write on public.group_post_reports;
create trigger trg_group_post_reports_before_write before insert or update on public.group_post_reports for each row execute function public.group_post_reports_before_write();

drop policy if exists "group reports: the reporter and the group's admins read" on public.group_post_reports;
create policy "group reports: the reporter and the group's admins read" on public.group_post_reports for select to authenticated
  using (reporter = (select auth.uid()) or public.is_group_member(group_id, array['admin']));
drop policy if exists "group reports: a reader of the post reports it" on public.group_post_reports;
create policy "group reports: a reader of the post reports it" on public.group_post_reports for insert to authenticated
  with check (reporter = (select auth.uid()) and exists (select 1 from public.posts p where p.id = group_post_reports.post_id));
drop policy if exists "group reports: the group's admins dismiss" on public.group_post_reports;
create policy "group reports: the group's admins dismiss" on public.group_post_reports for update to authenticated
  using (public.is_group_member(group_id, array['admin'])) with check (public.is_group_member(group_id, array['admin']));
drop policy if exists "group reports: the reporter withdraws, the group's admins clear" on public.group_post_reports;
create policy "group reports: the reporter withdraws, the group's admins clear" on public.group_post_reports for delete to authenticated
  using (reporter = (select auth.uid()) or public.is_group_member(group_id, array['admin']));
revoke all on table public.group_post_reports from public, anon, authenticated, service_role;
grant select on table public.group_post_reports to anon;                  -- no policy for anon → an empty answer (F-26)
grant select, insert, delete on table public.group_post_reports to authenticated;
grant update (status) on table public.group_post_reports to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.group_post_reports to service_role;

-- ── 7. activity for the group cards ──────────────────────────────────────────────────────────
-- posts today / in the last 7 days (each capped at 1000) and the newest post's time, for up to 100 groups the caller can see
create or replace function public.group_activity(p_ids bigint[])
returns table (group_id bigint, posts_today int, posts_week int, last_post_at timestamptz)
language sql stable security definer set search_path = public as $$
  select g.id,
         (select count(*)::int from (select 1 from public.posts p where p.group_id = g.id and p.created_at >= date_trunc('day', now()) limit 1000) x),
         (select count(*)::int from (select 1 from public.posts p where p.group_id = g.id and p.created_at >= now() - interval '7 days' limit 1000) x),
         (select max(p.created_at) from public.posts p where p.group_id = g.id)
    from public.groups g
   where auth.uid() is not null and g.id = any(p_ids[1:100])
     and (g.type = 'public' or g.listed or g.created_by = auth.uid() or public.is_group_member(g.id)
          or exists (select 1 from public.group_invites i where i.group_id = g.id and i.user_id = auth.uid()))
$$;
revoke all on function public.group_activity(bigint[]) from public, anon, authenticated, service_role;
grant execute on function public.group_activity(bigint[]) to authenticated, service_role;

notify pgrst, 'reload schema';
