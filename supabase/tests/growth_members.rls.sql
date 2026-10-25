-- Founding members (0101), Ask an expert (0102), public company pages (0103), Arabic course titles + the specialty prompt (0104)
-- (AREA w-growth: W-42, W-43, decisions 1, 7, 9). Invitations: only Drugbox admins make / revoke them, the code is shown once and
-- stored only hashed, single use, expiry, quotas per segment (no pharmacy segment), the invitee joins by their own call, ten wrong
-- codes an hour block guessing, VIP months only for a company the founder runs, once. Expert sessions: Drugbox schedules, members
-- request / register (seats, start), the meeting link only for the registered from an hour before, reminders once, Q&A answered by
-- Drugbox or the expert and kept. Public pages: anon reads company pages without any contact or private field. Runs as the real API
-- roles with a JWT, in one transaction that is rolled back; test data carries the "GM " marker.
-- psql -f supabase/tests/growth_members.rls.sql
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

-- A Drugbox admin, F the invitee, X another member, O who owns a company F does not run
insert into auth.users (id, email) values ('b2000000-0000-0000-0000-000000000001','gm-a@x'),('b2000000-0000-0000-0000-000000000002','gm-f@x'),
  ('b2000000-0000-0000-0000-000000000003','gm-x@x'),('b2000000-0000-0000-0000-000000000004','gm-o@x') on conflict do nothing;
insert into public.profiles (id, name, headline) values ('b2000000-0000-0000-0000-000000000001','GM Admin', null),('b2000000-0000-0000-0000-000000000002','GM Founder', 'Regulatory Affairs'),
  ('b2000000-0000-0000-0000-000000000003','GM Other', 'Regulatory Affairs'),('b2000000-0000-0000-0000-000000000004','GM Owner', 'Production') on conflict (id) do update set name = excluded.name, headline = excluded.headline;
update public.profiles set role = 'admin' where id = 'b2000000-0000-0000-0000-000000000001';
create function pg_temp.A() returns void language sql as $$ select pg_temp.as_user('b2000000-0000-0000-0000-000000000001') $$;
create function pg_temp.F() returns void language sql as $$ select pg_temp.as_user('b2000000-0000-0000-0000-000000000002') $$;
create function pg_temp.X() returns void language sql as $$ select pg_temp.as_user('b2000000-0000-0000-0000-000000000003') $$;
create function pg_temp.O() returns void language sql as $$ select pg_temp.as_user('b2000000-0000-0000-0000-000000000004') $$;
create temp table codes (k text primary key, code text); grant all on codes to authenticated, anon;
create function pg_temp.code(k text) returns text language sql stable as $$ select code from codes where codes.k = code.k $$;
-- companies: F runs "GM Founder Pharma" (owner), O owns "GM Other Pharma"; an imported unclaimed page; a suspended one
select pg_temp.as_server();
insert into public.companies (owner_id, name, slug, type, sectors, status, phone, email, whatsapp, registry, city, tagline)
values ('b2000000-0000-0000-0000-000000000002', 'GM Founder Pharma', 'gm-founder-pharma', 'Manufacturer', '{Manufacturer}', 'verified', '+20 100 000 0001', 'sales@gmf.test', '+20100', '123456', 'Cairo', 'GM sterile injectables'),
       ('b2000000-0000-0000-0000-000000000004', 'GM Other Pharma', 'gm-other-pharma', 'Manufacturer', '{Manufacturer}', 'pending', null, null, null, null, 'Giza', null),
       (null, 'GM Imported Labs', 'gm-imported-labs', 'Labs & testing', '{Labs & testing}', 'unclaimed', '+20 2 0000', 'info@gmi.test', null, '777', 'Alexandria', null),
       ('b2000000-0000-0000-0000-000000000004', 'GM Gone Co', 'gm-gone-co', 'Manufacturer', '{Manufacturer}', 'suspended', null, null, null, null, 'Cairo', null);
