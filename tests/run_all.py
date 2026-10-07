"""Run every test suite and exit non-zero if anything failed (for CI and before handing over).
  python3 tests/run_all.py                 # sql + demo + e2e
  python3 tests/run_all.py sql demo        # only some groups: sql | sweep | demo | legacy | stress | demo-full | e2e | migrations
  python3 tests/run_all.py demo demo-full  # every demo check: the quick suites, the legacy suites and the speed A/B
Groups:
  sql    each supabase/tests/*.sql suite (not the stub / sweep) on its OWN fresh database: stub + every migration in order;
         passes when psql exits 0, a "TOTAL n / n" line is printed with both numbers equal, and no line starts with FAIL
  sweep  supabase/tests/schema_sweep.sql on a fresh database: every line must end in "none"
  demo   tests/demo/*.py on the demo build (DEMO_FILE, default web/dist/drugbox.html), in English and Arabic
  legacy tests/demo/legacy suites that check something ("n / n" lines) on the same build — long; not in the default run
  stress page-switching speed A/B: legacy/stress_base.py on BASE_FILE (default web/reference/demo-approved.html) and
         legacy/stress.py on DEMO_FILE, alternated STRESS_ROUNDS times (default 2); passes when the build has no JS errors or
         leftover overlays and its median switch time is at most 25% (+1 ms) slower than the base's — not in the default run
  demo-full  legacy + stress (one command for the long demo checks) — not in the default run
  e2e    tests/e2e/*_test.py against the running local stack (tools/local-supabase/start.sh, and start-payments.sh for e4*)
  migrations  tools/migration_check.py (every migration re-runnable, puts back each policy it creates) — not in the default run
         while older migrations still group several policies in one block
Settings: PGHOST PGPORT PGUSER (psql), DB_PREFIX (rv_runall: databases <prefix>_<suite>, dropped afterwards), DEMO_FILE,
  E2E_SKIP (comma-separated suite names to skip), and the e2e settings in tests/e2e/_dx.py."""
import os, re, sys, glob, time, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PG = ['psql', '-X', '-h', os.environ.get('PGHOST', '/tmp'), '-p', os.environ.get('PGPORT', '5433'), '-U', os.environ.get('PGUSER', 'postgres')]
PREFIX = os.environ.get('DB_PREFIX', 'rv_runall')
DEMO = os.path.abspath(os.environ.get('DEMO_FILE', ROOT + '/web/dist/drugbox.html'))   # suites build file:// URLs from it
MIGRATIONS = sorted(glob.glob(ROOT + '/supabase/migrations/[0-9][0-9][0-9][0-9]_*.sql'))
results = []   # (group, name, ok, seconds, detail)

def run(cmd, timeout=1800, env=None):
    t = time.time()
    try: r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env, cwd=ROOT); out, code = r.stdout + r.stderr, r.returncode
    except subprocess.TimeoutExpired as e: out, code = (e.stdout or b'').decode(errors='replace') + '\nTIMEOUT', 124
    return code, out, time.time() - t

def tally(out):   # the suite's own result line: its last "TOTAL n / m" or "n / m"
    fr = re.findall(r'(?m)(?:TOTAL\s+)?(\d+)\s*/\s*(\d+)\s*$', out or '')
    return f'{fr[-1][0]} / {fr[-1][1]}' if fr else ''

def record(group, name, ok, secs, detail='', out=''):
    results.append((group, name, ok, secs, detail)); print(('PASS  ' if ok else 'FAIL  ') + f'{group:6s} {name:34s} {secs:6.1f}s' + (f'  {tally(out):>9s}' if tally(out) else '') + ('' if ok else '\n      ' + detail.strip().replace('\n', '\n      ')[-1500:]), flush=True)

def fresh_db(name):
    code, out, _ = run(PG + ['-q', '-c', f'drop database if exists {name}', '-c', f'create database {name}'])
    if code: return out
    for f in [ROOT + '/supabase/tests/_local_supabase_stub.sql'] + MIGRATIONS:
        code, out, _ = run(PG + ['-q', '-d', name, '-v', 'ON_ERROR_STOP=1', '-f', f])
        if code: return f'{os.path.basename(f)}: {out[-800:]}'
    return None

