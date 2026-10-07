-- Integrity and speed (0022): deletes that foreign keys used to block, like notifications, counters, size limits, the
-- conversation list after a deleted message, the lean directory, deals visibility — then launch-scale data (10k people,
-- 5k companies, 20k deals, 60k events, 150k connections, 50k messages, 20k reviews) and EXPLAIN ANALYZE timings of the hot
-- reads BEFORE 0022 (the old policies / functions / indexes put back inside a savepoint) and AFTER.
-- Runs as the real API roles with a JWT, in one transaction that is rolled back; functional test data carries the "IP " marker.
-- Run on a fresh database (stub + all migrations): psql -f supabase/tests/integrity_perf.sql   (about a minute)
-- Harness: every action is a step() and every assertion an ok()/no(); an unexpected error becomes a FAIL with its message (the report
-- is never lost), a negative check passes only with the expected SQLSTATE, and psql exits non-zero when anything failed.
\set QUIET on
\set ON_ERROR_ROLLBACK on
set client_min_messages = warning;
\o /dev/null
begin;
create temp table r (n serial, name text, ok boolean, err text); grant all on r to authenticated, anon; grant all on r_n_seq to authenticated, anon;
create temp table ids (k text primary key, v text); grant all on ids to authenticated, anon;
create temp table perf (n serial, label text, variant text, ms numeric, jit int, seq text, idx text); grant all on perf to authenticated, anon; grant all on perf_n_seq to authenticated, anon;
create function pg_temp.as_user(u text) returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', u, true); perform set_config('request.jwt.claims', json_build_object('sub', u, 'role', 'authenticated')::text, true);
  perform set_config('role', 'authenticated', true); end $$;
create function pg_temp.as_anon() returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', '', true); perform set_config('request.jwt.claims', '{"role":"anon"}', true); perform set_config('role', 'anon', true); end $$;
-- server-side work (imports, the service role, an operator in psql): no JWT
create function pg_temp.as_server() returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', '', true); perform set_config('request.jwt.claims', '', true); perform set_config('role', 'none', true); end $$;
create function pg_temp.ok(p_name text, q text) returns void language plpgsql as $$ declare b boolean; begin
  execute 'select (' || q || ')::boolean' into b; insert into r(name, ok) values (p_name, coalesce(b, false));
  exception when others then insert into r(name, ok, err) values (p_name, false, sqlstate || ': ' || sqlerrm); end $$;
create function pg_temp.step(p_name text, q text) returns void language plpgsql as $$ begin execute q;
  exception when others then insert into r(name, ok, err) values ('step: ' || p_name, false, sqlstate || ': ' || sqlerrm); end $$;
-- the statement must be refused with this SQLSTATE; if it is allowed its effects are rolled back and the check fails
create function pg_temp.no(p_name text, q text, st text) returns void language plpgsql as $$ begin
  execute q; raise exception 'the statement was allowed' using errcode = 'DB001';
  exception when others then insert into r(name, ok, err) values (p_name, sqlstate = st, case when sqlstate <> st then sqlstate || ': ' || sqlerrm end); end $$;
create function pg_temp.id(k text) returns bigint language sql stable as $$ select v::bigint from ids where ids.k = id.k $$;
-- a write whose row count is kept under a key (checked by the next ok())
create function pg_temp.rows(p_k text, q text) returns void language plpgsql as $$ declare n bigint; begin
  execute q; get diagnostics n = row_count; insert into ids as i values (p_k, n) on conflict on constraint ids_pkey do update set v = excluded.v;
  exception when others then insert into r(name, ok, err) values ('write: ' || p_k, false, sqlstate || ': ' || sqlerrm); end $$;
create function pg_temp.u(i bigint) returns uuid language sql immutable as $$ select md5('ip-user-' || i)::uuid $$;
-- EXPLAIN ANALYZE (best of n, planning + execution); a DML statement is undone (subtransaction) after it is measured
create function pg_temp.explain1(q text) returns json language plpgsql as $$ declare j json; begin
  begin execute 'explain (analyze, timing off, format json) ' || q into j; raise exception using errcode = 'DBX01';
  exception when sqlstate 'DBX01' then null; end;
  return j; end $$;
create function pg_temp.perf(p_label text, p_variant text, q text, runs int default 3) returns void language plpgsql as $$
declare j json; best json; t numeric; bt numeric; i int; begin
  for i in 1..runs loop
    j := pg_temp.explain1(q); t := (j->0->>'Planning Time')::numeric + (j->0->>'Execution Time')::numeric;
    if bt is null or t < bt then bt := t; best := j; end if;
  end loop;
  insert into perf(label, variant, ms, jit, seq, idx)
  with recursive nd(x) as (select best->0->'Plan' union all select c from nd, json_array_elements(coalesce(nd.x->'Plans', '[]'::json)) c)
  select p_label, p_variant, round(bt, 1), coalesce((best->0->'JIT'->>'Functions')::int, 0),
         (select string_agg(distinct x->>'Relation Name', ',') from nd where x->>'Node Type' = 'Seq Scan'),
         (select string_agg(distinct x->>'Index Name', ',') from nd where x->>'Index Name' is not null);
exception when others then insert into r(name, ok, err) values ('perf: ' || p_label || ' / ' || p_variant, false, sqlstate || ': ' || sqlerrm); end $$;
create function pg_temp.ms(p_label text, p_variant text) returns numeric language sql stable as $$ select ms from perf where label = p_label and variant = p_variant $$;

-- people: alice (posts), bob (likes and comments), mallory (replies, creates a group), drugbox admin
insert into auth.users (id, email) values ('a1000000-0000-0000-0000-000000000001','ip-alice@x'),('b2000000-0000-0000-0000-000000000002','ip-bob@x'),
  ('c3000000-0000-0000-0000-000000000003','ip-mallory@x'),('d4000000-0000-0000-0000-000000000004','ip-admin@x') on conflict do nothing;
insert into public.profiles (id, name) values ('a1000000-0000-0000-0000-000000000001','IP Alice'),('b2000000-0000-0000-0000-000000000002','IP Bob'),
  ('c3000000-0000-0000-0000-000000000003','IP Mallory'),('d4000000-0000-0000-0000-000000000004','IP Admin') on conflict (id) do nothing;
update public.profiles set role = 'admin' where id = 'd4000000-0000-0000-0000-000000000004';
\set A '''a1000000-0000-0000-0000-000000000001'''
\set B '''b2000000-0000-0000-0000-000000000002'''
\set M '''c3000000-0000-0000-0000-000000000003'''
\set D '''d4000000-0000-0000-0000-000000000004'''

-- ══ F-18 / F-49 likes: one notification per person and post, gone on unlike; counters follow a moved reaction ══════
select pg_temp.as_user(:A);
select pg_temp.step('alice posts twice', $$with x as (insert into public.posts (user_id, body) values ('a1000000-0000-0000-0000-000000000001','IP post one'),('a1000000-0000-0000-0000-000000000001','IP post two') returning id)
  insert into ids select 'p' || row_number() over (order by id), id from x$$);
select pg_temp.as_user(:B);
select pg_temp.step('bob likes, unlikes and likes post one again', $$insert into public.reactions (post_id, user_id, kind) values (pg_temp.id('p1'), 'b2000000-0000-0000-0000-000000000002', 'like');
  delete from public.reactions where post_id = pg_temp.id('p1') and user_id = 'b2000000-0000-0000-0000-000000000002';
  insert into public.reactions (post_id, user_id, kind) values (pg_temp.id('p1'), 'b2000000-0000-0000-0000-000000000002', 'like')$$);