insert into ids select 'cf', id::text from public.companies where slug = 'gm-founder-pharma';
insert into ids select 'co', id::text from public.companies where slug = 'gm-other-pharma';
insert into public.company_products (company_id, name, category, description) select pg_temp.id('cf'), 'GM Ceftriaxone 1 g vial', 'Finished product', 'GM vials';

-- ══ 1. founding members ═══════════════════════════════════════════════════════════════════════
select pg_temp.F();
select pg_temp.ok('the segments are readable, with NO pharmacy / Rx segment', $$(select count(*) = 8 from public.founder_segments) and not exists (select 1 from public.founder_segments where key ~* 'rx|pharmac' or label_en ~* 'rx|pharmac' or label_ar ~ 'صيدل')$$);
select pg_temp.no('a member cannot make an invitation', $$select public.founder_invite_create('agency')$$, '42501');
select pg_temp.no('a member cannot change a quota', $$select public.founder_segment_quota('agency', 500)$$, '42501');
select pg_temp.no('… nor directly', $$update public.founder_segments set quota = 500 where key = 'agency'$$, '42501');
select pg_temp.ok('a member reads no invitation', $$(select count(*) = 0 from public.founder_invites_list(50)) and (select count(*) = 0 from public.founder_overview())$$);
select pg_temp.A();
select pg_temp.step('Drugbox makes an invitation for an agency', $$insert into codes select 'a', public.founder_invite_create('agency', 'GM for F', 30) ->> 'code'$$);
select pg_temp.ok('the code is long and formatted (DBX-XXXX ×5)', $$pg_temp.code('a') ~ '^DBX-[0-9A-Z]{4}(-[0-9A-Z]{4}){4}$'$$);
select pg_temp.as_server();
select pg_temp.ok('only its hash is stored, never the code', $$not exists (select 1 from public.founder_invites i where i.code_hint <> right(replace(pg_temp.code('a'), '-', ''), 4) or encode(i.code_hash, 'escape') like '%' || replace(pg_temp.code('a'), '-', '') || '%')$$);
select pg_temp.A();
select pg_temp.no('even an admin cannot read the hashes', $$select code_hash from public.founder_invites$$, '42501');
select pg_temp.step('… a second one, then a third, all different', $$insert into codes select 'b', public.founder_invite_create('agency') ->> 'code' union all select 'c', public.founder_invite_create('distributor') ->> 'code'$$);
select pg_temp.ok('… all different', $$(select count(distinct code) = 3 from codes)$$);
select pg_temp.no('an unknown segment is refused', $$select public.founder_invite_create('rx_traders')$$, '22023');
select pg_temp.step('the packaging quota is set to 1', $$select public.founder_segment_quota('packaging', 1)$$);
select pg_temp.step('… one packaging invitation', $$insert into codes select 'p', public.founder_invite_create('packaging') ->> 'code'$$);
select pg_temp.no('… a second goes over the quota', $$select public.founder_invite_create('packaging')$$, '23514');
select pg_temp.step('… revoking the first frees the place', $$select public.founder_invite_revoke((select id from public.founder_invites where segment = 'packaging'))$$);
select pg_temp.ok('… so a new one can be made', $$(select public.founder_invite_create('packaging') ? 'code')$$);
select pg_temp.ok('the overview counts open invitations', $$(select open_invites = 2 and joined = 0 from public.founder_overview() where key = 'agency')$$);

