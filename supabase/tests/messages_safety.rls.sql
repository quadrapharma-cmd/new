-- Messages: mute, block and report a conversation (0031, J-SOCIAL-40). Mutes and blocks are private to their owner; a block
-- makes the database refuse messages both ways; a report carries the reported person's messages as the database copied them,
-- and only Drugbox moderators read and close it.
-- Runs as the real API roles with a JWT, in one transaction that is rolled back; test data carries the "MX " marker.
-- Run on a fresh database (stub + migrations): psql -f supabase/tests/messages_safety.rls.sql
-- Harness as in followups.rls.sql: step()/ok()/no(); a negative check passes only with the expected SQLSTATE; non-zero exit on failure.
\set QUIET on
\set ON_ERROR_ROLLBACK on
set client_min_messages = warning;
\o /dev/null
begin;
create temp table r (n serial, name text, ok boolean, err text); grant all on r to authenticated, anon, service_role; grant all on r_n_seq to authenticated, anon, service_role;
create temp table ids (k text primary key, v text); grant all on ids to authenticated, anon, service_role;
create function pg_temp.as_user(u uuid) returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', u::text, true); perform set_config('request.jwt.claims', json_build_object('sub', u, 'role', 'authenticated')::text, true);
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
create function pg_temp.u(n int) returns uuid language sql immutable as $$ select ('f3100000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid $$;

-- people: u1 the member who protects herself, u2 the sender she mutes / blocks / reports, u3 an outsider, u4 a Drugbox moderator
select pg_temp.as_server();
insert into auth.users (id, email) select pg_temp.u(g), 'mx' || g || '@mx31.test' from generate_series(1, 4) g on conflict do nothing;
insert into public.profiles (id, name) select pg_temp.u(g), 'MX person ' || g from generate_series(1, 4) g on conflict (id) do nothing;
update public.profiles set role = 'moderator' where id = pg_temp.u(4);
insert into public.messages (sender_id, receiver_id, body) values (pg_temp.u(2), pg_temp.u(1), 'MX buy my product 1'), (pg_temp.u(2), pg_temp.u(1), 'MX buy my product 2'),
  (pg_temp.u(1), pg_temp.u(2), 'MX no thanks'), (pg_temp.u(2), pg_temp.u(3), 'MX to someone else');

-- ══ mute: one row per (owner, partner), private to the owner ═══════════════════════════════════
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 mutes u2', $$insert into public.conversation_mutes (partner) values (pg_temp.u(2))$$);
select pg_temp.ok('mute: the owner is the caller and she reads her mute', $$(select owner from public.conversation_mutes where partner = pg_temp.u(2)) = pg_temp.u(1)$$);
select pg_temp.no('mute: nobody mutes in someone else''s name', $$insert into public.conversation_mutes (owner, partner) values (pg_temp.u(3), pg_temp.u(2))$$, '42501');
select pg_temp.no('mute: not yourself', $$insert into public.conversation_mutes (partner) values (pg_temp.u(1))$$, '23514');
select pg_temp.ok('mute: muted messages still arrive', $$(select count(*) from public.messages where sender_id = pg_temp.u(2) and receiver_id = pg_temp.u(1)) = 2$$);
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.ok('mute: the muted person cannot see it', $$not exists (select 1 from public.conversation_mutes)$$);
select pg_temp.as_anon();
select pg_temp.ok('mute: anon reads nothing', $$not exists (select 1 from public.conversation_mutes)$$);

-- ══ block: the database refuses messages both ways ════════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 blocks u2', $$insert into public.user_blocks (blocked) values (pg_temp.u(2))$$);
select pg_temp.no('block: nobody blocks in someone else''s name', $$insert into public.user_blocks (blocker, blocked) values (pg_temp.u(3), pg_temp.u(2))$$, '42501');
select pg_temp.no('block: u1 cannot message the person she blocked', $$insert into public.messages (sender_id, receiver_id, body) values (pg_temp.u(1), pg_temp.u(2), 'MX after block')$$, '42501');
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.no('block: the blocked person cannot message u1', $$insert into public.messages (sender_id, receiver_id, body) values (pg_temp.u(2), pg_temp.u(1), 'MX after block')$$, '42501');
select pg_temp.ok('block: the blocked person is not told who blocked them (reads no block rows)', $$not exists (select 1 from public.user_blocks)$$);
select pg_temp.step('the blocked person still messages others', $$insert into public.messages (sender_id, receiver_id, body) values (pg_temp.u(2), pg_temp.u(3), 'MX still fine')$$);
select pg_temp.ok('block: …stored', $$exists (select 1 from public.messages where body = 'MX still fine')$$);
select pg_temp.ok('block: the guard is not callable from the API', $$not has_function_privilege('authenticated', 'public.messages_block_guard()', 'execute') and not has_function_privilege('anon', 'public.messages_block_guard()', 'execute')$$);

-- ══ report: the database copies the reported messages; only Drugbox closes it ════════════════
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 reports u2 with a made-up excerpt and status', $$with x as (insert into public.message_reports (reported, reason, details, excerpt, status)
  values (pg_temp.u(2), 'Spam or scam', 'Repeated offers', '[{"body":"invented"}]', 'actioned') returning id) insert into ids select 'rep', id from x$$);
