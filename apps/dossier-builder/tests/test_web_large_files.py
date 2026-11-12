"""Large files in the browser edition (web/dist), where the workspace lives in the browser's own storage.
- The browser refuses one stored value over about 127 MB, and a refused value used to stop every save after it: a file larger than
  that is kept (as a Blob) and is there, byte for byte, when the page is opened again.
- The browser's storage is the only ceiling left, so it is never hit in silence: a save the browser refuses is said on the screen for
  as long as it is true, and a file the storage has no room for leaves the wizard's draft again — so everything else keeps being saved.
Needs `python3 web/build.py`; skipped when dist is absent. Made-up data («Dermacure»)."""
import hashlib, http.server, pathlib, socket, struct, threading
import pytest

pw = pytest.importorskip('playwright.sync_api')
DIST = pathlib.Path(__file__).resolve().parents[1] / 'web' / 'dist'
pytestmark = pytest.mark.skipif(not (DIST / 'index.local.html').exists(), reason='web/dist not built')
H = "{headers: {'X-DB': '1'}}"


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


def scan_pdf(path, label, mb):
    """A real one-page PDF that weighs `mb` megabytes (a stream of bytes that do not repeat rides in it, as the pictures of a scan do)."""
    block = bytes(range(256)) * 4096
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>', None,
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>', None]
    stream = b'BT /F1 14 Tf 72 770 Td (' + label.encode('latin-1') + b') Tj ET'
    objs[3] = b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream'
    body = b''.join(block[:-4] + struct.pack('>I', i) for i in range(mb))
    objs[5] = b'<< /Length %d >>\nstream\n' % len(body) + body + b'\nendstream'
    out, offs = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n'), []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b'%d 0 obj\n' % i + o + b'\nendobj\n'
    x = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1) + b''.join(b'%010d 00000 n \n' % o for o in offs)
    out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, x)
    path.write_bytes(bytes(out))
    return path


def opener(ctx, site, errors):
    def open_(hash_):
        page = ctx.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.goto(site + '/index.local.html' + hash_)
        page.wait_for_selector('#boot', state='detached', timeout=180000)
        return page
    return open_


def test_a_file_over_the_browsers_ceiling_for_one_value_is_kept(site, tmp_path):
    f = scan_pdf(tmp_path / 'Dermacure stability scans 2019-2024.pdf', 'Stability Study Report - Dermacure', 140)
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1280, 'height': 800})
        errors = []
        open_ = opener(ctx, site, errors)
        page = open_('#/')
        page.evaluate("() => { const i = document.createElement('input'); i.type = 'file'; i.id = 'bigin'; document.body.appendChild(i); }")
        page.set_input_files('#bigin', str(f))                                           # a real file of the device, as a person's is
        got = page.evaluate("""async () => {
          const post = (path, body, json) => fetch(path, {method: 'POST', headers: json ? {'X-DB': '1', 'content-type': 'application/json'} : {'X-DB': '1'}, body});
          const dr = (await (await post('/api/intake/drafts', JSON.stringify({state: {step: 0}}), true)).json()).id;
          const fd = new FormData(); fd.append('file', document.querySelector('#bigin').files[0]); fd.append('kind', 'stability');
          const r = await post('/api/intake/drafts/' + dr + '/files', fd);
          const j = await r.json();
          await DBWEB.sync();                                                            // throws if the browser refuses the save
          const db = await new Promise((ok, bad) => { const q = indexedDB.open('/workspace'); q.onsuccess = () => ok(q.result); q.onerror = () => bad(q.error); });
          const all = await new Promise((ok, bad) => { const q = db.transaction('FILE_DATA').objectStore('FILE_DATA').getAll(); q.onsuccess = () => ok(q.result); q.onerror = () => bad(q.error); });
          return {dr, status: r.status, size: j.size, sha: j.sha256, blobs: all.filter(e => e.contents instanceof Blob).map(e => e.contents.size), note: !!document.getElementById('dbStorage')}; }""")
        assert got['status'] == 201 and got['size'] == f.stat().st_size and got['sha'] == sha
        assert got['blobs'] == [f.stat().st_size] and not got['note']                    # stored as a Blob: no ceiling of one value in its way
        page.close()
        page = open_('#/dossiers')                                                       # the page closed and opened again
        page.wait_for_selector('#draftBox', timeout=120000)
        assert '\t1\t' in page.inner_text('#draftBox')                                  # the draft, with its one document, is in the projects list
        back = page.evaluate("""async (dr) => { const r = await fetch('/api/intake/drafts/' + dr + '/files/' + encodeURIComponent('Dermacure stability scans 2019-2024.pdf'), %s);
          const d = await r.arrayBuffer(); if (!r.ok) return {status: r.status, why: new TextDecoder().decode(d).slice(-700)}; return {status: r.status, size: d.byteLength, sha: [...new Uint8Array(await crypto.subtle.digest('SHA-256', d))].map(x => x.toString(16).padStart(2, '0')).join('')}; }""" % H, got['dr'])
        assert back == {'status': 200, 'size': f.stat().st_size, 'sha': sha}             # every byte of it
        assert errors == [], errors
        b.close()


