-- Jobs (0060): posting for a company page, search, the application pipeline (employer, company admin, plain member, outsider, the
-- candidate), withdraw, closed / expired / saved jobs, the published CV, job alerts. Runs as the real API roles with a JWT, in one
-- transaction that is rolled back; test data carries the "JB " marker. Run on a fresh database (stub + migrations): psql -f supabase/tests/jobs.rls.sql
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
-- server-side work (imports, the service role, an operator in psql): no JWT
create function pg_temp.as_server() returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', '', true); perform set_config('request.jwt.claims', '', true); perform set_config('role', 'none', true); end $$;
create function pg_temp.ok(p_name text, q text) returns void language plpgsql as $$ declare b boolean; begin
  execute 'select (' || q || ')::boolean' into b; insert into r(name, ok) values (p_name, coalesce(b, false));
  exception when others then insert into r(name, ok, err) values (p_name, false, sqlstate || ': ' || sqlerrm); end $$;
create function pg_temp.step(p_name text, q text) returns void language plpgsql as $$ begin execute q;
  exception when others then insert into r(name, ok, err) values ('step: ' || p_name, false, sqlstate || ': ' || sqlerrm); end $$;
-- the statement must be refused with this SQLSTATE; if it is allowed its effects are rolled back and the check fails
create function pg_temp.no(p_name text, q text, st text) returns void language plpgsql as $$ begin
  execute q; raise exception 'the statement was allowed' using errcode = 'DB001';
  exception when others then insert into r(name, ok, err) values (p_name, sqlstate = st, case when sqlstate <> st then sqlstate || ': ' || sqlerrm end); end $$;
create function pg_temp.id(k text) returns bigint language sql stable as $$ select v::bigint from ids where ids.k = id.k $$;

create function pg_temp.g() returns text language sql stable as $$ select v from ids where k = 'group' $$;

-- E employer (owner of a verified page), A admin of that page, M plain member of it, S candidate, O outsider (owns an unverified page)
insert into auth.users (id, email) values ('a1000000-0000-0000-0000-000000000001','jb-e@x'),('a1000000-0000-0000-0000-000000000002','jb-a@x'),('a1000000-0000-0000-0000-000000000003','jb-m@x'),
  ('a1000000-0000-0000-0000-000000000004','jb-s@x'),('a1000000-0000-0000-0000-000000000005','jb-o@x') on conflict do nothing;
insert into public.profiles (id, name) values ('a1000000-0000-0000-0000-000000000001','JB Employer'),('a1000000-0000-0000-0000-000000000002','JB Admin'),('a1000000-0000-0000-0000-000000000003','JB Member'),
  ('a1000000-0000-0000-0000-000000000004','JB Seeker'),('a1000000-0000-0000-0000-000000000005','JB Outsider') on conflict (id) do nothing;
create function pg_temp.E() returns void language sql as $$ select pg_temp.as_user('a1000000-0000-0000-0000-000000000001') $$;
create function pg_temp.A() returns void language sql as $$ select pg_temp.as_user('a1000000-0000-0000-0000-000000000002') $$;
create function pg_temp.M() returns void language sql as $$ select pg_temp.as_user('a1000000-0000-0000-0000-000000000003') $$;
create function pg_temp.S() returns void language sql as $$ select pg_temp.as_user('a1000000-0000-0000-0000-000000000004') $$;
create function pg_temp.O() returns void language sql as $$ select pg_temp.as_user('a1000000-0000-0000-0000-000000000005') $$;
select pg_temp.E();
select pg_temp.step('E creates its company page', $$insert into public.companies (name, type, slug) values ('JB Pharma','Manufacturer','jb-pharma')$$);
select pg_temp.O();
select pg_temp.step('O creates its company page', $$insert into public.companies (name, type, slug) values ('JB Other','Manufacturer','jb-other')$$);
select pg_temp.as_server();
select pg_temp.step('Drugbox verifies JB Pharma', $$update public.companies set status = 'verified' where slug = 'jb-pharma'$$);
select pg_temp.step('A is an admin, M a member of JB Pharma', $$insert into public.company_members (company_id, user_id, role, accepted) select id, 'a1000000-0000-0000-0000-000000000002'::uuid, 'admin', true from public.companies where slug = 'jb-pharma'
  union all select id, 'a1000000-0000-0000-0000-000000000003'::uuid, 'member', true from public.companies where slug = 'jb-pharma'$$);
