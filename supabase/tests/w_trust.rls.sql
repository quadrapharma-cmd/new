-- Trust, safety and groups (area w-trust, 0090–0094): who stands behind a trade offer (verified company / individual / broker,
-- the trade profile first), sensitive posts held for Drugbox review, trader reports with evidence + right to reply + two
-- moderators, the supplier rating the buyer, phone verification that keeps the number private, group admin tools and invite links.
-- Runs as the real API roles with a JWT, in one transaction that is rolled back; test data carries the "WT " marker.
-- Run on a fresh database (stub + migrations): psql -f supabase/tests/w_trust.rls.sql
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
-- a refusal that names its reason: the DX hint the app reads
create function pg_temp.nohint(p_name text, q text, h text) returns void language plpgsql as $$ declare hh text; begin
  execute q; raise exception 'the statement was allowed' using errcode = 'DB001';
  exception when others then get stacked diagnostics hh = pg_exception_hint;
    insert into r(name, ok, err) values (p_name, coalesce(hh, '') = h, case when coalesce(hh, '') <> h then sqlstate || ' [' || coalesce(hh, '') || ']: ' || sqlerrm end); end $$;
create function pg_temp.id(k text) returns bigint language sql stable as $$ select v::bigint from ids where ids.k = id.k $$;
create function pg_temp.u(n int) returns uuid language sql immutable as $$ select ('a9000000-0000-0000-0000-0000000000' || lpad(n::text, 2, '0'))::uuid $$;
create function pg_temp.act(n int) returns void language sql as $$ select pg_temp.as_user(pg_temp.u(n)::text) $$;
create function pg_temp.told(n int, t text) returns bigint language sql stable security definer as $$ select count(*) from public.notifications where user_id = pg_temp.u(n) and type = t $$;

-- 1 A trader (member), 2 B another member, 3 C owner of an unverified company, 4 V owner of a verified company, 5 M1 moderator,
-- 6 M2 moderator, 7 X Drugbox admin, 8 G group admin, 9 J joiner, 10 K another joiner
insert into auth.users (id, email) select pg_temp.u(n), 'wt' || n || '@x' from generate_series(1, 10) n on conflict do nothing;
insert into public.profiles (id, name, role) select pg_temp.u(n), 'WT Member ' || chr(64 + n), case when n in (5, 6) then 'moderator' when n = 7 then 'admin' else 'user' end
  from generate_series(1, 10) n on conflict (id) do update set name = excluded.name, role = excluded.role;
select pg_temp.as_server();
select pg_temp.step('companies: C unverified, V verified', $$with a as (insert into public.companies (owner_id, name, slug, status) values (pg_temp.u(3), 'WT Unverified Pharma', 'wt-unverified', 'pending') returning id),
  b as (insert into public.companies (owner_id, name, slug, status) values (pg_temp.u(4), 'WT Verified Pharma', 'wt-verified', 'verified') returning id)
  insert into ids select 'coU', id::text from a union all select 'coV', id::text from b$$);
select pg_temp.step('storage: A''s broker authorisation, A''s and B''s report evidence', $$insert into storage.objects (bucket_id, name) values
  ('documents', 'listings/' || pg_temp.u(1) || '/auth.pdf'), ('documents', 'trader-reports/' || pg_temp.u(2) || '/invoice.pdf'), ('documents', 'trader-reports/' || pg_temp.u(1) || '/receipt.pdf')$$);

