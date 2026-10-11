"""Run every business journey file (tests/journeys/business_*.py) on several targets/languages/widths and write one summary.

  python3 tests/journeys/run_business.py --out DIR [--configs demo:en:1440,demo:ar:1440,demo:en:390,live:en:1440] [--jobs 3]
                                       [--files business_deals.py,…] [--summary DIR/results-business.json]

Live configs use APP_URL and DB_NAME from the environment (tests/e2e/_dx.py). Each file × config writes
DIR/<file>.<target>-<lang>-<width>.json; the summary lists, per journey, every config's PASS / FAIL (step and reason) / N/A,
and a combined demo verdict (PASS only when every demo config passes). Exit code 1 when any journey fails."""
import os, sys, json, glob, argparse, subprocess, time
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/journeys')
    ap.add_argument('--configs', default='demo:en:1440,demo:ar:1440,demo:en:390,live:en:1440')
    ap.add_argument('--jobs', type=int, default=3)
    ap.add_argument('--files', default='')
    ap.add_argument('--summary', default='')
    ap.add_argument('--only', default='')
    ap.add_argument('--no-run', action='store_true', help='only summarise existing result files')
    a = ap.parse_args()
    files = [os.path.join(HERE, f) for f in a.files.split(',') if f] or sorted(glob.glob(os.path.join(HERE, 'business_*.py')))
    configs = [tuple(c.split(':')) for c in a.configs.split(',') if c]
    os.makedirs(a.out, exist_ok=True)
    def run(job):
        f, (t, l, w) = job
        log = os.path.join(a.out, '%s.%s-%s-%s.log' % (os.path.basename(f)[:-3], t, l, w)); t0 = time.time()
        cmd = [sys.executable, f, '--target', t, '--lang', l, '--width', w, '--out', a.out] + (['--only', a.only] if a.only else [])
        with open(log, 'w') as fh: rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT).returncode
        print('%-26s %-5s %s %4s  rc=%d  %3ds' % (os.path.basename(f), t, l, w, rc, time.time() - t0), flush=True)
    if not a.no_run:
        with ThreadPoolExecutor(a.jobs) as ex: list(ex.map(run, [(f, c) for c in configs for f in files]))
    summary = {}
    for f in files:
        for (t, l, w) in configs:
            p = os.path.join(a.out, '%s.%s-%s-%s.json' % (os.path.basename(f)[:-3], t, l, w))
            if not os.path.exists(p): continue
            for r in json.load(open(p)):
                s = summary.setdefault(r['id'], {'id': r['id'], 'title': r.get('title', ''), 'file': os.path.basename(f), 'runs': {}})
                s['runs']['%s-%s-%s' % (t, l, w)] = {k: r.get(k) for k in ('status', 'fail_step', 'fail_text', 'reason')}
    out = []
    for jid in sorted(summary):
        s = summary[jid]; runs = s['runs']
        demo = [(k, v) for k, v in runs.items() if k.startswith('demo-')]
        live = [(k, v) for k, v in runs.items() if k.startswith('live-')]
        def verdict(rs):
            if not rs: return 'not run', None
            if all(v['status'] == 'N/A' for _, v in rs): return 'N/A', None
            bad = [(k, v) for k, v in rs if v['status'] == 'FAIL']
            return ('FAIL', bad[0]) if bad else ('PASS', None)
        s['demo'], dbad = verdict(demo); s['live'], lbad = verdict(live)
        first = dbad if s['demo'] == 'FAIL' else None
        if lbad: s['live_fail_step'] = lbad[1]['fail_step']; s['live_reason'] = lbad[1]['reason']
        if dbad: s['demo_fail_config'] = dbad[0]; s['demo_fail_step'] = dbad[1]['fail_step']; s['demo_reason'] = dbad[1]['reason']
        out.append(s)
    path = a.summary or os.path.join(a.out, 'results-business.json')
    json.dump({'configs': ['%s-%s-%s' % c for c in configs], 'journeys': out}, open(path, 'w'), indent=1, ensure_ascii=False)
    for s in out:
        print('%-12s demo %-5s live %-5s  %s' % (s['id'], s['demo'], s['live'], (s.get('live_reason') or s.get('demo_reason') or '')[:110]))
    print('summary →', path)
    sys.exit(0 if all(s['demo'] in ('PASS', 'N/A') and s['live'] in ('PASS', 'N/A', 'not run') for s in out) else 1)

if __name__ == '__main__': main()
