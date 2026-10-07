-- 0021 — trust layer, company hub, deals engine, groups: every finding's reproduction must now be refused, every normal flow still works.
-- Runs as the real API roles (authenticated / anon) with a JWT, in one transaction that is rolled back. Run it on a fresh database
-- (stub + migrations), like the other suites: psql -f supabase/tests/trust_hub_deals.rls.sql
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
create function pg_temp.u(n int) returns uuid language sql immutable as $$ select ('d2000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid $$;

-- people: u1 owner of a verified company (posts a job), u2 its HR member, u3 candidate, u4 outsider, u5 Drugbox admin, u6 moderator,
--         u7 owner of a verified supplier and of a second (pending) company, u8 invited member, u9 the verified company's team admin,
--         u10 owner of a pending company only
insert into auth.users (id, email) select pg_temp.u(g), 'u' || g || '@t21.test' from generate_series(1, 10) g on conflict do nothing;
insert into public.profiles (id, name) select pg_temp.u(g), 'T21 person ' || g from generate_series(1, 10) g on conflict (id) do nothing;
update public.profiles set role = 'admin' where id = pg_temp.u(5);
update public.profiles set role = 'moderator' where id = pg_temp.u(6);
update public.profiles set open_to_work = true, experience = '[{"company":"T21 Verified Co","title":"QC Analyst"},{"company":"T21 D Co","title":"QC"}]'::jsonb where id = pg_temp.u(3);
update public.profiles set open_to_work = true where id = pg_temp.u(4);
update public.profiles set open_to_work = true, experience = '[{"company":"T21 Verified","title":"QC"}]'::jsonb where id = pg_temp.u(8);
insert into public.companies (owner_id, name, slug, type, status, registry, licensed) values
  (pg_temp.u(1), 'T21 Verified Co', 't21-vco', 'Manufacturer', 'verified', '111222', true),
  (pg_temp.u(7), 'T21 B Co', 't21-bco', 'Supplier', 'verified', '333444', false),
  (pg_temp.u(7), 'T21 C Co', 't21-cco', 'Manufacturer', 'pending', null, false),
  (pg_temp.u(10), 'T21 D Co', 't21-dco', 'Manufacturer', 'pending', null, false),
  (null, 'T21 Ghost Pharma', 't21-ghost', 'Manufacturer', 'unclaimed', null, false);
insert into ids select replace(slug, 't21-', ''), id::text from public.companies where slug like 't21-%';
insert into public.company_members (company_id, user_id, role, accepted, show_public) values
  (pg_temp.id('vco'), pg_temp.u(2), 'hr', true, true), (pg_temp.id('vco'), pg_temp.u(9), 'admin', true, true);
insert into public.company_sites (company_id, name, type) values (pg_temp.id('vco'), 'T21 VCo plant', 'factory'), (pg_temp.id('bco'), 'T21 BCo plant', 'factory');
insert into ids select 'vsite', id::text from public.company_sites where name = 'T21 VCo plant';
insert into ids select 'bsite', id::text from public.company_sites where name = 'T21 BCo plant';
insert into public.company_documents (company_id, type, product, number, created_by, file_path) values (pg_temp.id('vco'), 'CEP', 'Metformin HCl', 'T21-CEP-1', pg_temp.u(1), 'verification/x/cep.pdf');
insert into public.jobs (user_id, title, company, category, active) values (pg_temp.u(1), 'T21 QC Analyst', 'T21 Verified Co', 'qaqc', true), (pg_temp.u(1), 'T21 Closed job', 'T21 Verified Co', 'qaqc', false);
insert into ids select 'job', id::text from public.jobs where title = 'T21 QC Analyst';
insert into ids select 'closedjob', id::text from public.jobs where title = 'T21 Closed job';
insert into storage.objects (bucket_id, name) values ('reference-evidence', 'd2000000-0000-0000-0000-000000000002/ev.pdf');

-- ══ F-10 / F-34: reviews after a real interaction ═══════════════════════════════════════════
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.step('the outsider sends one unsolicited message', $$insert into public.messages (sender_id, receiver_id, body) values (pg_temp.u(4), pg_temp.u(1), 'hi')$$);
select pg_temp.no('F-10 one unsolicited message is not an interaction (anonymous employer review refused)',
  $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body, anonymous) values (pg_temp.u(4), pg_temp.u(1), 'employer', 1,1,1,1, 'Terrible employer, never pays, avoid at all costs', true)$$, '42501');
select pg_temp.ok('F-10 my_interactions() does not list someone I only messaged', $$not exists (select 1 from public.my_interactions() where party = pg_temp.u(1))$$);
select pg_temp.no('F-10 a review under role employer of someone who posted no job is refused',
  $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body) values (pg_temp.u(4), pg_temp.u(3), 'employer', 1,1,1,1, 'Terrible employer, never pays, avoid at all costs')$$, '42501');
-- the candidate applies → may review the employer (anonymously); the employer may review the candidate (signed)
select pg_temp.as_user('d2000000-0000-0000-0000-000000000003');
select pg_temp.step('the candidate applies', $$insert into public.job_applications (job_id, user_id, note) values (pg_temp.id('job'), pg_temp.u(3), 'Interested')$$);
select pg_temp.step('the applicant reviews the employer anonymously',
  $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body, anonymous) values (pg_temp.u(3), pg_temp.u(1), 'employer', 5,4,5,4, 'Fast, transparent hiring; the salary range was shared up front.', true)$$);
select pg_temp.ok('F-10 an applicant reviews the employer anonymously (application = real interaction)', $$exists (select 1 from public.job_reviews where reviewer = pg_temp.u(3) and reviewee = pg_temp.u(1) and anonymous)$$);
select pg_temp.ok('F-10 my_interactions() lists the employer for the applicant', $$exists (select 1 from public.my_interactions() where party = pg_temp.u(1))$$);
select pg_temp.step('the applicant edits the review (upsert path of the app)',
  $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body, anonymous) values (pg_temp.u(3), pg_temp.u(1), 'employer', 5,5,5,4, 'Fast, transparent hiring; the salary range was shared up front!', true)
    on conflict (reviewer, reviewee, reviewee_role) do update set c2 = excluded.c2, body = excluded.body$$);