-- ══ 1. trade profile, verified company, broker (0090) ══
select pg_temp.act(1);
select pg_temp.nohint('A cannot post an offer before the trade profile', $$insert into public.products (user_id, name, type, category) values (pg_temp.u(1), 'WT Paracetamol API', 'supply', 'api')$$, 'DX410');
select pg_temp.step('A fills the trade profile', $$insert into public.trade_profiles (user_id, role, company, governorate, sells) values (pg_temp.u(1), 'distributor', ' WT Nile Trade ', 'Giza', 'APIs and excipients')$$);
select pg_temp.no('a pharmacy is not a trading role', $$update public.trade_profiles set role = 'pharmacy' where user_id = pg_temp.u(1)$$, '23514');
select pg_temp.no('a governorate from the list only', $$update public.trade_profiles set governorate = 'Nowhere' where user_id = pg_temp.u(1)$$, '23514');
select pg_temp.no('it says what they buy or sell', $$update public.trade_profiles set sells = null, buys = ' ' where user_id = pg_temp.u(1)$$, '23514');
select pg_temp.ok('… trimmed by the database', $$(select company from public.trade_profiles where user_id = pg_temp.u(1)) = 'WT Nile Trade'$$);
select pg_temp.act(2);
select pg_temp.no('B cannot write a trade profile for A', $$insert into public.trade_profiles (user_id, role, governorate, sells) values (pg_temp.u(1), 'supplier', 'Cairo', 'x y') on conflict (user_id) do update set company = 'hacked'$$, '42501');
select pg_temp.act(2);
select pg_temp.step('B tries to change A''s card (no row changes)', $$update public.trade_profiles set company = 'hacked' where user_id = pg_temp.u(1)$$);
select pg_temp.ok('… A''s card is unchanged', $$(select company from public.trade_profiles where user_id = pg_temp.u(1)) = 'WT Nile Trade'$$);
select pg_temp.ok('B reads A''s trade card (members do)', $$(public.trade_card(pg_temp.u(1)) -> 'profile' ->> 'governorate') = 'Giza'$$);
select pg_temp.act(1);
select pg_temp.step('A posts as an individual', $$with p as (insert into public.products (user_id, name, type, category, description) values (pg_temp.u(1), 'WT Paracetamol API', 'supply', 'api', 'BP grade, 500 kg') returning id) insert into ids select 'pA', id::text from p$$);
select pg_temp.ok('… posted_as is individual', $$(select posted_as from public.products where id = pg_temp.id('pA')) = 'individual'$$);
select pg_temp.nohint('a broker offer needs the owner named', $$insert into public.products (user_id, name, type, category, posted_as, broker_commission, broker_auth_path) values (pg_temp.u(1), 'WT Dossier', 'supply', 'registration', 'broker', 3, 'listings/' || pg_temp.u(1) || '/auth.pdf')$$, 'DX413');
select pg_temp.nohint('a broker offer needs the commission', $$insert into public.products (user_id, name, type, category, posted_as, broker_for, broker_auth_path) values (pg_temp.u(1), 'WT Dossier', 'supply', 'registration', 'broker', 'WT Owner Co', 'listings/' || pg_temp.u(1) || '/auth.pdf')$$, 'DX414');
select pg_temp.nohint('a broker offer needs the authorisation uploaded', $$insert into public.products (user_id, name, type, category, posted_as, broker_for, broker_commission, broker_auth_path) values (pg_temp.u(1), 'WT Dossier', 'supply', 'registration', 'broker', 'WT Owner Co', 3, 'listings/' || pg_temp.u(1) || '/missing.pdf')$$, 'DX415');
select pg_temp.nohint('… and in A''s own folder', $$insert into public.products (user_id, name, type, category, posted_as, broker_for, broker_commission, broker_auth_path) values (pg_temp.u(1), 'WT Dossier', 'supply', 'registration', 'broker', 'WT Owner Co', 3, 'trader-reports/' || pg_temp.u(2) || '/invoice.pdf')$$, 'DX415');
select pg_temp.step('A posts a broker offer with everything', $$with p as (insert into public.products (user_id, name, type, category, posted_as, broker_for, broker_commission, broker_auth_path) values (pg_temp.u(1), 'WT Amoxicillin dossier', 'supply', 'registration', 'broker', 'WT Owner Co', 2.5, 'listings/' || pg_temp.u(1) || '/auth.pdf') returning id) insert into ids select 'pB', id::text from p$$);
select pg_temp.no('commission at most 50 %', $$update public.products set broker_commission = 60 where id = pg_temp.id('pB')$$, '23514');
select pg_temp.nohint('an individual offer carries no broker details', $$insert into public.products (user_id, name, type, category, broker_for) values (pg_temp.u(1), 'WT X', 'supply', 'api', 'Someone')$$, 'DX413');
select pg_temp.nohint('only Drugbox posts as Drugbox', $$insert into public.products (user_id, name, type, category, posted_as) values (pg_temp.u(1), 'WT X', 'supply', 'api', 'drugbox')$$, 'DX416');
select pg_temp.act(2);
select pg_temp.ok('B reads the broker offer and its authorisation (the proof)', $$(select broker_for from public.products where id = pg_temp.id('pB')) = 'WT Owner Co' and public.can_read_document('listings/' || pg_temp.u(1) || '/auth.pdf')$$);
-- company offers: the badge first
select pg_temp.act(3);
select pg_temp.step('C fills the trade profile', $$insert into public.trade_profiles (user_id, role, governorate, buys) values (pg_temp.u(3), 'manufacturer', 'Alexandria', 'Packaging')$$);
select pg_temp.nohint('C cannot post AS the unverified company', $$insert into public.products (user_id, name, type, category, company_id) values (pg_temp.u(3), 'WT Blister foil', 'demand', 'other', pg_temp.id('coU'))$$, 'DX412');
select pg_temp.nohint('… nor say "company" with no company', $$insert into public.products (user_id, name, type, category, posted_as) values (pg_temp.u(3), 'WT Blister foil', 'demand', 'other', 'company')$$, 'DX411');
select pg_temp.step('C posts the same as themselves', $$insert into public.products (user_id, name, type, category) values (pg_temp.u(3), 'WT Blister foil', 'demand', 'other')$$);
select pg_temp.nohint('C cannot move an own offer to the unverified company later', $$update public.products set company_id = pg_temp.id('coU'), posted_as = 'company' where user_id = pg_temp.u(3) and name = 'WT Blister foil'$$, 'DX412');
select pg_temp.act(4);
select pg_temp.step('V fills the trade profile', $$insert into public.trade_profiles (user_id, role, governorate, sells) values (pg_temp.u(4), 'manufacturer', 'Cairo', 'Finished products')$$);
select pg_temp.step('V posts AS the verified company', $$insert into public.products (user_id, name, type, category, company_id) values (pg_temp.u(4), 'WT Tablets 500mg', 'supply', 'finished', pg_temp.id('coV'))$$);
select pg_temp.ok('… posted_as is company', $$(select posted_as from public.products where name = 'WT Tablets 500mg') = 'company'$$);
select pg_temp.no('V cannot post for a company V does not belong to', $$insert into public.products (user_id, name, type, category, company_id) values (pg_temp.u(4), 'WT Other', 'supply', 'finished', pg_temp.id('coU'))$$, '42501');
-- deal-room listings follow the same rules
select pg_temp.as_server();
select pg_temp.step('a deal room with C and A as members', $$with g as (insert into public.groups (name, topic, type, created_by) values ('WT Deal Room', 'DEAL ROOM', 'private', pg_temp.u(3)) returning id),
  m as (insert into public.group_members (group_id, user_id, role) select id, pg_temp.u(3), 'admin' from g union all select id, pg_temp.u(1), 'member' from g returning group_id)
  insert into ids select distinct 'room', group_id::text from m$$);
