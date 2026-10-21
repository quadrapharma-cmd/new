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
create function pg_temp.err(q text) returns text language plpgsql as $$ begin execute q; return null; exception when others then return sqlerrm; end $$;
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
-- a Fawry charge that failed: the order never got a reference — it must never block a new payment (verification finding 1)
select pg_temp.step('a Fawry order whose charge never returned a reference', $$with x as (select (public.create_order('boost', 'fawry', null, pg_temp.id('la'))).id) insert into ids select 'of0', id::text from x$$);
select pg_temp.no('the buyer cannot close an order through payment_start_failed (server-only)', $$select public.payment_start_failed(pg_temp.id('of0'), '{}')$$, '42501');
select pg_temp.no('a second Fawry order while the first is being issued (its first 2 minutes) is refused — parallel requests make one reference', $$select public.create_order('boost', 'fawry', null, pg_temp.id('la'))$$, '23505');
select pg_temp.ok('…saying so', $$pg_temp.err($q$select public.create_order('boost', 'fawry', null, pg_temp.id('la'))$q$) like 'A Fawry reference for this is being issued%'$$);
select pg_temp.as_server();
update public.payment_orders set created_at = now() - interval '3 minutes' where id = pg_temp.id('of0');
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.step('a new Fawry order for the same listing', $$with x as (select (public.create_order('boost', 'fawry', null, pg_temp.id('la'))).id) insert into ids select 'of', id::text from x$$);
select pg_temp.ok('…is allowed: an order without a reference is not "you already have a Fawry reference"', $$pg_temp.id('of') is not null and pg_temp.id('of') <> pg_temp.id('of0')$$);
select pg_temp.ok('…and the order without a reference is left alone (a reference issued a moment later still finds it)', $$(select status = 'pending' from public.payment_orders where id = pg_temp.id('of0'))$$);
select pg_temp.as_server();
update public.payment_orders set created_at = now() - interval '20 minutes' where id = pg_temp.id('of0');
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.ok('…after 15 minutes without a reference My payments shows it as did not go through', $$exists (select 1 from jsonb_array_elements(public.my_payments(null)) e where (e->>'id')::bigint = pg_temp.id('of0') and e->>'status' = 'failed')$$);
select pg_temp.as_server();
select pg_temp.ok('payment_start_failed closes it (hidden from My payments)', $$public.payment_start_failed(pg_temp.id('of0'), '{}') = 'failed'$$);
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.ok('…hidden', $$not exists (select 1 from jsonb_array_elements(public.my_payments(null)) e where (e->>'id')::bigint = pg_temp.id('of0'))$$);
select pg_temp.as_server();
select pg_temp.ok('payment_start_failed (payments-create, when the provider refuses) closes a pending order', $$public.payment_start_failed(pg_temp.id('of'), '{"statusCode":9999}') = 'failed'$$);
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.step('another Fawry order, this time Fawry issues its reference', $$with x as (select (public.create_order('boost', 'fawry', null, pg_temp.id('la'))).id) insert into ids select 'of2', id::text from x$$);
select pg_temp.as_server();
select public.set_order_provider_ref(pg_temp.id('of2'), '771234567890', null, now() + interval '48 hours');
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.no('a second Fawry order for the same listing is refused while the first reference is payable', $$select public.create_order('boost', 'fawry', null, pg_temp.id('la'))$$, '23505');
select pg_temp.ok('…and the message names the real Fawry reference (not our order number)', $$pg_temp.err($q$select public.create_order('boost', 'fawry', null, pg_temp.id('la'))$q$) like 'You already have a Fawry reference for this (771234567890)%'$$);
select pg_temp.as_server();
update public.payment_orders set fawry_expires_at = now() - interval '1 minute' where id = pg_temp.id('of2');
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.step('the reference expired: a new Fawry order', $$with x as (select (public.create_order('boost', 'fawry', null, pg_temp.id('la'))).id) insert into ids select 'of3', id::text from x$$);
select pg_temp.ok('…an expired reference does not block a new one', $$pg_temp.id('of3') is not null$$);
select pg_temp.as_server();
select public.set_order_provider_ref(pg_temp.id('of3'), 'FR-' || pg_temp.id('of3'), null, now() + interval '48 hours');
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.step('an InstaPay order', $$with x as (select (public.create_order('boost', 'instapay', null, pg_temp.id('la'))).id) insert into ids select 'oi', id::text from x$$);
select pg_temp.no('…a second InstaPay order while the first waits for its transfer is refused', $$select public.create_order('boost', 'instapay', null, pg_temp.id('la'))$$, '23505');
-- the receipt path (finding 10e)
select pg_temp.no('submit_instapay refuses a receipt path with ..', $$select public.submit_instapay(pg_temp.id('oi'), 'IPN-1234', 'payments/e1111111-1111-1111-1111-111111111111/../e2222222-2222-2222-2222-222222222222/r.png')$$, '42501');
select pg_temp.no('…a receipt in someone else''s folder', $$select public.submit_instapay(pg_temp.id('oi'), 'IPN-1234', 'payments/e2222222-2222-2222-2222-222222222222/r.png')$$, '42501');
select pg_temp.no('…a receipt in a sub-folder', $$select public.submit_instapay(pg_temp.id('oi'), 'IPN-1234', 'payments/e1111111-1111-1111-1111-111111111111/x/r.png')$$, '42501');
select pg_temp.no('…a receipt with an unsafe name', $$select public.submit_instapay(pg_temp.id('oi'), 'IPN-1234', 'payments/e1111111-1111-1111-1111-111111111111/.r png')$$, '42501');
select pg_temp.no('…a receipt outside payments/', $$select public.submit_instapay(pg_temp.id('oi'), 'IPN-1234', 'cv/e1111111-1111-1111-1111-111111111111/r.png')$$, '42501');
select pg_temp.no('…an empty transfer number', $$select public.submit_instapay(pg_temp.id('oi'), '  ', null)$$, '22023');
select pg_temp.ok('…nothing changed', $$(select status = 'pending' and receipt_path is null from public.payment_orders where id = pg_temp.id('oi'))$$);
select pg_temp.step('the buyer sends the transfer with a receipt in their own folder', $$select public.submit_instapay(pg_temp.id('oi'), 'IPN-1234', 'payments/e1111111-1111-1111-1111-111111111111/a1b2c3.png')$$);
select pg_temp.ok('…the order is under review with that receipt', $$(select status = 'review' and receipt_path = 'payments/e1111111-1111-1111-1111-111111111111/a1b2c3.png' from public.payment_orders where id = pg_temp.id('oi'))$$);
select pg_temp.no('a second InstaPay order while one is under review is refused (finding 10d)', $$select public.create_order('boost', 'instapay', null, pg_temp.id('la'))$$, '23505');
select pg_temp.no('the buyer cannot cancel an InstaPay transfer Drugbox is checking', $$select public.cancel_order(pg_temp.id('oi'))$$, '22023');
-- 10b / 10c: no VIP for a suspended company, no paid promotion of an inactive listing
select pg_temp.as_server();
with x as (insert into public.companies (owner_id, name, type) values ('e1111111-1111-1111-1111-111111111111', 'PP Suspended Co', 'Distributor') returning id) insert into ids select 'susp', id::text from x;
update public.companies set status = 'suspended' where id = pg_temp.id('susp');
with x as (insert into public.products (user_id, name, category, type) values ('e1111111-1111-1111-1111-111111111111', 'PP hidden listing', 'api', 'supply') returning id) insert into ids select 'lh', id::text from x;
do $$ begin   -- taken off the marketplace (a listing status, where the schema has one, decides `active`)
  if exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'products' and column_name = 'status') then
    execute 'update public.products set status = ''paused'' where id = ' || pg_temp.id('lh');
  end if;
  update public.products set active = false where id = pg_temp.id('lh');
