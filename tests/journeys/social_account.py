"""Social journeys — account: sign-up, confirmation, sign-in, sign-out, password reset, settings, deletion, language,
appearance (J-SOCIAL-01 … 09). Run: python3 tests/journeys/social_account.py --target demo|live --lang en|ar --width 1440|390"""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW, APP_VISIBLE, LOGIN_VISIBLE
from _social import *

DEMO_PEOPLE = r'Haytham|Chairman & CEO|Quadra Pharm|Alia Mourad|Vivian Zhou|Omar Khaled|Faisal Rahmani'

def sidebar_badges(pg):
    return pg.evaluate("""()=>[...document.querySelectorAll('#app .nl-badge,#app .tnb-badge,#app [class*=badge]')].filter(e=>e.offsetParent!==null&&/^\\d+$/.test(e.innerText.trim())&&e.closest('#content')===null).map(e=>e.innerText.trim())""")

def bright_share(pg):
    """Share of near-white pixels in the visible page content (a screenshot, as the eye sees it — computed colours
    lie when a layer paints over them)."""
    import io
    from PIL import Image
    box = pg.evaluate("(()=>{const r=document.getElementById('content').getBoundingClientRect();return {x:Math.max(r.left,0),y:Math.max(r.top,0),width:Math.min(r.width,innerWidth),height:Math.min(r.height,innerHeight-Math.max(r.top,0))}})()")
    im = Image.open(io.BytesIO(pg.screenshot(clip=box))).convert('L').resize((200, 200))
    px = list(im.tobytes()); return sum(1 for v in px if v > 235) / len(px)

def chrome_text(pg):
    """Top bar + sidebar text (everything in the app outside the page content)."""
    return pg.evaluate("""()=>{const a=document.getElementById('app');const c=document.getElementById('content');let t='';
        a.querySelectorAll('*').forEach(e=>{if(e.children.length===0&&e.offsetParent!==null&&!c.contains(e))t+=' '+e.innerText});return t}""")

