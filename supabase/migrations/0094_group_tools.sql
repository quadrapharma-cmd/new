-- ═════════════════════════════════════════════════════════════════════
-- 0094 — tools for a group's admins, and moving a WhatsApp group honestly (area w-trust: W-08, W-44)
--   W-08 — group settings the admins choose (groups columns, edited like the other settings), kept by the database:
--     rules_required    a member reads and accepts the rules before joining (group_rule_acceptances; group_accept_rules)
--     daily_post_limit  posts a member may publish a day in the group (1–50; Cairo's day)
--     slow_mode_minutes minutes between two posts of a member (1–1440)
--     block_duplicates  the same words posted again in the group within 7 days are refused (on by default)
--     block_links       invite links to outside chat groups are refused
--     review_posts      members' posts wait in Manage → Pending posts until an admin publishes them (posts.group_pending)
--     require_category  a post says what it is (the post's category: not "general")
--     Group admins and Sub-Admins are not limited. Every refusal says why (EN; the app translates) with a DX42x code.
--   W-44 — the group's admin invites its members with a LINK they share themselves; every person joins by themselves (after
--     reading the rules): group_invite_links (group_link_create / group_link_revoke / group_link_preview / group_join_by_link).
--     Drugbox never imports phone numbers, contacts or members. A group's admin can ask Drugbox to mark the group as a
--     "Drugbox partner group" (group_partner_requests → Admin → Review, groups.partner_at set by Drugbox only).
-- Every new table / function has its own GRANT / REVOKE (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. settings ────
alter table public.groups add column if not exists rules_required    boolean not null default false;
alter table public.groups add column if not exists daily_post_limit  int;
alter table public.groups add column if not exists slow_mode_minutes int;
alter table public.groups add column if not exists block_duplicates  boolean not null default true;
alter table public.groups add column if not exists block_links       boolean not null default false;
alter table public.groups add column if not exists review_posts      boolean not null default false;
alter table public.groups add column if not exists require_category  boolean not null default false;
alter table public.groups add column if not exists partner_at        timestamptz;
do $$ begin
  alter table public.groups add constraint groups_tools_range check ((daily_post_limit is null or daily_post_limit between 1 and 50)
                                                                     and (slow_mode_minutes is null or slow_mode_minutes between 1 and 1440));
exception when duplicate_object then null; end $$;
grant select (rules_required, daily_post_limit, slow_mode_minutes, block_duplicates, block_links, review_posts, require_category, partner_at)
  on table public.groups to anon, authenticated;

-- only Drugbox marks a partner group (the admins' settings update cannot)
create or replace function public.groups_partner_guard() returns trigger language plpgsql set search_path = public as $$
begin
  if public.is_server_call() then return new; end if;
  if tg_op = 'INSERT' then new.partner_at := null; elsif new.partner_at is distinct from old.partner_at then new.partner_at := old.partner_at; end if;
  return new;
end $$;
revoke all on function public.groups_partner_guard() from public, anon, authenticated, service_role;
grant execute on function public.groups_partner_guard() to authenticated, service_role;
drop trigger if exists trg_groups_partner_guard on public.groups;
create trigger trg_groups_partner_guard before insert or update on public.groups for each row execute function public.groups_partner_guard();

-- ── 2. posting rules ────
alter table public.posts add column if not exists group_pending boolean not null default false;
grant select (group_pending) on table public.posts to anon, authenticated;
create index if not exists idx_posts_group_user on public.posts (group_id, user_id, created_at desc) where group_id is not null;
create index if not exists idx_posts_group_pending on public.posts (group_id, created_at) where group_pending;

create or replace function public.posts_group_rules() returns trigger language plpgsql security definer set search_path = public as $$
declare g public.groups; me uuid := auth.uid(); n int; last_at timestamptz; nb text; day0 timestamptz;
begin
  if new.group_id is null then new.group_pending := false; return new; end if;
  if tg_op = 'UPDATE' then
    if current_setting('drugbox.group_publish', true) = '1' then return new; end if;
    new.group_pending := old.group_pending;                                          -- only group_publish_post changes it
    if new.body is not distinct from old.body or me is null then return new; end if;
  else
    new.group_pending := false;
  end if;
  if me is null then return new; end if;                                             -- server writes (imports, fixtures)
  select * into g from public.groups where id = new.group_id;
  if g.id is null or public.is_group_member(g.id, array['admin', 'moderator']) or public.is_moderator() then return new; end if;
  nb := private.review_norm(new.body);
  if g.block_links and nb ~* 'chat\.whatsapp\.com|wa\.me/|whatsapp\.com/(channel|invite)|t\.me/|telegram\.(me|dog)/|telegram\.org/joinchat|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/' then
    raise exception 'Links to outside chat groups are not allowed in this group' using errcode = '42501', hint = 'DX423';
  end if;
  if tg_op = 'INSERT' then
    if g.require_category and coalesce(new.category, 'general') = 'general' then
      raise exception 'This group asks every post to say what it is — choose a category' using errcode = '22023', hint = 'DX424';
    end if;
    if g.daily_post_limit is not null then
      day0 := (date_trunc('day', now() at time zone 'Africa/Cairo')) at time zone 'Africa/Cairo';
      select count(*) into n from public.posts p where p.group_id = g.id and p.user_id = me and p.created_at >= day0;
      if n >= g.daily_post_limit then
        raise exception 'This group allows % post(s) a day per member — you can post again tomorrow', g.daily_post_limit using errcode = '54000', hint = 'DX420';
      end if;
    end if;
    if g.slow_mode_minutes is not null then
      select max(p.created_at) into last_at from public.posts p where p.group_id = g.id and p.user_id = me;
      if last_at is not null and last_at > now() - make_interval(mins => g.slow_mode_minutes) then
        raise exception 'Slow mode: this group allows one post every % minute(s) — wait % more', g.slow_mode_minutes,
          greatest(1, ceil(extract(epoch from (last_at + make_interval(mins => g.slow_mode_minutes) - now())) / 60))::int using errcode = '54000', hint = 'DX421';
      end if;
    end if;
  end if;
  if g.block_duplicates and char_length(nb) >= 12 and exists (
       select 1 from public.posts p where p.group_id = g.id and p.id is distinct from new.id and p.created_at > now() - interval '7 days'
          and p.user_id = me and private.review_norm(p.body) = nb) then
    raise exception 'You already posted this in the group this week — edit the earlier post instead of posting it again' using errcode = '23505', hint = 'DX422';
  end if;
  if tg_op = 'INSERT' and g.review_posts then new.group_pending := true; end if;
  return new;
end $$;
revoke all on function public.posts_group_rules() from public, anon, authenticated, service_role;
grant execute on function public.posts_group_rules() to authenticated, service_role;
drop trigger if exists trg_posts_c_group_rules on public.posts;
create trigger trg_posts_c_group_rules before insert or update on public.posts for each row execute function public.posts_group_rules();

-- a pending post is read by its author, the group's admins and Drugbox (restrictive: added to every other read rule)
drop policy if exists "posts: waiting for the group's admins" on public.posts;
create policy "posts: waiting for the group's admins" on public.posts as restrictive for select
  using (not group_pending or user_id = (select auth.uid()) or public.is_group_member(group_id, array['admin', 'moderator']) or (select public.is_moderator()));

-- a pending post tells nobody yet (0091's notify_group_post) — told when it is published
create or replace function public.notify_group_post() returns trigger
language plpgsql security definer set search_path = public as $$
declare gname text;
begin
  if new.group_id is null or new.review_hold or new.group_pending then return null; end if;
  if tg_op = 'UPDATE' and not ((old.review_hold or old.group_pending) and not (new.review_hold or new.group_pending)) then return null; end if;
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
drop trigger if exists trg_notify_group_post_released on public.posts;
create trigger trg_notify_group_post_released after update of review_hold, group_pending on public.posts for each row
  when (new.group_id is not null and (old.review_hold or old.group_pending) and not (new.review_hold or new.group_pending)) execute function public.notify_group_post();

-- the admins publish or decline a pending post (declining deletes it; the author is told either way)
create or replace function public.group_publish_post(p_post bigint, p_publish boolean) returns text
language plpgsql security definer set search_path = public as $$
declare p public.posts; gname text;
begin
  select * into p from public.posts where id = p_post for update;
  if p.id is null or p.group_id is null then raise exception 'Post not found' using errcode = 'P0002'; end if;
  if not public.is_group_member(p.group_id, array['admin', 'moderator']) then raise exception 'Only the group''s admins decide' using errcode = '42501'; end if;
  if not p.group_pending then raise exception 'This post was already decided' using errcode = '22023', hint = 'DX409'; end if;
  select name into gname from public.groups where id = p.group_id;
  if p_publish then
    perform set_config('drugbox.group_publish', '1', true);
    update public.posts set group_pending = false where id = p.id;
    perform set_config('drugbox.group_publish', '', true);
  else
    delete from public.posts where id = p.id;    -- notify_group_post_removed (0061) tells the author
  end if;
  if p_publish then
    insert into public.notifications (user_id, type, from_user, group_id, post_id, message, data)
    values (p.user_id, 'group_post_published', auth.uid(), p.group_id, p.id, 'published your post in "' || left(coalesce(gname, ''), 120) || '"', jsonb_build_object('excerpt', left(p.body, 80)));
  end if;
  return case when p_publish then 'published' else 'declined' end;
end $$;
revoke all on function public.group_publish_post(bigint, boolean) from public, anon, authenticated, service_role;
grant execute on function public.group_publish_post(bigint, boolean) to authenticated, service_role;

create or replace function public.group_pending_posts(p_group bigint) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when not public.is_group_member(p_group, array['admin', 'moderator']) then null else coalesce((select jsonb_agg(to_jsonb(x) order by x.created_at) from (
    select p.id, p.body, p.category, p.created_at, p.user_id, (select a.name from public.profiles a where a.id = p.user_id) as author
      from public.posts p where p.group_id = p_group and p.group_pending and not p.review_hold order by p.created_at limit 100) x), '[]'::jsonb) end
$$;
revoke all on function public.group_pending_posts(bigint) from public, anon, authenticated, service_role;
grant execute on function public.group_pending_posts(bigint) to authenticated, service_role;

-- ── 3. the rules before joining ────
create table if not exists public.group_rule_acceptances (
  group_id    bigint not null references public.groups(id) on delete cascade,
  user_id     uuid not null references public.profiles(id) on delete cascade,
  accepted_at timestamptz not null default now(),
  primary key (group_id, user_id)
);
create index if not exists idx_group_rule_acceptances_user on public.group_rule_acceptances (user_id);
alter table public.group_rule_acceptances enable row level security;
drop policy if exists "rule acceptances: the member and the group's admins read" on public.group_rule_acceptances;
create policy "rule acceptances: the member and the group's admins read" on public.group_rule_acceptances for select to authenticated
  using (user_id = (select auth.uid()) or public.is_group_member(group_id, array['admin', 'moderator']));
revoke all on table public.group_rule_acceptances from public, anon, authenticated, service_role;
grant select on table public.group_rule_acceptances to anon, authenticated;      -- written by group_accept_rules only
grant select, insert, update, delete, truncate, references, trigger on table public.group_rule_acceptances to service_role;

create or replace function public.group_accept_rules(p_group bigint) returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if not exists (select 1 from public.groups g where g.id = p_group and g.archived_at is null
                   and (g.type = 'public' or g.listed or public.is_group_member(g.id)
                        or exists (select 1 from public.group_invites i where i.group_id = g.id and i.user_id = auth.uid())
                        or exists (select 1 from public.group_invite_links l where l.group_id = g.id and l.revoked_at is null))) then
    raise exception 'Group not found' using errcode = 'P0002'; end if;
  insert into public.group_rule_acceptances (group_id, user_id) values (p_group, auth.uid())
  on conflict (group_id, user_id) do update set accepted_at = now();
end $$;

-- a member who joins by themselves has accepted the rules when the group asks for it (admins adding / approving are not asked)
create or replace function public.group_members_rules_guard() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null or new.user_id <> auth.uid() or new.role in ('admin', 'moderator') then return new; end if;
  if exists (select 1 from public.groups g where g.id = new.group_id and g.rules_required and g.created_by <> new.user_id)
     and not exists (select 1 from public.group_rule_acceptances a where a.group_id = new.group_id and a.user_id = new.user_id) then
    raise exception 'Read and accept the group''s rules first' using errcode = '42501', hint = 'DX425';
  end if;
  return new;
end $$;
revoke all on function public.group_members_rules_guard() from public, anon, authenticated, service_role;
grant execute on function public.group_members_rules_guard() to authenticated, service_role;
drop trigger if exists trg_group_members_rules_guard on public.group_members;
create trigger trg_group_members_rules_guard before insert on public.group_members for each row execute function public.group_members_rules_guard();
-- a join REQUEST to a private group also needs the rules accepted first
create or replace function public.group_join_requests_rules_guard() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null or new.user_id <> auth.uid() then return new; end if;
  if exists (select 1 from public.groups g where g.id = new.group_id and g.rules_required)
     and not exists (select 1 from public.group_rule_acceptances a where a.group_id = new.group_id and a.user_id = new.user_id) then
    raise exception 'Read and accept the group''s rules first' using errcode = '42501', hint = 'DX425';
  end if;
  return new;
end $$;
revoke all on function public.group_join_requests_rules_guard() from public, anon, authenticated, service_role;
grant execute on function public.group_join_requests_rules_guard() to authenticated, service_role;
drop trigger if exists trg_group_join_requests_rules_guard on public.group_join_requests;
create trigger trg_group_join_requests_rules_guard before insert on public.group_join_requests for each row execute function public.group_join_requests_rules_guard();

-- ── 4. invite links (W-44) ────
create table if not exists public.group_invite_links (
  id          bigint generated always as identity primary key,
  group_id    bigint not null references public.groups(id) on delete cascade,
  token       text not null unique,
  created_by  uuid references public.profiles(id) on delete set null,
  expires_at  timestamptz,
  max_uses    int check (max_uses is null or max_uses between 1 and 100000),
  uses        int not null default 0,
  revoked_at  timestamptz,
  created_at  timestamptz not null default now(),
  constraint group_invite_links_token check (token ~ '^[A-Za-z0-9_-]{20,40}$')
);
create index if not exists idx_group_invite_links_group on public.group_invite_links (group_id, created_at desc);
create index if not exists idx_group_invite_links_by on public.group_invite_links (created_by);
alter table public.group_invite_links enable row level security;
drop policy if exists "invite links: the group's admins read" on public.group_invite_links;
create policy "invite links: the group's admins read" on public.group_invite_links for select to authenticated
  using (public.is_group_member(group_id, array['admin', 'moderator']));
revoke all on table public.group_invite_links from public, anon, authenticated, service_role;
grant select on table public.group_invite_links to anon, authenticated;         -- written through the functions only
grant select, insert, update, delete, truncate, references, trigger on table public.group_invite_links to service_role;
revoke all on sequence public.group_invite_links_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.group_invite_links_id_seq to service_role;

revoke all on function public.group_accept_rules(bigint) from public, anon, authenticated, service_role;
grant execute on function public.group_accept_rules(bigint) to authenticated, service_role;

create or replace function public.group_link_create(p_group bigint, p_days int default null, p_max int default null) returns jsonb
language plpgsql security definer set search_path = public as $$
declare t text; r public.group_invite_links;
begin
  if not public.is_group_member(p_group, array['admin', 'moderator']) then raise exception 'Only the group''s admins make invite links' using errcode = '42501'; end if;
  if exists (select 1 from public.groups g where g.id = p_group and g.archived_at is not null) then raise exception 'This group is archived' using errcode = '42501'; end if;
  if (select count(*) from public.group_invite_links l where l.group_id = p_group and l.revoked_at is null and (l.expires_at is null or l.expires_at > now())) >= 5 then
    raise exception 'A group keeps at most 5 active invite links — stop one first' using errcode = '54000', hint = 'DX426'; end if;
  if p_days is not null and p_days not between 1 and 365 then raise exception 'A link lasts 1 to 365 days' using errcode = '22023'; end if;
  t := replace(gen_random_uuid()::text, '-', '') || left(replace(gen_random_uuid()::text, '-', ''), 8);   -- 40 random hex characters
  insert into public.group_invite_links (group_id, token, created_by, expires_at, max_uses)
  values (p_group, t, auth.uid(), case when p_days is null then null else now() + make_interval(days => p_days) end, p_max) returning * into r;
  return to_jsonb(r);
end $$;
revoke all on function public.group_link_create(bigint, int, int) from public, anon, authenticated, service_role;
grant execute on function public.group_link_create(bigint, int, int) to authenticated, service_role;

create or replace function public.group_link_revoke(p_link bigint) returns void
language plpgsql security definer set search_path = public as $$
declare g bigint;
begin
  select group_id into g from public.group_invite_links where id = p_link;
  if g is null or not public.is_group_member(g, array['admin', 'moderator']) then raise exception 'Only the group''s admins stop invite links' using errcode = '42501'; end if;
  update public.group_invite_links set revoked_at = coalesce(revoked_at, now()) where id = p_link;
end $$;
revoke all on function public.group_link_revoke(bigint) from public, anon, authenticated, service_role;
grant execute on function public.group_link_revoke(bigint) to authenticated, service_role;

-- what the person who opens a link sees before joining (signed in): the group, its rules, whether the link still works
create or replace function public.group_link_preview(p_token text) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when auth.uid() is null then null else (
    select jsonb_build_object('group_id', g.id, 'name', g.name, 'emoji', g.emoji, 'description', g.description, 'type', g.type, 'rules', g.rules,
                              'rules_required', g.rules_required, 'member_count', g.member_count, 'partner', g.partner_at is not null,
                              'member', public.is_group_member(g.id),
                              'ok', l.revoked_at is null and (l.expires_at is null or l.expires_at > now()) and (l.max_uses is null or l.uses < l.max_uses) and g.archived_at is null)
      from public.group_invite_links l join public.groups g on g.id = l.group_id where l.token = p_token) end
$$;
revoke all on function public.group_link_preview(text) from public, anon, authenticated, service_role;
grant execute on function public.group_link_preview(text) to authenticated, service_role;

-- the person joins by themselves (the link is the admins' invitation, also for a private group)
create or replace function public.group_join_by_link(p_token text, p_accept_rules boolean default false) returns text
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); l public.group_invite_links; g public.groups;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if private.is_suspended(me) then raise exception 'Your account is suspended' using errcode = '42501'; end if;
  select * into l from public.group_invite_links where token = p_token for update;
  if l.id is null then raise exception 'This invite link does not exist' using errcode = 'P0002', hint = 'DX427'; end if;
  select * into g from public.groups where id = l.group_id;
  if l.revoked_at is not null or (l.expires_at is not null and l.expires_at <= now()) or (l.max_uses is not null and l.uses >= l.max_uses) or g.archived_at is not null then
    raise exception 'This invite link no longer works — ask the group''s admin for a new one' using errcode = '42501', hint = 'DX428'; end if;
  if exists (select 1 from public.group_members m where m.group_id = g.id and m.user_id = me) then return 'already'; end if;
  if exists (select 1 from public.user_blocks b join public.group_members m on m.user_id = b.blocker
              where m.group_id = g.id and m.role = 'admin' and b.blocked = me) then
    raise exception 'You cannot join this group' using errcode = '42501'; end if;
  if g.rules_required then
    if not coalesce(p_accept_rules, false) then raise exception 'Read and accept the group''s rules first' using errcode = '42501', hint = 'DX425'; end if;
    insert into public.group_rule_acceptances (group_id, user_id) values (g.id, me) on conflict (group_id, user_id) do update set accepted_at = now();
  end if;
  insert into public.group_members (group_id, user_id, role) values (g.id, me, 'member') on conflict do nothing;
  delete from public.group_join_requests where group_id = g.id and user_id = me;
  update public.group_invite_links set uses = uses + 1 where id = l.id;
  return 'member';
end $$;
revoke all on function public.group_join_by_link(text, boolean) from public, anon, authenticated, service_role;
grant execute on function public.group_join_by_link(text, boolean) to authenticated, service_role;

-- ── 5. Drugbox partner groups ────
create table if not exists public.group_partner_requests (
  group_id     bigint primary key references public.groups(id) on delete cascade,
  requested_by uuid references public.profiles(id) on delete set null,
  note         text not null check (char_length(note) between 10 and 1000),
  status       text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  decided_by   uuid references public.profiles(id) on delete set null,
  decision_note text check (char_length(coalesce(decision_note, '')) <= 500),
  created_at   timestamptz not null default now(),
  decided_at   timestamptz
);
create index if not exists idx_group_partner_requests_pending on public.group_partner_requests (created_at) where status = 'pending';
create index if not exists idx_group_partner_requests_by on public.group_partner_requests (requested_by);
create index if not exists idx_group_partner_requests_decided_by on public.group_partner_requests (decided_by);
alter table public.group_partner_requests enable row level security;
drop policy if exists "partner requests: the group's admins and Drugbox read" on public.group_partner_requests;
create policy "partner requests: the group's admins and Drugbox read" on public.group_partner_requests for select to authenticated
  using (public.is_group_member(group_id, array['admin']) or (select public.is_moderator()));
revoke all on table public.group_partner_requests from public, anon, authenticated, service_role;
grant select on table public.group_partner_requests to anon, authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.group_partner_requests to service_role;

create or replace function public.group_partner_request(p_group bigint, p_note text) returns void
language plpgsql security definer set search_path = public as $$
declare v text := btrim(coalesce(p_note, ''));
begin
  if not public.is_group_member(p_group, array['admin']) then raise exception 'Only the group''s admins ask for this' using errcode = '42501'; end if;
  if char_length(v) < 10 then raise exception 'Tell Drugbox about the group in at least 10 characters' using errcode = '22023'; end if;
  if exists (select 1 from public.groups g where g.id = p_group and g.partner_at is not null) then raise exception 'This group is already a Drugbox partner group' using errcode = '22023'; end if;
  insert into public.group_partner_requests (group_id, requested_by, note) values (p_group, auth.uid(), left(v, 1000))
  on conflict (group_id) do update set requested_by = excluded.requested_by, note = excluded.note, status = 'pending', decided_by = null,
                                     decision_note = null, created_at = now(), decided_at = null
    where public.group_partner_requests.status <> 'pending';
end $$;
revoke all on function public.group_partner_request(bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.group_partner_request(bigint, text) to authenticated, service_role;

create or replace function public.group_partner_queue() returns jsonb
language sql stable security definer set search_path = public as $$
  select case when not public.is_moderator() then null else coalesce((select jsonb_agg(to_jsonb(x) order by x.created_at) from (
    select r.group_id, r.note, r.created_at, g.name, g.emoji, g.type, g.member_count, (select p.name from public.profiles p where p.id = r.requested_by) as who
      from public.group_partner_requests r join public.groups g on g.id = r.group_id where r.status = 'pending' limit 200) x), '[]'::jsonb) end
$$;
revoke all on function public.group_partner_queue() from public, anon, authenticated, service_role;
grant execute on function public.group_partner_queue() to authenticated, service_role;

create or replace function public.group_partner_decide(p_group bigint, p_ok boolean, p_note text default null) returns text
language plpgsql security definer set search_path = public as $$
declare r public.group_partner_requests; gname text; v_note text := nullif(left(btrim(coalesce(p_note, '')), 500), '');
begin
  if not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  select * into r from public.group_partner_requests where group_id = p_group for update;
  if r.group_id is null then raise exception 'Request not found' using errcode = 'P0002'; end if;
  if r.status <> 'pending' then raise exception 'Already decided by % (%)', private.who(r.decided_by), r.status using errcode = 'DX409'; end if;
  update public.group_partner_requests set status = case when p_ok then 'approved' else 'rejected' end, decided_by = auth.uid(), decision_note = v_note, decided_at = now()
   where group_id = p_group;
  if p_ok then update public.groups set partner_at = now() where id = p_group; end if;
  select name into gname from public.groups where id = p_group;
  if r.requested_by is not null then
    insert into public.notifications (user_id, type, from_user, group_id, message, data)
    values (r.requested_by, 'group_partner_decided', null, p_group, null, jsonb_strip_nulls(jsonb_build_object('outcome', case when p_ok then 'approved' else 'rejected' end, 'group', gname, 'note', v_note)));
  end if;
  perform private.log_decision('partner', p_group::text, left(coalesce(gname, 'Group'), 300), case when p_ok then 'approved' else 'rejected' end, v_note, null);
  return case when p_ok then 'approved' else 'rejected' end;
end $$;
revoke all on function public.group_partner_decide(bigint, boolean, text) from public, anon, authenticated, service_role;
grant execute on function public.group_partner_decide(bigint, boolean, text) to authenticated, service_role;

notify pgrst, 'reload schema';
