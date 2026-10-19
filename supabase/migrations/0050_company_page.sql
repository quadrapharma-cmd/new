-- ═════════════════════════════════════════════════════════════════════
-- 0050 — a company page keeps what its owner saves (B-02, B-03, B-09; J-BUSINESS-16, 18, 19, 22)
--   The live app said "published" and then "not saved online yet" for products, logo, cover and certificates, and
--   "sent for review in the next update" for sites: nothing reached the database. This adds what the page needs:
--   1. company-media: a bucket for a company's logo, cover and product photos (companies/<company id>/…), written only by
--      the company's owners / admins / regulatory, read by signed-in members (like videos and post media, 0020).
--   2. company_products: the catalogue fields the page shows (category, pack, description, minimum order, price with its
--      currency, photo) — written by owners / admins / regulatory (the existing policy). A photo must be the company's own
--      object in company-media. The directory's product summary carries them and is refreshed on UPDATE too (it was only
--      refreshed on insert and delete).
--   3. site_certificates: the certificate's document (documents bucket, verification/<company id>/…: the team's owners and
--      admins and Drugbox read it, never other members of the public) and certificates for the whole company (no site).
--      Drugbox checks a certificate (review_certificate: checked) or rejects it with a reason: the row and its file are
--      removed and the company's owner is told why (notification data — written in the reader's language by the app).
--      A changed name / expiry / document needs a new check (the existing guard, now also for the document).
--   4. company_sites: free production months are 'YYYY-MM' strings (a month index would shift every month).
-- Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. company-media bucket ────
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('company-media', 'company-media', true, 5242880, array['image/jpeg','image/png','image/webp'])
on conflict (id) do update set public = true, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;

