-- ═════════════════════════════════════════════════════════════════════
-- 0062 — Training (T-01; J-COMMUNITY-35 … 40)
--   1. courses        topic (for the filters), instructor, price (EGP before VAT; 0 = free), hours, pass mark, Arabic title and
--                     description (the owner's content comes later); a course people are enrolled in stays readable to them
--                     after Drugbox takes it out of the catalog
--   2. lessons        course_lessons: the syllabus (title, kind, minutes) is public; the content (text, video, PDF) is opened only
--                     by the course's learners (lesson_content()) and its files live in the private course-media bucket
--                     (courses/<course id>/…), readable through signed links by learners and Drugbox only
--   3. progress       lesson_progress: a learner marks lessons done (only in a course they are enrolled in)
--   4. quiz           course_questions (the right answers are never sent to the browser), course_submit_quiz(): all lessons done,
--                     a score against the course's pass mark, 5 attempts an hour; passing completes the course (server only)
--   5. certificates   one per learner and course, a unique code; the public verify link (signed out too) reads the one code it names
--   6. payments       a paid course is a payment product (course_<id>, kept in step with its price); create_order() sells it,
--                     activate_order() enrolls the buyer after the provider (or Drugbox, for InstaPay) confirmed the payment;
--                     the browser can enrol itself only in a free course, and a paid enrollment cannot be dropped
-- Every table, sequence and function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. courses ──────────────────────────────────────────────────────────────────────────────────────────
alter table public.training_courses add column if not exists topic            text not null default 'other';
alter table public.training_courses add column if not exists instructor       text not null default '';
alter table public.training_courses add column if not exists instructor_title text not null default '';
alter table public.training_courses add column if not exists price_egp        numeric(10,2) not null default 0;
alter table public.training_courses add column if not exists hours            numeric(5,1);
alter table public.training_courses add column if not exists pass_mark        int not null default 70;
alter table public.training_courses add column if not exists title_ar         text;
alter table public.training_courses add column if not exists description_ar   text;
alter table public.training_courses add column if not exists updated_at       timestamptz not null default now();
do $$ begin
  alter table public.training_courses add constraint training_courses_topic_chk check (topic in ('gmp', 'regulatory', 'formulation', 'quality', 'market', 'other'));
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.training_courses add constraint training_courses_more_chk check (price_egp >= 0 and price_egp <= 100000 and (hours is null or hours between 0.5 and 500)
    and pass_mark between 50 and 100 and length(instructor) <= 120 and length(instructor_title) <= 160 and length(coalesce(title_ar, '')) <= 160 and length(coalesce(description_ar, '')) <= 2000);
exception when duplicate_object then null; end $$;
-- the six courses of the approved page: their topic and hours (instructor, price and content wait on the owner)
update public.training_courses set topic = v.topic, hours = coalesce(training_courses.hours, v.hours)
  from (values ('GMP Fundamentals', 'gmp', 4), ('EDA Registration Process', 'regulatory', 6), ('ICH Guidelines', 'quality', 8),
               ('Cosmetics Regulation', 'regulatory', 3), ('Stability Studies', 'formulation', 5), ('GCC Market Access', 'market', 4)) v(title, topic, hours)
 where training_courses.title = v.title and training_courses.topic = 'other';

create or replace function private.enrolled_in_course(p_course bigint) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.course_enrollments e where e.course_id = p_course and e.user_id = auth.uid())
$$;
revoke all on function private.enrolled_in_course(bigint) from public, anon, authenticated, service_role;
grant execute on function private.enrolled_in_course(bigint) to anon, authenticated, service_role;   -- the catalog policy asks it for signed-out readers too (false)

drop policy if exists "courses: everyone reads active" on public.training_courses;
create policy "courses: everyone reads active" on public.training_courses for select
  using (active or public.is_platform_admin() or private.enrolled_in_course(id));

create or replace function public.training_courses_touch() returns trigger language plpgsql set search_path = public as $$
begin
  new.updated_at := now();
  if tg_op = 'INSERT' then if not public.is_server_call() then new.enrolled_count := 0; new.created_at := now(); end if;
  else new.enrolled_count := old.enrolled_count; new.created_at := old.created_at; end if;
  return new;
