-- Company records (0056 deal files + supplier reviews, 0057 group buying, 0058 follower notices + company jobs, 0059 compliance
-- documents, memberships, activity log, e-mail outbox). Runs as the real API roles with a JWT, in one transaction that is rolled
-- back; test data carries the "CR " marker. Run on a fresh database (stub + migrations):
--   psql -f supabase/tests/company_records.rls.sql
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

-- people: buyer owner (company A), supplier owner (company B), supplier sales, supplier quality, supplier regulatory, an outsider, a moderator
insert into auth.users (id, email) values ('e1111111-1111-1111-1111-111111111111','cr-buyer@x.test'),('e2222222-2222-2222-2222-222222222222','cr-supplier@x.test'),
  ('e3333333-3333-3333-3333-333333333333','cr-sales@x.test'),('e4444444-4444-4444-4444-444444444444','cr-quality@x.test'),('e5555555-5555-5555-5555-555555555555','cr-out@x.test'),
  ('e6666666-6666-6666-6666-666666666666','cr-reg@x.test'),('e7777777-7777-7777-7777-777777777777','cr-mod@x.test'),('e8888888-8888-8888-8888-888888888888','cr-reviewer@x.test') on conflict do nothing;
insert into public.profiles (id, name) values ('e1111111-1111-1111-1111-111111111111','CR Buyer'),('e2222222-2222-2222-2222-222222222222','CR Supplier'),
  ('e3333333-3333-3333-3333-333333333333','CR Sales'),('e4444444-4444-4444-4444-444444444444','CR Quality'),('e5555555-5555-5555-5555-555555555555','CR Outsider'),
  ('e6666666-6666-6666-6666-666666666666','CR Regulatory'),('e7777777-7777-7777-7777-777777777777','CR Moderator'),('e8888888-8888-8888-8888-888888888888','CR Reviewer') on conflict (id) do update set name = excluded.name;
update public.profiles set role = 'admin' where id = 'e7777777-7777-7777-7777-777777777777';
update public.profiles set role = 'moderator' where id = 'e8888888-8888-8888-8888-888888888888';   -- a Drugbox reviewer who is not an admin

select pg_temp.as_server();
select pg_temp.step('a buyer company, a supplier company with sales / quality / regulatory, an outsider company; a quote deal and a rated order', $$
  with x as (insert into public.companies (owner_id, name, slug, type, status) values ('e1111111-1111-1111-1111-111111111111', 'CR Buyer Co', 'cr-buyer-co', 'Distributor', 'verified') returning id) insert into ids select 'a', id::text from x;
  with x as (insert into public.companies (owner_id, name, slug, type, status) values ('e2222222-2222-2222-2222-222222222222', 'CR Supplier Co', 'cr-supplier-co', 'Manufacturer', 'verified') returning id) insert into ids select 'b', id::text from x;
  with x as (insert into public.companies (owner_id, name, slug, type, status) values ('e5555555-5555-5555-5555-555555555555', 'CR Outside Co', 'cr-outside-co', 'Distributor', 'verified') returning id) insert into ids select 'o', id::text from x;
  insert into public.company_members (company_id, user_id, role, accepted, show_public) values (pg_temp.id('b'), 'e3333333-3333-3333-3333-333333333333', 'sales', true, true),
    (pg_temp.id('b'), 'e4444444-4444-4444-4444-444444444444', 'quality', true, false), (pg_temp.id('b'), 'e6666666-6666-6666-6666-666666666666', 'regulatory', true, false);
  with x as (insert into public.deals (ref, type, title, from_company_id, from_user, to_company_id, status) values ('CRDEAL1', 'quote', 'CR Paracetamol quote', pg_temp.id('a'), 'e1111111-1111-1111-1111-111111111111', pg_temp.id('b'), 'open') returning id) insert into ids select 'd1', id::text from x;
  with x as (insert into public.deals (ref, type, title, from_company_id, from_user, to_company_id, status) values ('CRDEAL2', 'quote', 'CR Rated order', pg_temp.id('a'), 'e1111111-1111-1111-1111-111111111111', pg_temp.id('b'), 'completed') returning id) insert into ids select 'd2', id::text from x;
  insert into public.deal_events (deal_id, side, action, note, data, actor) values (pg_temp.id('d2'), 'from', 'rate', 'Late delivery', '{"stars": 2, "note": "Late delivery"}', 'e1111111-1111-1111-1111-111111111111');
  insert into storage.objects (bucket_id, name, owner) values ('documents', 'deals/' || pg_temp.id('d1') || '/po-1.pdf', 'e1111111-1111-1111-1111-111111111111'),
    ('documents', 'deals/' || pg_temp.id('d1') || '/coa-1.pdf', 'e5555555-5555-5555-5555-555555555555'),
    ('documents', 'companydocs/' || pg_temp.id('b') || '/cep-1.pdf', 'e6666666-6666-6666-6666-666666666666'),
    ('documents', 'companydocs/' || pg_temp.id('o') || '/x.pdf', 'e5555555-5555-5555-5555-555555555555')$$);

