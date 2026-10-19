-- Training (0062): the catalog and syllabus for everyone, lesson content and quiz questions for learners only (never the answers),
-- progress, the final quiz (all lessons first, pass mark, attempts per hour), certificates and the public verify link, free courses
-- enrolled by the learner, paid courses only by the server after payment (create_order / confirm_payment), a paid enrolment stays,
-- a deactivated course stays open to its learners, Drugbox manages courses, private lesson files. Runs as the real API roles with a
-- JWT, in one transaction that is rolled back; test data carries the "TR " marker. Run on a fresh database (stub + migrations):
-- psql -f supabase/tests/training.rls.sql
-- Harness: every action is a step() and every assertion an ok()/no(); an unexpected error becomes a FAIL with its message (the report
-- is never lost), a negative check passes only with the expected SQLSTATE, and psql exits non-zero when anything failed.
\set QUIET on
\set ON_ERROR_ROLLBACK on
set client_min_messages = warning;
\o /dev/null
begin;
create temp table r (n serial, name text, ok boolean, err text); grant all on r to authenticated, anon; grant all on r_n_seq to authenticated, anon;
create temp table ids (k text primary key, v text); grant all on ids to authenticated, anon;
create function pg_temp.as_user(u text) returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', u, true); perform set_config('request.jwt.claims', json_build_object('sub', u, 'role', 'authenticated')::text, true);
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

-- A Drugbox admin, L learner, O outsider
insert into auth.users (id, email) values ('a3000000-0000-0000-0000-000000000001','tr-a@x'),('a3000000-0000-0000-0000-000000000002','tr-l@x'),
  ('a3000000-0000-0000-0000-000000000003','tr-o@x') on conflict do nothing;
insert into public.profiles (id, name) values ('a3000000-0000-0000-0000-000000000001','TR Admin'),('a3000000-0000-0000-0000-000000000002','TR Learner'),
  ('a3000000-0000-0000-0000-000000000003','TR Outsider') on conflict (id) do update set name = excluded.name;
update public.profiles set role = 'admin' where id = 'a3000000-0000-0000-0000-000000000001';
create function pg_temp.A() returns void language sql as $$ select pg_temp.as_user('a3000000-0000-0000-0000-000000000001') $$;
create function pg_temp.L() returns void language sql as $$ select pg_temp.as_user('a3000000-0000-0000-0000-000000000002') $$;
create function pg_temp.O() returns void language sql as $$ select pg_temp.as_user('a3000000-0000-0000-0000-000000000003') $$;
create function pg_temp.L_id() returns uuid language sql immutable as $$ select 'a3000000-0000-0000-0000-000000000002'::uuid $$;

-- 1. Drugbox publishes courses, lessons and a quiz; nobody else can
select pg_temp.O();
select pg_temp.no('a member cannot add a course', $$insert into public.training_courses (title) values ('TR Fake course')$$, '42501');
select pg_temp.A();
select pg_temp.step('Drugbox adds a free course (2 lessons, 2 questions)', $$with x as (insert into public.training_courses (title, description, topic, hours, instructor, enrolled_count) values ('TR Free GMP', 'GMP basics', 'gmp', 2, 'Dr. TR', 99) returning id) insert into ids select 'f', id::text from x$$);
select pg_temp.ok('the browser''s enrolment count is ignored', $$(select enrolled_count = 0 from public.training_courses where id = pg_temp.id('f'))$$);
select pg_temp.step('… its lessons', $$with x as (insert into public.course_lessons (course_id, position, title, kind, minutes, body, media_path) values
  (pg_temp.id('f'), 1, 'TR Intro', 'video', 12, 'TR secret body 1', 'courses/' || pg_temp.id('f') || '/intro.webm'), (pg_temp.id('f'), 2, 'TR Notes', 'pdf', 8, 'TR secret body 2', null) returning id, position)
  insert into ids select 'l' || position, id::text from x$$);
