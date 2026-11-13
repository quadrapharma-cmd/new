"""Opening the browser edition (web/dist). The runtime's own files — about 30 MB — are downloaded once and kept in the browser's
storage: the next opening fetches none of them, a new version fetches only what changed, and anything wrong with that storage
falls back to the network. The loading screen says how far the download is, and when no data has arrived for a while it says so,
with a way to try again — a slow opening never looks like one that is stuck.
Needs `python3 web/build.py`; skipped when dist is absent."""
import http.server, json, pathlib, re, socket, threading, time
import pytest

pw = pytest.importorskip('playwright.sync_api')
DIST = pathlib.Path(__file__).resolve().parents[1] / 'web' / 'dist'
pytestmark = pytest.mark.skipif(not (DIST / 'index.local.html').exists(), reason='web/dist not built')


class Site:
    """The built pages, served with no browser caching (as when a new version is published), every request recorded; a file can
    be held back to make the line go dead."""

    def __init__(self):
        site = self
        self.seen, self.hold, self.block = [], None, None      # hold: a large file stops midway; block: a file does not start

        class Quiet(http.server.SimpleHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def __init__(self, *a, **k):
                super().__init__(*a, directory=str(DIST), **k)

            def log_message(self, *a, **k):
                pass

            def end_headers(self):
                self.send_header('Cache-Control', 'no-store')
                super().end_headers()

            def copyfile(self, source, out):
                site.seen.append(self.path.split('?')[0])
                while site.block and site.block in self.path:
                    time.sleep(0.1)
                n = 0
                while True:
                    buf = source.read(16384)
                    if not buf:
                        break
                    out.write(buf)
                    n += len(buf)
                    while site.hold and site.hold in self.path and n > 200000:
                        time.sleep(0.1)
        s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
        self.srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), Quiet)
        self.srv.daemon_threads = True
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f'http://127.0.0.1:{port}'

    def binaries(self):
        return [p for p in self.seen if p.endswith('.b64.txt')]


@pytest.fixture()
def site():
    s = Site()
    yield s
    s.hold = s.block = None
    s.srv.shutdown()


WATCH = """(() => { window.__boot = []; const note = () => { const s = document.getElementById('bootSub'); if (s && s.textContent && window.__boot[window.__boot.length - 1] !== s.textContent) window.__boot.push(s.textContent); };
  new MutationObserver(note).observe(document, {subtree: true, childList: true, characterData: true}); })();"""


def opened(page):
    page.wait_for_function("() => document.documentElement.dataset.engine && !document.getElementById('boot')", timeout=240000)


def new_page(ctx, errors):
    page = ctx.new_page()
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','en');" + WATCH)
    return page


def test_the_runtime_is_downloaded_once_and_then_read_from_the_device(site):
    manifest = json.loads(re.search(r'const DB_MANIFEST = (\{.*?\});', (DIST / 'assets' / 'engine.worker.js').read_text(encoding='utf-8')).group(1))
    for path, (wire, tag, start, size) in manifest.items():                                 # the list written at build time is the files as they are
        assert (DIST / (path + '.b64.txt')).stat().st_size == wire and len(tag) == 16 and size > 0, path
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1280, 'height': 800})
        errors = []
        page = new_page(ctx, errors)
        page.goto(site.url + '/index.local.html#/')
        opened(page)
        first = site.binaries()
        said = [s for s in page.evaluate("() => window.__boot") if 'بينزّل ملفات التشغيل' in s]       # (the loading screen speaks the page's first language: Arabic)
        assert len(first) >= 20 and said, said                                              # the first time: fetched, and the screen said how far
        assert re.search(r'[\d.]+ من \d+ ميجا — أول مرة بس، بعدها بتتفتح من جهازك', said[-1]), said[-1]
        page.wait_for_timeout(1500)                                                         # the files reach the browser's storage
        site.seen.clear()
        page.reload()
        opened(page)
        assert site.binaries() == [], site.binaries()                                       # the second time: not one of them is fetched…
        assert any('المحفوظة على جهازك — مفيش تنزيل' in s for s in page.evaluate("() => window.__boot"))      # …and the screen says where they came from
        assert page.evaluate("async () => (await (await fetch('/api/health', {headers: {'X-DB': '1'}})).json()).ok") is True
        # a new version changed one file: only that one is fetched (here: what is stored for it no longer matches)
        page.evaluate("""() => new Promise((ok, bad) => { const q = indexedDB.open('db-runtime'); q.onerror = () => bad(q.error);
          q.onsuccess = () => { const t = q.result.transaction('files', 'readwrite'), s = t.objectStore('files');
            s.put({tag: 'an older version', data: new ArrayBuffer(8)}, 'assets/engine.zip');
            s.put({tag: 'left over', data: new ArrayBuffer(8)}, 'assets/pyodide/no-longer-used.whl');
            t.oncomplete = () => ok(); t.onerror = () => bad(t.error); }; })""")
        site.seen.clear()
        page.reload()
        opened(page)
        assert site.binaries() == ['/assets/engine.zip.b64.txt'], site.binaries()
        page.wait_for_timeout(1500)
        keys = page.evaluate("""() => new Promise(ok => { const q = indexedDB.open('db-runtime'); q.onsuccess = () => { const r = q.result.transaction('files').objectStore('files').getAllKeys(); r.onsuccess = () => ok(r.result); }; })""")
        assert sorted(keys) == sorted(manifest) and errors == [], (set(keys) ^ set(manifest), errors)      # what is no part of this version was removed
        b.close()


