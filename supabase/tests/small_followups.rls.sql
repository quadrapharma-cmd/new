-- Small follow-ups (0025): company documents are for signed-in members only — anon gets an empty answer (N-7); a private-group invitation notifies the
-- invited person, and the notice goes when the invitation is withdrawn (N-8); a taken company slug gets a suffix from the
-- database instead of a unique violation (F-74).
-- Runs as the real API roles with a JWT, in one transaction that is rolled back; test data carries the "SF " marker.
-- Run on a fresh database (stub + migrations): psql -f supabase/tests/small_followups.rls.sql
-- Harness as in followups.rls.sql: step()/ok()/no(); a negative check passes only with the expected SQLSTATE; non-zero exit on failure.
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
create function pg_temp.u(n int) returns uuid language sql immutable as $$ select ('f2500000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid $$;
-- group_invite notifications a person has for a group (counted by the server, whatever row security shows)
create function pg_temp.invites(p_to uuid, p_group bigint) returns int language sql stable as $$
  select count(*)::int from public.notifications where user_id = p_to and group_id = p_group and type = 'group_invite' $$;

-- people: u1 company owner + group admin, u2 invited person, u3 outsider, u4 second founder (same company name), u5 plain member
select pg_temp.as_server();
insert into auth.users (id, email) select pg_temp.u(g), 'sf' || g || '@sf25.test' from generate_series(1, 5) g on conflict do nothing;
insert into public.profiles (id, name) select pg_temp.u(g), 'SF person ' || g from generate_series(1, 5) g on conflict (id) do nothing;
insert into public.companies (owner_id, name, slug, type, status, registry) values (pg_temp.u(1), 'SF Co', 'sf-co', 'Manufacturer', 'verified', 'SF-1');
insert into ids select 'co', id from public.companies where slug = 'sf-co';
insert into public.company_documents (company_id, type, product, number, expiry, status, file_path, created_by)
  values (pg_temp.id('co'), 'CEP', 'SF Paracetamol', 'R1-CEP-2020-001', '2030-01-01', 'declared', 'verification/sf/cep.pdf', pg_temp.u(1));

-- ══ N-7 company documents: members only ═══════════════════════════════════════════════════════
select pg_temp.as_anon();
select pg_temp.ok('N-7 anon reads no company_documents metadata (empty answer, no error)', $$(select count(*) from public.company_documents) = 0$$);
select pg_temp.ok('N-7 anon reads nothing through company_documents_public', $$(select count(*) from public.company_documents_public) = 0$$);
select pg_temp.ok('N-7 …not even the certificate number of a known company', $$not exists (select 1 from public.company_documents where number = 'R1-CEP-2020-001')
  and not exists (select 1 from public.company_documents_public where company_id = pg_temp.id('co'))$$);
select pg_temp.no('N-7 anon never reads the private file path', $$select file_path from public.company_documents$$, '42501');
select pg_temp.as_user(pg_temp.u(5));
select pg_temp.ok('N-7 a signed-in member still reads another company''s document metadata', $$(select count(*) from public.company_documents where company_id = pg_temp.id('co')) = 1$$);
select pg_temp.ok('N-7 …and through company_documents_public', $$(select number from public.company_documents_public where company_id = pg_temp.id('co')) = 'R1-CEP-2020-001'$$);
select pg_temp.no('N-7 the private file path stays hidden from members', $$select file_path from public.company_documents$$, '42501');
select pg_temp.as_server();
select pg_temp.ok('N-7 the read policy names authenticated only', $$(select roles from pg_policies where tablename = 'company_documents' and policyname = 'documents: everyone reads metadata') = '{authenticated}'::name[]$$);
select pg_temp.ok('N-7 no other select policy opens the table to anon', $$not exists (select 1 from pg_policies where tablename = 'company_documents' and cmd in ('SELECT', 'ALL')
  and roles && array['anon', 'public']::name[])$$);

-- ══ N-8 a private-group invitation notifies the invited person ════════════════════════════════
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 opens a private group', $$with x as (insert into public.groups (name, type, created_by) values ('SF Private room', 'private', pg_temp.u(1)) returning id) insert into ids select 'grp', id from x$$);
select pg_temp.step('u1 invites u2', $$insert into public.group_invites (group_id, user_id, invited_by) values (pg_temp.id('grp'), pg_temp.u(2), pg_temp.u(1))$$);
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.ok('N-8 the invited person has a group_invite notification from the inviter', $$(select count(*) from public.notifications where user_id = pg_temp.u(2) and type = 'group_invite'
  and from_user = pg_temp.u(1) and group_id = pg_temp.id('grp') and not read) = 1$$);
select pg_temp.ok('N-8 …whose message names the group (the live app shows "<sender> <message>")', $$(select message from public.notifications where user_id = pg_temp.u(2) and type = 'group_invite') = 'invited you to join the private group "SF Private room"'$$);
select pg_temp.ok('N-8 …and the sender shows through the adapter''s join (actor:profiles!notifications_from_user_fkey)', $$(select p.name from public.notifications n join public.profiles p on p.id = n.from_user where n.user_id = pg_temp.u(2) and n.type = 'group_invite') = (select name from public.profiles where id = pg_temp.u(1))$$);
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.ok('N-8 nobody else sees it', $$(select count(*) from public.notifications where type = 'group_invite') = 0$$);
select pg_temp.as_server();
select pg_temp.ok('N-8 the inviter gets nothing', $$(select count(*) from public.notifications where user_id = pg_temp.u(1) and type = 'group_invite') = 0$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 withdraws the invitation', $$delete from public.group_invites where group_id = pg_temp.id('grp') and user_id = pg_temp.u(2)$$);
select pg_temp.as_server();
select pg_temp.ok('N-8 a withdrawn invitation takes its notification', $$pg_temp.invites(pg_temp.u(2), pg_temp.id('grp')) = 0$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 invites u2 again', $$insert into public.group_invites (group_id, user_id, invited_by) values (pg_temp.id('grp'), pg_temp.u(2), pg_temp.u(1))$$);
select pg_temp.as_server();
select pg_temp.ok('N-8 inviting again notifies again, once', $$pg_temp.invites(pg_temp.u(2), pg_temp.id('grp')) = 1$$);
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.step('u2 joins with the invitation', $$insert into public.group_members (group_id, user_id, role) values (pg_temp.id('grp'), pg_temp.u(2), 'member')$$);
select pg_temp.as_server();
select pg_temp.ok('N-8 joining uses up the invitation and keeps the notice (history)', $$not exists (select 1 from public.group_invites where group_id = pg_temp.id('grp'))
  and pg_temp.invites(pg_temp.u(2), pg_temp.id('grp')) = 1$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 invites u3, who declines', $$insert into public.group_invites (group_id, user_id, invited_by) values (pg_temp.id('grp'), pg_temp.u(3), pg_temp.u(1))$$);
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.ok('N-8 u3 was notified', $$(select count(*) from public.notifications where type = 'group_invite' and group_id = pg_temp.id('grp')) = 1$$);
select pg_temp.step('u3 declines', $$delete from public.group_invites where group_id = pg_temp.id('grp') and user_id = pg_temp.u(3)$$);
select pg_temp.as_server();
select pg_temp.ok('N-8 a declined invitation takes its notification', $$pg_temp.invites(pg_temp.u(3), pg_temp.id('grp')) = 0$$);
select pg_temp.as_user(pg_temp.u(5));
select pg_temp.step('u5 opens a group and "invites" themself', $$with x as (insert into public.groups (name, type, created_by) values ('SF u5 room', 'private', pg_temp.u(5)) returning id) insert into ids select 'grp5', id from x;
  insert into public.group_invites (group_id, user_id, invited_by) values (pg_temp.id('grp5'), pg_temp.u(5), pg_temp.u(5))$$);
select pg_temp.as_server();
select pg_temp.ok('N-8 inviting yourself notifies nobody', $$pg_temp.invites(pg_temp.u(5), pg_temp.id('grp5')) = 0$$);
select pg_temp.no('N-8 a browser cannot write a group_invite notice for someone else', $$select pg_temp.as_user(pg_temp.u(3));
  insert into public.notifications (user_id, type, from_user, group_id, message) values (pg_temp.u(2), 'group_invite', pg_temp.u(3), pg_temp.id('grp'), 'x')$$, '42501');
select pg_temp.as_server();
select pg_temp.step('the group is deleted', $$delete from public.groups where id = pg_temp.id('grp')$$);
select pg_temp.ok('N-8 deleting the group removes its notices', $$(select count(*) from public.notifications where type = 'group_invite' and user_id = pg_temp.u(2)) = 0$$);
select pg_temp.ok('N-8 the trigger functions are not callable from the API', $$not has_function_privilege('authenticated', 'public.notify_group_invite()', 'execute')
  and not has_function_privilege('anon', 'public.group_invite_withdrawn()', 'execute')$$);

-- ══ F-74 a unique company slug from the server ═════════════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 creates "SF Same Pharma"', $$insert into public.companies (owner_id, name, slug, type) values (pg_temp.u(1), 'SF Same Pharma', 'sf-same-pharma', 'Manufacturer')$$);
select pg_temp.as_user(pg_temp.u(4));
select pg_temp.step('u4 creates a company with the same name and slug', $$with x as (insert into public.companies (owner_id, name, slug, type)
  values (pg_temp.u(4), 'SF Same Pharma', 'sf-same-pharma', 'Manufacturer') returning slug) insert into ids select 's2', slug from x$$);
select pg_temp.ok('F-74 a second company with the same slug is saved (no unique violation) as -2', $$(select v from ids where k = 's2') = 'sf-same-pharma-2'$$);
select pg_temp.step('and a third', $$with x as (insert into public.companies (owner_id, name, slug, type)
  values (pg_temp.u(4), 'SF Same Pharma', 'sf-same-pharma', 'Manufacturer') returning slug) insert into ids select 's3', slug from x$$);
select pg_temp.ok('F-74 …a third as -3', $$(select v from ids where k = 's3') = 'sf-same-pharma-3'$$);
select pg_temp.step('seven more with the same slug', $$insert into public.companies (owner_id, name, slug, type) select pg_temp.u(4), 'SF Same Pharma', 'sf-same-pharma', 'Manufacturer' from generate_series(1, 7)$$);
select pg_temp.ok('F-74 after -9 a short random suffix keeps them unique', $$(select count(distinct slug) from public.companies where name = 'SF Same Pharma') = 10
  and exists (select 1 from public.companies where name = 'SF Same Pharma' and slug ~ '^sf-same-pharma-[0-9a-f]{6}$')$$);
select pg_temp.ok('F-74 the original keeps its slug', $$(select owner_id from public.companies where slug = 'sf-same-pharma') = pg_temp.u(1)$$);
select pg_temp.step('an Arabic-only name without a slug', $$with x as (insert into public.companies (owner_id, name, type) values (pg_temp.u(4), 'شركة الاختبار', 'Manufacturer') returning id, slug)
  insert into ids select 'ar', slug = 'company-' || id from x$$);
select pg_temp.ok('F-74 an Arabic-only name without a slug gets company-<id>', $$(select v from ids where k = 'ar')::boolean$$);
select pg_temp.step('a free slug', $$with x as (insert into public.companies (owner_id, name, slug, type) values (pg_temp.u(4), 'SF Unique', 'sf-unique-x1', 'Manufacturer') returning slug) insert into ids select 'free', slug from x$$);
select pg_temp.ok('F-74 a free slug is kept as sent', $$(select v from ids where k = 'free') = 'sf-unique-x1'$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.no('F-74 the slug still never changes on update (0020)', $$update public.companies set slug = 'sf-other' where id = pg_temp.id('co')$$, '42501');
select pg_temp.step('a normal page edit', $$update public.companies set tagline = 'SF tagline' where id = pg_temp.id('co')$$);
select pg_temp.ok('F-74 a normal page edit keeps the slug', $$(select slug from public.companies where id = pg_temp.id('co')) = 'sf-co' and (select tagline from public.companies where id = pg_temp.id('co')) = 'SF tagline'$$);
select pg_temp.as_server();
select pg_temp.ok('F-74 the slug trigger function is not callable from the API', $$not has_function_privilege('anon', 'public.companies_before_write()', 'execute') and not has_function_privilege('authenticated', 'public.companies_before_write()', 'execute')$$);

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
