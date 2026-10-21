-- Groups (0061): sector / country / post policy checks, the Sub-Admin (moderator) role, mute, the last admin, the new-post digest
-- notice, "admins only" and archived groups, a removed member is told, join requests answered by a moderator, deal-room listings
-- answered through the deals engine. Runs as the real API roles with a JWT, in one transaction that is rolled back; test data carries
-- the "GR " marker. Run on a fresh database (stub + migrations): psql -f supabase/tests/groups.rls.sql
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

-- A admin (creates the groups), M becomes the moderator, C plain member, D outsider
insert into auth.users (id, email) values ('a2000000-0000-0000-0000-000000000001','gr-a@x'),('a2000000-0000-0000-0000-000000000002','gr-m@x'),
  ('a2000000-0000-0000-0000-000000000003','gr-c@x'),('a2000000-0000-0000-0000-000000000004','gr-d@x') on conflict do nothing;
insert into public.profiles (id, name) values ('a2000000-0000-0000-0000-000000000001','GR Admin'),('a2000000-0000-0000-0000-000000000002','GR Moderator'),
  ('a2000000-0000-0000-0000-000000000003','GR Member'),('a2000000-0000-0000-0000-000000000004','GR Outsider') on conflict (id) do nothing;
create function pg_temp.A() returns void language sql as $$ select pg_temp.as_user('a2000000-0000-0000-0000-000000000001') $$;
create function pg_temp.M() returns void language sql as $$ select pg_temp.as_user('a2000000-0000-0000-0000-000000000002') $$;
create function pg_temp.C() returns void language sql as $$ select pg_temp.as_user('a2000000-0000-0000-0000-000000000003') $$;
create function pg_temp.D() returns void language sql as $$ select pg_temp.as_user('a2000000-0000-0000-0000-000000000004') $$;
create function pg_temp.unread(u text, t text) returns bigint language sql stable security definer as $$
  select count(*) from public.notifications n where n.user_id = u::uuid and n.type = t and not n.read and n.group_id in (pg_temp.id('g'), pg_temp.id('p'), pg_temp.id('dr')) $$;

-- 1. a group with its sector, countries and post policy
select pg_temp.A();
select pg_temp.step('A creates a public group (Pharma, Egypt + UAE)', $$with x as (insert into public.groups (created_by, name, description, type, sector, country) values ('a2000000-0000-0000-0000-000000000001', 'GR Pharma Talk', 'Regulatory chat', 'public', 'pharma', '{EG,AE}') returning id) insert into ids select 'g', id::text from x$$);
select pg_temp.ok('the creator is its admin', $$public.is_group_member(pg_temp.id('g'), array['admin'])$$);
select pg_temp.no('a country is a two-letter code', $$insert into public.groups (created_by, name, type, country) values ('a2000000-0000-0000-0000-000000000001', 'GR Bad', 'public', '{Egypt}')$$, '23514');
select pg_temp.no('the sector is one of the list', $$insert into public.groups (created_by, name, type, sector) values ('a2000000-0000-0000-0000-000000000001', 'GR Bad', 'public', 'food')$$, '23514');
select pg_temp.no('the post policy is members or admins', $$insert into public.groups (created_by, name, type, post_policy) values ('a2000000-0000-0000-0000-000000000001', 'GR Bad', 'public', 'anyone')$$, '23514');
select pg_temp.ok('search finds it by a word of its description, any case', $$exists (select 1 from public.groups_search('REGULATORY') where id = pg_temp.id('g'))$$);
select pg_temp.ok('a wildcard in the search is a plain character', $$not exists (select 1 from public.groups_search('gr%talk') where id = pg_temp.id('g'))$$);
select pg_temp.M(); select pg_temp.step('M joins', $$insert into public.group_members (group_id, user_id) values (pg_temp.id('g'), 'a2000000-0000-0000-0000-000000000002')$$);
select pg_temp.C(); select pg_temp.step('C joins', $$insert into public.group_members (group_id, user_id) values (pg_temp.id('g'), 'a2000000-0000-0000-0000-000000000003')$$);