select pg_temp.F();
select pg_temp.ok('the invitee sees what it is for before choosing', $$(select public.founder_invite_peek(pg_temp.code('a')) ->> 'state' = 'open' and public.founder_invite_peek(pg_temp.code('a')) ->> 'segment' = 'agency')$$);
select pg_temp.ok('a revoked invitation says so', $$(select public.founder_invite_peek(pg_temp.code('p')) ->> 'state' = 'revoked')$$);
select pg_temp.no('a revoked invitation cannot be used', $$select public.founder_redeem(pg_temp.code('p'))$$, '55000');
select pg_temp.no('F cannot give VIP months before joining', $$select public.founder_apply_vip(pg_temp.id('cf'))$$, '42501');
select pg_temp.ok('a made-up code is refused (and counted)', $$(select public.founder_redeem('DBX-AAAA-AAAA-AAAA-AAAA-AAAA') ->> 'error' = 'invalid')$$);
select pg_temp.no('… a company F does not run', $$select public.founder_redeem(lower(replace(pg_temp.code('a'), '-', ' ')), pg_temp.id('co'))$$, '42501');
select pg_temp.as_server();
select pg_temp.ok('… F is not a founder yet (the whole join was undone)', $$not exists (select 1 from public.founder_members where user_id = 'b2000000-0000-0000-0000-000000000002') and (select used_by is null from public.founder_invites where code_hint = right(replace(pg_temp.code('a'), '-', ''), 4))$$);
select pg_temp.F();
select pg_temp.step('F joins, giving the 3 VIP months to their own company', $$select public.founder_redeem(lower(replace(pg_temp.code('a'), '-', ' ')), pg_temp.id('cf'))$$);
select pg_temp.ok('F is a founding member (agency)', $$(select segment = 'agency' from public.founder_members where user_id = auth.uid())$$);
select pg_temp.ok('F''s company is VIP for about 3 months', $$(select plan = 'vip' and vip_until between now() + interval '88 days' and now() + interval '93 days' from public.companies where id = pg_temp.id('cf'))$$);
select pg_temp.ok('my_founder says the VIP months were used', $$(select (public.my_founder() ->> 'vip_open')::boolean = false and (public.my_founder() ->> 'vip_company_id')::bigint = pg_temp.id('cf'))$$);
select pg_temp.no('the VIP months cannot be given twice', $$select public.founder_apply_vip(pg_temp.id('cf'))$$, '55000');
select pg_temp.no('F cannot use a second invitation', $$select public.founder_redeem(pg_temp.code('b'))$$, '55000');
select pg_temp.ok('F reads the badge list but not the invitation or company behind it', $$(select count(*) >= 1 from public.founder_members where user_id = auth.uid())$$);
select pg_temp.no('… the invitation id stays private', $$select invite_id from public.founder_members$$, '42501');
select pg_temp.no('F cannot make themself a founder of another segment', $$insert into public.founder_members (user_id, segment) values (auth.uid(), 'manufacturer')$$, '42501');
select pg_temp.no('F cannot change their segment', $$update public.founder_members set segment = 'manufacturer' where user_id = auth.uid()$$, '42501');
select pg_temp.X();
select pg_temp.no('another member cannot reuse F''s code', $$select public.founder_redeem(pg_temp.code('a'))$$, '55000');
select pg_temp.ok('X sees F''s founder badge', $$(select count(*) = 1 from public.founder_members where user_id = 'b2000000-0000-0000-0000-000000000002')$$);
select pg_temp.as_server();
select pg_temp.step('X has tried 10 wrong codes this hour', $$insert into private.founder_attempts (user_id) select 'b2000000-0000-0000-0000-000000000003' from generate_series(1, 10)$$);
select pg_temp.X();
select pg_temp.no('… the 11th try is blocked, even with a good code', $$select public.founder_redeem(pg_temp.code('b'))$$, '54000');
select pg_temp.as_server();
select pg_temp.step('the hour passes', $$delete from private.founder_attempts where user_id = 'b2000000-0000-0000-0000-000000000003'$$);
select pg_temp.step('the distributor invitation expires', $$update public.founder_invites set expires_at = now() - interval '1 minute' where segment = 'distributor'$$);
select pg_temp.X();
select pg_temp.no('an expired invitation is refused', $$select public.founder_redeem(pg_temp.code('c'))$$, '55000');
select pg_temp.step('X joins with the second agency code (no company)', $$select public.founder_redeem(pg_temp.code('b'))$$);
select pg_temp.ok('X''s VIP months are still open', $$(select (public.my_founder() ->> 'vip_open')::boolean)$$);
select pg_temp.as_anon();
select pg_temp.no('anon cannot join', $$select public.founder_redeem(pg_temp.code('b'))$$, '42501');
select pg_temp.ok('anon reads no founder', $$(select count(*) = 0 from public.founder_members)$$);
select pg_temp.A();
select pg_temp.ok('the admin''s list shows who used which', $$(select count(*) = 2 from public.founder_invites_list(50) where segment = 'agency' and state = 'used')$$);
select pg_temp.no('a used invitation cannot be revoked', $$select public.founder_invite_revoke((select id from public.founder_invites where used_by = 'b2000000-0000-0000-0000-000000000002'))$$, '55000');
select pg_temp.step('the agency quota is set to 2 (2 joined)', $$select public.founder_segment_quota('agency', 2)$$);
select pg_temp.no('… no new agency invitation over it', $$select public.founder_invite_create('agency')$$, '23514');

