-- Listings and group buying (0008 + 0021): posting rights, joins, target reached, member orders created by the database, AVL from an
-- approved questionnaire; outsider and anonymous visitor. Runs as the real API roles with a JWT, in one transaction that is rolled back;
-- test data carries the "LG " marker and assertions are scoped to it. Run on a fresh database (stub + migrations): psql -f supabase/tests/listings_groups.rls.sql
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

create function pg_temp.g() returns text language sql stable as $$ select v from ids where k = 'group' $$;

insert into auth.users (id, email) values ('11111111-aaaa-0000-0000-000000000001','lg-org@x'),('22222222-aaaa-0000-0000-000000000002','lg-member@x'),('33333333-aaaa-0000-0000-000000000003','lg-sup@x'),('44444444-aaaa-0000-0000-000000000004','lg-out@x') on conflict do nothing;
insert into public.profiles (id, name) values ('11111111-aaaa-0000-0000-000000000001','LG Organiser'),('22222222-aaaa-0000-0000-000000000002','LG Member'),('33333333-aaaa-0000-0000-000000000003','LG Supplier'),('44444444-aaaa-0000-0000-000000000004','LG Outsider') on conflict (id) do nothing;
select pg_temp.as_user('11111111-aaaa-0000-0000-000000000001');
select pg_temp.step('the organiser creates its company', $$insert into public.companies (name, type, slug) values ('LG Org Pharma','Manufacturer','lg-org-pharma')$$);
select pg_temp.as_user('22222222-aaaa-0000-0000-000000000002');
select pg_temp.step('the member creates its company', $$insert into public.companies (name, type, slug) values ('LG Member Labs','Manufacturer','lg-member-labs')$$);
select pg_temp.as_user('33333333-aaaa-0000-0000-000000000003');
select pg_temp.step('the supplier creates its company', $$insert into public.companies (name, type, slug) values ('LG Big API','Supplier','lg-big-api')$$);
-- listings
select pg_temp.step('the supplier posts its surplus', $$insert into public.company_listings (company_id, kind, product, qty, price, off, created_by) select id, 'surplus', 'LG MCC PH-101', '750 kg', 'US$ 2.40/kg', 30, '33333333-aaaa-0000-0000-000000000003' from public.companies where slug = 'lg-big-api'$$);
select pg_temp.ok('a company posts its surplus', $$(select count(*) = 1 from public.company_listings where product = 'LG MCC PH-101')$$);
select pg_temp.as_user('44444444-aaaa-0000-0000-000000000004');
select pg_temp.ok('everyone signed in can see listings', $$(select count(*) = 1 from public.company_listings where product = 'LG MCC PH-101')$$);
select pg_temp.no('cannot post a listing for a company you do not belong to', $$insert into public.company_listings (company_id, kind, product, created_by) select id, 'surplus', 'LG Fake', '44444444-aaaa-0000-0000-000000000004' from public.companies where slug = 'lg-big-api'$$, '42501');
select pg_temp.as_anon();
select pg_temp.no('anon cannot post a listing', $$insert into public.company_listings (company_id, kind, product, created_by) select id, 'surplus', 'LG Anon', '44444444-aaaa-0000-0000-000000000004' from public.companies where slug = 'lg-big-api'$$, '42501');
-- group buying
select pg_temp.as_user('11111111-aaaa-0000-0000-000000000001');
select pg_temp.step('the organiser opens a group with its share', $$
  insert into ids select 'group', (public.deal_create('group','lg-big-api','lg-org-pharma','LG Group buy — Metformin HCl','{"product":"LG Metformin HCl","target":1000,"unit":"kg","price":"US$ 5.10/kg","by":"2099-12-31"}','Buying group opened')).ref;
  select public.deal_join(pg_temp.g(), 'lg-org-pharma', 400)$$);
select pg_temp.ok('the organiser opens a group with its share (open, 400 of 1000)',
  $$(select status = 'open' from public.deals where ref = pg_temp.g()) and (select sum(m.qty) = 400 from public.deal_members m join public.deals d on d.id = m.deal_id where d.ref = pg_temp.g())$$);
