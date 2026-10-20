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
create function pg_temp.err_of(q text) returns text language plpgsql as $$ begin execute q; return null; exception when others then return sqlerrm; end $$;
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

-- ══ 2. names: an allowlist and a skeleton (0038 — every string the verifiers used is in supabase/tests/name_rule.sql) ══════════
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.step('u2 renames herself with an invisible character and doubled spaces', $$update public.profiles set name = E'PN  Zeina​ X⁠' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: invisible characters are removed and spaces collapse', $$(select name from public.profiles where id = pg_temp.u(2)) = 'PN Zeina X'$$);
select pg_temp.ok('names: the key is the skeleton, the name is not flagged', $$(select name_key = public.person_name_key('PN Zeina X') and not name_needs_fix from public.profiles where id = pg_temp.u(2))$$);
select pg_temp.no('names: the picker separator cannot be part of a name ("PN Hala X · Pharco X")', $$update public.profiles set name = 'PN Hala X · Pharco X' where id = pg_temp.u(2)$$, '23514');
select pg_temp.no('names: U+A78F LATIN LETTER SINOLOGICAL DOT is refused', $$update public.profiles set name = U&'PN Hala X \A78F Pharco X' where id = pg_temp.u(2)$$, '23514');
select pg_temp.no('names: U+11174 (draws a dot) is refused', $$update public.profiles set name = U&'PN Hala X \+011174 Pharco X' where id = pg_temp.u(2)$$, '23514');
select pg_temp.no('names: U+1F797 (draws a dot) is refused', $$update public.profiles set name = U&'PN Hala X \+01F797 Pharco X' where id = pg_temp.u(2)$$, '23514');
select pg_temp.no('names: U+111D0 (a digit that draws a dot) is refused', $$update public.profiles set name = U&'PN Hala X \+0111D0 Pharco X' where id = pg_temp.u(2)$$, '23514');
select pg_temp.no('names: U+FFFC (draws nothing) is refused', $$update public.profiles set name = U&'PN Zeina X\FFFC' where id = pg_temp.u(2)$$, '23514');
select pg_temp.no('names: ∘ and ▪ are refused', $$update public.profiles set name = 'PN Hala X ∘ Pharco ▪ X' where id = pg_temp.u(2)$$, '23514');
select pg_temp.no('names: a Cyrillic letter inside a Latin word is refused ("PN Rаna")', $$update public.profiles set name = U&'PN R\0430na X' where id = pg_temp.u(2)$$, '23514');
select pg_temp.no('names: digits are refused', $$update public.profiles set name = 'PN person 2' where id = pg_temp.u(2)$$, '23514');
select pg_temp.no('names: 0037''s separator " - " (a word without a letter) is refused', $$update public.profiles set name = 'PN Hala X - Pharco X' where id = pg_temp.u(2)$$, '23514');
select pg_temp.ok('names: a refused name leaves the old one', $$(select name from public.profiles where id = pg_temp.u(2)) = 'PN Zeina X'$$);
select pg_temp.ok('names: the refusal says why, in the app''s words', $$(select pg_temp.err_of($q$update public.profiles set name = 'PN person 2' where id = pg_temp.u(2)$q$)) = 'A name cannot contain numbers'$$);
select pg_temp.ok('names: and names the character', $$(select pg_temp.err_of($q$update public.profiles set name = U&'PN Zeina X\FFFC' where id = pg_temp.u(2)$q$)) like '%remove “￼” (U+FFFC)'$$);
select pg_temp.step('u2 cannot forge her key or flag', $$update public.profiles set name_key = 'pn hala x', name_needs_fix = true where id = pg_temp.u(2)$$);
select pg_temp.ok('names: key and flag are the database''s', $$(select name_key = public.person_name_key('PN Zeina X') and not name_needs_fix from public.profiles where id = pg_temp.u(2))$$);
select pg_temp.step('real names are accepted (Arabic with harakat, accents, apostrophes, brackets)', $$update public.profiles set name = 'د. نرمين أبو زيدٍ' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: an Arabic name with harakat is kept as written', $$(select name from public.profiles where id = pg_temp.u(2)) = 'د. نرمين أبو زيدٍ'$$);
select pg_temp.step('…and "Al-Hassan (Pharm.D.)", "O’Brien"', $$update public.profiles set name = 'PN Al-Hassan O’Brien (Pharm.D.)' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: brackets, dots, hyphens and apostrophes are kept', $$(select name from public.profiles where id = pg_temp.u(2)) = 'PN Al-Hassan O’Brien (Pharm.D.)'$$);
select pg_temp.step('u2 tries a name of only invisible characters', $$update public.profiles set name = E'​‌ ' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: an empty name becomes "Member"', $$(select name from public.profiles where id = pg_temp.u(2)) = 'Member'$$);
-- a server write (SQL, service role) of a name that breaks the rule is kept and flagged; an edit that keeps it keeps the flag
select pg_temp.as_server();
update public.profiles set name = 'PN person 1' where id = pg_temp.u(1);
select pg_temp.ok('names: a server write of a name with a digit is kept and flagged', $$(select name = 'PN person 1' and name_needs_fix from public.profiles where id = pg_temp.u(1))$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 (flagged) saves her profile with the same name', $$update public.profiles set name = 'PN person 1', headline = 'QA' where id = pg_temp.u(1)$$);
select pg_temp.ok('names: an edit that keeps a flagged name is saved and the flag stays', $$(select headline = 'QA' and name_needs_fix from public.profiles where id = pg_temp.u(1))$$);
select pg_temp.no('names: …but she cannot change it to another name that breaks the rule', $$update public.profiles set name = 'PN person 11' where id = pg_temp.u(1)$$, '23514');
select pg_temp.step('u1 fixes her name', $$update public.profiles set name = 'PN Person One' where id = pg_temp.u(1)$$);
select pg_temp.ok('names: a fixed name clears the flag', $$(select not name_needs_fix from public.profiles where id = pg_temp.u(1))$$);
select pg_temp.ok('names: every member reads key and flag, never the phone', $$has_column_privilege('authenticated', 'public.profiles', 'name_key', 'SELECT') and has_column_privilege('authenticated', 'public.profiles', 'name_needs_fix', 'SELECT')
  and not has_column_privilege('authenticated', 'public.profiles', 'phone', 'SELECT')$$);
-- sign-up (handle_new_user runs for every caller): the name typed must follow the rule
select pg_temp.as_server();
insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(5), 'pn5@pn36.test', jsonb_build_object('name', E'PN Twin​')) on conflict do nothing;
select pg_temp.ok('sign-up: an invisible character is removed', $$(select name from public.profiles where id = pg_temp.u(5)) = 'PN Twin'$$);
select pg_temp.no('sign-up: U+2E33 RAISED DOT is refused (nothing is created)', $$insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(6), 'pn6@pn36.test', jsonb_build_object('name', U&'PN Hala X \2E33 Pharco X'))$$, '23514');
select pg_temp.ok('sign-up: …no account and no profile', $$not exists (select 1 from auth.users where id = pg_temp.u(6)) and not exists (select 1 from public.profiles where id = pg_temp.u(6))$$);
select pg_temp.no('sign-up: a Cyrillic look-alike of a Latin name is refused', $$insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(6), 'pn6@pn36.test', jsonb_build_object('name', U&'PN R\0430na'))$$, '23514');
insert into auth.users (id, email) values (pg_temp.u(7), 'pn.seven7@pn36.test') on conflict do nothing;
select pg_temp.ok('sign-up: no name → the e-mail''s letters ("pn seven")', $$(select name = 'pn seven' and not name_needs_fix from public.profiles where id = pg_temp.u(7))$$);
insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(8), 'pn8@pn36.test', jsonb_build_object('name', 'Мария Иванова')) on conflict do nothing;
select pg_temp.ok('sign-up: a whole-Cyrillic name is accepted', $$(select name = 'Мария Иванова' and not name_needs_fix from public.profiles where id = pg_temp.u(8))$$);
-- 0039: the browser cannot set the key or the flag by keeping the name either — both are computed again from the rule
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.step('u2 sends her own name with a forged key', $$update public.profiles set name = 'Member', name_key = 'pn hala x' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: a forged key with the same name is replaced by the real one', $$(select name_key = public.person_name_key('Member') and not name_needs_fix from public.profiles where id = pg_temp.u(2))$$);
-- 0039: what 0038 refused and real people write; and the messages name what was typed
select pg_temp.step('a title written the Egyptian way, "د/ …"', $$update public.profiles set name = 'د/ هيثم دويدار' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: "د/ هيثم دويدار" is kept as written', $$(select name = 'د/ هيثم دويدار' and not name_needs_fix from public.profiles where id = pg_temp.u(2))$$);
select pg_temp.step('a Latin title on a Cyrillic name, a pasted non-breaking hyphen and an apostrophe', $$update public.profiles set name = U&'Dr. \041C\0430\0440\0438\044F Anne\2011Marie O''Brien' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: the hyphen look-alike is stored as "-" and the apostrophe as ’', $$(select name = 'Dr. Мария Anne-Marie O’Brien' and not name_needs_fix from public.profiles where id = pg_temp.u(2))$$);
select pg_temp.no('names: a Cyrillic word that reads as Latin next to a Latin title is refused ("Dr. Ѕаӏіһ")', $$update public.profiles set name = U&'Dr. \0405\0430\04CF\0456\04BB' where id = pg_temp.u(2)$$, '23514');
select pg_temp.no('names: the same mark twice on one letter is refused', $$update public.profiles set name = U&'PN Hale\0301\0301' where id = pg_temp.u(2)$$, '23514');
select pg_temp.ok('names: the refusal names the character typed (U+FE69, not the "$" it becomes)', $$(select pg_temp.err_of($q$update public.profiles set name = U&'PN Ahmed \FE69x' where id = pg_temp.u(2)$q$)) like '%remove “﹩” (U+FE69)'$$);
select pg_temp.ok('names: …the word that is only punctuation', $$(select pg_temp.err_of($q$update public.profiles set name = 'د . أحمد' where id = pg_temp.u(2)$q$)) = '“.” is not a word — join it to the word next to it (remove the space)'$$);
select pg_temp.ok('names: …and the alphabets accepted', $$(select pg_temp.err_of($q$update public.profiles set name = '张伟' where id = pg_temp.u(2)$q$)) like 'Write a name in Latin, Arabic, Greek or Cyrillic letters — “张” (U+5F20)%'$$);
-- 0039: a conversation says how many other members share the partner's skeleton — even members this browser never loaded
select pg_temp.as_server();
insert into auth.users (id, email, raw_user_meta_data) select pg_temp.u(g), 'pn' || g || '@pn36.test', jsonb_build_object('name', 'PN Famous Person') from generate_series(12, 13) g on conflict do nothing;
update public.profiles set name = 'PN F' || chr(1072) || 'mous Person' where id = pg_temp.u(13);   -- a server write: kept, flagged, same skeleton
insert into public.messages (sender_id, receiver_id, body) values (pg_temp.u(13), pg_temp.u(4), 'PN hello, it is me');
select pg_temp.as_user(pg_temp.u(4));
select pg_temp.ok('my_conversations: name_twins counts the other members with the partner''s skeleton', $$(select name_twins = 1 and name_key = public.person_name_key('PN Famous Person') and name_needs_fix from public.my_conversations(30) where partner = pg_temp.u(13))$$);
select pg_temp.as_user(pg_temp.u(12));
select pg_temp.ok('my_conversations: a member sees no conversation she is not in', $$not exists (select 1 from public.my_conversations(30) where partner = pg_temp.u(13))$$);
select pg_temp.as_server();
-- existing names (0038's own update, then 0039's, re-applied here): invisible characters and U+FFFC go; a name the new rule allows
-- once normalised is stored normalised and not flagged; any other name is kept and flagged
insert into auth.users (id, email) select pg_temp.u(g), 'pn' || g || '@pn36.test' from generate_series(9, 11) g on conflict do nothing;
set session_replication_role = replica;   -- rows as 0037 left them (no name trigger)
update public.profiles set name = U&'PN Zeina Old\FFFC', name_key = null, name_needs_fix = false where id = pg_temp.u(7);
update public.profiles set name = 'PN Hala Old - Pharco Old', name_key = null, name_needs_fix = false where id = pg_temp.u(8);
update public.profiles set name = 'د/ هيثم قديم' where id = pg_temp.u(9);
update public.profiles set name = U&'PN Anne\2011Old O''Brien' where id = pg_temp.u(10);
update public.profiles set name = U&'PN Hale\0301\0301 Old' where id = pg_temp.u(11);
update public.profiles set name_key = 'stale', name_needs_fix = true where id = pg_temp.u(9);    -- flagged by 0038 ("/" was refused)
update public.profiles set name_key = null, name_needs_fix = false where id in (pg_temp.u(10), pg_temp.u(11));
set session_replication_role = origin;
\ir ../migrations/0038_names_allowlist.sql
\ir ../migrations/0039_names_rule_2.sql
\o /dev/null
select pg_temp.ok('existing names (0039): a name 0038 flagged that the new rule allows is no longer flagged', $$(select name = 'د/ هيثم قديم' and not name_needs_fix and name_key = public.person_name_key('د/ هيثم قديم') from public.profiles where id = pg_temp.u(9))$$);
select pg_temp.ok('existing names (0039): look-alike hyphens and apostrophes are written - and ’ (reads the same)', $$(select name = 'PN Anne-Old O’Brien' and not name_needs_fix from public.profiles where id = pg_temp.u(10))$$);
select pg_temp.ok('existing names (0039): a mark repeated on a letter is kept and flagged', $$(select name = normalize(U&'PN Hale\0301\0301 Old', NFC) and name_needs_fix from public.profiles where id = pg_temp.u(11))$$);
select pg_temp.ok('existing names: U+FFFC is removed, the name is then allowed (not flagged)', $$(select name = 'PN Zeina Old' and not name_needs_fix and name_key = public.person_name_key('PN Zeina Old') from public.profiles where id = pg_temp.u(7))$$);
select pg_temp.ok('existing names: a name that still breaks the rule is kept as it reads and flagged', $$(select name = 'PN Hala Old - Pharco Old' and name_needs_fix and name_key is not null from public.profiles where id = pg_temp.u(8))$$);
select pg_temp.ok('existing names: every profile has a key', $$not exists (select 1 from public.profiles where name_key is null)$$);

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
