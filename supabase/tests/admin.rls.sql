-- Admin (0063): every decision is made once ("Already decided by …") and logged with who and when; undo where it is safe (never a
-- payment or a claim); site certificates checked or rejected with a note, the company told; company reports closed by Drugbox only,
-- the reporter told; suspension (a suspended account writes nothing and reads its reason), roles and the profile badge by Drugbox
-- admins only; Users and Posts lists for the team; a removed post told to its author and restorable from the log. Runs as the real API
-- roles with a JWT, in one transaction that is rolled back; test data carries the "AD " marker.
-- Run on a fresh database (stub + migrations): psql -f supabase/tests/admin.rls.sql
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
insert into auth.users (id, email) select ('a4000000-0000-0000-0000-00000000000' || n)::uuid, 'ad' || n || '@x' from generate_series(1, 7) n on conflict do nothing;
insert into public.profiles (id, name) values ('a4000000-0000-0000-0000-000000000001','AD Admin One'),('a4000000-0000-0000-0000-000000000002','AD Admin Two'),
  ('a4000000-0000-0000-0000-000000000003','AD Moderator'),('a4000000-0000-0000-0000-000000000004','AD Owner'),('a4000000-0000-0000-0000-000000000005','AD Reporter'),
  ('a4000000-0000-0000-0000-000000000006','AD Member'),('a4000000-0000-0000-0000-000000000007','AD Fake Profile') on conflict (id) do update set name = excluded.name;
update public.profiles set role = 'admin' where id in ('a4000000-0000-0000-0000-000000000001','a4000000-0000-0000-0000-000000000002');
update public.profiles set role = 'moderator' where id = 'a4000000-0000-0000-0000-000000000003';
create function pg_temp.u(n int) returns uuid language sql immutable as $$ select ('a4000000-0000-0000-0000-00000000000' || n)::uuid $$;
create function pg_temp.act(n int) returns void language sql as $$ select pg_temp.as_user(pg_temp.u(n)::text) $$;
create function pg_temp.acts(k text, i text) returns bigint language sql stable security definer as $$ select count(*) from public.admin_actions where kind = k and item_id = i and undone_at is null $$;
create function pg_temp.told(n int, pat text) returns bigint language sql stable security definer as $$ select count(*) from public.notifications where user_id = pg_temp.u(n) and message ~* pat $$;

select pg_temp.act(4);
select pg_temp.step('O creates its company page', $$insert into public.companies (name, type, slug) values ('AD Pharma','Manufacturer','ad-pharma')$$);
select pg_temp.as_server();
insert into ids select 'co', id::text from public.companies where slug = 'ad-pharma';

-- 1. verification: decided once, logged, undone safely
select pg_temp.act(4);
select pg_temp.step('O asks for verification', $$with x as (insert into public.verification_requests (company_id, submitted_by, registry) values (pg_temp.id('co'), pg_temp.u(4), 'AD-778') returning id) insert into ids select 'vr', id::text from x$$);
select pg_temp.step('O tries to approve its own request', $$update public.verification_requests set status = 'approved' where id = pg_temp.id('vr')$$);
select pg_temp.as_server();
select pg_temp.ok('… it stays pending', $$(select status = 'pending' from public.verification_requests where id = pg_temp.id('vr'))$$);
select pg_temp.act(1);
select pg_temp.step('A1 approves', $$update public.verification_requests set status = 'approved' where id = pg_temp.id('vr')$$);
select pg_temp.ok('… the company is verified; the decision is logged with A1', $$(select status = 'verified' from public.companies where id = pg_temp.id('co'))
  and (select actor = pg_temp.u(1) and decision = 'approved' from public.admin_actions where kind = 'verification' and item_id = pg_temp.id('vr')::text)$$);