NO_STORE = """(() => { const open = indexedDB.open.bind(indexedDB);          /* the storage for the runtime's files is closed to the page */
  indexedDB.open = function (name, v) { if (name === 'db-runtime') throw new DOMException('denied', 'SecurityError'); return v === undefined ? open(name) : open(name, v); }; })();
"""


def test_without_that_storage_it_still_opens_from_the_network(site):
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1280, 'height': 800})

        def closed(route):
            r = route.fetch()
            route.fulfill(response=r, body=NO_STORE + r.text())
        ctx.route('**/assets/engine.worker.js', closed)
        errors = []
        page = new_page(ctx, errors)
        for _ in range(2):                                                                  # both openings fetch: nothing could be kept, nothing is broken
            site.seen.clear()
            page.goto(site.url + '/index.local.html#/') if not site.seen and page.url == 'about:blank' else page.reload()
            opened(page)
            assert len(site.binaries()) >= 20
        assert page.evaluate("() => document.documentElement.dataset.engine") == 'worker' and errors == [], errors
        b.close()


def test_a_dead_line_is_said_with_a_way_to_try_again(site):
    site.hold = 'python_stdlib'                                                             # the line goes dead inside one large file
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        errors = []
        page = new_page(b.new_context(viewport={'width': 1280, 'height': 800}), errors)
        page.goto(site.url + '/index.local.html#/', wait_until='commit')
        page.wait_for_selector('#bootHelp:not([hidden])', timeout=120000)
        text = page.inner_text('#boot')
        assert re.search(r'مفيش بيانات وصلت من \d+ ثانية: الاتصال بطيء أو مقطوع', text) and 'حاول تاني' in text, text
        assert re.search(r'بقاله \d+ ثانية', text) and re.search(r'بينزّل ملفات التشغيل: [\d.]+ من \d+ ميجا', text), text      # how long, and how far it got
        site.hold = None                                                                    # the line comes back
        page.click('#bootHelp button')
        opened(page)
        assert errors == [], errors
        b.close()


def test_the_first_moment_already_says_what_is_happening(site):
    """Item 15: even while the runtime's own script is still on its way (held back here), the page is not blank: its first bytes
    say that the program is opening and why the first time takes a minute; the progress screen takes over once it runs."""
    site.block = 'pyodide/pyodide.js'
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        errors = []
        page = new_page(b.new_context(viewport={'width': 390, 'height': 800}), errors)
        page.goto(site.url + '/index.local.html#/', wait_until='commit')
        page.wait_for_selector('#boot0', state='visible', timeout=20000)
        first = page.inner_text('#boot0')
        assert 'بيفتح منشئ ملفات التسجيل' in first and 'Opening Dossier Builder' in first and not page.locator('#boot').count()
        site.block = None
        page.wait_for_selector('#boot', timeout=60000)
        assert page.locator('#boot0').count() == 0                                          # the progress screen replaced it
        opened(page)
        b.close()