insert into ids select 'co', id::text from public.companies where slug = 'jb-pharma';

-- 1. posting
select pg_temp.O();
select pg_temp.no('O cannot post a job for JB Pharma', $$insert into public.jobs (user_id, title, company_id) values ('a1000000-0000-0000-0000-000000000005', 'JB Fake', pg_temp.id('co'))$$, '42501');
select pg_temp.E();
select pg_temp.step('E posts a job for its page', $$with x as (insert into public.jobs (user_id, title, company, company_id, location, country, type, seniority, category, description, tags, requirements)
  values ('a1000000-0000-0000-0000-000000000001', 'JB HPLC Analyst', 'whatever', pg_temp.id('co'), 'Alexandria', 'EG', 'full-time', 'junior', 'qaqc', 'Method validation', '{GMP}', '{"Pharmacy degree"}') returning id) insert into ids select 'job', id::text from x$$);
select pg_temp.ok('the job carries the page''s own name', $$(select company = 'JB Pharma' from public.jobs where id = pg_temp.id('job'))$$);
select pg_temp.step('E posts a Dubai contract job', $$with x as (insert into public.jobs (user_id, title, company_id, location, country, type, category) values ('a1000000-0000-0000-0000-000000000001', 'JB Sales Rep', pg_temp.id('co'), 'Dubai', 'AE', 'contract', 'sales') returning id) insert into ids select 'job2', id::text from x$$);
select pg_temp.no('a country code must be two capital letters', $$insert into public.jobs (user_id, title, country) values ('a1000000-0000-0000-0000-000000000001', 'JB Bad', 'eg')$$, '23514');
-- 2. search
select pg_temp.S();
select pg_temp.ok('search: words match title + tags + requirements, any case', $$(public.jobs_search('jb hplc gmp pharmacy') ->> 'total')::int = 1$$);
select pg_temp.ok('search: the filters combine (QA/QC + full-time + Egypt + junior)', $$(public.jobs_search('jb', 'qaqc', array['full-time'], array['EG'], 'junior') ->> 'total')::int = 1$$);
select pg_temp.ok('search: a contract job is not full-time; a UAE job is not Egypt', $$(public.jobs_search('jb', null, array['full-time'], array['AE']) ->> 'total')::int = 0$$);
select pg_temp.ok('search: the page is ordered and limited, the total counts all', $$jsonb_array_length(public.jobs_search('jb', p_limit => 1) -> 'rows') = 1 and (public.jobs_search('jb', p_limit => 1) ->> 'total')::int = 2$$);
select pg_temp.ok('search rows never carry search_text', $$not ((public.jobs_search('jb') -> 'rows' -> 0) ? 'search_text')$$);
select pg_temp.ok('search: a wildcard in the words is plain text', $$(public.jobs_search('%') ->> 'total')::int = 0$$);
-- 3. applying and the pipeline
select pg_temp.step('S saves the Dubai job', $$insert into public.saved_jobs (user_id, job_id) values ('a1000000-0000-0000-0000-000000000004', pg_temp.id('job2'))$$);
select pg_temp.step('S applies (trying to set its own status)', $$insert into public.job_applications (job_id, user_id, note, status) values (pg_temp.id('job'), 'a1000000-0000-0000-0000-000000000004', 'JB please', 'hired')$$);
select pg_temp.ok('the database starts it as submitted', $$(select status = 'submitted' from public.job_applications where job_id = pg_temp.id('job'))$$);
select pg_temp.no('S cannot move its own application', $$update public.job_applications set status = 'hired' where job_id = pg_temp.id('job')$$, '42501');
select pg_temp.M();
select pg_temp.no('a member of the company cannot apply to its job', $$insert into public.job_applications (job_id, user_id) values (pg_temp.id('job'), 'a1000000-0000-0000-0000-000000000003')$$, '42501');
select pg_temp.ok('a plain member does not read the applications', $$(select count(*) = 0 from public.job_applications where job_id = pg_temp.id('job'))$$);
select pg_temp.ok('…nor through job_applicants()', $$(select count(*) = 0 from public.job_applicants(pg_temp.id('job')))$$);
select pg_temp.O();
select pg_temp.ok('an outsider reads no application', $$(select count(*) = 0 from public.job_applications where job_id = pg_temp.id('job'))$$);
select pg_temp.ok('an outsider gets no applicant', $$(select count(*) = 0 from public.job_applicants(pg_temp.id('job')))$$);
select pg_temp.step('an outsider''s status update changes nothing', $$update public.job_applications set status = 'rejected' where job_id = pg_temp.id('job')$$);
select pg_temp.E();
select pg_temp.ok('E lists the applicant with the note', $$(select note = 'JB please' and user_id = 'a1000000-0000-0000-0000-000000000004' from public.job_applicants(pg_temp.id('job')))$$);
select pg_temp.step('E opens it (viewed)', $$update public.job_applications set status = 'viewed' where job_id = pg_temp.id('job')$$);
select pg_temp.ok('opening it marks it viewed, no notification', $$(select status = 'viewed' from public.job_applications where job_id = pg_temp.id('job'))
  and not exists (select 1 from public.notifications where user_id = 'a1000000-0000-0000-0000-000000000004' and type = 'job_status')$$);
