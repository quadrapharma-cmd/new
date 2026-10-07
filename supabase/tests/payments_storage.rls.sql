-- Payments, moderation and storage (0018 + 0023): Paymob callbacks bound to the signed order id with amount and currency,
-- provider never confirms InstaPay, one transaction pays one order, nothing "active" when the listing/company is gone,
-- VIP ends at vip_until, InstaPay rejection only in review, the reported company cannot dismiss or rewrite reports,
-- a deleted post takes its files, evidence bucket limits/removal, storage paths in the writer's own folder.
-- Runs as the real API roles with a JWT (the webhooks as service_role), in one transaction that is rolled back; test data carries
-- the "PS " marker. Run on a fresh database (stub + migrations): psql -f supabase/tests/payments_storage.rls.sql
-- Harness as in listings_groups.rls.sql: step()/ok()/no(); a negative check passes only with the expected SQLSTATE; non-zero exit on failure.
\set QUIET on
\set ON_ERROR_ROLLBACK on
set client_min_messages = warning;
\o /dev/null
begin;
create temp table r (n serial, name text, ok boolean, err text); grant all on r to authenticated, anon, service_role; grant all on r_n_seq to authenticated, anon, service_role;
create temp table ids (k text primary key, v text); grant all on ids to authenticated, anon, service_role;
create function pg_temp.as_user(u text) returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', u, true); perform set_config('request.jwt.claims', json_build_object('sub', u, 'role', 'authenticated')::text, true);
  perform set_config('role', 'authenticated', true); end $$;
create function pg_temp.as_anon() returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', '', true); perform set_config('request.jwt.claims', '{"role":"anon"}', true); perform set_config('role', 'anon', true); end $$;
-- the Edge Functions call the database with the service-role key: no user, role service_role
create function pg_temp.as_service() returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', '', true); perform set_config('request.jwt.claims', '{"role":"service_role"}', true); perform set_config('role', 'service_role', true); end $$;
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
-- a webhook call: the text confirm_payment answers
create function pg_temp.confirm(p text, k text, tx text, cents int, cur text) returns text language sql as $$
  select public.confirm_payment(p, k, tx, cents, cur, jsonb_build_object('provider', p, 'id', tx)) $$;
-- number of rows a statement changed (RLS hides rows silently: 0 means refused)
-- (-1: refused for lack of privilege)
create function pg_temp.rows(q text) returns int language plpgsql as $$ declare n int; begin execute q; get diagnostics n = row_count; return n;
  exception when insufficient_privilege then return -1; end $$;
create function pg_temp.id(k text) returns bigint language sql stable as $$ select v::bigint from ids where ids.k = id.k $$;
create function pg_temp.ref(k text) returns text language sql stable as $$ select merchant_ref from public.payment_orders where id = pg_temp.id(k) $$;

-- O owner · X another member · A Drugbox admin · B reporter / evidence author
insert into auth.users (id, email) values ('0a000000-0000-0000-0000-00000000000a','ps-owner@x'),('0b000000-0000-0000-0000-00000000000b','ps-other@x'),
  ('0c000000-0000-0000-0000-00000000000c','ps-admin@x'),('0d000000-0000-0000-0000-00000000000d','ps-reporter@x') on conflict do nothing;
insert into public.profiles (id, name) values ('0a000000-0000-0000-0000-00000000000a','PS Owner'),('0b000000-0000-0000-0000-00000000000b','PS Other'),
  ('0c000000-0000-0000-0000-00000000000c','PS Admin'),('0d000000-0000-0000-0000-00000000000d','PS Reporter') on conflict (id) do nothing;
