-- Company page data and team (0050 B-02/B-03/B-09, 0051 B-04): products and pictures, sites and certificates and Drugbox's
-- decision on them, invitations, join requests and routing by role. Runs as the real API roles with a JWT, in one transaction
-- that is rolled back; test data carries the "CP " marker. Run on a fresh database (stub + migrations):
--   psql -f supabase/tests/company_page_team.rls.sql
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
create function pg_temp.as_server() returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', '', true); perform set_config('request.jwt.claims', '', true); perform set_config('role', 'none', true); end $$;
create function pg_temp.ok(p_name text, q text) returns void language plpgsql as $$ declare b boolean; begin
  execute 'select (' || q || ')::boolean' into b; insert into r(name, ok) values (p_name, coalesce(b, false));
  exception when others then insert into r(name, ok, err) values (p_name, false, sqlstate || ': ' || sqlerrm); end $$;
create function pg_temp.step(p_name text, q text) returns void language plpgsql as $$ begin execute q;
  exception when others then insert into r(name, ok, err) values ('step: ' || p_name, false, sqlstate || ': ' || sqlerrm); end $$;
create function pg_temp.no(p_name text, q text, st text) returns void language plpgsql as $$ begin
  execute q; raise exception 'the statement was allowed' using errcode = 'DB001';
  exception when others then insert into r(name, ok, err) values (p_name, sqlstate = st, case when sqlstate <> st then sqlstate || ': ' || sqlerrm end); end $$;
create function pg_temp.id(k text) returns bigint language sql stable as $$ select v::bigint from ids where ids.k = id.k $$;

-- people: owner, admin, sales member, quality member, an outsider, an invitee with an account, a moderator
insert into auth.users (id, email) values ('d1111111-1111-1111-1111-111111111111','cp-owner@x.test'),('d2222222-2222-2222-2222-222222222222','cp-admin@x.test'),
  ('d3333333-3333-3333-3333-333333333333','cp-sales@x.test'),('d4444444-4444-4444-4444-444444444444','cp-quality@x.test'),('d5555555-5555-5555-5555-555555555555','cp-out@x.test'),
  ('d6666666-6666-6666-6666-666666666666','cp-invitee@x.test'),('d7777777-7777-7777-7777-777777777777','cp-mod@x.test') on conflict do nothing;
insert into public.profiles (id, name) values ('d1111111-1111-1111-1111-111111111111','CP Owner'),('d2222222-2222-2222-2222-222222222222','CP Admin'),
  ('d3333333-3333-3333-3333-333333333333','CP Sales'),('d4444444-4444-4444-4444-444444444444','CP Quality'),('d5555555-5555-5555-5555-555555555555','CP Outsider'),
  ('d6666666-6666-6666-6666-666666666666','CP Invitee'),('d7777777-7777-7777-7777-777777777777','CP Moderator') on conflict (id) do update set name = excluded.name;
update public.profiles set role = 'admin' where id = 'd7777777-7777-7777-7777-777777777777';

select pg_temp.as_server();
select pg_temp.step('a company with an owner, an admin, a sales and a quality member; a second company of the outsider', $$
  with x as (insert into public.companies (owner_id, name, type) values ('d1111111-1111-1111-1111-111111111111', 'CP Page Pharma', 'Manufacturer') returning id) insert into ids select 'co', id::text from x;
  insert into public.company_members (company_id, user_id, role, accepted, show_public) values
    (pg_temp.id('co'), 'd2222222-2222-2222-2222-222222222222', 'admin', true, true), (pg_temp.id('co'), 'd3333333-3333-3333-3333-333333333333', 'sales', true, false),
    (pg_temp.id('co'), 'd4444444-4444-4444-4444-444444444444', 'quality', true, false);
  with x as (insert into public.companies (owner_id, name, type) values ('d5555555-5555-5555-5555-555555555555', 'CP Other Co', 'Distributor') returning id) insert into ids select 'other', id::text from x;
  insert into storage.objects (bucket_id, name, owner) values ('company-media', 'companies/' || pg_temp.id('co') || '/product-a.jpg', 'd1111111-1111-1111-1111-111111111111'),
    ('company-media', 'companies/' || pg_temp.id('other') || '/logo-b.jpg', 'd5555555-5555-5555-5555-555555555555'),
    ('documents', 'verification/' || pg_temp.id('co') || '/cert-a.pdf', 'd4444444-4444-4444-4444-444444444444');
  with x as (insert into public.companies (owner_id, name, type, status, source) values (null, 'CP Unclaimed Labs', 'Lab', 'unclaimed', 'public_list') returning id) insert into ids select 'unc', id::text from x$$);

