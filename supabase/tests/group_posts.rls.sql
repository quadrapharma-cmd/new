-- Group posts (0027): a discussion inside every group. Group posts are posts with group_id: members (or every signed-in member
-- of a public group) read them, only members write them, the main feed is group_id IS NULL; comments, likes, files and saves
-- follow their post; group admins remove posts/comments, pin one post, answer reports; private groups can be listed and people
-- ask to join (group_request_join / group_decide_request / group_cancel_request) with notifications to the admins.
-- Runs as the real API roles with a JWT, in one transaction that is rolled back; test data carries the "GP " marker.
-- Run on a fresh database (stub + migrations): psql -f supabase/tests/group_posts.rls.sql
-- Harness as in small_followups.rls.sql: step()/ok()/no(); a negative check passes only with the expected SQLSTATE; non-zero exit on failure.
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
create function pg_temp.u(n int) returns uuid language sql immutable as $$ select ('f2700000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid $$;
-- counted by the server, whatever row security shows
create function pg_temp.notifs(p_to uuid, p_type text, p_group bigint) returns int language sql stable as $$
  select count(*)::int from public.notifications where user_id = p_to and type = p_type and group_id = p_group $$;
grant execute on all functions in schema pg_temp to authenticated, anon;

-- people: u1 creator + admin of every test group, u2 member, u3 outsider, u4 asks to join, u5 second admin of the private group,
-- u6 Drugbox moderator, u7 asks and is then invited, u8 asks and is declined
select pg_temp.as_server();
insert into auth.users (id, email) select pg_temp.u(g), 'gp' || g || '@gp27.test' from generate_series(1, 8) g on conflict do nothing;
insert into public.profiles (id, name) select pg_temp.u(g), 'GP person ' || g from generate_series(1, 8) g on conflict (id) do nothing;
update public.profiles set role = 'moderator' where id = pg_temp.u(6);

-- ══ groups: public, listed private, unlisted private ═════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 opens a public group (sends listed false)', $$with x as (insert into public.groups (name, type, created_by, listed) values ('GP Public', 'public', pg_temp.u(1), false) returning id) insert into ids select 'pub', id from x$$);
select pg_temp.step('u1 opens a listed private group', $$with x as (insert into public.groups (name, description, rules, type, created_by, listed) values ('GP Private', 'Approved members only', 'Be kind', 'private', pg_temp.u(1), true) returning id) insert into ids select 'priv', id from x$$);
select pg_temp.step('u1 opens an unlisted private group', $$with x as (insert into public.groups (name, type, created_by) values ('GP Secret', 'private', pg_temp.u(1)) returning id) insert into ids select 'unl', id from x$$);
select pg_temp.step('u1 opens a private deal room asking to be listed', $$with x as (insert into public.groups (name, type, topic, created_by, listed) values ('GP Deal', 'private', 'DEAL ROOM', pg_temp.u(1), true) returning id) insert into ids select 'deal', id from x$$);
select pg_temp.ok('a public group is always listed', $$(select listed from public.groups where id = pg_temp.id('pub'))$$);
select pg_temp.ok('a private group is unlisted unless asked; a listed one keeps its rules', $$not (select listed from public.groups where id = pg_temp.id('unl'))
  and (select listed and rules = 'Be kind' from public.groups where id = pg_temp.id('priv'))$$);
select pg_temp.ok('a private deal room is never listed', $$not (select listed from public.groups where id = pg_temp.id('deal'))$$);
select pg_temp.as_server();
insert into public.group_members (group_id, user_id, role) values (pg_temp.id('pub'), pg_temp.u(2), 'member'), (pg_temp.id('priv'), pg_temp.u(2), 'member'),
  (pg_temp.id('priv'), pg_temp.u(5), 'member');
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('u1 makes u5 an admin of the private group', $$update public.group_members set role = 'admin' where group_id = pg_temp.id('priv') and user_id = pg_temp.u(5)$$);

select pg_temp.as_user(pg_temp.u(3));
select pg_temp.ok('an outsider sees the public and the listed private group, not the unlisted one or the deal room', $$(select count(*) from public.groups where id in (pg_temp.id('pub'), pg_temp.id('priv'))) = 2
  and (select count(*) from public.groups where id in (pg_temp.id('unl'), pg_temp.id('deal'))) = 0$$);
select pg_temp.ok('an outsider reads the listed group''s description and rules', $$(select description || '|' || rules from public.groups where id = pg_temp.id('priv')) = 'Approved members only|Be kind'$$);
select pg_temp.ok('…but not the private group''s member list', $$(select count(*) from public.group_members where group_id = pg_temp.id('priv')) = 0$$);
select pg_temp.ok('…while a public group''s members are listed for signed-in members', $$(select count(*) from public.group_members where group_id = pg_temp.id('pub')) = 2$$);
select pg_temp.step('an outsider tries to edit the private group', $$update public.groups set rules = 'hacked' where id = pg_temp.id('priv')$$);
select pg_temp.ok('…and nothing changes', $$(select rules from public.groups where id = pg_temp.id('priv')) = 'Be kind'$$);
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.ok('a member reads the private group''s member list', $$(select count(*) from public.group_members where group_id = pg_temp.id('priv')) = 3$$);
select pg_temp.step('a plain member tries to edit the rules', $$update public.groups set rules = 'member rules' where id = pg_temp.id('priv')$$);
select pg_temp.ok('…and nothing changes', $$(select rules from public.groups where id = pg_temp.id('priv')) = 'Be kind'$$);
select pg_temp.as_user(pg_temp.u(5));
select pg_temp.step('the second admin (not the creator) edits the rules and description', $$update public.groups set rules = 'Be kind. No spam.', description = 'Approved members' where id = pg_temp.id('priv')$$);
select pg_temp.ok('…and they are saved; creator and member count untouched', $$(select rules || '|' || description || '|' || created_by::text || '|' || member_count from public.groups where id = pg_temp.id('priv'))
  = 'Be kind. No spam.|Approved members|' || pg_temp.u(1)::text || '|3'$$);
select pg_temp.as_anon();
select pg_temp.ok('anon sees no group, no member', $$(select count(*) from public.groups where name like 'GP %') = 0 and (select count(*) from public.group_members) = 0$$);

-- ══ group posts: who writes, who reads, the main feed ════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.step('a member posts in the public group', $$with x as (insert into public.posts (user_id, body, group_id) values (pg_temp.u(2), 'GP public group post', pg_temp.id('pub')) returning id) insert into ids select 'p_pub', id from x$$);
select pg_temp.step('a member posts in the private group', $$with x as (insert into public.posts (user_id, body, group_id) values (pg_temp.u(2), 'GP private group post', pg_temp.id('priv')) returning id) insert into ids select 'p_priv', id from x$$);
select pg_temp.step('a member posts in the main feed', $$with x as (insert into public.posts (user_id, body) values (pg_temp.u(2), 'GP main feed post') returning id) insert into ids select 'p_main', id from x$$);
select pg_temp.ok('the group posts are saved with their group', $$(select count(*) from public.posts where id in (pg_temp.id('p_pub'), pg_temp.id('p_priv')) and group_id is not null) = 2$$);
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.no('an outsider cannot post in a public group they did not join', $$insert into public.posts (user_id, body, group_id) values (pg_temp.u(3), 'GP x', pg_temp.id('pub'))$$, '42501');
select pg_temp.no('an outsider cannot post in a private group', $$insert into public.posts (user_id, body, group_id) values (pg_temp.u(3), 'GP x', pg_temp.id('priv'))$$, '42501');
select pg_temp.no('an outsider cannot post in an unlisted group', $$insert into public.posts (user_id, body, group_id) values (pg_temp.u(3), 'GP x', pg_temp.id('unl'))$$, '42501');
select pg_temp.no('nobody posts in another person''s name inside a group', $$insert into public.posts (user_id, body, group_id) values (pg_temp.u(2), 'GP x', pg_temp.id('pub'))$$, '42501');
select pg_temp.ok('an outsider reads the public group''s post', $$exists (select 1 from public.posts where id = pg_temp.id('p_pub'))$$);
select pg_temp.ok('an outsider never reads the private group''s post', $$not exists (select 1 from public.posts where id = pg_temp.id('p_priv'))
  and not exists (select 1 from public.posts where body = 'GP private group post')$$);
select pg_temp.ok('the main feed (group_id is null) holds no group post', $$(select count(*) from public.posts where group_id is null and body like 'GP %') = 1
  and (select body from public.posts where group_id is null and body like 'GP %') = 'GP main feed post'$$);
select pg_temp.ok('the group feed of the public group: its post only', $$(select array_agg(id order by created_at desc, id desc) from public.posts where group_id = pg_temp.id('pub')) = array[pg_temp.id('p_pub')]$$);
select pg_temp.ok('the group feed of the private group is empty for an outsider', $$(select count(*) from public.posts where group_id = pg_temp.id('priv')) = 0$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.ok('the private group''s admin reads its post', $$exists (select 1 from public.posts where id = pg_temp.id('p_priv'))$$);
select pg_temp.as_user(pg_temp.u(6));
select pg_temp.ok('a Drugbox moderator reads a private group''s post (moderation)', $$exists (select 1 from public.posts where id = pg_temp.id('p_priv'))$$);
select pg_temp.as_anon();
select pg_temp.ok('anon reads no post at all (F-26 kept)', $$(select count(*) from public.posts) = 0$$);
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.no('a post cannot move into another group', $$update public.posts set group_id = pg_temp.id('pub') where id = pg_temp.id('p_priv')$$, '42501');
select pg_temp.no('a group post cannot move out to the main feed', $$update public.posts set group_id = null where id = pg_temp.id('p_priv')$$, '42501');
select pg_temp.no('a main feed post cannot move into a group', $$update public.posts set group_id = pg_temp.id('priv') where id = pg_temp.id('p_main')$$, '42501');
select pg_temp.step('the author edits the group post''s text', $$update public.posts set body = 'GP private group post (edited)' where id = pg_temp.id('p_priv')$$);
select pg_temp.ok('…which is saved, still in its group', $$(select body || '|' || group_id from public.posts where id = pg_temp.id('p_priv')) = 'GP private group post (edited)|' || pg_temp.id('priv')$$);

-- ══ comments, likes, files, saves, views, shares follow the post ═══════════════════════════════
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.step('the member comments, likes, attaches a file and saves the private post', $$
  with c as (insert into public.comments (post_id, user_id, body) values (pg_temp.id('p_priv'), pg_temp.u(2), 'GP inside comment') returning id) insert into ids select 'c_priv', id from c;
  insert into public.reactions (post_id, user_id) values (pg_temp.id('p_priv'), pg_temp.u(2));
  insert into public.post_media (post_id, url, type) values (pg_temp.id('p_priv'), 'https://x.test/posts/gp/1.png', 'image');
  insert into public.saved_posts (user_id, post_id) values (pg_temp.u(2), pg_temp.id('p_priv'))$$);
select pg_temp.as_user(pg_temp.u(5));
select pg_temp.step('another member comments and likes', $$insert into public.comments (post_id, user_id, body) values (pg_temp.id('p_priv'), pg_temp.u(5), 'GP admin comment');
  insert into public.reactions (post_id, user_id) values (pg_temp.id('p_priv'), pg_temp.u(5))$$);
select pg_temp.ok('the member sees both comments, both likes, the file', $$(select count(*) from public.comments where post_id = pg_temp.id('p_priv')) = 2
  and (select count(*) from public.reactions where post_id = pg_temp.id('p_priv')) = 2 and (select count(*) from public.post_media where post_id = pg_temp.id('p_priv')) = 1$$);
select pg_temp.ok('counters and the author''s notifications work as for any post', $$(select like_count || '|' || comment_count from public.posts where id = pg_temp.id('p_priv')) = '2|2'$$);
select pg_temp.as_server();
select pg_temp.ok('…the author is notified of the comment and the like', $$(select count(*) from public.notifications where user_id = pg_temp.u(2) and post_id = pg_temp.id('p_priv') and type in ('comment', 'like')) = 2$$);
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.ok('an outsider reads none of the private post''s comments, likes or files', $$(select count(*) from public.comments where post_id = pg_temp.id('p_priv')) = 0
  and (select count(*) from public.reactions where post_id = pg_temp.id('p_priv')) = 0 and (select count(*) from public.post_media where post_id = pg_temp.id('p_priv')) = 0
  and not exists (select 1 from public.comments where body like 'GP inside%')$$);
select pg_temp.no('an outsider cannot comment on the private post', $$insert into public.comments (post_id, user_id, body) values (pg_temp.id('p_priv'), pg_temp.u(3), 'GP x')$$, '42501');
select pg_temp.no('an outsider cannot like the private post', $$insert into public.reactions (post_id, user_id) values (pg_temp.id('p_priv'), pg_temp.u(3))$$, '42501');
select pg_temp.no('an outsider cannot save the private post', $$insert into public.saved_posts (user_id, post_id) values (pg_temp.u(3), pg_temp.id('p_priv'))$$, '42501');
select pg_temp.no('an outsider cannot attach a file to it', $$insert into public.post_media (post_id, url, type) values (pg_temp.id('p_priv'), 'https://x.test/a.png', 'image')$$, '42501');
select pg_temp.step('an outsider comments on and likes the PUBLIC group''s post', $$insert into public.comments (post_id, user_id, body) values (pg_temp.id('p_pub'), pg_temp.u(3), 'GP outsider comment');
  insert into public.reactions (post_id, user_id) values (pg_temp.id('p_pub'), pg_temp.u(3))$$);
select pg_temp.ok('…which is saved (a public group is open to every signed-in member)', $$(select comment_count || '|' || like_count from public.posts where id = pg_temp.id('p_pub')) = '1|1'$$);
select pg_temp.step('an outsider "views" and "shares" the private post', $$select public.increment_post_views(array[pg_temp.id('p_priv'), pg_temp.id('p_main')])$$);
select pg_temp.ok('…sharing it returns nothing', $$public.increment_post_share(pg_temp.id('p_priv')) is null$$);
select pg_temp.as_server();
select pg_temp.ok('…and only the visible post was counted', $$(select view_count || '|' || share_count from public.posts where id = pg_temp.id('p_priv')) = '0|0'
  and (select view_count from public.posts where id = pg_temp.id('p_main')) = 1$$);
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.ok('a member''s share of the private post counts', $$public.increment_post_share(pg_temp.id('p_priv')) = 1$$);

-- ══ leaving: the posts stay, the person stops seeing them (except their own) ═══════════════════
select pg_temp.as_server();
insert into public.posts (user_id, body, group_id) values (pg_temp.u(1), 'GP admin post', pg_temp.id('priv'));
insert into ids select 'p_admin', id from public.posts where body = 'GP admin post';
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.step('the member leaves the private group', $$delete from public.group_members where group_id = pg_temp.id('priv') and user_id = pg_temp.u(2)$$);
select pg_temp.ok('…no longer reads the others'' posts there', $$not exists (select 1 from public.posts where id = pg_temp.id('p_admin'))$$);
select pg_temp.ok('…still reads (and can delete) their own', $$exists (select 1 from public.posts where id = pg_temp.id('p_priv'))$$);
select pg_temp.no('…and cannot post there any more', $$insert into public.posts (user_id, body, group_id) values (pg_temp.u(2), 'GP after leaving', pg_temp.id('priv'))$$, '42501');
select pg_temp.as_server();
insert into public.group_members (group_id, user_id, role) values (pg_temp.id('priv'), pg_temp.u(2), 'member');

-- ══ admins moderate: remove, pin ═════════════════════════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.step('a plain member tries to delete the admin''s post', $$delete from public.posts where id = pg_temp.id('p_admin')$$);
select pg_temp.ok('…which stays', $$exists (select 1 from public.posts where id = pg_temp.id('p_admin'))$$);
select pg_temp.step('a plain member tries to delete another member''s comment', $$delete from public.comments where body = 'GP admin comment'$$);
select pg_temp.ok('…which stays', $$exists (select 1 from public.comments where body = 'GP admin comment')$$);
select pg_temp.no('a plain member cannot pin', $$select public.group_pin_post(pg_temp.id('priv'), pg_temp.id('p_admin'))$$, '42501');
select pg_temp.as_user(pg_temp.u(5));
select pg_temp.step('the second admin pins a post of the group', $$select public.group_pin_post(pg_temp.id('priv'), pg_temp.id('p_admin'))$$);
select pg_temp.ok('…which every member reads as the pinned post', $$(select pinned_post_id from public.groups where id = pg_temp.id('priv')) = pg_temp.id('p_admin')$$);
select pg_temp.no('a post of another group cannot be pinned (function)', $$select public.group_pin_post(pg_temp.id('priv'), pg_temp.id('p_pub'))$$, '42501');
select pg_temp.no('…nor a main feed post', $$select public.group_pin_post(pg_temp.id('priv'), pg_temp.id('p_main'))$$, '42501');
select pg_temp.no('…nor by writing the column directly', $$update public.groups set pinned_post_id = pg_temp.id('p_pub') where id = pg_temp.id('priv')$$, '42501');
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.no('an outsider cannot pin in a public group', $$select public.group_pin_post(pg_temp.id('pub'), pg_temp.id('p_pub'))$$, '42501');
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('the creator pins the public group''s post by writing the column', $$update public.groups set pinned_post_id = pg_temp.id('p_pub') where id = pg_temp.id('pub')$$);
select pg_temp.ok('…which is saved', $$(select pinned_post_id from public.groups where id = pg_temp.id('pub')) = pg_temp.id('p_pub')$$);
select pg_temp.step('the admin removes a member''s comment in the group', $$delete from public.comments where id = pg_temp.id('c_priv')$$);
select pg_temp.ok('…which is gone; the count follows', $$not exists (select 1 from public.comments where id = pg_temp.id('c_priv')) and (select comment_count from public.posts where id = pg_temp.id('p_priv')) = 1$$);
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.step('the outsider comments on the main feed post', $$insert into public.comments (post_id, user_id, body) values (pg_temp.id('p_main'), pg_temp.u(3), 'GP outsider main comment')$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('a group admin tries to delete a comment outside their groups', $$delete from public.comments where body = 'GP outsider main comment'$$);
select pg_temp.ok('…which stays (group admins moderate their own group only)', $$exists (select 1 from public.comments where body = 'GP outsider main comment')$$);
select pg_temp.step('…or a main feed post', $$delete from public.posts where id = pg_temp.id('p_main')$$);
select pg_temp.ok('…which stays', $$exists (select 1 from public.posts where id = pg_temp.id('p_main'))$$);
select pg_temp.step('the admin removes the pinned post', $$delete from public.posts where id = pg_temp.id('p_admin')$$);
select pg_temp.ok('…the post is gone and the group is unpinned', $$not exists (select 1 from public.posts where id = pg_temp.id('p_admin'))
  and (select pinned_post_id from public.groups where id = pg_temp.id('priv')) is null$$);

-- ══ join requests ════════════════════════════════════════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(4));
select pg_temp.ok('asking to join a public group joins it at once', $$public.group_request_join(pg_temp.id('pub')) = 'member'$$);
select pg_temp.ok('…as a member', $$exists (select 1 from public.group_members where group_id = pg_temp.id('pub') and user_id = pg_temp.u(4) and role = 'member')$$);
select pg_temp.ok('asking to join the listed private group → pending', $$public.group_request_join(pg_temp.id('priv'), '  I work in QA at a Cairo plant  ') = 'pending'$$);
select pg_temp.ok('asking again changes nothing', $$public.group_request_join(pg_temp.id('priv')) = 'pending'$$);
select pg_temp.ok('the person reads their own request (message trimmed)', $$(select status || '|' || message from public.group_join_requests where group_id = pg_temp.id('priv') and user_id = pg_temp.u(4)) = 'pending|I work in QA at a Cairo plant'$$);
select pg_temp.ok('…but is not a member yet and reads no post', $$not public.is_group_member(pg_temp.id('priv')) and not exists (select 1 from public.posts where group_id = pg_temp.id('priv'))$$);
select pg_temp.no('the request cannot be written directly (status never comes from the browser)', $$insert into public.group_join_requests (group_id, user_id, status) values (pg_temp.id('unl'), pg_temp.u(4), 'approved')$$, '42501');
select pg_temp.no('…nor approved by its author', $$update public.group_join_requests set status = 'approved' where user_id = pg_temp.u(4)$$, '42501');
select pg_temp.no('an unlisted private group cannot be asked (it looks like no group)', $$select public.group_request_join(pg_temp.id('unl'))$$, 'P0002');
select pg_temp.no('…nor a group that does not exist', $$select public.group_request_join(-1)$$, 'P0002');
select pg_temp.as_server();
select pg_temp.ok('both admins of the group are notified once, naming the group', $$pg_temp.notifs(pg_temp.u(1), 'group_join_request', pg_temp.id('priv')) = 1
  and pg_temp.notifs(pg_temp.u(5), 'group_join_request', pg_temp.id('priv')) = 1 and pg_temp.notifs(pg_temp.u(2), 'group_join_request', pg_temp.id('priv')) = 0
  and (select message || '|' || from_user from public.notifications where user_id = pg_temp.u(1) and type = 'group_join_request') = 'asked to join the private group "GP Private"|' || pg_temp.u(4)$$);
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.ok('an outsider reads nobody''s request', $$(select count(*) from public.group_join_requests) = 0$$);
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.ok('a plain member does not read the requests', $$(select count(*) from public.group_join_requests where group_id = pg_temp.id('priv')) = 0$$);
select pg_temp.no('…nor answer them', $$select public.group_decide_request(pg_temp.id('priv'), pg_temp.u(4), true)$$, '42501');
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.ok('the admin reads the pending request with its message', $$(select message from public.group_join_requests where group_id = pg_temp.id('priv') and status = 'pending' and user_id = pg_temp.u(4)) = 'I work in QA at a Cairo plant'$$);
select pg_temp.ok('the admin approves → approved', $$public.group_decide_request(pg_temp.id('priv'), pg_temp.u(4), true) = 'approved'$$);
select pg_temp.ok('…the person is a member; member count 4', $$exists (select 1 from public.group_members where group_id = pg_temp.id('priv') and user_id = pg_temp.u(4) and role = 'member')
  and (select member_count from public.groups where id = pg_temp.id('priv')) = 4$$);
select pg_temp.no('…answering again finds nothing pending', $$select public.group_decide_request(pg_temp.id('priv'), pg_temp.u(4), false)$$, 'P0002');
select pg_temp.as_server();
select pg_temp.ok('…the admins'' "asked to join" notices are gone; the person is told', $$pg_temp.notifs(pg_temp.u(1), 'group_join_request', pg_temp.id('priv')) = 0
  and pg_temp.notifs(pg_temp.u(5), 'group_join_request', pg_temp.id('priv')) = 0
  and (select message || '|' || from_user from public.notifications where user_id = pg_temp.u(4) and type = 'group_join_approved' and group_id = pg_temp.id('priv')) = 'approved your request to join "GP Private"|' || pg_temp.u(1)$$);
select pg_temp.as_user(pg_temp.u(4));
select pg_temp.ok('the new member reads the group''s posts and posts there', $$exists (select 1 from public.posts where id = pg_temp.id('p_priv'))$$);
select pg_temp.step('the new member posts', $$insert into public.posts (user_id, body, group_id) values (pg_temp.u(4), 'GP newcomer post', pg_temp.id('priv'))$$);
select pg_temp.ok('asking once a member says member', $$public.group_request_join(pg_temp.id('priv')) = 'member'$$);

-- declined, then asked again after 30 days
select pg_temp.as_user(pg_temp.u(8));
select pg_temp.ok('u8 asks to join', $$public.group_request_join(pg_temp.id('priv')) = 'pending'$$);
select pg_temp.as_user(pg_temp.u(5));
select pg_temp.ok('the second admin declines → rejected', $$public.group_decide_request(pg_temp.id('priv'), pg_temp.u(8), false) = 'rejected'$$);
select pg_temp.as_server();
select pg_temp.ok('…no member row, the notices are gone, nobody is told of the refusal', $$not exists (select 1 from public.group_members where group_id = pg_temp.id('priv') and user_id = pg_temp.u(8))
  and pg_temp.notifs(pg_temp.u(1), 'group_join_request', pg_temp.id('priv')) = 0 and not exists (select 1 from public.notifications where user_id = pg_temp.u(8))$$);
select pg_temp.as_user(pg_temp.u(8));
select pg_temp.ok('the person sees the answer', $$(select status from public.group_join_requests where group_id = pg_temp.id('priv')) = 'rejected'$$);
select pg_temp.no('asking again within 30 days is refused', $$select public.group_request_join(pg_temp.id('priv'))$$, '42501');
select pg_temp.as_server();
update public.group_join_requests set decided_at = now() - interval '31 days' where user_id = pg_temp.u(8);
select pg_temp.as_user(pg_temp.u(8));
select pg_temp.ok('…after 30 days the person can ask again', $$public.group_request_join(pg_temp.id('priv'), 'second try') = 'pending'$$);
select pg_temp.ok('…the request is pending again with the new message', $$(select status || '|' || message || '|' || (decided_at is null) from public.group_join_requests where group_id = pg_temp.id('priv')) = 'pending|second try|true'$$);
select pg_temp.as_server();
select pg_temp.ok('…both admins notified again', $$pg_temp.notifs(pg_temp.u(1), 'group_join_request', pg_temp.id('priv')) = 1 and pg_temp.notifs(pg_temp.u(5), 'group_join_request', pg_temp.id('priv')) = 1$$);
select pg_temp.as_user(pg_temp.u(8));
select pg_temp.step('the person withdraws the request', $$select public.group_cancel_request(pg_temp.id('priv'))$$);
select pg_temp.ok('…the request and the admins'' notices are gone', $$not exists (select 1 from public.group_join_requests where group_id = pg_temp.id('priv') and user_id = pg_temp.u(8))$$);
select pg_temp.as_server();
select pg_temp.ok('…(notices counted by the server)', $$pg_temp.notifs(pg_temp.u(1), 'group_join_request', pg_temp.id('priv')) = 0 and pg_temp.notifs(pg_temp.u(5), 'group_join_request', pg_temp.id('priv')) = 0$$);

-- an invitation while a request waits: joining by the invitation answers the request
select pg_temp.as_user(pg_temp.u(7));
select pg_temp.ok('u7 asks to join', $$public.group_request_join(pg_temp.id('priv')) = 'pending'$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('the admin invites u7 instead', $$insert into public.group_invites (group_id, user_id, invited_by) values (pg_temp.id('priv'), pg_temp.u(7), pg_temp.u(1))$$);
select pg_temp.as_user(pg_temp.u(7));
select pg_temp.ok('u7 asking again with the invitation joins at once', $$public.group_request_join(pg_temp.id('priv')) = 'member'$$);
select pg_temp.ok('…the request is closed as approved', $$(select status from public.group_join_requests where group_id = pg_temp.id('priv') and user_id = pg_temp.u(7)) = 'approved'$$);
select pg_temp.as_server();
select pg_temp.ok('…and the admins'' notices are gone', $$pg_temp.notifs(pg_temp.u(1), 'group_join_request', pg_temp.id('priv')) = 0$$);

-- flood limit: 20 waiting requests per person
select pg_temp.as_server();
insert into public.groups (name, type, created_by, listed) select 'GP Flood ' || g, 'private', pg_temp.u(1), true from generate_series(1, 21) g;
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.step('u3 asks 20 groups', $$select public.group_request_join(id) from public.groups where name like 'GP Flood %' and name <> 'GP Flood 21'$$);
select pg_temp.ok('…20 waiting', $$(select count(*) from public.group_join_requests where status = 'pending') = 20$$);
select pg_temp.no('the 21st waits for answers first', $$select public.group_request_join((select id from public.groups where name = 'GP Flood 21'))$$, '42501');

-- ══ reports to the group's admins (Manage → Reports) ═════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(4));
select pg_temp.step('a member reports a post in the group (sends status dismissed, another group)', $$insert into public.group_post_reports (post_id, reporter, group_id, reason, status)
  values (pg_temp.id('p_priv'), pg_temp.u(4), pg_temp.id('pub'), 'Off topic advertising', 'dismissed')$$);
select pg_temp.ok('…the report is open and filed under the post''s own group', $$(select status || '|' || group_id from public.group_post_reports where post_id = pg_temp.id('p_priv')) = 'open|' || pg_temp.id('priv')$$);
select pg_temp.no('…once per post', $$insert into public.group_post_reports (post_id, reporter, reason) values (pg_temp.id('p_priv'), pg_temp.u(4), 'again')$$, '23505');
select pg_temp.no('a main feed post is not reported to group admins', $$insert into public.group_post_reports (post_id, reporter, reason) values (pg_temp.id('p_main'), pg_temp.u(4), 'x')$$, '22023');
select pg_temp.no('nobody reports in another person''s name', $$insert into public.group_post_reports (post_id, reporter, reason) values (pg_temp.id('p_pub'), pg_temp.u(2), 'x')$$, '42501');
select pg_temp.no('the reporter cannot dismiss it', $$update public.group_post_reports set reason = 'changed' where post_id = pg_temp.id('p_priv')$$, '42501');
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.no('an outsider cannot report a post they cannot read', $$insert into public.group_post_reports (post_id, reporter, reason) values (pg_temp.id('p_priv'), pg_temp.u(3), 'x')$$, '42501');
select pg_temp.ok('an outsider reads no report', $$(select count(*) from public.group_post_reports) = 0$$);
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.ok('a plain member reads no other member''s report', $$(select count(*) from public.group_post_reports) = 0$$);
select pg_temp.step('a plain member tries to dismiss it', $$update public.group_post_reports set status = 'dismissed' where post_id = pg_temp.id('p_priv')$$);
select pg_temp.as_user(pg_temp.u(5));
select pg_temp.ok('the group''s admin reads the open report (still open after the member''s try)', $$(select status || '|' || reason from public.group_post_reports where group_id = pg_temp.id('priv')) = 'open|Off topic advertising'$$);
select pg_temp.step('the admin dismisses it', $$update public.group_post_reports set status = 'dismissed' where post_id = pg_temp.id('p_priv')$$);
select pg_temp.ok('…dismissed', $$(select status from public.group_post_reports where post_id = pg_temp.id('p_priv')) = 'dismissed'$$);
select pg_temp.no('…the admin cannot rewrite the reason', $$update public.group_post_reports set reason = 'x' where post_id = pg_temp.id('p_priv')$$, '42501');
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('"Remove post": the admin deletes the reported post', $$delete from public.posts where id = pg_temp.id('p_priv')$$);
select pg_temp.ok('…the post, its comments, likes, files, saves and reports are gone', $$not exists (select 1 from public.posts where id = pg_temp.id('p_priv'))$$);
select pg_temp.as_server();
select pg_temp.ok('…(checked by the server)', $$not exists (select 1 from public.comments where post_id = pg_temp.id('p_priv')) and not exists (select 1 from public.reactions where post_id = pg_temp.id('p_priv'))
  and not exists (select 1 from public.post_media where post_id = pg_temp.id('p_priv')) and not exists (select 1 from public.saved_posts where post_id = pg_temp.id('p_priv'))
  and not exists (select 1 from public.group_post_reports where post_id = pg_temp.id('p_priv'))$$);

-- ══ activity for the cards ═══════════════════════════════════════════════════════════════════
select pg_temp.as_user(pg_temp.u(3));
select pg_temp.ok('activity: an outsider gets the public and the listed group, not the unlisted one', $$(select array_agg(group_id order by group_id) from public.group_activity(array[pg_temp.id('pub'), pg_temp.id('priv'), pg_temp.id('unl')]))
  = array[least(pg_temp.id('pub'), pg_temp.id('priv')), greatest(pg_temp.id('pub'), pg_temp.id('priv'))]$$);
select pg_temp.ok('activity: posts today / this week / last post', $$(select posts_today || '|' || posts_week || '|' || (last_post_at is not null) from public.group_activity(array[pg_temp.id('priv')])) = '1|1|true'
  and (select posts_week from public.group_activity(array[pg_temp.id('pub')])) = 1$$);
select pg_temp.as_anon();
select pg_temp.no('anon cannot call the group functions', $$select public.group_activity(array[1::bigint])$$, '42501');
select pg_temp.no('…nor ask to join', $$select public.group_request_join(1)$$, '42501');
select pg_temp.ok('anon reads the new tables without an error, and nothing in them', $$(select count(*) from public.group_join_requests) = 0 and (select count(*) from public.group_post_reports) = 0$$);

-- ══ deleting a group takes its posts (and its pin) with it ═══════════════════════════════════
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.step('the creator deletes the pinned public group', $$delete from public.groups where id = pg_temp.id('pub')$$);
select pg_temp.as_server();
select pg_temp.ok('…the group and its posts are gone', $$not exists (select 1 from public.groups where id = pg_temp.id('pub')) and not exists (select 1 from public.posts where id = pg_temp.id('p_pub'))$$);

-- ══ schema and privileges ════════════════════════════════════════════════════════════════════
select pg_temp.as_server();
select pg_temp.ok('posts.group_id references groups, deleted with the group', $$exists (select 1 from pg_constraint where conrelid = 'public.posts'::regclass and contype = 'f'
  and confrelid = 'public.groups'::regclass and confdeltype = 'c')$$);
select pg_temp.ok('the group feed index (group_id, created_at desc, id desc) exists', $$exists (select 1 from pg_indexes where indexname = 'idx_posts_group_feed' and indexdef like '%(group_id, created_at DESC, id DESC)%')$$);
select pg_temp.ok('the RPCs are for signed-in members only', $$not has_function_privilege('anon', 'public.group_request_join(bigint,text)', 'execute')
  and not has_function_privilege('anon', 'public.group_decide_request(bigint,uuid,boolean)', 'execute') and not has_function_privilege('anon', 'public.group_cancel_request(bigint)', 'execute')
  and not has_function_privilege('anon', 'public.group_pin_post(bigint,bigint)', 'execute') and has_function_privilege('authenticated', 'public.group_request_join(bigint,text)', 'execute')
  and has_function_privilege('authenticated', 'public.group_decide_request(bigint,uuid,boolean)', 'execute')$$);
select pg_temp.ok('the trigger functions are not callable from the API', $$not has_function_privilege('authenticated', 'public.groups_before_write()', 'execute')
  and not has_function_privilege('authenticated', 'public.group_members_close_request()', 'execute') and not has_function_privilege('authenticated', 'public.group_post_reports_before_write()', 'execute')$$);
select pg_temp.ok('join requests: members only read them; nobody writes them directly', $$has_table_privilege('authenticated', 'public.group_join_requests', 'select')
  and not has_table_privilege('authenticated', 'public.group_join_requests', 'insert') and not has_table_privilege('authenticated', 'public.group_join_requests', 'update')
  and not has_table_privilege('authenticated', 'public.group_join_requests', 'delete') and not has_table_privilege('anon', 'public.group_join_requests', 'insert')$$);
select pg_temp.ok('reports: only the status column can be updated', $$has_column_privilege('authenticated', 'public.group_post_reports', 'status', 'update')
  and not has_column_privilege('authenticated', 'public.group_post_reports', 'reason', 'update') and not has_column_privilege('authenticated', 'public.group_post_reports', 'group_id', 'update')$$);

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