select pg_temp.no('a lesson file must sit in its own course''s folder', $$insert into public.course_lessons (course_id, position, title, media_path) values (pg_temp.id('f'), 3, 'TR Bad', 'courses/1/../x.pdf')$$, '23514');
select pg_temp.step('… its quiz', $$insert into public.course_questions (course_id, position, prompt, options, answer) values
  (pg_temp.id('f'), 1, 'TR What does GMP stand for?', '{Good Manufacturing Practice,Great Medicine Plan}', 0), (pg_temp.id('f'), 2, 'TR Who signs the batch?', '{The driver,The QP}', 1)$$);
select pg_temp.step('Drugbox adds a paid course (EGP 1,000 before VAT)', $$with x as (insert into public.training_courses (title, price_egp, hours) values ('TR Paid Stability', 1000, 5) returning id) insert into ids select 'p', id::text from x$$);
select pg_temp.step('… with one lesson', $$insert into public.course_lessons (course_id, position, title, body) values (pg_temp.id('p'), 1, 'TR Paid lesson', 'TR paid body')$$);
select pg_temp.ok('Drugbox reads the quiz with its answers', $$(select array_agg(answer order by position) = '{0,1}' from public.course_questions_admin(pg_temp.id('f')))$$);
select pg_temp.O();
select pg_temp.no('a member cannot add a lesson', $$insert into public.course_lessons (course_id, position, title) values (pg_temp.id('f'), 9, 'TR Fake lesson')$$, '42501');
select pg_temp.no('a member cannot read the quiz answers', $$select * from public.course_questions_admin(pg_temp.id('f'))$$, '42501');
select pg_temp.step('a member tries to change a price', $$update public.training_courses set price_egp = 1 where id = pg_temp.id('p')$$);
select pg_temp.as_server();
select pg_temp.ok('… the price is unchanged; the course is sold as course_<id> at its price', $$(select price_egp = 1000 from public.training_courses where id = pg_temp.id('p'))
  and (select amount_egp = 1000 and kind = 'course' and active from public.payment_products where code = 'course_' || pg_temp.id('p'))$$);
select pg_temp.ok('a free course is not sold', $$not exists (select 1 from public.payment_products where code = 'course_' || pg_temp.id('f'))$$);

-- 2. the catalog and syllabus for everyone; content, files and questions for learners only
select pg_temp.as_anon();
select pg_temp.ok('anon sees the course and its syllabus', $$exists (select 1 from public.training_courses where id = pg_temp.id('f')) and (select count(*) = 2 from public.course_lessons where course_id = pg_temp.id('f'))$$);
select pg_temp.no('anon cannot read lesson bodies', $$select body from public.course_lessons where course_id = pg_temp.id('f')$$, '42501');
select pg_temp.no('anon cannot open a lesson', $$select public.lesson_content(pg_temp.id('l1'))$$, '42501');
select pg_temp.O();
select pg_temp.no('a member cannot read lesson bodies', $$select body, media_path from public.course_lessons where course_id = pg_temp.id('f')$$, '42501');
select pg_temp.no('a member who is not enrolled cannot open a lesson', $$select public.lesson_content(pg_temp.id('l1'))$$, '42501');
select pg_temp.ok('… nor read the quiz', $$not exists (select 1 from public.course_questions where course_id = pg_temp.id('f'))$$);
select pg_temp.as_server();
select pg_temp.step('a lesson file is stored', $$insert into storage.objects (bucket_id, name) values ('course-media', 'courses/' || pg_temp.id('f') || '/intro.webm')$$);
select pg_temp.O();
select pg_temp.ok('… an outsider cannot read it', $$not exists (select 1 from storage.objects where bucket_id = 'course-media')$$);
select pg_temp.no('… nor upload into the course', $$insert into storage.objects (bucket_id, name, owner) values ('course-media', 'courses/' || pg_temp.id('f') || '/x.pdf', 'a3000000-0000-0000-0000-000000000003')$$, '42501');

