"""Profile composer (demo build): post from your own profile, stay on it, no composer on other people's profiles, greeting never 'undefined'."""
from playwright.sync_api import sync_playwright
import os, sys
F = os.environ.get('DEMO_FILE', '/tmp/drugbox_brand.html'); LANG = sys.argv[1] if len(sys.argv) > 1 else 'en'; R = []
def T(n, ok, d=''): R.append(ok); print(('✅ ' if ok else '❌ ') + n + ('' if ok else '  → ' + str(d)[:200]))
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); ctx = b.new_context(viewport={'width': 1440, 'height': 900}); ctx.add_init_script("try{localStorage.setItem('dx_lang','%s')}catch(e){}" % LANG)
    pg = ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:150]))
    pg.goto('file://' + F, wait_until='load'); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(2800)
    if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
    E = pg.evaluate
    E("goto('profile')"); pg.wait_for_timeout(1000)
    T('own profile: the composer sits at the top of Activity', E("!!document.querySelector('#profileTabContent .dx-pp-comp .composer')") and E("document.querySelector('#profileTabContent').firstElementChild.classList.contains('dx-pp-comp')"))
    T('greeting uses the name after the title (Haytham)', any(n in E("document.querySelector('#profileTabContent .comp-btn').textContent") for n in ('Haytham', 'هيثم')))
    n0 = E("document.querySelectorAll('#profileTabContent .post').length")
    E("document.querySelector('#profileTabContent .comp-btn').click()"); pg.wait_for_timeout(400)
    T('the composer opens the same post window as Home', E("!!document.getElementById('postBody')"))
    pg.fill('#postBody', 'Posted straight from my profile'); E("submitPost()"); pg.wait_for_timeout(900)
    T('after posting you stay on your profile', E("document.body.getAttribute('data-page')") == 'profile')
    T('the new post appears at the top of your posts', E("document.querySelectorAll('#profileTabContent .post').length") == n0 + 1 and 'Posted straight from my profile' in E("document.querySelector('#profileTabContent .post').innerText"))
    for i, t in [(0, 'img'), (1, 'file'), (3, 'job')]:
        E(f"document.querySelectorAll('#profileTabContent .comp-act')[{i}].click()"); pg.wait_for_timeout(300)
        ok = E("!!document.querySelector('.modal-bg')"); E("document.querySelectorAll('.modal-bg').forEach(m=>m.remove())")
        T(f'the {t} shortcut opens the post window', ok)
    other = E("USERS.find(u=>u.id!==ME.id&&POSTS.some(p=>p.uid===u.id)).id")
    E(f"gotoProfile({other})"); pg.wait_for_timeout(900)
    T("no composer on someone else's profile", not E("!!document.querySelector('#profileTabContent .dx-pp-comp')") and E("document.querySelectorAll('#profileTabContent .post').length") >= 1)
    E("goto('feed')"); pg.wait_for_timeout(600); E("ME.name='Probe'"); E("goto('feed')"); pg.wait_for_timeout(600)
    T('one-word name: the greeting says the name, not "undefined"', 'undefined' not in E("document.querySelector('.comp-btn').textContent") and 'Probe' in E("document.querySelector('.comp-btn').textContent"), E("document.querySelector('.comp-btn').textContent"))
    T('no errors in the page', not errs, errs)
    print(LANG, sum(R), '/', len(R)); b.close()
sys.exit(0 if R and all(R) else 1)
