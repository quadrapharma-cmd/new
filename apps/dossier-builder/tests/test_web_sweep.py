"""Error sweep of the browser edition (web/dist) as claude.ai serves it: every screen of a made-up dossier, in Arabic and in English,
under a page policy as strict as the frame's. Dialogs are never answered (confirm() → false, prompt() → null, print() does nothing),
Claude and the downloads are stand-ins, the Google font answers. Written down, with the screen and the click before it: page errors,
console errors, requests that fail, answers ≥ 400, toasts (and whether they are marked as an error), red alerts, an empty screen,
a screen wider than the window.

  test_every_screen_opens_clean      — every screen, both languages: nothing above may happen (a red alert only where one belongs)
  test_no_screen_is_wider_than_a_phone — the same screens at 390 px: none scrolls sideways
  test_every_button_can_be_clicked   — SWEEP_CLICKS=1 only (minutes): what can be clicked is clicked; refusals with a reason are
                                       allowed, a failure without one is not. Run it before a publish.
Needs `python3 web/build.py` first; skipped when dist is absent."""
import functools, http.server, os, pathlib, socket, threading
import pytest
from fixtures_pdf import make_pdf

pw = pytest.importorskip('playwright.sync_api')
DIST = pathlib.Path(os.environ.get('DB_DIST') or pathlib.Path(__file__).resolve().parents[1] / 'web' / 'dist')      # DB_DIST=<folder>: the page as claude.ai serves it, read back after a publish
pytestmark = pytest.mark.skipif(not (DIST / 'index.html').exists(), reason='web/dist not built')
GPU = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
POLICY = ["default-src 'self'", "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'", "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
          "font-src https://fonts.gstatic.com", "img-src 'self' data: blob:", "connect-src 'self'", "worker-src 'self' blob:", "frame-src 'none'", "object-src 'none'"]

INIT = """
window.__saved = []; window.__toasts = []; window.__bad = []; window.__asked = [];
(() => {
  const sample = async (input, opts) => { window.__asked.push('text'); return { text: '{}', truncated: false }; };
  sample.json = async (input, opts) => { window.__asked.push('json'); return {}; };
  sample.limits = async () => ({ maxPromptBytes: 262144, images: { maxCount: 5, maxInputBytes: 20e6, mediaTypes: ['image/png', 'image/jpeg'] } });
  const downloads = { save: async ({ filename }) => { window.__saved.push(filename); } };
  window.claude = { use: async n => (n === 'sample' ? sample : n === 'downloads' ? downloads : null) };
  window.confirm = () => false; window.prompt = () => null; window.print = () => { window.__toasts.push({ t: Date.now(), bad: true, text: '[window.print() was called: it does nothing inside claude.ai]' }); };
  const seen = () => { const el = document.getElementById('toast'); if (!el) return;
    new MutationObserver(() => { if (!el.hidden && el.textContent) { const last = window.__toasts.at(-1);
      if (!last || last.text !== el.textContent || Date.now() - last.t > 1500) window.__toasts.push({ t: Date.now(), bad: el.classList.contains('bad'), text: el.textContent }); } })
      .observe(el, { childList: true, characterData: true, subtree: true, attributes: true }); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', seen); else seen();
})();
"""
WRAP = """() => { if (window.__wrapped) return; window.__wrapped = true; const f = window.fetch;
  window.fetch = async function (u, o) { const r = await f.apply(this, arguments);
    try { const s = typeof u === 'string' ? u : (u && u.url) || ''; if (r.status >= 400 && s.indexOf('/api/') >= 0) { const c = r.clone(); window.__bad.push({ url: s, method: (o && o.method) || 'GET', status: r.status, body: (await c.text()).slice(0, 400) }); } } catch (e) {}
    return r; }; }"""
STATE = """() => ({ hash: location.hash, alerts: [...document.querySelectorAll('.alert.bad')].filter(a => a.offsetParent).map(a => (a.innerText || '').replace(/\\s+/g, ' ').slice(0, 200)),
  drawer: (d => d && !d.hidden ? (document.getElementById('dTitle').textContent || '') : null)(document.getElementById('drawer')),
  empty: !(document.getElementById('view').innerText || '').trim(), wide: document.documentElement.scrollWidth - window.innerWidth,
  title: ((document.querySelector('#view h1') || {}).innerText || '').trim() })"""