select pg_temp.step('bob likes it once more the way the adapter does (upsert)', $$insert into public.reactions (post_id, user_id, kind) values (pg_temp.id('p1'), 'b2000000-0000-0000-0000-000000000002', 'like')
  on conflict (post_id, user_id) do update set post_id = excluded.post_id, user_id = excluded.user_id, kind = excluded.kind$$);
select pg_temp.as_user(:A);
select pg_temp.ok('like / unlike / like / upsert leaves exactly one "liked your post" notification', $$(select count(*) from public.notifications where type = 'like' and post_id = pg_temp.id('p1')) = 1$$);
select pg_temp.ok('like_count = 1', $$(select like_count from public.posts where id = pg_temp.id('p1')) = 1$$);
select pg_temp.as_user(:B);
select pg_temp.step('bob unlikes', $$delete from public.reactions where post_id = pg_temp.id('p1') and user_id = 'b2000000-0000-0000-0000-000000000002'$$);
select pg_temp.as_user(:A);
select pg_temp.ok('unlike removes the notification and the count', $$(select count(*) from public.notifications where type = 'like' and post_id = pg_temp.id('p1')) = 0 and (select like_count from public.posts where id = pg_temp.id('p1')) = 0$$);
select pg_temp.as_user(:B);
select pg_temp.step('bob likes post one, then moves the reaction to post two with an UPDATE (REST allows it)', $$insert into public.reactions (post_id, user_id, kind) values (pg_temp.id('p1'), 'b2000000-0000-0000-0000-000000000002', 'like');
  update public.reactions set post_id = pg_temp.id('p2') where post_id = pg_temp.id('p1') and user_id = 'b2000000-0000-0000-0000-000000000002'$$);
select pg_temp.as_user(:A);
select pg_temp.ok('a moved reaction moves the count: post one 0, post two 1 (= real reactions)', $$(select like_count from public.posts where id = pg_temp.id('p1')) = 0 and (select like_count from public.posts where id = pg_temp.id('p2')) = 1
  and (select count(*) from public.reactions where post_id = pg_temp.id('p2')) = 1$$);
select pg_temp.ok('... and the notification: none for post one, one for post two', $$(select count(*) from public.notifications where type = 'like' and post_id = pg_temp.id('p1')) = 0 and (select count(*) from public.notifications where type = 'like' and post_id = pg_temp.id('p2')) = 1$$);
select pg_temp.as_server();
select pg_temp.ok('one like counter trigger on reactions, and it covers UPDATE', $$(select count(*) from pg_trigger where tgrelid = 'public.reactions'::regclass and not tgisinternal and tgname like '%count%') = 1
  and (select tgtype & 16 = 16 from pg_trigger where tgrelid = 'public.reactions'::regclass and tgname = 'trg_like_count')$$);
select pg_temp.no('the database itself refuses a second like notification for the same person and post', $$insert into public.notifications (user_id, type, from_user, post_id) values ('a1000000-0000-0000-0000-000000000001','like','b2000000-0000-0000-0000-000000000002', (select v::bigint from ids where k = 'p2'))$$, '23505');

-- ══ F-17 deletes that foreign keys used to block ═══════════════════════════════════════════════════════════════════
select pg_temp.as_user(:B);
select pg_temp.step('bob comments on post two', $$with x as (insert into public.comments (post_id, user_id, body) values (pg_temp.id('p2'), 'b2000000-0000-0000-0000-000000000002', 'IP parent comment') returning id) insert into ids select 'c1', id from x$$);
select pg_temp.as_user(:M);
select pg_temp.step('mallory replies to bob''s comment', $$insert into public.comments (post_id, user_id, body, parent_id) values (pg_temp.id('p2'), 'c3000000-0000-0000-0000-000000000003', 'IP reply', pg_temp.id('c1'))$$);
select pg_temp.as_user(:B);
select pg_temp.rows('del_c1', $$delete from public.comments where id = pg_temp.id('c1')$$);
select pg_temp.ok('bob can delete his comment although someone replied (the reply goes with it)', $$pg_temp.id('del_c1') = 1 and (select count(*) from public.comments where post_id = pg_temp.id('p2')) = 0$$);
select pg_temp.ok('comment_count follows (0)', $$(select comment_count from public.posts where id = pg_temp.id('p2')) = 0$$);
select pg_temp.step('bob comments again', $$insert into public.comments (post_id, user_id, body) values (pg_temp.id('p2'), 'b2000000-0000-0000-0000-000000000002', 'IP second comment')$$);
select pg_temp.as_user(:A);
select pg_temp.ok('post two has notifications (like + comment) before the delete', $$(select count(*) from public.notifications where post_id = pg_temp.id('p2')) >= 2$$);
select pg_temp.rows('del_p2', $$delete from public.posts where id = pg_temp.id('p2')$$);
select pg_temp.ok('alice deletes her post that was liked and commented on', $$pg_temp.id('del_p2') = 1$$);
select pg_temp.as_server();
select pg_temp.ok('its notifications, reactions and comments went with it', $$(select count(*) from public.notifications where post_id = (select v::bigint from ids where k = 'p2')) = 0
  and (select count(*) from public.reactions where post_id = (select v::bigint from ids where k = 'p2')) = 0 and (select count(*) from public.comments where post_id = (select v::bigint from ids where k = 'p2')) = 0$$);
-- account deletion: mallory created a group, bob triggered notifications, the admin decided a verification request
select pg_temp.as_user(:M);
select pg_temp.step('mallory creates a group', $$with x as (insert into public.groups (name, created_by, type) values ('IP Group', 'c3000000-0000-0000-0000-000000000003', 'public') returning id) insert into ids select 'g1', id from x$$);
select pg_temp.as_user(:B);
select pg_temp.step('bob likes post one (alice gets a notification from bob)', $$insert into public.reactions (post_id, user_id, kind) values (pg_temp.id('p1'), 'b2000000-0000-0000-0000-000000000002', 'like')$$);
select pg_temp.as_server();
select pg_temp.step('a company, its verification request decided by the admin, and a sponsorship', $$
  with x as (insert into public.companies (name, type, slug, owner_id) values ('IP Pharma', 'Manufacturer', 'ip-pharma', 'a1000000-0000-0000-0000-000000000001') returning id) insert into ids select 'co', id from x;
  insert into public.verification_requests (company_id, submitted_by, registry, status, reviewed_by) values (pg_temp.id('co'), 'a1000000-0000-0000-0000-000000000001', 'IP-REG-1', 'rejected', 'd4000000-0000-0000-0000-000000000004');
  insert into public.notifications (user_id, type, from_user, message) values ('a1000000-0000-0000-0000-000000000001', 'verification', 'd4000000-0000-0000-0000-000000000004', 'IP decided'),
                                                                         ('a1000000-0000-0000-0000-000000000001', 'connection_request', 'b2000000-0000-0000-0000-000000000002', 'IP from bob');
  insert into public.sponsored_suppliers (company_id, name) values (pg_temp.id('co'), 'IP Sponsor')$$);
select pg_temp.rows('del_m', $$delete from auth.users where id = 'c3000000-0000-0000-0000-000000000003'$$);
select pg_temp.ok('the group creator''s account can be deleted (the group stays, without a creator)', $$pg_temp.id('del_m') = 1
  and (select created_by is null from public.groups where id = pg_temp.id('g1'))$$);
