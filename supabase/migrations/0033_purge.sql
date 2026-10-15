-- ═════════════════════════════════════════════════════════════════════
-- 0033 — the marketplace's numbers come from the database (phase 1, B-06)
--   The approved marketplace shows "1.2K listings", "312 supply", "340 suppliers", "76 jobs", "54 providers" and a count per
--   category. Those were sample numbers in the live app as well — next to a paid product (Boost / Featured) that is a
--   misleading advertisement. market_stats() returns the real counts in ONE call (the page used to need none; ten separate
--   count requests would slow it down):
--     supply, demand            active supply listings (products) and open requests (enquiries, type demand)
--     by_cat, demand_by_cat     the same per category (api, finished, cmo, registration, equipment, service, other)
--     suppliers                 distinct members with an active supply listing
--     service_providers         distinct members with an active service listing
--     jobs                      active jobs
--   Only totals of what every signed-in member can already read (active listings, open requests, active jobs) — no row, no
--   person. security definer so the count is one index scan, not a row-by-row policy check; signed-in members only.
-- Every new function has its own GRANT/REVOKE (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

create or replace function public.market_stats()
returns jsonb language sql stable security definer set search_path = public as $$
  select case when auth.uid() is null then null else jsonb_build_object(
    'supply',            (select count(*) from public.products  where active and type = 'supply'),
    'demand',            (select count(*) from public.enquiries where status = 'active' and type = 'demand'),
    'by_cat',            (select coalesce(jsonb_object_agg(c, n), '{}'::jsonb) from (select coalesce(category, 'other') c, count(*) n from public.products where active and type = 'supply' group by 1) x),
    'demand_by_cat',     (select coalesce(jsonb_object_agg(c, n), '{}'::jsonb) from (select coalesce(category, 'other') c, count(*) n from public.enquiries where status = 'active' and type = 'demand' group by 1) x),
    'suppliers',         (select count(distinct user_id) from public.products where active and type = 'supply'),
    'service_providers', (select count(distinct user_id) from public.products where active and type = 'supply' and category = 'service'),
    'jobs',              (select count(*) from public.jobs where active)
  ) end
$$;
revoke all on function public.market_stats() from public, anon, authenticated, service_role;
grant execute on function public.market_stats() to authenticated, service_role;

notify pgrst, 'reload schema';