-- ══ 2. ask an expert ═════════════════════════════════════════════════════════════════════════
select pg_temp.F();
select pg_temp.ok('members read the topics', $$(select count(*) = 10 from public.expert_topics)$$);
select pg_temp.step('F asks for "Buying a registration file safely"', $$insert into public.expert_requests (topic, note) values ('file_purchase', 'GM how to check the transfer papers')$$);
select pg_temp.no('… only once', $$insert into public.expert_requests (topic) values ('file_purchase')$$, '23505');
select pg_temp.no('"another topic" needs a note', $$insert into public.expert_requests (topic) values ('other')$$, '42501');
select pg_temp.no('F cannot ask in someone else''s name', $$insert into public.expert_requests (user_id, topic) values ('b2000000-0000-0000-0000-000000000003', 'nfsa')$$, '42501');
select pg_temp.X();
select pg_temp.step('X asks for it too', $$insert into public.expert_requests (topic) values ('file_purchase')$$);
select pg_temp.ok('X sees 2 asked, without names', $$(select asked = 2 and mine from public.expert_topic_demand() where topic = 'file_purchase')$$);
select pg_temp.ok('X does not read F''s request', $$(select count(*) = 1 from public.expert_requests)$$);
select pg_temp.no('a member cannot schedule a session', $$select public.expert_session_save(null, 'file_purchase', 'GM x', null, null, 'GM Expert', null, '2030-01-01 20:00', 60, 10, null)$$, '42501');
select pg_temp.no('… nor write one directly', $$insert into public.expert_sessions (topic, title, expert_name, starts_at) values ('nfsa', 'GM x', 'GM y', now() + interval '1 day')$$, '42501');
select pg_temp.A();
select pg_temp.ok('Drugbox sees the notes of the requests', $$(select asked = 2 and jsonb_array_length(notes) = 1 from public.expert_requests_admin() where topic = 'file_purchase')$$);
select pg_temp.no('a session in the past is refused', $$select public.expert_session_save(null, 'file_purchase', 'GM Buying a file safely', null, null, 'GM Dr. Expert', null, '2020-01-01 20:00', 60, 2, null)$$, '22023');
select pg_temp.no('a meeting link must be https', $$select public.expert_session_save(null, 'file_purchase', 'GM Buying a file safely', null, null, 'GM Dr. Expert', null, '2030-01-01 20:00', 60, 2, 'javascript:alert(1)')$$, '22023');
select pg_temp.step('Drugbox schedules a session in 2 days at 20:00 Cairo, 2 seats, the expert is member O', $$insert into ids values ('s', public.expert_session_save(null, 'file_purchase', 'GM Buying a file safely', 'GM شراء ملف بأمان', 'GM about', 'GM Dr. Expert', 'GM 20 years', to_char((now() at time zone 'Africa/Cairo')::date + 2, 'YYYY-MM-DD') || ' 20:00', 60, 2, 'https://meet.example.test/gm-room', 'b2000000-0000-0000-0000-000000000004')::text)$$);
select pg_temp.as_server();
select pg_temp.ok('the members who asked are told', $$(select count(*) = 2 from public.notifications where type = 'expert_session' and (data ->> 'session')::bigint = pg_temp.id('s'))$$);
select pg_temp.F();
select pg_temp.no('F does not read the meeting link from the table', $$select join_url from public.expert_sessions$$, '42501');
select pg_temp.no('… nor through the link function before registering', $$select public.expert_session_link(pg_temp.id('s'))$$, '42501');
select pg_temp.step('F registers', $$insert into public.expert_registrations (session_id) values (pg_temp.id('s'))$$);
select pg_temp.no('… the link opens only an hour before', $$select public.expert_session_link(pg_temp.id('s'))$$, '55000');
select pg_temp.no('F cannot register someone else', $$insert into public.expert_registrations (session_id, user_id) values (pg_temp.id('s'), 'b2000000-0000-0000-0000-000000000003')$$, '42501');
select pg_temp.step('F asks a question', $$insert into public.expert_questions (session_id, body) values (pg_temp.id('s'), 'GM Who pays the transfer fees?')$$);
select pg_temp.no('F cannot answer it', $$select public.expert_answer((select id from public.expert_questions where body like 'GM Who pays%'), 'GM me')$$, '42501');
select pg_temp.no('… nor write an answer into it', $$update public.expert_questions set answer = 'GM forged' where body like 'GM Who pays%'$$, '42501');
select pg_temp.X();
select pg_temp.no('X, not registered, cannot ask', $$insert into public.expert_questions (session_id, body) values (pg_temp.id('s'), 'GM Can I ask too?')$$, '42501');
select pg_temp.step('X registers (2 of 2 seats)', $$insert into public.expert_registrations (session_id) values (pg_temp.id('s'))$$);
select pg_temp.ok('the seat count is right', $$(select registered_count = 2 from public.expert_sessions where id = pg_temp.id('s'))$$);
select pg_temp.A();
select pg_temp.no('the seats cannot go below the registered', $$select public.expert_session_save(pg_temp.id('s'), 'file_purchase', 'GM Buying a file safely', null, null, 'GM Dr. Expert', null, to_char((now() at time zone 'Africa/Cairo')::date + 2, 'YYYY-MM-DD') || ' 20:00', 60, 1, null, 'b2000000-0000-0000-0000-000000000004')$$, '23514');
select pg_temp.O();
select pg_temp.no('a third member finds it full', $$insert into public.expert_registrations (session_id) values (pg_temp.id('s'))$$, '23514');
select pg_temp.ok('the expert (O) reads the link any time', $$(select public.expert_session_link(pg_temp.id('s')) = 'https://meet.example.test/gm-room')$$);
select pg_temp.step('the expert answers F', $$select public.expert_answer((select id from public.expert_questions where body like 'GM Who pays%'), 'GM The buyer, unless the contract says otherwise.')$$);
select pg_temp.as_server();
select pg_temp.ok('F is told', $$(select count(*) = 1 from public.notifications where user_id = 'b2000000-0000-0000-0000-000000000002' and type = 'expert_answer')$$);
select pg_temp.as_server();
select pg_temp.step('reminders now: none due', $$select 1$$);
select pg_temp.ok('nothing is due 2 days before', $$(select (public.growth_tick() ->> 'reminders')::int = 0)$$);
select pg_temp.step('the session is now in 20 hours', $$update public.expert_sessions set starts_at = now() + interval '20 hours' where id = pg_temp.id('s')$$);
select pg_temp.ok('the day reminder goes to both registered, once', $$(select (public.growth_tick() ->> 'reminders')::int = 2) and (select (public.growth_tick() ->> 'reminders')::int = 0)$$);
select pg_temp.step('the session is now in 30 minutes', $$update public.expert_sessions set starts_at = now() + interval '30 minutes' where id = pg_temp.id('s')$$);
select pg_temp.ok('the hour reminder goes once', $$(select (public.growth_tick() ->> 'reminders')::int = 2) and (select (public.growth_tick() ->> 'reminders')::int = 0)$$);
select pg_temp.F();
select pg_temp.ok('now the registered F gets the link', $$(select public.expert_session_link(pg_temp.id('s')) = 'https://meet.example.test/gm-room')$$);
select pg_temp.ok('F''s reminders are 2', $$(select count(*) = 2 from public.notifications where user_id = auth.uid() and type = 'expert_reminder')$$);
select pg_temp.no('F cannot cancel the session', $$select public.expert_session_set_status(pg_temp.id('s'), 'cancelled')$$, '42501');
select pg_temp.as_server();
select pg_temp.step('the session took place (2 hours ago)', $$update public.expert_sessions set starts_at = now() - interval '2 hours' where id = pg_temp.id('s')$$);
select pg_temp.A();
select pg_temp.step('Drugbox marks it done', $$select public.expert_session_set_status(pg_temp.id('s'), 'done')$$);
select pg_temp.X();
select pg_temp.ok('the Q&A is kept and readable by every member', $$(select count(*) = 1 from public.expert_questions where session_id = pg_temp.id('s') and answer like 'GM The buyer%')$$);
select pg_temp.ok('the session list shows it with its question', $$(select status = 'done' and questions = 1 and registered from public.expert_sessions_list(50) where id = pg_temp.id('s'))$$);
select pg_temp.no('nobody asks after the session ended', $$insert into public.expert_questions (session_id, body) values (pg_temp.id('s'), 'GM Late question?')$$, '42501');
select pg_temp.no('… nor registers', $$insert into public.expert_registrations (session_id) values (pg_temp.id('s'))$$, '55000');
select pg_temp.as_anon();
select pg_temp.ok('anon reads no session, question or request', $$(select count(*) = 0 from public.expert_sessions) and (select count(*) = 0 from public.expert_questions) and (select count(*) = 0 from public.expert_requests)$$);

