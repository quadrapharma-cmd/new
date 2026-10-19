-- Social (0041–0045): edits are marked by the database; reposts, replies, comment likes and mentions are each member's own and
-- refused across a block; tags are the database's; profile pictures only from the member's own folder; endorsements of listed skills,
-- never one's own; who-viewed respects the viewer's choice; search_all is for members only and leaves out blocked people; saved
-- searches are private (20 each); member reports, the reported-members queue and suspensions (refused writes, reporters told);
-- message notices once per unread conversation; the e-mail outbox is the server's alone.
-- Run on a fresh database (stub + migrations): psql -f supabase/tests/social.rls.sql — a negative check passes only with the expected SQLSTATE,
-- and psql exits non-zero when anything failed.
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

grant all on r to service_role; grant all on r_n_seq to service_role; grant all on ids to service_role;
create function pg_temp.as_service() returns void language plpgsql as $$ begin
  perform set_config('request.jwt.claim.sub', '', true); perform set_config('request.jwt.claims', '{"role":"service_role"}', true); perform set_config('role', 'service_role', true); end $$;

insert into auth.users (id, email, encrypted_password) values
  ('aaaa0041-0000-0000-0000-000000000001','s41-a@x', crypt('Pass-A-2026', gen_salt('bf'))), ('aaaa0041-0000-0000-0000-000000000002','s41-b@x', crypt('Pass-B-2026', gen_salt('bf'))), ('aaaa0041-0000-0000-0000-000000000003','s41-c@x', crypt('Pass-C-2026', gen_salt('bf'))),
  ('aaaa0041-0000-0000-0000-000000000004','s41-m@x', crypt('Pass-M-2026', gen_salt('bf'))), ('aaaa0041-0000-0000-0000-000000000005','s41-d@x', crypt('Pass-D-2026', gen_salt('bf'))) on conflict do nothing;
insert into public.profiles (id, name) values ('aaaa0041-0000-0000-0000-000000000001','S41 Alice'),('aaaa0041-0000-0000-0000-000000000002','S41 Bob'),('aaaa0041-0000-0000-0000-000000000003','S41 Cara'),('aaaa0041-0000-0000-0000-000000000004','S41 Mod'),('aaaa0041-0000-0000-0000-000000000005','S41 Dina') on conflict (id) do update set name = excluded.name;
update public.profiles set role = 'admin' where id = 'aaaa0041-0000-0000-0000-000000000004';
update public.profiles set skills = array['GMP','Validation'] where id = 'aaaa0041-0000-0000-0000-000000000001';
insert into public.posts (user_id, body) values ('aaaa0041-0000-0000-0000-000000000001', 'S41 alice post #Stability #دواء'), ('aaaa0041-0000-0000-0000-000000000002', 'S41 bob post');
insert into ids select 'pa', id::text from public.posts where body like 'S41 alice post%';
insert into ids select 'pb', id::text from public.posts where body = 'S41 bob post';
insert into public.comments (post_id, user_id, body) values (pg_temp.id('pb'), 'aaaa0041-0000-0000-0000-000000000001', 'S41 alice comment');
insert into ids select 'ca', id::text from public.comments where body = 'S41 alice comment';
insert into public.comments (post_id, user_id, body) values (pg_temp.id('pb'), 'aaaa0041-0000-0000-0000-000000000002', 'S41 bob own comment');
insert into ids select 'cb', id::text from public.comments where body = 'S41 bob own comment';
insert into public.posts (user_id, body) values ('aaaa0041-0000-0000-0000-000000000003', 'S41 cara post');
insert into ids select 'pc', id::text from public.posts where body = 'S41 cara post';
insert into public.comments (post_id, user_id, body) values (pg_temp.id('pc'), 'aaaa0041-0000-0000-0000-000000000003', 'S41 cara comment');
insert into ids select 'cc', id::text from public.comments where body = 'S41 cara comment';

-- ══ edits are marked by the database ════════════════════════════════════════════════════════
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.step('Alice edits her post', $$update public.posts set body = 'S41 alice post edited #Stability' where id = pg_temp.id('pa')$$);
select pg_temp.ok('the edit is marked', $$(select edited_at is not null from public.posts where id = pg_temp.id('pa'))$$);
select pg_temp.step('Alice tries to clear the mark', $$update public.posts set edited_at = null where id = pg_temp.id('pa')$$);
select pg_temp.ok('the mark stays', $$(select edited_at is not null from public.posts where id = pg_temp.id('pa'))$$);
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000002');
select pg_temp.step('Bob tries to edit Alice''s post', $$update public.posts set body = 'hacked' where id = pg_temp.id('pa')$$);
select pg_temp.ok('Alice''s post is unchanged', $$(select body like 'S41 alice post edited%' from public.posts where id = pg_temp.id('pa'))$$);

