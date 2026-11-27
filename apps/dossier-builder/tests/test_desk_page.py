"""The desk page («مكتب eBOX», desk/index.html) in Chromium, with a stand-in for claude.ai's runtime (its database, the «Claude
Code Remote» connector, the asset store): where each request goes — a dossier's own work session first, the desk's scheduled
task (a new session) next, the session the desk was made in last — and what the page shows when none is reachable; the work
session's link; the note while reading Drive folders is not allowed; no error and no sideways scroll on a phone."""
import json
from pathlib import Path

import pytest

pw = pytest.importorskip('playwright.sync_api')
PAGE = Path(__file__).resolve().parents[1] / 'desk' / 'index.html'
MAIN = 'session_01LcrRaPNd7k7FvK6ziA9n4b'

STAND_IN = r"""
(() => {
  window.__calls = []; window.__fail = {}; window.__docs = new Map();
  const docs = window.__docs, listeners = [];
  const copy = (x) => (x === undefined ? undefined : JSON.parse(JSON.stringify(x)));
  const snap = (path) => ({ id: path.split('/').pop(), exists: docs.has(path), data: () => copy(docs.get(path)), metadata: { fromCache: false } });
  const emit = () => setTimeout(() => listeners.forEach((l) => l()), 0);
  window.__seed = (path, data) => { docs.set(path, data); emit(); };
  const doc = (path) => ({
    set: async (data) => { docs.set(path, copy(data)); emit(); },
    get: async () => snap(path),
    onSnapshot(cb) { const l = () => cb(snap(path)); listeners.push(l); setTimeout(l, 0); return () => {}; },
  });
  const query = (coll, order, lim) => ({
    orderBy: (f, dir) => query(coll, [f, dir || 'asc'], lim),
    limit: (n) => query(coll, order, n),
    doc: (id) => doc(coll + '/' + id),
    onSnapshot(cb) {
      const l = () => {
        let ds = [...docs.keys()].filter((p) => p.startsWith(coll + '/') && p.split('/').length === 2).map(snap);
        if (order) ds.sort((a, b) => { const x = a.data()[order[0]] || '', y = b.data()[order[0]] || ''; return (x < y ? -1 : x > y ? 1 : 0) * (order[1] === 'desc' ? -1 : 1); });
        if (lim) ds = ds.slice(0, lim);
        cb({ docs: ds, size: ds.length, empty: !ds.length, metadata: { fromCache: false } });
      };
      listeners.push(l); setTimeout(l, 0); return () => {};
    },
  });
  const db = { doc, collection: (c) => query(c, null, null) };
  const mcp = { callTool: async (server, tool, input) => {
    window.__calls.push({ server, tool, input });
    const code = window.__fail[tool + ':' + (input.session_id || input.trigger_id || '')] || window.__fail[tool];
    if (code) throw { code, message: code };
    return { payload: { ok: true } };
  } };
  const assets = { upload: async (f) => ({ id: 'f'.repeat(32), url: '/_blob/' + 'f'.repeat(32), sizeBytes: f.size, contentType: f.type }) };
  const user = { can: async () => true };
  window.claude = { use: async (n) => ({ db, mcp, assets, user })[n] || null };
})();
"""

RUNNING = {'name': 'ملف للتجربة', 'status': 'running', 'session': 'session_0WorkerTest1', 'created': '2026-11-22T10:00:00Z',
           'updated': '2026-11-22T10:05:00Z', 'stages': {'read': 'done', 'repeats': 'running'}, 'source': {'drive': None, 'uploads': []}}


@pytest.fixture(scope='module')
def browser():
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser, tmp_path):
    html = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,'
            'viewport-fit=cover"><style>:root{color-scheme:light}body{margin:0}[hidden]{display:none!important}</style></head><body>'
            + PAGE.read_text(encoding='utf-8') + '</body></html>')
    f = tmp_path / 'desk.html'
    f.write_text(html, encoding='utf-8')
    pg = browser.new_page(viewport={'width': 390, 'height': 844})
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.add_init_script(STAND_IN)
    pg.errors = errors
    pg.open = lambda: (pg.goto(f.as_uri()), pg.wait_for_function('window.__calls !== undefined'))
    yield pg
    assert not errors, errors
    pg.close()


def seed(pg, path, data):
    pg.evaluate('([p, d]) => window.__seed(p, d)', [path, data])


def calls(pg):
    return pg.evaluate('window.__calls')


def messages(pg):
    return pg.evaluate("[...window.__docs.entries()].filter(([p]) => p.startsWith('messages/')).map(([, d]) => d)")


def test_a_new_dossier_starts_its_own_session(page):
    page.open()
    seed(page, 'config/desk', {'trigger_id': 'trig_0DeskTest1'})
    page.click('nav.tabs button[data-tab="new"]')
    note = page.locator('#nf-drive-state')
    note.wait_for(state='visible')
    assert 'لم تُفعَّل' in note.inner_text()                                     # Drive folders are not read yet
    page.fill('#nf-name', 'ملف للتجربة')
    page.fill('#nf-drive', 'https://drive.google.com/drive/folders/abc123')
    assert page.locator('#nf-country').input_value() == 'EG'                     # Egypt unless another country is chosen
    page.select_option('#nf-country', 'SA')
    page.click('#nf-go')
    page.wait_for_function('window.__calls.length >= 1')
    c = calls(page)
    assert '\nالدولة: SA\n' in c[0]['input']['text']
    d = page.evaluate("[...window.__docs.entries()].find(([p]) => p.startsWith('dossiers/'))[1]")
    assert d['country'] == 'SA'
    assert len(c) == 1 and c[0]['server'] == 'Claude Code Remote' and c[0]['tool'] == 'fire_trigger'
    assert c[0]['input']['trigger_id'] == 'trig_0DeskTest1' and c[0]['input']['text'].startswith('[مكتب eBOX] ملف جديد\nالمعرّف: d-')
    assert 'مجلد Drive: https://drive.google.com/drive/folders/abc123' in c[0]['input']['text']
    page.wait_for_function("[...window.__docs.keys()].some((p) => p.startsWith('messages/'))")
    m = messages(page)
    assert len(m) == 1 and m[0]['delivered'] is True and m[0]['dossier'].startswith('d-')
    assert 'جلسة عمل خاصة به' in page.locator('#nf-msg').inner_text()
    seed(page, 'config/desk', {'trigger_id': 'trig_0DeskTest1', 'drive_read': True})
    page.click('nav.tabs button[data-tab="new"]')
    page.wait_for_timeout(100)
    assert not note.is_visible()


