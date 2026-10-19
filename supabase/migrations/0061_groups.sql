-- ═════════════════════════════════════════════════════════════════════
-- 0061 — Groups, the rest (G-01, G-04 … G-15; J-COMMUNITY-01 … 18)
--   1. groups         country (codes, for "By Country"), sector (Pharma / Cosmetics …), archived_at (read-only, hidden from
--                     discovery, members still read), post_policy (all members / admins only)
--   2. members        role 'moderator' (the Sub-Admin: removes posts and comments, handles reports and join requests; only admins
--                     change roles and settings); muted (no notices for new posts); the last admin can never be removed or
--                     demoted; a removed member is told
--   3. posts          an archived group takes no posts, comments or members; "admins only" groups take posts from admins and
--                     moderators; a new post tells the members (one unread notice per member and group, counting the new posts)
--   4. listings       deal-room requests and offers (group_listings), answered through group_listing_respond(): a deal is created
--                     by the deals engine (deal_create — never a direct insert); one answer per person and listing
-- Every table, sequence and function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. groups ───────────────────────────────────────────────────────────────────────────────────────────
alter table public.groups add column if not exists country     text[] not null default '{}';
alter table public.groups add column if not exists sector      text;
alter table public.groups add column if not exists archived_at timestamptz;
alter table public.groups add column if not exists post_policy text not null default 'members';
do $$ begin
  alter table public.groups add constraint groups_country_chk check (cardinality(country) <= 12 and array_to_string(country, ',') ~ '^([A-Z]{2}(,[A-Z]{2})*)?$');
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.groups add constraint groups_sector_chk check (sector is null or sector in ('pharma', 'cosmetics', 'devices', 'supplements', 'other'));
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.groups add constraint groups_post_policy_chk check (post_policy in ('members', 'admins'));
exception when duplicate_object then null; end $$;
create index if not exists idx_groups_country on public.groups using gin (country);
create index if not exists idx_groups_name_trgm on public.groups using gin (lower(name || ' ' || coalesce(description, '')) gin_trgm_ops);

-- archived groups are hidden from everyone but their members (and Drugbox moderators)
drop policy if exists "groups: archived only for members" on public.groups;
create policy "groups: archived only for members" on public.groups as restrictive for select to authenticated
  using (archived_at is null or created_by = (select auth.uid()) or public.is_group_member(id) or (select public.is_moderator()));

