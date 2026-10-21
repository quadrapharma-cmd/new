-- ═════════════════════════════════════════════════════════════════════
-- 0043 — search (area social: S-18 one search for people, companies, listings, jobs, groups and posts; J-SOCIAL-47 saved searches
--        with alerts; S-09 the people who blocked me, or whom I blocked, and deleted members are never suggested or found)
--   1. trigram indexes        every searched text has a pg_trgm index, so "%eva%" reads the index, not the table (100k scale)
--   2. search_all(q, n)       one call, as the member (row-level security decides what is readable): up to n of each kind
--   3. saved_searches         a member's saved Marketplace / Jobs searches (query + filters + alert); a new listing or job that
--                             matches an alerting search tells its owner ('saved_search')
--   4. suggest_people         as 0030, without deleted members and people blocked either way
-- Every table and function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. indexes ───────────────────────────────────────────────────────────────────────────────────────────
create index if not exists idx_profiles_name_trgm on public.profiles using gin (name gin_trgm_ops);
create index if not exists idx_profiles_company_trgm on public.profiles using gin (company gin_trgm_ops);
create index if not exists idx_profiles_headline_trgm on public.profiles using gin (headline gin_trgm_ops);
create index if not exists idx_products_name_trgm on public.products using gin (name gin_trgm_ops) where active;
create index if not exists idx_jobs_title_trgm on public.jobs using gin (title gin_trgm_ops) where active;
create index if not exists idx_jobs_company_trgm on public.jobs using gin (company gin_trgm_ops) where active;
create index if not exists idx_groups_name_trgm on public.groups using gin (name gin_trgm_ops);
create index if not exists idx_posts_body_trgm on public.posts using gin (body gin_trgm_ops) where group_id is null;

-- ── 2. search_all ────────────────────────────────────────────────────────────────────────────────────────
create or replace function private.blocks_with_me() returns uuid[]
language sql stable security definer set search_path = public as $$
  select coalesce(array_agg(distinct x.p), '{}') from (
    select b.blocked as p from public.user_blocks b where b.blocker = auth.uid()
    union all select b.blocker from public.user_blocks b where b.blocked = auth.uid()) x
$$;
revoke all on function private.blocks_with_me() from public, anon; grant execute on function private.blocks_with_me() to authenticated, service_role;

create or replace function public.search_all(p_q text, p_limit int default 6) returns jsonb
language plpgsql stable set search_path = public as $$
declare q text := regexp_replace(trim(coalesce(p_q, '')), '\s+', ' ', 'g'); pat text; pre text; n int := least(greatest(coalesce(p_limit, 6), 1), 20); bl uuid[];
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if length(q) < 2 or length(q) > 80 then return jsonb_build_object('q', q); end if;
  pre := replace(replace(replace(q, '\', '\\'), '%', '\%'), '_', '\_'); pat := '%' || pre || '%'; pre := pre || '%';
  bl := private.blocks_with_me();
  return jsonb_build_object('q', q,
    'people', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select p.id, p.name, p.headline, p.company, p.avatar_url, p.verified, p.location, p.country from public.profiles p
         where (p.name ilike pat or p.company ilike pat or p.headline ilike pat) and p.account_type is distinct from 'deleted' and p.id <> auth.uid() and p.id <> all (bl)
         order by (p.name ilike pre) desc, (p.name ilike pat) desc, length(p.name), p.created_at desc limit n) x),
    'companies', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select c.id, c.slug, c.name, c.city, c.country, c.verified, c.logo_emoji, c.type from public.companies c
         where (c.name ilike pat or c.name_ar ilike pat) order by (c.name ilike pre) desc, c.verified desc nulls last, length(c.name) limit n) x),
    'products', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select r.id, r.name, r.category, r.price, r.unit, r.emoji, r.user_id, (select s.name from public.profiles s where s.id = r.user_id) as seller from public.products r
         where r.active and r.name ilike pat and r.user_id <> all (bl) order by (r.name ilike pre) desc, r.created_at desc limit n) x),
    'jobs', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select j.id, j.title, j.company, j.location, j.type, j.user_id from public.jobs j
         where j.active and (j.title ilike pat or j.company ilike pat) and j.user_id <> all (bl) order by (j.title ilike pre) desc, j.created_at desc limit n) x),
    'groups', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select g.id, g.name, g.emoji, g.type, g.member_count from public.groups g
         where g.name ilike pat order by (g.name ilike pre) desc, g.member_count desc limit n) x),
    'posts', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select o.id, left(o.body, 240) as body, o.user_id, o.created_at, (select a.name from public.profiles a where a.id = o.user_id) as author from public.posts o
         where o.group_id is null and o.body ilike pat and o.user_id <> all (bl) order by o.created_at desc limit n) x));