select pg_temp.rows('del_b', $$delete from auth.users where id = 'b2000000-0000-0000-0000-000000000002'$$);
select pg_temp.ok('an account that triggered notifications can be deleted (they stay without a sender)', $$pg_temp.id('del_b') = 1
  and not exists (select 1 from public.notifications where from_user = 'b2000000-0000-0000-0000-000000000002')
  and exists (select 1 from public.notifications where message = 'IP from bob' and from_user is null)$$);
select pg_temp.rows('del_d', $$delete from auth.users where id = 'd4000000-0000-0000-0000-000000000004'$$);
select pg_temp.ok('an admin who decided a verification request can be deleted (the decision keeps its status)', $$pg_temp.id('del_d') = 1
  and (select reviewed_by is null and status = 'rejected' from public.verification_requests where registry = 'IP-REG-1')$$);
select pg_temp.rows('del_co', $$delete from public.companies where id = pg_temp.id('co')$$);
select pg_temp.ok('a sponsored company can be deleted (the sponsorship goes with it)', $$pg_temp.id('del_co') = 1
  and not exists (select 1 from public.sponsored_suppliers where name = 'IP Sponsor')$$);
select pg_temp.ok('no NO ACTION foreign key left in public except payment_orders.product_code (intended)', $$(select coalesce(string_agg(conname, ','), '') from pg_constraint c join pg_namespace n on n.oid = c.connamespace
  where contype = 'f' and nspname = 'public' and confdeltype = 'a') = 'payment_orders_product_code_fkey'$$);

-- ══ F-48 group members: +1/−1 ═══════════════════════════════════════════════════════════════════════════════════════
insert into auth.users (id, email) values ('e5000000-0000-0000-0000-000000000005', 'ip-eve@x') on conflict do nothing;
select pg_temp.step('two people join the group, one leaves', $$
  insert into public.group_members (group_id, user_id, role) values (pg_temp.id('g1'), 'a1000000-0000-0000-0000-000000000001', 'member');
  insert into public.group_members (group_id, user_id, role) values (pg_temp.id('g1'), 'e5000000-0000-0000-0000-000000000005', 'member');
  delete from public.group_members where group_id = pg_temp.id('g1') and user_id = 'e5000000-0000-0000-0000-000000000005'$$);
select pg_temp.ok('member_count = real members', $$(select member_count from public.groups where id = pg_temp.id('g1')) = (select count(*) from public.group_members where group_id = pg_temp.id('g1'))$$);
select pg_temp.ok('the counter moves by +1/−1 (no recount that reads a stale count under concurrent joins)', $$(select prosrc !~* 'count\(\*\)' and prosrc ~ 'member_count \+ 1' from pg_proc where proname = 'group_member_count')$$);

-- ══ F-43 size limits ════════════════════════════════════════════════════════════════════════════════════════════════
select pg_temp.as_user(:A);
select pg_temp.step('a 10,000-character message is accepted', $$insert into public.messages (sender_id, receiver_id, body) values ('a1000000-0000-0000-0000-000000000001', 'e5000000-0000-0000-0000-000000000005', repeat('x', 10000))$$);
select pg_temp.no('a 10,001-character message is refused', $$insert into public.messages (sender_id, receiver_id, body) values ('a1000000-0000-0000-0000-000000000001', 'e5000000-0000-0000-0000-000000000005', repeat('x', 10001))$$, '23514');
select pg_temp.step('a profile with demo-sized text saves', $$update public.profiles set headline = 'Regulatory Affairs Manager · EDA · CTD dossiers', bio = repeat('Experienced in regulatory affairs and QA. ', 20),
  location = 'Cairo, Egypt', skills = array['GMP','EDA','ICH','CTD'] where id = 'a1000000-0000-0000-0000-000000000001'$$);
select pg_temp.no('a 6,000-character profile bio is refused', $$update public.profiles set bio = repeat('x', 6000) where id = 'a1000000-0000-0000-0000-000000000001'$$, '23514');
select pg_temp.step('alice creates a company page', $$insert into public.companies (name, type, slug) values ('IP Size Pharma', 'Manufacturer', 'ip-size-pharma')$$);
select pg_temp.no('a 40 KB company profile is refused', $$update public.companies set profile = jsonb_build_object('services', (select jsonb_agg(repeat('s', 100)) from generate_series(1, 400))) where slug = 'ip-size-pharma'$$, '23514');
select pg_temp.step('a normal company profile and about text save', $$update public.companies set profile = '{"services":["Toll manufacturing","Packaging"],"address":"Street 1","color":"#1a56db"}', bio = repeat('Leading manufacturer of finished dosage forms. ', 10), tagline = 'Quality medicines since 1998' where slug = 'ip-size-pharma'$$);
select pg_temp.ok('every limit is in force (validated)', $$(select count(*) from pg_constraint where conname in ('messages_body_len','profiles_text_len','companies_text_len','companies_profile_size','company_listings_text_len','deals_json_size','deal_events_size') and convalidated) = 7$$);

-- ══ F-166 the conversation list after a deleted message ═════════════════════════════════════════════════════════════
select pg_temp.step('alice writes three messages to eve', $$insert into public.messages (sender_id, receiver_id, body) values ('a1000000-0000-0000-0000-000000000001', 'e5000000-0000-0000-0000-000000000005', 'IP m1');
  insert into public.messages (sender_id, receiver_id, body) values ('a1000000-0000-0000-0000-000000000001', 'e5000000-0000-0000-0000-000000000005', 'IP m2');
  insert into public.messages (sender_id, receiver_id, body) values ('a1000000-0000-0000-0000-000000000001', 'e5000000-0000-0000-0000-000000000005', 'IP m3')$$);
select pg_temp.as_server();
select pg_temp.step('Drugbox deletes the newest one', $$delete from public.messages where body = 'IP m3'$$);
select pg_temp.ok('both heads now show the previous message, eve''s unread drops to the 3 left', $$(select last_body = 'IP m2' and unread = 3 from public.conversation_heads where owner = 'e5000000-0000-0000-0000-000000000005' and partner = 'a1000000-0000-0000-0000-000000000001')
  and (select last_body = 'IP m2' and last_from_me from public.conversation_heads where owner = 'a1000000-0000-0000-0000-000000000001' and partner = 'e5000000-0000-0000-0000-000000000005')$$);
select pg_temp.step('the whole conversation is deleted', $$delete from public.messages where sender_id = 'a1000000-0000-0000-0000-000000000001' and receiver_id = 'e5000000-0000-0000-0000-000000000005'$$);
select pg_temp.ok('... and both heads go', $$not exists (select 1 from public.conversation_heads where owner in ('a1000000-0000-0000-0000-000000000001','e5000000-0000-0000-0000-000000000005') and partner in ('a1000000-0000-0000-0000-000000000001','e5000000-0000-0000-0000-000000000005'))$$);

-- ══ F-110 / F-112 / F-46 / F-99 functions and catalog ═══════════════════════════════════════════════════════════════
select pg_temp.step('alice and eve exchange two messages', $$insert into public.messages (sender_id, receiver_id, body) values ('a1000000-0000-0000-0000-000000000001', 'e5000000-0000-0000-0000-000000000005', 'IP hello');
  insert into public.messages (sender_id, receiver_id, body) values ('e5000000-0000-0000-0000-000000000005', 'a1000000-0000-0000-0000-000000000001', 'IP hi')$$);