-- ══ 0056: deal files ══
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.ok('the buyer attaches a PO they uploaded to the deal''s folder', $$public.deal_attach('CRDEAL1', 'PO', 'deals/' || pg_temp.id('d1') || '/po-1.pdf', 'po.pdf') > 0$$);
select pg_temp.ok('…it is a deal event the supplier side is told about', $$(select count(*) from public.deal_events where deal_id = pg_temp.id('d1') and action = 'file') = 1$$);
select pg_temp.no('a file uploaded by someone else cannot be attached', $$select public.deal_attach('CRDEAL1', 'CoA', 'deals/' || pg_temp.id('d1') || '/coa-1.pdf', 'coa.pdf')$$, '42501');
select pg_temp.no('a path outside the deal''s folder is refused', $$select public.deal_attach('CRDEAL1', 'PO', 'companydocs/' || pg_temp.id('b') || '/cep-1.pdf', 'x.pdf')$$, '42501');
select pg_temp.ok('the buyer reads the file list', $$(select count(*) from public.deal_files where deal_id = pg_temp.id('d1')) = 1$$);
select pg_temp.no('nobody writes deal_files directly', $$insert into public.deal_files (deal_id, side, kind, name, path) values (pg_temp.id('d1'), 'from', 'PO', 'x', 'deals/x/y.pdf')$$, '42501');
select pg_temp.as_user('e3333333-3333-3333-3333-333333333333');
select pg_temp.ok('the supplier''s sales member reads the file and may open it', $$(select count(*) from public.deal_files where deal_id = pg_temp.id('d1')) = 1 and public.can_read_document('deals/' || pg_temp.id('d1') || '/po-1.pdf')$$);
select pg_temp.as_user('e5555555-5555-5555-5555-555555555555');
select pg_temp.ok('an outsider sees no file of the deal', $$(select count(*) from public.deal_files where deal_id = pg_temp.id('d1')) = 0$$);
select pg_temp.ok('…and may not open it', $$not public.can_read_document('deals/' || pg_temp.id('d1') || '/po-1.pdf')$$);
select pg_temp.no('…nor attach to it', $$select public.deal_attach('CRDEAL1', 'CoA', 'deals/' || pg_temp.id('d1') || '/coa-1.pdf', 'coa.pdf')$$, '42501');
select pg_temp.ok('…nor upload into its folder', $$not public.can_write_document('deals/' || pg_temp.id('d1') || '/new.pdf')$$);

