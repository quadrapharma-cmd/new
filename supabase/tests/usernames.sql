-- @username (S-03, the owner's decision of 25 Oct — Facebook's rule: names may be alike, every member has a unique username; 0070_usernames).
-- 1. database = app: the username every name of tests/names/username_names.txt gives (username_base), and the key, the reason and the
--    sentence of every username of tests/names/username_strings.txt (username_key, username_problem, username_message) and the numbered
--    candidates — the app's side from node tools/names/username_rule.mjs --expect (the generated code of web/src/username.js and the
--    adapter, checked against the rule's definition first).
-- 2. made at sign-up: identical names numbered (base, base.2 …), Arabic and Latin spellings of one name share it, titles skipped, a short
--    name numbered at once, a reserved word left out, every profile has a username and the key the database computes; 300+ real names.
-- 3. written ONLY through set_username(): a member's UPDATE of username / username_key is refused; the reasons (format, reserved, taken —
--    a look-alike of a taken one too —, held for 30 days, 5 changes a day), a username given up is held for its member and can be taken
--    back, an expired hold frees it; username_available() says the same and is limited to 60 checks a minute; anon can call neither.
-- 4. the new tables: RLS on, a member reads only their own rows and writes none; my_conversations() returns the username; columns grants.
-- Runs as the real API roles with a JWT, in one transaction that is rolled back. Run from the repository root on a fresh database
-- (stub + migrations): psql -f supabase/tests/usernames.sql
\set QUIET on
\set ON_ERROR_ROLLBACK on
set client_min_messages = warning;
\o /dev/null
begin;
create temp table r (n serial, name text, ok boolean, err text); grant all on r to authenticated, anon, service_role; grant all on r_n_seq to authenticated, anon, service_role;
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
create function pg_temp.no(p_name text, q text, st text, msg text default null) returns void language plpgsql as $$ begin
  execute q; raise exception 'the statement was allowed' using errcode = 'DB001';
  exception when others then insert into r(name, ok, err) values (p_name, sqlstate = st and (msg is null or sqlerrm ~ msg), case when sqlstate <> st or (msg is not null and sqlerrm !~ msg) then sqlstate || ': ' || sqlerrm end); end $$;
create function pg_temp.yes(p_name text, q text) returns void language plpgsql as $$ begin execute q; insert into r(name, ok) values (p_name, true);
  exception when others then insert into r(name, ok, err) values (p_name, false, sqlstate || ': ' || sqlerrm); end $$;
create function pg_temp.u(n int) returns uuid language sql immutable as $$ select ('f3700000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid $$;
create function pg_temp.signup(n int, name text) returns text language plpgsql as $$ begin
  insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(n), 'un' || n || '@un70.test', jsonb_build_object('name', name));
  return (select username from public.profiles where id = pg_temp.u(n)); end $$;
grant execute on function pg_temp.signup(int, text) to authenticated;

-- ══ 1. database = app ══════════════════════════════════════════════════════════════════════════
create temp table app (kind text, s text, a text, b text, c text);
\set ON_ERROR_STOP on
\copy app from program 'node tools/names/username_rule.mjs --expect'
\set ON_ERROR_STOP off
select pg_temp.ok('the app''s rule was loaded: 300+ real names, the usernames as typed, the candidates', $q$(select count(*) filter (where kind = 'n') >= 300 and count(*) filter (where kind = 'u') >= 80 and count(*) filter (where kind = 'c') = 30 from app)$q$);
insert into r(name, ok, err) select 'database = app: the username a name gives (username_base), for every name', count(*) = 0,
       count(*) || ' differ, e.g. ' || string_agg(format('%s: db=%s app=%s', s, public.username_base(s), a), '; ') filter (where rn <= 6)
  from (select *, row_number() over () rn from app where kind = 'n' and public.username_base(s) is distinct from a) d;
