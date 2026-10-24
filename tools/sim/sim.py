#!/usr/bin/env python3
"""Drugbox activity simulator — synthetic accounts that use every function of the app, every day, at random times.
A soak / regression / load test for the LOCAL stack and a future STAGING project. It refuses any other target (simlib/safety.py).

    python3 tools/sim/sim.py check                                   # is the target allowed? (prints why not)
    python3 tools/sim/sim.py run --accounts 100 --speed 720           # one simulated day in ~2 minutes, then the report
    python3 tools/sim/sim.py run --accounts 1000 --speed 0 --tag n1000 --timings --ui 24
    python3 tools/sim/sim.py daemon --accounts 100 --speed 1          # every day, in real time, until stopped
    python3 tools/sim/sim.py ui --sample 24                            # only the Playwright driver (≤ 4 browsers)
    python3 tools/sim/sim.py report --day 2026-10-24                    # rebuild a report from the day's log
    python3 tools/sim/sim.py cleanup                                   # delete every simulated account and all its data

Target: APP_URL (default http://localhost:54321/), DB_NAME/PGHOST/PGPORT (local) or STAGING_DB_URL, DRUGBOX_SIM_TARGET
(local | staging), DRUGBOX_SIM_ALLOWED_HOSTS. Payments only through the local Paymob/Fawry stand-in (start-payments.sh).
See docs/SIM.md."""
import argparse, datetime, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from simlib import safety, report  # noqa: E402
from simlib.db import DB, dsn_from_env  # noqa: E402

CAIRO = None


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def anon_key(kind):
    if kind == 'staging':
        k = os.environ.get('DRUGBOX_SIM_ANON_KEY')
        if not k: raise SystemExit('DRUGBOX_SIM_ANON_KEY (the staging anon key) is required')
        return k
    conf = os.path.join(os.environ.get('RUN_DIR', '/tmp'), 'drugbox-pgrst.conf')
    sec = re.search(r'^jwt-secret = "(.*)"$', open(conf).read(), re.M).group(1)
    import base64, hashlib, hmac
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d, separators=(',', ':')).encode()).rstrip(b'=').decode()
    h, p = b({'alg': 'HS256', 'typ': 'JWT'}), b({'role': 'anon', 'iss': 'local', 'iat': 1700000000, 'exp': 2000000000})
    s = base64.urlsafe_b64encode(hmac.new(sec.encode(), ('%s.%s' % (h, p)).encode(), hashlib.sha256).digest()).rstrip(b'=').decode()
    return '%s.%s.%s' % (h, p, s)


def fn_env():
    path = os.environ.get('DRUGBOX_FN_ENV', os.path.join(os.environ.get('RUN_DIR', '/tmp'), 'drugbox-fn.env'))
    if not os.path.exists(path): return {}
    out = {}
    for l in open(path).read().splitlines():
        if '=' in l and not l.lstrip().startswith('#'):
            k, v = l.split('=', 1); v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] == '"': v = v[1:-1].replace('\\"', '"').replace('\\$', '$').replace('\\`', '`').replace('\\\\', '\\')
            out[k.strip()] = v
    return out


def connect():
    url = os.environ.get('APP_URL', 'http://localhost:54321/')
    kind = os.environ.get('DRUGBOX_SIM_TARGET', 'local').strip().lower()
    dsn = dsn_from_env(kind)
    t = safety.check_target(url, db_name=os.environ.get('DB_NAME', 'drugbox_live') if kind == 'local' else None, db_url=dsn if kind == 'staging' else dsn_url(dsn))
    db = DB(dsn, size=12)
    return t, db


def dsn_url(dsn):
    if dsn.startswith('postgres'): return dsn
    kv = dict(p.split('=', 1) for p in dsn.split())
    h = kv.get('host', '')
    return 'postgresql://%s@%s:%s/%s' % (kv.get('user'), '127.0.0.1' if h.startswith('/') else h, kv.get('port'), kv.get('dbname'))


