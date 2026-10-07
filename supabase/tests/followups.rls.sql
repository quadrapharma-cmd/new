-- Follow-ups (0024): Fawry pays an order only with its own reference; review roles follow the relationship; my_interactions()
-- agrees with can_review(); erasing any kind of account (a company owner with deals or a buying group too) keeps the company
-- history; one application notification per job and person, none for a deleted comment, retention; the reported company
-- neither sees the reporter nor changes the status; the anon key reads no content; every foreign key has an index;
-- Drugbox admins verify people (and only that); the whole-list directory RPC is not in the API.
-- Runs as the real API roles with a JWT (the webhooks as service_role), in one transaction that is rolled back; test data
-- carries the "FU " marker. Run on a fresh database (stub + migrations): psql -f supabase/tests/followups.rls.sql
-- Harness as in payments_storage.rls.sql: step()/ok()/no(); a negative check passes only with the expected SQLSTATE; non-zero exit on failure.
\set QUIET on
\set ON_ERROR_ROLLBACK on
set client_min_messages = warning;
\o /dev/null
begin;
create temp table r (n serial, name text, ok boolean, err text); grant all on r to authenticated, anon, service_role; grant all on r_n_seq to authenticated, anon, service_role;
create temp table ids (k text primary key, v text); grant all on ids to authenticated, anon, service_role;
create function pg_temp.as_user(u uuid) returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', u::text, true); perform set_config('request.jwt.claims', json_build_object('sub', u, 'role', 'authenticated')::text, true);
  perform set_config('role', 'authenticated', true); end $$;
create function pg_temp.as_anon() returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', '', true); perform set_config('request.jwt.claims', '{"role":"anon"}', true); perform set_config('role', 'anon', true); end $$;
create function pg_temp.as_service() returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', '', true); perform set_config('request.jwt.claims', '{"role":"service_role"}', true); perform set_config('role', 'service_role', true); end $$;
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
-- rows a statement changed (RLS hides rows silently: 0 means refused; -1: no privilege)
create function pg_temp.rows(q text) returns int language plpgsql as $$ declare n int; begin execute q; get diagnostics n = row_count; return n;
  exception when insufficient_privilege then return -1; end $$;