-- ══ 0056: supplier reviews ══
select pg_temp.as_user('e5555555-5555-5555-5555-555555555555');
select pg_temp.no('an outsider cannot reply to a review of the supplier', $$select public.review_reply('CRDEAL2', 'Not us')$$, '42501');
select pg_temp.as_user('e4444444-4444-4444-4444-444444444444');
select pg_temp.no('the supplier''s quality member cannot reply (owner, admins, management or sales only)', $$select public.review_reply('CRDEAL2', 'Sorry')$$, '42501');
select pg_temp.as_user('e3333333-3333-3333-3333-333333333333');
select pg_temp.ok('the supplier''s sales member replies publicly', $$public.review_reply('CRDEAL2', 'CR We changed carriers')$$);
select pg_temp.ok('…the reply shows with the review', $$(select (public.company_reviews(pg_temp.id('b'))::jsonb -> 0 ->> 'reply')) = 'CR We changed carriers'$$);
select pg_temp.no('sales cannot ask Drugbox to check the review (owner / admins only)', $$select public.review_dispute('CRDEAL2', 'unfair')$$, '42501');
select pg_temp.no('members cannot read the dispute table', $$select 1/(count(*)-count(*)) from public.review_responses$$, '22012');
select pg_temp.as_user('e2222222-2222-2222-2222-222222222222');
select pg_temp.ok('the supplier''s owner asks Drugbox to check it', $$public.review_dispute('CRDEAL2', 'CR The delay was customs')$$);
select pg_temp.no('the owner cannot decide it', $$select public.review_decide('CRDEAL2', false)$$, '42501');
select pg_temp.ok('the dispute queue is empty for a non-moderator', $$public.review_disputes()::jsonb = '[]'::jsonb$$);
select pg_temp.as_user('e7777777-7777-7777-7777-777777777777');
select pg_temp.ok('Drugbox sees the disputed review in its queue', $$jsonb_array_length(public.review_disputes()::jsonb) >= 1$$);
select pg_temp.ok('Drugbox removes it', $$public.review_decide('CRDEAL2', false, 'Customs delay documented')$$);
select pg_temp.ok('…deciding twice changes nothing', $$not public.review_decide('CRDEAL2', true)$$);
select pg_temp.as_user('e5555555-5555-5555-5555-555555555555');
select pg_temp.ok('a removed review is no longer on the page', $$public.company_reviews(pg_temp.id('b'))::jsonb = '[]'::jsonb$$);
select pg_temp.as_server();
select pg_temp.ok('the buyer and the supplier owner each got the decision', $$(select count(distinct user_id) from public.notifications where type = 'review_decided' and company_id = pg_temp.id('b')) = 2$$);

-- ══ 0057: group buying ══
select pg_temp.step('an open buying group organised by A at B with A and O as members; an expired one', $$
  with x as (insert into public.deals (ref, type, title, from_company_id, from_user, to_company_id, status, lines) values ('CRGRP1', 'group', 'CR group', pg_temp.id('a'), 'e1111111-1111-1111-1111-111111111111', pg_temp.id('b'), 'open', '{"target": 1000, "unit": "kg"}') returning id) insert into ids select 'g1', id::text from x;
  insert into public.deal_members (deal_id, company_id, qty) values (pg_temp.id('g1'), pg_temp.id('a'), 300), (pg_temp.id('g1'), pg_temp.id('o'), 200);
  with x as (insert into public.deals (ref, type, title, from_company_id, from_user, to_company_id, status, lines) values ('CRGRP2', 'group', 'CR old group', pg_temp.id('a'), 'e1111111-1111-1111-1111-111111111111', pg_temp.id('b'), 'open', jsonb_build_object('target', 1000, 'unit', 'kg', 'by', (current_date - 3)::text)) returning id) insert into ids select 'g2', id::text from x;
  insert into public.deal_members (deal_id, company_id, qty) values (pg_temp.id('g2'), pg_temp.id('a'), 100)$$);
