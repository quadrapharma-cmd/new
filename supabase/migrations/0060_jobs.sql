-- ═════════════════════════════════════════════════════════════════════
-- 0060 — Jobs, the rest of the hiring loop (J-01 … J-07; J-COMMUNITY-19 … 29)
--   1. jobs           company_id (the page the job is posted for), search_text (what the keyword search matches, kept by a
--                     trigger, trigram index), a closed job's date; an expired job (deadline passed) is closed for everyone
--                     but its poster; a job I saved or applied to stays readable after it closed ("This job is closed")
--   2. jobs_search()  one call per page: the matching jobs (newest first, keyset on created_at, id) and how many match —
--                     words, department, employment types, countries, level (security invoker: the read policies decide)
--   3. applications   the employer moves an application (viewed / shortlisted / interviewed + date / hired / rejected / no_show,
--                     with an optional note to the candidate); the candidate is notified of each decision (not of "viewed");
--                     the job's company admins manage it like the poster
--   4. open to work   job_seeker_cvs (documents/cv/<uid>/…): readable by the person, and by members of a verified company while
--                     the person is open to work (signed links only — the row itself is never readable by other members)
--   5. job_alerts     a saved search; a new matching job notifies its owner once (at most 10 alerts a day per person)
-- Every table, sequence and function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. jobs ─────────────────────────────────────────────────────────────────────────────────────────────
alter table public.jobs add column if not exists company_id  bigint references public.companies(id) on delete set null;
alter table public.jobs add column if not exists search_text text;
alter table public.jobs add column if not exists closed_at   timestamptz;
create index if not exists idx_jobs_company on public.jobs (company_id) where company_id is not null;
do $$ begin
  alter table public.jobs add constraint jobs_country_chk check (country is null or country ~ '^[A-Z]{2}$');
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.jobs add constraint jobs_lists_len check (coalesce(array_length(requirements, 1), 0) <= 30 and coalesce(array_length(benefits, 1), 0) <= 30
                                                               and coalesce(array_length(tags, 1), 0) <= 20);
exception when duplicate_object then null; end $$;

-- what the search matches: title, company, place, description, tags, requirements (lower case; Arabic is unchanged by lower())
create or replace function public.jobs_search_text() returns trigger
language plpgsql set search_path = public as $$
begin
  new.search_text := lower(concat_ws(' ', new.title, new.company, new.location, new.description,
                                     array_to_string(new.tags, ' '), array_to_string(new.requirements, ' ')));
  if tg_op = 'UPDATE' and new.active is distinct from old.active then new.closed_at := case when new.active then null else now() end; end if;
  return new;
end $$;
revoke all on function public.jobs_search_text() from public, anon, authenticated, service_role;
grant execute on function public.jobs_search_text() to service_role;
drop trigger if exists trg_jobs_search_text on public.jobs;
create trigger trg_jobs_search_text before insert or update on public.jobs for each row execute function public.jobs_search_text();
update public.jobs set search_text = lower(concat_ws(' ', title, company, location, description, array_to_string(tags, ' '), array_to_string(requirements, ' ')))
 where search_text is null;
create index if not exists idx_jobs_search_trgm on public.jobs using gin (search_text gin_trgm_ops) where active;
create index if not exists idx_jobs_open_page on public.jobs (created_at desc, id desc) where active;

-- the page a job is posted for must be one the poster manages; the job then carries that page's name
create or replace function public.jobs_company_guard() returns trigger
language plpgsql set search_path = public as $$   -- invoker: is_server_call() must see the caller's role (is_company_member is a definer itself)
begin
  if public.is_server_call() then return new; end if;
  if new.company_id is not null and (tg_op = 'INSERT' or new.company_id is distinct from old.company_id) then
    if not public.is_company_member(new.company_id, array['owner', 'admin']) then
      raise exception 'You can post jobs only for a company page you manage' using errcode = '42501';
    end if;
  end if;
  if new.company_id is not null then select c.name into new.company from public.companies c where c.id = new.company_id; end if;
  return new;
