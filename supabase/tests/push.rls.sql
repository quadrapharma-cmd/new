-- Web push (0110, w-pwa): a member reads and removes only their own devices, cannot read the device keys, cannot add a device
-- by writing the table, and push_subscribe() takes only addresses of the known push services (no other server can be made a target);
-- an address that was another account's on this browser moves to the caller; at most 10 devices. A notice is queued for a device
-- only of a kind the member allows, never from someone either side blocked or a muted conversation; the queue and the sender's
-- functions are the service role's only; a device the push service no longer knows is removed. Run on a fresh database.
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

insert into auth.users (id, email) values ('aaaa0110-0000-0000-0000-000000000001','pu-a@x'),('aaaa0110-0000-0000-0000-000000000002','pu-b@x'),('aaaa0110-0000-0000-0000-000000000003','pu-c@x') on conflict do nothing;
insert into public.profiles (id, name) values ('aaaa0110-0000-0000-0000-000000000001','PU Alice'),('aaaa0110-0000-0000-0000-000000000002','PU Bob'),('aaaa0110-0000-0000-0000-000000000003','PU Carol') on conflict (id) do update set name = excluded.name;
create function pg_temp.k() returns text language sql immutable as $$ select repeat('A',86)||'Q' $$;
create function pg_temp.au() returns text language sql immutable as $$ select repeat('B',21)||'A' $$;

-- ══ devices ═══════════════════════════════════════════════════════════════════════════════════
select pg_temp.as_anon();
select pg_temp.no('a visitor cannot subscribe', $$select public.push_subscribe('https://fcm.googleapis.com/fcm/send/anon1', pg_temp.k(), pg_temp.au())$$, '42501');
select pg_temp.no('a visitor cannot read devices', $$select count(*) from public.push_subscriptions$$, '42501');
select pg_temp.as_user('aaaa0110-0000-0000-0000-000000000001');
select pg_temp.step('Alice subscribes on Chrome', $$insert into ids values ('a1', public.push_subscribe('https://fcm.googleapis.com/fcm/send/alice-1', pg_temp.k(), pg_temp.au()))$$);
select pg_temp.step('Alice subscribes on an iPhone', $$insert into ids values ('a2', public.push_subscribe('https://web.push.apple.com/QAlice2', pg_temp.k(), pg_temp.au()))$$);
select pg_temp.ok('Alice sees her two devices', $$(select count(*) = 2 from public.push_subscriptions)$$);
select pg_temp.no('Alice cannot read the device keys (server only)', $$select p256dh from public.push_subscriptions$$, '42501');
select pg_temp.no('Alice cannot add a device by writing the table', $$insert into public.push_subscriptions (user_id, endpoint, p256dh, auth) values ('aaaa0110-0000-0000-0000-000000000001', 'https://fcm.googleapis.com/fcm/send/alice-x', pg_temp.k(), pg_temp.au())$$, '42501');
select pg_temp.no('Alice cannot move a device to Bob', $$update public.push_subscriptions set user_id = 'aaaa0110-0000-0000-0000-000000000002'$$, '42501');
select pg_temp.no('an address on another server is refused (no SSRF target)', $$select public.push_subscribe('https://evil.example/fcm.googleapis.com/x', pg_temp.k(), pg_temp.au())$$, '22023');
select pg_temp.no('a look-alike host is refused', $$select public.push_subscribe('https://fcm.googleapis.com.evil.example/x', pg_temp.k(), pg_temp.au())$$, '22023');
select pg_temp.no('plain http to a push service is refused', $$select public.push_subscribe('http://fcm.googleapis.com/fcm/send/x', pg_temp.k(), pg_temp.au())$$, '22023');
select pg_temp.no('an address with credentials / odd characters is refused', $$select public.push_subscribe('https://user@fcm.googleapis.com/x', pg_temp.k(), pg_temp.au())$$, '22023');
select pg_temp.no('the loopback stand-in is not a push service here', $$select public.push_subscribe('http://127.0.0.1:54600/push/x', pg_temp.k(), pg_temp.au())$$, '22023');
select pg_temp.no('a wrong-size key is refused', $$select public.push_subscribe('https://fcm.googleapis.com/fcm/send/alice-3', 'abc', pg_temp.au())$$, '22023');
select pg_temp.as_user('aaaa0110-0000-0000-0000-000000000002');
select pg_temp.ok('Bob does not see Alice''s devices', $$(select count(*) = 0 from public.push_subscriptions)$$);
select pg_temp.step('Bob tries to remove Alice''s devices', $$delete from public.push_subscriptions$$);
select pg_temp.as_server();
select pg_temp.ok('Alice''s devices are still there', $$(select count(*) = 2 from public.push_subscriptions where user_id = 'aaaa0110-0000-0000-0000-000000000001')$$);
select pg_temp.as_user('aaaa0110-0000-0000-0000-000000000002');
select pg_temp.step('Bob signs in on Alice''s Chrome (same browser address)', $$insert into ids values ('b1', public.push_subscribe('https://fcm.googleapis.com/fcm/send/alice-1', pg_temp.k(), pg_temp.au()))$$);
select pg_temp.as_server();
select pg_temp.ok('that browser is now Bob''s only — Alice gets nothing there any more', $$(select user_id = 'aaaa0110-0000-0000-0000-000000000002' from public.push_subscriptions where endpoint = 'https://fcm.googleapis.com/fcm/send/alice-1')$$);
select pg_temp.as_user('aaaa0110-0000-0000-0000-000000000001');
select pg_temp.step('Alice turns her iPhone off', $$delete from public.push_subscriptions where endpoint = 'https://web.push.apple.com/QAlice2'$$);
select pg_temp.ok('Alice has no device left', $$(select count(*) = 0 from public.push_subscriptions)$$);
select pg_temp.step('Alice subscribes 12 browsers', $$select public.push_subscribe('https://fcm.googleapis.com/fcm/send/alice-n' || g, pg_temp.k(), pg_temp.au()) from generate_series(1, 12) g$$);
select pg_temp.ok('at most 10 devices are kept (the newest)', $$(select count(*) = 10 and bool_and(endpoint <> 'https://fcm.googleapis.com/fcm/send/alice-n1') from public.push_subscriptions)$$);
select pg_temp.step('Alice keeps one device for the queue checks', $$delete from public.push_subscriptions where endpoint <> 'https://fcm.googleapis.com/fcm/send/alice-n12'$$);