select pg_temp.as_user('e5000000-0000-0000-0000-000000000005');
select pg_temp.ok('conversation_messages / new_messages / my_last_message_id return only the caller''s own messages', $$(select count(*) from public.conversation_messages('a1000000-0000-0000-0000-000000000001')) = 2
  and (select bool_and(receiver_id = 'e5000000-0000-0000-0000-000000000005') from public.new_messages(0)) and (select count(*) from public.new_messages(0)) = 1
  and public.my_last_message_id() = (select max(id) from public.messages where receiver_id = 'e5000000-0000-0000-0000-000000000005')$$);
select pg_temp.as_user('f6000000-0000-0000-0000-000000000006');
select pg_temp.ok('a third person reads nothing of that conversation', $$(select count(*) from public.conversation_messages('a1000000-0000-0000-0000-000000000001')) = 0 and (select count(*) from public.new_messages(0)) = 0 and public.my_last_message_id() = 0$$);
select pg_temp.as_anon();
select pg_temp.no('anon cannot call conversation_messages', $$select * from public.conversation_messages('a1000000-0000-0000-0000-000000000001')$$, '42501');
select pg_temp.no('anon cannot call directory_companies_page', $$select public.directory_companies_page()$$, '42501');
select pg_temp.as_server();
select pg_temp.ok('get_reviews_many filters with `not r.hidden` (matches the partial index)', $$(select prosrc ~ 'not r\.hidden' and prosrc !~ 'coalesce\(r\.hidden' from pg_proc where proname = 'get_reviews_many')$$);
select pg_temp.ok('JIT is off for the API login role in this database', $$exists (select 1 from pg_db_role_setting s join pg_database d on d.oid = s.setdatabase
  where d.datname = current_database() and s.setrole = (select oid from pg_roles where rolname = 'authenticator') and 'jit=off' = any(s.setconfig))$$);
select pg_temp.ok('no two indexes with the same definition', $$not exists (select 1 from pg_indexes where schemaname = 'public' group by tablename, regexp_replace(indexdef, '^.* USING ', '') having count(*) > 1)$$);
select pg_temp.ok('no single-column index whose column already leads a wider plain index (write overhead)', $$not exists (
  select 1 from pg_index a join pg_index b on b.indrelid = a.indrelid and b.indexrelid <> a.indexrelid
  where a.indrelid in (select oid from pg_class where relnamespace = 'public'::regnamespace) and a.indnatts = 1 and b.indnatts > 1 and not a.indisunique
    and a.indpred is null and b.indpred is null and a.indexprs is null and b.indexprs is null and a.indkey[0] = b.indkey[0]
    and (select amname from pg_am m join pg_class c on c.relam = m.oid where c.oid = a.indexrelid) = 'btree'
    and (select amname from pg_am m join pg_class c on c.relam = m.oid where c.oid = b.indexrelid) = 'btree'
    and a.indoption[0] = b.indoption[0])$$);
select pg_temp.ok('0010''s (user_id, created_at desc) application index exists now', $$exists (select 1 from pg_indexes where indexname = 'idx_job_apps_user_created')$$);
-- the foreign keys that are looked up on every post / comment / account delete or on a hot read have an index
select pg_temp.ok('hot foreign keys are indexed (notifications, comments, products, jobs, companies, followers, saved, heads, deals)', $$not exists (
  select 1 from (values ('notifications','post_id'),('notifications','from_user'),('comments','parent_id'),('comments','user_id'),('products','user_id'),('jobs','user_id'),
      ('companies','owner_id'),('company_followers','user_id'),('saved_posts','post_id'),('saved_jobs','job_id'),('enquiries','user_id'),('groups','created_by'),
      ('conversation_heads','partner'),('deal_members','company_id'),('deal_events','actor'),('deals','assignee')) v(t, c)
  where not exists (select 1 from pg_index i join pg_attribute a on a.attrelid = i.indrelid and a.attnum = i.indkey[0]
                    where i.indrelid = ('public.' || v.t)::regclass and a.attname = v.c))$$);

-- ══ F-05 directory_companies_page: same row shape, stable pages ════════════════════════════════════════════════════
insert into auth.users (id, email) select pg_temp.u(i), 'ip' || i || '@x.test' from generate_series(1, 10000) i;
insert into public.companies (owner_id, name, slug, type, location, bio, status, registry, licensed, sectors, governorate, city, plan, profile, tagline, phone, email, website, created_at)
select case when i = 1 then pg_temp.u(1) when i % 10 = 0 then null else pg_temp.u(10 + (i * 7) % 9000) end, 'IP Company ' || lpad(i::text, 5, '0'), 'ip-company-' || i, 'Manufacturer',
       'Industrial zone ' || (i % 40), repeat('Leading manufacturer of finished dosage forms for the Egyptian and Gulf markets. ', 4),
       case when i % 10 = 0 then 'unclaimed' when i % 10 in (1, 2) then 'pending' when i % 97 = 0 then 'suspended' else 'verified' end,
       case when i % 10 in (0, 1, 2) then null else 'CR-' || (100000 + i) end, i % 2 = 0,
       array[(array['Finished dosage','API','CMO','Distribution','Cosmetics'])[1 + i % 5]], (array['Cairo','Giza','Alexandria','10th of Ramadan','6th October'])[1 + i % 5], 'City ' || (i % 50),
       case when i % 50 = 0 then 'vip' else 'free' end, jsonb_build_object('services', array['Toll manufacturing','Packaging','Stability studies'], 'address', 'Street ' || i, 'color', '#1a56db'),
       'Quality medicines since ' || (1980 + i % 40), '+20 2 ' || (20000000 + i), 'info' || i || '@company.test', 'https://company' || i || '.test', now() - (i % 700) * interval '1 day'
from generate_series(1, 5000) i;
insert into ids select 'co' || s.i, c.id from generate_series(1, 2) s(i) join public.companies c on c.slug = 'ip-company-' || s.i;
insert into public.company_members (company_id, user_id, role, accepted, show_public)
select c.id, pg_temp.u(10 + (c.id * 13 + k * 101) % 9000), (array['admin','sales','quality'])[k], k < 3, k < 3 from public.companies c, generate_series(1, 3) k where c.slug like 'ip-company-%' on conflict do nothing;
insert into public.company_members (company_id, user_id, role, accepted, show_public) values (pg_temp.id('co2'), pg_temp.u(1), 'sales', true, true) on conflict do nothing;
insert into public.company_products (company_id, name, active_ingredient, active_ingredient_ar, dosage_form, strength, role)
select c.id, 'Product ' || c.id || '-' || k, (array['Metformin','Amoxicillin','Paracetamol','Atorvastatin','Omeprazole','Ibuprofen'])[1 + (c.id + k) % 6], 'مادة فعالة', (array['Tablet','Capsule','Syrup'])[1 + k % 3], '500 mg',
       (array['manufacturer','registration_holder','supplier'])[1 + k % 3] from public.companies c, generate_series(1, 10) k where c.slug like 'ip-company-%';