select pg_temp.as_user('e5555555-5555-5555-5555-555555555555');
select pg_temp.ok('a member changes its own share', $$(public.deal_member_set('CRGRP1', 'cr-outside-co', 250)).id = pg_temp.id('g1')$$);
select pg_temp.ok('…the new share is kept', $$(select qty from public.deal_members where deal_id = pg_temp.id('g1') and company_id = pg_temp.id('o')) = 250$$);
select pg_temp.no('…but never another company''s share', $$select public.deal_member_set('CRGRP1', 'cr-buyer-co', 0)$$, '42501');
select pg_temp.ok('a member leaves with 0', $$(public.deal_member_set('CRGRP1', 'cr-outside-co', 0)).id > 0$$);
select pg_temp.ok('…and is no longer in the group', $$not exists (select 1 from public.deal_members where deal_id = pg_temp.id('g1') and company_id = pg_temp.id('o'))$$);
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.no('the organiser cannot leave its own group', $$select public.deal_member_set('CRGRP1', 'cr-buyer-co', 0)$$, '42501');
select pg_temp.no('a negative quantity is refused', $$select public.deal_member_set('CRGRP1', 'cr-buyer-co', -5)$$, '22023');
select pg_temp.ok('a group past its date below target closes as expired', $$public.group_close_expired('CRGRP2') = 'expired'$$);
select pg_temp.ok('…its status is expired', $$(select status from public.deals where id = pg_temp.id('g2')) = 'expired'$$);
select pg_temp.no('…and nobody changes shares in it any more', $$select public.deal_member_set('CRGRP2', 'cr-buyer-co', 500)$$, '42501');
select pg_temp.ok('an open group with time left stays open', $$public.group_close_expired('CRGRP1') = 'open'$$);
select pg_temp.as_anon();
select pg_temp.no('the signed-out visitor cannot call it', $$select public.group_close_expired('CRGRP1')$$, '42501');

-- ══ 0058: company jobs ══
select pg_temp.as_anon();
select pg_temp.no('company_jobs is for signed-in members', $$select public.company_jobs(1)$$, '42501');

-- ══ 0059: compliance documents ══
select pg_temp.as_user('e6666666-6666-6666-6666-666666666666');
select pg_temp.step('the regulatory member adds a CEP with its file', $$
  with x as (insert into public.company_documents (company_id, type, product, number, file_path, file_name, created_by) values (pg_temp.id('b'), 'CEP', 'Metformin', 'R1-CEP 2019-1', 'companydocs/' || pg_temp.id('b') || '/cep-1.pdf', 'cep.pdf', 'e6666666-6666-6666-6666-666666666666') returning id) insert into ids select 'doc1', id::text from x$$);
