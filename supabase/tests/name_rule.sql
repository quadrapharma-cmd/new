-- One rule for names in the database and in the app (S-03, 0038): for EVERY code point of planes 0 and 1, in four places (inside a
-- Latin word, alone between spaces, at the start, inside an Arabic word), the database's person_name_norm, person_name_problem and
-- person_name_key must give what the live app's nmNorm, nmProblem and nmSkel give (web/src/live/adapter.js, generated with the
-- migration by tools/names/name_rule.mjs). The app's side comes from node tools/names/name_rule.mjs --expect, which first checks that
-- both generated regions are current and that the app's code follows the rule's definition (every number refused; every symbol,
-- private-use, unassigned, punctuation and restricted letter refused; the verifiers' look-alikes refused; twins share a skeleton),
-- and fails the load otherwise. A code point whose NFKC or NFD differs between Node and PostgreSQL (one knows a newer Unicode) is
-- not compared; there must be few of them. Then the strings every verifier used, and the real names that must keep working.
-- Run from the repository root (the program path is relative), on a fresh database (stub + migrations):
--   psql -f supabase/tests/name_rule.sql
\set QUIET on
set client_min_messages = warning;
\o /dev/null
begin;
create temp table r (n serial, name text, ok boolean, err text);
create temp table app (cp int, place text, norm text, problem text, skel text, nf text, nd text);
\set ON_ERROR_STOP on
\copy app from program 'node tools/names/name_rule.mjs --expect'
\set ON_ERROR_STOP off
create temp table got as
  select a.*, d.s, public.person_name_norm(d.s) as db_norm, public.person_name_problem(public.person_name_norm(d.s)) as db_problem, public.person_name_key(d.s) as db_skel,
         normalize(chr(a.cp), NFKC) is distinct from a.nf or normalize(chr(a.cp), NFD) is distinct from a.nd as skew
    from app a cross join lateral (select case a.place when 'w' then 'Ab' || chr(a.cp) || 'ab' when 's' then 'Ab ' || chr(a.cp) || ' ab'
                                                     when 'b' then chr(a.cp) || 'ab' else 'بب' || chr(a.cp) || 'بب' end as s) d;
insert into r(name, ok, err) select 'the app''s rule was loaded for every code point of planes 0-1 (4 places each)', count(*) = 4 * (131071 - 2048), count(*)::text from app;
insert into r(name, ok, err) select 'database = app: the normalised name, for every code point', count(*) = 0,
       count(*) || ' differ, e.g. ' || string_agg(format('U+%s/%s db=%s app=%s', upper(to_hex(cp)), place, db_norm, norm), '; ') filter (where rn <= 6)
  from (select *, row_number() over () rn from got where not skew and db_norm <> norm) d;
insert into r(name, ok, err) select 'database = app: allowed or why not, for every code point', count(*) = 0,
       count(*) || ' differ, e.g. ' || string_agg(format('U+%s/%s db=%s app=%s', upper(to_hex(cp)), place, db_problem, problem), '; ') filter (where rn <= 6)
  from (select *, row_number() over () rn from got where not skew and db_problem <> problem) d;
insert into r(name, ok, err) select 'database = app: the skeleton, for every code point', count(*) = 0,
       count(*) || ' differ, e.g. ' || string_agg(format('U+%s/%s db=%s app=%s', upper(to_hex(cp)), place, db_skel, skel), '; ') filter (where rn <= 6)
  from (select *, row_number() over () rn from got where not skew and db_skel <> skel) d;
insert into r(name, ok, err) select 'few code points normalise differently in Node and PostgreSQL (newer Unicode)', count(distinct cp) < 400, count(distinct cp)::text from got where skew;
insert into r(name, ok, err) select 'the picker separator "·" (and every dot look-alike tried) cannot be part of an allowed name', count(*) = 0, string_agg(s, ' | ')
  from (select s from got where place in ('w', 's', 'r') and cp in (183, 903, 5867, 8226, 8231, 8729, 8901, 11825, 11827, 12539, 42895, 65381, 70004, 70096, 128919, 8728, 9642, 65532, 65533)
          and problem = '') d;
-- every string the verifiers used (p1b privacy/s03.py, reverify1/s03b.py and s03c.py, reverify2/s03/s03d.py and s03e.py) and the
-- look-alikes listed in S-03: refused with the reason, or (invisible characters) the same name as the real one
insert into r(name, ok, err) select 'verifier: ' || x.name, public.person_name_problem(public.person_name_norm(x.s)) = x.want,
       coalesce(public.person_name_problem(public.person_name_norm(x.s)), 'null') || ' / ' || public.person_name_norm(x.s) from (values
  ('"Dr. Hala X · Pharco X" (the picker''s own separator)', 'Dr. Hala Tufice · Pharco Tufice', 'char'),
  ('U+A78F LATIN LETTER SINOLOGICAL DOT', U&'Dr. Hala Tufice \A78F Pharco Tufice', 'char'),
  ('U+2E33 RAISED DOT', U&'Dr. Hala Tufice \2E33 Pharco Tufice', 'char'),
  ('U+11174 MAHAJANI ABBREVIATION SIGN', U&'Dr. Hala Tufice \+011174 Pharco Tufice', 'char'),
  ('U+1F797 MEDIUM SMALL WHITE CIRCLE', U&'Dr. Hala Tufice \+01F797 Pharco Tufice', 'char'),
  ('U+111D0 SHARADA DIGIT ZERO', U&'Dr. Hala Tufice \+0111D0 Pharco Tufice', 'digit'),
  ('U+2218 RING OPERATOR ∘', 'Dr. Hala Tufice ∘ Pharco Tufice', 'char'),
  ('U+25AA BLACK SMALL SQUARE ▪', 'Dr. Hala Tufice ▪ Pharco Tufice', 'char'),
  ('U+FFFC + U+10C9 ("￼ႉ")', U&'Dr. Hala Tufice \FFFC\10C9 Pharco Tufice', 'char'),
  ('U+FFFC OBJECT REPLACEMENT at the end ("Dr. Zeina X￼")', U&'Dr. Zeina Tufice\FFFC', 'char'),
  ('U+FFFD REPLACEMENT CHARACTER', U&'Dr. Zeina Tufice\FFFD', 'char'),
  ('Cyrillic а in "Dr. Rаna"', U&'Dr. R\0430na Tufice', 'script'),
  ('Greek ο in a Latin word', U&'Dr. N\03BFur Tufice', 'script'),
  ('a Latin word next to a Cyrillic word', U&'Dr. \0418\0432\0430\043D', 'script'),
  ('"Dr. Hala X - Pharco X" (0037''s separator: a word without a letter)', 'Dr. Hala Tufice - Pharco Tufice', 'word'),
  ('a digit ("Dr. Rana 2")', 'Dr. Rana 2', 'digit'),
  ('an Arabic-Indic zero standing alone', 'د. هالة ٠ فاركو', 'digit'),
  ('U+02D1 MODIFIER LETTER HALF TRIANGULAR COLON (Common script)', U&'Dr. Hala \02D1 Pharco', 'char'),
  ('U+01C3 click letter ǃ (Restricted)', U&'Dr. Hala\01C3', 'char'),
  ('a combining mark with no letter', U&'Dr. Hala \0307 Pharco', 'word'),
  ('four marks on one letter', U&'Dr. Hab\0301\0301\0301\0301', 'mark'),
  ('invisible U+200B is removed: allowed', U&'Dr. Zeina Tufice\200B', ''),
  ('invisible U+1D173 is removed: allowed', U&'Dr. Zeina Tufice\+01D173', ''),
  ('invisible U+1BCA0 is removed: allowed', U&'Dr. Zeina\+01BCA0 Tufice', ''),
  ('double spaces collapse: allowed', 'Dr.  Zeina Tufice', '')) x(name, s, want);
insert into r(name, ok, err) select 'verifier: invisible look-alikes are stored as the SAME name as the real one (' || x.s || ')',
       public.person_name_norm(x.s) = 'Dr. Zeina Tufice', public.person_name_norm(x.s) from (values
  (U&'Dr. Zeina Tufice\200B'), (U&'Dr. Zeina Tufice\+01D173'), (U&'Dr. Zeina\+01BCA0 Tufice'), ('Dr.  Zeina Tufice')) x(s);
-- names real people have keep working
insert into r(name, ok, err) select 'real name allowed: ' || x.s, public.person_name_problem(public.person_name_norm(x.s)) = '',
       public.person_name_problem(public.person_name_norm(x.s)) from (values
  ('د. هالة الشامي'), ('Dr. Ahmed El-Sayed'), ('O''Brien'), ('O’Brien'), ('José Müller'), ('Ünal'), ('د. نرمين أبو زيدٍ'), ('مُحَمَّد عَبْدُ اللَّه'),
  ('Al-Hassan (Pharm.D.)'), ('Smith, John'), ('Мария Иванова'), ('Νίκος Παπαδόπουλος'), ('Dr. Ahmed محمد'), ('Eng. Omar Khaled'), ('هـالة'), ('Zoë'), ('Çelik Şahin'),
  ('Nguyễn Văn An'), ('Łukasz Wójcik'), ('Søren Ærø'), ('Dr. Nermeen Abou-Zeid')) x(s);
insert into r(name, ok, err) select 'stored as typed: ' || x.s, public.person_name_norm(x.s) = x.want, public.person_name_norm(x.s) from (values
  ('هـالة', 'هالة'), (U&'\FF24\FF52. Hala', 'Dr. Hala'), ('  José   Müller ', 'José Müller'), (U&'Jose\0301', 'José')) x(s, want);
-- twins by skeleton: names that look the same have the same key; names that differ do not
insert into r(name, ok, err) select 'same skeleton: ' || x.a || ' / ' || x.b, public.person_name_key(x.a) = public.person_name_key(x.b), public.person_name_key(x.a) || ' / ' || public.person_name_key(x.b) from (values
  ('Dr. Rana Tufice', U&'Dr. R\0430na Tufice'), ('Ilya', 'llya'), ('O''Brien', 'O’Brien'), ('هالة', 'هالَة'), ('د. هالة الشامي', 'د. هالَة الشّامي'),
  ('Dr. Nermeen Tufece', 'DR. NERMEEN TUFECE'), ('Dr. Islam Tufice', 'Dr. lslam Tufice'), ('Dr. Zeina Tufice', U&'Dr. Zeina Tufice\200B'), ('Dr. Zeina Tufice', U&'Dr. Zeina Tufice\+01D173'), ('Dr. Zeina Tufice', U&'Dr. Zeina Tufice\FFFC'),
  ('Paul', U&'\0420aul'), ('Rana', U&'R\0430na'), ('Omar', U&'\039Fmar')) x(a, b);
insert into r(name, ok, err) select 'different skeleton: ' || x.a || ' / ' || x.b, public.person_name_key(x.a) <> public.person_name_key(x.b), public.person_name_key(x.a) from (values
  ('Dr. Zeina Tufice', 'Dr. Zeina Tufica'), ('Ibrahim', 'ibrahim'), ('أبو', 'ابو'), ('Ali', 'All'), ('Hala', 'Hana')) x(a, b);
\o
\pset tuples_only on
select (case when ok then 'PASS  ' else 'FAIL  ' end) || name || coalesce('   [' || err || ']', '') from r order by n;
select 'TOTAL ' || count(*) filter (where ok) || ' / ' || count(*) from r;
\set ON_ERROR_STOP on
do $$ declare f int; t int; begin select count(*) filter (where not ok), count(*) into f, t from r;
  if t = 0 or f > 0 then raise exception '% of % check(s) FAILED', f, t; end if; end $$;
rollback;
