-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0020 — security core (code review 2026-10, items F-01 F-03 F-08 F-09 F-12 F-26 F-27 F-94 F-95 F-96
--                F-101 F-102 F-103 F-104 F-113 F-163 F-164 F-165 F-169 F-177)
-- The database is the trust boundary: nothing the browser sends can grant a role, a badge, a paid placement,
-- a ranking or a consent. Server-managed columns are set here; the approved interface and the adapter never
-- send them, so ordinary flows are unchanged (supabase/tests/security_core.rls.sql checks both sides).
-- Safe to run more than once.
-- ═════════════════════════════════════════════════════════════════════

-- ── 0. who is calling? ────────────────────────────────────────────────────────
-- Browser calls run as anon / authenticated. Server work (migrations and SQL, the service role, the auth hook)
-- runs as another role, and SECURITY DEFINER functions (activate_order, verification_requests_apply,
-- reply_to_reference, the counter triggers) run as their owner: the guards below leave all of those alone.
create or replace function public.is_server_call() returns boolean language sql stable as $$
  select current_user not in ('anon', 'authenticated')
$$;

-- ── 1. F-94 handle_new_user: pinned search_path, never a NULL or empty name ──
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, name)
  values (new.id, left(coalesce(nullif(trim(new.raw_user_meta_data->>'name'), ''), nullif(split_part(coalesce(new.email, ''), '@', 1), ''), 'Member'), 120));
  return new;
end;
$$;

-- ── 2. F-01 profiles: role, verified and account_type are set by Drugbox only ──
-- role / verified / account_type: hard error (the interface never edits them — only an attacker sends them).
-- followers_count / profile_views / created_at / id: kept silently (server-maintained).
-- The first admin is made with SQL or the service role (a server call), as the tests already do.
create or replace function public.profiles_guard() returns trigger language plpgsql as $$
begin
  if public.is_server_call() then return new; end if;
  if tg_op = 'INSERT' then                                  -- rows come from handle_new_user; defaults if ever reached
    new.role := 'user'; new.verified := false; new.account_type := 'professional';
    new.followers_count := 0; new.profile_views := 0; new.created_at := now();
    return new;
  end if;
  if (new.role is distinct from old.role or new.verified is distinct from old.verified or new.account_type is distinct from old.account_type)
     and not public.is_platform_admin() then
    raise exception 'Roles and verification are managed by Drugbox' using errcode = '42501';
  end if;
  new.id := old.id; new.followers_count := old.followers_count; new.profile_views := old.profile_views; new.created_at := old.created_at;
  return new;
end $$;
drop trigger if exists trg_profiles_guard on public.profiles;
create trigger trg_profiles_guard before insert or update on public.profiles for each row execute function public.profiles_guard();
alter policy "profiles: own update" on public.profiles using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

