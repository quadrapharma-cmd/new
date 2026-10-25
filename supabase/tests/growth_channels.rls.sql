-- Official Drugbox channels, the scheduler and the therapeutic tags (0100, AREA w-growth: W-41, W-21). Only Drugbox admins plan and
-- publish channel posts (draft → scheduled in Cairo time → published by growth_tick(), edit / cancel before); nobody posts into a
-- channel from the browser, nobody becomes a channel's admin, a group's own admins cannot make their group official; a channel post
-- reads as Drugbox (as_drugbox, the members' notice names no person); thera tags come from the text (+ the tags Drugbox gave a channel
-- post), never from the browser; feed_thera / market_search_thera filter on the server. Runs as the real API roles with a JWT, in one
-- transaction that is rolled back; test data carries the "GW " marker. Run on a fresh database (stub + migrations):
-- psql -f supabase/tests/growth_channels.rls.sql
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

-- A Drugbox admin, M member, G a member who runs their own group, O outsider
insert into auth.users (id, email) values ('b1000000-0000-0000-0000-000000000001','gw-a@x'),('b1000000-0000-0000-0000-000000000002','gw-m@x'),
  ('b1000000-0000-0000-0000-000000000003','gw-g@x'),('b1000000-0000-0000-0000-000000000004','gw-o@x') on conflict do nothing;
insert into public.profiles (id, name) values ('b1000000-0000-0000-0000-000000000001','GW Admin'),('b1000000-0000-0000-0000-000000000002','GW Member'),
  ('b1000000-0000-0000-0000-000000000003','GW Groupadmin'),('b1000000-0000-0000-0000-000000000004','GW Outsider') on conflict (id) do update set name = excluded.name;
update public.profiles set role = 'admin' where id = 'b1000000-0000-0000-0000-000000000001';

create function pg_temp.A() returns void language sql as $$ select pg_temp.as_user('b1000000-0000-0000-0000-000000000001') $$;
create function pg_temp.M() returns void language sql as $$ select pg_temp.as_user('b1000000-0000-0000-0000-000000000002') $$;
create function pg_temp.G() returns void language sql as $$ select pg_temp.as_user('b1000000-0000-0000-0000-000000000003') $$;
create function pg_temp.O() returns void language sql as $$ select pg_temp.as_user('b1000000-0000-0000-0000-000000000004') $$;
insert into ids select 'news', id::text from public.groups where channel_key = 'news';
insert into ids select 'market', id::text from public.groups where channel_key = 'market';

-- 1. the four channels
select pg_temp.M();
select pg_temp.ok('the four channels exist, official, public, Drugbox-only posting', $$(select count(*) = 4 from public.groups where official and type = 'public' and post_policy = 'admins' and channel_key in ('news','jobs','regulatory','market'))$$);
select pg_temp.ok('each has its Arabic name', $$(select count(*) = 4 from public.groups where official and name_ar is not null)$$);
select pg_temp.ok('no member and no post were invented for them', $$(select coalesce(sum(member_count),0) = 0 from public.groups where official) and not exists (select 1 from public.posts p join public.groups g on g.id = p.group_id where g.official)$$);
select pg_temp.step('M joins Drugbox News', $$insert into public.group_members (group_id, user_id) values (pg_temp.id('news'), 'b1000000-0000-0000-0000-000000000002')$$);
select pg_temp.ok('… and reads it as a member', $$(select count(*) = 1 from public.group_members where group_id = pg_temp.id('news') and user_id = auth.uid())$$);
select pg_temp.no('a member cannot post into a channel', $$insert into public.posts (user_id, body, group_id) values (auth.uid(), 'GW I am Drugbox', pg_temp.id('news'))$$, '42501');
select pg_temp.no('a member cannot make themself the channel''s admin', $$update public.group_members set role = 'admin' where group_id = pg_temp.id('news') and user_id = auth.uid()$$, '42501');
select pg_temp.ok('a member cannot rename a channel (no row changes)', $$(select count(*) = 0 from (select 1) x where false)$$);
select pg_temp.step('… tries', $$update public.groups set name = 'GW Hijacked' where id = pg_temp.id('news')$$);
select pg_temp.ok('… and the name stays', $$(select name = 'Drugbox News' from public.groups where id = pg_temp.id('news'))$$);
select pg_temp.A();
select pg_temp.no('even a Drugbox admin does not post into a channel from the browser', $$insert into public.posts (user_id, body, group_id) values (auth.uid(), 'GW direct', pg_temp.id('news'))$$, '42501');
select pg_temp.no('a Drugbox admin cannot join a channel as its admin', $$insert into public.group_members (group_id, user_id, role) values (pg_temp.id('market'), auth.uid(), 'admin')$$, '42501');
select pg_temp.step('a Drugbox admin edits a channel''s Arabic description', $$update public.groups set description_ar = 'GW وصف' where id = pg_temp.id('news')$$);
select pg_temp.ok('… kept', $$(select description_ar = 'GW وصف' from public.groups where id = pg_temp.id('news'))$$);
select pg_temp.no('… but a channel cannot become private', $$update public.groups set type = 'private' where id = pg_temp.id('news')$$, '42501');
select pg_temp.no('… nor stop being a channel', $$update public.groups set official = false where id = pg_temp.id('news')$$, '42501');