end $$;
revoke all on function public.training_courses_touch() from public, anon, authenticated, service_role;
grant execute on function public.training_courses_touch() to service_role;
drop trigger if exists trg_training_courses_touch on public.training_courses;
create trigger trg_training_courses_touch before insert or update on public.training_courses for each row
  when (pg_trigger_depth() = 0) execute function public.training_courses_touch();   -- the enrolment counter (a nested trigger) still counts

-- ── 2. lessons ──────────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.course_lessons (
  id          bigint generated always as identity primary key,
  course_id   bigint not null references public.training_courses(id) on delete cascade,
  position    int not null,
  title       text not null,
  kind        text not null default 'text',
  minutes     int not null default 10,
  body        text not null default '',
  media_path  text,
  created_at  timestamptz not null default now(),
  constraint course_lessons_kind check (kind in ('video', 'pdf', 'text')),
  constraint course_lessons_len check (length(trim(title)) between 2 and 160 and length(body) <= 20000 and minutes between 1 and 600 and position between 1 and 200),
  constraint course_lessons_media check (media_path is null or media_path ~ ('^courses/' || course_id::text || '/[A-Za-z0-9._-]{1,120}$')),
  unique (course_id, position)
);
alter table public.course_lessons enable row level security;
drop policy if exists "lessons: the syllabus of a course you can see" on public.course_lessons;
create policy "lessons: the syllabus of a course you can see" on public.course_lessons for select
  using (exists (select 1 from public.training_courses c where c.id = course_lessons.course_id));
drop policy if exists "lessons: Drugbox adds" on public.course_lessons;
create policy "lessons: Drugbox adds" on public.course_lessons for insert to authenticated with check (public.is_platform_admin());
drop policy if exists "lessons: Drugbox edits" on public.course_lessons;
create policy "lessons: Drugbox edits" on public.course_lessons for update to authenticated using (public.is_platform_admin()) with check (public.is_platform_admin());
drop policy if exists "lessons: Drugbox removes" on public.course_lessons;
create policy "lessons: Drugbox removes" on public.course_lessons for delete to authenticated using (public.is_platform_admin());
-- the content columns are not readable through the API at all: lesson_content() hands them to learners
revoke all on table public.course_lessons from public, anon, authenticated, service_role;
grant select (id, course_id, position, title, kind, minutes, created_at) on table public.course_lessons to anon, authenticated;
grant insert (course_id, position, title, kind, minutes, body, media_path), update (position, title, kind, minutes, body, media_path), delete on table public.course_lessons to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.course_lessons to service_role;
revoke all on sequence public.course_lessons_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.course_lessons_id_seq to authenticated, service_role;

create or replace function public.lesson_content(p_lesson bigint) returns jsonb
language plpgsql stable security definer set search_path = public as $$
declare l public.course_lessons;
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into l from public.course_lessons where id = p_lesson;
  if l.id is null then raise exception 'This lesson is no longer available' using errcode = 'P0002'; end if;
  if not (public.is_platform_admin() or private.enrolled_in_course(l.course_id)) then
    raise exception 'Enroll in the course to open its lessons' using errcode = '42501'; end if;
  return jsonb_build_object('id', l.id, 'course_id', l.course_id, 'position', l.position, 'title', l.title, 'kind', l.kind, 'minutes', l.minutes,
                            'body', l.body, 'media_path', l.media_path);
end $$;
revoke all on function public.lesson_content(bigint) from public, anon, authenticated, service_role;
grant execute on function public.lesson_content(bigint) to authenticated, service_role;

-- lesson files: private, courses/<course id>/<file>; learners of that course and Drugbox read (signed links), Drugbox writes
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('course-media', 'course-media', false, 209715200, array['video/mp4', 'video/webm', 'application/pdf'])
on conflict (id) do update set public = false, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;
create or replace function private.course_of_media(p_name text) returns bigint language sql immutable set search_path = public as $$
  select case when (storage.foldername(p_name))[1] = 'courses' and (storage.foldername(p_name))[2] ~ '^[0-9]{1,18}$'
              then ((storage.foldername(p_name))[2])::bigint end