update public.profiles set role = 'admin' where id = '0c000000-0000-0000-0000-00000000000c';
\set O '\'0a000000-0000-0000-0000-00000000000a\''
\set X '\'0b000000-0000-0000-0000-00000000000b\''
\set A '\'0c000000-0000-0000-0000-00000000000c\''
\set B '\'0d000000-0000-0000-0000-00000000000d\''
select pg_temp.as_user(:O);
select pg_temp.step('the owner creates a company', $$with x as (insert into public.companies (name, type, slug) values ('PS Pharma','Manufacturer','ps-pharma') returning id) insert into ids select 'co', id from x$$);
select pg_temp.step('the owner creates a second company', $$with x as (insert into public.companies (name, type, slug) values ('PS Gone Labs','Manufacturer','ps-gone-labs') returning id) insert into ids select 'co2', id from x$$);
select pg_temp.step('the owner posts two listings', $$with x as (insert into public.products (user_id, name, category, type, active)
  values ('0a000000-0000-0000-0000-00000000000a','PS Listing one','api','supply',true),('0a000000-0000-0000-0000-00000000000a','PS Listing two','api','supply',true) returning id) insert into ids select 'l' || row_number() over (order by id), id from x$$);

-- ══ F-115 Paymob: bound by the signed order id; amount and currency must match ═══════════════
select pg_temp.step('the owner orders VIP by card', $$insert into ids select 'card', (public.create_order('vip_month','card',pg_temp.id('co'))).id$$);
select pg_temp.as_service();
select pg_temp.step('payments-create records Paymob''s order id', $$select public.set_order_provider_ref(pg_temp.id('card'), 'pi_ps_1', '7700001')$$);
select pg_temp.ok('the Paymob order id is stored with the order', $$(select provider_order = '7700001' and provider_ref = 'pi_ps_1' from public.payment_orders where id = pg_temp.id('card'))$$);
select pg_temp.ok('a callback naming our reference (unsigned merchant_order_id) does not find the order', $$pg_temp.confirm('paymob', pg_temp.ref('card'), 'tx-ps-1', 285000, 'EGP') = 'unknown order'$$);
select pg_temp.ok('a callback for another Paymob order does not pay this one', $$pg_temp.confirm('paymob', '7799999', 'tx-ps-1', 285000, 'EGP') = 'unknown order'$$);
select pg_temp.ok('a wrong currency with the same number of cents is refused', $$pg_temp.confirm('paymob', '7700001', 'tx-ps-1', 285000, 'USD') = 'currency mismatch'$$);
select pg_temp.ok('a missing currency is refused', $$pg_temp.confirm('paymob', '7700001', 'tx-ps-1', 285000, null) = 'currency mismatch'$$);
select pg_temp.ok('a wrong amount is refused', $$pg_temp.confirm('paymob', '7700001', 'tx-ps-1', 100, 'EGP') = 'amount mismatch'$$);
select pg_temp.ok('a Fawry notification cannot pay a card order', $$pg_temp.confirm('fawry', pg_temp.ref('card'), 'tx-ps-1', 285000, 'EGP') = 'unknown order'$$);
select pg_temp.ok('an unknown provider is refused', $$pg_temp.confirm('stripe', '7700001', 'tx-ps-1', 285000, 'EGP') = 'unknown provider'$$);
select pg_temp.as_server();
select pg_temp.ok('…and the order is still pending, the company still free', $$(select status = 'pending' from public.payment_orders where id = pg_temp.id('card')) and (select plan = 'free' from public.companies where id = pg_temp.id('co'))$$);
select pg_temp.as_service();
select pg_temp.ok('the signed order id + amount + currency pays the order', $$pg_temp.confirm('paymob', '7700001', 'tx-ps-1', 285000, 'egp') = 'paid'$$);
select pg_temp.as_server();
select pg_temp.ok('the company is VIP for 30 days and the owner is told it is active',
  $$(select plan = 'vip' and vip_until::date - now()::date between 29 and 30 from public.companies where id = pg_temp.id('co'))
    and (select count(*) = 1 from public.notifications where user_id = '0a000000-0000-0000-0000-00000000000a' and type = 'payment' and message like '%is active')$$);