select pg_temp.ok('…it waits for Drugbox (review), with who added it', $$(select status || '|' || created_by from public.company_documents where id = pg_temp.id('doc1')) = 'review|e6666666-6666-6666-6666-666666666666'$$);
select pg_temp.no('a member cannot mark a document verified', $$update public.company_documents set status = 'verified' where id = pg_temp.id('doc1')$$, '42501');
select pg_temp.no('…nor write Drugbox''s review note', $$update public.company_documents set review_note = 'ok' where id = pg_temp.id('doc1')$$, '42501');
select pg_temp.no('a file of another company is refused', $$insert into public.company_documents (company_id, type, number, file_path, created_by) values (pg_temp.id('b'), 'CEP', 'R1-X', 'companydocs/' || pg_temp.id('o') || '/x.pdf', 'e6666666-6666-6666-6666-666666666666')$$, '42501');
select pg_temp.no('a file that was never uploaded is refused', $$insert into public.company_documents (company_id, type, number, file_path, created_by) values (pg_temp.id('b'), 'CEP', 'R1-X', 'companydocs/' || pg_temp.id('b') || '/none.pdf', 'e6666666-6666-6666-6666-666666666666')$$, '42501');
select pg_temp.ok('the team lists the files', $$(select count(*) from public.company_document_files(pg_temp.id('b'))) = 1$$);
select pg_temp.as_user('e3333333-3333-3333-3333-333333333333');
select pg_temp.ok('a sales member of the team reads the file too', $$(select file_name from public.company_document_files(pg_temp.id('b'))) = 'cep.pdf' and public.can_read_document('companydocs/' || pg_temp.id('b') || '/cep-1.pdf')$$);
select pg_temp.ok('…but cannot upload company documents', $$not public.can_write_document('companydocs/' || pg_temp.id('b') || '/new.pdf')$$);
select pg_temp.no('…nor add one', $$insert into public.company_documents (company_id, type, number, created_by) values (pg_temp.id('b'), 'ISO 9001', 'ISO-1', 'e3333333-3333-3333-3333-333333333333')$$, '42501');
select pg_temp.as_user('e5555555-5555-5555-5555-555555555555');
select pg_temp.ok('an outsider sees the passport line (type, number, status)', $$(select status from public.company_documents where id = pg_temp.id('doc1')) = 'review'$$);
select pg_temp.no('…not the file columns', $$select file_path from public.company_documents where id = pg_temp.id('doc1')$$, '42501');
select pg_temp.ok('…no file list', $$(select count(*) from public.company_document_files(pg_temp.id('b'))) = 0$$);
select pg_temp.ok('…no signed link', $$not public.can_read_document('companydocs/' || pg_temp.id('b') || '/cep-1.pdf')$$);
select pg_temp.ok('…nothing in the review queue', $$(select count(*) from public.documents_to_review(100)) = 0$$);
select pg_temp.no('…and cannot review it', $$select public.document_review(pg_temp.id('doc1'), true)$$, '42501');
select pg_temp.step('the outsider tries to delete it', $$delete from public.company_documents where id = pg_temp.id('doc1')$$);
select pg_temp.as_server();
select pg_temp.ok('…nor delete it (still there)', $$exists (select 1 from public.company_documents where id = pg_temp.id('doc1'))$$);
select pg_temp.as_user('e5555555-5555-5555-5555-555555555555');
select pg_temp.as_anon();
select pg_temp.ok('the signed-out visitor reads nothing', $$(select count(*) from public.company_documents) = 0$$);
select pg_temp.as_user('e7777777-7777-7777-7777-777777777777');
select pg_temp.ok('Drugbox finds it in Compliance documents with its file', $$(select file_path from public.documents_to_review(100) where id = pg_temp.id('doc1')) = 'companydocs/' || pg_temp.id('b') || '/cep-1.pdf'$$);
select pg_temp.no('a rejection needs a reason', $$select public.document_review(pg_temp.id('doc1'), false, '')$$, '22023');
select pg_temp.ok('Drugbox verifies it', $$public.document_review(pg_temp.id('doc1'), true)$$);
select pg_temp.ok('…deciding twice changes nothing', $$not public.document_review(pg_temp.id('doc1'), false, 'late')$$);
select pg_temp.as_server();
select pg_temp.ok('…the person who added it is told', $$(select count(*) from public.notifications where user_id = 'e6666666-6666-6666-6666-666666666666' and type = 'document_reviewed') = 1$$);
select pg_temp.as_user('e6666666-6666-6666-6666-666666666666');
select pg_temp.step('the regulatory member changes the verified document''s number', $$update public.company_documents set number = 'R1-CEP 2019-2' where id = pg_temp.id('doc1')$$);
select pg_temp.ok('changing a verified document sends it back to review', $$(select status from public.company_documents where id = pg_temp.id('doc1')) = 'review'$$);
select pg_temp.step('…a membership is added (no file)', $$
  with x as (insert into public.company_documents (company_id, type, product, number, created_by) values (pg_temp.id('b'), 'Membership', 'Export Council for Medical Industries', 'EC-1', 'e6666666-6666-6666-6666-666666666666') returning id) insert into ids select 'mem', id::text from x$$);
select pg_temp.ok('a membership always waits for Drugbox', $$(select status from public.company_documents where id = pg_temp.id('mem')) = 'review'$$);
select pg_temp.step('the person who added it deletes it', $$delete from public.company_documents where id = pg_temp.id('doc1')$$);
select pg_temp.ok('the person who added a document may take it back', $$not exists (select 1 from public.company_documents where id = pg_temp.id('doc1'))$$);
select pg_temp.as_server();
select pg_temp.ok('…the file is gone from storage', $$not exists (select 1 from storage.objects where bucket_id = 'documents' and name = 'companydocs/' || pg_temp.id('b') || '/cep-1.pdf')$$);

