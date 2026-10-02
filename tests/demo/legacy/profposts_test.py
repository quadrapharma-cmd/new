from playwright.sync_api import sync_playwright
import sys
LANG=sys.argv[1] if len(sys.argv)>1 else 'en'
R=[]
def T(n,ok,d=''): R.append(ok); print(('✅ ' if ok else '❌ ')+n+('' if ok else '  → '+str(d)[:200]))
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]); ctx=b.new_context(viewport={'width':1440,'height':900}); ctx.add_init_script("try{localStorage.setItem('dx_lang','%s')}catch(e){}"%LANG)
    pg=ctx.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
    pg.goto('file:///tmp/drugbox_brand.html',wait_until='load'); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(2800)
    if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
    E=pg.evaluate
    E("goto('profile')"); pg.wait_for_timeout(900)
    n=E("document.querySelectorAll('#profileTabContent .post').length"); T('my profile shows my posts as full cards', n>=1, n)
    T('card has author name + actions (like/comment)', E("(()=>{var p=document.querySelector('#profileTabContent .post');return !!(p&&/Haytham/.test(p.innerText)&&p.querySelectorAll('button,[onclick]').length>=3)})()"))
    T('full text available (not cut at 220 chars)', E("(()=>{var p=document.querySelector('#profileTabContent .post');return p.innerText.length>260})()"), E("document.querySelector('#profileTabContent .post').innerText.length"))
    T('post count shown', E("!!document.querySelector('#profileTabContent .dx-pp-h')"))
    pg.locator('.ptab[data-tab="about"]').click(); pg.wait_for_timeout(300)
    T('About tab unchanged (bio, no post cards)', E("document.querySelectorAll('#profileTabContent .post').length")==0 and E("document.getElementById('profileTabContent').innerText.length")>20)
    pg.locator('.ptab[data-tab="activity"]').click(); pg.wait_for_timeout(300)
    T('back to Activity: cards again', E("document.querySelectorAll('#profileTabContent .post').length")>=1)
    lk=E("(()=>{var p=document.querySelector('#profileTabContent .post');var b=[...p.querySelectorAll('button,[onclick]')].find(x=>/like|react|أعجب|تفاعل/i.test((x.getAttribute('onclick')||'')+x.className+x.textContent));return b?b.getAttribute('onclick')||b.className:null})()")
    before=E("document.querySelector('#profileTabContent .post').innerText")
    if lk: E("(()=>{var p=document.querySelector('#profileTabContent .post');var b=[...p.querySelectorAll('button,[onclick]')].find(x=>/like|react|أعجب|تفاعل/i.test((x.getAttribute('onclick')||'')+x.className+x.textContent));b.click()})()"); pg.wait_for_timeout(400)
    T('like works on the profile card', lk and E("document.querySelector('#profileTabContent .post')?document.querySelector('#profileTabContent .post').innerText:''")!=before, lk)
    E("goto('feed')"); pg.wait_for_timeout(500)
    E("showPostModal()"); pg.wait_for_timeout(400)
    ok=E("!!document.getElementById('postBody')")
    if ok:
        pg.fill('#postBody','Test post from the composer — should appear on my profile.'); E("submitPost()"); pg.wait_for_timeout(600)
    E("goto('profile')"); pg.wait_for_timeout(900)
    T('a new post appears on my profile at once', ok and 'Test post from the composer' in E("document.getElementById('profileTabContent').innerText"), ok)
    uid=E("(POSTS.find(p=>p.uid!==ME.id)||{}).uid"); E(f"gotoProfile({uid})"); pg.wait_for_timeout(900)
    T("another person's profile shows their posts", E("document.querySelectorAll('#profileTabContent .post').length")>=1 and not E("/Haytham Dweedar/.test((document.querySelector('#profileTabContent .post .post-name')||{}).textContent||'')"))
    print('errors:', errs or 'none'); print(LANG, sum(R),'/',len(R)); b.close()