create function pg_temp.id(k text) returns bigint language sql stable as $$ select v::bigint from ids where ids.k = id.k $$;
create function pg_temp.u(n int) returns uuid language sql immutable as $$ select ('f2400000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid $$;
create function pg_temp.confirm(k text, tx text, cents int) returns text language sql as $$
  select public.confirm_payment('fawry', k, tx, cents, 'EGP', jsonb_build_object('provider', 'fawry', 'fawryRefNumber', tx)) $$;
-- erase an account the way Supabase does (auth.users row deleted by the server); true when the profile is gone
create function pg_temp.erase(u uuid) returns boolean language plpgsql as $$ begin
  delete from auth.users where id = u; return not exists (select 1 from public.profiles where id = u); end $$;
create function pg_temp.notifs(p_to uuid, p_from uuid, p_type text) returns int language sql stable as $$
  select count(*)::int from public.notifications where user_id = p_to and from_user = p_from and type = p_type $$;

-- people: u1 owner of FU Co (posts a job, open to work), u2 applicant + reviewer, u3 member who posts a job too (outsider),
--   u4 Drugbox admin, u5 moderator, u6 applies to FU Co through a company job request ('job' deal), u7 poster, u8 commenter,
--   u9 group creator, u10 owner of FU Buyer (in a buying group), u11 owner of FU Supplier (deals to it), u12 plain account,
--   u13 owner of FU Spare (Drugbox takes the page back)
select pg_temp.as_server();
insert into auth.users (id, email) select pg_temp.u(g), 'fu' || g || '@fu24.test' from generate_series(1, 13) g on conflict do nothing;
insert into public.profiles (id, name) select pg_temp.u(g), 'FU person ' || g from generate_series(1, 13) g on conflict (id) do nothing;
update public.profiles set role = 'admin' where id = pg_temp.u(4);
update public.profiles set role = 'moderator' where id = pg_temp.u(5);
update public.profiles set open_to_work = true where id in (pg_temp.u(1), pg_temp.u(2), pg_temp.u(6));
insert into public.companies (owner_id, name, slug, type, status, registry) values
  (pg_temp.u(1), 'FU Co', 'fu-co', 'Manufacturer', 'verified', 'FU-1'),
  (pg_temp.u(10), 'FU Buyer', 'fu-buyer', 'Distributor', 'verified', 'FU-10'),
  (pg_temp.u(11), 'FU Supplier', 'fu-supplier', 'Supplier', 'verified', 'FU-11'),
  (pg_temp.u(13), 'FU Spare', 'fu-spare', 'Manufacturer', 'pending', null);
insert into ids select replace(slug, 'fu-', ''), id::text from public.companies where slug like 'fu-%';
insert into public.company_members (company_id, user_id, role, accepted, show_public) values
  (pg_temp.id('co'), pg_temp.u(1), 'owner', true, true), (pg_temp.id('buyer'), pg_temp.u(10), 'owner', true, true),
  (pg_temp.id('supplier'), pg_temp.u(11), 'owner', true, true), (pg_temp.id('spare'), pg_temp.u(13), 'owner', true, true)
  on conflict do nothing;
insert into public.jobs (user_id, title, company, category, active) values (pg_temp.u(1), 'FU QC Analyst', 'FU Co', 'qaqc', true), (pg_temp.u(3), 'FU Outsider job', 'Elsewhere', 'qaqc', true);
insert into ids select 'job', id::text from public.jobs where title = 'FU QC Analyst';
insert into ids select 'job3', id::text from public.jobs where title = 'FU Outsider job';
-- history: a completed quote FU Buyer → FU Supplier, a buying group FU Co → FU Supplier that FU Buyer joined, a job request u6 → FU Co
insert into public.deals (type, title, from_company_id, from_user, to_company_id, status) values
  ('quote', 'FU Metformin 500 mg', pg_temp.id('buyer'), pg_temp.u(10), pg_temp.id('supplier'), 'delivered'),
  ('group', 'FU Paracetamol group', pg_temp.id('co'), pg_temp.u(1), pg_temp.id('supplier'), 'open'),
  ('job', 'FU application', null, pg_temp.u(6), pg_temp.id('co'), 'sent');
insert into ids select 'dquote', id::text from public.deals where title = 'FU Metformin 500 mg';
insert into ids select 'dgroup', id::text from public.deals where title = 'FU Paracetamol group';
insert into public.deal_members (deal_id, company_id, qty) values (pg_temp.id('dgroup'), pg_temp.id('buyer'), 100);
insert into public.posts (user_id, body) values (pg_temp.u(7), 'FU a post that people react to');
insert into ids select 'post', id::text from public.posts where body = 'FU a post that people react to';

-- ══ F-115 Fawry: an order is paid only with the reference number Fawry issued for it ════════════════
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('the owner orders VIP by Fawry', $$insert into ids select 'fw', (public.create_order('vip_month', 'fawry', pg_temp.id('co'))).id$$);
select pg_temp.step('…and a second one', $$insert into ids select 'fw2', (public.create_order('vip_month', 'fawry', pg_temp.id('co'))).id$$);
select pg_temp.as_server();
insert into ids select 'fwref', merchant_ref from public.payment_orders where id = pg_temp.id('fw');
insert into ids select 'fwamt', amount_cents::text from public.payment_orders where id = pg_temp.id('fw');
select pg_temp.as_service();
select pg_temp.ok('F-115 an order with no Fawry reference on record is never paid', $$pg_temp.confirm((select v from ids where k = 'fwref'), 'FU-FW-1', pg_temp.id('fwamt')::int) = 'reference mismatch'$$);
select pg_temp.step('payments-create stores Fawry''s reference numbers', $$select public.set_order_provider_ref(pg_temp.id('fw'), 'FU-FW-1'), public.set_order_provider_ref(pg_temp.id('fw2'), 'FU-FW-2')$$);
select pg_temp.ok('F-115 a signed notification carrying another order''s reference does not pay this order', $$pg_temp.confirm((select v from ids where k = 'fwref'), 'FU-FW-2', pg_temp.id('fwamt')::int) = 'reference mismatch'$$);
select pg_temp.ok('F-115 …nor one without a reference', $$pg_temp.confirm((select v from ids where k = 'fwref'), null, pg_temp.id('fwamt')::int) = 'reference mismatch'$$);
select pg_temp.as_server();
select pg_temp.ok('F-115 …the order still waits and its record is untouched', $$(select status = 'pending' and provider_ref = 'FU-FW-1' and provider_payload is null from public.payment_orders where id = pg_temp.id('fw'))$$);
select pg_temp.as_service();
select pg_temp.ok('F-115 the genuine notification pays it', $$pg_temp.confirm((select v from ids where k = 'fwref'), 'FU-FW-1', pg_temp.id('fwamt')::int) = 'paid'$$);
select pg_temp.ok('F-115 …and a replay is "already paid"', $$pg_temp.confirm((select v from ids where k = 'fwref'), 'FU-FW-1', pg_temp.id('fwamt')::int) = 'already paid'$$);
select pg_temp.as_server();
select pg_temp.ok('F-115 the other order is still pending', $$(select status = 'pending' from public.payment_orders where id = pg_temp.id('fw2'))$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.no('F-115 confirm_payment is not callable by members', $$select public.confirm_payment('fawry', 'DBX1', 'x', 1, 'EGP', '{}')$$, '42501');

-- ══ F-10 a review's role follows the relationship ═══════════════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.step('u2 applies to u1''s job', $$insert into public.job_applications (job_id, user_id, note) values (pg_temp.id('job'), pg_temp.u(2), 'FU interested')$$);
select pg_temp.no('F-10 the applicant cannot review the employer as a candidate (verifier''s repro, employer open to work)',
  $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body) values (pg_temp.u(2), pg_temp.u(1), 'candidate', 1,1,1,1, 'FU a candidate review the applicant may not write')$$, '42501');
select pg_temp.step('the applicant reviews the employer', $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body, anonymous) values (pg_temp.u(2), pg_temp.u(1), 'employer', 4,4,4,4, 'FU a clear and fair hiring process overall.', true)$$);
select pg_temp.ok('F-10 an applicant reviews the employer', $$exists (select 1 from public.job_reviews where reviewer = pg_temp.u(2) and reviewee = pg_temp.u(1) and reviewee_role = 'employer')$$);
select pg_temp.no('F-10 the applicant cannot review someone whose job they never applied to as an employer',
  $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body) values (pg_temp.u(2), pg_temp.u(3), 'employer', 1,1,1,1, 'FU an employer review without an application')$$, '42501');
