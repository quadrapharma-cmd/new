-- ═════════════════════════════════════════════════════════════════════
-- 0035 — the last sample numbers and lists in the live app come from the database (phase 1b: S-19, J-05, B-06, J-SOCIAL-49)
--   1. ticker_feed()        the top ticker on every page: the admins' active ticker_items, then the newest real listings,
--                           requests and jobs — ONE call at sign-in (four short index range scans). Security invoker: only what
--                           the member can already read (blocked employers' jobs stay hidden, as on the Jobs page).
--   2. jobs_stats()         the Jobs page numbers ("N open positions", "N jobs posted this week", "N candidates available now",
--                           the seniority counts, "Open Positions N jobs", "Available Candidates N profiles") — ONE call, the
--                           same rows the page lists (security invoker, the same block rules as open_candidates()).
--   3. profile_counts(id)   a member's real connection count for the profile header (connections are readable by their two
--                           parties only, so another member's count needs a definer). Signed-in members only.
--   4. profiles.intents     My Intents (Marketplace): what a member has / needs per category, kept with the profile (the
--                           existing profile policies apply: everyone signed in reads, only the owner updates). A check keeps
--                           it to the known categories and choices. It used to live in the browser only (and preset for
--                           everyone with sample choices).
--   5. The eight sample ticker rows 0001 seeded ("Metformin HCl GMP $5.80/kg", "Fette 1200 Tablet Press $45K" …) are switched
--      off — they are not real offers. An admin's own rows are untouched.
--   Also: two partial indexes (open-to-work members, members with a photo for Home) and my_network_stats() reading auth.uid()
--   once (it scanned every post: ~0.5 s at 300k posts). Not here: the sign-in page's totals ("12K+ professionals", "1,200+
--   listings", "18 countries") are left out in the live app rather than counted — the page is shown before sign-in, and the anon
--   key runs no function (F-27) and reads no member data (F-26).
-- Every new function has its own GRANT/REVOKE (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. ticker ────────────────────────────────────────────────────────
create or replace function public.ticker_feed()
returns jsonb language sql stable security invoker set search_path = public as $$
  select case when auth.uid() is null then '[]'::jsonb else coalesce((
    select jsonb_agg(jsonb_build_object('label', label, 'text', text) order by k, at desc) from (
      (select 0 k, now() at, t.label, t.text from public.ticker_items t where t.active order by t.sort_order, t.id limit 8)
      union all
      (select 1, p.created_at, case p.category when 'cmo' then 'CMO' when 'equipment' then 'Equipment' when 'registration' then 'License'
                                               when 'service' then 'Service' else 'Supply' end,
              left(p.name, 120) || coalesce(' ' || nullif(btrim(p.price), '') || coalesce('/' || nullif(btrim(p.unit), ''), ''), '')
         from public.products p where p.type = 'supply' and p.active order by p.created_at desc limit 6)
      union all
      (select 1, e.created_at, 'Demand', left(e.title, 120) from public.enquiries e where e.type = 'demand' and e.status = 'active' order by e.created_at desc limit 4)
      union all
      (select 1, j.created_at, 'Job', left(j.title, 120) || coalesce(' — ' || nullif(btrim(coalesce(nullif(btrim(j.company), ''), j.location)), ''), '')
         from public.jobs j where j.active order by j.created_at desc limit 4)
    ) x), '[]'::jsonb) end
$$;
revoke all on function public.ticker_feed() from public, anon, authenticated, service_role;
grant execute on function public.ticker_feed() to authenticated, service_role;

-- ── 2. jobs page numbers ─────────────────────────────────────────────
-- One pass over the active jobs grouped by level (the same level the job card shows: unknown → mid, "executive" → exec), and an
-- index-only count of the open-to-work members (the partial index below). auth.uid() and the block list are read once (a CTE),
-- never per row. 15–30 ms at 100k members / 20k jobs (tools/scale/timings.py; it was 40–90 ms written plainly).
create index if not exists idx_profiles_open_to_work_id on public.profiles (id) where open_to_work;
create or replace function public.jobs_stats()
returns jsonb language sql stable security invoker set search_path = public as $$
  with me as materialized (select auth.uid() uid, coalesce((select private.blocked_parties()), '{}'::uuid[]) blocked),
  j as (select case when seniority in ('exec', 'executive') then 'exec' when seniority in ('entry', 'junior', 'senior') then seniority else 'mid' end lvl,
               count(*) n, count(*) filter (where created_at >= now() - interval '7 days') w
          from public.jobs where active group by 1)
  select case when (select uid from me) is null then null else jsonb_build_object(
    'open',     coalesce((select sum(n) from j), 0),
    'week',     coalesce((select sum(w) from j), 0),
    'by_level', jsonb_build_object('exec', coalesce((select n from j where lvl = 'exec'), 0), 'senior', coalesce((select n from j where lvl = 'senior'), 0),
                                   'mid', coalesce((select n from j where lvl = 'mid'), 0), 'junior', coalesce((select n from j where lvl = 'junior'), 0),
                                   'entry', coalesce((select n from j where lvl = 'entry'), 0)),
    'candidates', (select count(*) from public.profiles p, me where p.open_to_work and p.id <> me.uid and p.id <> all (me.blocked))) end
$$;
revoke all on function public.jobs_stats() from public, anon, authenticated, service_role;
grant execute on function public.jobs_stats() to authenticated, service_role;

-- Home's member photos (the newest members who added one): a partial index, so the six are read directly
create index if not exists idx_profiles_avatar_created on public.profiles (created_at desc) where avatar_url is not null;

-- My Network's numbers (0003): auth.uid() was evaluated per row, so "impressions" scanned every post (~0.5 s at 300k posts, on
-- every visit to My Network); read once, each part is an index lookup. Same name, arguments, result and rights.
create or replace function public.my_network_stats() returns json language sql stable security invoker set search_path = public as $$
  select json_build_object(
    'connections',   (select count(*) from public.connections where requester = (select auth.uid()) and status = 'accepted')
                   + (select count(*) from public.connections where addressee = (select auth.uid()) and status = 'accepted'),
    'profile_views', (select coalesce(profile_views, 0) from public.profiles where id = (select auth.uid())),
    'impressions',   (select coalesce(sum(view_count), 0) from public.posts where user_id = (select auth.uid())))
$$;
revoke all on function public.my_network_stats() from public, anon, authenticated, service_role;
grant execute on function public.my_network_stats() to authenticated, service_role;

-- ── 3. a member's connection count ───────────────────────────────────
create or replace function public.profile_counts(p_id uuid)
returns jsonb language sql stable security definer set search_path = public as $$
  select case when auth.uid() is null or p_id is null then null else jsonb_build_object(
    'connections', (select count(*) from public.connections where requester = p_id and status = 'accepted')
                 + (select count(*) from public.connections where addressee = p_id and status = 'accepted')) end
$$;
revoke all on function public.profile_counts(uuid) from public, anon, authenticated, service_role;
grant execute on function public.profile_counts(uuid) to authenticated, service_role;

-- ── 4. My Intents ────────────────────────────────────────────────────
alter table public.profiles add column if not exists intents jsonb not null default '{}'::jsonb;
do $$ begin
  alter table public.profiles add constraint profiles_intents_chk check (
    jsonb_typeof(intents) = 'object'
    and intents - array['api', 'cosmetic', 'supplement', 'packaging', 'cmo', 'equipment', 'license', 'service', 'job', 'training'] = '{}'::jsonb
    and not jsonb_path_exists(intents, '$.* ? (@ != "i-have" && @ != "i-need" && @ != "both" && @ != "na")'));
exception when duplicate_object then null; end $$;

-- ── 5. the sample ticker rows ────────────────────────────────────────
update public.ticker_items t set active = false
 where t.active and (t.label, t.text) in (values ('Supply', 'Metformin HCl GMP $5.80/kg'), ('Demand', 'Ciprofloxacin HCl 2MT/month'),
   ('License', 'EDA Cosmetic Registration For Sale'), ('CMO', 'WHO-GMP Tablets — Quadra Pharm'), ('Equipment', 'Fette 1200 Tablet Press $45K'),
   ('Job', 'Senior RA Specialist — Giza, Egypt'), ('Supply', 'Hyaluronic Acid 99% Cosmetic Grade'), ('Deal closed', 'Amoxicillin 500kg ✓'));

notify pgrst, 'reload schema';