-- 3. enrolment
select pg_temp.L();
select pg_temp.no('the learner cannot enrol someone else', $$insert into public.course_enrollments (course_id, user_id) values (pg_temp.id('f'), 'a3000000-0000-0000-0000-000000000003')$$, '42501');
select pg_temp.no('the learner cannot enrol as completed', $$insert into public.course_enrollments (course_id, user_id, status) values (pg_temp.id('f'), pg_temp.L_id(), 'completed')$$, '42501');
select pg_temp.no('the learner cannot enrol itself in a paid course', $$insert into public.course_enrollments (course_id, user_id) values (pg_temp.id('p'), pg_temp.L_id())$$, '42501');
select pg_temp.step('the learner enrols in the free course', $$insert into public.course_enrollments (course_id, user_id) values (pg_temp.id('f'), pg_temp.L_id())$$);
select pg_temp.ok('… the count is 1', $$(select enrolled_count = 1 from public.training_courses where id = pg_temp.id('f'))$$);
select pg_temp.ok('the learner opens a lesson (text and file path)', $$(select (public.lesson_content(pg_temp.id('l1'))) ->> 'body' = 'TR secret body 1')$$);
select pg_temp.ok('… reads the lesson file', $$exists (select 1 from storage.objects where bucket_id = 'course-media' and name = 'courses/' || pg_temp.id('f') || '/intro.webm')$$);
select pg_temp.ok('… reads the questions', $$(select count(*) = 2 from public.course_questions where course_id = pg_temp.id('f'))$$);
select pg_temp.no('… but never the answers', $$select answer from public.course_questions where course_id = pg_temp.id('f')$$, '42501');
select pg_temp.no('the learner cannot mark itself completed', $$update public.course_enrollments set status = 'completed' where course_id = pg_temp.id('f')$$, '42501');

-- 4. progress and the quiz
select pg_temp.no('no progress in a course the learner is not enrolled in', $$insert into public.lesson_progress (lesson_id, course_id) select id, course_id from public.course_lessons where course_id = pg_temp.id('p')$$, '42501');
select pg_temp.step('the learner finishes lesson 1 (claiming another course)', $$insert into public.lesson_progress (lesson_id, course_id) values (pg_temp.id('l1'), pg_temp.id('p'))$$);
select pg_temp.ok('… the lesson decides the course', $$(select course_id = pg_temp.id('f') from public.lesson_progress where lesson_id = pg_temp.id('l1'))$$);
select pg_temp.no('the quiz waits for every lesson', $$select public.course_submit_quiz(pg_temp.id('f'), '{0,1}')$$, '22023');
select pg_temp.step('the learner finishes lesson 2', $$insert into public.lesson_progress (lesson_id, course_id) values (pg_temp.id('l2'), pg_temp.id('f'))$$);
select pg_temp.no('every question needs an answer', $$select public.course_submit_quiz(pg_temp.id('f'), '{0}')$$, '22023');
select pg_temp.ok('a wrong answer fails (50%% < 70%%) and does not complete the course', $$(select (r ->> 'passed')::boolean = false and (r ->> 'score')::int = 50 and r ->> 'code' is null from (select public.course_submit_quiz(pg_temp.id('f'), '{0,0}') r) x)
  and (select status = 'enrolled' from public.course_enrollments where course_id = pg_temp.id('f') and user_id = pg_temp.L_id())$$);
select pg_temp.ok('the right answers pass and issue a certificate', $$(select (r ->> 'passed')::boolean and (r ->> 'score')::int = 100 and r ->> 'code' ~ '^DBX-[0-9A-F]{10}$' from (select public.course_submit_quiz(pg_temp.id('f'), '{0,1}') r) x)$$);
select pg_temp.ok('… the course is completed with its date', $$(select status = 'completed' and completed_at is not null from public.course_enrollments where course_id = pg_temp.id('f') and user_id = pg_temp.L_id())$$);
select pg_temp.ok('… the certificate carries the name, course and hours; the learner is told', $$(select name = 'TR Learner' and course_title = 'TR Free GMP' and hours = 2 from public.certificates where user_id = pg_temp.L_id())
  and exists (select 1 from public.notifications where user_id = pg_temp.L_id() and type = 'certificate')$$);
