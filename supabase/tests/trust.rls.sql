-- Trust (0064 + the policies of 0001/0021): the person or company reviewed is told — an anonymous review's notice has no sender;
-- an edit tells nobody again; only the reviewer deletes a review; only the author withdraws a work reference; the person a record is
-- about replies to it and disputes a warning once. Runs as the real API roles with a JWT, in one transaction that is rolled back;
-- test data carries the "TR " marker.
-- Run on a fresh database (stub + migrations): psql -f supabase/tests/trust.rls.sql
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

-- A1, A2 Drugbox admins, M moderator, O company owner, R reporter, U member, F the account that gets suspended

-- E employer (has a job), C candidate (applied to it), O another member
insert into auth.users (id, email) select ('a5000000-0000-0000-0000-00000000000' || n)::uuid, 'tr' || n || '@x' from generate_series(1, 3) n on conflict do nothing;
insert into public.profiles (id, name) values ('a5000000-0000-0000-0000-000000000001','TR Employer'),('a5000000-0000-0000-0000-000000000002','TR Candidate'),
  ('a5000000-0000-0000-0000-000000000003','TR Other') on conflict (id) do update set name = excluded.name;
create function pg_temp.u(n int) returns uuid language sql immutable as $$ select ('a5000000-0000-0000-0000-00000000000' || n)::uuid $$;
create function pg_temp.act(n int) returns void language sql as $$ select pg_temp.as_user(pg_temp.u(n)::text) $$;
create function pg_temp.told(n int, pat text) returns bigint language sql stable security definer as $$ select count(*) from public.notifications where user_id = pg_temp.u(n) and message ~* pat $$;
create function pg_temp.sender(n int, pat text) returns uuid language sql stable security definer as $$ select from_user from public.notifications where user_id = pg_temp.u(n) and message ~* pat order by id desc limit 1 $$;
create function pg_temp.reviews(a int, b int) returns bigint language sql stable security definer as $$ select count(*) from public.job_reviews where reviewer = pg_temp.u(a) and reviewee = pg_temp.u(b) $$;
create function pg_temp.ref(k text) returns public.work_references language sql stable security definer as $$ select * from public.work_references where id = pg_temp.id(k) $$;

select pg_temp.as_server();
select pg_temp.step('E posts a job, C applies', $$with j as (insert into public.jobs (user_id, title, company) values (pg_temp.u(1), 'TR QC Analyst', 'TR Pharma') returning id),
  a as (insert into public.job_applications (job_id, user_id, note) select id, pg_temp.u(2), 'hi' from j returning job_id) insert into ids select 'job', job_id::text from a$$);

-- 1. reviews: the reviewed side is told; an anonymous review stays anonymous
select pg_temp.act(2);
select pg_temp.step('C reviews E''s company anonymously', $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1, c2, c3, c4, body, anonymous) values (pg_temp.u(2), pg_temp.u(1), 'employer', 4, 4, 5, 3, 'TR clear interview process and a fair salary band.', true)$$);
select pg_temp.as_server();
select pg_temp.ok('… E is told of an anonymous review, with no sender', $$pg_temp.told(1, '^Your company got an anonymous review') = 1 and pg_temp.sender(1, 'anonymous review') is null$$);
select pg_temp.act(2);
select pg_temp.step('C edits it (one per pair: the same row)', $$update public.job_reviews set body = 'TR clear interview process and a fair salary band. Edited.' where reviewer = pg_temp.u(2) and reviewee = pg_temp.u(1)$$);
select pg_temp.as_server();
select pg_temp.ok('… still one review, and nobody is told again', $$pg_temp.reviews(2, 1) = 1 and pg_temp.told(1, 'review') = 1$$);
select pg_temp.as_server();
select pg_temp.step('(as if C had first written it signed) a notice naming C', $$insert into public.notifications (user_id, type, from_user, message) values (pg_temp.u(1), 'review', pg_temp.u(2), 'reviewed your company on Drugbox Jobs')$$);
select pg_temp.act(2);
select pg_temp.step('C turns it signed, then anonymous again', $$update public.job_reviews set anonymous = false where reviewer = pg_temp.u(2) and reviewee = pg_temp.u(1); update public.job_reviews set anonymous = true where reviewer = pg_temp.u(2) and reviewee = pg_temp.u(1)$$);
select pg_temp.as_server();
select pg_temp.ok('… no review notice names C', $$not exists (select 1 from public.notifications where user_id = pg_temp.u(1) and type = 'review' and from_user = pg_temp.u(2))$$);
select pg_temp.act(1);
select pg_temp.step('E reviews C, signed', $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1, c2, c3, c4, body) values (pg_temp.u(1), pg_temp.u(2), 'candidate', 5, 5, 4, 5, 'TR punctual and well prepared for the interview.')$$);
select pg_temp.as_server();
select pg_temp.ok('… C is told, from E', $$pg_temp.told(2, '^reviewed you on Drugbox Jobs') = 1 and pg_temp.sender(2, '^reviewed you') = pg_temp.u(1)$$);
select pg_temp.no('a company cannot post anonymously', $$select pg_temp.act(1); update public.job_reviews set anonymous = true where reviewer = pg_temp.u(1)$$, '23514');
select pg_temp.as_server();