end $$;
revoke all on function public.jobs_company_guard() from public, anon, authenticated, service_role;
grant execute on function public.jobs_company_guard() to service_role;
drop trigger if exists trg_jobs_company_guard on public.jobs;
create trigger trg_jobs_company_guard before insert or update on public.jobs for each row execute function public.jobs_company_guard();

-- who manages a job: its poster, or an owner / admin of the company page it is posted for
create or replace function private.can_manage_job(p_job bigint) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.jobs j where j.id = p_job
                   and (j.user_id = auth.uid() or (j.company_id is not null and public.is_company_member(j.company_id, array['owner', 'admin']))))
$$;
revoke all on function private.can_manage_job(bigint) from public, anon, authenticated, service_role;
grant execute on function private.can_manage_job(bigint) to authenticated, service_role;

-- the pages I manage and the jobs I saved or applied to, each read once per query (an init plan), never per row
create or replace function private.my_admin_companies() returns bigint[]
language sql stable security definer set search_path = public as $$
  select coalesce(array_agg(distinct x.id), '{}') from (
    select m.company_id id from public.company_members m where m.user_id = auth.uid() and m.accepted and m.role in ('owner', 'admin')
    union all select c.id from public.companies c where c.owner_id = auth.uid()) x
$$;
revoke all on function private.my_admin_companies() from public, anon, authenticated, service_role;
grant execute on function private.my_admin_companies() to authenticated, service_role;
create or replace function private.my_job_ids() returns bigint[]
language sql stable security definer set search_path = public as $$
  select coalesce(array_agg(distinct x.job_id), '{}') from (
    select s.job_id from public.saved_jobs s where s.user_id = auth.uid()
    union all select a.job_id from public.job_applications a where a.user_id = auth.uid()) x
$$;
revoke all on function private.my_job_ids() from public, anon, authenticated, service_role;
grant execute on function private.my_job_ids() to authenticated, service_role;

-- reading: an open job (not past its deadline) for every member; my own jobs always; a job I saved or applied to after it closed
drop policy if exists "jobs: everyone can read" on public.jobs;
drop policy if exists "jobs: open jobs for members" on public.jobs;
create policy "jobs: open jobs for members" on public.jobs for select to authenticated
  using (active and (deadline is null or deadline >= current_date));
drop policy if exists "jobs: saved or applied stay readable" on public.jobs;
create policy "jobs: saved or applied stay readable" on public.jobs for select to authenticated
  using (id = any (coalesce((select private.my_job_ids()), '{}'::bigint[])));
drop policy if exists "jobs: company admins manage" on public.jobs;
create policy "jobs: company admins manage" on public.jobs for all to authenticated
  using (company_id = any (coalesce((select private.my_admin_companies()), '{}'::bigint[])))
  with check (company_id = any (coalesce((select private.my_admin_companies()), '{}'::bigint[])));

-- ── 2. jobs_search ──────────────────────────────────────────────────────────────────────────────────────
-- p_q: words, each must appear (title, company, place, description, tags, requirements); p_types: full-time / part-time /
-- contract / remote (a remote job matches "remote" whatever its type); p_level as the card shows it (unknown → mid).
-- Returns {"total": n, "rows": [...]} — the rows are the page after (p_before, p_before_id), at most p_limit (1…100).
create or replace function public.jobs_search(p_q text default '', p_category text default null, p_types text[] default null,
                                              p_countries text[] default null, p_level text default null,
                                              p_before timestamptz default null, p_before_id bigint default null, p_limit int default 50)