select pg_temp.ok('F-10 …the edit is stored on the same review', $$(select c2 = 5 and body like '%up front!' from public.job_reviews where reviewer = pg_temp.u(3) and reviewee = pg_temp.u(1))$$);
select pg_temp.no('F-10 the same person cannot be reviewed twice under the other role',
  $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body) values (pg_temp.u(3), pg_temp.u(1), 'candidate', 1,1,1,1, 'Second review of the same person under another role')$$, '23505');
select pg_temp.no('F-10 a self review is refused',
  $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body) values (pg_temp.u(3), pg_temp.u(3), 'employer', 5,5,5,5, 'I am great, really great, hire me')$$, '42501');
select pg_temp.step('the reviewer tries to hide their own review', $$update public.job_reviews set hidden = true where reviewer = pg_temp.u(3)$$);
select pg_temp.ok('F-34 the reviewer cannot set hidden (kept by the database)', $$(select not hidden from public.job_reviews where reviewer = pg_temp.u(3))$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.step('the employer reviews the applicant (signed)',
  $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body) values (pg_temp.u(1), pg_temp.u(3), 'candidate', 5,5,4,5, 'Reliable analyst, strong HPLC skills, always on time.')$$);
select pg_temp.ok('F-10 the employer reviews the applicant (signed)', $$exists (select 1 from public.job_reviews where reviewer = pg_temp.u(1) and reviewee = pg_temp.u(3))$$);
select pg_temp.no('F-10 an anonymous review of a candidate is still refused',
  $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body, anonymous) values (pg_temp.u(1), pg_temp.u(3), 'candidate', 1,1,1,1, 'Anonymous attack on a candidate is not allowed', true)
    on conflict (reviewer, reviewee, reviewee_role) do update set anonymous = true$$, '23514');
