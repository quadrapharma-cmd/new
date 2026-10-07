-- Security core tests for 0020 (code review 2026-10). Each check prints PASS/FAIL. Runs as real API roles with a JWT subject,
-- and as anon. Every item has a negative test (the attack must be refused or neutralised) and a positive one (the flow still works).
\set QUIET on
set client_min_messages = warning;
begin;
-- people: profiles are created by handle_new_user (F-94); ADM is made admin by the server (SQL), as in production
insert into auth.users (id, email) values ('a0000000-0000-0000-0000-00000000000a','alice@x'),('b0000000-0000-0000-0000-00000000000b','bob@x'),
  ('c0000000-0000-0000-0000-00000000000c','carol@x'),('d0000000-0000-0000-0000-00000000000d','admin@x') on conflict do nothing;
update public.profiles set role='admin' where id='d0000000-0000-0000-0000-00000000000d';
update public.profiles set company='Acme Pharma' where id='a0000000-0000-0000-0000-00000000000a';
update public.profiles set experience='[{"title":"QA","company":"Acme Pharma"}]'::jsonb where id='b0000000-0000-0000-0000-00000000000b';
create temp table r (n serial, name text, ok boolean);
grant all on r to anon, authenticated; grant all on r_n_seq to anon, authenticated;
create or replace function pg_temp.as_user(u text) returns void language plpgsql as $$ begin perform set_config('request.jwt.claim.sub', u, true); perform set_config('role','authenticated', true); end $$;
create or replace function pg_temp.as_anon() returns void language plpgsql as $$ begin perform set_config('request.jwt.claim.sub', '', true); perform set_config('role','anon', true); end $$;
create or replace function pg_temp.refused(q text) returns boolean language plpgsql as $$ begin execute q; return false; exception when others then return true; end $$;
create or replace function pg_temp.err(q text) returns text language plpgsql as $$ begin execute q; return null; exception when others then return sqlstate; end $$;
\set A '''a0000000-0000-0000-0000-00000000000a'''
\set B '''b0000000-0000-0000-0000-00000000000b'''
\set C '''c0000000-0000-0000-0000-00000000000c'''
\set ADM '''d0000000-0000-0000-0000-00000000000d'''

-- ── F-94 handle_new_user ──
insert into auth.users (id, email, raw_user_meta_data) values ('e0000000-0000-0000-0000-00000000000e', null, '{}');
insert into r(name,ok) select 'F-94 a sign-up without email or name still gets a profile ("Member")', (select name='Member' from public.profiles where id='e0000000-0000-0000-0000-00000000000e');
insert into auth.users (id, email, raw_user_meta_data) values ('f0000000-0000-0000-0000-00000000000f', 'frank@x', '{"name":"   "}');
insert into r(name,ok) select 'F-94 an empty name falls back to the email', (select name='frank' from public.profiles where id='f0000000-0000-0000-0000-00000000000f');
insert into r(name,ok) select 'F-94 handle_new_user has a pinned search_path', exists(select 1 from pg_proc where proname='handle_new_user' and prosecdef and array_to_string(proconfig,',') like '%search_path%');

-- ── F-01 profiles: no self-promotion ──
select pg_temp.as_user(:A);
insert into r(name,ok) select 'F-01 a member cannot make themself admin (42501)', pg_temp.err($$update public.profiles set role='admin' where id='a0000000-0000-0000-0000-00000000000a'$$)='42501';
insert into r(name,ok) select 'F-01 a member cannot self-verify', pg_temp.err($$update public.profiles set verified=true where id='a0000000-0000-0000-0000-00000000000a'$$)='42501';
insert into r(name,ok) select 'F-01 a member cannot change their account type', pg_temp.err($$update public.profiles set account_type='admin' where id='a0000000-0000-0000-0000-00000000000a'$$)='42501';
insert into r(name,ok) select 'F-01 still not an admin afterwards', not public.is_platform_admin() and (select role='user' and not verified from public.profiles where id='a0000000-0000-0000-0000-00000000000a');
update public.profiles set followers_count=999999, profile_views=999999, created_at='2001-01-01', headline='QA lead' where id='a0000000-0000-0000-0000-00000000000a';
insert into r(name,ok) select 'F-01 vanity counters and created_at are kept by the server, the headline edit works', (select followers_count=0 and profile_views=0 and created_at > now() - interval '1 day' and headline='QA lead' from public.profiles where id='a0000000-0000-0000-0000-00000000000a');
update public.profiles set headline='HACKED' where id='b0000000-0000-0000-0000-00000000000b';
insert into r(name,ok) select 'F-01 another person''s profile cannot be edited (0 rows)', (select headline is distinct from 'HACKED' from public.profiles where id='b0000000-0000-0000-0000-00000000000b');
select pg_temp.as_user(:ADM);
update public.profiles set verified=true where id='d0000000-0000-0000-0000-00000000000d';
insert into r(name,ok) select 'F-01 Drugbox admins keep their rights', (select verified from public.profiles where id='d0000000-0000-0000-0000-00000000000d') and public.is_platform_admin();
reset role;
update public.profiles set verified=true where id='b0000000-0000-0000-0000-00000000000b';
insert into r(name,ok) select 'F-01 the server (SQL / service role) still sets roles and badges', (select verified from public.profiles where id='b0000000-0000-0000-0000-00000000000b');