def same_stack(sim, db):
    """The database we check is the one the target writes to: a canary row written through the API must appear in it."""
    acc = sim.admin
    if not acc.ensure(): raise safety.Refused('the sim admin cannot sign in at the target')
    r = acc.get('profiles', 'select=id&id=eq.%s' % acc.uid)
    if not (r.ok and r.data) or not db.val("select 1 from auth.users where id=%s and email=%s", (acc.uid, acc.email)):
        raise safety.Refused('the database the simulator checks is not the target\'s database')


def git_head():
    try: return subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    except Exception: return '?'


def timings(sim, db):
    """tools/scale/timings.py as the busiest simulated member (row-level security on), JSON + text."""
    heavy = db.one("select p.id from public.profiles p join auth.users u on u.id=p.id where u.email like '%%@sim.drugbox.test' and u.email not like 'sim-admin@%%' "
                   "order by (select count(*) from public.connections c where c.requester=p.id or c.addressee=p.id) desc limit 1")
    typical = db.one("select p.id from public.profiles p join auth.users u on u.id=p.id where u.email like '%%@sim.drugbox.test' and u.email not like 'sim-admin@%%' order by p.id limit 1")
    if not heavy: return None
    out = os.path.join(sim.state, 'timings.json')
    env = dict(os.environ, STAGING_DB_URL=dsn_url(db.dsn) if not db.dsn.startswith('postgres') else db.dsn)
    cmd = [sys.executable, os.path.join(ROOT, 'tools', 'scale', 'timings.py'), '--uuid', heavy[0], '--runs', '5', '--json', out]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=900)
    try: data = json.load(open(out))
    except Exception: data = None
    return {'member': heavy[0], 'exit': r.returncode, 'text': (r.stdout + r.stderr)[-6000:], 'json': data}


def cmd_check(a):
    t, db = connect()
    print('OK — target allowed:', json.dumps(t)); print('payments:', safety.check_payments(fn_env(), t))


def build_sim(a):
    from simlib.engine import Sim
    t, db = connect()
    return Sim(a, t, db, anon_key(t['kind']), fn_env(), log), t, db


def cmd_run(a, days=None):
    sim, t, db = build_sim(a)
    log('target %s (%s); payments: %s' % (t['url'], t['kind'], sim.payments[1] if sim.payments[0] else 'OFF — ' + sim.payments[1]))
    before = report.db_snapshot(db)
    t0 = time.time(); st = sim.bootstrap(a.accounts)
    log('accounts: %s (%.0f s)' % (json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in st.items()}), time.time() - t0))
    if st['failed']: log('sign-up failures: %s' % st['failed'][:5])
    same_stack(sim, db)
    date = datetime.date.fromisoformat(a.date) if a.date else datetime.date.today()
    first = not os.path.exists(os.path.join(sim.state, 'days')) or not any(f.endswith('.jsonl') for f in os.listdir(os.path.join(sim.state, 'days'))) or a.first_day
    res = []
    for d in range(days or a.days):
        day = date + datetime.timedelta(days=d)
        path, n, wall = sim.run_day(day, first_day=(first and d == 0), label=('-' + a.tag) if a.tag else '')
        res.append((day, path, n, wall))
        if sim.stopped: break
    ui = None
    if a.ui and not sim.stopped:
        from simlib import ui as uidrv
        ui = uidrv.run(sim, db, a.ui, a.browsers, configs=a.ui_configs.split(','), seed='%s:%s' % (a.seed, date), log=log)
    after = report.db_snapshot(db)
    slow = timings(sim, db) if a.timings else None
    for day, path, n, wall in res:
        write_report(a, sim, t, db, day, path, wall, before, after, slow, ui, st)
    if sim.stopped: raise SystemExit('stopped: ' + sim.stopped)


