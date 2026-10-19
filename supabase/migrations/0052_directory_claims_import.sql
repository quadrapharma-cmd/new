-- ═════════════════════════════════════════════════════════════════════
-- 0052 — how companies get into the directory (B-01; J-BUSINESS-12, 14, 49)
--   The directory was empty and nothing could fill it except self-registration. This adds the two other honest ways in:
--   1. Claims with proof: claim_company(company, note, registry document) — the claimant uploads the commercial registry
--      document to documents/claims/<their id>/… (only they and Drugbox's reviewers can read it); the claim waits in Admin →
--      Review → Claims; approving it makes the claimant the owner (0021's verification_requests_apply), rejecting it tells
--      them why. A claim without the document is refused.
--   2. Admin bulk import: admin_import_companies(rows, dry_run) — a Drugbox admin loads companies from a PUBLIC list (each
--      row names its source; nothing is invented): every row is validated (name, sectors from the directory's list, e-mail,
--      website, phone), de-duplicated against the existing companies (same registry number, or the same name / Arabic name
--      once spelling, case, punctuation and legal suffixes are set aside) and against the rows before it, and created as
--      status 'unclaimed', source 'public_list', no owner — a page its company can claim. A dry run reports what would happen
--      without writing. tools/import_companies.py reads a CSV and calls it.
--   companies.source_ref keeps where an imported company came from (shown to Drugbox, not invented later).
-- Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

alter table public.companies add column if not exists source_ref text;
do $$ begin
  alter table public.companies add constraint companies_source_ref_len check (length(source_ref) <= 300);
exception when duplicate_object then null; end $$;

-- ── documents: a claim's registry document (claims/<claimant>/…) ────
create or replace function public.can_read_document(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
                   or exists (select 1 from public.job_applications a join public.jobs j on j.id = a.job_id where a.cv_path = p_name and j.user_id = auth.uid())
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin']) or public.is_moderator()
                        or (storage.filename(p_name) like 'cert-%' and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['quality'])))
    when 'payments' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_platform_admin()
    when 'claims' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_moderator()
    else false end
$$;
create or replace function public.can_write_document(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin'])
                        or (storage.filename(p_name) like 'cert-%' and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['quality'])))
    when 'payments' then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'claims' then (storage.foldername(p_name))[2] = auth.uid()::text
    else false end
$$;

-- ── claims need the registry document ────
do $$ begin   -- the claim takes three arguments now (no defaults: a two-argument call reaches the overload below, never this one by accident)
  if exists (select 1 from pg_proc p where p.oid = 'public.claim_company(bigint, text, text)'::regprocedure and p.pronargdefaults > 0) then drop function public.claim_company(bigint, text, text); end if;
exception when undefined_function then null; end $$;
create or replace function public.claim_company(p_company_id bigint, p_note text, p_registry_path text)
returns bigint language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); c public.companies; rid bigint;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into c from public.companies where id = p_company_id;
  if c.id is null then raise exception 'Company not found' using errcode = 'P0002'; end if;
  if c.status <> 'unclaimed' or c.owner_id is not null then raise exception 'This page is already claimed' using errcode = '42501'; end if;
  if p_registry_path is null or p_registry_path !~ ('^claims/' || me::text || '/[A-Za-z0-9._-]{1,120}$')
     or not exists (select 1 from storage.objects o where o.bucket_id = 'documents' and o.name = p_registry_path) then
    raise exception 'Attach the commercial registry document' using errcode = '22023';
  end if;
  if exists (select 1 from public.verification_requests v where v.company_id = c.id and v.submitted_by = me and v.claim and v.status = 'pending') then
    raise exception 'Your claim is already under review' using errcode = '42501';
  end if;
  if (select count(*) from public.verification_requests v where v.submitted_by = me and v.claim and v.created_at > now() - interval '1 day') >= 5 then
    raise exception 'Too many claims today — please try again tomorrow' using errcode = '42501';
  end if;
  insert into public.verification_requests (company_id, submitted_by, registry, note, claim, registry_path)
  values (c.id, me, coalesce(nullif(trim(c.registry), ''), 'claim-' || c.id), left(nullif(trim(p_note), ''), 1000), true, p_registry_path)
  returning id into rid;
  return rid;