select pg_temp.act(2);
select pg_temp.no('A2 cannot reject what A1 approved', $$update public.verification_requests set status = 'rejected', note = 'second opinion' where id = pg_temp.id('vr')$$, 'DX409');
select pg_temp.ok('… still approved', $$(select status = 'approved' from public.verification_requests where id = pg_temp.id('vr'))$$);
select pg_temp.act(3);
select pg_temp.no('a moderator cannot take a verification back', $$select public.admin_undo((select id from public.admin_actions where kind = 'verification' and item_id = pg_temp.id('vr')::text))$$, '42501');
select pg_temp.act(2);
select pg_temp.step('A2 undoes the approval', $$select public.admin_undo((select id from public.admin_actions where kind = 'verification' and item_id = pg_temp.id('vr')::text))$$);
select pg_temp.ok('… the request is pending, the company too, O is told', $$(select status = 'pending' from public.verification_requests where id = pg_temp.id('vr'))
  and (select status = 'pending' from public.companies where id = pg_temp.id('co')) and pg_temp.told(4, 'reviewed again') = 1$$);
select pg_temp.no('the same decision cannot be undone twice', $$select public.admin_undo((select id from public.admin_actions where kind = 'verification' and item_id = pg_temp.id('vr')::text))$$, 'DX409');
select pg_temp.step('A2 now rejects with a note', $$update public.verification_requests set status = 'rejected', note = 'Tax card expired' where id = pg_temp.id('vr')$$);
select pg_temp.ok('… O is told the note; two decisions are logged', $$pg_temp.told(4, 'Tax card expired') = 1
  and (select count(*) = 2 from public.admin_actions where kind = 'verification' and item_id = pg_temp.id('vr')::text)$$);

-- 2. a claim approval is never undone here
select pg_temp.as_server();
select pg_temp.step('an unclaimed page with a claim', $$with c as (insert into public.companies (name, type, slug, status, source) values ('AD Unclaimed','Distributor','ad-unclaimed','unclaimed','public_list') returning id)
  insert into ids select 'uc', id::text from c$$);
select pg_temp.act(5);
select pg_temp.step('… R claims it', $$insert into ids select 'cl', public.claim_company(pg_temp.id('uc'), 'I work there')::text$$);
select pg_temp.act(1);
select pg_temp.step('A1 approves the claim', $$update public.verification_requests set status = 'approved' where id = pg_temp.id('cl')$$);
select pg_temp.ok('… R owns the page; logged as a claim', $$(select owner_id = pg_temp.u(5) from public.companies where id = pg_temp.id('uc')) and pg_temp.acts('claim', pg_temp.id('cl')::text) = 1$$);
select pg_temp.no('… and it cannot be undone here', $$select public.admin_undo((select id from public.admin_actions where kind = 'claim' and item_id = pg_temp.id('cl')::text))$$, '22023');

-- 3. warning references
select pg_temp.as_server();
set session_replication_role = replica;   -- setup only: the employer rules of 0021 are tested in trust_hub_deals.rls.sql
select pg_temp.step('a pending warning reference', $$with x as (insert into public.work_references (author, candidate, kind, role_title, from_month, to_month, category, evidence_path, body, status) values (pg_temp.u(4), pg_temp.u(6), 'warn', 'QC chemist', '2022-01-01', '2024-12-01', 'Left without notice', 'ad/evidence.pdf', 'AD left the night shift twice without notice and did not return the lab keys for a week.', 'pending') returning id) insert into ids select 'wr', id::text from x$$);
set session_replication_role = origin;
select pg_temp.act(6);
select pg_temp.no('a member cannot moderate', $$select public.moderate_reference(pg_temp.id('wr'), 'rejected')$$, '42501');
select pg_temp.act(3);
select pg_temp.step('M publishes it', $$select public.moderate_reference(pg_temp.id('wr'), 'published')$$);
select pg_temp.act(1);
select pg_temp.no('A1 cannot reject it afterwards', $$select public.moderate_reference(pg_temp.id('wr'), 'rejected')$$, 'DX409');
select pg_temp.ok('… still published by M, logged', $$(select status = 'published' and decided_by = pg_temp.u(3) from public.work_references where id = pg_temp.id('wr')) and pg_temp.acts('reference', pg_temp.id('wr')::text) = 1$$);
select pg_temp.step('A1 undoes it', $$select public.admin_undo((select id from public.admin_actions where kind = 'reference' and item_id = pg_temp.id('wr')::text))$$);
select pg_temp.ok('… pending again, nobody''s decision', $$(select status = 'pending' and decided_by is null from public.work_references where id = pg_temp.id('wr'))$$);