-- ── F-177 grants: no direct writes where only functions write; nothing for anon ──
select pg_temp.as_user(:A);
insert into r(name,ok) select 'F-177 a member cannot insert a profile row', pg_temp.err($$insert into public.profiles (id, name) values ('a0000000-0000-0000-0000-00000000000a','x')$$)='42501';
insert into r(name,ok) select 'F-177 a member cannot delete a profile row', pg_temp.err($$delete from public.profiles where id='a0000000-0000-0000-0000-00000000000a'$$)='42501';
insert into r(name,ok) select 'F-177 payment orders take no direct writes', pg_temp.err($$insert into public.payment_orders (user_id, product_code, method, amount_cents, status) values ('a0000000-0000-0000-0000-00000000000a','boost','card',1,'paid')$$)='42501'
  and not has_table_privilege('authenticated','public.payment_orders','update') and not has_table_privilege('authenticated','public.payment_products','insert');
insert into r(name,ok) select 'F-177 messages cannot be deleted', not has_table_privilege('authenticated','public.messages','delete');
insert into r(name,ok) select 'F-177 no API role can TRUNCATE (it skips row-level security)', not exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind='r' and (has_table_privilege('authenticated', c.oid, 'truncate') or has_table_privilege('anon', c.oid, 'truncate')));
insert into r(name,ok) select 'F-177 members hold no write privilege that no policy allows (tables of 0001-0019)', not exists(
  select 1 from (values ('payment_orders','INSERT'),('payment_orders','UPDATE'),('payment_orders','DELETE'),('payment_products','INSERT'),('payment_products','DELETE'),
    ('profiles','INSERT'),('profiles','DELETE'),('messages','DELETE'),('notifications','INSERT'),('comments','UPDATE'),('post_media','UPDATE'),('company_followers','UPDATE'),
    ('course_enrollments','UPDATE'),('work_references','UPDATE'),('verification_requests','DELETE'),('company_reports','DELETE')) v(t, c)
  where has_table_privilege('authenticated', 'public.' || v.t, v.c)
    and not exists(select 1 from pg_policies p where p.schemaname='public' and p.tablename=v.t and p.cmd in (v.c, 'ALL')));
select pg_temp.as_anon();
insert into r(name,ok) select 'F-177 anon cannot insert a post', pg_temp.err($$insert into public.posts (user_id, body) values ('a0000000-0000-0000-0000-00000000000a','x')$$)='42501';
insert into r(name,ok) select 'F-177 anon has no write or sequence privilege on any public table', not exists(select 1 from information_schema.table_privileges where grantee='anon' and table_schema='public' and privilege_type in ('INSERT','UPDATE','DELETE'))
  and not exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and (case when c.relkind='S' then has_sequence_privilege('anon', c.oid, 'usage') else false end));
reset role;

-- ── F-03 paid placements come only from a confirmed payment ──
select pg_temp.as_user(:A);
insert into public.products (user_id, name, category, type, boosted_until, featured_until) values ('a0000000-0000-0000-0000-00000000000a','Metformin HCl','api','supply','2099-01-01','2099-01-01');
insert into r(name,ok) select 'F-03 boosted/featured sent with a new listing are dropped', (select boosted_until is null and featured_until is null from public.products where name='Metformin HCl');
update public.products set boosted_until='2099-01-01', featured_until='2099-01-01', price='US$ 5' where name='Metformin HCl';
insert into r(name,ok) select 'F-03 the owner cannot boost by hand; the price edit works', (select boosted_until is null and featured_until is null and price='US$ 5' from public.products where name='Metformin HCl');
select * into temp t_boost from public.create_order('boost','card',null,(select id from public.products where name='Metformin HCl'));
reset role;
select public.set_order_provider_ref((select id from t_boost), 'pi-1', 'po-1');
create temp table t_paid as select public.confirm_payment('paymob','po-1','pm-1',(select amount_cents from t_boost),'EGP','{}'::jsonb) as s;
insert into r(name,ok) select 'F-03 a confirmed payment (server) activates the boost', (select s='paid' from t_paid)
  and (select boosted_until > now() + interval '6 days' from public.products where name='Metformin HCl');
