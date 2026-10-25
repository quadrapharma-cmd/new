-- Structured trade offers (0071–0075, W-trade): what the browser cannot forge on a listing and its items, the kind's required
-- fields, the company verification rule, duplicates and the weekly renewal, matching and its notices, price requests, reserved /
-- sold with ratings, the private box and documents seen by Drugbox, the checklist before agreeing, the agency deal, the
-- distributor profile, the trade dictionary. Runs as the real API roles with a JWT, in one transaction that is rolled back;
-- test data carries the "TX " marker.   psql -f supabase/tests/trade.rls.sql
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
create function pg_temp.n(q text) returns int language plpgsql as $$ declare k int; begin execute q; get diagnostics k = row_count; return k; end $$;
create function pg_temp.id(k text) returns bigint language sql stable as $$ select v::bigint from ids where ids.k = id.k $$;
create function pg_temp.txt(k text) returns text language sql stable as $$ select v from ids where ids.k = txt.k $$;

-- people: S seller (verified company), B buyer (verified company), O outsider (no company), U owner of an unverified company, M Drugbox, C saved search
insert into auth.users (id, email) values ('f1111111-1111-1111-1111-111111111111','tx-s@x.test'),('f2222222-2222-2222-2222-222222222222','tx-b@x.test'),
  ('f3333333-3333-3333-3333-333333333333','tx-o@x.test'),('f4444444-4444-4444-4444-444444444444','tx-u@x.test'),('f5555555-5555-5555-5555-555555555555','tx-m@x.test'),
  ('f6666666-6666-6666-6666-666666666666','tx-c@x.test') on conflict do nothing;
insert into public.profiles (id, name) values ('f1111111-1111-1111-1111-111111111111','TX Seller'),('f2222222-2222-2222-2222-222222222222','TX Buyer'),
  ('f3333333-3333-3333-3333-333333333333','TX Outsider'),('f4444444-4444-4444-4444-444444444444','TX Unverified'),('f5555555-5555-5555-5555-555555555555','TX Drugbox'),
  ('f6666666-6666-6666-6666-666666666666','TX Saver') on conflict (id) do update set name = excluded.name;
update public.profiles set role = 'admin' where id = 'f5555555-5555-5555-5555-555555555555';

select pg_temp.as_server();
select pg_temp.step('three companies (two verified)', $$
  with x as (insert into public.companies (owner_id, name, type, status) values ('f1111111-1111-1111-1111-111111111111', 'TX Seller Co', 'Distributor', 'verified') returning id, slug) insert into ids select 'sco', id::text from x;
  insert into ids select 'sslug', slug from public.companies where id = pg_temp.id('sco');
  with x as (insert into public.companies (owner_id, name, type, status) values ('f2222222-2222-2222-2222-222222222222', 'TX Buyer Co', 'Manufacturer', 'verified') returning id) insert into ids select 'bco', id::text from x;
  insert into ids select 'bslug', slug from public.companies where id = pg_temp.id('bco');
  with x as (insert into public.companies (owner_id, name, type) values ('f4444444-4444-4444-4444-444444444444', 'TX Unverified Co', 'Distributor') returning id) insert into ids select 'uco', id::text from x;
  insert into public.saved_searches (user_id, kind, name, q, filters, alert) values ('f6666666-6666-6666-6666-666666666666', 'market', 'TX panadol', 'بنادول', '{}', 'instant');
  insert into storage.objects (bucket_id, name, owner) values ('documents', 'listings/f1111111-1111-1111-1111-111111111111/doc-a.pdf', 'f1111111-1111-1111-1111-111111111111'),
    ('documents', 'listings/f2222222-2222-2222-2222-222222222222/doc-b.pdf', 'f2222222-2222-2222-2222-222222222222')$$);

-- ══ a stock listing: what the browser cannot write ══
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111');
select pg_temp.step('the seller drafts a stock listing for his company, forging the server''s columns and an unknown field', $$
  with x as (insert into public.products (user_id, name, kind, status, company_id, attrs, search_text, roots, root_words, fingerprint, bumped_at, published_at, closed_reason, docs_checked_at, type, category)
    values ('f1111111-1111-1111-1111-111111111111', 'TX weekly stock', 'stock', 'draft', pg_temp.id('sco'), '{"gov":"giza","credit_days":60,"urgent":true,"evil":"x","gov2":1,"currency":"EGP"}',
            'forged', '{forged}', '{forged}', 'forged', now() + interval '9 days', now() - interval '1 year', 'sold', now(), 'demand', 'cmo') returning id)
  insert into ids select 'p1', id::text from x$$);