-- 2. only the reviewer deletes a review
select pg_temp.act(3);
select pg_temp.step('O tries to delete C''s review', $$delete from public.job_reviews where reviewer = pg_temp.u(2)$$);
select pg_temp.act(1);
select pg_temp.step('E (the one reviewed) tries too', $$delete from public.job_reviews where reviewer = pg_temp.u(2)$$);
select pg_temp.as_server();
select pg_temp.ok('… C''s review is still there', $$pg_temp.reviews(2, 1) = 1$$);
select pg_temp.act(2);
select pg_temp.step('C deletes it', $$delete from public.job_reviews where reviewer = pg_temp.u(2) and reviewee = pg_temp.u(1)$$);
select pg_temp.as_server();
select pg_temp.ok('… gone, E''s review of C stays', $$pg_temp.reviews(2, 1) = 0 and pg_temp.reviews(1, 2) = 1$$);

-- 3. references: only the author withdraws; the person replies and disputes a warning once
set session_replication_role = replica;   -- setup only: the employer rules of 0021 are tested in trust_hub_deals.rls.sql
select pg_temp.step('E''s honorable record and a pending warning about C', $$with h as (insert into public.work_references (author, candidate, kind, role_title, from_month, to_month, body, status) values (pg_temp.u(1), pg_temp.u(2), 'honor', 'QC Chemist', '2022-01-01', '2024-12-01', 'TR led the HPLC method transfer and trained two new analysts on the line.', 'published') returning id),
  w as (insert into public.work_references (author, candidate, kind, role_title, from_month, to_month, category, evidence_path, body, status) values (pg_temp.u(1), pg_temp.u(2), 'warn', 'QC Chemist', '2022-01-01', '2024-12-01', 'Left without notice', 'tr/evidence.pdf', 'TR left the night shift twice without notice and did not return the lab keys.', 'pending') returning id)
  insert into ids select 'honor', id::text from h union all select 'warn', id::text from w$$);
set session_replication_role = origin;
select pg_temp.act(2);
select pg_temp.ok('C reads both records about C (the pending warning too)', $$(select count(*) from public.work_references where candidate = pg_temp.u(2)) = 2$$);
select pg_temp.step('C replies to the honorable record', $$select public.reply_to_reference(pg_temp.id('honor'), 'TR thank you, it was a pleasure.', false)$$);
select pg_temp.as_server();
select pg_temp.ok('… the reply is stored, the record stays published', $$(pg_temp.ref('honor')).reply like 'TR thank you%' and (pg_temp.ref('honor')).status = 'published'$$);
select pg_temp.no('O cannot reply to a record about C', $$select pg_temp.act(3); select public.reply_to_reference(pg_temp.id('warn'), 'TR not mine', true)$$, 'P0002');
select pg_temp.no('E (the author) cannot dispute it either', $$select pg_temp.act(1); select public.reply_to_reference(pg_temp.id('warn'), 'TR not mine', true)$$, 'P0002');
select pg_temp.act(2);
select pg_temp.step('C disputes the warning', $$select public.reply_to_reference(pg_temp.id('warn'), 'TR I resigned in writing with a month of notice.', true)$$);
select pg_temp.as_server();
select pg_temp.ok('… disputed, with the reply', $$(pg_temp.ref('warn')).status = 'disputed' and (pg_temp.ref('warn')).disputed_at is not null and (pg_temp.ref('warn')).reply like 'TR I resigned%'$$);
select pg_temp.no('a second dispute is refused', $$select pg_temp.act(2); select public.reply_to_reference(pg_temp.id('warn'), 'TR again', true)$$, '42501');
select pg_temp.act(2);
select pg_temp.step('… but the reply can still be updated', $$select public.reply_to_reference(pg_temp.id('warn'), 'TR I resigned in writing; HR signed the letter.', false)$$);
select pg_temp.as_server();
select pg_temp.ok('… updated, still disputed', $$(pg_temp.ref('warn')).reply like '%HR signed%' and (pg_temp.ref('warn')).status = 'disputed'$$);
select pg_temp.act(3);
select pg_temp.step('O tries to withdraw E''s record', $$delete from public.work_references where id = pg_temp.id('honor')$$);
select pg_temp.act(2);
select pg_temp.step('C (the person it is about) tries too', $$delete from public.work_references where id = pg_temp.id('honor')$$);
select pg_temp.as_server();
select pg_temp.ok('… it is still there', $$(pg_temp.ref('honor')).id is not null$$);
select pg_temp.act(1);
select pg_temp.step('E withdraws it', $$delete from public.work_references where id = pg_temp.id('honor')$$);
select pg_temp.as_server();
select pg_temp.ok('… removed everywhere', $$(pg_temp.ref('honor')).id is null$$);

-- 4. anon
select pg_temp.as_anon();
select pg_temp.no('anon cannot reply to a reference', $$select public.reply_to_reference(1, 'x', false)$$, '42501');
select pg_temp.ok('anon reads no pending warning', $$(select count(*) from public.work_references where kind = 'warn' and status <> 'published') = 0$$);

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
