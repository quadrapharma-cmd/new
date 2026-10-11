"""Journey harness — tests that do the real job of a feature end to end, like a user, and FAIL at the first dead end.

A journey is a function decorated with @journey('J-AREA-NN', applies='both'|'demo'|'live'). It receives a J object and
runs numbered steps:

    @journey('J-SOCIAL-11')
    def publish_text_post(j):
        pg = j.signin()                                # demo: the demo account; live: a fresh account made through the UI
        with j.step('Open the composer from Home'):
            j.click(pg, j.T('What.s on your mind', 'بم تفكر|ماذا يدور'))
        with j.step('Post appears after reload'):
            j.check(cond, 'what is wrong')                # → FAIL at step N: what is wrong
            j.notbuilt('no Edit in the post menu')        # → FAIL at step N: not built: no Edit in the post menu

The first failed step stops the journey; the harness records which step and why, screenshots every open page, and
prints 'J-ID: PASS' or 'J-ID: FAIL at step N: reason'. A journey never passes because something is missing.

Targets (command line or environment):
  --target demo   the standalone demo file (DEMO_FILE, default web/dist/drugbox.html), sample data in the browser
  --target live   the live app at APP_URL with the database DB_NAME (tests/e2e/_dx.py settings: APP_URL, DB_NAME,
                  PGHOST, PGPORT, PGUSER); fresh accounts are signed up through the UI for each journey
  --lang en|ar    interface language (the app keeps it in localStorage dx_lang)
  --width 1440|390  viewport width (390 → 390x844, otherwise 1440x900)
  --out DIR       results: DIR/<file>.<target>-<lang>-<width>.json and failure screenshots DIR/shots/
  --only J-ID,…   run only these journeys
"""
import os, re, sys, json, time, uuid, argparse, traceback
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tests', 'e2e'))
import _dx                                                   # APP_URL, DB_NAME, psql settings, fixtures (one place for the machine)
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

DEMO_FILE = os.path.abspath(os.environ.get('DEMO_FILE', os.path.join(ROOT, 'web', 'dist', 'drugbox.html')))
PW = 'Str0ng-pass!2026'
REGISTRY = []
APP_VISIBLE = "(()=>{const e=document.getElementById('app');return !!e&&e.getClientRects().length>0&&getComputedStyle(e).visibility!='hidden'})()"
LOGIN_VISIBLE = "(()=>{const e=document.getElementById('loginPage');return !!e&&e.getClientRects().length>0&&getComputedStyle(e).visibility!='hidden'})()"
# every toast the page shows is logged in window.__jt (toasts vanish after a few seconds; a journey must still see them)
TOAST_LOG = """(()=>{const log=[];window.__jt=log;const scan=()=>{document.querySelectorAll('#toast,.toast,.dx-toast,[role=status],[role=alert]').forEach(e=>{const t=(e.innerText||'').trim();
  if(t&&e.getClientRects().length&&log[log.length-1]!==t)log.push(t)})};const start=()=>new MutationObserver(scan).observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['class','style']});
  if(document.body)start();else document.addEventListener('DOMContentLoaded',start)})()"""
DEAD_END = re.compile(r"coming soon|opens in the full app|in the mobile app|not available yet|قريبًا|قريبا|في التطبيق", re.I)

class StepFail(Exception): pass
class _Stop(Exception): pass
class _Skip(Exception): pass

def journey(jid, applies='both', title=''):
    def deco(fn):
        REGISTRY.append({'id': jid, 'fn': fn, 'applies': applies, 'title': title or (fn.__doc__ or fn.__name__).strip().split('\n')[0]})
        return fn
    return deco

