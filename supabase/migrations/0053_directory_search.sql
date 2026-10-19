-- ═════════════════════════════════════════════════════════════════════
-- 0053 — the directory search finds a misspelt company name (J-BUSINESS-01) and the page's dates and cover come with its row
--   directory_companies_page (0026) with one more way to match a search: a word of the English or Arabic name close to the
--   query (pg_trgm word similarity ≥ 0.6, "medsinya" → "Medsinia Industries"; queries of 4–40 characters, served by the trigram
--   indexes on name / name_ar), and two more columns in each row: updated_at (the page's freshness, B-22 — no extra request
--   per page) and cover_url (0050's cover). Same arguments, same order, same limits.
-- Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════
-- pg_trgm's functions are not callable by the API roles (0026): the fuzzy match runs as its owner, in the private schema (not an RPC)
create or replace function private.directory_fuzzy(p_q text) returns setof bigint language sql stable security definer set search_path = public as $$
  select c.id from public.companies c where length(p_q) between 4 and 40 and (p_q <% c.name or p_q <% c.name_ar) limit 500   -- a misspelt name is short; a long query is not a name (its few trigrams would match every short name)
$$;
revoke all on function private.directory_fuzzy(text) from public, anon, authenticated, service_role;
grant execute on function private.directory_fuzzy(text) to authenticated, service_role;

create or replace function public.directory_companies_page(p_limit int default 100, p_offset int default 0, p_q text default null)
returns json language plpgsql stable security invoker set search_path = public set jit = off set plan_cache_mode = force_generic_plan as $$
declare
  v_q   text := nullif(left(trim(coalesce(p_q, '')), 100), '');
  v_lim int  := least(greatest(coalesce(p_limit, 100), 1), 200);
  v_off int  := greatest(coalesce(p_offset, 0), 0);
  v_ids bigint[];
begin
  -- the page's ids in the directory order: verified first, then (effective) VIP, then name, id. (A STABLE function: both
  -- statements see the snapshot of the call, as the single statement before did.)
  with hits as (   -- a search: the companies whose name / Arabic name or one of whose products matches (the same test as before)
    select c2.id from public.companies c2 where c2.name ilike '%' || v_q || '%' or c2.name_ar ilike '%' || v_q || '%'
    union   -- a misspelt name ("medsinya" → Medsinia): a word of the name close enough (pg_trgm word similarity, on the name indexes)
    select f.id from private.directory_fuzzy(v_q) f(id)
    union
    select p.company_id from public.company_products p
     where p.name ilike '%' || v_q || '%' or p.active_ingredient ilike '%' || v_q || '%' or p.active_ingredient_ar ilike '%' || v_q || '%')
  select case when exists (select 1 from public.companies e where e.plan = 'vip' and e.status <> 'suspended' and e.vip_until <= now())
    then array(select c.id from public.companies c   -- a VIP plan has run out: it sorts as free
               where c.status <> 'suspended' and (v_q is null or c.id in (select h.id from hits h))
               order by (c.status = 'verified') desc, (c.plan = 'vip' and (c.vip_until is null or c.vip_until > now())) desc, c.name, c.id
               limit v_lim offset v_off)
    else array(select c.id from public.companies c   -- none has: read in index order, stop after offset + limit
               where c.status <> 'suspended' and (v_q is null or c.id in (select h.id from hits h))
               order by (c.status = 'verified') desc, (c.plan = 'vip') desc, c.name, c.id
               limit v_lim offset v_off) end
  into v_ids;

  return (
    with mine as (select public.my_company_ids() as id),
    rated as (select * from public.company_ratings(v_ids))
    select coalesce(json_agg(x order by (x.status = 'verified') desc, (x.plan = 'vip') desc, x.name, x.id), '[]'::json) from (
      select c.id, c.slug, c.name, c.name_ar, c.status, c.registry, c.licensed, c.sectors, c.governorate, c.city, c.location, c.tagline, c.bio,
             c.founded, c.employees, c.website, c.phone, c.email, c.whatsapp, c.hours,
             case when c.plan = 'vip' and (c.vip_until is null or c.vip_until > now()) then 'vip' else 'free' end as plan,
             c.logo_url, c.cover_url, c.follower_count, c.profile, c.created_at, c.updated_at, c.intro_video,
             -- company_tier(c.id), the same rule: 0 not verified / no registry, 1 not licensed, 3 a checked valid GMP-type certificate, else 2
             case when c.status <> 'verified' or c.registry is null then 0 when not c.licensed then 1 when s.gmp then 3 else 2 end as tier,
             c.id in (select id from mine) as mine,
             coalesce(s.certs, '[]'::json) as certs,
             coalesce(dp.products, '[]'::json) as products,
             json_build_object('rating', r.rating, 'reviews', coalesce(r.reviews, 0)) as track
      from public.companies c
      left join rated r on r.company_id = c.id
      left join lateral (   -- the listed certificates (not expired) and company_tier's GMP-type test, in one pass
        select json_agg(distinct s.name) filter (where s.expiry is null or s.expiry >= current_date) as certs,
               bool_or(s.checked_at is not null and (s.expiry is null or s.expiry >= current_date)
                       and s.name ~* '(GMP|ISO 17025|GDP|ISO 15378|ISO 22716)') as gmp
        from public.site_certificates s where s.company_id = c.id) s on true
      left join private.directory_products dp on dp.company_id = c.id
      where c.id = any(v_ids)) x);
end $$;

notify pgrst, 'reload schema';