select pg_temp.as_service();
select pg_temp.ok('a replayed callback does not activate twice', $$pg_temp.confirm('paymob', '7700001', 'tx-ps-1', 285000, 'EGP') = 'already paid'$$);
select pg_temp.as_user(:O);
select pg_temp.step('the owner orders VIP yearly by wallet', $$insert into ids select 'wallet', (public.create_order('vip_year','wallet',pg_temp.id('co'))).id$$);
select pg_temp.as_service();
select pg_temp.step('…with its own Paymob order', $$select public.set_order_provider_ref(pg_temp.id('wallet'), 'pi_ps_2', '7700002')$$);
select pg_temp.ok('one Paymob transaction cannot pay a second order', $$pg_temp.confirm('paymob', '7700002', 'tx-ps-1', 2850000, 'EGP') = 'transaction already used'$$);
select pg_temp.no('the database itself refuses two paid orders with one transaction', $$update public.payment_orders set status = 'paid', provider_ref = 'tx-ps-1' where id = pg_temp.id('wallet')$$, '23505');
select pg_temp.no('Paymob''s order id cannot be given to a second order', $$select public.set_order_provider_ref(pg_temp.id('wallet'), 'pi_ps_2', '7700001')$$, '23505');

-- ══ F-116 a provider never confirms an InstaPay order; only pending orders are paid ═══════════
select pg_temp.as_user(:O);
select pg_temp.step('the owner orders a featured listing by InstaPay', $$insert into ids select 'insta', (public.create_order('featured','instapay',null,pg_temp.id('l1'))).id$$);
select pg_temp.step('…and sends the transfer number', $$select public.submit_instapay(pg_temp.id('insta'), 'IPN-PS-1', null)$$);
select pg_temp.as_service();
select pg_temp.ok('a Fawry notification cannot confirm an InstaPay order in review', $$pg_temp.confirm('fawry', pg_temp.ref('insta'), 'fw-ps-9', 450300, 'EGP') = 'unknown order'$$);
select pg_temp.as_server();
select pg_temp.ok('…the InstaPay order still waits for Drugbox', $$(select status = 'review' from public.payment_orders where id = pg_temp.id('insta')) and (select featured_until is null from public.products where id = pg_temp.id('l1'))$$);
select pg_temp.as_user(:O);
select pg_temp.step('the owner orders a boost by Fawry', $$insert into ids select 'fawry', (public.create_order('boost','fawry',null,pg_temp.id('l1'))).id$$);
select pg_temp.as_server();
update public.payment_orders set status = 'expired' where id = pg_temp.id('fawry');
select pg_temp.as_service();
select pg_temp.ok('an order that is no longer pending is not paid', $$pg_temp.confirm('fawry', pg_temp.ref('fawry'), 'fw-ps-1', 165300, 'EGP') = 'order is expired'$$);
select pg_temp.as_server();
update public.payment_orders set status = 'pending' where id = pg_temp.id('fawry');
select pg_temp.as_service();
select pg_temp.ok('a signed Fawry notification pays the Fawry order', $$pg_temp.confirm('fawry', pg_temp.ref('fawry'), 'fw-ps-1', 165300, 'EGP') = 'paid'$$);
select pg_temp.as_server();
select pg_temp.ok('…and boosts the listing for 7 days', $$(select boosted_until::date - now()::date between 6 and 7 from public.products where id = pg_temp.id('l1'))$$);

-- ══ F-114 rejecting a transfer: only an order waiting for review, notified once ═══════════════
select pg_temp.as_user(:A);
select pg_temp.no('rejecting a paid order is refused', $$select public.review_instapay(pg_temp.id('card'), false)$$, 'P0001');
select pg_temp.as_server();
select pg_temp.ok('…the paying customer gets no "could not match" message', $$(select count(*) = 0 from public.notifications where user_id = '0a000000-0000-0000-0000-00000000000a' and message like 'We could not match%')
   and (select status = 'paid' from public.payment_orders where id = pg_temp.id('card'))$$);
select pg_temp.as_user(:A);
select pg_temp.step('Drugbox rejects the transfer in review', $$select public.review_instapay(pg_temp.id('insta'), false)$$);
select pg_temp.no('rejecting it a second time is refused', $$select public.review_instapay(pg_temp.id('insta'), false)$$, 'P0001');
select pg_temp.as_server();
select pg_temp.ok('the customer is told once, the order failed', $$(select count(*) = 1 from public.notifications where user_id = '0a000000-0000-0000-0000-00000000000a' and message like 'We could not match%')
   and (select status = 'failed' from public.payment_orders where id = pg_temp.id('insta'))$$);
select pg_temp.as_user(:X);
select pg_temp.no('a member cannot review transfers', $$select public.review_instapay(pg_temp.id('insta'), true)$$, '42501');