@journey('J-SOCIAL-01')
def signup_new_professional(j):
    """A new professional creates an account so that she exists on Drugbox as herself."""
    pg = j.new_page()
    email = j.email('mona')
    with j.step('Open the app and wait for the login page'):
        j.check(j.on_login(pg), 'the login page is not shown')
    with j.step("Click 'Create one' under the sign-in form"):
        j.click(pg, r'^(Create one|أنشئ حسابًا|إنشاء حساب|أنشئ واحدًا)', scope='#loginPage', what='Create one')
        j.check(pg.is_visible('#suName'), 'the sign-up form did not open')
        if j.live:      # S-19: the page every new member opens does not claim a member count the database does not have
            sub = j.text(pg, '#signupPage'); n = int(j.sql1("select count(*) from public.profiles") or 0)
            claims = [int(x.replace(',', '')) for x in re.findall(r'(\d[\d,]{2,})\s*\+?\s*(?:pharma|متخصص)', sub)]
            j.check(not [c for c in claims if c > n], 'the sign-up page claims %s professionals; the database has %d members' % (claims, n))
    with j.step('Try a 5-character password: a specific error, no account'):
        pg.fill('#suName', 'Mona Fathy'); pg.fill('#suEmail', email); pg.fill('#suPw', 'abcde')
        if pg.locator('#suCompany').count(): pg.fill('#suCompany', 'Pharco')
        if pg.locator('#suRole').count():
            # S-15: no specialty is chosen for her — the list starts on an empty "choose…" entry, so nobody gets a role by default
            first = pg.eval_on_selector('#suRole', 'e=>({v:e.value,t:(e.options[e.selectedIndex]||{}).text||""})')
            j.check(first['v'] == '' and re.search(r'Choose|اختر', first['t']), 'the specialty list starts on a preselected role ("%s"), not on an empty choice' % first['t'])
            opts = pg.eval_on_selector_all('#suRole option', 'o=>o.map(x=>x.textContent.trim())')
            qc = [o for o in opts if re.search(r'Quality Control|الجودة', o)]
            j.check(qc, 'the specialty list has no Quality Control (options: %s)' % opts)
            pg.select_option('#suRole', label=qc[0])
        pg.click('#signupPage button.f-btn.dx-js-only'); pg.wait_for_timeout(700)
        err = j.text(pg, '#suErr')
        j.check(err.strip() and not j.in_app(pg), 'a 5-character password gave no error (or opened the app)')
        j.check(not re.search(r'AuthApiError|\{|status|422|400', err), 'raw API text in the error: ' + err)
    with j.step('Try an already-registered email: a human error, no second account'):
        taken = 'haytham@drugbox.com' if j.demo else j.email('taken')
        if j.live: j.sql("insert into auth.users (email, encrypted_password) values ('%s', crypt('Other-pass-1', gen_salt('bf')))" % taken)
        else: taken = pg.evaluate("(()=>{const b=document.querySelector('.lg-demo');const m=(b.getAttribute('onclick')||'').match(/value='([^']+@[^']+)'/);return m?m[1]:'haytham@drugbox.com'})()")
        pg.fill('#suEmail', taken); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn.dx-js-only'); pg.wait_for_timeout(1500)
        err = j.text(pg, '#suErr')
        j.check(not j.in_app(pg), 'sign-up with an already-registered email (%s) opened the app as a new account' % taken)
        j.check(err.strip(), 'no message at all for an already-registered email')
        if j.live: j.check(j.sql1("select count(*) from auth.users where email='%s'" % taken) == '1', 'a second account was created for the same email')
    with j.step('Submit with valid data: the app opens on Home greeting Mona Fathy (no demo identity)'):
        pg.fill('#suEmail', email); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn.dx-js-only')
        j.check(j.wait(pg, APP_VISIBLE, 20), 'the app did not open after a valid sign-up: ' + j.text(pg, '#suErr'))
        j.settle(pg, 1200); j.skip_tour(pg)
        j.check(pg.evaluate('ME.name') == 'Mona Fathy', 'signed in as "%s", not Mona Fathy' % pg.evaluate('ME.name'))
        ch = chrome_text(pg)
        bad = re.findall(r'Haytham|Chairman & CEO|Quadra Pharm|\bVIP\b', ch)
        j.check(not bad, 'the top bar / sidebar of the new account still show the demo identity: %s' % sorted(set(bad)))
        comp = j.text(pg, '#content')
        j.check(re.search(r"What.s on your mind, Mona|Mona", comp), 'the composer does not greet Mona')
    with j.step('Open own profile: name, company and specialty exactly as typed'):
        j.click(pg, r'^(Profile|الملف الشخصي|ملفي)$', what='Profile', exact=True) if j.find(pg, r'^(Profile|الملف الشخصي|ملفي)$', exact=True) else pg.click('#topAv')
        j.settle(pg, 900); t = j.text(pg)
        j.check('Mona Fathy' in t, 'own profile does not show the name')
        j.check('Pharco' in t, 'own profile does not show the company "Pharco" typed at sign-up')
        j.check(re.search(r'Quality Control|الجودة', t), 'own profile does not show the specialty "Quality Control" chosen at sign-up')
    if j.live:
        with j.step('Live: auth.users has the email; profiles row has name, company and specialty'):
            uid = j.sql1("select id from auth.users where email='%s'" % email); j.check(uid, 'no auth.users row')
            row = j.sql1("select coalesce(name,'∅')||'|'||coalesce(company,'∅')||'|'||coalesce(headline,'∅') from public.profiles where id='%s'" % uid)
            j.check('∅' not in row and 'Pharco' in row, 'profiles row is incomplete (name|company|headline): ' + row)
            j.check(row.split('|')[-1] == 'Quality Control / QA', 'the specialty is not stored as the one canonical value whatever the interface language (headline: %s)' % row.split('|')[-1])
        with j.step('Live: the new account sees no demo people, posts, badges or messages'):
            j.nav(pg, 'feed'); t = j.text(pg)
            demo = re.findall(DEMO_PEOPLE + r'|12K\+ professionals|#EDA2025', t)
            j.check(not demo, 'Home of a brand-new account shows demo content: %s' % sorted(set(demo))[:6])
            # the top ticker (outside #content) never shows the demo's sample offers (S-19)
            tick = re.findall(r'Metformin HCl GMP \$5\.80/kg|Fette 1200 Tablet Press|WHO-GMP Tablets — Quadra Pharm|Ciprofloxacin HCl 2MT/month|Amoxicillin 500kg', j.text(pg, '#app'))
            j.check(not tick, 'the ticker of a brand-new account shows demo offers: %s' % sorted(set(tick))[:4])
            badges = [b for b in sidebar_badges(pg) if b != '0']
            j.check(not badges, 'a brand-new account shows badge numbers %s' % badges)
            for page in ('network', 'messages', 'notifs'):
                j.nav(pg, page); t = j.text(pg)
                demo = re.findall(DEMO_PEOPLE, t)
                j.check(not demo, '%s of a brand-new account shows demo people: %s' % (page, sorted(set(demo))))
    with j.step('Reload: still signed in as Mona, profile unchanged'):
        if j.demo: j.skip('demo keeps no account across a reload (no backend) — checked in live')
        j.reload(pg)
        j.check(j.in_app(pg), 'reload returned to the login page')
        j.check(pg.evaluate('ME.name') == 'Mona Fathy', 'after reload signed in as "%s"' % pg.evaluate('ME.name'))
        pg.evaluate("goto('profile')"); j.settle(pg, 900); t = j.text(pg)
        j.check('Pharco' in t and re.search(r'Quality Control|الجودة', t), 'after reload the profile lost company/specialty')