select pg_temp.no('E cannot change the candidate''s note', $$update public.job_applications set note = 'x' where job_id = pg_temp.id('job')$$, '42501');
select pg_temp.A();
select pg_temp.step('the page admin invites S to an interview with a note', $$update public.job_applications set status = 'interviewed', interview_at = '2026-11-02 10:00+02', employer_note = 'JB room 3' where job_id = pg_temp.id('job')$$);
select pg_temp.ok('the page admin moved it', $$(select status = 'interviewed' and employer_note = 'JB room 3' from public.job_applications where job_id = pg_temp.id('job'))$$);
select pg_temp.no('an application never goes back to submitted', $$update public.job_applications set status = 'submitted' where job_id = pg_temp.id('job')$$, '42501');
select pg_temp.S();
select pg_temp.ok('S is notified once of the interview (with the date and note)', $$(select count(*) = 1 from public.notifications where user_id = 'a1000000-0000-0000-0000-000000000004' and type = 'job_status' and data ->> 'status' = 'interviewed' and data ->> 'note' = 'JB room 3')$$);
select pg_temp.ok('My applications shows it with its status', $$(select status = 'interviewed' and title = 'JB HPLC Analyst' from public.my_applications() where job_id = pg_temp.id('job'))$$);
select pg_temp.E();
select pg_temp.ok('my_jobs counts per stage', $$(select (stages ->> 'interviewed')::int = 1 and applicant_count = 1 from public.my_jobs() where id = pg_temp.id('job'))$$);
select pg_temp.M();
select pg_temp.ok('a plain member does not see the page''s jobs in my_jobs', $$(select count(*) = 0 from public.my_jobs() where id = pg_temp.id('job'))$$);
-- 4. closed, expired and saved jobs
select pg_temp.E();
select pg_temp.step('E closes the Dubai job and lets the first one expire', $$update public.jobs set active = false where id = pg_temp.id('job2'); update public.jobs set deadline = current_date - 1 where id = pg_temp.id('job')$$);
select pg_temp.ok('a closed job has its closing date', $$(select closed_at is not null from public.jobs where id = pg_temp.id('job2'))$$);
select pg_temp.ok('E still reads its own closed and expired jobs', $$(select count(*) = 2 from public.jobs where id in (pg_temp.id('job'), pg_temp.id('job2')))$$);
select pg_temp.O();
select pg_temp.ok('an outsider does not read the closed or the expired job', $$(select count(*) = 0 from public.jobs where id in (pg_temp.id('job'), pg_temp.id('job2')))$$);
select pg_temp.no('nobody applies to an expired job', $$insert into public.job_applications (job_id, user_id) values (pg_temp.id('job'), 'a1000000-0000-0000-0000-000000000005')$$, '42501');
select pg_temp.S();
select pg_temp.ok('S reads the closed job it saved and the expired one it applied to', $$(select count(*) = 2 from public.jobs where id in (pg_temp.id('job'), pg_temp.id('job2')))$$);
select pg_temp.ok('search no longer finds them', $$(public.jobs_search('jb') ->> 'total')::int = 0$$);
-- 5. withdraw: the employer no longer reads it (nor its CV)
select pg_temp.step('S withdraws', $$delete from public.job_applications where job_id = pg_temp.id('job')$$);
select pg_temp.E();
select pg_temp.ok('E reads no application after the withdrawal', $$(select count(*) = 0 from public.job_applications where job_id = pg_temp.id('job'))$$);
-- 6. the published CV
select pg_temp.S();
select pg_temp.no('the CV path must be in S''s own folder', $$insert into public.job_seeker_cvs (cv_path) values ('cv/a1000000-0000-0000-0000-000000000005/x.pdf')$$, '23514');
select pg_temp.no('nobody files a CV for someone else', $$insert into public.job_seeker_cvs (user_id, cv_path) values ('a1000000-0000-0000-0000-000000000005', 'cv/a1000000-0000-0000-0000-000000000005/x.pdf')$$, '42501');
select pg_temp.step('S publishes its profile with a CV', $$update public.profiles set open_to_work = true, desired_role = 'JB QC Chemist' where id = 'a1000000-0000-0000-0000-000000000004';
  insert into public.job_seeker_cvs (cv_path) values ('cv/a1000000-0000-0000-0000-000000000004/p.pdf')$$);