select pg_temp.as_user(:A);
select * into temp t_feat from public.create_order('featured','instapay',null,(select id from public.products where name='Metformin HCl'));
select public.submit_instapay((select id from t_feat),'IPN-1',null);
update public.products set boosted_until=null where name='Metformin HCl';
insert into r(name,ok) select 'F-03 the owner cannot clear or change an active boost either', (select boosted_until > now() from public.products where name='Metformin HCl');
select pg_temp.as_user(:ADM);
update public.products set featured_until='2099-01-01' where name='Metformin HCl';
insert into r(name,ok) select 'F-03 not even a Drugbox admin sets a placement by hand (only activate_order does)', (select featured_until is null from public.products where name='Metformin HCl');
select public.review_instapay((select id from t_feat), true);
insert into r(name,ok) select 'F-03 Drugbox confirming an InstaPay transfer activates the featured placement', (select featured_until > now() + interval '29 days' from public.products where name='Metformin HCl');
reset role;

-- ── F-09 / F-164 server-managed columns on posts, comments, messages ──
select pg_temp.as_user(:A);
insert into public.posts (id, user_id, body, created_at, pinned, like_count, comment_count, view_count, share_count) values (9000000000,'a0000000-0000-0000-0000-00000000000a','forged post','2099-01-01',true,99999,5000,1000000,777);
insert into r(name,ok) select 'F-09 a post cannot be dated 2099, pinned or seeded with counters; its id comes from the sequence', (select id < 1000000 and created_at between now() - interval '1 minute' and now() + interval '1 minute' and not pinned and like_count=0 and comment_count=0 and view_count=0 and share_count=0 from public.posts where body='forged post');
insert into public.posts (user_id, body, created_at) values ('a0000000-0000-0000-0000-00000000000a','null post', null);
insert into r(name,ok) select 'F-09 created_at is never null (the feed cursor stays valid)', (select created_at is not null from public.posts where body='null post');
insert into r(name,ok) select 'F-102 a comment must belong to a post', pg_temp.refused($$insert into public.comments (post_id, user_id, body) values (null,'a0000000-0000-0000-0000-00000000000a','orphan')$$);
insert into public.comments (post_id, user_id, body, created_at) select id,'a0000000-0000-0000-0000-00000000000a','late comment','2099-01-01' from public.posts where body='forged post';
insert into r(name,ok) select 'F-09 a comment cannot be dated in the future; the counter still moves', (select created_at < now() + interval '1 minute' from public.comments where body='late comment') and (select comment_count=1 from public.posts where body='forged post');
insert into public.messages (id, sender_id, receiver_id, body, created_at, read_at) values (9223372036854775000,'a0000000-0000-0000-0000-00000000000a','b0000000-0000-0000-0000-00000000000b','pinned forever','2099-12-31',now());
insert into r(name,ok) select 'F-09 a message cannot carry a huge id, a 2099 date or a preset read receipt', (select id < 1000000 and created_at < now() + interval '1 minute' and read_at is null from public.messages where body='pinned forever');
reset role;
insert into r(name,ok) select 'F-09 the receiver''s unread counter is incremented', (select unread=1 from public.conversation_heads where owner='b0000000-0000-0000-0000-00000000000b' and partner='a0000000-0000-0000-0000-00000000000a');
select pg_temp.as_user(:A);
insert into public.messages (id, sender_id, receiver_id, body) values ((select last_value + 1 from public.messages_id_seq),'a0000000-0000-0000-0000-00000000000a','b0000000-0000-0000-0000-00000000000b','id theft');
select pg_temp.as_user(:C);
insert into r(name,ok) select 'F-09 the next sender is not hit by a stolen id (no duplicate key)', not pg_temp.refused($$insert into public.messages (sender_id, receiver_id, body) values ('c0000000-0000-0000-0000-00000000000c','b0000000-0000-0000-0000-00000000000b','hello B')$$);
select pg_temp.as_user(:B);
insert into r(name,ok) select 'F-09 the receiver cannot change a message''s id', pg_temp.err($$update public.messages set id=900000 where body='pinned forever'$$)='42501';
update public.messages set read_at=now() where sender_id='a0000000-0000-0000-0000-00000000000a' and receiver_id='b0000000-0000-0000-0000-00000000000b' and read_at is null;
insert into r(name,ok) select 'F-09 read receipts by the receiver still work (0004)', (select count(*)=0 from public.messages where receiver_id='b0000000-0000-0000-0000-00000000000b' and sender_id='a0000000-0000-0000-0000-00000000000a' and read_at is null)
  and (select unread=0 from public.conversation_heads where owner='b0000000-0000-0000-0000-00000000000b' and partner='a0000000-0000-0000-0000-00000000000a');