-- search: the groups whose name or description holds every word (any case, Arabic too), newest activity first
create or replace function public.groups_search(p_q text, p_limit int default 30)
returns setof public.groups language sql stable security invoker set search_path = public as $$
  select g.* from public.groups g
   where g.archived_at is null
     and not exists (select 1 from unnest(array_remove(regexp_split_to_array(lower(trim(coalesce(p_q, ''))), '\s+'), '')) w
                      where lower(g.name || ' ' || coalesce(g.description, '')) not like '%' || replace(replace(replace(w, '\', '\\'), '%', '\%'), '_', '\_') || '%')
   order by g.member_count desc, g.created_at desc
   limit least(greatest(coalesce(p_limit, 30), 1), 100)
$$;
revoke all on function public.groups_search(text, int) from public, anon, authenticated, service_role;
grant execute on function public.groups_search(text, int) to authenticated, service_role;

-- ── 2. members: the Sub-Admin role, mute, the last admin ────────────────────────────────────────────────
alter table public.group_members add column if not exists muted boolean not null default false;
alter table public.group_members drop constraint if exists group_members_role_check;
alter table public.group_members add constraint group_members_role_check check (role = any (array['member', 'moderator', 'admin']));

create or replace function public.group_members_guard() returns trigger
language plpgsql set search_path = public as $$
begin
  if tg_op = 'UPDATE' then
    if new.group_id <> old.group_id or new.user_id <> old.user_id then raise exception 'Membership cannot be moved' using errcode = '42501'; end if;
    new.joined_at := old.joined_at;
    if new.role is distinct from old.role and not public.is_server_call() and not public.is_group_member(old.group_id, array['admin']) then
      raise exception 'Only the group''s admins change roles' using errcode = '42501'; end if;
    if new.muted is distinct from old.muted and not public.is_server_call() and auth.uid() is distinct from old.user_id then
      raise exception 'Only the member chooses their notifications' using errcode = '42501'; end if;
    if old.role = 'admin' and new.role <> 'admin'
       and not exists (select 1 from public.group_members m where m.group_id = old.group_id and m.role = 'admin' and m.user_id <> old.user_id) then
      raise exception 'A group needs at least one admin — make someone else admin first' using errcode = '42501'; end if;
    return new;
  end if;
  -- DELETE: the last admin stays (unless the group itself is being deleted)
  if old.role = 'admin' and exists (select 1 from public.groups g where g.id = old.group_id)
     and not exists (select 1 from public.group_members m where m.group_id = old.group_id and m.role = 'admin' and m.user_id <> old.user_id) then
    raise exception 'A group needs at least one admin — make someone else admin first, or delete the group' using errcode = '42501'; end if;
  return old;
end $$;
revoke all on function public.group_members_guard() from public, anon, authenticated, service_role;
grant execute on function public.group_members_guard() to service_role;
drop trigger if exists trg_group_members_guard on public.group_members;
create trigger trg_group_members_guard before update or delete on public.group_members for each row execute function public.group_members_guard();

-- a member mutes or unmutes the group for themself (the guard keeps everything else as it was)
drop policy if exists "group members: a member sets their notifications" on public.group_members;
create policy "group members: a member sets their notifications" on public.group_members for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

-- an archived group takes no new members
drop policy if exists "group members: none join an archived group" on public.group_members;
create policy "group members: none join an archived group" on public.group_members as restrictive for insert to authenticated
  with check (not exists (select 1 from public.groups g where g.id = group_members.group_id and g.archived_at is not null));

-- a member removed by someone else is told (not when they leave, not when the group is deleted)
create or replace function public.notify_group_removed() returns trigger
language plpgsql security definer set search_path = public as $$
declare gname text;
begin
  if auth.uid() is null or auth.uid() = old.user_id then return null; end if;
  select name into gname from public.groups where id = old.group_id; if gname is null then return null; end if;
  insert into public.notifications (user_id, type, from_user, group_id, message)
  values (old.user_id, 'group_removed', auth.uid(), old.group_id, 'removed you from the group "' || left(gname, 120) || '"');
  return null;
end $$;
revoke all on function public.notify_group_removed() from public, anon, authenticated, service_role;
grant execute on function public.notify_group_removed() to service_role;
drop trigger if exists trg_notify_group_removed on public.group_members;
create trigger trg_notify_group_removed after delete on public.group_members for each row execute function public.notify_group_removed();

-- moderators (Sub-Admins) do the moderation work with the admins: remove posts and comments, read and close reports, answer requests
drop policy if exists "posts: group admins remove posts in their group" on public.posts;
create policy "posts: group admins remove posts in their group" on public.posts for delete to authenticated
  using (group_id is not null and public.is_group_member(group_id, array['admin', 'moderator']));
drop policy if exists "comments: group admins remove comments in their group" on public.comments;
create policy "comments: group admins remove comments in their group" on public.comments for delete to authenticated
  using (exists (select 1 from public.posts p where p.id = comments.post_id and p.group_id is not null and public.is_group_member(p.group_id, array['admin', 'moderator'])));
drop policy if exists "comments: the post's author removes comments on it" on public.comments;
create policy "comments: the post's author removes comments on it" on public.comments for delete to authenticated
  using (exists (select 1 from public.posts p where p.id = comments.post_id and p.user_id = (select auth.uid())));
drop policy if exists "group reports: the reporter and the group's admins read" on public.group_post_reports;
create policy "group reports: the reporter and the group's admins read" on public.group_post_reports for select
  using (reporter = (select auth.uid()) or public.is_group_member(group_id, array['admin', 'moderator']));
drop policy if exists "group reports: the group's admins dismiss" on public.group_post_reports;
create policy "group reports: the group's admins dismiss" on public.group_post_reports for update
  using (public.is_group_member(group_id, array['admin', 'moderator'])) with check (public.is_group_member(group_id, array['admin', 'moderator']));
drop policy if exists "group reports: the reporter withdraws, the group's admins clear" on public.group_post_reports;
create policy "group reports: the reporter withdraws, the group's admins clear" on public.group_post_reports for delete
  using (reporter = (select auth.uid()) or public.is_group_member(group_id, array['admin', 'moderator']));

create or replace function public.group_decide_request(p_group bigint, p_user uuid, p_approve boolean)
returns text language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); st text := case when p_approve then 'approved' else 'rejected' end; gname text;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if p_approve is null then raise exception 'Approve or decline' using errcode = '22023'; end if;
  if not public.is_group_member(p_group, array['admin', 'moderator']) then
    raise exception 'Only the group''s admins can answer join requests' using errcode = '42501';
  end if;
  update public.group_join_requests set status = st, decided_at = now(), decided_by = me
   where group_id = p_group and user_id = p_user and status = 'pending';
  if not found then raise exception 'There is no pending request from this person' using errcode = 'P0002'; end if;
  delete from public.notifications where type = 'group_join_request' and group_id = p_group and from_user = p_user;
  select name into gname from public.groups where id = p_group;
  delete from public.notifications where user_id = p_user and group_id = p_group and type in ('group_join_approved', 'group_join_declined');
  if p_approve then
    insert into public.group_members (group_id, user_id, role) values (p_group, p_user, 'member') on conflict do nothing;
    insert into public.notifications (user_id, type, from_user, group_id, message)
    values (p_user, 'group_join_approved', me, p_group, 'approved your request to join "' || left(coalesce(gname, ''), 120) || '"');
  else   -- told politely; they can ask again later
    insert into public.notifications (user_id, type, from_user, group_id, message)
    values (p_user, 'group_join_declined', me, p_group, 'could not accept your request to join "' || left(coalesce(gname, ''), 120) || '" this time');
  end if;
  return st;
end $$;
revoke all on function public.group_decide_request(bigint, uuid, boolean) from public, anon, authenticated, service_role;
grant execute on function public.group_decide_request(bigint, uuid, boolean) to authenticated, service_role;

-- ── 3. posting: archived groups and "admins only" groups; telling the members ──────────────────────────
create or replace function private.can_post_in_group(p_group bigint) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.groups g where g.id = p_group and g.archived_at is null
                   and (g.post_policy = 'members' or public.is_group_member(g.id, array['admin', 'moderator'])))
$$;
revoke all on function private.can_post_in_group(bigint) from public, anon, authenticated, service_role;
grant execute on function private.can_post_in_group(bigint) to authenticated, service_role;
create or replace function private.group_open(p_group bigint) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.groups g where g.id = p_group and g.archived_at is null)
$$;
revoke all on function private.group_open(bigint) from public, anon, authenticated, service_role;
grant execute on function private.group_open(bigint) to authenticated, service_role;
drop policy if exists "posts: groups that take posts" on public.posts;
create policy "posts: groups that take posts" on public.posts as restrictive for insert to authenticated
  with check (group_id is null or private.can_post_in_group(group_id));
drop policy if exists "comments: not in an archived group" on public.comments;
create policy "comments: not in an archived group" on public.comments as restrictive for insert to authenticated
  with check (not exists (select 1 from public.posts p where p.id = comments.post_id and p.group_id is not null and not private.group_open(p.group_id)));

create unique index if not exists idx_notifs_group_post_unread on public.notifications (user_id, group_id) where type = 'group_post' and read = false;
-- a new group post: one unread notice per member (not muted, not the author) and group — later posts update it ("3 new posts")
create or replace function public.notify_group_post() returns trigger
language plpgsql security definer set search_path = public as $$
declare gname text;
begin
  if new.group_id is null then return null; end if;
  select name into gname from public.groups where id = new.group_id;
  insert into public.notifications (user_id, type, from_user, group_id, post_id, message, data)
  select m.user_id, 'group_post', new.user_id, new.group_id, new.id, 'posted in "' || left(coalesce(gname, ''), 120) || '"', jsonb_build_object('n', 1)
    from public.group_members m
   where m.group_id = new.group_id and m.user_id <> new.user_id and not m.muted
  on conflict (user_id, group_id) where type = 'group_post' and read = false
  do update set from_user = excluded.from_user, post_id = excluded.post_id, created_at = now(),
                data = jsonb_build_object('n', coalesce((public.notifications.data ->> 'n')::int, 1) + 1),
                message = (coalesce((public.notifications.data ->> 'n')::int, 1) + 1)::text || ' new posts in "' || left(coalesce(gname, ''), 120) || '"';
  return null;
end $$;
revoke all on function public.notify_group_post() from public, anon, authenticated, service_role;
grant execute on function public.notify_group_post() to service_role;
drop trigger if exists trg_notify_group_post on public.posts;
create trigger trg_notify_group_post after insert on public.posts for each row when (new.group_id is not null) execute function public.notify_group_post();

-- ── 4. deal-room listings ───────────────────────────────────────────────────────────────────────────────
create table if not exists public.group_listings (
  id          bigint generated always as identity primary key,
  group_id    bigint not null references public.groups(id) on delete cascade,
  user_id     uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  company_id  bigint references public.companies(id) on delete set null,
  kind        text not null,
  title       text not null,
  details     text not null default '',
  price       text,
  status      text not null default 'open',
  responses   int not null default 0,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint group_listings_kind check (kind in ('rfq', 'sale', 'surplus')),
  constraint group_listings_status check (status in ('open', 'closed')),
  constraint group_listings_len check (length(title) between 3 and 120 and length(details) <= 400 and length(price) <= 60)
);
create index if not exists idx_group_listings_group on public.group_listings (group_id, created_at desc) where status = 'open';
create index if not exists idx_group_listings_user on public.group_listings (user_id);
create index if not exists idx_group_listings_company on public.group_listings (company_id) where company_id is not null;
alter table public.group_listings enable row level security;
drop policy if exists "group listings: who reads the group reads them" on public.group_listings;
create policy "group listings: who reads the group reads them" on public.group_listings for select to authenticated
  using (group_id in (select public.readable_group_ids()) or user_id = (select auth.uid()));
drop policy if exists "group listings: members post" on public.group_listings;
create policy "group listings: members post" on public.group_listings for insert to authenticated
  with check (user_id = (select auth.uid()) and public.is_group_member(group_id) and private.group_open(group_id)
              and exists (select 1 from public.groups g where g.id = group_id and g.topic = 'DEAL ROOM')
              and (company_id is null or public.is_company_member(company_id)));
drop policy if exists "group listings: the author or the group's admins change them" on public.group_listings;
create policy "group listings: the author or the group's admins change them" on public.group_listings for update to authenticated
  using (user_id = (select auth.uid()) or public.is_group_member(group_id, array['admin', 'moderator']))
  with check (user_id = (select auth.uid()) or public.is_group_member(group_id, array['admin', 'moderator']));
drop policy if exists "group listings: the author or the group's admins remove them" on public.group_listings;
create policy "group listings: the author or the group's admins remove them" on public.group_listings for delete to authenticated
  using (user_id = (select auth.uid()) or public.is_group_member(group_id, array['admin', 'moderator']));
revoke all on table public.group_listings from public, anon, authenticated, service_role;
grant select on table public.group_listings to anon;                           -- no policy for anon → an empty answer (F-26)
grant select, insert, update, delete on table public.group_listings to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.group_listings to service_role;
revoke all on sequence public.group_listings_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.group_listings_id_seq to authenticated, service_role;

-- the server keeps the counters and the dates; only the author or the group's admins change the text / status
create or replace function public.group_listings_guard() returns trigger
language plpgsql set search_path = public as $$
begin
  if public.is_server_call() then return new; end if;
  if tg_op = 'INSERT' then new.responses := 0; new.status := 'open'; new.created_at := now(); new.updated_at := now(); return new; end if;
  if new.group_id <> old.group_id or new.user_id <> old.user_id or new.kind <> old.kind then raise exception 'A listing cannot be moved' using errcode = '42501'; end if;
  new.responses := old.responses; new.created_at := old.created_at; new.updated_at := now();
  if (new.title, new.details, new.price, new.company_id) is distinct from (old.title, old.details, old.price, old.company_id) and auth.uid() <> old.user_id then
    raise exception 'Only the author edits a listing' using errcode = '42501'; end if;
  return new;
end $$;
revoke all on function public.group_listings_guard() from public, anon, authenticated, service_role;
grant execute on function public.group_listings_guard() to service_role;
drop trigger if exists trg_group_listings_guard on public.group_listings;
create trigger trg_group_listings_guard before insert or update on public.group_listings for each row execute function public.group_listings_guard();

create table if not exists public.group_listing_responses (
  listing_id bigint not null references public.group_listings(id) on delete cascade,
  user_id    uuid not null references public.profiles(id) on delete cascade,
  deal_ref   text,
  created_at timestamptz not null default now(),
  primary key (listing_id, user_id)
);
create index if not exists idx_group_listing_responses_user on public.group_listing_responses (user_id);
alter table public.group_listing_responses enable row level security;
drop policy if exists "listing answers: the person who answered and the listing's author read" on public.group_listing_responses;
create policy "listing answers: the person who answered and the listing's author read" on public.group_listing_responses for select to authenticated
  using (user_id = (select auth.uid()) or exists (select 1 from public.group_listings l where l.id = listing_id and l.user_id = (select auth.uid())));
revoke all on table public.group_listing_responses from public, anon, authenticated, service_role;
grant select on table public.group_listing_responses to anon;                  -- no policy for anon → an empty answer (F-26)
grant select on table public.group_listing_responses to authenticated;         -- written by group_listing_respond() only
grant select, insert, update, delete, truncate, references, trigger on table public.group_listing_responses to service_role;

-- answering a listing: a member of the deal room, on behalf of a company page they belong to. A request to buy (rfq) is answered with
-- an offer ('surplus' deal: the buyer accepts or counters); an offer is answered with a request for a quote ('quote' deal).
create or replace function public.group_listing_respond(p_listing bigint, p_from_slug text, p_message text default '', p_price text default null, p_lead text default null)
returns text language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); l public.group_listings; to_slug text; d public.deals; t text;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into l from public.group_listings where id = p_listing;
  if l.id is null then raise exception 'This listing is no longer available' using errcode = 'P0002'; end if;
  if not public.is_group_member(l.group_id) then raise exception 'Join the group to answer its listings' using errcode = '42501'; end if;
  if l.status <> 'open' or not private.group_open(l.group_id) then raise exception 'This listing is closed' using errcode = '42501'; end if;
  if l.user_id = me then raise exception 'This is your own listing' using errcode = '42501'; end if;
  if exists (select 1 from public.group_listing_responses r where r.listing_id = l.id and r.user_id = me) then
    raise exception 'You already answered this listing — follow it in your Deals' using errcode = '23505'; end if;
  select c.slug into to_slug from public.companies c where c.id = l.company_id;
  if to_slug is null then raise exception 'This listing has no company page — message its author instead' using errcode = '42501'; end if;
  t := left(l.title, 160);
  d := public.deal_create(case when l.kind = 'rfq' then 'surplus' else 'quote' end, to_slug, p_from_slug, t,
         jsonb_strip_nulls(jsonb_build_object('listing', l.id, 'group', l.group_id, 'price', nullif(left(coalesce(p_price, ''), 60), ''), 'lead', nullif(left(coalesce(p_lead, ''), 60), ''))),
         left(coalesce(p_message, ''), 600));
  insert into public.group_listing_responses (listing_id, user_id, deal_ref) values (l.id, me, d.ref);
  update public.group_listings set responses = responses + 1 where id = l.id;
  return d.ref;
end $$;
revoke all on function public.group_listing_respond(bigint, text, text, text, text) from public, anon, authenticated, service_role;
grant execute on function public.group_listing_respond(bigint, text, text, text, text) to authenticated, service_role;

notify pgrst, 'reload schema';