insert into public.company_sites (company_id, name, type, city, governorate) select c.id, 'Main plant', 'factory', c.city, c.governorate from public.companies c where c.slug like 'ip-company-%';
insert into public.site_certificates (site_id, company_id, name, expiry, source, checked_at)
select s.id, s.company_id, (array['GMP','ISO 9001','ISO 17025','GDP'])[1 + (s.company_id + k) % 4], current_date + ((s.company_id * k) % 900 - 100)::int, 'company', case when (s.company_id + k) % 2 = 0 then now() end
from public.company_sites s join public.companies c on c.id = s.company_id and c.slug like 'ip-company-%', generate_series(1, 2) k;
analyze public.companies; analyze public.company_members; analyze public.company_products; analyze public.site_certificates;
select pg_temp.as_user(pg_temp.u(1)::text);
select pg_temp.ok('a page has the same keys as a directory_companies() row', $$(select array_agg(k order by k) from json_object_keys((public.directory_companies_page(1)) -> 0) k)
  = (select array_agg(k order by k) from json_object_keys((public.directory_companies(1)) -> 0) k)$$);
select pg_temp.ok('pages 1 and 2 do not overlap and follow one order (verified, VIP, name)', $$(with a as (select (e ->> 'id')::bigint id, n from json_array_elements(public.directory_companies_page(100, 0)) with ordinality t(e, n)),
       b as (select (e ->> 'id')::bigint id, n + 100 as n from json_array_elements(public.directory_companies_page(100, 100)) with ordinality t(e, n)),
       ab as (select * from a union all select * from b),
       ref as (select c.id, row_number() over (order by (c.status = 'verified') desc, (c.plan = 'vip') desc, c.name, c.id) n from public.companies c where c.status <> 'suspended')
  select count(*) = 200 and count(distinct id) = 200 and bool_and(ab.n = ref.n) from ab join ref using (id))$$);
select pg_temp.ok('a page holds at most 200 companies', $$json_array_length(public.directory_companies_page(100000)) = 200$$);
select pg_temp.ok('"mine" marks exactly the caller''s companies (owner of company 1, member of company 2)', $$(select array_agg((e ->> 'id')::bigint order by (e ->> 'id')::bigint) from json_array_elements(public.directory_companies_page(200, 0, 'IP Company 0000')) e where (e ->> 'mine')::boolean)
  = array[pg_temp.id('co1'), pg_temp.id('co2')]$$);
select pg_temp.ok('search by product / ingredient finds companies', $$json_array_length(public.directory_companies_page(5, 0, 'Product ' || pg_temp.id('co2') || '-1')) >= 1$$);
select pg_temp.ok('no suspended company in the pages', $$not exists (select 1 from json_array_elements(public.directory_companies_page(200, 0)) e where e ->> 'status' = 'suspended')$$);

-- ══ launch-scale data (functional data above stays; everything is rolled back at the end) ══════════════════════════
select pg_temp.as_server();
-- 150k connections: u(1) has 500 friends, 20 of them are hubs with 3,000 connections each
alter table public.connections disable trigger user;
insert into public.connections (requester, addressee, status, created_at)
select pg_temp.u(a), pg_temp.u(b), case when i % 20 < 17 then 'accepted' when i % 20 < 19 then 'pending' else 'rejected' end, now() - (i % 700) * interval '1 day'
from (select i, 1 + (abs(hashtext('ca' || i)) % 10000) a, 1 + (abs(hashtext('cb' || i)) % 10000) b from generate_series(1, 60000) i) s where a <> b on conflict do nothing;
insert into public.connections (requester, addressee, status, created_at) select pg_temp.u(1), pg_temp.u(100 + i), 'accepted', now() - i * interval '1 hour' from generate_series(1, 500) i on conflict do nothing;
alter table public.connections enable trigger user;
analyze public.connections;
-- F-47: below the new bounds (an ordinary person: ~10 friends with ~10 connections each) the suggestions are the 0003 ones
create function pg_temp.suggest_0003(p_me uuid, p_limit int) returns table (id uuid, mutual int) language sql stable as $$
  with me as (select p_me as uid),
  lim as (select least(greatest(coalesce(p_limit, 12), 1), 50) as n),
  friends as (select case when c.requester = me.uid then c.addressee else c.requester end as fid
              from public.connections c, me where c.status = 'accepted' and (c.requester = me.uid or c.addressee = me.uid)),
  known as (select case when c.requester = me.uid then c.addressee else c.requester end as pid
            from public.connections c, me where c.requester = me.uid or c.addressee = me.uid),
  second as (select case when c.requester = f.fid then c.addressee else c.requester end as pid, count(*)::int as mutual
             from public.connections c join friends f on f.fid in (c.requester, c.addressee) where c.status = 'accepted' group by 1),
  ranked as (select s.pid, s.mutual from second s, me where s.pid <> me.uid and s.pid not in (select pid from known) order by s.mutual desc limit (select n from lim)),
  fill as (select p.id as pid, 0 as mutual from public.profiles p, me where p.id <> me.uid and p.id not in (select pid from known) and p.id not in (select pid from ranked)
           order by p.created_at desc limit (select n from lim))
  select x.pid, x.mutual from (select * from ranked union all select * from fill) x order by x.mutual desc limit (select n from lim)
$$;
create temp table sug_cmp (who int, v text, id uuid, mutual int); grant all on sug_cmp to authenticated;
insert into sug_cmp select w, 'old', x.id, x.mutual from generate_series(50, 59) w, pg_temp.suggest_0003(pg_temp.u(w), 12) x;
create function pg_temp.sug_new(w int) returns void language plpgsql as $$ begin
  perform pg_temp.as_user(pg_temp.u(w)::text); insert into sug_cmp select w, 'new', x.id, x.mutual from public.suggest_people(12) x; perform pg_temp.as_server(); end $$;
select pg_temp.sug_new(w) from generate_series(50, 59) w;
-- (ties in mutual count / join date may come out in another order: the ranking is compared by its mutual counts and by the
--  people strictly above the lowest count)
select pg_temp.ok('suggest_people for ten ordinary people: same ranking as 0003 (mutual counts, and the same people above the cut)', $$not exists (
  select 1 from generate_series(50, 59) w
  where (select array_agg(mutual order by mutual desc) from sug_cmp where who = w and v = 'old') is distinct from (select array_agg(mutual order by mutual desc) from sug_cmp where who = w and v = 'new')
     or (select array_agg(id order by id) from sug_cmp where who = w and v = 'old' and mutual > (select min(mutual) from sug_cmp where who = w and v = 'old'))
        is distinct from (select array_agg(id order by id) from sug_cmp where who = w and v = 'new' and mutual > (select min(mutual) from sug_cmp where who = w and v = 'new')))
  and (select count(*) from sug_cmp where v = 'new') = 120 and (select sum(mutual) from sug_cmp where v = 'new') > 0$$);
-- 20 of u(1)'s friends are hubs with 3,000 connections each
alter table public.connections disable trigger user;
insert into public.connections (requester, addressee, status) select pg_temp.u(100 + h), pg_temp.u(1 + (h * 977 + k * 3) % 10000), 'accepted' from generate_series(1, 20) h, generate_series(1, 3000) k
 where pg_temp.u(100 + h) <> pg_temp.u(1 + (h * 977 + k * 3) % 10000) on conflict do nothing;