-- ══ F-31 nothing is "active" when the listing or company is gone ══════════════════════════════
select pg_temp.as_user(:O);
select pg_temp.step('the owner orders a boost for listing two by Fawry', $$insert into ids select 'gone', (public.create_order('boost','fawry',null,pg_temp.id('l2'))).id$$);
select pg_temp.step('the owner orders VIP for the second company by card', $$insert into ids select 'gonec', (public.create_order('vip_month','card',pg_temp.id('co2'))).id$$);
select pg_temp.step('…then deletes the listing', $$delete from public.products where id = pg_temp.id('l2')$$);
select pg_temp.as_service();
select pg_temp.step('Paymob''s order id for the company order', $$select public.set_order_provider_ref(pg_temp.id('gonec'), 'pi_ps_3', '7700003')$$);
select pg_temp.ok('the payment is recorded but nothing is activated', $$pg_temp.confirm('fawry', pg_temp.ref('gone'), 'fw-ps-2', 165300, 'EGP') = 'paid, not activated (refund due)'$$);
select pg_temp.as_server();
delete from public.companies where id = pg_temp.id('co2');
select pg_temp.as_service();
select pg_temp.ok('a deleted company page is not made VIP', $$pg_temp.confirm('paymob', '7700003', 'tx-ps-3', 285000, 'EGP') = 'paid, not activated (refund due)'$$);
select pg_temp.as_server();
select pg_temp.ok('the buyer is told a refund is due, not that it is active',
  $$(select count(*) = 2 from public.notifications where user_id = '0a000000-0000-0000-0000-00000000000a' and message like 'Payment received for %refund you')
    and (select count(*) = 2 from public.notifications where user_id = '0a000000-0000-0000-0000-00000000000a' and message like '%is active')$$);
select pg_temp.ok('Drugbox admins are told to refund', $$(select count(*) = 2 from public.notifications where user_id = '0c000000-0000-0000-0000-00000000000c' and message like '%refund due')$$);
select pg_temp.ok('the order keeps the reason', $$(select provider_payload->>'not_activated' = 'listing' and status = 'paid' from public.payment_orders where id = pg_temp.id('gone'))$$);
select pg_temp.as_user(:X);
select pg_temp.step('another member creates a company', $$with x as (insert into public.companies (name, type, slug) values ('PS Other Co','Manufacturer','ps-other-co') returning id) insert into ids select 'co3', id from x$$);
select pg_temp.step('…orders VIP for it', $$insert into ids select 'left', (public.create_order('vip_month','card',pg_temp.id('co3'))).id$$);
select pg_temp.as_server();
update public.companies set owner_id = '0a000000-0000-0000-0000-00000000000a' where id = pg_temp.id('co3');
delete from public.company_members where company_id = pg_temp.id('co3') and user_id = '0b000000-0000-0000-0000-00000000000b';
select pg_temp.as_service();
select pg_temp.step('…Paymob''s order id', $$select public.set_order_provider_ref(pg_temp.id('left'), 'pi_ps_4', '7700004')$$);
select pg_temp.ok('a company the buyer no longer manages is not made VIP', $$pg_temp.confirm('paymob', '7700004', 'tx-ps-4', 285000, 'EGP') = 'paid, not activated (refund due)'$$);
select pg_temp.ok('…it stays free', $$(select plan = 'free' from public.companies where id = pg_temp.id('co3'))$$);

