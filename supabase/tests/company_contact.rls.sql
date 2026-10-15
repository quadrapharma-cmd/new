-- Talking to a company from its page (0032, B-05): company_contacts() names who answers each kind of request, company_message()
-- delivers to that person (chosen by the database) with one notification a day. Runs as the real API roles with a JWT, in one
-- transaction that is rolled back; test data carries the "CC " marker. Run on a fresh database (stub + migrations):
--   psql -f supabase/tests/company_contact.rls.sql
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
create function pg_temp.who(c text, kind text) returns text language sql stable as $$ select public.company_contacts(pg_temp.id(c)) -> kind ->> 'name' $$;

-- people: the owner, a public sales member, a hidden quality member, a buyer
insert into auth.users (id, email) values ('c1111111-1111-1111-1111-111111111111','cc-owner@x'),('c2222222-2222-2222-2222-222222222222','cc-sales@x'),
  ('c3333333-3333-3333-3333-333333333333','cc-hidden@x'),('c4444444-4444-4444-4444-444444444444','cc-buyer@x') on conflict do nothing;
insert into public.profiles (id, name) values ('c1111111-1111-1111-1111-111111111111','CC Owner'),('c2222222-2222-2222-2222-222222222222','CC Sales'),
  ('c3333333-3333-3333-3333-333333333333','CC Hidden'),('c4444444-4444-4444-4444-444444444444','CC Buyer') on conflict (id) do update set name = excluded.name;

select pg_temp.as_server();
select pg_temp.step('a company with an owner, a public sales member routed for quotes and a hidden member routed for questionnaires', $$
  with x as (insert into public.companies (owner_id, name, type) values ('c1111111-1111-1111-1111-111111111111', 'CC Talk Pharma', 'Manufacturer') returning id) insert into ids select 'co', id::text from x;
  insert into public.company_members (company_id, user_id, role, accepted, show_public) values
    (pg_temp.id('co'), 'c2222222-2222-2222-2222-222222222222', 'sales', true, true), (pg_temp.id('co'), 'c3333333-3333-3333-3333-333333333333', 'quality', true, false)
    on conflict (company_id, user_id) do update set role = excluded.role, accepted = true, show_public = excluded.show_public;
  insert into public.company_routing (company_id, request_type, user_id) values (pg_temp.id('co'), 'quote', 'c2222222-2222-2222-2222-222222222222'),
    (pg_temp.id('co'), 'questionnaire', 'c3333333-3333-3333-3333-333333333333');
  with x as (insert into public.companies (owner_id, name, type, status, source) values (null, 'CC Unclaimed Labs', 'Manufacturer', 'unclaimed', 'public_list') returning id) insert into ids select 'unc', id::text from x$$);

-- ── who answers ──
select pg_temp.as_user('c4444444-4444-4444-4444-444444444444');
select pg_temp.ok('the buyer cannot read the routing table itself (it stays members-only)', $$(select count(*) from public.company_routing where company_id = pg_temp.id('co')) = 0$$);
select pg_temp.ok('quote requests: the routed public sales member, by id, name and role', $$(select c->'quote' = jsonb_build_object('id', 'c2222222-2222-2222-2222-222222222222', 'name', 'CC Sales', 'role', 'sales') from (select public.company_contacts(pg_temp.id('co')) c) x)$$);
select pg_temp.ok('a member who did not agree to be listed is never named: questionnaires fall back to the owner', $$pg_temp.who('co', 'questionnaire') = 'CC Owner'$$);
select pg_temp.ok('no routing for a kind: the owner answers (job)', $$pg_temp.who('co', 'job') = 'CC Owner'$$);
select pg_temp.ok('every kind of the approved "Who receives what" is answered', $$(select array_agg(k order by k) from jsonb_object_keys(public.company_contacts(pg_temp.id('co'))) k) = array['dossier','group','job','questionnaire','quote','service','surplus']$$);
select pg_temp.ok('nobody answers for an unclaimed page', $$(select public.company_contacts(pg_temp.id('unc')) -> 'quote') = 'null'::jsonb$$);
select pg_temp.no('the internal answerer is not an API function', $$select * from public.company_answerer(pg_temp.id('co'), 'quote')$$, '42501');
select pg_temp.as_user('c1111111-1111-1111-1111-111111111111');
select pg_temp.ok('the company''s own owner sees the routing as the deals engine uses it (the unlisted member answers questionnaires)', $$(select public.company_contacts(pg_temp.id('co')) -> 'questionnaire' ->> 'id') = 'c3333333-3333-3333-3333-333333333333'$$);
select pg_temp.as_server();
select pg_temp.ok('…the same person deal_receiver() sends questionnaires to', $$public.deal_receiver(pg_temp.id('co'), 'questionnaire') = 'c3333333-3333-3333-3333-333333333333'$$);