-- ══ the queue ════════════════════════════════════════════════════════════════════════════════
select pg_temp.as_server();
insert into public.notifications (user_id, type, from_user, message) values ('aaaa0110-0000-0000-0000-000000000001', 'follow', 'aaaa0110-0000-0000-0000-000000000003', 'q-follow');            -- follows: off by default
insert into public.notifications (user_id, type, from_user, message) values ('aaaa0110-0000-0000-0000-000000000001', 'comment', 'aaaa0110-0000-0000-0000-000000000003', 'q-comment');          -- comments: on
insert into public.notifications (user_id, type, from_user, message) values ('aaaa0110-0000-0000-0000-000000000001', 'deal', 'aaaa0110-0000-0000-0000-000000000003', 'q-deal');                -- business: on
insert into public.notifications (user_id, type, from_user, message) values ('aaaa0110-0000-0000-0000-000000000003', 'comment', 'aaaa0110-0000-0000-0000-000000000001', 'q-carol');            -- Carol has no device
select pg_temp.ok('a kind the member switched off is not queued (follow)', $$not exists (select 1 from private.push_outbox o join public.notifications n on n.id = o.notification_id where n.message = 'q-follow')$$);
select pg_temp.ok('allowed kinds are queued (comment, deal)', $$(select count(*) = 2 from private.push_outbox o join public.notifications n on n.id = o.notification_id where n.message in ('q-comment', 'q-deal'))$$);
select pg_temp.ok('a member without a device gets nothing queued', $$not exists (select 1 from private.push_outbox where user_id = 'aaaa0110-0000-0000-0000-000000000003')$$);
select pg_temp.as_user('aaaa0110-0000-0000-0000-000000000001');
select pg_temp.step('Alice switches comments off for her devices', $$update public.member_settings set push_comments = false where user_id = 'aaaa0110-0000-0000-0000-000000000001'$$);
select pg_temp.no('Alice cannot write a setting that is not hers to write', $$update public.member_settings set unsub_token = gen_random_uuid() where user_id = 'aaaa0110-0000-0000-0000-000000000001'$$, '42501');
select pg_temp.as_server();
insert into public.notifications (user_id, type, from_user, message) values ('aaaa0110-0000-0000-0000-000000000001', 'comment', 'aaaa0110-0000-0000-0000-000000000003', 'q-comment-2');
select pg_temp.ok('a switched-off kind is no longer queued', $$not exists (select 1 from private.push_outbox o join public.notifications n on n.id = o.notification_id where n.message = 'q-comment-2')$$);
insert into public.user_blocks (blocker, blocked) values ('aaaa0110-0000-0000-0000-000000000001', 'aaaa0110-0000-0000-0000-000000000003');
insert into public.notifications (user_id, type, from_user, message) values ('aaaa0110-0000-0000-0000-000000000001', 'deal', 'aaaa0110-0000-0000-0000-000000000003', 'q-blocked');
select pg_temp.ok('nothing from someone Alice blocked', $$not exists (select 1 from private.push_outbox o join public.notifications n on n.id = o.notification_id where n.message = 'q-blocked')$$);
delete from public.user_blocks where blocker = 'aaaa0110-0000-0000-0000-000000000001';
insert into public.user_blocks (blocker, blocked) values ('aaaa0110-0000-0000-0000-000000000003', 'aaaa0110-0000-0000-0000-000000000001');
insert into public.notifications (user_id, type, from_user, message) values ('aaaa0110-0000-0000-0000-000000000001', 'deal', 'aaaa0110-0000-0000-0000-000000000003', 'q-blocked-2');
select pg_temp.ok('nothing from someone who blocked Alice', $$not exists (select 1 from private.push_outbox o join public.notifications n on n.id = o.notification_id where n.message = 'q-blocked-2')$$);
delete from public.user_blocks where blocker = 'aaaa0110-0000-0000-0000-000000000003';
insert into public.conversation_mutes (owner, partner) values ('aaaa0110-0000-0000-0000-000000000001', 'aaaa0110-0000-0000-0000-000000000003');
insert into public.notifications (user_id, type, from_user, message) values ('aaaa0110-0000-0000-0000-000000000001', 'message', 'aaaa0110-0000-0000-0000-000000000003', 'q-muted');
select pg_temp.ok('no message notice from a muted conversation', $$not exists (select 1 from private.push_outbox o join public.notifications n on n.id = o.notification_id where n.message = 'q-muted')$$);