select pg_temp.act(3);
select pg_temp.nohint('deal room: not as the unverified company', $$insert into public.group_listings (group_id, company_id, kind, title) values (pg_temp.id('room'), pg_temp.id('coU'), 'rfq', 'WT Need foil')$$, 'DX412');
select pg_temp.step('deal room: as themselves', $$insert into public.group_listings (group_id, kind, title) values (pg_temp.id('room'), 'rfq', 'WT Need foil')$$);
select pg_temp.ok('… individual', $$(select posted_as from public.group_listings where title = 'WT Need foil') = 'individual'$$);

-- the words: trade phrases that must pass, and the sensitive ones each rule must catch (EN + AR, as the trade writes them)
select pg_temp.as_server();
select pg_temp.ok('ordinary B2B trade phrases are not held', $$(select bool_and(cardinality(private.review_topics(x)) = 0) from unnest(array[
  'متوفر باراسيتامول API بكميات للمصانع', 'مطلوب ملف تسجيل أموكسيسيلين', 'تول تصنيع أقراص بالمصنع عندنا', 'وكالة توزيع حصرية للدلتا', 'الدفع آجل ٦٠ يوم',
  'Available: Metformin HCl BP 500 kg, CEP, COA attached', 'Wanted: toll manufacturing for effervescent tablets', 'Distribution rights for KSA and UAE',
  'تخدير موضعي ليدوكايين API للمصانع', 'جدول تسعير الكميات مرفق', 'مستلزمات تعبئة وتغليف بلستر', 'for patients with diabetes: metformin XR dossier for licensing',
  'منتج مفرط الحساسية؟ لا — مسحوق ناعم', 'Packaging supplier: blister foil, 2 tons']) x)$$);
select pg_temp.ok('the sensitive phrases are each caught by their rule', $$(select bool_and(private.review_topics(x[1]) @> array[x[2]]) from (values
  (array['محتاج دوا لمريض ضروري', 'retail']), (array['متوفر بالقطاعي للصيدليات', 'retail']), (array['علبة واحدة بالروشتة', 'retail']), (array['we sell to pharmacies at good prices', 'retail']),
  (array['متوفر ترامادول ٢٢٥', 'controlled']), (array['والترامادول موجود', 'controlled']), (array['أدوية الجدول متاحة', 'controlled']), (array['pregabalin 300 available', 'controlled']),
  (array['استيراد لحساب الغير على سجلنا', 'import']), (array['import on behalf of clients, our licence', 'import']),
  (array['عندنا عقود صورية للتسجيل', 'sham']), (array['fake invoices available', 'sham']),
  (array['ادخل الجروب https://chat.whatsapp.com/Abc', 'invite']), (array['join t.me/pharma_eg', 'invite'])) v(x))$$);