-- ══ 0050: products ══
select pg_temp.as_user('d1111111-1111-1111-1111-111111111111');
select pg_temp.step('the owner adds a product with category, pack, price, currency and the company''s own photo', $$
  with x as (insert into public.company_products (company_id, name, category, pack, description, moq, price, currency, image_path)
    values (pg_temp.id('co'), 'CP Paracetamol 500 mg', 'Finished dosage', 'blister', 'Film-coated', '100,000 tablets', 'US$ 0.02', 'USD', 'companies/' || pg_temp.id('co') || '/product-a.jpg') returning id) insert into ids select 'p1', id::text from x$$);
select pg_temp.ok('the product is saved with its fields', $$(select price || currency || pack from public.company_products where id = pg_temp.id('p1')) = 'US$ 0.02USDblister'$$);
select pg_temp.ok('the directory''s product summary carries the new fields', $$(select products::jsonb -> 0 ->> 'image' from private.directory_products where company_id = pg_temp.id('co')) = 'companies/' || pg_temp.id('co') || '/product-a.jpg'$$);
select pg_temp.no('a photo of another company is refused', $$update public.company_products set image_path = 'companies/' || pg_temp.id('other') || '/logo-b.jpg' where id = pg_temp.id('p1')$$, '42501');
select pg_temp.no('a photo that was never uploaded is refused', $$update public.company_products set image_path = 'companies/' || pg_temp.id('co') || '/missing.jpg' where id = pg_temp.id('p1')$$, '42501');
select pg_temp.no('an outside URL as photo is refused', $$update public.company_products set image_path = 'https://evil.example/x.png' where id = pg_temp.id('p1')$$, '42501');
select pg_temp.no('an unknown currency is refused', $$update public.company_products set currency = 'BTC' where id = pg_temp.id('p1')$$, '23514');
select pg_temp.step('the owner renames the product', $$update public.company_products set name = 'CP Paracetamol 500 mg tabs' where id = pg_temp.id('p1')$$);
select pg_temp.ok('the directory summary follows an UPDATE', $$(select products::jsonb -> 0 ->> 'name' from private.directory_products where company_id = pg_temp.id('co')) = 'CP Paracetamol 500 mg tabs'$$);
select pg_temp.as_user('d3333333-3333-3333-3333-333333333333');
select pg_temp.step('a sales member tries to rename a product', $$update public.company_products set name = 'CP hacked' where id = pg_temp.id('p1')$$);
select pg_temp.ok('…the row is not touched (RLS)', $$(select name from public.company_products where id = pg_temp.id('p1')) = 'CP Paracetamol 500 mg tabs'$$);
select pg_temp.as_user('d5555555-5555-5555-5555-555555555555');
select pg_temp.no('an outsider cannot add a product to the company', $$insert into public.company_products (company_id, name) values (pg_temp.id('co'), 'CP fake')$$, '42501');
select pg_temp.step('an outsider tries to delete a product', $$delete from public.company_products where id = pg_temp.id('p1')$$);
select pg_temp.ok('…the row is still there', $$exists (select 1 from public.company_products where id = pg_temp.id('p1'))$$);
select pg_temp.ok('everyone signed in reads the products', $$(select count(*) from public.company_products where company_id = pg_temp.id('co')) = 1$$);

-- ══ 0050: logo / cover ══
select pg_temp.as_user('d1111111-1111-1111-1111-111111111111');
select pg_temp.step('the owner sets an uploaded logo and cover', $$update public.companies set logo_url = 'companies/' || pg_temp.id('co') || '/product-a.jpg', cover_url = 'companies/' || pg_temp.id('co') || '/product-a.jpg' where id = pg_temp.id('co')$$);
select pg_temp.ok('logo and cover are saved', $$(select logo_url is not null and cover_url is not null from public.companies where id = pg_temp.id('co'))$$);
select pg_temp.no('an outside URL as logo is refused', $$update public.companies set logo_url = 'https://tracker.example/p.gif' where id = pg_temp.id('co')$$, '42501');
select pg_temp.no('another company''s picture as cover is refused', $$update public.companies set cover_url = 'companies/' || pg_temp.id('other') || '/logo-b.jpg' where id = pg_temp.id('co')$$, '42501');
select pg_temp.ok('company-media: the owner may upload under the company''s folder', $$public.can_write_company_media('companies/' || pg_temp.id('co') || '/x.jpg')$$);
select pg_temp.ok('company-media: not under another company''s folder', $$not public.can_write_company_media('companies/' || pg_temp.id('other') || '/x.jpg')$$);
select pg_temp.as_user('d3333333-3333-3333-3333-333333333333');
select pg_temp.ok('company-media: a sales member may not upload pictures', $$not public.can_write_company_media('companies/' || pg_temp.id('co') || '/x.jpg')$$);