-- 4. site certificates
select pg_temp.act(4);
select pg_temp.step('O adds a site and two certificates', $$with s as (insert into public.company_sites (company_id, name) values (pg_temp.id('co'), 'AD Obour plant') returning id) insert into ids select 'site', id::text from s;
  insert into public.site_certificates (site_id, company_id, name, expiry) select v::bigint, pg_temp.id('co'), x, '2030-01-01' from ids, (values ('AD WHO-GMP'), ('AD ISO 9001')) n(x) where k = 'site'$$);
select pg_temp.as_server();
insert into ids select 'c1', id::text from public.site_certificates where name = 'AD WHO-GMP';
insert into ids select 'c2', id::text from public.site_certificates where name = 'AD ISO 9001';
select pg_temp.act(4);
select pg_temp.no('O cannot check its own certificate', $$select public.cert_decide(pg_temp.id('c1'), true)$$, '42501');
select pg_temp.act(3);
select pg_temp.ok('M checks one', $$public.cert_decide(pg_temp.id('c1'), true) = 'checked'$$);
select pg_temp.ok('… checked_at and checked_by are set; the owner is told; logged', $$(select checked_at is not null and checked_by = pg_temp.u(3) from public.site_certificates where id = pg_temp.id('c1'))
  and pg_temp.told(4, 'checked your certificate "AD WHO-GMP"') = 1 and pg_temp.acts('certificate', pg_temp.id('c1')::text) = 1$$);
select pg_temp.act(1);
select pg_temp.no('A1 cannot reject it afterwards', $$select public.cert_decide(pg_temp.id('c1'), false, 'second look')$$, 'DX409');
select pg_temp.no('a rejection needs a reason', $$select public.cert_decide(pg_temp.id('c2'), false, '')$$, '22023');
select pg_temp.ok('A1 rejects the other with a reason', $$public.cert_decide(pg_temp.id('c2'), false, 'The scan is unreadable') = 'rejected'$$);
select pg_temp.ok('… the owner sees the reason', $$pg_temp.told(4, 'unreadable') = 1$$);
select pg_temp.act(4);
select pg_temp.step('O uploads a new scan (renames it)', $$update public.site_certificates set name = 'AD ISO 9001:2015' where id = pg_temp.id('c2')$$);
select pg_temp.as_server();
select pg_temp.ok('… it is waiting for a check again', $$(select rejected_at is null and reject_note is null and checked_at is null from public.site_certificates where id = pg_temp.id('c2'))$$);

-- 5. company reports
select pg_temp.act(5);
select pg_temp.step('R reports wrong information', $$with x as (insert into public.company_reports (company_id, reporter, section, issue, status) values (pg_temp.id('co'), pg_temp.u(5), 'Sites', 'AD the factory moved', 'open') returning id) insert into ids select 'rp', id::text from x$$);
select pg_temp.act(4);
select pg_temp.step('the company tries to close it', $$update public.company_reports set status = 'dismissed' where id = pg_temp.id('rp')$$);
select pg_temp.as_server();
select pg_temp.ok('… it stays open', $$(select status = 'open' from public.company_reports where id = pg_temp.id('rp'))$$);
select pg_temp.act(3);
select pg_temp.step('M resolves it', $$update public.company_reports set status = 'resolved' where id = pg_temp.id('rp')$$);
select pg_temp.ok('… decided by M; R is told; logged', $$(select decided_by = pg_temp.u(3) and decided_at is not null from public.company_reports where id = pg_temp.id('rp'))
  and pg_temp.told(5, 'corrected') = 1 and pg_temp.acts('report', pg_temp.id('rp')::text) = 1$$);