MARK = """() => { let k = 0; const seen = {};
  document.querySelectorAll('#view button, #view a.btn, #view [role=tab], #view summary, #view .chip[data-f], #view [data-go]').forEach(e => {
    delete e.dataset.sweep;
    if (!e.offsetParent || e.disabled) return;
    const sig = e.tagName + '|' + [...e.attributes].map(a => a.name).filter(n => n.startsWith('data-') && n !== 'data-sweep').sort().join(',') + '|' + (e.id || '') + '|' + (e.innerText || '').trim().slice(0, 40);
    seen[sig] = (seen[sig] || 0) + 1;
    if (seen[sig] > 2) return;                                             // two of each kind of button are enough
    e.dataset.sweep = String(k++); });
  return k; }"""
SKIP = ('delete', 'remove', 'حذف', 'مسح السجل', 'logout', 'sign out', 'تسجيل الخروج', 'reset', 'restore', 'استرجاع')      # what would undo the dossier the sweep works on
SCREENS = ('guide', 'tree', 'board', 'prepare', 'office', 'data', 'publisher', 'checks', 'search', 'export', 'audit', 'review', 'review/screening', 'review/workspace',
           'review/letter', 'review/responses', 'review/verdict', 'review/settings')
ALERT_BELONGS = ('export', 'checks', 'review', 'board', 'guide', 'prepare')     # screens that say in red what stops the dossier: that is their work


