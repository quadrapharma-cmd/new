-- Company hub (004 + 0006 + 0021): team and consent, sites and certificates, private documents, verification, level, search.
-- Runs as the real API roles (authenticated / anon) with a JWT, in one transaction that is rolled back; test data carries the
-- "CH " marker and every assertion is scoped to it. Run on a fresh database (stub + migrations): psql -f supabase/tests/company_hub.rls.sql
-- Harness: every action is a step() and every assertion an ok()/no(); an unexpected error becomes a FAIL with its message (the report
-- is never lost), a negative check passes only with the expected SQLSTATE, and psql exits non-zero when anything failed.
\set QUIET on
\set ON_ERROR_ROLLBACK on
set client_min_messages = warning;
\o /dev/null
begin;
create temp table r (n serial, name text, ok boolean, err text); grant all on r to authenticated, anon; grant all on r_n_seq to authenticated, anon;
create temp table ids (k text primary key, v text); grant all on ids to authenticated, anon;
create function pg_temp.as_user(u text) returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', u, true); perform set_config('request.jwt.claims', json_build_object('sub', u, 'role', 'authenticated')::text, true);
  perform set_config('role', 'authenticated', true); end $$;
create function pg_temp.as_anon() returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', '', true); perform set_config('request.jwt.claims', '{"role":"anon"}', true); perform set_config('role', 'anon', true); end $$;
-- server-side work (imports, the service role, an operator in psql): no JWT
create function pg_temp.as_server() returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', '', true); perform set_config('request.jwt.claims', '', true); perform set_config('role', 'none', true); end $$;
create function pg_temp.ok(p_name text, q text) returns void language plpgsql as $$ declare b boolean; begin
  execute 'select (' || q || ')::boolean' into b; insert into r(name, ok) values (p_name, coalesce(b, false));
  exception when others then insert into r(name, ok, err) values (p_name, false, sqlstate || ': ' || sqlerrm); end $$;
create function pg_temp.step(p_name text, q text) returns void language plpgsql as $$ begin execute q;
  exception when others then insert into r(name, ok, err) values ('step: ' || p_name, false, sqlstate || ': ' || sqlerrm); end $$;
-- the statement must be refused with this SQLSTATE; if it is allowed its effects are rolled back and the check fails
create function pg_temp.no(p_name text, q text, st text) returns void language plpgsql as $$ begin
  execute q; raise exception 'the statement was allowed' using errcode = 'DB001';
  exception when others then insert into r(name, ok, err) values (p_name, sqlstate = st, case when sqlstate <> st then sqlstate || ': ' || sqlerrm end); end $$;
create function pg_temp.id(k text) returns bigint language sql stable as $$ select v::bigint from ids where ids.k = id.k $$;

-- people: owner, member, outsider, Drugbox admin
insert into auth.users (id, email) values ('11111111-1111-1111-1111-111111111111','ch-owner@x'),('22222222-2222-2222-2222-222222222222','ch-member@x'),
  ('33333333-3333-3333-3333-333333333333','ch-outsider@x'),('44444444-4444-4444-4444-444444444444','ch-admin@x') on conflict do nothing;
insert into public.profiles (id, name) values ('11111111-1111-1111-1111-111111111111','CH Owner'),('22222222-2222-2222-2222-222222222222','CH Member'),
  ('33333333-3333-3333-3333-333333333333','CH Outsider'),('44444444-4444-4444-4444-444444444444','CH Admin') on conflict (id) do nothing;
update public.profiles set role = 'admin' where id = '44444444-4444-4444-4444-444444444444';

