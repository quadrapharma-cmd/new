"""Shared settings and helpers for the end-to-end suites.
Everything that depends on the machine comes from the environment (defaults = tools/local-supabase/start.sh):
  APP_URL (http://localhost:54321/)  DB_NAME (drugbox_live)  PGHOST (/tmp)  PGPORT (5433)  PGUSER (postgres)
  DRUGBOX_FIXTURES (/tmp/vids — made by tests/fixtures/make_fixtures.py)  DRUGBOX_FN_ENV ($RUN_DIR/drugbox-fn.env — written by start-payments.sh)
  DX_LANG (en | ar — the interface language the browser suites start in)
Every suite ends with done(): it prints "N / N" and exits 1 when any check failed (tests/run_all.py relies on it)."""
import os, re, sys, time, uuid, subprocess
APP_URL = os.environ.get('APP_URL', 'http://localhost:54321/')
DB = os.environ.get('DB_NAME', 'drugbox_live')
PSQL = ['psql', '-h', os.environ.get('PGHOST', '/tmp'), '-p', os.environ.get('PGPORT', '5433'), '-U', os.environ.get('PGUSER', 'postgres'), '-d', DB, '-tA', '-v', 'ON_ERROR_STOP=1']
FIXTURES = os.environ.get('DRUGBOX_FIXTURES', '/tmp/vids')
FN_ENV = os.environ.get('DRUGBOX_FN_ENV', os.path.join(os.environ.get('RUN_DIR', '/tmp'), 'drugbox-fn.env'))
LANG = os.environ.get('DX_LANG', 'en')
ST = '%d%s' % (time.time(), uuid.uuid4().hex[:6])   # unique per run: suites started in the same second never share an e-mail
STN = int(time.time()) * 1000 + uuid.uuid4().int % 1000   # the same, where a number is needed (registry numbers)
R = []

def T(name, ok, detail=''):
    R.append(bool(ok)); print(('✅ ' if ok else '❌ ') + name + ('' if ok else '  → ' + str(detail)[:240])); return ok

def sql(q):
    """Run SQL as the database owner; any error stops the suite (a failed setup must never make a check pass by accident)."""
    r = subprocess.run(PSQL + ['-c', q], capture_output=True, text=True)
    if r.returncode: raise SystemExit('SQL failed: ' + r.stderr.strip()[:300])
    return r.stdout.strip()

def fn_env():
    """The payment settings start-payments.sh wrote (KEY="value" lines)."""
    if not os.path.exists(FN_ENV): raise SystemExit(FN_ENV + ' not found — run tools/local-supabase/start-payments.sh first (or set DRUGBOX_FN_ENV)')
    out = {}
    for l in open(FN_ENV).read().splitlines():
        if '=' in l and not l.lstrip().startswith('#'):
            k, v = l.split('=', 1); v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in '"\'': v = v[1:-1].replace('\\"', '"').replace('\\$', '$').replace('\\`', '`').replace('\\\\', '\\')
            out[k.strip()] = v
    return out

def wait_for(fn, timeout=10.0, every=0.25):
    """Poll fn() until it returns something truthy (or the time is up) and return its last value — instead of fixed sleeps."""
    end = time.time() + timeout
    while True:
        v = fn()
        if v or time.time() > end: return v
        time.sleep(every)

def lang_init(ctx):
    """Start the browser context in DX_LANG (the interface keeps the choice in localStorage dx_lang)."""
    if LANG != 'en': ctx.add_init_script("try{localStorage.setItem('dx_lang','%s')}catch(e){}" % LANG)
    return ctx

SCHEMA_ERRORS = ('42703', '42P01', '42883', '42804', '22P02', 'PGRST100', 'PGRST200', 'PGRST202', 'PGRST204', 'PGRST301', 'PGRST302')
def refused(err):
    """A write the database refused or ignored — and NOT one that failed for another reason (renamed column, missing table,
    bad input syntax, expired session), which would otherwise keep a negative check green. err: {code, message} or None.
    None (no error) counts as refused only together with a database check that nothing changed — every caller has one."""
    if not err: return True
    code, msg = str(err.get('code') or ''), str(err.get('message') or '')
    return code not in SCHEMA_ERRORS and not re.search(r'(column|relation|function|table|type|schema)\b[^,;]* does not exist|could not find|JWT|schema cache|invalid input syntax', msg, re.I)
# JavaScript to put after a supabase-js call: the error as {code, message} (or null)
ERR = ".then(r=>r.error?{code:r.error.code||'',message:r.error.message||''}:null)"

def done():
    print(sum(R), '/', len(R))
    sys.exit(0 if R and all(R) else 1)