select pg_temp.ok('the server''s columns are the server''s (keys, search text, renewal, publication, docs check)', $$(select search_text <> 'forged' and roots <> '{forged}' and fingerprint <> 'forged' and bumped_at is null and published_at is null
  and closed_reason is null and docs_checked_at is null from public.products where id = pg_temp.id('p1'))$$);
select pg_temp.ok('the kind decides the side and the category', $$(select type = 'supply' and category = 'finished' from public.products where id = pg_temp.id('p1'))$$);
select pg_temp.ok('unknown fields are dropped, known ones kept in their type', $$(select attrs = '{"gov":"giza","credit_days":60,"urgent":true,"currency":"EGP"}'::jsonb from public.products where id = pg_temp.id('p1'))$$);
select pg_temp.no('publishing a stock listing without items is refused', $$update public.products set status = 'active' where id = pg_temp.id('p1')$$, '22023');
select pg_temp.no('an item without a quantity cannot be published either', $$
  insert into public.listing_lines (listing_id, name) values (pg_temp.id('p1'), 'TX empty'); update public.products set status = 'active' where id = pg_temp.id('p1')$$, '22023');
select pg_temp.step('remove it again', $$delete from public.listing_lines where listing_id = pg_temp.id('p1')$$);
select pg_temp.no('an item''s key is the database''s (no column grant)', $$insert into public.listing_lines (listing_id, name, qty, unit, item_key) values (pg_temp.id('p1'), 'TX x', 1, 'box', 'forged')$$, '42501');
select pg_temp.no('an unknown unit is refused', $$insert into public.listing_lines (listing_id, name, qty, unit) values (pg_temp.id('p1'), 'TX x', 1, 'barrel')$$, '23514');
select pg_temp.step('two items', $$insert into public.listing_lines (listing_id, pos, name, name_ar, strength, form, qty, unit, expiry, source, origin_country, pack_state, cold) values
  (pg_temp.id('p1'), 0, 'Panadol Extra', 'بنادول اكسترا', '500 mg', 'tab', 120, 'box', '2027-03-01', 'company', 'EG', 'intact', false),
  (pg_temp.id('p1'), 1, 'TX insulin pen', null, '100 iu', 'vial', 25, 'pack', '2026-12-01', 'importer', 'DE', 'intact', true)$$);
select pg_temp.ok('the items carry their keys; the listing''s search text and roots follow them', $$(select l.item_key = 'extra panadol 500mg tab' and p.search_text like '% panadol %' and p.search_text like '% بنادول %' and 'extra panadol' = any(p.roots)
  from public.listing_lines l join public.products p on p.id = l.listing_id where l.listing_id = pg_temp.id('p1') and l.pos = 0)$$);
select pg_temp.step('publish', $$update public.products set status = 'active' where id = pg_temp.id('p1')$$);
select pg_temp.ok('published: active, published_at set by the database, 30 days', $$(select active and published_at is not null and expires_at between now() + interval '29 days' and now() + interval '31 days' from public.products where id = pg_temp.id('p1'))$$);
select pg_temp.no('the same offer again is refused as a duplicate (renew that one)', $$
  with x as (insert into public.products (user_id, name, kind, status, company_id) values ('f1111111-1111-1111-1111-111111111111', 'TX weekly stock', 'stock', 'draft', pg_temp.id('sco')) returning id)
  insert into ids select 'dup', id::text from x;
  insert into public.listing_lines (listing_id, pos, name, name_ar, strength, form, qty, unit, expiry, source, origin_country, pack_state, cold) values
  (pg_temp.id('dup'), 0, 'Panadol Extra', 'بنادول اكسترا', '500 mg', 'tab', 120, 'box', '2027-03-01', 'company', 'EG', 'intact', false),
  (pg_temp.id('dup'), 1, 'TX insulin pen', null, '100 iu', 'vial', 25, 'pack', '2026-12-01', 'importer', 'DE', 'intact', true);
  update public.products set status = 'active' where id = pg_temp.id('dup')$$, '23505');
select pg_temp.no('the seller cannot mark it reserved by a plain update', $$update public.products set status = 'reserved' where id = pg_temp.id('p1')$$, '42501');
select pg_temp.no('…nor change its kind once published', $$update public.products set kind = 'wanted' where id = pg_temp.id('p1')$$, '42501');