$$;
revoke all on function private.course_of_media(text) from public, anon, authenticated, service_role;
grant execute on function private.course_of_media(text) to authenticated, service_role;
drop policy if exists "course media: learners and Drugbox read" on storage.objects;
create policy "course media: learners and Drugbox read" on storage.objects for select to authenticated
  using (bucket_id = 'course-media' and (public.is_platform_admin() or private.enrolled_in_course(private.course_of_media(name))));
drop policy if exists "course media: Drugbox uploads" on storage.objects;
create policy "course media: Drugbox uploads" on storage.objects for insert to authenticated
  with check (bucket_id = 'course-media' and public.is_platform_admin() and private.course_of_media(name) is not null);
drop policy if exists "course media: Drugbox replaces" on storage.objects;
create policy "course media: Drugbox replaces" on storage.objects for update to authenticated
  using (bucket_id = 'course-media' and public.is_platform_admin()) with check (bucket_id = 'course-media' and public.is_platform_admin() and private.course_of_media(name) is not null);
drop policy if exists "course media: Drugbox removes" on storage.objects;
create policy "course media: Drugbox removes" on storage.objects for delete to authenticated using (bucket_id = 'course-media' and public.is_platform_admin());

-- ── 3. progress ─────────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.lesson_progress (
  user_id      uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  lesson_id    bigint not null references public.course_lessons(id) on delete cascade,
  course_id    bigint not null references public.training_courses(id) on delete cascade,
  completed_at timestamptz not null default now(),
  primary key (user_id, lesson_id)
);
create index if not exists idx_lesson_progress_course on public.lesson_progress (user_id, course_id);
create index if not exists idx_lesson_progress_lesson on public.lesson_progress (lesson_id);
create index if not exists idx_lesson_progress_course_only on public.lesson_progress (course_id);
alter table public.lesson_progress enable row level security;
create or replace function public.lesson_progress_guard() returns trigger language plpgsql set search_path = public as $$
begin
  if public.is_server_call() then return new; end if;
  select l.course_id into new.course_id from public.course_lessons l where l.id = new.lesson_id;   -- the lesson decides the course
  new.completed_at := now();
  return new;
end $$;
revoke all on function public.lesson_progress_guard() from public, anon, authenticated, service_role;
grant execute on function public.lesson_progress_guard() to service_role;
drop trigger if exists trg_lesson_progress_guard on public.lesson_progress;
create trigger trg_lesson_progress_guard before insert on public.lesson_progress for each row execute function public.lesson_progress_guard();
drop policy if exists "progress: yours" on public.lesson_progress;
create policy "progress: yours" on public.lesson_progress for select to authenticated using (user_id = (select auth.uid()) or (select public.is_platform_admin()));
drop policy if exists "progress: mark a lesson of your course done" on public.lesson_progress;
create policy "progress: mark a lesson of your course done" on public.lesson_progress for insert to authenticated
  with check (user_id = (select auth.uid()) and private.enrolled_in_course(course_id));
drop policy if exists "progress: undo yours" on public.lesson_progress;
create policy "progress: undo yours" on public.lesson_progress for delete to authenticated using (user_id = (select auth.uid()));
revoke all on table public.lesson_progress from public, anon, authenticated, service_role;
grant select on table public.lesson_progress to anon;                          -- no policy for anon → an empty answer (F-26)
grant select, insert, delete on table public.lesson_progress to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.lesson_progress to service_role;

-- ── 4. the final quiz ───────────────────────────────────────────────────────────────────────────────────
create table if not exists public.course_questions (
  id         bigint generated always as identity primary key,
  course_id  bigint not null references public.training_courses(id) on delete cascade,
  position   int not null,
  prompt     text not null,
  options    text[] not null,
  answer     int not null,
  constraint course_questions_ok check (length(trim(prompt)) between 3 and 500 and cardinality(options) between 2 and 6 and answer >= 0 and answer < cardinality(options)
                                        and position between 1 and 100),
  unique (course_id, position)
);
alter table public.course_questions enable row level security;
drop policy if exists "questions: learners and Drugbox read" on public.course_questions;
create policy "questions: learners and Drugbox read" on public.course_questions for select to authenticated
  using ((select public.is_platform_admin()) or private.enrolled_in_course(course_id));
