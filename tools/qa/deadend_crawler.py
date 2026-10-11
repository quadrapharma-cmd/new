#!/usr/bin/env python3
"""Drugbox dead-end crawler — does every visible control lead somewhere?

Opens a target (the standalone demo file, or the live app URL with a freshly signed-up account), signs in, visits every
page reachable from the navigation, and on each page clicks every visible interactive element — buttons, links,
[onclick], role=button/tab, cards made clickable from script (outermost cursor:pointer) — one at a time from a fresh
page state, then classifies what happened:

  navigated · left_app · new_window · download · file_picker · clipboard · share · print   (it went somewhere)
  dialog (with content) · dialog_confirm · changed (the page changed in place) · focused_input · closed
  dialog_empty · dialog_thin (a panel with a title but no body: no inputs, no list, < 160 characters)
  confirm_no_effect (a confirmation/save inside a dialog whose only effect is closing it)
  toast_only (a toast and nothing else) · placeholder_toast ("coming soon", "opens in the app"…)
  no_effect · placeholder_href (#p-need…) · js_error · network_error (live: 4xx/5xx/failed request)
  wrong_item (a card opens a detail/page that does not mention the card's own title)
  family_partial (only some cards of a repeated family respond, e.g. "only the first 2 of 9")
  family_same_detail (every card opens the same panel — only the title changes: a template, not the item)
  warnings: self_only (only the clicked control changed), stored_only, request_only, click_failed, console_error,
  unsaved_change (live: something changed on screen but no request was sent)

Elements revealed by a click (dialog contents, dropdown menus, tab panels) are clicked too — one level deep — by
replaying the opening click from a fresh state each time; identical reveals (the same panel opened by every card of a
family) are crawled once.

Fresh state: before every click the page's list of interactive elements must equal the list captured right after a
clean sign-in and navigation (fingerprint). If it does not, the crawler first tries a soft reset (Escape, navigate
again) and otherwise reloads in a brand-new browser context (empty storage) and signs in again.

Limits (all reported, never silent — every element not clicked appears under "skipped" with its reason):
  --family-sample K  repeated elements of one family (same tag/class/handler shape, e.g. 50 product cards): K are
                     clicked — the first three, the middle, the last two; the rest are listed as "family sample".
  --max-per-page N   at most N elements per page (after sampling), in document order; the rest are "page cap".
  --reveal-cap N     at most N revealed elements per distinct dialog/menu; --max-depth2 N per page in total.
  --max-views N      pages/views discovered (navigation and one level of in-page navigation, e.g. a company page).
  Never clicked: sign-out, external links (http to another site, mailto:, tel:) — listed as skipped.

Output: <out>/crawl.json (every click, every skip, run settings) and <out>/crawl.md (by page, dead ends first).
Exit code: 1 when a JS error was seen or a dead end is not in the allow-list (tools/qa/deadend_allow.json — the owner
approves entries); 0 otherwise. 2 on a crawler failure.

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
    'placeholder_href_re': r'^#p-|^#need|^javascript:\s*void|^#todo',
}
SEVERITY = {
    'js_error': 'fail', 'no_effect': 'fail', 'dialog_empty': 'fail', 'dialog_thin': 'fail', 'confirm_no_effect': 'fail',
    'toast_only': 'fail', 'placeholder_toast': 'fail', 'placeholder_href': 'fail', 'network_error': 'fail',
    'wrong_item': 'fail', 'family_partial': 'fail', 'family_same_detail': 'fail', 'alert_only': 'fail',
    'self_only': 'warn', 'stored_only': 'warn', 'request_only': 'warn', 'click_failed': 'warn', 'console_error': 'warn',
    'unsaved_change': 'warn', 'unstable_page': 'warn',
}
OK_KINDS = {'navigated', 'left_app', 'new_window', 'download', 'file_picker', 'clipboard', 'share', 'print', 'dialog',
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
        self.hard_resets = 0
        lib = open(os.path.join(HERE, 'qa_lib.js'), encoding='utf-8').read()
        jcfg = dict(APP)
        jcfg['seed'] = 1234567 if opts['mode'] == 'demo' else 0
        self.lib = lib.replace('__QA_CFG__', json.dumps(jcfg))

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
    def open_app(self):
        pg = self.new_context()
        url = self.o['url']
        pg.goto(url, wait_until='load', timeout=60000)
        pg.wait_for_timeout(250)
        try: pg.evaluate('typeof endSplash==="function"&&endSplash()')
        except Exception: pass
        pg.wait_for_timeout(250)
        if self.o['mode'] == 'demo':
            pg.click('.lg-demo'); pg.click('#loginPage button.f-btn.dx-js-only')
        elif self.account and self.account.get('new'):
            pg.evaluate('showSignup()'); pg.wait_for_timeout(200)
            pg.fill('#suName', self.account['name']); pg.fill('#suEmail', self.account['email']); pg.fill('#suPw', self.account['pw'])
            pg.click('#signupPage button.f-btn')
            self.account['new'] = False
        else:
            if not pg.is_visible('#app'):
                pg.fill('#loginEmail', self.account['email']); pg.fill('#loginPw', self.account['pw']); pg.click('#loginPage button.f-btn')
        pg.wait_for_function("document.getElementById('app')&&document.getElementById('app').offsetWidth>0", timeout=30000)
        pg.wait_for_timeout(400 if self.o['mode'] == 'demo' else 2500)
        pg.evaluate("document.querySelectorAll('#dxTour').forEach(function(e){e.remove()});window.__qaStart=document.body.getAttribute('data-page')")
        self.settle(300, 1500)
        return pg

    def settle(self, minimum=350, maximum=None):
        pg = self.pg
        maximum = maximum or (2000 if self.o['mode'] == 'demo' else 6000)
        t0 = time.time(); pg.wait_for_timeout(minimum)
        while (time.time() - t0) * 1000 < maximum:
            quiet = pg.evaluate('performance.now()-window.__qa.lastMut')
            pending = [x for x in self.reqs if x['st'] is None and x['t'] > t0 - 2] if self.o['mode'] == 'live' else []
            if quiet > 220 and not pending: return
            pg.wait_for_timeout(120)

    def now(self):
        return time.time()


# ---------------------------------------------------------------- crawling one view
class ViewCrawler:
    def __init__(self, s, view, cfg, opts):
        self.s, self.view, self.cfg, self.o = s, view, cfg, opts
        self.records, self.skips, self.new_views, self.notes = [], [], [], []
        self.notes_set = set()
        self.fp = None

    # path replay: each step is {key, occ, text}
    def click_ref(self, ref, settle=True):
        pg = self.s.pg
        c = pg.evaluate('([k,o])=>window.__qa.find(k,o)', [ref['key'], ref['occ']])
        if not c: return 'missing'
        pt = pg.evaluate('i=>window.__qa.point(i)', c['i'])
        if 'err' in pt: return pt['err']
        pg.mouse.click(pt['x'], pt['y'])
        if settle: self.s.settle(300)
        return None

    def goto_view(self):
        pg = self.s.pg
        for st in self.view['path']:
            err = self.click_ref(st)
            if err: return 'path step "%s": %s' % (st.get('text', '')[:30], err)
        pg.evaluate("window.scrollTo(0,0);var c=document.querySelector('%s');if(c)c.scrollTop=0" % APP['content_sel'])
        pg.wait_for_timeout(150)
        for _ in range(3):   # a page that opens with a panel already covering it: close it (and say so)
            b = pg.evaluate('()=>window.__qa.blocking()')
            if not b: break
            if b not in self.notes_set:
                self.notes_set.add(b); self.notes.append('page opens with a panel already covering it: ' + b)
            if not b.startswith('closed'): break
            self.s.settle(150, 1000)
        return None

    def hard_reset(self):
        self.s.hard_resets += 1
        self.s.open_app()
        err = self.goto_view()
        self.s.pg.evaluate('window.__qa.setBaseFixed()')
        return err

    def fresh(self):
        """Bring the page back to the state captured at the start of this view (fingerprint must match)."""
        pg = self.s.pg
        try:
            if pg.url.split('#')[0] != self.o['url'].split('#')[0] or self.s.pg.is_closed(): raise RuntimeError('left app')
            for _ in range(2): pg.keyboard.press('Escape'); pg.wait_for_timeout(60)
            if pg.evaluate('window.__qa.closeOverlays()'): pg.wait_for_timeout(250)
            if pg.evaluate('document.getElementById("app").offsetWidth===0'): raise RuntimeError('signed out')
            pg.evaluate(APP['home_js']); pg.wait_for_timeout(60)
            err = self.goto_view()
            if not err:
                self.s.settle(150, 1200)
                if pg.evaluate('window.__qa.fingerprint()') == self.fp and pg.evaluate('window.__qa.view()') == self.view['key']:
                    return True
        except Exception:
            pass
        err = self.hard_reset()
        ok = not err and pg_eval(self.s.pg, 'window.__qa.fingerprint()') == self.fp
        if not ok and err: self.notes.append('reset failed: ' + err)
        return ok

    def measure_click(self, ref, cand, opener=None):
        """Click one element (already fresh, opener already replayed) and classify the outcome."""
        s, pg = self.s, self.s.pg
        c = pg.evaluate('([k,o])=>window.__qa.find(k,o)', [ref['key'], ref['occ']])
        if not c: return {'kind': 'click_failed', 'detail': 'element not found after reset'}
        pt = pg.evaluate('i=>window.__qa.point(i)', c['i'])
        if 'err' in pt: return {'kind': 'click_failed', 'detail': pt['err']}
        selfpath = pg.evaluate('i=>window.__qa.selfPath(i)', c['i'])
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
        s.settle(380 if self.o['mode'] == 'demo' else 700)
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
        after = pg.evaluate('()=>window.__qa.cands().map(x=>[x.key,x.region,x.text,x.skey])')
        out.update(diff=r['d'], fx=r['fx'], toast=r['toast'], net=reqs)
        if errs: out['errors'] = errs
        if cons: out['console'] = cons[:4]
        # revealed elements: keys whose count grew
        cnt = {}
        for k in before: cnt[k] = cnt.get(k, 0) + 1
        seen, revealed = {}, []
        for k, reg, txt, skey in after:
            seen[k] = seen.get(k, 0) + 1
            if seen[k] > cnt.get(k, 0): revealed.append({'key': k, 'occ': seen[k] - 1, 'text': txt, 'region': reg, 'skey': skey})
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
        elif r['view'] != self.view['key'] and r['view'] != (opener or {}).get('view_after'):
            kind, out['detail'] = 'navigated', r['view']
            out['view_after'] = r['view']
        elif r['ov']:
            ov = max(r['ov'], key=lambda m: m['area'] * 1000 + m['chars'])
            out['dialog'] = {k: v for k, v in ov.items() if k != 'text'}
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
            elif ov['body_chars'] < 160 and ov['inputs'] == 0 and ov['list_max'] < 3 and ov['media'] == 0:
                kind = 'dialog_thin'
                out['detail'] = ('opens "%s" — a panel with no content: %d characters besides its buttons (%s), no input, no list'
                                 % (ov['title'], ov['body_chars'], ', '.join(ov['button_texts'][:5]) or 'no buttons'))
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
            if re.search(APP['close_re'], txt, re.I) or not txt: kind, out['detail'] = 'closed', 'dialog closed'
            else: kind, out['detail'] = 'confirm_no_effect', '"%s" only closes the dialog — nothing else happens' % txt[:40]
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
        else:
            kind, out['detail'] = 'no_effect', 'nothing visible happened'
        if kind == 'navigated':
            out['_view_text'] = r['text']
        out['kind'] = kind
        if errs:
            out['also'] = out.get('also', []) + ['js_error']
        if bad:
            out['also'] = out.get('also', []) + ['network_error']
            out['net_errors'] = bad[:4]
        if self.o['mode'] == 'live' and kind in ('changed', 'self_only') and not writes and cand.get('cardlike') is False and \
                re.search(APP['confirm_re'] + r'|like|follow|connect|save|accept|إعجاب|متابعة|تواصل|قبول', cand.get('text') or '', re.I):
            out['also'] = out.get('also', []) + ['unsaved_change']
        if cons and not errs: out['also'] = out.get('also', []) + ['console_error']
        return out

    def plan(self, cands, depth, scope_regions):
        """Pick the elements to click: family sampling + page cap. Returns (targets, skipped)."""
        targets, skipped = [], []
        fams = {}
        for c in cands:
            if c['region'] not in scope_regions: continue
            fams.setdefault(c['fam'], []).append(c)
        K = self.o['family_sample']
        chosen = set()
        for fam, members in fams.items():
            n = len(members)
            texts = {m['text'] for m in members}
            if n > K and len(texts) > 1:
                idx = sorted({0, 1, 2, n // 2, n - 2, n - 1})[:K]
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
            if c['disabled']: skipped.append(dict(c, reason='disabled')); continue
            targets.append(c)
        cap = self.o['max_per_page'] if depth == 1 else self.o['reveal_cap']
        if len(targets) > cap:
            for c in targets[cap:]: skipped.append(dict(c, reason='cap: more than %d elements on this %s' % (cap, 'page' if depth == 1 else 'dialog/menu')))
            targets = targets[:cap]
        return targets, skipped

    def record(self, c, res, depth, opener=None):
        rec = {'view': self.view['key'], 'depth': depth, 'region': c['region'], 'tag': c['tag'], 'text': c['text'], 'id_attr': c['id'],
               'cls': c['cls'], 'onclick': c['oc'][:100], 'href': c['href'][:100], 'fam': c['fam'], 'fam_index': c.get('fam_index', 0),
               'fam_size': c.get('fam_size', 1), 'title': c.get('title', ''), 'cardlike': c['cardlike'],
               'skey': c['skey'], 'socc': c['socc']}
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
        rec['_body'] = (res.get('_dialog_full') or '')[:3000]
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
        self.fp = pg.evaluate('window.__qa.fingerprint()')
        cands = pg.evaluate('()=>window.__qa.cands()')
        if self.view.get('fp_expected') and self.view['fp_expected'] != self.fp:
            self.notes.append('page differs between visits (fingerprint)')
        regions = ({'content'} if include_content else set()) | ({'chrome'} if include_chrome else set())
        targets, skipped = self.plan(cands, 1, regions)
        self.skips += [self.skip_rec(c, 1) for c in skipped]
        reveal_seen, depth2 = set(), []
        deadline = time.time() + self.o['view_timeout']
        for i, c in enumerate(targets):
            if time.time() > deadline:
                for c2 in targets[i:]: self.skips.append(self.skip_rec(dict(c2, reason='time limit for this page (%ds)' % self.o['view_timeout']), 1))
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
            if res['kind'] == 'navigated':
                self.new_views.append({'key': res['view_after'], 'path': self.view['path'] + [ref], 'from': c['text'][:40]})
            rv = [x for x in res.get('revealed', []) if x['region'] != 'toast']
            if rv and res['kind'] in ('dialog', 'dialog_thin', 'dialog_confirm', 'changed', 'self_only', 'focused_input'):
                sig = sha('|'.join(sorted({x['skey'] for x in rv})))
                if sig in reveal_seen:
                    rec['reveal'] = 'same controls as an earlier dialog/menu (crawled once)'
                else:
                    reveal_seen.add(sig)
                    depth2.append((c, ref, rec, rv, res))
        # ---- depth 2: what the clicks revealed
        budget = self.o['max_depth2']
        for c, ref, rec, rv, res in depth2:
            fams = {}
            for x in rv:
                x.update({'fam': x['skey'], 'cardlike': False, 'disabled': False, 'title': '', 'oc': '', 'href': '', 'tag': x['key'].split('|')[0],
                          'id': x['key'].split('|')[1], 'cls': x['key'].split('|')[2][:80], 'socc': x['occ']})
                x['oc'] = x['key'].split('|')[3]; x['href'] = x['key'].split('|')[4]
                x['region'] = 'revealed'
            tg, sk = self.plan(rv, 2, {'revealed'})
            opener = {'text': c['text'], 'sid': rec['sid'], 'view_after': res.get('view_after')}
            for x in sk: self.skips.append(self.skip_rec(x, 2, opener))
            for j, x in enumerate(tg):
                if budget <= 0 or time.time() > deadline:
                    for x2 in tg[j:]: self.skips.append(self.skip_rec(dict(x2, reason='depth-2 budget/time limit for this page'), 2, opener))
                    break
                budget -= 1
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

    def skip_rec(self, c, depth, opener=None):
        r = {'view': self.view['key'], 'depth': depth, 'region': c.get('region'), 'tag': c.get('tag'), 'text': c.get('text', ''),
             'onclick': c.get('oc', '')[:80], 'href': c.get('href', '')[:80], 'reason': c['reason']}
        if opener: r['opener'] = opener['text'][:40]
        return r


def pg_eval(pg, js):
    try: return pg.evaluate(js)
    except Exception: return None


# ---------------------------------------------------------------- tasks (run in worker processes)
def task_view(opts, cfg, view, include_chrome, account, include_content=True):
    from playwright.sync_api import sync_playwright
    t0 = time.time()
    with sync_playwright() as pw:
        s = Session(pw, opts, cfg, account)
        vc = ViewCrawler(s, view, cfg, opts)
        try:
            vc.run(include_chrome, include_content)
        except Exception as e:
            vc.notes.append('crawler failure: ' + traceback.format_exc()[-600:])
        finally:
            stray = [e[1] for e in s.errors]
            s.close()
    return {'cfg': cfg, 'view': view['key'], 'records': vc.records, 'skips': vc.skips, 'new_views': vc.new_views,
            'notes': vc.notes, 'errors_total': stray, 'hard_resets': s.hard_resets, 'seconds': round(time.time() - t0, 1)}


def task_start(opts, cfg, account):
    """Sign in (or sign up) and return the start view key."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        s = Session(pw, opts, cfg, account)
        try:
            pg = s.open_app()
            v = pg.evaluate('window.__qa.view()')
            info = pg.evaluate("({dir:document.documentElement.dir||document.body.dir||getComputedStyle(document.body).direction, lang:document.documentElement.lang})")
            return {'view': v, 'info': info, 'errors': [e[1] for e in s.errors], 'account': account}
        finally:
            s.close()