-- ══ tags are the database's ════════════════════════════════════════════════════════════════
select pg_temp.as_server();
select pg_temp.ok('the edited post keeps its tag', $$(select count(*) = 1 from public.post_tags where post_id = pg_temp.id('pa') and tag = 'stability')$$);
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.no('a member cannot write tags', $$insert into public.post_tags (post_id, tag) values (pg_temp.id('pb'), 'fake')$$, '42501');
select pg_temp.step('an Arabic tag', $$update public.posts set body = 'S41 alice post #دواء' where id = pg_temp.id('pa')$$);
select pg_temp.ok('Arabic tags are kept', $$(select count(*) = 1 from public.post_tags where post_id = pg_temp.id('pa') and tag = 'دواء')$$);

-- ══ reposts ═══════════════════════════════════════════════════════════════════════════════
select pg_temp.step('Alice reposts Bob''s post', $$insert into public.reposts (user_id, post_id, note) values ('aaaa0041-0000-0000-0000-000000000001', pg_temp.id('pb'), 'worth reading')$$);
select pg_temp.no('Alice cannot repost as Bob', $$insert into public.reposts (user_id, post_id) values ('aaaa0041-0000-0000-0000-000000000002', pg_temp.id('pa'))$$, '42501');
select pg_temp.no('the same repost twice is refused', $$insert into public.reposts (user_id, post_id) values ('aaaa0041-0000-0000-0000-000000000001', pg_temp.id('pb'))$$, '23505');
select pg_temp.as_server();
select pg_temp.ok('Bob''s post counts one share', $$(select share_count = 1 from public.posts where id = pg_temp.id('pb'))$$);
select pg_temp.ok('Bob is told once', $$(select count(*) = 1 from public.notifications where user_id = 'aaaa0041-0000-0000-0000-000000000002' and from_user = 'aaaa0041-0000-0000-0000-000000000001' and type = 'repost')$$);

-- ══ replies ═══════════════════════════════════════════════════════════════════════════════
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000003');
select pg_temp.step('Cara replies to Alice''s comment', $$insert into public.comments (post_id, user_id, body, parent_id) values (pg_temp.id('pb'), 'aaaa0041-0000-0000-0000-000000000003', 'S41 cara reply', pg_temp.id('ca'))$$);
select pg_temp.no('a reply to a comment of another post is refused', $$insert into public.comments (post_id, user_id, body, parent_id) values (pg_temp.id('pa'), 'aaaa0041-0000-0000-0000-000000000003', 'x', pg_temp.id('ca'))$$, '22023');
select pg_temp.step('Cara replies to Bob''s own comment', $$insert into public.comments (post_id, user_id, body, parent_id) values (pg_temp.id('pb'), 'aaaa0041-0000-0000-0000-000000000003', 'S41 cara reply to bob', pg_temp.id('cb'))$$);
select pg_temp.as_server();
insert into ids select 'cr', id::text from public.comments where body = 'S41 cara reply';
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.step('Alice answers the reply (a reply to a reply)', $$insert into public.comments (post_id, user_id, body, parent_id) values (pg_temp.id('pb'), 'aaaa0041-0000-0000-0000-000000000001', 'S41 alice re-reply', pg_temp.id('cr'))$$);
select pg_temp.as_server();
select pg_temp.ok('a reply to a reply joins the thread (one level)', $$(select parent_id = pg_temp.id('ca') from public.comments where body = 'S41 alice re-reply')$$);
select pg_temp.ok('Alice is told of Cara''s reply', $$(select count(*) = 1 from public.notifications where user_id = 'aaaa0041-0000-0000-0000-000000000001' and from_user = 'aaaa0041-0000-0000-0000-000000000003' and type = 'reply')$$);
select pg_temp.ok('Bob is told once of the reply to his own comment (no extra "comment" notice)', $$(select count(*) filter (where type = 'reply') = 1 and count(*) filter (where type = 'comment' and comment_id = (select id from public.comments where body = 'S41 cara reply to bob')) = 0 from public.notifications where user_id = 'aaaa0041-0000-0000-0000-000000000002' and from_user = 'aaaa0041-0000-0000-0000-000000000003')$$);