drop policy if exists "questions: Drugbox adds" on public.course_questions;
create policy "questions: Drugbox adds" on public.course_questions for insert to authenticated with check (public.is_platform_admin());
drop policy if exists "questions: Drugbox edits" on public.course_questions;
create policy "questions: Drugbox edits" on public.course_questions for update to authenticated using (public.is_platform_admin()) with check (public.is_platform_admin());
drop policy if exists "questions: Drugbox removes" on public.course_questions;
create policy "questions: Drugbox removes" on public.course_questions for delete to authenticated using (public.is_platform_admin());
revoke all on table public.course_questions from public, anon, authenticated, service_role;
grant select (id, course_id, position, prompt, options) on table public.course_questions to anon, authenticated;   -- never the answer; anon: empty (F-26)
grant insert (course_id, position, prompt, options, answer), update (position, prompt, options, answer), delete on table public.course_questions to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.course_questions to service_role;
revoke all on sequence public.course_questions_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.course_questions_id_seq to authenticated, service_role;

-- Drugbox editing a quiz sees the answers
create or replace function public.course_questions_admin(p_course bigint)
returns table (id bigint, "position" int, prompt text, options text[], answer int) language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_platform_admin() then raise exception 'Only the Drugbox team manages courses' using errcode = '42501'; end if;
  return query select q.id, q.position, q.prompt, q.options, q.answer from public.course_questions q where q.course_id = p_course order by q.position;
end $$;
revoke all on function public.course_questions_admin(bigint) from public, anon, authenticated, service_role;
grant execute on function public.course_questions_admin(bigint) to authenticated, service_role;

