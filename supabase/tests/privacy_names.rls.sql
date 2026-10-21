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
select pg_temp.ok('names: and names the character', $$(select pg_temp.err_of($q$update public.profiles set name = U&'PN Zeina X\FFFC' where id = pg_temp.u(2)$q$)) like U&'%remove “\2068\FFFC\2069” (\2068U+FFFC\2069)'$$);
select pg_temp.step('u2 cannot forge her key or flag', $$update public.profiles set name_key = 'pn hala x', name_needs_fix = true where id = pg_temp.u(2)$$);
select pg_temp.ok('names: key and flag are the database''s', $$(select name_key = public.person_name_key('PN Zeina X') and not name_needs_fix from public.profiles where id = pg_temp.u(2))$$);
select pg_temp.step('real names are accepted (Arabic with harakat, accents, apostrophes, brackets)', $$update public.profiles set name = 'د. نرمين أبو زيدٍ' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: an Arabic name with harakat is stored without them (fourth version)', $$(select name from public.profiles where id = pg_temp.u(2)) = 'د. نرمين أبو زيد'$$);
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
select pg_temp.no('names: the same mark twice on one letter is refused', $$update public.profiles set name = U&'PN Hale\0301\0301' where id = pg_temp.u(2)$$, '23514');
-- the third version (0039_names_rule_3): a Cyrillic word that reads as Latin is that Latin name's twin (ӏ U+04CF has the skeleton of l)
select pg_temp.step('"Dr. Ѕаӏіһ" (Cyrillic letters that read "Dr. Salih")', $$update public.profiles set name = U&'Dr. \0405\0430\04CF\0456\04BB' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: "Dr. Ѕаӏіһ" is allowed with the skeleton of "Dr. Salih" (a twin, told apart)', $$(select name_key = public.person_name_key('Dr. Salih') and not name_needs_fix from public.profiles where id = pg_temp.u(2))$$);
select pg_temp.step('a Greek name that reads as Latin, "Άννα Βίσση"', $$update public.profiles set name = 'Άννα Βίσση' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: "Άννα Βίσση" is kept as written, not flagged', $$(select name = 'Άννα Βίσση' and not name_needs_fix from public.profiles where id = pg_temp.u(2))$$);
select pg_temp.step('an em dash and a title glued to an Arabic name', $$update public.profiles set name = 'Dr.أحمد Jean—Paul' where id = pg_temp.u(2)$$);
select pg_temp.ok('names: the em dash is stored as a hyphen', $$(select name = 'Dr.أحمد Jean-Paul' and not name_needs_fix from public.profiles where id = pg_temp.u(2))$$);
select pg_temp.no('names: e + U+0335 overlay ("PN Ahme̵d") is refused', $$update public.profiles set name = U&'PN Ahme\0335d' where id = pg_temp.u(2)$$, '23514');
select pg_temp.ok('names: …saying which letter and mark', $$(select pg_temp.err_of($q$update public.profiles set name = U&'PN Ahme\0335d' where id = pg_temp.u(2)$q$)) like U&'Remove the mark added to “\2068e\0335\2069” (\2068U+0335\2069)%'$$);
select pg_temp.no('names: a dotless ı + dot above ("PN Alı̇") is refused', $$update public.profiles set name = U&'PN Al\0131\0307' where id = pg_temp.u(2)$$, '23514');
select pg_temp.no('names: i + dot above ("PN Sali̇h") is refused', $$update public.profiles set name = U&'PN Sali\0307h' where id = pg_temp.u(2)$$, '23514');
select pg_temp.no('names: a Greek capital with a macron ("Τ̄ΑΣΟΣ") is refused', $$update public.profiles set name = U&'\03A4\0304\0391\03A3\039F\03A3' where id = pg_temp.u(2)$$, '23514');
select pg_temp.no('names: Ɥ U+A78D (draws as Cyrillic Ч) is refused', $$update public.profiles set name = U&'\A78DEXOB' where id = pg_temp.u(2)$$, '23514');
select pg_temp.no('names: a Latin Extended-G letter (no font draws it) is refused', $$update public.profiles set name = U&'PN Ahmed \+01DF00' where id = pg_temp.u(2)$$, '23514');
select pg_temp.as_server();
select pg_temp.no('sign-up: "Ahme̵d" is refused (nothing is created)', $$insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(14), 'pn14@pn36.test', jsonb_build_object('name', U&'PN Ahme\0335d'))$$, '23514');
select pg_temp.ok('sign-up: …no profile either', $$not exists (select 1 from public.profiles where id = pg_temp.u(14))$$);
insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(14), 'pn14@pn36.test', jsonb_build_object('name', 'ОКСАНА КОРОТКОВА')) on conflict do nothing;
select pg_temp.ok('sign-up: an all-caps Cyrillic name is accepted', $$(select name = 'ОКСАНА КОРОТКОВА' and not name_needs_fix from public.profiles where id = pg_temp.u(14))$$);
select pg_temp.as_anon();
select pg_temp.no('anon cannot write a name', $$update public.profiles set name = 'PN anon' where id = pg_temp.u(2)$$, '42501');
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.ok('names: the refusal names the character typed (U+FE69, not the "$" it becomes)', $$(select pg_temp.err_of($q$update public.profiles set name = U&'PN Ahmed \FE69x' where id = pg_temp.u(2)$q$)) like U&'%remove “\2068﹩\2069” (\2068U+FE69\2069)'$$);
select pg_temp.ok('names: …the word that is only punctuation', $$(select pg_temp.err_of($q$update public.profiles set name = 'د . أحمد' where id = pg_temp.u(2)$q$)) = U&'“\2068.\2069” is not a word — join it to the word next to it (remove the space)'$$);
select pg_temp.ok('names: …and the alphabets accepted', $$(select pg_temp.err_of($q$update public.profiles set name = '张伟' where id = pg_temp.u(2)$q$)) like U&'Write a name in Latin, Arabic, Greek or Cyrillic letters — “\2068张\2069” (\2068U+5F20\2069)%'$$);
-- 0039: a conversation says how many other members share the partner's skeleton — even members this browser never loaded
select pg_temp.as_server();
insert into auth.users (id, email, raw_user_meta_data) select pg_temp.u(g), 'pn' || g || '@pn36.test', jsonb_build_object('name', 'PN Famous Person') from generate_series(12, 13) g on conflict do nothing;
update public.profiles set name = 'PN F' || chr(1072) || 'mous Person' where id = pg_temp.u(13);   -- a server write: kept, flagged, same skeleton
insert into public.messages (sender_id, receiver_id, body) values (pg_temp.u(13), pg_temp.u(4), 'PN hello, it is me');
select pg_temp.as_user(pg_temp.u(4));
select pg_temp.ok('my_conversations: name_twins counts the other members with the partner''s skeleton', $$(select name_twins = 1 and name_key = public.person_name_key('PN Famous Person') and name_needs_fix from public.my_conversations(30) where partner = pg_temp.u(13))$$);
select pg_temp.as_user(pg_temp.u(12));
select pg_temp.ok('my_conversations: a member sees no conversation she is not in', $$not exists (select 1 from public.my_conversations(30) where partner = pg_temp.u(13))$$);
-- a flagged member cannot lift her own flag, nor give herself another key, by keeping her name (the trigger computes both)
select pg_temp.as_user(pg_temp.u(13));
select pg_temp.step('u13 (flagged) writes name_needs_fix = false and a key of her own', $$update public.profiles set name_needs_fix = false, name_key = 'pn someone else' where id = pg_temp.u(13)$$);
select pg_temp.ok('names: the flag and the key stay what the rule says', $$(select name_needs_fix and name_key = public.person_name_key('PN Famous Person') from public.profiles where id = pg_temp.u(13))$$);
select pg_temp.as_server();
-- existing names (0038's own update, then 0039's, re-applied here): invisible characters and U+FFFC go; a name the new rule allows
-- once normalised is stored normalised and not flagged; any other name is kept and flagged
insert into auth.users (id, email) select pg_temp.u(g), 'pn' || g || '@pn36.test' from generate_series(9, 11) g on conflict do nothing;
insert into auth.users (id, email) select pg_temp.u(g), 'pn' || g || '@pn36.test' from generate_series(15, 19) g on conflict do nothing;
insert into auth.users (id, email) select pg_temp.u(g), 'pn' || g || '@pn36.test' from generate_series(27, 30) g on conflict do nothing;
insert into auth.users (id, email) select pg_temp.u(g), 'pn' || g || '@pn36.test' from generate_series(35, 39) g on conflict do nothing;
set session_replication_role = replica;   -- rows as 0037 left them (no name trigger)
update public.profiles set name = U&'PN Zeina Old\FFFC', name_key = null, name_needs_fix = false where id = pg_temp.u(7);
update public.profiles set name = 'PN Hala Old - Pharco Old', name_key = null, name_needs_fix = false where id = pg_temp.u(8);
update public.profiles set name = 'د/ هيثم قديم' where id = pg_temp.u(9);
update public.profiles set name = U&'PN Anne\2011Old O''Brien' where id = pg_temp.u(10);
update public.profiles set name = U&'PN Hale\0301\0301 Old' where id = pg_temp.u(11);
update public.profiles set name = 'Άννα Βίσση' where id = pg_temp.u(15);               -- flagged by 0039_names_rule_2 ('latin'), allowed by the third version
update public.profiles set name = U&'PN Ahme\0335d Old' where id = pg_temp.u(16);      -- allowed by 0039_names_rule_2, refused by the third version
update public.profiles set name = 'PN Jean—Paul Old' where id = pg_temp.u(17);         -- an em dash: refused by 0039_names_rule_2, a hyphen in the third
update public.profiles set name = 'PN حْالد قديم' where id = pg_temp.u(18);              -- a sukun over ح: allowed by the third version, removed by the fourth
update public.profiles set name = 'د / سامي قديم' where id = pg_temp.u(19);              -- a spaced slash: refused before the fourth version
update public.profiles set name = 'PN مُصْطَفَى 2' where id = pg_temp.u(27);              -- a digit (flagged) and harakat
update public.profiles set name = 'PN José Old', name_key = 'pn jose\u0301 old' where id = pg_temp.u(28);   -- keyed by the third version
update public.profiles set name = '(MBA) PN Old', name_key = '(rnba) pn old', name_needs_fix = false where id = pg_temp.u(29);   -- a bracket first: allowed before the fifth version
update public.profiles set name = 'ثروت قديم', name_key = 'stale', name_needs_fix = false where id = pg_temp.u(30);       -- ث: keyed like ئ by the fifth version
-- sixth version (round 5): a space inside a bracket (refused as a word before: tidied now), the space after a letter that never joins,
-- the Turkish İ for i — names that look alike, keyed apart until the sixth version
update public.profiles set name = 'PN Ali ( MBA ) Old', name_key = null, name_needs_fix = false where id = pg_temp.u(35);
update public.profiles set name = 'عبد الله قديم', name_key = null, name_needs_fix = false where id = pg_temp.u(36);
update public.profiles set name = 'عبدالله قديم', name_key = null, name_needs_fix = false where id = pg_temp.u(37);
update public.profiles set name = 'PN Alİ Old', name_key = null, name_needs_fix = false where id = pg_temp.u(38);
update public.profiles set name = 'PN Ali Old', name_key = null, name_needs_fix = false where id = pg_temp.u(39);
update public.profiles set name_key = null, name_needs_fix = false where id in (pg_temp.u(18), pg_temp.u(19), pg_temp.u(27));
update public.profiles set name_key = null, name_needs_fix = false where id in (pg_temp.u(15), pg_temp.u(16), pg_temp.u(17));
update public.profiles set name_key = 'stale', name_needs_fix = true where id = pg_temp.u(9);    -- flagged by 0038 ("/" was refused)
update public.profiles set name_key = null, name_needs_fix = false where id in (pg_temp.u(10), pg_temp.u(11));
set session_replication_role = origin;
\ir ../migrations/0038_names_allowlist.sql
\ir ../migrations/0039_names_rule_2.sql
\o /dev/null
select pg_temp.ok('existing names (0039_names_rule_2): "Άννα Βίσση" was flagged for reading as Latin', $$(select name_needs_fix from public.profiles where id = pg_temp.u(15))$$);
\o
\ir ../migrations/0039_names_rule_3.sql
\o /dev/null
select pg_temp.ok('existing names (third version): an Arabic name with a sukun over an undotted letter was kept as written', $$(select name = 'PN حْالد قديم' from public.profiles where id = pg_temp.u(18))$$);
\o
\ir ../migrations/0039_names_rule_4.sql
\ir ../migrations/0039_names_rule_5.sql
\o /dev/null
select pg_temp.ok('existing names (fifth version): a space inside a bracket was flagged (a word that is only "(")', $$(select name = 'PN Ali ( MBA ) Old' and name_needs_fix from public.profiles where id = pg_temp.u(35))$$);
select pg_temp.ok('existing names (fifth version): «عبد الله قديم» and «عبدالله قديم» had two skeletons', $$(select count(distinct name_key) = 2 from public.profiles where id in (pg_temp.u(36), pg_temp.u(37)))$$);
select pg_temp.ok('existing names (fifth version): «PN Alİ Old» and «PN Ali Old» had two skeletons', $$(select count(distinct name_key) = 2 from public.profiles where id in (pg_temp.u(38), pg_temp.u(39)))$$);
\o
\ir ../migrations/0039_names_rule_6.sql
\o /dev/null
select pg_temp.ok('existing names (sixth version): a space inside a bracket is tidied, «PN Ali (MBA) Old», no longer flagged', $$(select name = 'PN Ali (MBA) Old' and not name_needs_fix and name_key = public.person_name_key('PN Ali (MBA) Old') from public.profiles where id = pg_temp.u(35))$$);
select pg_temp.ok('existing names (sixth version): «عبد الله قديم» and «عبدالله قديم» are twins (one skeleton), both kept as written, not flagged', $$(select count(distinct name_key) = 1 and bool_and(not name_needs_fix)
  and string_agg(name, '|' order by id) = 'عبد الله قديم|عبدالله قديم' from public.profiles where id in (pg_temp.u(36), pg_temp.u(37)))$$);
select pg_temp.ok('existing names (sixth version): «PN Alİ Old» and «PN Ali Old» are twins, kept as written, not flagged', $$(select count(distinct name_key) = 1 and bool_and(not name_needs_fix)
  and string_agg(name, '|' order by id) = 'PN Alİ Old|PN Ali Old' from public.profiles where id in (pg_temp.u(38), pg_temp.u(39)))$$);
select pg_temp.ok('existing names (fifth version): a name starting with a bracket is kept and flagged («(MBA) PN Old», bidi)', $$(select name = '(MBA) PN Old' and name_needs_fix and name_key = public.person_name_key('(MBA) PN Old') from public.profiles where id = pg_temp.u(29))$$);
select pg_temp.ok('existing names (fifth version): «ثروت قديم» is keyed again — the twin of «ئروت قديم» (bold ث / ئ)', $$(select name = 'ثروت قديم' and not name_needs_fix and name_key = public.person_name_key('ئروت قديم') from public.profiles where id = pg_temp.u(30))$$);
select pg_temp.ok('existing names (fourth version): the sukun is removed, «PN حالد قديم», not flagged, keyed', $$(select name = 'PN حالد قديم' and not name_needs_fix and name_key = public.person_name_key('PN حالد قديم') from public.profiles where id = pg_temp.u(18))$$);
select pg_temp.ok('existing names (fourth version): a spaced slash is joined, «د/ سامي قديم»', $$(select name = 'د/ سامي قديم' and not name_needs_fix from public.profiles where id = pg_temp.u(19))$$);
select pg_temp.ok('existing names (fourth version): a flagged name with harakat loses them and stays flagged', $$(select name = 'PN مصطفى 2' and name_needs_fix from public.profiles where id = pg_temp.u(27))$$);
select pg_temp.ok('existing names (fourth version): an accented name is keyed again (é and è are one mark now)', $$(select name_key = public.person_name_key('PN Josè Old') from public.profiles where id = pg_temp.u(28))$$);
select pg_temp.ok('existing names (third version): "Άννα Βίσση" is kept and no longer flagged', $$(select name = 'Άννα Βίσση' and not name_needs_fix and name_key = public.person_name_key('Άννα Βίσση') from public.profiles where id = pg_temp.u(15))$$);
select pg_temp.ok('existing names (third version): a mark NFKC cannot join is KEPT (never stripped into another name) and flagged', $$(select name = U&'PN Ahme\0335d Old' and name_needs_fix and name_key = public.person_name_key(U&'PN Ahme\0335d Old') from public.profiles where id = pg_temp.u(16))$$);
select pg_temp.ok('existing names (third version): an em dash is written as a hyphen, not flagged', $$(select name = 'PN Jean-Paul Old' and not name_needs_fix from public.profiles where id = pg_temp.u(17))$$);
select pg_temp.ok('existing names (0039): a name 0038 flagged that the new rule allows is no longer flagged', $$(select name = 'د/ هيثم قديم' and not name_needs_fix and name_key = public.person_name_key('د/ هيثم قديم') from public.profiles where id = pg_temp.u(9))$$);
select pg_temp.ok('existing names (0039): look-alike hyphens and apostrophes are written - and ’ (reads the same)', $$(select name = 'PN Anne-Old O’Brien' and not name_needs_fix from public.profiles where id = pg_temp.u(10))$$);
select pg_temp.ok('existing names (0039): a mark repeated on a letter is kept and flagged', $$(select name = normalize(U&'PN Hale\0301\0301 Old', NFC) and name_needs_fix from public.profiles where id = pg_temp.u(11))$$);
select pg_temp.ok('existing names: U+FFFC is removed, the name is then allowed (not flagged)', $$(select name = 'PN Zeina Old' and not name_needs_fix and name_key = public.person_name_key('PN Zeina Old') from public.profiles where id = pg_temp.u(7))$$);
select pg_temp.ok('existing names: a name that still breaks the rule is kept as it reads and flagged', $$(select name = 'PN Hala Old - Pharco Old' and name_needs_fix and name_key is not null from public.profiles where id = pg_temp.u(8))$$);
select pg_temp.ok('existing names: every profile has a key', $$not exists (select 1 from public.profiles where name_key is null)$$);

-- ══ 2b. every way a name is written (fourth and fifth versions, 0039_names_rule_4 and _5) ═══════════════════════════════════════════════════
-- The ways a name reaches profiles.name, found by reading the catalog (so a new one fails this suite until it is added here): the
-- sign-up trigger handle_new_user (auth.users metadata) and a member's own UPDATE (Edit Profile, PATCH /profiles); a Drugbox admin's
-- UPDATE of another member (the "verify people" policy) cannot touch the name; no other function writes it, anon and members cannot INSERT a
-- profile, and nothing copies a changed auth.users metadata name. For each: a disallowed name is refused, a look-alike of an existing
-- member is normalised the same way (the mark over an undotted letter removed; an accent that draws like another keyed as its twin),
-- and the stored name_key is the database's skeleton of what was typed (supabase/tests/name_rule.sql shows it is the app's).
select pg_temp.as_server();
select pg_temp.ok('write paths: the functions that INSERT or UPDATE profiles are the four known ones', $$(select array_agg(p.proname::text order by p.proname) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
   where n.nspname in ('public', 'private', 'auth') and p.prosrc ~* '(insert\s+into\s+(public\.)?profiles|update\s+(public\.)?profiles\s+(as\s+\w+\s+)?set)')
  = array['handle_new_user', 'increment_profile_view', 'person_followers_count', 'profiles_followers_count']$$);
