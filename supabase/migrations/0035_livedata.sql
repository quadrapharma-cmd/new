-- ═════════════════════════════════════════════════════════════════════
-- 0035 — the last sample numbers and lists in the live app come from the database (phase 1b: S-19, J-05, B-06, J-SOCIAL-49)
--   1. ticker_feed()        the top ticker on every page: the admins' active ticker_items, then the newest real listings,
--                           requests and jobs — ONE call at sign-in (four short index range scans). Security invoker: only what
--                           the member can already read (blocked employers' jobs stay hidden, as on the Jobs page).
--   2. jobs_stats()         the Jobs page numbers ("N open positions", "N jobs posted this week", "N candidates available now",
--                           the seniority counts, "Open Positions N jobs", "Available Candidates N profiles") — ONE call, the
--                           same rows the page lists (security invoker, the same block rules as open_candidates()).
--   3. public_stats()       the sign-in page and Home "N professionals / N listings / N countries" — totals only, no row, no
--                           person. The sign-in page is shown before sign-in, so anon may call it: public.public_stats() is a
--                           security INVOKER wrapper around private.public_counts() (security definer, in the private schema
--                           PostgREST does not expose), so no definer function in public is callable by anon (schema sweep 5).
--                           Cheap at 100k members: the member count is an index-only scan, the country count a loose index
--                           scan on the new idx_profiles_country (one probe per country), the listing counts use the live indexes.
--   4. profile_counts(id)   a member's real connection count for the profile header (connections are readable by their two
--                           parties only, so another member's count needs a definer). Signed-in members only.
--   5. profiles.intents     My Intents (Marketplace): what a member has / needs per category, kept with the profile (the
--                           existing profile policies apply: everyone signed in reads, only the owner updates). A check keeps
--                           it to the known categories and choices. It used to live in the browser only (and preset for
--                           everyone with sample choices).
--   6. The eight sample ticker rows 0001 seeded ("Metformin HCl GMP $5.80/kg", "Fette 1200 Tablet Press $45K" …) are switched
--      off — they are not real offers. An admin's own rows are untouched.
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
create or replace function public.jobs_stats()
returns jsonb language sql stable security invoker set search_path = public as $$
  select case when auth.uid() is null then null else (
    select jsonb_build_object(
      'open',     count(*),
      'week',     count(*) filter (where j.created_at >= now() - interval '7 days'),
      'by_level', jsonb_build_object('exec', count(*) filter (where j.lvl = 'exec'), 'senior', count(*) filter (where j.lvl = 'senior'),
                                     'mid', count(*) filter (where j.lvl = 'mid'), 'junior', count(*) filter (where j.lvl = 'junior'),
                                     'entry', count(*) filter (where j.lvl = 'entry')),
      'candidates', (select count(*) from public.profiles p where p.open_to_work and p.id <> auth.uid()
                       and p.id <> all (coalesce((select private.blocked_parties()), '{}'::uuid[]))))
    from (select created_at, case when seniority in ('exec', 'executive') then 'exec' when seniority in ('entry', 'junior', 'senior') then seniority
                                  else 'mid' end lvl
            from public.jobs where active) j) end
$$;
revoke all on function public.jobs_stats() from public, anon, authenticated, service_role;
grant execute on function public.jobs_stats() to authenticated, service_role;

-- ── 3. public totals (sign-in page, Home) ─────────────────────────────
create index if not exists idx_profiles_country on public.profiles (country);
create or replace function private.public_counts()
returns jsonb language sql stable security definer set search_path = public as $$
  with recursive c(country) as (                          -- a loose index scan: one probe of idx_profiles_country per country
    (select country from public.profiles where country is not null order by country limit 1)
    union all
    select (select p.country from public.profiles p where p.country > c.country order by p.country limit 1) from c where c.country is not null)
  select jsonb_build_object(
    'members',   (select count(*) from public.profiles),
    'listings',  (select count(*) from public.products where type = 'supply' and active)
               + (select count(*) from public.enquiries where type = 'demand' and status = 'active'),
    'countries', (select count(country) from c))
$$;
revoke all on function private.public_counts() from public, anon, authenticated, service_role;
grant execute on function private.public_counts() to anon, authenticated, service_role;
create or replace function public.public_stats()
returns jsonb language sql stable security invoker set search_path = public as $$ select private.public_counts() $$;
revoke all on function public.public_stats() from public, anon, authenticated, service_role;
grant execute on function public.public_stats() to anon, authenticated, service_role;

-- ── 4. a member's connection count ───────────────────────────────────
create or replace function public.profile_counts(p_id uuid)
returns jsonb language sql stable security definer set search_path = public as $$
  select case when auth.uid() is null or p_id is null then null else jsonb_build_object(
    'connections', (select count(*) from public.connections where requester = p_id and status = 'accepted')
                 + (select count(*) from public.connections where addressee = p_id and status = 'accepted')) end
$$;
revoke all on function public.profile_counts(uuid) from public, anon, authenticated, service_role;
grant execute on function public.profile_counts(uuid) to authenticated, service_role;

-- ── 5. My Intents ────────────────────────────────────────────────────
alter table public.profiles add column if not exists intents jsonb not null default '{}'::jsonb;
do $$ begin
  alter table public.profiles add constraint profiles_intents_chk check (
    jsonb_typeof(intents) = 'object'
    and intents - array['api', 'cosmetic', 'supplement', 'packaging', 'cmo', 'equipment', 'license', 'service', 'job', 'training'] = '{}'::jsonb
    and not jsonb_path_exists(intents, '$.* ? (@ != "i-have" && @ != "i-need" && @ != "both" && @ != "na")'));
exception when duplicate_object then null; end $$;

-- ── 6. the sample ticker rows ────────────────────────────────────────
update public.ticker_items t set active = false
 where t.active and (t.label, t.text) in (values ('Supply', 'Metformin HCl GMP $5.80/kg'), ('Demand', 'Ciprofloxacin HCl 2MT/month'),
   ('License', 'EDA Cosmetic Registration For Sale'), ('CMO', 'WHO-GMP Tablets — Quadra Pharm'), ('Equipment', 'Fette 1200 Tablet Press $45K'),
   ('Job', 'Senior RA Specialist — Giza, Egypt'), ('Supply', 'Hyaluronic Acid 99% Cosmetic Grade'), ('Deal closed', 'Amoxicillin 500kg ✓'));

notify pgrst, 'reload schema';