-- ══ 0050: sites and certificates ══
select pg_temp.as_user('d2222222-2222-2222-2222-222222222222');
select pg_temp.step('the admin adds a site with capabilities and free months', $$
  with x as (insert into public.company_sites (company_id, name, type, governorate, city, dosage_forms, capacity, free_slots)
    values (pg_temp.id('co'), 'CP Obour plant', 'factory', 'Qalyubia', 'Obour', '{Tablets}', '6M / month', '["2026-11","2027-01"]') returning id) insert into ids select 's1', id::text from x$$);
select pg_temp.no('free months must be YYYY-MM strings', $$update public.company_sites set free_slots = '[1,2]' where id = pg_temp.id('s1')$$, '23514');
select pg_temp.as_user('d4444444-4444-4444-4444-444444444444');
select pg_temp.step('the quality member adds a GDP certificate with its document (and tries to mark it checked)', $$
  with x as (insert into public.site_certificates (site_id, company_id, name, expiry, file_path, checked_at)
    values (pg_temp.id('s1'), pg_temp.id('co'), 'GDP', '2027-12-31', 'verification/' || pg_temp.id('co') || '/cert-a.pdf', null) returning id) insert into ids select 'c1', id::text from x$$);
select pg_temp.ok('the certificate is saved unchecked, its source the document', $$(select checked_at is null and source = 'document' from public.site_certificates where id = pg_temp.id('c1'))$$);
select pg_temp.step('the quality member tries to mark it checked', $$update public.site_certificates set checked_at = now() where id = pg_temp.id('c1')$$);
select pg_temp.ok('…it stays unchecked', $$(select checked_at is null from public.site_certificates where id = pg_temp.id('c1'))$$);
select pg_temp.no('a certificate document from another folder is refused', $$insert into public.site_certificates (site_id, company_id, name, file_path) values (pg_temp.id('s1'), pg_temp.id('co'), 'ISO 9001', 'verification/' || pg_temp.id('other') || '/cert-x.pdf')$$, '42501');
select pg_temp.ok('the quality member may read and upload certificate documents (cert-…)', $$public.can_read_document('verification/' || pg_temp.id('co') || '/cert-a.pdf') and public.can_write_document('verification/' || pg_temp.id('co') || '/cert-b.pdf')$$);
select pg_temp.ok('…but not the registry or tax card', $$not public.can_read_document('verification/' || pg_temp.id('co') || '/registry-a.pdf') and not public.can_write_document('verification/' || pg_temp.id('co') || '/tax_card-a.pdf')$$);
select pg_temp.step('a company-wide certificate (no site)', $$with x as (insert into public.site_certificates (site_id, company_id, name) values (null, pg_temp.id('co'), 'ISO 9001') returning id) insert into ids select 'c2', id::text from x$$);
select pg_temp.as_user('d5555555-5555-5555-5555-555555555555');
select pg_temp.ok('an outsider cannot read the certificate document', $$not public.can_read_document('verification/' || pg_temp.id('co') || '/cert-a.pdf')$$);
select pg_temp.no('an outsider cannot add a site', $$insert into public.company_sites (company_id, name) values (pg_temp.id('co'), 'CP fake site')$$, '42501');
select pg_temp.ok('the public Sites tab lists the site with its certificate id and "has a document" (not the path)', $$(select (x -> 0 -> 'certs' -> 0 ->> 'id')::bigint = pg_temp.id('c1') and (x -> 0 -> 'certs' -> 0 ->> 'doc')::boolean and position('cert-a' in x::text) = 0 from (select public.company_sites_public((select slug from public.companies where id = pg_temp.id('co'))) x) y)$$);
select pg_temp.ok('the company-wide certificates are public as such', $$(select json_array_length(public.company_certs_public((select slug from public.companies where id = pg_temp.id('co'))))) = 1$$);
select pg_temp.no('an outsider cannot decide a certificate', $$select public.review_certificate(pg_temp.id('c1'), true)$$, '42501');
select pg_temp.as_user('d7777777-7777-7777-7777-777777777777');
select pg_temp.no('a rejection needs a reason', $$select public.review_certificate(pg_temp.id('c2'), false, '  ')$$, '22023');
select pg_temp.step('Drugbox checks the GDP certificate and rejects the company-wide one', $$select public.review_certificate(pg_temp.id('c1'), true); select public.review_certificate(pg_temp.id('c2'), false, 'Not readable')$$);
select pg_temp.as_server();
select pg_temp.ok('checked: checked_at set, owner notified', $$(select checked_at is not null from public.site_certificates where id = pg_temp.id('c1')) and exists (select 1 from public.notifications where user_id = 'd1111111-1111-1111-1111-111111111111' and type = 'cert_checked')$$);
select pg_temp.ok('rejected: the row is gone and the owner gets the reason', $$not exists (select 1 from public.site_certificates where id = pg_temp.id('c2')) and exists (select 1 from public.notifications where user_id = 'd1111111-1111-1111-1111-111111111111' and type = 'cert_rejected' and data ->> 'reason' = 'Not readable')$$);
select pg_temp.as_user('d4444444-4444-4444-4444-444444444444');
select pg_temp.step('the quality member changes the checked certificate''s expiry', $$update public.site_certificates set expiry = '2028-06-30' where id = pg_temp.id('c1')$$);
select pg_temp.ok('a changed certificate needs a new check', $$(select checked_at is null from public.site_certificates where id = pg_temp.id('c1'))$$);