select pg_temp.ok('write paths: of them only handle_new_user writes a name (the others count views and followers)', $$not exists (select 1 from pg_proc p join pg_namespace n on n.oid = p.pronamespace
   where n.nspname in ('public', 'private', 'auth') and p.proname <> 'handle_new_user' and p.prosrc ~* 'profiles' and p.prosrc ~* '(set|,)\s*name\s*=|profiles\s*\([^)]*\mname\M')$$);
select pg_temp.ok('write paths: the only trigger on auth.users runs on INSERT (a later metadata change never reaches the name)', $$(select array_agg(tgname::text) from pg_trigger
   where tgrelid = 'auth.users'::regclass and not tgisinternal) = array['on_auth_user_created'] and (select tgtype & 16 = 0 and tgtype & 4 = 4 from pg_trigger where tgname = 'on_auth_user_created')$$);
select pg_temp.ok('write paths: anon and members cannot INSERT a profile', $$not has_table_privilege('anon', 'public.profiles', 'INSERT') and not has_table_privilege('authenticated', 'public.profiles', 'INSERT')$$);
-- the members a look-alike would copy
insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(20), 'pn20@pn36.test', jsonb_build_object('name', 'خالد الفيصل')),
  (pg_temp.u(21), 'pn21@pn36.test', jsonb_build_object('name', 'José Tufice')), (pg_temp.u(22), 'pn22@pn36.test', jsonb_build_object('name', 'PN Admin')),
  (pg_temp.u(31), 'pn31@pn36.test', jsonb_build_object('name', 'ثروت الفيصل')), (pg_temp.u(32), 'pn32@pn36.test', jsonb_build_object('name', 'Szőke Tufice'))
  on conflict do nothing;
