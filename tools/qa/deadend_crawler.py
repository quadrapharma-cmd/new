#!/usr/bin/env python3
"""Drugbox dead-end crawler — does every visible control lead somewhere?

Opens a target (the standalone demo file, or the live app URL with a freshly signed-up account), signs in, visits every
page reachable from the navigation, and on each page clicks every visible interactive element — buttons, links,
[onclick], role=button/tab, cards made clickable from script (outermost cursor:pointer) — one at a time from a fresh
page state, then classifies what happened (see tools/qa/README.md for the full list):

  fine:      navigated · dialog (with content) · dialog_confirm · changed (in place) · focused_input · closed · validation
             · already_active · disabled · new_window · clipboard · share · print · download · file_picker · left_app
  dead ends: no_effect · toast_only · placeholder_toast ("coming soon"…) · placeholder_href (#p-need…) · dialog_empty
             · dialog_thin (a large panel with almost nothing in it, or a card's detail that shows nothing the card did
             not already show) · confirm_no_effect · alert_only · wrong_item · network_error (live) · js_error
             · family_partial ("only the first 2 of 9 respond") · family_wrong_detail (cards open another item's detail)
             · family_same_detail (every card opens the same template)
  warnings:  self_only · stored_only · request_only · needs_input · unsaved_change (live) · click_failed · console_error

Elements revealed by a click (dialog contents, menus, tab panels) are clicked too — one level deep — by replaying the
opening click from a fresh state each time; identical reveals (the same panel opened by every card) are crawled once.

Fresh state: before every click the whole visible DOM must equal the snapshot taken right after a clean sign-in and
navigation to the page (background noise such as clocks is learned and ignored; toasts are ignored). Cheapest first:
nothing changed → click; otherwise close dialogs and navigate to the page again; otherwise reload in a brand-new browser
context (empty storage) and sign in again.

Limits (all reported, never silent — every element not clicked appears under "Skipped" with its reason):
  --family-sample K  repeated elements of one family (same tag/class/handler shape; cards: same look, whatever their
                     handler): K are clicked — the first three, the middle, the last two.
  --max-per-page N   at most N elements per page (after sampling), in document order.
  --reveal-cap N     at most N revealed elements per distinct dialog/menu; --max-depth2 N per page in total.
  --max-views N      pages per configuration (the navigation plus one more navigation step, e.g. a company page).
  --view-timeout S   seconds per page and configuration.
  The first configuration (default en-1440) uses these limits; the others (en-390, ar-1440, ar-390) use the lighter
  --secondary-* limits unless --full. Navigation (top bar, side menu, phone menu) is never sampled or capped.
  Never clicked: sign-out, external links (another site, mailto:, tel:).

Output: <out>/crawl.json (every click, every skip, run settings) and <out>/crawl.md (by page, dead ends first).
Exit code: 1 when a JS error was seen or a dead end is not in the allow-list (tools/qa/deadend_allow.json — the owner
approves entries); 0 otherwise; 2 when the crawler itself could not run.

Examples:
  python3 tools/qa/deadend_crawler.py --target web/dist/drugbox.html --out /tmp/crawl
  python3 tools/qa/deadend_crawler.py --target http://localhost:54321/ --out /tmp/crawl-live
  python3 tools/qa/deadend_crawler.py --target web/dist/drugbox.html --langs en --widths 1440 --pages groups
"""
import argparse, concurrent.futures as cf, hashlib, json, os, re, sys, time, traceback, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

# ---------------------------------------------------------------- app knowledge (the only Drugbox-specific part)
APP = {
    'content_sel': '#content',
    'toast_sel': '#toast, .dbk-toast, #dxOk, #dxUndo, .toast',
    'cand_sel': 'a[href], button, [onclick], [role=button], [role=tab], [role=link], [role=menuitem], [role=switch], '
                '[role=checkbox], [data-tab], summary, label[for], input[type=checkbox], input[type=radio], select',
    'ignore_sel': '#splash, #authWrap, #dxTour, #dxLiteGo',
    'title_sel': '[class*=title], [class*=name], h1, h2, h3, h4, strong, b',
    'state_classes': r'^(active|show|on|open|selected|checked|expanded|is-|dbk-new|liked|saved|joined|following|done|current)',
    'noise_classes': r'(hover|ripple|press|focus|tilt|anim|pulse|blink|lx-|flash|shake|enter|leave|fade)',
    'storage_noise': r'^(sb-|dx-auth|dx_scroll|dx_last|dx_seen|dx_perf|dx_tour|dx_lang|dx_theme|dx_t_)',
    'overlay_min_area': 0.02,
    'busy_sel': '#dxLoader.on',   # the app's full-screen loader: wait for it to go before clicking
    # a view = the page plus the shape of what is shown in #content (a company page inside "companies" is its own view)
    'view_key_js': r"""(function(){var c=document.querySelector('#content');var p=document.body.getAttribute('data-page')||'?';
        if(!c)return p;var k=[].filter.call(c.children,function(e){return e.getClientRects().length&&e.tagName!=='FOOTER'&&!/dx-sr|dx-ill/.test(e.className)})
        .map(function(e){return e.id||String(e.className).split(' ').filter(function(x){return x&&!/^(active|show|on|open)$/.test(x)}).slice(0,2).join('.')}).join('+');
        if(p==='profile'&&window.ME){var n=c.querySelector('.profile-info');if(n&&ME.name&&n.innerText.indexOf(ME.name)<0)k+=':other'}
        return p+'/'+k})()""",
    # soft reset: back to the start page without reloading (the navigation path of the view is replayed after it)
    'home_js': "typeof goto==='function'&&goto(window.__qaStart||'feed')",
    'signout_re': r'log ?out|sign ?out|doLogout|تسجيل الخروج|خروج',
    'close_re': r'^(×|✕|x|close|cancel|back|done|ok|got it|not now|later|dismiss|skip|إغلاق|اغلاق|إلغاء|الغاء|رجوع|تم|حسنا|لاحقا|تخطي)$|close|cancel|إغلاق|إلغاء',
    'confirm_re': r'confirm|yes|leave|delete|remove|sure|continue|submit|save|send|post|publish|apply|pay|join|invite|create|تأكيد|نعم|مغادرة|حذف|إزالة|متابعة|حفظ|إرسال|نشر|تقديم|ادفع|انضم|دعوة|إنشاء',
    'placeholder_re': r'coming soon|soon\b|not (yet )?available|in the (full|mobile) app|opens in the|under construction|placeholder|'
                      r'قريب|قريبًا|قريباً|غير متاح|في التطبيق|التطبيق الكامل',
    'validation_re': r'empty|required|please (enter|fill|write|type|choose|select|add)|give (your|it|the) .{0,20}name|at least \d|invalid|'
                     r'^(add|enter|choose|select|write|type) (the|a|an|your)\b|is missing|'
                     r'مطلوب|فارغ|من فضلك|يرجى|اكتب|أدخل|ادخل|أضف|اختر',
    'submit_re': r'send|submit|post|publish|save|reply|comment|apply|search|create|invite|add|confirm|continue|next|➤|'
                 r'إرسال|نشر|حفظ|رد|تعليق|بحث|إنشاء|دعوة|أضف|إضافة|تأكيد|متابعة|التالي|submit\w*\(|send\w*\(|post\w*\(',
    # live: a control whose own label is one of these actions must reach the server when it changes the screen
    'action_re': r'^\W*(\+\s*)?(join|follow|connect|like|save|accept|subscribe|enroll|apply|send|post|unfollow|remove|delete|'
                 r'انضم|متابعة|تابع|تواصل|إعجاب|حفظ|قبول|اشترك|سجل|تقديم|إرسال|نشر|حذف|إزالة)\b',
    'placeholder_href_re': r'^#p-|^#need|^javascript:\s*void|^#todo',
}
SEVERITY = {
    'js_error': 'fail', 'no_effect': 'fail', 'dialog_empty': 'fail', 'dialog_thin': 'fail', 'confirm_no_effect': 'fail',
    'toast_only': 'fail', 'placeholder_toast': 'fail', 'placeholder_href': 'fail', 'network_error': 'fail',
    'wrong_item': 'fail', 'family_partial': 'fail', 'family_same_detail': 'fail', 'family_wrong_detail': 'fail', 'alert_only': 'fail',
    'self_only': 'warn', 'stored_only': 'warn', 'request_only': 'warn', 'click_failed': 'warn', 'console_error': 'warn',
    'unsaved_change': 'warn', 'unstable_page': 'warn', 'needs_input': 'warn',
}
OK_KINDS = {'disabled', 'already_active', 'validation', 'navigated', 'left_app', 'new_window', 'download', 'file_picker', 'clipboard', 'share', 'print', 'dialog',
            'dialog_confirm', 'changed', 'focused_input', 'closed', 'native_dialog'}


def sev(kind):
    return SEVERITY.get(kind, 'ok')


def sha(s, n=10):
    return hashlib.sha1(s.encode('utf-8')).hexdigest()[:n]


def nrm(s):
    return re.sub(r'[^0-9a-z؀-ۿ]+', '', (s or '').lower())