-- ══ comment likes ═════════════════════════════════════════════════════════════════════════
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000003');
select pg_temp.step('Cara likes Alice''s comment', $$insert into public.comment_reactions (comment_id, user_id) values (pg_temp.id('ca'), 'aaaa0041-0000-0000-0000-000000000003')$$);
select pg_temp.no('Cara cannot like as Alice', $$insert into public.comment_reactions (comment_id, user_id) values (pg_temp.id('ca'), 'aaaa0041-0000-0000-0000-000000000001')$$, '42501');
select pg_temp.no('the same like twice is refused', $$insert into public.comment_reactions (comment_id, user_id) values (pg_temp.id('ca'), 'aaaa0041-0000-0000-0000-000000000003')$$, '23505');
select pg_temp.no('a member cannot set a like count', $$update public.comments set like_count = 99 where id = pg_temp.id('cc')$$, '42501');
select pg_temp.as_server();
select pg_temp.ok('the comment counts one like', $$(select like_count = 1 from public.comments where id = pg_temp.id('ca'))$$);
select pg_temp.ok('Alice is told once that Cara liked her comment (0049)', $$(select count(*) = 1 from public.notifications where user_id = 'aaaa0041-0000-0000-0000-000000000001' and from_user = 'aaaa0041-0000-0000-0000-000000000003' and type = 'comment_like' and comment_id = pg_temp.id('ca'))$$);

-- ══ mentions ══════════════════════════════════════════════════════════════════════════════
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.step('Alice mentions Cara in her post', $$insert into public.post_mentions (post_id, user_id) values (pg_temp.id('pa'), 'aaaa0041-0000-0000-0000-000000000003')$$);
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000002');
select pg_temp.no('Bob cannot add mentions to Alice''s post', $$insert into public.post_mentions (post_id, user_id) values (pg_temp.id('pa'), 'aaaa0041-0000-0000-0000-000000000005')$$, '42501');
select pg_temp.as_server();
select pg_temp.ok('Cara is told she was mentioned', $$(select count(*) = 1 from public.notifications where user_id = 'aaaa0041-0000-0000-0000-000000000003' and from_user = 'aaaa0041-0000-0000-0000-000000000001' and type = 'mention')$$);

-- ══ blocks cover more than messages ═══════════════════════════════════════════════════════
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000003');
select pg_temp.step('Cara blocks Dina', $$insert into public.user_blocks (blocker, blocked) values ('aaaa0041-0000-0000-0000-000000000003', 'aaaa0041-0000-0000-0000-000000000005')$$);
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000005');
select pg_temp.no('Dina cannot send Cara a connection request', $$insert into public.connections (requester, addressee, status) values ('aaaa0041-0000-0000-0000-000000000005', 'aaaa0041-0000-0000-0000-000000000003', 'pending')$$, '42501');
select pg_temp.no('Dina cannot follow Cara', $$insert into public.person_followers (person_id, user_id) values ('aaaa0041-0000-0000-0000-000000000003', 'aaaa0041-0000-0000-0000-000000000005')$$, '42501');
select pg_temp.no('Dina cannot comment on Cara''s post', $$insert into public.comments (post_id, user_id, body) values (pg_temp.id('pc'), 'aaaa0041-0000-0000-0000-000000000005', 'x')$$, '42501');
select pg_temp.no('Dina cannot react to Cara''s post', $$insert into public.reactions (post_id, user_id, kind) values (pg_temp.id('pc'), 'aaaa0041-0000-0000-0000-000000000005', 'like')$$, '42501');
select pg_temp.no('Dina cannot repost Cara''s post', $$insert into public.reposts (user_id, post_id) values ('aaaa0041-0000-0000-0000-000000000005', pg_temp.id('pc'))$$, '42501');
select pg_temp.no('Dina cannot like Cara''s comment', $$insert into public.comment_reactions (comment_id, user_id) values (pg_temp.id('cc'), 'aaaa0041-0000-0000-0000-000000000005')$$, '42501');
select pg_temp.step('Dina posts', $$insert into public.posts (user_id, body) values ('aaaa0041-0000-0000-0000-000000000005', 'S41 dina post')$$);
select pg_temp.no('Dina cannot mention Cara', $$insert into public.post_mentions (post_id, user_id) select id, 'aaaa0041-0000-0000-0000-000000000003' from public.posts where body = 'S41 dina post'$$, '42501');
select pg_temp.ok('Dina''s block list names Cara', $$(select 'aaaa0041-0000-0000-0000-000000000003'::uuid = any (public.my_block_list()))$$);
select pg_temp.ok('Dina''s suggestions never include Cara', $$(select count(*) = 0 from public.suggest_people(50) s where s.id = 'aaaa0041-0000-0000-0000-000000000003')$$);
select pg_temp.ok('Dina''s search leaves Cara out', $$(select jsonb_array_length(public.search_all('S41 Cara', 6)->'people') = 0)$$);
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.ok('Alice''s search finds Cara', $$(select jsonb_array_length(public.search_all('S41 Cara', 6)->'people') = 1)$$);
select pg_temp.ok('search finds posts, people and is limited', $$(select jsonb_array_length(public.search_all('S41', 2)->'people') = 2 and jsonb_array_length(public.search_all('S41', 2)->'posts') = 2)$$);
select pg_temp.as_anon();
select pg_temp.no('a visitor cannot search members', $$select public.search_all('S41', 6)$$, '42501');

