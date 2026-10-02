"""Live intro videos: an owner uploads the company video (real button), another member watches it from Storage; a personal video;
Storage refuses uploads outside your own folder, wrong file types, and edits to someone else's video details. (WebM: the test
browser is open-source Chromium, which cannot decode H.264.)"""
from playwright.sync_api import sync_playwright
import subprocess, time, os
U = os.environ.get('APP_URL', 'http://localhost:54321/'); DB = os.environ.get('DB_NAME', 'drugbox_live'); V = '/tmp/vids'; R = []
def T(n, ok, d=''): R.append(ok); print(('✅ ' if ok else '❌ ') + n + ('' if ok else '  → ' + str(d)[:220]))
def sql(q):
    r = subprocess.run(['psql', '-h', '/tmp', '-p', '5433', '-U', 'postgres', '-d', DB, '-tA', '-v', 'ON_ERROR_STOP=1', '-c', q], capture_output=True, text=True)
    if r.returncode: raise SystemExit('SQL failed: ' + r.stderr.strip()[:300])
    return r.stdout.strip()
st = int(time.time()); PW = 'Strong-pass-2026'
def signup(pg, name, email):
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', name); pg.fill('#suEmail', email); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn'); pg.wait_for_timeout(3500)
    return pg.evaluate("dxLive.uuidOf(ME.id)")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"]); errs = []
    O, X = [b.new_context(viewport={'width': 1440, 'height': 900}).new_page() for _ in range(2)]
    for pg in (O, X): pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    o = signup(O, 'Dr. Video Owner', f'vown{st}@x.test'); x = signup(X, 'Dr. Viewer', f'vview{st}@x.test')
    slug = f'video-pharma-{st}'
    cid = sql(f"insert into public.companies (owner_id, name, slug, type, status, sectors) values ('{o}','Video Pharma {st}','{slug}','Manufacturer','verified','{{Manufacturer}}') returning id").split('\n')[0]
    O.reload(wait_until='load'); O.wait_for_timeout(400); O.evaluate('endSplash()'); O.wait_for_timeout(4500)
    O.evaluate(f"dxHub.page('{slug}','overview')"); O.wait_for_timeout(2500)
    with O.expect_file_chooser() as fc: O.evaluate("document.querySelector('#dxDir .dx-vid-up').click()")
    fc.value.set_files(V + '/company_intro.webm'); O.wait_for_timeout(5000)
    iv = sql(f"select intro_video->>'path'||'|'||(intro_video->>'duration') from public.companies where id={cid}")
    T('the owner uploads the company video: stored in the company folder, length recorded', iv.startswith(f'companies/{cid}/intro.webm|4'), iv)
    T('the video and its poster frame are in Storage', sql(f"select count(*) from storage.objects where bucket_id='videos' and name like 'companies/{cid}/%'") == '2' and os.path.exists(f'/tmp/drugbox-storage/videos/companies/{cid}/intro.webm'))
    X.reload(wait_until='load'); X.wait_for_timeout(400); X.evaluate('endSplash()'); X.wait_for_timeout(4500)
    X.evaluate(f"dxHub.page('{slug}','overview')"); X.wait_for_timeout(2500)
    T('another member sees the company video card (without upload buttons)', X.evaluate("!!document.querySelector('#dxDir .dx-vid-play')") and not X.evaluate("!!document.querySelector('#dxDir .dx-vid-up')"))
    X.evaluate("document.querySelector('#dxDir .dx-vid-play').click()"); X.wait_for_timeout(3500)
    stt = X.evaluate("(()=>{var v=document.querySelector('.dbk-ov video');return v?{rs:v.readyState,d:Math.round(v.duration),src:v.currentSrc.indexOf('/storage/v1/object/public/videos/')>0}:null})()")
    T('…and plays it from Storage', stt and stt['rs'] >= 2 and stt['d'] == 4 and stt['src'], stt)
    X.evaluate("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
    X.evaluate("goto('profile')"); X.wait_for_timeout(2000)
    with X.expect_file_chooser() as fc: X.evaluate("document.querySelector('.dx-vid-up').click()")
    fc.value.set_files(V + '/me_intro.webm'); X.wait_for_timeout(5000)
    T('a person uploads their own introduction (people/<their id>/)', sql(f"select intro_video->>'path' from public.profiles where id='{x}'") == f'people/{x}/intro.webm')
    O.evaluate(f"gotoProfile(dxLive.aid('{x}'))"); O.wait_for_timeout(2500)
    T("opening the profile of someone not seen before shows THEIR profile (not mine)", O.evaluate("window._profUser&&window._profUser.name") == 'Dr. Viewer', O.evaluate("window._profUser&&window._profUser.name"))
    T("others see that person's video on their profile", O.evaluate("!!document.querySelector('.dx-vid-play')") and not O.evaluate("!!document.querySelector('.dx-vid-up')"))
    # security, straight against Storage and the database
    r = X.evaluate(f"dxLive.sb.storage.from('videos').upload('companies/{cid}/intro.webm', new Blob([new Uint8Array(100)],{{type:'video/webm'}}), {{upsert:true}}).then(r=>!!r.error)")
    T("cannot upload into a company you don't manage", r)
    r = X.evaluate(f"dxLive.sb.storage.from('videos').upload('people/{o}/fake.webm', new Blob([new Uint8Array(100)],{{type:'video/webm'}})).then(r=>!!r.error)")
    T("cannot upload into someone else's folder", r)
    r = X.evaluate(f"dxLive.sb.storage.from('videos').upload('people/{x}/notes.txt', new Blob(['hello'],{{type:'text/plain'}})).then(r=>!!r.error)")
    T('Storage refuses files that are not videos', r)
    r = X.evaluate(f"dxLive.sb.storage.from('videos').remove(['companies/{cid}/intro.webm']).then(r=>(r.data||[]).length)")
    T("cannot delete another company's video", r == 0 and os.path.exists(f'/tmp/drugbox-storage/videos/companies/{cid}/intro.webm'))
    r = X.evaluate(f"dxLive.sb.from('profiles').update({{intro_video:{{path:'people/{x}/intro.webm',duration:1}}}}).eq('id','{o}').select().then(r=>(r.data||[]).length)")
    T("cannot change someone else's video details", r == 0)
    O.evaluate(f"dxHub.page('{slug}','overview')"); O.wait_for_timeout(2000)
    O.evaluate("document.querySelector('#dxDir .dx-vid-rm').click()"); O.wait_for_timeout(2500)
    T('the owner removes the video: files and details are gone', sql(f"select intro_video is null from public.companies where id={cid}") == 't' and sql(f"select count(*) from storage.objects where name like 'companies/{cid}/%'") == '0')
    T('no errors in the pages', not errs, errs)
    print(sum(R), '/', len(R)); b.close()