insert into r(name,ok) select 'F-09 the sender cannot mark their own message read (0 rows)', (select count(*)=0 from (select 1 from public.messages where body='hello B' and read_at is not null) x);
-- posts: author edits body only; Drugbox pins
select pg_temp.as_user(:A);
update public.posts set body='edited post', pinned=true, like_count=50, user_id='b0000000-0000-0000-0000-00000000000b' where body='forged post';
insert into r(name,ok) select 'F-164 the author edits the text; pin, counters and author stay', (select pinned=false and like_count=0 and user_id='a0000000-0000-0000-0000-00000000000a' from public.posts where body='edited post');
update public.posts set body='HACKED' where user_id='b0000000-0000-0000-0000-00000000000b';
select pg_temp.as_user(:ADM);
update public.posts set pinned=true, body='admin rewrote it' where body='edited post';
insert into r(name,ok) select 'F-164 Drugbox pins a post but cannot rewrite it', (select pinned and body='edited post' from public.posts where user_id='a0000000-0000-0000-0000-00000000000a' and pinned);
select pg_temp.as_user(:B);
insert into r(name,ok) select 'F-164 a person cannot forge a notification for themself', pg_temp.refused($$insert into public.notifications (user_id, type, from_user, message) values ('b0000000-0000-0000-0000-00000000000b','connection_accepted','a0000000-0000-0000-0000-00000000000a','<img src=x onerror=alert(1)>')$$);
reset role;
insert into public.notifications (user_id, type, message) values ('b0000000-0000-0000-0000-00000000000b','payment','real notice');
select pg_temp.as_user(:B);
update public.notifications set read=true, message='rewritten', type='deal' where message='real notice' or message='rewritten';
insert into r(name,ok) select 'F-164 a notification can be marked read and nothing else', (select read and type='payment' from public.notifications where message='real notice' and user_id='b0000000-0000-0000-0000-00000000000b');
-- enquiries, jobs, groups
select pg_temp.as_user(:A);
insert into public.enquiries (id, user_id, type, category, title, body, created_at) values ('ENQ0001','a0000000-0000-0000-0000-00000000000a','demand','api','Need API','Metformin 2 MT','2099-01-01');
insert into r(name,ok) select 'F-164 a buy request id is server-generated (F-101: no dead reply_count column)', (select count(*)=1 from public.enquiries where title='Need API' and user_id='a0000000-0000-0000-0000-00000000000a' and id <> 'ENQ0001' and id like 'E%' and created_at < now() + interval '1 minute')
  and not exists(select 1 from information_schema.columns where table_schema='public' and table_name='enquiries' and column_name='reply_count');
insert into public.jobs (user_id, title, category, applicant_count) values ('a0000000-0000-0000-0000-00000000000a','QA Pharmacist','qaqc',8888);
insert into r(name,ok) select 'F-09 a job cannot be seeded with applicants', (select applicant_count=0 from public.jobs where title='QA Pharmacist');
insert into public.groups (name, type, created_by, member_count) values ('GMP circle','public','a0000000-0000-0000-0000-00000000000a',123456);
update public.groups set member_count=123456 where name='GMP circle';
insert into r(name,ok) select 'F-09 a group''s member count is the real one (creator = 1)', (select member_count=1 from public.groups where name='GMP circle');
-- work references: the candidate's reply cannot be pre-filled
-- (later migrations may refuse this author altogether — either way no forged reply is ever stored)
select pg_temp.err($$insert into public.work_references (author, candidate, kind, role_title, from_month, to_month, body, reply, replied_at, created_at)
  values ('a0000000-0000-0000-0000-00000000000a','b0000000-0000-0000-0000-00000000000b','honor','QA officer','2024-01-01','2025-01-01','Reliable, precise and a pleasure to work with over the whole year.','I admit it, sorry.',now(),'2019-01-01')$$);
reset role;
insert into r(name,ok) select 'F-09 a reference never carries a reply written by its author, nor a back-dated created_at', not exists(select 1 from public.work_references where author='a0000000-0000-0000-0000-00000000000a' and (reply='I admit it, sorry.' or created_at < now() - interval '1 minute'));
select pg_temp.as_user(:A);