-- ══ the company rule (owner): a company page posts as the company only when verified ══
select pg_temp.as_user('f4444444-4444-4444-4444-444444444444');
select pg_temp.no('an unverified company cannot post an offer as the company', $$insert into public.products (user_id, name, company_id, price) values ('f4444444-4444-4444-4444-444444444444', 'TX unverified offer', pg_temp.id('uco'), '5')$$, '42501');
select pg_temp.step('…its owner posts as himself', $$insert into public.products (user_id, name, price) values ('f4444444-4444-4444-4444-444444444444', 'TX unverified offer', '5')$$);
select pg_temp.no('…and cannot move his own listing to the company afterwards', $$update public.products set company_id = pg_temp.id('uco') where name = 'TX unverified offer'$$, '42501');

-- ══ the kind's required fields ══
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111');
select pg_temp.no('toll capacity without GMP is refused', $$insert into public.products (user_id, name, kind, attrs) values ('f1111111-1111-1111-1111-111111111111', 'TX toll', 'toll', '{"forms":["tab"],"min_batch":"1","lead_time":"1"}')$$, '22023');
select pg_temp.no('…GMP yes without its date and issuer is refused', $$insert into public.products (user_id, name, kind, attrs) values ('f1111111-1111-1111-1111-111111111111', 'TX toll', 'toll', '{"forms":["tab"],"min_batch":"1","lead_time":"1","gmp":"yes"}')$$, '22023');
select pg_temp.step('…complete, it publishes (90 days, CMO)', $$with x as (insert into public.products (user_id, name, kind, attrs) values ('f1111111-1111-1111-1111-111111111111', 'TX toll', 'toll',
  '{"forms":["tab","cap","zz"],"min_batch":"150,000","lead_time":"6 weeks","gmp":"yes","gmp_by":"EDA","gmp_date":"2025-04","free_months":["2026-12","2026-13"]}') returning id) insert into ids select 'toll', id::text from x$$);
select pg_temp.ok('…unknown forms and impossible months are dropped', $$(select attrs -> 'forms' = '["tab","cap"]'::jsonb and attrs -> 'free_months' = '["2026-12"]'::jsonb and category = 'cmo' and expires_at > now() + interval '89 days' from public.products where id = pg_temp.id('toll'))$$);
select pg_temp.no('a registration file without its stage is refused', $$insert into public.products (user_id, name, kind, attrs) values ('f1111111-1111-1111-1111-111111111111', 'TX file', 'file_sale', '{"authority":"eda","reg_type":"human"}')$$, '22023');
select pg_temp.step('a registration file with its fields and a private notification number', $$
  with x as (insert into public.products (user_id, name, kind, company_id, attrs) values ('f1111111-1111-1111-1111-111111111111', 'TX Paracetamol file', 'file_sale', pg_temp.id('sco'),
    '{"authority":"eda","reg_type":"human","stage":"notification","public_price":34,"price_increase":"submitted"}') returning id) insert into ids select 'file', id::text from x;
  insert into public.listing_private (listing_id, notif_no) values (pg_temp.id('file'), 'TX-7781')$$);
select pg_temp.ok('a file never expires', $$(select expires_at is null and attrs ->> 'public_price' = '34' from public.products where id = pg_temp.id('file'))$$);
select pg_temp.no('the private box cannot hold documents written by the browser', $$update public.listing_private set doc_paths = '{x}' where listing_id = pg_temp.id('file')$$, '42501');

-- ══ reading: the items and the private box ══
select pg_temp.as_user('f3333333-3333-3333-3333-333333333333');
select pg_temp.ok('another member reads the published listing''s items', $$(select count(*) = 2 from public.listing_lines where listing_id = pg_temp.id('p1'))$$);
select pg_temp.ok('…and listing_items gives them', $$(select jsonb_array_length(public.listing_items(pg_temp.id('p1'))) = 2)$$);
select pg_temp.ok('the private box is not readable directly', $$not exists (select 1 from public.listing_private where listing_id = pg_temp.id('file'))$$);
select pg_temp.no('…nor through its function before it is shared', $$select public.listing_private_get(pg_temp.id('file'))$$, '42501');
select pg_temp.no('another member cannot add items to someone''s listing', $$insert into public.listing_lines (listing_id, name, qty, unit) values (pg_temp.id('p1'), 'TX intruder', 1, 'box')$$, '42501');
select pg_temp.ok('…nor change or remove them (no row reached)', $$pg_temp.n('update public.listing_lines set qty = 1 where listing_id = ' || pg_temp.id('p1')) + pg_temp.n('delete from public.listing_lines where listing_id = ' || pg_temp.id('p1')) = 0$$);
select pg_temp.ok('Arabic search finds the English item (canonical words)', $$(select (public.market_search('بانادول') -> 'rows') @> jsonb_build_array(jsonb_build_object('id', pg_temp.id('p1'))))$$);
select pg_temp.ok('…and «أقراص ٥٠٠» finds tablets 500 mg', $$(select (public.market_search('أقراص ٥٠٠') -> 'rows') @> jsonb_build_array(jsonb_build_object('id', pg_temp.id('p1'))))$$);
select pg_temp.ok('the saved search «بنادول» was alerted when the listing was published', $$true$$);