returns jsonb language sql stable security invoker set search_path = public as $$
  with w as (select array_remove(regexp_split_to_array(lower(trim(coalesce(p_q, ''))), '\s+'), '') words),
  m as (
    select j.* from public.jobs j, w
     where j.active and (j.deadline is null or j.deadline >= current_date)
       and (p_category is null or j.category = p_category)
       and (p_countries is null or cardinality(p_countries) = 0 or j.country = any (p_countries))
       and (p_types is null or cardinality(p_types) = 0 or lower(coalesce(j.type, '')) = any (p_types) or ('remote' = any (p_types) and j.remote))
       and (p_level is null or (case when j.seniority in ('exec', 'executive') then 'exec' when j.seniority in ('entry', 'junior', 'senior') then j.seniority else 'mid' end) = p_level)
       and (cardinality(w.words) = 0 or not exists (select 1 from unnest(w.words) x where j.search_text not like '%' || replace(replace(replace(x, '\', '\\'), '%', '\%'), '_', '\_') || '%'))
  ),
  pg as (
    select * from m
     where p_before is null or (m.created_at, m.id) < (p_before, coalesce(p_before_id, 9223372036854775807))
     order by m.created_at desc, m.id desc limit least(greatest(coalesce(p_limit, 50), 1), 100)
  )
  select jsonb_build_object('total', (select count(*) from m),
    'rows', coalesce((select jsonb_agg(to_jsonb(pg) - 'search_text' || jsonb_build_object('poster', (
        select jsonb_build_object('id', p.id, 'name', p.name, 'headline', p.headline, 'company', p.company, 'avatar_url', p.avatar_url,
                                  'verified', p.verified, 'country', p.country, 'location', p.location)
          from public.profiles p where p.id = pg.user_id),
        'company_verified', (select c.status = 'verified' from public.companies c where c.id = pg.company_id),
        'company_slug', (select c.slug from public.companies c where c.id = pg.company_id))
      order by pg.created_at desc, pg.id desc) from pg), '[]'::jsonb))
$$;
revoke all on function public.jobs_search(text, text, text[], text[], text, timestamptz, bigint, int) from public, anon, authenticated, service_role;
grant execute on function public.jobs_search(text, text, text[], text[], text, timestamptz, bigint, int) to authenticated, service_role;

-- ── 3. applications ─────────────────────────────────────────────────────────────────────────────────────
alter table public.job_applications add column if not exists status_at    timestamptz default now();
alter table public.job_applications add column if not exists interview_at timestamptz;
alter table public.job_applications add column if not exists employer_note text;
do $$ begin
  alter table public.job_applications add constraint job_applications_employer_note_len check (length(employer_note) <= 1000);
exception when duplicate_object then null; end $$;
create index if not exists idx_job_apps_job_created on public.job_applications (job_id, created_at desc);

create or replace function public.job_applications_guard() returns trigger
language plpgsql set search_path = public as $$
begin
  if auth.uid() is null or current_user not in ('anon', 'authenticated') or public.is_platform_admin() then return new; end if;
  if tg_op = 'INSERT' then
    if exists (select 1 from public.jobs j where j.id = new.job_id and j.user_id = new.user_id) then raise exception 'You cannot apply to your own job' using errcode = '42501'; end if;
    if exists (select 1 from public.jobs j where j.id = new.job_id and j.company_id is not null and public.is_company_member(j.company_id)) then
      raise exception 'You cannot apply to a job of your own company' using errcode = '42501'; end if;
    if not exists (select 1 from public.jobs j where j.id = new.job_id and j.active and (j.deadline is null or j.deadline >= current_date)) then
      raise exception 'This job is no longer open' using errcode = '42501'; end if;
    new.status := 'submitted'; new.created_at := now(); new.status_at := now(); new.interview_at := null; new.employer_note := null;
    return new;
  end if;
  if new.job_id <> old.job_id or new.user_id <> old.user_id or new.created_at is distinct from old.created_at then
    raise exception 'An application cannot be moved' using errcode = '42501';
  end if;
  if auth.uid() = old.user_id then
    if new.status is distinct from old.status or new.interview_at is distinct from old.interview_at or new.employer_note is distinct from old.employer_note then
      raise exception 'The status of an application is set by the employer' using errcode = '42501'; end if;
    new.status_at := old.status_at;
  else
    if new.note is distinct from old.note or new.cv_path is distinct from old.cv_path then
      raise exception 'Only the status can be changed by the employer' using errcode = '42501'; end if;
    if new.status = 'submitted' and old.status <> 'submitted' then raise exception 'An application cannot go back to submitted' using errcode = '42501'; end if;
    if new.status = 'viewed' and old.status <> 'submitted' then new.status := old.status; end if;           -- opening it again changes nothing
    if new.status is distinct from old.status then new.status_at := now(); else new.status_at := old.status_at; end if;
  end if;
  return new;
end $$;

-- the job's company admins read and move its applications like the poster (the poster policies stay)
drop policy if exists "job_apps: company admins read" on public.job_applications;
create policy "job_apps: company admins read" on public.job_applications for select to authenticated
  using ((select private.can_manage_job(job_id)));
drop policy if exists "job_apps: company admins set the status" on public.job_applications;
create policy "job_apps: company admins set the status" on public.job_applications for update to authenticated
  using ((select private.can_manage_job(job_id))) with check ((select private.can_manage_job(job_id)));

-- the candidate hears of each decision (opening the application — "viewed" — is not a decision)
create or replace function public.notify_application_status() returns trigger
language plpgsql security definer set search_path = public as $$
declare t text; co text; msg text;
begin
  if new.status is not distinct from old.status or new.status in ('submitted', 'viewed') then return null; end if;
  select title, coalesce(nullif(company, ''), 'the employer') into t, co from public.jobs where id = new.job_id;
  msg := case new.status
    when 'shortlisted' then 'shortlisted your application for ' || t
    when 'interviewed' then 'invited you to an interview for ' || t || coalesce(' on ' || to_char(new.interview_at at time zone 'Africa/Cairo', 'DD Mon YYYY'), '')
    when 'hired'       then 'hired you for ' || t || ' — congratulations!'
    when 'rejected'    then 'thanks you for applying to ' || t || ' — they went ahead with other candidates this time'
    when 'no_show'     then 'marked your interview for ' || t || ' as missed'
    else 'updated your application for ' || t end;
  insert into public.notifications (user_id, type, from_user, job_id, message, data)
  values (new.user_id, 'job_status', auth.uid(), new.job_id, msg,
          jsonb_build_object('status', new.status, 'company', co, 'title', t, 'note', left(coalesce(new.employer_note, ''), 300),
                             'interview_at', new.interview_at));
  return null;
end $$;
revoke all on function public.notify_application_status() from public, anon, authenticated, service_role;
grant execute on function public.notify_application_status() to service_role;
drop trigger if exists trg_notify_application_status on public.job_applications;
create trigger trg_notify_application_status after update of status on public.job_applications
  for each row execute function public.notify_application_status();

-- the applicants of a job with what the employer needs to decide (one call): the person, the note, the CV path (opened through a
-- signed link — storage checks can_read_document), the status and its date, and whether the person is on my preferred list
create or replace function public.job_applicants(p_job bigint)
returns table (user_id uuid, name text, headline text, company text, location text, country text, avatar_url text, verified boolean,
               years_experience int, note text, cv_path text, status text, status_at timestamptz, interview_at timestamptz,
               employer_note text, created_at timestamptz, preferred boolean)
language sql stable security definer set search_path = public as $$
  select a.user_id, p.name, p.headline, p.company, p.location, p.country::text, p.avatar_url, p.verified, p.years_experience,
         a.note, a.cv_path, a.status, a.status_at, a.interview_at, a.employer_note, a.created_at,
         exists (select 1 from public.job_lists l where l.owner = auth.uid() and l.target = a.user_id and l.side = 'employer' and l.list = 'white')
    from public.job_applications a join public.profiles p on p.id = a.user_id
   where a.job_id = p_job and (select private.can_manage_job(p_job))
   order by 17 desc, a.created_at desc
$$;
revoke all on function public.job_applicants(bigint) from public, anon, authenticated, service_role;
grant execute on function public.job_applicants(bigint) to authenticated, service_role;

-- my applications, newest first, with the job (also a closed one) and where each stands
create or replace function public.my_applications()
returns table (job_id bigint, title text, company text, location text, country text, active boolean, deadline date,
               status text, status_at timestamptz, interview_at timestamptz, employer_note text, created_at timestamptz)
language sql stable security definer set search_path = public as $$
  select a.job_id, j.title, j.company, j.location, j.country::text, j.active and (j.deadline is null or j.deadline >= current_date), j.deadline,
         a.status, a.status_at, a.interview_at, a.employer_note, a.created_at
    from public.job_applications a join public.jobs j on j.id = a.job_id
   where a.user_id = auth.uid()
   order by a.created_at desc
   limit 200
$$;
revoke all on function public.my_applications() from public, anon, authenticated, service_role;
grant execute on function public.my_applications() to authenticated, service_role;

-- my jobs (posted by me or for a page I manage) with the number of applicants per stage
create or replace function public.my_jobs()
returns table (id bigint, title text, company text, location text, country text, type text, seniority text, category text, salary text,
               deadline date, active boolean, expired boolean, created_at timestamptz, applicant_count int, stages jsonb)
language sql stable security definer set search_path = public as $$
  select j.id, j.title, j.company, j.location, j.country::text, j.type, j.seniority, j.category, j.salary, j.deadline, j.active,
         j.deadline is not null and j.deadline < current_date, j.created_at, j.applicant_count,
         coalesce((select jsonb_object_agg(s.status, s.n) from (select a.status, count(*) n from public.job_applications a where a.job_id = j.id group by a.status) s), '{}'::jsonb)
    from public.jobs j
   where j.user_id = auth.uid() or (j.company_id is not null and public.is_company_member(j.company_id, array['owner', 'admin']))
   order by j.created_at desc
   limit 200
$$;
revoke all on function public.my_jobs() from public, anon, authenticated, service_role;
grant execute on function public.my_jobs() to authenticated, service_role;

-- ── 4. open to work: the CV a candidate publishes ───────────────────────────────────────────────────────
-- the CV a member publishes with "Post My Profile" lives in its own table, not as a profiles column: functions that return profile rows
-- with their columns named (open_candidates, 0036) keep working, and nobody but its owner reads the path
create table if not exists public.job_seeker_cvs (
  user_id    uuid primary key default auth.uid() references public.profiles(id) on delete cascade,
  cv_path    text not null,
  updated_at timestamptz not null default now(),
  constraint job_seeker_cvs_path check (cv_path like 'cv/' || user_id::text || '/%')
);
alter table public.job_seeker_cvs enable row level security;
drop policy if exists "seeker cv: own" on public.job_seeker_cvs;
create policy "seeker cv: own" on public.job_seeker_cvs for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
revoke all on table public.job_seeker_cvs from public, anon, authenticated, service_role;
grant select on table public.job_seeker_cvs to anon;                           -- no policy for anon → an empty answer (F-26)
grant select, insert, update, delete on table public.job_seeker_cvs to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.job_seeker_cvs to service_role;
create index if not exists idx_job_seeker_cvs_path on public.job_seeker_cvs (cv_path);
-- it is only ever opened through a signed link — storage asks can_read_document():
create or replace function public.can_read_document(p_name text)
returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
                   or exists (select 1 from public.job_applications a join public.jobs j on j.id = a.job_id
                               where a.cv_path = p_name and (j.user_id = auth.uid() or (j.company_id is not null and public.is_company_member(j.company_id, array['owner', 'admin']))))
                   or (exists (select 1 from public.job_seeker_cvs v join public.profiles p on p.id = v.user_id where v.cv_path = p_name and p.open_to_work)
                       and exists (select 1 from public.companies c where c.status = 'verified' and public.is_company_member(c.id)))
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin']) or public.is_moderator())
    when 'payments' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_platform_admin()
    else false end
$$;
-- an employer's view of a candidate's published CV path (members of a verified company only; else null)
create or replace function public.candidate_cv(p_user uuid) returns text
language sql stable security definer set search_path = public as $$
  select v.cv_path from public.job_seeker_cvs v join public.profiles p on p.id = v.user_id
   where v.user_id = p_user and p.open_to_work
     and (p.id = auth.uid() or exists (select 1 from public.companies c where c.status = 'verified' and public.is_company_member(c.id)))
$$;
revoke all on function public.candidate_cv(uuid) from public, anon, authenticated, service_role;
grant execute on function public.candidate_cv(uuid) to authenticated, service_role;

-- ── 5. job alerts ───────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.job_alerts (
  id         bigint generated always as identity primary key,
  user_id    uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  q          text not null default '',
  category   text,
  types      text[] not null default '{}',
  countries  text[] not null default '{}',
  level      text,
  created_at timestamptz not null default now(),
  constraint job_alerts_q_len check (length(q) <= 120),
  constraint job_alerts_cat check (category is null or category in ('regulatory', 'qaqc', 'production', 'sales', 'rd', 'other')),
  constraint job_alerts_level check (level is null or level in ('exec', 'senior', 'mid', 'junior', 'entry')),
  constraint job_alerts_lists check (cardinality(types) <= 4 and cardinality(countries) <= 10)
);
create index if not exists idx_job_alerts_user on public.job_alerts (user_id, created_at desc);
alter table public.job_alerts enable row level security;
drop policy if exists "job alerts: own" on public.job_alerts;
create policy "job alerts: own" on public.job_alerts for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
revoke all on table public.job_alerts from public, anon, authenticated, service_role;
grant select on table public.job_alerts to anon;                               -- no policy for anon → an empty answer (F-26)
grant select, insert, delete on table public.job_alerts to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.job_alerts to service_role;
revoke all on sequence public.job_alerts_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.job_alerts_id_seq to authenticated, service_role;

-- at most 20 saved searches each
create or replace function public.job_alerts_limit() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.created_at := now();                       -- user_id: the row policy refuses an alert for anyone else
  if (select count(*) from public.job_alerts where user_id = new.user_id) >= 20 then
    raise exception 'You can keep up to 20 job alerts' using errcode = '23514'; end if;
  new.q := lower(trim(new.q));
  return new;
end $$;
revoke all on function public.job_alerts_limit() from public, anon, authenticated, service_role;
grant execute on function public.job_alerts_limit() to service_role;
drop trigger if exists trg_job_alerts_limit on public.job_alerts;
create trigger trg_job_alerts_limit before insert on public.job_alerts for each row execute function public.job_alerts_limit();

create unique index if not exists idx_notifs_job_alert_once on public.notifications (user_id, job_id) where type = 'job_alert' and job_id is not null;

-- a new open job: each alert it matches notifies its owner once (the poster and blocked parties excluded), at most 10 a day each
create or replace function public.notify_job_alerts() returns trigger
language plpgsql security definer set search_path = public as $$
declare lvl text;
begin
  if not new.active then return null; end if;
  lvl := case when new.seniority in ('exec', 'executive') then 'exec' when new.seniority in ('entry', 'junior', 'senior') then new.seniority else 'mid' end;
  insert into public.notifications (user_id, type, from_user, job_id, message, data)
  select distinct on (a.user_id) a.user_id, 'job_alert', new.user_id, new.id, 'New job matching your alert: ' || new.title,
         jsonb_build_object('alert', a.id, 'q', a.q, 'title', new.title, 'company', new.company)
    from public.job_alerts a
   where a.user_id <> new.user_id
     and (a.category is null or a.category = new.category)
     and (cardinality(a.countries) = 0 or new.country = any (a.countries))
     and (cardinality(a.types) = 0 or lower(coalesce(new.type, '')) = any (a.types) or ('remote' = any (a.types) and new.remote))
     and (a.level is null or a.level = lvl)
     and (a.q = '' or not exists (select 1 from unnest(regexp_split_to_array(a.q, '\s+')) x where x <> '' and new.search_text not like '%' || replace(replace(replace(x, '\', '\\'), '%', '\%'), '_', '\_') || '%'))
     and not exists (select 1 from public.job_lists l where l.list = 'black' and (l.until is null or l.until >= current_date)
                       and ((l.owner = a.user_id and l.target = new.user_id) or (l.owner = new.user_id and l.target = a.user_id)))
     and (select count(*) from public.notifications n where n.user_id = a.user_id and n.type = 'job_alert' and n.created_at > now() - interval '1 day') < 10
  on conflict do nothing;
  return null;
end $$;
revoke all on function public.notify_job_alerts() from public, anon, authenticated, service_role;
grant execute on function public.notify_job_alerts() to service_role;
drop trigger if exists trg_notify_job_alerts on public.jobs;
create trigger trg_notify_job_alerts after insert on public.jobs for each row execute function public.notify_job_alerts();

notify pgrst, 'reload schema';
