-- ═════════════════════════════════════════════════════════════════════
-- 0102 — Ask an expert (AREA w-growth: W-43): sessions arranged on request
--   1. topics      the list members ask about (safe registration-file purchase, NFSA, agency contracts, the toll card, pricing,
--                  importing, cold chain, the authority's labs / track & trace, choosing a factory) + "other" with a note
--   2. requests    a member asks for a topic (one open request per member and topic, withdrawn by them); everyone sees how
--                  many asked (expert_topic_demand), Drugbox sees who and their notes
--   3. sessions    a Drugbox admin schedules a session (title EN/AR, the expert's name and line, start, length, seats, the
--                  meeting link); the members who asked for its topic are told; members register (seats counted by one
--                  trigger); the meeting link is given only to the registered (expert_session_link), from an hour before
--   4. reminders   growth_tick() tells the registered a day before and an hour before (once each)
--   5. Q&A         a registered member asks before or during the session; a Drugbox admin (or the expert, when the expert is a
--                  member) answers; questions and answers stay readable to every member afterwards; the asker or Drugbox
--                  removes a question; Drugbox hides one that breaks the rules
-- Every table, sequence and function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. topics ───────────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.expert_topics (
  key       text primary key,
  title_en  text not null,
  title_ar  text not null,
  sort      int not null default 0
);
alter table public.expert_topics enable row level security;
drop policy if exists "expert topics: members read" on public.expert_topics;
create policy "expert topics: members read" on public.expert_topics for select to authenticated using (true);
revoke all on table public.expert_topics from public, anon, authenticated, service_role;
grant select on table public.expert_topics to anon, authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.expert_topics to service_role;
insert into public.expert_topics (key, title_en, title_ar, sort) values
  ('file_purchase',  'Buying a registration file safely',        'شراء ملف تسجيل بأمان',              1),
  ('nfsa',           'NFSA notification (supplements, food)',    'إخطار هيئة سلامة الغذاء (المكملات والأغذية)',           2),
  ('agency_contract','Agency and distribution contracts',        'عقود الوكالة والتوزيع',               3),
  ('toll_card',      'The toll-manufacturing card',              'كارت التصنيع لدى الغير',            4),
  ('pricing',        'Pricing and price increases',              'التسعير وزيادة الأسعار',             5),
  ('importer',       'Importing and the importer''s file',       'الاستيراد وملف المستورد',            6),
  ('cold_chain',     'Cold chain',                               'سلسلة التبريد',                     7),
  ('labs_tracking',  'Authority labs and track & trace',         'معامل الهيئة والتتبع',               8),
  ('choose_factory', 'Choosing a factory',                       'اختيار مصنع',                       9),
  ('other',          'Another topic',                            'موضوع آخر',                        10)
on conflict (key) do nothing;

-- ── 2. requests ─────────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.expert_requests (
  id          bigint generated always as identity primary key,
  user_id     uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  topic       text not null references public.expert_topics(key),
  note        text check (length(note) <= 500),
  created_at  timestamptz not null default now(),
  unique (user_id, topic)
);
create index if not exists idx_expert_requests_topic on public.expert_requests (topic, created_at desc);
alter table public.expert_requests enable row level security;
drop policy if exists "expert requests: own and Drugbox read" on public.expert_requests;
create policy "expert requests: own and Drugbox read" on public.expert_requests for select to authenticated
  using (user_id = (select auth.uid()) or public.is_platform_admin());
drop policy if exists "expert requests: a member asks" on public.expert_requests;
create policy "expert requests: a member asks" on public.expert_requests for insert to authenticated
  with check (user_id = (select auth.uid()) and (topic <> 'other' or length(trim(coalesce(note, ''))) >= 5));
drop policy if exists "expert requests: the member withdraws" on public.expert_requests;
create policy "expert requests: the member withdraws" on public.expert_requests for delete to authenticated using (user_id = (select auth.uid()));
drop policy if exists "a suspended account does not write" on public.expert_requests;
create policy "a suspended account does not write" on public.expert_requests as restrictive for insert to authenticated with check ((select private.not_suspended()));
revoke all on table public.expert_requests from public, anon, authenticated, service_role;
grant select on table public.expert_requests to anon;
grant select, insert, delete on table public.expert_requests to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.expert_requests to service_role;
revoke all on sequence public.expert_requests_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.expert_requests_id_seq to authenticated, service_role;
create or replace function public.expert_requests_guard() returns trigger language plpgsql set search_path = public as $$
begin
  if public.is_server_call() then return new; end if;
  new.created_at := now(); new.note := nullif(trim(coalesce(new.note, '')), '');
  return new;
end $$;
revoke all on function public.expert_requests_guard() from public, anon, authenticated, service_role;
grant execute on function public.expert_requests_guard() to service_role;
drop trigger if exists trg_expert_requests_guard on public.expert_requests;
create trigger trg_expert_requests_guard before insert on public.expert_requests for each row execute function public.expert_requests_guard();

-- how many members asked for each topic (no names)
create or replace function public.expert_topic_demand() returns table (topic text, asked int, mine boolean)
language sql stable security definer set search_path = public as $$
  select t.key, (select count(*)::int from public.expert_requests r where r.topic = t.key),
         exists (select 1 from public.expert_requests r where r.topic = t.key and r.user_id = auth.uid())
    from public.expert_topics t where auth.uid() is not null order by t.sort
$$;
revoke all on function public.expert_topic_demand() from public, anon, authenticated, service_role;
grant execute on function public.expert_topic_demand() to authenticated, service_role;

-- ── 3. sessions ─────────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.expert_sessions (
  id                bigint generated always as identity primary key,
  topic             text not null references public.expert_topics(key),
  title             text not null check (length(title) between 3 and 160),
  title_ar          text check (length(title_ar) <= 160),
  about             text check (length(about) <= 2000),
  expert_name       text not null check (length(expert_name) between 2 and 120),
  expert_line       text check (length(expert_line) <= 200),          -- e.g. "Regulatory consultant, 20 years at …"
  expert_user       uuid references public.profiles(id) on delete set null,
  starts_at         timestamptz not null,
  minutes           int not null default 60 check (minutes between 15 and 240),
  seats             int not null default 100 check (seats between 1 and 1000),
  join_url          text check (join_url is null or (length(join_url) <= 400 and join_url ~* '^https://[^\s<>"]{4,}$')),
  status            text not null default 'scheduled' check (status in ('scheduled', 'cancelled', 'done')),
  registered_count  int not null default 0,
  created_by        uuid references public.profiles(id) on delete set null,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);
create index if not exists idx_expert_sessions_start on public.expert_sessions (starts_at desc);
create index if not exists idx_expert_sessions_topic on public.expert_sessions (topic);
create index if not exists idx_expert_sessions_expert on public.expert_sessions (expert_user) where expert_user is not null;
create index if not exists idx_expert_sessions_created_by on public.expert_sessions (created_by) where created_by is not null;
alter table public.expert_sessions enable row level security;
drop policy if exists "expert sessions: members read" on public.expert_sessions;
create policy "expert sessions: members read" on public.expert_sessions for select to authenticated using (true);
revoke all on table public.expert_sessions from public, anon, authenticated, service_role;
grant select (id, topic, title, title_ar, about, expert_name, expert_line, expert_user, starts_at, minutes, seats, status, registered_count, created_at, updated_at)
  on table public.expert_sessions to authenticated;                            -- the meeting link only through expert_session_link()
grant select (id) on table public.expert_sessions to anon;                     -- no policy for anon → empty (F-26)
grant select, insert, update, delete, truncate, references, trigger on table public.expert_sessions to service_role;
revoke all on sequence public.expert_sessions_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.expert_sessions_id_seq to service_role;

create table if not exists public.expert_registrations (
  session_id   bigint not null references public.expert_sessions(id) on delete cascade,
  user_id      uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  created_at   timestamptz not null default now(),
  reminded_day  boolean not null default false,
  reminded_hour boolean not null default false,
  primary key (session_id, user_id)
);
create index if not exists idx_expert_registrations_user on public.expert_registrations (user_id);
alter table public.expert_registrations enable row level security;
drop policy if exists "expert registrations: own and Drugbox read" on public.expert_registrations;
create policy "expert registrations: own and Drugbox read" on public.expert_registrations for select to authenticated
  using (user_id = (select auth.uid()) or public.is_platform_admin()
         or exists (select 1 from public.expert_sessions s where s.id = session_id and s.expert_user = (select auth.uid())));
drop policy if exists "expert registrations: the member registers" on public.expert_registrations;
create policy "expert registrations: the member registers" on public.expert_registrations for insert to authenticated
  with check (user_id = (select auth.uid()));
drop policy if exists "expert registrations: the member cancels" on public.expert_registrations;
create policy "expert registrations: the member cancels" on public.expert_registrations for delete to authenticated using (user_id = (select auth.uid()));
drop policy if exists "a suspended account does not write" on public.expert_registrations;
create policy "a suspended account does not write" on public.expert_registrations as restrictive for insert to authenticated with check ((select private.not_suspended()));
revoke all on table public.expert_registrations from public, anon, authenticated, service_role;
grant select on table public.expert_registrations to anon;
grant select (session_id, user_id, created_at), insert (session_id, user_id), delete on table public.expert_registrations to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.expert_registrations to service_role;

-- registering: only a scheduled session that has not started, while seats are left (checked under a lock on the session)
create or replace function public.expert_registrations_guard() returns trigger
language plpgsql security definer set search_path = public as $$
declare s public.expert_sessions;
begin
  if tg_op = 'INSERT' then
    select * into s from public.expert_sessions where id = new.session_id for update;
    if auth.uid() is not null then                        -- a member registering (the server, e.g. a seed, is not checked)
      if s.id is null then raise exception 'This session is gone' using errcode = 'P0002'; end if;
      if s.status <> 'scheduled' then raise exception 'This session is %', s.status using errcode = '55000'; end if;
      if s.starts_at <= now() then raise exception 'This session has already started' using errcode = '55000'; end if;
      if s.registered_count >= s.seats then raise exception 'This session is full' using errcode = '23514'; end if;
    end if;
    new.created_at := now(); new.reminded_day := false; new.reminded_hour := false;
    update public.expert_sessions set registered_count = registered_count + 1 where id = new.session_id;
    return new;
  end if;
  update public.expert_sessions set registered_count = greatest(registered_count - 1, 0) where id = old.session_id;
  return old;
end $$;
revoke all on function public.expert_registrations_guard() from public, anon, authenticated, service_role;
grant execute on function public.expert_registrations_guard() to service_role;
drop trigger if exists trg_expert_registrations_guard on public.expert_registrations;
drop trigger if exists trg_expert_registrations_count on public.expert_registrations;
create trigger trg_expert_registrations_count before insert or delete on public.expert_registrations for each row execute function public.expert_registrations_guard();

-- Drugbox schedules / changes / cancels a session (p_local: the Cairo date and time 'YYYY-MM-DD HH24:MI')
create or replace function public.expert_session_save(p_id bigint, p_topic text, p_title text, p_title_ar text, p_about text, p_expert_name text,
                                                       p_expert_line text, p_local text, p_minutes int, p_seats int, p_join_url text, p_expert_user uuid default null)
returns bigint language plpgsql security definer set search_path = public as $$
declare at timestamptz; old public.expert_sessions; nid bigint; tname text;
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin schedules expert sessions' using errcode = '42501'; end if;
  if not exists (select 1 from public.expert_topics where key = p_topic) then raise exception 'Pick a topic' using errcode = '22023'; end if;
  if length(trim(coalesce(p_title, ''))) < 3 then raise exception 'Give the session a title' using errcode = '22023'; end if;
  if length(trim(coalesce(p_expert_name, ''))) < 2 then raise exception 'Name the expert' using errcode = '22023'; end if;
  if nullif(trim(coalesce(p_join_url, '')), '') is not null and (length(trim(p_join_url)) > 400 or trim(p_join_url) !~* '^https://[^\s<>"]{4,}$') then raise exception 'The meeting link must start with https://' using errcode = '22023'; end if;
  begin at := (to_timestamp(trim(coalesce(p_local, '')), 'YYYY-MM-DD HH24:MI')::timestamp at time zone 'Africa/Cairo');
  exception when others then raise exception 'Give the date and time as YYYY-MM-DD HH:MM (Cairo time)' using errcode = '22023'; end;
  if at is null then raise exception 'Give the date and time as YYYY-MM-DD HH:MM (Cairo time)' using errcode = '22023'; end if;
  if p_expert_user is not null and not exists (select 1 from public.profiles where id = p_expert_user) then raise exception 'That member is not on Drugbox' using errcode = '22023'; end if;
  if p_id is null then
    if at <= now() then raise exception 'Pick a time in the future' using errcode = '22023'; end if;
    insert into public.expert_sessions (topic, title, title_ar, about, expert_name, expert_line, expert_user, starts_at, minutes, seats, join_url, created_by)
    values (p_topic, trim(p_title), nullif(trim(coalesce(p_title_ar, '')), ''), nullif(trim(coalesce(p_about, '')), ''), trim(p_expert_name), nullif(trim(coalesce(p_expert_line, '')), ''),
            p_expert_user, at, coalesce(p_minutes, 60), coalesce(p_seats, 100), nullif(trim(coalesce(p_join_url, '')), ''), auth.uid())
    returning id into nid;
    -- the members who asked for this topic are told (once per session)
    select title_en into tname from public.expert_topics where key = p_topic;
    insert into public.notifications (user_id, type, message, data)
    select r.user_id, 'expert_session', 'An expert session you asked for: "' || left(trim(p_title), 120) || '"', jsonb_build_object('session', nid, 'topic', p_topic)
      from public.expert_requests r where r.topic = p_topic;
    return nid;
  end if;
  select * into old from public.expert_sessions where id = p_id for update;
  if not found then raise exception 'This session is gone' using errcode = 'P0002'; end if;
  if old.status <> 'scheduled' then raise exception 'This session is %', old.status using errcode = '55000'; end if;
  if p_seats is not null and p_seats < old.registered_count then raise exception '% members are already registered — the seats cannot be fewer', old.registered_count using errcode = '23514'; end if;
  update public.expert_sessions set topic = p_topic, title = trim(p_title), title_ar = nullif(trim(coalesce(p_title_ar, '')), ''), about = nullif(trim(coalesce(p_about, '')), ''),
         expert_name = trim(p_expert_name), expert_line = nullif(trim(coalesce(p_expert_line, '')), ''), expert_user = p_expert_user,
         starts_at = at, minutes = coalesce(p_minutes, minutes), seats = coalesce(p_seats, seats), join_url = nullif(trim(coalesce(p_join_url, '')), ''), updated_at = now()
   where id = p_id;
  if at is distinct from old.starts_at then              -- a new time: the registered are told and reminded again
    update public.expert_registrations set reminded_day = false, reminded_hour = false where session_id = p_id;
    insert into public.notifications (user_id, type, message, data)
    select g.user_id, 'expert_session', 'The expert session "' || left(trim(p_title), 120) || '" moved to a new time', jsonb_build_object('session', p_id, 'moved', true)
      from public.expert_registrations g where g.session_id = p_id;
  end if;
  return p_id;
end $$;
revoke all on function public.expert_session_save(bigint, text, text, text, text, text, text, text, int, int, text, uuid) from public, anon, authenticated, service_role;
grant execute on function public.expert_session_save(bigint, text, text, text, text, text, text, text, int, int, text, uuid) to authenticated, service_role;

create or replace function public.expert_session_set_status(p_id bigint, p_status text) returns void
language plpgsql security definer set search_path = public as $$
declare s public.expert_sessions;
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin changes expert sessions' using errcode = '42501'; end if;
  if p_status not in ('cancelled', 'done') then raise exception 'Cancel it or mark it done' using errcode = '22023'; end if;
  select * into s from public.expert_sessions where id = p_id for update;
  if not found then raise exception 'This session is gone' using errcode = 'P0002'; end if;
  if s.status <> 'scheduled' then raise exception 'This session is already %', s.status using errcode = '55000'; end if;
  update public.expert_sessions set status = p_status, updated_at = now() where id = p_id;
  if p_status = 'cancelled' then
    insert into public.notifications (user_id, type, message, data)
    select g.user_id, 'expert_session', 'The expert session "' || left(s.title, 120) || '" was cancelled', jsonb_build_object('session', p_id, 'cancelled', true)
      from public.expert_registrations g where g.session_id = p_id;
  end if;
end $$;
revoke all on function public.expert_session_set_status(bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.expert_session_set_status(bigint, text) to authenticated, service_role;

-- the meeting link: for the registered (and Drugbox / the expert), from an hour before the start until it ends
create or replace function public.expert_session_link(p_id bigint) returns text
language plpgsql stable security definer set search_path = public as $$
declare s public.expert_sessions; me uuid := auth.uid();
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into s from public.expert_sessions where id = p_id;
  if not found then raise exception 'This session is gone' using errcode = 'P0002'; end if;
  if not (public.is_platform_admin() or s.expert_user = me) then
    if not exists (select 1 from public.expert_registrations g where g.session_id = p_id and g.user_id = me) then raise exception 'Register for the session to get its link' using errcode = '42501'; end if;
    if s.status <> 'scheduled' then raise exception 'This session is %', s.status using errcode = '55000'; end if;
    if now() < s.starts_at - interval '1 hour' then raise exception 'The link opens an hour before the session' using errcode = '55000'; end if;
    if now() > s.starts_at + make_interval(mins => s.minutes) then raise exception 'This session has ended — its questions and answers stay here' using errcode = '55000'; end if;
  end if;
  return s.join_url;
end $$;
revoke all on function public.expert_session_link(bigint) from public, anon, authenticated, service_role;
grant execute on function public.expert_session_link(bigint) to authenticated, service_role;

-- ── 5. Q&A ──────────────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.expert_questions (
  id           bigint generated always as identity primary key,
  session_id   bigint not null references public.expert_sessions(id) on delete cascade,
  user_id      uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  body         text not null check (length(body) between 5 and 1000),
  answer       text check (length(answer) <= 4000),
  answered_by  uuid references public.profiles(id) on delete set null,
  answered_at  timestamptz,
  hidden       boolean not null default false,
  created_at   timestamptz not null default now()
);
create index if not exists idx_expert_questions_session on public.expert_questions (session_id, created_at);
create index if not exists idx_expert_questions_user on public.expert_questions (user_id);
create index if not exists idx_expert_questions_answered_by on public.expert_questions (answered_by) where answered_by is not null;
alter table public.expert_questions enable row level security;
drop policy if exists "expert questions: members read the kept Q&A" on public.expert_questions;
create policy "expert questions: members read the kept Q&A" on public.expert_questions for select to authenticated
  using (not hidden or user_id = (select auth.uid()) or public.is_platform_admin());
drop policy if exists "expert questions: the registered ask" on public.expert_questions;
create policy "expert questions: the registered ask" on public.expert_questions for insert to authenticated
  with check (user_id = (select auth.uid())
              and exists (select 1 from public.expert_registrations g where g.session_id = expert_questions.session_id and g.user_id = (select auth.uid()))
              and exists (select 1 from public.expert_sessions s where s.id = expert_questions.session_id and s.status = 'scheduled'
                            and now() < s.starts_at + make_interval(mins => s.minutes)));
drop policy if exists "expert questions: the asker or Drugbox removes" on public.expert_questions;
create policy "expert questions: the asker or Drugbox removes" on public.expert_questions for delete to authenticated
  using (user_id = (select auth.uid()) or public.is_platform_admin());
drop policy if exists "a suspended account does not write" on public.expert_questions;
create policy "a suspended account does not write" on public.expert_questions as restrictive for insert to authenticated with check ((select private.not_suspended()));
revoke all on table public.expert_questions from public, anon, authenticated, service_role;
grant select on table public.expert_questions to anon;
grant select, delete, insert (session_id, user_id, body) on table public.expert_questions to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.expert_questions to service_role;
revoke all on sequence public.expert_questions_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.expert_questions_id_seq to authenticated, service_role;
create or replace function public.expert_questions_guard() returns trigger language plpgsql set search_path = public as $$
begin
  if public.is_server_call() then return new; end if;
  new.answer := null; new.answered_by := null; new.answered_at := null; new.hidden := false; new.created_at := now(); new.body := trim(new.body);
  return new;
end $$;
revoke all on function public.expert_questions_guard() from public, anon, authenticated, service_role;
grant execute on function public.expert_questions_guard() to service_role;
drop trigger if exists trg_expert_questions_guard on public.expert_questions;
create trigger trg_expert_questions_guard before insert on public.expert_questions for each row execute function public.expert_questions_guard();

-- Drugbox (or the session's expert, a member) answers; the asker is told
create or replace function public.expert_answer(p_question bigint, p_answer text) returns void
language plpgsql security definer set search_path = public as $$
declare q public.expert_questions; s public.expert_sessions; a text := nullif(trim(coalesce(p_answer, '')), '');
begin
  select * into q from public.expert_questions where id = p_question for update;
  if not found then raise exception 'This question is gone' using errcode = 'P0002'; end if;
  select * into s from public.expert_sessions where id = q.session_id;
  if not (public.is_platform_admin() or (s.expert_user is not null and s.expert_user = auth.uid())) then
    raise exception 'Only Drugbox or the session''s expert answers' using errcode = '42501'; end if;
  if a is null then raise exception 'Write the answer' using errcode = '22023'; end if;
  if length(a) > 4000 then raise exception 'An answer is at most 4,000 characters' using errcode = '22023'; end if;
  update public.expert_questions set answer = a, answered_by = auth.uid(), answered_at = now() where id = p_question;
  if q.user_id <> auth.uid() then
    insert into public.notifications (user_id, type, message, data)
    values (q.user_id, 'expert_answer', 'Your question in "' || left(s.title, 120) || '" was answered', jsonb_build_object('session', s.id, 'question', q.id));
  end if;
end $$;
revoke all on function public.expert_answer(bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.expert_answer(bigint, text) to authenticated, service_role;

create or replace function public.expert_question_hide(p_question bigint, p_hidden boolean) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin hides questions' using errcode = '42501'; end if;
  update public.expert_questions set hidden = coalesce(p_hidden, true) where id = p_question;
  if not found then raise exception 'This question is gone' using errcode = 'P0002'; end if;
end $$;
revoke all on function public.expert_question_hide(bigint, boolean) from public, anon, authenticated, service_role;
grant execute on function public.expert_question_hide(bigint, boolean) to authenticated, service_role;

-- the Training page: sessions (upcoming first, then past with their Q&A), with my registration
create or replace function public.expert_sessions_list(p_limit int default 30)
returns table (id bigint, topic text, title text, title_ar text, about text, expert_name text, expert_line text, starts_at timestamptz, starts_local text,
               minutes int, seats int, registered_count int, status text, registered boolean, questions int, has_link boolean)
language sql stable security definer set search_path = public as $$
  select s.id, s.topic, s.title, s.title_ar, s.about, s.expert_name, s.expert_line, s.starts_at, to_char(s.starts_at at time zone 'Africa/Cairo', 'YYYY-MM-DD HH24:MI'),
         s.minutes, s.seats, s.registered_count, s.status,
         exists (select 1 from public.expert_registrations g where g.session_id = s.id and g.user_id = auth.uid()),
         (select count(*)::int from public.expert_questions q where q.session_id = s.id and (not q.hidden or q.user_id = auth.uid())),
         s.join_url is not null
    from public.expert_sessions s
   where auth.uid() is not null and (s.status <> 'cancelled' or s.starts_at > now() - interval '7 days')
   order by (s.status = 'scheduled' and s.starts_at + make_interval(mins => s.minutes) > now()) desc,
            case when s.status = 'scheduled' and s.starts_at + make_interval(mins => s.minutes) > now() then s.starts_at end asc,
            s.starts_at desc
   limit least(greatest(coalesce(p_limit, 30), 1), 100)
$$;
revoke all on function public.expert_sessions_list(int) from public, anon, authenticated, service_role;
grant execute on function public.expert_sessions_list(int) to authenticated, service_role;

-- Admin → Expert sessions: the requests per topic with the members' notes
create or replace function public.expert_requests_admin() returns table (topic text, asked int, notes jsonb)
language sql stable security definer set search_path = public as $$
  select t.key, (select count(*)::int from public.expert_requests r where r.topic = t.key),
         coalesce((select jsonb_agg(jsonb_build_object('name', p.name, 'note', r.note, 'at', r.created_at) order by r.created_at desc)
                     from (select * from public.expert_requests r where r.topic = t.key and r.note is not null order by r.created_at desc limit 20) r
                     join public.profiles p on p.id = r.user_id), '[]'::jsonb)
    from public.expert_topics t where public.is_platform_admin() order by t.sort
$$;
revoke all on function public.expert_requests_admin() from public, anon, authenticated, service_role;
grant execute on function public.expert_requests_admin() to authenticated, service_role;

-- ── 4. reminders: growth_tick() now also sends them ─────────────────────────────────────────────────────
create or replace function private.expert_reminders() returns int
language plpgsql security definer set search_path = public as $$
declare n int := 0; k int;
begin
  with due as (update public.expert_registrations g set reminded_day = true
                 from public.expert_sessions s
                where s.id = g.session_id and s.status = 'scheduled' and not g.reminded_day
                  and s.starts_at > now() + interval '1 hour' and s.starts_at <= now() + interval '24 hours'
               returning g.user_id, s.id, s.title, s.starts_at)
  insert into public.notifications (user_id, type, message, data)
  select user_id, 'expert_reminder', 'Tomorrow: the expert session "' || left(title, 120) || '"', jsonb_build_object('session', id, 'when', 'day')
    from due;
  get diagnostics k = row_count; n := n + k;
  with due as (update public.expert_registrations g set reminded_hour = true, reminded_day = true
                 from public.expert_sessions s
                where s.id = g.session_id and s.status = 'scheduled' and not g.reminded_hour
                  and s.starts_at > now() and s.starts_at <= now() + interval '1 hour'
               returning g.user_id, s.id, s.title)
  insert into public.notifications (user_id, type, message, data)
  select user_id, 'expert_reminder', 'In an hour: the expert session "' || left(title, 120) || '" — the link is open', jsonb_build_object('session', id, 'when', 'hour')
    from due;
  get diagnostics k = row_count; n := n + k;
  return n;
end $$;
revoke all on function private.expert_reminders() from public, anon, authenticated, service_role;
grant execute on function private.expert_reminders() to service_role;

create or replace function public.growth_tick() returns jsonb
language plpgsql security definer set search_path = public as $$
declare n int := 0; r record;
begin
  for r in select id from public.channel_schedule where status = 'scheduled' and publish_at <= now() order by publish_at, id limit 50 loop
    if private.channel_publish(r.id) is not null then n := n + 1; end if;
  end loop;
  return jsonb_build_object('published', n, 'reminders', private.expert_reminders());
end $$;
revoke all on function public.growth_tick() from public, anon, authenticated, service_role;
grant execute on function public.growth_tick() to service_role;

notify pgrst, 'reload schema';
