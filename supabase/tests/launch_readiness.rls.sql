-- Launch readiness (0026): the API roles' privileges are written out explicitly (a project that does not grant new public tables
-- to anon/authenticated/service_role automatically — Supabase's api.auto_expose_new_tables, deprecated 2026-10-30 — ends with
-- exactly the same privileges); the directory page is cheaper with exactly the same output; company slugs are chosen one at a
-- time, so two different names can no longer race to the same suffix (N-12).
-- Runs in one transaction that is rolled back; test data carries the "LR " marker. The slug race uses two real extra sessions
-- (dblink): those rows are committed by those sessions and deleted again at the end.
-- Run on a fresh database (stub + migrations): psql -f supabase/tests/launch_readiness.rls.sql
-- Harness as in followups.rls.sql: step()/ok()/no(); a negative check passes only with the expected SQLSTATE; non-zero exit on failure.
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
create function pg_temp.u(n int) returns uuid language sql immutable as $$ select ('f2600000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid $$;

-- the API roles' privileges on everything the migrations create in public / private: effective rights and explicit ACL entries
create function pg_temp.privs() returns setof text language sql stable as $$
  with roles(r) as (values ('anon'), ('authenticated'), ('service_role')),
  rel as (select c.oid, format('%I.%I', n.nspname, c.relname) as name, c.relkind, c.relacl from pg_class c join pg_namespace n on n.oid = c.relnamespace
          where n.nspname in ('public', 'private') and c.relkind in ('r','v','m','p','f','S')),
  fn as (select p.oid, format('%I.%I(%s)', n.nspname, p.proname, pg_get_function_identity_arguments(p.oid)) as name, coalesce(p.proacl, acldefault('f', p.proowner)) as acl
         from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname in ('public', 'private'))
  select 'rel ' || name || ' ' || r || ' ' || p || '=' || case when relkind = 'S' then has_sequence_privilege(r, oid, p) else has_table_privilege(r, oid, p) end
  from rel, roles, unnest(case when relkind = 'S' then array['USAGE','SELECT','UPDATE'] else array['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] end) p
  union all
  select 'col ' || rel.name || '.' || a.attname || ' ' || r || ' ' || p || '=' || has_column_privilege(r, rel.oid, a.attnum, p)
  from rel join pg_attribute a on a.attrelid = rel.oid and a.attnum > 0 and not a.attisdropped, roles, unnest(array['SELECT','INSERT','UPDATE','REFERENCES']) p where rel.relkind <> 'S'
  union all
  select 'fn ' || name || ' ' || r || ' EXECUTE=' || has_function_privilege(r, oid, 'EXECUTE') from fn, roles
  union all
  select 'acl ' || rel.name || ' ' || coalesce(g.rolname, 'PUBLIC') || ' ' || x.privilege_type || ' ' || x.is_grantable
  from rel, aclexplode(rel.relacl) x left join pg_roles g on g.oid = x.grantee where x.grantee = 0 or g.rolname in ('anon','authenticated','service_role')
  union all
  select 'acl ' || rel.name || '.' || a.attname || ' ' || coalesce(g.rolname, 'PUBLIC') || ' ' || x.privilege_type || ' ' || x.is_grantable
  from rel join pg_attribute a on a.attrelid = rel.oid and a.attnum > 0 and not a.attisdropped and a.attacl is not null, aclexplode(a.attacl) x left join pg_roles g on g.oid = x.grantee
  where x.grantee = 0 or g.rolname in ('anon','authenticated','service_role')
  union all
  select 'acl ' || fn.name || ' ' || coalesce(g.rolname, 'PUBLIC') || ' ' || x.privilege_type || ' ' || x.is_grantable
  from fn, aclexplode(fn.acl) x left join pg_roles g on g.oid = x.grantee where x.grantee = 0 or g.rolname in ('anon','authenticated','service_role') $$;

-- ══ 1. N-12 two DIFFERENT names cannot race to the same slug ════════════════════════════════════════════════════
-- Two real sessions (dblink). Committed rows x, x-2, x-3 exist; session A inserts 'x' (gets x-4) and keeps its transaction open;
-- session B inserts a company whose own slug IS x-4 and is seen waiting; A commits; B must then get x-4-2 — before 0026 the two
-- locks differed (x vs x-4), B was not held back, found x-4 free and failed with 23505 when A committed.
-- (first: the main transaction must not yet hold any lock the two extra sessions need — the later sections create companies and re-run 0026)
select pg_temp.as_server();
select pg_temp.step('dblink for two extra sessions', $$create extension if not exists dblink schema extensions$$);
create function pg_temp.conn() returns text language sql stable as $$
  select format('dbname=%s host=%s port=%s user=%s application_name=lr26_race options=''-c lock_timeout=15s -c statement_timeout=30s''', current_database(),
                coalesce(nullif(trim(split_part(current_setting('unix_socket_directories'), ',', 1)), ''), '127.0.0.1'), current_setting('port'), current_user) $$;
-- wait (≤ 10 s) until the session with this backend pid waits for a lock
create function pg_temp.wait_blocked(p int) returns boolean language plpgsql as $$ begin
  for i in 1 .. 200 loop
    if exists (select 1 from pg_locks where pid = p and not granted) then return true; end if;
    perform pg_sleep(0.05);
  end loop; return false; end $$;
select pg_temp.step('two sessions', $$select extensions.dblink_connect('lr_a', pg_temp.conn()); select extensions.dblink_connect('lr_b', pg_temp.conn())$$);
select pg_temp.step('committed: lr-race, lr-race-2, lr-race-3', $$select extensions.dblink_exec('lr_a', $q$delete from public.companies where name like 'LR Race%' or name like 'LR Same%'$q$);
  select extensions.dblink_exec('lr_a', $q$insert into public.companies (name, slug, status) values ('LR Race', 'lr-race', 'unclaimed')$q$);
  select extensions.dblink_exec('lr_a', $q$insert into public.companies (name, slug, status) values ('LR Race', 'lr-race', 'unclaimed')$q$);
  select extensions.dblink_exec('lr_a', $q$insert into public.companies (name, slug, status) values ('LR Race', 'lr-race', 'unclaimed')$q$)$$);
select pg_temp.step('A: insert "LR Race" (needs lr-race-4), transaction left open', $$select extensions.dblink_exec('lr_a', 'begin');
  select extensions.dblink_exec('lr_a', $q$insert into public.companies (name, slug, status) values ('LR Race', 'lr-race', 'unclaimed')$q$)$$);
insert into ids select 'pid_b', b from extensions.dblink('lr_b', 'select pg_backend_pid()') as t(b int);
select pg_temp.step('B: insert "LR Race 4" with slug lr-race-4 (sent, not waited for)', $$select extensions.dblink_send_query('lr_b', $q$insert into public.companies (name, slug, status) values ('LR Race 4', 'lr-race-4', 'unclaimed') returning slug$q$)$$);
select pg_temp.ok('N-12 B waits while A has not committed', $$pg_temp.wait_blocked(pg_temp.id('pid_b')::int)$$);
select pg_temp.step('A commits', $$select extensions.dblink_exec('lr_a', 'commit')$$);
select pg_temp.ok('N-12 B is saved (no unique violation) with the next free slug lr-race-4-2', $$(select slug from extensions.dblink_get_result('lr_b') as t(slug text)) = 'lr-race-4-2'$$);
select pg_temp.step('drain B', $$select * from extensions.dblink_get_result('lr_b') as t(slug text)$$);
select pg_temp.ok('N-12 A kept lr-race-4; four "LR Race" pages and one "LR Race 4", all different', $$
  (select string_agg(slug, ',' order by slug) from extensions.dblink('lr_a', $q$select slug from public.companies where name like 'LR Race%'$q$) as t(slug text))
  = 'lr-race,lr-race-2,lr-race-3,lr-race-4,lr-race-4-2'$$);
-- the same slug at the same moment (what 0025 already handled) still works with the single lock
select pg_temp.step('A: insert "LR Same" open; B: insert "LR Same"', $$select extensions.dblink_exec('lr_a', 'begin');
  select extensions.dblink_exec('lr_a', $q$insert into public.companies (name, slug, status) values ('LR Same', 'lr-same', 'unclaimed')$q$);
  select extensions.dblink_send_query('lr_b', $q$insert into public.companies (name, slug, status) values ('LR Same', 'lr-same', 'unclaimed') returning slug$q$)$$);
select pg_temp.ok('N-12 the second "LR Same" waits', $$pg_temp.wait_blocked(pg_temp.id('pid_b')::int)$$);
select pg_temp.step('A commits', $$select extensions.dblink_exec('lr_a', 'commit')$$);
select pg_temp.ok('N-12 …and gets lr-same-2', $$(select slug from extensions.dblink_get_result('lr_b') as t(slug text)) = 'lr-same-2'$$);
select pg_temp.step('drain B', $$select * from extensions.dblink_get_result('lr_b') as t(slug text)$$);
-- a different, unrelated slug is never refused (it only waits for the short slug check of the other insert)
select pg_temp.step('A: insert "LR Race" open again (lr-race-5)', $$select extensions.dblink_exec('lr_a', 'begin');
  select extensions.dblink_exec('lr_a', $q$insert into public.companies (name, slug, status) values ('LR Race', 'lr-race', 'unclaimed')$q$)$$);
select pg_temp.step('B: an unrelated company', $$select extensions.dblink_send_query('lr_b', $q$insert into public.companies (name, slug, status) values ('LR Same Other', 'lr-same-other', 'unclaimed') returning slug$q$)$$);
select pg_temp.step('A rolls back', $$select extensions.dblink_exec('lr_a', 'rollback')$$);
select pg_temp.ok('N-12 the unrelated company keeps its own slug', $$(select slug from extensions.dblink_get_result('lr_b') as t(slug text)) = 'lr-same-other'$$);
select pg_temp.step('drain B', $$select * from extensions.dblink_get_result('lr_b') as t(slug text)$$);
select pg_temp.ok('N-12 the slug trigger function is still not callable from the API', $$not has_function_privilege('anon', 'public.companies_before_write()', 'execute')
  and not has_function_privilege('authenticated', 'public.companies_before_write()', 'execute')$$);
select pg_temp.step('clean up the committed race rows', $$select extensions.dblink_exec('lr_a', $q$delete from public.companies where name like 'LR Race%' or name like 'LR Same%'$q$)$$);
select pg_temp.ok('(cleanup) no race rows left', $$(select n from extensions.dblink('lr_a', $q$select count(*) from public.companies where name like 'LR Race%' or name like 'LR Same%'$q$) as t(n bigint)) = 0$$);
select pg_temp.step('close the sessions', $$select extensions.dblink_disconnect('lr_a'); select extensions.dblink_disconnect('lr_b')$$);


-- ══ 2. explicit grants: the same privileges without any automatic grant ══════════════════════════════════════════
select pg_temp.as_server();
create temp table priv_before as select pg_temp.privs() as p;
-- a project that grants NOTHING automatically: every privilege of the API roles on the migrations' objects is taken away
-- (stricter than Supabase's new default: PUBLIC loses EXECUTE on every function too)
do $$ declare o record; begin
  for o in select format('%I.%I', n.nspname, c.relname) as name, c.relkind from pg_class c join pg_namespace n on n.oid = c.relnamespace
           where n.nspname in ('public', 'private') and c.relkind in ('r','v','m','p','f','S') loop
    execute format('revoke all on %s %s from anon, authenticated, service_role', case when o.relkind = 'S' then 'sequence' else 'table' end, o.name);
  end loop;
  for o in select format('%I.%I(%s)', n.nspname, p.proname, pg_get_function_identity_arguments(p.oid)) as name, p.prokind from pg_proc p
           join pg_namespace n on n.oid = p.pronamespace where n.nspname in ('public', 'private') and p.prokind in ('f', 'p') loop
    execute format('revoke all on %s %s from public, anon, authenticated, service_role', case when o.prokind = 'p' then 'procedure' else 'function' end, o.name);
  end loop;
end $$;
select pg_temp.ok('(setup) with nothing granted, the API is closed: authenticated cannot read profiles', $$not has_table_privilege('authenticated', 'public.profiles', 'SELECT')$$);
\ir ../migrations/0026_launch_readiness.sql
select pg_temp.as_server();
create temp table priv_after as select pg_temp.privs() as p;
select pg_temp.ok('grants: 0026 alone restores every privilege of anon, authenticated and service_role exactly (effective rights + ACL entries)',
  $$not exists (select p from priv_before except select p from priv_after) and not exists (select p from priv_after except select p from priv_before)$$);
insert into r(name, ok, err) select 'grants: differs after 0026 on a project without automatic grants: ' || p, false, null
  from ((select p from priv_before except select p from priv_after) union all (select p from priv_after except select p from priv_before)) d limit 10;
select pg_temp.ok('grants: the snapshot covers tables, columns, sequences and functions', $$(select count(*) from priv_after where p like 'rel %') > 300
  and (select count(*) from priv_after where p like 'fn %') > 300 and (select count(*) from priv_after where p like 'col %') > 1000$$);
-- the deploy script's grant check (deploy/supabase_deploy.sh step 4)
select pg_temp.ok('grants: every table with a read policy is readable by its role (deploy check)', $$not exists (select 1 from pg_policies p
  cross join lateral unnest(case when 'public' = any(p.roles) then array['anon','authenticated']::name[] else p.roles end) r(role)
  where p.schemaname = 'public' and p.cmd in ('SELECT', 'ALL') and r.role in ('anon', 'authenticated')
    and not has_any_column_privilege(r.role, format('public.%I', p.tablename), 'SELECT'))$$);
select pg_temp.ok('grants: every insertable table can use its sequence (deploy check)', $$not exists (select 1 from pg_class c join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
  join pg_attrdef d on d.adrelid = c.oid join pg_depend dep on dep.classid = 'pg_attrdef'::regclass and dep.objid = d.oid and dep.refclassid = 'pg_class'::regclass
  join pg_class s on s.oid = dep.refobjid and s.relkind = 'S'
  where c.relkind = 'r' and has_table_privilege('authenticated', c.oid, 'INSERT')
    and case when s.relkind = 'S' then not has_sequence_privilege('authenticated', s.oid, 'USAGE') else false end)$$);
-- the privacy rules of 0020 / 0024 / 0025 hold after the explicit grants
select pg_temp.ok('privacy: anon writes nothing (no INSERT/UPDATE/DELETE/TRUNCATE on any public table)', $$not exists (select 1 from pg_class c where c.relnamespace = 'public'::regnamespace
  and c.relkind in ('r','v','p') and (has_table_privilege('anon', c.oid, 'INSERT') or has_table_privilege('anon', c.oid, 'UPDATE') or has_table_privilege('anon', c.oid, 'DELETE')
  or has_table_privilege('anon', c.oid, 'TRUNCATE')))$$);
select pg_temp.ok('privacy: anon uses no sequence', $$not exists (select 1 from pg_class c where c.relnamespace = 'public'::regnamespace and c.relkind = 'S'
  and (has_sequence_privilege('anon', c.oid, 'USAGE') or has_sequence_privilege('anon', c.oid, 'UPDATE')))$$);
select pg_temp.ok('privacy: anon runs none of the server-only or member RPCs', $$not has_function_privilege('anon', 'public.directory_companies_page(int,int,text)', 'execute')
  and not has_function_privilege('anon', 'public.company_ratings(bigint[])', 'execute') and not has_function_privilege('anon', 'public.activate_order(bigint)', 'execute')
  and not has_function_privilege('authenticated', 'public.activate_order(bigint)', 'execute') and not has_function_privilege('authenticated', 'public.companies_before_write()', 'execute')$$);
select pg_temp.ok('privacy: the private document path stays hidden from members (column grants)', $$not has_column_privilege('authenticated', 'public.company_documents', 'file_path', 'SELECT')
  and has_column_privilege('authenticated', 'public.company_documents', 'number', 'SELECT')$$);


-- ══ 3. the directory page: same JSON as before, for every page, search and member ═══════════════════════════════
-- dir_old = directory_companies_page exactly as 0022 wrote it (company_tier() per row, the wide sort)
create function pg_temp.dir_old(p_limit int default 100, p_offset int default 0, p_q text default null)
returns json language sql stable security invoker set search_path = public set jit = off as $old$
  with q as (select nullif(left(trim(coalesce(p_q, '')), 100), '') as q),
  page as (
    select c.* from public.companies c, q
    where c.status <> 'suspended'
      and (q.q is null or c.name ilike '%' || q.q || '%' or c.name_ar ilike '%' || q.q || '%'
           or exists (select 1 from public.company_products p where p.company_id = c.id
                      and (p.name ilike '%' || q.q || '%' or p.active_ingredient ilike '%' || q.q || '%' or p.active_ingredient_ar ilike '%' || q.q || '%')))
    order by (c.status = 'verified') desc, (c.plan = 'vip' and (c.vip_until is null or c.vip_until > now())) desc, c.name, c.id
    limit least(greatest(coalesce(p_limit, 100), 1), 200) offset greatest(coalesce(p_offset, 0), 0)),
  mine as (select public.my_company_ids() as id),
  rated as (select * from public.company_ratings(array(select id from page)))
  select coalesce(json_agg(x order by (x.status = 'verified') desc, (x.plan = 'vip') desc, x.name, x.id), '[]'::json) from (
    select c.id, c.slug, c.name, c.name_ar, c.status, c.registry, c.licensed, c.sectors, c.governorate, c.city, c.location, c.tagline, c.bio,
           c.founded, c.employees, c.website, c.phone, c.email, c.whatsapp, c.hours,
           case when c.plan = 'vip' and (c.vip_until is null or c.vip_until > now()) then 'vip' else 'free' end as plan,
           c.logo_url, c.follower_count, c.profile, c.created_at, c.intro_video,
           public.company_tier(c.id) as tier, c.id in (select id from mine) as mine,
           (select coalesce(json_agg(distinct s.name), '[]'::json) from public.site_certificates s where s.company_id = c.id and (s.expiry is null or s.expiry >= current_date)) as certs,
           (select coalesce(json_agg(json_build_object('name', p.name, 'ingredient', p.active_ingredient, 'ingredient_ar', p.active_ingredient_ar,
                   'form', p.dosage_form, 'strength', p.strength, 'role', p.role) order by p.name), '[]'::json) from public.company_products p where p.company_id = c.id) as products,
           json_build_object('rating', r.rating, 'reviews', coalesce(r.reviews, 0)) as track
    from page c left join rated r on r.company_id = c.id) x
$old$;
grant execute on function pg_temp.dir_old(int, int, text) to authenticated;
select pg_temp.as_server();
insert into auth.users (id, email) select pg_temp.u(g), 'lr' || g || '@lr26.test' from generate_series(1, 4) g on conflict do nothing;
insert into public.profiles (id, name) select pg_temp.u(g), 'LR person ' || g from generate_series(1, 4) g on conflict (id) do nothing;
-- named companies covering every branch of the tier rule and of the plan, then 260 more in mixed states (several pages)
insert into public.companies (owner_id, name, name_ar, slug, type, status, registry, licensed, plan, vip_until) values
  (pg_temp.u(1), 'LR Alpha Pharma',   'ألفا',  'lr-alpha',   'Manufacturer', 'verified', 'LR-1', true,  'vip',  now() + interval '30 days'),
  (pg_temp.u(2), 'LR Beta Labs',      null,    'lr-beta',    'Manufacturer', 'verified', 'LR-2', true,  'free', null),
  (pg_temp.u(3), 'LR Gamma',          null,    'lr-gamma',   'Distributor',  'verified', 'LR-3', true,  'vip',  now() - interval '1 day'),
  (pg_temp.u(3), 'LR Delta',          null,    'lr-delta',   'Distributor',  'verified', 'LR-4', false, 'vip',  null),
  (pg_temp.u(3), 'LR Epsilon',        null,    'lr-epsilon', 'Distributor',  'verified', null,   true,  'free', null),
  (pg_temp.u(3), 'LR Zeta',           'زيتا ميتفورمين', 'lr-zeta', 'Manufacturer', 'pending', 'LR-6', true, 'free', null),
  (pg_temp.u(3), 'LR Eta',            null,    'lr-eta',     'Manufacturer', 'suspended', 'LR-7', true, 'vip', null),
  (pg_temp.u(3), 'LR Theta',          null,    'lr-theta',   'Manufacturer', 'verified', 'LR-8', true,  'free', null),
  (pg_temp.u(3), 'LR Theta',          null,    'lr-theta-b', 'Manufacturer', 'verified', 'LR-9', true,  'free', null),
  (pg_temp.u(1), 'LR Iota 100% _x_',  null,    'lr-iota',    'Manufacturer', 'verified', 'LR-10', true, 'free', null);
insert into public.companies (owner_id, name, name_ar, slug, type, status, registry, licensed, plan, vip_until)
select case when g % 10 <> 9 then pg_temp.u(3) end, 'LR Bulk ' || lpad(g::text, 3, '0') || case when g % 7 = 0 then ' Metformin Co' else '' end,
       case when g % 5 = 0 then 'شركة ' || g end, 'lr-bulk-' || g, 'Manufacturer',
       case when g % 10 = 9 then 'unclaimed' else (array['verified','verified','pending','suspended'])[1 + g % 4] end, case when g % 6 <> 0 then 'LRB-' || g end, g % 3 <> 0,
       case when g % 4 = 1 then 'vip' else 'free' end, case when g % 8 = 1 then now() - interval '2 days' when g % 8 = 5 then now() + interval '9 days' end
from generate_series(1, 260) g;
insert into ids select 'co_' || slug, id from public.companies where slug like 'lr-%';
insert into public.company_sites (company_id, name) select id, 'LR site' from public.companies where slug like 'lr-%';
-- certificates: checked + valid GMP (tier 3), checked but expired, unchecked, not a GMP-type name, lower-case ISO 17025 with no expiry, duplicates
insert into public.site_certificates (site_id, company_id, name, expiry, checked_at)
select s.id, s.company_id, x.name, x.expiry, x.checked
from public.company_sites s join public.companies c on c.id = s.company_id
cross join lateral (values
  ('GMP',       current_date + 100, now(), c.slug in ('lr-alpha', 'lr-delta', 'lr-epsilon', 'lr-zeta') or c.slug ~ '^lr-bulk-[0-9]*[05]$'),
  ('GMP',       current_date - 1,   now(), c.slug in ('lr-beta') or c.slug ~ '^lr-bulk-[0-9]*[16]$'),
  ('EU GMP',    current_date + 10,  null::timestamptz, c.slug in ('lr-gamma', 'lr-alpha') or c.slug ~ '^lr-bulk-[0-9]*[27]$'),
  ('ISO 9001',  current_date + 10,  now(), c.slug in ('lr-theta', 'lr-alpha') or c.slug ~ '^lr-bulk-[0-9]*[38]$'),
  ('iso 17025', null::date,         now(), c.slug in ('lr-theta-b') or c.slug ~ '^lr-bulk-[0-9]*9$'),
  ('ISO 9001',  current_date,       now(), c.slug in ('lr-alpha') or c.slug ~ '^lr-bulk-[0-9]*3$')) x(name, expiry, checked, wanted)
where c.slug like 'lr-%' and x.wanted;
insert into public.company_products (company_id, name, active_ingredient, active_ingredient_ar, dosage_form, strength)
select c.id, p.name, p.ai, p.ai_ar, 'Tablet', '500 mg' from public.companies c cross join lateral (values
  ('Glucolr', 'Metformin', 'ميتفورمين', c.slug in ('lr-beta', 'lr-gamma') or c.slug ~ '^lr-bulk-[0-9]*[29]$'),
  ('Paralr',  'Paracetamol', null, c.slug in ('lr-alpha', 'lr-beta') or c.slug ~ '^lr-bulk-[0-9]*[147]$'),
  ('Amoxlr',  'Amoxicillin', 'أموكسيسيلين', c.slug in ('lr-alpha') or c.slug ~ '^lr-bulk-[0-9]*5$')) p(name, ai, ai_ar, wanted)
where c.slug like 'lr-%' and p.wanted;
-- ratings (the track record): rated deals into Alpha and Theta from other companies
insert into public.deals (type, title, from_company_id, to_company_id, status)
select 'quote', 'LR deal ' || g, pg_temp.id('co_lr-gamma'), case when g <= 3 then pg_temp.id('co_lr-alpha') else pg_temp.id('co_lr-theta') end, 'completed' from generate_series(1, 5) g;
insert into public.deal_events (deal_id, side, action, data)
select d.id, 'from', 'rate', jsonb_build_object('stars', 3 + (d.id % 3)) from public.deals d where d.title like 'LR deal %';
insert into public.deal_events (deal_id, side, action, data) select d.id, 'from', 'note', '{}' from public.deals d where d.title like 'LR deal %';
select pg_temp.ok('(setup) the directory data covers tiers 0-3, both plans, certificates, products, ratings and "mine"', $$
  (select count(distinct public.company_tier(id)) from public.companies where slug like 'lr-%') = 4
  and exists (select 1 from public.companies where slug like 'lr-%' and plan = 'vip' and vip_until < now())
  and (select count(*) from public.deal_events where action = 'rate') >= 5$$);
-- every member, every page size and offset (across page ends), every kind of search: byte-identical JSON
create temp table dir_cases as
  select l, o, q from unnest(array[100, 7, 1, 200, 0, -5, null]) l, unnest(array[0, 3, 100, 150, 199, 260, 400, -1, null]) o,
         unnest(array[null, '', '   ', 'LR', 'lr theta', 'metformin', 'MET', 'ميتفورمين', 'شركة', 'Paralr', '100%', '_x_', '%', '_', 'none-such', repeat('LR', 80)]) q;
grant select on dir_cases to authenticated;
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.ok('directory: a member of two companies gets byte-identical JSON for ' || (select count(*) from dir_cases) || ' page/search cases',
  $$not exists (select 1 from dir_cases where pg_temp.dir_old(l, o, q)::text is distinct from public.directory_companies_page(l, o, q)::text)$$);
select pg_temp.ok('directory: …and the cases are not empty (tiers 0-3, vip, mine, ratings, certificates, products all appear)', $$
  (select count(distinct (e->>'tier')) from json_array_elements(public.directory_companies_page(200, 0, 'LR')) e) = 4
  and exists (select 1 from json_array_elements(public.directory_companies_page(200, 0, 'LR')) e where (e->>'mine')::boolean and e->>'plan' = 'vip' and (e->'track'->>'reviews')::int = 3
              and json_array_length(e->'certs') = 3 and json_array_length(e->'products') = 2)$$);
select pg_temp.ok('directory: the default arguments give the same page', $$pg_temp.dir_old()::text = public.directory_companies_page()::text$$);
select pg_temp.as_user(pg_temp.u(2));
select pg_temp.ok('directory: identical for a member of one company', $$not exists (select 1 from dir_cases where l in (100, 7) and o in (0, 100, 150)
  and pg_temp.dir_old(l, o, q)::text is distinct from public.directory_companies_page(l, o, q)::text)$$);
select pg_temp.as_user(pg_temp.u(4));
select pg_temp.ok('directory: identical for a member without a company', $$not exists (select 1 from dir_cases where l in (100, 200) and o in (0, 150)
  and pg_temp.dir_old(l, o, q)::text is distinct from public.directory_companies_page(l, o, q)::text)$$);
select pg_temp.as_server();
select pg_temp.step('a certificate expires, a VIP plan runs out, a company is verified', $$update public.site_certificates set expiry = current_date - 1 where company_id = pg_temp.id('co_lr-alpha') and name = 'GMP';
  update public.companies set vip_until = now() - interval '1 minute' where slug = 'lr-alpha'; update public.companies set status = 'verified' where slug = 'lr-zeta'$$);
select pg_temp.as_user(pg_temp.u(1));
select pg_temp.ok('directory: still identical after certificates, plans and statuses change (nothing is stale)', $$not exists (select 1 from dir_cases where l in (100, 200) and o in (0, 150)
  and pg_temp.dir_old(l, o, q)::text is distinct from public.directory_companies_page(l, o, q)::text)$$);
select pg_temp.ok('directory: Alpha''s level follows its certificate (3 → 2 when the GMP expires)', $$(select (e->>'tier')::int from json_array_elements(public.directory_companies_page(200, 0, 'LR Alpha')) e) = 2$$);
select pg_temp.as_anon();
select pg_temp.ok('privacy: with the explicit grants anon still reads no person and no company (row security, 0024)', $$(select count(*) from public.profiles) = 0
  and (select count(*) from public.companies) = 0 and (select count(*) from public.company_products) = 0 and (select count(*) from public.site_certificates) = 0$$);
select pg_temp.no('privacy: …and nothing of the directory''s product cache', $$select count(*) from private.directory_products$$, '42501');
select pg_temp.no('directory: anon still cannot call it', $$select public.directory_companies_page(100, 0, null)$$, '42501');
select pg_temp.as_server();
select pg_temp.ok('directory: the rating lookup has its partial index', $$exists (select 1 from pg_indexes where schemaname = 'public' and tablename = 'deal_events' and indexname = 'idx_deal_events_rate')$$);

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