-- ══ 2. held for review (0091) ══
select pg_temp.act(1);
select pg_temp.step('A posts a retail sale for a patient (Arabic)', $$with p as (insert into public.posts (user_id, body) values (pg_temp.u(1), 'WT متوفر علبة واحدة للمريض بالروشتة') returning id) insert into ids select 'held', id::text from p$$);
select pg_temp.step('A posts a WhatsApp invite link', $$with p as (insert into public.posts (user_id, body) values (pg_temp.u(1), 'WT join us https://chat.whatsapp.com/AbCdEf123') returning id) insert into ids select 'held2', id::text from p$$);
select pg_temp.step('A posts an ordinary trade post', $$with p as (insert into public.posts (user_id, body) values (pg_temp.u(1), 'WT متوفر باراسيتامول API بكميات للمصانع') returning id) insert into ids select 'clean', id::text from p$$);
select pg_temp.ok('A sees the held post (it is not deleted)', $$exists (select 1 from public.posts where id = pg_temp.id('held') and review_hold)$$);
select pg_temp.ok('… the clean one is not held', $$not (select review_hold from public.posts where id = pg_temp.id('clean'))$$);
select pg_temp.no('A cannot clear the hold', $$update public.posts set review_hold = false where id = pg_temp.id('held') returning (case when review_hold then 1/0 else 1 end)$$, '22012');
select pg_temp.act(2);
select pg_temp.ok('B does not see the held posts', $$not exists (select 1 from public.posts where id in (pg_temp.id('held'), pg_temp.id('held2')))$$);
select pg_temp.ok('B sees the clean post', $$exists (select 1 from public.posts where id = pg_temp.id('clean'))$$);
select pg_temp.ok('search leaves the held post out', $$not (public.search_all('WT join us', 6) -> 'posts' @> jsonb_build_array(jsonb_build_object('id', pg_temp.id('held2'))))$$);
select pg_temp.ok('B reads no hold row', $$(select count(*) from public.content_holds) = 0$$);
select pg_temp.ok('B is not the Drugbox team: no queue', $$public.held_review_queue() is null$$);
select pg_temp.no('B cannot decide a hold', $$select public.held_review_decide(1, true)$$, '42501');
select pg_temp.as_server();
select pg_temp.ok('A is told, with the reason (two notices)', $$pg_temp.told(1, 'auto_review') = 2 and exists (select 1 from public.notifications where user_id = pg_temp.u(1) and type = 'auto_review' and data -> 'topics' ? 'retail')$$);
select pg_temp.ok('… the invite link notice says invite', $$exists (select 1 from public.notifications where user_id = pg_temp.u(1) and type = 'auto_review' and data -> 'topics' ? 'invite')$$);
-- offers: held offers are paused and cannot be resumed
select pg_temp.act(1);
select pg_temp.step('A lists a controlled substance', $$with p as (insert into public.products (user_id, name, type, category, description) values (pg_temp.u(1), 'WT Tramadol 50mg', 'supply', 'finished', '10,000 strips') returning id) insert into ids select 'heldp', id::text from p$$);
select pg_temp.ok('… the offer is paused and held', $$(select status = 'paused' and review_hold and not active from public.products where id = pg_temp.id('heldp'))$$);
select pg_temp.nohint('A cannot resume it', $$update public.products set status = 'active' where id = pg_temp.id('heldp')$$, 'DX417');
select pg_temp.step('A edits a clean offer into an import-for-others one', $$update public.products set description = 'استيراد لحساب الغير على سجلنا' where id = pg_temp.id('pA')$$);
select pg_temp.ok('… an edit is held too', $$(select review_hold from public.products where id = pg_temp.id('pA'))$$);
select pg_temp.act(2);
select pg_temp.ok('B sees neither held offer', $$not exists (select 1 from public.products where id in (pg_temp.id('heldp'), pg_temp.id('pA')))$$);
select pg_temp.ok('market_search shows neither', $$coalesce((select count(*) from jsonb_array_elements(public.market_search('WT', null, null, 50, 0) -> 'rows') x where (x ->> 'id')::bigint in (pg_temp.id('heldp'), pg_temp.id('pA'))), 0) = 0$$);
select pg_temp.act(5);
select pg_temp.ok('the moderator sees the queue (4 items, with the body)', $$jsonb_array_length(public.held_review_queue()) = 4 and (public.held_review_queue() -> 0 ->> 'body') is not null$$);
select pg_temp.step('M1 publishes the clean-looking patient post', $$select public.held_review_decide((select id from public.content_holds where kind = 'post' and item_id = pg_temp.id('held')), true, 'ok')$$);
select pg_temp.step('M1 removes the controlled offer', $$select public.held_review_decide((select id from public.content_holds where kind = 'offer' and item_id = pg_temp.id('heldp')), false, 'controlled substances are not traded on Drugbox')$$);
select pg_temp.act(6);
select pg_temp.no('decided once (M2 is told who decided)', $$select public.held_review_decide((select id from public.content_holds where kind = 'post' and item_id = pg_temp.id('held')), false)$$, 'DX409');
select pg_temp.step('M2 publishes the edited offer', $$select public.held_review_decide((select id from public.content_holds where kind = 'offer' and item_id = pg_temp.id('pA')), true)$$);
select pg_temp.act(2);
select pg_temp.ok('B now sees the published post', $$exists (select 1 from public.posts where id = pg_temp.id('held'))$$);
select pg_temp.ok('… and the published offer is active again', $$(select status from public.products where id = pg_temp.id('pA')) = 'active'$$);
select pg_temp.as_server();
select pg_temp.ok('the removed offer is gone', $$not exists (select 1 from public.products where id = pg_temp.id('heldp'))$$);
select pg_temp.ok('A is told both outcomes, with the note', $$pg_temp.told(1, 'auto_review_decided') = 3 and exists (select 1 from public.notifications where user_id = pg_temp.u(1) and type = 'auto_review_decided' and data ->> 'outcome' = 'removed' and data ->> 'note' ~ 'controlled')$$);
select pg_temp.ok('the decisions are logged', $$(select count(*) from public.admin_actions where kind = 'held') = 3$$);
select pg_temp.act(7);
select pg_temp.step('Drugbox''s own post is not held', $$insert into public.posts (user_id, body) values (pg_temp.u(7), 'WT reminder: no sales to pharmacies — للصيدليات ممنوع')$$);
select pg_temp.ok('… not held', $$not (select review_hold from public.posts where user_id = pg_temp.u(7) order by id desc limit 1)$$);