insert into r(name, ok, err) select 'database = app: the key, the reason and the sentence, for every username', count(*) = 0,
       count(*) || ' differ, e.g. ' || string_agg(format('%s: db=%s/%s app=%s/%s', s, public.username_key(s), public.username_problem(s), a, b), '; ') filter (where rn <= 6)
  from (select *, row_number() over () rn from app where kind = 'u' and (public.username_key(s) is distinct from a or public.username_problem(s) is distinct from b
          or (b <> '' and public.username_message(s, b) is distinct from c))) d;
insert into r(name, ok, err) select 'database = app: the numbered candidates', count(*) = 0, string_agg(format('%s %s: db=%s app=%s', s, b, public.username_candidate(s, b::int), a), '; ')
  from app where kind = 'c' and public.username_candidate(s, b::int) is distinct from a;
select pg_temp.ok('every name gives a username or a base the database numbers (no reserved word, a letter, a-z 0-9 .)', $q$(select bool_and(a ~ '^[a-z0-9.]+$' and a ~ '[a-z]' and public.username_problem(a) in ('', 'short')) from app where kind = 'n')$q$);
select pg_temp.ok('the empty username: refused, "Choose a username"', $q$public.username_problem('') = 'empty' and public.username_message('', 'empty') = 'Choose a username'$q$);
select pg_temp.ok('look-alikes are one key: ahmed.ali = AhmedAli = ahrned.ali = ahmed.a1i = ahmecl.ali; vvael = wael; 0mar = omar', $q$
  (select count(distinct public.username_key(x)) = 1 from unnest(array['ahmed.ali', 'AhmedAli', 'ahrned.ali', 'ahmed.a1i', 'ahmecl.ali', 'ahmed.aIi']) x)
  and public.username_key('vvael') = public.username_key('wael') and public.username_key('0mar') = public.username_key('omar')$q$);
select pg_temp.ok('different usernames stay different keys: ahmed.ali / ahmed.aly / ahmed.ali2', $q$(select count(distinct public.username_key(x)) = 3 from unnest(array['ahmed.ali', 'ahmed.aly', 'ahmed.ali2']) x)$q$);

-- ══ 2. made at sign-up ═════════════════════════════════════════════════════════════════════════
select pg_temp.as_server();
create temp table su (n int, name text, username text);
insert into su select g, n, pg_temp.signup(g, n) from (values (1, 'Ahmed Ali'), (2, 'أحمد علي'), (3, 'Dr. Ahmed Ali'), (4, 'Ali'), (5, 'Ali'), (6, 'Om'), (7, 'Dr. Maha Moderator'),
  (8, 'Drugbox Finance'), (9, 'محمد أحمد'), (10, 'عبد الرحمن'), (11, 'José Ali'), (12, 'Dr. Haytham Dweedar'), (13, 'بىىىام علي'), (14, 'Mohamed Ahmed Ali Hassan')) v(g, n);
select pg_temp.ok('identical and same-sounding names are numbered: ahmed.ali, ahmed.ali.2, ahmed.ali.3 (Arabic, title skipped)', $q$
  (select string_agg(username, ',' order by n) from su where n in (1, 2, 3)) = 'ahmed.ali,ahmed.ali.2,ahmed.ali.3'$q$);
select pg_temp.ok('a short name is numbered at once: ali.1, ali.2; «Om» → om.01', $q$(select string_agg(username, ',' order by n) from su where n in (4, 5, 6)) = 'ali.1,ali.2,om.01'$q$);
select pg_temp.ok('a reserved word is left out: «Dr. Maha Moderator» → maha.1, «Drugbox Finance» → finance', $q$(select string_agg(username, ',' order by n) from su where n in (7, 8)) = 'maha.1,finance'$q$);
select pg_temp.ok('Arabic as Egyptians write it, accents without: mohamed.ahmed, abdelrahman, jose.ali, haytham.dweedar; first and last word', $q$
  (select string_agg(username, ',' order by n) from su where n in (9, 10, 11, 12, 14)) = 'mohamed.ahmed,abdelrahman,jose.ali,haytham.dweedar,mohamed.hassan'$q$);