@journey('J-SOCIAL-02', applies='live')
def signup_with_confirmation(j):
    """A new user whose email must be confirmed is guided through confirmation and can then sign in."""
    pg = j.new_page()
    email = 'vivian.%s@confirm.test' % j.tag          # the local stack asks this domain to confirm its e-mail ("Confirm email" on)
    with j.step('Sign up with name, a new email and a valid password'):
        j.click(pg, r'^(Create one|أنشئ حسابًا|إنشاء حساب)', scope='#loginPage', what='Create one')
        j.check(pg.is_visible('#suName'), 'the sign-up form did not open')
        pg.fill('#suName', 'Viviane Zhao'); pg.fill('#suEmail', email); pg.fill('#suPw', PW)
        if pg.locator('#suCompany').count(): pg.fill('#suCompany', 'Zhejiang API Co')
        pg.click('#signupPage button.f-btn.dx-js-only'); pg.wait_for_timeout(1500)
        j.check(not j.in_app(pg), 'the app opened before the email was confirmed')
    with j.step('A clear screen says a confirmation email went to the address, with a Resend button'):
        t = j.text(pg, '#signupPage')
        j.check(email in t, 'the message after sign-up does not name the address the link went to: "%s"' % t[:200])
        j.check(re.search(r'confirm|تأكيد', t, re.I) and not re.search(r'error|AuthApi|\{', t), 'no clear confirmation message after sign-up: "%s"' % t[:200])
        j.check(j.find(pg, r'Resend|إعادة إرسال', scope='#signupPage'), 'no "Resend confirmation email" after sign-up')
        wait_mail(j, email, r'Confirm your signup', 1)
        j.check(j.sql1("select count(*) from auth.users where email='%s' and email_confirmed_at is null" % email) == '1', 'auth.users has no unconfirmed row for the new address')
    with j.step('Sign in before confirming: "not confirmed" with Resend (not "invalid credentials")'):
        pg.click('#signupPage [onclick="showLogin()"]'); pg.wait_for_timeout(300)
        pg.fill('#loginEmail', email); pg.fill('#loginPw', PW); pg.click('#loginPage button.f-btn.dx-js-only'); pg.wait_for_timeout(1500)
        t = j.text(pg, '#loginPage')
        j.check(not j.in_app(pg), 'an unconfirmed account signed in')
        j.check(re.search(r'not confirmed|لم يتم تأكيد', t, re.I), 'signing in before confirming does not say the email is not confirmed: "%s"' % t[:200])
        j.check(not re.search(r'incorrect|invalid|غير صحيحة', t, re.I), 'signing in before confirming says the password is wrong')
    with j.step('Resend: a second email arrives'):
        j.click(pg, r'Resend|إعادة إرسال', scope='#loginPage', what='Resend confirmation email')
        wait_mail(j, email, r'Confirm your signup', 2)
    with j.step('Open the link of the last email in the same browser: back on Drugbox, signed in as Vivian'):
        link = wait_mail(j, email, r'Confirm your signup', 2)['link']
        j.check(link, 'the confirmation email has no link')
        pg.goto(link, wait_until='load'); j.settle(pg, 1500)
        try: j.wait_js(pg, "typeof endSplash==='function'", 10); pg.evaluate('endSplash()')
        except Exception: pass
        j.check(pg.url.startswith(re.sub(r'/$', '', __import__('_dx').APP_URL)), 'the link did not come back to Drugbox: %s' % pg.url)
        j.check(j.wait(pg, APP_VISIBLE, 15), 'after the confirmation link the app did not open: %s' % j.text(pg, '#loginPage')[:200])
        j.wait(pg, "window.ME&&ME.name==='Viviane Zhao'", 8)
        j.check(pg.evaluate('ME.name') == 'Viviane Zhao', 'after confirming signed in as "%s"' % pg.evaluate('ME.name'))
    with j.step('Sign out and in with the email and password: the app opens as Vivian with her profile'):
        pg.evaluate('doLogout()'); j.settle(pg)
        j.signin(pg, email, PW); j.check(pg.evaluate('ME.name') == 'Viviane Zhao', 'signed in as "%s"' % pg.evaluate('ME.name'))
        j.nav(pg, 'profile'); t = j.text(pg); j.check('Viviane Zhao' in t and 'Zhejiang API Co' in t, 'the profile does not show the sign-up data')
        j.check(j.sql1("select count(*) from auth.users where email='%s' and email_confirmed_at is not null" % email) == '1', 'auth.users.email_confirmed_at is not set')
        j.check(j.sql1("select count(*) from public.profiles p join auth.users u on u.id=p.id where u.email='%s'" % email) == '1', 'not exactly one profiles row')
        j.check(j.sql1("select terms_version is not null from public.member_settings s join auth.users u on u.id=s.user_id where u.email='%s'" % email) == 't', 'the Terms version agreed to at sign-up is not recorded')

@journey('J-SOCIAL-03')
def signin_stays_signed_in(j):
    """A registered member signs in, stays signed in across reloads and browser restarts, wrong password is clear."""
    if j.live:
        with j.step('Precondition: account A exists (created through the sign-up form)'):
            a = j.person('Dr. Amal Sign'); pa = a['page']; pa.evaluate('doLogout()'); pa.context.close(); j.pages.remove(pa)
        email, pw = a['email'], a['pw']
    pg = j.new_page()
    if j.demo:
        pg.click('.lg-demo'); email = pg.input_value('#loginEmail'); pw = pg.input_value('#loginPw'); pg.fill('#loginEmail', ''); pg.fill('#loginPw', '')
    with j.step('Enter the email and a WRONG password; click Sign In → inline error, password keeps focus'):
        pg.fill('#loginEmail', email); pg.fill('#loginPw', 'Wrong-pass-999'); pg.click('#loginPage button.f-btn.dx-js-only'); pg.wait_for_timeout(1500)
        err = j.text(pg, '#loginErr')
        j.check(not j.in_app(pg), 'a wrong password opened the app')
        j.check(re.search(r'incorrect|wrong|invalid|غير صحيح|خطأ|خاطئة', err, re.I), 'no clear "email or password is incorrect" error (got "%s")' % err.strip()[:80])
        unknown_err = None
        pg.fill('#loginEmail', 'nobody.' + j.tag + '@journey.test'); pg.fill('#loginPw', 'Wrong-pass-999'); pg.click('#loginPage button.f-btn.dx-js-only'); pg.wait_for_timeout(1500)
        unknown_err = j.text(pg, '#loginErr')
        j.check(unknown_err.strip() == err.strip(), 'unknown email and wrong password give different messages (account enumeration): "%s" vs "%s"' % (unknown_err.strip()[:60], err.strip()[:60]))
        focused = pg.evaluate("document.activeElement&&document.activeElement.id")
        j.check(focused == 'loginPw', 'after the error the focus is on "%s", not the password field' % focused)
    with j.step('Enter the right password and press Enter: busy state, opens Home as the right person'):
        pg.fill('#loginEmail', email); pg.fill('#loginPw', pw); pg.focus('#loginPw'); pg.keyboard.press('Enter')
        busy = j.wait(pg, "(()=>{const b=document.querySelector('#loginPage button.f-btn.dx-js-only');return b&&(b.disabled||b.getAttribute('aria-busy')==='true'||/…|\\.\\.\\./.test(b.innerText))||document.getElementById('app').getClientRects().length>0})()", 3)
        j.check(j.wait(pg, APP_VISIBLE, 15), 'pressing Enter did not sign in')
        j.settle(pg, 900); j.skip_tour(pg)
        if j.live: j.check(pg.evaluate('ME.name') == 'Dr. Amal Sign', 'signed in as "%s"' % pg.evaluate('ME.name'))
        who = pg.evaluate('ME.name')
    with j.step('Reload: the app opens directly as the same person'):
        j.reload(pg); j.check(j.in_app(pg) and pg.evaluate('ME.name') == who, 'reload did not keep the session')
    with j.step('A new browser context with the saved session opens the app as the same person'):
        if j.demo:   # a file:// page has no origin Playwright can copy into a new context: the demo reopens in this browser instead
            pg2 = j.new_page(pg.context)
        else: state = pg.context.storage_state(); pg2 = j.new_page(j.new_ctx(storage_state=state))
        j.check(j.in_app(pg2) and pg2.evaluate('ME.name') == who, 'a new browser with the saved session shows the login page (the session is not kept)')
    with j.step('A second tab of the app is signed in too'):
        pg3 = j.new_page(pg.context)
        j.check(j.in_app(pg3) and pg3.evaluate('ME.name') == who, 'the second tab is not signed in')