-- ══ profile pictures and lists ════════════════════════════════════════════════════════════
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.no('a photo from another site is refused', $$update public.profiles set avatar_url = 'https://evil.example/x.jpg' where id = 'aaaa0041-0000-0000-0000-000000000001'$$, '22023');
select pg_temp.no('someone else''s photo is refused', $$update public.profiles set avatar_url = 'http://localhost:54321/storage/v1/object/public/avatars/aaaa0041-0000-0000-0000-000000000002/avatar-1.jpg' where id = 'aaaa0041-0000-0000-0000-000000000001'$$, '22023');
select pg_temp.step('her own uploaded photo is kept', $$update public.profiles set avatar_url = 'http://localhost:54321/storage/v1/object/public/avatars/aaaa0041-0000-0000-0000-000000000001/avatar-1.jpg' where id = 'aaaa0041-0000-0000-0000-000000000001'$$);
select pg_temp.no('an experience list that is not a list of objects is refused', $$update public.profiles set experience = '["x"]'::jsonb where id = 'aaaa0041-0000-0000-0000-000000000001'$$, '23514');
select pg_temp.no('a skill longer than 60 characters is refused', $$update public.profiles set skills = array[repeat('x', 61)] where id = 'aaaa0041-0000-0000-0000-000000000001'$$, '23514');

-- ══ endorsements ══════════════════════════════════════════════════════════════════════════
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000002');
select pg_temp.step('Bob endorses Alice for GMP', $$insert into public.skill_endorsements (profile_id, skill, endorser) values ('aaaa0041-0000-0000-0000-000000000001', 'GMP', 'aaaa0041-0000-0000-0000-000000000002')$$);
select pg_temp.no('a skill Alice does not list cannot be endorsed', $$insert into public.skill_endorsements (profile_id, skill, endorser) values ('aaaa0041-0000-0000-0000-000000000001', 'Cooking', 'aaaa0041-0000-0000-0000-000000000002')$$, '42501');
select pg_temp.no('Bob cannot endorse as Cara', $$insert into public.skill_endorsements (profile_id, skill, endorser) values ('aaaa0041-0000-0000-0000-000000000001', 'Validation', 'aaaa0041-0000-0000-0000-000000000003')$$, '42501');
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.no('Alice cannot endorse herself', $$insert into public.skill_endorsements (profile_id, skill, endorser) values ('aaaa0041-0000-0000-0000-000000000001', 'GMP', 'aaaa0041-0000-0000-0000-000000000001')$$, '23514');
select pg_temp.step('Alice tries to remove Bob''s endorsement', $$delete from public.skill_endorsements where endorser = 'aaaa0041-0000-0000-0000-000000000002'$$);
select pg_temp.as_server();
select pg_temp.ok('Bob''s endorsement stays', $$(select count(*) = 1 from public.skill_endorsements where profile_id = 'aaaa0041-0000-0000-0000-000000000001' and endorser = 'aaaa0041-0000-0000-0000-000000000002')$$);
select pg_temp.ok('Alice is told of the endorsement', $$(select count(*) = 1 from public.notifications where user_id = 'aaaa0041-0000-0000-0000-000000000001' and from_user = 'aaaa0041-0000-0000-0000-000000000002' and type = 'endorse')$$);
update public.profiles set skills = array['Validation'] where id = 'aaaa0041-0000-0000-0000-000000000001';
select pg_temp.ok('a removed skill takes its endorsements with it', $$(select count(*) = 0 from public.skill_endorsements where profile_id = 'aaaa0041-0000-0000-0000-000000000001' and skill = 'GMP')$$);