-- 2. roles: only admins change them; the moderator is not an admin
select pg_temp.no('C cannot make itself a moderator', $$update public.group_members set role = 'moderator' where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000003'$$, '42501');
select pg_temp.A();
select pg_temp.step('A makes M a moderator (Sub-Admin)', $$update public.group_members set role = 'moderator' where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000002'$$);
select pg_temp.ok('M is a moderator', $$(select role = 'moderator' from public.group_members where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000002')$$);
select pg_temp.no('a role outside member / moderator / admin is refused', $$update public.group_members set role = 'owner' where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000003'$$, '23514');
select pg_temp.M();
select pg_temp.step('the moderator tries to make C an admin', $$update public.group_members set role = 'admin' where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000003'$$);
select pg_temp.ok('… C is still a plain member', $$(select role = 'member' from public.group_members where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000003')$$);
select pg_temp.step('the moderator tries to edit the group''s settings', $$update public.groups set name = 'GR Hijacked' where id = pg_temp.id('g')$$);
select pg_temp.ok('… the name is unchanged', $$(select name = 'GR Pharma Talk' from public.groups where id = pg_temp.id('g'))$$);

-- 3. the last admin
select pg_temp.A();
select pg_temp.no('the only admin cannot step down', $$update public.group_members set role = 'member' where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000001'$$, '42501');
select pg_temp.no('the only admin cannot leave', $$delete from public.group_members where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000001'$$, '42501');

-- 4. new posts: one unread notice per member and group, counting; mute; the author is not told
select pg_temp.C();
select pg_temp.step('C posts twice', $$insert into public.posts (user_id, body, group_id) values ('a2000000-0000-0000-0000-000000000003', 'GR first', pg_temp.id('g')), ('a2000000-0000-0000-0000-000000000003', 'GR second', pg_temp.id('g'))$$);
select pg_temp.as_server();
select pg_temp.ok('A has one unread notice for the group, saying 2 new posts', $$pg_temp.unread('a2000000-0000-0000-0000-000000000001', 'group_post') = 1
  and (select message like '2 new posts%' from public.notifications where user_id = 'a2000000-0000-0000-0000-000000000001' and type = 'group_post' and group_id = pg_temp.id('g'))$$);
select pg_temp.C();
select pg_temp.ok('the author is not told about its own posts', $$pg_temp.unread('a2000000-0000-0000-0000-000000000003', 'group_post') = 0$$);
select pg_temp.step('C mutes the group', $$update public.group_members set muted = true where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000003'$$);
select pg_temp.step('C tries to mute the group for M', $$update public.group_members set muted = true where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000002'$$);
select pg_temp.as_server();
select pg_temp.ok('… M is not muted, C is', $$(select not muted from public.group_members where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000002')
  and (select muted from public.group_members where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000003')$$);
select pg_temp.A();
select pg_temp.no('even an admin cannot mute the group for C', $$update public.group_members set muted = false where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000003'$$, '42501');
select pg_temp.step('A posts', $$with x as (insert into public.posts (user_id, body, group_id) values ('a2000000-0000-0000-0000-000000000001', 'GR from the admin', pg_temp.id('g')) returning id) insert into ids select 'apost', id::text from x$$);
select pg_temp.ok('the muted member is not told', $$pg_temp.unread('a2000000-0000-0000-0000-000000000003', 'group_post') = 0$$);
select pg_temp.ok('M is told (one notice)', $$pg_temp.unread('a2000000-0000-0000-0000-000000000002', 'group_post') = 1$$);

-- 5. moderation: the moderator removes posts and comments; a plain member does not; the post's author removes comments on it
select pg_temp.C();
select pg_temp.step('C deletes nothing of A''s', $$delete from public.posts where id = pg_temp.id('apost')$$);
select pg_temp.ok('… A''s post is still there', $$exists (select 1 from public.posts where id = pg_temp.id('apost'))$$);
select pg_temp.M();
select pg_temp.step('M comments on A''s post', $$with x as (insert into public.comments (post_id, user_id, body) values (pg_temp.id('apost'), 'a2000000-0000-0000-0000-000000000002', 'GR comment') returning id) insert into ids select 'cm', id::text from x$$);
select pg_temp.C();
select pg_temp.step('C tries to delete M''s comment', $$delete from public.comments where id = pg_temp.id('cm')$$);
select pg_temp.ok('… it is still there', $$exists (select 1 from public.comments where id = pg_temp.id('cm'))$$);
select pg_temp.A();
select pg_temp.step('A (the post''s author) removes the comment on its post', $$delete from public.comments where id = pg_temp.id('cm')$$);
select pg_temp.ok('… it is gone', $$not exists (select 1 from public.comments where id = pg_temp.id('cm'))$$);
select pg_temp.M();
select pg_temp.step('the moderator removes C''s post', $$delete from public.posts where group_id = pg_temp.id('g') and body = 'GR first'$$);
select pg_temp.ok('… it is gone', $$not exists (select 1 from public.posts where group_id = pg_temp.id('g') and body = 'GR first')$$);
select pg_temp.ok('C is told its post was removed (with an excerpt)', $$pg_temp.unread('a2000000-0000-0000-0000-000000000003', 'group_post_removed') = 1$$);
select pg_temp.C();
select pg_temp.step('C deletes its own second post', $$delete from public.posts where group_id = pg_temp.id('g') and body = 'GR second'$$);
select pg_temp.ok('… and is not told about its own deletion', $$pg_temp.unread('a2000000-0000-0000-0000-000000000003', 'group_post_removed') = 1$$);

-- 6. "admins only" posting
select pg_temp.A();
select pg_temp.step('A sets the group to admins-only posting', $$update public.groups set post_policy = 'admins' where id = pg_temp.id('g')$$);
select pg_temp.C();
select pg_temp.no('a plain member cannot post', $$insert into public.posts (user_id, body, group_id) values ('a2000000-0000-0000-0000-000000000003', 'GR blocked', pg_temp.id('g'))$$, '42501');
select pg_temp.M();
select pg_temp.step('the moderator can post', $$insert into public.posts (user_id, body, group_id) values ('a2000000-0000-0000-0000-000000000002', 'GR mod post', pg_temp.id('g'))$$);
select pg_temp.ok('… the moderator''s post is there', $$exists (select 1 from public.posts where group_id = pg_temp.id('g') and body = 'GR mod post')$$);
select pg_temp.A(); select pg_temp.step('A opens posting again', $$update public.groups set post_policy = 'members' where id = pg_temp.id('g')$$);

-- 7. archive: members still read, nobody else sees it, no new members, posts or comments; restore
select pg_temp.step('A archives the group', $$update public.groups set archived_at = now() where id = pg_temp.id('g')$$);
select pg_temp.D();
select pg_temp.ok('an outsider no longer sees the archived group', $$not exists (select 1 from public.groups where id = pg_temp.id('g'))$$);
select pg_temp.ok('… nor its posts', $$not exists (select 1 from public.posts where group_id = pg_temp.id('g'))$$);
select pg_temp.ok('search leaves it out', $$not exists (select 1 from public.groups_search('GR Pharma') where id = pg_temp.id('g'))$$);
select pg_temp.no('an outsider cannot join it', $$insert into public.group_members (group_id, user_id) values (pg_temp.id('g'), 'a2000000-0000-0000-0000-000000000004')$$, '42501');
select pg_temp.C();
select pg_temp.ok('a member still reads it and its posts', $$exists (select 1 from public.groups where id = pg_temp.id('g')) and exists (select 1 from public.posts where id = pg_temp.id('apost'))$$);
select pg_temp.no('a member cannot post in it', $$insert into public.posts (user_id, body, group_id) values ('a2000000-0000-0000-0000-000000000003', 'GR archived post', pg_temp.id('g'))$$, '42501');
select pg_temp.no('a member cannot comment in it', $$insert into public.comments (post_id, user_id, body) values (pg_temp.id('apost'), 'a2000000-0000-0000-0000-000000000003', 'GR archived comment')$$, '42501');
select pg_temp.A();
select pg_temp.no('even its admin cannot post while it is archived', $$insert into public.posts (user_id, body, group_id) values ('a2000000-0000-0000-0000-000000000001', 'GR archived', pg_temp.id('g'))$$, '42501');
select pg_temp.step('A restores it', $$update public.groups set archived_at = null where id = pg_temp.id('g')$$);
select pg_temp.D();
select pg_temp.ok('the outsider sees it again', $$exists (select 1 from public.groups where id = pg_temp.id('g'))$$);

-- the creator manages only while an admin
select pg_temp.as_server();
select pg_temp.step('M becomes an admin, A steps down to member', $$update public.group_members set role = 'admin' where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000002';
  update public.group_members set role = 'member' where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000001'$$);
select pg_temp.A();
select pg_temp.step('the demoted creator tries to rename and archive', $$update public.groups set name = 'GR Taken over', archived_at = now() where id = pg_temp.id('g')$$);
select pg_temp.step('… and to delete it', $$delete from public.groups where id = pg_temp.id('g')$$);
select pg_temp.as_server();
select pg_temp.ok('… nothing changed and the group is still there', $$(select name = 'GR Pharma Talk' and archived_at is null from public.groups where id = pg_temp.id('g'))$$);
select pg_temp.step('A is an admin again, M a moderator', $$update public.group_members set role = 'admin' where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000001';
  update public.group_members set role = 'moderator' where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000002'$$);

-- 8. removing a member tells them; leaving does not
select pg_temp.A();
select pg_temp.step('A removes C', $$delete from public.group_members where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000003'$$);
select pg_temp.ok('C is told it was removed', $$pg_temp.unread('a2000000-0000-0000-0000-000000000003', 'group_removed') = 1$$);
select pg_temp.M();
select pg_temp.step('the moderator tries to remove A', $$delete from public.group_members where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000001'$$);
select pg_temp.ok('… A is still a member', $$public.is_group_member(pg_temp.id('g'), array['admin']) is not null and exists (select 1 from public.group_members where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000001')$$);
select pg_temp.step('M leaves', $$delete from public.group_members where group_id = pg_temp.id('g') and user_id = 'a2000000-0000-0000-0000-000000000002'$$);
select pg_temp.ok('leaving sends no removal notice', $$pg_temp.unread('a2000000-0000-0000-0000-000000000002', 'group_removed') = 0$$);
select pg_temp.A();
select pg_temp.step('deleting the group removes its last admin with it', $$delete from public.groups where id = pg_temp.id('g')$$);
select pg_temp.ok('… the group and its members are gone', $$not exists (select 1 from public.groups where id = pg_temp.id('g')) and not exists (select 1 from public.group_members where group_id = pg_temp.id('g'))$$);

-- 9. a private group: a moderator answers join requests; the person is told either way
select pg_temp.step('A creates a private group listed in discovery', $$with x as (insert into public.groups (created_by, name, type, listed) values ('a2000000-0000-0000-0000-000000000001', 'GR Private', 'private', true) returning id) insert into ids select 'p', id::text from x$$);
select pg_temp.as_server();
select pg_temp.step('M is a moderator there', $$insert into public.group_members (group_id, user_id, role) values (pg_temp.id('p'), 'a2000000-0000-0000-0000-000000000002', 'moderator')$$);
select pg_temp.D(); select pg_temp.step('D asks to join', $$select public.group_request_join(pg_temp.id('p'), 'GR please')$$);
select pg_temp.C(); select pg_temp.step('C asks to join', $$select public.group_request_join(pg_temp.id('p'), 'GR me too')$$);
select pg_temp.no('a requester cannot approve itself', $$select public.group_decide_request(pg_temp.id('p'), 'a2000000-0000-0000-0000-000000000003', true)$$, '42501');
select pg_temp.M();
select pg_temp.step('the moderator declines D', $$select public.group_decide_request(pg_temp.id('p'), 'a2000000-0000-0000-0000-000000000004', false)$$);
select pg_temp.step('the moderator approves C', $$select public.group_decide_request(pg_temp.id('p'), 'a2000000-0000-0000-0000-000000000003', true)$$);
select pg_temp.ok('D is told politely', $$pg_temp.unread('a2000000-0000-0000-0000-000000000004', 'group_join_declined') = 1$$);
select pg_temp.ok('C is told and is a member', $$pg_temp.unread('a2000000-0000-0000-0000-000000000003', 'group_join_approved') = 1 and public.is_group_member(pg_temp.id('p'))$$);
select pg_temp.no('the same request cannot be answered twice', $$select public.group_decide_request(pg_temp.id('p'), 'a2000000-0000-0000-0000-000000000004', true)$$, 'P0002');
select pg_temp.D();
select pg_temp.ok('D does not see the private group''s members', $$not exists (select 1 from public.group_members where group_id = pg_temp.id('p'))$$);

-- 10. deal-room listings
select pg_temp.A(); select pg_temp.step('A creates its company page', $$insert into public.companies (name, type, slug) values ('GR Buyer','Distributor','gr-buyer')$$);
select pg_temp.C(); select pg_temp.step('C creates its company page', $$insert into public.companies (name, type, slug) values ('GR Seller','Manufacturer','gr-seller')$$);
select pg_temp.as_server();
insert into ids select 'cob', id::text from public.companies where slug = 'gr-buyer';
insert into ids select 'cos', id::text from public.companies where slug = 'gr-seller';
select pg_temp.A();
select pg_temp.step('A creates a deal room', $$with x as (insert into public.groups (created_by, name, type, topic) values ('a2000000-0000-0000-0000-000000000001', 'GR Deal Room', 'public', 'DEAL ROOM') returning id) insert into ids select 'dr', id::text from x$$);
select pg_temp.no('a listing in a group that is not a deal room is refused', $$insert into public.group_listings (group_id, kind, title) values (pg_temp.id('p'), 'rfq', 'GR wrong room')$$, '42501');
select pg_temp.step('A posts a request to buy for its company', $$with x as (insert into public.group_listings (group_id, company_id, kind, title, details, responses, status) values (pg_temp.id('dr'), pg_temp.id('cob'), 'rfq', 'GR Paracetamol API 500 kg', 'CIF Alexandria', 99, 'closed') returning id) insert into ids select 'l', id::text from x$$);
select pg_temp.ok('a new listing starts open with no answers (the browser''s numbers are ignored)', $$(select status = 'open' and responses = 0 from public.group_listings where id = pg_temp.id('l'))$$);
select pg_temp.C();
select pg_temp.no('a non-member cannot post a listing', $$insert into public.group_listings (group_id, kind, title) values (pg_temp.id('dr'), 'sale', 'GR outsider sale')$$, '42501');
select pg_temp.no('a non-member cannot answer a listing', $$select public.group_listing_respond(pg_temp.id('l'), 'gr-seller', 'hi')$$, '42501');
select pg_temp.step('C joins the deal room', $$insert into public.group_members (group_id, user_id) values (pg_temp.id('dr'), 'a2000000-0000-0000-0000-000000000003')$$);
select pg_temp.no('C cannot post for a company it does not belong to', $$insert into public.group_listings (group_id, company_id, kind, title) values (pg_temp.id('dr'), pg_temp.id('cob'), 'sale', 'GR fake sale')$$, '42501');
select pg_temp.step('C tries to edit A''s listing', $$update public.group_listings set title = 'GR changed', responses = 50 where id = pg_temp.id('l')$$);
select pg_temp.ok('… nothing changed', $$(select title = 'GR Paracetamol API 500 kg' and responses = 0 from public.group_listings where id = pg_temp.id('l'))$$);
select pg_temp.step('C lists without a company, then tries to put A''s company on it', $$with x as (insert into public.group_listings (group_id, kind, title) values (pg_temp.id('dr'), 'sale', 'GR plain sale') returning id) insert into ids select 'l2', id::text from x$$);
select pg_temp.no('… refused (a listing speaks only for a company you belong to)', $$update public.group_listings set company_id = pg_temp.id('cob') where id = pg_temp.id('l2')$$, '42501');
select pg_temp.no('C cannot write an answer row by hand', $$insert into public.group_listing_responses (listing_id, user_id) values (pg_temp.id('l'), 'a2000000-0000-0000-0000-000000000003')$$, '42501');
select pg_temp.no('C cannot answer for a company it does not belong to', $$select public.group_listing_respond(pg_temp.id('l'), 'gr-buyer', 'as A')$$, '42501');
select pg_temp.step('C answers with an offer from its company', $$insert into ids select 'ref', public.group_listing_respond(pg_temp.id('l'), 'gr-seller', 'GR we can supply', 'USD 4.1/kg', '3 weeks')$$);
select pg_temp.ok('the answer is a real deal from the seller to the buyer (an offer on a request to buy)', $$exists (select 1 from public.deals d where d.ref = (select v from ids where k = 'ref') and d.type = 'surplus'
  and d.from_company_id = pg_temp.id('cos') and d.to_company_id = pg_temp.id('cob'))$$);
select pg_temp.as_server();
select pg_temp.ok('A is told what came in and from where (not the bare title)', $$exists (select 1 from public.notifications where user_id = 'a2000000-0000-0000-0000-000000000001' and type = 'deal'
  and message = 'sent an offer for your request "GR Paracetamol API 500 kg" in the deal room "GR Deal Room"' and data ->> 'deal' = (select v from ids where k = 'ref'))$$);
select pg_temp.C();
select pg_temp.ok('the listing counts one answer', $$(select responses = 1 from public.group_listings where id = pg_temp.id('l'))$$);
select pg_temp.no('one answer per person', $$select public.group_listing_respond(pg_temp.id('l'), 'gr-seller', 'again')$$, '23505');
select pg_temp.ok('C reads its own answer', $$exists (select 1 from public.group_listing_responses where listing_id = pg_temp.id('l'))$$);
select pg_temp.A();
select pg_temp.no('A cannot answer its own listing', $$select public.group_listing_respond(pg_temp.id('l'), 'gr-buyer', 'me')$$, '42501');
select pg_temp.ok('the listing''s author reads who answered', $$(select count(*) = 1 from public.group_listing_responses where listing_id = pg_temp.id('l'))$$);
select pg_temp.step('A closes its listing', $$update public.group_listings set status = 'closed' where id = pg_temp.id('l')$$);
select pg_temp.as_server();
select pg_temp.step('M joins the deal room', $$insert into public.group_members (group_id, user_id) values (pg_temp.id('dr'), 'a2000000-0000-0000-0000-000000000002')$$);
select pg_temp.M();
select pg_temp.ok('another member does not read the answers', $$not exists (select 1 from public.group_listing_responses where listing_id = pg_temp.id('l'))$$);
select pg_temp.no('a closed listing takes no answers', $$select public.group_listing_respond(pg_temp.id('l'), 'gr-seller', 'late')$$, '42501');
select pg_temp.D();
select pg_temp.ok('an outsider still reads the public deal room''s listings', $$exists (select 1 from public.group_listings where id = pg_temp.id('l'))$$);
select pg_temp.as_anon();
select pg_temp.ok('anon reads no listing and no answer', $$(select count(*) = 0 from public.group_listings) and (select count(*) = 0 from public.group_listing_responses)$$);
select pg_temp.no('anon cannot search groups', $$select public.groups_search('gr')$$, '42501');

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