-- ══ 0059: a file behind a record cannot be swapped; Drugbox's decision is not undone; reviewers who are not admins ══
select pg_temp.as_server();
select pg_temp.step('a second CEP with its file (uploaded by the regulatory member), a certificate with its file, a deal file', $$
  insert into storage.objects (bucket_id, name, owner) values ('documents', 'companydocs/' || pg_temp.id('b') || '/cep-2.pdf', 'e6666666-6666-6666-6666-666666666666'),
    ('documents', 'verification/' || pg_temp.id('b') || '/cert-gmp.pdf', 'e4444444-4444-4444-4444-444444444444'), ('documents', 'deals/' || pg_temp.id('d1') || '/spec-2.pdf', 'e1111111-1111-1111-1111-111111111111');
  with x as (insert into public.company_documents (company_id, type, product, number, file_path, file_name, created_by) values (pg_temp.id('b'), 'CEP', 'Ibuprofen', 'R1-CEP 2020-7', 'companydocs/' || pg_temp.id('b') || '/cep-2.pdf', 'cep2.pdf', 'e6666666-6666-6666-6666-666666666666') returning id) insert into ids select 'doc2', id::text from x;
  update public.company_documents set status = 'review' where id = pg_temp.id('doc2');
  with x as (insert into public.site_certificates (company_id, name, expiry, file_path) values (pg_temp.id('b'), 'WHO-GMP', current_date + 300, 'verification/' || pg_temp.id('b') || '/cert-gmp.pdf') returning id) insert into ids select 'cert', id::text from x$$);
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.ok('the buyer attaches the spec', $$public.deal_attach('CRDEAL1', 'Specification', 'deals/' || pg_temp.id('d1') || '/spec-2.pdf', 'spec.pdf') > 0$$);
select pg_temp.as_user('e8888888-8888-8888-8888-888888888888');
select pg_temp.ok('a Drugbox reviewer (moderator, not admin) verifies a document', $$public.document_review(pg_temp.id('doc2'), true)$$);
select pg_temp.ok('…and checks a certificate', $$public.review_certificate(pg_temp.id('cert'), true)$$);
select pg_temp.as_server();
select pg_temp.ok('…both decisions are stored (verified; checked)', $$(select status from public.company_documents where id = pg_temp.id('doc2')) = 'verified'
  and (select checked_at is not null from public.site_certificates where id = pg_temp.id('cert'))$$);
select pg_temp.as_user('e3333333-3333-3333-3333-333333333333');
select pg_temp.step('the supplier''s sales member tries to delete the buyer''s attached file', $$delete from storage.objects where bucket_id = 'documents' and name = 'deals/' || pg_temp.id('d1') || '/spec-2.pdf'$$);
select pg_temp.as_user('e2222222-2222-2222-2222-222222222222');
select pg_temp.step('the owner tries to delete the verified document''s file and the checked certificate''s file', $$delete from storage.objects where bucket_id = 'documents' and name in ('companydocs/' || pg_temp.id('b') || '/cep-2.pdf', 'verification/' || pg_temp.id('b') || '/cert-gmp.pdf')$$);
select pg_temp.as_user('e6666666-6666-6666-6666-666666666666');
select pg_temp.step('even the uploader tries to delete the verified document''s file', $$delete from storage.objects where bucket_id = 'documents' and name = 'companydocs/' || pg_temp.id('b') || '/cep-2.pdf'$$);
select pg_temp.as_server();
select pg_temp.ok('no file behind a record can be removed (so none can be swapped): deal file, verified document, checked certificate', $$
  (select count(*) from storage.objects where bucket_id = 'documents' and name in ('deals/' || pg_temp.id('d1') || '/spec-2.pdf', 'companydocs/' || pg_temp.id('b') || '/cep-2.pdf', 'verification/' || pg_temp.id('b') || '/cert-gmp.pdf')) = 3$$);
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.no('…and a new upload under the same name is refused', $$insert into storage.objects (bucket_id, name, owner) values ('documents', 'deals/' || pg_temp.id('d1') || '/spec-2.pdf', 'e1111111-1111-1111-1111-111111111111')$$, '23505');
select pg_temp.as_server();
select pg_temp.step('an unattached upload of the buyer', $$insert into storage.objects (bucket_id, name, owner) values ('documents', 'deals/' || pg_temp.id('d1') || '/draft.pdf', 'e1111111-1111-1111-1111-111111111111')$$);
select pg_temp.as_user('e3333333-3333-3333-3333-333333333333');
select pg_temp.step('the other side tries to delete it', $$delete from storage.objects where bucket_id = 'documents' and name = 'deals/' || pg_temp.id('d1') || '/draft.pdf'$$);
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.step('the buyer deletes their own unattached upload', $$delete from storage.objects where bucket_id = 'documents' and name = 'deals/' || pg_temp.id('d1') || '/draft.pdf'$$);
select pg_temp.as_server();
select pg_temp.ok('only the uploader removed the unattached file', $$not exists (select 1 from storage.objects where bucket_id = 'documents' and name = 'deals/' || pg_temp.id('d1') || '/draft.pdf')$$);
select pg_temp.step('Drugbox rejects the membership', $$update public.company_documents set status = 'rejected', review_note = 'Not on the council''s list' where id = pg_temp.id('mem')$$);
select pg_temp.as_user('e2222222-2222-2222-2222-222222222222');
select pg_temp.no('the company cannot undo a rejection', $$update public.company_documents set status = 'declared' where id = pg_temp.id('mem')$$, '42501');
select pg_temp.no('…nor take a document out of Drugbox''s queue', $$update public.company_documents set status = 'declared' where id = pg_temp.id('doc2')$$, '42501');
select pg_temp.as_user('e4444444-4444-4444-4444-444444444444');
select pg_temp.step('the quality member tries to make the CEP theirs', $$update public.company_documents set created_by = 'e4444444-4444-4444-4444-444444444444' where id = pg_temp.id('doc2')$$);
select pg_temp.as_server();
select pg_temp.ok('…who added a document never changes', $$(select created_by from public.company_documents where id = pg_temp.id('doc2')) = 'e6666666-6666-6666-6666-666666666666'$$);