-- ══ matching ══
select pg_temp.as_user('f2222222-2222-2222-2222-222222222222');
select pg_temp.step('the buyer posts «مطلوب بنادول اكسترا»', $$with x as (insert into public.products (user_id, name, kind, company_id) values ('f2222222-2222-2222-2222-222222222222', 'مطلوب بنادول اكسترا', 'wanted', pg_temp.id('bco')) returning id) insert into ids select 'w', id::text from x$$);
select pg_temp.as_server();
select pg_temp.ok('the pair is recorded once', $$(select count(*) = 1 from public.trade_matches where a = least(pg_temp.id('p1'), pg_temp.id('w')) and b = greatest(pg_temp.id('p1'), pg_temp.id('w')))$$);
select pg_temp.ok('the seller is told (in the app) and the notice is queued for e-mail', $$exists (select 1 from public.notifications n join public.notification_outbox o on o.notification_id = n.id
  where n.user_id = 'f1111111-1111-1111-1111-111111111111' and n.type = 'trade_match' and (n.data ->> 'listing')::bigint = pg_temp.id('w'))$$);
select pg_temp.ok('the buyer gets the summary', $$exists (select 1 from public.notifications where user_id = 'f2222222-2222-2222-2222-222222222222' and type = 'trade_match' and (data ->> 'count')::int = 1)$$);
select pg_temp.ok('the saved search «بنادول» was alerted by the English listing', $$exists (select 1 from public.notifications where user_id = 'f6666666-6666-6666-6666-666666666666' and type = 'saved_search' and (data ->> 'id')::bigint = pg_temp.id('p1'))$$);
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111');
select pg_temp.ok('the seller''s matches list the buyer''s request', $$(select public.my_trade_matches() @> jsonb_build_array(jsonb_build_object('id', pg_temp.id('w'))))$$);
select pg_temp.as_user('f3333333-3333-3333-3333-333333333333');
select pg_temp.ok('an outsider sees no matches of others', $$(select count(*) = 0 from public.trade_matches) and jsonb_array_length(public.my_trade_matches()) = 0$$);

-- ══ renewing: free once a week ══
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111');
select pg_temp.no('renewing just after publishing is refused (the date of the next free renewal)', $$select public.listing_renew(pg_temp.id('p1'))$$, '42501');
select pg_temp.as_user('f3333333-3333-3333-3333-333333333333');
select pg_temp.no('another member cannot renew it', $$select public.listing_renew(pg_temp.id('p1'))$$, '42501');
select pg_temp.as_server(); select pg_temp.step('a week later', $$update public.products set created_at = now() - interval '8 days' where id = pg_temp.id('p1')$$);
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111');
select pg_temp.step('the seller renews', $$select public.listing_renew(pg_temp.id('p1'))$$);
select pg_temp.ok('…it moved up (bumped_at) and runs 30 days from now', $$(select bumped_at > now() - interval '1 minute' and expires_at > now() + interval '29 days' from public.products where id = pg_temp.id('p1'))$$);
select pg_temp.no('…and not again the same week', $$select public.listing_renew(pg_temp.id('p1'))$$, '42501');

-- ══ asking the price ══
select pg_temp.as_user('f3333333-3333-3333-3333-333333333333');
select pg_temp.ok('a member without a company asks the price: a message naming the listing', $$(select public.listing_price_ask(pg_temp.id('p1'), null, '50 box', 'TX please') ->> 'kind' = 'message')$$);
select pg_temp.as_server();
select pg_temp.ok('…the seller has the message, the notice and one inquiry', $$(select count(*) = 1 from public.messages where sender_id = 'f3333333-3333-3333-3333-333333333333' and body like 'Price request:%listing #' || pg_temp.id('p1') || '%')
  and exists (select 1 from public.notifications where user_id = 'f1111111-1111-1111-1111-111111111111' and type = 'price_ask') and (select inquiry_count = 1 from public.products where id = pg_temp.id('p1'))$$);