-- ══ 3. trader reports and the right to reply (0092) ══
select pg_temp.act(2);
select pg_temp.nohint('a report needs evidence', $$select public.trader_report(pg_temp.u(1), 'non_delivery', 'WT paid in advance, nothing delivered in 6 weeks', '{}')$$, 'DX431');
select pg_temp.nohint('… uploaded by the reporter', $$select public.trader_report(pg_temp.u(1), 'non_delivery', 'WT paid in advance, nothing delivered in 6 weeks', array['trader-reports/' || pg_temp.u(1) || '/receipt.pdf'])$$, 'DX431');
select pg_temp.nohint('… and says what happened', $$select public.trader_report(pg_temp.u(1), 'non_delivery', 'short', array['trader-reports/' || pg_temp.u(2) || '/invoice.pdf'])$$, 'DX430');
select pg_temp.no('not about oneself', $$select public.trader_report(pg_temp.u(2), 'other', 'WT reporting myself for no reason at all', array['trader-reports/' || pg_temp.u(2) || '/invoice.pdf'])$$, '22023');
select pg_temp.step('B reports A with the invoice', $$insert into ids select 'rep', public.trader_report(pg_temp.u(1), 'non_delivery', 'WT paid in advance, nothing delivered in 6 weeks', array['trader-reports/' || pg_temp.u(2) || '/invoice.pdf'])::text$$);
select pg_temp.nohint('one open report per pair', $$select public.trader_report(pg_temp.u(1), 'other', 'WT the same trader again, a second time', array['trader-reports/' || pg_temp.u(2) || '/invoice.pdf'])$$, 'DX432');
select pg_temp.act(3);
select pg_temp.ok('C (not a party) reads nothing', $$not exists (select 1 from public.trader_reports) and not public.can_read_document('trader-reports/' || pg_temp.u(2) || '/invoice.pdf')$$);
select pg_temp.no('C cannot reply for A', $$select public.trader_report_reply(pg_temp.id('rep'), 'WT not my report but I reply')$$, '42501');
select pg_temp.act(1);
select pg_temp.ok('… A reads the report and the evidence', $$exists (select 1 from public.trader_reports where id = pg_temp.id('rep') and reporter = pg_temp.u(2)) and public.can_read_document('trader-reports/' || pg_temp.u(2) || '/invoice.pdf')$$);
select pg_temp.ok('… A sees it in my_trader_reports as about_me', $$(public.my_trader_reports() -> 0 ->> 'side') = 'about_me'$$);
select pg_temp.no('A cannot change the report itself', $$update public.trader_reports set status = 'dismissed' where id = pg_temp.id('rep')$$, '42501');
select pg_temp.act(5);
select pg_temp.nohint('no vote before the reply (7 days)', $$select public.trader_report_vote(pg_temp.id('rep'), true)$$, 'DX433');
select pg_temp.act(1);
select pg_temp.step('A replies with a receipt', $$select public.trader_report_reply(pg_temp.id('rep'), 'WT the goods were shipped, here is the courier receipt', array['trader-reports/' || pg_temp.u(1) || '/receipt.pdf'])$$);
select pg_temp.act(2);
select pg_temp.ok('B reads A''s reply evidence', $$public.can_read_document('trader-reports/' || pg_temp.u(1) || '/receipt.pdf')$$);
select pg_temp.ok('B does not read the moderators'' votes', $$(select count(*) from public.trader_report_votes) = 0$$);
select pg_temp.no('B cannot vote', $$select public.trader_report_vote(pg_temp.id('rep'), true)$$, '42501');
select pg_temp.act(5);
select pg_temp.ok('M1 sees it in the queue, can vote', $$(public.trader_reports_queue() -> 0 ->> 'can_vote')::boolean$$);
select pg_temp.ok('… one vote does not decide', $$public.trader_report_vote(pg_temp.id('rep'), true, 'invoice paid, no delivery note') = 'voted'$$);
select pg_temp.nohint('M1 cannot vote twice', $$select public.trader_report_vote(pg_temp.id('rep'), true)$$, 'DX434');
select pg_temp.act(6);
select pg_temp.ok('M2 agrees → upheld', $$public.trader_report_vote(pg_temp.id('rep'), true) = 'upheld'$$);
select pg_temp.as_server();
select pg_temp.ok('both sides are told the outcome', $$pg_temp.told(1, 'trader_report_decided') = 1 and pg_temp.told(2, 'trader_report_decided') = 1 and pg_temp.told(1, 'trader_report') = 1 and pg_temp.told(2, 'trader_report_reply') = 1$$);
select pg_temp.act(3);
select pg_temp.ok('the upheld report counts on A''s card (not the accusation)', $$(public.trade_card(pg_temp.u(1)) ->> 'reports_upheld')::int = 1$$);
select pg_temp.as_server();
select pg_temp.step('M1 is reported by A', $$update public.profiles set role = 'moderator' where id = pg_temp.u(1)$$);
select pg_temp.act(2);
select pg_temp.step('B reports A again (the first is decided)', $$insert into ids select 'rep2', public.trader_report(pg_temp.u(1), 'other', 'WT a second matter, different shipment', array['trader-reports/' || pg_temp.u(2) || '/invoice.pdf'])::text$$);
select pg_temp.act(1);
select pg_temp.step('A replies', $$select public.trader_report_reply(pg_temp.id('rep2'), 'WT my side of the second matter')$$);
select pg_temp.no('A (now a moderator) cannot vote on a report about A', $$select public.trader_report_vote(pg_temp.id('rep2'), false)$$, '42501');
select pg_temp.as_server();
select pg_temp.step('A is a member again', $$update public.profiles set role = 'user' where id = pg_temp.u(1)$$);
select pg_temp.act(5); select pg_temp.step('M1 dismisses', $$select public.trader_report_vote(pg_temp.id('rep2'), false)$$);
select pg_temp.act(6);
select pg_temp.ok('M2 upholds: a split waits', $$public.trader_report_vote(pg_temp.id('rep2'), true) = 'voted'$$);
select pg_temp.as_server();
select pg_temp.ok('… still open', $$(select status from public.trader_reports where id = pg_temp.id('rep2')) = 'open'$$);