class _Step:
    def __init__(self, j, text): self.j, self.text = j, text
    def __enter__(self):
        self.j.n += 1; self.t0 = time.time(); self.j.steps.append({'n': self.j.n, 'step': self.text}); return self
    def __exit__(self, et, ev, tb):
        rec = self.j.steps[-1]; rec['secs'] = round(time.time() - self.t0, 1)
        if et is None: rec['ok'] = True; return False
        if et is _Stop: return False
        if et is _Skip: rec['ok'] = None; rec['skipped'] = str(ev); return True
        if et is StepFail: reason = str(ev)
        elif et is PWTimeout: reason = 'timeout: ' + str(ev).split('\n')[0][:200]
        else: reason = 'error: %s: %s' % (et.__name__, str(ev).split('\n')[0][:300])
        rec['ok'] = False; rec['reason'] = reason
        if et is not StepFail: rec['trace'] = ''.join(traceback.format_exception(et, ev, tb))[-1500:]
        self.j.failed = (self.j.n, self.text, reason); self.j._shots()
        raise _Stop()

class J:
    def __init__(self, cfg, browser, jid):
        self.cfg, self.browser, self.id = cfg, browser, jid
        self.target, self.lang, self.width = cfg['target'], cfg['lang'], cfg['width']
        self.live, self.demo, self.ar = self.target == 'live', self.target == 'demo', self.lang == 'ar'
        self.height = 844 if self.width <= 480 else 900
        self.n = 0; self.steps = []; self.failed = None; self.pages = []; self.ctxs = []; self.errors = []; self.shots = []; self.dialogs = []
        self.tag = uuid.uuid4().hex[:8]; self.mails = 0
        self.data = {}                                       # anything a journey wants in its result

    # ---- steps and verdicts -------------------------------------------------------------------------------------------
    def step(self, text): return _Step(self, text)
    def fail(self, reason): raise StepFail(reason)
    def check(self, cond, reason):
        if not cond: raise StepFail(reason)
        return cond
    def notbuilt(self, what): raise StepFail('not built: ' + what)
    def T(self, en, ar): return ar if self.ar else en
    def skip(self, reason):
        """End the current step without a verdict (recorded as skipped) — only for what a target cannot have, e.g. the
        demo keeps no data across a reload (no backend); never for a missing feature."""
        raise _Skip(reason)

    def act(self, pg, el, what, verify, timeout=4, expect=''):
        """Click el (a Locator/ElementHandle) and wait until verify() is truthy. When it never is, fail plainly: a control
        whose only effect is a toast is a dead end; one with no visible effect does nothing."""
        if el is None: self.notbuilt('no visible control "%s"' % what)
        mark = self.toast_mark(pg); seen = []
        el.click(); end = time.time() + timeout
        while True:
            pg.wait_for_timeout(250)
            seen = self.toasts_since(pg, mark)
            try: v = verify()
            except Exception: v = None
            if v: return v
            if time.time() > end: break
        for t in seen:
            if DEAD_END.search(t): self.fail('dead end: "%s" only shows the toast "%s"' % (what, t[:80]))
        if seen: self.fail('dead end: "%s" only shows the toast "%s"%s' % (what, seen[0][:80], (' — expected ' + expect) if expect else ' — nothing else changes'))
        self.fail('"%s" did nothing visible%s' % (what, (' (expected ' + expect + ')') if expect else ''))
    def note(self, k, v): self.data[k] = v

    # ---- browser ------------------------------------------------------------------------------------------------------
    def new_ctx(self, storage_state=None, lang=None):
        kw = {'viewport': {'width': self.width, 'height': self.height}}
        if storage_state: kw['storage_state'] = storage_state
        ctx = self.browser.new_context(**kw); self.ctxs.append(ctx)
        if self.demo: ctx.route(lambda u: not u.startswith(('file:', 'data:', 'blob:')), lambda r: r.abort())
        ctx.add_init_script("try{if(!localStorage.getItem('dx_lang'))localStorage.setItem('dx_lang','%s');localStorage.setItem('dx_tour_done','1')}catch(e){}" % (lang or self.lang))
        ctx.add_init_script(TOAST_LOG)
        try: ctx.grant_permissions(['clipboard-read', 'clipboard-write'])
        except Exception: pass
        return ctx

    def new_page(self, ctx=None, url=None):
        ctx = ctx or self.new_ctx(); pg = ctx.new_page(); self.pages.append(pg)
        pg.on('pageerror', lambda e: self.errors.append('pageerror: ' + str(e)[:200]))
        pg.on('dialog', lambda d: (self.dialogs.append(d.message[:160]), self.errors.append('native dialog: ' + d.message[:120]), d.accept()))
        if url is not False: self.open(pg, url)
        return pg

    @property
    def url(self): return 'file://' + DEMO_FILE if self.demo else _dx.APP_URL

    def open(self, pg, url=None):
        pg.goto(url or self.url, wait_until='load')
        try: self.wait_js(pg, "typeof endSplash==='function'", 15); pg.evaluate('endSplash()')
        except Exception: pass
        pg.wait_for_timeout(400)
        # signed in → the app shows; otherwise the login page
        try: self.wait_js(pg, "(()=>{const v=e=>!!e&&e.getClientRects().length>0&&getComputedStyle(e).visibility!='hidden';return v(document.getElementById('app'))||v(document.getElementById('loginPage'))})()", 15)
        except Exception: pass
        self.settle(pg)
        return pg

    def settle(self, pg, ms=600):
        pg.wait_for_timeout(ms)
        if self.live:
            try: pg.wait_for_load_state('networkidle', timeout=4000)
            except Exception: pass

    def in_app(self, pg):
        return pg.evaluate("(()=>{const e=document.getElementById('app');return !!e&&e.getClientRects().length>0&&getComputedStyle(e).visibility!='hidden'})()")

    def on_login(self, pg):
        return pg.evaluate("(()=>{const e=document.getElementById('loginPage');return !!e&&e.getClientRects().length>0&&getComputedStyle(e).visibility!='hidden'})()")

    def skip_tour(self, pg):
        try:
            if pg.locator('.tour-skip:visible').count(): pg.click('.tour-skip')
        except Exception: pass

    # ---- accounts ------------------------------------------------------------------------------------------------------
    def demo_signin(self, pg):
        pg.click('.lg-demo'); pg.click('#loginPage button.f-btn.dx-js-only')
        self.wait_js(pg, "(()=>{const e=document.getElementById('app');return !!e&&e.getClientRects().length>0})()", 15)
        self.settle(pg, 900); self.skip_tour(pg); return pg

    def email(self, who): return '%s.%s@journey.test' % (re.sub(r'[^a-z]', '', who.lower())[:12] or 'member', self.tag + uuid.uuid4().hex[:4])

    def signup(self, pg, name, email=None, pw=PW, company=None, role=None):
        """Live: create an account through the sign-up form (as a person would) and wait until the app opens as them.
        Returns {'id': uuid, 'local': local numeric id, 'email', 'pw', 'name'}."""
        email = email or self.email(name)
        if not self.on_login(pg): self.open(pg)
        pg.click('#loginPage [onclick="showSignup()"]')
        pg.wait_for_selector('#suName', state='visible', timeout=5000)
        pg.fill('#suName', name); pg.fill('#suEmail', email); pg.fill('#suPw', pw)
        if company is not None and pg.locator('#suCompany').count(): pg.fill('#suCompany', company)
        if role is not None and pg.locator('#suRole').count():
            try: pg.select_option('#suRole', label=role)
            except Exception: pg.select_option('#suRole', index=1)
        pg.click('#signupPage button.f-btn.dx-js-only')
        try: self.wait_js(pg, "window.dxLive&&window.ME&&dxLive.uuidOf&&!!dxLive.uuidOf(ME.id)&&document.getElementById('app').getClientRects().length>0", 20)
        except PWTimeout: raise StepFail('sign-up did not open the app for %s (%s)' % (name, self.text(pg, '#suErr')[:120]))
        self.settle(pg, 800); self.skip_tour(pg)
        me = pg.evaluate("({id:dxLive.uuidOf(ME.id),local:ME.id})")
        return {'id': me['id'], 'local': me['local'], 'email': email, 'pw': pw, 'name': name, 'page': pg}

    def person(self, name, **kw):
        """Live: a new browser context + a fresh account signed up through the UI. Demo: the signed-in demo account."""
        pg = self.new_page(self.new_ctx())
        if self.demo: self.demo_signin(pg); return {'page': pg, 'name': pg.evaluate('ME.name'), 'local': pg.evaluate('ME.id')}
        return self.signup(pg, name, **kw)

    def signin(self, pg, email, pw):
        if not self.on_login(pg): self.open(pg)
        pg.fill('#loginEmail', email); pg.fill('#loginPw', pw); pg.click('#loginPage button.f-btn.dx-js-only')
        try: self.wait_js(pg, "(()=>{const e=document.getElementById('app');return !!e&&e.getClientRects().length>0})()", 15)
        except PWTimeout: raise StepFail('sign-in did not open the app (%s)' % self.text(pg, '#loginErr')[:120])
        self.settle(pg, 900); self.skip_tour(pg); return pg

    def local_of(self, pg, uid):
        """The interface's numeric id for a database person (fetching the person into the page first)."""
        return pg.evaluate("u=>dxLive.aid(u)", uid)

    # ---- database (live) -----------------------------------------------------------------------------------------------
    def sql(self, q):
        try: return _dx.sql(q)
        except SystemExit as e: raise StepFail('database: %s' % str(e)[:240])     # _dx.sql exits the suite; a journey records it
    def sql1(self, q):
        r = self.sql(q); return r.split('\n')[0] if r else ''
    def has_table(self, t): return self.sql1("select to_regclass('public.%s') is not null" % t) == 't'
    def has_column(self, t, c): return self.sql1("select count(*) from information_schema.columns where table_schema='public' and table_name='%s' and column_name='%s'" % (t, c)) == '1'
    def need_table(self, t, what): self.check(self.has_table(t), 'not built: no table public.%s — %s' % (t, what))

    # ---- reading the page ----------------------------------------------------------------------------------------------
    def text(self, pg, sel='#content'):
        try: return pg.evaluate("s=>{const e=document.querySelector(s);return e?e.innerText:''}", sel)
        except Exception: return ''

    def toast_mark(self, pg):
        """A mark for toasts_since: the toasts the page has shown and the native alert()s so far."""
        try: n = pg.evaluate("(window.__jt||[]).length")
        except Exception: n = 0
        return (n, len(self.dialogs))
    def toasts_since(self, pg, mark):
        """Toasts (and native alert() texts) shown since mark."""
        if isinstance(mark, int): mark = (mark, len(self.dialogs))
        try: t = pg.evaluate("m=>(window.__jt||[]).slice(m)", mark[0])
        except Exception: t = []
        return t + ['alert: ' + d for d in self.dialogs[mark[1]:]]

    def toasts(self, pg):
        return pg.evaluate("""()=>[...document.querySelectorAll('#toast.show,.toast.show,.dx-toast,[role=status]')].filter(e=>e.offsetParent!==null||getComputedStyle(e).opacity>0).map(e=>e.innerText.trim()).filter(Boolean)""")

    def wait_js(self, pg, js, timeout=15):
        """Like page.wait_for_function, by polling page.evaluate — the live app's Content-Security-Policy forbids eval,
        which wait_for_function needs. Raises PWTimeout when the expression never becomes truthy."""
        if not self.wait(pg, js, timeout): raise PWTimeout('waited %ds for: %s' % (timeout, js[:120]))
        return True

    def wait(self, pg, js, timeout=8, arg=None):
        """Poll a JS expression (string) in the page until truthy; returns the value (or the falsy last value)."""
        end = time.time() + timeout; v = None
        while True:
            try: v = pg.evaluate(js, arg) if arg is not None else pg.evaluate(js)
            except Exception: v = None
            if v or time.time() > end: return v
            pg.wait_for_timeout(250)

    def wait_db(self, q, timeout=8, want=None):
        end = time.time() + timeout
        while True:
            v = self.sql1(q)
            if (v == want if want is not None else v not in ('', '0', 'f')) or time.time() > end: return v
            time.sleep(0.3)

    def find(self, pg, pattern, scope='#app', kinds='button,a,[role=button],[role=menuitem],[role=option],[onclick],.ctx-item,.ch-dd-item,.pact,label,summary,[tabindex="0"]', exact=False):
        """The visible clickable element whose own text / aria-label / title / placeholder matches pattern (regex);
        the smallest such element. Returns a Locator or None."""
        h = pg.evaluate_handle("""([scope,kinds,pat,exact])=>{const re=new RegExp(pat,'i');const root=document.querySelector(scope)||document;
          const vis=e=>{if(!e.isConnected)return false;const r=e.getBoundingClientRect();if(r.width<2||r.height<2||r.right<=0||r.left>=innerWidth)return false;const s=getComputedStyle(e);return s.visibility!='hidden'&&s.display!='none'&&s.opacity!='0'};
          const lab=e=>((e.getAttribute('aria-label')||'')+' '+(e.getAttribute('title')||'')+' '+(e.innerText||e.value||'')).replace(/\\s+/g,' ').trim();
          const pick=r=>{let best=null,bl=1e9;for(const e of r.querySelectorAll(kinds)){if(!vis(e))continue;const t=lab(e);if(!t)continue;
            const ok=exact?re.test(t)&&t.length<80:re.test(t);if(ok&&t.length<bl){best=e;bl=t.length}}return best};
          /* an open dialog covers the page: what a person can click is inside it */
          const dlg=[...document.querySelectorAll('.dbk-ov,.modal-bg,[role=dialog][aria-modal=true]')].filter(d=>vis(d)&&(root===document||root.contains(d)||d.contains(root)||root===document.body)).pop();
          if(dlg&&!dlg.contains(root))return pick(dlg);
          return pick(root)}""", [scope, kinds, pattern, exact])
        el = h.as_element()
        return el

    def click(self, pg, pattern, scope='#app', what=None, settle=500, **kw):
        """Click the visible control matching pattern; fail as 'not built' when there is none; fail as a dead end when
        the click only shows a 'coming soon'-type toast."""
        el = self.find(pg, pattern, scope, **kw)
        if not el: self.notbuilt('no visible control "%s"%s' % (what or pattern, '' if scope == '#app' else ' in ' + scope))
        mark = self.toast_mark(pg)
        el.scroll_into_view_if_needed(); el.click(); pg.wait_for_timeout(settle)
        self.dead_end(pg, mark, what or pattern)
        return el

    def dead_end(self, pg, before=(), what=''):
        """Fail when a toast shown since `before` (a toast_mark, or a set of toasts) says the feature is not there."""
        new = self.toasts_since(pg, before) if isinstance(before, (int, tuple)) else [t for t in self.toasts(pg) if t not in before]
        for t in new:
            if DEAD_END.search(t): self.fail('dead end: "%s" only shows the toast "%s"' % (what, t[:80]))
        return new

    def nav(self, pg, page):
        """Go to a page the way a person does: the visible top-bar / sidebar / bottom-bar entry for it."""
        el = pg.evaluate_handle("""p=>{const vis=e=>{const r=e.getBoundingClientRect();return r.width>1&&r.height>1&&getComputedStyle(e).visibility!='hidden'&&r.bottom>0&&r.top<innerHeight+2&&r.right>0&&r.left<innerWidth};
            return [...document.querySelectorAll('#app [onclick]')].find(e=>vis(e)&&new RegExp("goto\\\\(['\\"]"+p+"['\\"]\\\\)").test(e.getAttribute('onclick')))||null}""", page).as_element()
        if not el and pg.locator('#sbToggle:visible').count():          # phone: the sidebar opens from its toggle
            pg.click('#sbToggle'); pg.wait_for_timeout(400)
            el = pg.evaluate_handle("""p=>{const vis=e=>{const r=e.getBoundingClientRect();return r.width>1&&r.height>1&&getComputedStyle(e).visibility!='hidden'&&r.bottom>0&&r.top<innerHeight+2&&r.right>0&&r.left<innerWidth};
                return [...document.querySelectorAll('#app [onclick]')].find(e=>vis(e)&&new RegExp("goto\\\\(['\\"]"+p+"['\\"]\\\\)").test(e.getAttribute('onclick')))||null}""", page).as_element()
        if not el: self.notbuilt('no visible navigation entry to "%s" at %dpx' % (page, self.width))
        el.click(); self.settle(pg); return pg

    def reload(self, pg):
        pg.reload(wait_until='load')
        try: self.wait_js(pg, "typeof endSplash==='function'", 15); pg.evaluate('endSplash()')
        except Exception: pass
        try: self.wait_js(pg, "(()=>{const v=e=>!!e&&e.getClientRects().length>0&&getComputedStyle(e).visibility!='hidden';return v(document.getElementById('app'))||v(document.getElementById('loginPage'))})()", 15)
        except Exception: pass
        self.settle(pg, 1200); self.skip_tour(pg); return pg

    def demo_persists(self, what):
        """Demo pages keep only what the demo layers store in the browser; a journey that requires a reload to keep
        state checks it like any other acceptance."""
        return what

    def _shots(self):
        d = os.path.join(self.cfg['out'], 'shots'); os.makedirs(d, exist_ok=True)
        for i, pg in enumerate(self.pages):
            try:
                if pg.is_closed(): continue
                p = os.path.join(d, '%s.%s-%s-%d.p%d.png' % (self.id, self.target, self.lang, self.width, i)); pg.screenshot(path=p); self.shots.append(p)
            except Exception: pass

    def close(self):
        for c in self.ctxs:
            try: c.close()
            except Exception: pass