-- ══ who viewed my profile ═════════════════════════════════════════════════════════════════
insert into public.profile_view_log (target, viewer) values ('aaaa0041-0000-0000-0000-000000000001', 'aaaa0041-0000-0000-0000-000000000002'), ('aaaa0041-0000-0000-0000-000000000001', 'aaaa0041-0000-0000-0000-000000000003') on conflict do nothing;
update public.member_settings set show_visits = false where user_id = 'aaaa0041-0000-0000-0000-000000000003';
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.ok('Alice sees Bob named and Cara counted only', $$(select (v->>'total')::int = 2 and (v->>'private')::int = 1 and jsonb_array_length(v->'viewers') = 1 and v->'viewers'->0->>'name' = 'S41 Bob' from (select public.my_profile_viewers(20) v) x)$$);
select pg_temp.as_anon();
select pg_temp.no('a visitor cannot ask who viewed', $$select public.my_profile_viewers(20)$$, '42501');

-- ══ saved searches ════════════════════════════════════════════════════════════════════════
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.step('Alice saves a search', $$insert into public.saved_searches (user_id, kind, name, q, filters, alert) values ('aaaa0041-0000-0000-0000-000000000001', 'market', 'Metformin', 'Metformin', '{}', 'instant')$$);
select pg_temp.no('Alice cannot save a search for Bob', $$insert into public.saved_searches (user_id, kind, name, q) values ('aaaa0041-0000-0000-0000-000000000002', 'market', 'x', 'x')$$, '42501');
select pg_temp.step('Alice saves 19 more', $$insert into public.saved_searches (user_id, name, q) select 'aaaa0041-0000-0000-0000-000000000001', 'n' || g, 'q' from generate_series(1, 19) g$$);
select pg_temp.no('the 21st is refused', $$insert into public.saved_searches (user_id, name, q) values ('aaaa0041-0000-0000-0000-000000000001', 'one more', 'q')$$, '23514');
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000002');
select pg_temp.ok('Bob cannot read Alice''s saved searches', $$(select count(*) = 0 from public.saved_searches where user_id = 'aaaa0041-0000-0000-0000-000000000001')$$);
select pg_temp.step('Bob lists Metformin', $$insert into public.products (user_id, name, category, price, unit) values ('aaaa0041-0000-0000-0000-000000000002', 'Metformin HCl S41 lot', 'api', 3.9, 'kg')$$);
select pg_temp.as_server();
select pg_temp.ok('Alice is told of the new match', $$(select count(*) = 1 from public.notifications where user_id = 'aaaa0041-0000-0000-0000-000000000001' and type = 'saved_search' and data->>'title' = 'Metformin HCl S41 lot')$$);

-- ══ messages: one notice per unread conversation ══════════════════════════════════════════
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000005');
select pg_temp.step('Dina messages Alice twice', $$insert into public.messages (sender_id, receiver_id, body) values ('aaaa0041-0000-0000-0000-000000000005', 'aaaa0041-0000-0000-0000-000000000001', 'S41 hi'), ('aaaa0041-0000-0000-0000-000000000005', 'aaaa0041-0000-0000-0000-000000000001', 'S41 hi again')$$);
select pg_temp.as_server();
select pg_temp.ok('Alice has one message notice', $$(select count(*) = 1 from public.notifications where user_id = 'aaaa0041-0000-0000-0000-000000000001' and from_user = 'aaaa0041-0000-0000-0000-000000000005' and type = 'message' and not read)$$);
select pg_temp.ok('the notice is queued for e-mail (Alice''s default: messages on)', $$(select count(*) = 1 from private.email_outbox o join public.notifications n on n.id = o.notification_id where n.user_id = 'aaaa0041-0000-0000-0000-000000000001' and n.type = 'message')$$);
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.step('Alice reads the conversation', $$update public.messages set read_at = now() where receiver_id = 'aaaa0041-0000-0000-0000-000000000001' and sender_id = 'aaaa0041-0000-0000-0000-000000000005'$$);
select pg_temp.as_server();
select pg_temp.ok('reading it marks the notice read', $$(select count(*) = 0 from public.notifications where user_id = 'aaaa0041-0000-0000-0000-000000000001' and from_user = 'aaaa0041-0000-0000-0000-000000000005' and type = 'message' and not read)$$);
insert into public.conversation_mutes (owner, partner) values ('aaaa0041-0000-0000-0000-000000000001', 'aaaa0041-0000-0000-0000-000000000005');
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000005');
select pg_temp.step('Dina writes again', $$insert into public.messages (sender_id, receiver_id, body) values ('aaaa0041-0000-0000-0000-000000000005', 'aaaa0041-0000-0000-0000-000000000001', 'S41 muted')$$);
select pg_temp.as_server();
select pg_temp.ok('a muted sender makes no notice', $$(select count(*) = 0 from public.notifications where user_id = 'aaaa0041-0000-0000-0000-000000000001' and from_user = 'aaaa0041-0000-0000-0000-000000000005' and type = 'message' and not read)$$);