create table if not exists public.course_quiz_attempts (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references public.profiles(id) on delete cascade,
  course_id  bigint not null references public.training_courses(id) on delete cascade,
  score      int not null,
  passed     boolean not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_course_quiz_attempts_user on public.course_quiz_attempts (user_id, course_id, created_at desc);
create index if not exists idx_course_quiz_attempts_course on public.course_quiz_attempts (course_id);
alter table public.course_quiz_attempts enable row level security;
drop policy if exists "attempts: yours" on public.course_quiz_attempts;
create policy "attempts: yours" on public.course_quiz_attempts for select to authenticated using (user_id = (select auth.uid()) or (select public.is_platform_admin()));
revoke all on table public.course_quiz_attempts from public, anon, authenticated, service_role;
grant select on table public.course_quiz_attempts to anon, authenticated;           -- written by course_submit_quiz() only; anon: empty (F-26)
grant select, insert, update, delete, truncate, references, trigger on table public.course_quiz_attempts to service_role;
revoke all on sequence public.course_quiz_attempts_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.course_quiz_attempts_id_seq to service_role;

-- ── 5. certificates ─────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.certificates (
  code         text primary key,
  user_id      uuid not null references public.profiles(id) on delete cascade,
  course_id    bigint references public.training_courses(id) on delete set null,
  name         text not null,
  course_title text not null,
  hours        numeric(5,1),
  issued_at    timestamptz not null default now(),
  revoked_at   timestamptz,
  unique (user_id, course_id)
);
create index if not exists idx_certificates_course on public.certificates (course_id);
alter table public.certificates enable row level security;
drop policy if exists "certificates: members see valid ones, you see yours" on public.certificates;
create policy "certificates: members see valid ones, you see yours" on public.certificates for select to authenticated
  using (revoked_at is null or user_id = (select auth.uid()) or (select public.is_platform_admin()));
drop policy if exists "certificates: Drugbox revokes" on public.certificates;
create policy "certificates: Drugbox revokes" on public.certificates for update to authenticated using (public.is_platform_admin()) with check (public.is_platform_admin());
revoke all on table public.certificates from public, anon, authenticated, service_role;
grant select on table public.certificates to authenticated;
grant update (revoked_at) on table public.certificates to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.certificates to service_role;

-- the public verify link (signed out too): the page asks for the one code in the link, sent in the x-dbx-cert request header, and
-- this policy lets exactly that certificate through — nobody can list certificates, and no function is open to signed-out callers (F-27)
create or replace function private.asked_certificate() returns text language sql stable set search_path = public as $$
  select upper(nullif(trim(coalesce(nullif(current_setting('request.headers', true), '')::json ->> 'x-dbx-cert', '')), ''))
$$;
revoke all on function private.asked_certificate() from public, anon, authenticated, service_role;
grant execute on function private.asked_certificate() to anon, authenticated, service_role;
drop policy if exists "certificates: the verify link reads the one asked" on public.certificates;
create policy "certificates: the verify link reads the one asked" on public.certificates for select to anon, authenticated
  using (code = private.asked_certificate());
grant select (code, name, course_title, hours, issued_at, revoked_at) on table public.certificates to anon;
drop function if exists public.verify_certificate(text);

create or replace function public.course_submit_quiz(p_course bigint, p_answers int[] default '{}') returns jsonb
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); c public.training_courses; e public.course_enrollments; total int; right_ int := 0; done_ int; lessons_ int;
        sc int; ok boolean; cert text; recent int;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into c from public.training_courses where id = p_course;
  if c.id is null then raise exception 'This course is no longer available' using errcode = 'P0002'; end if;
  select * into e from public.course_enrollments where course_id = p_course and user_id = me;
  if e.course_id is null then raise exception 'Enroll in the course first' using errcode = '42501'; end if;
  if e.status = 'completed' then
    select code into cert from public.certificates where user_id = me and course_id = p_course;
    return jsonb_build_object('passed', true, 'score', null, 'already', true, 'code', cert);
  end if;
  select count(*) into lessons_ from public.course_lessons where course_id = p_course;
  select count(*) into done_ from public.lesson_progress p join public.course_lessons l on l.id = p.lesson_id where p.user_id = me and l.course_id = p_course;
  if lessons_ = 0 then raise exception 'This course has no lessons yet — it cannot be completed' using errcode = '22023'; end if;   -- (verifier B1)
  if done_ < lessons_ then raise exception 'Finish all the lessons first (% of % done)', done_, lessons_ using errcode = '22023'; end if;
  select count(*) into recent from public.course_quiz_attempts where user_id = me and course_id = p_course and created_at > now() - interval '1 hour';
  perform pg_advisory_xact_lock(hashtextextended(me::text || ':' || p_course::text, 7));   -- parallel calls wait: the limit holds
  select count(*) into recent from public.course_quiz_attempts where user_id = me and course_id = p_course and created_at > now() - interval '1 hour';
  if recent >= 5 then raise exception 'Five attempts in an hour — review the lessons and try again later' using errcode = '54000'; end if;
  select count(*) into total from public.course_questions where course_id = p_course;
  if total > 0 then
    if coalesce(cardinality(p_answers), 0) <> total then raise exception 'Answer every question (% questions)', total using errcode = '22023'; end if;
    select count(*) into right_ from (select q.answer, row_number() over (order by q.position) as rn from public.course_questions q where q.course_id = p_course) x
     where p_answers[x.rn] = x.answer;                                               -- answers in the order the questions are shown
    sc := round(100.0 * right_ / total);
  else
    sc := 100;                                                                       -- a course without a quiz: finishing the lessons is enough
  end if;
  ok := sc >= c.pass_mark;
  insert into public.course_quiz_attempts (user_id, course_id, score, passed) values (me, p_course, sc, ok);
  if ok then
    update public.course_enrollments set status = 'completed', completed_at = now() where course_id = p_course and user_id = me;
    cert := 'DBX-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 10));
    insert into public.certificates (code, user_id, course_id, name, course_title, hours)
    select cert, me, c.id, coalesce(nullif(trim(p.name), ''), 'Drugbox member'), c.title, c.hours from public.profiles p where p.id = me
    on conflict (user_id, course_id) do nothing;                                -- a certificate Drugbox withdrew stays withdrawn
    select code into cert from public.certificates where user_id = me and course_id = p_course;
    insert into public.notifications (user_id, type, message, data)
    values (me, 'certificate', 'Your certificate for "' || left(c.title, 120) || '" is ready', jsonb_build_object('code', cert, 'course', c.id));
  end if;
  return jsonb_build_object('passed', ok, 'score', sc, 'correct', right_, 'total', total, 'pass_mark', c.pass_mark, 'code', cert);
