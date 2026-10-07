"""Migration re-run check: every migration must be safe to run twice, and must put back every policy it creates.
  python3 tools/migration_check.py            (PGHOST /tmp, PGPORT 5433, PGUSER postgres; database DB_NAME, default rv_migration_check)
For each migration in order, on a fresh database (stub + the migrations before it):
  1. apply it;
  2. apply it AGAIN (in one transaction): it must not fail, and must not change any policy, function, trigger, index or column;
  3. for every policy it creates that still exists at that point: drop just that policy and re-apply the migration (rolled back
     afterwards) — the policy must come back. A DO block holding several `create policy` statements with one
     `exception when duplicate_object` handler stops at the first policy that exists, silently skipping the others.
Exits 1 on any finding. 0001_init.sql is the base schema and is known not to be re-runnable (plain CREATE TABLE): reported, not failed."""
import os, re, sys, glob, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get('DB_NAME', 'rv_migration_check')
PG = ['psql', '-X', '-q', '-h', os.environ.get('PGHOST', '/tmp'), '-p', os.environ.get('PGPORT', '5433'), '-U', os.environ.get('PGUSER', 'postgres')]
KNOWN_NOT_RERUNNABLE = {'0001_init.sql'}
MIGRATIONS = sorted(glob.glob(ROOT + '/supabase/migrations/[0-9][0-9][0-9][0-9]_*.sql'))
SNAP = r"""select 'policy ' || schemaname || '.' || tablename || ' ' || policyname, cmd || ' ' || roles::text || ' ' || coalesce(qual, '') || ' ' || coalesce(with_check, '') from pg_policies where schemaname in ('public', 'storage')
union all select 'function ' || p.oid::regprocedure::text, md5(pg_get_functiondef(p.oid)) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
  where n.nspname in ('public', 'storage', 'auth') and p.prokind = 'f' and not exists (select 1 from pg_depend d where d.objid = p.oid and d.deptype = 'e')
union all select 'trigger ' || tgrelid::regclass::text || ' ' || tgname, pg_get_triggerdef(oid) from pg_trigger where not tgisinternal
union all select 'index ' || schemaname || '.' || indexname, indexdef from pg_indexes where schemaname in ('public', 'storage')
union all select 'column ' || table_schema || '.' || table_name || '.' || column_name, data_type || ' ' || coalesce(column_default, '') || ' ' || is_nullable
  from information_schema.columns where table_schema = 'public'"""
findings, notes = [], []

def psql(args, stdin=None):
    r = subprocess.run(PG + args, input=stdin, capture_output=True, text=True); return r.returncode, r.stdout, r.stderr
def snapshot():
    code, out, err = psql(['-d', DB, '-tA', '-F', '\x1f', '-c', SNAP])
    if code: raise SystemExit('snapshot failed: ' + err)
    return dict(l.split('\x1f', 1) for l in out.splitlines() if '\x1f' in l)
def apply(f, once=True):
    return psql(['-d', DB, '-v', 'ON_ERROR_STOP=1'] + (['-1'] if once else []) + ['-f', f])

psql(['-c', f'drop database if exists {DB}']); code, _, err = psql(['-c', f'create database {DB}'])
if code: raise SystemExit(err)
code, _, err = apply(ROOT + '/supabase/tests/_local_supabase_stub.sql', once=False)
if code: raise SystemExit('stub: ' + err)
for f in MIGRATIONS:
    name = os.path.basename(f); src = open(f, encoding='utf-8').read()
    code, _, err = apply(f, once=False)
    if code: findings.append(f'{name}: does not apply: {err.strip()[-400:]}'); break
    before = snapshot()
    code, _, err = apply(f)
    if code:
        (notes if name in KNOWN_NOT_RERUNNABLE else findings).append(f'{name}: fails when run a second time: {err.strip().splitlines()[0][:200]}')
        continue
    after = snapshot()
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    if changed: findings.append(f'{name}: a second run changes {len(changed)} definition(s): ' + ', '.join(changed[:8]))
    # every policy this migration creates comes back when it alone is missing
    for pol, table in re.findall(r'create\s+policy\s+"([^"]+)"\s+on\s+([\w."]+)', src, re.I):
        schema, tbl = (table.replace('"', '').split('.') + [''])[:2] if '.' in table else ('public', table.replace('"', ''))
        key = f'policy {schema}.{tbl} {pol}'
        if key not in after: continue   # replaced by this migration under another name
        script = (f'begin;\ndrop policy "{pol}" on {schema}.{tbl};\n\\i {f}\n'
                  f"do $chk$ begin if not exists (select 1 from pg_policies where schemaname = '{schema}' and tablename = '{tbl}' and policyname = $p${pol}$p$) "
                  f"then raise exception 'NOT RECREATED'; end if; end $chk$;\nrollback;\n")
        with tempfile.NamedTemporaryFile('w', suffix='.sql', delete=False) as t: t.write(script)
        code, _, err = psql(['-d', DB, '-v', 'ON_ERROR_STOP=1', '-f', t.name]); os.unlink(t.name)
        if code: findings.append(f'{name}: when policy "{pol}" on {schema}.{tbl} is missing, a re-run does not create it' + ('' if 'NOT RECREATED' in err else f' ({err.strip()[-200:]})'))
psql(['-c', f'drop database if exists {DB}'])
for n in notes: print('note   ' + n)
for x in findings: print('FAIL   ' + x)
print('migration re-run check: %s (%d migrations)' % ('OK' if not findings else '%d finding(s)' % len(findings), len(MIGRATIONS)))
sys.exit(1 if findings else 0)