-- ══ F-30 VIP ends at vip_until ═══════════════════════════════════════════════════════════
select pg_temp.as_server();
update public.companies set vip_until = now() - interval '1 day' where id = pg_temp.id('co');
select pg_temp.as_user(:X);
select pg_temp.ok('a lapsed VIP is not VIP when read (is_vip, also companies?select=is_vip)', $$(select not public.is_vip(c) and c.plan = 'vip' from public.companies c where c.id = pg_temp.id('co'))$$);
select pg_temp.no('members cannot run the expiry', $$select public.expire_vip_plans()$$, '42501');
select pg_temp.as_server();
update public.companies set plan = 'vip', vip_until = null where id = pg_temp.id('co3');
select pg_temp.ok('the daily expiry runs', $$public.expire_vip_plans() >= 1$$);
select pg_temp.ok('…and turns the lapsed plan back to free', $$(select plan = 'free' from public.companies where id = pg_temp.id('co'))$$);
select pg_temp.ok('a VIP granted by Drugbox without an end date stays VIP', $$(select plan = 'vip' and public.is_vip(c) from public.companies c where c.id = pg_temp.id('co3'))$$);
select pg_temp.as_user(:O);
select pg_temp.step('the owner renews VIP after it lapsed', $$insert into ids select 'renew', (public.create_order('vip_month','card',pg_temp.id('co'))).id$$);
select pg_temp.as_service();
select pg_temp.step('…Paymob''s order id', $$select public.set_order_provider_ref(pg_temp.id('renew'), 'pi_ps_5', '7700005')$$);
select pg_temp.ok('the renewal is paid', $$pg_temp.confirm('paymob', '7700005', 'tx-ps-5', 285000, 'EGP') = 'paid'$$);
select pg_temp.ok('…for 30 days from today (not from the lapsed date)', $$(select plan = 'vip' and vip_until::date - now()::date between 29 and 30 from public.companies where id = pg_temp.id('co'))$$);
select pg_temp.as_anon();
select pg_temp.no('anonymous visitors cannot run is_vip', $$select public.is_vip(c) from public.companies c limit 1$$, '42501');

-- ══ server-only payment functions ═══════════════════════════════════════════════════════════
select pg_temp.as_user(:O);
select pg_temp.no('a member cannot call confirm_payment', $$select pg_temp.confirm('paymob', '7700002', 'tx-ps-x', 2850000, 'EGP')$$, '42501');
select pg_temp.no('a member cannot set the provider references', $$select public.set_order_provider_ref(pg_temp.id('wallet'), 'x', 'y')$$, '42501');
select pg_temp.no('a member cannot activate an order', $$select public.activate_order(pg_temp.id('wallet'))$$, '42501');
select pg_temp.ok('a member cannot write orders (no row, or no privilege once 0020 is in)', $$pg_temp.rows('update public.payment_orders set provider_order = ''1'' where id = pg_temp.id(''wallet'')') <= 0$$);

-- ══ F-32 the reported company may only mark a report fixed ═══════════════════════════════════
select pg_temp.as_user(:B);
select pg_temp.step('a member reports wrong information', $$with x as (insert into public.company_reports (company_id, reporter, section, issue, correction)
  values (pg_temp.id('co'), '0d000000-0000-0000-0000-00000000000d', 'About', 'PS the founding year is wrong', '1998') returning id) insert into ids select 'rep', id from x$$);
select pg_temp.step('…and another one', $$with x as (insert into public.company_reports (company_id, reporter, section, issue)
  values (pg_temp.id('co'), '0d000000-0000-0000-0000-00000000000d', 'Contact', 'PS the phone number is dead') returning id) insert into ids select 'rep2', id from x$$);
select pg_temp.as_user(:O);
select pg_temp.no('the company cannot dismiss a report', $$update public.company_reports set status = 'dismissed' where id = pg_temp.id('rep')$$, '42501');
select pg_temp.no('the company cannot rewrite the report', $$update public.company_reports set issue = 'nothing wrong here' where id = pg_temp.id('rep')$$, '42501');
select pg_temp.no('the company cannot rewrite the correction', $$update public.company_reports set correction = 'x', status = 'resolved' where id = pg_temp.id('rep')$$, '42501');
select pg_temp.no('the company cannot move the report to another company', $$update public.company_reports set company_id = pg_temp.id('co3') where id = pg_temp.id('rep')$$, '42501');
select pg_temp.step('the company marks it fixed (the page''s "Mark fixed" sends ''fixed'')', $$update public.company_reports set status = 'fixed' where id = pg_temp.id('rep')$$);
select pg_temp.ok('…it is resolved, the text as filed', $$(select status = 'resolved' and issue = 'PS the founding year is wrong' and correction = '1998' from public.company_reports where id = pg_temp.id('rep'))$$);
select pg_temp.step('the company marks the other one resolved', $$update public.company_reports set status = 'resolved' where id = pg_temp.id('rep2')$$);
select pg_temp.no('the company cannot re-open or dismiss a resolved report', $$update public.company_reports set status = 'dismissed' where id = pg_temp.id('rep2')$$, '42501');
select pg_temp.as_user(:A);
select pg_temp.step('Drugbox dismisses / re-opens reports', $$update public.company_reports set status = 'dismissed' where id = pg_temp.id('rep2')$$);
select pg_temp.ok('…Drugbox decided', $$(select status = 'dismissed' from public.company_reports where id = pg_temp.id('rep2'))$$);
select pg_temp.as_user(:X);
select pg_temp.ok('an outsider changes nothing', $$pg_temp.rows('update public.company_reports set status = ''dismissed'' where id = pg_temp.id(''rep'')') = 0$$);

