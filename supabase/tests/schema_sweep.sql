-- Schema sweep — must print three "none" lines. Run on any database after all migrations.
-- 1) a table with row-level security ON and NO policy is unusable in production (it hid three bugs that the demo could not show)
select 'RLS on, no policy: ' || coalesce(string_agg(c.relname, ', '), 'none') from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public' and c.relkind = 'r' and c.relrowsecurity and not exists (select 1 from pg_policies p where p.schemaname = 'public' and p.tablename = c.relname);
-- 2) every public table has row-level security on
select 'RLS off: ' || coalesce(string_agg(c.relname, ', '), 'none') from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity;
-- 3) one counter trigger per table (two counters double-count)
select 'Tables with two counters: ' || coalesce(string_agg(t, ', '), 'none') from (select tgrelid::regclass::text t from pg_trigger
 where not tgisinternal and tgname::text like '%count%' group by 1 having count(*) > 1) x;