-- ══ the e-mail outbox is the server's ═════════════════════════════════════════════════════
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.no('a member cannot read the outbox', $$select count(*) from private.email_outbox$$, '42501');
select pg_temp.no('a member cannot claim e-mails', $$select public.email_outbox_claim(10)$$, '42501');
select pg_temp.no('a member cannot mark an e-mail sent', $$select public.email_outbox_done(1, true, null)$$, '42501');
select pg_temp.as_service();
select pg_temp.ok('the server claims the due e-mails with their address', $$(select count(*) >= 1 from jsonb_array_elements(public.email_outbox_claim(50)) e where e->>'to' = 's41-a@x' and e->'notice'->>'type' = 'message')$$);
select pg_temp.as_server();
update public.member_settings set email_reactions = false, email_comments = false where user_id = 'aaaa0041-0000-0000-0000-000000000002';
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000003');
select pg_temp.step('Cara reacts to Bob''s post', $$insert into public.reactions (post_id, user_id, kind) values (pg_temp.id('pb'), 'aaaa0041-0000-0000-0000-000000000003', 'like')$$);
select pg_temp.as_server();
select pg_temp.ok('a kind switched off is not e-mailed', $$(select count(*) = 0 from private.email_outbox o join public.notifications n on n.id = o.notification_id where n.user_id = 'aaaa0041-0000-0000-0000-000000000002' and n.type = 'like')$$);