select pg_temp.as_user('44444444-aaaa-0000-0000-000000000004');
select pg_temp.ok('any signed-in person can see the buying group', $$(select count(*) = 1 from public.deals where ref = pg_temp.g())$$);
select pg_temp.no('cannot join without belonging to a company', $$select public.deal_join(pg_temp.g(), 'lg-member-labs', 100)$$, '42501');
select pg_temp.as_anon();
select pg_temp.no('anon cannot join a group', $$select public.deal_join(pg_temp.g(), 'lg-member-labs', 100)$$, '42501');
select pg_temp.as_user('33333333-aaaa-0000-0000-000000000003');
select pg_temp.no('the supplier cannot join its own group', $$select public.deal_join(pg_temp.g(), 'lg-big-api', 100)$$, '42501');
select pg_temp.no('the supplier cannot confirm before the target is reached', $$select public.deal_act(pg_temp.g(), 'confirm_group', '{}', 'to')$$, '42501');
select pg_temp.as_user('22222222-aaaa-0000-0000-000000000002');
select pg_temp.no('a zero share is refused', $$select public.deal_join(pg_temp.g(), 'lg-member-labs', 0)$$, '22023');
select pg_temp.step('a member joins with 700', $$select public.deal_join(pg_temp.g(), 'lg-member-labs', 700)$$);
select pg_temp.ok('a member joins with 700 → target reached (1,100 of 1,000)', $$(select status = 'target_reached' from public.deals where ref = pg_temp.g())$$);
select pg_temp.no('joining after the target is reached is refused', $$select public.deal_join(pg_temp.g(), 'lg-member-labs', 50)$$, '42501');
select pg_temp.as_user('33333333-aaaa-0000-0000-000000000003');
select pg_temp.ok('the supplier is notified that the target was reached', $$exists (select 1 from public.notifications where user_id = '33333333-aaaa-0000-0000-000000000003' and message = 'Buying group reached its target: LG Group buy — Metformin HCl')$$);
select pg_temp.step('the supplier confirms the group price', $$select public.deal_act(pg_temp.g(), 'confirm_group', '{}', 'to')$$);
select pg_temp.ok('the supplier confirms the group price', $$(select status = 'confirmed' from public.deals where ref = pg_temp.g())$$);
select pg_temp.ok('the database creates one accepted order per member at the group price',
  $$(select count(*) = 2 from public.deals where group_of = (select id from public.deals where ref = pg_temp.g()) and status = 'accepted' and offer ->> 'price' = 'US$ 5.10/kg')$$);
select pg_temp.as_user('22222222-aaaa-0000-0000-000000000002');
select pg_temp.ok('each member sees its own order (700 kg)', $$exists (select 1 from public.deals where title = 'LG Metformin HCl — 700 kg (group order)' and status = 'accepted')$$);
select pg_temp.ok('…and not the other member''s order', $$not exists (select 1 from public.deals where title = 'LG Metformin HCl — 400 kg (group order)')$$);
-- questionnaire approval → AVL
select pg_temp.as_user('11111111-aaaa-0000-0000-000000000001');
select pg_temp.step('the organiser sends a questionnaire', $$insert into ids select 'qn', (public.deal_create('questionnaire','lg-big-api','lg-org-pharma','LG Supplier qualification','{}','Please answer')).ref$$);
select pg_temp.as_user('33333333-aaaa-0000-0000-000000000003');
select pg_temp.step('the supplier answers', $$select public.deal_act((select v from ids where k = 'qn'), 'answer', '{"answers":{"gmp":"yes"}}', 'to')$$);
select pg_temp.no('the supplier cannot approve itself', $$select public.deal_act((select v from ids where k = 'qn'), 'approve', '{}', 'from')$$, '42501');
select pg_temp.as_user('11111111-aaaa-0000-0000-000000000001');
select pg_temp.step('the organiser approves', $$select public.deal_act((select v from ids where k = 'qn'), 'approve', '{}', 'from')$$);
select pg_temp.ok('an approved questionnaire puts the supplier on the buyer''s approved list',
  $$(select a.status = 'approved' from public.approved_suppliers a join public.companies b on b.id = a.buyer_company_id join public.companies s on s.id = a.supplier_company_id where b.slug = 'lg-org-pharma' and s.slug = 'lg-big-api')$$);
select pg_temp.as_user('44444444-aaaa-0000-0000-000000000004');
select pg_temp.ok('an outsider cannot read another company''s approved list', $$(select count(*) = 0 from public.approved_suppliers a join public.companies b on b.id = a.buyer_company_id where b.slug = 'lg-org-pharma')$$);
select pg_temp.as_anon();
select pg_temp.ok('anon cannot read the approved list either', $$(select count(*) = 0 from public.approved_suppliers a join public.companies b on b.id = a.buyer_company_id where b.slug = 'lg-org-pharma')$$);

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