-- ══ F-41 deleting a post removes its files ═════════════════════════════════════════════════
select pg_temp.as_user(:O);
select pg_temp.step('the owner posts with a photo and a file', $$with x as (insert into public.posts (user_id, body) values ('0a000000-0000-0000-0000-00000000000a', 'PS post with media') returning id) insert into ids select 'post', id from x;
  with x as (insert into public.posts (user_id, body) values ('0a000000-0000-0000-0000-00000000000a', 'PS second post') returning id) insert into ids select 'post2', id from x;
  insert into storage.objects (bucket_id, name, owner) values
    ('post-media', 'posts/0a000000-0000-0000-0000-00000000000a/' || pg_temp.id('post') || '-a1.jpg', '0a000000-0000-0000-0000-00000000000a'),
    ('post-media', 'posts/0a000000-0000-0000-0000-00000000000a/' || pg_temp.id('post') || '-b2.pdf', '0a000000-0000-0000-0000-00000000000a'),
    ('post-media', 'posts/0a000000-0000-0000-0000-00000000000a/' || pg_temp.id('post2') || '-c3.jpg', '0a000000-0000-0000-0000-00000000000a');
  insert into public.post_media (post_id, url, type, name) values
    (pg_temp.id('post'), 'http://x/storage/v1/object/public/post-media/posts/0a000000-0000-0000-0000-00000000000a/' || pg_temp.id('post') || '-a1.jpg', 'image', 'photo')$$);
select pg_temp.as_user(:X);
select pg_temp.step('another member posts a photo', $$with x as (insert into public.posts (user_id, body) values ('0b000000-0000-0000-0000-00000000000b', 'PS abusive post') returning id) insert into ids select 'xpost', id from x;
  insert into storage.objects (bucket_id, name, owner) values ('post-media', 'posts/0b000000-0000-0000-0000-00000000000b/' || pg_temp.id('xpost') || '-z9.jpg', '0b000000-0000-0000-0000-00000000000b')$$);
select pg_temp.as_user(:O);
select pg_temp.step('the owner deletes the post', $$delete from public.posts where id = pg_temp.id('post')$$);
select pg_temp.as_server();
select pg_temp.ok('its photo and file are gone (links stop working), its media rows too',
  $$(select count(*) = 0 from storage.objects where bucket_id = 'post-media' and name like 'posts/0a000000-0000-0000-0000-00000000000a/' || pg_temp.id('post') || '-%')
    and (select count(*) = 0 from public.post_media where post_id = pg_temp.id('post'))$$);
select pg_temp.ok('the other post''s and other people''s files stay', $$(select count(*) = 2 from storage.objects where bucket_id = 'post-media' and (name like '%/' || pg_temp.id('post2') || '-c3.jpg' or name like '%/' || pg_temp.id('xpost') || '-z9.jpg'))$$);
select pg_temp.as_user(:A);
select pg_temp.step('Drugbox removes the abusive post', $$delete from public.posts where id = pg_temp.id('xpost')$$);
select pg_temp.as_server();
select pg_temp.ok('…and its photo is taken down too', $$(select count(*) = 0 from storage.objects where bucket_id = 'post-media' and name like '%/' || pg_temp.id('xpost') || '-z9.jpg')$$);