def write_report(a, sim, t, db, day, path, wall, before, after, slow, ui, st=None):
    recs = report.load(path)
    lags = sorted(r.get('lag_s', 0) for r in recs if r.get('lag_s') is not None)
    meta = {'date': day.isoformat(), 'tag': a.tag, 'target': t['url'], 'target_kind': t['kind'], 'seed': a.seed, 'accounts': a.accounts, 'speed': a.speed,
            'wall_s': wall, 'concurrency': a.concurrency, 'rps': a.rps, 'head': git_head(), 'bootstrap': {k: (v if not isinstance(v, list) else v[:20]) for k, v in (st or {}).items()},
            'lag_p50': report.pct(lags, 50), 'lag_p95': report.pct(lags, 95), 'lag_max': lags[-1] if lags else None, 'db_slow': db.slow[:20], 'bucket_wait_s': round(sim.bucket.waited, 1)}
    out = os.path.join(a.out or os.path.join(ROOT, 'docs', 'sim'), 'report-%s%s' % (day.isoformat(), ('-' + a.tag) if a.tag else ''))
    js = report.write(recs, meta, before, after, out + '.md', out + '.json', slow=slow, ui=ui)
    log('report → %s.md (%s)' % (out, json.dumps(js['totals'])))


def cmd_daemon(a):
    """Run day after day until stopped (Ctrl-C). At speed 1 a day takes a day; the day's report is written at its end."""
    a.first_day = False
    while True:
        cmd_run(a, days=1)
        if a.speed == 1:   # wait for the next Cairo midnight
            from zoneinfo import ZoneInfo
            now = datetime.datetime.now(ZoneInfo('Africa/Cairo')); nxt = (now + datetime.timedelta(days=1)).replace(hour=0, minute=1, second=0)
            time.sleep(max(60, (nxt - now).total_seconds()))
        a.date = None


def cmd_ui(a):
    sim, t, db = build_sim(a)
    st = sim.bootstrap(a.accounts)
    from simlib import ui as uidrv
    res = uidrv.run(sim, db, a.sample, a.browsers, configs=a.ui_configs.split(','), seed='%s:%s' % (a.seed, a.date or datetime.date.today()), log=log,
                    only=a.ui_actions.split(',') if a.ui_actions else None)
    print(json.dumps({k: v for k, v in res.items() if k != 'records'}, indent=1, ensure_ascii=False)[:4000])


def cmd_report(a):
    from simlib.engine import Sim
    t, db = connect()
    sim = Sim(a, t, db, anon_key(t['kind']), fn_env(), log)
    path = os.path.join(sim.state, 'days', '%s%s.jsonl' % (a.day, ('-' + a.tag) if a.tag else ''))
    snap = report.db_snapshot(db)
    write_report(a, sim, t, db, datetime.date.fromisoformat(a.day), path, 0, snap, snap, None, None)


def cmd_catalog(a):
    """The action catalog as a Markdown table (docs/SIM.md), and which journeys it covers."""
    from simlib import catalog, engine  # noqa: F401  (engine imports every action module)
    from simlib.ui import UI_ACTIONS
    print('| action | area | path | who | journeys |'); print('|---|---|---|---|---|')
    for n, x in sorted(catalog.ACTIONS.items(), key=lambda kv: (kv[1].area, kv[0])):
        print('| `%s` | %s | %s | %s%s | %s |' % (n, x.area, x.path, x.who, ' (rare)' if x.rare else '', ' '.join(j.replace('J-', '') for j in x.journeys)))
    for n, (js, w) in sorted(UI_ACTIONS.items()): print('| `%s` | ui | ui | any | %s |' % (n, ' '.join(j.replace('J-', '') for j in js)))
    allj = {'J-%s-%02d' % (a_, i) for a_, k in (('SOCIAL', 51), ('BUSINESS', 49), ('COMMUNITY', 50)) for i in range(1, k + 1)}
    cov = {j for x in catalog.ACTIONS.values() for j in x.journeys} | {j for js, w in UI_ACTIONS.values() for j in js} | {'J-SOCIAL-01'}   # sign-up: the bootstrap
    print('\n%d of %d journeys have an action; without one: %s' % (len(cov & allj), len(allj), ', '.join(sorted(allj - cov)) or 'none'))