insert into ids select 'cert', code from public.certificates where user_id = 'a3000000-0000-0000-0000-000000000002';
select pg_temp.ok('passing again returns the same certificate', $$(select r ->> 'code' = (select v from ids where k = 'cert') from (select public.course_submit_quiz(pg_temp.id('f'), '{0,1}') r) x)$$);
select pg_temp.no('the learner cannot write a certificate', $$insert into public.certificates (code, user_id, name, course_title) values ('DBX-FFFFFFFFFF', pg_temp.L_id(), 'x', 'y')$$, '42501');
select pg_temp.O();
select pg_temp.ok('another member sees the valid certificate (profile)', $$exists (select 1 from public.certificates where code = (select v from ids where k = 'cert'))$$);
create function pg_temp.ask(k text) returns void language sql as $$ select set_config('request.headers', json_build_object('x-dbx-cert', k)::text, true) $$;
select pg_temp.as_anon();
select pg_temp.ok('signed out, certificates cannot be listed', $$not exists (select 1 from public.certificates)$$);
select pg_temp.ask(lower((select v from ids where k = 'cert')));
select pg_temp.ok('signed out, the verify link (its code) shows exactly that certificate', $$(select count(*) = 1 from public.certificates)
  and (select name = 'TR Learner' and course_title = 'TR Free GMP' and revoked_at is null from public.certificates where code = (select v from ids where k = 'cert'))$$);