update public.profiles set role = 'admin' where id = pg_temp.u(22);
-- 1. sign-up metadata
select pg_temp.no('sign-up: a letter not supported yet is refused (Hausa Ɗ)', $$insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(23), 'pn23@pn36.test', jsonb_build_object('name', 'Ɗanjuma Ƙasim'))$$, '23514');
select pg_temp.ok('sign-up: …saying it is not supported yet (isolated)', $$pg_temp.err_of($q$insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(23), 'pn23@pn36.test', jsonb_build_object('name', 'Ɗanjuma Ƙasim'))$q$)
  = U&'The letter “\2068Ɗ\2069” (\2068U+018A\2069) is not supported in names yet'$$);
select pg_temp.no('sign-up: a spaced hyphen is refused', $$insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(23), 'pn23@pn36.test', jsonb_build_object('name', 'PN Ali - MBA'))$$, '23514');
select pg_temp.ok('sign-up: …suggesting the parentheses', $$pg_temp.err_of($q$insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(23), 'pn23@pn36.test', jsonb_build_object('name', 'PN Ali - MBA'))$q$)
  = U&'Put what follows the name in parentheses — write “\2068PN Ali (MBA)\2069”'$$);
insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(23), 'pn23@pn36.test', jsonb_build_object('name', 'حْالد الفيصل')) on conflict do nothing;
select pg_temp.ok('sign-up: «حْالد الفيصل» (looks like «خالد الفيصل») is stored without the sukun: «حالد الفيصل», keyed as typed — the twin of «خالد الفيصل» (sixth version: ح / خ draw within a dot in some font)', $$(select name = 'حالد الفيصل' and name_key = public.person_name_key('حْالد الفيصل')
  and name_key = (select name_key from public.profiles where id = pg_temp.u(20)) and not name_needs_fix from public.profiles where id = pg_temp.u(23))$$);
insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(24), 'pn24@pn36.test', jsonb_build_object('name', 'Josè Tufice')) on conflict do nothing;
select pg_temp.ok('sign-up: «Josè Tufice» (looks like «José Tufice») is keyed as its twin', $$(select name_key = (select name_key from public.profiles where id = pg_temp.u(21)) and name_key = public.person_name_key('Josè Tufice')
  from public.profiles where id = pg_temp.u(24))$$);
-- fifth version (v-spoof-r1): a bracket the bidi algorithm reorders is refused; bold ث / ئ are one skeleton; a zero-width non-joiner is a space
select pg_temp.no('sign-up: a bracket before the name is refused («(MBA) PN Ali» drew as «PN Ali (MBA)» in Arabic)', $$insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(33), 'pn33@pn36.test', jsonb_build_object('name', '(MBA) PN Ali'))$$, '23514');
select pg_temp.ok('sign-up: …suggesting the bracket after the name', $$pg_temp.err_of($q$insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(33), 'pn33@pn36.test', jsonb_build_object('name', '(MBA) PN Ali'))$q$)
  = U&'Put the part in brackets after the name — write “\2068PN Ali (MBA)\2069”'$$);
select pg_temp.no('sign-up: «PN (علي) محمد» is refused (drew as «PN محمد (علي)» in English)', $$insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(33), 'pn33@pn36.test', jsonb_build_object('name', 'PN (علي) محمد'))$$, '23514');
insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(33), 'pn33@pn36.test', jsonb_build_object('name', 'ئروت الفيصل')) on conflict do nothing;
select pg_temp.ok('sign-up: «ئروت الفيصل» (bold, looks like «ثروت الفيصل») is keyed as its twin', $$(select name = 'ئروت الفيصل' and not name_needs_fix and name_key = public.person_name_key('ئروت الفيصل')
  and name_key = (select name_key from public.profiles where id = pg_temp.u(31)) from public.profiles where id = pg_temp.u(33))$$);
insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(34), 'pn34@pn36.test', jsonb_build_object('name', U&'\0639\0644\06CC\200C\0631\0636\0627 Tufice')) on conflict do nothing;
select pg_temp.ok('sign-up: «علی‌رضا» (a zero-width non-joiner) is stored «علی رضا»', $$(select name = 'علی رضا Tufice' and not name_needs_fix from public.profiles where id = pg_temp.u(34))$$);
-- sixth version (round 5): the Turkish İ, a space after a letter that never joins — allowed, keyed as the twins they look like; a space
-- inside a bracket tidied
insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(40), 'pn40@pn36.test', jsonb_build_object('name', 'PN Ali Kaya')),
  (pg_temp.u(41), 'pn41@pn36.test', jsonb_build_object('name', 'PN Alİ Kaya')), (pg_temp.u(42), 'pn42@pn36.test', jsonb_build_object('name', 'عبد الله الفيصل')),
  (pg_temp.u(43), 'pn43@pn36.test', jsonb_build_object('name', 'عبدالله الفيصل')), (pg_temp.u(44), 'pn44@pn36.test', jsonb_build_object('name', 'PN Ali ( MBA )')) on conflict do nothing;
select pg_temp.ok('sign-up: «PN Alİ Kaya» is allowed, stored as typed and keyed as the twin of «PN Ali Kaya»', $$(select name = 'PN Alİ Kaya' and not name_needs_fix and name_key = (select name_key from public.profiles where id = pg_temp.u(40))
  from public.profiles where id = pg_temp.u(41))$$);
