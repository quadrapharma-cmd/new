-- One rule for names in the database and in the app (S-03, 0038, its second version 0039_names_rule_2, its third version
-- 0039_names_rule_3, its fourth version 0039_names_rule_4, its fifth 0039_names_rule_5, its sixth 0039_names_rule_6 and its seventh 0039_names_rule_7): for EVERY code point of planes 0 and
-- 1, in four places (inside a Latin word, alone between spaces, at the start, inside an Arabic word), the database's
-- person_name_norm, person_name_problem and person_name_key must give what the live app's nmNorm, nmProblem and nmSkel give, and
-- person_name_message what nmMessage says (inside a word and alone; web/src/live/adapter.js, generated with the migration by
-- tools/names/name_rule.mjs). The app's side comes from node tools/names/name_rule.mjs --expect, which first checks that
-- both generated regions are current and that the app's code follows the rule's definition (every number refused; every symbol,
-- private-use, unassigned, punctuation and restricted letter refused; the verifiers' look-alikes refused; twins share a skeleton),
-- and fails the load otherwise. A code point whose NFKC or NFD differs between Node and PostgreSQL (one knows a newer Unicode) is
-- not compared; there must be few of them. Then EVERY string the verifiers used in rounds 1-4 (supabase/tests/name_rule_strings.txt,
-- through node tools/names/name_rule.mjs --strings): the database gives what the app gives, and no allowed name keeps a combining
-- mark; then the verifiers' attacks one by one with the reason expected, and the real names that must keep working.
-- Run from the repository root (the program path is relative), on a fresh database (stub + migrations):
--   psql -f supabase/tests/name_rule.sql
\set QUIET on
set client_min_messages = warning;
\o /dev/null
begin;
create temp table r (n serial, name text, ok boolean, err text);
create temp table app (cp int, place text, norm text, problem text, skel text, nf text, nd text, msg text);
\set ON_ERROR_STOP on
\copy app from program 'node tools/names/name_rule.mjs --expect'
\set ON_ERROR_STOP off
create temp table got as
  select a.*, d.s, public.person_name_norm(d.s) as db_norm, public.person_name_problem(public.person_name_norm(d.s)) as db_problem, public.person_name_key(d.s) as db_skel,
         case when a.problem <> '' and a.place in ('w', 's') then public.person_name_message(d.s, a.problem) else '' end as db_msg,
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
insert into r(name, ok, err) select 'database = app: the message (the character as typed, the word), for every code point refused', count(*) = 0,
       count(*) || ' differ, e.g. ' || string_agg(format('U+%s/%s db=%s app=%s', upper(to_hex(cp)), place, db_msg, msg), '; ') filter (where rn <= 6)
  from (select *, row_number() over () rn from got where not skew and db_msg is distinct from msg) d;
insert into r(name, ok, err) select 'few code points normalise differently in Node and PostgreSQL (newer Unicode)', count(distinct cp) < 400, count(distinct cp)::text from got where skew;
-- every string the verifiers used in rounds 1-4 (fifth version; round 4 added 10,000+ whole-name variants and the bold-weight letters): the database = the app, and an allowed name holds no combining mark
create temp table vs (s text, norm text, problem text, skel text, msg text, hasmark boolean);
\set ON_ERROR_STOP on
\copy vs from program 'node tools/names/name_rule.mjs --strings supabase/tests/name_rule_strings.txt'
\set ON_ERROR_STOP off
create temp table vgot as select v.*, public.person_name_norm(v.s) as db_norm, public.person_name_problem(public.person_name_norm(v.s)) as db_problem,
       public.person_name_key(v.s) as db_skel, case when v.problem <> '' then public.person_name_message(v.s, v.problem) else '' end as db_msg from vs v;
insert into r(name, ok, err) select 'the verifiers'' strings of rounds 1-4 were loaded', count(*) >= 12000, count(*)::text from vs;
insert into r(name, ok, err) select 'database = app for every string the verifiers used (normalised name, reason, skeleton, message)', count(*) = 0,
       count(*) || ' differ, e.g. ' || string_agg(format('%s: db=%s/%s app=%s/%s', s, db_norm, db_problem, norm, problem), '; ') filter (where rn <= 6)
  from (select *, row_number() over () rn from vgot where db_norm <> norm or db_problem <> problem or db_skel <> skel or db_msg is distinct from msg) d;
insert into r(name, ok, err) select 'no allowed name keeps a combining mark (accents are one character, Arabic diacritics are removed)', count(*) = 0, string_agg(s, ' | ')
  from vgot where problem = '' and hasmark;
insert into r(name, ok, err) select 'no allowed name keeps an Arabic diacritic (vowel mark, tanween, shadda, sukun, superscript alef, Quranic mark)', count(*) = 0, string_agg(s, ' | ')
  from vgot where db_problem = '' and db_norm ~ ('[' || U&'!0610-!061A!064B-!0652!0656-!065F!0670!06D6-!06DC!06DF-!06E8!06EA-!06ED!0897-!089F!08CA-!08E1!08E3-!08FF' uescape '!' || ']');
insert into r(name, ok, err) select 'the picker separator "·" (and every dot look-alike tried) cannot be part of an allowed name', count(*) = 0, string_agg(s, ' | ')
  from (select s from got where place in ('w', 's', 'r') and cp in (183, 903, 5867, 8226, 8231, 8729, 8901, 11825, 11827, 12539, 42895, 65381, 70004, 70096, 128919, 8728, 9642, 65532, 65533)
          and problem = '') d;
-- every string the verifiers used (p1b privacy/s03.py, reverify1/s03b.py and s03c.py, reverify2/s03/s03d.py and s03e.py) and the
-- look-alikes listed in S-03: refused with the reason, or (invisible characters) the same name as the real one
insert into r(name, ok, err) select 'verifier: ' || x.name, public.person_name_problem(public.person_name_norm(x.s)) = x.want,
       coalesce(public.person_name_problem(public.person_name_norm(x.s)), 'null') || ' / ' || public.person_name_norm(x.s) from (values
  ('"Dr. Hala X · Pharco X" (the picker''s own separator)', 'Dr. Hala Tufice · Pharco Tufice', 'char'),
  ('U+A78F LATIN LETTER SINOLOGICAL DOT (a restricted letter)', U&'Dr. Hala Tufice \A78F Pharco Tufice', 'unsupported'),
  ('U+2E33 RAISED DOT', U&'Dr. Hala Tufice \2E33 Pharco Tufice', 'char'),
  ('U+11174 MAHAJANI ABBREVIATION SIGN', U&'Dr. Hala Tufice \+011174 Pharco Tufice', 'char'),
  ('U+1F797 MEDIUM SMALL WHITE CIRCLE', U&'Dr. Hala Tufice \+01F797 Pharco Tufice', 'char'),
  ('U+111D0 SHARADA DIGIT ZERO', U&'Dr. Hala Tufice \+0111D0 Pharco Tufice', 'digit'),
  ('U+2218 RING OPERATOR ∘', 'Dr. Hala Tufice ∘ Pharco Tufice', 'char'),
  ('U+25AA BLACK SMALL SQUARE ▪', 'Dr. Hala Tufice ▪ Pharco Tufice', 'char'),
  ('U+FFFC + U+1089 MYANMAR SIGN SHAN TONE-5 ("￼ႉ")', U&'Dr. Hala Tufice \FFFC\1089 Pharco Tufice', 'char'),
  ('U+FFFC OBJECT REPLACEMENT at the end ("Dr. Zeina X￼")', U&'Dr. Zeina Tufice\FFFC', 'char'),
  ('U+FFFD REPLACEMENT CHARACTER', U&'Dr. Zeina Tufice\FFFD', 'char'),
  ('Cyrillic а in "Dr. Rаna"', U&'Dr. R\0430na Tufice', 'script'),
  ('Greek ο in a Latin word', U&'Dr. N\03BFur Tufice', 'script'),
  ('"Dr. Hala X - Pharco X" (0037''s separator: a spaced hyphen, fourth version: its own reason)', 'Dr. Hala Tufice - Pharco Tufice', 'dash'),
  ('a digit ("Dr. Rana 2")', 'Dr. Rana 2', 'digit'),
  ('an Arabic-Indic zero standing alone', 'د. هالة ٠ فاركو', 'digit'),
  ('U+02D1 MODIFIER LETTER HALF TRIANGULAR COLON (Common script)', U&'Dr. Hala \02D1 Pharco', 'letter'),
  ('U+01C3 click letter ǃ (Restricted)', U&'Dr. Hala\01C3', 'unsupported'),
  ('a combining mark with no letter (third version: a mark NFKC cannot join to a letter)', U&'Dr. Hala \0307 Pharco', 'accent'),
  ('four marks on one letter', U&'Dr. Hab\0301\0301\0301\0301', 'accent'),
  ('four vowel marks on one Arabic letter (fourth version: removed)', U&'د. هالة الشا\064E\064F\0650\0652مي', ''),
  -- 0039 (verifier rounds atk-bypass-r1 / atk-unicode-r1 / atk-legit-r1)
  ('the same mark twice on one letter ("é́", it can draw over itself)', U&'Dr. Hal\00E9\0301 Tufice', 'accent'),
  ('the same mark twice, decomposed', U&'Dr. Hale\0301\0301 Tufice', 'accent'),
  ('a shadda twice on one Arabic letter (fourth version: removed)', U&'د. هالة الشا\0651\0651مي', ''),
  ('two different marks are fine ("ệ")', U&'Dr. Ne\0323\0302 Tufice', ''),
  ('African noon ࢽ (draws as ن before a letter; TR39 gives it the skeleton of ى): not an Arabic-block letter', U&'\08BD\0628\064A\0644', 'unsupported'),
  ('African qaf ࢼ (draws as ف before a letter; TR39: ڡ)', U&'\0639\08BC\062A', 'unsupported'),
  ('a whole word in Chinese', '张伟 (Zhang Wei)', 'letter'),
  ('Hebrew', 'דוד כהן', 'letter'),
  ('Armenian', 'Արամ Խաչատրյան', 'letter'),
  ('the em dash is a hyphen in a name (third version: every \p{Pd})', 'Anne—Marie Tufice', ''),
  ('a quotation mark', 'Ahmed "Mido" Ali', 'char'),
  ('the Catalan middle dot (it is the picker separator)', 'Gal·la Puig', 'char'),
  ('a fullwidth dollar is named as typed', U&'Ahmed \FE69x', 'char'),
  ('a space before a dot ("د . أحمد")', 'د . أحمد علي', 'word'),
  ('a space before a comma', 'Ahmed Ali , PhD', 'word'),
  ('a hyphen standing alone (fourth version: its own reason, the message suggests parentheses)', 'Hala Ali - Pharco', 'dash'),
  ('a slash standing alone (fourth version: joined to the word before it)', 'د / هيثم', ''),
  ('a slash standing alone at the start', '/ هيثم', 'word'),
  -- third version: a whole Greek or Cyrillic word that reads as a Latin one is allowed — it has the Latin word's skeleton (ӏ U+04CF too:
  -- tools/names/pixel-twins.txt), so it is that name's twin (atk-legit-r2: «Μαρία», «Άννα Βίσση», «Вера Кох» were refused by 0039_names_rule_2)
  ('a Cyrillic word that reads as a Latin one, next to Latin words ("Dr. Рара")', U&'Dr. \0420\0430\0440\0430 Tufice', ''),
  ('"Dr. Ѕаӏіһ" (its skeleton is "dr. salih")', U&'Dr. \0405\0430\04CF\0456\04BB', ''),
  ('a Greek name that reads as Latin ("Αννα")', 'Αννα', ''),
  -- third version (atk-unicode-r2, atk-bypass-r2): a mark NFKC cannot join to its letter is refused — it can draw on a stroke the
  -- letter already has, or on a dot it already has, and look like nothing while the skeleton differs
  ('e + U+0335 short stroke overlay ("Ahme̵d")', U&'Ahme\0335d Tufice', 'accent'),
  ('N + U+0335 ("N̵ada")', U&'N\0335ada Tufice', 'accent'),
  ('W + U+0335 ("W̵ael")', U&'W\0335ael Tufice', 'accent'),
  ('Greek Ν + U+0335', U&'\039D\0335\03B9\03BA\03B7', 'accent'),
  ('Greek capital Τ + macron ("Τ̄ΑΣΟΣ")', U&'\03A4\0304\0391\03A3\039F\03A3', 'accent'),
  ('Greek capital Ζ + macron', U&'\0396\0304\03B7\03BD\03C9', 'accent'),
  ('Greek capital Π + macron', U&'\03A0\0304\03B1\03CD\03BB\03BF\03C2', 'accent'),
  ('Greek capital Ε + macron', U&'\0395\0304\03BB\03AD\03BD\03B7', 'accent'),
  ('Greek capital Ρ + macron', U&'\03A1\0304\03AD\03B1', 'accent'),
  ('Greek capital Ζ + perispomeni', U&'\0396\0342\03B7\03BD\03C9', 'accent'),
  ('Greek capital Μ + acute', U&'\039C\0301\03B1\03C1\03AF\03B1', 'accent'),
  ('i + U+0307 dot above ("Sali̇h", TR39 §5.4)', U&'Sali\0307h Tufice', 'accent'),
  ('dotless ı + U+0307 dot above ("Salı̇h")', U&'Mohamed Al\0131\0307', 'accent'),
  ('j + U+0307', U&'j\0307ana Tufice', 'accent'),
  ('two overlay marks, one order', U&'Ho\0335\0338da', 'accent'),
  ('two overlay marks, the other order', U&'Ho\0338\0335da', 'accent'),
  ('ų + diaeresis + macron', U&'R\0173\0308\0304ta', 'accent'),
  ('a Yoruba tone mark on a letter with a dot below (no single character: refused, said plainly)', U&'Ade\1ECD\0301la', 'accent'),
  ('a hamza mark on a letter it does not join ("ب" + U+0654)', U&'ب\0654ب', 'accent'),
  ('Cyrillic Ext-D combining letter U+1E08F (no font draws it)', U&'Ahmed X\+01E08F', 'accent'),
  ('Latin capital turned H U+A78D (Latin Extended-D: Cyrillic Ч to the pixel)', U&'\A78DEXOB', 'unsupported'),
  ('Latin Extended-G U+1DF00 (no font draws it)', U&'Ahmed \+01DF00', 'unsupported'),
  ('Latin Extended-G U+1DF1E', U&'Ahmed X\+01DF1E', 'unsupported'),
  ('Latin Extended-E ꭦ', U&'Ahmed X\AB66', 'unsupported'),
  ('Cyrillic Extended-B ꙿ', U&'Ahmed X\A67F', 'unsupported'),
  ('ʿ U+02BF (ayn of transliteration) is written ’ like ʾ (fourth version)', 'Saʿīd Ḥasan', ''),
  -- fourth version (atk-unicode-r3): a mark above an undotted Arabic letter drew as its dot — the mark is removed, never stored
  ('ح + sukun ("حْالد" drew as "خالد")', 'حْالد', ''), ('ر + sukun ("رْياد" / "زياد")', 'رْياد', ''), ('د + sukun ("دْكي" / "ذكي")', 'دْكي', ''),
  ('ع + sukun ("عْادة" / "غادة")', 'عْادة', ''), ('dotless noon + sukun ("حسںْ" / "حسن")', 'حسںْ', ''),
  ('Quranic small high marks and small waw ("إِنَّهُۥ")', 'إِنَّهُۥ', ''), ('a hamza mark on a letter it does not join, after a vowel mark', U&'ب\064E\0654ب', 'accent'),
  -- fourth version (atk-legit-r3): letters of the four alphabets not taken yet say so; tone marks on Yoruba letters stay refused
  ('Hausa Ɗ Ƙ', 'Ɗanjuma Ƙasim', 'unsupported'), ('Akan Ɔ', 'Ɔpɔku Mensah', 'unsupported'), ('Akan Ɛ', 'Ɛfua Sutherland', 'unsupported'),
  ('Yoruba tone marks', 'Ọláfẹ́mi Adébáyọ̀', 'accent'), ('a spaced en dash', 'Hala Ali – Head of QA', 'dash'),
  -- fourth version (render_scan.py): Arabic letters of the languages Drugbox serves (Arabic, Persian, Urdu, Kurdish, Maghrebi) only —
  -- the others draw like a common letter with a small mark for its dot (ݕ / ي, ڂ / خ, ې / ب, ݵ / ݺ)
  ('ݕ (Arabic Supplement)', U&'\0628\0755\0644', 'unsupported'), ('ڂ (hah with two dots above)', U&'\0682\0627\0644\062F', 'unsupported'),
  ('ې (Uyghur yeh)', U&'\06D0\0627\0645', 'unsupported'), ('ؠ (Kashmiri yeh)', U&'\0639\0644\0620', 'unsupported'),
  ('Persian, Urdu, Kurdish and Maghrebi letters are taken', 'پرویز گلشیری ڈاکٹر عبدالقدیر ڤيڨا ڕۆژ ڵێ ئەو ڧاطمة', ''),
  -- fifth version (v-real-r1): the Maghrebi gaf ڭ and feh ڢ are taken; Pashto, Sindhi and Uyghur letters stay 'unsupported'
  ('Maghrebi gaf ڭ ("ڭمال العلوي")', 'ڭمال العلوي', ''), ('Maghrebi feh ڢ', 'ڢاطمة الزهراء', ''),
  ('Pashto ځ', 'ځلمی خلیلزاد', 'unsupported'), ('Pashto ښ', 'ښکلا احمدي', 'unsupported'), ('Uyghur ۇ', 'ئۇيغۇر ئەخمەت', 'unsupported'), ('Sindhi ڄ', 'ڄام ڻانو', 'unsupported'),
  ('a Persian name with a zero-width non-joiner ("علی رضا" typed with U+200C)', U&'\0639\0644\06CC\200C\0631\0636\0627 \0645\062D\0645\062F\06CC\200C\0646\0698\0627\062F', ''),
  -- fifth version (v-spoof-r1): brackets the bidi algorithm can reorder. "(MBA) Ahmed Ali" drew EXACTLY as "Ahmed Ali (MBA)" in the
  -- Arabic interface, "(صيدلي) أحمد علي" as "أحمد علي (صيدلي)" in the English one, "Ali (علي) محمد" as "Ali محمد (علي)", "منى (Ali)
  -- Mona" as "منى Mona (Ali)" (tools/names/render_scan.py --part names): refused — one pair, after a letter, around letters of one
  -- direction, between letters of one direction
  ('a bracket before the first letter ("(MBA) Ahmed Ali")', '(MBA) Ahmed Ali', 'bracket'), ('the same in Arabic ("(صيدلي) أحمد علي")', '(صيدلي) أحمد علي', 'bracket'),
  ('an Arabic word in brackets between a Latin and an Arabic word', 'Ali (علي) محمد', 'bracket'), ('a Latin word in brackets between an Arabic and a Latin word', 'منى (Ali) Mona', 'bracket'),
  ('a bracket not closed', 'Ahmed Ali (MBA', 'bracket'), ('a bracket closed but not opened', 'Ahmed) Ali', 'bracket'), ('two pairs of brackets', 'Hala Ali (Head of QA) (Pharco)', 'bracket'),
  ('brackets around letters of both directions', 'Ali (Head, فاركو)', 'bracket'), ('a name in brackets only', '(Ahmed)', 'bracket'),
  ('the bracketed part after the name is fine', 'Ahmed Ali (MBA)', ''), ('…in Arabic', 'أحمد علي (صيدلي)', ''), ('…an Arabic name after a Latin one', 'Ali محمد (علي)', ''),
  ('a nickname in the middle, one direction', 'Ahmed (Mido) Ali', ''), ('a transliteration in brackets', 'Ziad (زياد)', ''), ('an Arabic nickname between Latin words', 'Mona (منى) Ali', ''),
  -- sixth version (round 5): a space just inside a bracket is tidied away, not refused; the round-5 look-alikes are ALLOWED (they are
  -- twins of the real names — same skeleton —, never refused for looking alike)
  ('a space inside the brackets ("Ahmed Ali ( MBA )")', 'Ahmed Ali ( MBA )', ''), ('…in Arabic', 'أحمد علي ( صيدلي )', ''), ('…a nickname in the middle', 'Ahmed ( Mido ) Ali', ''),
  ('…still a bracket before the first letter', '( MBA ) Ahmed Ali', 'bracket'), ('…empty brackets are no word', 'Ahmed Ali ( )', 'word'),
  ('the Turkish capital İ for i ("Alİ Kaya")', 'Alİ Kaya', ''), ('the dotless ı for i', 'Alı Kaya', ''), ('a space after a letter that never joins ("عبد الله أحمد")', 'عبد الله أحمد', ''),
  -- seventh version (round 6, v-spoof6-r1): a mark drawn beside its letter and the apostrophe it reads as — both spellings ALLOWED (twins)
  ('Slovak ľ ("Paľo Kováč")', 'Paľo Kováč', ''), ('…its look-alike l + ’ ("Pal’o Kováč")', 'Pal’o Kováč', ''), ('Czech ť ("Šťastný")', 'Šťastný', ''), ('…"Št’astný"', 'Št’astný', ''),
  ('Greek capital with tonos ("Άννα Νίκου")', 'Άννα Νίκου', ''), ('…"’Αννα Νίκου"', '’Αννα Νίκου', ''), ('"Marie ďAlessandro"', 'Marie ďAlessandro', ''), ('Vietnamese ơ ư ("Phương Hồ")', 'Phương Hồ', ''),
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
  ('Nguyễn Văn An'), ('Łukasz Wójcik'), ('Søren Ærø'), ('Dr. Nermeen Abou-Zeid'),
  -- refused by 0038, allowed by 0039 (atk-legit-r1: Egyptian titles with "/", Latin titles on Greek/Cyrillic names, pasted
  -- hyphens and apostrophes, the Arabic comma)
  ('د/ هيثم دويدار'), ('م/ محمود عبد الرحمن'), ('ك/ أحمد سامي'), ('أ.د/ محمد السيد'), ('الدكتور/ أحمد'), ('Dr/ Ahmed'), ('Ph/ Mohamed Hassan'), ('Pharm/ Ahmed'),
  ('Dr. Νίκος Παπαδόπουλος'), ('Dr. Мария Иванова'), ('Мария Иванова (Maria Ivanova)'), ('Вера Иванова'), ('Μαρία Κωνσταντίνου'), ('Νίκος Παπαδόπουλος (Nikos Papadopoulos)'), ('Dr. Иван'),
  (U&'Anne\2011Marie Dubois'), (U&'Dr. Ahmed El\2013Sayed'), (U&'Ahmed El\2212Sayed'), ('د. أحمد علي، صيدلي'), (U&'\041C\0430\0440\02BC\044F\043D\0430 \0413\0440\0438\0433\043E\0440\02BC\0454\0432\0430'),
  ('O‘Brien Kelly'), ('O´Brien Kelly'), ('O`Brien'), ('ʻAbd al-ʻAziz'), ('Mary-Jane O''Neil-Smith'), ('Ahmed Ali, M.B.B.Ch., Ph.D.'), ('مصطفىٰ كامل'), ('ريم السيد (صيدلانية)'),
  ('Ahmed Ali (أحمد علي)'), ('پرویز گلشیری'), ('Ἀλέξανδρος Παπάς'), ('Đặng Thị Ngọc Hân'),
  -- refused by 0039_names_rule_2, allowed by the third version (atk-legit-r2): Greek and Cyrillic names that read as Latin, a title
  -- glued to a name in another alphabet, the em dash
  ('Μαρία'), ('Νίκη'), ('Ειρήνη'), ('Μαρίνα Μάρκου'), ('Άννα Βίσση'), ('Dr. Νίκη Βίσση'), ('ΑΝΝΑ ΚΑΡΑΤΖΑ'), ('Вера Кох'), ('ОКСАНА КОРОТКОВА'), ('АННА АХМАТОВА'),
  ('ЧЕХОВ'), ('Dr.أحمد علي'), ('د.Ahmed Ali'), ('Jean—Paul Sartre'), ('Mo''men Abd El-Raouf'), ('Mª José García'), ('Ahmed ‘Mido’ Ali'), ('Fāʾiza Ḥusayn'),
  ('İsmail Ñúñez'), ('Məmmədov Əli'), ('Nguyễn Thị Ánh'), ('مُحَمَّد عَبْدُ الرَّحْمٰن'), ('الدكتورة/ هالة السعيد'), ('Ґанна Ґонта')) x(s);