def main(module_name=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', default=os.environ.get('J_TARGET', 'demo'), choices=['demo', 'live'])
    ap.add_argument('--lang', default=os.environ.get('J_LANG', 'en'), choices=['en', 'ar'])
    ap.add_argument('--width', type=int, default=int(os.environ.get('J_WIDTH', '1440')))
    ap.add_argument('--out', default=os.environ.get('J_OUT', '/tmp/journeys'))
    ap.add_argument('--only', default=os.environ.get('J_ONLY', ''))
    a = ap.parse_args()
    cfg = {'target': a.target, 'lang': a.lang, 'width': a.width, 'out': a.out}
    os.makedirs(a.out, exist_ok=True)
    only = set(x.strip() for x in a.only.split(',') if x.strip())
    name = os.path.splitext(os.path.basename(module_name or sys.argv[0]))[0]
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--no-sandbox'])
        for jd in REGISTRY:
            if only and jd['id'] not in only: continue
            res = {'id': jd['id'], 'title': jd['title'], 'target': a.target, 'lang': a.lang, 'width': a.width}
            if jd['applies'] not in ('both', a.target):
                res.update(status='N/A', reason='journey applies to the %s app only' % jd['applies']); print('%s: N/A (%s only)' % (jd['id'], jd['applies']), flush=True)
                results.append(res); continue
            j = J(cfg, browser, jd['id']); t0 = time.time()
            try: jd['fn'](j)
            except _Stop: pass
            except Exception as e:                           # an error outside a step: count it against the next step
                j.failed = (j.n + 1, '(outside a step)', 'error: %s: %s' % (type(e).__name__, str(e).split('\n')[0][:300])); j._shots()
            finally: j.close()
            res.update(status='FAIL' if j.failed else 'PASS', steps=j.steps, secs=round(time.time() - t0, 1), shots=j.shots, page_errors=j.errors[:10], data=j.data)
            if j.failed: res.update(fail_step=j.failed[0], fail_text=j.failed[1], reason=j.failed[2]); print('%s: FAIL at step %d: %s' % (jd['id'], j.failed[0], j.failed[2]), flush=True)
            else: print('%s: PASS' % jd['id'], flush=True)
            results.append(res)
        browser.close()
    out = os.path.join(a.out, '%s.%s-%s-%d.json' % (name, a.target, a.lang, a.width))
    json.dump(results, open(out, 'w'), indent=1, ensure_ascii=False)
    n_pass = sum(r['status'] == 'PASS' for r in results); n_run = sum(r['status'] != 'N/A' for r in results)
    print('%d / %d journeys pass (%s %s %d) → %s' % (n_pass, n_run, a.target, a.lang, a.width, out))
    sys.exit(0 if n_pass == n_run else 1)