select pg_temp.ok('report: filed as open by the caller', $$(select reporter = pg_temp.u(1) and status = 'open' from public.message_reports where id = pg_temp.id('rep'))$$);
select pg_temp.ok('report: the excerpt is what u2 actually sent u1 (not what the browser sent)', $$(select jsonb_array_length(excerpt) = 2 and excerpt::text like '%MX buy my product 1%'
  and excerpt::text not like '%invented%' and excerpt::text not like '%MX no thanks%' and excerpt::text not like '%someone else%' from public.message_reports where id = pg_temp.id('rep'))$$);
select pg_temp.step('u1 sends a report naming u3 as the reporter', $$insert into public.message_reports (reporter, reported, reason) values (pg_temp.u(3), pg_temp.u(2), 'MX forged')$$);
select pg_temp.as_server();
select pg_temp.ok('report: nobody reports in someone else''s name (the database files it as the caller)', $$not exists (select 1 from public.message_reports where reporter = pg_temp.u(3))
  and (select reporter from public.message_reports where reason = 'MX forged') = pg_temp.u(1)$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.no('report: a person who never wrote to you cannot be reported', $$insert into public.message_reports (reported, reason) values (pg_temp.u(4), 'x')$$, '42501');
select pg_temp.step('the reporter tries to close her own report', $$update public.message_reports set status = 'dismissed' where id = pg_temp.id('rep')$$);
select pg_temp.ok('report: …it stays open', $$(select status from public.message_reports where id = pg_temp.id('rep')) = 'open'$$);
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.ok('report: the reported person cannot read it', $$not exists (select 1 from public.message_reports)$$);
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.ok('report: an outsider cannot read it', $$not exists (select 1 from public.message_reports)$$);
select pg_temp.as_anon();
select pg_temp.ok('report: anon reads nothing', $$not exists (select 1 from public.message_reports)$$);
select pg_temp.as_user(pg_temp.u(4));
select pg_temp.ok('report: the moderator reads it', $$exists (select 1 from public.message_reports where id = pg_temp.id('rep'))$$);
select pg_temp.no('report: the moderator cannot change what was reported', $$update public.message_reports set excerpt = '[]' where id = pg_temp.id('rep')$$, '42501');
select pg_temp.step('the moderator takes action', $$update public.message_reports set status = 'actioned' where id = pg_temp.id('rep')$$);
select pg_temp.ok('report: closed, with who and when', $$(select status = 'actioned' and decided_by = pg_temp.u(4) and decided_at is not null from public.message_reports where id = pg_temp.id('rep'))$$);

-- ══ unblock ══════════════════════════════════════════════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 unblocks and unmutes u2', $$delete from public.user_blocks where blocked = pg_temp.u(2); delete from public.conversation_mutes where partner = pg_temp.u(2)$$);
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.step('u2 writes again', $$insert into public.messages (sender_id, receiver_id, body) values (pg_temp.u(2), pg_temp.u(1), 'MX after unblock')$$);
select pg_temp.as_server();
select pg_temp.ok('unblock: messages arrive again', $$exists (select 1 from public.messages where body = 'MX after unblock')$$);

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