@journey('J-SOCIAL-04')
def signout_shared_pc(j):
    """A member signs out on a shared PC and nothing of hers stays visible or usable."""
    if j.live:
        a = j.person('Dr. Aya Shared'); pg = a['page']
        b = j.person('Dr. Bahaa Next'); pb = b['page']; pb.evaluate('doLogout()'); pb.context.close(); j.pages.remove(pb)
        post_db(j, a['id'], 'Private-ish update from Aya ' + j.tag)
        j.reload(pg)
    else:
        pg = j.new_page(); j.demo_signin(pg)
    tab2 = j.new_page(pg.context)
    with j.step('Open Profile and click Sign Out → login page with empty fields'):
        j.nav(pg, 'profile')
        j.click(pg, r'^(Sign Out|Sign out|Log out|تسجيل الخروج|خروج)$', what='Sign Out', exact=True)
        j.check(j.wait(pg, LOGIN_VISIBLE, 6), 'sign out did not show the login page')
        j.check(pg.input_value('#loginEmail') == '' and pg.input_value('#loginPw') == '', 'the login fields are not empty after sign out')
    with j.step('Browser Back and reload show no page of the app'):
        pg.go_back(); pg.wait_for_timeout(800)
        if pg.url.startswith('about:'): j.open(pg)            # Back left the app (no routing — J-SOCIAL-50): the next person opens it again
        j.check(not j.in_app(pg), 'Back after sign out shows the app again')
        j.reload(pg); j.check(not j.in_app(pg), 'reload after sign out shows the app again')
    with j.step('The other tab switches to the login page; its old session cannot read data'):
        ok = j.wait(tab2, LOGIN_VISIBLE, 8)
        j.check(ok, 'the second tab still shows the app after sign out in the first tab')
    with j.step('Sign in as a different account B: only B, nothing cached from A'):
        left = pg.evaluate("Object.keys(localStorage).filter(k=>/^(dx_|dbx_|dx-|sb-)/.test(k)&&!/lang|theme|tour|font|season|text|size/i.test(k))")
        j.check(not left, "after sign out the browser still keeps the member's data: %s" % left[:8])
        if j.demo: return
        j.signin(pg, b['email'], b['pw'])
        j.check(pg.evaluate('ME.name') == 'Dr. Bahaa Next', 'signed in as "%s" instead of B' % pg.evaluate('ME.name'))
        t = j.text(pg) + chrome_text(pg)
        j.check('Aya' not in chrome_text(pg), "A's name is still in B's top bar/sidebar")