-- ── a message to the company ──
select pg_temp.as_user('c4444444-4444-4444-4444-444444444444');
select pg_temp.step('the buyer messages the company twice', $$select public.company_message(pg_temp.id('co'), '  CC Do you have CEP for Metformin?  '); select public.company_message(pg_temp.id('co'), 'CC And the DMF?')$$);
select pg_temp.as_server();
select pg_temp.ok('the messages go to the routed sales member, trimmed', $$(select array_agg(body order by id) from public.messages where sender_id = 'c4444444-4444-4444-4444-444444444444' and receiver_id = 'c2222222-2222-2222-2222-222222222222') = array['CC Do you have CEP for Metformin?', 'CC And the DMF?']$$);
select pg_temp.ok('the routed member gets ONE notification naming the company (not one per message)', $$(select count(*) = 1 and bool_and(type = 'company_message' and message like 'messaged CC Talk Pharma: "CC Do you have CEP%') from public.notifications where user_id = 'c2222222-2222-2222-2222-222222222222' and from_user = 'c4444444-4444-4444-4444-444444444444')$$);
select pg_temp.ok('nobody else at the company is notified', $$not exists (select 1 from public.notifications where user_id in ('c1111111-1111-1111-1111-111111111111', 'c3333333-3333-3333-3333-333333333333') and from_user = 'c4444444-4444-4444-4444-444444444444')$$);
select pg_temp.as_user('c2222222-2222-2222-2222-222222222222');
select pg_temp.ok('the routed member reads the conversation (ordinary messages)', $$(select count(*) from public.messages where sender_id = 'c4444444-4444-4444-4444-444444444444') = 2$$);

-- the sales member leaves: the owner answers and receives
select pg_temp.step('the sales member leaves the team', $$delete from public.company_members where company_id = pg_temp.id('co') and user_id = 'c2222222-2222-2222-2222-222222222222'$$);
select pg_temp.as_user('c4444444-4444-4444-4444-444444444444');
select pg_temp.ok('after the routed member left, quotes go to the owner', $$pg_temp.who('co', 'quote') = 'CC Owner'$$);
select pg_temp.step('the buyer messages again', $$select public.company_message(pg_temp.id('co'), 'CC Anyone there?')$$);
select pg_temp.as_server();
select pg_temp.ok('…and the owner receives it, with a notification', $$exists (select 1 from public.messages where receiver_id = 'c1111111-1111-1111-1111-111111111111' and body = 'CC Anyone there?')
  and exists (select 1 from public.notifications where user_id = 'c1111111-1111-1111-1111-111111111111' and type = 'company_message')$$);

-- refusals
select pg_temp.as_user('c4444444-4444-4444-4444-444444444444');
select pg_temp.no('nobody answers for an unclaimed page: the message is refused with a clear reason (P0002)', $$select public.company_message(pg_temp.id('unc'), 'CC hello')$$, 'P0002');
select pg_temp.no('an empty message is refused', $$select public.company_message(pg_temp.id('co'), '   ')$$, '22023');
select pg_temp.as_user('c1111111-1111-1111-1111-111111111111');
select pg_temp.no('the person who answers cannot message their own company', $$select public.company_message(pg_temp.id('co'), 'CC to myself')$$, '22023');
select pg_temp.as_anon();
select pg_temp.no('anon cannot ask who answers', $$select public.company_contacts(pg_temp.id('co'))$$, '42501');
select pg_temp.no('anon cannot message a company', $$select public.company_message(pg_temp.id('co'), 'CC hi')$$, '42501');
select pg_temp.as_server();
update public.companies set status = 'suspended' where id = pg_temp.id('co');
select pg_temp.as_user('c4444444-4444-4444-4444-444444444444');
select pg_temp.ok('a suspended page answers nothing', $$(select public.company_contacts(pg_temp.id('co')) -> 'quote') = 'null'::jsonb$$);

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
