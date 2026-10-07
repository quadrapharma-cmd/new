"""Arabic / RTL smoke test of the live app: sign up in English, switch to Arabic with the interface's own button, walk the main
pages with live data (right-to-left, Arabic labels, no script or console errors, no sideways scrolling), reload (Arabic is kept),
and switch back to English. The other suites run in English; CLAUDE.md's non-negotiable #1 is both languages."""
from playwright.sync_api import sync_playwright
import re
from _dx import APP_URL as U, R, T, sql, ST, wait_for, done   # shared settings: tests/e2e/_dx.py
AR = re.compile(r'[؀-ۿ]')
PAGES = ['feed', 'market', 'companies', 'jobs', 'network', 'messages', 'notifs', 'profile', 'groups', 'training', 'saved']
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); pg = b.new_context(viewport={'width': 1440, 'height': 900}).new_page(); errs, cons = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    # console errors from the app (incl. CSP refusals); a third-party file this machine cannot reach (fonts behind a proxy) is not one
    pg.on("console", lambda m: cons.append(m.text[:150]) if m.type == 'error' and not (m.text.startswith('Failed to load resource: net::ERR_') and not (m.location or {}).get('url', '').startswith(U.rstrip('/'))) else None)
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', 'د. سارة التجربة'); pg.fill('#suEmail', f'rtl{ST}@x.test'); pg.fill('#suPw', 'Strong-pass-2026'); pg.click('#signupPage button.f-btn')
    wait_for(lambda: pg.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); pg.wait_for_timeout(2000)
    me = pg.evaluate("dxLive.uuidOf(ME.id)")
    T('an Arabic name is stored as typed', sql(f"select name from public.profiles where id='{me}'") == 'د. سارة التجربة')
    pg.evaluate("toggleLang()"); pg.wait_for_timeout(1200)
    T('the language button switches the whole page to Arabic, right to left', pg.evaluate("[document.documentElement.lang, document.documentElement.dir]") == ['ar', 'rtl'])
    bad = []
    for page in PAGES:
        pg.evaluate(f"goto('{page}')"); pg.wait_for_timeout(1800)
        st = pg.evaluate("""(()=>{var c=document.getElementById('content');return {dir:document.documentElement.dir, text:(c&&c.innerText||'').slice(0,4000),
          wide:document.documentElement.scrollWidth-document.documentElement.clientWidth}})()""")
        if st['dir'] != 'rtl' or not AR.search(st['text']) or st['wide'] > 2: bad.append((page, st['dir'], bool(AR.search(st['text'])), st['wide']))
    T('every main page renders in Arabic, right to left, with no sideways scrolling', not bad, bad)
    pg.reload(wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()')
    wait_for(lambda: pg.evaluate("document.getElementById('app') && getComputedStyle(document.getElementById('app')).display !== 'none'"), 20); pg.wait_for_timeout(1500)
    T('after a reload the app opens signed in and still in Arabic', pg.evaluate("document.documentElement.dir") == 'rtl' and AR.search(pg.inner_text('#content') or '') is not None)
    pg.evaluate("toggleLang()"); pg.wait_for_timeout(1000)
    T('switching back gives the English page, left to right', pg.evaluate("[document.documentElement.lang, document.documentElement.dir]") == ['en', 'ltr'])
    T('no script errors in the page', not errs, errs)
    T('no console errors (incl. blocked requests or content-security-policy violations)', not cons, cons[:6])
    b.close()
done()