-- ══ 0051: team ══
select pg_temp.as_server();
select pg_temp.ok('who receives what follows the roles: quotes → sales, questionnaires → quality, dossiers → admin', $$
  (select user_id from public.company_routing where company_id = pg_temp.id('co') and request_type = 'quote') = 'd3333333-3333-3333-3333-333333333333'
  and (select user_id from public.company_routing where company_id = pg_temp.id('co') and request_type = 'questionnaire') = 'd4444444-4444-4444-4444-444444444444'
  and (select user_id from public.company_routing where company_id = pg_temp.id('co') and request_type = 'dossier') = 'd2222222-2222-2222-2222-222222222222'$$);
select pg_temp.as_user('d3333333-3333-3333-3333-333333333333');
select pg_temp.no('a sales member cannot invite', $$select public.company_invite(pg_temp.id('co'), 'cp-invitee@x.test', 'CP Invitee', 'sales')$$, '42501');
select pg_temp.as_user('d2222222-2222-2222-2222-222222222222');
select pg_temp.no('an admin cannot invite an admin', $$select public.company_invite(pg_temp.id('co'), 'cp-invitee@x.test', 'CP Invitee', 'admin')$$, '42501');
select pg_temp.no('nobody is invited as owner', $$select public.company_invite(pg_temp.id('co'), 'cp-invitee@x.test', 'CP Invitee', 'owner')$$, '22023');
select pg_temp.ok('the admin invites a member by e-mail (an account): a pending invitation', $$public.company_invite(pg_temp.id('co'), 'CP-Invitee@X.test', 'CP Invitee', 'regulatory') = 'member'$$);
select pg_temp.ok('an address without an account is kept as an invitation', $$public.company_invite(pg_temp.id('co'), 'new.person@cp.test', 'New Person', 'hr') = 'email'$$);
select pg_temp.ok('the admin sees both in Team', $$(select count(*) from public.company_members where company_id = pg_temp.id('co') and pending = 'invite') = 1 and (select count(*) from public.company_invites where company_id = pg_temp.id('co')) = 1$$);
select pg_temp.as_user('d6666666-6666-6666-6666-666666666666');
select pg_temp.ok('the invitee is notified', $$exists (select 1 from public.notifications where user_id = 'd6666666-6666-6666-6666-666666666666' and type = 'company_invite' and company_id = pg_temp.id('co'))$$);
select pg_temp.ok('a pending invitation gives no access (not a member)', $$not public.is_company_member(pg_temp.id('co'))$$);
select pg_temp.no('the invitee cannot accept by writing the row directly', $$update public.company_members set accepted = true where company_id = pg_temp.id('co') and user_id = 'd6666666-6666-6666-6666-666666666666'$$, '42501');
select pg_temp.ok('the invitee sees the invitation', $$(select json_array_length(public.my_company_invites())) = 1$$);
select pg_temp.step('the invitee accepts', $$select public.company_invite_respond(pg_temp.id('co'), true)$$);
select pg_temp.ok('now a member with the invited role, not shown publicly', $$public.is_company_member(pg_temp.id('co'), array['regulatory']) and (select not show_public from public.company_members where company_id = pg_temp.id('co') and user_id = 'd6666666-6666-6666-6666-666666666666')$$);
select pg_temp.as_server();
select pg_temp.ok('dossiers now go to the regulatory member; the inviter was told', $$(select user_id from public.company_routing where company_id = pg_temp.id('co') and request_type = 'dossier') = 'd6666666-6666-6666-6666-666666666666'
  and exists (select 1 from public.notifications where user_id = 'd2222222-2222-2222-2222-222222222222' and type = 'company_invite_answer')$$);
