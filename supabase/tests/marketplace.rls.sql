-- Marketplace (0054, B-06…B-10): listing fields the browser cannot forge, status / expiry, views and inquiries counted by the
-- database, quotes on requests through the deals engine, intent matching, saved listings, the COA in private storage.
-- Runs as the real API roles with a JWT, in one transaction that is rolled back; test data carries the "MK " marker.
--   psql -f supabase/tests/marketplace.rls.sql
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

-- people: a seller (with a company), a buyer (with a company), an outsider, a member who needs APIs, Drugbox
insert into auth.users (id, email) values ('e1111111-1111-1111-1111-111111111111','mk-seller@x.test'),('e2222222-2222-2222-2222-222222222222','mk-buyer@x.test'),
  ('e3333333-3333-3333-3333-333333333333','mk-out@x.test'),('e4444444-4444-4444-4444-444444444444','mk-intent@x.test'),('e5555555-5555-5555-5555-555555555555','mk-admin@x.test') on conflict do nothing;
insert into public.profiles (id, name) values ('e1111111-1111-1111-1111-111111111111','MK Seller'),('e2222222-2222-2222-2222-222222222222','MK Buyer'),
  ('e3333333-3333-3333-3333-333333333333','MK Outsider'),('e4444444-4444-4444-4444-444444444444','MK Intent'),('e5555555-5555-5555-5555-555555555555','MK Admin') on conflict (id) do update set name = excluded.name;
update public.profiles set role = 'admin' where id = 'e5555555-5555-5555-5555-555555555555';
update public.profiles set intents = '{"api": "i-have"}' where id = 'e4444444-4444-4444-4444-444444444444';

select pg_temp.as_server();
select pg_temp.step('two companies', $$
  with x as (insert into public.companies (owner_id, name, type) values ('e1111111-1111-1111-1111-111111111111', 'MK Seller Co', 'Distributor') returning id, slug) insert into ids select 'sco', id::text from x;
  with x as (insert into public.companies (owner_id, name, type) values ('e2222222-2222-2222-2222-222222222222', 'MK Buyer Co', 'Manufacturer') returning id) insert into ids select 'bco', id::text from x;
  insert into storage.objects (bucket_id, name, owner) values ('documents', 'listings/e1111111-1111-1111-1111-111111111111/coa-a.pdf', 'e1111111-1111-1111-1111-111111111111')$$);

-- ══ a listing ══
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.step('the seller lists for his company with a COA, trying to set counters, verified certificates and a renewal date', $$
  with x as (insert into public.products (user_id, type, category, name, price, unit, moq, company_id, coa_path, view_count, inquiry_count, certs_verified, renewed_at, docs)
    values ('e1111111-1111-1111-1111-111111111111', 'supply', 'api', 'MK Metformin', '5.80', 'kg', '500 kg', pg_temp.id('sco'), 'listings/e1111111-1111-1111-1111-111111111111/coa-a.pdf', 999, 99, '{WHO-GMP}', now() + interval '5 years', '{WHO-GMP}') returning id)
  insert into ids select 'p1', id::text from x$$);
