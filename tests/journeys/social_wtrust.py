"""Social journey of the trust slice (area w-trust): an identity that does not get lost with a phone (W-20) — a verified phone
that stays private, 'member since', a 'new account' notice on the profile and in a conversation.
Run: python3 tests/journeys/social_wtrust.py --target demo|live --lang en|ar --width 1440|390 --out DIR"""
import re, sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _social import goto_profile
from _biz import dlg_text, dlg_click, close_dialogs
import _dx

def line(pg): return pg.evaluate("(document.querySelector('.wt-line')||{}).innerText||''")

@journey('J-SOCIAL-W20')
def verified_private_phone(j):
    """A member verifies their phone; others see "Phone verified", "Member since" and "New account" — never the number."""
    num = '010%08d' % random.randint(0, 99999999); shown = num[:3] + ' ' + num[3:7] + ' ' + num[7:]
    if j.live:
        a = j.person('Amira Saleh'); pg = a['page']; b = j.person('Bahaa Kamel'); pb = b['page']
    else: pg = j.demo_signin(j.new_page())
    with j.step('My profile: "Member since" and "📱 Verify my phone"'):
        j.nav(pg, 'profile'); j.wait(pg, "!!document.querySelector('.wt-line')", 8); l0 = line(pg)
        j.check(re.search(r'Member since|عضو منذ', l0), 'my profile does not say "Member since": "%s"' % l0)
        j.check(pg.locator('.wt-line [data-wt=phone]').count(), 'not built: no "Verify my phone" on my profile (line: "%s")' % l0)
    with j.step('Verify: the number → a code by SMS → a wrong code is refused → the right code verifies'):
        pg.locator('.wt-line [data-wt=phone]').click(); pg.wait_for_timeout(500)
        j.check(re.search(r'stays private|يفضل خاص', dlg_text(pg)), 'the window does not say the number stays private')
        pg.fill('#wtPh', 'not a number'); dlg_click(j, pg, r'Send code|ابعت الكود', 'Send code'); pg.wait_for_timeout(900)
        j.check(re.search(r'mobile number|رقم موبايل', pg.evaluate("(document.getElementById('wtPhErr')||{}).innerText||''")), 'a wrong number is not refused with a reason')
        pg.fill('#wtPh', shown); dlg_click(j, pg, r'Send code|ابعت الكود', 'Send code'); pg.wait_for_timeout(1500)
        t = dlg_text(pg); j.check(re.search(r'Enter the code|اكتب الكود', t), 'the code window did not open (dialog: "%s")' % t[:160])
        if j.live:
            code = j.wait_db("select substring(body from 'code: (\\d{6})') from private.sms_outbox where phone='+20%s' order by id desc limit 1" % num[1:], 8)
            j.check(code and len(code) == 6, 'no SMS with a code was queued for the number')
        else:
            m = re.search(r'(\d{6})', t); j.check(m, 'the demo does not show its code (no SMS in the demo)'); code = m.group(1)
        pg.fill('#wtCode', '000000' if code != '000000' else '111111'); pg.locator('.dbk-ov [data-a=ok]').last.click(); pg.wait_for_timeout(1200)
        j.check(re.search(r'not right|غير صحيح', pg.evaluate("(document.getElementById('wtCodeErr')||{}).innerText||''")), 'a wrong code is not refused')
        pg.fill('#wtCode', code); mark = j.toast_mark(pg); pg.locator('.dbk-ov [data-a=ok]').last.click(); j.settle(pg, 1500)
        j.check(re.search(r'phone is verified|رقمك اتوثّق', ' '.join(j.toasts_since(pg, mark))), 'not told the phone is verified')
        j.wait(pg, "!!document.querySelector('.wt-line .wt-ok')", 8)
        j.check(re.search(r'Phone verified|رقم موثّق', line(pg)), 'my profile does not show "Phone verified": "%s"' % line(pg))
        if j.live:
            j.check(j.sql1("select phone_verified_at is not null from public.member_verifications where user_id='%s'" % a['id']) == 't', 'no verification in the database')
            j.check(j.sql1("select phone from public.profiles where id='%s'" % a['id']) == '+20' + num[1:], 'the verified number is not my (private) phone')
    with j.step('After a reload it is still verified'):
        j.reload(pg); j.nav(pg, 'profile'); j.wait(pg, "!!document.querySelector('.wt-line .wt-ok')", 8)
        j.check(re.search(r'Phone verified|رقم موثّق', line(pg)), 'after a reload the phone is not shown as verified')
    if j.live:
        with j.step('Another member sees "Phone verified", "Member since", "New account" — never the number (not in the page, not through the API)'):
            j.nav(pb, 'feed'); goto_profile(j, pb, a); j.wait(pb, "!!document.querySelector('.wt-line .wt-ok')", 8); l1 = line(pb)
            j.check(re.search(r'Phone verified|رقم موثّق', l1) and re.search(r'Member since|عضو منذ', l1) and re.search(r'New account|حساب جديد', l1), 'another member sees: "%s"' % l1)
            j.check(num[1:] not in pb.evaluate("document.body.innerText").replace(' ', ''), 'the number shows on the profile to another member')
            r = pb.evaluate("u=>Promise.all([dxLive.sb.from('profiles').select('phone').eq('id',u),dxLive.sb.from('member_verifications').select('phone_hash').eq('user_id',u),dxLive.sb.rpc('trade_card',{p_user:u})]).then(a=>[a[0].error?'refused':JSON.stringify(a[0].data),a[1].error?'refused':JSON.stringify(a[1].data),JSON.stringify(a[2].data)])", a['id'])
            j.check(r[0] == 'refused' and r[1] == 'refused' and num[1:] not in r[2], 'the number or its hash can be read through the API: %s' % r)
            r = pb.evaluate("p=>dxLive.sb.rpc('phone_verify_start',{p_phone:p}).then(x=>x.error?x.error.message:'sent')", shown)
            j.check(re.search(r'already verified on another', r), 'another account can verify the same number: %s' % r)
        with j.step('In a conversation with a new account, a notice says so'):
            pb.evaluate("u=>messageUser(dxLive.aid(u))", a['id']); j.settle(pb, 2500)
            j.wait(pb, "!!document.querySelector('.wt-newacc')", 10)
            j.check(re.search(r'New account|حساب جديد', pb.evaluate("(document.querySelector('.wt-newacc')||{}).innerText||''")), 'no new-account notice in the conversation')
        with j.step('Another number typed in Edit Profile is not verified any more'):
            j.sql("update public.profiles set phone='+201099990000' where id='%s'" % a['id'])
            j.check(j.sql1("select phone_verified_at is null from public.member_verifications where user_id='%s'" % a['id']) == 't', 'a changed number stays verified')
            j.reload(pg); j.nav(pg, 'profile'); j.wait(pg, "!!document.querySelector('.wt-line [data-wt=phone]')", 8)
            j.check(pg.locator('.wt-line [data-wt=phone]').count(), 'after changing the number the profile still says verified')
    else:
        with j.step('A conversation with a sample new account shows the new-account notice'):
            pg.evaluate("messageUser(6)"); j.settle(pg, 2000); j.wait(pg, "!!document.querySelector('.wt-newacc')", 8)
            j.check(re.search(r'New account|حساب جديد', pg.evaluate("(document.querySelector('.wt-newacc')||{}).innerText||''")), 'no new-account notice in the conversation')

