-- One rule for names in the database and in the app (S-03, 0037): clean_person_name() must give, for EVERY Unicode code point,
-- what the live app's nmClean (web/src/live/adapter.js) gives — inside a word, alone between spaces and at the start of a name.
-- The app's side comes from node tools/names/name_rule.mjs --expect, which first checks nmClean against the rule's definition
-- (default-ignorable, format and control characters removed; spaces; free combining marks; the 52 dot look-alikes) and fails
-- the load if it does not hold. A code point whose NFKC differs between Node and PostgreSQL (one knows a newer Unicode) is not
-- compared; there must be few of them.
-- Run from the repository root (the program path is relative), on a fresh database (stub + migrations):
--   psql -f supabase/tests/name_rule.sql
\set QUIET on
set client_min_messages = warning;
\o /dev/null
begin;
create temp table r (n serial, name text, ok boolean, err text);
create temp table app (cp int, place text, want text, nf text);
\set ON_ERROR_STOP on
\copy app from program 'node tools/names/name_rule.mjs --expect'
\set ON_ERROR_STOP off
create temp table got as
  select a.cp, a.place, a.want, coalesce(public.clean_person_name(case a.place when 'w' then 'a' || chr(a.cp) || 'b' when 's' then 'a ' || chr(a.cp) || ' b' else chr(a.cp) || 'b' end), '') as db,
         normalize(chr(a.cp), NFKC) is distinct from a.nf as skew
    from app a;
insert into r(name, ok, err) select 'the app''s rule was loaded for every code point (3 places each)', count(*) = 3 * (1114111 - 2048), count(*)::text from app;
insert into r(name, ok, err) select 'database = app for every code point both normalise alike', count(*) = 0,
       count(*) || ' differ, e.g. ' || string_agg(format('U+%s/%s db=%s app=%s', upper(to_hex(cp)), place, db, want), '; ') filter (where rn <= 8)
  from (select *, row_number() over () rn from got where not skew and db <> want) d;
insert into r(name, ok, err) select 'few code points normalise differently in Node and PostgreSQL (newer Unicode)', count(distinct cp) < 400, count(distinct cp)::text from got where skew;
-- the verifier's strings (p1b reverify1, s03b.py) and the cases that must stay as they are
insert into r(name, ok, err) select x.name, public.clean_person_name(x.s) is not distinct from x.want, public.clean_person_name(x.s) from (values
  ('U+A78F sinological dot is the picker separator', U&'Dr. Hala Tufice \A78F Pharco Tufice', 'Dr. Hala Tufice - Pharco Tufice'),
  ('U+2E33 raised dot is the picker separator', U&'Dr. Hala Tufice \2E33 Pharco Tufice', 'Dr. Hala Tufice - Pharco Tufice'),
  ('U+1427, U+10101, U+0F0B (untested by the verifier) too', U&'A \1427 B \+010101 C \0F0B D', 'A - B - C - D'),
  ('U+1D173 (default-ignorable) is removed', U&'Dr. Zeina Tufice\+01D173', 'Dr. Zeina Tufice'),
  ('U+1BCA0 (default-ignorable) is removed', U&'Dr. Zeina\+01BCA0 Tufice', 'Dr. Zeina Tufice'),
  ('U+02D9 dot above (NFKC: a free combining dot) is removed', U&'Dr. Hala X \02D9 Pharco X', 'Dr. Hala X Pharco X'),
  ('full-width letters are the same letters (NFKC)', U&'\FF24\FF52. Hala', 'Dr. Hala'),
  ('an Arabic-Indic zero standing alone is a separator', 'د. هالة ٠ فاركو', 'د. هالة - فاركو'),
  ('an Arabic name keeps its letters and its marks', 'د. نرمين  أبو زيدٍ', 'د. نرمين أبو زيدٍ'),
  ('a name with an accent keeps it', 'Dr. Zoë Müller', 'Dr. Zoë Müller'),
  ('a name of only invisible characters is empty', U&'\200B\+01D173 \FEFF', null)) x(name, s, want);
\o
\pset tuples_only on
select (case when ok then 'PASS  ' else 'FAIL  ' end) || name || coalesce('   [' || err || ']', '') from r order by n;
select 'TOTAL ' || count(*) filter (where ok) || ' / ' || count(*) from r;
\set ON_ERROR_STOP on
do $$ declare f int; t int; begin select count(*) filter (where not ok), count(*) into f, t from r;
  if t = 0 or f > 0 then raise exception '% of % check(s) FAILED', f, t; end if; end $$;
rollback;