create or replace function public.can_write_company_media(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select (storage.foldername(p_name))[1] = 'companies' and (storage.foldername(p_name))[2] ~ '^\d{1,18}$'
     and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin','regulatory'])
$$;
revoke all on function public.can_write_company_media(text) from public, anon, authenticated, service_role;
grant execute on function public.can_write_company_media(text) to authenticated, service_role;

do $$ begin
  create policy "company media: members see" on storage.objects for select to authenticated using (bucket_id = 'company-media');
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "company media: the team uploads" on storage.objects for insert to authenticated with check (bucket_id = 'company-media' and public.can_write_company_media(name));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "company media: the team replaces" on storage.objects for update to authenticated using (bucket_id = 'company-media' and public.can_write_company_media(name)) with check (bucket_id = 'company-media' and public.can_write_company_media(name));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "company media: the team deletes" on storage.objects for delete to authenticated using (bucket_id = 'company-media' and public.can_write_company_media(name));
exception when duplicate_object then null; end $$;

-- a picture on the page (logo, cover, product photo) is a company-media object of that company — never someone else's URL
create or replace function public.company_media_ok(p_company bigint, p_path text) returns boolean language sql stable security definer set search_path = public as $$
  select p_path is null or (p_path ~ ('^companies/' || p_company::text || '/[A-Za-z0-9._-]{1,120}$')
     and exists (select 1 from storage.objects o where o.bucket_id = 'company-media' and o.name = p_path))
$$;
revoke all on function public.company_media_ok(bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.company_media_ok(bigint, text) to service_role;

-- ── 2. products ────
alter table public.company_products add column if not exists category    text;
alter table public.company_products add column if not exists pack        text;
alter table public.company_products add column if not exists description text;
alter table public.company_products add column if not exists moq         text;
alter table public.company_products add column if not exists price       text;
alter table public.company_products add column if not exists currency    text;
alter table public.company_products add column if not exists image_path  text;
alter table public.company_products add column if not exists sort_order  int not null default 0;
alter table public.company_products add column if not exists updated_at  timestamptz not null default now();
do $$ begin
  alter table public.company_products add constraint company_products_fields_len check (length(category) <= 40 and length(pack) <= 20
    and length(description) <= 2000 and length(moq) <= 80 and length(price) <= 60 and length(image_path) <= 200 and sort_order between 0 and 10000);
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.company_products add constraint company_products_currency_chk check (currency is null or currency in ('EGP','USD','EUR','SAR','AED','GBP','CNY','INR'));
exception when duplicate_object then null; end $$;

create or replace function public.company_products_guard() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if not public.company_media_ok(new.company_id, new.image_path) then
    raise exception 'The product photo must be uploaded to this company''s page' using errcode = '42501';
  end if;
  new.updated_at := now();
  return new;
end $$;
revoke all on function public.company_products_guard() from public, anon, authenticated, service_role;
drop trigger if exists trg_company_products_guard on public.company_products;
create trigger trg_company_products_guard before insert or update on public.company_products for each row execute function public.company_products_guard();

-- the directory's product summary: the fields the page and the search show
create or replace function private.directory_products_refresh(p_ids bigint[]) returns void language plpgsql security definer set search_path = public as $$
begin
  if p_ids is null or cardinality(p_ids) = 0 then return; end if;
  perform pg_advisory_xact_lock(hashtext('drugbox.directory_products'));
  delete from private.directory_products d where d.company_id = any(p_ids)
     and not exists (select 1 from public.company_products p where p.company_id = d.company_id);
  insert into private.directory_products (company_id, products)
  select p.company_id, json_agg(json_build_object('id', p.id, 'name', p.name, 'ingredient', p.active_ingredient, 'ingredient_ar', p.active_ingredient_ar,
                 'form', p.dosage_form, 'strength', p.strength, 'role', p.role, 'category', p.category, 'pack', p.pack, 'description', p.description,
                 'moq', p.moq, 'price', p.price, 'currency', p.currency, 'image', p.image_path) order by p.sort_order, p.id)
    from public.company_products p where p.company_id = any(p_ids) group by p.company_id
  on conflict (company_id) do update set products = excluded.products;
end $$;
revoke all on function private.directory_products_refresh(bigint[]) from public, anon, authenticated, service_role;
drop trigger if exists trg_directory_products_upd on public.company_products;
create trigger trg_directory_products_upd after update on public.company_products referencing old table as old_rows new table as new_rows
  for each statement execute function private.directory_products_changed();
-- rows written before this migration get the new fields in the summary
select private.directory_products_refresh(array(select distinct company_id from public.company_products));

-- ── 3. certificates: their document, the whole company, Drugbox's decision ────
alter table public.site_certificates add column if not exists file_path text;
alter table public.site_certificates alter column site_id drop not null;
do $$ begin
  alter table public.site_certificates add constraint site_certificates_file_len check (length(file_path) <= 200);
exception when duplicate_object then null; end $$;

create or replace function public.site_certificates_guard() returns trigger language plpgsql as $$
begin
  -- server work, Drugbox's admins, and the review functions (review_certificate runs as its owner, not as the API role): a
  -- reviewer's own direct write meets the same rules as anyone's
  if auth.uid() is null or public.is_platform_admin() or current_user not in ('authenticated', 'anon') then return new; end if;
  if new.source = 'public_list' then new.source := 'company'; end if;
  -- the document is a private file of this company's verification folder that exists
  if new.file_path is not null and (tg_op = 'INSERT' or new.file_path is distinct from old.file_path) then
    if new.file_path !~ ('^verification/' || new.company_id::text || '/[A-Za-z0-9._-]{1,120}$')
       or not exists (select 1 from storage.objects o where o.bucket_id = 'documents' and o.name = new.file_path) then
      raise exception 'The certificate document must be uploaded for this company' using errcode = '42501';
    end if;
  end if;
  if new.file_path is not null then new.source := 'document'; elsif new.source = 'document' then new.source := 'company'; end if;
  if tg_op = 'INSERT' then new.checked_at := null;
  elsif new.name is distinct from old.name or new.expiry is distinct from old.expiry or new.file_path is distinct from old.file_path
        or new.checked_at is distinct from old.checked_at then new.checked_at := null; end if;
  return new;
end $$;
revoke all on function public.site_certificates_guard() from public, anon, authenticated, service_role;

-- Drugbox's decision on one certificate: checked, or rejected with a reason (the row and its file go; the owner is told why)
create or replace function public.review_certificate(p_id bigint, p_ok boolean, p_reason text default null)
returns boolean language plpgsql security definer set search_path = public as $$
declare c record; v_reason text := nullif(left(trim(coalesce(p_reason, '')), 300), ''); v_owner uuid; v_site text;
begin
  if auth.uid() is null or not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  select * into c from public.site_certificates where id = p_id for update;
  if c.id is null then raise exception 'This certificate does not exist any more' using errcode = 'P0002'; end if;
  select owner_id into v_owner from public.companies where id = c.company_id;
  select name into v_site from public.company_sites where id = c.site_id;
  if p_ok then
    update public.site_certificates set checked_at = now() where id = p_id;
    if v_owner is not null then
      insert into public.notifications (user_id, type, from_user, company_id, data)
      values (v_owner, 'cert_checked', null, c.company_id, jsonb_build_object('name', c.name, 'site', v_site));
    end if;
  else
    if v_reason is null then raise exception 'Write the reason for the company' using errcode = '22023'; end if;
    delete from public.site_certificates where id = p_id;
    if c.file_path is not null then delete from storage.objects where bucket_id = 'documents' and name = c.file_path; end if;
    if v_owner is not null then
      insert into public.notifications (user_id, type, from_user, company_id, data)
      values (v_owner, 'cert_rejected', null, c.company_id, jsonb_build_object('name', c.name, 'site', v_site, 'reason', v_reason));
    end if;
  end if;
  return true;
end $$;
revoke all on function public.review_certificate(bigint, boolean, text) from public, anon, authenticated, service_role;
grant execute on function public.review_certificate(bigint, boolean, text) to authenticated, service_role;

-- a company's own certificates without a site (the page editor's "Send for verification"), as the public reads them
create or replace function public.company_certs_public(p_slug text)
returns json language sql stable security invoker set search_path = public as $$
  select coalesce(json_agg(json_build_object('id', t.id, 'name', t.name, 'expiry', t.expiry, 'source', t.source, 'checked', t.checked_at) order by t.name), '[]'::json)
  from public.site_certificates t join public.companies c on c.id = t.company_id
  where c.slug = p_slug and c.status <> 'suspended' and t.site_id is null
$$;
revoke all on function public.company_certs_public(text) from public, anon, authenticated, service_role;
grant execute on function public.company_certs_public(text) to authenticated, service_role;

-- the team's quality people manage certificates (the policy above): they may also upload and read a certificate's document
-- (verification/<company id>/cert-…); the registry, tax card and licence stay with owners / admins
create or replace function public.can_read_document(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
                   or exists (select 1 from public.job_applications a join public.jobs j on j.id = a.job_id where a.cv_path = p_name and j.user_id = auth.uid())
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin']) or public.is_moderator()
                        or (storage.filename(p_name) like 'cert-%' and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['quality'])))
    when 'payments' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_platform_admin()
    else false end