end $$;
revoke all on function public.search_all(text, int) from public, anon, authenticated, service_role;
grant execute on function public.search_all(text, int) to authenticated, service_role;

-- ── 3. saved searches ────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.saved_searches (
  id         bigint generated always as identity primary key,
  user_id    uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  kind       text not null default 'market',
  name       text not null,
  q          text not null default '',
  filters    jsonb not null default '{}'::jsonb,
  alert      text not null default 'daily',
  created_at timestamptz not null default now(),
  seen_at    timestamptz not null default now(),
  constraint saved_searches_kind_chk check (kind in ('market', 'jobs')),
  constraint saved_searches_alert_chk check (alert in ('instant', 'daily', 'weekly', 'off')),
  constraint saved_searches_len check (length(name) between 1 and 120 and length(q) <= 80 and jsonb_typeof(filters) = 'object' and pg_column_size(filters) <= 4096)
);
create index if not exists idx_saved_searches_user on public.saved_searches (user_id, created_at desc);
create index if not exists idx_saved_searches_alert on public.saved_searches (kind) where alert <> 'off' and q <> '';
alter table public.saved_searches enable row level security;
do $$ begin
  create policy "saved searches: own read" on public.saved_searches for select using (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "saved searches: own add" on public.saved_searches for insert with check (user_id = (select auth.uid()) and (select count(*) from public.saved_searches s where s.user_id = (select auth.uid())) < 20);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "saved searches: own change" on public.saved_searches for update using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "saved searches: own remove" on public.saved_searches for delete using (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
revoke all on table public.saved_searches from public, anon, authenticated, service_role;
grant select on table public.saved_searches to anon;
grant select, delete on table public.saved_searches to authenticated;
grant insert (user_id, kind, name, q, filters, alert) on table public.saved_searches to authenticated;
grant update (name, alert, seen_at) on table public.saved_searches to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.saved_searches to service_role;

-- a new listing or job: the owners of matching alerting searches are told (one notice per search and item, at most 200)
create or replace function public.saved_search_matches() returns trigger
language plpgsql security definer set search_path = public as $$
declare k text := case when tg_table_name = 'jobs' then 'jobs' else 'market' end; t text; title text; s record; n int := 0; r jsonb := to_jsonb(new);
begin
  if not coalesce((r->>'active')::boolean, true) then return null; end if;
  title := coalesce(case when k = 'jobs' then r->>'title' else r->>'name' end, '');           /* read as JSON: one function for two tables */
  t := lower(title || ' ' || coalesce(case when k = 'jobs' then r->>'company' end, ''));
  for s in select ss.id, ss.user_id, ss.name from public.saved_searches ss
            where ss.kind = k and ss.alert <> 'off' and ss.q <> '' and ss.user_id <> (r->>'user_id')::uuid and position(lower(ss.q) in t) > 0
              and not exists (select 1 from public.user_blocks b where (b.blocker = ss.user_id and b.blocked = (r->>'user_id')::uuid) or (b.blocker = (r->>'user_id')::uuid and b.blocked = ss.user_id))
            limit 200 loop
    insert into public.notifications (user_id, type, from_user, job_id, message, data)
    values (s.user_id, 'saved_search', (r->>'user_id')::uuid, case when k = 'jobs' then (r->>'id')::bigint end,
            'New match for your saved search “' || left(s.name, 80) || '”: ' || left(title, 120),
            jsonb_build_object('kind', k, 'id', (r->>'id')::bigint, 'search', s.id));
    n := n + 1;
  end loop;
  return null;
end $$;
revoke all on function public.saved_search_matches() from public, anon, authenticated, service_role;
grant execute on function public.saved_search_matches() to service_role;
drop trigger if exists trg_products_saved_search on public.products;
create trigger trg_products_saved_search after insert on public.products for each row execute function public.saved_search_matches();
drop trigger if exists trg_jobs_saved_search on public.jobs;
create trigger trg_jobs_saved_search after insert on public.jobs for each row execute function public.saved_search_matches();

-- ── 4. suggestions: never a deleted member, never someone blocked either way ─────────────────────────────
create or replace function public.suggest_people(p_limit int default 12)
returns table (id uuid, name text, headline text, company text, country text, verified boolean, avatar_url text, location text,
               followers_count int, open_to_work boolean, hiring boolean, mutual int)
language sql stable security definer set search_path = public as $$
  with me as (select auth.uid() as uid),
  lim as (select least(greatest(coalesce(p_limit, 12), 1), 50) as n),
  mine as (select nullif(lower(btrim(p.company)), '') as co from public.profiles p, me where p.id = me.uid),
  friends as materialized (select case when c.requester = me.uid then c.addressee else c.requester end as fid
              from public.connections c, me where c.status = 'accepted' and (c.requester = me.uid or c.addressee = me.uid)
              order by c.created_at desc nulls last limit 300),
  known as materialized (select case when c.requester = me.uid then c.addressee else c.requester end as pid
            from public.connections c, me where c.requester = me.uid or c.addressee = me.uid
            union all select d.person_id from public.people_dismissed d, me where d.user_id = me.uid
            union all select b.blocked from public.user_blocks b, me where b.blocker = me.uid
            union all select b.blocker from public.user_blocks b, me where b.blocked = me.uid),
  second as (select x.pid, count(*)::int as mutual
             from friends f cross join lateral (
               (select c.addressee as pid from public.connections c where c.requester = f.fid and c.status = 'accepted' limit 200)
               union all
               (select c.requester from public.connections c where c.addressee = f.fid and c.status = 'accepted' limit 200)) x
             group by x.pid),
  ranked as (select s.pid, s.mutual from second s, me where s.pid <> me.uid and s.pid not in (select pid from known)
             order by s.mutual desc limit (select n from lim)),
  colleagues as (select p.id as pid, 0 as mutual from public.profiles p, me, mine
                  where mine.co is not null and lower(btrim(p.company)) = mine.co and p.id <> me.uid and p.id not in (select pid from known)
                    and p.account_type is distinct from 'deleted'
                  order by p.created_at desc limit (select n from lim)),
  fill as (select p.id as pid, 0 as mutual from public.profiles p, me where p.id <> me.uid
             and p.id not in (select pid from known) and p.id not in (select pid from ranked) and p.account_type is distinct from 'deleted'
           order by p.created_at desc limit (select n from lim)),
  picked as materialized (select u.pid, max(u.mutual) as mutual from (select * from ranked union all select * from colleagues union all select * from fill) u group by u.pid)
  select p.id, p.name, p.headline, p.company, p.country::text, p.verified, p.avatar_url, p.location, p.followers_count, p.open_to_work, p.hiring, x.mutual
  from picked x join public.profiles p on p.id = x.pid
  where auth.uid() is not null and p.id = any(array(select pid from picked)) and p.account_type is distinct from 'deleted'
  order by x.mutual desc, (lower(btrim(p.company)) is not distinct from (select co from mine) and (select co from mine) is not null) desc, p.created_at desc
  limit (select n from lim)
$$;
revoke all on function public.suggest_people(p_limit integer) from public, anon, authenticated, service_role;
grant execute on function public.suggest_people(p_limit integer) to authenticated, service_role;

notify pgrst, 'reload schema';