alter table public.connections enable trigger user;
-- 50k messages: u(1) has a 30,000-message conversation with u(2) and 20,000 from 500 partners
alter table public.messages disable trigger user;
insert into public.messages (sender_id, receiver_id, body, read_at, created_at)
select case when k % 2 = 0 then pg_temp.u(1) else pg_temp.u(2) end, case when k % 2 = 0 then pg_temp.u(2) else pg_temp.u(1) end, 'Hot message ' || k, now(), now() - (30000 - k) * interval '1 minute' from generate_series(1, 30000) k;
insert into public.messages (sender_id, receiver_id, body, read_at, created_at)
select pg_temp.u(3000 + i % 500), pg_temp.u(1), 'Message ' || i, case when i % 10 <> 0 then now() end, now() - i * interval '2 minute' from generate_series(1, 20000) i;
alter table public.messages enable trigger user;
-- 20k deals (300 touch company 1 / u(1)), 60k events, group members
insert into public.deals (ref, type, title, from_company_id, from_user, to_company_id, lines, status, ontime, group_key, offer, created_at, updated_at)
select 'IPD' || i, t.ty, 'IP Deal ' || i, case when t.ty = 'job' then null when i <= 100 then pg_temp.id('co1') else pg_temp.id('co2') + 1 + (i * 3) % 4990 end,
       case when i <= 100 then pg_temp.u(1) else pg_temp.u(10 + (i * 13) % 9000) end,
       case when i > 100 and i <= 300 then pg_temp.id('co1') else pg_temp.id('co2') + 1 + (i * 7 + 1) % 4990 end, jsonb_build_object('qty', 100, 'unit', 'kg', 'price', 'USD 5.8'),
       case when i % 4 = 0 then 'delivered' when i % 4 = 1 then 'closed' when i % 4 = 2 then 'sent' else 'quoted' end, i % 5 <> 0,
       case when t.ty = 'group' then 'G' || i end, jsonb_build_object('price', 'USD 5.5', 'validity', '14 days'), now() - (i % 365) * interval '1 day', now() - ((i * 7919) % 525600) * interval '1 minute'
from (select i, (array['quote','service','surplus','questionnaire','dossier','job','group'])[1 + i % 7] ty from generate_series(1, 20000) i) t
where not (t.ty <> 'job' and (case when i <= 100 then pg_temp.id('co1') else pg_temp.id('co2') + 1 + (i * 3) % 4990 end) = (case when i > 100 and i <= 300 then pg_temp.id('co1') else pg_temp.id('co2') + 1 + (i * 7 + 1) % 4990 end));
insert into public.deal_events (deal_id, side, action, note, data, actor, created_at)
select d.id, case when k = 2 then 'to' else 'from' end, case when k = 1 then 'sent' when k = 2 then 'quote' else 'rate' end, 'note ' || k,
       case when k = 3 then jsonb_build_object('stars', 1 + d.id % 5) else '{}'::jsonb end, d.from_user, d.created_at + k * interval '1 hour'
from public.deals d, generate_series(1, 3) k where d.title like 'IP Deal %';
insert into public.deal_members (deal_id, company_id, qty) select d.id, pg_temp.id('co2') + 1 + (d.id * 5 + k) % 4990, 50 from public.deals d, generate_series(1, 2) k where d.type = 'group' and d.title like 'IP Deal %' on conflict do nothing;
-- 20k job reviews (10% hidden) about 2,000 people
insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1, c2, c3, c4, body, anonymous, hidden, created_at)
select pg_temp.u(a), pg_temp.u(b), case when i % 2 = 0 then 'employer' else 'candidate' end, 1 + i % 5, 1 + (i / 2) % 5, 1 + (i / 3) % 5, 1 + (i / 4) % 5,
       'Review ' || i || ': professional, transparent about salary and respectful of time.', i % 14 = 0, i % 10 = 0, now() - (i % 365) * interval '1 day'
from (select i, 1 + (abs(hashtext('rv' || i)) % 10000) a, 1 + (abs(hashtext('re' || i)) % 2000) b from generate_series(1, 20000) i) s where a <> b on conflict do nothing;
-- 30k notifications, 20k listings
insert into public.notifications (user_id, type, from_user, message, read, created_at)
select pg_temp.u(1 + i % 10000), (array['comment','connection_request','deal'])[1 + i % 3], pg_temp.u(1 + (i * 7) % 10000), 'IP n', i % 5 <> 0, now() - (i % 365) * interval '1 day' from generate_series(1, 30000) i;
insert into public.company_listings (ref, company_id, kind, product, qty, batch, expiry, price, off, reg_status, markets, deal_kind, active, created_at)
select 'IPL' || i, pg_temp.id('co1') + i % 4990, case when i % 2 = 0 then 'surplus' else 'dossier' end, 'Listing product ' || i, '500 kg', 'B' || i, '2027-06', 'USD 12/kg', 20, 'Registered', 'Egypt', 'licence', i % 10 <> 0, now() - (i % 365) * interval '1 day' from generate_series(1, 20000) i;
-- 20k company follows (u(1) follows 30 pages)
insert into public.company_followers (company_id, user_id) select pg_temp.id('co1') + (i * 31) % 4990, pg_temp.u(10 + (i * 17) % 9000) from generate_series(1, 20000) i on conflict do nothing;
insert into public.company_followers (company_id, user_id) select pg_temp.id('co1') + i * 7, pg_temp.u(1) from generate_series(1, 30) i on conflict do nothing;
-- three people with nothing yet (account deletions are measured on them)
insert into auth.users (id, email) select pg_temp.u(20000 + i), 'ip-empty' || i || '@x.test' from generate_series(1, 9) i;
analyze;

-- ══ F-04 deals visibility is unchanged (checked at scale, against the rule written out) ════════════════════════════
create temp table vis (who text, ids bigint[]); grant all on vis to authenticated;
select pg_temp.as_user(pg_temp.u(1)::text);
insert into vis select 'u1', array(select id from public.deals order by id);
insert into vis select 'u1-events', array(select e.id from public.deal_events e order by e.id);
select pg_temp.as_user(pg_temp.u(9999)::text);
insert into vis select 'light', array(select id from public.deals order by id);
select pg_temp.as_server();
select pg_temp.ok('u1 (owner of company 1, sales in company 2) sees exactly: own person deals, both sides of its companies, all group orders',
  $$(select ids from vis where who = 'u1') = array(select d.id from public.deals d where (d.from_company_id is null and d.from_user = pg_temp.u(1))
     or d.to_company_id in (pg_temp.id('co1'), pg_temp.id('co2')) or d.from_company_id in (pg_temp.id('co1'), pg_temp.id('co2')) or d.type = 'group' order by d.id)
   and cardinality((select ids from vis where who = 'u1')) > 3000$$);
select pg_temp.ok('a person without companies sees own person deals and group orders only', $$(select ids from vis where who = 'light') = array(select d.id from public.deals d where (d.from_company_id is null and d.from_user = pg_temp.u(9999)) or d.type = 'group' order by d.id)$$);
select pg_temp.ok('deal events are visible exactly for the visible deals', $$(select ids from vis where who = 'u1-events') = array(select e.id from public.deal_events e where e.deal_id = any(array(select unnest(ids) from vis where who = 'u1')) order by e.id)$$);

-- the directory's rating / reviews per card are the company page's (company_track_record) — checked where that rule is
-- 0021's (rated deals to the company, jobs excluded, related companies ignored), which company_ratings() follows
select pg_temp.as_user(pg_temp.u(1)::text);
select pg_temp.ok('directory cards carry the same rating and review count as the full track record (first 200 companies)', $$
  (select prosrc !~ '<> ''job''' from pg_proc where proname = 'company_track_record')
  or not exists (select 1 from json_array_elements(public.directory_companies_page(200, 0)) e
                 where (e -> 'track' ->> 'rating') is distinct from (public.company_track_record((e ->> 'id')::bigint) ->> 'rating')
                    or (e -> 'track' ->> 'reviews')::int <> (public.company_track_record((e ->> 'id')::bigint) ->> 'reviews')::int)
  and (select count(*) from json_array_elements(public.directory_companies_page(200, 0)) e where (e -> 'track' ->> 'reviews')::int > 0) > 20$$);