insert into r(name, ok, err) select 'stored as typed: ' || x.s, public.person_name_norm(x.s) = x.want, public.person_name_norm(x.s) from (values
  ('هـالة', 'هالة'), (U&'\FF24\FF52. Hala', 'Dr. Hala'), ('  José   Müller ', 'José Müller'), (U&'Jose\0301', 'José'),
  -- 0039: look-alikes of the punctuation a name holds are written as it; the apostrophe is stored as ’ (as the app shows it)
  ('O''Brien', 'O’Brien'), (U&'Anne\2011Marie', 'Anne-Marie'), (U&'El\2013Sayed', 'El-Sayed'), ('O´Brien', 'O’Brien'), ('O‘Brien', 'O’Brien'),
  (U&'\041C\0430\0440\02BC\044F\043D\0430', 'Мар’яна'), (U&'\FD3E\0635\064A\062F\0644\064A\FD3F', '(صيدلي)'), (U&'Ahmed\FF0FAli', 'Ahmed/Ali'),
  -- fourth version: Arabic diacritics removed (a mark over an undotted letter can no longer draw as its dot), a spaced slash joined to
  -- the word before it, ʿ written ’, a hamza that NFKC can join once a Quranic mark between them is gone
  ('حْالد', 'حالد'), ('رْياد', 'رياد'), ('دْكي', 'دكي'), ('عْادة', 'عادة'), ('حسںْ', 'حسں'), ('مُحَمَّد عَبْدُ الرَّحْمٰن', 'محمد عبد الرحمن'), ('د. نرمين أبو زيدٍ', 'د. نرمين أبو زيد'),
  ('إِنَّهُۥ', 'إنه'), (U&'\0627\06D6\0654', 'أ'), ('ب َ ب', 'ب ب'), ('د / محمد علي', 'د/ محمد علي'), ('ا.د / سامي فهمي', 'ا.د/ سامي فهمي'), ('د/ سامي / صيدلي', 'د/ سامي/ صيدلي'),
  ('Saʿīd Ḥasan', 'Sa’īd Ḥasan'), ('ʿAbd al-ʿAzīz', '’Abd al-’Azīz'),
  -- fifth version: a zero-width non-joiner after an Arabic letter that joins the next is a space (the letters keep their shapes);
  -- after one that never joins (د) it changes nothing and is removed
  (U&'\0639\0644\06CC\200C\0631\0636\0627 \0645\062D\0645\062F\06CC\200C\0646\0698\0627\062F', 'علی رضا محمدی نژاد'), (U&'\0639\0628\062F\200C\0627\0644\0644\0647', 'عبدالله'),
  (U&'Ah\200Cmed', 'Ahmed'),
  -- sixth version: a space just inside a bracket is tidied away (it was refused as a word: "(" alone)
  ('Ahmed Ali ( MBA )', 'Ahmed Ali (MBA)'), ('Ahmed Ali (MBA )', 'Ahmed Ali (MBA)'), ('أحمد علي ( صيدلي )', 'أحمد علي (صيدلي)'), ('Ahmed ( Mido ) Ali', 'Ahmed (Mido) Ali'),
  ('Alİ Kaya', 'Alİ Kaya'), ('عبد الله أحمد', 'عبد الله أحمد')) x(s, want);