-- ── F-95 / F-96 companies ──
insert into public.companies (name, type, slug, follower_count, source, created_at, registry, status, plan) values ('Alice Labs','Manufacturer','alice-labs',250000,'public_list','2001-01-01','CR-FAKE','verified','vip');
insert into r(name,ok) select 'F-95 a new company carries no fake followers, provenance, date or registry (and starts pending)', (select follower_count=0 and source='company' and created_at > now() - interval '1 minute' and registry is null and status='pending' and plan='free' from public.companies where slug='alice-labs');
update public.companies set follower_count=250000, source='public_list', created_at='2001-01-01', registry='CR-FAKE', tagline='Quality first' where slug='alice-labs';
insert into r(name,ok) select 'F-95 the owner''s page edit works; counters, provenance and registry are kept by the server', (select follower_count=0 and source='company' and registry is null and tagline='Quality first' from public.companies where slug='alice-labs');
insert into r(name,ok) select 'F-95 the public address (slug) cannot be changed by the team', pg_temp.err($$update public.companies set slug='pfizer-egypt' where slug='alice-labs'$$)='42501';
select pg_temp.as_user(:ADM);
insert into public.companies (owner_id, name, type) values ('d0000000-0000-0000-0000-00000000000d','Admin Made Co','Supplier');
insert into r(name,ok) select 'F-96 a company created by a Drugbox admin starts pending too', (select status='pending' from public.companies where name='Admin Made Co');
reset role;
insert into public.companies (owner_id, name, type) values ('d0000000-0000-0000-0000-00000000000d','Imported Co','Supplier');
insert into r(name,ok) select 'F-96 the column default is pending (imports must say unclaimed explicitly)', (select status='pending' from public.companies where name='Imported Co');
-- registry still arrives through verification
select pg_temp.as_user(:A);
insert into public.verification_requests (company_id, submitted_by, registry) select id,'a0000000-0000-0000-0000-00000000000a','123456' from public.companies where slug='alice-labs';
select pg_temp.as_user(:ADM);
update public.verification_requests set status='approved' where registry='123456';
insert into r(name,ok) select 'F-95 approval by Drugbox still verifies the company and sets its registry', (select status='verified' and registry='123456' from public.companies where slug='alice-labs');

-- ── F-08 / F-103 connections ──
select pg_temp.as_user(:A);
insert into public.connections (requester, addressee, status) values ('a0000000-0000-0000-0000-00000000000a','b0000000-0000-0000-0000-00000000000b','accepted');
insert into r(name,ok) select 'F-08 a request inserted as "accepted" is stored pending (consent still needed, nobody told of an acceptance)', (select status='pending' from public.connections where requester='a0000000-0000-0000-0000-00000000000a' and addressee='b0000000-0000-0000-0000-00000000000b')
  and not exists(select 1 from public.notifications where type='connection_accepted');
update public.connections set status='accepted' where requester='a0000000-0000-0000-0000-00000000000a' and addressee='b0000000-0000-0000-0000-00000000000b';
insert into r(name,ok) select 'F-08 the requester cannot accept their own request (0 rows)', (select status='pending' from public.connections where requester='a0000000-0000-0000-0000-00000000000a' and addressee='b0000000-0000-0000-0000-00000000000b');
select pg_temp.as_user(:B);
insert into r(name,ok) select 'F-08 the addressee is notified of the request', exists(select 1 from public.notifications where user_id='b0000000-0000-0000-0000-00000000000b' and type='connection_request');
insert into r(name,ok) select 'F-08 the addressee cannot rewrite the requester (42501)', pg_temp.err($$update public.connections set requester='c0000000-0000-0000-0000-00000000000c', status='accepted' where addressee='b0000000-0000-0000-0000-00000000000b'$$)='42501';
update public.connections set status='accepted' where requester='a0000000-0000-0000-0000-00000000000a' and addressee='b0000000-0000-0000-0000-00000000000b' and status='pending';
insert into r(name,ok) select 'F-08 the addressee accepts (the interface''s own update)', (select status='accepted' from public.connections where requester='a0000000-0000-0000-0000-00000000000a' and addressee='b0000000-0000-0000-0000-00000000000b');
update public.connections set status='rejected' where requester='a0000000-0000-0000-0000-00000000000a' and addressee='b0000000-0000-0000-0000-00000000000b';
insert into r(name,ok) select 'F-08 an answered request cannot be answered again', (select status='accepted' from public.connections where requester='a0000000-0000-0000-0000-00000000000a' and addressee='b0000000-0000-0000-0000-00000000000b');
insert into public.connections (requester, addressee, status) values ('b0000000-0000-0000-0000-00000000000b','a0000000-0000-0000-0000-00000000000a','pending');
insert into r(name,ok) select 'F-103 the reverse pair cannot be added again (one row per pair, no double count)', (select count(*)=1 from public.connections where 'a0000000-0000-0000-0000-00000000000a' in (requester, addressee) and 'b0000000-0000-0000-0000-00000000000b' in (requester, addressee));
select pg_temp.as_user(:A);
insert into r(name,ok) select 'F-101 followers_count = accepted connections, for both people', (select followers_count=1 from public.profiles where id='a0000000-0000-0000-0000-00000000000a') and (select followers_count=1 from public.profiles where id='b0000000-0000-0000-0000-00000000000b');
insert into r(name,ok) select 'F-101 my_network_stats counts the pair once', (public.my_network_stats()->>'connections')::int = 1;
-- crossing requests: C asks A while A already asked C → connected, no second row
insert into public.connections (requester, addressee, status) values ('a0000000-0000-0000-0000-00000000000a','c0000000-0000-0000-0000-00000000000c','pending');
select pg_temp.as_user(:C);
insert into public.connections (requester, addressee, status) values ('c0000000-0000-0000-0000-00000000000c','a0000000-0000-0000-0000-00000000000a','pending');
insert into r(name,ok) select 'F-103 a request that crosses a pending one from the other side accepts it', (select count(*)=1 and bool_and(status='accepted') from public.connections where 'a0000000-0000-0000-0000-00000000000a' in (requester, addressee) and 'c0000000-0000-0000-0000-00000000000c' in (requester, addressee));
delete from public.connections where requester='c0000000-0000-0000-0000-00000000000c' or addressee='c0000000-0000-0000-0000-00000000000c';
insert into r(name,ok) select 'F-101 the count follows a removed connection', (select followers_count=0 from public.profiles where id='c0000000-0000-0000-0000-00000000000c') and (select followers_count=1 from public.profiles where id='a0000000-0000-0000-0000-00000000000a');
reset role;
insert into r(name,ok) select 'F-103 even the server cannot create the reverse duplicate', pg_temp.err($$insert into public.connections (requester, addressee, status) values ('b0000000-0000-0000-0000-00000000000b','a0000000-0000-0000-0000-00000000000a','accepted')$$)='23505';

