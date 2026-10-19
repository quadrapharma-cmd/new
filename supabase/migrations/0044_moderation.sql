-- ═════════════════════════════════════════════════════════════════════
-- 0044 — moderation of members (area social: S-09 report a person or a comment, the reported-members queue, J-SOCIAL-51 suspend)
--   1. member_reports        a member reports a person (or one of their comments — the comment is copied into the report by the
--                            database) with a reason; once per reporter, person and comment while open; reporters read only their own
--   2. account_suspensions   Drugbox suspends an account with a reason; the database then refuses that member's posts, comments,
--                            messages, reactions, requests, follows, listings and jobs ("Your account is suspended")
--   3. moderation_log        every decision of the Drugbox team: who, when, what, why
--   4. reported_members()    the queue: every open report about a member (posts, messages, the member, comments) grouped per account
--      member_decide()       suspend (and remove their posts) or dismiss; every reporter is told the outcome; logged
--      lift_suspension()     the suspension ends; logged
--      my_account_status()   the signed-in member learns they are suspended (the app shows it and signs out)
-- Every table and function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. member reports ────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.member_reports (
  id          bigint generated always as identity primary key,
  reporter    uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  reported    uuid not null references public.profiles(id) on delete cascade,
  comment_id  bigint references public.comments(id) on delete set null,
  reason      text not null,
  note        text,
  excerpt     text,
  status      text not null default 'open',
  created_at  timestamptz not null default now(),
  decided_by  uuid references public.profiles(id) on delete set null,
  decided_at  timestamptz,
  constraint member_reports_reason_chk check (reason in ('spam', 'fake', 'scam', 'abusive', 'other')),
  constraint member_reports_status_chk check (status in ('open', 'actioned', 'dismissed')),
  constraint member_reports_note_len check (length(note) <= 500 and length(excerpt) <= 2000),
  constraint member_reports_not_self check (reporter <> reported)
);
create unique index if not exists idx_member_reports_once on public.member_reports (reporter, reported, coalesce(comment_id, 0)) where status = 'open';
create index if not exists idx_member_reports_reported on public.member_reports (reported) where status = 'open';
create index if not exists idx_member_reports_comment on public.member_reports (comment_id) where comment_id is not null;
create index if not exists idx_member_reports_decided_by on public.member_reports (decided_by) where decided_by is not null;
alter table public.member_reports enable row level security;
do $$ begin
  create policy "member reports: own or Drugbox read" on public.member_reports for select using (reporter = (select auth.uid()) or (select public.is_moderator()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "member reports: own add" on public.member_reports for insert with check (reporter = (select auth.uid()) and reported <> (select auth.uid()));
exception when duplicate_object then null; end $$;
revoke all on table public.member_reports from public, anon, authenticated, service_role;
grant select on table public.member_reports to anon;
grant select on table public.member_reports to authenticated;
grant insert (reporter, reported, comment_id, reason, note) on table public.member_reports to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.member_reports to service_role;
-- the reported comment is copied (the reporter cannot make it up) and must be the reported person's
create or replace function public.member_reports_fill() returns trigger
language plpgsql security definer set search_path = public as $$
declare c record;
begin
  new.status := 'open'; new.created_at := now(); new.decided_by := null; new.decided_at := null; new.excerpt := null;
  if new.comment_id is not null then
    select k.user_id, k.body into c from public.comments k where k.id = new.comment_id;
    if not found or c.user_id <> new.reported then raise exception 'This comment is not theirs' using errcode = '22023'; end if;
    new.excerpt := left(c.body, 2000);
  end if;
  return new;
end $$;
revoke all on function public.member_reports_fill() from public, anon, authenticated, service_role;
grant execute on function public.member_reports_fill() to service_role;
drop trigger if exists trg_member_reports_fill on public.member_reports;
create trigger trg_member_reports_fill before insert on public.member_reports for each row execute function public.member_reports_fill();

-- ── 2. suspensions ───────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.account_suspensions (
  user_id      uuid primary key references public.profiles(id) on delete cascade,
  reason       text not null,
  suspended_by uuid references public.profiles(id) on delete set null,
  suspended_at timestamptz not null default now(),
  constraint account_suspensions_reason_len check (length(reason) between 1 and 500)
);
create index if not exists idx_account_suspensions_by on public.account_suspensions (suspended_by) where suspended_by is not null;
alter table public.account_suspensions enable row level security;
do $$ begin
  create policy "suspensions: own or Drugbox read" on public.account_suspensions for select using (user_id = (select auth.uid()) or (select public.is_moderator()));
exception when duplicate_object then null; end $$;
revoke all on table public.account_suspensions from public, anon, authenticated, service_role;
grant select on table public.account_suspensions to anon, authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.account_suspensions to service_role;

create or replace function public.writer_not_suspended() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is not null and exists (select 1 from public.account_suspensions s where s.user_id = auth.uid()) then
    raise exception 'Your account is suspended' using errcode = '42501';
  end if;
  return new;
end $$;
revoke all on function public.writer_not_suspended() from public, anon, authenticated, service_role;
grant execute on function public.writer_not_suspended() to service_role;
do $$ declare t text; begin
  foreach t in array array['posts', 'comments', 'messages', 'reactions', 'reposts', 'comment_reactions', 'connections', 'person_followers', 'products', 'jobs',
                           'enquiries', 'skill_endorsements', 'post_mentions', 'member_reports', 'post_reports', 'message_reports'] loop
    if to_regclass('public.' || t) is not null then
      execute format('drop trigger if exists trg_%s_not_suspended on public.%I', t, t);
      execute format('create trigger trg_%s_not_suspended before insert on public.%I for each row execute function public.writer_not_suspended()', t, t);
    end if;
  end loop;
end $$;

-- ── 3. the log ───────────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.moderation_log (
  id          bigint generated always as identity primary key,
  admin       uuid references public.profiles(id) on delete set null,
  action      text not null,
  target_user uuid references public.profiles(id) on delete set null,
  reason      text,
  detail      jsonb not null default '{}'::jsonb,
  at          timestamptz not null default now()
);
create index if not exists idx_moderation_log_target on public.moderation_log (target_user, at desc);
create index if not exists idx_moderation_log_admin on public.moderation_log (admin);
alter table public.moderation_log enable row level security;
do $$ begin
  create policy "moderation log: Drugbox read" on public.moderation_log for select using ((select public.is_moderator()));
exception when duplicate_object then null; end $$;
revoke all on table public.moderation_log from public, anon, authenticated, service_role;
grant select on table public.moderation_log to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.moderation_log to service_role;

-- ── 4. the queue and the decisions ───────────────────────────────────────────────────────────────────────
create or replace function public.reported_members(p_limit int default 50) returns jsonb
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  return coalesce((select jsonb_agg(x order by x->>'last_at' desc) from (
    select jsonb_build_object('id', u.uid, 'name', p.name, 'headline', p.headline, 'company', p.company,
             'suspended', exists (select 1 from public.account_suspensions s where s.user_id = u.uid),
             'reports', count(*), 'reporters', count(distinct u.reporter), 'reasons', jsonb_agg(distinct u.reason), 'last_at', max(u.at),
             'samples', (jsonb_agg(jsonb_build_object('kind', u.kind, 'text', u.txt, 'note', u.note) order by u.at desc) filter (where u.txt is not null or u.note is not null)),
             'posts', (select count(*) from public.posts o where o.user_id = u.uid)) as x
      from (select r.post_author as uid, r.reporter, r.reason, r.created_at as at, 'post' as kind, left(r.post_excerpt, 300) as txt, r.note
              from public.post_reports r where r.status = 'open' and r.post_author is not null
            union all select m.reported, m.reporter, m.reason, m.created_at, 'messages', left((select string_agg(e->>'body', ' · ') from jsonb_array_elements(coalesce(m.excerpt, '[]'::jsonb)) e), 300), m.details
              from public.message_reports m where m.status = 'open'
            union all select k.reported, k.reporter, k.reason, k.created_at, case when k.comment_id is null and k.excerpt is null then 'member' else 'comment' end, left(k.excerpt, 300), k.note
              from public.member_reports k where k.status = 'open') u
      join public.profiles p on p.id = u.uid
     group by u.uid, p.name, p.headline, p.company
     order by max(u.at) desc limit least(greatest(coalesce(p_limit, 50), 1), 200)) t), '[]'::jsonb);
end $$;
revoke all on function public.reported_members(int) from public, anon, authenticated, service_role;
grant execute on function public.reported_members(int) to authenticated;

create or replace function public.member_decide(p_user uuid, p_action text, p_reason text default null, p_remove_posts boolean default false) returns integer
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); why text := nullif(left(trim(coalesce(p_reason, '')), 500), ''); n int := 0; removed int := 0;
begin
  if me is null or not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  if p_action not in ('suspend', 'dismiss') then raise exception 'Choose suspend or dismiss' using errcode = '22023'; end if;
  if p_user = me then raise exception 'You cannot suspend yourself' using errcode = '22023'; end if;
  if p_action = 'suspend' then
    if why is null then raise exception 'Write the reason for the suspension' using errcode = '22023'; end if;
    insert into public.account_suspensions (user_id, reason, suspended_by) values (p_user, why, me)
      on conflict (user_id) do update set reason = excluded.reason, suspended_by = excluded.suspended_by, suspended_at = now();
    if p_remove_posts then delete from public.posts where user_id = p_user; get diagnostics removed = row_count; end if;
  end if;
  with a as (update public.member_reports set status = case when p_action = 'suspend' then 'actioned' else 'dismissed' end, decided_by = me, decided_at = now()
              where reported = p_user and status = 'open' returning reporter),
       b as (update public.message_reports set status = case when p_action = 'suspend' then 'actioned' else 'dismissed' end
              where reported = p_user and status = 'open' returning reporter),
       c as (update public.post_reports set status = case when p_action = 'suspend' then 'removed' else 'dismissed' end, decided_by = me, decided_at = now()
              where post_author = p_user and status = 'open' returning reporter),
       closed as (select reporter from a union all select reporter from b union all select reporter from c)
  insert into public.notifications (user_id, type, from_user, message, data)
    select distinct reporter, 'report_closed', null::uuid, null::text, jsonb_build_object('outcome', case when p_action = 'suspend' then 'member_actioned' else 'member_dismissed' end)
      from closed where reporter <> p_user;
  get diagnostics n = row_count;
  insert into public.moderation_log (admin, action, target_user, reason, detail)
    values (me, case when p_action = 'suspend' then 'suspend' else 'dismiss_reports' end, p_user, why, jsonb_build_object('posts_removed', removed, 'reporters_told', n));
  return n;
end $$;
revoke all on function public.member_decide(uuid, text, text, boolean) from public, anon, authenticated, service_role;
grant execute on function public.member_decide(uuid, text, text, boolean) to authenticated;

create or replace function public.lift_suspension(p_user uuid, p_reason text default null) returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null or not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  delete from public.account_suspensions where user_id = p_user;
  insert into public.moderation_log (admin, action, target_user, reason) values (auth.uid(), 'lift_suspension', p_user, nullif(left(trim(coalesce(p_reason, '')), 500), ''));
end $$;
revoke all on function public.lift_suspension(uuid, text) from public, anon, authenticated, service_role;
grant execute on function public.lift_suspension(uuid, text) to authenticated;

create or replace function public.my_account_status() returns jsonb
language sql stable security definer set search_path = public as $$
  select jsonb_build_object('suspended', s.user_id is not null, 'reason', s.reason, 'since', s.suspended_at)
    from (select auth.uid() as uid) me left join public.account_suspensions s on s.user_id = me.uid where me.uid is not null
$$;
revoke all on function public.my_account_status() from public, anon, authenticated, service_role;
grant execute on function public.my_account_status() to authenticated;

-- ── 5. a block covers more than messages (S-09): no request, follow, comment, reaction, repost or comment like between the two ──
create or replace function private.blocked_between(a uuid, b uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select a is not null and b is not null and exists (select 1 from public.user_blocks x where (x.blocker = a and x.blocked = b) or (x.blocker = b and x.blocked = a))
$$;
revoke all on function private.blocked_between(uuid, uuid) from public, anon; grant execute on function private.blocked_between(uuid, uuid) to authenticated, service_role;
create or replace function public.block_guard() returns trigger
language plpgsql security definer set search_path = public as $$
declare a uuid; b uuid; r jsonb := to_jsonb(new);
begin
  case tg_table_name
    when 'connections' then a := (r->>'requester')::uuid; b := (r->>'addressee')::uuid;
    when 'person_followers' then a := (r->>'user_id')::uuid; b := (r->>'person_id')::uuid;
    when 'comments', 'reactions', 'reposts' then a := (r->>'user_id')::uuid; select p.user_id into b from public.posts p where p.id = (r->>'post_id')::bigint;
    when 'comment_reactions' then a := (r->>'user_id')::uuid; select c.user_id into b from public.comments c where c.id = (r->>'comment_id')::bigint;
    else return new;
  end case;
  if a <> b and private.blocked_between(a, b) then raise exception 'You can''t interact with this person' using errcode = '42501'; end if;
  return new;
end $$;
revoke all on function public.block_guard() from public, anon, authenticated, service_role;
grant execute on function public.block_guard() to service_role;
do $$ declare t text; begin
  foreach t in array array['connections', 'person_followers', 'comments', 'reactions', 'reposts', 'comment_reactions'] loop
    execute format('drop trigger if exists trg_%s_block_guard on public.%I', t, t);
    execute format('create trigger trg_%s_block_guard before insert on public.%I for each row execute function public.block_guard()', t, t);
  end loop;
end $$;
-- the people I blocked and the people who blocked me — the app leaves them out of pickers and suggestions
create or replace function public.my_block_list() returns uuid[]
language sql stable security definer set search_path = public as $$ select private.blocks_with_me() $$;
revoke all on function public.my_block_list() from public, anon, authenticated, service_role;
grant execute on function public.my_block_list() to authenticated;

notify pgrst, 'reload schema';