select pg_temp.ok('F-10 my_interactions() of the applicant: the employer, nobody else', $$array(select party from public.my_interactions() order by 1) = array[pg_temp.u(1)]$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('the employer reviews the applicant', $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body) values (pg_temp.u(1), pg_temp.u(2), 'candidate', 5,5,5,5, 'FU reliable, prepared and on time for every step.')$$);
select pg_temp.ok('F-10 the employer reviews the applicant as a candidate', $$exists (select 1 from public.job_reviews where reviewer = pg_temp.u(1) and reviewee = pg_temp.u(2) and reviewee_role = 'candidate')$$);
select pg_temp.no('F-10 the employer cannot review a person who applied to their company as an employer',
  $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body) values (pg_temp.u(1), pg_temp.u(6), 'employer', 1,1,1,1, 'FU the wrong role for this relationship')$$, '42501');
select pg_temp.step('the company reviews the person who applied through a job request', $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body) values (pg_temp.u(1), pg_temp.u(6), 'candidate', 3,3,3,3, 'FU applied through our company page; good file.')$$);
select pg_temp.ok('F-10 a job request to my company counts as an application (candidate review stored)', $$exists (select 1 from public.job_reviews where reviewer = pg_temp.u(1) and reviewee = pg_temp.u(6))$$);
select pg_temp.ok('F-10 my_interactions() of the employer: both applicants', $$array(select party from public.my_interactions() order by 1) = array[pg_temp.u(2), pg_temp.u(6)]$$);
select pg_temp.as_user(pg_temp.u(6));
select pg_temp.ok('F-10 the person who applied through the company page may review its owner as an employer', $$public.can_review(pg_temp.u(6), pg_temp.u(1), 'employer') and not public.can_review(pg_temp.u(6), pg_temp.u(1), 'candidate')$$);
select pg_temp.ok('F-10 …and my_interactions() lists the company''s team', $$exists (select 1 from public.my_interactions() where party = pg_temp.u(1))$$);
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.no('F-10 an employer who never dealt with a candidate cannot review them',
  $$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1,c2,c3,c4, body) values (pg_temp.u(3), pg_temp.u(2), 'candidate', 1,1,1,1, 'FU a candidate review without any contact')$$, '42501');
