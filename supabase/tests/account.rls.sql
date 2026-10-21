-- Account (0040): member settings are private and only their choices are writable; the password check; account deletion needs the
-- member's password and the word DELETE, then the server step (service role) leaves a hidden "Deleted member" tombstone, removes
-- the member's rows, keeps the other person's conversation and the payment record, and refuses new messages to the tombstone;
-- export_my_data returns only the member's own data. Run on a fresh database (stub + migrations): psql -f supabase/tests/account.rls.sql
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
  ('aaaa0040-0000-0000-0000-000000000001','ac-a@x', crypt('Pass-A-2026', gen_salt('bf'))),
  ('aaaa0040-0000-0000-0000-000000000002','ac-b@x', crypt('Pass-B-2026', gen_salt('bf'))) on conflict do nothing;
insert into public.profiles (id, name) values ('aaaa0040-0000-0000-0000-000000000001','AC Alice'),('aaaa0040-0000-0000-0000-000000000002','AC Bob') on conflict (id) do update set name = excluded.name;
select pg_temp.ok('a new profile gets its settings row', $$(select count(*) = 2 from public.member_settings where user_id in ('aaaa0040-0000-0000-0000-000000000001','aaaa0040-0000-0000-0000-000000000002'))$$);
-- data of both (server side: preconditions)
insert into public.posts (user_id, body) values ('aaaa0040-0000-0000-0000-000000000001', 'AC alice post'), ('aaaa0040-0000-0000-0000-000000000002', 'AC bob post');
insert into public.comments (post_id, user_id, body) select id, 'aaaa0040-0000-0000-0000-000000000001', 'AC alice comment' from public.posts where body = 'AC bob post';
insert into public.reactions (post_id, user_id, kind) select id, 'aaaa0040-0000-0000-0000-000000000001', 'like' from public.posts where body = 'AC bob post';
insert into public.connections (requester, addressee, status) values ('aaaa0040-0000-0000-0000-000000000001','aaaa0040-0000-0000-0000-000000000002','accepted');
insert into public.messages (sender_id, receiver_id, body) values ('aaaa0040-0000-0000-0000-000000000001','aaaa0040-0000-0000-0000-000000000002','AC hello bob'),('aaaa0040-0000-0000-0000-000000000002','aaaa0040-0000-0000-0000-000000000001','AC hello alice');
insert into public.payment_orders (user_id, product_code, method, amount_cents, status) values ('aaaa0040-0000-0000-0000-000000000001', (select code from public.payment_products order by code limit 1), 'card', 11400, 'paid');

-- ══ settings ════════════════════════════════════════════════════════════════════════════════
select pg_temp.as_user('aaaa0040-0000-0000-0000-000000000001');
select pg_temp.step('Alice changes her e-mail choices', $$update public.member_settings set email_reactions = true, digest = 'daily', show_visits = false where user_id = 'aaaa0040-0000-0000-0000-000000000001'$$);
select pg_temp.ok('the change is kept', $$(select email_reactions and digest = 'daily' and not show_visits from public.member_settings where user_id = 'aaaa0040-0000-0000-0000-000000000001')$$);
select pg_temp.no('Alice cannot set her unsubscribe token', $$update public.member_settings set unsub_token = gen_random_uuid() where user_id = 'aaaa0040-0000-0000-0000-000000000001'$$, '42501');
select pg_temp.no('Alice cannot write the Terms record', $$update public.member_settings set terms_version = 'x' where user_id = 'aaaa0040-0000-0000-0000-000000000001'$$, '42501');
select pg_temp.no('a digest value outside the list is refused', $$update public.member_settings set digest = 'hourly' where user_id = 'aaaa0040-0000-0000-0000-000000000001'$$, '23514');
select pg_temp.ok('Alice cannot read Bob''s settings', $$(select count(*) = 0 from public.member_settings where user_id = 'aaaa0040-0000-0000-0000-000000000002')$$);
select pg_temp.step('Alice tries to change Bob''s settings', $$update public.member_settings set email_messages = false where user_id = 'aaaa0040-0000-0000-0000-000000000002'$$);
select pg_temp.as_server();
select pg_temp.ok('… and nothing changed for Bob', $$(select email_messages from public.member_settings where user_id = 'aaaa0040-0000-0000-0000-000000000002')$$);
select pg_temp.as_anon();
select pg_temp.ok('anon reads no settings', $$(select count(*) = 0 from public.member_settings)$$);
select pg_temp.no('anon cannot check a password', $$select public.verify_my_password('x')$$, '42501');

-- ══ password check ══════════════════════════════════════════════════════════════════════════
select pg_temp.as_user('aaaa0040-0000-0000-0000-000000000001');
select pg_temp.ok('the right password checks out', $$public.verify_my_password('Pass-A-2026')$$);
select pg_temp.ok('a wrong one does not', $$not public.verify_my_password('nope')$$);
select pg_temp.step('four more wrong tries', $$select public.verify_my_password('n1'), public.verify_my_password('n2'), public.verify_my_password('n3'), public.verify_my_password('n4')$$);
select pg_temp.no('the 5th wrong try in 15 minutes blocks the check', $$select public.verify_my_password('Pass-A-2026')$$, 'P0001');
select pg_temp.as_server();
delete from private.password_attempts where user_id = 'aaaa0040-0000-0000-0000-000000000001';