def cmd_cleanup(a):
    """Delete every simulated account (e-mail at sim.drugbox.test) and everything it made; the imported test pages too."""
    t, db = connect()
    dom = '%@' + safety.SIM_DOMAIN
    ids = [r[0] for r in db.q("select id from auth.users where email like %s", (dom,))]
    log('%d simulated accounts' % len(ids))
    if not ids: return
    files = db.q("select bucket_id, name from storage.objects where owner = any(%s::uuid[])", (ids,))
    # the server-side clean-up, in one transaction: the deals of the simulated companies and people (a business record that
    # keeps its companies), the pages they own or that were imported for them, their files, then the accounts — every other
    # row that points at a person goes with the account through its foreign key
    db.q("""with co as (select id from public.companies where owner_id = any(%(ids)s::uuid[]) or slug like 'sim-%%'),
              dl as (delete from public.deals where from_user = any(%(ids)s::uuid[]) or from_company_id in (select id from co) or to_company_id in (select id from co) returning id),
              cs as (delete from public.companies where id in (select id from co) returning id),
              tc as (delete from public.training_courses where title like '%%(simulated)' returning id),
              gr as (delete from public.groups where created_by = any(%(ids)s::uuid[]) returning id),
              so as (delete from storage.objects where owner = any(%(ids)s::uuid[]) returning 1)
         select (select count(*) from dl), (select count(*) from cs), (select count(*) from tc), (select count(*) from gr), (select count(*) from so)""", {'ids': ids})
    db.q("delete from auth.users where id = any(%s::uuid[])", (ids,))
    store = os.environ.get('STORE_DIR', '/tmp/drugbox-storage')
    gone = 0
    if t['kind'] == 'local':
        for b, n in files:
            f = os.path.join(store, b, n)
            if os.path.realpath(f).startswith(os.path.realpath(store) + os.sep) and os.path.exists(f): os.remove(f); gone += 1
    left = db.val("select count(*) from public.profiles where id = any(%s::uuid[])", (ids,))
    log('deleted: accounts %d, files %d; profiles left: %s' % (len(ids), gone, left))
    reg = os.path.join(HERE, 'state')
    log('registry kept in %s (delete it by hand if you want the passwords gone too)' % reg)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('check', 'run', 'daemon', 'ui', 'report', 'cleanup', 'catalog'):
        p = sub.add_parser(name)
        p.add_argument('--seed', default=os.environ.get('DRUGBOX_SIM_SEED', 'drugbox-sim-1'))
        p.add_argument('--accounts', type=int, default=100)
        p.add_argument('--state', default=None, help='registry and day logs (default tools/sim/state/<target>)')
        p.add_argument('--concurrency', type=int, default=12, help='API driver threads (bounded)')
        p.add_argument('--rps', type=int, default=150, help='global request rate limit (requests per second)')
        p.add_argument('--speed', type=float, default=720, help='how many times faster than real time (0 = as fast as possible)')
        p.add_argument('--scale', type=float, default=1.0, help='multiply every intensity (actions per day)')
        p.add_argument('--date', default=None); p.add_argument('--days', type=int, default=1); p.add_argument('--tag', default='')
        p.add_argument('--first-day', action='store_true', help='plan the set-up actions again (profiles, companies, teams)')
        p.add_argument('--out', default=None); p.add_argument('--timings', action='store_true')
        p.add_argument('--ui', type=int, default=0, help='UI-driver actions after the API day'); p.add_argument('--sample', type=int, default=16)
        p.add_argument('--browsers', type=int, default=4); p.add_argument('--ui-configs', default='en-1440,ar-1440,en-390,ar-390')
        p.add_argument('--ui-actions', default='', help='only these UI actions (comma-separated), e.g. ui.logout')
        p.add_argument('--day', default=datetime.date.today().isoformat())
    a = ap.parse_args()
    a.browsers = max(1, min(4, a.browsers))   # never more than 4 browsers
    a.concurrency = max(1, min(64, a.concurrency))
    try:
        {'check': cmd_check, 'run': cmd_run, 'daemon': cmd_daemon, 'ui': cmd_ui, 'report': cmd_report, 'cleanup': cmd_cleanup, 'catalog': cmd_catalog}[a.cmd](a)
    except safety.Refused as e:
        print(e.code, file=sys.stderr); sys.exit(3)


if __name__ == '__main__':
    main()
