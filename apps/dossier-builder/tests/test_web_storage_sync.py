"""The browser edition saves its workspace to the browser's storage one save at a time (16/11/2026).
The click sweep found «warning: 2 FS.syncfs operations in flight at once» after «إضافة مستندات»: the save the timer starts after a
request, the wizard's own call once its files are posted and the tab being left each started a save of their own, whatever was
running. Two at once did the work twice and shared the large-file layer's lists of what to read back (the second emptied the
first's). Now a save asked for while another runs waits for it and then runs, for what was written meanwhile; those asked while
one waits share it (web/bigfs.js).
And a save asked for before the engine is up (the tab left while the program opens) threw an error in the page: it now waits.
The first test needs node; the second needs `python3 web/build.py` (skipped when dist is absent), or DB_DIST."""
import http.server, json, os, pathlib, shutil, socket, subprocess, threading
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = pathlib.Path(os.environ.get('DB_DIST') or ROOT / 'web' / 'dist')      # DB_DIST=<folder>: the page as claude.ai serves it, read back after a publish

HARNESS = r"""
const fs = require('fs');
const DB_BIGFS = new Function(fs.readFileSync(process.argv[process.argv.length - 1], 'utf8') + '\nreturn DB_BIGFS;')();
const IDBFS = { storeRemoteEntry: (s, p, e, cb) => cb(null), loadRemoteEntry: (s, p, cb) => cb(null, null) };
const log = [], inFlight = { n: 0, most: 0 };
let fail = 0;
const FS = { syncfs(populate, cb) {                      // as the runtime's: counts the saves in flight, and each takes a while
  inFlight.n++; inFlight.most = Math.max(inFlight.most, inFlight.n);
  const k = log.filter(x => x[0] === 'start').length; log.push(['start', populate, k]);
  setTimeout(() => { inFlight.n--; log.push(['end', populate, k]); cb(fail-- > 0 ? new Error('refused') : null); }, 40);
} };
const sync = DB_BIGFS(IDBFS);
const wait = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const out = {};
  const a = sync(FS, false);                               // a save starts
  await wait(5);
  const b = sync(FS, false), c = sync(FS, false);          // two more asked while it runs: one more save, after it
  out.shared = b === c;
  await Promise.all([a, b, c]);
  out.afterBusy = log.map(x => x[0]).join(',');
  const d = sync(FS, false); await d;                      // nothing running: it starts at once
  out.starts = log.filter(x => x[0] === 'start').length;
  log.length = 0;
  await Promise.all([sync(FS, true), sync(FS, false)]);    // the read at start and a save: one after the other
  out.populate = log.map(x => x[0] + (x[1] ? ':read' : ':save')).join(',');
  log.length = 0; fail = 1;
  const e = sync(FS, false); await wait(5); const f = sync(FS, false);
  out.refused = await e.then(() => 'saved', err => 'refused: ' + err.message);
  out.next = await f.then(() => 'saved', err => 'refused: ' + err.message);      // a refused save does not stop the next one
  out.most = inFlight.most;
  console.log(JSON.stringify(out));
})();
"""


def run_harness(bigfs):
    p = subprocess.run(['node', '-e', HARNESS, str(bigfs)], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.mark.skipif(not shutil.which('node'), reason='node not installed')
def test_saves_of_the_browser_storage_never_run_two_at_once():
    out = run_harness(ROOT / 'web' / 'bigfs.js')
    assert out['most'] == 1, out                                     # never two in flight
    assert out['afterBusy'] == 'start,end,start,end', out            # the two asked during the first: one more save, after it
    assert out['shared'] is True, out
    assert out['starts'] == 3, out
    assert out['populate'] == 'start:read,end:read,start:save,end:save', out
    assert out['refused'] == 'refused: refused' and out['next'] == 'saved', out


@pytest.fixture(scope='module')
def site():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(DIST), **k)

        def log_message(self, *a, **k):
            pass
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), Quiet)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{port}'
    srv.shutdown()


EARLY = """window.__early = 'not asked';
const t = setInterval(() => { if (!window.DBWEB) return; clearInterval(t);
  try { window.DBWEB.sync().then(() => { window.__early = 'saved'; }, e => { window.__early = 'refused: ' + (e && e.message || e); });
        window.__early = 'asked'; }
  catch (e) { window.__early = 'threw: ' + (e && e.message || e); } }, 0);"""


@pytest.mark.skipif(not (DIST / 'index.local.html').exists(), reason='web/dist not built')
@pytest.mark.parametrize('engine', ['worker', 'page'])
def test_the_page_asks_for_saves_at_once_and_before_the_engine_is_up_without_a_fault(site, engine):
    pw = pytest.importorskip('playwright.sync_api')
    seen = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context().new_page()
        page.on('console', lambda m: seen.append(f'console.{m.type}: {m.text}') if m.type in ('error', 'warning') else None)
        page.on('pageerror', lambda e: seen.append(f'pageerror: {e}'))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.add_init_script(EARLY)
        page.goto(site + '/index.local.html' + ('?engine=page' if engine == 'page' else ''))
        page.wait_for_selector('#boot', state='detached', timeout=180000)
        assert page.evaluate("document.documentElement.dataset.engine") == engine
        page.wait_for_function("window.__early !== 'asked' && window.__early !== 'not asked'", timeout=60000)
        assert page.evaluate('window.__early') == 'saved'               # asked while the engine was opening: saved once it was up
        r = page.evaluate("""async () => {
          await fetch('/api/intake/drafts', {method: 'POST', headers: {'X-DB': '1', 'content-type': 'application/json'},
                                             body: JSON.stringify({state: {v: 2, d: {name: 'Dermacure'}}})});
          await Promise.all([DBWEB.sync(), DBWEB.sync(), DBWEB.sync()]);        // three at once, after a write
          await new Promise(r => setTimeout(r, 600));                             // and the save the request's timer starts
          await DBWEB.sync();
          return 'saved'; }""")
        assert r == 'saved'
        b.close()
    assert not [s for s in seen if 'in flight' in s or s.startswith('pageerror')], seen
