-- Network follow-ups (0030): following a person (S-11) with one follower count that never counts a pair twice, the
-- "started following you" notice once per pair, a declined request that its sender cannot clear and re-send (S-04),
-- suggestions ranked mutual → colleagues → newest and never a dismissed person (J-SOCIAL-34).
-- Runs as the real API roles with a JWT, in one transaction that is rolled back; test data carries the "NF " marker.
-- Run on a fresh database (stub + migrations): psql -f supabase/tests/network_followups.rls.sql
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
create function pg_temp.u(n int) returns uuid language sql immutable as $$ select ('f3000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid $$;
-- followers_count of a person, read as the server
create function pg_temp.fc(n int) returns int language sql stable as $$ select followers_count from public.profiles where id = pg_temp.u(n) $$;
create function pg_temp.follow_notes(p_to int, p_from int) returns int language sql stable as $$
  select count(*)::int from public.notifications where user_id = pg_temp.u(p_to) and from_user = pg_temp.u(p_from) and type = 'follow' $$;

-- people: u1 follower, u2 leader, u3 connected with u2, u4 colleague of u5 (same company), u5 asks for suggestions, u6 newest stranger, u7 bridge
select pg_temp.as_server();
insert into auth.users (id, email) select pg_temp.u(g), 'nf' || g || '@nf30.test' from generate_series(1, 7) g on conflict do nothing;
insert into public.profiles (id, name, company) select pg_temp.u(g), 'NF person ' || g, case when g in (4, 5) then 'NF Pharma' when g = 7 then 'NF Bridge' else 'NF Other ' || g end
  from generate_series(1, 7) g on conflict (id) do nothing;
update public.profiles p set name = 'NF person ' || g, company = case when g in (4, 5) then 'NF Pharma' when g = 7 then 'NF Bridge' else 'NF Other ' || g end
  from generate_series(1, 7) g where p.id = pg_temp.u(g);   -- sign-up may already have made the profiles
update public.profiles set company = '  nf pharma ' where id = pg_temp.u(4);   -- the same company, written differently
update public.profiles set created_at = now() + interval '1 hour' where id = pg_temp.u(6);   -- the newest member

-- ══ S-11 following a person ═══════════════════════════════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 follows u2', $$insert into public.person_followers (person_id) values (pg_temp.u(2))$$);
select pg_temp.ok('S-11 a member follows a person as herself', $$(select user_id from public.person_followers where person_id = pg_temp.u(2)) = pg_temp.u(1)$$);
select pg_temp.no('S-11 …never on behalf of someone else', $$insert into public.person_followers (person_id, user_id) values (pg_temp.u(3), pg_temp.u(2))$$, '42501');
select pg_temp.no('S-11 …never herself', $$insert into public.person_followers (person_id) values (pg_temp.u(1))$$, '23514');
select pg_temp.no('S-11 …and once per person', $$insert into public.person_followers (person_id) values (pg_temp.u(2))$$, '23505');
select pg_temp.step('u1 tries to write its own follower count', $$update public.profiles set followers_count = 99 where id = pg_temp.u(1)$$);
select pg_temp.as_server();
select pg_temp.ok('S-11 the followed person''s followers_count is 1', $$pg_temp.fc(2) = 1$$);
select pg_temp.ok('S-11 the follower count cannot be written from the API', $$pg_temp.fc(1) = 0$$);
select pg_temp.ok('S-11 she gets one "started following you" notice', $$pg_temp.follow_notes(2, 1) = 1$$);
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.ok('S-11 the person followed sees who follows him', $$(select count(*) from public.person_followers where person_id = pg_temp.u(2)) = 1$$);
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.ok('S-11 a third member does not see the follow', $$(select count(*) from public.person_followers) = 0$$);
select pg_temp.step('u3 tries to remove the follow', $$delete from public.person_followers where person_id = pg_temp.u(2)$$);
select pg_temp.as_server();
select pg_temp.ok('S-11 …and cannot remove it', $$(select count(*) from public.person_followers where person_id = pg_temp.u(2)) = 1$$);
select pg_temp.as_anon();
select pg_temp.ok('S-11 anon reads no follows (empty answer)', $$(select count(*) from public.person_followers) = 0$$);
select pg_temp.no('S-11 anon cannot follow', $$insert into public.person_followers (person_id, user_id) values (pg_temp.u(2), pg_temp.u(3))$$, '42501');

-- connecting with someone you follow does not count twice; removing the connection leaves the follow counted
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 asks u2 to connect', $$insert into public.connections (requester, addressee) values (pg_temp.u(1), pg_temp.u(2))$$);
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.step('u2 accepts', $$update public.connections set status = 'accepted' where requester = pg_temp.u(1) and addressee = pg_temp.u(2)$$);
select pg_temp.as_server();
select pg_temp.ok('S-11 connected + following: u2 still has 1 follower (no double count)', $$pg_temp.fc(2) = 1$$);
select pg_temp.ok('S-11 …and u1 gets 1 (the connection)', $$pg_temp.fc(1) = 1$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 unfollows while connected', $$delete from public.person_followers where person_id = pg_temp.u(2)$$);
select pg_temp.as_server();
select pg_temp.ok('S-11 unfollowing a connection keeps the count (the connection counts)', $$pg_temp.fc(2) = 1$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 follows again', $$insert into public.person_followers (person_id) values (pg_temp.u(2))$$);
select pg_temp.step('u1 removes the connection', $$delete from public.connections where requester = pg_temp.u(1) and addressee = pg_temp.u(2)$$);
select pg_temp.as_server();
select pg_temp.ok('S-10 removing the connection: u2 keeps 1 follower (the follow), u1 goes to 0', $$pg_temp.fc(2) = 1 and pg_temp.fc(1) = 0$$);
select pg_temp.ok('S-11 following again sent no second notice', $$pg_temp.follow_notes(2, 1) = 1$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 unfollows', $$delete from public.person_followers where person_id = pg_temp.u(2)$$);
select pg_temp.as_server();
select pg_temp.ok('S-11 unfollowing lowers the count to 0', $$pg_temp.fc(2) = 0$$);
select pg_temp.ok('S-11 the recount in the migration gives the same numbers', $$not exists (select 1 from public.profiles p where p.id in (select pg_temp.u(g) from generate_series(1, 7) g)
  and p.followers_count <> (select count(distinct o) from (select addressee o from public.connections where requester = p.id and status = 'accepted'
     union all select requester from public.connections where addressee = p.id and status = 'accepted' union all select user_id from public.person_followers where person_id = p.id) z))$$);

-- ══ S-04 a declined request stays declined for its sender ══════════════════════════════════════
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.step('u3 asks u1', $$insert into public.connections (requester, addressee) values (pg_temp.u(3), pg_temp.u(1))$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 declines', $$update public.connections set status = 'rejected' where requester = pg_temp.u(3) and addressee = pg_temp.u(1)$$);
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.step('u3 tries to delete the declined request', $$delete from public.connections where requester = pg_temp.u(3) and addressee = pg_temp.u(1)$$);
select pg_temp.no('S-04 …nor ask again at once', $$insert into public.connections (requester, addressee) values (pg_temp.u(3), pg_temp.u(1))$$, '23505');
select pg_temp.as_server();
select pg_temp.ok('S-04 the sender cannot delete the declined request: the declined row is still there, not pending', $$(select status from public.connections where requester = pg_temp.u(3) and addressee = pg_temp.u(1)) = 'rejected'$$);
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.step('u3 asks u5 (pending)', $$insert into public.connections (requester, addressee) values (pg_temp.u(3), pg_temp.u(5))$$);
select pg_temp.step('u3 withdraws it', $$delete from public.connections where requester = pg_temp.u(3) and addressee = pg_temp.u(5)$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 removes the declined row', $$delete from public.connections where requester = pg_temp.u(3) and addressee = pg_temp.u(1)$$);
select pg_temp.as_server();
select pg_temp.ok('S-04 a sender still withdraws a pending request', $$not exists (select 1 from public.connections where requester = pg_temp.u(3) and addressee = pg_temp.u(5))$$);
select pg_temp.ok('S-04 the person who declined can remove the row', $$not exists (select 1 from public.connections where requester = pg_temp.u(3) and addressee = pg_temp.u(1))$$);

-- ══ J-SOCIAL-34 suggestions: mutual, then colleagues, then newest; dismissed never ═══════════════
select pg_temp.as_server();
insert into public.connections (requester, addressee, status) values (pg_temp.u(5), pg_temp.u(7), 'accepted'), (pg_temp.u(7), pg_temp.u(3), 'accepted');
select pg_temp.as_user(pg_temp.u(5));
select pg_temp.step('u5 asks for suggestions', $$insert into ids select 'sug' || s.k, s.id::text from public.suggest_people(50) with ordinality as s(id, name, headline, company, country, verified, avatar_url, location, followers_count, open_to_work, hiring, mutual, k)$$);
select pg_temp.step('u5 mutual of #1', $$insert into ids select 'mutual1', s.mutual::text from public.suggest_people(1) s$$);
select pg_temp.ok('J-34 the mutual connection (u3, via u7) comes first', $$(select v from ids where k = 'sug1') = pg_temp.u(3)::text and (select v from ids where k = 'mutual1') = '1'$$);
select pg_temp.ok('J-34 the colleague (u4, same company written differently) comes second, before the newest member', $$(select v from ids where k = 'sug2') = pg_temp.u(4)::text
  and (select replace(k, 'sug', '')::int from ids where k like 'sug%' and v = pg_temp.u(6)::text) > 2$$);
select pg_temp.ok('J-34 never herself or someone already connected', $$(select count(*) from ids where k like 'sug%') > 2 and not exists (select 1 from ids where k like 'sug%' and v in (pg_temp.u(5)::text, pg_temp.u(7)::text))$$);
select pg_temp.step('u5 dismisses u3', $$insert into public.people_dismissed (person_id) values (pg_temp.u(3))$$);
select pg_temp.ok('J-34 a member dismisses a suggestion as herself', $$(select user_id from public.people_dismissed where person_id = pg_temp.u(3)) = pg_temp.u(5)$$);
select pg_temp.no('J-34 …never for someone else', $$insert into public.people_dismissed (user_id, person_id) values (pg_temp.u(1), pg_temp.u(4))$$, '42501');
select pg_temp.ok('J-34 the dismissed person is no longer suggested', $$not exists (select 1 from public.suggest_people(50) where id = pg_temp.u(3))$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.ok('J-34 others do not see her dismissals', $$(select count(*) from public.people_dismissed) = 0$$);
select pg_temp.ok('J-34 …and still get u3 suggested', $$exists (select 1 from public.suggest_people(50) where id = pg_temp.u(3))$$);
select pg_temp.as_anon();
select pg_temp.no('J-34 anon cannot ask for suggestions', $$select * from public.suggest_people(5)$$, '42501');
select pg_temp.as_server();
select pg_temp.ok('grants: the follow counter is not callable from the API', $$not has_function_privilege('anon', 'public.person_followers_count()', 'execute') and not has_function_privilege('authenticated', 'public.person_followers_count()', 'execute')$$);

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