end $$;
revoke all on function public.course_submit_quiz(bigint, int[]) from public, anon, authenticated, service_role;
grant execute on function public.course_submit_quiz(bigint, int[]) to authenticated, service_role;

-- ── 6. enrolment: free courses by the learner, paid ones by the server after payment ───────────────────
alter table public.course_enrollments add column if not exists order_id bigint references public.payment_orders(id) on delete set null;
create index if not exists idx_course_enrollments_order on public.course_enrollments (order_id) where order_id is not null;
drop policy if exists "enrollments: enroll yourself" on public.course_enrollments;
create policy "enrollments: enroll yourself" on public.course_enrollments for insert
  with check (user_id = (select auth.uid()) and status = 'enrolled' and order_id is null and completed_at is null
              and exists (select 1 from public.training_courses c where c.id = course_id and c.active and c.price_egp = 0));
drop policy if exists "enrollments: a paid course stays yours" on public.course_enrollments;
create policy "enrollments: a paid course stays yours" on public.course_enrollments as restrictive for delete to authenticated
  using (order_id is null);
revoke all on table public.course_enrollments from public, anon, authenticated, service_role;
grant select, references, trigger on table public.course_enrollments to anon;   -- no policy for anon → an empty answer (F-26)
grant select, insert, delete, references, trigger on table public.course_enrollments to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.course_enrollments to service_role;

-- ── 7. a paid course is a payment product ───────────────────────────────────────────────────────────────
do $$ declare k text; begin
  for k in select conname from pg_constraint where conrelid = 'public.payment_products'::regclass and contype = 'c'
             and (pg_get_constraintdef(oid) ~ 'kind' or pg_get_constraintdef(oid) ~ 'duration_days') loop
    execute format('alter table public.payment_products drop constraint %I', k);
  end loop;
end $$;
alter table public.payment_products add constraint payment_products_kind_chk check (kind in ('vip', 'boost', 'featured', 'course'));
alter table public.payment_products add constraint payment_products_duration_chk check (duration_days > 0 or kind = 'course');
alter table public.payment_products add column if not exists course_id bigint references public.training_courses(id) on delete set null;
create unique index if not exists idx_payment_products_course on public.payment_products (course_id) where course_id is not null;
alter table public.payment_orders add column if not exists course_id bigint references public.training_courses(id) on delete set null;
create index if not exists idx_payment_orders_course on public.payment_orders (course_id) where course_id is not null;

-- the price on the course is the price charged: its product follows every change (and stops selling when the course is free or off)
create or replace function public.training_course_product() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.price_egp > 0 then
    insert into public.payment_products (code, label, kind, amount_egp, duration_days, active, course_id)
    values ('course_' || new.id, left('Course: ' || new.title, 120), 'course', new.price_egp, 0, new.active, new.id)
    on conflict (code) do update set label = excluded.label, amount_egp = excluded.amount_egp, active = excluded.active, course_id = excluded.course_id;
  else
    update public.payment_products set active = false where code = 'course_' || new.id;
  end if;
  return null;
end $$;
revoke all on function public.training_course_product() from public, anon, authenticated, service_role;
grant execute on function public.training_course_product() to service_role;
drop trigger if exists trg_training_course_product on public.training_courses;
create trigger trg_training_course_product after insert or update of price_egp, title, active on public.training_courses
  for each row execute function public.training_course_product();

create or replace function public.create_order(p_product text, p_method text, p_company bigint default null, p_listing bigint default null)
returns public.payment_orders language plpgsql security definer set search_path = public as $$
declare pr public.payment_products; o public.payment_orders;
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into pr from public.payment_products where code = p_product and active; if not found then raise exception 'Unknown product'; end if;
  if pr.kind = 'vip' and (p_company is null or not public.is_company_member(p_company, array['owner','admin'])) then raise exception 'Only the company''s owner or admins can upgrade it' using errcode = '42501'; end if;
  if pr.kind in ('boost','featured') and not exists (select 1 from public.products where id = p_listing and user_id = auth.uid()) then raise exception 'You can boost only your own listings' using errcode = '42501'; end if;
  if pr.kind = 'course' then
    if not exists (select 1 from public.training_courses c where c.id = pr.course_id and c.active and c.price_egp > 0) then raise exception 'This course is not on sale at the moment' using errcode = 'P0002'; end if;
    if exists (select 1 from public.course_enrollments e where e.course_id = pr.course_id and e.user_id = auth.uid()) then raise exception 'You are already enrolled in this course' using errcode = '23505'; end if;
  end if;
  insert into public.payment_orders (user_id, product_code, company_id, listing_id, course_id, method, amount_cents)
  values (auth.uid(), pr.code, case when pr.kind = 'vip' then p_company end, case when pr.kind in ('boost','featured') then p_listing end,
          case when pr.kind = 'course' then pr.course_id end, p_method, round(pr.amount_egp * (1 + pr.vat_rate) * 100))
  returning * into o;
  return o;