end $$;
select pg_temp.ok('(the hidden listing is inactive)', $$(select not active from public.products where id = pg_temp.id('lh'))$$);
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.no('VIP cannot be bought for a suspended company', $$select public.create_order('vip_month', 'card', pg_temp.id('susp'), null)$$, '42501');
select pg_temp.no('a paid boost of an inactive listing is refused', $$select public.create_order('boost', 'card', null, pg_temp.id('lh'))$$, '42501');
select pg_temp.no('…and Featured too', $$select public.create_order('featured', 'fawry', null, pg_temp.id('lh'))$$, '42501');
-- 10a: the buyer cancels a pending order; nothing can activate it afterwards
select pg_temp.step('a card order (abandoned on the Paymob page)', $$with x as (select (public.create_order('featured', 'card', null, pg_temp.id('la'))).id) insert into ids select 'oc', id::text from x$$);
select pg_temp.as_user('e2222222-2222-2222-2222-222222222222');
select pg_temp.no('another member cannot cancel my order', $$select public.cancel_order(pg_temp.id('oc'))$$, '42501');
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.ok('the buyer cancels their own pending order', $$public.cancel_order(pg_temp.id('oc')) = 'cancelled'$$);
select pg_temp.ok('…it is cancelled in the database', $$(select status from public.payment_orders where id = pg_temp.id('oc')) = 'cancelled'$$);
select pg_temp.no('…a cancelled order cannot be cancelled again', $$select public.cancel_order(pg_temp.id('oc'))$$, '22023');
select pg_temp.no('the buyer cannot set it back to pending', $$update public.payment_orders set status = 'pending' where id = pg_temp.id('oc')$$, '42501');
select pg_temp.as_server();
update public.payment_orders set provider_order = 'PO-' || id where id = pg_temp.id('oc');
select pg_temp.ok('a late Paymob callback for the cancelled order activates nothing (refund due)', $$public.confirm_payment('paymob', 'PO-' || pg_temp.id('oc'), 'tx-oc', 450300, 'EGP', '{}') = 'order is cancelled (refund due)'
  and (select status from public.payment_orders where id = pg_temp.id('oc')) = 'cancelled' and (select featured_until is null from public.products where id = pg_temp.id('la'))$$);
