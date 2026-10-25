-- ═════════════════════════════════════════════════════════════════════
-- 0103 — Company pages for signed-out visitors (AREA w-growth: the owner's decision 1; J-BUSINESS-02 / 04 / 10 visitor steps)
--   A company page is public: its name (EN/AR), about, sectors, city, logo and cover, products, sites with their capacity
--   calendar, certificates (as checked or not by Drugbox) and the verified badge. Contacting it needs sign-in, so a visitor
--   gets NO phone, e-mail, WhatsApp, registry number, team, documents, reviews' authors or anything private.
--   The signed-out app calls these functions (anon); they run as their owner but return only the public fields, built from the
--   same functions the signed-in directory uses (directory_companies_page, company_sites_public, company_certs_public), so the
--   two never drift apart. Suspended companies are never shown.
--   public_company_meta(slug) gives the title / description for the page's <title>, description and Open Graph tags.
-- Every function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- the contact and private fields a visitor never gets
create or replace function private.public_company_strip(c jsonb) returns jsonb language sql immutable as $$
  select (c - array['phone', 'email', 'whatsapp', 'registry', 'hours', 'owner_id', 'source_ref', 'vip_until', 'vip_reminded_at', 'mine', 'tax_verified'])
         || jsonb_build_object('mine', false)
$$;
revoke all on function private.public_company_strip(jsonb) from public, anon, authenticated, service_role;
grant execute on function private.public_company_strip(jsonb) to service_role;

-- a page of the directory (same order, search and card fields as directory_companies_page, minus contact details)
create or replace function public.public_directory_page(p_limit int default 100, p_offset int default 0, p_q text default null)
returns jsonb language sql stable security definer set search_path = public set jit = off as $$
  select coalesce(jsonb_agg(private.public_company_strip(x.c) order by x.n), '[]'::jsonb)
    from jsonb_array_elements(public.directory_companies_page(least(greatest(coalesce(p_limit, 100), 1), 100), greatest(coalesce(p_offset, 0), 0), p_q)::jsonb)
         with ordinality as x(c, n)
$$;
revoke all on function public.public_directory_page(int, int, text) from public, anon, authenticated, service_role;
grant execute on function public.public_directory_page(int, int, text) to anon, authenticated, service_role;

-- one company by its address (a shared link): the directory's row for it, with its products in full (public fields)
create or replace function public.public_company(p_slug text) returns jsonb
language sql stable security definer set search_path = public as $$
  select private.public_company_strip(to_jsonb(c) - array['bio_private'])
         || jsonb_build_object('plan', case when c.plan = 'vip' and (c.vip_until is null or c.vip_until > now()) then 'vip' else 'free' end,
                               'products', coalesce((select jsonb_agg(jsonb_build_object('id', p.id, 'company_id', p.company_id, 'name', p.name, 'active_ingredient', p.active_ingredient,
                                   'active_ingredient_ar', p.active_ingredient_ar, 'dosage_form', p.dosage_form, 'strength', p.strength, 'role', p.role, 'category', p.category,
                                   'pack', p.pack, 'description', p.description, 'moq', p.moq, 'price', p.price, 'currency', p.currency, 'image_path', p.image_path,
                                   'sort_order', p.sort_order, 'created_at', p.created_at, 'updated_at', p.updated_at,
                                   'ingredient', p.active_ingredient, 'ingredient_ar', p.active_ingredient_ar, 'form', p.dosage_form) order by p.sort_order, p.id)
                                 from public.company_products p where p.company_id = c.id), '[]'::jsonb))
    from public.companies c where c.slug = p_slug and c.status <> 'suspended'
$$;
revoke all on function public.public_company(text) from public, anon, authenticated, service_role;
grant execute on function public.public_company(text) to anon, authenticated, service_role;

create or replace function public.public_company_sites(p_slug text) returns json
language sql stable security definer set search_path = public as $$
  select public.company_sites_public(p_slug)
$$;
revoke all on function public.public_company_sites(text) from public, anon, authenticated, service_role;
grant execute on function public.public_company_sites(text) to anon, authenticated, service_role;

create or replace function public.public_company_certs(p_slug text) returns json
language sql stable security definer set search_path = public as $$
  select public.company_certs_public(p_slug)
$$;
revoke all on function public.public_company_certs(text) from public, anon, authenticated, service_role;
grant execute on function public.public_company_certs(text) to anon, authenticated, service_role;

-- the sites of a directory page in one call (the cards say "N sites" and filter by certificate)
create or replace function public.public_sites_for(p_ids bigint[]) returns jsonb
language sql stable security definer set search_path = public as $$
  select coalesce(jsonb_agg(jsonb_build_object('id', s.id, 'company_id', s.company_id, 'name', s.name, 'type', s.type, 'city', s.city, 'governorate', s.governorate,
           'dosage_forms', s.dosage_forms, 'min_batch', s.min_batch, 'capacity', s.capacity, 'free_slots', s.free_slots,
           'certs', (select coalesce(jsonb_agg(jsonb_build_object('name', t.name, 'expiry', t.expiry, 'source', t.source, 'checked_at', t.checked_at) order by t.name), '[]'::jsonb)
                     from public.site_certificates t where t.site_id = s.id and t.company_id = s.company_id)) order by s.id), '[]'::jsonb)
    from public.company_sites s join public.companies c on c.id = s.company_id
   where s.company_id = any(p_ids[1:200]) and c.status <> 'suspended'
$$;
revoke all on function public.public_sites_for(bigint[]) from public, anon, authenticated, service_role;
grant execute on function public.public_sites_for(bigint[]) to anon, authenticated, service_role;

-- for <title>, <meta name=description> and Open Graph
create or replace function public.public_company_meta(p_slug text) returns jsonb
language sql stable security definer set search_path = public as $$
  select jsonb_build_object('name', c.name, 'name_ar', c.name_ar, 'slug', c.slug, 'verified', c.status = 'verified', 'unclaimed', c.status = 'unclaimed',
                            'description', left(coalesce(nullif(c.tagline, ''), nullif(c.bio, ''), array_to_string(c.sectors, ' · ') || coalesce(' — ' || c.city, '')), 200),
                            'image', c.logo_url)
    from public.companies c where c.slug = p_slug and c.status <> 'suspended'
$$;
revoke all on function public.public_company_meta(text) from public, anon, authenticated, service_role;
grant execute on function public.public_company_meta(text) to anon, authenticated, service_role;

notify pgrst, 'reload schema';