select pg_temp.act(1);
select pg_temp.no('A1 cannot dismiss it afterwards', $$update public.company_reports set status = 'dismissed' where id = pg_temp.id('rp')$$, 'DX409');
select pg_temp.step('A1 undoes it', $$select public.admin_undo((select id from public.admin_actions where kind = 'report' and item_id = pg_temp.id('rp')::text))$$);
select pg_temp.ok('… open again', $$(select status = 'open' and decided_by is null from public.company_reports where id = pg_temp.id('rp'))$$);

-- 6. an InstaPay payment is logged and never undone
select pg_temp.as_server();
select pg_temp.step('an InstaPay order in review', $$with x as (insert into public.payment_orders (user_id, product_code, company_id, method, amount_cents, status, transfer_ref) values (pg_temp.u(4), 'vip_month', pg_temp.id('co'), 'instapay', 285000, 'review', 'ADT1') returning id) insert into ids select 'po', id::text from x$$);
select pg_temp.act(1);
select pg_temp.step('A1 confirms it', $$select public.review_instapay(pg_temp.id('po'), true)$$);
select pg_temp.ok('… logged with the amount', $$(select decision = 'paid' and label like '%2,850.00%' from public.admin_actions where kind = 'payment' and item_id = pg_temp.id('po')::text)$$);
select pg_temp.no('… and cannot be undone', $$select public.admin_undo((select id from public.admin_actions where kind = 'payment' and item_id = pg_temp.id('po')::text))$$, '22023');
select pg_temp.act(2);
select pg_temp.no('A2 cannot confirm it again', $$select public.review_instapay(pg_temp.id('po'), false)$$, 'P0001');

-- 7. suspension
select pg_temp.act(6);
select pg_temp.no('a member cannot suspend', $$select public.admin_suspend(pg_temp.u(7), 'fake')$$, '42501');
select pg_temp.act(3);
select pg_temp.no('a moderator cannot suspend', $$select public.admin_suspend(pg_temp.u(7), 'fake')$$, '42501');
select pg_temp.act(1);
select pg_temp.no('an admin account cannot be suspended', $$select public.admin_suspend(pg_temp.u(2), 'oops')$$, '22023');
select pg_temp.no('a suspension needs a reason', $$select public.admin_suspend(pg_temp.u(7), '')$$, '22023');
select pg_temp.step('A1 suspends F', $$select public.admin_suspend(pg_temp.u(7), 'Fake profile — impersonates a QA manager')$$);
select pg_temp.act(7);
select pg_temp.no('F cannot post', $$insert into public.posts (user_id, body) values (pg_temp.u(7), 'AD spam')$$, '42501');
select pg_temp.no('F cannot message', $$insert into public.messages (sender_id, receiver_id, body) values (pg_temp.u(7), pg_temp.u(6), 'AD hi')$$, '42501');
select pg_temp.no('F cannot ask to connect', $$insert into public.connections (requester, addressee) values (pg_temp.u(7), pg_temp.u(6))$$, '42501');
select pg_temp.ok('F reads why', $$(select reason like 'Fake profile%' from public.account_suspensions where user_id = pg_temp.u(7))$$);
select pg_temp.act(6);
select pg_temp.ok('another member does not read it', $$not exists (select 1 from public.account_suspensions)$$);
select pg_temp.act(1);
select pg_temp.step('A1 restores F', $$select public.admin_unsuspend(pg_temp.u(7))$$);
select pg_temp.act(7);
select pg_temp.step('F posts again', $$insert into public.posts (user_id, body) values (pg_temp.u(7), 'AD back again')$$);
select pg_temp.ok('… the post is there; F was told', $$exists (select 1 from public.posts where body = 'AD back again') and pg_temp.told(7, 'active again') = 1$$);