select pg_temp.as_user('f3333333-3333-3333-3333-333333333333');
select pg_temp.step('two more the same day', $$select public.listing_price_ask(pg_temp.id('p1')); select public.listing_price_ask(pg_temp.id('p1'))$$);
select pg_temp.no('…a fourth is refused', $$select public.listing_price_ask(pg_temp.id('p1'))$$, '42501');
select pg_temp.no('an item of another listing is refused', $$select public.listing_price_ask(pg_temp.id('toll'), (select min(id) from public.listing_lines where listing_id = pg_temp.id('p1')))$$, 'P0002');
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111');
select pg_temp.no('the seller cannot ask his own listing', $$select public.listing_price_ask(pg_temp.id('p1'))$$, '22023');
select pg_temp.as_user('f2222222-2222-2222-2222-222222222222');
select pg_temp.step('company to company', $$insert into ids select 'ask_b', public.listing_price_ask(pg_temp.id('p1'), null, '80 box', null, pg_temp.txt('bslug'))::text$$);
select pg_temp.ok('company to company: a quote request in the deals engine, linked to the listing', $$(select pg_temp.txt('ask_b')::jsonb ->> 'kind' = 'deal')
  and exists (select 1 from public.deals where lines ->> 'listing_id' = pg_temp.id('p1')::text and from_company_id = pg_temp.id('bco') and status = 'sent')$$);
select pg_temp.ok('…naming a company one does not belong to does not open a deal for it: a message instead', $$(select (public.listing_price_ask(pg_temp.id('p1'), null, null, null, pg_temp.txt('sslug')) ->> 'kind') = 'message')
  and not exists (select 1 from public.deals where from_company_id = pg_temp.id('sco') and lines ->> 'listing_id' = pg_temp.id('p1')::text)$$);

-- ══ reserved / sold ══
select pg_temp.as_user('f3333333-3333-3333-3333-333333333333');
select pg_temp.no('an outsider cannot reserve someone''s listing', $$select public.listing_close(pg_temp.id('p1'), 'reserved')$$, '42501');
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111');
select pg_temp.step('the seller reserves it', $$select public.listing_close(pg_temp.id('p1'), 'reserved')$$);
select pg_temp.ok('reserved: still shown (active), status reserved', $$(select active and status = 'reserved' from public.products where id = pg_temp.id('p1'))$$);
select pg_temp.no('…reopening by a plain update is refused', $$update public.products set status = 'active' where id = pg_temp.id('p1')$$, '42501');
select pg_temp.as_user('f3333333-3333-3333-3333-333333333333');
select pg_temp.no('…price requests are closed', $$select public.listing_price_ask(pg_temp.id('p1'))$$, '42501');
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111');
select pg_temp.ok('the members who asked can be named', $$(select public.listing_counterparts(pg_temp.id('p1')) @> '[{"id":"f3333333-3333-3333-3333-333333333333"}]'::jsonb)$$);
select pg_temp.no('naming someone who never wrote is refused', $$select public.listing_close(pg_temp.id('p1'), 'sold', 'f6666666-6666-6666-6666-666666666666')$$, '22023');
select pg_temp.step('sold to the outsider who asked', $$insert into ids select 'oc1', (public.listing_close(pg_temp.id('p1'), 'sold', 'f3333333-3333-3333-3333-333333333333') ->> 'outcome')$$);
select pg_temp.ok('closed as sold; the outcome waits for the buyer', $$(select status = 'closed' and closed_reason = 'sold' and not active from public.products where id = pg_temp.id('p1'))
  and (select status = 'pending' from public.trade_outcomes where id = pg_temp.id('oc1'))$$);