select pg_temp.ok('counters, verified certificates and the renewal are the database''s', $$(select view_count = 0 and inquiry_count = 0 and certs_verified = '{}' and renewed_at is null from public.products where id = pg_temp.id('p1'))$$);
select pg_temp.ok('a bare price is in US dollars; it expires in 30 days', $$(select currency = 'USD' and expires_at between now() + interval '29 days' and now() + interval '31 days' from public.products where id = pg_temp.id('p1'))$$);
select pg_temp.no('listing for a company one does not belong to is refused', $$insert into public.products (user_id, name, company_id) values ('e1111111-1111-1111-1111-111111111111', 'MK fake', pg_temp.id('bco'))$$, '42501');
select pg_temp.no('a COA path of someone else is refused', $$insert into public.products (user_id, name, coa_path) values ('e1111111-1111-1111-1111-111111111111', 'MK fake2', 'listings/e2222222-2222-2222-2222-222222222222/x.pdf')$$, '42501');
select pg_temp.step('the seller pauses it', $$update public.products set status = 'paused' where id = pg_temp.id('p1')$$);
select pg_temp.ok('paused: not active', $$(select not active from public.products where id = pg_temp.id('p1'))$$);
select pg_temp.as_user('e2222222-2222-2222-2222-222222222222');
select pg_temp.ok('a paused listing is not visible to others', $$not exists (select 1 from public.products where id = pg_temp.id('p1'))$$);
select pg_temp.ok('…nor in the marketplace search', $$(select (public.market_search('MK Metformin') ->> 'total')::int = 0)$$);
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.ok('the owner still reads it (My Listings)', $$(select count(*) = 1 from jsonb_array_elements(public.my_listings()) x where (x ->> 'id')::bigint = pg_temp.id('p1'))$$);
select pg_temp.step('…and resumes it', $$update public.products set status = 'active' where id = pg_temp.id('p1')$$);
select pg_temp.as_user('e2222222-2222-2222-2222-222222222222');
select pg_temp.ok('active again: in the search with its company and COA flag (not the path)', $$(select (r -> 'rows' -> 0 -> 'co' ->> 'name') = 'MK Seller Co' and (r -> 'rows' -> 0 ->> 'has_coa')::boolean and position('coa-a' in r::text) = 0 from (select public.market_search('MK Metformin') r) x)$$);
select pg_temp.ok('a signed-in member may open the COA of an active listing', $$public.can_read_document('listings/e1111111-1111-1111-1111-111111111111/coa-a.pdf')$$);
select pg_temp.no('another member cannot change the listing', $$update public.products set name = 'MK hacked' where id = pg_temp.id('p1') returning 1/0$$, '22012');
select pg_temp.ok('…the row is unchanged', $$(select name from public.products where id = pg_temp.id('p1')) = 'MK Metformin'$$);
select pg_temp.no('another member cannot renew it', $$select public.listing_renew(pg_temp.id('p1'))$$, '42501');
-- views and inquiries
select pg_temp.step('the buyer views it twice the same day and contacts the seller twice', $$select public.listing_view(pg_temp.id('p1')); select public.listing_view(pg_temp.id('p1'));
  select public.listing_contact(pg_temp.id('p1'), 'MK is it available?'); select public.listing_contact(pg_temp.id('p1'), 'MK and the COA?')$$);
select pg_temp.as_server();
select pg_temp.ok('one view and one inquiry are counted; two messages reached the seller naming the listing', $$(select view_count = 1 and inquiry_count = 1 from public.products where id = pg_temp.id('p1'))
  and (select count(*) from public.messages where sender_id = 'e2222222-2222-2222-2222-222222222222' and receiver_id = 'e1111111-1111-1111-1111-111111111111' and body like 'Re: MK Metformin (listing #%') = 2$$);
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.ok('the owner''s own view is not counted', $$public.listing_view(pg_temp.id('p1')) = false$$);
select pg_temp.no('the owner cannot contact himself', $$select public.listing_contact(pg_temp.id('p1'), 'MK me')$$, '22023');
select pg_temp.ok('the owner reads who asked', $$(select count(*) from public.listing_inquiries where listing_id = pg_temp.id('p1')) = 1$$);
select pg_temp.as_user('e3333333-3333-3333-3333-333333333333');
select pg_temp.ok('an outsider does not read the inquiries', $$(select count(*) from public.listing_inquiries where listing_id = pg_temp.id('p1')) = 0$$);
select pg_temp.ok('nobody reads the view log (it answers with nothing)', $$(select count(*) = 0 from public.listing_views)$$);
-- demand, matching and quotes
select pg_temp.as_user('e2222222-2222-2222-2222-222222222222');
select pg_temp.step('the buyer posts a demand for an API for his company', $$with x as (insert into public.products (user_id, type, category, name, moq, company_id) values ('e2222222-2222-2222-2222-222222222222', 'demand', 'api', 'MK Ciprofloxacin wanted', '2 MT', pg_temp.id('bco')) returning id) insert into ids select 'd1', id::text from x$$);
select pg_temp.as_server();
select pg_temp.ok('the member who has APIs to sell is told (once), the buyer himself not', $$(select count(*) from public.notifications where type = 'listing_match' and user_id = 'e4444444-4444-4444-4444-444444444444' and (data ->> 'listing')::bigint = pg_temp.id('d1')) = 1
  and not exists (select 1 from public.notifications where type = 'listing_match' and user_id = 'e2222222-2222-2222-2222-222222222222')$$);
