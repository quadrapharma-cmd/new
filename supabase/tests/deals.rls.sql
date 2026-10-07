-- Deals engine (0007 + 0008 + 0021): a full quote deal between two companies, every out-of-turn step refused, expiry, self-dealing,
-- privacy (outsider and anonymous visitor), track record. Runs as the real API roles with a JWT, in one transaction that is rolled back;
-- test data carries the "DL " marker and assertions are scoped to it. Run on a fresh database (stub + migrations): psql -f supabase/tests/deals.rls.sql
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

create function pg_temp.ref() returns text language sql stable as $$ select v from ids where k = 'ref' $$;

insert into auth.users (id, email) values ('a1111111-0000-0000-0000-000000000001','dl-buyer@x'),('b2222222-0000-0000-0000-000000000002','dl-seller@x'),('c3333333-0000-0000-0000-000000000003','dl-outsider@x') on conflict do nothing;
insert into public.profiles (id, name) values ('a1111111-0000-0000-0000-000000000001','DL Buyer'),('b2222222-0000-0000-0000-000000000002','DL Seller'),('c3333333-0000-0000-0000-000000000003','DL Outsider') on conflict (id) do nothing;
select pg_temp.as_user('a1111111-0000-0000-0000-000000000001');
select pg_temp.step('the buyer creates its company', $$insert into public.companies (name, type, slug) values ('DL Buyer Pharma','Manufacturer','dl-buyer-pharma')$$);
select pg_temp.as_user('b2222222-0000-0000-0000-000000000002');
select pg_temp.step('the seller creates its company', $$insert into public.companies (name, type, slug) values ('DL Seller API','Supplier','dl-seller-api')$$);
-- buyer sends an RFQ
select pg_temp.as_user('a1111111-0000-0000-0000-000000000001');
select pg_temp.step('the buyer sends an RFQ', $$insert into ids select 'ref', (public.deal_create('quote','dl-seller-api','dl-buyer-pharma','DL Metformin HCl — 2 MT','{"qty":"2","unit":"MT","inc":"CIF"}','Need CEP')).ref$$);
select pg_temp.ok('RFQ created as "sent", with its first event', $$(select status = 'sent' from public.deals where ref = pg_temp.ref()) and (select count(*) = 1 from public.deal_events e join public.deals d on d.id = e.deal_id where d.ref = pg_temp.ref())$$);
select pg_temp.as_user('b2222222-0000-0000-0000-000000000002');
select pg_temp.ok('the supplier owner is notified (seen from their own account)', $$exists (select 1 from public.notifications where user_id = 'b2222222-0000-0000-0000-000000000002' and type = 'deal' and message = 'DL Metformin HCl — 2 MT')$$);
select pg_temp.as_user('a1111111-0000-0000-0000-000000000001');
-- valid titles, so only the rule under test can refuse them (a 1-character title would be refused by the table itself)
select pg_temp.no('cannot send a request to your own company', $$select public.deal_create('quote','dl-buyer-pharma','dl-buyer-pharma','DL Self deal test')$$, '42501');
select pg_temp.no('cannot send on behalf of a company you do not belong to', $$select public.deal_create('quote','dl-buyer-pharma','dl-seller-api','DL Membership test')$$, '42501');
select pg_temp.no('the buyer cannot quote on their own request (wrong side)', $$select public.deal_act(pg_temp.ref(),'quote','{"price":"1"}','to')$$, '42501');
select pg_temp.no('the buyer cannot accept before there is an offer (out of turn)', $$select public.deal_act(pg_temp.ref(),'accept')$$, '42501');
select pg_temp.no('direct edits are impossible (only the engine changes deals)', $$update public.deals set status = 'closed' where ref = pg_temp.ref()$$, '42501');
-- outsider: the ref is known (captured above), so the engine itself must refuse — not merely fail to find the row
select pg_temp.as_user('c3333333-0000-0000-0000-000000000003');
select pg_temp.ok('an outsider cannot see the deal or its events', $$(select count(*) from public.deals where ref = pg_temp.ref()) = 0 and (select count(*) from public.deal_events e join public.deals d on d.id = e.deal_id where d.ref = pg_temp.ref()) = 0$$);
select pg_temp.no('an outsider cannot act on it, even with its reference (the step itself is legal now)', $$select public.deal_act(pg_temp.ref(),'quote','{"price":"1"}','to')$$, '42501');
select pg_temp.no('an outsider cannot act on it as the sender either', $$select public.deal_act(pg_temp.ref(),'cancel','{}','from')$$, '42501');
-- anonymous visitor
select pg_temp.as_anon();
select pg_temp.ok('anon cannot see the deal', $$(select count(*) from public.deals where ref = pg_temp.ref()) = 0$$);
select pg_temp.no('anon cannot act on it', $$select public.deal_act(pg_temp.ref(),'cancel','{}','from')$$, '42501');
select pg_temp.no('anon cannot create a request', $$select public.deal_create('job','dl-seller-api',null,'DL Anonymous request')$$, '42501');
-- seller quotes
select pg_temp.as_user('b2222222-0000-0000-0000-000000000002');
select pg_temp.step('the supplier quotes', $$select public.deal_act(pg_temp.ref(),'quote','{"price":"US$ 5.40 / kg","validity":"14 days","lead":"3 weeks"}')$$);
select pg_temp.ok('the supplier quotes → "quoted", offer stored', $$(select status = 'quoted' and offer ->> 'price' = 'US$ 5.40 / kg' from public.deals where ref = pg_temp.ref())$$);
select pg_temp.as_user('a1111111-0000-0000-0000-000000000001');
select pg_temp.ok('the buyer is notified of the quote (seen from their own account)', $$exists (select 1 from public.notifications where user_id = 'a1111111-0000-0000-0000-000000000001' and type = 'deal' and message like 'DL Metformin HCl — 2 MT — quote%')$$);
-- expired offer
select pg_temp.as_server();
select pg_temp.step('the offer ages 20 days', $$update public.deals set offer_at = now() - interval '20 days' where ref = pg_temp.ref()$$);
select pg_temp.as_user('a1111111-0000-0000-0000-000000000001');
select pg_temp.no('an expired offer cannot be accepted', $$select public.deal_act(pg_temp.ref(),'accept')$$, '42501');
select pg_temp.step('the buyer counters', $$select public.deal_act(pg_temp.ref(),'counter','{"price":"US$ 5.10 / kg"}')$$);
select pg_temp.as_user('b2222222-0000-0000-0000-000000000002');
select pg_temp.step('the supplier quotes again', $$select public.deal_act(pg_temp.ref(),'quote','{"price":"US$ 5.20 / kg","validity":"14 days"}')$$);
select pg_temp.as_user('a1111111-0000-0000-0000-000000000001');
select pg_temp.step('the buyer accepts', $$select public.deal_act(pg_temp.ref(),'accept')$$);
select pg_temp.ok('counter → new quote → accepted', $$(select status = 'accepted' and offer ->> 'price' = 'US$ 5.20 / kg' from public.deals where ref = pg_temp.ref())$$);
select pg_temp.as_user('b2222222-0000-0000-0000-000000000002');
select pg_temp.step('the supplier confirms and ships', $$select public.deal_act(pg_temp.ref(),'confirm'); select public.deal_act(pg_temp.ref(),'ship')$$);
select pg_temp.no('the supplier cannot mark their own shipment received', $$select public.deal_act(pg_temp.ref(),'receive')$$, '42501');
select pg_temp.as_user('a1111111-0000-0000-0000-000000000001');
select pg_temp.step('the buyer receives it', $$select public.deal_act(pg_temp.ref(),'receive','{"ontime":"yes"}')$$);
select pg_temp.no('a rating outside 1–5 stars is refused', $$select public.deal_act(pg_temp.ref(),'rate','{"stars":9}')$$, '22023');
select pg_temp.step('the buyer rates it', $$select public.deal_act(pg_temp.ref(),'rate','{"stars":5,"note":"On time, full CEP"}')$$);
select pg_temp.ok('full path: sent → quoted → countered → quoted → accepted → confirmed → shipped → delivered → closed',
  $$(select status = 'closed' from public.deals where ref = pg_temp.ref())
    and (select string_agg(action, '>' order by e.id) from public.deal_events e join public.deals d on d.id = e.deal_id where d.ref = pg_temp.ref()) = 'sent>quote>counter>quote>accept>confirm>ship>receive>rate'$$);
select pg_temp.no('a deal can be rated only once', $$select public.deal_act(pg_temp.ref(),'rate','{"stars":1}')$$, '42501');
select pg_temp.ok('track record: 1 completed, 100% on time, ★5.0 from 1 review',
  $$(select (public.company_track_record(id)::jsonb) @> '{"orders":1,"ontime":100,"rating":5.0,"reviews":1,"requests":1,"answered":1}' from public.companies where slug = 'dl-seller-api')$$);

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