select pg_temp.ok('S reads its own CV row', $$(select cv_path like 'cv/a1000000-0000-0000-0000-000000000004/%' from public.job_seeker_cvs)$$);
select pg_temp.O();
select pg_temp.ok('other members read no CV row', $$(select count(*) = 0 from public.job_seeker_cvs)$$);
select pg_temp.ok('open_candidates lists S with its desired role', $$(select desired_role = 'JB QC Chemist' from public.open_candidates(100) where id = 'a1000000-0000-0000-0000-000000000004')$$);
select pg_temp.ok('a member of an unverified page gets no CV', $$public.candidate_cv('a1000000-0000-0000-0000-000000000004') is null and not public.can_read_document('cv/a1000000-0000-0000-0000-000000000004/p.pdf')$$);
select pg_temp.M();
select pg_temp.ok('a member of a verified page gets the CV (signed link)', $$public.candidate_cv('a1000000-0000-0000-0000-000000000004') is not null and public.can_read_document('cv/a1000000-0000-0000-0000-000000000004/p.pdf')$$);
select pg_temp.S();
select pg_temp.step('S hides its profile', $$update public.profiles set open_to_work = false where id = 'a1000000-0000-0000-0000-000000000004'$$);
select pg_temp.M();
select pg_temp.ok('a hidden profile''s CV is no longer readable', $$public.candidate_cv('a1000000-0000-0000-0000-000000000004') is null and not public.can_read_document('cv/a1000000-0000-0000-0000-000000000004/p.pdf')$$);
-- 7. job alerts
select pg_temp.S();
select pg_temp.step('S saves a search: hplc in Egypt', $$insert into public.job_alerts (q, countries) values ('  HPLC ', '{EG}')$$);
select pg_temp.ok('the alert is S''s, its words lower-cased', $$(select user_id = 'a1000000-0000-0000-0000-000000000004' and q = 'hplc' from public.job_alerts)$$);
select pg_temp.no('an alert for someone else is refused', $$insert into public.job_alerts (user_id, q) values ('a1000000-0000-0000-0000-000000000005', 'x')$$, '42501');
select pg_temp.O();
select pg_temp.ok('an outsider reads no alert of S', $$(select count(*) = 0 from public.job_alerts)$$);
select pg_temp.E();
select pg_temp.step('E posts a matching and a non-matching job', $$insert into public.jobs (user_id, title, company_id, country, tags) values ('a1000000-0000-0000-0000-000000000001', 'JB HPLC Lead', pg_temp.id('co'), 'EG', '{}'), ('a1000000-0000-0000-0000-000000000001', 'JB HPLC Dubai', pg_temp.id('co'), 'AE', '{}')$$);
select pg_temp.S();
select pg_temp.ok('S is notified once, of the matching job only', $$(select count(*) = 1 and min(data ->> 'title') = 'JB HPLC Lead' from public.notifications where user_id = 'a1000000-0000-0000-0000-000000000004' and type = 'job_alert')$$);
select pg_temp.as_anon();
select pg_temp.ok('anon reads no job and no alert', $$(select count(*) = 0 from public.jobs) and (select count(*) = 0 from public.job_alerts)$$);
select pg_temp.no('anon cannot search', $$select public.jobs_search('jb')$$, '42501');

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