-- ── F-104 counters: signed-in, once per person per day ──
select pg_temp.as_anon();
insert into r(name,ok) select 'F-104 anon cannot bump view, share or profile counters', pg_temp.err($$select public.increment_post_views(array(select id from public.posts))$$)='42501' and pg_temp.err($$select public.increment_post_share(1)$$)='42501' and pg_temp.err($$select public.increment_profile_view('b0000000-0000-0000-0000-00000000000b')$$)='42501';
select pg_temp.as_user(:A);
select public.increment_post_views(array(select id from public.posts where body='null post')); select public.increment_post_views(array(select id from public.posts where body='null post')); select public.increment_post_views(array(select id from public.posts where body='null post'));
select public.increment_post_share((select id from public.posts where body='null post')); select public.increment_post_share((select id from public.posts where body='null post'));
select public.increment_profile_view('b0000000-0000-0000-0000-00000000000b'); select public.increment_profile_view('b0000000-0000-0000-0000-00000000000b'); select public.increment_profile_view('a0000000-0000-0000-0000-00000000000a');
select pg_temp.as_user(:C);
select public.increment_post_views(array(select id from public.posts where body='null post')); select public.increment_profile_view('b0000000-0000-0000-0000-00000000000b');
insert into r(name,ok) select 'F-104 three views by one person count once; two people count twice', (select view_count=2 from public.posts where body='null post');
insert into r(name,ok) select 'F-104 shares count once per person per day', (select share_count=1 from public.posts where body='null post');
insert into r(name,ok) select 'F-104 profile views: once per visitor per day, never your own', (select profile_views=2 from public.profiles where id='b0000000-0000-0000-0000-00000000000b') and (select profile_views=0 from public.profiles where id='a0000000-0000-0000-0000-00000000000a');
insert into r(name,ok) select 'F-104 the view log is not writable from the API', not has_table_privilege('authenticated','public.post_view_log','insert') and not has_table_privilege('authenticated','public.profile_view_log','delete');

-- ── F-12 jobs_interacted is not an oracle ──
select pg_temp.as_anon();
insert into r(name,ok) select 'F-12 anon cannot call jobs_interacted', pg_temp.err($$select public.jobs_interacted('a0000000-0000-0000-0000-00000000000a','b0000000-0000-0000-0000-00000000000b')$$)='42501';
select pg_temp.as_user(:C);
insert into r(name,ok) select 'F-12 a third person cannot learn whether A and B talked', not public.jobs_interacted('a0000000-0000-0000-0000-00000000000a','b0000000-0000-0000-0000-00000000000b');
insert into r(name,ok) select 'F-12 ...and cannot review B without an interaction', pg_temp.refused($$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1, c2, c3, c4, body) values ('c0000000-0000-0000-0000-00000000000c','a0000000-0000-0000-0000-00000000000a','employer',1,1,1,1,'I never dealt with them but I dislike them a lot.')$$);
select pg_temp.as_user(:A);
insert into r(name,ok) select 'F-12 a party still gets a true answer', public.jobs_interacted('a0000000-0000-0000-0000-00000000000a','b0000000-0000-0000-0000-00000000000b');
-- (while the review policy is the one that calls jobs_interacted, as in 0012; a later migration may replace it)
select pg_temp.err($$insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1, c2, c3, c4, body) values ('a0000000-0000-0000-0000-00000000000a','b0000000-0000-0000-0000-00000000000b','employer',5,4,5,4,'Fast, transparent hiring; the salary range was shared up front.')$$);
insert into r(name,ok) select 'F-12 a review after a real interaction still works (policy uses jobs_interacted)', (select count(*)=1 from public.job_reviews where reviewer='a0000000-0000-0000-0000-00000000000a')
  or not exists(select 1 from pg_policies where tablename='job_reviews' and cmd='INSERT' and with_check ~ 'jobs_interacted');