select pg_temp.ok('…and Drugbox''s admins are told a refund is due', $$exists (select 1 from public.notifications where user_id = 'e4444444-4444-4444-4444-444444444444' and message like '%paid after the buyer cancelled%refund due%')$$);
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');

-- ══ the server pays and fails orders ══
select pg_temp.as_server();
update public.payment_orders set provider_order = 'PO-' || id where id in (pg_temp.id('o1'), pg_temp.id('o2'));
select pg_temp.ok('a wrong amount does not pay', $$public.confirm_payment('paymob', 'PO-' || pg_temp.id('o2'), 'tx1', 100, 'EGP', '{}') = 'amount mismatch'$$);
select pg_temp.ok('the right amount pays', $$public.confirm_payment('paymob', 'PO-' || pg_temp.id('o2'), 'tx2', 165300, 'EGP', '{}') = 'paid'$$);
select pg_temp.ok('…and activates the boost for 7 days', $$(select boosted_until > now() + interval '6 days' from public.products where id = pg_temp.id('la'))$$);
select pg_temp.ok('the paid order has an invoice number DBX-INV-<year>-<6 digits>', $$(select invoice_no ~ '^DBX-INV-\d{4}-\d{6}$' from public.payment_orders where id = pg_temp.id('o2'))$$);
select pg_temp.ok('a repeated callback does not activate twice', $$public.confirm_payment('paymob', 'PO-' || pg_temp.id('o2'), 'tx2', 165300, 'EGP', '{}') = 'already paid'$$);
select pg_temp.ok('a late callback for the superseded order is still honoured (the money arrived)', $$public.confirm_payment('paymob', 'PO-' || pg_temp.id('o1'), 'tx3', 165300, 'EGP', '{}') = 'paid'$$);
select pg_temp.ok('two paid orders have two different invoice numbers', $$(select count(distinct invoice_no) from public.payment_orders where id in (pg_temp.id('o1'), pg_temp.id('o2'))) = 2$$);
select pg_temp.ok('Fawry EXPIRED: the order expires', $$public.fail_payment('fawry', 'DBX' || pg_temp.id('of3'), 'FR-' || pg_temp.id('of3'), 'EXPIRED', '{}') = 'expired'$$);
select pg_temp.ok('…and the buyer is told', $$exists (select 1 from public.notifications where user_id = 'e1111111-1111-1111-1111-111111111111' and message like 'Your Fawry reference%expired%')$$);
select pg_temp.ok('a failure notice for a paid order changes nothing', $$public.fail_payment('paymob', 'PO-' || pg_temp.id('o2'), 'x', 'FAILED', '{}') = 'order is paid' and (select status from public.payment_orders where id = pg_temp.id('o2')) = 'paid'$$);
select pg_temp.ok('Fawry with another reference cannot fail an order', $$public.fail_payment('fawry', 'DBX' || pg_temp.id('of2'), 'WRONG', 'EXPIRED', '{}') = 'reference mismatch'$$);
-- invoices keep what they said when issued (finding 8)
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.step('the invoice as issued', $$insert into ids select 'inv', public.order_invoice(pg_temp.id('o2'))::text$$);
select pg_temp.as_server();
update public.payment_products set vat_rate = 0.15, label = 'Renamed boost', duration_days = 9 where code = 'boost';
update public.billing_settings set legal_name = 'Drugbox Renamed LLC', tax_reg_no = '999-999-999' where id;
update public.profiles set name = 'PP Owner Renamed' where id = 'e1111111-1111-1111-1111-111111111111';
update public.payment_orders set invoice_no = 'DBX-INV-2026-999998', invoice_snapshot = '{}' where id = pg_temp.id('o2');
select pg_temp.ok('an issued invoice number and its contents cannot be rewritten (even by the service role)', $$(select invoice_no from public.payment_orders where id = pg_temp.id('o2')) = (select v::jsonb->>'invoice_no' from ids where k = 'inv')$$);
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.ok('after price, VAT, seller and name changes the issued invoice is unchanged (product, days, VAT rate, seller, buyer)', $$(select v::jsonb from ids where k = 'inv') = public.order_invoice(pg_temp.id('o2'))
  and public.order_invoice(pg_temp.id('o2'))->>'product' = 'Marketplace boost' and (public.order_invoice(pg_temp.id('o2'))->>'vat_rate')::numeric = 0.14 and (public.order_invoice(pg_temp.id('o2'))->>'days')::int = 7
  and public.order_invoice(pg_temp.id('o2'))->'seller'->>'name' <> 'Drugbox Renamed LLC' and public.order_invoice(pg_temp.id('o2'))->'buyer'->>'name' = 'PP Owner'$$);