@pytest.fixture(scope='module')
def site():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()

    class H(http.server.SimpleHTTPRequestHandler):
        extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, '.html': 'text/html; charset=utf-8',
                          '.js': 'text/javascript; charset=utf-8', '.txt': 'text/plain; charset=utf-8'}

        def end_headers(self):
            self.send_header('Content-Security-Policy', '; '.join(POLICY))
            super().end_headers()

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(H, directory=str(DIST)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{port}'
    srv.shutdown()


def sweep(site, tmp_path, lang, width=1440, height=900, clicks=False):
    """→ (events, screens): everything written down on the way, and what each screen was."""
    files = [make_pdf(tmp_path / 'made-up-composition.pdf', 'Composition certificate\nDermacure 20 mg cream (made up)\nExampletine 20 mg'),
             make_pdf(tmp_path / 'made-up-coa.pdf', 'Certificate of Analysis\nProduct: Dermacure 20 mg cream (made up)\nBatch No.: 240101\nAssay 99.6 %')]
    office = pathlib.Path(__file__).parent / 'data' / 'office'
    files += sorted(p for p in office.iterdir() if p.suffix in ('.docx', '.xlsx'))[:2] if office.is_dir() else []
    events, screens, now = [], [], {'where': 'boot', 'click': None}

    def note(kind, text, **more):
        events.append({'kind': kind, 'where': now['where'], 'after': now['click'], 'text': str(text)[:500], **more})
    with pw.sync_playwright() as p:
        b = p.chromium.launch(args=GPU)
        page = b.new_context(viewport={'width': width, 'height': height}).new_page()
        page.on('pageerror', lambda e: note('pageerror', e))
        page.on('console', lambda m: note('console.' + m.type, m.text) if m.type == 'error' else None)
        page.on('requestfailed', lambda r: note('requestfailed', r.url[:200] + ' ' + str(r.failure)))
        page.on('response', lambda r: note('http', f'{r.status} {r.url[:200]}', status=r.status) if r.status >= 400 else None)
        page.route('https://fonts.googleapis.com/**', lambda r: r.fulfill(status=200, content_type='text/css', body='/* fonts */'))
        page.add_init_script(f"localStorage.setItem('db.lang','{lang}')")
        page.add_init_script(INIT)
        page.goto(site + '/index.html#/')
        page.wait_for_selector('#boot', state='detached', timeout=240000)
        page.evaluate('() => DBWEB.ready()')
        page.evaluate(WRAP)
        try:                                                              # the first screen drawn — the state the first look checks, not a second on the clock
            page.wait_for_function("() => (document.getElementById('view').innerText || '').trim()", timeout=60000)      # (a busy machine took longer: 16/11/2026)
        except Exception:
            pass                                                          # still empty after a minute: the look below says so
        page.wait_for_timeout(1000)

        def flush(where):
            st = page.evaluate(STATE)
            for x in page.evaluate('() => window.__toasts.splice(0)'):
                note('toast', x['text'], bad=bool(x.get('bad')))
            for x in page.evaluate('() => window.__bad.splice(0)'):
                note('api', f"{x['method']} {x['url']} → {x['status']} {x['body']}", status=x['status'])
            for a in st['alerts']:
                note('alert', a)
            if st['empty']:
                note('empty', 'the screen is empty')
            if st['wide'] > 2:
                note('wide', f"the screen is {st['wide']} px wider than the window")
            return st

        def settle(ms=400):
            page.wait_for_timeout(ms)
            try:
                page.wait_for_function("() => { const b = document.getElementById('busy'); return !b || b.hidden; }", timeout=60000)
            except Exception:
                note('stuck', 'the working bar did not go away in 60 s')
            page.wait_for_timeout(200)

        def go(route):
            now['where'], now['click'] = route, None
            page.evaluate('r => { location.hash = r; }', '#' + route)
            settle(600)
            st = flush(route)
            screens.append({'route': route, 'title': st['title']})
            return st

        flush('/')
        did = page.evaluate("""async () => (await (await fetch('/api/dossiers', {method: 'POST', headers: {'X-DB': '1', 'Content-Type': 'application/json'},
            body: JSON.stringify({name: 'Dermacure (made up)', profile: {dossier_kind: 'generic', origin: 'local', licence: 'own', activity: 'new', apis: [{name: 'Exampletine', manufacturer: 'Example API Co.', option: 'CEP'}]},
            product: {name: 'Dermacure 20 mg', dosageform: 'cream', manufacturer: 'Example Pharm'}, envelope: {}})})).json()).id""")
        board = page.evaluate("async id => (await (await fetch(`/api/dossiers/${id}/board`)).json())", did)
        slots = [s['slot_id'] for s in board['slots'] if s.get('doc_class') == 'company_technical' and s.get('level') == 'R' and not s['documents']]
        for f, slot in zip(files, slots):
            st = page.evaluate("""async ([id, slot, name, data]) => { const fd = new FormData(); fd.append('file', new File([new Uint8Array(data)], name)); fd.append('meta', '{}');
                return (await fetch(`/api/dossiers/${id}/slots/${encodeURIComponent(slot)}/documents`, {method: 'POST', body: fd})).status; }""", [did, slot, f.name, list(f.read_bytes())])
            if st != 201:
                note('setup', f'{f.name} in {slot}: {st}')
        page.evaluate('() => { window.__bad.splice(0); window.__toasts.splice(0); }')
        routes = ['/', '/dossiers', '/new', '/variations', '/package', '/faults'] + [f'/d/{did}/{v}' for v in SCREENS]
        for r in routes:
            go(r)
            if not clicks:
                continue
            n = page.evaluate(MARK)
            for k in range(n):
                el = page.query_selector(f'[data-sweep="{k}"]')
                if not el:                                                # the screen was drawn again: mark again
                    go(r)
                    page.evaluate(MARK)
                    el = page.query_selector(f'[data-sweep="{k}"]')
                    if not el:
                        continue
                label = (el.inner_text() or el.get_attribute('aria-label') or el.get_attribute('title') or el.get_attribute('id') or '').strip().replace('\n', ' ')[:60]
                href = el.get_attribute('href') or ''
                if any(w in label.lower() for w in SKIP) or href.startswith('http') or el.get_attribute('target') == '_blank':
                    continue
                now['click'] = label or f'#{k}'
                try:
                    el.click(timeout=3000)
                except Exception as e:
                    note('click', f'could not click «{label}»: {str(e)[:120]}')
                    continue
                settle(300)
                st = flush(r)
                if st['drawer'] is not None:                              # what the click opened is looked at, then closed
                    page.keyboard.press('Escape')
                    page.wait_for_timeout(150)
                if page.query_selector('.dbprog'):                        # a program's layer: what it says is kept, then it is closed
                    page.wait_for_timeout(2500)
                    note('program', page.evaluate("() => { const l = document.querySelector('.dbprog'); return (l.querySelector('.dbprog-name').textContent + ' | ' + l.querySelector('.dbprog-status').textContent).replace(/\\s+/g, ' '); }"))
                    for sel in ('.dbprog [data-act="close"]', '.dbprog-ask button', '.dbprog [data-act="close"]'):
                        c = page.query_selector(sel)
                        if c:
                            try:
                                c.click(timeout=1500)
                            except Exception:
                                pass
                            page.wait_for_timeout(300)
                    if page.query_selector('.dbprog'):
                        note('stuck', 'a program layer stayed open')
                        page.evaluate("() => document.querySelectorAll('.dbprog').forEach(x => x.parentNode.removeChild(x))")
                if st['hash'].lstrip('#') != r:
                    go(r)
                    page.evaluate(MARK)
        b.close()
    return events, screens


def said(events):
    seen, out = set(), []
    for e in events:
        key = (e['kind'], e['where'].split('/')[-1], e['text'][:140])
        if key not in seen:
            seen.add(key)
            out.append(f"[{e['kind']}] {e['where']}" + (f" ⟵ «{e['after']}»" if e['after'] else '') + f": {e['text'][:260]}")
    return '\n'.join(out)


def hard(e):
    """What is never right, whatever was clicked."""
    if e['kind'] in ('pageerror', 'requestfailed', 'empty', 'stuck', 'setup'):
        return True
    if e['kind'] == 'console.error':
        return 'Failed to load resource' not in e['text']                 # those are counted by their answer (http / api), below
    if e['kind'] == 'http':
        return '/api/' not in e['text'] or e['status'] >= 500             # a file of the page that is not there; the engine failing
    return e['kind'] == 'api' and e['status'] >= 500


@pytest.mark.parametrize('lang', ['ar', 'en'])
def test_every_screen_opens_clean(site, tmp_path, lang):
    events, screens = sweep(site, tmp_path, lang)
    assert len(screens) == 6 + len(SCREENS) and all(s['title'] or s['route'] in ('/', '/new') for s in screens), screens
    bad = [e for e in events if hard(e) or e['kind'] in ('api', 'http', 'wide') or (e['kind'] == 'toast' and e.get('bad'))
           or (e['kind'] == 'alert' and not any(e['where'].endswith('/' + s) or f'/{s}/' in e['where'] for s in ALERT_BELONGS))]
    assert not bad, said(bad)


def test_no_screen_is_wider_than_a_phone(site, tmp_path):
    events, screens = sweep(site, tmp_path, 'ar', width=390, height=844)
    bad = [e for e in events if hard(e) or e['kind'] == 'wide']
    assert len(screens) == 6 + len(SCREENS) and not bad, said(bad)


@pytest.mark.skipif(not os.environ.get('SWEEP_CLICKS'), reason='set SWEEP_CLICKS=1: it clicks every button of every screen (minutes)')
@pytest.mark.parametrize('lang', ['ar', 'en'])
def test_every_button_can_be_clicked(site, tmp_path, lang):
    events, screens = sweep(site, tmp_path, lang, clicks=True)
    bad = [e for e in events if hard(e)]
    print(said(events))                                                   # with -s: everything the clicks said, to read before a publish
    assert not bad, said(bad)


@pytest.mark.parametrize('lang', ['ar', 'en'])
def test_the_product_file_page_opens_clean(site, lang):
    """«ملف المنتجات» is a second page of the artifact (suite.html): it starts the same engine, and every screen of its menu opens
    without an error, in both languages."""
    events = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch(args=GPU)
        page = b.new_context(viewport={'width': 1440, 'height': 900}).new_page()
        page.on('pageerror', lambda e: events.append(f'pageerror: {e}'))
        page.on('console', lambda m: events.append(f'console: {m.text}') if m.type == 'error' else None)
        page.on('response', lambda r: events.append(f'http {r.status} {r.url}') if r.status >= 400 else None)
        page.route('https://fonts.googleapis.com/**', lambda r: r.fulfill(status=200, content_type='text/css', body='/* fonts */'))
        page.add_init_script(f"localStorage.setItem('db.lang','{lang}')")
        page.add_init_script(INIT)
        page.goto(site + '/suite.html#/')
        page.wait_for_selector('#boot', state='detached', timeout=240000)
        page.evaluate('() => DBWEB.ready()')
        page.evaluate(WRAP)
        page.wait_for_selector('#nav a', timeout=60000)
        assert page.title().startswith('eBOX')
        routes = [h for h in page.evaluate("() => [...document.querySelectorAll('#nav a')].map(a => a.getAttribute('href'))") if h and h.startswith('#')]
        assert len(routes) >= 6, routes
        for r in routes:
            page.evaluate('r => { location.hash = r; }', r)
            page.wait_for_timeout(500)
            page.wait_for_function("() => { const b = document.getElementById('busy'); return !b || b.hidden; }", timeout=60000)
            page.wait_for_timeout(200)
            if not page.inner_text('#view').strip():
                events.append(f'empty: {r}')
            for x in page.evaluate('() => window.__toasts.splice(0)'):
                if x.get('bad'):
                    events.append(f"toast at {r}: {x['text']}")
            for x in page.evaluate('() => window.__bad.splice(0)'):
                events.append(f"api at {r}: {x['method']} {x['url']} → {x['status']} {x['body'][:200]}")
        b.close()
    assert not events, '\n'.join(events)