end $$;
revoke all on function public.create_order(text, text, bigint, bigint) from public, anon, authenticated, service_role;
grant execute on function public.create_order(text, text, bigint, bigint) to authenticated, service_role;

-- 0023's activation, plus courses: the buyer is enrolled (once; a paid enrolment remembers its order)
create or replace function public.activate_order(p_id bigint) returns boolean language plpgsql security definer set search_path = public as $$
declare o public.payment_orders; pr public.payment_products; n int := 0; what text; ctitle text;
begin
  select * into o from public.payment_orders where id = p_id; select * into pr from public.payment_products where code = o.product_code;
  if pr.kind = 'vip' then
    what := 'company page';
    update public.companies c set plan = 'vip',
           vip_until = case when c.plan = 'vip' and c.vip_until is null then null       -- granted by Drugbox without an end date
                            else greatest(coalesce(c.vip_until, now()), now()) + make_interval(days => pr.duration_days) end
     where c.id = o.company_id
       and (c.owner_id = o.user_id or exists (select 1 from public.company_members m where m.company_id = c.id and m.user_id = o.user_id and m.role in ('owner','admin')));
  elsif pr.kind = 'boost' then
    what := 'listing';
    update public.products set boosted_until = greatest(coalesce(boosted_until, now()), now()) + make_interval(days => pr.duration_days)
     where id = o.listing_id and user_id = o.user_id;
  elsif pr.kind = 'course' then
    what := 'course';
    select title into ctitle from public.training_courses where id = o.course_id;
    if ctitle is not null then
      insert into public.course_enrollments (course_id, user_id, status, order_id) values (o.course_id, o.user_id, 'enrolled', o.id)
      on conflict (course_id, user_id) do nothing;
      get diagnostics n = row_count;                                           -- already enrolled (paid twice): refund due, below
      if n = 0 then what := 'course (you were already enrolled)'; end if;
    end if;
  else
    what := 'listing';
    update public.products set featured_until = greatest(coalesce(featured_until, now()), now()) + make_interval(days => pr.duration_days)
     where id = o.listing_id and user_id = o.user_id;
  end if;
  if pr.kind <> 'course' then get diagnostics n = row_count; end if;
  if n = 0 then
    update public.payment_orders set provider_payload = coalesce(provider_payload, '{}'::jsonb) || jsonb_build_object('not_activated', what) where id = o.id;
    insert into public.notifications (user_id, type, message)
    values (o.user_id, 'payment', 'Payment received for ' || pr.label || ' (' || o.merchant_ref || '), but '
                                  || case when what like 'course (%' then 'you were already enrolled' else 'the ' || what || ' is no longer available' end || ' — the Drugbox team will refund you');
    insert into public.notifications (user_id, type, message)
    select p.id, 'payment', 'Order ' || o.merchant_ref || ' was paid but not activated (the ' || what || ' is gone) — refund due'
      from public.profiles p where p.role = 'admin';
    return false;
  end if;
  insert into public.notifications (user_id, type, message)
  values (o.user_id, 'payment', case when pr.kind = 'course' then 'Payment received — you can start "' || left(ctitle, 120) || '" now'
                                     else 'Payment received — ' || pr.label || ' is active' end);
  return true;
end $$;
revoke all on function public.activate_order(bigint) from public, anon, authenticated, service_role;
grant execute on function public.activate_order(bigint) to service_role;

notify pgrst, 'reload schema';
