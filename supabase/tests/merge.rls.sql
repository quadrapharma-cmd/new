-- The three areas together (0065): open_candidates() with named columns; one search over what every area added; one suspension
-- for every write path (social's account_suspensions, refused for business and community features too); the name rule for a name
-- typed for someone else (company invitations) and for the name printed on a certificate; a certificate decided once.
-- Runs as the real API roles with a JWT, in one transaction that is rolled back; test data carries the "MG " marker.
-- Run on a fresh database (stub + migrations): psql -f supabase/tests/merge.rls.sql
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

-- A admin, M moderator, O company owner (and the suspended member's colleague), S the member who gets suspended, W a member who searches, R a reporter
insert into auth.users (id, email) select ('a6500000-0000-0000-0000-00000000000' || n)::uuid, 'mg' || n || '@x' from generate_series(1, 6) n on conflict do nothing;
insert into public.profiles (id, name) values ('a6500000-0000-0000-0000-000000000001','MG Admin'),('a6500000-0000-0000-0000-000000000002','MG Moderator'),
  ('a6500000-0000-0000-0000-000000000003','MG Owner'),('a6500000-0000-0000-0000-000000000004','MG Suspendee Zed'),('a6500000-0000-0000-0000-000000000005','MG Searcher'),
  ('a6500000-0000-0000-0000-000000000006','MG Reporter') on conflict (id) do update set name = excluded.name;
create function pg_temp.u(n int) returns uuid language sql immutable as $$ select ('a6500000-0000-0000-0000-00000000000' || n)::uuid $$;
create function pg_temp.act(n int) returns void language sql as $$ select pg_temp.as_user(pg_temp.u(n)::text) $$;
create function pg_temp.search(q text, k text) returns jsonb language sql as $$ select public.search_all(q, 20) -> k $$;
select pg_temp.as_server();
update public.profiles set role = 'admin' where id = pg_temp.u(1);
update public.profiles set role = 'moderator' where id = pg_temp.u(2);
update public.profiles set open_to_work = true where id in (pg_temp.u(4), pg_temp.u(6));
select pg_temp.step('a company of O with S as a member, a catalogue product and a site', $$with c as (insert into public.companies (name, slug, owner_id, status, type) values ('MG Quartz Pharma', 'mg-quartz-pharma', pg_temp.u(3), 'verified', 'Manufacturer') returning id)
  insert into ids select 'co', id::text from c$$);
select pg_temp.step('…members', $$insert into public.company_members (company_id, user_id, role, accepted) values (pg_temp.id('co'), pg_temp.u(3), 'owner', true), (pg_temp.id('co'), pg_temp.u(4), 'admin', true) on conflict do nothing$$);
select pg_temp.step('…a product in the catalogue', $$with p as (insert into public.company_products (company_id, name, active_ingredient) values (pg_temp.id('co'), 'MG Zolvexa 20 mg', 'mgzolvexatine') returning id) insert into ids select 'cp', id::text from p$$);
select pg_temp.step('…a suspended company', $$insert into public.companies (name, slug, owner_id, status, type) values ('MG Quartz Hidden', 'mg-quartz-hidden', pg_temp.u(3), 'suspended', 'Distributor')$$);
select pg_temp.step('…an unclaimed page', $$insert into public.companies (name, slug, status, type, source) values ('MG Quartz Unclaimed', 'mg-quartz-unclaimed', 'unclaimed', 'Distributor', 'public_list')$$);
select pg_temp.step('a listing still on the market and an expired one', $$insert into public.products (user_id, name, category, type, active) values (pg_temp.u(3), 'MG Quartzine API fresh', 'api', 'supply', true), (pg_temp.u(3), 'MG Quartzine API stale', 'api', 'supply', true)$$);
select pg_temp.step('…the stale one last renewed 60 days ago (expired after 30, 0054)', $$update public.products set renewed_at = now() - interval '60 days' where name = 'MG Quartzine API stale'$$);
select pg_temp.step('an open job and one past its deadline', $$insert into public.jobs (user_id, title, company, deadline) values (pg_temp.u(3), 'MG Quartz QC open', 'MG Quartz Pharma', current_date + 10), (pg_temp.u(3), 'MG Quartz QC closed', 'MG Quartz Pharma', current_date - 2)$$);
select pg_temp.step('a group and an archived group', $$insert into public.groups (name, created_by, type) values ('MG Quartz Circle', pg_temp.u(3), 'public'), ('MG Quartz Archive', pg_temp.u(3), 'public')$$);
select pg_temp.step('…archived', $$update public.groups set archived_at = now() where name = 'MG Quartz Archive'$$);
select pg_temp.step('a group S may ask to join', $$with g as (insert into public.groups (name, created_by, type) values ('MG Private Circle', pg_temp.u(3), 'private') returning id) insert into ids select 'pg', id::text from g$$);

-- 1. open_candidates(): a named table
select pg_temp.ok('open_candidates() returns a named table (not "setof profiles")', $$(select not p.proretset or p.prorettype <> 'public.profiles'::regtype from pg_proc p where p.proname = 'open_candidates')
  and (select p.prorettype = 'record'::regtype from pg_proc p where p.proname = 'open_candidates')$$);
select pg_temp.step('a new profiles column (as a later migration would add)', $$alter table public.profiles add column mg_extra text$$);
select pg_temp.act(5);
select pg_temp.ok('…open_candidates() still works and never carries a phone', $$(select count(*) >= 2 and bool_and(phone is null) from public.open_candidates(100) where id in (pg_temp.u(4), pg_temp.u(6)))$$);
select pg_temp.as_server();
select pg_temp.step('…the column goes again', $$alter table public.profiles drop column mg_extra$$);

-- 2. search over what every area added
select pg_temp.act(5);
select pg_temp.ok('search: a company is found by a product of its catalogue', $$exists (select 1 from jsonb_array_elements(pg_temp.search('Zolvexa', 'companies')) x where x->>'slug' = 'mg-quartz-pharma')$$);
select pg_temp.ok('…and by its active ingredient', $$exists (select 1 from jsonb_array_elements(pg_temp.search('mgzolvexatine', 'companies')) x where x->>'slug' = 'mg-quartz-pharma')$$);
select pg_temp.ok('search: a suspended company is not found', $$not exists (select 1 from jsonb_array_elements(pg_temp.search('MG Quartz', 'companies')) x where x->>'slug' = 'mg-quartz-hidden')
  and exists (select 1 from jsonb_array_elements(pg_temp.search('MG Quartz', 'companies')) x where x->>'slug' = 'mg-quartz-pharma')$$);
select pg_temp.ok('search: a listing on the market is found, an expired one is not', $$(select count(*) filter (where x->>'name' = 'MG Quartzine API fresh') = 1 and count(*) filter (where x->>'name' = 'MG Quartzine API stale') = 0
  from jsonb_array_elements(pg_temp.search('MG Quartzine', 'products')) x)$$);
select pg_temp.ok('search: an open job is found, one past its deadline is not', $$(select count(*) filter (where x->>'title' = 'MG Quartz QC open') = 1 and count(*) filter (where x->>'title' = 'MG Quartz QC closed') = 0
  from jsonb_array_elements(pg_temp.search('MG Quartz QC', 'jobs')) x)$$);
select pg_temp.ok('search: an archived group is not found by a non-member', $$(select count(*) filter (where x->>'name' = 'MG Quartz Circle') = 1 and count(*) filter (where x->>'name' = 'MG Quartz Archive') = 0
  from jsonb_array_elements(pg_temp.search('MG Quartz', 'groups')) x)$$);
select pg_temp.act(3);
select pg_temp.ok('…but by its creator', $$exists (select 1 from jsonb_array_elements(pg_temp.search('MG Quartz Archive', 'groups')) x where x->>'name' = 'MG Quartz Archive')$$);
select pg_temp.act(5);
select pg_temp.ok('search: S is found before the suspension (people and find_people)', $$exists (select 1 from jsonb_array_elements(pg_temp.search('Suspendee Zed', 'people')) x where (x->>'id')::uuid = pg_temp.u(4))
  and exists (select 1 from public.find_people('Suspendee Zed') where id = pg_temp.u(4))$$);

-- 3. one suspension for the whole app
select pg_temp.act(6);
select pg_temp.step('R reports S (social S-09)', $$insert into public.member_reports (reporter, reported, reason, note) values (pg_temp.u(6), pg_temp.u(4), 'fake', 'MG impersonation')$$);
select pg_temp.act(2);
select pg_temp.no('a moderator does not suspend from Admin → Users (admins only, 0063)', $$select public.admin_suspend(pg_temp.u(4), 'MG fake profile')$$, '42501');
select pg_temp.no('Reported members does not suspend an admin account either', $$select public.member_decide(pg_temp.u(1), 'suspend', 'MG no')$$, '22023');
select pg_temp.act(1);
select pg_temp.step('A suspends S from Admin → Users', $$select public.admin_suspend(pg_temp.u(4), 'MG fake profile')$$);
select pg_temp.as_server();
select pg_temp.ok('…one suspension row (social''s table), with who and why', $$(select reason = 'MG fake profile' and suspended_by = pg_temp.u(1) from public.account_suspensions where user_id = pg_temp.u(4))$$);
select pg_temp.ok('…S''s open report is closed and R is told the account was suspended', $$not exists (select 1 from public.member_reports where reported = pg_temp.u(4) and status = 'open')
  and exists (select 1 from public.notifications where user_id = pg_temp.u(6) and type = 'report_closed' and data->>'outcome' = 'member_actioned')$$);
select pg_temp.ok('…in the social log and in the Decided history', $$exists (select 1 from public.moderation_log where target_user = pg_temp.u(4) and action = 'suspend' and admin = pg_temp.u(1))
  and exists (select 1 from public.admin_actions where kind = 'suspension' and item_id = pg_temp.u(4)::text and decision = 'suspended')$$);
select pg_temp.act(5);
select pg_temp.ok('search: S is no longer found (people)', $$not exists (select 1 from jsonb_array_elements(pg_temp.search('Suspendee Zed', 'people')) x where (x->>'id')::uuid = pg_temp.u(4))$$);
select pg_temp.ok('…nor by find_people (Network)', $$not exists (select 1 from public.find_people('Suspendee Zed') where id = pg_temp.u(4))$$);
select pg_temp.ok('…nor among open candidates', $$not exists (select 1 from public.open_candidates(100) where id = pg_temp.u(4))$$);
select pg_temp.act(4);
select pg_temp.no('S adds no catalogue product', $$insert into public.company_products (company_id, name) values (pg_temp.id('co'), 'MG still selling')$$, '42501');
select pg_temp.no('S changes no catalogue product', $$update public.company_products set name = 'MG renamed' where id = pg_temp.id('cp')$$, '42501');
select pg_temp.no('S adds no site', $$insert into public.company_sites (company_id, name) values (pg_temp.id('co'), 'MG Plant 2')$$, '42501');
select pg_temp.no('S declares no compliance document', $$insert into public.company_documents (company_id, type, number) values (pg_temp.id('co'), 'GDP', 'MG-1')$$, '42501');
select pg_temp.no('S invites nobody to the company', $$select public.company_invite(pg_temp.id('co'), 'mg-new@x.test', 'MG New Person', 'sales')$$, '42501');
select pg_temp.no('S follows no company', $$insert into public.company_followers (company_id, user_id) values (pg_temp.id('co'), pg_temp.u(4))$$, '42501');
select pg_temp.no('S lists nothing (products)', $$insert into public.products (user_id, name, category, type, active) values (pg_temp.u(4), 'MG spam API', 'api', 'supply', true)$$, '42501');
select pg_temp.no('S posts no job', $$insert into public.jobs (user_id, title, company) values (pg_temp.u(4), 'MG spam job', 'MG')$$, '42501');
select pg_temp.no('S applies to no job', $$insert into public.job_applications (job_id, user_id) select id, pg_temp.u(4) from public.jobs where title = 'MG Quartz QC open'$$, '42501');
select pg_temp.no('S sets no job alert', $$insert into public.job_alerts (user_id, q) values (pg_temp.u(4), 'MG')$$, '42501');
select pg_temp.no('S asks to join no group', $$insert into public.group_join_requests (group_id, user_id) values (pg_temp.id('pg'), pg_temp.u(4))$$, '42501');
select pg_temp.no('S posts nothing in a group', $$insert into public.posts (user_id, body, group_id) select pg_temp.u(4), 'MG spam', id from public.groups where name = 'MG Quartz Circle'$$, '42501');
select pg_temp.step('S uploads a registry document (a file in their own folder)', $$insert into storage.objects (bucket_id, name, owner) values ('documents', 'claims/' || pg_temp.u(4) || '/r.pdf', pg_temp.u(4))$$);
select pg_temp.no('S claims no company page', $$select public.claim_company((select id from public.companies where slug = 'mg-quartz-unclaimed'), 'mine', 'claims/' || pg_temp.u(4) || '/r.pdf')$$, '42501');
select pg_temp.no('S writes no review', $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1, c2, c3, c4, body) values (pg_temp.u(4), pg_temp.u(3), 'employer', 5, 5, 5, 5, 'MG self-serving review text here')$$, '42501');
select pg_temp.act(1);
select pg_temp.step('A lifts the suspension (Admin → Users)', $$select public.admin_unsuspend(pg_temp.u(4))$$);
select pg_temp.as_server();
select pg_temp.ok('…logged in both histories', $$exists (select 1 from public.moderation_log where target_user = pg_temp.u(4) and action = 'lift_suspension')
  and exists (select 1 from public.admin_actions where kind = 'suspension' and item_id = pg_temp.u(4)::text and decision = 'restored')$$);
select pg_temp.act(4);
select pg_temp.step('S adds a catalogue product again', $$insert into public.company_products (company_id, name) values (pg_temp.id('co'), 'MG back in stock')$$);
select pg_temp.ok('…stored', $$exists (select 1 from public.company_products where name = 'MG back in stock')$$);
select pg_temp.act(2);
select pg_temp.step('M suspends S from Reported members (social)', $$select public.member_decide(pg_temp.u(4), 'suspend', 'MG again')$$);
select pg_temp.as_server();
select pg_temp.ok('…in the Decided history too', $$(select count(*) from public.admin_actions where kind = 'suspension' and item_id = pg_temp.u(4)::text and decision = 'suspended') = 2$$);
select pg_temp.act(2);
select pg_temp.step('M lifts it (social)', $$select public.lift_suspension(pg_temp.u(4), 'MG ok now')$$);
select pg_temp.as_server();
select pg_temp.ok('…restored in the Decided history', $$(select count(*) from public.admin_actions where kind = 'suspension' and item_id = pg_temp.u(4)::text and decision = 'restored') = 2$$);

-- 4. names typed for someone else, or printed for them
select pg_temp.act(3);
select pg_temp.no('an invitation with a name the rule refuses (a digit) is refused', $$select public.company_invite(pg_temp.id('co'), 'mg-bad@x.test', 'MG Agent 007', 'sales')$$, '23514');
select pg_temp.step('an invitation with look-alike punctuation', $$select public.company_invite(pg_temp.id('co'), 'mg-ok@x.test', 'MG Jean' || U&'\2010' || 'Paul', 'sales')$$);
select pg_temp.as_server();
select pg_temp.ok('…stored in the rule''s normal form (the hyphen look-alike becomes -)', $$(select name from public.company_invites where email = 'mg-ok@x.test') = 'MG Jean-Paul'$$);
select pg_temp.no('a certificate is not printed with a name that breaks the rule', $$insert into public.certificates (code, user_id, name, course_title) values ('MG-CERT-1', pg_temp.u(5), 'MG Learner 2', 'MG Course')$$, '23514');
select pg_temp.step('a certificate with a fine name', $$insert into public.certificates (code, user_id, name, course_title) values ('MG-CERT-2', pg_temp.u(5), '  MG   Learner ', 'MG Course')$$);
select pg_temp.ok('…printed in the rule''s normal form', $$(select name from public.certificates where code = 'MG-CERT-2') = 'MG Learner'$$);

-- 5. a certificate is decided once
select pg_temp.step('a site and two certificates of O''s company', $$with s as (insert into public.company_sites (company_id, name) values (pg_temp.id('co'), 'MG Plant') returning id),
  c as (insert into public.site_certificates (site_id, company_id, name, expiry) select id, pg_temp.id('co'), 'MG GMP', current_date + 300 from s returning id) insert into ids select 'cert', id::text from c$$);
select pg_temp.act(2);
select pg_temp.ok('M checks it (review_certificate, the Review queue''s path)', $$public.review_certificate(pg_temp.id('cert'), true)$$);
select pg_temp.as_server();
select pg_temp.ok('…checked by M, in the Decided history', $$(select checked_at is not null and checked_by = pg_temp.u(2) from public.site_certificates where id = pg_temp.id('cert'))
  and exists (select 1 from public.admin_actions where kind = 'certificate' and item_id = pg_temp.id('cert')::text and decision = 'checked' and actor = pg_temp.u(2))$$);
select pg_temp.act(1);
select pg_temp.no('A cannot reject it afterwards (decided once)', $$select public.review_certificate(pg_temp.id('cert'), false, 'second look')$$, 'DX409');
select pg_temp.ok('verification requests have one decide-once trigger (before the approval)', $$(select count(*) from pg_trigger where tgrelid = 'public.verification_requests'::regclass and not tgisinternal and tgfoid = 'public.verification_requests_once'::regproc) = 1$$);

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