-- ── F-165 get_ratings aggregates the requested people only ──
insert into public.messages (sender_id, receiver_id, body) values ('a0000000-0000-0000-0000-00000000000a','c0000000-0000-0000-0000-00000000000c','hi C');
reset role;
delete from public.job_reviews;
insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1, c2, c3, c4, body) values
  ('a0000000-0000-0000-0000-00000000000a','b0000000-0000-0000-0000-00000000000b','employer',5,4,5,4,'Fast, transparent hiring; the salary range was shared up front.'),
  ('a0000000-0000-0000-0000-00000000000a','c0000000-0000-0000-0000-00000000000c','employer',2,2,2,2,'Slow process and no feedback after the interview, sadly.');
select pg_temp.as_user(:A);
insert into r(name,ok) select 'F-165 get_ratings with ids returns those people only, ranked among them', (select count(*)=1 and max(rank)=1 and max(n)=1 from public.get_ratings('employer', array['c0000000-0000-0000-0000-00000000000c'::uuid])) and (select count(*)=2 from public.get_ratings('employer'));

-- ── F-26 / F-169 nothing personal before sign-in ──
reset role;
insert into storage.buckets (id, name, public) values ('videos','videos',true) on conflict (id) do nothing;
insert into storage.objects (bucket_id, name, owner) values ('videos','people/a0000000-0000-0000-0000-00000000000a/intro.webm','a0000000-0000-0000-0000-00000000000a');
insert into public.deals (type, title, from_company_id, from_user, to_company_id, status, lines)
  select 'group', 'Metformin buying group', a.id, 'a0000000-0000-0000-0000-00000000000a', b.id, 'open', '{"price":"US$ 3","target":100}'::jsonb
  from public.companies a, public.companies b where a.slug='alice-labs' and b.name='Admin Made Co';
select pg_temp.as_anon();
insert into r(name,ok) select 'F-26 anon reads no profile (no phone, no role)', (select count(*)=0 from public.profiles);
insert into r(name,ok) select 'F-26 anon reads no company (no registry, no contact), not even through the directory RPC', (select count(*)=0 from public.companies) and pg_temp.err($$select public.directory_companies(10)$$)='42501';
insert into r(name,ok) select 'F-26 anon sees no buying group', (select count(*)=0 from public.deals);
insert into r(name,ok) select 'F-26 anon finds no open-to-work candidate', pg_temp.err($$select * from public.open_candidates(10)$$)='42501';
insert into r(name,ok) select 'F-26 the login page still has what it needs (settings, ticker, prices)', (select count(*)>0 from public.settings) and (select count(*)>0 from public.ticker_items) and (select count(*)>0 from public.payment_products);
insert into r(name,ok) select 'F-169 anon cannot list the objects of a public bucket', (select count(*)=0 from storage.objects where bucket_id='videos');
select pg_temp.as_user(:C);
insert into r(name,ok) select 'F-26 members read people and companies', (select count(*)>0 from public.profiles) and (select count(*)>0 from public.companies) and (select json_array_length(public.directory_companies_page(10))>0);
insert into r(name,ok) select 'F-26 members still see the open buying groups', (select count(*)=1 from public.deals where type='group' and title='Metformin buying group');
insert into r(name,ok) select 'F-169 members still see bucket objects (replace/remove keep working)', (select count(*)=1 from storage.objects where bucket_id='videos');

-- ── F-27 / F-12 function privileges ──
select pg_temp.as_anon();
-- pgcrypto sits in `extensions` (as on Supabase; the API exposes only public), so it is no RPC: absent (42883) or refused (42501)
insert into r(name,ok) select 'F-27 anon cannot run pgcrypto / pg_trgm functions', pg_temp.err($$select public.gen_salt('bf')$$) in ('42501','42883') and pg_temp.err($$select show_trgm('hello')$$)='42501' and pg_temp.err($$select public.armor('x'::bytea)$$) in ('42501','42883');
insert into r(name,ok) select 'F-27 anon cannot call the app''s RPCs', pg_temp.err($$select public.get_reviews_many(array['a0000000-0000-0000-0000-00000000000a'::uuid],'employer')$$)='42501'
  and pg_temp.err($$select public.company_track_record(1)$$)='42501' and pg_temp.err($$select public.deal_receiver(1,'quote')$$)='42501' and pg_temp.err($$select public.moderate_reference(1,'published')$$)='42501';
