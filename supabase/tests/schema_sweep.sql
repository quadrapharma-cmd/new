-- Schema sweep — every line must end in "none". Run on any database after all migrations (tests/run_all.py sweep does it).
-- 1) a table with row-level security ON and NO policy is unusable in production (it hid three bugs that the demo could not show)
select 'RLS on, no policy: ' || coalesce(string_agg(c.relname, ', '), 'none') from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public' and c.relkind = 'r' and c.relrowsecurity and not exists (select 1 from pg_policies p where p.schemaname = 'public' and p.tablename = c.relname);
-- 2) every public table has row-level security on
select 'RLS off: ' || coalesce(string_agg(c.relname, ', '), 'none') from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity;
-- 3) one counter trigger per table (two counters double-count) — found by name OR by what the trigger does (x_count = x_count ± …)
select 'Tables with two counters: ' || coalesce(string_agg(t, ', '), 'none') from (select g.tgrelid::regclass::text t from pg_trigger g join pg_proc f on f.oid = g.tgfoid
 where not g.tgisinternal and (g.tgname::text like '%count%' or pg_get_functiondef(f.oid) ~* '\m\w+_count\s*=\s*(coalesce\()?\s*\w*\.?\w+_count\s*\)?\s*[-+]')
 group by 1 having count(*) > 1) x;
-- 4) a write the signed-in user is granted but no policy allows: it silently does nothing (or a policy went missing, e.g. a
--    migration re-run that skipped the rest of a multi-policy block) — revoke the grant or add the policy
select 'Signed-in writes granted without a policy: ' || coalesce(string_agg(t || ' ' || cmd, ', ' order by t, cmd), 'none') from (
 select c.relname t, cmd from pg_class c join pg_namespace n on n.oid = c.relnamespace cross join unnest(array['INSERT', 'UPDATE', 'DELETE']) cmd
  where n.nspname = 'public' and c.relkind = 'r' and c.relrowsecurity and has_table_privilege('authenticated', c.oid, cmd)
    and not exists (select 1 from pg_policies q where q.schemaname = 'public' and q.tablename = c.relname and q.cmd in (cmd, 'ALL')
                    and (q.roles && array['authenticated', 'public']::name[]))) x;
-- 5) a SECURITY DEFINER function the anon key can call (it runs with the owner's rights) — only the helpers that row policies
--    evaluate as the calling role may stay callable
select 'Security-definer functions anon can call: ' || coalesce(string_agg(p.oid::regprocedure::text, ', '), 'none') from pg_proc p join pg_namespace n on n.oid = p.pronamespace
 where n.nspname = 'public' and p.prosecdef and p.prorettype <> 'trigger'::regtype and has_function_privilege('anon', p.oid, 'execute')
   and not exists (select 1 from pg_policies q where coalesce(q.qual, '') || ' ' || coalesce(q.with_check, '') ~ ('\m' || p.proname || '\('));
-- 6) every storage bucket has at least one policy on storage.objects that names it (else uploads/reads fail silently)
select 'Buckets without a policy: ' || coalesce(string_agg(b.id, ', '), 'none') from storage.buckets b
 where not exists (select 1 from pg_policies q where q.schemaname = 'storage' and q.tablename = 'objects' and coalesce(q.qual, '') || ' ' || coalesce(q.with_check, '') like '%''' || b.id || '''%');