def drop_db(name): run(PG + ['-q', '-c', f'drop database if exists {name}'])

def sql_suites():
    for f in sorted(glob.glob(ROOT + '/supabase/tests/*.sql')):
        base = os.path.basename(f)
        if base in ('_local_supabase_stub.sql', 'schema_sweep.sql'): continue
        db = PREFIX + '_' + re.sub(r'\W', '_', base.split('.')[0]); t = time.time()
        err = fresh_db(db)
        if err: record('sql', base, False, time.time() - t, 'database build failed: ' + err); drop_db(db); continue
        code, out, _ = run(PG + ['-d', db, '-v', 'ON_ERROR_STOP=1', '-f', f])
        tot = re.findall(r'TOTAL\s+(\d+)\s*/\s*(\d+)', out); fails = [l for l in out.splitlines() if l.strip().startswith(('FAIL', '❌'))]
        ok = code == 0 and bool(tot) and all(a == b and a != '0' for a, b in tot) and not fails
        record('sql', base, ok, time.time() - t, '\n'.join(fails[:20]) + '\n' + out[-600:] if not ok else '', out)
        drop_db(db)

def sweep():
    db = PREFIX + '_sweep'; t = time.time(); err = fresh_db(db)
    if err: record('sweep', 'schema_sweep.sql', False, time.time() - t, 'database build failed: ' + err); drop_db(db); return
    code, out, _ = run(PG + ['-tA', '-d', db, '-v', 'ON_ERROR_STOP=1', '-f', ROOT + '/supabase/tests/schema_sweep.sql'])
    lines = [l for l in out.splitlines() if l.strip()]
    ok = code == 0 and len(lines) >= 3 and all(l.rstrip().endswith(': none') for l in lines)
    record('sweep', 'schema_sweep.sql', ok, time.time() - t, out if not ok else '', f"{sum(l.rstrip().endswith(': none') for l in lines)} / {len(lines)}"); drop_db(db)

def fractions_ok(out):   # every "n / m" result line has n == m, nothing marked ❌ / FAIL
    fr = re.findall(r'(?m)(\d+)\s*/\s*(\d+)\s*$', out)
    return bool(fr) and all(a == b for a, b in fr) and not re.search(r'(?m)^\s*(❌|FAIL)', out)

def demo():
    if not os.path.exists(DEMO): record('demo', 'build', False, 0, f'{DEMO} not found — python3 web/build/build.py first (or set DEMO_FILE)'); return
    env = {**os.environ, 'DEMO_FILE': DEMO}
    for f in sorted(glob.glob(ROOT + '/tests/demo/*.py')):
        for lang in ('en', 'ar'):
            code, out, s = run([sys.executable, f, lang], env=env)
            record('demo', f'{os.path.basename(f)} {lang}', code == 0 and fractions_ok(out), s, out[-1500:], out)

def legacy():
    import tempfile
    var = tempfile.mkdtemp(prefix='dx_variants_')   # the no-script viewers the lite suites imitate, made from this build
    run([sys.executable, ROOT + '/tests/fixtures/make_demo_variants.py', DEMO, var])
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p: engines = [e for e in ('webkit', 'chromium') if os.path.exists(getattr(p, e).executable_path)]
    if 'webkit' not in engines: print('note: WebKit is not installed here — the lite suites run on Chromium only (python3 -m playwright install webkit)')
    env = {**os.environ, 'DEMO_FILE': DEMO, 'DEMO_VARIANTS': var, 'DX_ENGINES': ','.join(engines)}
    for f in sorted(glob.glob(ROOT + '/tests/demo/legacy/*.py')):
        src = open(f, encoding='utf-8').read()
        if not re.search(r'sum\((R|o for _, ?o in R)\)', src): continue   # audits that print observations only (a11y, perf, stress…) are run by hand
        if 'webkit' in src and 'DX_ENGINES' not in src and 'webkit' not in env['DX_ENGINES']: print('SKIP  legacy ' + os.path.basename(f) + ' (needs WebKit)'); continue
        code, out, s = run([sys.executable, f], env=env)
        record('legacy', os.path.basename(f), code == 0 and fractions_ok(out), s, out[-1500:], out)