select pg_temp.as_server();

-- ══ timings: AFTER 0022 ════════════════════════════════════════════════════════════════════════════════════════════
\set deals_q 'SELECT d.*, COALESCE(ev.deal_events, ''[]'') AS deal_events, COALESCE(dm.deal_members, ''[]'') AS deal_members, row_to_json(fc.*) AS fc, row_to_json(tc.*) AS tc, row_to_json(fu.*) AS fu FROM public.deals d LEFT JOIN LATERAL (SELECT json_agg(e) AS deal_events FROM (SELECT e.* FROM public.deal_events e WHERE e.deal_id = d.id) e) ev ON TRUE LEFT JOIN LATERAL (SELECT json_agg(m) AS deal_members FROM (SELECT m.qty, row_to_json(co.*) AS co FROM public.deal_members m LEFT JOIN LATERAL (SELECT c.slug, c.name FROM public.companies c WHERE c.id = m.company_id) co ON TRUE WHERE m.deal_id = d.id) m) dm ON TRUE LEFT JOIN LATERAL (SELECT c.slug, c.name FROM public.companies c WHERE c.id = d.from_company_id) fc ON TRUE LEFT JOIN LATERAL (SELECT c.slug, c.name FROM public.companies c WHERE c.id = d.to_company_id) tc ON TRUE LEFT JOIN LATERAL (SELECT p.name FROM public.profiles p WHERE p.id = d.from_user) fu ON TRUE ORDER BY d.updated_at DESC LIMIT 300'
\set listings_q 'select l.*, row_to_json(co.*) as co from public.company_listings l left join lateral (select c.slug, c.name from public.companies c where c.id = l.company_id) co on true where l.active order by l.created_at desc limit 500'
create function pg_temp.timings(v text) returns void language plpgsql as $$ begin
  perform pg_temp.as_user(pg_temp.u(1)::text);
  perform pg_temp.perf('GET /deals (u1, 300 rows + events + members)', v, current_setting('ip.deals_q'));
  perform pg_temp.perf('directory: whole list (5,000)', v, 'select public.directory_companies(5000)', case when v like 'before%' then 1 else 2 end);
  if v like 'after%' then perform pg_temp.perf('directory: one page (100)', v, 'select public.directory_companies_page(100, 0)'); end if;
  perform pg_temp.perf('suggest_people (500 friends, 20 hubs)', v, 'select * from public.suggest_people(12)');
  perform pg_temp.perf('conversation_messages (30k-message chat)', v, 'select * from public.conversation_messages(''' || pg_temp.u(2) || ''')');
  perform pg_temp.perf('live start: newest message id to me', v, 'select id from public.messages where receiver_id = ''' || pg_temp.u(1) || ''' order by id desc limit 1');
  perform pg_temp.perf('get_reviews_many (60 people)', v, 'select * from public.get_reviews_many(array(select pg_temp.u(i) from generate_series(1, 60) i), ''employer'')');
  perform pg_temp.perf('listings page (500 active + company)', v, current_setting('ip.listings_q'));
  perform pg_temp.perf('pages I follow (company_followers?user_id)', v, 'select * from public.company_followers where user_id = ''' || pg_temp.u(1) || '''');
  perform pg_temp.as_user(pg_temp.u(9999)::text);
  perform pg_temp.perf('GET /deals (person without companies)', v, current_setting('ip.deals_q'));
  perform pg_temp.as_server();
  perform pg_temp.perf('delete an account with no activity', v, 'delete from auth.users where id = ''' || pg_temp.u(20000 + case when v like 'before%' then 1 else 2 end) || '''', 1);
end $$;
select set_config('ip.deals_q', :'deals_q', true), set_config('ip.listings_q', :'listings_q', true);
set local jit = off;
select pg_temp.timings('after (jit off)');
set local jit = on;
select pg_temp.timings('after (jit on)');

-- ══ timings: BEFORE 0022 (old policies, functions and indexes put back in a savepoint, then rolled back) ═══════════
savepoint before_0022;
select pg_temp.as_server();
drop index public.idx_deals_updated; drop index public.idx_companies_owner; drop index public.idx_company_followers_user; drop index public.idx_listings_active_created;
drop index public.idx_notifs_from; drop index public.idx_comments_user; drop index public.idx_heads_partner; drop index public.idx_refs_author; drop index public.idx_jobs_user;
drop index public.idx_products_user; drop index public.idx_enquiries_user; drop index public.idx_groups_created_by; drop index public.idx_deal_events_actor; drop index public.idx_deals_assignee;
drop index public.idx_listings_created_by; drop index public.idx_job_apps_user_created;
create index idx_msgs_receiver on public.messages (receiver_id); create index idx_conn_requester on public.connections (requester); create index idx_conn_addressee on public.connections (addressee);
create index idx_job_apps_user on public.job_applications (user_id);
drop policy "deals: the two sides read" on public.deals;
create policy "deals: the two sides read" on public.deals for select
  using ((from_company_id is null and from_user = (select auth.uid())) or public.is_company_member(to_company_id) or (from_company_id is not null and public.is_company_member(from_company_id)));
drop policy "deal events: the two sides read" on public.deal_events;
create policy "deal events: the two sides read" on public.deal_events for select using (exists (select 1 from public.deals d where d.id = deal_id));
drop policy "deal members: readable with the deal" on public.deal_members;
create policy "deal members: readable with the deal" on public.deal_members for select using (exists (select 1 from public.deals d where d.id = deal_id));
create or replace function public.get_reviews_many(p_ids uuid[], p_role text)
returns table (reviewee uuid, id bigint, author text, anonymous boolean, c1 smallint, c2 smallint, c3 smallint, c4 smallint, body text, created_at timestamptz, mine boolean)
language sql stable security definer set search_path = public as $$
  select r.reviewee, r.id, case when r.anonymous then null else p.name end, r.anonymous, r.c1, r.c2, r.c3, r.c4, r.body, r.created_at, r.reviewer = auth.uid()
  from public.job_reviews r join public.profiles p on p.id = r.reviewer
  where r.reviewee = any(p_ids) and r.reviewee_role = p_role and not coalesce(r.hidden, false)
  order by r.created_at desc limit 2000
$$;
alter function public.conversation_messages(uuid, bigint, int) security invoker;
create or replace function public.suggest_people(p_limit int default 12)
returns table (id uuid, name text, headline text, company text, country text, verified boolean, avatar_url text, location text,
               followers_count int, open_to_work boolean, hiring boolean, mutual int)
language sql stable security definer set search_path = public as $$
  with me as (select auth.uid() as uid),
  lim as (select least(greatest(coalesce(p_limit, 12), 1), 50) as n),
  friends as (select case when c.requester = me.uid then c.addressee else c.requester end as fid
              from public.connections c, me where c.status = 'accepted' and (c.requester = me.uid or c.addressee = me.uid)),
  known as (select case when c.requester = me.uid then c.addressee else c.requester end as pid
            from public.connections c, me where c.requester = me.uid or c.addressee = me.uid),
  second as (select case when c.requester = f.fid then c.addressee else c.requester end as pid, count(*)::int as mutual
             from public.connections c join friends f on f.fid in (c.requester, c.addressee) where c.status = 'accepted'
             group by 1),
  ranked as (select s.pid, s.mutual from second s, me where s.pid <> me.uid and s.pid not in (select pid from known)
             order by s.mutual desc limit (select n from lim)),
  fill as (select p.id as pid, 0 as mutual from public.profiles p, me where p.id <> me.uid
             and p.id not in (select pid from known) and p.id not in (select pid from ranked)
           order by p.created_at desc limit (select n from lim))
  select p.id, p.name, p.headline, p.company, p.country::text, p.verified, p.avatar_url, p.location, p.followers_count, p.open_to_work, p.hiring, x.mutual
  from (select * from ranked union all select * from fill) x join public.profiles p on p.id = x.pid
  where auth.uid() is not null
  order by x.mutual desc, p.created_at desc
  limit (select n from lim)
$$;
analyze public.messages; analyze public.connections;
select pg_temp.as_server();
select pg_temp.timings('before (jit on)');
-- keep the measurements (psql variables outlive the rollback), undo the old schema
select coalesce((select json_agg(p) from perf p where variant like 'before%'), '[]') as perf_before \gset
rollback to savepoint before_0022;
insert into perf (label, variant, ms, jit, seq, idx) select label, variant, ms, jit, seq, idx from json_populate_recordset(null::perf, :'perf_before');

-- ══ speed checks ════════════════════════════════════════════════════════════════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(1)::text);
create temp table sug_hub as select id, mutual from public.suggest_people(12);
select pg_temp.as_server();
select pg_temp.ok('suggest_people for a person with 500 friends (20 of them hubs): 12 people, never themself or someone they know', $$(select count(*) from sug_hub) = 12
  and not exists (select 1 from sug_hub s where s.id = pg_temp.u(1) or exists (select 1 from public.connections c where (c.requester = pg_temp.u(1) and c.addressee = s.id) or (c.addressee = pg_temp.u(1) and c.requester = s.id)))
  and (select min(mutual) from sug_hub) > 0$$);
select pg_temp.ok('GET /deals: the plan is cheap enough that JIT never starts, even with jit on (before: 79 functions compiled)', $$(select max(jit) = 0 from perf where label like 'GET /deals%' and variant like 'after%')$$);
select pg_temp.ok('GET /deals (u1): no sequential scan of deals, and at least 5x faster than before', $$(select coalesce(seq, '') !~ '(^|,)deals(,|$)' from perf where label like 'GET /deals (u1%' and variant = 'after (jit off)')
  and pg_temp.ms('GET /deals (u1, 300 rows + events + members)', 'after (jit off)') * 5 < pg_temp.ms('GET /deals (u1, 300 rows + events + members)', 'before (jit on)')$$);
select pg_temp.ok('GET /deals (person without companies): at least 5x faster than before', $$pg_temp.ms('GET /deals (person without companies)', 'after (jit off)') * 5 < pg_temp.ms('GET /deals (person without companies)', 'before (jit on)')$$);
select pg_temp.ok('directory: one page is at least 10x faster than the whole list and weighs under 300 KB', $$pg_temp.ms('directory: one page (100)', 'after (jit off)') * 10 < pg_temp.ms('directory: whole list (5,000)', 'before (jit on)')
  and (select length(public.directory_companies_page(100, 0)::text) < 300 * 1024)$$);
-- inside a definer function the plan is not shown by EXPLAIN of the call: the bodies' queries are explained directly,
-- as the function owner runs them
select pg_temp.perf('inner: get_reviews_many body', 'after (jit off)', 'select r.id from public.job_reviews r where r.reviewee = any(array(select pg_temp.u(i) from generate_series(1, 60) i)) and r.reviewee_role = ''employer'' and not r.hidden');
select pg_temp.perf('inner: get_reviews_many body', 'before (jit on)', 'select r.id from public.job_reviews r where r.reviewee = any(array(select pg_temp.u(i) from generate_series(1, 60) i)) and r.reviewee_role = ''employer'' and not coalesce(r.hidden, false)');
select pg_temp.ok('get_reviews_many''s predicate uses the reviews index (no scan of job_reviews)', $$(select coalesce(seq, '') !~ 'job_reviews' and idx ~ 'idx_job_reviews_reviewee' from perf where label = 'inner: get_reviews_many body' and variant = 'after (jit off)')$$);
select pg_temp.perf('inner: conversation_messages body', 'after (jit off)', 'select m.id from public.messages m where least(m.sender_id, m.receiver_id) = least(''' || pg_temp.u(1) || '''::uuid, ''' || pg_temp.u(2) || '''::uuid) and greatest(m.sender_id, m.receiver_id) = greatest(''' || pg_temp.u(1) || '''::uuid, ''' || pg_temp.u(2) || '''::uuid) order by least(m.sender_id, m.receiver_id), greatest(m.sender_id, m.receiver_id), m.created_at desc, m.id desc limit 50');
select pg_temp.ok('conversation_messages reads the pair index', $$(select idx ~ 'idx_msgs_pair' and coalesce(seq, '') !~ 'messages' from perf where label = 'inner: conversation_messages body' and variant = 'after (jit off)')$$);
select pg_temp.ok('the listings page and "pages I follow" read by index', $$(select bool_and(coalesce(seq, '') !~ '(company_listings|company_followers)') from perf where (label like 'listings page%' or label like 'pages I follow%') and variant = 'after (jit off)')$$);
select pg_temp.ok('with JIT off nothing is compiled', $$(select max(jit) = 0 from perf where variant = 'after (jit off)')$$);

-- ══ report ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
select pg_temp.as_server();
select :'LAST_ERROR_SQLSTATE' = '00000' as clean, :'LAST_ERROR_MESSAGE' as lastmsg \gset
insert into r(name, ok, err) select 'no statement of the suite failed outside a check', :'clean'::boolean, nullif(:'lastmsg', '');
\o
\pset tuples_only on
\pset format unaligned
select 'TIMINGS (ms, planning + execution, best of 3; "before" = 0001–0021 shapes put back in a savepoint)';
select rpad(l.label, 46) || ' before ' || lpad(coalesce(b.ms::text, '-'), 8) || ' | after jit off ' || lpad(coalesce(a.ms::text, '-'), 7) || ' | after jit on ' || lpad(coalesce(j.ms::text, '-'), 7)
       || ' | x' || coalesce(round(b.ms / nullif(a.ms, 0), 1)::text, '-') || ' | jit fns before ' || coalesce(b.jit, 0) || ' | seq scans after: ' || coalesce(a.seq, 'none')
  from (select distinct label, min(n) over (partition by label) o from perf) l
  left join perf b on b.label = l.label and b.variant = 'before (jit on)' left join perf a on a.label = l.label and a.variant = 'after (jit off)'
  left join perf j on j.label = l.label and j.variant = 'after (jit on)' order by l.o;
select 'payload: directory_companies(5000) ' || pg_size_pretty(length(public.directory_companies(5000)::text)::bigint) || ', directory_companies_page(100) ' || pg_size_pretty(length(public.directory_companies_page(100, 0)::text)::bigint);
select (case when ok then 'PASS  ' else 'FAIL  ' end) || name || coalesce('   [' || err || ']', '') from r order by n;
select 'TOTAL ' || count(*) filter (where ok) || ' / ' || count(*) from r;
\set ON_ERROR_STOP on
do $$ declare f int; t int; begin select count(*) filter (where not ok), count(*) into f, t from r;
  if t = 0 or f > 0 then raise exception '% of % check(s) FAILED', f, t; end if; end $$;
rollback;
