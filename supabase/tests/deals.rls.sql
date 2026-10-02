-- Deals engine tests: a full quote deal between two companies, every out-of-turn step refused, expiry, self-dealing, privacy, track record.
\set QUIET on
set client_min_messages = warning;
begin;
insert into auth.users (id, email) values ('a1111111-0000-0000-0000-000000000001','buyer@x'),('b2222222-0000-0000-0000-000000000002','seller@x'),('c3333333-0000-0000-0000-000000000003','outsider@x') on conflict do nothing;
create temp table r (n serial, name text, ok boolean); grant all on r to authenticated; grant all on r_n_seq to authenticated;
create or replace function pg_temp.as_user(u text) returns void language plpgsql as $$ begin perform set_config('request.jwt.claim.sub', u, true); perform set_config('role','authenticated', true); end $$;
create or replace function pg_temp.refused(q text) returns boolean language plpgsql as $$ begin execute q; return false; exception when others then return true; end $$;
select pg_temp.as_user('a1111111-0000-0000-0000-000000000001'); insert into public.companies (name, type, slug) values ('Buyer Pharma','Manufacturer','buyer-pharma');
select pg_temp.as_user('b2222222-0000-0000-0000-000000000002'); insert into public.companies (name, type, slug) values ('Seller API','Supplier','seller-api');
-- buyer sends an RFQ
select pg_temp.as_user('a1111111-0000-0000-0000-000000000001');
select public.deal_create('quote','seller-api','buyer-pharma','Metformin HCl — 2 MT','{"qty":"2","unit":"MT","inc":"CIF"}','Need CEP') into temp t1;
insert into r(name,ok) select 'RFQ created as "sent", with its first event', (select status='sent' from public.deals where title='Metformin HCl — 2 MT') and (select count(*)=1 from public.deal_events e join public.deals d on d.id=e.deal_id where d.title='Metformin HCl — 2 MT');
select pg_temp.as_user('b2222222-0000-0000-0000-000000000002');
insert into r(name,ok) select 'the supplier owner is notified (seen from their own account)', exists(select 1 from public.notifications where user_id='b2222222-0000-0000-0000-000000000002' and type='deal');
select pg_temp.as_user('a1111111-0000-0000-0000-000000000001');
insert into r(name,ok) select 'cannot send a request to your own company', pg_temp.refused($$select public.deal_create('quote','buyer-pharma','buyer-pharma','x')$$);
insert into r(name,ok) select 'cannot send on behalf of a company you do not belong to', pg_temp.refused($$select public.deal_create('quote','buyer-pharma','seller-api','x')$$);
insert into r(name,ok) select 'the buyer cannot quote on their own request (wrong side)', pg_temp.refused($$select public.deal_act((select ref from public.deals where title='Metformin HCl — 2 MT'),'quote','{"price":"1"}','to')$$);
insert into r(name,ok) select 'the buyer cannot accept before there is an offer (out of turn)', pg_temp.refused($$select public.deal_act((select ref from public.deals where title='Metformin HCl — 2 MT'),'accept')$$);
insert into r(name,ok) select 'direct edits are impossible (only the engine changes deals)', pg_temp.refused($$update public.deals set status='closed'$$);
-- outsider
select pg_temp.as_user('c3333333-0000-0000-0000-000000000003');
insert into r(name,ok) select 'an outsider cannot see the deal', (select count(*) from public.deals where title='Metformin HCl — 2 MT')=0;
insert into r(name,ok) select 'an outsider cannot act on it', pg_temp.refused($$select public.deal_act((select ref from public.deals limit 1),'quote','{"price":"1"}')$$);
-- seller quotes
select pg_temp.as_user('b2222222-0000-0000-0000-000000000002');
select public.deal_act((select ref from public.deals where title='Metformin HCl — 2 MT'),'quote','{"price":"US$ 5.40 / kg","validity":"14 days","lead":"3 weeks"}');
insert into r(name,ok) select 'the supplier quotes → "quoted", offer stored', (select status='quoted' and offer->>'price'='US$ 5.40 / kg' from public.deals where title='Metformin HCl — 2 MT');
select pg_temp.as_user('a1111111-0000-0000-0000-000000000001');
insert into r(name,ok) select 'the buyer is notified of the quote (seen from their own account)', exists(select 1 from public.notifications where user_id='a1111111-0000-0000-0000-000000000001' and type='deal');
select pg_temp.as_user('b2222222-0000-0000-0000-000000000002');
-- expired offer
reset role; update public.deals set offer_at = now() - interval '20 days' where title='Metformin HCl — 2 MT';
select pg_temp.as_user('a1111111-0000-0000-0000-000000000001');
insert into r(name,ok) select 'an expired offer cannot be accepted', pg_temp.refused($$select public.deal_act((select ref from public.deals where title='Metformin HCl — 2 MT'),'accept')$$);
select public.deal_act((select ref from public.deals where title='Metformin HCl — 2 MT'),'counter','{"price":"US$ 5.10 / kg"}');
select pg_temp.as_user('b2222222-0000-0000-0000-000000000002');
select public.deal_act((select ref from public.deals where title='Metformin HCl — 2 MT'),'quote','{"price":"US$ 5.20 / kg","validity":"14 days"}');
select pg_temp.as_user('a1111111-0000-0000-0000-000000000001');
select public.deal_act((select ref from public.deals where title='Metformin HCl — 2 MT'),'accept');
insert into r(name,ok) select 'counter → new quote → accepted', (select status='accepted' and offer->>'price'='US$ 5.20 / kg' from public.deals where title='Metformin HCl — 2 MT');
select pg_temp.as_user('b2222222-0000-0000-0000-000000000002');
select public.deal_act((select ref from public.deals where title='Metformin HCl — 2 MT'),'confirm'); select public.deal_act((select ref from public.deals where title='Metformin HCl — 2 MT'),'ship');
insert into r(name,ok) select 'the supplier cannot mark their own shipment received', pg_temp.refused($$select public.deal_act((select ref from public.deals where title='Metformin HCl — 2 MT'),'receive')$$);
select pg_temp.as_user('a1111111-0000-0000-0000-000000000001');
select public.deal_act((select ref from public.deals where title='Metformin HCl — 2 MT'),'receive','{"ontime":"yes"}');
insert into r(name,ok) select 'a rating outside 1–5 stars is refused', pg_temp.refused($$select public.deal_act((select ref from public.deals where title='Metformin HCl — 2 MT'),'rate','{"stars":9}')$$);
select public.deal_act((select ref from public.deals where title='Metformin HCl — 2 MT'),'rate','{"stars":5,"note":"On time, full CEP"}');
insert into r(name,ok) select 'full path: sent → quoted → countered → quoted → accepted → confirmed → shipped → delivered → closed', (select status='closed' from public.deals where title='Metformin HCl — 2 MT') and (select string_agg(action,'>' order by e.id) from public.deal_events e join public.deals d on d.id=e.deal_id where d.title='Metformin HCl — 2 MT')='sent>quote>counter>quote>accept>confirm>ship>receive>rate';
insert into r(name,ok) select 'a deal can be rated only once', pg_temp.refused($$select public.deal_act((select ref from public.deals where title='Metformin HCl — 2 MT'),'rate','{"stars":1}')$$);
insert into r(name,ok) select 'track record: 1 completed, 100% on time, ★5.0 from 1 review', (select (public.company_track_record(id)::jsonb) @> '{"orders":1,"ontime":100,"rating":5.0,"reviews":1,"requests":1,"answered":1}' from public.companies where slug='seller-api');
reset role;
select (case when ok then 'PASS  ' else 'FAIL  ' end) || name from r order by n;
select 'TOTAL ' || count(*) filter (where ok) || ' / ' || count(*) from r;
rollback;