select pg_temp.step('the address without an account signs up', $$insert into auth.users (id, email) values ('d8888888-8888-8888-8888-888888888888', 'new.person@cp.test');
  insert into public.profiles (id, name) values ('d8888888-8888-8888-8888-888888888888', 'CP New Person') on conflict (id) do update set name = excluded.name$$);
select pg_temp.ok('…and finds the invitation (pending, notified); the address invitation is used up', $$exists (select 1 from public.company_members where company_id = pg_temp.id('co') and user_id = 'd8888888-8888-8888-8888-888888888888' and pending = 'invite' and role = 'hr')
  and exists (select 1 from public.notifications where user_id = 'd8888888-8888-8888-8888-888888888888' and type = 'company_invite') and not exists (select 1 from public.company_invites where email = 'new.person@cp.test')$$);
select pg_temp.as_user('d8888888-8888-8888-8888-888888888888');
select pg_temp.step('the new person declines', $$select public.company_invite_respond(pg_temp.id('co'), false)$$);
select pg_temp.ok('declined: no row', $$not exists (select 1 from public.company_members where company_id = pg_temp.id('co') and user_id = 'd8888888-8888-8888-8888-888888888888')$$);
select pg_temp.no('there is nothing more to answer', $$select public.company_invite_respond(pg_temp.id('co'), true)$$, 'P0002');
-- join requests
select pg_temp.no('asking to join as admin is refused', $$select public.company_join_request(pg_temp.id('co'), 'admin')$$, '22023');
select pg_temp.step('the person asks to join as sales', $$select public.company_join_request(pg_temp.id('co'), 'sales', 'Cairo office')$$);
select pg_temp.ok('a pending request, no access; the owner and the admin are notified', $$not public.is_company_member(pg_temp.id('co'))
  and (select count(*) from public.notifications n where n.type = 'company_join_request' and n.company_id = pg_temp.id('co') and n.from_user = 'd8888888-8888-8888-8888-888888888888') = 0$$);
select pg_temp.as_server();
select pg_temp.ok('…the owner and the admin got the notice', $$(select count(*) from public.notifications n where n.type = 'company_join_request' and n.company_id = pg_temp.id('co') and n.from_user = 'd8888888-8888-8888-8888-888888888888') = 2$$);
select pg_temp.as_user('d8888888-8888-8888-8888-888888888888');
select pg_temp.no('the requester cannot approve himself', $$select public.company_join_decide(pg_temp.id('co'), 'd8888888-8888-8888-8888-888888888888', true)$$, '42501');
select pg_temp.no('…nor by writing the row', $$update public.company_members set accepted = true where company_id = pg_temp.id('co') and user_id = 'd8888888-8888-8888-8888-888888888888'$$, '42501');
select pg_temp.as_user('d5555555-5555-5555-5555-555555555555');
select pg_temp.no('an outsider cannot approve it', $$select public.company_join_decide(pg_temp.id('co'), 'd8888888-8888-8888-8888-888888888888', true)$$, '42501');
select pg_temp.as_user('d2222222-2222-2222-2222-222222222222');
select pg_temp.no('the admin cannot approve with role admin', $$select public.company_join_decide(pg_temp.id('co'), 'd8888888-8888-8888-8888-888888888888', true, 'admin')$$, '42501');
select pg_temp.step('the admin approves as sales', $$select public.company_join_decide(pg_temp.id('co'), 'd8888888-8888-8888-8888-888888888888', true, 'sales')$$);
select pg_temp.as_user('d8888888-8888-8888-8888-888888888888');
select pg_temp.ok('the requester is a sales member and told so', $$public.is_company_member(pg_temp.id('co'), array['sales']) and exists (select 1 from public.notifications where user_id = 'd8888888-8888-8888-8888-888888888888' and type = 'company_join_answer')$$);
select pg_temp.as_user('d5555555-5555-5555-5555-555555555555');
select pg_temp.no('asking to join an unclaimed page is refused (claim it)', $$select public.company_join_request(pg_temp.id('unc'), 'sales')$$, '22023');
select pg_temp.as_anon();
select pg_temp.no('anon cannot invite', $$select public.company_invite(pg_temp.id('co'), 'a@b.c', 'x', 'sales')$$, '42501');
select pg_temp.no('anon cannot ask to join', $$select public.company_join_request(pg_temp.id('co'), 'sales')$$, '42501');
select pg_temp.no('anon cannot read invitations', $$select count(*) from public.company_invites$$, '42501');

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