-- ══ export ══════════════════════════════════════════════════════════════════════════════════
select pg_temp.as_user('aaaa0040-0000-0000-0000-000000000001');
select pg_temp.ok('the export has my profile, my post, my comment, my two messages and my payment', $$(select (d->'profile'->>'name') = 'AC Alice' and jsonb_array_length(d->'posts') = 1
  and jsonb_array_length(d->'comments') = 1 and jsonb_array_length(d->'messages') = 2 and jsonb_array_length(d->'payments') = 1 and not (d->'settings' ? 'unsub_token') from (select public.export_my_data() d) x)$$);
select pg_temp.ok('… and nothing of Bob''s posts', $$(select not (public.export_my_data()->'posts')::text like '%AC bob post%')$$);

-- ══ deletion ════════════════════════════════════════════════════════════════════════════════
select pg_temp.no('the server step refuses a deletion its member did not confirm', $$select public.account_anonymise('aaaa0040-0000-0000-0000-000000000001')$$, '42501');
select pg_temp.as_service();
select pg_temp.no('… even for the service role', $$select public.account_anonymise('aaaa0040-0000-0000-0000-000000000001')$$, '42501');
select pg_temp.as_user('aaaa0040-0000-0000-0000-000000000001');
select pg_temp.no('the confirmation word is required', $$select public.account_delete_begin('Pass-A-2026', 'yes')$$, '22023');
select pg_temp.ok('the password is required (a wrong one is answered, not raised)', $$(public.account_delete_begin('wrong', 'DELETE')->>'error') = 'Your password is not correct'$$);
select pg_temp.as_server();
select pg_temp.ok('… and the wrong attempt stays recorded (0047: the lock cannot be bypassed)', $$(select count(*) >= 1 from private.password_attempts where user_id = 'aaaa0040-0000-0000-0000-000000000001')$$);
delete from private.password_attempts where user_id = 'aaaa0040-0000-0000-0000-000000000001';
select pg_temp.as_user('aaaa0040-0000-0000-0000-000000000001');
select pg_temp.ok('with both, the deletion starts and lists the files', $$(public.account_delete_begin('Pass-A-2026', 'DELETE') ? 'files')$$);
select pg_temp.as_user('aaaa0040-0000-0000-0000-000000000002');
select pg_temp.no('Bob cannot run the server step for Alice', $$select public.account_anonymise('aaaa0040-0000-0000-0000-000000000001')$$, '42501');
select pg_temp.as_service();
select pg_temp.step('the server step', $$select public.account_anonymise('aaaa0040-0000-0000-0000-000000000001')$$);
select pg_temp.as_server();
select pg_temp.ok('the profile is a tombstone', $$(select name = 'Deleted member' and account_type = 'deleted' and headline is null and bio is null and avatar_url is null from public.profiles where id = 'aaaa0040-0000-0000-0000-000000000001')$$);
select pg_temp.ok('her post, comment, reaction, connection and settings are gone', $$(select (select count(*) from public.posts where user_id = 'aaaa0040-0000-0000-0000-000000000001') + (select count(*) from public.comments where user_id = 'aaaa0040-0000-0000-0000-000000000001')
  + (select count(*) from public.reactions where user_id = 'aaaa0040-0000-0000-0000-000000000001') + (select count(*) from public.connections where requester = 'aaaa0040-0000-0000-0000-000000000001') + (select count(*) from public.member_settings where user_id = 'aaaa0040-0000-0000-0000-000000000001') = 0)$$);
select pg_temp.ok('Bob''s post no longer counts her like and comment', $$(select like_count = 0 and comment_count = 0 from public.posts where body = 'AC bob post')$$);
select pg_temp.ok('the messages stay for Bob', $$(select count(*) = 2 from public.messages where sender_id = 'aaaa0040-0000-0000-0000-000000000001' or receiver_id = 'aaaa0040-0000-0000-0000-000000000001')$$);
select pg_temp.ok('the payment order stays, and the buyer is in the billing archive', $$(select count(*) = 1 from public.payment_orders where user_id = 'aaaa0040-0000-0000-0000-000000000001') and (select buyer_name = 'AC Alice' from private.billing_archive where user_id = 'aaaa0040-0000-0000-0000-000000000001')$$);
select pg_temp.as_user('aaaa0040-0000-0000-0000-000000000002');
select pg_temp.ok('Bob cannot read the tombstone', $$(select count(*) = 0 from public.profiles where id = 'aaaa0040-0000-0000-0000-000000000001')$$);
select pg_temp.ok('Bob''s conversation list says "Deleted member"', $$(select name = 'Deleted member' from public.my_conversations(10) where partner = 'aaaa0040-0000-0000-0000-000000000001')$$);
select pg_temp.no('Bob cannot write to a deleted member', $$insert into public.messages (sender_id, receiver_id, body) values ('aaaa0040-0000-0000-0000-000000000002','aaaa0040-0000-0000-0000-000000000001','AC are you there')$$, '42501');
select pg_temp.no('a member cannot make a profile a tombstone', $$update public.profiles set account_type = 'deleted' where id = 'aaaa0040-0000-0000-0000-000000000002'$$, '42501');
select pg_temp.as_anon();
select pg_temp.ok('anon cannot read the tombstone either', $$(select count(*) = 0 from public.profiles where id = 'aaaa0040-0000-0000-0000-000000000001')$$);

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