-- ══ F-98 evidence bucket ══════════════════════════════════════════════════════════════════
select pg_temp.ok('evidence: 10 MB, PDF/JPEG/PNG only (as the documents bucket)', $$(select file_size_limit = 10485760 and allowed_mime_types = array['application/pdf','image/jpeg','image/png'] from storage.buckets where id = 'reference-evidence')$$);
select pg_temp.as_user(:B);
select pg_temp.step('the author uploads two evidence files', $$insert into storage.objects (bucket_id, name, owner) values ('reference-evidence', '0d000000-0000-0000-0000-00000000000d/ps-e1.pdf', '0d000000-0000-0000-0000-00000000000d'),
  ('reference-evidence', '0d000000-0000-0000-0000-00000000000d/ps-e2.pdf', '0d000000-0000-0000-0000-00000000000d')$$);
select pg_temp.as_server();
set local session_replication_role = replica;      -- the reference itself is not under test here (its own rules need a verified employer)
with x as (insert into public.work_references (author, candidate, kind, role_title, from_month, to_month, category, body, evidence_path, status)
  values ('0d000000-0000-0000-0000-00000000000d', '0a000000-0000-0000-0000-00000000000a', 'warn', 'QC', '2021-01-01', '2024-12-01', 'Left without notice',
          'PS left in the middle of a validation campaign without any notice', '0d000000-0000-0000-0000-00000000000d/ps-e2.pdf', 'pending') returning id) insert into ids select 'wref', id from x;
set local session_replication_role = origin;
select pg_temp.as_user(:X);
select pg_temp.ok('nobody else removes the author''s evidence', $$pg_temp.rows('delete from storage.objects where bucket_id = ''reference-evidence'' and name like ''0d000000-0000-0000-0000-00000000000d/%''') = 0$$);
select pg_temp.as_user(:B);
select pg_temp.ok('the author removes an unused upload', $$pg_temp.rows('delete from storage.objects where bucket_id = ''reference-evidence'' and name = ''0d000000-0000-0000-0000-00000000000d/ps-e1.pdf''') = 1$$);
select pg_temp.ok('…but not the evidence of a live warning', $$pg_temp.rows('delete from storage.objects where bucket_id = ''reference-evidence'' and name = ''0d000000-0000-0000-0000-00000000000d/ps-e2.pdf''') = 0$$);
select pg_temp.step('the author withdraws the warning', $$delete from public.work_references where id = pg_temp.id('wref')$$);
select pg_temp.as_server();
select pg_temp.ok('…and its evidence file goes with it', $$(select count(*) = 0 from storage.objects where bucket_id = 'reference-evidence' and name = '0d000000-0000-0000-0000-00000000000d/ps-e2.pdf')$$);

-- ══ F-97 paths in the writer's own folder; the review is Drugbox's ═══════════════════════════
select pg_temp.as_user(:O);
select pg_temp.step('the owner uploads the tax card for the company', $$insert into storage.objects (bucket_id, name, owner) values
  ('documents', 'verification/' || pg_temp.id('co') || '/tax-ps.pdf', '0a000000-0000-0000-0000-00000000000a'),
  ('documents', 'verification/' || pg_temp.id('co3') || '/tax-other.pdf', '0a000000-0000-0000-0000-00000000000a')$$);
select pg_temp.no('a request cannot carry a forged review', $$insert into public.verification_requests (company_id, submitted_by, registry, reviewed_by, reviewed_at, note)
  values (pg_temp.id('co'), '0a000000-0000-0000-0000-00000000000a', '778899', '0c000000-0000-0000-0000-00000000000c', now(), 'approved by Drugbox')$$, '42501');
select pg_temp.no('a licence that is not an uploaded file is refused', $$insert into public.verification_requests (company_id, submitted_by, registry, licence_path)
  values (pg_temp.id('co'), '0a000000-0000-0000-0000-00000000000a', '778899', 'not-a-real-file')$$, '42501');
select pg_temp.no('another person''s CV / receipt cannot be offered as a document', $$insert into public.verification_requests (company_id, submitted_by, registry, tax_card_path)
  values (pg_temp.id('co'), '0a000000-0000-0000-0000-00000000000a', '778899', 'cv/0b000000-0000-0000-0000-00000000000b/cv.pdf')$$, '42501');