-- a Drugbox reviewer who also runs a company gets no shortcut for it: only the review functions act as Drugbox
select pg_temp.as_server();
select pg_temp.step('the reviewer owns a company of their own', $$
  with x as (insert into public.companies (owner_id, name, slug, type, status) values ('e8888888-8888-8888-8888-888888888888', 'CR Reviewer Co', 'cr-reviewer-co', 'Distributor', 'verified') returning id) insert into ids select 'rc', id::text from x;
  insert into storage.objects (bucket_id, name, owner) values ('documents', 'companydocs/' || pg_temp.id('rc') || '/own.pdf', 'e8888888-8888-8888-8888-888888888888')$$);
select pg_temp.as_user('e8888888-8888-8888-8888-888888888888');
select pg_temp.no('the reviewer cannot add their own company''s document as verified', $$insert into public.company_documents (company_id, type, number, file_path, created_by, status) values (pg_temp.id('rc'), 'GDP certificate', 'GDP-1', 'companydocs/' || pg_temp.id('rc') || '/own.pdf', 'e8888888-8888-8888-8888-888888888888', 'verified')$$, '42501');
select pg_temp.no('…nor point their document at another company''s file (and delete it with the row)', $$insert into public.company_documents (company_id, type, number, file_path, created_by) values (pg_temp.id('rc'), 'CEP', 'CEP-X', 'companydocs/' || pg_temp.id('b') || '/cep-2.pdf', 'e8888888-8888-8888-8888-888888888888')$$, '42501');
select pg_temp.step('the reviewer adds their own document properly', $$
  with x as (insert into public.company_documents (company_id, type, number, file_path, created_by) values (pg_temp.id('rc'), 'GDP certificate', 'GDP-1', 'companydocs/' || pg_temp.id('rc') || '/own.pdf', 'e8888888-8888-8888-8888-888888888888') returning id) insert into ids select 'rdoc', id::text from x$$);
select pg_temp.no('…and cannot mark it verified directly', $$update public.company_documents set status = 'verified' where id = pg_temp.id('rdoc')$$, '42501');

-- an invitation cancelled and sent again does not notify again (one notice a week per person and company)
select pg_temp.as_user('e2222222-2222-2222-2222-222222222222');
select pg_temp.step('the supplier invites the outsider, cancels, invites again — three rounds', $$
  select public.company_invite(pg_temp.id('b'), 'cr-out@x.test', 'CR Outsider', 'sales');
  delete from public.company_members where company_id = pg_temp.id('b') and user_id = 'e5555555-5555-5555-5555-555555555555';
  select public.company_invite(pg_temp.id('b'), 'cr-out@x.test', 'CR Outsider', 'sales');
  delete from public.company_members where company_id = pg_temp.id('b') and user_id = 'e5555555-5555-5555-5555-555555555555';
  select public.company_invite(pg_temp.id('b'), 'cr-out@x.test', 'CR Outsider', 'sales')$$);