select pg_temp.as_server();
update public.payment_orders set status = 'refunded' where id = pg_temp.id('o2');
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.ok('a refunded order''s invoice still opens, marked refunded, with the same number', $$(public.order_invoice(pg_temp.id('o2'))->>'refunded')::boolean and public.order_invoice(pg_temp.id('o2'))->>'invoice_no' = (select v::jsonb->>'invoice_no' from ids where k = 'inv')$$);
select pg_temp.as_server();
update public.payment_orders set status = 'paid' where id = pg_temp.id('o2');
update public.payment_products set vat_rate = 0.14, label = 'Marketplace boost', duration_days = 7 where code = 'boost';

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

-- ══ re-verification round 2: Fawry references cannot be withdrawn, lost answers, expired listings, rejected transfers stay listed ══
select pg_temp.as_server();
select pg_temp.step('three more listings of the owner: one fresh, one fresh for InstaPay, one expired', $$
  with x as (insert into public.products (user_id, name, category, type) values ('e1111111-1111-1111-1111-111111111111', 'PP listing C', 'api', 'supply') returning id) insert into ids select 'lc', id::text from x;
  with x as (insert into public.products (user_id, name, category, type) values ('e1111111-1111-1111-1111-111111111111', 'PP listing E', 'api', 'supply') returning id) insert into ids select 'le', id::text from x;
  with x as (insert into public.products (user_id, name, category, type) values ('e1111111-1111-1111-1111-111111111111', 'PP listing D', 'api', 'supply') returning id) insert into ids select 'ld', id::text from x;
  set local session_replication_role = replica; update public.products set expires_at = now() - interval '1 day' where id = pg_temp.id('ld'); set local session_replication_role = origin$$);   -- 0054's trigger would renew it
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.step('a Fawry order whose reference Fawry issued', $$with x as (select (public.create_order('boost', 'fawry', null, pg_temp.id('lc'))).id) insert into ids select 'of5', id::text from x$$);
select pg_temp.as_server();
select public.set_order_provider_ref(pg_temp.id('of5'), 'FR-LIVE-' || pg_temp.id('of5'), null, now() + interval '48 hours');
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.no('a live Fawry reference cannot be "cancelled" (Fawry keeps it payable until it expires)', $$select public.cancel_order(pg_temp.id('of5'))$$, '22023');
select pg_temp.ok('…the order stays pending with its reference', $$(select status from public.payment_orders where id = pg_temp.id('of5')) = 'pending'$$);
select pg_temp.as_server();
select pg_temp.step('the reference expires', $$update public.payment_orders set fawry_expires_at = now() - interval '1 minute', created_at = now() - interval '1 hour' where id = pg_temp.id('of5')$$);
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.no('a paid boost for an expired listing is refused (it is not in the marketplace)', $$select public.create_order('boost', 'card', null, pg_temp.id('ld'))$$, '42501');
select pg_temp.no('…nor an included VIP boost', $$select public.use_included_boost(pg_temp.id('ld'), pg_temp.id('vip'))$$, '42501');
select pg_temp.step('an InstaPay transfer for listing E, sent', $$with x as (select (public.create_order('boost', 'instapay', null, pg_temp.id('le'))).id) insert into ids select 'oi9', id::text from x;
  select public.submit_instapay(pg_temp.id('oi9'), 'IPX-998877', null)$$);