def test_a_dossiers_requests_go_to_its_session(page):
    page.open()
    seed(page, 'config/desk', {'trigger_id': 'trig_0DeskTest1'})
    seed(page, 'dossiers/d-1', RUNNING)
    page.locator('button.card').first.click()
    link = page.locator('a.btn', has_text='جلسة العمل')
    assert link.get_attribute('href') == 'https://claude.ai/code/session_0WorkerTest1'
    page.locator('button.btn', has_text='إيقاف').click()
    page.wait_for_function('window.__calls.length >= 1')
    c = calls(page)[-1]
    assert c['tool'] == 'send_message' and c['input']['session_id'] == 'session_0WorkerTest1' and c['input']['priority'] == 'now'
    assert c['input']['message'].startswith('[مكتب eBOX] إيقاف\nالمعرّف: d-1')
    page.click('nav.tabs button[data-tab="files"]')
    page.locator('button.card').first.click()
    page.locator('button.btn', has_text='اسأل Claude عن هذا الملف').click()
    page.fill('#chat-in', 'عن ملف «ملف للتجربة»: أين وصل؟')
    page.click('#chat-go')
    page.wait_for_function('window.__calls.length >= 2')
    c = calls(page)[-1]
    assert c['tool'] == 'send_message' and c['input']['session_id'] == 'session_0WorkerTest1' and 'priority' not in c['input']
    assert c['input']['message'].startswith('[مكتب eBOX] رسالة\nالمعرّف: d-1\n')


def test_a_session_gone_hands_the_request_to_a_new_one(page):
    page.open()
    seed(page, 'config/desk', {'trigger_id': 'trig_0DeskTest1'})
    seed(page, 'dossiers/d-1', {**RUNNING, 'status': 'stopped'})
    page.evaluate("window.__fail['send_message:session_0WorkerTest1'] = 'tool_error'")
    page.locator('button.card').first.click()
    page.locator('button.btn', has_text='متابعة من حيث توقّف').click()
    page.wait_for_function('window.__calls.length >= 2')
    c = calls(page)
    assert [x['tool'] for x in c] == ['send_message', 'fire_trigger']
    assert c[1]['input']['text'] == c[0]['input']['message'] and c[1]['input']['text'].startswith('[مكتب eBOX] متابعة\nالمعرّف: d-1')


def test_a_general_message_starts_a_session(page):
    page.open()
    seed(page, 'config/desk', {'trigger_id': 'trig_0DeskTest1'})
    page.click('nav.tabs button[data-tab="chat"]')
    page.fill('#chat-in', 'كم ملفًا اكتمل؟')
    page.click('#chat-go')
    page.wait_for_function('window.__calls.length >= 1')
    c = calls(page)
    assert len(c) == 1 and c[0]['tool'] == 'fire_trigger' and c[0]['input']['text'] == '[مكتب eBOX] رسالة\nكم ملفًا اكتمل؟'


def test_without_a_scheduled_task_the_desks_own_session(page):
    page.open()
    page.click('nav.tabs button[data-tab="chat"]')
    page.fill('#chat-in', 'سؤال')
    page.click('#chat-go')
    page.wait_for_function('window.__calls.length >= 1')
    c = calls(page)
    assert len(c) == 1 and c[0]['tool'] == 'send_message' and c[0]['input']['session_id'] == MAIN


def test_nothing_reachable_is_said_and_kept_to_copy(page):
    page.open()
    seed(page, 'config/desk', {'trigger_id': 'trig_0DeskTest1'})
    page.evaluate("window.__fail['fire_trigger'] = 'not_granted'")
    page.click('nav.tabs button[data-tab="chat"]')
    page.fill('#chat-in', 'سؤال')
    page.click('#chat-go')
    page.wait_for_function("[...window.__docs.keys()].some((p) => p.startsWith('messages/'))")
    assert [x['tool'] for x in calls(page)] == ['fire_trigger']                   # the connector refused: no other route tried
    m = messages(page)
    assert m[0]['delivered'] is False and m[0]['carried'] == '[مكتب eBOX] رسالة\nسؤال'
    page.locator('.bubble .meta button').wait_for()
    assert 'لم تصل إلى Claude' in page.locator('.bubble .meta').first.inner_text()
    assert page.locator('#conn-t').inner_text() == 'Claude عبر المحادثة'


def test_no_sideways_scroll_on_a_phone(page):
    page.open()
    seed(page, 'config/desk', {'trigger_id': 'trig_0DeskTest1'})
    seed(page, 'dossiers/d-1', RUNNING)
    for tab in ('files', 'new', 'chat'):
        page.click(f'nav.tabs button[data-tab="{tab}"]')
        page.wait_for_timeout(100)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), tab
    page.click('nav.tabs button[data-tab="files"]')
    page.locator('button.card').first.click()
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