insert into r(name,ok) select 'F-27 anon executes no public function except the helpers row policies evaluate', not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='public' and has_function_privilege('anon', p.oid, 'execute') and p.prorettype <> 'trigger'::regtype   -- trigger functions cannot be called
    and not exists(select 1 from pg_policies q where coalesce(q.qual,'')||' '||coalesce(q.with_check,'') ~ ('\m' || p.proname || '\('))) ;
select pg_temp.as_user(:A);
insert into r(name,ok) select 'F-27 members cannot run pgcrypto / pg_trgm either', pg_temp.err($$select public.gen_salt('bf')$$) in ('42501','42883') and pg_temp.err($$select public.crypt('a','b')$$) in ('42501','42883') and pg_temp.err($$select show_limit()$$)='42501'
  and not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace join pg_depend d on d.objid=p.oid and d.classid='pg_proc'::regclass and d.deptype='e'
                 where n.nspname='public' and (has_function_privilege('anon', p.oid, 'execute') or has_function_privilege('authenticated', p.oid, 'execute')));
insert into r(name,ok) select 'F-27 deal_receiver is internal to the deals engine', pg_temp.err($$select public.deal_receiver(1,'quote')$$)='42501';
insert into r(name,ok) select 'F-27 the RPCs the app calls still run for members', (select json_typeof(public.directory_companies_page(5))='array') and (select count(*)>=0 from public.get_reviews_many(array['b0000000-0000-0000-0000-00000000000b'::uuid],'employer')) and (select count(*)>=0 from public.my_interactions()) and public.company_track_record(1) is not null;
reset role;
select pg_temp.as_user(:C);
set local enable_seqscan = off;
insert into r(name,ok) select 'F-27 ILIKE search through the pg_trgm index works for a member', pg_temp.err($$select count(*) from public.companies where name ilike '%lice La%'$$) is null
  and (select count(*)=1 from public.companies where name ilike '%lice La%');
reset enable_seqscan;
-- every table answers anon and members with rows or nothing — never an error (policy helpers stay executable)
select pg_temp.as_anon();
insert into r(name,ok) select 'F-26 anon can query every table and storage.objects without an error (results may be empty)', coalesce((select string_agg(c.oid::regclass::text, ',') from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where ((n.nspname='public' and c.relkind in ('r','v')) or c.oid='storage.objects'::regclass) and pg_temp.err(format('select count(*) from %s', c.oid::regclass)) is not null), 'none') = 'none';
insert into r(name,ok) select 'F-01 anon cannot even ask (is_server_call is not executable by anon)', pg_temp.err('select public.is_server_call()')='42501';
select pg_temp.as_user(:C);
insert into r(name,ok) select 'F-26 a member can query every table and storage.objects without an error', coalesce((select string_agg(c.oid::regclass::text, ',') from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where ((n.nspname='public' and c.relkind in ('r','v')) or c.oid='storage.objects'::regclass) and pg_temp.err(format('select count(*) from %s', c.oid::regclass)) is not null), 'none') = 'none';
insert into r(name,ok) select 'F-01 a member is never a server call', not public.is_server_call();
reset role;
insert into r(name,ok) select 'F-01 SQL / the service role is a server call', public.is_server_call();

-- ── F-113 / F-163 catalog checks ──
insert into r(name,ok) select 'F-113 the five write policies use (select auth.uid()), evaluated once', (select count(*)=5 from pg_policies where schemaname='public' and policyname in ('messages: receiver marks read','members: owners/admins or the person update','members: owners/admins remove, or leave','documents: owners/admins/regulatory/quality add','verification: owners/admins submit')
  and regexp_replace(coalesce(qual,'')||' '||coalesce(with_check,''), '\(\s*SELECT auth\.uid\(\) AS uid\)', '', 'g') !~ 'auth\.uid\(\)');
insert into r(name,ok) select 'F-163 the unused english full-text indexes are gone', not exists(select 1 from pg_indexes where indexname in ('idx_posts_fts','idx_products_fts','idx_conn_status'));
insert into r(name,ok) select 'F-102 comments.post_id and post_media.post_id are not null', (select bool_and(is_nullable='NO') from information_schema.columns where table_schema='public' and table_name in ('comments','post_media') and column_name='post_id');

reset role;
select (case when ok then 'PASS  ' else 'FAIL  ' end) || name from r order by n;
select 'TOTAL ' || count(*) filter (where ok) || ' / ' || count(*) from r;
\set ON_ERROR_STOP on
do $$ declare f int; t int; begin select count(*) filter (where not ok), count(*) into f, t from r;
  if t = 0 or f > 0 then raise exception '% of % check(s) FAILED', f, t; end if; end $$;
rollback;