-- ══ member reports, the queue, suspension ═════════════════════════════════════════════════
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.step('Alice reports Bob', $$insert into public.member_reports (reporter, reported, reason, note) values ('aaaa0041-0000-0000-0000-000000000001', 'aaaa0041-0000-0000-0000-000000000002', 'spam', 'sends ads')$$);
select pg_temp.no('the same open report twice is refused', $$insert into public.member_reports (reporter, reported, reason) values ('aaaa0041-0000-0000-0000-000000000001', 'aaaa0041-0000-0000-0000-000000000002', 'spam')$$, '23505');
select pg_temp.no('Alice cannot report herself', $$insert into public.member_reports (reporter, reported, reason) values ('aaaa0041-0000-0000-0000-000000000001', 'aaaa0041-0000-0000-0000-000000000001', 'spam')$$, '42501');
select pg_temp.no('Alice cannot report in Cara''s name', $$insert into public.member_reports (reporter, reported, reason) values ('aaaa0041-0000-0000-0000-000000000003', 'aaaa0041-0000-0000-0000-000000000002', 'spam')$$, '42501');
select pg_temp.step('Alice reports Cara''s comment', $$insert into public.member_reports (reporter, reported, reason, comment_id) values ('aaaa0041-0000-0000-0000-000000000001', 'aaaa0041-0000-0000-0000-000000000003', 'abusive', pg_temp.id('cc'))$$);
select pg_temp.ok('the comment is copied into the report', $$(select excerpt = 'S41 cara comment' from public.member_reports where reporter = 'aaaa0041-0000-0000-0000-000000000001' and reported = 'aaaa0041-0000-0000-0000-000000000003')$$);
select pg_temp.no('Alice cannot open the queue', $$select public.reported_members(10)$$, '42501');
select pg_temp.no('Alice cannot suspend anyone', $$select public.member_decide('aaaa0041-0000-0000-0000-000000000002', 'suspend', 'x', false)$$, '42501');
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000002');
select pg_temp.ok('Bob cannot read reports about him', $$(select count(*) = 0 from public.member_reports where reported = 'aaaa0041-0000-0000-0000-000000000002')$$);
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000004');
select pg_temp.ok('the moderator sees Bob in the queue', $$(select count(*) = 1 from jsonb_array_elements(public.reported_members(50)) x where x->>'id' = 'aaaa0041-0000-0000-0000-000000000002')$$);
select pg_temp.no('a suspension needs a reason', $$select public.member_decide('aaaa0041-0000-0000-0000-000000000002', 'suspend', '', false)$$, '22023');
select pg_temp.step('the moderator suspends Bob and removes his posts', $$select public.member_decide('aaaa0041-0000-0000-0000-000000000002', 'suspend', 'Spam ads', true)$$);
select pg_temp.as_server();
select pg_temp.ok('the suspension is stored with its reason', $$(select reason = 'Spam ads' and suspended_by = 'aaaa0041-0000-0000-0000-000000000004' from public.account_suspensions where user_id = 'aaaa0041-0000-0000-0000-000000000002')$$);
select pg_temp.ok('Bob''s posts are removed', $$(select count(*) = 0 from public.posts where user_id = 'aaaa0041-0000-0000-0000-000000000002')$$);
select pg_temp.ok('Alice is told the outcome', $$(select count(*) = 1 from public.notifications where user_id = 'aaaa0041-0000-0000-0000-000000000001' and type = 'report_closed' and data->>'outcome' = 'member_actioned')$$);
select pg_temp.ok('the decision is logged', $$(select count(*) = 1 from public.moderation_log where target_user = 'aaaa0041-0000-0000-0000-000000000002' and action = 'suspend' and admin = 'aaaa0041-0000-0000-0000-000000000004')$$);
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000002');
select pg_temp.ok('Bob learns he is suspended', $$(select (public.my_account_status()->>'suspended')::boolean)$$);
select pg_temp.no('Bob cannot post', $$insert into public.posts (user_id, body) values ('aaaa0041-0000-0000-0000-000000000002', 'after')$$, '42501');
select pg_temp.no('Bob cannot message', $$insert into public.messages (sender_id, receiver_id, body) values ('aaaa0041-0000-0000-0000-000000000002', 'aaaa0041-0000-0000-0000-000000000001', 'after')$$, '42501');
select pg_temp.no('Bob cannot comment', $$insert into public.comments (post_id, user_id, body) values (pg_temp.id('pa'), 'aaaa0041-0000-0000-0000-000000000002', 'after')$$, '42501');
select pg_temp.no('Bob cannot lift his own suspension', $$select public.lift_suspension('aaaa0041-0000-0000-0000-000000000002', 'me')$$, '42501');
-- 0047: a suspension stops changes too; a deleted account writes nothing; blocks cover replies; no request to a deleted member
select pg_temp.as_server();
insert into public.posts (user_id, body) values ('aaaa0041-0000-0000-0000-000000000002', 'S41 bob kept post');
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000002');
select pg_temp.no('suspended Bob cannot edit a post', $$update public.posts set body = 'spam' where user_id = 'aaaa0041-0000-0000-0000-000000000002'$$, '42501');
select pg_temp.no('suspended Bob cannot change his profile', $$update public.profiles set headline = 'Buy cheap pills' where id = 'aaaa0041-0000-0000-0000-000000000002'$$, '42501');
select pg_temp.no('suspended Bob cannot create a group', $$insert into public.groups (name, created_by, type) values ('Spam group', 'aaaa0041-0000-0000-0000-000000000002', 'public')$$, '42501');
select pg_temp.as_server();
update public.profiles set account_type = 'deleted' where id = 'aaaa0041-0000-0000-0000-000000000005';
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000005');
select pg_temp.no('a deleted account''s old token cannot post', $$insert into public.posts (user_id, body) values ('aaaa0041-0000-0000-0000-000000000005', 'ghost')$$, '42501');
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.no('nobody can send a request to a deleted member', $$insert into public.connections (requester, addressee, status) values ('aaaa0041-0000-0000-0000-000000000001', 'aaaa0041-0000-0000-0000-000000000005', 'pending')$$, '42501');
select pg_temp.no('nobody can follow a deleted member', $$insert into public.person_followers (person_id, user_id) values ('aaaa0041-0000-0000-0000-000000000005', 'aaaa0041-0000-0000-0000-000000000001')$$, '42501');
select pg_temp.no('a photo address with ".." is refused', $$update public.profiles set avatar_url = 'http://localhost:54321/storage/v1/object/public/avatars/aaaa0041-0000-0000-0000-000000000001/../aaaa0041-0000-0000-0000-000000000003/avatar.jpg' where id = 'aaaa0041-0000-0000-0000-000000000001'$$, '22023');
select pg_temp.no('another host with the path in its query is refused', $$update public.profiles set avatar_url = 'https://evil.example/?/storage/v1/object/public/avatars/aaaa0041-0000-0000-0000-000000000001/a.jpg' where id = 'aaaa0041-0000-0000-0000-000000000001'$$, '22023');
select pg_temp.as_server();
insert into public.posts (user_id, body) values ('aaaa0041-0000-0000-0000-000000000004', 'S41 mod post');
insert into public.comments (post_id, user_id, body) select id, 'aaaa0041-0000-0000-0000-000000000003', 'S41 cara on mod post' from public.posts where body = 'S41 mod post';
insert into public.user_blocks (blocker, blocked) values ('aaaa0041-0000-0000-0000-000000000003', 'aaaa0041-0000-0000-0000-000000000004') on conflict do nothing;
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000004');
select pg_temp.no('a blocked person cannot reply to the blocker''s comment', $$insert into public.comments (post_id, user_id, body, parent_id) select c.post_id, 'aaaa0041-0000-0000-0000-000000000004', 'x', c.id from public.comments c where c.body = 'S41 cara on mod post'$$, '42501');