# ---------------------------------------------------------------- browser session
class Session:
    def __init__(self, pw, opts, cfg, account=None):
        self.pw, self.o, self.cfg, self.account = pw, opts, cfg, account
        self.browser = pw.chromium.launch(args=['--no-sandbox'])
        self.ctx = self.pg = None
        self.errors, self.console, self.reqs, self.popups, self.downloads, self.choosers, self.dialogs = [], [], [], [], [], [], []
        self.hard_resets = self.soft_resets = self.reuse = 0
        self.notes = []
        lib = opts.get('lib') or open(os.path.join(HERE, 'qa_lib.js'), encoding='utf-8').read()   # read once per run
        jcfg = dict(APP)
        jcfg['seed'] = 1234567 if opts['mode'] == 'demo' else 0
        # the view function is part of the injected script (no eval: the live app's CSP forbids it)
        self.lib = lib.replace('__QA_CFG__', json.dumps(jcfg)).replace('__QA_VIEW__', APP['view_key_js'])

    def close(self):
        try: self.browser.close()
        except Exception: pass

    def new_context(self):
        if self.ctx:
            try: self.ctx.close()
            except Exception: pass
        w = self.cfg['width']
        kw = dict(viewport={'width': w, 'height': 900 if w > 500 else 844}, locale='ar-EG' if self.cfg['lang'] == 'ar' else 'en-US',
                  timezone_id='Africa/Cairo', accept_downloads=False)
        if w < 500: kw.update(is_mobile=True, has_touch=True, device_scale_factor=1)
        self.ctx = self.browser.new_context(**kw)
        self.ctx.add_init_script("try{localStorage.setItem('dx_lang','%s');localStorage.setItem('dx_tour_done','1')}catch(e){}" % self.cfg['lang'])
        self.ctx.add_init_script(self.lib)
        if self.o['mode'] == 'demo':   # offline: the demo must not depend on the network
            self.ctx.route(lambda u: not u.startswith(('file:', 'data:', 'blob:')), lambda r: r.abort())
        pg = self.ctx.new_page(); self.pg = pg
        self.ctx.on('page', self._popup)
        pg.set_default_timeout(8000)
        pg.on('pageerror', lambda e: self.errors.append((time.time(), str(e)[:300])))
        pg.on('console', lambda m: self.console.append((time.time(), m.text[:200])) if m.type == 'error' else None)
        pg.on('dialog', self._dialog)
        pg.on('filechooser', lambda fc: self.choosers.append(time.time()))
        pg.on('download', lambda d: (self.downloads.append((time.time(), d.suggested_filename)), d.cancel()))
        if self.o['mode'] == 'live':
            pg.on('request', self._req)
            pg.on('requestfinished', self._reqdone)
            pg.on('requestfailed', lambda r: self._reqdone(r, failed=True))
        return pg

    def _popup(self, p):
        if p != self.pg:
            self.popups.append((time.time(), p.url))
            try: p.close()
            except Exception: pass

    def _dialog(self, d):
        self.dialogs.append((time.time(), d.type, d.message[:200]))
        try:
            if d.type == 'prompt': d.accept('QA test')
            elif d.type in ('confirm', 'beforeunload'): d.accept()
            else: d.dismiss()
        except Exception: pass

    API = re.compile(r'/(rest|auth|storage|functions)/v1/')

    def _req(self, r):
        if self.API.search(r.url): self.reqs.append({'t': time.time(), 'm': r.method, 'u': r.url, 'st': None, 'obj': r})

    def _reqdone(self, r, failed=False):
        for x in reversed(self.reqs):
            if x['obj'] is r:
                try: x['st'] = 'failed' if failed else (r.response().status if r.response() else 'failed')
                except Exception: x['st'] = 'failed'
                return

    # -------------------------------------------------- sign in
    def open_app(self, full_settle=True):
        pg = self.new_context()
        url = self.o['url']
        demo = self.o['mode'] == 'demo'
        if demo:
            # Demo reloads happen hundreds of times: Playwright's clock skips the fixed waits of the sign-in (the splash hands
            # over to the sign-in page after 700 ms; the full-screen loader stays 1.1 s). Otherwise time runs normally.
            pg.clock.install(); pg.clock.resume()
        pg.goto(url, wait_until='load', timeout=60000)
        try:
            self.wait_js('typeof endSplash==="function"', 10000)
            pg.evaluate('endSplash()')
            if demo: pg.clock.fast_forward(800)
        except Exception: pass
        # endSplash() shows the sign-in page 700 ms later: signing in before that would be undone
        self.wait_js("(function(){var s=document.getElementById('splash');return !s||s.style.display==='none'})()", 10000)
        if demo:
            # the demo account card, then "Sign in" — the page's own controls, clicked from the DOM (a pointer click waits
            # for the login card's entrance animation)
            pg.evaluate("document.querySelector('.lg-demo').click();document.querySelector('#loginPage button.f-btn.dx-js-only').click()")
            pg.wait_for_timeout(20); pg.clock.fast_forward(100); pg.wait_for_timeout(20); pg.clock.fast_forward(1200)
        elif self.account and self.account.get('new'):
            # live: a brand-new account, signed up through the page's own form
            pg.evaluate('showSignup()'); pg.wait_for_timeout(200)
            pg.fill('#suName', self.account['name']); pg.fill('#suEmail', self.account['email']); pg.fill('#suPw', self.account['pw'])
            pg.click('#signupPage button.f-btn')
            self.account['new'] = False
        else:
            pg.wait_for_timeout(300)   # a stored session opens the app by itself
            if not pg.is_visible('#app'):
                pg.fill('#loginEmail', self.account['email']); pg.fill('#loginPw', self.account['pw']); pg.click('#loginPage button.f-btn')
        self.wait_js("!!(document.getElementById('app')&&document.getElementById('app').offsetWidth>0)", 30000)
        pg.wait_for_timeout(30 if demo else 2500)
        pg.evaluate("document.querySelectorAll('#dxTour').forEach(function(e){e.remove()});window.__qaStart=document.body.getAttribute('data-page')")
        try: self.wait_js("!document.querySelector('%s')" % APP['busy_sel'], 8000)
        except Exception: pass
        # the start page counts its numbers up for ~1.3 s; when another page is opened next, that wait is pointless
        if full_settle:
            if demo: pg.clock.fast_forward(2000)
            self.settle(150 if demo else 250, 2000)
        else: pg.wait_for_timeout(40)
        return pg

    def wait_js(self, expr, timeout_ms):
        """poll an expression (page.wait_for_function compiles it inside the page, which the live app's CSP forbids)"""
        t_end = time.time() + timeout_ms / 1000.0
        while True:
            try:
                if self.pg.evaluate(expr): return True
            except Exception as e:
                if 'Execution context was destroyed' not in str(e) and time.time() > t_end: raise
            if time.time() > t_end: raise TimeoutError('waiting for %s' % expr[:80])
            self.pg.wait_for_timeout(50)

    def settle(self, minimum=350, maximum=None):
        pg = self.pg
        maximum = maximum or (2000 if self.o['mode'] == 'demo' else 6000)
        t0 = time.time(); pg.wait_for_timeout(minimum)
        while (time.time() - t0) * 1000 < maximum:
            quiet = pg.evaluate('performance.now()-window.__qa.lastMut')
            pending = [x for x in self.reqs if x['st'] is None and x['t'] > t0 - 2] if self.o['mode'] == 'live' else []
            if quiet > (160 if self.o['mode'] == 'demo' else 300) and not pending: return
            pg.wait_for_timeout(120)

    def now(self):
        return time.time()