-- the refusal names what the person typed (not what normalising made of it), the word to fix, and the accepted alphabets
insert into r(name, ok, err) select 'message: ' || x.s, public.person_name_message(x.s, public.person_name_problem(public.person_name_norm(x.s))) = x.want,
       public.person_name_message(x.s, public.person_name_problem(public.person_name_norm(x.s))) from (values
  -- fourth version: what a message quotes is isolated (U+2068 … U+2069) so the Arabic sentence keeps its order (atk-legit-r3)
  (U&'Ahmed \FE69x', U&'A name can only have letters, spaces and . - '' ( ) , / ، — remove “\2068﹩\2069” (\2068U+FE69\2069)'),
  ('Anne★Marie', U&'A name can only have letters, spaces and . - '' ( ) , / ، — remove “\2068★\2069” (\2068U+2605\2069)'),
  ('张伟 (Zhang Wei)', U&'Write a name in Latin, Arabic, Greek or Cyrillic letters — “\2068张\2069” (\2068U+5F20\2069) is not one of them'),
  ('د . أحمد علي', U&'“\2068.\2069” is not a word — join it to the word next to it (remove the space)'),
  (U&'Dr. R\0430na', U&'Write each word of a name in one alphabet — “\2068R\0430na\2069” mixes alphabets'),
  (U&'Ahme\0335d', U&'Remove the mark added to “\2068e\0335\2069” (\2068U+0335\2069) — Drugbox accepts an accented letter typed as one character, such as é, ü or ñ'),
  (U&'Mohamed Al\0131\0307', U&'Remove the mark added to “\2068\0131\0307\2069” (\2068U+0307\2069) — Drugbox accepts an accented letter typed as one character, such as é, ü or ñ'),
  (U&'Ahmed X\+01E08F', U&'Remove the mark added to “\2068X\+01E08F\2069” (\2068U+1E08F\2069) — Drugbox accepts an accented letter typed as one character, such as é, ü or ñ'),
  (U&'Dr.R\0430na', U&'Write each word of a name in one alphabet — “\2068R\0430na\2069” mixes alphabets'),
  (U&'Dr. Zeina X\FFFC', U&'A name can only have letters, spaces and . - '' ( ) , / ، — remove “\2068\FFFC\2069” (\2068U+FFFC\2069)'),
  ('Dr. Rana 2', 'A name cannot contain numbers'),
  ('Ahmed Ali - MBA', U&'Put what follows the name in parentheses — write “\2068Ahmed Ali (MBA)\2069”'),
  ('Hala Ali – Head of QA', U&'Put what follows the name in parentheses — write “\2068Hala Ali (Head of QA)\2069”'),
  ('Ɗanjuma Ƙasim', U&'The letter “\2068Ɗ\2069” (\2068U+018A\2069) is not supported in names yet'),
  ('Ɔpɔku Mensah', U&'The letter “\2068Ɔ\2069” (\2068U+0186\2069) is not supported in names yet'),
  (U&'\A78DEXOB', U&'The letter “\2068\A78D\2069” (\2068U+A78D\2069) is not supported in names yet'),
  -- fifth version: a suggestion the rule accepts when there are several dashes (v-real-r1), the bracket moved after the name
  ('Hala Ali – Head of QA – Pharco', U&'Put what follows the name in parentheses — write “\2068Hala Ali (Head of QA, Pharco)\2069”'),
  ('(MBA) Ahmed Ali', U&'Put the part in brackets after the name — write “\2068Ahmed Ali (MBA)\2069”'),
  ('(صيدلي) أحمد علي', U&'Put the part in brackets after the name — write “\2068أحمد علي (صيدلي)\2069”'),
  ('Ali (علي) محمد', U&'Put the part in brackets after the name — write “\2068Ali محمد (علي)\2069”'),
  ('Hala Ali (Head of QA) (Pharco)', U&'Put the part in brackets after the name — write “\2068Hala Ali (Head of QA, Pharco)\2069”'),
  ('Ahmed Ali (MBA', U&'Put the part in brackets after the name — write “\2068Ahmed Ali (MBA)\2069”'),
  ('Ali (Head, فاركو)', U&'What is in brackets is written in one direction — Arabic letters, or Latin, Greek and Cyrillic ones — “\2068(Head, فاركو)\2069” mixes them')) x(s, want);