select pg_temp.step('the reviewee tries to delete a review about them', $$delete from public.job_reviews where reviewee = pg_temp.u(1)$$);
select pg_temp.ok('F-34 the reviewee cannot delete a review about them', $$exists (select 1 from public.get_reviews(pg_temp.u(1), 'employer'))$$);
select pg_temp.ok('F-10 the public label "Verified applicant" comes from a real application', $$(select author from public.get_reviews(pg_temp.u(1), 'employer') limit 1) = 'Verified applicant'$$);
-- a connection with messages BOTH ways is an interaction; one way is not
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.step('the outsider asks to connect', $$insert into public.connections (requester, addressee, status) values (pg_temp.u(4), pg_temp.u(1), 'pending')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.step('the employer accepts', $$update public.connections set status = 'accepted' where requester = pg_temp.u(4) and addressee = pg_temp.u(1)$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.no('F-10 connection + a one-way message: still no review',
  $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body, anonymous) values (pg_temp.u(4), pg_temp.u(1), 'employer', 1,1,1,1, 'Terrible employer, never pays, avoid at all costs', true)$$, '42501');
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.step('the employer writes back', $$insert into public.messages (sender_id, receiver_id, body) values (pg_temp.u(1), pg_temp.u(4), 'hello back')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.step('the contact reviews the employer',
  $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body, anonymous) values (pg_temp.u(4), pg_temp.u(1), 'employer', 3,3,3,3, 'We talked at length about a role; a fair and clear process.', true)$$);
select pg_temp.ok('F-10 connection + messages both ways = real interaction (review stored)', $$exists (select 1 from public.job_reviews where reviewer = pg_temp.u(4) and reviewee = pg_temp.u(1))$$);
select pg_temp.ok('F-10 …and its anonymous label is "Anonymous", not "Verified applicant"', $$(select author from public.get_reviews(pg_temp.u(1), 'employer') where mine) = 'Anonymous'$$);
select pg_temp.no('F-34 a non-moderator cannot hide a review', $$select public.moderate_review((select id from public.job_reviews where reviewer = pg_temp.u(4)), true)$$, '42501');
select pg_temp.as_user('d2000000-0000-0000-0000-000000000006');
select pg_temp.ok('F-34 a moderator sees the raw reviews', $$(select count(*) from public.job_reviews where reviewer in (pg_temp.u(1), pg_temp.u(3), pg_temp.u(4))) = 3$$);
select pg_temp.step('the moderator hides the applicant''s review', $$select public.moderate_review((select id from public.job_reviews where reviewer = pg_temp.u(3)), true)$$);
select pg_temp.ok('F-34 moderate_review() hides it and the getters drop it', $$(select hidden from public.job_reviews where reviewer = pg_temp.u(3))
  and not exists (select 1 from public.get_reviews(pg_temp.u(1), 'employer') where author = 'Verified applicant')
  and not exists (select 1 from public.get_reviews_many(array[pg_temp.u(1)], 'employer') where c1 = 5)$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000003');
select pg_temp.step('the reviewer edits the hidden review', $$update public.job_reviews set body = 'Fast, transparent hiring; the salary range was shared up front. Edited.' where reviewer = pg_temp.u(3)$$);
select pg_temp.ok('F-34 the reviewer editing their review cannot un-hide it', $$(select hidden from public.job_reviews where reviewer = pg_temp.u(3))$$);
select pg_temp.as_anon();
select pg_temp.no('F-10 anon cannot write a review', $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body) values (pg_temp.u(4), pg_temp.u(1), 'employer', 1,1,1,1, 'Anonymous visitor review attempt, forty chars')$$, '42501');
select pg_temp.no('F-10 anon cannot ask can_review() (no interaction oracle)', $$select public.can_review(pg_temp.u(3), pg_temp.u(1), 'employer')$$, '42501');
select pg_temp.no('F-34 anon cannot moderate reviews', $$select public.moderate_review(1, false)$$, '42501');
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.no('F-10 has_real_interaction() is internal (authenticated cannot call it)', $$select public.has_real_interaction(pg_temp.u(3), pg_temp.u(1))$$, '42501');
select pg_temp.ok('F-10 can_review() answers only about the caller', $$not public.can_review(pg_temp.u(3), pg_temp.u(1), 'employer')$$);

-- ══ F-35: a block never reveals who blocked you ═════════════════════════════════════════════
select pg_temp.as_user('d2000000-0000-0000-0000-000000000003');
select pg_temp.ok('F-35 open_candidates() lists the outsider before any block', $$exists (select 1 from public.open_candidates(100) where id = pg_temp.u(4))$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.step('the employer blacklists the outsider', $$insert into public.job_lists (owner, target, side, list, reason) values (pg_temp.u(1), pg_temp.u(4), 'employer', 'black', 'Spam or scam')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.ok('F-35 jobs_hidden_for_me() does not name the person who blocked me', $$not exists (select 1 from public.jobs_hidden_for_me() where party = pg_temp.u(1))$$);
select pg_temp.ok('F-35 the helper that knows both directions is not an RPC (not in the exposed schema)', $$not exists (select 1 from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public' and p.proname in ('blocked_parties', 'jobs_blocked_with'))$$);
select pg_temp.ok('F-35 …but their jobs are simply not there for me', $$(select count(*) from public.jobs where id = pg_temp.id('job')) = 0$$);
select pg_temp.ok('F-35 …and they are not in my interactions any more', $$not exists (select 1 from public.my_interactions() where party = pg_temp.u(1))$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000003');
select pg_temp.ok('F-35 everyone else still sees the job and the outsider', $$(select count(*) from public.jobs where id = pg_temp.id('job')) = 1 and exists (select 1 from public.open_candidates(100) where id = pg_temp.u(4))$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.ok('F-35 the employer sees their own job; open_candidates() hides the blocked person', $$(select count(*) from public.jobs where id = pg_temp.id('job')) = 1 and not exists (select 1 from public.open_candidates(100) where id = pg_temp.u(4))$$);
select pg_temp.as_anon();
select pg_temp.ok('F-35 an anonymous visitor still reads open jobs', $$(select count(*) from public.jobs where id = pg_temp.id('job')) = 1$$);

-- ══ F-28: the applicant cannot set the status; the poster can ═══════════════════════════════
select pg_temp.as_user('d2000000-0000-0000-0000-000000000003');
select pg_temp.no('F-28 the applicant cannot set their own status', $$update public.job_applications set status = 'hired' where user_id = pg_temp.u(3)$$, '42501');
select pg_temp.step('the applicant edits their note', $$update public.job_applications set note = 'Interested — updated' where user_id = pg_temp.u(3)$$);
select pg_temp.ok('F-28 the applicant edits their note', $$(select note from public.job_applications where user_id = pg_temp.u(3)) = 'Interested — updated'$$);
select pg_temp.no('F-28 cannot apply to a closed job', $$insert into public.job_applications (job_id, user_id) values (pg_temp.id('closedjob'), pg_temp.u(3))$$, '42501');
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.no('F-28 cannot apply to your own job', $$insert into public.job_applications (job_id, user_id) values (pg_temp.id('job'), pg_temp.u(1))$$, '42501');
select pg_temp.step('the poster shortlists the applicant', $$update public.job_applications set status = 'shortlisted' where job_id = pg_temp.id('job') and user_id = pg_temp.u(3)$$);
select pg_temp.ok('F-28 the poster shortlists the applicant', $$(select status from public.job_applications where user_id = pg_temp.u(3)) = 'shortlisted'$$);
select pg_temp.no('F-28 the poster cannot rewrite the applicant''s note', $$update public.job_applications set note = 'rewritten' where user_id = pg_temp.u(3)$$, '42501');
select pg_temp.no('F-28 an application cannot be moved to another job', $$update public.job_applications set job_id = pg_temp.id('closedjob') where user_id = pg_temp.u(3)$$, '42501');
select pg_temp.as_user('d2000000-0000-0000-0000-000000000008');
select pg_temp.step('applying with status "hired"', $$insert into public.job_applications (job_id, user_id, status) values (pg_temp.id('job'), pg_temp.u(8), 'hired')$$);
select pg_temp.ok('F-28 applying with status "hired" is stored as "submitted"', $$(select status from public.job_applications where user_id = pg_temp.u(8)) = 'submitted'$$);
select pg_temp.step('the applicant withdraws', $$delete from public.job_applications where user_id = pg_temp.u(8)$$);
select pg_temp.ok('F-28 the applicant withdraws (deletes) their application', $$(select count(*) from public.job_applications where user_id = pg_temp.u(8)) = 0$$);
select pg_temp.as_anon();
select pg_temp.no('F-28 anon cannot apply', $$insert into public.job_applications (job_id, user_id) values (pg_temp.id('job'), pg_temp.u(4))$$, '42501');

-- ══ F-11: work references from the team of a verified company the person lists ═════════════
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.step('the outsider sets profiles.company to a wildcard', $$update public.profiles set company = '%%' where id = pg_temp.u(4)$$);
select pg_temp.no('F-11 profiles.company = ''%%'' no longer lets anyone publish an honour record',
  $$insert into public.work_references (author, candidate, kind, role_title, from_month, to_month, body) values (pg_temp.u(4), pg_temp.u(3), 'honor', 'QC Analyst', '2022-01-01', '2025-12-01', 'Fake honour record written by someone with no company at all, forty chars')$$, '42501');
select pg_temp.as_user('d2000000-0000-0000-0000-000000000010');
select pg_temp.no('F-11 the owner of a company that is not verified cannot write references (even if the person lists it)',
  $$insert into public.work_references (author, candidate, kind, role_title, from_month, to_month, body) values (pg_temp.u(10), pg_temp.u(3), 'honor', 'QC Analyst', '2022-01-01', '2025-12-01', 'Honour record from a pending company, which is not allowed before verification')$$, '42501');
select pg_temp.as_user('d2000000-0000-0000-0000-000000000007');
select pg_temp.no('F-11 a verified company the person never listed cannot write about them',
  $$insert into public.work_references (author, candidate, kind, role_title, from_month, to_month, body) values (pg_temp.u(7), pg_temp.u(3), 'honor', 'QC Analyst', '2022-01-01', '2025-12-01', 'Honour record from a verified company this person never worked for, refused')$$, 'P0001');
select pg_temp.as_user('d2000000-0000-0000-0000-000000000002');
select pg_temp.no('F-11 "T21 Verified" is not "T21 Verified Co": no substring matching',
  $$insert into public.work_references (author, candidate, kind, role_title, from_month, to_month, body) values (pg_temp.u(2), pg_temp.u(8), 'honor', 'QC', '2022-01-01', '2025-12-01', 'This person only lists a prefix of our name, so this must be refused by the rule')$$, 'P0001');
select pg_temp.step('the HR member writes an honour record',
  $$insert into public.work_references (author, candidate, kind, role_title, from_month, to_month, body) values (pg_temp.u(2), pg_temp.u(3), 'honor', 'QC Analyst', '2022-01-01', '2025-12-01', 'Reliable analyst; ran the HPLC lab during two inspections with zero observations.')$$);
select pg_temp.ok('F-11 an accepted HR member of the verified company the person lists publishes an honour record', $$(select status from public.work_references where author = pg_temp.u(2) and kind = 'honor') = 'published'$$);
select pg_temp.no('F-11 a warning with a made-up evidence path is refused',
  $$insert into public.work_references (author, candidate, kind, role_title, from_month, to_month, category, body, evidence_path) values (pg_temp.u(2), pg_temp.u(3), 'warn', 'QC Analyst', '2022-01-01', '2025-12-01', 'Left without notice', 'Left in the middle of a validation campaign without any notice to the lab.', 'not-a-real-object')$$, '23514');
select pg_temp.step('the HR member files a warning with real evidence',
  $$insert into public.work_references (author, candidate, kind, role_title, from_month, to_month, category, body, evidence_path) values (pg_temp.u(2), pg_temp.u(3), 'warn', 'QC Analyst', '2022-01-01', '2025-12-01', 'Left without notice', 'Left in the middle of a validation campaign without any notice to the lab.', 'd2000000-0000-0000-0000-000000000002/ev.pdf')$$);
select pg_temp.ok('F-11 a warning with real evidence in the author''s folder waits for moderation', $$(select status from public.work_references where author = pg_temp.u(2) and kind = 'warn') = 'pending'$$);
insert into ids select 'warn', id::text from public.work_references where author = pg_temp.u(2) and kind = 'warn';

-- ══ F-33: one dispute, then the moderator's decision is final ═══════════════════════════════
select pg_temp.as_user('d2000000-0000-0000-0000-000000000006');
select pg_temp.step('the moderator publishes the warning', $$select public.moderate_reference(pg_temp.id('warn'), 'published')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000003');
select pg_temp.step('the person disputes it', $$select public.reply_to_reference(pg_temp.id('warn'), 'I dispute this', true)$$);
select pg_temp.ok('F-33 the person disputes a published warning once', $$(select status from public.work_references where id = pg_temp.id('warn')) = 'disputed'$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000006');
select pg_temp.step('the moderator upholds it', $$select public.moderate_reference(pg_temp.id('warn'), 'published')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000003');
select pg_temp.no('F-33 after the moderator''s decision a second dispute is refused', $$select public.reply_to_reference(pg_temp.id('warn'), 'again', true)$$, '42501');
select pg_temp.step('the person replies', $$select public.reply_to_reference(pg_temp.id('warn'), 'My side of the story', false)$$);
select pg_temp.ok('F-33 …a reply is always possible and the warning stays published', $$(select status || '|' || reply from public.work_references where id = pg_temp.id('warn')) = 'published|My side of the story'$$);

-- ══ F-13 / F-108 / F-109: certificates belong to the site's company; suspended companies are not served ══
select pg_temp.as_user('d2000000-0000-0000-0000-000000000007');
select pg_temp.no('F-13 a competitor cannot plant a certificate on another company''s site',
  $$insert into public.site_certificates (site_id, company_id, name, expiry, source) values (pg_temp.id('vsite'), pg_temp.id('bco'), 'FDA WARNING LETTER - site closed', '2030-01-01', 'public_list')$$, '23503');
select pg_temp.step('the supplier adds a certificate to its own site', $$insert into public.site_certificates (site_id, company_id, name, expiry, source) values (pg_temp.id('bsite'), pg_temp.id('bco'), 'ISO 9001', '2030-01-01', 'public_list')$$);
select pg_temp.ok('F-13 a company adds certificates to its own site, never with Drugbox provenance', $$(select source from public.site_certificates where name = 'ISO 9001' and company_id = pg_temp.id('bco')) = 'company'$$);
select pg_temp.no('F-13 a certificate cannot be moved to another company''s site', $$update public.site_certificates set site_id = pg_temp.id('vsite') where name = 'ISO 9001' and company_id = pg_temp.id('bco')$$, '23503');
select pg_temp.ok('F-13 the public site page lists only the site''s own certificates',
  $$(public.company_sites_public('t21-vco')::jsonb -> 0 -> 'certs') = '[]'::jsonb and (public.company_sites_public('t21-bco')::jsonb -> 0 -> 'certs' -> 0 ->> 'name') = 'ISO 9001'$$);
select pg_temp.ok('F-108 search_companies() lists the company while it is active', $$exists (select 1 from public.search_companies('T21 C Co') where slug = 't21-cco')$$);
select pg_temp.ok('F-109 the directory keeps a deterministic order when it is cut by its limit (verified first, then name)',
  $$(public.directory_companies(1)::jsonb -> 0 ->> 'slug') = (select slug from public.companies where status <> 'suspended' order by (status = 'verified') desc, name, id limit 1)$$);

-- ══ F-14: editing a verified document clears the verification ══════════════════════════════
select pg_temp.as_user('d2000000-0000-0000-0000-000000000005');
select pg_temp.step('Drugbox verifies the CEP', $$update public.company_documents set status = 'verified' where number = 'T21-CEP-1'$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.step('the owner rewrites the verified CEP', $$update public.company_documents set type = 'WHO PQ', product = 'Sildenafil', number = 'T21-FAKE-999' where number = 'T21-CEP-1'$$);
select pg_temp.ok('F-14 the owner rewriting a verified document drops it back to "declared"', $$(select status from public.company_documents_public where number = 'T21-FAKE-999') = 'declared'$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000005');
select pg_temp.step('Drugbox verifies it again and corrects the expiry', $$update public.company_documents set status = 'verified' where number = 'T21-FAKE-999'; update public.company_documents set expiry = '2030-01-01' where number = 'T21-FAKE-999'$$);
select pg_temp.ok('F-14 Drugbox editing a verified document keeps it verified', $$(select status from public.company_documents_public where number = 'T21-FAKE-999') = 'verified'$$);

-- ══ F-100 / F-37 / F-38: the team ═══════════════════════════════════════════════════════════
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.step('the owner invites u8 as sales', $$insert into public.company_members (company_id, user_id, role) values (pg_temp.id('vco'), pg_temp.u(8), 'sales')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000008');
select pg_temp.ok('F-100 an invited person is not a member before accepting (but sees their invitation)', $$not public.is_company_member(pg_temp.id('vco')) and exists (select 1 from public.company_members where user_id = pg_temp.u(8))$$);
select pg_temp.no('F-100 …cannot act for the company (no listing)', $$insert into public.company_listings (company_id, kind, product, created_by) values (pg_temp.id('vco'), 'surplus', 'Not mine', pg_temp.u(8))$$, '42501');
select pg_temp.no('F-100 …cannot send requests in its name', $$select public.deal_create('quote', 't21-bco', 't21-vco', 'Invited but not accepted')$$, '42501');
select pg_temp.step('u8 accepts', $$update public.company_members set accepted = true, show_public = true where company_id = pg_temp.id('vco') and user_id = pg_temp.u(8)$$);
select pg_temp.ok('F-100 …and is one after accepting', $$public.is_company_member(pg_temp.id('vco'))$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.step('the owner adds u4 with the owner role', $$insert into public.company_members (company_id, user_id, role) values (pg_temp.id('vco'), pg_temp.u(4), 'owner')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.ok('F-100 even an owner-role invitation gives nothing before it is accepted', $$not public.is_company_member(pg_temp.id('vco'))$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000009');
select pg_temp.no('F-37 a team admin cannot remove the page owner', $$delete from public.company_members where company_id = pg_temp.id('vco') and user_id = pg_temp.u(1)$$, '42501');
select pg_temp.no('F-37 a team admin cannot remove an owner-role member', $$delete from public.company_members where company_id = pg_temp.id('vco') and user_id = pg_temp.u(4)$$, '42501');
select pg_temp.step('the team admin removes an ordinary member', $$delete from public.company_members where company_id = pg_temp.id('vco') and user_id = pg_temp.u(8)$$);
select pg_temp.ok('F-37 a team admin removes an ordinary member', $$not exists (select 1 from public.company_members where company_id = pg_temp.id('vco') and user_id = pg_temp.u(8))$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.no('F-37 the page owner cannot leave their own team', $$delete from public.company_members where company_id = pg_temp.id('vco') and user_id = pg_temp.u(1)$$, '42501');
select pg_temp.step('the owner removes the owner-role invitation', $$delete from public.company_members where company_id = pg_temp.id('vco') and user_id = pg_temp.u(4)$$);
select pg_temp.no('F-38 requests cannot be routed to someone outside the team', $$insert into public.company_routing (company_id, request_type, user_id) values (pg_temp.id('vco'), 'quote', pg_temp.u(4))$$, '42501');
select pg_temp.step('the owner routes quotes to the HR member', $$insert into public.company_routing (company_id, request_type, user_id) values (pg_temp.id('vco'), 'quote', pg_temp.u(2))$$);
select pg_temp.as_server();
select pg_temp.ok('F-38 quotes are routed to the HR member', $$public.deal_receiver(pg_temp.id('vco'), 'quote') = pg_temp.u(2)$$);

-- ══ F-15 / F-16 / F-40 / F-105 / F-106 / F-107 / F-167 / F-39: the deals engine ═════════════
select pg_temp.as_user('d2000000-0000-0000-0000-000000000002');
select pg_temp.step('the HR member sends an RFQ for the company', $$select public.deal_create('quote','t21-bco','t21-vco','RFQ paracetamol 500 kg','{"qty":500,"unit":"kg"}','hello',null,'T21Q1')$$);
select pg_temp.ok('F-15 an HR member sends an RFQ for the company', $$(select status from public.deals where ref = 'T21Q1') = 'sent'$$);
select pg_temp.step('the HR member sends a questionnaire', $$select public.deal_create('questionnaire','t21-bco','t21-vco','Supplier qualification (t21)','{}','Please answer',null,'T21QN')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000007');
select pg_temp.step('the supplier answers', $$select public.deal_act('T21QN','answer','{"answers":{"gmp":"yes"}}','to')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000002');
select pg_temp.no('F-40 an HR member cannot approve a supplier questionnaire (quality team only)', $$select public.deal_act('T21QN','approve','{}','from')$$, '42501');
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.step('the owner approves it', $$select public.deal_act('T21QN','approve','{}','from')$$);
select pg_temp.ok('F-40 the owner approves it → supplier on the approved list', $$exists (select 1 from public.approved_suppliers where buyer_company_id = pg_temp.id('vco') and supplier_company_id = pg_temp.id('bco') and status = 'approved')$$);
-- the HR member leaves the company: the RFQ they sent is no longer theirs
select pg_temp.as_user('d2000000-0000-0000-0000-000000000002');
select pg_temp.step('the HR member leaves the company', $$delete from public.company_members where company_id = pg_temp.id('vco') and user_id = pg_temp.u(2)$$);
select pg_temp.ok('F-38 routing to the member who left is dropped (falls back to the owner)', $$not exists (select 1 from public.company_routing where user_id = pg_temp.u(2))$$);
select pg_temp.ok('F-15 an ex-member no longer sees the deal they sent', $$(select count(*) from public.deals where ref = 'T21Q1') = 0$$);
select pg_temp.no('F-15 …and cannot act on it (refused for membership, the step itself is legal)', $$select public.deal_act('T21Q1','cancel','{}','from')$$, '42501');
select pg_temp.as_server();
select pg_temp.ok('F-38 …the receiver of new quotes is the owner again', $$public.deal_receiver(pg_temp.id('vco'), 'quote') = pg_temp.u(1)$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000007');
select pg_temp.no('F-16 a validity of 99999999999 days is refused when quoting', $$select public.deal_act('T21Q1','quote','{"price":"US$ 9.99/kg","validity":"99999999999 days"}','to')$$, '22023');
select pg_temp.no('F-16 a validity of 0 days is refused', $$select public.deal_act('T21Q1','quote','{"price":"US$ 9.99/kg","validity":"0 days"}','to')$$, '22023');
select pg_temp.step('the supplier quotes normally', $$select public.deal_act('T21Q1','quote','{"price":"US$ 9.99/kg","validity":"14 days"}','to')$$);
select pg_temp.ok('F-16 a normal quote is stored', $$(select status from public.deals where ref = 'T21Q1') = 'quoted'$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.ok('F-15 the supplier''s quote notified the company''s owner, not the person who left',
  $$exists (select 1 from public.notifications where user_id = pg_temp.u(1) and message like 'RFQ paracetamol 500 kg — quote%')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000002');
select pg_temp.ok('F-15 …the person who left was not told', $$not exists (select 1 from public.notifications where user_id = pg_temp.u(2) and message like 'RFQ paracetamol 500 kg — quote%')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.step('the owner accepts', $$select public.deal_act('T21Q1','accept','{}','from')$$);
select pg_temp.ok('F-15 the owner (never involved before) acts for the company', $$(select status from public.deals where ref = 'T21Q1') = 'accepted'$$);
-- a person's job application still works through from_user
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.step('a person applies through the engine', $$select public.deal_create('job','t21-bco',null,'QA officer (t21)','{}','my application',null,'T21J1')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000007');
select pg_temp.step('the company runs the application', $$select public.deal_act('T21J1','shortlist'); select public.deal_act('T21J1','interview'); select public.deal_act('T21J1','offer')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.step('the applicant accepts the offer', $$select public.deal_act('T21J1','accept_job')$$);
select pg_temp.ok('F-15 a job applicant (no company) still runs their application to "hired"', $$(select status from public.deals where ref = 'T21J1') = 'hired'$$);
select pg_temp.no('F-106 no requests to an unclaimed page (nobody could ever answer)', $$select public.deal_create('job','t21-ghost',null,'Job at a ghost page','{}','x')$$, '42501');
-- flood limits
select pg_temp.ok('F-105 ten requests to the same company within the hour are allowed (T21J1 + 9)',
  $$(select count(*) from (select public.deal_create('job','t21-bco',null,'Follow-up ' || g,'{}','x') from generate_series(1, 9) g) x) = 9$$);
select pg_temp.no('F-105 …the 11th to that company is refused', $$select public.deal_create('job','t21-bco',null,'Follow-up 11','{}','x')$$, '42501');
select pg_temp.as_server();
select pg_temp.step('20 more requests by the same person (server-side insert)', $$insert into public.deals (type, title, from_user, to_company_id, status) select 'job', 'Bulk ' || g, pg_temp.u(4), pg_temp.id('cco'), 'applied' from generate_series(1, 20) g$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.no('F-105 more than 30 requests in an hour are refused', $$select public.deal_create('job','t21-vco',null,'Request 31','{}','x')$$, '42501');
-- group buying: numbers, open-state cancel/decline, final price, event authorship
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.no('F-16 a group target of NaN is refused', $$select public.deal_create('group','t21-bco','t21-vco','Group buy — bad target','{"product":"X","target":"NaN","unit":"kg"}','x')$$, '22023');
select pg_temp.no('F-16 a group target of 1e30 is refused', $$select public.deal_create('group','t21-bco','t21-vco','Group buy — huge target','{"product":"X","target":1e30,"unit":"kg"}','x')$$, '22023');
select pg_temp.step('the organiser opens three groups', $$
  select public.deal_create('group','t21-bco','t21-vco','Group buy — Metformin (t21)','{"product":"Metformin HCl","target":1000,"unit":"kg","price":"To be confirmed","by":"2099-12-31"}','opened',null,'T21G1');
  select public.deal_create('group','t21-bco','t21-vco','Group buy — MCC (t21)','{"product":"MCC","target":1000,"unit":"kg","price":"US$ 2/kg","by":"2099-12-31"}','opened',null,'T21G2');
  select public.deal_create('group','t21-bco','t21-vco','Group buy — Lactose (t21)','{"product":"Lactose","target":1000,"unit":"kg","price":"US$ 1/kg","by":"2099-12-31"}','opened',null,'T21G3')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000007');
select pg_temp.no('F-16 a NaN share is refused', $$select public.deal_join('T21G1','t21-cco','NaN'::numeric)$$, '22023');
select pg_temp.no('F-16 an Infinity share is refused', $$select public.deal_join('T21G1','t21-cco','Infinity'::numeric)$$, '22023');
select pg_temp.no('F-16 a 1e30 share is refused', $$select public.deal_join('T21G1','t21-cco',1e30)$$, '22023');
select pg_temp.no('F-16 a 0.5 share is refused', $$select public.deal_join('T21G1','t21-cco',0.5)$$, '22023');
select pg_temp.step('a member company joins with 250', $$select public.deal_join('T21G1','t21-cco',250)$$);
select pg_temp.ok('F-16 a normal share joins (open, 250)', $$(select status from public.deals where ref = 'T21G1') = 'open' and (select sum(qty) from public.deal_members m join public.deals d on d.id = m.deal_id where d.ref = 'T21G1') = 250$$);
select pg_temp.ok('F-107 the supplier declines an open group', $$(select status from public.deal_act('T21G3','decline','{}','to')) = 'declined'$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.ok('F-107 the organiser cancels an open group', $$(select status from public.deal_act('T21G2','cancel','{}','from')) = 'cancelled'$$);
select pg_temp.step('the organiser joins with 750', $$select public.deal_join('T21G1','t21-vco',750)$$);
select pg_temp.ok('F-16 target reached at 1,000', $$(select status from public.deals where ref = 'T21G1') = 'target_reached'$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000007');
select pg_temp.step('the supplier confirms with the final price', $$select public.deal_act('T21G1','confirm_group','{"price":"US$ 4.90/kg"}','to')$$);
select pg_temp.ok('F-107 the supplier sets the final price when confirming; member orders carry it',
  $$(select lines ->> 'price' from public.deals where ref = 'T21G1') = 'US$ 4.90/kg'
    and (select count(*) from public.deals where group_of = (select id from public.deals where ref = 'T21G1') and status = 'accepted' and offer ->> 'price' = 'US$ 4.90/kg') = 2$$);
select pg_temp.ok('F-167 the member order''s "sent" event is authored by the member, not the supplier',
  $$(select count(*) from public.deal_events e join public.deals o on o.id = e.deal_id where o.group_of = (select id from public.deals where ref = 'T21G1') and e.action = 'sent' and e.actor = o.from_user) = 2$$);
-- track record: a person owning two companies cannot rate themself
select pg_temp.step('one owner runs a deal between their two companies, rated 5 stars', $$
  select public.deal_create('quote','t21-bco','t21-cco','Self deal (t21)','{}','x',null,'T21SELF');
  select public.deal_act('T21SELF','quote','{"price":"1","validity":"14 days"}','to'); select public.deal_act('T21SELF','accept','{}','from'); select public.deal_act('T21SELF','confirm','{}','to');
  select public.deal_act('T21SELF','ship','{}','to'); select public.deal_act('T21SELF','receive','{"ontime":"yes"}','from'); select public.deal_act('T21SELF','rate','{"stars":5}','from')$$);
select pg_temp.ok('F-39 a closed deal between two companies with the same owner does not count in the track record',
  $$(select status from public.deals where ref = 'T21SELF') = 'closed' and (public.company_track_record(pg_temp.id('bco'))::jsonb) @> '{"orders":0,"reviews":0}'$$);
select pg_temp.ok('F-39 …while the real request from Verified Co does', $$(public.company_track_record(pg_temp.id('bco'))::jsonb ->> 'requests')::int >= 1$$);
-- F-36: a page with deals on record cannot be deleted; one without can
select pg_temp.no('F-36 the owner cannot delete a company page that has deals on record', $$delete from public.companies where slug = 't21-bco'$$, '42501');
select pg_temp.ok('F-36 …the other company''s request is still there', $$exists (select 1 from public.deals where ref = 'T21SELF')$$);
select pg_temp.as_server();
select pg_temp.no('F-36 even server-side, deleting the page does not cascade into other companies'' deals (RESTRICT)', $$delete from public.companies where slug = 't21-bco'$$, '23503');
select pg_temp.step('a second, empty page with a team admin', $$insert into public.companies (owner_id, name, slug, type, status) values (pg_temp.u(7), 'T21 Empty Co', 't21-empty', 'Supplier', 'pending');
  insert into public.company_members (company_id, user_id, role, accepted) select id, pg_temp.u(9), 'admin', true from public.companies where slug = 't21-empty'$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000007');
select pg_temp.step('its owner deletes it', $$delete from public.companies where slug = 't21-empty'$$);
select pg_temp.ok('F-36 a page without history can still be deleted by its owner (its team goes with it)', $$not exists (select 1 from public.companies where slug = 't21-empty')$$);
select pg_temp.ok('F-167 the API roles cannot TRUNCATE the engine tables', $$not has_table_privilege('authenticated', 'public.deals', 'TRUNCATE') and not has_table_privilege('anon', 'public.deal_events', 'TRUNCATE')$$);
-- F-106 / F-108: suspension
select pg_temp.as_server();
select pg_temp.step('Drugbox suspends C Co', $$update public.companies set status = 'suspended' where slug = 't21-cco'$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000007');
select pg_temp.no('F-106 a suspended company cannot send requests', $$select public.deal_create('quote','t21-vco','t21-cco','From a suspended company','{}','x')$$, '42501');
select pg_temp.no('F-106 …nor receive them', $$select public.deal_create('quote','t21-cco','t21-bco','To a suspended company','{}','x')$$, 'P0002');
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.ok('F-108 search_companies() and company_sites_public() hide a suspended company',
  $$not exists (select 1 from public.search_companies('T21 C Co') where slug = 't21-cco') and public.company_sites_public('t21-cco')::text = '[]'$$);
select pg_temp.as_anon();
select pg_temp.no('anon cannot create deals', $$select public.deal_create('job','t21-bco',null,'Anonymous request','{}','x')$$, '42501');
select pg_temp.no('anon cannot join groups', $$select public.deal_join('T21G1','t21-vco',1)$$, '42501');
select pg_temp.no('anon cannot claim pages', $$select public.claim_company(pg_temp.id('ghost'), 'mine')$$, '42501');

-- ══ F-42 / F-168: claiming a page, reviewed by Drugbox ══════════════════════════════════════
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.no('F-42 a page that has an owner cannot be claimed', $$select public.claim_company(pg_temp.id('vco'), 'mine')$$, '42501');
select pg_temp.step('the person tries the demo''s way (writing owner_id)', $$update public.companies set owner_id = pg_temp.u(4), status = 'pending' where slug = 't21-ghost'$$);
select pg_temp.ok('F-42 writing owner_id directly changes nothing (row-level security)', $$not exists (select 1 from public.companies where slug = 't21-ghost' and owner_id is not null)$$);
select pg_temp.step('the person claims the unclaimed page', $$insert into ids select 'claim', public.claim_company(pg_temp.id('ghost'), 'I am the regulatory manager, work email on request')::text$$);
select pg_temp.ok('F-42 claim_company() files a claim the claimant can see', $$exists (select 1 from public.verification_requests where id = pg_temp.id('claim') and claim and status = 'pending' and submitted_by = pg_temp.u(4))$$);
select pg_temp.no('F-42 a second claim while one is pending is refused', $$select public.claim_company(pg_temp.id('ghost'), 'again')$$, '42501');
select pg_temp.ok('F-42 the page stays unclaimed until Drugbox decides', $$(select status from public.companies where slug = 't21-ghost') = 'unclaimed'$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000006');
select pg_temp.ok('F-168 a moderator sees the verification requests', $$exists (select 1 from public.verification_requests where id = pg_temp.id('claim'))$$);
select pg_temp.no('F-168 a moderator may not approve (admins only)', $$update public.verification_requests set status = 'approved' where id = pg_temp.id('claim')$$, '42501');
select pg_temp.ok('F-168 a moderator can read verification documents, not payment receipts',
  $$public.can_read_document(format('verification/%s/registry.pdf', pg_temp.id('vco'))) and not public.can_read_document('payments/' || pg_temp.u(1) || '/receipt.pdf')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000005');
select pg_temp.step('the admin approves the claim', $$update public.verification_requests set status = 'approved' where id = pg_temp.id('claim')$$);
select pg_temp.ok('F-42 approval makes the claimant the owner, the page "pending", with an owner membership',
  $$(select owner_id = pg_temp.u(4) and status = 'pending' from public.companies where id = pg_temp.id('ghost'))
    and exists (select 1 from public.company_members where company_id = pg_temp.id('ghost') and user_id = pg_temp.u(4) and role = 'owner' and accepted)$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.ok('F-42 the new owner is told and can now act for the page',
  $$exists (select 1 from public.notifications where user_id = pg_temp.u(4) and message like 'Your claim was approved%') and public.is_company_member(pg_temp.id('ghost'), array['owner'])$$);
select pg_temp.step('the new owner reports wrong data on another page', $$insert into public.company_reports (company_id, reporter, section, issue) values (pg_temp.id('vco'), pg_temp.u(4), 'About', 'Wrong address on the page')$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000006');
select pg_temp.step('the moderator resolves the report', $$update public.company_reports set status = 'resolved' where company_id = pg_temp.id('vco') and reporter = pg_temp.u(4)$$);
select pg_temp.ok('F-168 a moderator sees and closes company reports', $$(select status from public.company_reports where company_id = pg_temp.id('vco') and reporter = pg_temp.u(4)) = 'resolved'$$);

-- ══ F-29: private groups ════════════════════════════════════════════════════════════════════
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.step('the creator opens a private group (member_count 99 sent)', $$insert into public.groups (name, description, type, created_by, member_count) values ('T21 Private room', 'Invite only', 'private', pg_temp.u(1), 99)$$);
select pg_temp.as_server();
insert into ids select 'pgroup', id::text from public.groups where name = 'T21 Private room';
select pg_temp.ok('F-29 member_count is kept by the database (99 ignored → 1, the creator)', $$(select member_count from public.groups where id = pg_temp.id('pgroup')) = 1$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.ok('F-29 a private group is invisible to outsiders', $$(select count(*) from public.groups where id = pg_temp.id('pgroup')) = 0$$);
select pg_temp.no('F-29 …and cannot be joined without an invitation', $$insert into public.group_members (group_id, user_id, role) values (pg_temp.id('pgroup'), pg_temp.u(4), 'member')$$, '42501');
select pg_temp.no('F-29 an outsider cannot invite themself', $$insert into public.group_invites (group_id, user_id, invited_by) values (pg_temp.id('pgroup'), pg_temp.u(4), pg_temp.u(4))$$, '42501');
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.step('the group admin invites the outsider', $$insert into public.group_invites (group_id, user_id, invited_by) values (pg_temp.id('pgroup'), pg_temp.u(4), pg_temp.u(1))$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000004');
select pg_temp.ok('F-29 the invited person sees the group and the invitation', $$(select count(*) from public.groups where id = pg_temp.id('pgroup')) = 1 and exists (select 1 from public.group_invites where user_id = pg_temp.u(4))$$);
select pg_temp.no('F-29 …cannot join as admin', $$insert into public.group_members (group_id, user_id, role) values (pg_temp.id('pgroup'), pg_temp.u(4), 'admin')$$, '42501');
select pg_temp.step('the invited person joins', $$insert into public.group_members (group_id, user_id, role) values (pg_temp.id('pgroup'), pg_temp.u(4), 'member')$$);
select pg_temp.ok('F-29 …joins as a member, the invitation is used up, count 2',
  $$exists (select 1 from public.group_members where group_id = pg_temp.id('pgroup') and user_id = pg_temp.u(4))
    and not exists (select 1 from public.group_invites where group_id = pg_temp.id('pgroup')) and (select member_count from public.groups where id = pg_temp.id('pgroup')) = 2$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000008');
select pg_temp.ok('F-29 someone not invited still cannot see it', $$(select count(*) from public.groups where id = pg_temp.id('pgroup')) = 0$$);
select pg_temp.step('u8 opens a group of their own and "invites" themself to it', $$insert into public.groups (name, type, created_by) values ('T21 u8 room', 'private', pg_temp.u(8));
  insert into public.group_invites (group_id, user_id, invited_by) select id, pg_temp.u(8), pg_temp.u(8) from public.groups where name = 'T21 u8 room'$$);
select pg_temp.no('F-29 an invitation to one group does not open another private group', $$insert into public.group_members (group_id, user_id, role) values (pg_temp.id('pgroup'), pg_temp.u(8), 'member')$$, '42501');
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.no('F-29 the group admin cannot rewrite a membership row to another person', $$update public.group_members set user_id = pg_temp.u(8) where group_id = pg_temp.id('pgroup') and user_id = pg_temp.u(4)$$, '42501');
select pg_temp.step('the group admin promotes the member', $$update public.group_members set role = 'admin' where group_id = pg_temp.id('pgroup') and user_id = pg_temp.u(4)$$);
select pg_temp.ok('F-29 …but can promote a member to admin', $$(select role from public.group_members where group_id = pg_temp.id('pgroup') and user_id = pg_temp.u(4)) = 'admin'$$);
select pg_temp.step('the creator writes member_count', $$update public.groups set member_count = 500 where id = pg_temp.id('pgroup')$$);
select pg_temp.ok('F-29 the creator cannot write member_count', $$(select member_count from public.groups where id = pg_temp.id('pgroup')) = 2$$);
select pg_temp.step('a public group', $$insert into public.groups (name, type, created_by) values ('T21 Public room', 'public', pg_temp.u(1))$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000008');
select pg_temp.step('u8 joins the public group', $$insert into public.group_members (group_id, user_id, role) select id, pg_temp.u(8), 'member' from public.groups where name = 'T21 Public room'$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000001');
select pg_temp.step('the creator switches it to private', $$update public.groups set type = 'private' where name = 'T21 Public room'$$);
select pg_temp.as_user('d2000000-0000-0000-0000-000000000008');
select pg_temp.ok('F-29 a member keeps seeing a group that was switched to private', $$(select count(*) from public.groups where name = 'T21 Public room') = 1$$);
select pg_temp.as_anon();
select pg_temp.ok('F-29 anon sees no private group', $$(select count(*) from public.groups where name like 'T21 %' and type = 'private') = 0$$);

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