-- 2. a group's own admins cannot make it official
select pg_temp.G();
select pg_temp.step('G creates their own group', $$with x as (insert into public.groups (name, created_by) values ('GW Own group', auth.uid()) returning id) insert into ids select 'own', id::text from x$$);
select pg_temp.ok('G is its admin', $$public.is_group_member(pg_temp.id('own'), array['admin'])$$);
select pg_temp.no('G cannot make it official', $$update public.groups set official = true where id = pg_temp.id('own')$$, '42501');
select pg_temp.no('G cannot give it a channel key', $$update public.groups set channel_key = 'news' where id = pg_temp.id('own')$$, '42501');
select pg_temp.no('G cannot tag it with therapeutic areas', $$update public.groups set thera = '{oncology}' where id = pg_temp.id('own')$$, '42501');
select pg_temp.no('nobody creates an official group', $$insert into public.groups (name, created_by, official) values ('GW Fake channel', auth.uid(), true)$$, '42501');
select pg_temp.step('a post with a fake as_drugbox and fake tags', $$with x as (insert into public.posts (user_id, body, as_drugbox, thera) values (auth.uid(), 'GW Insulin pens available for companies', true, '{oncology,biologics}') returning id) insert into ids select 'gp', id::text from x$$);
select pg_temp.ok('… is not Drugbox and carries only the text''s area', $$(select not as_drugbox and thera = '{insulin}' from public.posts where id = pg_temp.id('gp'))$$);
select pg_temp.step('G edits only the tags', $$update public.posts set thera = '{oncology}', as_drugbox = true where id = pg_temp.id('gp')$$);
select pg_temp.ok('… nothing changes', $$(select not as_drugbox and thera = '{insulin}' from public.posts where id = pg_temp.id('gp'))$$);
select pg_temp.step('G rewrites the text', $$update public.posts set body = 'GW Semaglutide and cancer drugs' where id = pg_temp.id('gp')$$);
select pg_temp.ok('… the areas follow the text', $$(select thera = '{glp1,oncology}' from public.posts where id = pg_temp.id('gp'))$$);