select pg_temp.as_user('aaaa0110-0000-0000-0000-000000000001');
select pg_temp.no('Alice cannot read the queue', $$select count(*) from private.push_outbox$$, '42501');
select pg_temp.no('Alice cannot claim the queue (it hands out device keys)', $$select public.push_outbox_claim(10)$$, '42501');
select pg_temp.no('Alice cannot mark a send', $$select public.push_outbox_done(1, true)$$, '42501');
select pg_temp.as_anon();
select pg_temp.no('a visitor cannot claim the queue', $$select public.push_outbox_claim(10)$$, '42501');
select pg_temp.as_service();
select pg_temp.step('the sender claims', $$insert into ids values ('claim', public.push_outbox_claim(50)::text)$$);
select pg_temp.ok('the claim carries Alice''s device with its keys and the sender''s name — never the notice text', $$(select jsonb_array_length(v::jsonb) = 2
   and (v::jsonb->0->'devices'->0->>'endpoint') = 'https://fcm.googleapis.com/fcm/send/alice-n12' and (v::jsonb->0->'devices'->0->>'p256dh') is not null
   and (v::jsonb->0->'notice'->>'from') = 'PU Carol' and position('q-' in v) = 0 from ids where k = 'claim')$$);
select pg_temp.ok('a claimed notice is not handed out twice', $$jsonb_array_length(public.push_outbox_claim(50)) = 0$$);
select pg_temp.step('the push service answers 410 for Alice''s device', $$select public.push_outbox_done(((select v::jsonb from ids where k = 'claim')->0->>'id')::bigint, true, null,
   array[((select v::jsonb from ids where k = 'claim')->0->'devices'->0->>'id')::bigint])$$);
select pg_temp.ok('the gone device is removed', $$not exists (select 1 from public.push_subscriptions where user_id = 'aaaa0110-0000-0000-0000-000000000001')$$);
select pg_temp.step('a failed send', $$select public.push_outbox_done(((select v::jsonb from ids where k = 'claim')->1->>'id')::bigint, false, 'timeout')$$);
select pg_temp.as_server();
select pg_temp.ok('a failed send is tried again later', $$(select sent_at is null and claimed_at is null and due_at > now() from private.push_outbox where id = ((select v::jsonb from ids where k = 'claim')->1->>'id')::bigint)$$);
select pg_temp.ok('account deletion removes the devices (cascade)', $$(select confdeltype = 'c' from pg_constraint where conrelid = 'public.push_subscriptions'::regclass and contype = 'f')$$);

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