select pg_temp.no('another company''s documents cannot be offered', $$insert into public.verification_requests (company_id, submitted_by, registry, registry_path)
  values (pg_temp.id('co'), '0a000000-0000-0000-0000-00000000000a', '778899', 'verification/' || pg_temp.id('co3') || '/tax-other.pdf')$$, '42501');
select pg_temp.no('no ../ out of the company''s folder', $$insert into public.verification_requests (company_id, submitted_by, registry, registry_path)
  values (pg_temp.id('co'), '0a000000-0000-0000-0000-00000000000a', '778899', 'verification/' || pg_temp.id('co') || '/../' || pg_temp.id('co3') || '/tax-other.pdf')$$, '42501');
select pg_temp.step('the owner sends the request with its uploaded tax card (as the live app does)', $$insert into public.verification_requests (company_id, submitted_by, registry, tax_card_path)
  values (pg_temp.id('co'), '0a000000-0000-0000-0000-00000000000a', '778899', 'verification/' || pg_temp.id('co') || '/tax-ps.pdf')$$);
select pg_temp.ok('…it waits for Drugbox', $$(select count(*) = 1 from public.verification_requests where company_id = pg_temp.id('co') and status = 'pending' and reviewed_by is null)$$);
select pg_temp.no('a profile cannot show another person''s video', $$update public.profiles set intro_video = '{"path":"people/0b000000-0000-0000-0000-00000000000b/intro.webm","duration":3}' where id = '0a000000-0000-0000-0000-00000000000a'$$, '42501');
select pg_temp.no('…nor a poster from elsewhere', $$update public.profiles set intro_video = '{"path":"people/0a000000-0000-0000-0000-00000000000a/intro.webm","poster":"companies/1/intro-poster.jpg"}' where id = '0a000000-0000-0000-0000-00000000000a'$$, '42501');
select pg_temp.step('a person sets their own video (as the live app does)', $$update public.profiles set intro_video = '{"path":"people/0a000000-0000-0000-0000-00000000000a/intro.webm","poster":"people/0a000000-0000-0000-0000-00000000000a/intro-poster.jpg","duration":3.2,"v":1}' where id = '0a000000-0000-0000-0000-00000000000a'$$);
select pg_temp.step('…and removes it', $$update public.profiles set intro_video = null where id = '0a000000-0000-0000-0000-00000000000a'$$);
select pg_temp.no('a company page cannot show another company''s video', $$update public.companies set intro_video = jsonb_build_object('path', 'companies/' || pg_temp.id('co3') || '/intro.mp4') where id = pg_temp.id('co')$$, '42501');
select pg_temp.step('a company sets its own video', $$update public.companies set intro_video = jsonb_build_object('path', 'companies/' || pg_temp.id('co') || '/intro.mp4', 'duration', 4) where id = pg_temp.id('co')$$);
select pg_temp.ok('…saved', $$(select intro_video->>'path' like 'companies/%/intro.mp4' from public.companies where id = pg_temp.id('co'))$$);
select pg_temp.no('a message photo must be in the conversation''s folder', $$insert into public.messages (sender_id, receiver_id, body, image_url) values ('0a000000-0000-0000-0000-00000000000a', '0b000000-0000-0000-0000-00000000000b', '', 'https://anything/other.jpg')$$, '42501');
select pg_temp.no('…not the other direction''s folder', $$insert into public.messages (sender_id, receiver_id, body, image_url) values ('0a000000-0000-0000-0000-00000000000a', '0b000000-0000-0000-0000-00000000000b', '', '0b000000-0000-0000-0000-00000000000b/0a000000-0000-0000-0000-00000000000a/p.jpg')$$, '42501');
select pg_temp.step('a photo in the conversation''s folder is sent (as the live app does)', $$insert into public.messages (sender_id, receiver_id, body, image_url, attachment) values ('0a000000-0000-0000-0000-00000000000a', '0b000000-0000-0000-0000-00000000000b', '',
  '0a000000-0000-0000-0000-00000000000a/0b000000-0000-0000-0000-00000000000b/ps1.jpg', '{"path":"0a000000-0000-0000-0000-00000000000a/0b000000-0000-0000-0000-00000000000b/ps1.jpg","name":"p.jpg","size":10,"kind":"photo"}')$$);

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
