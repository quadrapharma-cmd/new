-- Paying Drugbox (0055, B-14/B-15/B-16): the server's prices and VAT split, invoice numbers, failed / expired / superseded orders,
-- no duplicate pending Fawry / InstaPay order, who reads orders and invoices, VIP's included boosts — and tampering through the API
-- roles. Runs as the real API roles with a JWT, in one transaction that is rolled back; test data carries the "PP " marker.
-- Run on a fresh database (stub + migrations):   psql -f supabase/tests/payments_area.rls.sql
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

-- people: a VIP company owner (buyer), an outsider, a member of the company (sales), a Drugbox admin
insert into auth.users (id, email) values ('e1111111-1111-1111-1111-111111111111','pp-owner@x.test'),('e2222222-2222-2222-2222-222222222222','pp-out@x.test'),
  ('e3333333-3333-3333-3333-333333333333','pp-sales@x.test'),('e4444444-4444-4444-4444-444444444444','pp-admin@x.test') on conflict do nothing;
insert into public.profiles (id, name) values ('e1111111-1111-1111-1111-111111111111','PP Owner'),('e2222222-2222-2222-2222-222222222222','PP Outsider'),
  ('e3333333-3333-3333-3333-333333333333','PP Sales'),('e4444444-4444-4444-4444-444444444444','PP Admin') on conflict (id) do update set name = excluded.name;
update public.profiles set role = 'admin' where id = 'e4444444-4444-4444-4444-444444444444';

select pg_temp.as_server();
select pg_temp.step('a VIP company of the owner (with a sales member), a free company of the outsider, a listing each', $$
  with x as (insert into public.companies (owner_id, name, type, plan, vip_until) values ('e1111111-1111-1111-1111-111111111111', 'PP VIP Pharma', 'Manufacturer', 'vip', now() + interval '20 days') returning id) insert into ids select 'vip', id::text from x;
  with x as (insert into public.companies (owner_id, name, type) values ('e2222222-2222-2222-2222-222222222222', 'PP Free Co', 'Distributor') returning id) insert into ids select 'free', id::text from x;
  insert into public.company_members (company_id, user_id, role, accepted, show_public) values (pg_temp.id('vip'), 'e3333333-3333-3333-3333-333333333333', 'sales', true, false);
  with x as (insert into public.products (user_id, name, category, type) values ('e1111111-1111-1111-1111-111111111111', 'PP listing A', 'api', 'supply') returning id) insert into ids select 'la', id::text from x;
  with x as (insert into public.products (user_id, name, category, type) values ('e2222222-2222-2222-2222-222222222222', 'PP listing B', 'api', 'supply') returning id) insert into ids select 'lb', id::text from x$$);

-- ══ orders: the server's price, no writing by the browser ══
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.step('the owner orders a boost by card', $$with x as (select (public.create_order('boost', 'card', null, pg_temp.id('la'))).id) insert into ids select 'o1', id::text from x$$);
select pg_temp.ok('the amount is the server''s: 1,450 + 14 % = 1,653.00, split 1,450.00 + 203.00', $$(select amount_cents = 165300 and net_cents = 145000 and vat_cents = 20300 and status = 'pending' from public.payment_orders where id = pg_temp.id('o1'))$$);
select pg_temp.no('the buyer cannot insert an order', $$insert into public.payment_orders (user_id, product_code, listing_id, method, amount_cents) values ('e1111111-1111-1111-1111-111111111111', 'boost', pg_temp.id('la'), 'card', 100)$$, '42501');
select pg_temp.no('the buyer cannot mark the order paid', $$update public.payment_orders set status = 'paid' where id = pg_temp.id('o1')$$, '42501');
select pg_temp.no('the buyer cannot lower the amount', $$update public.payment_orders set amount_cents = 100 where id = pg_temp.id('o1')$$, '42501');
select pg_temp.no('the buyer cannot set an invoice number', $$update public.payment_orders set invoice_no = 'DBX-INV-2026-999999' where id = pg_temp.id('o1')$$, '42501');
select pg_temp.no('confirm_payment is server-only', $$select public.confirm_payment('paymob', 'x', 'y', 165300, 'EGP', '{}')$$, '42501');
select pg_temp.no('fail_payment is server-only', $$select public.fail_payment('paymob', 'x', 'y', 'FAILED', '{}')$$, '42501');
select pg_temp.no('activate_order is server-only', $$select public.activate_order(pg_temp.id('o1'))$$, '42501');
select pg_temp.no('set_order_provider_ref is server-only', $$select public.set_order_provider_ref(pg_temp.id('o1'), 'r', 'o', now())$$, '42501');
select pg_temp.no('assign_invoice_no is server-only', $$select public.assign_invoice_no(pg_temp.id('o1'))$$, '42501');
select pg_temp.no('vip_reminders is server-only', $$select public.vip_reminders()$$, '42501');
select pg_temp.no('an order for someone else''s listing is refused', $$select public.create_order('boost', 'card', null, pg_temp.id('lb'))$$, '42501');
select pg_temp.no('VIP for a company I do not manage is refused', $$select public.create_order('vip_month', 'card', pg_temp.id('free'), null)$$, '42501');
select pg_temp.no('an unknown method is refused', $$select public.create_order('boost', 'bitcoin', null, pg_temp.id('la'))$$, '22023');
select pg_temp.step('the buyer tries to change a price', $$update public.payment_products set amount_egp = 1 where code = 'boost'$$);
select pg_temp.ok('…the price is untouched (RLS)', $$(select amount_egp from public.payment_products where code = 'boost') = 1450$$);
select pg_temp.step('a second card order for the same listing', $$with x as (select (public.create_order('boost', 'card', null, pg_temp.id('la'))).id) insert into ids select 'o2', id::text from x$$);
select pg_temp.ok('the older card order is superseded: one pending card order per listing', $$(select count(*) from public.payment_orders where listing_id = pg_temp.id('la') and status = 'pending') = 1
  and (select status from public.payment_orders where id = pg_temp.id('o1')) = 'expired'$$);