-- 8. roles and the profile badge
select pg_temp.act(3);
select pg_temp.no('a moderator cannot change roles', $$select public.admin_set_role(pg_temp.u(6), 'admin')$$, '42501');
select pg_temp.no('a moderator cannot give the badge', $$select public.admin_verify_profile(pg_temp.u(6), true)$$, '42501');
select pg_temp.act(1);
select pg_temp.no('an admin cannot drop its own role', $$select public.admin_set_role(pg_temp.u(1), 'user')$$, '22023');
select pg_temp.step('A1 makes U a moderator and gives the badge', $$select public.admin_set_role(pg_temp.u(6), 'moderator'); select public.admin_verify_profile(pg_temp.u(6), true)$$);
select pg_temp.ok('… U is a verified moderator, told about the badge', $$(select role = 'moderator' and verified from public.profiles where id = pg_temp.u(6)) and pg_temp.told(6, 'verified your profile') = 1$$);
select pg_temp.step('A1 undoes the role', $$select public.admin_undo((select id from public.admin_actions where kind = 'role' and item_id = pg_temp.u(6)::text))$$);
select pg_temp.ok('… U is a member again', $$(select role = 'user' from public.profiles where id = pg_temp.u(6))$$);

-- 9. the team's lists
select pg_temp.act(3);
select pg_temp.ok('a moderator finds a member by name, with the account state', $$(select count(*) = 1 from public.admin_users('ad fake'))$$);
select pg_temp.ok('… and the newest posts', $$exists (select 1 from public.admin_posts('AD back') where body = 'AD back again')$$);
select pg_temp.act(5);
select pg_temp.no('a member cannot list accounts', $$select * from public.admin_users('')$$, '42501');
select pg_temp.ok('… nor read the decision log', $$not exists (select 1 from public.admin_actions)$$);

-- 10. a removed post: the author is told why; it comes back from the log
select pg_temp.as_server();
insert into ids select 'post', id::text from public.posts where body = 'AD back again';
insert into public.post_media (post_id, url, type, name) select v::bigint, 'https://x.test/ad.png', 'image', 'ad.png' from ids where k = 'post';
select pg_temp.act(5);
select pg_temp.no('a member cannot remove someone else''s post this way', $$select public.admin_delete_post(pg_temp.id('post'), 'spam')$$, '42501');
select pg_temp.act(3);
select pg_temp.no('a removal needs a reason', $$select public.admin_delete_post(pg_temp.id('post'), '')$$, '22023');
select pg_temp.step('M removes the post', $$insert into ids select 'rm', public.admin_delete_post(pg_temp.id('post'), 'Advertising outside the marketplace')::text$$);
select pg_temp.ok('… it is gone; the author is told why', $$not exists (select 1 from public.posts where id = pg_temp.id('post')) and pg_temp.told(7, 'removed your post: Advertising') = 1$$);
select pg_temp.step('M restores it', $$select public.admin_restore_post(pg_temp.id('rm'))$$);
select pg_temp.ok('… the same post with its picture is back; the author is told', $$exists (select 1 from public.posts where id = pg_temp.id('post') and body = 'AD back again')
  and exists (select 1 from public.post_media where post_id = pg_temp.id('post')) and pg_temp.told(7, 'restored your post') = 1$$);
select pg_temp.no('it cannot be restored twice', $$select public.admin_restore_post(pg_temp.id('rm'))$$, 'DX409');
select pg_temp.as_anon();
select pg_temp.ok('anon reads no decision and no suspension', $$(select count(*) = 0 from public.admin_actions) and (select count(*) = 0 from public.account_suspensions)$$);
select pg_temp.no('anon cannot undo', $$select public.admin_undo(1)$$, '42501');

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