-- ══ a connection's phone (0046) ═══════════════════════════════════════════════════════════
select pg_temp.as_server();
insert into public.connections (requester, addressee, status) values ('aaaa0041-0000-0000-0000-000000000001', 'aaaa0041-0000-0000-0000-000000000003', 'accepted') on conflict do nothing;
update public.profiles set phone = '+201001234567' where id = 'aaaa0041-0000-0000-0000-000000000003';
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.ok('a connection''s phone stays hidden until they share it', $$public.connection_phone('aaaa0041-0000-0000-0000-000000000003') is null$$);
select pg_temp.as_server();
update public.member_settings set phone_connections = true where user_id = 'aaaa0041-0000-0000-0000-000000000003';
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.ok('a connection who shares it: the phone', $$public.connection_phone('aaaa0041-0000-0000-0000-000000000003') = '+201001234567'$$);
select pg_temp.ok('the phone column itself stays private', $$not has_column_privilege('authenticated', 'public.profiles', 'phone', 'select')$$);
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000002');
select pg_temp.ok('not connected: no phone', $$public.connection_phone('aaaa0041-0000-0000-0000-000000000003') is null$$);
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000003');
select pg_temp.step('Cara blocks Alice', $$insert into public.user_blocks (blocker, blocked) values ('aaaa0041-0000-0000-0000-000000000003', 'aaaa0041-0000-0000-0000-000000000001')$$);
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.ok('connected but blocked: no phone', $$public.connection_phone('aaaa0041-0000-0000-0000-000000000003') is null$$);
select pg_temp.as_anon();
select pg_temp.no('a visitor cannot ask', $$select public.connection_phone('aaaa0041-0000-0000-0000-000000000003')$$, '42501');

-- ══ find_people (0048) ═════════════════════════════════════════════════════════════════════
select pg_temp.as_user('aaaa0041-0000-0000-0000-000000000001');
select pg_temp.ok('find_people finds members by name and never me', $$(select count(*) >= 2 and count(*) filter (where id = 'aaaa0041-0000-0000-0000-000000000001') = 0 from public.find_people('S41', null, null, 30))$$);
select pg_temp.ok('find_people leaves out deleted members', $$(select count(*) = 0 from public.find_people('S41 Dina', null, null, 30))$$);
select pg_temp.ok('find_people leaves out people blocked either way (Cara blocked Alice)', $$(select count(*) = 0 from public.find_people('S41 Cara', null, null, 30))$$);
select pg_temp.ok('find_people with nothing to look for returns nothing', $$(select count(*) = 0 from public.find_people(null, null, null, 30))$$);
select pg_temp.as_anon();
select pg_temp.no('a visitor cannot list members', $$select * from public.find_people('S41', null, null, 30)$$, '42501');

select pg_temp.as_anon();
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