def stress():
    import statistics
    base = os.path.abspath(os.environ.get('BASE_FILE', ROOT + '/web/reference/demo-approved.html'))
    if not os.path.exists(DEMO) or not os.path.exists(base): record('stress', 'A/B', False, 0, f'missing {DEMO if not os.path.exists(DEMO) else base}'); return
    env = {**os.environ, 'DEMO_FILE': DEMO, 'BASE_FILE': base}; runs = {'base': [], 'build': []}; t = time.time(); bad = []
    for i in range(max(1, int(os.environ.get('STRESS_ROUNDS', '2')))):   # alternated, so a busy machine slows both sides alike
        for side, f in ((('base', 'stress_base.py'), ('build', 'stress.py')) if i % 2 == 0 else (('build', 'stress.py'), ('base', 'stress_base.py'))):
            code, out, _ = run([sys.executable, ROOT + '/tests/demo/legacy/' + f], timeout=900, env=env)
            med = re.search(r'switch time ms: median ([\d.]+) \| p95 ([\d.]+)', out); er = re.search(r'JS errors: (\d+)', out); lo = re.search(r'leftover overlays: (\d+)', out)
            if code or not (med and er and lo): bad.append(f'{f} did not finish (exit {code}): {out[-600:]}'); continue
            if er.group(1) != '0' or lo.group(1) != '0':   # only the build is judged: an older base may have known errors
                (bad.append if side == 'build' else print)(f'      {side}: {er.group(1)} JS errors, {lo.group(1)} leftover overlays\n{out[-600:]}')
            runs[side].append(float(med.group(1)))
    if runs['base'] and runs['build']:
        b, n = statistics.median(runs['base']), statistics.median(runs['build'])
        detail = f'median switch {n:.1f} ms vs base {b:.1f} ms (runs {runs["build"]} vs {runs["base"]})'; print('      ' + detail)
        if n > b * 1.25 + 1: bad.append('page switching slower than the base: ' + detail)
    elif not bad: bad.append('no timings')
    record('stress', 'stress.py vs stress_base.py', not bad, time.time() - t, '\n'.join(bad))

def demo_full(): legacy(); stress()

def e2e():
    skip = set(filter(None, os.environ.get('E2E_SKIP', '').split(',')))
    for f in sorted(glob.glob(ROOT + '/tests/e2e/*_test.py')):
        name = os.path.basename(f)[:-3]
        if name in skip or name.split('_')[0] in skip: continue
        code, out, s = run([sys.executable, f])
        record('e2e', name, code == 0 and fractions_ok(out), s, out[-1500:], out)

def migrations():
    code, out, s = run([sys.executable, ROOT + '/tools/migration_check.py'])
    record('migr', 'tools/migration_check.py', code == 0, s, out[-3000:])

GROUPS = {'sql': sql_suites, 'sweep': sweep, 'demo': demo, 'legacy': legacy, 'stress': stress, 'demo-full': demo_full, 'e2e': e2e, 'migrations': migrations}
want = sys.argv[1:] or ['sql', 'sweep', 'demo', 'e2e']
for g in want:
    if g not in GROUPS: raise SystemExit(f'unknown group {g!r} — use: ' + ' '.join(GROUPS))
for g in want: GROUPS[g]()
bad = [r for r in results if not r[2]]
print(f'\n{len(results) - len(bad)} / {len(results)} suites passed' + (' — FAILED: ' + ', '.join(f'{g}:{n}' for g, n, *_ in bad) if bad else ''))
sys.exit(1 if bad or not results else 0)