select pg_temp.no('a sold listing is not renewed', $$select public.listing_renew(pg_temp.id('p1'))$$, '22023');
select pg_temp.no('the seller cannot confirm for the buyer', $$select public.trade_outcome_confirm(pg_temp.id('oc1'), true, 5)$$, '42501');
select pg_temp.no('…nor rate before the buyer confirmed', $$select public.trade_outcome_rate(pg_temp.id('oc1'), 5)$$, '22023');
select pg_temp.as_user('f2222222-2222-2222-2222-222222222222');
select pg_temp.ok('another member cannot read the sale', $$not exists (select 1 from public.trade_outcomes where id = pg_temp.id('oc1'))$$);
select pg_temp.no('…nor confirm it', $$select public.trade_outcome_confirm(pg_temp.id('oc1'), true, 5)$$, '42501');
select pg_temp.as_user('f3333333-3333-3333-3333-333333333333');
select pg_temp.no('stars outside 1–5 are refused', $$select public.trade_outcome_confirm(pg_temp.id('oc1'), true, 6)$$, '22023');
select pg_temp.step('the buyer confirms with 4 stars', $$select public.trade_outcome_confirm(pg_temp.id('oc1'), true, 4, 'TX good')$$);
select pg_temp.no('…only once', $$select public.trade_outcome_confirm(pg_temp.id('oc1'), true, 5)$$, '22023');
select pg_temp.ok('no company deal: the buyer has no company (person to company)', $$(select status = 'confirmed' and counterpart_stars = 4 and deal_id is null from public.trade_outcomes where id = pg_temp.id('oc1'))$$);
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111');
select pg_temp.step('the seller rates back', $$select public.trade_outcome_rate(pg_temp.id('oc1'), 5)$$);
select pg_temp.no('…once', $$select public.trade_outcome_rate(pg_temp.id('oc1'), 3)$$, '22023');
select pg_temp.ok('the seller''s trade record: one confirmed sale, 4 stars', $$(select (public.trade_record('f1111111-1111-1111-1111-111111111111') ->> 'confirmed')::int = 1 and (public.trade_record('f1111111-1111-1111-1111-111111111111') ->> 'stars')::numeric = 4)$$);

-- a sale between two companies counts in the deals engine
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111');
select pg_temp.step('a second listing, asked by the buyer''s company', $$with x as (insert into public.products (user_id, name, company_id, price) values ('f1111111-1111-1111-1111-111111111111', 'TX amoxicillin lot', pg_temp.id('sco'), '9') returning id) insert into ids select 'p2', id::text from x$$);
select pg_temp.as_user('f2222222-2222-2222-2222-222222222222'); select pg_temp.step('the buyer asks', $$select public.listing_price_ask(pg_temp.id('p2'), null, '10', null, pg_temp.txt('bslug'))$$);
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111'); select pg_temp.step('sold to the buyer', $$insert into ids select 'oc2', (public.listing_close(pg_temp.id('p2'), 'sold', 'f2222222-2222-2222-2222-222222222222') ->> 'outcome')$$);
select pg_temp.as_user('f2222222-2222-2222-2222-222222222222'); select pg_temp.step('the buyer confirms for his company', $$select public.trade_outcome_confirm(pg_temp.id('oc2'), true, 5, null, pg_temp.txt('bslug'))$$);
select pg_temp.as_server();
select pg_temp.ok('a closed, rated deal from the buyer''s company to the seller''s', $$(select d.status = 'closed' and d.from_company_id = pg_temp.id('bco') and d.to_company_id = pg_temp.id('sco')
  and exists (select 1 from public.deal_events e where e.deal_id = d.id and e.action = 'rate' and (e.data ->> 'stars')::int = 5) from public.deals d join public.trade_outcomes o on o.deal_id = d.id where o.id = pg_temp.id('oc2'))$$);