-- fifth version: every suggestion a message gives ('dash', 'bracket') is a name the rule accepts, for every string the verifiers used
-- (a name refused for its brackets may also break a rule checked after them — 'mark', 'script' —, which the suggestion keeps)
insert into r(name, ok, err) select 'every suggested name is accepted (''dash'' and ''bracket'', ' || count(*) || ' strings)', count(*) filter (where sp not in ('', 'mark', 'script')) = 0,
       string_agg(s || ' → ' || sug || ' (' || sp || ')', ' | ') filter (where sp not in ('', 'mark', 'script'))
  from (select s, sug, public.person_name_problem(public.person_name_norm(sug)) as sp
          from (select s, substring(msg from U&'“\2068(.*)\2069”$') as sug from vgot where problem in ('dash', 'bracket') and msg !~ '^What is in brackets') a) b;
-- twins by skeleton: names that look the same have the same key; names that differ do not
insert into r(name, ok, err) select 'same skeleton: ' || x.a || ' / ' || x.b, public.person_name_key(x.a) = public.person_name_key(x.b), public.person_name_key(x.a) || ' / ' || public.person_name_key(x.b) from (values
  ('Dr. Rana Tufice', U&'Dr. R\0430na Tufice'), ('Ilya', 'llya'), ('O''Brien', 'O’Brien'), ('هالة', 'هالَة'), ('د. هالة الشامي', 'د. هالَة الشّامي'),
  ('Dr. Nermeen Tufece', 'DR. NERMEEN TUFECE'), ('Dr. Islam Tufice', 'Dr. lslam Tufice'), ('Dr. Zeina Tufice', U&'Dr. Zeina Tufice\200B'), ('Dr. Zeina Tufice', U&'Dr. Zeina Tufice\+01D173'), ('Dr. Zeina Tufice', U&'Dr. Zeina Tufice\FFFC'),
  ('Paul', U&'\0420aul'), ('Rana', U&'R\0430na'), ('Omar', U&'\039Fmar'),
  -- 0039: a whole word in another alphabet that copies a Latin word; Arabic letters that draw the same before another letter
  -- (TR39 maps them: a qaf with one dot / feh, Farsi yeh / yeh / alef maksura, keheh / kaf, heh goal / heh, teh marbuta goal)
  ('Dr. Papa Tufice', U&'Dr. \0420\0430\0440\0430 Tufice'), ('فاطمة', 'ڧاطمة'), ('علي', 'على'), ('علي', 'علی'),
  ('كريم', 'کریم'), ('هالة', 'ہالۃ'), ('Anne-Marie', U&'Anne\2011Marie'), ('O’Brien', 'O´Brien'),
  -- third version: letters that draw alike while TR39 keys them apart (tools/names/pixel-twins.txt), a whole Cyrillic name that
  -- reads as Latin, the em dash
  ('Dr. Salih', U&'Dr. \0405\0430\04CF\0456\04BB'), ('Salih', U&'\0405\0430\04C0\0456\04BB'), ('Ahmed Ali', U&'Ahmed A\04CFi'),
  ('Jean-Paul', 'Jean—Paul'), ('Mapía', 'Μαρία'),
  -- fourth version: a name typed with Arabic diacritics is the same name as without them (and is stored without them)
  ('حالد', 'حْالد'), ('محمد عبد الرحمن', 'مُحَمَّد عَبْدُ الرَّحْمٰن'), ('د/ محمد علي', 'د / محمد علي'), ('Sa’īd', 'Saʿīd'), ('Sa’īd', 'Saʾīd'),
  -- fourth version: what tools/names/render_scan.py found drawn alike (every letter against every letter, 14-16 px): accents at the same
  -- place (é / è, Ŝ / Š, ἀ / ἁ, ş / ș / ę), two stacked accents and one (Ẵ / Ǎ), an accent above i or j in place of its dot (í / i),
  -- ئ / ت before a letter, г / ґ, ӏ / l / ا
  ('José Tufice', 'Josè Tufice'), ('Šara', 'Ŝara'), ('Hélène', 'Hêlène'), ('Müller', 'Mûller'), ('ἀλέξανδρος', 'ἁλέξανδρος'), ('Ştefan', 'Ștefan'),
  ('Ẵnh', 'Ǎnh'), ('Alí Tufice', 'Ali Tufice'), ('Ĵan', 'Jan'), ('تامر', 'ئامر'), ('Анна ганна', 'Анна ґанна'), ('Ahmed Ali', U&'Ahmed A\0627i'),
  -- fifth version: what the scan found with the app's font stacks at every weight (v-spoof-r1): bold initial ث / ئ (so ت / ث / ئ are one
  -- skeleton), double acute / circumflex + acute / inverted breve, the marks below (ring, dot, macron, circumflex, tilde, breve), ģ / ġ
  -- (g draws its cedilla above), и / н, к / ԟ, г / ғ, d / đ
  ('ثروت عادل', 'ئروت عادل'), ('ثامر', 'تامر'), ('Szőke Anna', 'Szổke Anna'), ('Szűcs', 'Szȗcs'), ('ḁla', 'ạla'), ('Ḏina', 'Ḓina'), ('Ṯariq', 'Ṱariq'), ('Ṯariq', 'Ţariq'),
  ('Ġorġ', 'Ģorģ'), ('Ģirts', 'Ǵirts'), ('Анна иванова', 'Анна нванова'), ('Mađar', 'Madar'), ('Ӱлан', 'Ӳлан'),
  -- fifth version: a zero-width non-joiner is a space; a letter of another alphabet is U+FFFD (the database and the app decompose the
  -- letters Unicode 16 added differently)
  (U&'\0639\0644\06CC\200C\0631\0636\0627', 'علی رضا'), (U&'\+0105C9abc', U&'\+011383abc'), (U&'\+016D68 Ahmed', U&'\+0105E4 Ahmed'),
  -- sixth version (round 5; the skeleton OVER-merges — twins cost a line of context, a look-alike with its own skeleton can be sent the
  -- message): the Turkish İ and ı are i and every key is case folded; spaces are ignored («عبد الله» = «عبدالله»); every pair
  -- tools/names/render_scan.py draws within ONE Arabic dot shares a skeleton (i / l / İ / î / Ī, the dotted and undotted Arabic letters
  -- that measure under a dot in some font and weight, an accent that draws within a dot of nothing on a bold capital); the first mark
  -- above every letter that shares i's key is dropped (أ / ا)
  ('Alİ Kaya', 'Ali Kaya'), ('Alı Kaya', 'Ali Kaya'), ('ALİ KAYA', 'Ali Kaya'), ('İsmail Öztürk', 'Ismail Ozturk'), ('Alî', 'AlĪ'), ('Ali', 'All'), ('Ibrahim', 'ibrahim'), ('ILYA', 'ilya'),
  ('عبد الله أحمد', 'عبدالله أحمد'), ('أبو بكر', 'أبوبكر'), ('نور الدين', 'نورالدين'), ('عبد الرحمن محمد', 'عبدالرحمن محمد'), ('ابن سينا', 'ابنسينا'), ('Ali Kaya', 'AliKaya'),
  (U&'\0639\0644\06CC\200C\0631\0636\0627', 'علیرضا'), ('Straße', 'Strasse'), ('Ahmed Ali ( MBA )', 'Ahmed Ali (MBA)'),
  ('أبو', 'ابو'), ('أحمد علي', 'احمد علي'), ('آمال', 'أمال'), ('حْالد', 'خالد'), ('رْياد', 'زياد'), ('دْكي', 'ذكي'), ('عْادة', 'غادة'), ('حسںْ', 'حسن'),
  ('تامر', 'بامر'), ('ح', 'خ'), ('ر', 'ز'), ('ص', 'ض'), ('ب', 'ن'), ('ي', 'ى'), ('ه', 'ة'), ('ف', 'ق'), ('هبة', 'هنة'),
  ('José', 'Jose'), ('Müller', 'Muller'), ('Ştefan', 'Stefan'), ('Alena', 'Alёna'), ('Ḣana', 'Hana'), ('Ḥana', 'Hana'), ('Ńada', 'Nada'),
  -- seventh version (round 6, v-spoof6-r1): the skeleton drops the apostrophe, and a letter whose mark the fonts draw BESIDE it (within
  -- the rows the letter covers: tools/names/render_scan.py --part beside) has its base letter's skeleton — Slovak / Czech ľ ť ď Ľ (the
  -- caron drawn as ’ after the letter), Greek capitals with the tonos or a breathing at their upper left, Vietnamese ơ ư (the horn)
  ('Paľo Kováč', 'Pal’o Kováč'), ('Paľo Kováč', 'Palo Kováč'), ('Peter Kráľ', 'Peter Král’'), ('Šťastný', 'Št’astný'), ('Ľudmila', 'L’udmila'), ('Marie d’Alessandro', 'Marie ďAlessandro'),
  ('ďurica', 'd’urica'), ('Άννα Νίκου', '’Αννα Νίκου'), ('Όλγα', '’Ολγα'), ('Ἀλέξανδρος', '’Αλέξανδρος'), ('Ή', '’Η'), ('Ώ', '’Ω'), ('Phương', 'Phu’o’ng'), ('Ơn', 'O’n'),
  ('O’Brien', 'OBrien'), ('Mo’men', 'Momen'), ('d’Alessandro', 'dAlessandro')) x(a, b);