select pg_temp.step('a Fawry order for the same listing', $$with x as (select (public.create_order('boost', 'fawry', null, pg_temp.id('la'))).id) insert into ids select 'of', id::text from x$$);
select pg_temp.no('a second Fawry order for the same listing is refused while the first is payable', $$select public.create_order('boost', 'fawry', null, pg_temp.id('la'))$$, '23505');
select pg_temp.no('…and an InstaPay one only once too', $$select public.create_order('boost', 'instapay', null, pg_temp.id('la')); select public.create_order('boost', 'instapay', null, pg_temp.id('la'))$$, '23505');

-- ══ the server pays and fails orders ══
select pg_temp.as_server();
update public.payment_orders set provider_order = 'PO-' || id, provider_ref = 'FR-' || id where id in (pg_temp.id('o1'), pg_temp.id('o2'), pg_temp.id('of'));
select pg_temp.ok('a wrong amount does not pay', $$public.confirm_payment('paymob', 'PO-' || pg_temp.id('o2'), 'tx1', 100, 'EGP', '{}') = 'amount mismatch'$$);
select pg_temp.ok('the right amount pays', $$public.confirm_payment('paymob', 'PO-' || pg_temp.id('o2'), 'tx2', 165300, 'EGP', '{}') = 'paid'$$);
select pg_temp.ok('…and activates the boost for 7 days', $$(select boosted_until > now() + interval '6 days' from public.products where id = pg_temp.id('la'))$$);
select pg_temp.ok('the paid order has an invoice number DBX-INV-<year>-<6 digits>', $$(select invoice_no ~ '^DBX-INV-\d{4}-\d{6}$' from public.payment_orders where id = pg_temp.id('o2'))$$);
select pg_temp.ok('a repeated callback does not activate twice', $$public.confirm_payment('paymob', 'PO-' || pg_temp.id('o2'), 'tx2', 165300, 'EGP', '{}') = 'already paid'$$);
select pg_temp.ok('a late callback for the superseded order is still honoured (the money arrived)', $$public.confirm_payment('paymob', 'PO-' || pg_temp.id('o1'), 'tx3', 165300, 'EGP', '{}') = 'paid'$$);
select pg_temp.ok('two paid orders have two different invoice numbers', $$(select count(distinct invoice_no) from public.payment_orders where id in (pg_temp.id('o1'), pg_temp.id('o2'))) = 2$$);
select pg_temp.ok('Fawry EXPIRED: the order expires', $$public.fail_payment('fawry', 'DBX' || pg_temp.id('of'), 'FR-' || pg_temp.id('of'), 'EXPIRED', '{}') = 'expired'$$);
select pg_temp.ok('…and the buyer is told', $$exists (select 1 from public.notifications where user_id = 'e1111111-1111-1111-1111-111111111111' and message like 'Your Fawry reference%expired%')$$);
select pg_temp.ok('a failure notice for a paid order changes nothing', $$public.fail_payment('paymob', 'PO-' || pg_temp.id('o2'), 'x', 'FAILED', '{}') = 'order is paid' and (select status from public.payment_orders where id = pg_temp.id('o2')) = 'paid'$$);
select pg_temp.ok('Fawry with another reference cannot fail an order', $$public.fail_payment('fawry', 'DBX' || pg_temp.id('of'), 'WRONG', 'EXPIRED', '{}') = 'reference mismatch'$$);