select pg_temp.ok('a name that looks like another is a name like any other (the eighth version refused «بىىىام»)', $q$(select username is not null from su where n = 13)$q$);
select pg_temp.ok('every profile has a username, a valid one, and the key the database computes', $q$
  not exists (select 1 from public.profiles where username is null or username_key is distinct from public.username_key(username) or public.username_problem(username) <> '')$q$);
-- 300+ real names at once, many of them the same: every username different, every key different
insert into auth.users (id, email, raw_user_meta_data) select pg_temp.u((1000 * k + a.rn)::int), 'bulk' || (1000 * k + a.rn) || '@un70.test', jsonb_build_object('name', a.s)
  from (select s, row_number() over (order by ctid) rn from app where kind = 'n') a, generate_series(2, 3) k order by k, a.rn;
select pg_temp.ok('the 300+ real names signed up twice: every member has a username, all keys distinct', $q$
  (select count(*) >= 600 and count(distinct username_key) = count(*) and bool_and(username is not null) from public.profiles where id::text like 'f3700000-%')$q$);
select pg_temp.ok('the second of each name is numbered (base.2 …)', $q$(select count(*) >= 300 and bool_and(username ~ '[.][0-9]+$') from public.profiles
  where id in (select pg_temp.u(3000 + g) from generate_series(1, 999) g))$q$);
-- a bulk import defers the per-row trigger in its session and gives every new member a username at once (username_assign_missing:
-- set-based, numbered among the members of the same username, the oldest first) — tools/scale/seed_100k.sql
set drugbox.defer_usernames = 'on';
insert into auth.users (id, email, raw_user_meta_data) select pg_temp.u(5000 + g), 'defer' || g || '@un70.test', jsonb_build_object('name', (array['Ahmed Ali', 'أحمد علي', 'Mona Hassan', 'Ali'])[1 + g % 4])
  from generate_series(1, 40) g;
select pg_temp.ok('deferred: the bulk-imported members have no username yet', $q$(select count(*) = 40 and bool_and(username is null) from public.profiles where id in (select pg_temp.u(5000 + g) from generate_series(1, 40) g))$q$);
reset drugbox.defer_usernames;
select pg_temp.ok('username_assign_missing gives the 40 members a username', $q$public.username_assign_missing() = 40$q$);
select pg_temp.ok('…each valid, with its key, all keys distinct — numbered after the members who had the name''s username', $q$
  (select count(*) = 40 and count(distinct username_key) = 40 and bool_and(username is not null and username_key = public.username_key(username) and public.username_problem(username) = '')
         from public.profiles where id in (select pg_temp.u(5000 + g) from generate_series(1, 40) g))
  and (select count(distinct username_key) = count(*) from public.profiles)$q$);

-- ══ 3. written only through set_username() ═════════════════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.no('a member cannot UPDATE their username directly (Edit Profile calls set_username)', $q$update public.profiles set username = 'my.own.pick' where id = pg_temp.u(1)$q$, '42501');
select pg_temp.no('a member cannot UPDATE their username_key', $q$update public.profiles set username_key = 'x' where id = pg_temp.u(1)$q$, '42501');
select pg_temp.yes('…and other columns still save (headline)', $q$update public.profiles set headline = 'Pharmacist' where id = pg_temp.u(1)$q$);
select pg_temp.ok('set_username: Ahmed.Ali.Pharma typed with capitals and @ → ahmed.ali.pharma', $q$public.set_username('@Ahmed.Ali.Pharma') = 'ahmed.ali.pharma'$q$);
select pg_temp.ok('…stored with its key; the old one is held for the member for 30 days', $q$
  (select username = 'ahmed.ali.pharma' and username_key = public.username_key('ahmed.ali.pharma') from public.profiles where id = pg_temp.u(1))
  and (select count(*) = 1 from public.username_holds where username = 'ahmed.ali' and profile_id = pg_temp.u(1) and held_until > now() + interval '29 days')$q$);