$$;
create or replace function public.can_write_document(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin'])
                        or (storage.filename(p_name) like 'cert-%' and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['quality'])))
    when 'payments' then (storage.foldername(p_name))[2] = auth.uid()::text
    else false end
$$;


-- the public Sites tab: each certificate's id (the team's editor removes or changes that one row) and whether a document is attached
create or replace function public.company_sites_public(p_slug text)
returns json language sql stable set search_path = public as $$
  select coalesce(json_agg(json_build_object('id', s.id, 'name', s.name, 'type', s.type, 'city', s.city, 'gov', s.governorate,
         'forms', s.dosage_forms, 'min_batch', s.min_batch, 'capacity', s.capacity, 'free_slots', s.free_slots,
         'certs', (select coalesce(json_agg(json_build_object('id', t.id, 'name', t.name, 'expiry', t.expiry, 'source', t.source, 'checked', t.checked_at,
                                                              'doc', t.file_path is not null) order by t.name), '[]'::json)
                   from public.site_certificates t where t.site_id = s.id and t.company_id = s.company_id)) order by s.id), '[]'::json)
  from public.company_sites s join public.companies c on c.id = s.company_id where c.slug = p_slug and c.status <> 'suspended'
$$;

-- the page's logo and cover (logo_url, cover_url) are company-media objects of that company (a path, never an outside URL)
create or replace function public.companies_media_guard() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null or public.is_platform_admin() then return new; end if;
  if (tg_op = 'INSERT' or new.logo_url is distinct from old.logo_url) and not public.company_media_ok(new.id, new.logo_url) then
    raise exception 'The logo must be uploaded to this company''s page' using errcode = '42501';
  end if;
  if (tg_op = 'INSERT' or new.cover_url is distinct from old.cover_url) and not public.company_media_ok(new.id, new.cover_url) then
    raise exception 'The cover photo must be uploaded to this company''s page' using errcode = '42501';
  end if;
  return new;
end $$;
revoke all on function public.companies_media_guard() from public, anon, authenticated, service_role;
drop trigger if exists trg_companies_media_guard on public.companies;
create trigger trg_companies_media_guard before insert or update of logo_url, cover_url on public.companies for each row execute function public.companies_media_guard();

-- ── 4. free production months are 'YYYY-MM' ────
update public.company_sites set free_slots = '[]'::jsonb
 where jsonb_typeof(free_slots) <> 'array' or jsonb_path_exists(free_slots, '$[*] ? (@.type() != "string" || !(@ like_regex "^[0-9]{4}-[0-9]{2}$"))');
do $$ begin
  alter table public.company_sites add constraint company_sites_slots_months check (jsonb_typeof(free_slots) = 'array'
    and jsonb_array_length(free_slots) <= 24 and not jsonb_path_exists(free_slots, '$[*] ? (@.type() != "string" || !(@ like_regex "^[0-9]{4}-[0-9]{2}$"))'));
exception when duplicate_object then null; end $$;

notify pgrst, 'reload schema';