-- owner creates a company → becomes owner member automatically; it starts "pending"
select pg_temp.as_user('11111111-1111-1111-1111-111111111111');
select pg_temp.step('the owner creates a company', $$with x as (insert into public.companies (owner_id, name, type) values ('11111111-1111-1111-1111-111111111111', 'CH Test Pharma', 'Manufacturer') returning id) insert into ids select 'co', id::text from x$$);
select pg_temp.ok('creator becomes owner member', $$exists (select 1 from public.company_members where company_id = pg_temp.id('co') and user_id = '11111111-1111-1111-1111-111111111111' and role = 'owner' and accepted)$$);
select pg_temp.ok('slug filled automatically', $$(select slug like 'ch-test-pharma-%' from public.companies where id = pg_temp.id('co'))$$);
select pg_temp.ok('a new company starts "pending" (verification comes from Drugbox)', $$(select status = 'pending' and not tax_verified and not licensed from public.companies where id = pg_temp.id('co'))$$);
-- owner adds a member (consent starts off)
select pg_temp.step('the owner adds a member, already "consenting"', $$insert into public.company_members (company_id, user_id, role, accepted, show_public) values (pg_temp.id('co'), '22222222-2222-2222-2222-222222222222', 'sales', true, true)$$);
select pg_temp.ok('added member: consent off until they agree', $$(select not accepted and not show_public from public.company_members where company_id = pg_temp.id('co') and user_id = '22222222-2222-2222-2222-222222222222')$$);
select pg_temp.step('the owner adds a site, a certificate and a document', $$
  with x as (insert into public.company_sites (company_id, name, type) values (pg_temp.id('co'), 'CH Giza plant', 'factory') returning id) insert into ids select 'site', id::text from x;
  insert into public.site_certificates (site_id, company_id, name, expiry) values (pg_temp.id('site'), pg_temp.id('co'), 'WHO-GMP', '2027-04-01');
  insert into public.company_documents (company_id, type, product, number, created_by, file_path) values (pg_temp.id('co'), 'CEP', 'Metformin HCl', 'CH-CEP 2019-1', '11111111-1111-1111-1111-111111111111', 'private/cep.pdf')$$);

-- member: not a member before accepting; can give consent, cannot promote themself
select pg_temp.as_user('22222222-2222-2222-2222-222222222222');
select pg_temp.ok('an invited member has no rights before accepting (F-100)', $$not public.is_company_member(pg_temp.id('co'))$$);
select pg_temp.step('the member gives consent', $$update public.company_members set accepted = true, show_public = true where company_id = pg_temp.id('co') and user_id = '22222222-2222-2222-2222-222222222222'$$);
select pg_temp.ok('member can give their own consent', $$(select accepted from public.company_members where company_id = pg_temp.id('co') and user_id = '22222222-2222-2222-2222-222222222222')$$);
select pg_temp.no('member cannot promote themself to owner', $$update public.company_members set role = 'owner' where company_id = pg_temp.id('co') and user_id = '22222222-2222-2222-2222-222222222222'$$, '42501');
select pg_temp.no('sales member cannot add sites', $$insert into public.company_sites (company_id, name) values (pg_temp.id('co'), 'CH Fake site')$$, '42501');

-- outsider: reads public data, cannot edit anything, cannot see private file path
select pg_temp.as_user('33333333-3333-3333-3333-333333333333');
select pg_temp.ok('outsider reads the company, sites and certificates', $$(select count(*) from public.site_certificates where company_id = pg_temp.id('co') and name = 'WHO-GMP') = 1$$);
select pg_temp.step('the outsider tries to rename the company', $$update public.companies set name = 'Hacked' where id = pg_temp.id('co')$$);
select pg_temp.ok('outsider cannot rename the company (0 rows changed)', $$(select name from public.companies where id = pg_temp.id('co')) = 'CH Test Pharma'$$);
select pg_temp.no('outsider cannot read private document file paths', $$select file_path from public.company_documents where company_id = pg_temp.id('co')$$, '42501');
select pg_temp.ok('outsider still sees the passport metadata', $$(select count(*) from public.company_documents_public where company_id = pg_temp.id('co') and type = 'CEP') = 1$$);
select pg_temp.no('outsider cannot add themself to a team', $$insert into public.company_members (company_id, user_id, role) values (pg_temp.id('co'), '33333333-3333-3333-3333-333333333333', 'admin')$$, '42501');
select pg_temp.no('outsider cannot submit verification for another company', $$insert into public.verification_requests (company_id, submitted_by, registry) values (pg_temp.id('co'), '33333333-3333-3333-3333-333333333333', '999')$$, '42501');
select pg_temp.no('outsider cannot plant a certificate on the company''s site (F-13)', $$insert into public.site_certificates (site_id, company_id, name) values (pg_temp.id('site'), pg_temp.id('co'), 'Fake GMP')$$, '42501');