select pg_temp.ok('F-10 my_interactions() is empty for them', $$not exists (select 1 from public.my_interactions())$$);

-- ══ F-18 notifications: one per application, none for deleted comments, retention ════════════════════
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.step('the applicant withdraws and re-applies three times', $q$do $d$ begin for i in 1..3 loop
  delete from public.job_applications where job_id = pg_temp.id('job') and user_id = pg_temp.u(2);
  insert into public.job_applications (job_id, user_id, note) values (pg_temp.id('job'), pg_temp.u(2), 'FU again ' || i); end loop; end $d$$q$);
select pg_temp.as_server();
select pg_temp.ok('F-18 one application notification per job and person, however often they re-apply', $$pg_temp.notifs(pg_temp.u(1), pg_temp.u(2), 'job_application') = 1$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('the employer whitelists u8', $$insert into public.job_lists (owner, target, side, list) values (pg_temp.u(1), pg_temp.u(8), 'employer', 'white')$$);
select pg_temp.as_user(pg_temp.u(8));
select pg_temp.step('the preferred candidate applies', $$insert into public.job_applications (job_id, user_id, note) values (pg_temp.id('job'), pg_temp.u(8), 'FU preferred')$$);
select pg_temp.as_server();
select pg_temp.ok('F-18 a preferred candidate gives one notification (the shortlist one), not two', $$pg_temp.notifs(pg_temp.u(1), pg_temp.u(8), 'job_application') = 1
  and exists (select 1 from public.notifications where user_id = pg_temp.u(1) and from_user = pg_temp.u(8) and message like 'A preferred candidate applied%')$$);
select pg_temp.as_user(pg_temp.u(8));
select pg_temp.step('a member comments and deletes the comment three times', $q$do $d$ declare c bigint; begin for i in 1..3 loop
  insert into public.comments (post_id, user_id, body) values (pg_temp.id('post'), pg_temp.u(8), 'FU comment ' || i) returning id into c;
  delete from public.comments where id = c; end loop; end $d$$q$);
select pg_temp.step('…then leaves one comment', $$insert into public.comments (post_id, user_id, body) values (pg_temp.id('post'), pg_temp.u(8), 'FU the comment that stays')$$);
select pg_temp.as_server();
select pg_temp.ok('F-18 deleted comments leave no notification; the kept one has its own', $$pg_temp.notifs(pg_temp.u(7), pg_temp.u(8), 'comment') = 1
  and (select message from public.notifications where user_id = pg_temp.u(7) and from_user = pg_temp.u(8) and type = 'comment') = 'FU the comment that stays'$$);
insert into public.notifications (user_id, type, from_user, message, created_at) values
  (pg_temp.u(12), 'connection_request', pg_temp.u(3), 'FU old', now() - interval '200 days'),
  (pg_temp.u(12), 'connection_request', pg_temp.u(3), 'FU new', now() - interval '2 days');
select pg_temp.as_user(pg_temp.u(4));
select pg_temp.no('F-18 purge_old_notifications() is not callable by members, not even admins', $$select public.purge_old_notifications(180)$$, '42501');
select pg_temp.as_anon();
select pg_temp.no('F-18 …nor by anon', $$select public.purge_old_notifications(180)$$, '42501');
select pg_temp.as_service();
select pg_temp.no('F-18 the retention is at least 7 days', $$select public.purge_old_notifications(1)$$, '22023');
select pg_temp.ok('F-18 the server purges notifications older than 180 days', $$public.purge_old_notifications() >= 1$$);
select pg_temp.as_server();
select pg_temp.ok('F-18 …the recent one stays', $$(select array_agg(message order by message) from public.notifications where user_id = pg_temp.u(12)) = array['FU new']$$);

-- ══ F-32 the reported company sees no reporter and changes no status ═══════════════════════════════════
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.step('a member reports FU Co', $$with x as (insert into public.company_reports (company_id, reporter, section, issue) values (pg_temp.id('co'), pg_temp.u(3), 'About', 'FU the address is wrong') returning id) insert into ids select 'rep', id from x$$);
select pg_temp.ok('F-32 the reporter cannot close their own report either', $$pg_temp.rows('update public.company_reports set status = ''resolved'' where id = pg_temp.id(''rep'')') = 0$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.ok('F-32 the company reads no report row (no reporter id)', $$not exists (select 1 from public.company_reports where company_id = pg_temp.id('co'))$$);
select pg_temp.ok('F-32 the company reads the report without the reporter', $$(select issue from public.company_reports_received(pg_temp.id('co'))) = 'FU the address is wrong'
  and not exists (select 1 from public.company_reports_received() r where to_jsonb(r) ? 'reporter')$$);
select pg_temp.ok('F-32 the company cannot resolve it (it stays in Drugbox''s queue)', $$pg_temp.rows('update public.company_reports set status = ''resolved'' where id = pg_temp.id(''rep'')') = 0$$);
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.ok('F-32 someone else sees nothing through company_reports_received()', $$not exists (select 1 from public.company_reports_received(pg_temp.id('co')))$$);
select pg_temp.as_user(pg_temp.u(5));
select pg_temp.ok('F-32 a moderator sees it open in Admin → Review', $$(select status from public.company_reports where id = pg_temp.id('rep')) = 'open'$$);
select pg_temp.ok('F-32 …and closes it', $$pg_temp.rows('update public.company_reports set status = ''resolved'' where id = pg_temp.id(''rep'')') = 1$$);

-- ══ F-26 the anon key reads no content ════════════════════════════════════════════════════════════════
select pg_temp.as_anon();
select pg_temp.ok('F-26 anon reads none of posts, comments, reactions, post media, jobs, products, enquiries',
  $$(select count(*) from public.posts) + (select count(*) from public.comments) + (select count(*) from public.reactions) + (select count(*) from public.post_media)
  + (select count(*) from public.jobs) + (select count(*) from public.products) + (select count(*) from public.enquiries) = 0$$);
select pg_temp.ok('F-26 anon reads no company team, sites, products, certificates, listings, references, groups, sponsors',
  $$(select count(*) from public.company_members) + (select count(*) from public.company_sites) + (select count(*) from public.company_products)
  + (select count(*) from public.site_certificates) + (select count(*) from public.company_listings) + (select count(*) from public.work_references)
  + (select count(*) from public.groups) + (select count(*) from public.group_members) + (select count(*) from public.sponsored_suppliers) = 0$$);
select pg_temp.ok('F-26 the sign-in page still has what it needs (settings, ticker, prices)', $$(select count(*) > 0 from public.settings) and (select count(*) > 0 from public.ticker_items) and (select count(*) > 0 from public.payment_products)$$);
select pg_temp.as_user(pg_temp.u(12));
select pg_temp.ok('F-26 members still read posts, comments, jobs and company teams', $$(select count(*) > 0 from public.posts) and (select count(*) > 0 from public.comments)
  and (select count(*) > 0 from public.jobs) and (select count(*) > 0 from public.company_members)$$);

-- ══ admins verify people — and nothing else of someone else's profile ═════════════════════════════════
select pg_temp.as_user(pg_temp.u(4));
select pg_temp.ok('a Drugbox admin marks a person verified', $$pg_temp.rows('update public.profiles set verified = true where id = pg_temp.u(12)') = 1$$);
select pg_temp.ok('…and the profile shows it', $$(select verified from public.profiles where id = pg_temp.u(12))$$);
select pg_temp.no('…but cannot rewrite their profile', $$update public.profiles set headline = 'FU written by an admin' where id = pg_temp.u(12)$$, '42501');
select pg_temp.as_user(pg_temp.u(5));
select pg_temp.ok('a moderator cannot verify people', $$pg_temp.rows('update public.profiles set verified = false where id = pg_temp.u(12)') = 0$$);
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.ok('a member cannot verify someone else', $$pg_temp.rows('update public.profiles set verified = true where id = pg_temp.u(3)') = 0$$);
select pg_temp.no('…nor themself', $$update public.profiles set verified = true where id = pg_temp.u(2)$$, '42501');
select pg_temp.ok('…and still edits their own profile', $$pg_temp.rows('update public.profiles set headline = ''FU QA specialist'' where id = pg_temp.u(2)') = 1$$);

-- ══ F-05 / F-44 ══════════════════════════════════════════════════════════════════════════════════════
select pg_temp.no('F-05 the whole-list directory_companies() is not in the API', $$select public.directory_companies(10)$$, '42501');
select pg_temp.ok('F-05 the paged directory works', $$json_array_length(public.directory_companies_page(10)) > 0$$);
select pg_temp.as_server();
select pg_temp.ok('F-44 every foreign key has an index on its leading column', $$not exists (select 1 from pg_constraint c
  where c.contype = 'f' and c.connamespace = 'public'::regnamespace
    and not exists (select 1 from pg_index i where i.indrelid = c.conrelid and i.indkey[0] = c.conkey[1]))$$);

-- ══ F-17 every kind of account can be erased; company history stays ═══════════════════════════════════
select pg_temp.as_user(pg_temp.u(8));
select pg_temp.step('a member likes the post', $$insert into public.reactions (post_id, user_id, kind) values (pg_temp.id('post'), pg_temp.u(8), 'like')$$);
select pg_temp.as_user(pg_temp.u(9));
select pg_temp.step('u9 creates a group', $$with x as (insert into public.groups (name, type, created_by) values ('FU group', 'public', pg_temp.u(9)) returning id) insert into ids select 'grp', id from x$$);
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.step('…u3 joins it', $$insert into public.group_members (group_id, user_id) values (pg_temp.id('grp'), pg_temp.u(3))$$);
select pg_temp.as_server();
update public.profiles set experience = '[{"company":"FU Co","title":"QC analyst"}]'::jsonb where id = pg_temp.u(2);
insert into public.work_references (author, candidate, kind, role_title, from_month, to_month, body, status, decided_by)
  values (pg_temp.u(1), pg_temp.u(2), 'honor', 'QC analyst', '2024-01-01', '2025-01-01', 'FU worked with us for a year; careful and reliable analyst.', 'published', pg_temp.u(5));
insert into public.verification_requests (company_id, submitted_by, registry, status, reviewed_by) values (pg_temp.id('spare'), pg_temp.u(13), 'FU-13', 'rejected', pg_temp.u(5));
insert into ids select 'deals', count(*)::text from public.deals where title like 'FU %';
select pg_temp.ok('F-17 a plain account', $$pg_temp.erase(pg_temp.u(12))$$);
select pg_temp.ok('F-17 a poster (their post had likes and comments)', $$pg_temp.erase(pg_temp.u(7))$$);
select pg_temp.ok('F-17 an applicant and reviewer', $$pg_temp.erase(pg_temp.u(2))$$);
select pg_temp.ok('F-17 a commenter who liked a post', $$pg_temp.erase(pg_temp.u(8))$$);
select pg_temp.ok('F-17 a group creator', $$pg_temp.erase(pg_temp.u(9))$$);
select pg_temp.ok('F-17 …the group stays, with its member', $$exists (select 1 from public.groups where id = pg_temp.id('grp') and created_by is null)
  and exists (select 1 from public.group_members where group_id = pg_temp.id('grp') and user_id = pg_temp.u(3))$$);
select pg_temp.ok('F-17 a moderator who decided references and verifications', $$pg_temp.erase(pg_temp.u(5))$$);
select pg_temp.ok('F-17 the owner of a company with deals on record', $$pg_temp.erase(pg_temp.u(11))$$);
select pg_temp.ok('F-17 …the company stays, unclaimed, with its deals; the old owner''s membership is gone',
  $$(select status = 'unclaimed' and owner_id is null from public.companies where id = pg_temp.id('supplier'))
  and (select count(*) from public.deals where to_company_id = pg_temp.id('supplier')) = 2
  and not exists (select 1 from public.company_members where company_id = pg_temp.id('supplier'))$$);
select pg_temp.ok('F-17 the owner of a company in a buying group', $$pg_temp.erase(pg_temp.u(10))$$);
select pg_temp.ok('F-17 …the buying group keeps the company', $$exists (select 1 from public.deal_members where deal_id = pg_temp.id('dgroup') and company_id = pg_temp.id('buyer'))
  and (select status from public.companies where id = pg_temp.id('buyer')) = 'unclaimed'$$);
select pg_temp.ok('F-17 a person who applied through a company page', $$pg_temp.erase(pg_temp.u(6))$$);
select pg_temp.ok('F-17 …their job request (personal data) goes with the account', $$not exists (select 1 from public.deals where title = 'FU application')$$);
select pg_temp.ok('F-17 the owner of a company that posted jobs, organised a buying group and was paid', $$pg_temp.erase(pg_temp.u(1))$$);
select pg_temp.ok('F-17 …the buying group they organised stays, its sender unknown, with its members', $$exists (select 1 from public.deals where id = pg_temp.id('dgroup') and from_user is null)
  and exists (select 1 from public.deal_members where deal_id = pg_temp.id('dgroup'))$$);
select pg_temp.ok('F-17 …FU Co is unclaimed, its job and paid order history are as before', $$(select status from public.companies where id = pg_temp.id('co')) = 'unclaimed'
  and (select count(*) from public.deals where title like 'FU %') = pg_temp.id('deals') - 1$$);
select pg_temp.as_server();
select pg_temp.step('Drugbox takes a page back from its owner (SQL / server)', $$update public.companies set owner_id = null where id = pg_temp.id('spare')$$);
select pg_temp.ok('F-17 a page without an owner is unclaimed and the old owner is off its team', $$(select status from public.companies where id = pg_temp.id('spare')) = 'unclaimed'
  and not exists (select 1 from public.company_members where company_id = pg_temp.id('spare') and user_id = pg_temp.u(13))$$);
select pg_temp.as_user(pg_temp.u(13));
select pg_temp.ok('F-17 …so the old owner cannot edit it any more', $$pg_temp.rows('update public.companies set bio = ''FU mine again'' where id = pg_temp.id(''spare'')') = 0$$);

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