select pg_temp.no('refused: a character that is not a-z 0-9 .', $q$select public.set_username('ahmed_ali')$q$, '23514', 'remove');
select pg_temp.no('refused: too short', $q$select public.set_username('ali')$q$, '23514', 'at least 5');
select pg_temp.no('refused: a reserved word (drugbox.support)', $q$select public.set_username('drugbox.support')$q$, '23514', 'kept for Drugbox');
select pg_temp.no('refused: a look-alike of a taken username (ahrned.ali.2 = ahmed.ali.2), said as a look-alike (v-real1)', $q$select public.set_username('ahrned.ali.2')$q$, 'P0001', 'reads like a username a member has');
select pg_temp.no('refused: the same username without its dots is «taken» (ahmedali.2 = ahmed.ali.2)', $q$select public.set_username('ahmedali.2')$q$, 'P0001', 'is taken');
-- s03-user2 (v-user1): the reserved words read on the KEY — the look-alike digits 0 / 1 and words joined without a dot are Drugbox's too
select pg_temp.no('refused: ' || x, format('select public.set_username(%L)', x), '23514', 'kept for Drugbox')
  from unnest(array['adm1n.eg', 'supp0rt.eg', 'm0derator.eg', '0fficial.eg', 'officia1.eg', 'moderat0r.1', 'supp0rt2', 'supportteam', 'adminteam', 'theadmin',
                    'paymentseg', 'officialaccount', 'admins', 'officials', 'ad.min.eg', 'staff2', 'he1p.desk']) x;
select pg_temp.ok('allowed: names that hold a reserved word inside another (stafford.ali, hamad.mino, steam.eg, joeroot)', $q$
  public.username_problem('stafford.ali') = '' and public.username_problem('hamad.mino') = '' and public.username_problem('steam.eg') = '' and public.username_problem('joeroot') = ''$q$);