-- ══ the private box and the documents seen by Drugbox ══
select pg_temp.as_user('f2222222-2222-2222-2222-222222222222');
select pg_temp.step('the buyer asks about the file (a file request between companies)', $$insert into ids select 'dref', (public.listing_respond(pg_temp.id('file'), pg_temp.txt('bslug'), 'TX interested') ->> 'ref')$$);
select pg_temp.ok('…a dossier deal linked to the file', $$(select type = 'dossier' and status = 'requested' from public.deals where ref = pg_temp.txt('dref'))$$);
select pg_temp.no('…a second open request from the same company is refused', $$select public.listing_respond(pg_temp.id('file'), pg_temp.txt('bslug'))$$, '23505');
select pg_temp.as_user('f3333333-3333-3333-3333-333333333333');
select pg_temp.no('a member without a company page cannot open a file deal (writes to the lister instead)', $$select public.listing_respond(pg_temp.id('file'), 'tx-no-such-co')$$, '42501');
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111');
select pg_temp.no('the owner cannot share the box with someone who never asked', $$select public.listing_private_share(pg_temp.id('file'), 'f6666666-6666-6666-6666-666666666666')$$, '22023');
select pg_temp.step('the owner shares it with the buyer', $$select public.listing_private_share(pg_temp.id('file'), 'f2222222-2222-2222-2222-222222222222')$$);
select pg_temp.no('documents of another member''s folder are refused', $$select public.listing_docs_submit(pg_temp.id('file'), array['listings/f2222222-2222-2222-2222-222222222222/doc-b.pdf'])$$, '42501');
select pg_temp.no('…and files that were not uploaded', $$select public.listing_docs_submit(pg_temp.id('file'), array['listings/f1111111-1111-1111-1111-111111111111/doc-none.pdf'])$$, '42501');
select pg_temp.step('the owner sends his document to Drugbox', $$select public.listing_docs_submit(pg_temp.id('file'), array['listings/f1111111-1111-1111-1111-111111111111/doc-a.pdf'])$$);
select pg_temp.no('the owner cannot mark his documents seen', $$select public.listing_docs_review(pg_temp.id('file'), true)$$, '42501');
select pg_temp.as_user('f2222222-2222-2222-2222-222222222222');
select pg_temp.ok('the buyer it was shared with reads the notification number, not the documents', $$(select x ->> 'notif_no' = 'TX-7781' and x -> 'docs' = '[]'::jsonb from (select public.listing_private_get(pg_temp.id('file')) x) y)$$);
select pg_temp.ok('…nor the review queue (empty for members)', $$jsonb_array_length(public.listing_docs_queue()) = 0$$);
select pg_temp.as_user('f5555555-5555-5555-5555-555555555555');
select pg_temp.ok('Drugbox sees it in the queue with the documents', $$(select public.listing_docs_queue() @> jsonb_build_array(jsonb_build_object('id', pg_temp.id('file'))))$$);
select pg_temp.no('a refusal needs a reason', $$select public.listing_docs_review(pg_temp.id('file'), false)$$, '22023');
select pg_temp.step('Drugbox marks them seen', $$select public.listing_docs_review(pg_temp.id('file'), true)$$);
select pg_temp.as_server();
select pg_temp.ok('…the card shows it and the owner is told', $$(select docs_checked_at is not null from public.products where id = pg_temp.id('file'))
  and exists (select 1 from public.notifications where user_id = 'f1111111-1111-1111-1111-111111111111' and type = 'document_reviewed' and (data ->> 'listing')::bigint = pg_temp.id('file'))$$);
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111');
select pg_temp.step('new documents: Drugbox looks again', $$select public.listing_docs_submit(pg_temp.id('file'), array['listings/f1111111-1111-1111-1111-111111111111/doc-a.pdf'])$$);
select pg_temp.ok('…the badge is gone until then', $$(select docs_checked_at is null from public.products where id = pg_temp.id('file'))$$);

-- ══ «اتفقنا» on a file deal needs the checklist ══
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111');
select pg_temp.step('the owner signs the NDA and shares', $$select public.deal_act(pg_temp.txt('dref'), 'sign_nda'); select public.deal_act(pg_temp.txt('dref'), 'share', '{"note":"TX data room"}')$$);
select pg_temp.as_user('f2222222-2222-2222-2222-222222222222');
select pg_temp.no('agreeing without the checklist is refused', $$select public.deal_act(pg_temp.txt('dref'), 'agree')$$, '22023');
select pg_temp.no('…with one box missing too', $$select public.deal_act(pg_temp.txt('dref'), 'agree', '{"checklist":{"notif_seen":true,"stage_understood":true,"price_increase_checked":true,"transfer_needs_approval":true}}')$$, '22023');
select pg_temp.step('…with every box it is agreed', $$select public.deal_act(pg_temp.txt('dref'), 'agree', '{"checklist":{"notif_seen":true,"stage_understood":true,"price_increase_checked":true,"transfer_needs_approval":true,"docs_reviewed":true}}')$$);
select pg_temp.ok('…agreed, the checklist kept with the event', $$(select d.status = 'agreed' and (e.data -> 'checklist' ->> 'docs_reviewed') = 'true' from public.deals d join public.deal_events e on e.deal_id = d.id and e.action = 'agree' where d.ref = pg_temp.txt('dref'))$$);

-- ══ agency both ways ══
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111');
select pg_temp.no('an agency without governorates is refused', $$insert into public.products (user_id, name, kind, attrs) values ('f1111111-1111-1111-1111-111111111111', 'TX agency', 'agency', '{"cats":["supplements"]}')$$, '22023');
select pg_temp.step('an agency for supplements in Asyut and Sohag', $$with x as (insert into public.products (user_id, name, kind, company_id, attrs) values ('f1111111-1111-1111-1111-111111111111', 'TX vitamins agency', 'agency', pg_temp.id('sco'),
  '{"cats":["supplements"],"govs":["asyut","sohag","nowhere"],"exclusive":true,"bonus_pct":7}') returning id) insert into ids select 'ag', id::text from x$$);