FULL = """(() => { const put = IDBObjectStore.prototype.put;          /* a storage with no room for anything over 8 MB */
  IDBObjectStore.prototype.put = function (v, k) { const c = v && v.contents, n = c ? (c.size !== undefined ? c.size : c.byteLength) : 0;
    if (n > 8e6) { try { this.transaction.abort(); } catch (e) {} throw new DOMException('The quota has been exceeded.', 'QuotaExceededError'); }
    return put.call(this, v, k); }; })();
"""


def test_a_full_browser_storage_is_said_and_the_rest_is_still_saved(site, tmp_path):
    f = scan_pdf(tmp_path / 'Dermacure stability scans.pdf', 'Stability Study Report - Dermacure', 12)
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1280, 'height': 800})

        def full(route):
            r = route.fetch()
            route.fulfill(response=r, body=FULL + r.text())
        ctx.route('**/assets/engine.worker.js', full)
        errors = []
        open_ = opener(ctx, site, errors)
        page = open_('#/new')
        page.wait_for_selector('#intakeBtn', timeout=120000)
        with page.expect_file_chooser() as fc:
            page.click('#intakeBtn')
        fc.value.set_files(str(f))
        page.wait_for_selector('[data-unkept]', timeout=120000)                          # said on the document's own line, and it stays there
        line = page.inner_text('[data-docline="Dermacure stability scans.pdf"]')
        assert 'Not kept in the draft' in line and 'storage has no room' in line and 'until you close this page' in line
        page.wait_for_function("() => S.wiz && Object.keys(S.wiz.texts || {}).length === 1", timeout=120000)          # the document is still read and used in this visit
        page.wait_for_function("() => !document.getElementById('dbStorage')", timeout=30000)                         # the saves after it go through: no warning left
        state = page.evaluate("async () => ({drafts: (await (await fetch('/api/intake/drafts', %s)).json()).map(d => d.files), here: S.wiz.allFiles.map(x => x.name)})" % H)
        assert state == {'drafts': [0], 'here': ['Dermacure stability scans.pdf']}       # out of the draft, still in the page
        # the warning itself: a file that sits in the workspace with no room for it in the storage
        dr = page.evaluate("() => S.wiz.draftId")
        page.evaluate("""async (dr) => { const fd = new FormData(); fd.append('file', S.wiz.allFiles[0]); fd.append('kind', 'other');
          await fetch('/api/intake/drafts/' + dr + '/files', {method: 'POST', headers: {'X-DB': '1'}, body: fd}); }""", dr)
        page.wait_for_selector('#dbStorage', timeout=30000)
        note = page.inner_text('#dbStorage')
        assert 'refused to save' in note and 'is full' in note and 'not being saved' in note and 'Try saving again' in note
        page.click('#dbStorage button')                                                  # still no room: the warning stays
        page.wait_for_timeout(1500)
        assert page.is_visible('#dbStorage')
        page.evaluate("(dr) => fetch('/api/intake/drafts/' + dr + '/files/' + encodeURIComponent('Dermacure stability scans.pdf'), {method: 'DELETE', headers: {'X-DB': '1'}})", dr)
        page.wait_for_function("() => !document.getElementById('dbStorage')", timeout=30000)                         # the large file removed: saved again, the warning goes by itself
        page.close()
        page = open_('#/dossiers')                                                       # the draft itself was saved all along (what was read from the document with it)
        assert page.evaluate("async () => (await (await fetch('/api/intake/drafts', %s)).json()).map(d => [d.files, Object.keys(d.state.texts || {})])" % H) == [[0, ['Dermacure stability scans.pdf']]]
        assert not page.query_selector('#dbStorage')
        assert errors == [], errors
        b.close()