-- ══ 4. the supplier rates the buyer (0092) ══
select pg_temp.as_server();
select pg_temp.step('a delivered deal: C''s company buys from V''s company', $$with d as (insert into public.deals (type, title, from_company_id, from_user, to_company_id, status) values ('quote', 'WT foil order', pg_temp.id('coU'), pg_temp.u(3), pg_temp.id('coV'), 'delivered') returning id, ref)
  insert into ids select 'deal', ref from d$$);
select pg_temp.act(3);
select pg_temp.no('the buyer cannot rate itself as buyer', $$select public.deal_rate_buyer((select v from ids where k = 'deal'), 5)$$, '42501');
select pg_temp.act(2);
select pg_temp.no('an outsider cannot rate', $$select public.deal_rate_buyer((select v from ids where k = 'deal'), 1)$$, '42501');
select pg_temp.act(4);
select pg_temp.no('stars 1–5', $$select public.deal_rate_buyer((select v from ids where k = 'deal'), 9)$$, '22023');
select pg_temp.step('V rates the buyer 4', $$select public.deal_rate_buyer((select v from ids where k = 'deal'), 4, 'paid on time')$$);
select pg_temp.nohint('once', $$select public.deal_rate_buyer((select v from ids where k = 'deal'), 5)$$, 'DX436');
select pg_temp.ok('the buyer company''s rating', $$(public.buyer_rating(pg_temp.id('coU'), null) ->> 'n')::int = 1 and (public.buyer_rating(pg_temp.id('coU'), null) ->> 'avg')::numeric = 4$$);
select pg_temp.as_server();
select pg_temp.ok('the buyer is told', $$pg_temp.told(3, 'deal_rated_buyer') = 1$$);
select pg_temp.step('an open deal', $$with d as (insert into public.deals (type, title, from_company_id, to_company_id, status) values ('quote', 'WT open order', pg_temp.id('coU'), pg_temp.id('coV'), 'requested') returning ref) insert into ids select 'deal2', ref from d$$);
select pg_temp.act(4);
select pg_temp.nohint('not before delivery', $$select public.deal_rate_buyer((select v from ids where k = 'deal2'), 4)$$, 'DX435');

-- ══ 5. phone verification keeps the number private (0093) ══
select pg_temp.act(2);
select pg_temp.nohint('a number is a number', $$select public.phone_verify_start('call me')$$, 'DX440');
select pg_temp.step('B asks for a code', $$select public.phone_verify_start('010 1234 5678')$$);
select pg_temp.as_server();
select pg_temp.step('(the SMS) the code', $$insert into ids select 'code', substring(body from 'code: (\d{6})') from private.sms_outbox where phone = '+201012345678' order by id desc limit 1$$);
select pg_temp.ok('the code is stored only as a hash', $$not exists (select 1 from private.phone_codes where code_hash = (select v from ids where k = 'code'))$$);
select pg_temp.act(2);
select pg_temp.nohint('a wrong code', $$select public.phone_verify_confirm('000000')$$, 'DX445');
select pg_temp.ok('the right code verifies', $$(public.phone_verify_confirm((select v from ids where k = 'code')) ->> 'verified')::boolean$$);
select pg_temp.ok('… B''s card says verified', $$(public.trade_card(pg_temp.u(2)) ->> 'phone_verified')::boolean$$);
select pg_temp.act(3);
select pg_temp.ok('C sees "verified" but never B''s number', $$(public.trade_card(pg_temp.u(2)) ->> 'phone_verified')::boolean and (public.trade_card(pg_temp.u(2))::text !~ '1012345678')$$);
select pg_temp.no('C cannot read B''s phone column', $$select phone from public.profiles where id = pg_temp.u(2)$$, '42501');
select pg_temp.no('C cannot read the phone hash', $$select phone_hash from public.member_verifications$$, '42501');
select pg_temp.nohint('C cannot verify the same number', $$select public.phone_verify_start('+20 101 234 5678')$$, 'DX441');
select pg_temp.no('C cannot write a verification', $$insert into public.member_verifications (user_id, phone_verified_at) values (pg_temp.u(3), now())$$, '42501');
select pg_temp.act(2);
select pg_temp.step('B types another number in Edit Profile', $$update public.profiles set phone = '01099999999' where id = pg_temp.u(2)$$);
select pg_temp.ok('… no longer verified', $$not (public.trade_card(pg_temp.u(2)) ->> 'phone_verified')::boolean$$);
select pg_temp.ok('member since and new account on the card', $$(public.trade_card(pg_temp.u(2)) ->> 'new_account')::boolean and public.trade_card(pg_temp.u(2)) ? 'member_since'$$);
select pg_temp.step('codes: 2 more', $$select public.phone_verify_start('01012345671'); select public.phone_verify_start('01012345672')$$);
select pg_temp.nohint('at most 3 codes an hour', $$select public.phone_verify_start('01012345673')$$, 'DX442');