-- 3. the scheduler: Drugbox admins only
select pg_temp.M();
select pg_temp.no('a member cannot plan a channel post', $$select public.channel_schedule_save(null, 'news', 'GW x', null, 'draft')$$, '42501');
select pg_temp.no('a member cannot read the templates'' next slot', $$select public.channel_template_next('wanted_today')$$, '42501');
select pg_temp.ok('a member reads no template and no plan', $$(select count(*) = 0 from public.channel_templates) and (select count(*) = 0 from public.channel_schedule) and (select count(*) = 0 from public.channel_schedule_list(50))$$);
select pg_temp.no('a member cannot write the plan directly', $$insert into public.channel_schedule (group_id, body) values (pg_temp.id('news'), 'GW x')$$, '42501');
select pg_temp.no('a member cannot run the runner', $$select public.growth_tick()$$, '42501');
select pg_temp.as_anon();
select pg_temp.no('anon cannot plan', $$select public.channel_schedule_save(null, 'news', 'GW x', null, 'draft')$$, '42501');
select pg_temp.ok('anon reads no plan', $$(select count(*) = 0 from public.channel_schedule)$$);
select pg_temp.A();
select pg_temp.ok('the admin reads the seven templates of the content plan', $$(select count(*) = 7 from public.channel_templates)$$);
select pg_temp.ok('«مطلوب النهارده» is daily at 21:00 Cairo in Market', $$(select cadence = 'daily' and at_time = '21:00' and channel_key = 'market' and title_ar = 'مطلوب النهارده' from public.channel_templates where key = 'wanted_today')$$);
select pg_temp.ok('the next slot is in the future, at 21:00', $$(select public.channel_template_next('wanted_today') like '% 21:00' and (public.channel_template_next('wanted_today')::timestamp at time zone 'Africa/Cairo') > now())$$);
select pg_temp.ok('a weekly template''s next slot falls on its weekday', $$(select extract(dow from public.channel_template_next('regulatory_bulletin')::timestamp) = 0)$$);
select pg_temp.step('the admin saves a draft', $$insert into ids values ('d', public.channel_schedule_save(null, 'news', 'GW Draft about insulin', null, 'draft', '{fertility}', 'practical_guide')::text)$$);
select pg_temp.no('scheduling needs a time', $$select public.channel_schedule_save(pg_temp.id('d'), 'news', 'GW Draft', null, 'scheduled')$$, '22023');
select pg_temp.no('a time in the past is refused', $$select public.channel_schedule_save(pg_temp.id('d'), 'news', 'GW Draft', '2020-01-01 21:00', 'scheduled')$$, '22023');
select pg_temp.no('a wrong time format is refused', $$select public.channel_schedule_save(pg_temp.id('d'), 'news', 'GW Draft', 'tomorrow 9pm', 'scheduled')$$, '22023');
select pg_temp.no('an unknown area is refused', $$select public.channel_schedule_save(pg_temp.id('d'), 'news', 'GW Draft', null, 'draft', '{pharmacy}')$$, '22023');
select pg_temp.no('an unknown channel is refused', $$select public.channel_schedule_save(pg_temp.id('d'), 'gossip', 'GW Draft', null, 'draft')$$, '22023');
select pg_temp.no('an empty post is refused', $$select public.channel_schedule_save(null, 'news', '   ', null, 'draft')$$, '22023');
select pg_temp.no('the status cannot be set to published', $$select public.channel_schedule_save(pg_temp.id('d'), 'news', 'GW Draft', null, 'published')$$, '22023');
select pg_temp.step('the admin schedules it for tomorrow 21:00 Cairo', $$select public.channel_schedule_save(pg_temp.id('d'), 'news', 'GW Draft about insulin', to_char((now() at time zone 'Africa/Cairo')::date + 1, 'YYYY-MM-DD') || ' 21:00', 'scheduled', '{fertility}')$$);
select pg_temp.ok('… stored as that Cairo moment', $$(select status = 'scheduled' and publish_at = ((((now() at time zone 'Africa/Cairo')::date + 1) + time '21:00') at time zone 'Africa/Cairo') from public.channel_schedule where id = pg_temp.id('d'))$$);
select pg_temp.ok('… and listed with its Cairo time', $$(select publish_local like '% 21:00' and status = 'scheduled' and channel_key = 'news' from public.channel_schedule_list(50) where id = pg_temp.id('d'))$$);
select pg_temp.as_server();
select pg_temp.ok('the runner publishes nothing before the time', $$(select (public.growth_tick() ->> 'published')::int = 0) and (select status = 'scheduled' from public.channel_schedule where id = pg_temp.id('d'))$$);
select pg_temp.step('… time passes (the plan''s time is moved to a minute ago)', $$update public.channel_schedule set publish_at = now() - interval '1 minute' where id = pg_temp.id('d')$$);
select pg_temp.ok('the runner publishes it', $$(select (public.growth_tick() ->> 'published')::int = 1)$$);
select pg_temp.ok('… once', $$(select (public.growth_tick() ->> 'published')::int = 0)$$);
select pg_temp.ok('… as a Drugbox post in News, with the chosen tag and the text''s', $$(select p.as_drugbox and p.group_id = pg_temp.id('news') and p.thera = '{fertility,insulin}' and s.status = 'published' and s.published_at is not null
  from public.channel_schedule s join public.posts p on p.id = s.post_id where s.id = pg_temp.id('d'))$$);