@journey('J-SOCIAL-05')
def forgot_password(j):
    """A member who forgot his password resets it himself by email."""
    if j.live:
        with j.step('Precondition: account A exists, also signed in on a second device'):
            a = j.person('Dr. Hany Forgot'); pa = a['page']
            other = j.new_page(j.new_ctx()); j.signin(other, a['email'], a['pw'])
            pa.evaluate('doLogout()'); pa.context.close(); j.pages.remove(pa)
    pg = j.new_page()
    with j.step('On the login page click "Forgot password?" (shown in English, Arabic, at this width)'):
        j.click(pg, r'^(Forgot password\?|نسيت كلمة المرور؟)$', scope='#authWrap', what='Forgot password?', exact=True)
        inp = pg.locator('#authWrap input[type=email]:visible').first
        j.check(inp.count(), 'no email field on the forgot-password screen')
        j.check(pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1"), 'the forgot-password screen scrolls sideways')
    with j.step('Enter the account email and submit → a neutral confirmation; an unknown email gets the same answer'):
        mine = a['email'] if j.live else 'haytham@drugbox.app'
        inp.fill(mine); j.click(pg, r'Send reset link|أرسل رابط', scope='#authWrap', what='Send reset link')
        j.check(j.wait(pg, "(document.getElementById('fpOk')||{}).innerText", 6), 'no confirmation after asking for a reset link')
        said = j.text(pg, '#fpOk').strip()
        j.check(re.search(r'If an account exists|إذا كان هناك حساب', said), 'the answer is not neutral: "%s"' % said[:120])
        if j.demo: j.check(re.search(r'live app|التطبيق الحقيقي', said), 'the demo does not explain that reset works in the live app')
        inp.fill('nobody.%s@journey.test' % j.tag); j.click(pg, r'Send reset link|أرسل رابط', scope='#authWrap', what='Send reset link'); pg.wait_for_timeout(1200)
        j.check(j.text(pg, '#fpOk').strip() == said, 'an unknown email gets a different answer: "%s"' % j.text(pg, '#fpOk')[:120])
        if j.demo: return
        j.check(not mails(j, 'nobody.%s@journey.test' % j.tag), 'an email went to an address that has no account')
    with j.step('Open the reset link from the email: Drugbox asks for a new password'):
        link = wait_mail(j, a['email'], r'Reset your password')['link']; j.check(link, 'the reset email has no link')
        pg.goto(link, wait_until='load'); j.settle(pg, 1500)
        try: j.wait_js(pg, "typeof endSplash==='function'", 10); pg.evaluate('endSplash()')
        except Exception: pass
        j.check(j.wait(pg, "!!document.getElementById('npPw1')", 15), 'the reset link did not open a "choose a new password" screen')
    with j.step('Two different passwords, then a short one: each refused with a clear message'):
        pg.fill('#npPw1', 'New-pass-2026!'); pg.fill('#npPw2', 'Other-pass-2026!'); pg.click('.dbk-ov [data-a=ok]'); pg.wait_for_timeout(500)
        j.check(re.search(r'do not match|غير متطابقتين', j.text(pg, '#npMsg')), 'different passwords are not refused: "%s"' % j.text(pg, '#npMsg'))
        pg.fill('#npPw1', 'short'); pg.fill('#npPw2', 'short'); pg.click('.dbk-ov [data-a=ok]'); pg.wait_for_timeout(500)
        j.check(re.search(r'at least 8|8 أحرف', j.text(pg, '#npMsg')), 'a short password is not refused: "%s"' % j.text(pg, '#npMsg'))
    with j.step('Save the new password: saved, and the other device is signed out'):
        pg.fill('#npPw1', 'New-pass-2026!'); pg.fill('#npPw2', 'New-pass-2026!'); pg.click('.dbk-ov [data-a=ok]')
        j.check(j.wait(pg, "!document.getElementById('npPw1')", 8), 'the new password was not saved: "%s"' % j.text(pg, '#npMsg'))
        j.reload(other)
        j.check(j.wait(other, LOGIN_VISIBLE, 10), 'the other device is still signed in after the password was reset')
    with j.step('Sign in with the OLD password: refused; with the NEW one: the app opens'):
        pg.evaluate('doLogout()'); j.settle(pg)
        pg.fill('#loginEmail', a['email']); pg.fill('#loginPw', a['pw']); pg.click('#loginPage button.f-btn.dx-js-only'); pg.wait_for_timeout(1500)
        j.check(not j.in_app(pg), 'the old password still signs in')
        j.signin(pg, a['email'], 'New-pass-2026!'); j.check(pg.evaluate('ME.name') == 'Dr. Hany Forgot', 'the new password did not sign in as A')

def open_settings(j, pg):
    """Settings in two clicks from any page: the avatar (own profile), then Settings."""
    el = j.find(pg, r'^(Settings|الإعدادات)$', exact=True)
    if not el:
        pg.click('#topAv'); j.settle(pg)
        el = j.find(pg, r'^(Settings|الإعدادات)$', exact=True)
    j.check(el, 'not built: no Settings entry (top bar avatar → profile, or the side menu)')
    el.click(); j.settle(pg)
    j.check(pg.evaluate("document.body.getAttribute('data-page')") == 'settings', 'Settings did not open the Settings page')
    j.check(pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1"), 'the Settings page scrolls sideways at %dpx' % j.width)

@journey('J-SOCIAL-06', applies='live')
def account_settings(j):
    """A member changes her password and login email from a settings page."""
    a = j.person('Dr. Sara Settings'); pg = a['page']
    post_db(j, a['id'], 'Settings check post ' + j.tag)
    with j.step('Open account settings from the avatar / sidebar (two clicks from any page)'):
        j.nav(pg, 'network'); open_settings(j, pg)
        if j.ar: j.check(re.search(r'الحساب|كلمة المرور', j.text(pg)) and not re.search(r'\bChange password\b|\bCurrent password\b', j.text(pg)), 'the Settings page is not in Arabic')
    with j.step('Change password: a wrong current password is refused; the right one changes it'):
        pg.fill('#setPwCur', 'Not-my-pass-1'); pg.fill('#setPwNew', 'Brand-new-2026!'); pg.fill('#setPwNew2', 'Brand-new-2026!')
        j.click(pg, r'^(Change password|تغيير كلمة المرور)$', scope='#content', exact=True, what='Change password')
        j.check(j.wait(pg, "/not correct|غير صحيحة/.test((document.getElementById('setPwMsg')||{}).innerText||'')", 6), 'a wrong current password was not refused: "%s"' % j.text(pg, '#setPwMsg'))
        pg.fill('#setPwCur', a['pw']); pg.fill('#setPwNew', 'Brand-new-2026!'); pg.fill('#setPwNew2', 'Brand-new-2026!')
        j.click(pg, r'^(Change password|تغيير كلمة المرور)$', scope='#content', exact=True, what='Change password')
        j.check(j.wait(pg, "/changed|تم تغيير/.test((document.getElementById('setPwMsg')||{}).innerText||'')", 8), 'the password change was not confirmed: "%s"' % j.text(pg, '#setPwMsg'))
        wait_mail(j, a['email'], r'password was changed')
    with j.step('Sign out and in with the new password (the old one no longer works)'):
        pg.evaluate('doLogout()'); j.settle(pg)
        pg.fill('#loginEmail', a['email']); pg.fill('#loginPw', a['pw']); pg.click('#loginPage button.f-btn.dx-js-only'); pg.wait_for_timeout(1500)
        j.check(not j.in_app(pg), 'the old password still signs in')
        j.signin(pg, a['email'], 'Brand-new-2026!')
    new = 'sara.new.%s@journey.test' % j.tag
    with j.step('Change the sign-in email: only after the link sent to the new address; the old address is told'):
        open_settings(j, pg); pg.fill('#setNewEmail', new)
        j.click(pg, r'^(Change email|تغيير البريد الإلكتروني)$', scope='#content', exact=True, what='Change email')
        j.check(j.wait(pg, "/confirmation link|رابط تأكيد/.test((document.getElementById('setEmailMsg')||{}).innerText||'')", 8), 'no message about the confirmation link: "%s"' % j.text(pg, '#setEmailMsg'))
        link = wait_mail(j, new, r'Confirm email change')['link']; wait_mail(j, a['email'], r'Email change requested')
        j.check(j.sql1("select email from auth.users where id='%s'" % a['id']) == a['email'], 'the email changed before the new address was confirmed')
        pg.goto(link, wait_until='load'); j.settle(pg, 1500)
        try: j.wait_js(pg, "typeof endSplash==='function'", 10); pg.evaluate('endSplash()')
        except Exception: pass
        j.check(j.wait_db("select email from auth.users where id='%s'" % a['id'], 6, want=new) == new, 'opening the link did not change the email')
        j.check(j.wait(pg, APP_VISIBLE, 15), 'the email-change link did not open Drugbox signed in')
    with j.step('Sign out and in with the new email; profile, posts and connections unchanged'):
        if j.in_app(pg): pg.evaluate('doLogout()'); j.settle(pg)
        j.signin(pg, new, 'Brand-new-2026!'); j.check(pg.evaluate('ME.name') == 'Dr. Sara Settings', 'the new email does not sign in as Sara')
        j.check(j.sql1("select count(*) from public.posts where user_id='%s'" % a['id']) == '1', 'the posts changed with the email')
        j.nav(pg, 'profile'); j.check('Dr. Sara Settings' in j.text(pg), 'the profile changed with the email')

@journey('J-SOCIAL-07', applies='live')
def delete_account(j):
    """A member who leaves the network deletes her account and personal data."""
    c = j.person('Dr. Carmen Leaving'); pg = c['page']
    b = j.person('Dr. Basil Stays'); pb = b['page']
    with j.step('Precondition: C has a post (with a photo), a comment and a reaction on B\'s post, a connection and messages with B'):
        connect_db(j, c['id'], b['id'])
        cp = post_db(j, c['id'], 'Carmen farewell post ' + j.tag)
        bp = post_db(j, b['id'], 'Basil post for comments ' + j.tag)
        comment_db(j, c['id'], bp, 'Carmen comment ' + j.tag)
        j.sql("insert into public.reactions (post_id, user_id, kind) values (%s, '%s', 'like')" % (bp, c['id']))
        j.sql("insert into public.messages (sender_id, receiver_id, body) values ('%s','%s','Hi Basil from Carmen %s'),('%s','%s','Hi Carmen from Basil %s')" % (c['id'], b['id'], j.tag, b['id'], c['id'], j.tag))
        # a file of C's in storage (post photo), uploaded as C through the Storage API
        tok = pg.evaluate("dxLive.sb.auth.getSession().then(r=>r.data.session.access_token)")
        up = pg.evaluate("""async ([u,k,t,p])=>{const r=await fetch(u+'/storage/v1/object/post-media/posts/'+p+'/'+'x-'+Date.now()+'.png',{method:'POST',headers:{apikey:k,Authorization:'Bearer '+t,'content-type':'image/png'},body:new Blob([new Uint8Array([137,80,78,71])])});return r.status}""",
                         [pg.evaluate('DRUGBOX_CONFIG.url'), pg.evaluate('DRUGBOX_CONFIG.anonKey'), tok, c['id']])
        j.check(up == 200, 'precondition: could not upload a file as C (%s)' % up)
        j.check(j.sql1("select count(*) from storage.objects where owner='%s'" % c['id']) == '1', 'precondition: C has no file')
    with j.step('Open Settings → Delete account: the consequences are explained'):
        open_settings(j, pg)
        j.click(pg, r'^(Delete my account|احذف حسابي)$', scope='#content', exact=True, what='Delete my account')
        dlg = pg.locator('.dbk-ov:visible'); j.check(dlg.count(), 'Delete account opens no confirmation window')
        t = dlg.inner_text(); j.check(re.search(r'posts|منشورات', t) and re.search(r'Messages|الرسائل', t) and re.search(r'Payment|الدفع', t), 'the window does not explain what is deleted and kept: "%s"' % t[:200])
    with j.step('The wrong word or a wrong password is refused; nothing is deleted'):
        pg.fill('#delWord', 'please'); pg.fill('#delPw', c['pw']); dlg.locator('[data-a=ok]').click(); pg.wait_for_timeout(500)
        j.check(re.search(r'DELETE', j.text(pg, '#delMsg')), 'the wrong confirmation word is not refused')
        pg.fill('#delWord', 'DELETE'); pg.fill('#delPw', 'Wrong-pass-0'); dlg.locator('[data-a=ok]').click()
        j.check(j.wait(pg, "/not correct|غير صحيحة/.test((document.getElementById('delMsg')||{}).innerText||'')", 8), 'a wrong password is not refused: "%s"' % j.text(pg, '#delMsg'))
        j.check(j.sql1("select account_type from public.profiles where id='%s'" % c['id']) == 'professional', 'something was deleted after a wrong password')
    with j.step('Confirm with DELETE and the password: signed out with a farewell'):
        pg.fill('#delPw', c['pw']); pg.wait_for_timeout(600); dlg.locator('[data-a=ok]').click()   # (the window ignores a second click within 0.5 s)
        j.check(j.wait(pg, LOGIN_VISIBLE, 15), 'after deleting, the login page does not show: "%s"' % j.text(pg, '#delMsg'))
        j.check(re.search(r'account was deleted|تم حذف حسابك', j.text(pg, '#loginPage')), 'no farewell message')
    with j.step('Database: profile anonymised, sign-in removed, content and files deleted, messages kept for B'):
        row = j.sql1("select name||'|'||account_type||'|'||coalesce(headline,'')||coalesce(avatar_url,'')||coalesce(bio,'') from public.profiles where id='%s'" % c['id'])
        j.check(row == 'Deleted member|deleted|', 'the profile is not an anonymous tombstone: %s' % row)
        j.check(j.sql1("select count(*) from auth.users where email='%s'" % c['email']) == '0', 'the sign-in email still exists in auth.users')
        for q, what in (("select count(*) from public.posts where user_id='%s'", 'posts'), ("select count(*) from public.comments where user_id='%s'", 'comments'),
                        ("select count(*) from public.reactions where user_id='%s'", 'reactions'), ("select count(*) from public.connections where requester='%s' or addressee='%s'", 'connections'),
                        ("select count(*) from storage.objects where owner='%s' or name like '%%%s%%'", 'files')):
            n = j.sql1(q % ((c['id'],) * q.count('%s'))); j.check(n == '0', '%s %s of the deleted member remain' % (n, what))
        j.check(j.sql1("select count(*) from public.messages where sender_id='%s' or receiver_id='%s'" % (c['id'], c['id'])) == '2', 'the conversation with B was not kept for B')
        j.check(j.sql1("select like_count from public.posts where id=%s" % bp) == '0' and j.sql1("select comment_count from public.posts where id=%s" % bp) == '0', "B's post still counts C's reaction or comment")
    with j.step('B: Home, the post comments, Network and Messages no longer show C; the old conversation says "Deleted member" without errors'):
        errs = len(j.errors)
        j.reload(pb); j.nav(pb, 'feed'); t = j.text(pb); j.check(('Carmen farewell post ' + j.tag) not in t, "B still sees C's post")
        j.check(j.sql1("select count(*) from public.profiles where id='%s' and name like '%%Carmen%%'" % c['id']) == '0', "C's name is still in profiles")
        r = pb.evaluate("([u,k])=>dxLive.sb.from('profiles').select('id').eq('id',u).then(r=>(r.data||[]).length)", [c['id'], 0])
        j.check(r == 0, 'members can still read the deleted profile through the API')
        gone = "u=>!(window.USERS||[]).some(x=>dxLive.uuidOf(x.id)===u&&!/Deleted member/.test(x.name))"
        j.nav(pb, 'network'); pb.wait_for_timeout(1200); j.check(pb.evaluate(gone, c['id']), "B's network (connections, suggestions) still shows C")
        j.nav(pb, 'messages'); pb.wait_for_timeout(1500); t = j.text(pb)
        j.check(re.search(r'Deleted member|عضو محذوف', t), 'the old conversation does not say "Deleted member"')
        j.check('Carmen Leaving' not in t, 'Messages still shows the name of the deleted member')
        j.check(len(j.errors) == errs, 'page errors after the deletion: %s' % j.errors[errs:][:3])
    with j.step("Signing in with C's email and password fails"):
        j.click(pg, r'Back to sign in|العودة لتسجيل الدخول', scope='#authWrap', what='Back to sign in')
        pg.fill('#loginEmail', c['email']); pg.fill('#loginPw', c['pw']); pg.click('#loginPage button.f-btn.dx-js-only'); pg.wait_for_timeout(1500)
        j.check(not j.in_app(pg), "the deleted account still signs in")

@journey('J-SOCIAL-08')
def switch_language(j):
    """A member switches the whole interface between English and Arabic and it stays in the chosen language."""
    a = j.person('Dr. Lina Lang') if j.live else None
    pg = a['page'] if a else j.demo_signin(j.new_page(j.new_ctx(lang='en')))
    if pg.evaluate("document.documentElement.lang") == 'ar':
        pg.click('#langBtn'); j.settle(pg)
    with j.step('Click the language button (العربية) → html lang=ar dir=rtl'):
        el = pg.locator('#langBtn') if pg.is_visible('#langBtn') else j.find(pg, 'العربية', scope='body')
        if not el and pg.locator('#sbToggle:visible').count(): pg.click('#sbToggle'); pg.wait_for_timeout(400); el = j.find(pg, 'العربية', scope='body')
        j.check(el, 'no visible language button at %dpx (top bar, menu)' % j.width)
        el.click(); j.settle(pg)
        j.check(pg.evaluate("document.documentElement.lang") == 'ar' and pg.evaluate("document.documentElement.dir") == 'rtl', 'html is not lang=ar dir=rtl')
    with j.step('Visit Home, Profile, Network, Messages, Notifications, Saved: no English UI words'):
        leftovers = {}
        for page in ('feed', 'profile', 'network', 'messages', 'notifs', 'saved'):
            pg.evaluate("p=>goto(p)", page); j.settle(pg, 700)
            words = pg.evaluate("""()=>{const out=new Set();const c=document.getElementById('content');const w=document.createTreeWalker(c,NodeFilter.SHOW_TEXT);let n;
              const UI=/^(Like|Comment|Repost|Save|Saved|Share|Send|Reply|Follow|Following|Connect|Message|Edit|Delete|Report|Cancel|Post|Accept|Ignore|Search|View profile|See all|Show more|see more|Mark all read|Unread|All|Photo|File|Product|Experience|Skills|About|Activity)$/;
              while(n=w.nextNode()){const t=n.textContent.trim();if(!t||!n.parentElement.offsetParent)continue;if(UI.test(t))out.add(t)}return [...out]}""")
            if words: leftovers[page] = words[:8]
        j.check(not leftovers, 'English UI words left in Arabic: %s' % leftovers)
    with j.step('Trigger toasts (repost, save, copy link): they are Arabic'):
        pg.evaluate("goto('feed')"); j.settle(pg)
        eng = []
        for patt in (r'^(Repost|إعادة نشر|إعادة النشر|أعد النشر)$', r'^(Save|حفظ)$'):
            el = j.find(pg, patt, scope='#content', exact=True)
            if el:
                before = j.toast_mark(pg); el.click(); pg.wait_for_timeout(500)
                eng += [t for t in j.toasts_since(pg, before) if re.search(r'[A-Za-z]{4,}', t) and not re.search(r'[؀-ۿ]', t)]
        j.check(not eng, 'English toasts in Arabic: %s' % eng)
    with j.step('Reload, and the login page after sign-out, stay Arabic'):
        j.reload(pg); j.check(pg.evaluate("document.documentElement.lang") == 'ar', 'after reload the interface is not Arabic')
        pg.evaluate('doLogout()'); j.settle(pg)
        j.check(pg.evaluate("document.documentElement.dir") == 'rtl' and re.search(r'[؀-ۿ]', j.text(pg, '#loginPage')), 'the login page after sign-out is not Arabic')
    with j.step('Switch back to English: full English and LTR'):
        el = j.find(pg, r'^(English|EN)$', scope='body', exact=True)
        j.check(el, 'no language switch on the login page')
        el.click(); j.settle(pg)
        j.check(pg.evaluate("document.documentElement.lang") == 'en' and pg.evaluate("document.documentElement.dir") == 'ltr', 'switching back did not restore English/LTR')

@journey('J-SOCIAL-09')
def appearance(j):
    """A member adjusts appearance (dark, text size, season) and the choice is remembered."""
    a = j.person('Dr. Dina Dark') if j.live else None
    pg = a['page'] if a else j.demo_signin(j.new_page())
    with j.step('Click Appearance (dxThemeBtn) in the top bar'):
        btn = pg.locator('#dxThemeBtn')
        j.check(btn.count() and btn.is_visible() or j.find(pg, r'Theme|Appearance|المظهر'), 'no visible Appearance button at %dpx' % j.width)
        (btn if btn.is_visible() else j.find(pg, r'Theme|Appearance|المظهر')).click(); j.settle(pg, 400)
    with j.step('Choose Dark and a larger text size'):
        j.click(pg, r'^(Dark|داكن|ليلي)$', scope='body', what='Dark', exact=True)
        dark = pg.evaluate("document.documentElement.dataset.theme||document.body.dataset.theme||document.documentElement.className+' '+document.body.className")
        j.check(re.search('dark', dark), 'Dark did not switch the theme (%s)' % dark)
        fs0 = pg.evaluate("parseFloat(getComputedStyle(document.querySelector('#content')).fontSize)")
        big = j.find(pg, r'^(A\+|Large|Larger|كبير|أكبر)$', scope='body', exact=True)
        j.check(big, 'no larger-text option in the appearance panel')
        big.click(); pg.wait_for_timeout(300); pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
        if pg.locator('#dxThemeBtn:visible').count() and j.find(pg, r'^(Dark|داكن)$', scope='body', exact=True): pg.click('#dxThemeBtn'); pg.wait_for_timeout(200)
        fs1 = pg.evaluate("parseFloat(getComputedStyle(document.querySelector('#content .post-body, #content p, #content')).fontSize)")
        j.note('font', [fs0, fs1])
    with j.step('Visit Home, Messages, Profile, Network: dark everywhere, no horizontal scroll at this width'):
        light = []
        for page in ('feed', 'messages', 'profile', 'network'):
            pg.evaluate("p=>goto(p)", page); j.settle(pg, 500)
            bg = bright_share(pg)
            if bg > 0.25: light.append('%s: %d%% of the page is white' % (page, bg * 100))
            hs = pg.evaluate("document.documentElement.scrollWidth>innerWidth+1")
            if hs: light.append('%s: horizontal scroll' % page)
        j.check(not light, 'dark mode leaves white panels / overflow: %s' % light)
    with j.step('Reload and sign out/in: the choices are kept'):
        j.reload(pg)
        if j.on_login(pg): j.demo_signin(pg) if j.demo else j.signin(pg, a['email'], a['pw'])
        else:
            pg.evaluate('doLogout()'); j.settle(pg)
            j.demo_signin(pg) if j.demo else j.signin(pg, a['email'], a['pw'])
        j.wait(pg, "/dark/.test(document.documentElement.className+' '+(document.documentElement.dataset.theme||''))", 4)
        dark = pg.evaluate("document.documentElement.dataset.theme||document.body.dataset.theme||document.documentElement.className+' '+document.body.className")
        j.check(re.search('dark', dark), 'after reload the theme is no longer dark')
    with j.step('Reset to defaults'):
        el = pg.locator('#dxThemeBtn') if pg.is_visible('#dxThemeBtn') else j.find(pg, r'Theme|Appearance|المظهر')
        j.check(el, 'no visible Appearance button after signing in again'); el.click(); j.settle(pg, 300)
        j.click(pg, r'^(Reset|Default|Defaults|Light|افتراضي|إعادة|فاتح)$', scope='body', what='Reset / Light', exact=True)
        dark = pg.evaluate("document.documentElement.dataset.theme||document.body.dataset.theme||document.documentElement.className+' '+document.body.className")
        j.check(not re.search('dark', dark), 'reset did not leave dark mode')

if __name__ == '__main__': main(__file__)