-- ══ 6. group tools and invite links (0094) ══
select pg_temp.as_server();
select pg_temp.step('G''s public group with rules', $$with g as (insert into public.groups (name, type, created_by, rules) values ('WT Traders', 'public', pg_temp.u(8), '["Trade offers only","No retail"]'::jsonb) returning id),
  m as (insert into public.group_members (group_id, user_id, role) select id, pg_temp.u(8), 'admin' from g returning group_id) insert into ids select 'g', group_id::text from m$$);
select pg_temp.act(8);
select pg_temp.step('G turns the tools on', $$update public.groups set rules_required = true, daily_post_limit = 2, slow_mode_minutes = null, block_links = true, require_category = true where id = pg_temp.id('g')$$);
select pg_temp.no('the limit stays sensible', $$update public.groups set daily_post_limit = 500 where id = pg_temp.id('g')$$, '23514');
select pg_temp.step('G tries to mark the group partner', $$update public.groups set partner_at = now() where id = pg_temp.id('g')$$);
select pg_temp.ok('… only Drugbox does', $$(select partner_at is null from public.groups where id = pg_temp.id('g'))$$);
select pg_temp.act(9);
select pg_temp.nohint('J cannot join before accepting the rules', $$insert into public.group_members (group_id, user_id) values (pg_temp.id('g'), pg_temp.u(9))$$, 'DX425');
select pg_temp.nohint('… nor through group_request_join', $$select public.group_request_join(pg_temp.id('g'))$$, 'DX425');
select pg_temp.step('J accepts the rules and joins', $$select public.group_accept_rules(pg_temp.id('g')); insert into public.group_members (group_id, user_id) values (pg_temp.id('g'), pg_temp.u(9))$$);
select pg_temp.ok('… J is a member', $$exists (select 1 from public.group_members where group_id = pg_temp.id('g') and user_id = pg_temp.u(9))$$);
select pg_temp.nohint('a post says what it is', $$insert into public.posts (user_id, group_id, body) values (pg_temp.u(9), pg_temp.id('g'), 'WT hello everyone in the group')$$, 'DX424');
select pg_temp.nohint('no invite links to outside groups', $$insert into public.posts (user_id, group_id, body, category) values (pg_temp.u(9), pg_temp.id('g'), 'WT our other group t.me/joinchat/xyz', 'market')$$, 'DX423');
select pg_temp.step('J posts twice', $$insert into public.posts (user_id, group_id, body, category) values (pg_temp.u(9), pg_temp.id('g'), 'WT available: lactose monohydrate 200 kg', 'market'), (pg_temp.u(9), pg_temp.id('g'), 'WT needed: HPMC E5 100 kg', 'market')$$);
select pg_temp.nohint('the daily limit (2)', $$insert into public.posts (user_id, group_id, body, category) values (pg_temp.u(9), pg_temp.id('g'), 'WT available: talc 50 kg', 'market')$$, 'DX420');
select pg_temp.act(8);
select pg_temp.step('G sets slow mode, no daily limit', $$update public.groups set daily_post_limit = null, slow_mode_minutes = 30 where id = pg_temp.id('g')$$);
select pg_temp.act(9);
select pg_temp.nohint('slow mode', $$insert into public.posts (user_id, group_id, body, category) values (pg_temp.u(9), pg_temp.id('g'), 'WT available: talc 50 kg', 'market')$$, 'DX421');
select pg_temp.act(8);
select pg_temp.step('G: no slow mode, posts reviewed first', $$update public.groups set slow_mode_minutes = null, review_posts = true where id = pg_temp.id('g')$$);
select pg_temp.act(9);
select pg_temp.nohint('the same words twice in a week', $$insert into public.posts (user_id, group_id, body, category) values (pg_temp.u(9), pg_temp.id('g'), 'WT  Available: LACTOSE monohydrate 200 kg', 'market')$$, 'DX422');
select pg_temp.step('J posts (waits for the admins)', $$with p as (insert into public.posts (user_id, group_id, body, category) values (pg_temp.u(9), pg_temp.id('g'), 'WT available: talc 50 kg', 'market') returning id) insert into ids select 'pend', id::text from p$$);
select pg_temp.ok('… J sees it, pending', $$(select group_pending from public.posts where id = pg_temp.id('pend'))$$);
select pg_temp.no('J cannot publish it', $$select public.group_publish_post(pg_temp.id('pend'), true)$$, '42501');
select pg_temp.as_server(); select pg_temp.step('K joins (no rules on server write)', $$insert into public.group_members (group_id, user_id) values (pg_temp.id('g'), pg_temp.u(10))$$);
select pg_temp.act(10);
select pg_temp.ok('K (a member) does not see the pending post', $$not exists (select 1 from public.posts where id = pg_temp.id('pend'))$$);
select pg_temp.act(8);
select pg_temp.ok('G sees it in the pending list', $$jsonb_array_length(public.group_pending_posts(pg_temp.id('g'))) = 1$$);
select pg_temp.ok('G publishes it', $$public.group_publish_post(pg_temp.id('pend'), true) = 'published'$$);
select pg_temp.act(10);
select pg_temp.ok('K sees it now', $$exists (select 1 from public.posts where id = pg_temp.id('pend'))$$);
select pg_temp.as_server();
select pg_temp.ok('J is told it was published; K gets the group notice', $$pg_temp.told(9, 'group_post_published') = 1 and pg_temp.told(10, 'group_post') = 1$$);
select pg_temp.act(8);
select pg_temp.step('G posts freely (an admin)', $$insert into public.posts (user_id, group_id, body) values (pg_temp.u(8), pg_temp.id('g'), 'WT welcome — read the rules')$$);
-- invite links
select pg_temp.act(9);
select pg_temp.no('a member does not make invite links', $$select public.group_link_create(pg_temp.id('g'))$$, '42501');
select pg_temp.act(8);
select pg_temp.step('G makes a link (2 uses)', $$insert into ids select 'tok', public.group_link_create(pg_temp.id('g'), 30, 2) ->> 'token'$$);
select pg_temp.ok('… a long random token', $$char_length((select v from ids where k = 'tok')) >= 32$$);
select pg_temp.act(2);
select pg_temp.ok('B (signed in) previews the group and its rules', $$(public.group_link_preview((select v from ids where k = 'tok')) ->> 'rules_required')::boolean and (public.group_link_preview((select v from ids where k = 'tok')) ->> 'ok')::boolean$$);
select pg_temp.ok('B cannot list the group''s links', $$not exists (select 1 from public.group_invite_links)$$);
select pg_temp.nohint('B joins only after accepting the rules', $$select public.group_join_by_link((select v from ids where k = 'tok'), false)$$, 'DX425');
select pg_temp.ok('B joins by himself', $$public.group_join_by_link((select v from ids where k = 'tok'), true) = 'member'$$);
select pg_temp.ok('… once', $$public.group_join_by_link((select v from ids where k = 'tok'), true) = 'already'$$);
select pg_temp.act(1);
select pg_temp.ok('A joins (second use)', $$public.group_join_by_link((select v from ids where k = 'tok'), true) = 'member'$$);
select pg_temp.act(3);
select pg_temp.nohint('the third use is refused', $$select public.group_join_by_link((select v from ids where k = 'tok'), true)$$, 'DX428');
select pg_temp.nohint('a made-up token', $$select public.group_join_by_link('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', true)$$, 'DX427');
select pg_temp.act(8);
select pg_temp.step('G stops the link', $$select public.group_link_revoke((select id from public.group_invite_links where token = (select v from ids where k = 'tok')))$$);
select pg_temp.act(3);
select pg_temp.ok('… a stopped link shows as not working', $$not (public.group_link_preview((select v from ids where k = 'tok')) ->> 'ok')::boolean$$);
select pg_temp.as_anon();
select pg_temp.no('anon previews nothing', $$select public.group_link_preview((select v from ids where k = 'tok'))$$, '42501');
select pg_temp.no('anon cannot join by link', $$select public.group_join_by_link((select v from ids where k = 'tok'), true)$$, '42501');
-- partner groups
select pg_temp.act(9);
select pg_temp.no('a member does not ask for partner', $$select public.group_partner_request(pg_temp.id('g'), 'WT our WhatsApp group had 800 traders')$$, '42501');
select pg_temp.act(8);
select pg_temp.step('G asks Drugbox', $$select public.group_partner_request(pg_temp.id('g'), 'WT our WhatsApp group had 800 traders')$$);
select pg_temp.no('G cannot approve it', $$select public.group_partner_decide(pg_temp.id('g'), true)$$, '42501');
select pg_temp.act(5);
select pg_temp.ok('M1 sees it', $$jsonb_array_length(public.group_partner_queue()) = 1$$);
select pg_temp.ok('M1 approves', $$public.group_partner_decide(pg_temp.id('g'), true, 'welcome') = 'approved'$$);
select pg_temp.as_server();
select pg_temp.ok('the group is a partner and G is told', $$(select partner_at is not null from public.groups where id = pg_temp.id('g')) and pg_temp.told(8, 'group_partner_decided') = 1$$);

-- ══ 7. anon ══
select pg_temp.as_anon();
select pg_temp.ok('anon reads no trade profile, hold, report, verification', $$(select count(*) from public.trade_profiles) + (select count(*) from public.content_holds) + (select count(*) from public.trader_reports) = 0$$);
select pg_temp.no('anon has no trade card', $$select public.trade_card(pg_temp.u(1))$$, '42501');
select pg_temp.no('anon cannot report', $$select public.trader_report(pg_temp.u(1), 'other', 'xxxxxxxxxxxxxxxxxxxxxxxx', '{}')$$, '42501');

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