select pg_temp.as_user(pg_temp.u(4));
select pg_temp.no('refused: a username another member gave up (held for them for 30 days)', $q$select public.set_username('ahmed.ali')$q$, 'P0001', 'kept for them for 30 days');
select pg_temp.ok('username_available says the same: held / taken / reserved / free', $q$
  public.username_available('ahmed.ali')->>'reason' = 'held' and public.username_available('Ahmed.Ali.2')->>'reason' = 'taken'
  and public.username_available('ahmed.a1i.2')->>'reason' = 'alike'
  and public.username_available('admin2')->>'reason' = 'reserved' and (public.username_available('ali.free.now')->>'ok')::boolean$q$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.ok('the member who gave it up can take it back…', $q$public.set_username('ahmed.ali') = 'ahmed.ali'$q$);
select pg_temp.ok('…and the hold goes', $q$not exists (select 1 from public.username_holds where username_key = public.username_key('ahmed.ali'))$q$);
select pg_temp.ok('changing only dots or capitals is allowed…', $q$public.set_username('ahmedali') = 'ahmedali'$q$);
select pg_temp.ok('…keeps the key and holds nothing', $q$not exists (select 1 from public.username_holds where profile_id = pg_temp.u(1) and username_key = public.username_key('ahmed.ali'))$q$);
select pg_temp.ok('three more changes are allowed today (5 in all)…', $q$public.set_username('ahmed.one') = 'ahmed.one' and public.set_username('ahmed.two') = 'ahmed.two'$q$);
select pg_temp.no('…the sixth in a day is refused', $q$select public.set_username('ahmed.three')$q$, 'P0001', 'too often');
select pg_temp.ok('…and username_available says so before Save (v-real1), while the member''s own username stays «available»', $q$
  public.username_available('ahmed.three')->>'reason' = 'rate' and (public.username_available('ahmed.two')->>'ok')::boolean$q$);
select pg_temp.as_server();
update public.username_holds set held_until = now() - interval '1 second' where profile_id = pg_temp.u(1);
select pg_temp.as_user(pg_temp.u(5));
select pg_temp.ok('an expired hold frees the username for others', $q$public.set_username('ahmed.one') = 'ahmed.one'$q$);
select pg_temp.as_user(pg_temp.u(6));
select pg_temp.ok('username_available: 60 checks a minute, then «wait a minute»', $q$
  (select count(*) from generate_series(1, 60) g where (public.username_available('free.name.' || g)->>'ok')::boolean) = 60
  and public.username_available('free.name.61')->>'reason' = 'slow'$q$);
select pg_temp.as_anon();
select pg_temp.no('anon cannot call set_username', $q$select public.set_username('anon.name')$q$, '42501');
select pg_temp.no('anon cannot call username_available', $q$select public.username_available('anon.name')$q$, '42501');
select pg_temp.as_user(pg_temp.u(9));
select pg_temp.ok('another member reads usernames by column (select username from profiles)', $q$(select count(*) > 0 from public.profiles where username is not null and id <> pg_temp.u(9))$q$);
select pg_temp.no('a member cannot call username_assign (server only)', $q$select public.username_assign(pg_temp.u(9), 'x.y.z.w')$q$, '42501');
select pg_temp.no('a member cannot call username_assign_missing (server only)', $q$select public.username_assign_missing()$q$, '42501');

-- ══ 4. tables, policies, conversations ═════════════════════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.ok('a member reads only their own holds and changes', $q$(select count(*) = 0 from public.username_holds where profile_id <> pg_temp.u(1))
  and (select count(*) >= 5 from public.username_changes where profile_id = pg_temp.u(1)) and (select count(*) = 0 from public.username_changes where profile_id <> pg_temp.u(1))$q$);
select pg_temp.no('a member cannot write a hold', $q$insert into public.username_holds values ('zzzzz', 'zzzzz', pg_temp.u(1), now() + interval '1 day')$q$, '42501');
select pg_temp.no('a member cannot write a change', $q$insert into public.username_changes (profile_id, new_username) values (pg_temp.u(1), 'x')$q$, '42501');
select pg_temp.no('a member cannot reset the check counter', $q$update public.username_checks set n = 0$q$, '42501');
select pg_temp.as_server();
insert into public.messages (sender_id, receiver_id, body) values (pg_temp.u(2), pg_temp.u(1), 'UN hello');
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.ok('my_conversations returns the partner''s username', $q$(select username = 'ahmed.ali.2' from public.my_conversations(10) where partner = pg_temp.u(2))$q$);
select pg_temp.as_server();
select pg_temp.ok('RLS on every new table, each with a policy', $q$(select bool_and(c.relrowsecurity and exists (select 1 from pg_policy p where p.polrelid = c.oid))
  from pg_class c where c.oid in ('public.username_holds'::regclass, 'public.username_changes'::regclass, 'public.username_checks'::regclass))$q$);
select pg_temp.ok('members read username / username_key by column; no UPDATE of them gets through (the guard)', $q$
  has_column_privilege('authenticated', 'public.profiles', 'username', 'select') and has_column_privilege('anon', 'public.profiles', 'username', 'select')
  and has_column_privilege('authenticated', 'public.profiles', 'username_key', 'select')$q$);
select pg_temp.ok('set_username / username_available / username_assign are security definer; assign is server-only', $q$
  (select bool_and(prosecdef) from pg_proc where proname in ('set_username', 'username_available', 'username_assign'))
  and not has_function_privilege('authenticated', 'public.username_assign(uuid, text)', 'execute') and not has_function_privilege('anon', 'public.set_username(text)', 'execute')$q$);

\o
select format('%s %s%s', case when ok then 'ok  ' else 'FAIL' end, name, coalesce(' — ' || err, '')) from r order by n;
select format('TOTAL %s / %s', count(*) filter (where ok), count(*)) from r;
rollback;
