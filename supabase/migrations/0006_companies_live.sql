-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0006 — companies in the live app (step C1)
-- 1. Guard: a new company always starts "pending"; verification, licence and plan are set only by Drugbox.
-- 2. profile jsonb: page presentation fields (services, hours, address, colour, showcase) that are not queried.
-- 3. directory_companies(): the directory in one call — certificates in force, products for search, level.
-- 4. company_sites_public(slug): a company's sites with their certificates.
-- ═════════════════════════════════════════════════════════════════════
alter table public.companies add column if not exists profile jsonb not null default '{}'::jsonb;

-- unclaimed pages (the directory is pre-filled from public industry lists) have no owner until claimed;
-- only Drugbox creates them — the guard below makes any other creator the owner
alter table public.companies alter column owner_id drop not null;
do $$ begin
  alter table public.companies add constraint companies_owner_unless_unclaimed check (owner_id is not null or status = 'unclaimed');
exception when duplicate_object then null; end $$;

create or replace function public.companies_guard() returns trigger language plpgsql as $$
begin
  if public.is_platform_admin() then return new; end if;
  if tg_op = 'INSERT' then
    new.status := 'pending'; new.tax_verified := false; new.licensed := false; new.plan := 'free'; new.vip_until := null; new.verified := false;
    new.owner_id := auth.uid();
    return new;
  end if;
  if new.status is distinct from old.status or new.tax_verified is distinct from old.tax_verified or new.licensed is distinct from old.licensed
     or new.plan is distinct from old.plan or new.vip_until is distinct from old.vip_until or new.verified is distinct from old.verified
     or new.owner_id is distinct from old.owner_id or (old.status = 'verified' and new.registry is distinct from old.registry) then
    raise exception 'Verification, licence, plan and ownership are managed by Drugbox' using errcode = '42501';
  end if;
  return new;
end $$;
drop trigger if exists trg_companies_guard on public.companies;
create trigger trg_companies_guard before insert or update on public.companies for each row
  when (auth.uid() is not null) execute function public.companies_guard();

-- the team (owner/admin) edits the page; the table's own policy only knew the owner
do $$ begin
  create policy "companies: team admins edit" on public.companies for update
    using (public.is_company_member(id, array['owner','admin'])) with check (public.is_company_member(id, array['owner','admin']));
exception when duplicate_object then null; end $$;

create or replace function public.directory_companies(p_limit int default 5000)
returns json language sql stable security invoker set search_path = public as $$
  select coalesce(json_agg(x order by x.name), '[]'::json) from (
    select c.id, c.slug, c.name, c.name_ar, c.status, c.registry, c.licensed, c.sectors, c.governorate, c.city, c.location, c.tagline, c.bio,
           c.founded, c.employees, c.website, c.phone, c.email, c.whatsapp, c.hours, c.plan, c.logo_url, c.follower_count, c.profile, c.created_at,
           public.company_tier(c.id) as tier,
           public.is_company_member(c.id) as mine,
           (select coalesce(json_agg(distinct s.name), '[]'::json) from public.site_certificates s where s.company_id = c.id and (s.expiry is null or s.expiry >= current_date)) as certs,
           (select coalesce(json_agg(json_build_object('name', p.name, 'ingredient', p.active_ingredient, 'ingredient_ar', p.active_ingredient_ar,
                                                       'form', p.dosage_form, 'strength', p.strength, 'role', p.role) order by p.name), '[]'::json)
              from public.company_products p where p.company_id = c.id) as products
    from public.companies c
    where c.status <> 'suspended'
    limit least(greatest(coalesce(p_limit, 5000), 1), 10000)) x
$$;

create or replace function public.company_sites_public(p_slug text)
returns json language sql stable security invoker set search_path = public as $$
  select coalesce(json_agg(json_build_object('id', s.id, 'name', s.name, 'type', s.type, 'city', s.city, 'gov', s.governorate,
         'forms', s.dosage_forms, 'min_batch', s.min_batch, 'capacity', s.capacity, 'free_slots', s.free_slots,
         'certs', (select coalesce(json_agg(json_build_object('name', t.name, 'expiry', t.expiry, 'source', t.source, 'checked', t.checked_at) order by t.name), '[]'::json)
                   from public.site_certificates t where t.site_id = s.id)) order by s.id), '[]'::json)
  from public.company_sites s join public.companies c on c.id = s.company_id where c.slug = p_slug
$$;
grant execute on function public.directory_companies(int) to anon, authenticated;
grant execute on function public.company_sites_public(text) to anon, authenticated;

-- trusted server-side work (imports, admin tools, the service role) runs without a user identity: guards apply to users only
create or replace function public.site_certificates_guard() returns trigger language plpgsql as $$
begin
  if auth.uid() is null or public.is_platform_admin() then return new; end if;
  if tg_op = 'INSERT' then new.checked_at := null;
  elsif new.name is distinct from old.name or new.expiry is distinct from old.expiry or new.checked_at is distinct from old.checked_at then new.checked_at := null; end if;
  return new;
end $$;
create or replace function public.company_documents_guard() returns trigger language plpgsql as $$
begin
  if auth.uid() is null then return new; end if;
  if new.status = 'verified' and (tg_op = 'INSERT' or old.status is distinct from 'verified') and not public.is_platform_admin() then
    raise exception 'Only Drugbox can mark a document as verified' using errcode = '42501';
  end if;
  return new;
end $$;
create or replace function public.verification_requests_apply() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.status <> old.status then
    if auth.uid() is not null and not public.is_platform_admin() then raise exception 'Only Drugbox reviews verification requests' using errcode = '42501'; end if;
    new.reviewed_by := auth.uid(); new.reviewed_at := now();
    if new.status = 'approved' then
      update public.companies set status = 'verified', registry = new.registry, tax_verified = true,
             licensed = licensed or new.licence_path is not null where id = new.company_id;
    end if;
  end if;
  return new;
end $$;

-- refresh the API's schema cache so new tables, functions and relationships are usable at once
notify pgrst, 'reload schema';