# ---------------------------------------------------------------- crawling one view
class ViewCrawler:
    def __init__(self, s, view, cfg, opts):
        self.s, self.view, self.cfg, self.o = s, view, cfg, opts
        self.L = cfg.get('limits') or opts
        self.records, self.skips, self.new_views, self.notes = [], [], [], []
        self.notes_set = set()
        self.fp = None
        self.base, self.noise, self.learned = None, set(), 0
        self.soft_fail = []
        self.last_kind, self.depth_now = None, 1
        self.stream = None
        self.only = set(opts.get('only') or []) if not view['path'] else set()

    # path replay: each step is {key, occ, text}
    def click_ref(self, ref, settle=True):
        pg = self.s.pg
        c = pg.evaluate('([k,o])=>window.__qa.find(k,o)', [ref['key'], ref['occ']])
        if not c: return 'missing'
        pt = pg.evaluate('i=>window.__qa.point(i)', c['i'])
        for _ in range(8):   # covered for a moment (loader, closing animation): wait a little
            if 'err' not in pt or not pt['err'].startswith('covered'): break
            pg.wait_for_timeout(250)
            c = pg.evaluate('([k,o])=>window.__qa.find(k,o)', [ref['key'], ref['occ']])
            if not c: return 'missing'
            pt = pg.evaluate('i=>window.__qa.point(i)', c['i'])
        if 'err' in pt: return pt['err']
        pg.mouse.click(pt['x'], pt['y'])
        if settle: self.s.settle(220 if self.o['mode'] == 'demo' else 400)
        return None

    def goto_view(self):
        pg = self.s.pg
        demo = self.o['mode'] == 'demo'
        for st in self.view['path']:
            err = self.click_ref(st, settle=not demo)
            if err: return 'path step "%s": %s' % (st.get('text', '')[:30], err)
            if demo:   # opening a page: let its entrance animations (numbers counting up) finish at once
                pg.wait_for_timeout(30); pg.clock.fast_forward(2000); self.s.settle(60, 1500)
        pg.evaluate("window.scrollTo(0,0);var c=document.querySelector('%s');if(c)c.scrollTop=0" % APP['content_sel'])
        pg.wait_for_timeout(40 if demo else 150)
        for _ in range(3):   # a page that opens with a panel already covering it: close it (and say so)
            b = pg.evaluate('()=>window.__qa.blocking()')
            if not b: break
            if b not in self.notes_set:
                self.notes_set.add(b); self.notes.append('page opens with a panel already covering it: ' + b)
            if not b.startswith('closed'): break
            self.s.settle(150, 1000)
        return None

    def hard_reset(self):
        """Reload in a brand-new browser context (empty storage), sign in again and open the view. The first time, the
        resulting DOM snapshot becomes this view's resting state ("base"); after later reloads whatever differs from it
        can only be background noise (clocks, rotating tips) and is ignored from then on."""
        self.s.hard_resets += 1
        self.s.open_app(full_settle=not self.view['path'])
        err = self.goto_view()
        pg = self.s.pg
        pg.evaluate('window.__qa.setBaseFixed()')
        if err: return err
        self.s.settle(150, 1200)
        pg.evaluate("window.__qa.snap('fresh')")
        if self.base is None:
            self.base = pg.evaluate("window.__qa.exportSnap('fresh')")
        pg.evaluate('o=>window.__qa.loadSnap("base",o)', self.base)
        pg.evaluate('l=>window.__qa.addNoise(l)', sorted(self.noise))
        new = pg.evaluate("window.__qa.diffPaths('base','fresh',5000)")
        if new:
            self.noise |= set(new)
            pg.evaluate('l=>window.__qa.addNoise(l)', new)
            self.learned += len(new)
        return None

    def found_view(self, nv):
        self.new_views.append(nv)
        if self.stream is not None:
            try: self.stream.put((self.cfg['name'], len(self.view['path']), nv))
            except Exception: pass

    def at_base(self):
        r = self.s.pg.evaluate('()=>window.__qa.atBase()')
        return r['n'] == 0 and r['view'] == self.view['key']

    def fresh(self):
        """Bring the page back to its resting state: the whole visible DOM (not just the list of controls) must equal the
        snapshot taken after a clean sign-in, apart from learned background noise and toasts. Cheapest first: nothing
        changed → nothing to do; otherwise close dialogs and navigate to the view again; otherwise reload from scratch."""
        pg = self.s.pg
        try:
            if pg.is_closed() or pg.url.split('#')[0] != self.o['url'].split('#')[0]: raise RuntimeError('left app')
            if pg.evaluate('document.getElementById("app").offsetWidth===0'): raise RuntimeError('signed out')
            if self.at_base():
                self.s.reuse += 1
                return True
            if self.last_kind in ('changed', 'self_only', 'stored_only', 'already_active') and self.o['mode'] == 'demo' and self.depth_now == 1:
                raise RuntimeError('in-place change: reload')   # re-navigating rarely undoes these (measured: filters, joins)
            for _ in range(2): pg.keyboard.press('Escape'); pg.wait_for_timeout(40)
            if pg.evaluate('window.__qa.closeOverlays()'): pg.wait_for_timeout(200)
            if pg.evaluate('document.getElementById("app").offsetWidth===0'): raise RuntimeError('signed out')
            pg.evaluate(APP['home_js']); pg.wait_for_timeout(40)
            if self.o['mode'] == 'demo': pg.clock.fast_forward(2000)   # the start page's numbers count up again
            err = self.goto_view()
            if not err:
                self.s.settle(150, 1200)
                r = self.s.pg.evaluate('()=>window.__qa.atBase()')
                if r['n'] == 0 and r['view'] == self.view['key']:
                    self.s.soft_resets += 1
                    return True
                self.soft_fail.append((r['view'], r['sample'][:3]))
        except Exception as e:
            self.soft_fail.append(('exception', str(e)[:80]))
        err = self.hard_reset()
        if err: self.notes.append('reset failed: ' + err)
        return not err

    def measure_click(self, ref, cand, opener=None):
        """Click one element (already fresh, opener already replayed) and classify the outcome."""
        s, pg = self.s, self.s.pg
        c = pg.evaluate('([k,o])=>window.__qa.find(k,o)', [ref['key'], ref['occ']])
        if not c: return {'kind': 'click_failed', 'detail': 'element not found after reset'}
        pt = pg.evaluate('i=>window.__qa.point(i)', c['i'])
        if 'err' in pt: return {'kind': 'click_failed', 'detail': pt['err']}
        selfpath = pg.evaluate('i=>window.__qa.selfPath(i)', c['i'])
        empty_field = pg.evaluate('i=>window.__qa.emptyField(i)', c['i'])
        before = pg.evaluate('()=>window.__qa.cands().map(x=>x.key)')
        pg.mouse.move(pt['x'], pt['y']); pg.wait_for_timeout(90)
        pg.evaluate("()=>{const q=window.__qa;q.fx=[];q.toastFired=[];q.snap('s1');q.t1=q.toastText()}")
        t0 = time.time(); n_err, n_con, n_req, n_pop, n_dl, n_fc, n_dg = (len(s.errors), len(s.console), len(s.reqs), len(s.popups),
                                                                         len(s.downloads), len(s.choosers), len(s.dialogs))
        url0 = pg.url
        try:
            pg.mouse.click(pt['x'], pt['y'])
        except Exception as e:
            return {'kind': 'click_failed', 'detail': str(e)[:120]}
        s.settle(200 if self.o['mode'] == 'demo' else 700)
        out = {'detail': ''}
        errs = [e[1] for e in s.errors[n_err:]]
        cons = [e[1] for e in s.console[n_con:]]
        reqs = [{'m': r['m'], 'path': re.sub(r'^https?://[^/]+', '', r['u']).split('?')[0], 'st': r['st']} for r in s.reqs[n_req:]
                if not (r['m'] == 'GET' and '/realtime' in r['u'])]
        pops = [p[1] for p in s.popups[n_pop:]]
        dls = [d[1] for d in s.downloads[n_dl:]]
        dgs = s.dialogs[n_dg:]
        fc = len(s.choosers) > n_fc
        if pg.is_closed():
            return {'kind': 'js_error', 'detail': 'page closed'}
        if pg.url.split('#')[0] != url0.split('#')[0]:
            k = {'kind': 'left_app', 'detail': 'went to ' + pg.url[:120]}
            if errs: k['errors'] = errs
            return k
        r = pg.evaluate("""(sp)=>{const q=window.__qa;q.snap('s2');const d=q.diff('s1','s2',sp);
            return {d:d, ov:q.newOverlays('s1','s2'), gone:q.goneOverlays('s1','s2'), fx:q.fx.slice(0,8), toast:q.toastFired.length?q.toastText().split(' / ').filter(t=>q.t1.split(' / ').indexOf(t)<0).join(' / '):'',
                    t1:q.t1, view:q.snaps.s2.view, focus:q.focusInfo(), text:q.text(5000)}}""", selfpath)
        after = pg.evaluate('()=>window.__qa.cands().map(x=>[x.key,x.region,x.text,x.skey,x.active,x.disabled])')
        out.update(diff=r['d'], fx=r['fx'], toast=r['toast'], net=reqs)
        if errs: out['errors'] = errs
        if cons: out['console'] = cons[:4]
        # revealed elements: keys whose count grew
        cnt = {}
        for k in before: cnt[k] = cnt.get(k, 0) + 1
        seen, revealed = {}, []
        for k, reg, txt, skey, act, dis in after:
            seen[k] = seen.get(k, 0) + 1
            if seen[k] > cnt.get(k, 0): revealed.append({'key': k, 'occ': seen[k] - 1, 'text': txt, 'region': reg, 'skey': skey, 'active': act, 'dis': dis})
        out['revealed'] = revealed
        regions = r['d']['regions']
        real = {k: v for k, v in regions.items() if k != 'toast'}
        n_real = sum(real.values())
        fxk = [f['kind'] for f in r['fx']]
        placeholder = re.compile(APP['placeholder_re'], re.I)
        writes = [q for q in reqs if q['m'] != 'GET']
        bad = [q for q in reqs if q['st'] == 'failed' or (isinstance(q['st'], int) and q['st'] >= 400)]
        # ---- classification (first match wins; network errors and JS errors are reported on top)
        kind = None
        if pops: kind, out['detail'] = 'new_window', pops[0][:120]
        elif dls: kind, out['detail'] = 'download', dls[0]
        elif fc: kind, out['detail'] = 'file_picker', 'file chooser opened'
        elif r['view'] != self.view['key'] and r['view'] != (opener or {}).get('view_after') and not same_page_more(self.view['key'], r['view']):
            kind, out['detail'] = 'navigated', r['view']
            out['view_after'] = r['view']
        elif r['ov']:
            ov = max(r['ov'], key=lambda m: m['area'] * 1000 + m['chars'])
            out['dialog'] = {k: v for k, v in ov.items() if k not in ('text', 'body_text')}
            out['dialog_text'] = ov['text'][:600]
            out['_dialog_full'] = ov['text']
            confirmish = (ov['inputs'] == 0 and ov['buttons'] <= 4 and ov['body_chars'] < 320 and
                          any(re.search(APP['confirm_re'], b, re.I) for b in ov['button_texts']) and
                          any(re.search(APP['close_re'], b, re.I) for b in ov['button_texts']) and
                          re.search(r'\?|؟|sure|confirm|متأكد|تأكيد', ov['text'], re.I))
            if ov['chars'] < 15 and ov['inputs'] == 0 and ov['media'] == 0:
                kind, out['detail'] = 'dialog_empty', 'opens an empty panel'
            elif confirmish and len(revealed) <= 4:
                kind, out['detail'] = 'dialog_confirm', '"%s"' % ov['title']
            elif ov['body_chars'] < 160 and ov['inputs'] == 0 and ov['list_max'] < 3 and ov['media'] == 0 and ov['area'] >= 30:
                kind = 'dialog_thin'
                out['detail'] = ('opens "%s" — a large panel with almost nothing in it: %d characters besides its buttons (%s), no input, no list'
                                 % (ov['title'], ov['body_chars'], ', '.join(ov['button_texts'][:5]) or 'no buttons'))
            elif cand.get('cardlike') and ov['inputs'] == 0 and ov['list_max'] < 3 and ov['media'] == 0 and \
                    novel_chars(ov.get('body_text', ''), (cand.get('ctext') or '') + ' ' + (cand.get('text') or '')) < 60:
                kind = 'dialog_thin'
                nv = novel_words(ov.get('body_text', ''), (cand.get('ctext') or '') + ' ' + (cand.get('text') or ''))
                out['detail'] = ('opens "%s" — the detail shows nothing the card does not already show (new words: %s); no list of '
                                 'items (posts, members, products…), no text box; buttons: %s' % (ov['title'], ' '.join(nv)[:80] or 'none',
                                                                                                  ', '.join(ov['button_texts'][:5]) or 'none'))
            else:
                kind = 'dialog'
                out['detail'] = '"%s" (%d chars, %d inputs, %d buttons, list %d)' % (ov['title'], ov['chars'], ov['inputs'], ov['buttons'], ov['list_max'])
        elif dgs:
            t, typ, msg = dgs[0]
            kind = 'alert_only' if (typ == 'alert' and (n_real == 0)) else 'native_dialog'
            out['detail'] = '%s("%s")' % (typ, msg[:100])
        elif opener and r['gone'] and n_real and all(k in ('overlay',) for k in real) and not writes and not r['toast'] and 'stored' not in fxk:
            # inside a dialog: the only effect was the dialog closing
            txt = (cand.get('text') or '').strip()
            if re.search(APP['confirm_re'], txt, re.I) and not re.search(APP['close_re'], txt, re.I):
                kind, out['detail'] = 'confirm_no_effect', '"%s" only closes the dialog — nothing else happens' % txt[:40]
            else: kind, out['detail'] = 'closed', 'dialog closed'
        elif n_real and not (r['d']['self'] == n_real):
            kind, out['detail'] = 'changed', '%d element(s) changed in %s' % (n_real, ', '.join(sorted(real)))
            if r['toast']: out['detail'] += ' + toast "%s"' % r['toast'][:60]
        elif any(k in fxk for k in ('clipboard', 'share', 'print', 'new_window')):
            f = [x for x in r['fx'] if x['kind'] in ('clipboard', 'share', 'print', 'new_window')][0]
            kind, out['detail'] = f['kind'], f['detail'][:80]
        elif r['toast'] and placeholder.search(r['toast']):
            kind, out['detail'] = 'placeholder_toast', 'toast "%s"' % r['toast'][:100]
        elif n_real and r['d']['self'] == n_real:
            kind = 'self_only'
            out['detail'] = 'only the control itself changed' + (' + toast "%s"' % r['toast'][:60] if r['toast'] else '')
        elif r['toast']:
            if writes or 'stored' in fxk:
                kind, out['detail'] = 'stored_only', 'toast "%s" (+ %s)' % (r['toast'][:70], 'request' if writes else 'saved in browser storage')
            else:
                kind, out['detail'] = 'toast_only', 'toast "%s" and nothing else changed' % r['toast'][:80]
        elif r['focus']:
            kind, out['detail'] = 'focused_input', 'focus moved to ' + r['focus']
        elif writes or reqs:
            kind, out['detail'] = 'request_only', ', '.join('%s %s %s' % (q['m'], q['path'][-40:], q['st']) for q in reqs[:3])
        elif 'stored' in fxk:
            kind, out['detail'] = 'stored_only', 'saved in browser storage only: ' + ', '.join(f['detail'] for f in r['fx'] if f['kind'] == 'stored')[:80]
        elif cand.get('active'):
            kind, out['detail'] = 'already_active', 'already selected — selecting it again changes nothing'
        else:
            kind, out['detail'] = 'no_effect', 'nothing visible happened'
        if kind == 'navigated':
            out['_view_text'] = r['text']
        page_now = (r['view'] or '').split('/')[0]
        m = re.search(r"goto\('([^']+)'\)", cand.get('oc') or '')
        if kind == 'no_effect' and m and m.group(1) == page_now:
            kind, out['detail'] = 'already_active', 'goes to the page that is already open'
        if kind in ('toast_only', 'stored_only') and re.search(APP['validation_re'], r['toast'] or '', re.I):
            kind, out['detail'] = 'validation', 'validation message "%s"' % r['toast'][:80]
        elif kind in ('no_effect', 'self_only', 'toast_only') and empty_field and \
                re.search(APP['submit_re'], (cand.get('text') or '') + ' ' + (cand.get('oc') or ''), re.I):
            kind, out['detail'] = 'needs_input', 'does nothing while %s is empty (the crawler does not type)%s' % (
                empty_field, (' — toast "%s"' % r['toast'][:60]) if r['toast'] else '')
        out['kind'] = kind
        if errs:
            out['also'] = out.get('also', []) + ['js_error']
        if bad:
            out['also'] = out.get('also', []) + ['network_error']
            out['net_errors'] = bad[:4]
        if self.o['mode'] == 'live' and kind in ('changed', 'self_only') and not writes and not cand.get('cardlike') and \
                len(cand.get('text') or '') <= 30 and re.search(APP['action_re'], cand.get('text') or '', re.I) and \
                not [x for x in revealed if x['region'] != 'toast']:   # an inline "are you sure?" is not the action yet
            out['also'] = out.get('also', []) + ['unsaved_change']
        if cons and not errs: out['also'] = out.get('also', []) + ['console_error']
        return out

    def plan(self, cands, depth, scope_regions, nav=False):
        """Pick the elements to click: family sampling + page cap. Returns (targets, skipped). Navigation (the top bar,
        the side menu, a menu opened from them) is never sampled or capped: it is how pages are found."""
        targets, skipped = [], []
        fams = {}
        for c in cands:
            if c['region'] not in scope_regions: continue
            fams.setdefault(c['fam'], []).append(c)
        K = self.L['family_sample']
        chosen = set()
        for fam, members in fams.items():
            n = len(members)
            texts = {m['text'] for m in members}
            if n > K and len(texts) > 1 and members[0]['region'] != 'chrome' and not nav:   # navigation is never sampled
                pick, i = {0, 1, 2, n // 2, n - 2, n - 1}, 3
                while len(pick) < K: pick.add(i); i += 1
                idx = sorted(pick)[:K]
            else:
                idx = list(range(n)) if len(texts) > 1 or n <= 2 else list(range(min(n, 2)))
            for j, m in enumerate(members):
                m['fam_index'], m['fam_size'] = j, n
                if j in idx: chosen.add((m['key'], m['occ']))
                else: skipped.append(dict(m, reason='family sample: %d of %d similar elements clicked' % (len(idx), n)))
        sign = re.compile(APP['signout_re'], re.I)
        for c in cands:
            if c['region'] not in scope_regions or (c['key'], c['occ']) not in chosen: continue
            href = c['href']
            if sign.search(c['text'] + ' ' + c['oc']): skipped.append(dict(c, reason='sign-out (never clicked)')); continue
            if re.match(r'^(mailto:|tel:|sms:|whatsapp:)', href) or (re.match(r'^https?://', href) and not href.startswith(self.o['url'].split('#')[0])):
                skipped.append(dict(c, reason='external link (not followed): ' + href[:80])); continue
            if c['disabled']: skipped.append(dict(c, reason='disabled', disabled_rec=True)); continue
            targets.append(c)
        cap = self.L['max_per_page'] if depth == 1 else self.L['reveal_cap']
        if len(targets) > cap and not nav:
            for c in targets[cap:]: skipped.append(dict(c, reason='cap: more than %d elements on this %s' % (cap, 'page' if depth == 1 else 'dialog/menu')))
            targets = targets[:cap]
        return targets, skipped

    def record(self, c, res, depth, opener=None):
        rec = {'view': self.view['key'], 'depth': depth, 'region': c['region'], 'tag': c['tag'], 'text': c['text'], 'id_attr': c['id'],
               'cls': c['cls'], 'onclick': c['oc'][:100], 'href': c['href'][:100], 'fam': c['fam'], 'fam_index': c.get('fam_index', 0),
               'fam_size': c.get('fam_size', 1), 'title': c.get('title', ''), 'cardlike': c['cardlike'],
               'skey': c['skey'], 'socc': c['socc'], 'card_text': c.get('ctext', '')}
        if opener: rec['opener'] = {'text': opener['text'], 'sid': opener['sid']}
        rec.update({k: v for k, v in res.items() if not k.startswith('_') and k != 'revealed'})
        if re.search(APP['placeholder_href_re'], c['href'] or ''):
            rec.setdefault('also', []).append('placeholder_href')
        rec['sid'] = sha('%s|%s|%s|%s|%d|%s' % (self.view['key'].split(':')[0], (opener or {}).get('sid', ''), c['region'], c['skey'], c['socc'], depth))
        # wrong item: a card opens a detail / page that does not mention the card's title
        if c.get('cardlike') and c.get('title') and res['kind'] in ('dialog', 'dialog_thin', 'navigated', 'dialog_confirm'):
            body = res.get('_dialog_full') or res.get('_view_text') or ''
            t = nrm(c['title'])[:24]
            if len(t) >= 5 and t not in nrm(body):
                rec.setdefault('also', []).append('wrong_item')
                rec['wrong_item'] = 'card "%s" opens %s' % (c['title'][:50], ('"%s"' % res['dialog']['title']) if res.get('dialog') else res['kind'] + ' ' + str(res.get('detail'))[:60])
        rec['_body'] = (res.get('_dialog_full') or res.get('_view_text') or '')[:3000]
        rec['seq'] = len(self.records)
        self.records.append(rec)
        return rec

    def run(self, include_chrome, include_content=True):
        s, pg = self.s, None
        err = self.hard_reset()
        pg = s.pg
        if err:
            self.notes.append('could not open view: ' + err)
            return
        self.s.settle(200, 1500)
        # learn background noise (timers, tickers) for 1.2 s
        pg.evaluate("window.__qa.snap('n0')"); pg.wait_for_timeout(1200); pg.evaluate("window.__qa.snap('n1')")
        pg.evaluate("window.__qa.learnNoise('n0','n1')")
        self.noise |= set(pg.evaluate('window.__qa.noiseList()'))
        self.fp = pg.evaluate('window.__qa.fingerprint()')
        cands = pg.evaluate('()=>window.__qa.cands()')
        if self.view.get('fp_expected') and self.view['fp_expected'] != self.fp:
            self.notes.append('page differs between visits (fingerprint)')
        regions = ({'content'} if include_content else set()) | ({'chrome'} if include_chrome else set())
        targets, skipped = self.plan(cands, 1, regions)
        for c in skipped:
            if c.get('disabled_rec'): self.record(c, {'kind': 'disabled', 'detail': 'disabled control (not clicked)'}, 1)
            else: self.skips.append(self.skip_rec(c, 1))
        reveal_seen, depth2 = set(), []
        deadline = time.time() + self.L['view_timeout'] * (2 if include_chrome and not include_content else 1)
        for i, c in enumerate(targets):
            if time.time() > deadline:
                for c2 in targets[i:]: self.skips.append(self.skip_rec(dict(c2, reason='time limit for this page (%ds)' % self.L['view_timeout']), 1))
                break
            if self.only and self.only <= {v['key'].split('/')[0] for v in self.new_views}:
                for c2 in targets[i:]: self.skips.append(self.skip_rec(dict(c2, reason='not needed: the pages asked for (--pages) were found'), 1))
                depth2 = []
                break
            if i and not self.fresh():
                self.notes.append('could not restore a fresh state before "%s"' % c['text'][:40])
            ref = {'key': c['key'], 'occ': c['occ'], 'text': c['text']}
            try:
                res = self.measure_click(ref, c)
            except Exception as e:
                res = {'kind': 'click_failed', 'detail': 'crawler: ' + str(e).split('\n')[0][:150]}
                try: self.hard_reset()
                except Exception: pass
            rec = self.record(c, res, 1)
            self.last_kind = res['kind']
            if res['kind'] == 'navigated':
                self.found_view({'key': res['view_after'], 'path': self.view['path'] + [ref], 'from': c['text'][:40]})
            rv = [x for x in res.get('revealed', []) if x['region'] != 'toast']
            if rv and res['kind'] in ('dialog', 'dialog_thin', 'dialog_confirm', 'changed', 'self_only', 'focused_input'):
                sig = sha('|'.join(sorted({x['skey'] for x in rv})))
                if sig in reveal_seen:
                    rec['reveal'] = 'same controls as an earlier dialog/menu (crawled once)'
                else:
                    reveal_seen.add(sig)
                    depth2.append((c, ref, rec, rv, res))
        # ---- depth 2: what the clicks revealed
        budget = self.L['max_depth2']
        self.depth_now = 2
        for c, ref, rec, rv, res in depth2:
            fams = {}
            for x in rv:
                x.update({'fam': x['skey'], 'cardlike': False, 'disabled': x.get('dis', False), 'title': '', 'oc': '', 'href': '', 'tag': x['key'].split('|')[0],
                          'id': x['key'].split('|')[1], 'cls': x['key'].split('|')[2][:80], 'socc': x['occ']})
                x['oc'] = x['key'].split('|')[3]; x['href'] = x['key'].split('|')[4]
                x['region'] = 'revealed'
            # a menu opened from the navigation: every item is clicked (pages are found this way) — in the primary
            # configuration, and on a phone, where the side menu is such a menu; elsewhere the usual caps apply
            nav = c['region'] == 'chrome' and (self.cfg.get('primary', True) or self.cfg['width'] < 500)
            tg, sk = self.plan(rv, 2, {'revealed'}, nav=nav)
            opener = {'text': c['text'], 'sid': rec['sid'], 'view_after': res.get('view_after')}
            for x in sk:
                if x.get('disabled_rec'): self.record(x, {'kind': 'disabled', 'detail': 'disabled control (not clicked)'}, 2, opener)
                else: self.skips.append(self.skip_rec(x, 2, opener))
            if nav:   # menu items that repeat a top-level link which already led to its page ("Groups — Go to Groups")
                known = {nrm(r['text']) for r in self.records if r['depth'] == 1 and r['kind'] == 'navigated' and len(nrm(r['text'])) >= 4}
                keep = []
                for x in tg:
                    t = nrm(x['text'])
                    k = next((k for k in known if t == k or t.startswith(k)), None)
                    if k: self.skips.append(self.skip_rec(dict(x, reason='repeats a navigation link already clicked ("%s")' % k[:30]), 2, opener))
                    else: keep.append(x)
                tg = keep
            for j, x in enumerate(tg):
                if (budget <= 0 and not nav) or time.time() > deadline:
                    for x2 in tg[j:]: self.skips.append(self.skip_rec(dict(x2, reason='depth-2 budget/time limit for this page'), 2, opener))
                    break
                if not nav: budget -= 1
                try:
                    self.fresh()
                    e = self.click_ref(ref)
                    if e: res2 = {'kind': 'click_failed', 'detail': 'could not reopen "%s": %s' % (c['text'][:30], e)}
                    else:
                        pg = self.s.pg; pg.evaluate("window.__qa.snap('o0')")
                        res2 = self.measure_click({'key': x['key'], 'occ': x['occ']}, x, opener)
                except Exception as e2:
                    res2 = {'kind': 'click_failed', 'detail': 'crawler: ' + str(e2).split('\n')[0][:150]}
                    try: self.hard_reset()
                    except Exception: pass
                self.record(x, res2, 2, opener)
                if res2.get('kind') == 'navigated':
                    self.found_view({'key': res2['view_after'], 'path': self.view['path'] + [ref, {'key': x['key'], 'occ': x['occ'], 'text': x['text']}],
                                           'from': (c['text'][:20] + ' › ' + x['text'][:20])})

    def skip_rec(self, c, depth, opener=None):
        r = {'view': self.view['key'], 'depth': depth, 'region': c.get('region'), 'tag': c.get('tag'), 'text': c.get('text', ''),
             'onclick': c.get('oc', '')[:80], 'href': c.get('href', '')[:80], 'reason': c['reason']}
        if opener: r['opener'] = opener['text'][:40]
        r['seq'] = len(self.skips)
        return r


def same_page_more(a, b):
    """b is page a with something added (a seasonal banner after a theme change), not another page"""
    pa, _, ka = a.partition('/'); pb, _, kb = b.partition('/')
    return pa == pb and set(filter(None, ka.split(':')[0].split('+'))) <= set(filter(None, kb.split(':')[0].split('+'))) and ':' not in kb.replace(ka, '', 1)


WORD = re.compile(r"[0-9A-Za-z\u0600-\u06ff][0-9A-Za-z\u0600-\u06ff,.'\u2019-]*")


def novel_words(text, known):
    """words of a panel that the element it was opened from did not already show"""
    k = {w.lower().strip(',.') for w in WORD.findall(known or '')}
    out, seen = [], set()
    for w in WORD.findall(text or ''):
        lw = w.lower().strip(',.')
        if len(lw) < 2 or lw in k or lw in seen: continue
        seen.add(lw); out.append(w)
    return out


def novel_chars(text, known):
    return sum(len(w) + 1 for w in novel_words(text, known))


def pg_eval(pg, js):
    try: return pg.evaluate(js)
    except Exception: return None


# ---------------------------------------------------------------- tasks (run in worker processes)
def task_view(opts, cfg, view, include_chrome, account, include_content=True, stream=None):
    from playwright.sync_api import sync_playwright
    t0 = time.time()
    with sync_playwright() as pw:
        s = Session(pw, opts, cfg, account)
        vc = ViewCrawler(s, view, cfg, opts)
        vc.stream = stream
        try:
            vc.run(include_chrome, include_content)
        except Exception as e:
            vc.notes.append('crawler failure: ' + traceback.format_exc()[-600:])
        finally:
            stray = [e[1] for e in s.errors]
            s.close()
    return {'cfg': cfg, 'view': view['key'], 'records': vc.records, 'skips': vc.skips, 'new_views': vc.new_views,
            'notes': vc.notes, 'errors_total': stray, 'hard_resets': s.hard_resets, 'soft_resets': s.soft_resets, 'unchanged': s.reuse,
            'noise_learned': vc.learned, 'seconds': round(time.time() - t0, 1)}


def task_start(opts, cfg, account):
    """Sign in (or sign up) and note the start view."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        s = Session(pw, opts, cfg, account)
        try:
            t0 = time.time()
            pg = s.open_app()
            v = pg.evaluate('window.__qa.view()')
            info = pg.evaluate("({dir:document.documentElement.dir||document.body.dir||getComputedStyle(document.body).direction, lang:document.documentElement.lang})")
            return {'view': v, 'info': info, 'errors': [e[1] for e in s.errors], 'account': account,
                    'seconds': round(time.time() - t0, 1)}
        finally:
            s.close()


# ---------------------------------------------------------------- orchestration
NUM = re.compile(r'\d[\d,.]*\d|\d')
DETAIL_KINDS = ('dialog', 'dialog_thin', 'dialog_confirm', 'navigated')
NOTHING_KINDS = {'no_effect', 'toast_only', 'placeholder_toast', 'alert_only', 'dialog_empty', 'closed'}   # "did not respond"


def nums(t):
    """numbers with two or more digits ("920", "1,100", "3,800") — small counters like "2 active" are too common to compare"""
    out = set()
    for x in NUM.findall(t or ''):
        d = re.sub(r'\D', '', x)
        if len(d) >= 2: out.add(d)
    return out


def own_item(r):
    """Does the detail a card opened show that card's own item? Its title must appear in it, and when the card shows
    numbers (members, price, quantity) at least one of them must appear too."""
    body = r.get('_body') or ''
    t = nrm(r.get('title'))[:24]
    if len(t) >= 5 and t not in nrm(body): return False, 'title "%s" not in the detail' % r['title'][:40]
    cn = nums(r.get('card_text'))
    if cn and not (cn & nums(body)):
        return False, 'card shows %s, the detail shows %s' % ('/'.join(sorted(cn)[:3]), '/'.join(sorted(nums(body))[:4]) or 'no numbers')
    return True, ''


def family_findings(records):
    """Repeated elements (cards, rows) that do not behave alike."""
    out = []
    groups = {}
    for r in records:
        if r['depth'] != 1 or r.get('fam_size', 1) < 3 or r['kind'] == 'disabled': continue
        groups.setdefault((r['cfgname'], r['view'], r['fam']), []).append(r)
    for (cfgname, view, fam), rs in groups.items():
        rs.sort(key=lambda r: r['fam_index'])
        if len(rs) < 3: continue
        n = rs[0]['fam_size']
        label = rs[0].get('title') or rs[0]['text'][:40]
        sampled = '%d sampled' % len(rs) if len(rs) < n else 'all'
        # 1. some respond, some do not
        rs_p = [r for r in rs if r['kind'] not in ('click_failed', 'needs_input', 'disabled')]
        works = [r['kind'] not in NOTHING_KINDS for r in rs_p]
        if len(rs_p) >= 3 and any(works) and not all(works):
            rs = rs_p
            k = 0
            while k < len(works) and works[k]: k += 1
            prefix = k > 0 and not any(works[k:])
            desc = ('only the first %d of %d similar elements respond (%s)' % (rs[k - 1]['fam_index'] + 1, n, sampled)) if prefix else \
                   ('%d of %d sampled similar elements do not respond' % (works.count(False), len(rs)))
            out.append({'kind': 'family_partial', 'cfgname': cfgname, 'view': view, 'fam': fam, 'text': label,
                        'detail': desc + ': ' + ', '.join(['"%s" → %s' % ((r.get('title') or r['text'])[:30], r['kind'])
                                                           for r, w in zip(rs, works) if not w][:5]),
                        'members': [(r['fam_index'] + 1, (r.get('title') or r['text'])[:40], r['kind']) for r in rs]})
        # 2. cards whose detail is another item's (header copied from a template / an earlier card)
        opened = [r for r in rs if r['kind'] in DETAIL_KINDS and r.get('_body') and r.get('cardlike')]
        if len(opened) >= 2:
            verdict = [own_item(r) for r in opened]
            bad = [(r, why) for r, (ok, why) in zip(opened, verdict) if not ok]
            if bad:
                oks = [ok for ok, _ in verdict]
                k = 0
                while k < len(oks) and oks[k]: k += 1
                prefix = k > 0 and not any(oks[k:])
                if prefix:
                    desc = 'only the first %d of %d cards open their own item (%s); from card %d on the detail shows another item' % (
                        opened[k - 1]['fam_index'] + 1, n, sampled, opened[k]['fam_index'] + 1)
                else:
                    desc = '%d of %d sampled cards open a detail that is not their own item' % (len(bad), len(opened))
                out.append({'kind': 'family_wrong_detail', 'cfgname': cfgname, 'view': view, 'fam': fam, 'text': label,
                            'detail': desc + ': ' + '; '.join('card %d "%s": %s' % (r['fam_index'] + 1, (r.get('title') or r['text'])[:30], why)
                                                              for r, why in bad[:4]),
                            'members': [(r['fam_index'] + 1, (r.get('title') or r['text'])[:40], 'own item' if ok else 'NOT its item: ' + why)
                                        for r, (ok, why) in zip(opened, verdict)]})
        # 3. every card opens the same panel (only the title changes): a template, not the item
        if len(opened) >= 3:
            bodies = []
            for r in opened:
                b = r.get('_body') or ''
                for t in {r.get('title') or '', (r.get('dialog') or {}).get('title') or ''}:
                    if t: b = b.replace(t, '')
                bodies.append(nrm(b))
            best = max(set(bodies), key=bodies.count)
            same = bodies.count(best)
            if same >= 3 and same >= 0.6 * len(bodies):
                ex = [r for r, b in zip(opened, bodies) if b == best]
                out.append({'kind': 'family_same_detail', 'cfgname': cfgname, 'view': view, 'fam': fam, 'text': label,
                            'detail': '%d of %d cards that open a detail open the same one — only the title changes: "%s"' %
                                      (same, len(opened), re.sub(r'\s+', ' ', (ex[0].get('_body') or ''))[:160]),
                            'members': [(r['fam_index'] + 1, (r.get('title') or r['text'])[:40], (r.get('dialog') or {}).get('title', '')) for r in ex]})
    return out


def finding_id(page, kind, sid):
    return '%s:%s:%s' % (page, kind, sid)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--target', default=os.path.join(REPO, 'web/dist/drugbox.html'), help='demo .html file or live app URL')
    ap.add_argument('--out', default=os.path.join(REPO, 'qa-crawl'))
    ap.add_argument('--allow', default=os.path.join(HERE, 'deadend_allow.json'))
    ap.add_argument('--langs', default='en,ar')
    ap.add_argument('--widths', default='1440,390')
    ap.add_argument('--pages', default='', help='only these pages (data-page names, comma separated)')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--family-sample', type=int, default=6)
    ap.add_argument('--max-per-page', type=int, default=70)
    ap.add_argument('--reveal-cap', type=int, default=8)
    ap.add_argument('--max-depth2', type=int, default=25)
    ap.add_argument('--max-views', type=int, default=30)
    ap.add_argument('--view-timeout', type=int, default=240, help='seconds per page and configuration; the rest is reported as skipped')
    ap.add_argument('--secondary-family-sample', type=int, default=2, help='family sample in the 2nd..nth configuration')
    ap.add_argument('--secondary-max-per-page', type=int, default=25, help='page cap in the 2nd..nth configuration')
    ap.add_argument('--secondary-max-depth2', type=int, default=6, help='revealed elements per page in the 2nd..nth configuration')
    ap.add_argument('--full', action='store_true', help='crawl every configuration with the full limits (slower)')
    ap.add_argument('--label', default='')
    a = ap.parse_args()

    t_start = time.time()
    tgt = a.target
    if re.match(r'^https?://', tgt):
        opts = {'mode': 'live', 'url': tgt if tgt.endswith('/') else tgt + '/'}
    else:
        p = os.path.abspath(tgt)
        if not os.path.exists(p): sys.exit('target not found: ' + p)
        opts = {'mode': 'demo', 'url': 'file://' + p}
    opts['lib'] = open(os.path.join(HERE, 'qa_lib.js'), encoding='utf-8').read()
    opts.update(only=sorted(x for x in a.pages.split(',') if x), family_sample=a.family_sample, max_per_page=a.max_per_page, reveal_cap=a.reveal_cap, max_depth2=a.max_depth2,
                view_timeout=a.view_timeout)
    cfgs = [{'lang': l, 'width': int(w), 'name': '%s-%s' % (l, w)} for l in a.langs.split(',') for w in a.widths.split(',')]
    full = dict(family_sample=a.family_sample, max_per_page=a.max_per_page, reveal_cap=a.reveal_cap, max_depth2=a.max_depth2, view_timeout=a.view_timeout)
    light = dict(family_sample=a.secondary_family_sample, max_per_page=a.secondary_max_per_page, reveal_cap=a.reveal_cap,
                 max_depth2=a.secondary_max_depth2, view_timeout=a.view_timeout)
    for i, c in enumerate(cfgs):   # the first configuration is crawled fully; the others with lighter sampling (unless --full)
        c['limits'] = full if (i == 0 or a.full) else light
        c['primary'] = i == 0 or a.full
    only = set(x for x in a.pages.split(',') if x)
    os.makedirs(a.out, exist_ok=True)
    allow = {}
    if os.path.exists(a.allow):
        try:
            for e in json.load(open(a.allow, encoding='utf-8')).get('allow', []): allow[e['id']] = e
        except Exception as e:
            sys.exit('allow-list unreadable: %s' % e)
    log = lambda *x: print('[%5.0fs]' % (time.time() - t_start), *x, flush=True)
    log('target', opts['url'], '| configs', ', '.join(c['name'] for c in cfgs))

    accounts = {}
    for c in cfgs:
        if opts['mode'] == 'live':
            st = '%d%s' % (time.time(), uuid.uuid4().hex[:6])
            accounts[c['name']] = {'email': 'crawl-%s-%s@quadra.test' % (c['name'], st), 'pw': 'Crawl-pass-2026', 'name': 'QA Crawler %s' % c['name'].upper(), 'new': True}
        else:
            accounts[c['name']] = None
    all_records, all_skips, notes, js_errors, timing = [], [], [], [], []
    starts = {}
    import multiprocessing as mp
    stream = mp.Manager().Queue()   # views discovered by running tasks
    with cf.ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(task_start, opts, c, accounts[c['name']]): c for c in cfgs}
        for f in cf.as_completed(futs):
            c = futs[f]
            try:
                r = f.result()
            except Exception as e:
                sys.stderr.write('could not sign in for %s: %s\n' % (c['name'], e)); sys.exit(2)
            starts[c['name']] = r
            if r.get('account'): accounts[c['name']] = dict(r['account'], new=False)
            js_errors += [{'cfg': c['name'], 'where': 'sign-in', 'error': e} for e in r['errors']]
            log('signed in', c['name'], '→', r['view'], r['info'])
        # The start view is crawled as two tasks — its navigation (which discovers the pages) and its own content — and
        # every page is queued as soon as some task discovers it.
        done_views = {c['name']: set() for c in cfgs}
        pending = {}

        waiting, seqn = [], [0]   # own queue: the primary configuration first, then by discovery order

        def submit(c, v, chrome, content):
            seqn[0] += 1
            waiting.append(((0 if c.get('primary') else 1, cfgs.index(c), seqn[0]), c, v, chrome, content))

        def feed_pool():
            waiting.sort(key=lambda w: w[0])
            while waiting and len(pending) < a.workers:
                _, c, v, chrome, content = waiting.pop(0)
                f = ex.submit(task_view, opts, c, v, chrome, accounts[c['name']], content, stream)
                pending[f] = (c, v, chrome)
        for c in cfgs:
            v = {'key': starts[c['name']]['view'], 'path': []}
            done_views[c['name']].add(v['key'])
            submit(c, v, True, False)
            submit(c, v, False, not only or v['key'].split('/')[0] in only)

        def consider(c, parent_depth, nv):
            page = nv['key'].split('/')[0]
            if nv['key'] in done_views[c['name']]: return
            if only and page not in only: return
            if parent_depth >= 2 or len(done_views[c['name']]) >= a.max_views:
                all_skips.append({'cfgname': c['name'], 'view': nv['key'], 'depth': 0, 'text': nv['from'],
                                  'reason': 'view not crawled: depth/views limit (--max-views %d, two navigation steps)' % a.max_views})
                done_views[c['name']].add(nv['key']); return
            done_views[c['name']].add(nv['key'])
            submit(c, {'key': nv['key'], 'path': nv['path']}, False, True)
        byname = {c['name']: c for c in cfgs}
        feed_pool()
        while pending or waiting:
            feed_pool()
            done, _ = cf.wait(list(pending), timeout=1.0, return_when=cf.FIRST_COMPLETED)
            while True:   # pages found while a task is still running are crawled at once
                try: cname, pdepth, nv = stream.get_nowait()
                except Exception: break
                consider(byname[cname], pdepth, nv)
            for f in sorted(done, key=lambda f: (pending[f][0]['name'], pending[f][1]['key'], pending[f][2])):
                c, v, chrome = pending.pop(f)
                try:
                    r = f.result()
                except Exception as e:
                    notes.append({'cfg': c['name'], 'view': v['key'], 'note': 'worker failed: %s' % e}); continue
                for x in r['records']: x['cfgname'] = c['name']
                for x in r['skips']: x['cfgname'] = c['name']
                all_records += r['records']; all_skips += r['skips']
                notes += [{'cfg': c['name'], 'view': v['key'], 'note': n} for n in r['notes']]
                in_click = {e for x in r['records'] for e in x.get('errors', [])}
                js_errors += [{'cfg': c['name'], 'where': v['key'] + ' (while resetting / navigating)', 'error': e} for e in r['errors_total'] if e not in in_click]
                vname = v['key'] + (' [navigation]' if chrome else '')
                timing.append({'cfg': c['name'], 'view': vname, 'seconds': r['seconds'], 'clicks': len(r['records']), 'hard_resets': r['hard_resets'],
                               'soft_resets': r['soft_resets'], 'unchanged': r['unchanged'], 'noise_learned': r['noise_learned']})
                log('%-8s %-44s %3d clicks %3d skipped %4.0fs  reloads %d, soft %d, untouched %d' % (c['name'], vname[:44], len(r['records']), len(r['skips']),
                    r['seconds'], r['hard_resets'], r['soft_resets'], r['unchanged']))
                for nv in sorted(r['new_views'], key=lambda x: (x['key'], len(x['path']))):
                    consider(c, len(v['path']), nv)
    if only:   # the start page is crawled for its navigation only; report just the pages asked for
        all_records = [r for r in all_records if r['view'].split('/')[0] in only]
        all_skips = [r for r in all_skips if (r.get('view') or '').split('/')[0] in only]
    report(a, opts, cfgs, starts, all_records, all_skips, notes, js_errors, timing, allow, time.time() - t_start)


# ---------------------------------------------------------------- report
def report(a, opts, cfgs, starts, records, skips, notes, js_errors, timing, allow, secs):
    order = {c['name']: i for i, c in enumerate(cfgs)}   # deterministic: configuration order, then page order
    records.sort(key=lambda r: (order.get(r['cfgname'], 9), r['view'], r['depth'], r.get('opener', {}).get('sid', '') if isinstance(r.get('opener'), dict) else '', r.get('seq', 0)))
    skips.sort(key=lambda r: (order.get(r['cfgname'], 9), r.get('view') or '', r.get('depth', 0), r.get('seq', 0)))
    fam = family_findings(records)
    # findings: one per (page, kind, element) merged across configurations
    F = {}

    def add(page, kind, sid, rec, detail, cfgname, extra=None):
        fid = finding_id(page, kind, sid)
        f = F.setdefault(fid, {'id': fid, 'page': page, 'kind': kind, 'severity': sev(kind), 'element': '', 'detail': detail,
                               'configs': [], 'allowed': fid in allow, 'views': set()})
        if cfgname not in f['configs']: f['configs'].append(cfgname)
        f['views'].add(rec.get('view', ''))
        if not f['element'] or cfgname.startswith('en'):
            f['element'] = describe(rec)
            f['detail'] = detail
        if extra: f.update(extra)
    for r in records:
        page = r['view'].split('/')[0]
        kinds = [r['kind']] + [k for k in r.get('also', []) if k != r['kind']]
        for k in kinds:
            if sev(k) == 'ok': continue
            d = r.get('detail', '')
            if k == 'js_error': d = '; '.join(r.get('errors', []))[:300]
            elif k == 'network_error': d = ', '.join('%s %s → %s' % (q['m'], q['path'], q['st']) for q in r.get('net_errors', []))
            elif k == 'wrong_item': d = r.get('wrong_item', '')
            elif k == 'placeholder_href': d = 'href="%s" (%s)' % (r['href'], r['kind'])
            elif k == 'console_error': d = '; '.join(r.get('console', []))[:200]
            elif k == 'unsaved_change': d = 'the screen changed but no request was sent — the change is lost on reload'
            if r['depth'] == 1 and r.get('fam_size', 1) >= 3 and r.get('cardlike'):
                # one finding per family of cards, not one per card
                fid = finding_id(page, k, 'f' + sha(r['fam']))
                f0 = F.get(fid)
                ex = '#%d "%s"' % (r['fam_index'] + 1, (r.get('title') or r['text'])[:30])
                if f0 is None:
                    add(page, k, 'f' + sha(r['fam']), dict(r, text=(r.get('title') or r['text'])), d, r['cfgname'],
                        {'cards': [ex], 'cards_cfg': r['cfgname'], 'one_detail': d})
                else:
                    add(page, k, 'f' + sha(r['fam']), r, f0['detail'], r['cfgname'])
                    if f0['cards_cfg'] == r['cfgname'] and ex not in f0['cards']: f0['cards'].append(ex)
                continue
            add(page, k, r['sid'], r, d, r['cfgname'])
    for f in fam:
        page = f['view'].split('/')[0]
        add(page, f['kind'], sha(f['fam']), {'view': f['view'], 'text': f['text'], 'tag': 'family'}, f['detail'], f['cfgname'], {'members': f['members']})
    for e in js_errors:
        page = e['where'].split('/')[0]
        add(page, 'js_error', sha(re.sub(r'\d+', '', e['error'])[:120]), {'view': e['where'], 'text': '(page)', 'tag': ''}, e['error'][:300], e['cfg'])
    for f in F.values():
        if f.get('cards'):
            f['detail'] = '%d sampled card(s) of this family (%s) — e.g. %s' % (len(f['cards']), ', '.join(f['cards'][:8]), f.pop('one_detail'))
    findings = sorted(F.values(), key=lambda f: ({'fail': 0, 'warn': 1}.get(f['severity'], 2), f['allowed'], f['page'], f['kind'], f['element']))
    for f in findings: f['views'] = sorted(f['views'])
    new_fail = [f for f in findings if f['severity'] == 'fail' and not f['allowed']]
    any_js = any(f['kind'] == 'js_error' for f in findings)
    kinds = {}
    for r in records: kinds[r['kind']] = kinds.get(r['kind'], 0) + 1
    out = {
        'target': opts['url'], 'mode': opts['mode'], 'label': a.label, 'configs': [c['name'] for c in cfgs],
        'start': {k: {'view': v['view'], 'dir': v['info'].get('dir')} for k, v in starts.items()},
        'limits': {'family_sample': a.family_sample, 'max_per_page': a.max_per_page, 'reveal_cap': a.reveal_cap,
                   'max_depth2': a.max_depth2, 'max_views': a.max_views, 'view_timeout_s': a.view_timeout,
                   'secondary': None if a.full or len(cfgs) == 1 else {'configs': [c['name'] for c in cfgs[1:]], 'family_sample': a.secondary_family_sample,
                                                                       'max_per_page': a.secondary_max_per_page, 'max_depth2': a.secondary_max_depth2}},
        'seconds': round(secs), 'clicks': len(records), 'skipped': len(skips), 'outcomes': kinds,
        'result': 'FAIL' if (new_fail or any_js) else 'PASS',
        'new_dead_ends': len(new_fail), 'findings': findings, 'records': [{k: v for k, v in r.items() if k != '_body'} for r in records],
        'skips': skips, 'notes': notes, 'timing': sorted(timing, key=lambda t: (t['cfg'], t['view'])),
    }
    jp = os.path.join(a.out, 'crawl.json')
    json.dump(out, open(jp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=False)
    mp = os.path.join(a.out, 'crawl.md')
    open(mp, 'w', encoding='utf-8').write(markdown(out, records, skips, findings, allow))
    print('\n%s — %d clicks, %d skipped (all listed), %d findings (%d new dead ends, %d allowed), %d s' %
          (out['result'], len(records), len(skips), len(findings), len(new_fail), sum(1 for f in findings if f['allowed']), secs))
    print('report:', mp, '\njson:  ', jp)
    sys.exit(1 if (new_fail or any_js) else 0)


def describe(r):
    t = (r.get('text') or '').replace('|', '/')[:60] or '(no text)'
    bits = [r.get('tag') or '']
    if r.get('id_attr'): bits.append('#' + r['id_attr'])
    elif r.get('cls'): bits.append('.' + r['cls'].split('.')[0])
    w = '"%s" %s' % (t, ''.join(bits))
    if r.get('onclick'): w += ' onclick=%s' % r['onclick'][:50]
    elif r.get('href'): w += ' href=%s' % r['href'][:50]
    if r.get('opener'): w += ' (inside "%s")' % (r['opener']['text'] if isinstance(r['opener'], dict) else r['opener'])[:40]
    return w


KIND_TEXT = {
    'js_error': 'JavaScript error', 'no_effect': 'Nothing happens', 'dialog_empty': 'Opens an empty dialog',
    'dialog_thin': 'Opens a panel with no content (dead end)', 'confirm_no_effect': 'Confirm/save button with no effect',
    'toast_only': 'Only a toast — nothing else changes', 'placeholder_toast': 'Placeholder message ("coming soon"…)',
    'placeholder_href': 'Placeholder link', 'network_error': 'Server request failed', 'wrong_item': 'Opens the wrong item',
    'family_partial': 'Only some of the repeated cards work', 'family_same_detail': 'Every card opens the same template',
    'family_wrong_detail': 'Cards open another item\'s detail', 'disabled': 'Disabled',
    'needs_input': 'Does nothing while its field is empty', 'validation': 'Validation message', 'already_active': 'Already selected',
    'alert_only': 'Only a browser alert', 'self_only': 'Only the button itself changes', 'stored_only': 'Saved locally/request only, no visible result',
    'request_only': 'Request sent, nothing visible', 'click_failed': 'Could not be clicked', 'console_error': 'Console error',
    'unsaved_change': 'Changes on screen but is not saved', 'unstable_page': 'Page differs between visits',
}


def markdown(out, records, skips, findings, allow):
    L = []
    L.append('# Dead-end crawl — %s' % (out['label'] or os.path.basename(out['target'])))
    L.append('')
    L.append('**%s** · target `%s` (%s) · configurations %s · %d clicks · %d elements skipped (listed below) · %d s' %
             (out['result'], out['target'], out['mode'], ', '.join(out['configs']), out['clicks'], out['skipped'], out['seconds']))
    L.append('')
    L.append('Dead ends not in the allow-list: **%d** · JavaScript errors: **%d** · allow-list entries matched: %d' %
             (out['new_dead_ends'], sum(1 for f in findings if f['kind'] == 'js_error'), sum(1 for f in findings if f['allowed'])))
    L.append('')
    lim = out['limits']
    L.append('Limits (nothing is capped silently): repeated elements of one family → %d clicked (first 3, middle, last 2); '
             'at most %d elements per page; %d per dialog/menu and %d revealed elements per page; %d views per configuration; '
             '%d s per page. Sign-out and external links are never clicked.' %
             (lim['family_sample'], lim['max_per_page'], lim['reveal_cap'], lim['max_depth2'], lim['max_views'], lim['view_timeout_s']))
    if lim.get('secondary'):
        sl = lim['secondary']
        L.append('')
        L.append('Those limits apply to %s. The other configurations (%s) repeat the crawl with lighter sampling — %d per family, '
                 '%d elements per page, %d revealed elements per page — to catch what only breaks in Arabic or on a phone; run with '
                 '`--full` to crawl them as deeply.' % (out['configs'][0], ', '.join(sl['configs']), sl['family_sample'], sl['max_per_page'], sl['max_depth2']))
    L.append('')
    L.append('Outcomes: ' + ', '.join('%s %d' % (k, v) for k, v in sorted(out['outcomes'].items(), key=lambda x: -x[1])))
    L.append('')
    L.append('To approve a finding, copy its id into `tools/qa/deadend_allow.json` (`{"allow":[{"id": "...", "why": "...", "approved_by": "owner"}]}`).')
    L.append('')
    pages = sorted({f['page'] for f in findings} | {r['view'].split('/')[0] for r in records})
    # pages with failures first
    def pscore(p):
        return (-sum(1 for f in findings if f['page'] == p and f['severity'] == 'fail' and not f['allowed']), p)
    pages.sort(key=pscore)
    L.append('## Summary by page')
    L.append('')
    L.append('| page | clicks | dead ends (new) | warnings | worked | skipped |')
    L.append('|---|---|---|---|---|---|')
    for p in pages:
        rs = [r for r in records if r['view'].split('/')[0] == p]
        fs = [f for f in findings if f['page'] == p]
        L.append('| %s | %d | %d (%d) | %d | %d | %d |' % (p, len(rs), sum(1 for f in fs if f['severity'] == 'fail'),
                 sum(1 for f in fs if f['severity'] == 'fail' and not f['allowed']), sum(1 for f in fs if f['severity'] == 'warn'),
                 sum(1 for r in rs if sev(r['kind']) == 'ok'), sum(1 for s in skips if (s.get('view') or '').split('/')[0] == p)))
    L.append('')
    for p in pages:
        fs = [f for f in findings if f['page'] == p]
        rs = [r for r in records if r['view'].split('/')[0] == p]
        L.append('## %s' % p)
        L.append('')
        views = sorted({r['view'] for r in rs})
        if views: L.append('Views: ' + ', '.join('`%s`' % v for v in views))
        L.append('')
        fail = [f for f in fs if f['severity'] == 'fail']
        warn = [f for f in fs if f['severity'] == 'warn']
        if fail:
            L.append('### Dead ends (%d)' % len(fail))
            L.append('')
            for f in fail:
                L.append('- %s**%s** — %s — %s  \n  `%s` · %s%s' % ('(allowed) ' if f['allowed'] else '', KIND_TEXT.get(f['kind'], f['kind']), f['element'],
                         f['detail'], f['id'], ' '.join(f['configs']), ''))
                if f.get('members'):
                    L.append('  members: ' + '; '.join('#%s %s → %s' % m for m in f['members'][:9]))
            L.append('')
        if warn:
            L.append('### Warnings (%d)' % len(warn))
            L.append('')
            for f in warn:
                L.append('- %s — %s — %s  \n  `%s` · %s' % (KIND_TEXT.get(f['kind'], f['kind']), f['element'], f['detail'], f['id'], ' '.join(f['configs'])))
            L.append('')
        okr = [r for r in rs if sev(r['kind']) == 'ok' and r['cfgname'] == out['configs'][0]]
        if okr:
            L.append('<details><summary>Worked (%d in %s)</summary>' % (len(okr), out['configs'][0]))
            L.append('')
            for r in okr:
                L.append('- %s → %s %s' % (describe(r), r['kind'], (r.get('detail') or '')[:120]))
            L.append('')
            L.append('</details>')
            L.append('')
        sk = [s for s in skips if (s.get('view') or '').split('/')[0] == p]
        if sk:
            L.append('<details><summary>Skipped (%d, all configurations)</summary>' % len(sk))
            L.append('')
            agg = {}
            for s in sk:
                k = (s['reason'], s.get('opener', ''), (s.get('text') or '')[:50])
                agg.setdefault(k, []).append(s['cfgname'])
            for (reason, opener, text), cs in sorted(agg.items()):
                L.append('- "%s"%s — %s (%s)' % (text, (' inside "%s"' % opener) if opener else '', reason, ' '.join(sorted(set(cs)))))
            L.append('')
            L.append('</details>')
            L.append('')
    if out['notes']:
        L.append('## Crawler notes')
        L.append('')
        for n in out['notes']: L.append('- %s %s: %s' % (n['cfg'], n['view'], n['note'][:300]))
        L.append('')
    L.append('## Timing')
    L.append('')
    for t in out['timing']:
        L.append('- %s %s: %ss, %d clicks; resets: %d reloads, %d re-navigations, %d not needed; %d noisy elements learned' %
                 (t['cfg'], t['view'], t['seconds'], t['clicks'], t['hard_resets'], t['soft_resets'], t['unchanged'], t['noise_learned']))
    return '\n'.join(L) + '\n'


if __name__ == '__main__':
    main()