end $$;
revoke all on function public.claim_company(bigint, text, text) from public, anon, authenticated, service_role;
grant execute on function public.claim_company(bigint, text, text) to authenticated, service_role;
-- the two-argument claim (0021) stays callable with the same rules: without a registry document it is refused
create or replace function public.claim_company(p_company_id bigint, p_note text default null) returns bigint language sql security definer set search_path = public as $$
  select public.claim_company(p_company_id, p_note, null::text)
$$;
revoke all on function public.claim_company(bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.claim_company(bigint, text) to authenticated, service_role;

-- ── admin bulk import from a public list ────
-- a name as the directory compares it: lower case, Arabic letters unified, no punctuation, no legal-form suffixes
create or replace function public.company_name_key(p text) returns text language sql immutable set search_path = public as $$
  select nullif(trim(regexp_replace(regexp_replace(regexp_replace(regexp_replace(
           translate(lower(coalesce(p, '')), 'أإآىةؤئـ', 'ااايهوي'),
           '[ً-ْ]', '', 'g'),
           '[^[:alnum:]؀-ۿ ]+', ' ', 'g'),
           '(^| )(s ?a ?e|sae|co|company|corp|corporation|inc|ltd|llc|limited|plc|ش ?م ?م|شركه)(?= |$)', ' ', 'g'),
           '\s+', ' ', 'g')), '')
$$;
revoke all on function public.company_name_key(text) from public, anon, authenticated, service_role;
grant execute on function public.company_name_key(text) to authenticated, service_role;
create index if not exists idx_companies_name_key on public.companies (public.company_name_key(name));
create index if not exists idx_companies_name_ar_key on public.companies (public.company_name_key(name_ar)) where name_ar is not null;
create index if not exists idx_companies_registry on public.companies (registry) where registry is not null;

create or replace function public.admin_import_companies(p_rows jsonb, p_dry_run boolean default true)
returns jsonb language plpgsql security definer set search_path = public as $$
declare r jsonb; i int := 0; out jsonb := '[]'::jsonb; v_name text; v_ar text; v_sectors text[]; v_bad text; v_dup bigint; v_id bigint; v_slug text;
        v_seen text[] := '{}'; v_key text; v_akey text; v_email text; v_web text; v_phone text; v_src text; v_reg text; v_forms text[]; v_site text; v_certs text[];
        ok_sectors text[] := array['Manufacturer','Cosmetics','CMO / Toll','API & excipients','Packaging','Labs & testing','Distribution','Regulatory & consulting','Supplements'];
begin
  if auth.uid() is null or not public.is_platform_admin() then raise exception 'Only a Drugbox admin can import companies' using errcode = '42501'; end if;
  if jsonb_typeof(p_rows) <> 'array' or jsonb_array_length(p_rows) = 0 then raise exception 'No rows to import' using errcode = '22023'; end if;
  if jsonb_array_length(p_rows) > 2000 then raise exception 'At most 2,000 rows per import' using errcode = '54000'; end if;
  for r in select value from jsonb_array_elements(p_rows) loop
    i := i + 1; v_bad := null; v_dup := null; v_id := null; v_slug := null;
    v_name := nullif(trim(r ->> 'name'), ''); v_ar := nullif(trim(r ->> 'name_ar'), ''); v_src := nullif(trim(r ->> 'source'), '');
    v_reg := nullif(regexp_replace(coalesce(r ->> 'registry', ''), '\D', '', 'g'), '');
    v_email := nullif(lower(trim(r ->> 'email')), ''); v_web := nullif(trim(r ->> 'website'), ''); v_phone := nullif(trim(r ->> 'phone'), '');
    v_sectors := array(select trim(x) from unnest(string_to_array(coalesce(r ->> 'sectors', ''), ';')) x where trim(x) <> '');
    v_forms := array(select trim(x) from unnest(string_to_array(coalesce(r ->> 'dosage_forms', ''), ';')) x where trim(x) <> '');
    v_certs := array(select trim(x) from unnest(string_to_array(coalesce(r ->> 'certificates', ''), ';')) x where trim(x) <> '');
    v_site := nullif(trim(r ->> 'site'), '');
    v_key := public.company_name_key(v_name); v_akey := public.company_name_key(v_ar);
    if v_name is null or length(v_name) < 2 or length(v_name) > 200 then v_bad := 'name is missing or longer than 200 characters';
    elsif v_ar is not null and length(v_ar) > 200 then v_bad := 'Arabic name is longer than 200 characters';
    elsif v_src is null then v_bad := 'source is missing — every imported company names the public list it comes from';
    elsif length(v_src) > 300 then v_bad := 'source is longer than 300 characters';
    elsif cardinality(v_sectors) = 0 then v_bad := 'sectors are missing';
    elsif exists (select 1 from unnest(v_sectors) s where s <> all(ok_sectors)) then v_bad := 'unknown sector: ' || (select string_agg(s, ', ') from unnest(v_sectors) s where s <> all(ok_sectors));
    elsif v_email is not null and v_email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then v_bad := 'e-mail is not valid';
    elsif v_web is not null and v_web !~* '^(https?://)?[a-z0-9.-]+\.[a-z]{2,}(/\S*)?$' then v_bad := 'website is not valid';
    elsif v_phone is not null and v_phone !~ '^\+?[0-9 ()-]{6,30}$' then v_bad := 'phone is not valid';
    elsif length(coalesce(r ->> 'governorate', '')) > 60 or length(coalesce(r ->> 'city', '')) > 80 or length(coalesce(r ->> 'address', '')) > 500 then v_bad := 'address fields are too long';
    elsif v_site is not null and (length(v_site) < 2 or length(v_site) > 120) then v_bad := 'site name must be 2–120 characters';
    elsif exists (select 1 from unnest(v_certs) x where length(x) < 2 or length(x) > 80) then v_bad := 'a certificate name must be 2–80 characters';
    end if;
    if v_bad is null then
      select x.id into v_dup from (                     -- each test on its own index (100,000 companies: no scan per row)
          select c.id from public.companies c where v_reg is not null and c.registry = v_reg
          union all select c.id from public.companies c where public.company_name_key(c.name) = v_key
          union all select c.id from public.companies c where v_akey is not null and public.company_name_key(c.name) = v_akey
          union all select c.id from public.companies c where c.name_ar is not null and public.company_name_key(c.name_ar) = v_key
          union all select c.id from public.companies c where v_akey is not null and c.name_ar is not null and public.company_name_key(c.name_ar) = v_akey) x
       limit 1;
      if v_dup is null and (v_key = any(v_seen) or (v_akey is not null and v_akey = any(v_seen)) or (v_reg is not null and ('reg:' || v_reg) = any(v_seen))) then v_bad := 'duplicate of an earlier row in this file'; end if;
    end if;
    if v_bad is not null then out := out || jsonb_build_object('row', i, 'name', v_name, 'status', 'invalid', 'reason', v_bad); continue; end if;
    if v_dup is not null then out := out || jsonb_build_object('row', i, 'name', v_name, 'status', 'duplicate', 'id', v_dup, 'slug', (select slug from public.companies where id = v_dup)); continue; end if;
    v_seen := v_seen || v_key || coalesce(v_akey, v_key) || case when v_reg is not null then 'reg:' || v_reg else v_key end;
    if not p_dry_run then
      insert into public.companies (owner_id, name, slug, name_ar, type, sectors, governorate, city, location, phone, email, website, registry, status, source, source_ref)
      values (null, v_name, nullif(public.slugify(regexp_replace(v_name, '\s*(S\.?\s?A\.?\s?E\.?|Co\.?|Ltd\.?|LLC|Inc\.?)\s*$', '', 'i')), ''), v_ar, v_sectors[1], v_sectors, nullif(trim(r ->> 'governorate'), ''), nullif(trim(r ->> 'city'), ''), nullif(trim(r ->> 'address'), ''),
              v_phone, v_email, regexp_replace(coalesce(v_web, ''), '^https?://', '', 'i'), v_reg, 'unclaimed', 'public_list', v_src)
      returning id, slug into v_id, v_slug;
      update public.companies set website = null where id = v_id and website = '';
      if v_site is not null or cardinality(v_forms) > 0 or cardinality(v_certs) > 0 then
        with s as (insert into public.company_sites (company_id, name, type, city, governorate, dosage_forms)
                   values (v_id, coalesce(v_site, left(coalesce(nullif(trim(r ->> 'city'), ''), v_name) || ' site', 120)), 'factory', nullif(trim(r ->> 'city'), ''), nullif(trim(r ->> 'governorate'), ''), v_forms) returning id)
        insert into public.site_certificates (site_id, company_id, name, source) select s.id, v_id, x, 'public_list' from s, unnest(v_certs) x;
      end if;
    end if;
    out := out || jsonb_build_object('row', i, 'name', v_name, 'status', case when p_dry_run then 'would create' else 'created' end, 'id', v_id, 'slug', v_slug);
  end loop;
  return jsonb_build_object('dry_run', p_dry_run, 'rows', i,
    'created', (select count(*) from jsonb_array_elements(out) e where e ->> 'status' in ('created', 'would create')),
    'duplicates', (select count(*) from jsonb_array_elements(out) e where e ->> 'status' = 'duplicate'),
    'invalid', (select count(*) from jsonb_array_elements(out) e where e ->> 'status' = 'invalid'), 'results', out);
end $$;
revoke all on function public.admin_import_companies(jsonb, boolean) from public, anon, authenticated, service_role;
grant execute on function public.admin_import_companies(jsonb, boolean) to authenticated, service_role;

-- ── Directory health for Drugbox (J-BUSINESS-49): the whole directory, from the database ────
create or replace function public.directory_health() returns jsonb language plpgsql stable security definer set search_path = public as $$
declare v jsonb;
begin
  if auth.uid() is null or not public.is_moderator() then raise exception 'Only the Drugbox team can see this' using errcode = '42501'; end if;
  select jsonb_build_object(
    'total', count(*), 'claimed', count(*) filter (where status <> 'unclaimed'), 'verified', count(*) filter (where status = 'verified'),
    'active', count(*) filter (where updated_at > now() - interval '7 days'), 'dormant', count(*) filter (where updated_at < now() - interval '60 days'),
    'stale_n', count(*) filter (where updated_at < now() - interval '180 days'))
    into v from public.companies where status <> 'suspended';
  return v || jsonb_build_object(
    'stale', coalesce((select jsonb_agg(jsonb_build_object('slug', slug, 'name', name, 'updated_at', updated_at) order by updated_at) from
              (select slug, name, updated_at from public.companies where status <> 'suspended' and updated_at < now() - interval '180 days' order by updated_at limit 20) x), '[]'::jsonb),
    'reported', coalesce((select jsonb_agg(jsonb_build_object('slug', c.slug, 'name', c.name, 'n', x.n, 'sections', x.sections) order by x.last desc) from
              (select company_id, count(*) as n, string_agg(distinct section, ', ') as sections, max(created_at) as last from public.company_reports where status = 'open' group by company_id order by max(created_at) desc limit 20) x
              join public.companies c on c.id = x.company_id), '[]'::jsonb),
    'open_reports', (select count(*) from public.company_reports where status = 'open'),
    'deals_month', (select count(*) from public.deals where created_at > now() - interval '30 days'),
    'requests', (select count(*) from public.deals where to_company_id is not null and created_at > now() - interval '90 days'),
    'answered', (select count(*) from public.deals d where d.to_company_id is not null and d.created_at > now() - interval '90 days'
                   and exists (select 1 from public.deal_events e where e.deal_id = d.id and e.side = 'to')));
end $$;
revoke all on function public.directory_health() from public, anon, authenticated, service_role;
grant execute on function public.directory_health() to authenticated, service_role;

-- ── the reporter of wrong information hears what Drugbox did (J-BUSINESS-09) ────
create or replace function public.company_reports_decided_notify() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.status is distinct from old.status and old.status = 'open' and new.status in ('resolved', 'dismissed', 'fixed') then
    insert into public.notifications (user_id, type, from_user, company_id, data)
    values (new.reporter, 'report_decided', null, new.company_id,
            jsonb_build_object('company', (select name from public.companies where id = new.company_id), 'section', new.section, 'outcome', new.status));
  end if;
  return null;
end $$;
revoke all on function public.company_reports_decided_notify() from public, anon, authenticated, service_role;
drop trigger if exists trg_company_reports_decided_notify on public.company_reports;
create trigger trg_company_reports_decided_notify after update of status on public.company_reports for each row execute function public.company_reports_decided_notify();

notify pgrst, 'reload schema';
