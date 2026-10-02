-- Listings and group buying: posting rights, joins, target reached, member orders created by the database, AVL from an approved questionnaire.
\set QUIET on
set client_min_messages = warning;
begin;
insert into auth.users (id, email) values ('11111111-aaaa-0000-0000-000000000001','org@x'),('22222222-aaaa-0000-0000-000000000002','member@x'),('33333333-aaaa-0000-0000-000000000003','sup@x'),('44444444-aaaa-0000-0000-000000000004','out@x') on conflict do nothing;
create temp table r (n serial, name text, ok boolean); grant all on r to authenticated; grant all on r_n_seq to authenticated;
create or replace function pg_temp.as_user(u text) returns void language plpgsql as $$ begin perform set_config('request.jwt.claim.sub', u, true); perform set_config('role','authenticated', true); end $$;
create or replace function pg_temp.refused(q text) returns boolean language plpgsql as $$ begin execute q; return false; exception when others then return true; end $$;
select pg_temp.as_user('11111111-aaaa-0000-0000-000000000001'); insert into public.companies (name, type, slug) values ('Org Pharma','Manufacturer','org-pharma');
select pg_temp.as_user('22222222-aaaa-0000-0000-000000000002'); insert into public.companies (name, type, slug) values ('Member Labs','Manufacturer','member-labs');
select pg_temp.as_user('33333333-aaaa-0000-0000-000000000003'); insert into public.companies (name, type, slug) values ('Big API','Supplier','big-api');
-- listings
insert into public.company_listings (company_id, kind, product, qty, price, off, created_by) select id,'surplus','MCC PH-101','750 kg','US$ 2.40/kg',30,'33333333-aaaa-0000-0000-000000000003' from public.companies where slug='big-api';
insert into r(name,ok) select 'a company posts its surplus', (select count(*)=1 from public.company_listings where product='MCC PH-101');
select pg_temp.as_user('44444444-aaaa-0000-0000-000000000004');
insert into r(name,ok) select 'everyone can see listings', (select count(*)=1 from public.company_listings where product='MCC PH-101');
insert into r(name,ok) select 'cannot post a listing for a company you do not belong to', pg_temp.refused($$insert into public.company_listings (company_id, kind, product, created_by) select id,'surplus','Fake','44444444-aaaa-0000-0000-000000000004' from public.companies where slug='big-api'$$);
-- group buying
select pg_temp.as_user('11111111-aaaa-0000-0000-000000000001');
select public.deal_create('group','big-api','org-pharma','Group buy — Metformin HCl','{"product":"Metformin HCl","target":1000,"unit":"kg","price":"US$ 5.10/kg","by":"2099-12-31"}','Buying group opened');
select public.deal_join((select ref from public.deals where title='Group buy — Metformin HCl'),'org-pharma',400);
insert into r(name,ok) select 'the organiser opens a group with its share (open, 400 of 1000)', (select status='open' from public.deals where title='Group buy — Metformin HCl') and (select sum(qty)=400 from public.deal_members);
select pg_temp.as_user('44444444-aaaa-0000-0000-000000000004');
insert into r(name,ok) select 'any company can see the buying group', (select count(*)=1 from public.deals where title='Group buy — Metformin HCl');
insert into r(name,ok) select 'cannot join without belonging to a company', pg_temp.refused($$select public.deal_join((select ref from public.deals where title='Group buy — Metformin HCl'),'member-labs',100)$$);
select pg_temp.as_user('33333333-aaaa-0000-0000-000000000003');
insert into r(name,ok) select 'the supplier cannot join its own group', pg_temp.refused($$select public.deal_join((select ref from public.deals where title='Group buy — Metformin HCl'),'big-api',100)$$);
insert into r(name,ok) select 'the supplier cannot confirm before the target is reached', pg_temp.refused($$select public.deal_act((select ref from public.deals where title='Group buy — Metformin HCl'),'confirm_group','{}','to')$$);
select pg_temp.as_user('22222222-aaaa-0000-0000-000000000002');
insert into r(name,ok) select 'a zero share is refused', pg_temp.refused($$select public.deal_join((select ref from public.deals where title='Group buy — Metformin HCl'),'member-labs',0)$$);
select public.deal_join((select ref from public.deals where title='Group buy — Metformin HCl'),'member-labs',700);
insert into r(name,ok) select 'a member joins with 700 → target reached (1,100 of 1,000)', (select status='target_reached' from public.deals where title='Group buy — Metformin HCl');
insert into r(name,ok) select 'joining after the target is reached is refused', pg_temp.refused($$select public.deal_join((select ref from public.deals where title='Group buy — Metformin HCl'),'member-labs',50)$$);
select pg_temp.as_user('33333333-aaaa-0000-0000-000000000003');
insert into r(name,ok) select 'the supplier is notified that the target was reached', exists(select 1 from public.notifications where user_id='33333333-aaaa-0000-0000-000000000003' and message like 'Buying group reached%');
select public.deal_act((select ref from public.deals where title='Group buy — Metformin HCl'),'confirm_group','{}','to');
insert into r(name,ok) select 'the supplier confirms the group price', (select status='confirmed' from public.deals where title='Group buy — Metformin HCl');
insert into r(name,ok) select 'the database creates one accepted order per member at the group price', (select count(*)=2 from public.deals where group_of=(select id from public.deals where title='Group buy — Metformin HCl') and status='accepted' and offer->>'price'='US$ 5.10/kg');
select pg_temp.as_user('22222222-aaaa-0000-0000-000000000002');
insert into r(name,ok) select 'each member sees its own order (700 kg)', exists(select 1 from public.deals where title like 'Metformin HCl — 700 kg (group order)' and status='accepted');
-- questionnaire approval → AVL
select pg_temp.as_user('11111111-aaaa-0000-0000-000000000001');
select public.deal_create('questionnaire','big-api','org-pharma','Supplier qualification','{}','Please answer');
select pg_temp.as_user('33333333-aaaa-0000-0000-000000000003'); select public.deal_act((select ref from public.deals where title='Supplier qualification'),'answer','{"answers":{"gmp":"yes"}}','to');
select pg_temp.as_user('11111111-aaaa-0000-0000-000000000001'); select public.deal_act((select ref from public.deals where title='Supplier qualification'),'approve','{}','from');
insert into r(name,ok) select 'an approved questionnaire puts the supplier on the buyer''s approved list', (select a.status='approved' from public.approved_suppliers a join public.companies b on b.id=a.buyer_company_id where b.slug='org-pharma');
select pg_temp.as_user('44444444-aaaa-0000-0000-000000000004');
insert into r(name,ok) select 'an outsider cannot read another company''s approved list', (select count(*)=0 from public.approved_suppliers);
reset role;
select (case when ok then 'PASS  ' else 'FAIL  ' end) || name from r order by n;
select 'TOTAL ' || count(*) filter (where ok) || ' / ' || count(*) from r;
rollback;