-- ── 3. F-03 F-09 F-95 F-164 server-managed columns ───────────────────────────
-- One guard per table, for browser callers only. id and created_at come from the server; counters start at 0
-- and never change by hand; paid placements (products.boosted_until/featured_until) are written only by
-- activate_order; pinned is a Drugbox action; a message is never inserted already read; a reference never
-- carries the candidate's reply; a notification only changes its read flag.
-- Kept silently (a whole-row save could echo them) — except a changed id or company slug on update: a hard
-- error, because only an attacker sends those.
-- A client-chosen id above the sequence (a 2099 message id freezes live polling, last_value+1 steals the next
-- sender's id) is replaced from the sequence; the default has already drawn the normal one.
create or replace function public.server_columns() returns trigger language plpgsql as $$
declare admin boolean; seq text;
begin
  if public.is_server_call() then return new; end if;
  admin := tg_table_name in ('posts', 'companies') and public.is_platform_admin();
  if tg_op = 'INSERT' then
    if tg_table_name <> 'enquiries' then
      seq := pg_get_serial_sequence(format('%I.%I', tg_table_schema, tg_table_name), 'id');
      if new.id is null or new.id > coalesce(pg_sequence_last_value(seq::regclass), 0) then new.id := nextval(seq); end if;
    end if;
    new.created_at := now();
    case tg_table_name
      when 'posts' then new.like_count := 0; new.comment_count := 0; new.view_count := 0; new.share_count := 0;
                        if not admin then new.pinned := false; end if;
      when 'messages' then new.read_at := null;
      when 'products' then new.boosted_until := null; new.featured_until := null;
      when 'enquiries' then new.id := 'E' || substr(md5(random()::text || clock_timestamp()::text), 1, 10);   -- never client-chosen (0009)
      when 'jobs' then new.applicant_count := 0;
      when 'groups' then new.member_count := 0;
      when 'companies' then new.follower_count := 0; new.source := 'company';
                            if not admin then new.registry := null; end if;                                      -- arrives with verification
      when 'work_references' then new.reply := null; new.replied_at := null;
      else null;
    end case;
    return new;
  end if;
  -- UPDATE
  if new.id is distinct from old.id then raise exception 'The id cannot change' using errcode = '42501'; end if;
  new.created_at := old.created_at;
  case tg_table_name
    when 'posts' then new.user_id := old.user_id; new.like_count := old.like_count; new.comment_count := old.comment_count;
                      new.view_count := old.view_count; new.share_count := old.share_count;
                      if not admin then new.pinned := old.pinned; end if;
                      if (select auth.uid()) is distinct from old.user_id then new.body := old.body; new.category := old.category; end if;   -- Drugbox only pins
    when 'products' then new.user_id := old.user_id; new.boosted_until := old.boosted_until; new.featured_until := old.featured_until;
    when 'enquiries' then new.user_id := old.user_id;
    when 'jobs' then new.user_id := old.user_id; new.applicant_count := old.applicant_count;
    when 'groups' then new.created_by := old.created_by; new.member_count := old.member_count;
    when 'companies' then new.follower_count := old.follower_count; new.source := old.source;
                          if not admin then new.registry := old.registry; end if;
                          if new.slug is distinct from old.slug and not admin then
                            raise exception 'The company address (slug) cannot change' using errcode = '42501';
                          end if;
    when 'work_references' then new.author := old.author; new.candidate := old.candidate; new.reply := old.reply; new.replied_at := old.replied_at;
    when 'notifications' then new.user_id := old.user_id; new.type := old.type; new.from_user := old.from_user;
                              new.post_id := old.post_id; new.message := old.message;
    else null;
  end case;
  return new;
end $$;
do $$ declare t text; begin
  foreach t in array array['posts', 'comments', 'messages', 'products', 'enquiries', 'jobs', 'groups', 'companies', 'work_references', 'notifications'] loop
    execute format('drop trigger if exists trg_%I_server_columns on public.%I', t, t);
    execute format('create trigger trg_%I_server_columns before insert or update on public.%I for each row execute function public.server_columns()', t, t);
  end loop;
end $$;
-- (rows the browser dated in the future, e.g. a post "from 2099" held at the top of the feed, are brought back to now)
update public.posts set created_at = now() where created_at is null or created_at > now() + interval '1 minute';
update public.comments set created_at = now() where created_at is null or created_at > now() + interval '1 minute';
update public.messages set created_at = now() where created_at is null or created_at > now() + interval '1 minute';
alter table public.posts    alter column created_at set not null, alter column created_at set default now();
alter table public.comments alter column created_at set not null, alter column created_at set default now();
alter table public.messages alter column created_at set not null, alter column created_at set default now();

-- F-96: a company starts pending, whoever creates it (the guard already forced it for members; admins and imports
-- too — an import of the public list says status 'unclaimed' explicitly)
alter table public.companies alter column status set default 'pending';
-- F-102: a comment or attachment always belongs to a post (orphans passed RLS and skipped the counter)
delete from public.comments where post_id is null;
delete from public.post_media where post_id is null;
alter table public.comments   alter column post_id set not null;
alter table public.post_media alter column post_id set not null;
-- F-163: full-text indexes nobody queries, in a configuration that cannot index Arabic — dropped (search uses
-- ILIKE on pg_trgm indexes, as the company directory does); idx_conn_status indexed a three-value column next to
-- the (party, status) indexes
drop index if exists public.idx_posts_fts;
drop index if exists public.idx_products_fts;
drop index if exists public.idx_conn_status;

-- ── 4. F-08 F-103 connections: a request is pending until the addressee answers; one row per pair ─
-- insert: pending only, as yourself (the interface always sends 'pending');
-- update: the addressee, only from pending, only to accepted/rejected; requester/addressee/dates never change.
alter policy "connections: request" on public.connections with check ((select auth.uid()) = requester and status = 'pending');
alter policy "connections: addressee responds" on public.connections
  using ((select auth.uid()) = addressee and status = 'pending')
  with check ((select auth.uid()) = addressee and status in ('accepted', 'rejected'));
-- both directions cannot coexist: a request that crosses a pending one from the other side accepts it instead
create or replace function public.connections_guard() returns trigger language plpgsql as $$
declare rev public.connections;
begin
  if public.is_server_call() then return new; end if;
  if tg_op = 'INSERT' then
    if new.id is null or new.id > coalesce(pg_sequence_last_value('public.connections_id_seq'::regclass), 0) then new.id := nextval('public.connections_id_seq'); end if;
    new.created_at := now(); new.status := 'pending';
    select * into rev from public.connections where requester = new.addressee and addressee = new.requester;
    if rev.id is not null then
      if rev.status = 'pending' then update public.connections set status = 'accepted' where id = rev.id;          -- they asked first: connect
      elsif rev.status = 'rejected' then delete from public.connections where id = rev.id; return new;            -- ask again after a refusal
      end if;
      return null;                                                                                                  -- already connected
    end if;
    return new;
  end if;
  if new.requester <> old.requester or new.addressee <> old.addressee or new.id <> old.id or new.created_at is distinct from old.created_at then
    raise exception 'Only the answer to a connection request can change' using errcode = '42501';
  end if;
  if old.status <> 'pending' or new.status not in ('accepted', 'rejected') then
    raise exception 'This request was already answered' using errcode = '42501';
  end if;
  return new;
end $$;
drop trigger if exists trg_connections_guard on public.connections;
create trigger trg_connections_guard before insert or update on public.connections for each row execute function public.connections_guard();
-- existing reverse duplicates: keep the accepted one, else the older one
delete from public.connections c using public.connections d
 where d.requester = c.addressee and d.addressee = c.requester
   and (case when c.status = 'accepted' and d.status <> 'accepted' then false when d.status = 'accepted' and c.status <> 'accepted' then true else c.id > d.id end);
create unique index if not exists connections_pair_uq on public.connections (least(requester, addressee), greatest(requester, addressee));

-- ── 5. F-101 counters that were never maintained ──────────────────────────────
-- profiles.followers_count is shown on every person card (adapter: followers): it is the number of accepted
-- connections (people follow each other by connecting; company follows have their own counter). +1/−1 here.
create or replace function public.profiles_followers_count() returns trigger language plpgsql security definer set search_path = public as $$
declare was boolean := tg_op <> 'INSERT' and old.status = 'accepted';
        now_on boolean := tg_op <> 'DELETE' and new.status = 'accepted';
begin
  if now_on and not was then
    update public.profiles set followers_count = followers_count + 1 where id in (new.requester, new.addressee);
  elsif was and not now_on then
    update public.profiles set followers_count = greatest(followers_count - 1, 0) where id in (old.requester, old.addressee);
  end if;
  return null;
end $$;
revoke all on function public.profiles_followers_count() from public, anon, authenticated;
drop trigger if exists trg_connections_followers_count on public.connections;
create trigger trg_connections_followers_count after insert or update of status or delete on public.connections for each row execute function public.profiles_followers_count();
update public.profiles p set followers_count = coalesce(n.k, 0)
  from public.profiles q left join (select x.id, count(*) as k from (select requester as id from public.connections where status = 'accepted'
                                     union all select addressee from public.connections where status = 'accepted') x group by x.id) n on n.id = q.id
 where q.id = p.id and p.followers_count is distinct from coalesce(n.k, 0);
-- enquiries.reply_count: there are no enquiry replies in the schema and nothing reads it — dropped
alter table public.enquiries drop column if exists reply_count;

-- ── 6. F-104 view / share / profile-view counters: signed-in only, once per person per day ──
-- (only today's rows matter for the once-a-day rule; older rows can be deleted at any time, e.g. by a daily job)
create table if not exists public.post_view_log (
  post_id bigint not null references public.posts(id) on delete cascade,
  viewer  uuid   not null references public.profiles(id) on delete cascade,
  kind    text   not null check (kind in ('view', 'share')),
  day     date   not null default current_date,
  primary key (post_id, viewer, kind, day)
);
create table if not exists public.profile_view_log (
  target uuid not null references public.profiles(id) on delete cascade,
  viewer uuid not null references public.profiles(id) on delete cascade,
  day    date not null default current_date,
  primary key (target, viewer, day)
);
-- the viewer's rows: read by the "your own" policies and removed with the account (on delete cascade)
create index if not exists idx_post_view_log_viewer    on public.post_view_log (viewer);
create index if not exists idx_profile_view_log_viewer on public.profile_view_log (viewer);
alter table public.post_view_log    enable row level security;
alter table public.profile_view_log enable row level security;
do $$ begin
  create policy "post views: your own" on public.post_view_log for select using (viewer = (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "profile views: your own" on public.profile_view_log for select using (viewer = (select auth.uid()));
exception when duplicate_object then null; end $$;
revoke insert, update, delete, truncate on public.post_view_log, public.profile_view_log from anon, authenticated;   -- the functions below write them

create or replace function public.increment_post_views(post_ids bigint[])
returns void language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid();
begin
  if me is null then return; end if;
  with seen as (
    insert into public.post_view_log (post_id, viewer, kind)
    select p.id, me, 'view' from public.posts p where p.id = any(post_ids)
    on conflict do nothing returning post_id)
  update public.posts p set view_count = view_count + 1 from seen where p.id = seen.post_id;
end $$;
create or replace function public.increment_post_share(p_id bigint)
returns int language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); n int;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  insert into public.post_view_log (post_id, viewer, kind) select p_id, me, 'share' where exists (select 1 from public.posts where id = p_id) on conflict do nothing;
  if found then update public.posts set share_count = share_count + 1 where id = p_id returning share_count into n;
  else select share_count into n from public.posts where id = p_id; end if;
  return n;
end $$;
create or replace function public.increment_profile_view(target uuid)
returns void language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid();
begin
  if me is null or target is null or target = me then return; end if;
  insert into public.profile_view_log (target, viewer) select target, me where exists (select 1 from public.profiles where id = target) on conflict do nothing;
  if found then update public.profiles set profile_views = profile_views + 1 where id = target; end if;
end $$;

-- ── 7. F-12 jobs_interacted: only the two parties may ask ─────────────────────
-- (stays executable by authenticated: the job_reviews policies evaluate it as the caller, always with the caller
--  as one of the two parties)
create or replace function public.jobs_interacted(a uuid, b uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select auth.uid() is not null and auth.uid() in (a, b) and (
         exists (select 1 from public.job_applications ja join public.jobs j on j.id = ja.job_id
                 where (ja.user_id = a and j.user_id = b) or (ja.user_id = b and j.user_id = a))
      or exists (select 1 from public.messages m
                 where (m.sender_id = a and m.receiver_id = b) or (m.sender_id = b and m.receiver_id = a)))
$$;

-- ── 8. F-165 get_ratings: aggregate the requested people only ─────────────────
-- (the Bayesian prior stays the role's overall mean — one plain aggregate, no group-by or rank over everyone;
--  with ids, the rank is among the requested people. Nothing in the app calls it yet.)
create or replace function public.get_ratings(p_role text, ids uuid[] default null)
returns table (party uuid, n int, avg numeric, c1 numeric, c2 numeric, c3 numeric, c4 numeric, bayes numeric, rank int)
language sql stable security definer set search_path = public as $$
  with g as (select coalesce(avg((c1 + c2 + c3 + c4) / 4.0), 4) as m from public.job_reviews where reviewee_role = p_role and not hidden),
  agg as (
    select reviewee as party, count(*)::int as n, avg((c1 + c2 + c3 + c4) / 4.0) as avg, avg(c1) c1, avg(c2) c2, avg(c3) c3, avg(c4) c4
    from public.job_reviews where reviewee_role = p_role and not hidden and (ids is null or reviewee = any(ids)) group by reviewee)
  select a.party, a.n, round(a.avg, 2), round(a.c1, 2), round(a.c2, 2), round(a.c3, 2), round(a.c4, 2),
         round((3 * g.m + a.avg * a.n) / (3 + a.n), 3) as bayes,
         (rank() over (order by (3 * g.m + a.avg * a.n) / (3 + a.n) desc))::int
  from agg a, g
$$;

-- ── 9. F-164 posts: the author edits body/category, Drugbox pins; notifications are read-only ─
do $$ begin
  create policy "posts: own edit" on public.posts for update using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "posts: admin pins" on public.posts for update using (public.is_platform_admin()) with check (public.is_platform_admin());
exception when duplicate_object then null; end $$;
-- notifications are written by triggers and functions; a person reads, marks read and deletes their own
drop policy if exists "notifications: own" on public.notifications;
do $$ begin
  create policy "notifications: own read" on public.notifications for select using ((select auth.uid()) = user_id);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "notifications: own mark read" on public.notifications for update using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "notifications: own delete" on public.notifications for delete using ((select auth.uid()) = user_id);
exception when duplicate_object then null; end $$;

-- ── 10. F-113 the five write policies that evaluated auth.uid() per row ───────
alter policy "messages: receiver marks read" on public.messages using (receiver_id = (select auth.uid())) with check (receiver_id = (select auth.uid()));
alter policy "members: owners/admins or the person update" on public.company_members
  using (public.is_company_member(company_id, array['owner','admin']) or user_id = (select auth.uid()));
alter policy "members: owners/admins remove, or leave" on public.company_members
  using (public.is_company_member(company_id, array['owner','admin']) or user_id = (select auth.uid()));
alter policy "documents: owners/admins/regulatory/quality add" on public.company_documents
  with check (public.is_company_member(company_id, array['owner','admin','regulatory','quality']) and created_by = (select auth.uid()));
alter policy "verification: owners/admins submit" on public.verification_requests
  with check (public.is_company_member(company_id, array['owner','admin']) and submitted_by = (select auth.uid()) and status = 'pending');

-- ── 11. F-26 F-169 nothing personal before sign-in ────────────────────────────
-- The live app reads nothing before a session exists (the login and sign-up pages need no data), so people,
-- companies and buying groups (with their members and events) are for members only. Public buckets are served
-- by URL (/object/public does not use these policies) — listing objects is for signed-in people only.
alter policy "profiles: everyone can read" on public.profiles to authenticated;
alter policy "companies: everyone can read" on public.companies to authenticated;
alter policy "deals: group orders are open to all" on public.deals to authenticated;
alter policy "videos: anyone can watch" on storage.objects to authenticated;
alter policy "post media: anyone can see" on storage.objects to authenticated;

-- ── 12. F-12 F-27 F-177 privileges: only what the app needs, nothing by default ─
-- functions: no anonymous execution (the app calls every RPC signed in) — except the helpers that row policies
-- evaluate as the calling role (is_platform_admin, is_company_member, …: anon reads must come back empty, not fail).
-- Computed from the policies, so a re-run after later migrations keeps their helpers. jobs_interacted is a policy
-- helper too, but only for writes anon cannot make; deal_receiver is internal to the deals engine; the extensions'
-- functions (pgcrypto, pg_trgm) are not RPCs at all (pg_trgm indexes keep working).
-- (PostgreSQL grants EXECUTE to PUBLIC on every new function and a per-schema default cannot take that back, so a
--  migration that adds a function revokes it from public, anon itself, as 0012 does; security_core.rls.sql fails
--  on any public function anon can run that no row policy needs)
do $$ declare f record; begin
  for f in select p.oid::regprocedure::text as sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
            where n.nspname = 'public' and has_function_privilege('anon', p.oid, 'execute')
              and not exists (select 1 from pg_policies q where coalesce(q.qual, '') || ' ' || coalesce(q.with_check, '') ~ ('\m' || p.proname || '\('))
  loop
    execute format('revoke execute on function %s from public, anon', f.sig);
  end loop;
  for f in select p.oid::regprocedure::text as sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
            join pg_depend d on d.objid = p.oid and d.classid = 'pg_proc'::regclass and d.deptype = 'e' where n.nspname = 'public'
  loop
    execute format('revoke execute on function %s from public, anon, authenticated', f.sig);
  end loop;
end $$;
alter default privileges in schema public revoke execute on functions from anon;
revoke execute on function public.jobs_interacted(uuid, uuid) from public, anon;
revoke execute on function public.deal_receiver(bigint, text) from public, anon, authenticated;
grant execute on function public.is_server_call() to authenticated;                 -- the guards run as the caller
-- tables: the anon key never writes, and nothing is granted beyond what a policy allows
revoke insert, update, delete, truncate on all tables in schema public from anon;
revoke all on all sequences in schema public from anon;
alter default privileges in schema public revoke insert, update, delete, truncate on tables from anon;
alter default privileges in schema public revoke all on sequences from anon;
revoke insert, update, delete on public.payment_orders from authenticated;      -- create_order / confirm_payment / submit_instapay only
revoke insert, delete on public.payment_products from authenticated;            -- prices are seeded; Drugbox edits them
revoke insert, delete on public.profiles from authenticated;                     -- created by handle_new_user, removed with the account
revoke delete on public.messages from authenticated;                             -- a conversation is never rewritten
revoke insert on public.notifications from authenticated;                        -- written by triggers and functions
revoke update on public.comments, public.post_media, public.company_followers, public.course_enrollments, public.work_references from authenticated;   -- no edit policy (functions write)
revoke delete on public.verification_requests, public.company_reports from authenticated;                                      -- no delete policy
revoke truncate on all tables in schema public from authenticated;               -- TRUNCATE skips row-level security
alter default privileges in schema public revoke truncate on tables from authenticated;

-- refresh the API's schema cache so new tables, functions and relationships are usable at once
notify pgrst, 'reload schema';
