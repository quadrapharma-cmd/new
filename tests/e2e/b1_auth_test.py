from playwright.sync_api import sync_playwright
from _dx import APP_URL as U, R, T, sql, ST, refused, ERR, wait_for, done   # shared settings: tests/e2e/_dx.py
EMAIL=f'test{ST}@quadra.test'
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]); ctx=b.new_context(viewport={'width':1440,'height':900}); pg=ctx.new_page(); errs=[]
    pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
    pg.goto(U,wait_until='load'); pg.wait_for_timeout(500); pg.evaluate('endSplash()'); pg.wait_for_timeout(900)
    T('login page shows; demo shortcut hidden in the live app', pg.is_visible('#loginPage') and not pg.is_visible('.lg-demo'))
    pg.fill('#loginEmail', EMAIL); pg.fill('#loginPw','whatever123'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(1200)
    T('unknown account is refused with a clear message', pg.is_visible('#loginErr') and 'Wrong email or password' in pg.inner_text('#loginErr') and not pg.is_visible('#app'), pg.inner_text('#loginErr') if pg.is_visible('#loginErr') else '')
    pg.evaluate("showSignup()"); pg.wait_for_timeout(300)
    pg.fill('#suName','Dr. Test Person'); pg.fill('#suEmail',EMAIL); pg.fill('#suPw','short'); pg.click('#signupPage button.f-btn'); pg.wait_for_timeout(500)
    T('short password refused', 'at least 8' in pg.inner_text('#suErr'))
    pg.fill('#suCompany','Test Labs'); pg.select_option('#suRole', label='Quality Control / QA')
    pg.fill('#suPw','Strong-pass-2026'); pg.click('#signupPage button.f-btn'); pg.wait_for_timeout(2500)
    T('sign-up creates the account and opens the app', pg.is_visible('#app'))
    me=pg.evaluate("({id:dxLive.uuidOf(ME.id),local:ME.id,name:ME.name,ini:ME.initials})")
    T('ME is the real person (database id behind a local number, entered name)', len(str(me['id']))==36 and me['local']>1000 and me['name']=='Dr. Test Person' and me['ini']=='DT', me)
    T('profile row created in the database with the name', sql(f"select name from public.profiles where id='{me['id']}'")=='Dr. Test Person')
    # S-15: the company and specialty typed at sign-up are kept (0029 handle_new_user) and shown as the new person's own
    T('sign-up keeps the company and the specialty (profile row + the app as that person)', sql(f"select company||'|'||headline from public.profiles where id='{me['id']}'")=='Test Labs|Quality Control / QA'
      and pg.evaluate("ME.company+'|'+ME.headline")=='Test Labs|Quality Control / QA', pg.evaluate("ME.company+'|'+ME.headline"))
    T('password stored encrypted (bcrypt), never plain', sql(f"select encrypted_password like '$2%' and encrypted_password<>'Strong-pass-2026' from auth.users where email='{EMAIL}'")=='t')
    pg.evaluate("doLogout()"); pg.wait_for_timeout(1000)
    T('sign-out returns to the login page', pg.is_visible('#loginPage') and not pg.is_visible('#app'))
    T('session removed from the browser', pg.evaluate("!localStorage.getItem('dx-auth')"))
    pg.evaluate("showSignup()"); pg.fill('#suName','Someone Else'); pg.fill('#suEmail',EMAIL); pg.fill('#suPw','Another-pass-1'); pg.click('#signupPage button.f-btn'); pg.wait_for_timeout(1500)
    # an address that is already registered gets the same neutral answer as a new one awaiting confirmation (no account
    # enumeration — Supabase with "Confirm email" on): nothing is created, the app does not open, the first password still works
    T('duplicate email: no second account, neutral message (does not reveal that the address is registered)',
      'Check your email' in pg.inner_text('#suErr') and 'already' not in pg.inner_text('#suErr') and not pg.is_visible('#app')
      and sql(f"select count(*) from auth.users where email='{EMAIL}'") == '1', pg.inner_text('#suErr'))
    pg.evaluate("showLogin()"); pg.fill('#loginEmail',EMAIL); pg.fill('#loginPw','wrong-password'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(1200)
    T('wrong password refused', 'Wrong email or password' in pg.inner_text('#loginErr'))
    pg.fill('#loginPw','Strong-pass-2026'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(2500)
    T('correct password signs in', pg.is_visible('#app') and pg.evaluate("ME.name")=='Dr. Test Person')
    pg.reload(wait_until='load'); pg.wait_for_timeout(600); pg.evaluate('endSplash()'); pg.wait_for_timeout(2500)
    T('reload keeps you signed in (opens the app after the splash)', pg.is_visible('#app') and pg.evaluate("ME.name")=='Dr. Test Person')
    other=sql(f"insert into auth.users (email, encrypted_password) values ('other{ST}@x.test', crypt('x-pass-123', gen_salt('bf'))) returning id").split('\n')[0]
    T('setup: the other person exists (a real id, not an empty string)', len(other)==36 and sql(f"select count(*) from public.profiles where id='{other}'")=='1', other)
    r=pg.evaluate(f"dxLive.sb.from('profiles').update({{name:'HACKED'}}).eq('id','{other}').select().then(r=>({{n:(r.data||[]).length,e:r.error&&{{code:r.error.code,message:r.error.message}}}}))")
    T("cannot change another person's profile (row-level security: the request is accepted, no row matches)", r['n']==0 and not r['e'] and sql(f"select name from public.profiles where id='{other}'")!='HACKED', r)
    r=pg.evaluate("dxLive.sb.from('profiles').update({headline:'QA lead'}).eq('id',dxLive.uuidOf(ME.id)).select().then(r=>({n:(r.data||[]).length,e:r.error&&r.error.message}))")
    T('can change your own profile', r['n']==1 and sql(f"select headline from public.profiles where id='{me['id']}'")=='QA lead', r)
    # F-01: the browser must not be able to make itself admin/verified or change server-kept columns of its own profile
    # (FAILS before migration 0020_security_core.sql — the profiles own-update policy had no column guard)
    me_id=me['id']
    r=pg.evaluate(f"dxLive.sb.from('profiles').update({{role:'admin',verified:true}}).eq('id','{me_id}')"+ERR)
    T('cannot make yourself admin or verified (role and verified are set by Drugbox only)', refused(r) and sql(f"select role||'|'||coalesce(verified::text,'f') from public.profiles where id='{me_id}'") in ('user|f','user|false'), (r, sql(f"select role, verified from public.profiles where id='{me_id}'")))
    r=pg.evaluate(f"dxLive.sb.from('profiles').update({{followers_count:99999,profile_views:99999}}).eq('id','{me_id}')"+ERR)
    T('cannot set your own follower / profile-view counters', refused(r) and sql(f"select coalesce(followers_count,0)<99999 and coalesce(profile_views,0)<99999 from public.profiles where id='{me_id}'")=='t', r)
    # S-01: Edit Profile → Save Changes writes the profile (the real modal and button), a refusal keeps the editor and says why
    def edit_profile(vals, open_to_work=None):
        pg.evaluate("goto('profile')"); pg.wait_for_timeout(700); pg.click('#content button:has-text("Edit Profile")'); pg.wait_for_timeout(300)
        for k, v in vals.items(): pg.fill('#ep-' + k, v)
        if open_to_work is not None: pg.set_checked('#ep-open', open_to_work)
        pg.click('.modal-bg button:has-text("Save Changes")'); pg.wait_for_timeout(1500)
    row=lambda: sql(f"select concat_ws('|',name,headline,company,location,website,phone,certs,open_to_work,bio) from public.profiles where id='{me_id}'")
    edit_profile({'name':'Dr. Test Person','headline':'QC Lead','company':'Test Labs','loc':'Alexandria, Egypt','web':'testlabs.example.org','phone':'+20 3 555 0101','certs':'ISO 17025','bio':'Bio <i>as typed</i>'}, True)
    T('Edit Profile → Save Changes writes every field it edits to the profile row', row()=='Dr. Test Person|QC Lead|Test Labs|Alexandria, Egypt|testlabs.example.org|+20 3 555 0101|ISO 17025|t|Bio <i>as typed</i>'
      and not pg.locator('.modal-bg #ep-name').count(), row())
    edit_profile({'web':'javascript:alert(1)'})
    T('a javascript: website is refused next to the field; nothing is written', pg.is_visible('#ep-err') and pg.locator('.modal-bg #ep-web').count()==1
      and sql(f"select website from public.profiles where id='{me_id}'")=='testlabs.example.org', pg.inner_text('#ep-err') if pg.locator('#ep-err').count() else '')
    pg.evaluate("document.querySelector('.modal-bg').remove()")
    edit_profile({'phone':'+20 ' + '1'*60, 'headline':'Not saved'})
    T('a value the database refuses (0029: phone over 40 characters): the editor stays open with what was typed, a plain message, nothing changed',
      pg.locator('.modal-bg #ep-phone').count()==1 and pg.input_value('#ep-headline')=='Not saved' and pg.evaluate("ME.headline")=='QC Lead'
      and sql(f"select headline from public.profiles where id='{me_id}'")=='QC Lead' and 'too long' in pg.evaluate("document.body.innerText"), row())
    pg.evaluate("document.querySelector('.modal-bg').remove()")
    r=pg.evaluate(f"dxLive.sb.from('profiles').update({{website:'javascript:alert(1)'}}).eq('id','{me_id}')"+ERR)
    T('the database refuses a website that is not a web address (0029), even past the interface', refused(r) and sql(f"select website from public.profiles where id='{me_id}'")=='testlabs.example.org', r)
    pg.reload(wait_until='load'); pg.wait_for_timeout(600); pg.evaluate('endSplash()'); pg.wait_for_timeout(2500)
    T('after a reload the saved profile is shown (headline, location, website, Open to work)', pg.evaluate("[ME.headline,ME.location,ME.web,ME.openToWork].join('|')")=='QC Lead|Alexandria, Egypt|testlabs.example.org|true',
      pg.evaluate("[ME.headline,ME.location,ME.web,ME.openToWork].join('|')"))
    T('no errors in the page', not errs, errs)
    b.close()
done()