-- ══ who reads orders and invoices ══
select pg_temp.as_user('e2222222-2222-2222-2222-222222222222');
select pg_temp.ok('the outsider reads none of the owner''s orders', $$(select count(*) from public.payment_orders where user_id = 'e1111111-1111-1111-1111-111111111111') = 0$$);
select pg_temp.ok('…and my_payments for the VIP company gives nothing', $$public.my_payments(pg_temp.id('vip')) = '[]'::jsonb$$);
select pg_temp.no('…and cannot open its invoice', $$select public.order_invoice(pg_temp.id('o2'))$$, '42501');
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.ok('the buyer reads the invoice: net + VAT = total, the product, the seller', $$(select (v->>'net')::numeric + (v->>'vat')::numeric = (v->>'total')::numeric and (v->>'total')::numeric = 1653 and v->>'product' = 'Marketplace boost' and v->'seller'->>'name' is not null from (select public.order_invoice(pg_temp.id('o2')) v) x)$$);
select pg_temp.no('no invoice for an order that is not paid', $$select public.order_invoice(pg_temp.id('of'))$$, '22023');
select pg_temp.ok('My payments lists my orders', $$jsonb_array_length(public.my_payments(null)) >= 3$$);

-- ══ VIP included boosts ══
select pg_temp.ok('a VIP company has 3 included boosts this month', $$public.included_boosts_left(pg_temp.id('vip')) = 3$$);
select pg_temp.ok('using one says 2 are left', $$(public.use_included_boost(pg_temp.id('la'), pg_temp.id('vip')) ->> 'left')::int = 2$$);
select pg_temp.ok('…the count agrees and no payment order was made', $$public.included_boosts_left(pg_temp.id('vip')) = 2 and (select count(*) from public.vip_boost_uses where company_id = pg_temp.id('vip')) = 1$$);
select pg_temp.no('the owner cannot write a use directly (no grant)', $$insert into public.vip_boost_uses (company_id, month) values (pg_temp.id('vip'), date_trunc('month', now())::date)$$, '42501');
select pg_temp.no('…nor delete the count', $$delete from public.vip_boost_uses where company_id = pg_temp.id('vip')$$, '42501');
select pg_temp.no('another person''s listing cannot take the company''s boost', $$select public.use_included_boost(pg_temp.id('lb'), pg_temp.id('vip'))$$, '42501');
select pg_temp.step('two more uses', $$select public.use_included_boost(pg_temp.id('la'), pg_temp.id('vip')); select public.use_included_boost(pg_temp.id('la'), pg_temp.id('vip'))$$);
select pg_temp.no('a fourth use this month is refused', $$select public.use_included_boost(pg_temp.id('la'), pg_temp.id('vip'))$$, '54000');
select pg_temp.as_user('e3333333-3333-3333-3333-333333333333');
select pg_temp.ok('a sales member does not see the company''s credits (managers only)', $$public.included_boosts_left(pg_temp.id('vip')) = 0$$);
select pg_temp.as_user('e2222222-2222-2222-2222-222222222222');
select pg_temp.no('the outsider cannot consume the VIP company''s boosts with his own listing', $$select public.use_included_boost(pg_temp.id('lb'), pg_temp.id('vip'))$$, '42501');
select pg_temp.no('a free company has no included boosts', $$select public.use_included_boost(pg_temp.id('lb'), pg_temp.id('free'))$$, '42501');
select pg_temp.step('the outsider tries to change the seller details on invoices', $$update public.billing_settings set legal_name = 'Evil' where id$$);
select pg_temp.ok('…the row is untouched (RLS)', $$(select legal_name from public.billing_settings) <> 'Evil'$$);
select pg_temp.as_server();
update public.companies set vip_until = now() - interval '1 minute' where id = pg_temp.id('vip');
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.ok('when VIP has ended, no included boosts are left', $$public.included_boosts_left(pg_temp.id('vip')) = 0$$);
select pg_temp.as_anon();
select pg_temp.no('anon cannot order', $$select public.create_order('boost', 'card', null, 1)$$, '42501');
select pg_temp.no('anon cannot read invoices', $$select public.order_invoice(1)$$, '42501');
select pg_temp.no('anon cannot read my payments', $$select public.my_payments(null)$$, '42501');
select pg_temp.no('anon cannot use boosts', $$select public.use_included_boost(1, 1)$$, '42501');

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
