-- Private phone numbers, names a person can tell apart, Drugbox notices kept as data (0036, S-03, S-20, A-03).
-- Runs as the real API roles with a JWT, in one transaction that is rolled back; test data carries the "PN " marker.
-- Run on a fresh database (stub + migrations): psql -f supabase/tests/privacy_names.rls.sql
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
create function pg_temp.u(n int) returns uuid language sql immutable as $$ select ('f3600000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid $$;

-- people: u1 a member with a phone, u2 another member, u3 a Drugbox moderator, u4 the author of a reported post
select pg_temp.as_server();
insert into auth.users (id, email) select pg_temp.u(g), 'pn' || g || '@pn36.test' from generate_series(1, 4) g on conflict do nothing;
update public.profiles set name = 'PN person ' || right(id::text, 1) where id in (pg_temp.u(1), pg_temp.u(2), pg_temp.u(3), pg_temp.u(4));
update public.profiles set phone = '+20 100 555 1234' where id = pg_temp.u(1);
update public.profiles set role = 'moderator' where id = pg_temp.u(3);

-- ══ 1. phone stays with its owner ══════════════════════════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.no('phone: another member cannot read it (select name, phone)', $$select name, phone from public.profiles where id = pg_temp.u(1)$$, '42501');
select pg_temp.no('phone: another member cannot list who has one (filter on phone)', $$select id from public.profiles where phone is not null$$, '42501');
select pg_temp.no('phone: select * is refused for members (it would include phone)', $$select * from public.profiles limit 1$$, '42501');
select pg_temp.ok('phone: the public columns still read for everyone signed in', $$(select name from public.profiles where id = pg_temp.u(1)) = 'PN person 1'$$);
select pg_temp.ok('phone: my_profile() gives another member only their own row', $$(select count(*) from public.my_profile() where id = pg_temp.u(1)) = 0 and (select count(*) from public.my_profile()) = 1$$);
select pg_temp.ok('phone: open_candidates() never carries a phone', $$not exists (select 1 from public.open_candidates(100) where phone is not null)$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.ok('phone: the owner reads her phone through my_profile()', $$(select phone from public.my_profile()) = '+20 100 555 1234'$$);
select pg_temp.step('phone: the owner changes it (Edit Profile, no phone in the answer)', $$update public.profiles set phone = '+20 100 555 9999' where id = pg_temp.u(1)$$);
select pg_temp.ok('phone: the change is kept', $$(select phone from public.my_profile()) = '+20 100 555 9999'$$);
select pg_temp.as_anon();
select pg_temp.no('phone: anon cannot read it', $$select phone from public.profiles$$, '42501');
select pg_temp.no('phone: anon cannot call my_profile()', $$select * from public.my_profile()$$, '42501');

-- ══ 2. names a person can tell apart ══════════════════════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.step('u2 renames herself with an invisible character and doubled spaces', $$update public.profiles set name = E'PN  Zeina​ X⁠' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: invisible characters are removed and spaces collapse', $$(select name from public.profiles where id = pg_temp.u(2)) = 'PN Zeina X'$$);
select pg_temp.step('u2 calls herself "PN Hala X · Pharco X"', $$update public.profiles set name = 'PN Hala X · Pharco X' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: the picker separator cannot be part of a name', $$(select name from public.profiles where id = pg_temp.u(2)) = 'PN Hala X - Pharco X'$$);
select pg_temp.step('u2 tries other dot-like separators', $$update public.profiles set name = E'PN Hala X•Pharco ∙ X' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: every dot-like separator becomes "-"', $$(select name from public.profiles where id = pg_temp.u(2)) = 'PN Hala X - Pharco - X'$$);
-- the look-alikes the p1b verifier got through 0036 (0037: one rule generated from the Unicode properties — supabase/tests/name_rule.sql)
select pg_temp.step('u2 calls herself "PN Hala X ꞏ Pharco X" (U+A78F LATIN LETTER SINOLOGICAL DOT)', $$update public.profiles set name = U&'PN Hala X \A78F Pharco X' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: U+A78F is the picker separator too', $$(select name from public.profiles where id = pg_temp.u(2)) = 'PN Hala X - Pharco X'$$);
select pg_temp.step('u2 renames herself "PN Zeina X" + U+1D173 (a default-ignorable character)', $$update public.profiles set name = U&'PN Zeina X\+01D173' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: U+1D173 is removed', $$(select name from public.profiles where id = pg_temp.u(2)) = 'PN Zeina X'$$);
select pg_temp.step('u2 tries a name of only invisible characters', $$update public.profiles set name = E'​‌ ' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: an empty name becomes "Member"', $$(select name from public.profiles where id = pg_temp.u(2)) = 'Member'$$);
select pg_temp.as_server();
insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(5), 'pn5@pn36.test', jsonb_build_object('name', E'PN Twin​')) on conflict do nothing;
select pg_temp.ok('names: sign-up cleans the name too', $$(select name from public.profiles where id = pg_temp.u(5)) = 'PN Twin'$$);
insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(6), 'pn6@pn36.test', jsonb_build_object('name', U&'PN Hala X \2E33 Pharco X')) on conflict do nothing;
select pg_temp.ok('names: sign-up maps U+2E33 RAISED DOT to the separator', $$(select name from public.profiles where id = pg_temp.u(6)) = 'PN Hala X - Pharco X'$$);
select pg_temp.ok('names: an Arabic name keeps its letters', $$public.clean_person_name('د. نرمين  أبو زيد') = 'د. نرمين أبو زيد'$$);

-- ══ 3. Drugbox notices keep their data, the app writes the sentence ═════════════════════════════
select pg_temp.as_server();
insert into public.posts (user_id, body) values (pg_temp.u(4), 'PN fake EDA approval claim') returning id \gset
insert into ids values ('post', :'id');
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.step('u2 reports the post as misleading', $$insert into public.post_reports (post_id, reporter, reason, note) values (pg_temp.id('post'), pg_temp.u(2), 'misleading', 'PN fake')$$);
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.ok('decide: the moderator removes the post', $$public.post_report_decide((select id from public.post_reports where post_id = pg_temp.id('post')), true, 'PN see EDA site') = 1$$);
select pg_temp.as_server();
select pg_temp.ok('post_removed: the author gets the data, no English sentence', $$(select message is null and data->>'excerpt' = 'PN fake EDA approval claim' and data->>'reason' = 'misleading' and data->>'note' = 'PN see EDA site'
  from public.notifications where user_id = pg_temp.u(4) and type = 'post_removed')$$);
select pg_temp.ok('report_closed: the reporter gets the outcome, no English sentence', $$(select message is null and data->>'outcome' = 'removed' from public.notifications where user_id = pg_temp.u(2) and type = 'report_closed')$$);
select pg_temp.ok('decide: the post is gone', $$not exists (select 1 from public.posts where id = pg_temp.id('post'))$$);

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