def said(j, pg, sel, what):
    """The message shown in `sel`, in the interface language: Arabic words (and no English sentence) when the interface is Arabic."""
    j.check(j.wait(pg, "(document.querySelector(%r)||{}).innerText" % sel, 6), 'no message after %s' % what)
    t = j.text(pg, sel).strip()
    j.check(not re.search(r'AuthApi|Error:|\{|seconds|\bnull\b|undefined', t), '%s shows a technical message: "%s"' % (what, t[:160]))
    if j.ar: j.check(re.search(r'[ء-ي]', t) and not re.search(r'[A-Za-z]{4,} [A-Za-z]{3,}', t), '%s is not in Arabic: "%s"' % (what, t[:160]))
    return t

@journey('J-SOCIAL-W04', applies='live')
def auth_errors(j):
    """Every sign-in, sign-up and reset answer is a clear sentence in the interface language, and none tells a stranger whether an e-mail has an account."""
    from _social import mails, wait_mail
    a = j.person('Rasha Fathy'); pa = a['page']; pa.evaluate('doLogout()'); pa.context.close(); j.pages.remove(pa)
    nobody = 'nobody.%s@journey.test' % j.tag
    pg = j.new_page()
    with j.step('Sign in with a wrong password, then with an e-mail that has no account: the same sentence'):
        pg.fill('#loginEmail', a['email']); pg.fill('#loginPw', 'Wrong-pass-1!'); pg.click('#loginPage button.f-btn.dx-js-only'); pg.wait_for_timeout(1500)
        j.check(not j.in_app(pg), 'a wrong password signed in')
        t1 = said(j, pg, '#loginErr', 'a wrong password')
        j.check(re.search(r'Wrong email or password|غير صحيحة', t1), 'a wrong password is not said plainly: "%s"' % t1)
        pg.fill('#loginEmail', nobody); pg.fill('#loginPw', 'Wrong-pass-1!'); pg.click('#loginPage button.f-btn.dx-js-only'); pg.wait_for_timeout(1500)
        j.check(said(j, pg, '#loginErr', 'an unknown e-mail') == t1, 'an e-mail without an account gets another answer than a wrong password')
    with j.step('Sign up with a short password: refused with the reason'):
        j.click(pg, r'^(Create one|أنشئ حسابًا|إنشاء حساب)', scope='#loginPage', what='Create one')
        pg.fill('#suName', 'Rasha Second'); pg.fill('#suEmail', 'rasha2.%s@journey.test' % j.tag); pg.fill('#suPw', 'short')
        pg.click('#signupPage button.f-btn.dx-js-only'); pg.wait_for_timeout(1200)
        t = said(j, pg, '#suErr', 'a short password'); j.check(re.search(r'at least 8|8 أحرف', t), 'a short password is not refused with the reason: "%s"' % t)
        j.check(not j.in_app(pg), 'a short password signed up')
    with j.step('Sign up again with an e-mail that already has an account: no account made, no session, nothing revealed'):
        pg.fill('#suEmail', a['email']); pg.fill('#suPw', 'Another-pass-2026!'); pg.click('#signupPage button.f-btn.dx-js-only'); pg.wait_for_timeout(1500)
        j.check(not j.in_app(pg), 'signing up with a registered e-mail opened the app')
        t = j.text(pg, '#signupPage'); j.check(not re.search(r'AuthApi|\{', t), 'a technical message: "%s"' % t[:160])
        j.check(j.sql1("select count(*) from auth.users where email='%s'" % a['email'].lower()) == '1', 'a second account was made for the same e-mail')
    with j.step('Forgot password for my e-mail and for an unknown one: the same neutral answer; only mine gets a mail'):
        pg.click('#signupPage [onclick="showLogin()"]'); pg.wait_for_timeout(300)
        j.click(pg, r'^(Forgot password\?|نسيت كلمة المرور؟)$', scope='#authWrap', what='Forgot password?', exact=True)
        inp = pg.locator('#fpEmail'); inp.fill(a['email']); j.click(pg, r'Send reset link|أرسل رابط', scope='#authWrap', what='Send reset link')
        ok1 = said(j, pg, '#fpOk', 'asking for a reset link')
        inp.fill(nobody); j.click(pg, r'Send reset link|أرسل رابط', scope='#authWrap', what='Send reset link'); pg.wait_for_timeout(1500)
        j.check(j.text(pg, '#fpOk').strip() == ok1 and not j.text(pg, '#fpErr').strip(), 'an unknown e-mail gets another answer: "%s" / "%s"' % (j.text(pg, '#fpOk')[:100], j.text(pg, '#fpErr')[:100]))
        wait_mail(j, a['email'], r'Reset your password', 1); j.check(not mails(j, nobody), 'a mail went to an address that has no account')
    with j.step('Ask again at once, for mine and for the unknown one: "wait a moment" for both (one mail a minute), no second mail'):
        for who in (a['email'], nobody):
            inp.fill(who); j.click(pg, r'Send reset link|أرسل رابط', scope='#authWrap', what='Send reset link'); pg.wait_for_timeout(1500)
            t = said(j, pg, '#fpErr', 'asking again at once'); j.check(re.search(r'wait a moment|انتظر دقيقة', t), 'asking again at once does not say to wait: "%s"' % t)
            if who == nobody: j.check(t == t_mine, 'the unknown e-mail gets another "wait" answer: "%s" vs "%s"' % (t, t_mine))
            else: t_mine = t
        j.check(len([m for m in mails(j, a['email']) if re.search(r'Reset your password', m.get('subject', ''))]) == 1, 'a second reset mail went out within the minute')
    with j.step('Open the reset link, then open the same link again: the second time says the link is used or expired'):
        link = wait_mail(j, a['email'], r'Reset your password', 1)['link']
        p1 = j.new_page(j.new_ctx()); p1.goto(link, wait_until='load'); j.settle(p1, 1500)
        try: j.wait_js(p1, "typeof endSplash==='function'", 10); p1.evaluate('endSplash()')
        except Exception: pass
        j.check(j.wait(p1, "!!document.getElementById('npPw1')", 15), 'the reset link did not open "choose a new password"')
        p2 = j.new_page(j.new_ctx()); p2.goto(link, wait_until='load'); j.settle(p2, 1500)
        try: j.wait_js(p2, "typeof endSplash==='function'", 10); p2.evaluate('endSplash()')
        except Exception: pass
        j.check(not j.wait(p2, "!!document.getElementById('npPw1')", 3), 'a used reset link opened "choose a new password" again')
        t = said(j, p2, '#loginErr', 'a used link'); j.check(re.search(r'invalid or has expired|غير صالح', t), 'a used link is not explained: "%s"' % t)


if __name__ == '__main__': main()
