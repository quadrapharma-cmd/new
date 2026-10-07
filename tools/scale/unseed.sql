-- ═════════════════════════════════════════════════════════════════════
-- Drugbox — remove the staging load seed (tools/scale/seed_100k.sql) and nothing else
--
--   psql "$STAGING_DB_URL" -v ON_ERROR_STOP=1 -f tools/scale/unseed.sql
--
-- Removes: members *@scale.test (auth.users, their identities, profiles and everything that hangs off them),
-- the seed's companies (e-mail co<N>@scale.test) with their deals, and the seed's groups; then the `scale` schema.
-- Rows that seeded members left on REAL data (a like on a real post, a connection to a real person, a group or job
-- of a real member — e.g. from the k6 writes) are removed first with the triggers ON, so real counters and
-- conversation heads stay right. The rest goes in bulk with the tables' own triggers off (foreign keys stay on),
-- in ONE transaction: all or nothing. Safe to run more than once; a no-op when nothing is seeded.
-- ═════════════════════════════════════════════════════════════════════
\set ON_ERROR_STOP on
set statement_timeout = 0;
set lock_timeout = '30s';
set synchronous_commit = off;
set work_mem = '256MB';
set client_min_messages = warning;
\timing on
begin;
create temp table su on commit drop as select id from auth.users where email like '%@scale.test';
alter table su add primary key (id);
create temp table sc on commit drop as select id from public.companies where email like '%@scale.test';
alter table sc add primary key (id);
create temp table sg on commit drop as select id from public.groups where created_by in (select id from su);
alter table sg add primary key (id);
select (select count(*) from su) as members, (select count(*) from sc) as companies, (select count(*) from sg) as groups;

-- 1. seeded members' marks on real data, triggers ON (counters, heads, notifications of real members stay right)
delete from public.reactions r using public.posts p where p.id = r.post_id and r.user_id in (select id from su) and p.user_id not in (select id from su);
delete from public.comments c using public.posts p where p.id = c.post_id and c.user_id in (select id from su) and p.user_id not in (select id from su);
delete from public.connections where (requester in (select id from su)) <> (addressee in (select id from su));
delete from public.messages where (sender_id in (select id from su)) <> (receiver_id in (select id from su));
delete from public.group_members where user_id in (select id from su) and group_id not in (select id from sg);
delete from public.company_followers where user_id in (select id from su) and company_id not in (select id from sc);
delete from public.job_applications a using public.jobs j where j.id = a.job_id and a.user_id in (select id from su) and j.user_id not in (select id from su);
delete from public.company_members where user_id in (select id from su) and company_id not in (select id from sc);
delete from public.deal_members where company_id in (select id from sc) and deal_id in (select id from public.deals
  where coalesce(from_company_id, 0) not in (select id from sc) and to_company_id not in (select id from sc));
do $$ begin
  if to_regclass('public.course_enrollments') is not null then
    delete from public.course_enrollments where user_id in (select id from su);
  end if;
end $$;

-- 2. the rest in bulk: every public table's own triggers off for the transaction (foreign keys stay on)
do $$ declare t text; begin
  for t in select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public' and c.relkind = 'r' and exists (select 1 from pg_trigger g where g.tgrelid = c.oid and not g.tgisinternal) loop
    execute format('alter table public.%I disable trigger user', t);
  end loop;
end $$;
delete from public.deals where from_company_id in (select id from sc) or to_company_id in (select id from sc)
   or (from_company_id is null and from_user in (select id from su));
delete from public.approved_suppliers where buyer_company_id in (select id from sc) or supplier_company_id in (select id from sc);
-- the big tables first, by their own indexes (much faster than one cascade per member)
delete from public.notifications where user_id in (select id from su) or from_user in (select id from su);
delete from public.reactions where user_id in (select id from su);
delete from public.comments where user_id in (select id from su);
delete from public.saved_posts where user_id in (select id from su);
delete from public.posts where user_id in (select id from su);
delete from public.conversation_heads where owner in (select id from su);
delete from public.messages where sender_id in (select id from su);
delete from public.connections where requester in (select id from su) or addressee in (select id from su);
delete from public.job_applications where user_id in (select id from su);
delete from public.saved_jobs where user_id in (select id from su);
delete from public.jobs where user_id in (select id from su);
delete from public.group_members where user_id in (select id from su) or group_id in (select id from sg);
delete from public.groups where id in (select id from sg);
delete from public.company_followers where user_id in (select id from su) or company_id in (select id from sc);
delete from public.companies where id in (select id from sc);
delete from public.profiles where id in (select id from su);         -- cascades whatever is left (products, enquiries, reviews, …)
do $$ declare t text; begin
  for t in select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public' and c.relkind = 'r' and exists (select 1 from pg_trigger g where g.tgrelid = c.oid and not g.tgisinternal) loop
    execute format('alter table public.%I enable trigger user', t);
  end loop;
end $$;
-- 3. the accounts (auth.identities / sessions follow by their own foreign keys on Supabase)
delete from auth.users where id in (select id from su);
drop schema if exists scale cascade;
commit;
\timing off
select count(*) as scale_members_left from auth.users where email like '%@scale.test';