select pg_temp.ok('the member of News is told by Drugbox (no person named)', $$(select count(*) = 1 from public.notifications where user_id = 'b1000000-0000-0000-0000-000000000002' and type = 'group_post' and group_id = pg_temp.id('news') and from_user is null and (data ->> 'drugbox')::boolean)$$);
select pg_temp.A();
select pg_temp.no('a published post cannot be edited from the plan', $$select public.channel_schedule_save(pg_temp.id('d'), 'news', 'GW changed', null, 'draft')$$, '55000');
select pg_temp.no('… nor cancelled', $$select public.channel_schedule_cancel(pg_temp.id('d'))$$, '55000');
select pg_temp.no('… nor its text changed in the feed', $$update public.posts set body = 'GW edited' where id = (select post_id from public.channel_schedule where id = pg_temp.id('d'))$$, '42501');
select pg_temp.step('the admin plans another and cancels it', $$insert into ids values ('c', public.channel_schedule_save(null, 'market', 'GW Wanted today', to_char((now() at time zone 'Africa/Cairo')::date + 2, 'YYYY-MM-DD') || ' 21:00', 'scheduled', '{}', 'wanted_today')::text)$$);
select pg_temp.step('… cancel', $$select public.channel_schedule_cancel(pg_temp.id('c'))$$);
select pg_temp.as_server();
select pg_temp.step('… its time passes', $$update public.channel_schedule set publish_at = now() - interval '1 minute' where id = pg_temp.id('c')$$);
select pg_temp.ok('a cancelled post is never published', $$(select (public.growth_tick() ->> 'published')::int = 0) and (select status = 'cancelled' and post_id is null from public.channel_schedule where id = pg_temp.id('c'))$$);
select pg_temp.A();
select pg_temp.step('the admin publishes a draft now', $$insert into ids values ('n', public.channel_schedule_save(null, 'market', 'GW Agency market', null, 'draft')::text)$$);
select pg_temp.ok('… "Publish now" writes the post at once', $$(select public.channel_publish_now(pg_temp.id('n')) is not null)$$);
select pg_temp.ok('… and the plan says published', $$(select status = 'published' and post_id is not null from public.channel_schedule where id = pg_temp.id('n'))$$);
select pg_temp.M();
select pg_temp.no('a member cannot publish a plan', $$select public.channel_publish_now(pg_temp.id('c'))$$, '42501');
select pg_temp.no('a member cannot cancel a plan', $$select public.channel_schedule_cancel(pg_temp.id('c'))$$, '42501');
select pg_temp.ok('everyone reads the channel''s posts (public channel)', $$(select count(*) = 2 from public.posts p join public.groups g on g.id = p.group_id where g.official and p.as_drugbox)$$);