-- anonymous visitor: never writes, never sees private paths
select pg_temp.as_anon();
select pg_temp.no('anon cannot create a company', $$insert into public.companies (owner_id, name, type) values ('33333333-3333-3333-3333-333333333333', 'CH Anon Co', 'Manufacturer')$$, '42501');
select pg_temp.no('anon cannot join a team', $$insert into public.company_members (company_id, user_id, role) values (pg_temp.id('co'), '33333333-3333-3333-3333-333333333333', 'member')$$, '42501');
select pg_temp.no('anon cannot read private document file paths', $$select file_path from public.company_documents where company_id = pg_temp.id('co')$$, '42501');
select pg_temp.no('anon cannot submit verification', $$insert into public.verification_requests (company_id, submitted_by, registry) values (pg_temp.id('co'), '33333333-3333-3333-3333-333333333333', '999')$$, '42501');
select pg_temp.ok('anon sees no verification request', $$(select count(*) from public.verification_requests where company_id = pg_temp.id('co')) = 0$$);

-- owner: cannot self-verify a document or a verification request
select pg_temp.as_user('11111111-1111-1111-1111-111111111111');
select pg_temp.no('owner cannot mark their own document verified', $$update public.company_documents set status = 'verified' where company_id = pg_temp.id('co') and number = 'CH-CEP 2019-1'$$, '42501');
-- the licence is uploaded first to the company's own folder (documents/verification/<company id>/…, 0023 F-97)
select pg_temp.step('the owner uploads the licence', $$insert into storage.objects (bucket_id, name, owner) values ('documents', 'verification/' || pg_temp.id('co') || '/lic.pdf', '11111111-1111-1111-1111-111111111111')$$);
select pg_temp.no('a verification cannot point at a file outside the company folder', $$insert into public.verification_requests (company_id, submitted_by, registry, licence_path) values (pg_temp.id('co'), '11111111-1111-1111-1111-111111111111', 'CH123456', 'private/lic.pdf')$$, '42501');
select pg_temp.step('the owner submits the verification', $$insert into public.verification_requests (company_id, submitted_by, registry, licence_path) values (pg_temp.id('co'), '11111111-1111-1111-1111-111111111111', 'CH123456', 'verification/' || pg_temp.id('co') || '/lic.pdf')$$);
select pg_temp.step('the owner tries to approve it', $$update public.verification_requests set status = 'approved' where company_id = pg_temp.id('co')$$);
select pg_temp.ok('owner cannot approve their own verification', $$(select status = 'pending' from public.verification_requests where company_id = pg_temp.id('co'))$$);
select pg_temp.ok('level before approval = 0', $$public.company_tier(pg_temp.id('co')) = 0$$);