select pg_temp.as_server();
select pg_temp.ok('…one invitation notice only', $$(select count(*) from public.notifications where user_id = 'e5555555-5555-5555-5555-555555555555' and type = 'company_invite' and company_id = pg_temp.id('b')) = 1$$);

-- ══ 0059: activity log ══
select pg_temp.as_user('e3333333-3333-3333-3333-333333333333');
select pg_temp.step('a team member writes an activity entry as themselves', $$insert into public.company_activity (company_id, actor, text) values (pg_temp.id('b'), 'e3333333-3333-3333-3333-333333333333', 'CR Sent a quote')$$);
select pg_temp.no('…never as someone else', $$insert into public.company_activity (company_id, actor, text) values (pg_temp.id('b'), 'e2222222-2222-2222-2222-222222222222', 'CR forged')$$, '42501');
select pg_temp.no('…never edits it afterwards', $$update public.company_activity set text = 'x' where company_id = pg_temp.id('b')$$, '42501');
select pg_temp.as_user('e2222222-2222-2222-2222-222222222222');
select pg_temp.ok('the owner reads the team''s log', $$(select count(*) from public.company_activity where company_id = pg_temp.id('b')) = 1$$);
select pg_temp.as_user('e5555555-5555-5555-5555-555555555555');
select pg_temp.ok('an outsider reads nothing of it', $$(select count(*) from public.company_activity where company_id = pg_temp.id('b')) = 0$$);
select pg_temp.no('…and cannot write into it', $$insert into public.company_activity (company_id, actor, text) values (pg_temp.id('b'), 'e5555555-5555-5555-5555-555555555555', 'CR forged')$$, '42501');

-- ══ 0059: e-mail outbox ══
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.no('a member cannot read the queue', $$select 1/(count(*)-count(*)) from public.notification_outbox$$, '22012');
select pg_temp.no('…nor claim a batch', $$select * from public.outbox_claim(5)$$, '42501');
select pg_temp.no('…nor mark one sent', $$select public.outbox_done(1, true)$$, '42501');
select pg_temp.step('a member turns their e-mails off', $$insert into public.notification_prefs (user_id, email) values ('e1111111-1111-1111-1111-111111111111', false)$$);
select pg_temp.ok('a member sets their own e-mail preference', $$(select email from public.notification_prefs where user_id = 'e1111111-1111-1111-1111-111111111111') = false$$);
select pg_temp.no('…not someone else''s', $$insert into public.notification_prefs (user_id, email) values ('e2222222-2222-2222-2222-222222222222', false)$$, '42501');
select pg_temp.as_server();
select pg_temp.step('notices: a deal for the person who opted out, a deal and a like for another', $$
  with n as (insert into public.notifications (user_id, type, data) values ('e1111111-1111-1111-1111-111111111111', 'deal', '{"cr":1}') returning id) insert into ids select 'n1', id::text from n;
  with n as (insert into public.notifications (user_id, type, data) values ('e2222222-2222-2222-2222-222222222222', 'deal', '{"cr":1}') returning id) insert into ids select 'n2', id::text from n;
  with n as (insert into public.notifications (user_id, type, data) values ('e2222222-2222-2222-2222-222222222222', 'like', '{"cr":1}') returning id) insert into ids select 'n3', id::text from n$$);
select pg_temp.ok('nothing is queued for someone who turned e-mails off', $$not exists (select 1 from public.notification_outbox where notification_id = pg_temp.id('n1'))$$);
select pg_temp.ok('a business notice is queued for the others', $$exists (select 1 from public.notification_outbox where notification_id = pg_temp.id('n2') and status = 'pending')$$);
select pg_temp.ok('a like is not', $$not exists (select 1 from public.notification_outbox where notification_id = pg_temp.id('n3'))$$);

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