-- 4. filters
select pg_temp.ok('feed_thera finds the member post about GLP-1', $$(select count(*) >= 1 from public.feed_thera('glp1') where id = pg_temp.id('gp'))$$);
select pg_temp.ok('… not under fertility', $$(select count(*) = 0 from public.feed_thera('fertility') where id = pg_temp.id('gp'))$$);
select pg_temp.as_server();
select pg_temp.step('a supplier lists insulin', $$with x as (insert into public.products (user_id, name, description, type, category, active) values ('b1000000-0000-0000-0000-000000000003', 'GW Insulin glargine pens', 'bulk, for distributors', 'supply', 'finished', true) returning id) insert into ids select 'pr', id::text from x$$);
select pg_temp.M();
select pg_temp.ok('the product is tagged insulin', $$(select thera = '{insulin}' from public.products where id = pg_temp.id('pr'))$$);
select pg_temp.ok('market_search_thera finds it under insulin', $$(select (public.market_search_thera('insulin', 'GW') -> 'rows') @> jsonb_build_array(jsonb_build_object('id', pg_temp.id('pr'))))$$);
select pg_temp.ok('… and not under oncology', $$(select (public.market_search_thera('oncology', 'GW') ->> 'total')::int = 0)$$);
select pg_temp.no('an unknown area is refused', $$select public.market_search_thera('pharmacy')$$, '22023');
select pg_temp.as_anon();
select pg_temp.no('anon cannot search the market by area', $$select public.market_search_thera('insulin')$$, '42501');

-- 5. verifier round 1: a Drugbox post stays Drugbox's (restore, former admin, notices); dictionary false positives
select pg_temp.as_server();
select pg_temp.ok('"HMG-CoA" (statins) is not fertility; كيماويات (chemicals) is not oncology', $$private.thera_of('HMG-CoA reductase inhibitors API') = '{}' and private.thera_of('مورد كيماويات صناعية') = '{}' and private.thera_of('علاج كيماوي للأورام') = '{oncology}'$$);
insert into ids select 'np', post_id::text from public.channel_schedule where id = pg_temp.id('n');
select pg_temp.M();
select pg_temp.step('M likes and comments on the Drugbox post', $$insert into public.reactions (post_id, user_id, kind) values (pg_temp.id('np'), auth.uid(), 'like'); insert into public.comments (post_id, user_id, body) values (pg_temp.id('np'), auth.uid(), 'GW thanks')$$);
select pg_temp.as_server();
select pg_temp.ok('the publishing admin gets no personal notice about the Drugbox post', $$not exists (select 1 from public.notifications where user_id = 'b1000000-0000-0000-0000-000000000001' and post_id = pg_temp.id('np'))$$);
select pg_temp.A();
select pg_temp.step('Drugbox removes the channel post', $$insert into ids select 'act', public.admin_delete_post(pg_temp.id('np'), 'GW test removal')::text$$);
select pg_temp.step('… and restores it', $$select public.admin_restore_post(pg_temp.id('act'))$$);
select pg_temp.ok('the restored post is still a Drugbox post', $$(select as_drugbox from public.posts where id = pg_temp.id('np'))$$);
select pg_temp.as_server();
select pg_temp.step('the admin stops being a Drugbox admin', $$update public.profiles set role = 'user' where id = 'b1000000-0000-0000-0000-000000000001'$$);
select pg_temp.A();
select pg_temp.step('the former admin tries to change the Drugbox post', $$update public.posts set category = 'general' where id = pg_temp.id('np')$$);
select pg_temp.step('… and to delete it', $$delete from public.posts where id = pg_temp.id('np')$$);
select pg_temp.as_server();
select pg_temp.ok('the Drugbox post is untouched', $$(select category = 'market' and as_drugbox from public.posts where id = pg_temp.id('np'))$$);
update public.profiles set role = 'admin' where id = 'b1000000-0000-0000-0000-000000000001';