select pg_temp.ok('…an unknown governorate is dropped', $$(select attrs -> 'govs' = '["asyut","sohag"]'::jsonb from public.products where id = pg_temp.id('ag'))$$);
select pg_temp.as_user('f2222222-2222-2222-2222-222222222222');
select pg_temp.step('a distributor in Asyut looking for supplements', $$with x as (insert into public.products (user_id, name, kind, company_id, attrs) values ('f2222222-2222-2222-2222-222222222222', 'TX upper distributor', 'distributor', pg_temp.id('bco'),
  '{"cats":["supplements"],"govs":["asyut"]}') returning id) insert into ids select 'dist', id::text from x$$);
select pg_temp.as_server();
select pg_temp.ok('the agency and the distributor match', $$exists (select 1 from public.trade_matches where a = least(pg_temp.id('ag'), pg_temp.id('dist')) and b = greatest(pg_temp.id('ag'), pg_temp.id('dist')))$$);
select pg_temp.as_user('f2222222-2222-2222-2222-222222222222');
select pg_temp.step('the distributor applies', $$insert into ids select 'aref', (public.listing_respond(pg_temp.id('ag'), pg_temp.txt('bslug'), 'TX we cover Upper Egypt') ->> 'ref')$$);
select pg_temp.no('…the distributor cannot open the talks himself', $$select public.deal_act(pg_temp.txt('aref'), 'talk')$$, '42501');
select pg_temp.as_user('f1111111-1111-1111-1111-111111111111');
select pg_temp.step('the owner opens the talks and agrees', $$select public.deal_act(pg_temp.txt('aref'), 'talk'); select public.deal_act(pg_temp.txt('aref'), 'agree')$$);
select pg_temp.ok('an agreed agency deal', $$(select type = 'agency' and status = 'agreed' from public.deals where ref = pg_temp.txt('aref'))$$);
select pg_temp.as_user('f2222222-2222-2222-2222-222222222222');
select pg_temp.step('the distributor keeps his profile', $$insert into public.distributor_profiles (company_id, govs, cats, warehouses, cold_chain) values (pg_temp.id('bco'), '{asyut,minya}', '{supplements}', 2, true)$$);
select pg_temp.no('…an unknown governorate is refused', $$update public.distributor_profiles set govs = '{atlantis}' where company_id = pg_temp.id('bco')$$, '23514');
select pg_temp.as_user('f3333333-3333-3333-3333-333333333333');
select pg_temp.ok('members read it', $$exists (select 1 from public.distributor_profiles where company_id = pg_temp.id('bco') and updated_by = 'f2222222-2222-2222-2222-222222222222')$$);
select pg_temp.no('another member cannot write a company''s profile', $$insert into public.distributor_profiles (company_id, govs) values (pg_temp.id('sco'), '{cairo}')$$, '42501');
select pg_temp.ok('…nor change it (no row reached)', $$pg_temp.n('update public.distributor_profiles set warehouses = 99 where company_id = ' || pg_temp.id('bco')) = 0$$);

-- ══ the dictionary ══
select pg_temp.no('a member cannot add trade words', $$select public.trade_term_add('ملتي', 'multi')$$, '42501');
select pg_temp.no('…nor write the dictionary directly', $$insert into public.trade_terms (term, canon, kind) values ('x', 'x', 'drug')$$, '42501');
select pg_temp.as_user('f5555555-5555-5555-5555-555555555555');
select pg_temp.step('Drugbox adds a drug name', $$select public.trade_term_add('سنتروم', 'centrum')$$);
select pg_temp.ok('…both spellings reach it', $$public.trade_key('Centrum') = 'centrum' and public.trade_key('سنتروم') = 'centrum'$$);

-- ══ signed out ══
select pg_temp.as_anon();
select pg_temp.no('anon cannot search the marketplace', $$select public.market_search('بنادول')$$, '42501');
select pg_temp.ok('anon reads no items, matches, outcomes, private boxes or profiles', $$(select count(*) from public.listing_lines) + (select count(*) from public.trade_matches) + (select count(*) from public.trade_outcomes)
  + (select count(*) from public.listing_private) + (select count(*) from public.distributor_profiles) + (select count(*) from public.trade_terms) = 0$$);
select pg_temp.no('anon cannot ask a price', $$select public.listing_price_ask(1)$$, '42501');
select pg_temp.no('anon cannot reach the review queue', $$select public.listing_docs_queue()$$, '42501');

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