# ---------------------------------------------------------------- orchestration
def family_findings(records):
    """Repeated cards that do not behave alike."""
    out = []
    groups = {}
    for r in records:
        if r['depth'] != 1 or r.get('fam_size', 1) < 3: continue
        groups.setdefault((r['cfgname'], r['view'], r['fam']), []).append(r)
    for (cfgname, view, fam), rs in groups.items():
        rs.sort(key=lambda r: r['fam_index'])
        if len(rs) < 3: continue
        n = rs[0]['fam_size']
        works = [sev(r['kind']) == 'ok' and r['kind'] not in ('closed',) for r in rs]
        label = rs[0].get('title') or rs[0]['text'][:40]
        if any(works) and not all(works):
            ok_idx = [r['fam_index'] for r, w in zip(rs, works) if w]
            bad = [r for r, w in zip(rs, works) if not w]
            prefix = all(w for w in works[:len(ok_idx)]) and not any(works[len(ok_idx):])
            desc = ('only the first %d of %d similar elements respond' % (len(ok_idx), n)) if prefix else \
                   ('%d of %d sampled similar elements do not respond' % (len(bad), len(rs)))
            out.append({'kind': 'family_partial', 'cfgname': cfgname, 'view': view, 'fam': fam, 'detail': desc + ': ' +
                        ', '.join('"%s" → %s' % ((r.get('title') or r['text'])[:30], r['kind']) for r in bad[:5]),
                        'text': label, 'members': [(r['fam_index'], (r.get('title') or r['text'])[:40], r['kind']) for r in rs]})
        dl = [r for r in rs if r.get('dialog') and r['kind'] in ('dialog', 'dialog_thin', 'dialog_confirm')]
        if len(dl) >= 3:
            bodies = []
            for r in dl:
                b = r.get('_body') or ''
                for t in {r.get('title') or '', (r.get('dialog') or {}).get('title') or ''}:
                    if t: b = b.replace(t, '')
                bodies.append(re.sub(r'\s+', ' ', b).strip())
            same = max(bodies.count(b) for b in bodies)
            if same >= 3 and same == len(bodies):
                out.append({'kind': 'family_same_detail', 'cfgname': cfgname, 'view': view, 'fam': fam, 'text': label,
                            'detail': 'all %d sampled cards (of %d) open the same panel — only the title changes: "%s"' %
                                      (len(dl), n, bodies[0][:140]),
                            'members': [(r['fam_index'], (r.get('title') or r['text'])[:40], (r.get('dialog') or {}).get('title', '')) for r in dl]})
        for r in rs:
            if r.get('wrong_item'):
                pass
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
    ap.add_argument('--reveal-cap', type=int, default=10)
    ap.add_argument('--max-depth2', type=int, default=40)
    ap.add_argument('--max-views', type=int, default=30)
    ap.add_argument('--view-timeout', type=int, default=240, help='seconds per page and configuration; the rest is reported as skipped')
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
    opts.update(family_sample=a.family_sample, max_per_page=a.max_per_page, reveal_cap=a.reveal_cap, max_depth2=a.max_depth2,
                view_timeout=a.view_timeout)
    cfgs = [{'lang': l, 'width': int(w), 'name': '%s-%s' % (l, w)} for l in a.langs.split(',') for w in a.widths.split(',')]
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
        # wave 1: the start view (with navigation chrome); its navigations give the pages
        queue, done_views = [], {c['name']: set() for c in cfgs}
        for c in cfgs:
            v = {'key': starts[c['name']]['view'], 'path': []}
            queue.append((c, v, True)); done_views[c['name']].add(v['key'])
        wave = 0
        while queue:
            wave += 1
            futs = {ex.submit(task_view, opts, c, v, chrome, accounts[c['name']], not only or v['key'].split('/')[0] in only): (c, v)
                    for c, v, chrome in queue}
            queue = []
            for f in cf.as_completed(futs):
                c, v = futs[f]
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
                timing.append({'cfg': c['name'], 'view': v['key'], 'seconds': r['seconds'], 'clicks': len(r['records']), 'hard_resets': r['hard_resets']})
                log('%-8s %-40s %3d clicks %3d skipped %4.0fs %d reloads' % (c['name'], v['key'][:40], len(r['records']), len(r['skips']), r['seconds'], r['hard_resets']))
                depth = len(v['path'])
                for nv in r['new_views']:
                    page = nv['key'].split('/')[0]
                    if nv['key'] in done_views[c['name']]: continue
                    if only and page not in only: continue
                    if depth >= 2 or sum(len(x) for x in done_views.values()) >= a.max_views * len(cfgs):
                        all_skips.append({'cfgname': c['name'], 'view': nv['key'], 'depth': 0, 'text': nv['from'], 'reason': 'view not crawled: depth/views limit (--max-views %d)' % a.max_views})
                        done_views[c['name']].add(nv['key']); continue
                    done_views[c['name']].add(nv['key'])
                    queue.append((c, {'key': nv['key'], 'path': nv['path']}, False))
            queue.sort(key=lambda x: (x[0]['name'], x[1]['key']))
    if only:   # the start page is crawled for its navigation only; report just the pages asked for
        all_records = [r for r in all_records if r['view'].split('/')[0] in only]
        all_skips = [r for r in all_skips if (r.get('view') or '').split('/')[0] in only]
    report(a, opts, cfgs, starts, all_records, all_skips, notes, js_errors, timing, allow, time.time() - t_start)


# ---------------------------------------------------------------- report
def report(a, opts, cfgs, starts, records, skips, notes, js_errors, timing, allow, secs):
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
            add(page, k, r['sid'], r, d, r['cfgname'])
    for f in fam:
        page = f['view'].split('/')[0]
        add(page, f['kind'], sha(f['fam']), {'view': f['view'], 'text': f['text'], 'tag': 'family'}, f['detail'], f['cfgname'], {'members': f['members']})
    for e in js_errors:
        page = e['where'].split('/')[0]
        add(page, 'js_error', sha(re.sub(r'\d+', '', e['error'])[:120]), {'view': e['where'], 'text': '(page)', 'tag': ''}, e['error'][:300], e['cfg'])
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
                   'max_depth2': a.max_depth2, 'max_views': a.max_views, 'view_timeout_s': a.view_timeout},
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
    for t in out['timing']: L.append('- %s %s: %ss, %d clicks, %d reloads' % (t['cfg'], t['view'], t['seconds'], t['clicks'], t['hard_resets']))
    return '\n'.join(L) + '\n'


if __name__ == '__main__':
    main()