-- 6. verifier round 2 (0105): a Drugbox post has no member author; restore keeps its tags; the dictionary
select pg_temp.as_server();
select pg_temp.ok('a channel post has no member as author; Drugbox keeps who published it', $$(select p.user_id is null and s.published_by = 'b1000000-0000-0000-0000-000000000001' from public.channel_schedule s join public.posts p on p.id = s.post_id where s.id = pg_temp.id('d'))$$);
select pg_temp.ok('the admin got no "removed / restored your post" notice for it', $$not exists (select 1 from public.notifications where user_id = 'b1000000-0000-0000-0000-000000000001' and type in ('post_removed', 'post_restored'))$$);
select pg_temp.M();
select pg_temp.ok('a member reading the post (with the author embed) learns no admin', $$(select user_id is null from public.posts where id = pg_temp.id('np')) and not exists (select 1 from public.posts p join public.profiles a on a.id = p.user_id where p.as_drugbox)$$);
select pg_temp.no('a member cannot write an authorless post', $$insert into public.posts (user_id, body) values (null, 'GW nobody')$$, '42501');
select pg_temp.A();
insert into ids select 'dp', post_id::text from public.channel_schedule where id = pg_temp.id('d');
select pg_temp.step('Drugbox removes the tagged post (fertility picked, insulin from the text)', $$insert into ids select 'act2', public.admin_delete_post(pg_temp.id('dp'), 'GW test removal 2')::text$$);
select pg_temp.step('… and restores it', $$select public.admin_restore_post(pg_temp.id('act2'))$$);
select pg_temp.ok('… with the tags it had and still Drugbox''s', $$(select as_drugbox and user_id is null and thera = '{fertility,insulin}' from public.posts where id = pg_temp.id('dp'))$$);
select pg_temp.ok('0106: … and Admin → Channels links it to its plan again', $$(select post_id = pg_temp.id('dp') from public.channel_schedule where id = pg_temp.id('d'))$$);
select pg_temp.ok('0106: Admin → Posts names it "Drugbox" and finds it by that name', $$exists (select 1 from public.admin_posts('drugbox', 200) where id = pg_temp.id('dp') and author = 'Drugbox')$$);
select pg_temp.as_server();
select pg_temp.step('0106: O becomes a moderator', $$update public.profiles set role = 'moderator' where id = 'b1000000-0000-0000-0000-000000000004'$$);
select pg_temp.O();
select pg_temp.no('0106: a moderator cannot remove a Drugbox post', $$select public.admin_delete_post(pg_temp.id('dp'), 'GW moderator removal')$$, '42501');
select pg_temp.as_server();
select pg_temp.step('… O is a member again', $$update public.profiles set role = 'user' where id = 'b1000000-0000-0000-0000-000000000004'$$);
select pg_temp.M();
select pg_temp.step('0106: M reports the Drugbox post inside the channel', $$insert into public.group_post_reports (post_id, group_id, reporter, reason) values (pg_temp.id('dp'), pg_temp.id('news'), auth.uid(), 'spam')$$);
select pg_temp.O();
select pg_temp.step('0106: O reports it from a feed card (Saved)', $$insert into public.post_reports (post_id, reporter, reason) values (pg_temp.id('dp'), auth.uid(), 'misleading')$$);
select pg_temp.as_server();
select pg_temp.ok('… both reports are in Drugbox''s review queue', $$(select count(*) = 2 from public.post_reports where post_id = pg_temp.id('dp') and status = 'open' and post_author is null)$$);
select pg_temp.ok('0106: «العلاج الكيماوي» is oncology', $$private.thera_of('مطلوب أدوية العلاج الكيماوي') = '{oncology}'$$);
select pg_temp.M();
select pg_temp.step('M comments on the restored post', $$insert into public.comments (post_id, user_id, body) values (pg_temp.id('dp'), auth.uid(), 'GW still here')$$);
select pg_temp.as_server();
select pg_temp.ok('«الأمور ماشية» is not veterinary; «أدوية للماشية» is', $$private.thera_of('الأمور ماشية الحمد لله') = '{}' and private.thera_of('أدوية للماشية') = '{veterinary}' and private.thera_of('تحصينات الماشية') = '{veterinary}'$$);
select pg_temp.step('the publishing admin deletes their account', $$insert into private.account_deletions (user_id) values ('b1000000-0000-0000-0000-000000000001'); select public.account_anonymise('b1000000-0000-0000-0000-000000000001')$$);
select pg_temp.ok('… the Drugbox posts stay, with their comments', $$(select count(*) = 2 from public.posts where as_drugbox) and exists (select 1 from public.comments where post_id = pg_temp.id('dp'))$$);
select pg_temp.ok('… and the plan''s record of the publisher is cleared, not the post', $$not exists (select 1 from public.channel_schedule where published_by is not null) and (select status = 'published' from public.channel_schedule where id = pg_temp.id('n'))$$);

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
