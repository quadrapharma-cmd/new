"""Test videos are WebM (VP8): the open-source Chromium used for tests cannot decode H.264; Chrome/Safari/Edge can.
Intro videos (demo build): company video by its owner, personal video on the profile, candidate chip, limits, persistence, lazy loading."""
from playwright.sync_api import sync_playwright
import os, sys
F = os.environ.get('DEMO_FILE', '/tmp/drugbox_brand.html'); V = '/tmp/vids'; LANG = sys.argv[1] if len(sys.argv) > 1 else 'en'; R = []
def T(n, ok, d=''): R.append(ok); print(('✅ ' if ok else '❌ ') + n + ('' if ok else '  → ' + str(d)[:200]))
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"]); ctx = b.new_context(viewport={'width': 1440, 'height': 900}); ctx.add_init_script("try{localStorage.setItem('dx_lang','%s')}catch(e){}" % LANG)
    pg = ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    def login():
        pg.goto('file://' + F, wait_until='load'); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
        pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(2800)
        if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
    def toast(): return pg.evaluate("(document.querySelector('.dbk-toast')||{}).textContent||''")
    login(); E = pg.evaluate
    E("dxHub.page('quadra-pharm','overview')"); pg.wait_for_timeout(1500)
    T('owner sees "Add a company video" on the company page', E("!!document.querySelector('#dxDir .dx-vid-empty .dx-vid-up')"))
    T('nothing is loaded before upload/play (no <video> element)', E("document.querySelectorAll('.dx-vid video, .dx-vid-chip video').length") == 0)
    with pg.expect_file_chooser() as fc: E("document.querySelector('#dxDir .dx-vid-up').click()")
    fc.value.set_files(V + '/company_intro.webm'); pg.wait_for_timeout(3500)
    T('upload shows the video card with a poster frame and its length (0:04)', E("(()=>{var c=document.querySelector('#dxDir .dx-vid:not(.dx-vid-empty)');return !!(c&&/0:04/.test(c.innerText)&&/url\\(/.test(c.querySelector('.dx-vid-play').style.backgroundImage))})()"), E("(document.querySelector('#dxDir .dx-vid')||{}).innerText||''"))
    T('still no <video> on the page until Play (fast pages)', E("document.querySelectorAll('.dx-vid video, .dx-vid-chip video').length") == 0)
    E("document.querySelector('#dxDir .dx-vid-play').click()"); pg.wait_for_timeout(2000)
    st = E("(()=>{var v=document.querySelector('.dbk-ov video');return v?{rs:v.readyState,dur:Math.round(v.duration)}:null})()")
    T('Play opens the video and it loads (4 s)', st and st['rs'] >= 2 and st['dur'] == 4, st)
    E("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
    E("dxHub.page('medsinia-industries','overview')"); pg.wait_for_timeout(1500)
    T("a company that isn't mine shows no upload button", not E("!!document.querySelector('#dxDir .dx-vid-up')"))
    # personal video + limits
    E("goto('profile')"); pg.wait_for_timeout(1500)
    T('my profile offers "Add a video introduction"', E("!!document.querySelector('.dx-vid-empty .dx-vid-up')"))
    with pg.expect_file_chooser() as fc: E("document.querySelector('.dx-vid-up').click()")
    fc.value.set_files(V + '/too_long.webm'); pg.wait_for_timeout(3000)
    T('a 95-second video is refused with a clear message (limit 90 s)', ('90' in toast()) and E("!!document.querySelector('.dx-vid-empty')"), toast())
    with pg.expect_file_chooser() as fc: E("document.querySelector('.dx-vid-up').click()")
    fc.value.set_files({'name': 'notes.pdf', 'mimeType': 'application/pdf', 'buffer': b'%PDF-1.4'}); pg.wait_for_timeout(1200)
    T('a non-video file is refused', ('MP4' in toast() or 'MP4' in toast().upper()), toast())
    with pg.expect_file_chooser() as fc: E("document.querySelector('.dx-vid-up').click()")
    fc.value.set_files(V + '/me_intro.webm'); pg.wait_for_timeout(3500)
    T('my 3-second introduction is saved and shown on my profile', E("(()=>{var c=document.querySelector('.dx-vid:not(.dx-vid-empty)');return !!(c&&/0:03/.test(c.innerText))})()"))
    # persistence
    login(); E("dxHub.page('quadra-pharm','overview')"); pg.wait_for_timeout(1800)
    T('videos survive a reload', E("!!document.querySelector('#dxDir .dx-vid-play')"))
    # someone else's profile and a candidate card
    other = E("USERS.find(u=>u.id!==ME.id).id")
    E(f"dxMedia.put('p:{other}', new Blob([new Uint8Array(10)],{{type:'video/mp4'}}), {{poster:'',duration:42}})"); pg.wait_for_timeout(300); E("dxVideos.refresh()")
    E(f"gotoProfile({other})"); pg.wait_for_timeout(1500)
    T("another person's video shows on their profile, without upload buttons", E("!!document.querySelector('.dx-vid-play')") and not E("!!document.querySelector('.dx-vid-up')"))
    cand = E("(()=>{var c=[...document.querySelectorAll('#jx .jcard')];return 0})()")
    E("goto('jobs')"); pg.wait_for_timeout(1500)
    # candidate cards are linked to a real person by data-uid (that is how the live app links them)
    uid = other
    E(f"(()=>{{var c=[...document.querySelectorAll('#jx .jcard')].find(x=>x.querySelector('.role-badge.need'));if(c){{c.dataset.uid='{uid}';delete c.dataset.vid}}}})()")
    E(f"dxMedia.put('p:{uid}', new Blob([new Uint8Array(10)],{{type:'video/mp4'}}), {{poster:'',duration:61}})"); pg.wait_for_timeout(300); E("dxVideos.refresh()"); pg.wait_for_timeout(900)
    name = uid
    T('a candidate (linked by data-uid) with a video gets a "▶ Video intro · 1:01" chip', bool(uid) and E("[...document.querySelectorAll('#jx .dx-vid-chip')].some(c=>/1:01/.test(c.textContent))"), (name, uid))
    E("dxHub.page('quadra-pharm','overview')"); pg.wait_for_timeout(1500)
    E("document.querySelector('#dxDir .dx-vid-rm').click()"); pg.wait_for_timeout(1200)
    T('the owner can remove the company video', E("!!document.querySelector('#dxDir .dx-vid-empty')"))
    T('no errors in the page', not errs, errs)
    print(LANG, sum(R), '/', len(R)); b.close()