-- ══ 3. public company pages ══════════════════════════════════════════════════════════════════
select pg_temp.as_anon();
select pg_temp.ok('anon still reads no company table', $$(select count(*) = 0 from (select 1 from public.companies where slug like 'gm-%') x)$$);
select pg_temp.ok('a visitor gets the company page with its products', $$(select public.public_company('gm-founder-pharma') ->> 'name' = 'GM Founder Pharma' and jsonb_array_length(public.public_company('gm-founder-pharma') -> 'products') = 1)$$);
select pg_temp.ok('… with its about and verified status', $$(select public.public_company('gm-founder-pharma') ->> 'tagline' = 'GM sterile injectables' and public.public_company('gm-founder-pharma') ->> 'status' = 'verified')$$);
select pg_temp.ok('… but no phone, e-mail, WhatsApp, registry or owner', $$(select not (public.public_company('gm-founder-pharma') ?| array['phone', 'email', 'whatsapp', 'registry', 'owner_id', 'source_ref']))$$);
select pg_temp.ok('the directory page has no contact field either', $$not exists (select 1 from jsonb_array_elements(public.public_directory_page(100, 0, 'GM')) x where x ?| array['phone', 'email', 'whatsapp', 'registry'])$$);
select pg_temp.ok('… lists the GM companies, not the suspended one', $$(select count(*) = 3 from jsonb_array_elements(public.public_directory_page(100, 0, 'GM')) x where x ->> 'name' like 'GM %') and not exists (select 1 from jsonb_array_elements(public.public_directory_page(100, 0, 'GM')) x where x ->> 'slug' = 'gm-gone-co')$$);
select pg_temp.ok('an unclaimed imported page is marked unclaimed', $$(select public.public_company('gm-imported-labs') ->> 'status' = 'unclaimed' and (public.public_company_meta('gm-imported-labs') ->> 'unclaimed')::boolean)$$);
select pg_temp.ok('a suspended company is not shown at all', $$public.public_company('gm-gone-co') is null and public.public_company_meta('gm-gone-co') is null$$);
select pg_temp.ok('the page title / description for sharing', $$(select public.public_company_meta('gm-founder-pharma') ->> 'description' = 'GM sterile injectables')$$);
select pg_temp.ok('sites and certificates read as on the signed-in page', $$(select public.public_company_sites('gm-founder-pharma')::text = '[]' and public.public_company_certs('gm-founder-pharma')::text = '[]')$$);
select pg_temp.F();
select pg_temp.ok('a member gets the same public page (mine = false)', $$(select (public.public_company('gm-founder-pharma') ->> 'mine')::boolean = false)$$);