-- platform admin approves → company becomes verified + licensed; checks the certificate → level 3
select pg_temp.as_user('44444444-4444-4444-4444-444444444444');
select pg_temp.step('the admin approves', $$update public.verification_requests set status = 'approved' where company_id = pg_temp.id('co')$$);
select pg_temp.ok('admin approval verifies the company', $$(select status = 'verified' and tax_verified and licensed and registry = 'CH123456' from public.companies where id = pg_temp.id('co'))$$);
select pg_temp.ok('level after approval = 2 (certificate not yet checked)', $$public.company_tier(pg_temp.id('co')) = 2$$);
select pg_temp.step('the admin checks the certificate', $$update public.site_certificates set checked_at = now() where company_id = pg_temp.id('co') and name = 'WHO-GMP'$$);
select pg_temp.ok('level with a checked valid GMP certificate = 3', $$public.company_tier(pg_temp.id('co')) = 3$$);
select pg_temp.step('the admin verifies the document', $$update public.company_documents set status = 'verified' where company_id = pg_temp.id('co') and number = 'CH-CEP 2019-1'$$);
select pg_temp.ok('admin can verify a document', $$(select status = 'verified' from public.company_documents_public where company_id = pg_temp.id('co') and number = 'CH-CEP 2019-1')$$);

-- owner edits the checked certificate's expiry → check is cleared, level drops back to 2; same for a verified document (F-14)
select pg_temp.as_user('11111111-1111-1111-1111-111111111111');
select pg_temp.ok('the owner is told the company is verified', $$exists (select 1 from public.notifications where user_id = '11111111-1111-1111-1111-111111111111' and type = 'verification')$$);
select pg_temp.step('the owner edits the checked certificate', $$update public.site_certificates set expiry = '2028-01-01' where company_id = pg_temp.id('co') and name = 'WHO-GMP'$$);
select pg_temp.ok('company edit of a checked certificate clears the check', $$(select checked_at is null from public.site_certificates where company_id = pg_temp.id('co') and name = 'WHO-GMP')$$);
select pg_temp.ok('level returns to 2 until Drugbox re-checks', $$public.company_tier(pg_temp.id('co')) = 2$$);
select pg_temp.step('the owner tries to mark the certificate checked', $$update public.site_certificates set checked_at = now() where company_id = pg_temp.id('co') and name = 'WHO-GMP'$$);
select pg_temp.ok('owner cannot mark a certificate checked', $$(select checked_at is null from public.site_certificates where company_id = pg_temp.id('co') and name = 'WHO-GMP')$$);
select pg_temp.step('the owner rewrites the verified document', $$update public.company_documents set number = 'CH-CEP 2019-9', product = 'Other' where company_id = pg_temp.id('co') and number = 'CH-CEP 2019-1'$$);
select pg_temp.ok('owner edit to a verified document clears the verification (F-14)', $$(select status = 'declared' from public.company_documents_public where company_id = pg_temp.id('co') and number = 'CH-CEP 2019-9')$$);

-- search by active ingredient in Arabic
select pg_temp.as_server();
select pg_temp.step('a product is imported', $$insert into public.company_products (company_id, name, active_ingredient, active_ingredient_ar, role) values (pg_temp.id('co'), 'Metforal 500 mg', 'Metformin HCl', 'ميتفورمين', 'manufacturer')$$);
select pg_temp.as_user('33333333-3333-3333-3333-333333333333');
select pg_temp.ok('directory search finds the company by Arabic active ingredient', $$exists (select 1 from public.search_companies('ميتفورمين') where id = pg_temp.id('co'))$$);

-- ══ report ═══════════════════════════════════════════════════════════════════════════════════
select pg_temp.as_server();
select :'LAST_ERROR_SQLSTATE' = '00000' as clean, :'LAST_ERROR_MESSAGE' as lastmsg \gset
insert into r(name, ok, err) select 'no statement of the suite failed outside a check', :'clean'::boolean, nullif(:'lastmsg', '');
\o
\pset tuples_only on
select (case when ok then 'PASS  ' else 'FAIL  ' end) || name || coalesce('   [' || err || ']', '') from r order by n;
select 'TOTAL ' || count(*) filter (where ok) || ' / ' || count(*) from r;
\set ON_ERROR_STOP on
do $$ declare f int; t int; begin select count(*) filter (where not ok), count(*) into f, t from r;
  if t = 0 or f > 0 then raise exception '% of % check(s) FAILED', f, t; end if; end $$;
rollback;