insert into r(name, ok, err) select 'different skeleton: ' || x.a || ' / ' || x.b, public.person_name_key(x.a) <> public.person_name_key(x.b), public.person_name_key(x.a) from (values
  ('Dr. Zeina Tufice', 'Dr. Zeina Tufica'), ('Hala', 'Hana'),
  -- sixth version: the pairs below were different names until the fifth version (the undotted «حالد» and «خالد», «José» and «Jose»…);
  -- they draw within a dot of each other in some font and weight, so they are twins now (above). These stay different names:
  -- seventh version: an apostrophe is no letter — these stay different names
  ('Paľo Kováč', 'Pavo Kováč'), ('O’Brien', 'O’Brian'), ('Άννα', 'Άνα'),
  ('Hadia', 'Nadia'), ('Mona', 'Nona'), ('Omar', 'Amar'), ('Nour', 'Noor'), ('Dr. Ahmed Ali', 'Dr. Ahmad Ali'), ('Ali Kaya', 'Ali Kaye'), ('Mohamed', 'Mohammed'),
  ('سمير', 'شمير'), ('حسن', 'حسين'), ('محمد', 'احمد'), ('أحمد', 'إحمد'), ('س', 'ش'), ('ا', 'ل'), ('د', 'ر'), ('ع', 'ف'),
  -- fifth version: the words in another order are another name (the brackets that drew them alike are refused)
  ('Ahmed Ali (MBA)', 'Ahmed (MBA) Ali'), ('أحمد علي (صيدلي)', 'أحمد (صيدلي) علي'), ('Ali محمد (علي)', 'Ali (علي) محمد')) x(a, b);
insert into r(name, ok, err) select 'stored without the mark that drew as a dot: ' || x.a || ' → ' || public.person_name_norm(x.a) || ', not ' || x.b,
       public.person_name_norm(x.a) <> x.b and public.person_name_norm(x.a) !~ ('[' || U&'!064B-!0652!0670' uescape '!' || ']') and strpos(public.person_name_norm(x.a), x.u) > 0,
       public.person_name_norm(x.a) from (values
  ('حْالد', 'خالد', 'ح'), ('رْياد', 'زياد', 'ر'), ('دْكي', 'ذكي', 'د'), ('عْادة', 'غادة', 'ع'), ('حسںْ', 'حسن', 'ں')) x(a, b, u);
\o
\pset tuples_only on
select (case when ok then 'PASS  ' else 'FAIL  ' end) || name || coalesce('   [' || err || ']', '') from r order by n;
select 'TOTAL ' || count(*) filter (where ok) || ' / ' || count(*) from r;
\set ON_ERROR_STOP on
do $$ declare f int; t int; begin select count(*) filter (where not ok), count(*) into f, t from r;
  if t = 0 or f > 0 then raise exception '% of % check(s) FAILED', f, t; end if; end $$;
rollback;