select pg_temp.no('… only what the certificate shows', $$select user_id from public.certificates$$, '42501');
select pg_temp.ask('DBX-0000000000');
select pg_temp.ok('an unknown code shows nothing', $$not exists (select 1 from public.certificates)$$);
select pg_temp.ask(''' or 1=1 --');
select pg_temp.ok('a made-up header shows nothing', $$not exists (select 1 from public.certificates)$$);
select pg_temp.ask('');
select pg_temp.A();
select pg_temp.step('Drugbox revokes the certificate', $$update public.certificates set revoked_at = now() where code = (select v from ids where k = 'cert')$$);
select pg_temp.as_anon(); select pg_temp.ask((select v from ids where k = 'cert'));
select pg_temp.ok('… the verify link shows it revoked', $$(select revoked_at is not null from public.certificates where code = (select v from ids where k = 'cert'))$$);
select pg_temp.ask('');

-- 5. attempts per hour
select pg_temp.A();
select pg_temp.step('a course with a one-question quiz', $$with x as (insert into public.training_courses (title) values ('TR Quiz Only') returning id) insert into ids select 'q', id::text from x;
  insert into public.course_questions (course_id, position, prompt, options, answer) select v::bigint, 1, 'TR Pick B', '{A,B}', 1 from ids where k = 'q'$$);
select pg_temp.L();
select pg_temp.step('the learner enrols', $$insert into public.course_enrollments (course_id, user_id) values (pg_temp.id('q'), pg_temp.L_id())$$);
select pg_temp.step('five wrong attempts', $$select public.course_submit_quiz(pg_temp.id('q'), '{0}') from generate_series(1, 5)$$);
select pg_temp.no('a sixth attempt within the hour is refused', $$select public.course_submit_quiz(pg_temp.id('q'), '{1}')$$, '54000');

-- 6. paying for a course
select pg_temp.no('a free course cannot be bought', $$select public.create_order('course_' || pg_temp.id('f'), 'card')$$, 'P0001');
select pg_temp.step('the learner orders the paid course by card', $$insert into ids select 'o', (public.create_order('course_' || pg_temp.id('p'), 'card')).id::text$$);
select pg_temp.ok('… the server price + 14%% VAT, for that course', $$(select amount_cents = 114000 and course_id = pg_temp.id('p') and status = 'pending' from public.payment_orders where id = pg_temp.id('o'))$$);
select pg_temp.no('… the browser cannot pay it', $$select public.confirm_payment('paymob', 'x', 'y', 114000, 'EGP', '{}')$$, '42501');
select pg_temp.as_server();
select pg_temp.step('Paymob confirms the payment (signed callback)', $$update public.payment_orders set provider_order = 'TRPO1' where id = pg_temp.id('o')$$);
select pg_temp.ok('… a wrong amount does not enrol', $$public.confirm_payment('paymob', 'TRPO1', 'tx1', 100, 'EGP', '{}') = 'amount mismatch'
  and not exists (select 1 from public.course_enrollments where course_id = pg_temp.id('p'))$$);
select pg_temp.ok('… the right amount is paid', $$public.confirm_payment('paymob', 'TRPO1', 'tx1', 114000, 'EGP', '{}') = 'paid'$$);
select pg_temp.ok('… which enrols the buyer and tells them', $$exists (select 1 from public.course_enrollments where course_id = pg_temp.id('p') and user_id = pg_temp.L_id() and order_id = pg_temp.id('o'))
  and exists (select 1 from public.notifications where user_id = pg_temp.L_id() and type = 'payment' and message like 'Payment received — you can start%')$$);
select pg_temp.ok('… a repeated callback enrols nobody twice', $$public.confirm_payment('paymob', 'TRPO1', 'tx1', 114000, 'EGP', '{}') = 'already paid'
  and (select enrolled_count = 1 from public.training_courses where id = pg_temp.id('p'))$$);
select pg_temp.L();
select pg_temp.ok('the learner opens the paid lesson now', $$(select (public.lesson_content(id)) ->> 'body' = 'TR paid body' from public.course_lessons where course_id = pg_temp.id('p'))$$);
select pg_temp.step('the learner tries to drop the paid course', $$delete from public.course_enrollments where course_id = pg_temp.id('p')$$);
select pg_temp.ok('… it stays', $$exists (select 1 from public.course_enrollments where course_id = pg_temp.id('p'))$$);
select pg_temp.no('it cannot be bought twice', $$select public.create_order('course_' || pg_temp.id('p'), 'card')$$, '23505');
select pg_temp.O();
select pg_temp.no('an outsider cannot pay with a made-up product', $$select public.create_order('course_999999999', 'card')$$, 'P0001');

-- 7. Drugbox changes and withdraws a course
select pg_temp.A();
select pg_temp.step('Drugbox raises the price', $$update public.training_courses set price_egp = 1200 where id = pg_temp.id('p')$$);
select pg_temp.ok('… the product follows', $$(select amount_egp = 1200 from public.payment_products where code = 'course_' || pg_temp.id('p'))$$);
select pg_temp.step('Drugbox takes the free course out of the catalog', $$update public.training_courses set active = false where id = pg_temp.id('f')$$);
select pg_temp.O();
select pg_temp.ok('an outsider no longer sees it', $$not exists (select 1 from public.training_courses where id = pg_temp.id('f'))$$);
select pg_temp.no('… nor can enrol in it', $$insert into public.course_enrollments (course_id, user_id) values (pg_temp.id('f'), 'a3000000-0000-0000-0000-000000000003')$$, '42501');
select pg_temp.L();
select pg_temp.ok('its learner still has it and its lessons', $$exists (select 1 from public.training_courses where id = pg_temp.id('f')) and (public.lesson_content(pg_temp.id('l2'))) ->> 'title' = 'TR Notes'$$);
select pg_temp.A();
select pg_temp.step('Drugbox stops selling the paid course', $$update public.training_courses set active = false where id = pg_temp.id('p')$$);
select pg_temp.ok('… its product stops selling', $$(select not active from public.payment_products where code = 'course_' || pg_temp.id('p'))$$);
select pg_temp.as_anon();
select pg_temp.ok('anon reads no enrolment', $$(select count(*) = 0 from public.course_enrollments)$$);
select pg_temp.ok('anon reads no progress, attempt or question (empty, F-26)', $$(select count(*) = 0 from public.lesson_progress) and (select count(*) = 0 from public.course_quiz_attempts)
  and (select count(*) = 0 from public.course_questions)$$);
select pg_temp.no('anon never reads the answers', $$select answer from public.course_questions$$, '42501');

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
