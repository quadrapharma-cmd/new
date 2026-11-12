"""«Make it for me» in the browser edition, where the drafting is done by claude.ai's model inside the page (the `sample`
capability of the artifact runtime, simulated here to its contract: an answer that takes seconds to minutes, streamed text, a
viewer who may decline, plain `{code, message}` rejections). What the model is doing stays on the screen for as long as it takes,
it can be stopped, and when it gives no answer the reason is said and the page is filled from the product data alone.
Needs `python3 web/build.py`; skipped when dist is absent. Made-up data («Dermacure»)."""
import functools, http.server, json, pathlib, socket, threading
import pytest
from test_reading_cases import PROFILE, PRODUCT, ENV

pw = pytest.importorskip('playwright.sync_api')
DIST = pathlib.Path(__file__).resolve().parents[1] / 'web' / 'dist'
pytestmark = pytest.mark.skipif(not (DIST / 'index.local.html').exists(), reason='web/dist not built')

RUNTIME = """(() => {                                           /* the artifact runtime's `sample`, as its contract describes it */
  const ai = window.__ai = {mode: 'ok', calls: 0, opts: null, prompt: ''};
  const answer = {sections: {description: 'Dermacure 2 % cream is a white, homogeneous, smooth cream in an aluminium tube.',
                             composition: {rows: [['Neomycin sulphate', 'Active', 'Ph. Eur.', '3.5 mg', '0.35'], ['White soft paraffin', 'Base', 'Ph. Eur.', '996.5 mg', '99.65']]}},
                  gaps: [{what: 'Overage', why: 'not stated in the documents', ar: 'الزيادة'}], sources: {description: 'specification.pdf'}, notes: ''};
  const sample = async () => ({text: 'x', truncated: false, modelTierApplied: 'default'});
  sample.limits = async () => ({maxPromptBytes: 262144});
  sample.json = (input, opts) => new Promise((resolve, reject) => {
    ai.calls++; ai.prompt = String(input).slice(0, 300); ai.opts = Object.keys(opts || {}).sort();
    const t0 = Date.now(), text = JSON.stringify(answer), sig = opts && opts.signal;
    if (ai.mode !== 'ok') return setTimeout(() => reject({code: ai.mode, message: 'simulated ' + ai.mode}), 400);
    const timer = setInterval(() => {
      const ms = Date.now() - t0;
      if (sig && sig.aborted) { clearInterval(timer); return reject({code: 'cancelled', message: 'aborted'}); }
      if (ms > 2500 && opts && opts.onText) { const n = Math.min(text.length, Math.round((ms - 2500) / 2500 * text.length)); if (n) opts.onText({text: text.slice(0, n), delta: ''}); }
      if (ms > 5200) { clearInterval(timer); resolve(answer); }
    }, 150);
  });
  window.claude = {use: async name => name === 'sample' ? sample : null};
})();"""


@pytest.fixture(scope='module')
def site():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
    handler.log_message = lambda *a, **k: None
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{port}'
    srv.shutdown()


def test_make_it_for_me_says_what_the_model_is_doing_and_why_it_did_not_answer(site):
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': 1440, 'height': 960})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','ar');" + RUNTIME)
        page.goto(site + '/index.local.html#/')
        page.wait_for_function("() => document.documentElement.dataset.engine && !document.getElementById('boot')", timeout=240000)
        did = page.evaluate("""async (a) => { const J = {'X-DB': '1', 'content-type': 'application/json'};
          const did = (await (await fetch('/api/dossiers', {method: 'POST', headers: J, body: JSON.stringify({name: 'Dermacure', profile: a.profile, product: a.product, envelope: a.env})})).json()).id;
          await fetch('/api/dossiers/' + did + '/data', {method: 'PUT', headers: J, body: JSON.stringify({composition: [{name: 'Neomycin sulphate', role: 'active', standard: 'Ph. Eur.', amount: '3.5 mg'}]})});
          return did; }""", {'profile': PROFILE, 'product': PRODUCT, 'env': ENV})
        page.goto(f'{site}/index.local.html#/d/{did}/board')
        page.wait_for_selector('[data-tpl="P-01"]', timeout=60000)
        page.click('[data-tpl="P-01"]')
        page.wait_for_selector('#tplPanel .docprev')
        assert 'موديل claude.ai جوه الصفحة' in page.inner_text('#tplPanel')                       # the page knows the model is here
        stat = lambda: page.inner_text('#dpStat')

        # 1. the model answers after some seconds: thinking, then writing, then the page is filled with what it wrote
        page.click('#dpFill')
        page.wait_for_function("() => /Claude بيقرا المستندات وبيفكّر… \\d+ ثانية/.test(document.querySelector('#dpStat').textContent)", timeout=3000)
        assert 'ممكن ياخد لحد دقيقتين' in stat() and page.is_visible('#dpStop') and page.is_disabled('#dpFill')
        page.wait_for_function("() => /Claude بيكتب… \\d+ حرف/.test(document.querySelector('#dpStat').textContent)", timeout=6000)
        page.wait_for_function("() => document.querySelector('#tplPanel').textContent.includes('white, homogeneous, smooth cream')", timeout=8000)
        assert 'اتملت بموديل claude.ai في الصفحة' in stat() and 'White soft paraffin' in page.inner_text('#tplPanel')
        assert not page.is_visible('#dpStop') and not page.is_disabled('#dpFill')
        ai = page.evaluate("() => window.__ai")
        assert ai['calls'] == 1 and ai['opts'] == ['cache', 'modelTier', 'onText', 'signal'] and ai['prompt'].startswith('You draft one document')

        # 2. stopped by the person: nothing is filled, nothing is asked of the engine instead
        page.click('#dpFill')
        page.wait_for_selector('#dpStop:not([hidden])')
        page.wait_for_timeout(700)
        page.click('#dpStop')
        page.wait_for_function("() => document.querySelector('#dpStat').textContent.includes('اتوقف')", timeout=3000)
        assert not page.is_disabled('#dpFill') and 'white, homogeneous, smooth cream' in page.inner_text('#tplPanel')

        # 3. the viewer did not allow Claude, or its usage ran out: said in words, and the page is filled from the product data alone
        for code, words in (('not_granted', 'Claude ما اتسمحلوش في الصفحة دي'), ('rate_limited', 'وصلت لحد استخدام Claude'), ('invalid_json', 'ما طلعش بالشكل المطلوب')):
            page.evaluate("(m) => { window.__ai.mode = m; }", code)
            page.click('#dpFill')
            page.wait_for_function("(w) => document.querySelector('#dpStat').textContent.includes(w)", arg=words, timeout=20000)
            assert 'الصفحة اتملت من بيانات المنتج بس' in stat(), stat()
            assert 'Neomycin sulphate' in page.inner_text('#tplPanel') and 'white, homogeneous' not in page.inner_text('#tplPanel')
        assert errors == [], errors
        b.close()