select pg_temp.as_user('e4444444-4444-4444-4444-444444444444');
select pg_temp.step('Drugbox finds no transfer and rejects it', $$select public.review_instapay(pg_temp.id('oi9'), false)$$);
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.ok('a rejected transfer stays in My payments (as did not go through)', $$exists (select 1 from jsonb_array_elements(public.my_payments(null)) e where (e->>'id')::bigint = pg_temp.id('oi9') and e->>'status' = 'failed')$$);

select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.step('a Fawry order whose answer from Fawry was lost (no reference on record)', $$with x as (select (public.create_order('boost', 'fawry', null, pg_temp.id('le'))).id) insert into ids select 'of7', id::text from x$$);
select pg_temp.as_server();
select pg_temp.ok('a signed Fawry notice for it is still not paid (F-115)', $$public.confirm_payment('fawry', (select merchant_ref from public.payment_orders where id = pg_temp.id('of7')), 'FR-LOST-7', 165300, 'EGP', '{}') = 'reference mismatch'
  and (select status = 'pending' and provider_ref is null from public.payment_orders where id = pg_temp.id('of7'))$$);
select pg_temp.ok('…but Drugbox is told once, to reconcile and refund', $$(select count(*) from public.notifications where user_id = 'e4444444-4444-4444-4444-444444444444' and message like 'Fawry payment received for ' || (select merchant_ref from public.payment_orders where id = pg_temp.id('of7')) || ' %') = 1$$);
select pg_temp.step('Fawry sends it again', $$select public.confirm_payment('fawry', (select merchant_ref from public.payment_orders where id = pg_temp.id('of7')), 'FR-LOST-7', 165300, 'EGP', '{}')$$);
select pg_temp.step('a second, different reference arrives for the same order', $$select public.confirm_payment('fawry', (select merchant_ref from public.payment_orders where id = pg_temp.id('of7')), 'FR-LOST-8', 165300, 'EGP', '{}')$$);
select pg_temp.ok('…Drugbox is told about that one too (once per reference)', $$(select count(*) from public.notifications where message like 'Fawry payment received for ' || (select merchant_ref from public.payment_orders where id = pg_temp.id('of7')) || ' (reference FR-LOST-8)%' and user_id = 'e4444444-4444-4444-4444-444444444444') = 1$$);
select pg_temp.ok('…the first reference is still told once', $$(select count(*) from public.notifications where message like 'Fawry payment received for ' || (select merchant_ref from public.payment_orders where id = pg_temp.id('of7')) || ' (reference FR-LOST-7)%' and user_id = 'e4444444-4444-4444-4444-444444444444') = 1$$);

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