select pg_temp.ok('sign-up: «عبد الله الفيصل» is allowed, stored as typed and keyed as the twin of «عبدالله الفيصل»', $$(select name = 'عبد الله الفيصل' and not name_needs_fix and name_key = (select name_key from public.profiles where id = pg_temp.u(43))
  from public.profiles where id = pg_temp.u(42))$$);
select pg_temp.ok('sign-up: «PN Ali ( MBA )» is stored «PN Ali (MBA)» (it was refused)', $$(select name = 'PN Ali (MBA)' and not name_needs_fix from public.profiles where id = pg_temp.u(44))$$);
insert into public.messages (sender_id, receiver_id, body) values (pg_temp.u(42), pg_temp.u(4), 'PN salam from Abdallah');
select pg_temp.as_user(pg_temp.u(4));
select pg_temp.ok('my_conversations: «عبد الله الفيصل» writes first — name_twins counts «عبدالله الفيصل» (the skeleton ignores the space)', $$(select name_twins = 1 and name_key = public.person_name_key('عبدالله الفيصل') from public.my_conversations(30) where partner = pg_temp.u(42))$$);
select pg_temp.as_server();
insert into auth.users (id, email, raw_user_meta_data) values (pg_temp.u(25), 'pn25@pn36.test', jsonb_build_object('name', 'د / سامي فهمي')) on conflict do nothing;
select pg_temp.ok('sign-up: «د / سامي فهمي» is stored «د/ سامي فهمي»', $$(select name = 'د/ سامي فهمي' and not name_needs_fix from public.profiles where id = pg_temp.u(25))$$);
-- 2. a member's own UPDATE (Edit Profile)
select pg_temp.as_user(pg_temp.u(25));
select pg_temp.no('member: a letter not supported yet is refused', $$update public.profiles set name = 'Ɔpɔku Mensah' where id = pg_temp.u(25)$$, '23514');
select pg_temp.step('member: renames herself «عْادة الفيصل» (looks like «غادة»)', $$update public.profiles set name = 'عْادة الفيصل' where id = pg_temp.u(25)$$);
select pg_temp.ok('member: stored «عادة الفيصل», keyed as typed — the twin of «غادة الفيصل» (sixth version)', $$(select name = 'عادة الفيصل' and name_key = public.person_name_key('عْادة الفيصل') and name_key = public.person_name_key('غادة الفيصل') from public.profiles where id = pg_temp.u(25))$$);
select pg_temp.step('member: renames herself «حْالد الفيصل»', $$update public.profiles set name = 'حْالد الفيصل' where id = pg_temp.u(25)$$);
select pg_temp.ok('member: stored like the sign-up path stores it (same name, same key)', $$(select row(name, name_key) from public.profiles where id = pg_temp.u(25)) = (select row(name, name_key) from public.profiles where id = pg_temp.u(23))$$);
select pg_temp.step('member: «Saʿīd Ḥasan» (ʿ U+02BF)', $$update public.profiles set name = 'Saʿīd Ḥasan' where id = pg_temp.u(25)$$);
select pg_temp.ok('member: ʿ is stored ’ like ʾ', $$(select name = 'Sa’īd Ḥasan' and name_key = public.person_name_key('Saʾīd Ḥasan') from public.profiles where id = pg_temp.u(25))$$);
select pg_temp.no('member: «(صيدلي) أحمد الفيصل» is refused (a bracket before the name)', $$update public.profiles set name = '(صيدلي) أحمد الفيصل' where id = pg_temp.u(25)$$, '23514');
select pg_temp.no('member: «منى (Ali) Mona» is refused (drew as «منى Mona (Ali)» in Arabic)', $$update public.profiles set name = 'منى (Ali) Mona' where id = pg_temp.u(25)$$, '23514');
select pg_temp.step('member: renames herself «Szổke Tufice» (bold, looks like «Szőke Tufice»)', $$update public.profiles set name = 'Szổke Tufice' where id = pg_temp.u(25)$$);
select pg_temp.ok('member: keyed as the twin of «Szőke Tufice»', $$(select name = 'Szổke Tufice' and name_key = (select name_key from public.profiles where id = pg_temp.u(32)) from public.profiles where id = pg_temp.u(25))$$);
select pg_temp.step('member: «PN Ali محمد (علي)» (the bracket after the name, its own direction) is fine', $$update public.profiles set name = 'PN Ali محمد (علي)' where id = pg_temp.u(25)$$);
select pg_temp.ok('member: stored as written, not flagged', $$(select name = 'PN Ali محمد (علي)' and not name_needs_fix from public.profiles where id = pg_temp.u(25))$$);
select pg_temp.step('member: «Ahmed ( Mido ) PN» (spaces inside the brackets — sixth version)', $$update public.profiles set name = 'Ahmed ( Mido ) PN' where id = pg_temp.u(25)$$);
select pg_temp.ok('member: stored «Ahmed (Mido) PN», not flagged', $$(select name = 'Ahmed (Mido) PN' and not name_needs_fix from public.profiles where id = pg_temp.u(25))$$);
select pg_temp.step('member: renames herself «PN Alİ Kaya»', $$update public.profiles set name = 'PN Alİ Kaya' where id = pg_temp.u(25)$$);
select pg_temp.ok('member: keyed as the twin of «PN Ali Kaya» (same key as the sign-up path)', $$(select name = 'PN Alİ Kaya' and name_key = (select name_key from public.profiles where id = pg_temp.u(40)) from public.profiles where id = pg_temp.u(25))$$);
select pg_temp.step('member: another member''s row', $$update public.profiles set name = 'PN hijacked' where id = pg_temp.u(21)$$);
select pg_temp.ok('member: another member''s name is not touched (row security)', $$(select name from public.profiles where id = pg_temp.u(21)) = 'José Tufice'$$);
select pg_temp.no('member: cannot INSERT a profile', $$insert into public.profiles (id, name) values (pg_temp.u(26), 'PN extra')$$, '42501');
-- 3. a Drugbox admin (the "verify people" policy) changes only the role and verification of someone else — never the name
select pg_temp.as_user(pg_temp.u(22));
select pg_temp.no('admin: cannot rename another member, even with an allowed name', $$update public.profiles set name = 'رْياد الفيصل' where id = pg_temp.u(24)$$, '42501');
select pg_temp.no('admin: …nor with a disallowed one', $$update public.profiles set name = 'Ɗanjuma' where id = pg_temp.u(24)$$, '42501');
select pg_temp.ok('admin: the member''s name is unchanged', $$(select name from public.profiles where id = pg_temp.u(24)) = 'Josè Tufice'$$);
select pg_temp.step('admin: renames HERSELF «رْياد الفيصل» (looks like «زياد»)', $$update public.profiles set name = 'رْياد الفيصل' where id = pg_temp.u(22)$$);
select pg_temp.ok('admin: stored «رياد الفيصل», keyed as typed', $$(select name = 'رياد الفيصل' and name_key = public.person_name_key('رْياد الفيصل') from public.profiles where id = pg_temp.u(22))$$);
select pg_temp.no('admin: …and cannot rename herself «(MBA) PN Admin» (fifth version)', $$update public.profiles set name = '(MBA) PN Admin' where id = pg_temp.u(22)$$, '23514');
-- 4. anon; 5. a later change of the sign-up metadata
select pg_temp.as_anon();
select pg_temp.no('anon: cannot write a name', $$update public.profiles set name = 'حْالد' where id = pg_temp.u(20)$$, '42501');
select pg_temp.no('anon: cannot INSERT a profile', $$insert into public.profiles (id, name) values (pg_temp.u(26), 'PN extra')$$, '42501');
select pg_temp.as_server();
update auth.users set raw_user_meta_data = jsonb_build_object('name', 'Ɗanjuma') where id = pg_temp.u(20);
select pg_temp.ok('metadata: a later change of the sign-up metadata does not reach the name', $$(select name from public.profiles where id = pg_temp.u(20)) = 'خالد الفيصل'$$);
-- every stored name is what the rule makes of it, keyed by it
select pg_temp.ok('write paths: every PN profile is stored normalised and keyed by the rule', $$not exists (select 1 from public.profiles p join auth.users u on u.id = p.id where u.email like '%@pn36.test'
   and (p.name_key is distinct from public.person_name_key(p.name) or (not p.name_needs_fix and p.name <> public.person_name_norm(p.name))))$$);

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