select pg_temp.as_user('e3333333-3333-3333-3333-333333333333');
select pg_temp.no('a person without a company cannot quote', $$select public.listing_quote(pg_temp.id('d1'), (select slug from public.companies where id = pg_temp.id('sco')), 'US$ 20')$$, '42501');
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.no('a quote needs a price', $$select public.listing_quote(pg_temp.id('d1'), (select slug from public.companies where id = pg_temp.id('sco')), 'soon')$$, '22023');
select pg_temp.step('the seller quotes for his company', $$select public.listing_quote(pg_temp.id('d1'), (select slug from public.companies where id = pg_temp.id('sco')), 'US$ 20 per kg', '2 MT', '3 weeks')$$);
select pg_temp.ok('a quote deal from the buyer''s company to the seller''s, at "quoted" with the offer', $$(select count(*) = 1 from public.deals d where d.type = 'quote' and d.status = 'quoted' and d.from_company_id = pg_temp.id('bco') and d.to_company_id = pg_temp.id('sco') and d.offer ->> 'price' = 'US$ 20 per kg' and (d.lines ->> 'listing_id')::bigint = pg_temp.id('d1'))$$);
select pg_temp.no('…once (revise it instead)', $$select public.listing_quote(pg_temp.id('d1'), (select slug from public.companies where id = pg_temp.id('sco')), 'US$ 19')$$, '23505');
select pg_temp.as_user('e2222222-2222-2222-2222-222222222222');
select pg_temp.ok('the buyer sees the quote and may accept it (the engine''s next step)', $$(select status from public.deals where type = 'quote' and (lines ->> 'listing_id')::bigint = pg_temp.id('d1')) = 'quoted'$$);
select pg_temp.step('the buyer accepts', $$select public.deal_act((select ref from public.deals where type = 'quote' and (lines ->> 'listing_id')::bigint = pg_temp.id('d1')), 'accept', '{}'::jsonb, 'from')$$);
select pg_temp.ok('accepted', $$(select status from public.deals where type = 'quote' and (lines ->> 'listing_id')::bigint = pg_temp.id('d1')) = 'accepted'$$);
-- saved listings
select pg_temp.step('the buyer saves the listing', $$insert into public.saved_listings (listing_id) values (pg_temp.id('p1'))$$);
select pg_temp.no('…not for someone else', $$insert into public.saved_listings (user_id, listing_id) values ('e3333333-3333-3333-3333-333333333333', pg_temp.id('p1'))$$, '42501');
select pg_temp.as_user('e3333333-3333-3333-3333-333333333333');
select pg_temp.ok('nobody else reads it', $$(select count(*) from public.saved_listings) = 0$$);
-- Drugbox verifies a certificate
select pg_temp.as_user('e5555555-5555-5555-5555-555555555555');
select pg_temp.step('Drugbox marks WHO-GMP checked (and tries a certificate the seller never claimed)', $$select public.listing_verify_certs(pg_temp.id('p1'), '{WHO-GMP,CEP}')$$);
select pg_temp.as_user('e1111111-1111-1111-1111-111111111111');
select pg_temp.step('the owner edits the listing (title)', $$update public.products set name = 'MK Metformin HCl' where id = pg_temp.id('p1')$$);
select pg_temp.ok('the checked certificate stays (the owner cannot set or clear it)', $$(select certs_verified = '{WHO-GMP}' and name = 'MK Metformin HCl' from public.products where id = pg_temp.id('p1'))$$);
select pg_temp.step('the owner renews', $$select public.listing_renew(pg_temp.id('p1'))$$);
select pg_temp.ok('renewed now', $$(select renewed_at > now() - interval '1 minute' from public.products where id = pg_temp.id('p1'))$$);
select pg_temp.no('the owner cannot mark his own certificates checked', $$select public.listing_verify_certs(pg_temp.id('p1'), '{WHO-GMP}')$$, '42501');
select pg_temp.as_anon();
select pg_temp.no('anon cannot search the marketplace', $$select public.market_search('MK')$$, '42501');
select pg_temp.no('anon cannot quote', $$select public.listing_quote(1, 'x', '1')$$, '42501');

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