-- ══ 4. courses in Arabic, the specialty prompt ═══════════════════════════════════════════════
select pg_temp.as_server();
select pg_temp.step('F and X are accounts from before the new sign-up form', $$update public.profiles set created_at = (select at from private.growth_marks where key = 'specialty_prompt_from') - interval '1 day' where id in ('b2000000-0000-0000-0000-000000000002', 'b2000000-0000-0000-0000-000000000003')$$);
select pg_temp.step('N is a new account with the same headline', $$insert into auth.users (id, email) values ('b2000000-0000-0000-0000-000000000005','gm-n@x'); insert into public.profiles (id, name, headline) values ('b2000000-0000-0000-0000-000000000005', 'GM New', 'Regulatory Affairs') on conflict (id) do update set headline = excluded.headline$$);
select pg_temp.as_user('b2000000-0000-0000-0000-000000000005');
select pg_temp.ok('a new account that chose Regulatory Affairs is not asked', $$not public.specialty_prompt_due()$$);
select pg_temp.as_anon();
select pg_temp.ok('the six courses have Arabic titles and descriptions where they exist', $$not exists (select 1 from public.training_courses where title in ('GMP Fundamentals','EDA Registration Process','ICH Guidelines','Cosmetics Regulation','Stability Studies','GCC Market Access') and (title_ar is null or description_ar is null))$$);
select pg_temp.X();
select pg_temp.ok('X (headline "Regulatory Affairs") is asked', $$public.specialty_prompt_due()$$);
select pg_temp.step('X keeps it', $$select public.specialty_answer(null)$$);
select pg_temp.ok('… and is not asked again', $$not public.specialty_prompt_due()$$);
select pg_temp.ok('… the headline is unchanged', $$(select headline = 'Regulatory Affairs' from public.profiles where id = auth.uid())$$);
select pg_temp.F();
select pg_temp.step('F changes it to Quality Control / QA (their own profile row, then the answer)', $$update public.profiles set headline = 'Quality Control / QA' where id = auth.uid(); select public.specialty_answer('Quality Control / QA')$$);
select pg_temp.ok('… the headline is changed and the question gone', $$(select headline = 'Quality Control / QA' from public.profiles where id = auth.uid()) and not public.specialty_prompt_due()$$);
select pg_temp.no('a specialty with markup is refused', $$select public.specialty_answer('<b>x</b>')$$, '22023');
select pg_temp.no('F cannot write someone else''s answer', $$insert into public.member_prompts (user_id, key) values ('b2000000-0000-0000-0000-000000000003', 'specialty')$$, '42501');
select pg_temp.O();
select pg_temp.ok('O (another headline) is never asked', $$not public.specialty_prompt_due()$$);
select pg_temp.as_anon();
select pg_temp.no('anon is not asked', $$select public.specialty_prompt_due()$$, '42501');

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
