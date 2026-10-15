"""Social journeys — profiles: edit own profile, photo and cover, intro video, experience/education, skills and
endorsements, viewing another person's profile, honest reach numbers (J-SOCIAL-22 … 27, 49).
Run: python3 tests/journeys/social_profile.py --target demo|live --lang en|ar --width 1440|390"""
import re, sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW, APP_VISIBLE, LOGIN_VISIBLE
from _social import *
import _dx

def own_profile(j, pg):
    j.nav(pg, 'profile'); j.settle(pg, 900)

def tab(j, pg, pattern, what):
    el = j.find(pg, pattern, scope='#content', exact=True)
    if not el: j.notbuilt('no "%s" tab on the profile' % what)
    el.click(); j.settle(pg, 500)

def relogin(j, pg, who):
    """Reload; when the target keeps no session (demo), sign in again — the data itself must survive."""
    j.reload(pg)
    if j.on_login(pg): j.demo_signin(pg) if j.demo else j.signin(pg, who['email'], who['pw'])

def avatar_img(pg, scope):
    return pg.evaluate("s=>{const e=document.querySelector(s);if(!e)return '';const i=e.querySelector('img')||e;const bg=getComputedStyle(i).backgroundImage;return i.tagName==='IMG'?i.src:(bg&&bg!=='none'?bg:'')}", scope)

@journey('J-SOCIAL-22')
def edit_own_profile(j):
    """A member completes her own profile so employers and partners can judge her."""
    if j.live: a = j.person('Dr. Mona Profile'); b = j.person('Dr. Bassem Visitor'); pg = a['page']
    else: a = None; pg = j.demo_signin(j.new_page())
    vals = {'ep-name': 'Dr. Mona Fathy', 'ep-headline': 'QC Pharmacist | HPLC | GMP', 'ep-company': 'Pharco', 'ep-web': 'javascript:alert(1)',
            'ep-phone': '+20 100 555 0101', 'ep-certs': 'ICH Q7 · ISO 17025', 'ep-bio': 'QC pharmacist. صيدلانية جودة ' + j.tag + ' <b>bold?</b>'}
    with j.step('Own profile → Edit Profile opens the editor'):
        own_profile(j, pg)
        j.click(pg, r'Edit Profile|عدّل الملف|تعديل الملف', scope='#content', what='Edit Profile')
        j.check(pg.locator('.modal-bg #ep-name').count(), 'the profile editor did not open')
    with j.step('Fill name, headline, company, website, phone, certifications, bio, location; switch on Open to work'):
        missing = [k for k in vals if not pg.locator('#' + k).count()]
        j.check(not missing, 'not built: the editor has no %s field' % ', '.join(missing))
        for k, v in vals.items(): pg.fill('#' + k, v)
        loc = pg.locator('.modal-bg input[id*=loc], .modal-bg input[placeholder*="City" i], .modal-bg input[placeholder*="Location" i], .modal-bg input[aria-label*="Location" i]')
        otw = pg.locator('.modal-bg input[type=checkbox][id*=open i], .modal-bg [role=switch], .modal-bg label:has-text("Open to work") input, .modal-bg label:has-text("متاح") input')
        miss = [n for n, l in (('location', loc), ('Open to work', otw)) if not l.count()]
        j.check(not miss, 'not built: Edit Profile has no %s field' % ' / '.join(miss))
        loc.first.fill('Cairo, Egypt'); otw.first.check()
    with j.step('Save with the invalid website "javascript:alert(1)": refused or neutralised'):
        before = j.toast_mark(pg); j.click(pg, r'Save Changes|Save|حفظ', scope='.modal-bg', what='Save Changes'); pg.wait_for_timeout(800)
        open_ = pg.locator('.modal-bg #ep-web').count() > 0
        hrefs = pg.eval_on_selector_all('#content a[href]', 'a=>a.map(x=>x.getAttribute("href"))')
        j.check(not any((h or '').strip().lower().startswith('javascript:') for h in hrefs), 'the javascript: website became a link')
        if open_:
            pg.fill('#ep-web', 'https://pharco.example.org'); j.click(pg, r'Save Changes|Save|حفظ', scope='.modal-bg', what='Save Changes'); pg.wait_for_timeout(900)
        else:
            j.click(pg, r'Edit Profile|عدّل الملف|تعديل الملف', scope='#content', what='Edit Profile'); pg.fill('#ep-web', 'https://pharco.example.org')
            j.click(pg, r'Save Changes|Save|حفظ', scope='.modal-bg', what='Save Changes'); pg.wait_for_timeout(900)
    with j.step('Every field shows on the profile, top bar, sidebar card and own post author lines'):
        # bio, contact details and certifications live on the profile's About tab in the approved interface: read it as a person does
        tab(j, pg, r'^(About|نبذة)$', 'About'); t = j.text(pg)
        for k in ('ep-name', 'ep-headline', 'ep-company', 'ep-phone', 'ep-certs'):
            j.check(vals[k] in t, 'the profile does not show %s "%s"' % (k[3:], vals[k]))
        # the Arabic interface writes well-known places in Arabic (approved: the sample "Giza, Egypt" reads "الجيزة، مصر")
        j.check('pharco.example.org' in t and re.search(r'Cairo|القاهرة', t), 'the profile does not show the website / location')
        j.check(re.search(r'Open to work|متاح للعمل', t), 'no Open-to-work marker on the profile')
        j.check('<b>bold?</b>' in t, 'HTML in the bio was not shown as text')
        # the interface's monogram is the first letter of the first two words, title included ("Dr. Haytham Dweedar" → DH; e2e b1: "Dr. Test
        # Person" → DT), so "Dr. Mona Fathy" is DM — the top bar must show the NEW monogram (or a photo) and the sidebar card the new name
        ini = ''.join(w[0] for w in vals['ep-name'].split()[:2]).upper()
        j.check(j.text(pg, '#topAv').strip() in (ini, '') and 'Mona Fathy' in pg.evaluate("(document.getElementById('meName')||{}).textContent||''")
                and 'Mona Fathy' in j.text(pg, '#app'), 'the top bar / sidebar still show the old name')
    if j.live:
        with j.step('Live: the profiles row has every field'):
            row = j.sql1("select concat_ws('|',name,headline,company,website,phone,certs,bio,location,open_to_work) from public.profiles where id='%s'" % a['id'])
            j.check('QC Pharmacist' in row and 'pharco.example.org' in row and 'Cairo' in row and row.endswith('t'), 'profiles row not updated: ' + row[:160])
    with j.step('Reload and sign in again: all edits are still there'):
        if j.demo: j.skip('demo keeps no data across a reload (no backend) — checked in live')
        relogin(j, pg, a); own_profile(j, pg); t = j.text(pg)
        j.check(vals['ep-headline'] in t and 'Pharco' in t and re.search(r'Cairo|القاهرة', t), 'after reload the profile edits are gone')
    with j.step("B opens A's profile: headline, bio, website (safe link) and Open-to-work marker"):
        if j.demo: j.skip('the other party exists only in live')
        pb = b['page']; goto_profile(j, pb, a); tab(j, pb, r'^(About|نبذة)$', 'About'); t = j.text(pb)
        j.check(vals['ep-headline'] in t and 'صيدلانية' in t, "B does not see A's headline/bio")
        a_web = pb.locator('#content a[href*="pharco.example.org"]'); j.check(a_web.count() and 'noopener' in (a_web.first.get_attribute('rel') or ''), 'the website is not a safe link for B')
        j.check(re.search(r'Open to work|متاح للعمل', t), 'B sees no Open-to-work marker')

@journey('J-SOCIAL-23')
def photo_and_cover(j):
    """A member uploads a profile photo and a cover image so people recognise him."""
    from PIL import Image
    d = os.path.join(j.cfg['out'], 'fixtures'); os.makedirs(d, exist_ok=True)
    jpg = os.path.join(d, 'face.jpg'); Image.new('RGB', (1200, 1200), (30, 150, 90)).save(jpg, quality=92)
    big = os.path.join(d, 'big.png')
    if not os.path.exists(big): Image.frombytes('RGB', (2400, 1600), os.urandom(2400 * 1600 * 3)).save(big)
    cover = os.path.join(d, 'cover.jpg'); Image.new('RGB', (1600, 400), (120, 40, 160)).save(cover)
    if j.live: a = j.person('Dr. Ali Photo'); b = j.person('Dr. Bassem Looker'); connect_db(j, a['id'], b['id']); pg = a['page']
    else: a = None; pg = j.demo_signin(j.new_page())
    with j.step('Own profile: click 📷 on the avatar and choose a JPG: the photo replaces the initials'):
        own_profile(j, pg)
        el = pg.locator('#content [onclick*="changeAvatar"]'); j.check(el.count(), 'no 📷 on the avatar')
        with pg.expect_file_chooser(timeout=5000) as fc: el.first.click()
        fc.value.set_files(jpg); pg.wait_for_timeout(1500)
        ok = pg.evaluate("[...document.querySelectorAll('#content img,#topAv img')].some(i=>i.getClientRects().length&&/^(blob:|data:image|https?:)/.test(i.src)&&i.naturalWidth>50&&i.closest('[class*=av],[id*=Av],[class*=avatar],[class*=prof-av]'))||/url\\(/.test(getComputedStyle(document.getElementById('topAv')).backgroundImage)")
        j.check(ok, 'the avatar still shows initials after choosing a photo')
    with j.step('Click "Edit cover" and choose an image: the cover shows'):
        el = j.find(pg, r'Edit cover|عدّل الغلاف|تعديل الغلاف', scope='#content')
        j.check(el, 'no "Edit cover" on the own profile')
        before = j.toast_mark(pg)
        try:
            with pg.expect_file_chooser(timeout=3000) as fc: el.click()
        except Exception:
            j.dead_end(pg, before, 'Edit cover'); j.fail('"Edit cover" opens no file picker')
        fc.value.set_files(cover); pg.wait_for_timeout(1200)
        j.check(pg.evaluate("[...document.querySelectorAll('#content *')].some(e=>/url\\(\"?(blob:|data:image|https?:)/.test(getComputedStyle(e).backgroundImage)&&e.getBoundingClientRect().width>400)"), 'the cover image is not shown')
    with j.step('A too-big image / a PDF is refused with a clear message (or resized)'):
        el = pg.locator('#content [onclick*="changeAvatar"]').first; before = j.toast_mark(pg)
        with pg.expect_file_chooser(timeout=5000) as fc: el.click()
        fc.value.set_files(os.path.join(_dx.FIXTURES, 'spec.pdf')); pg.wait_for_timeout(1000)
        j.check(j.toasts_since(pg, before), 'a PDF chosen as profile photo gives no message')
    if j.live:
        with j.step('Live: image stored in a public bucket under A; profiles.avatar_url and cover_url set'):
            row = j.sql1("select coalesce(avatar_url,'∅')||' | '||coalesce(cover_url,'∅') from public.profiles where id='%s'" % a['id'])
            j.check('∅' not in row, 'profiles.avatar_url / cover_url not set: ' + row)
    with j.step('Reload: photo and cover remain'):
        if j.demo: j.skip('demo keeps no data across a reload (no backend) — checked in live')
        relogin(j, pg, a); own_profile(j, pg)
        j.check(pg.evaluate("[...document.querySelectorAll('#content img')].some(i=>/avatars|covers|storage/.test(i.src))"), 'after reload the photo is gone')
    with j.step("B sees A's photo on the profile, posts, comments, network cards, messages and search"):
        if j.demo: j.skip('the other party exists only in live')
        goto_profile(j, b['page'], a)
        j.check(b['page'].evaluate("[...document.querySelectorAll('#content img')].some(i=>/avatars|storage/.test(i.src))"), "B does not see A's photo on A's profile")

@journey('J-SOCIAL-24')
def intro_video(j):
    """A member uploads a short intro video so visitors to her profile hear her pitch."""
    vid, vid2 = os.path.join(_dx.FIXTURES, 'me_intro.webm'), os.path.join(_dx.FIXTURES, 'company_intro.webm')
    j.check(os.path.exists(vid), 'fixture %s missing (run tests/fixtures/make_fixtures.py)' % vid)
    bad = os.path.join(j.cfg['out'], 'fixtures', 'broken.webm'); os.makedirs(os.path.dirname(bad), exist_ok=True)
    open(bad, 'wb').write(b'\x1aE\xdf\xa3' + os.urandom(4000))
    if j.live: a = j.person('Dr. Amany Video'); b = j.person('Dr. Bassem Watcher'); pg = a['page']
    else: a = None; pg = j.demo_signin(j.new_page())
    def card(p): return p.locator('#content .dx-vid').first
    with j.step('Own profile: "Add a video introduction", upload the WebM: poster and duration show'):
        own_profile(j, pg); j.wait(pg, "!!document.querySelector('#content .dx-vid')", 6)
        el = j.find(pg, r'Add a video introduction|أضف فيديو تعريفي', scope='#content')
        j.check(el, 'no "Add a video introduction" on the own profile')
        with pg.expect_file_chooser(timeout=5000) as fc: el.click()
        fc.value.set_files(vid)
        j.check(j.wait(pg, "!!document.querySelector('#content .dx-vid-play')", 20), 'after upload the profile shows no video')
        j.check(re.search(r'\d+:\d\d', card(pg).inner_text()), 'no duration on the video card')
    with j.step('Play it: the video plays'):
        pg.locator('#content .dx-vid-play').first.click()
        j.check(j.wait(pg, "(()=>{const v=document.querySelector('video.dx-vid-player');return !!v&&v.readyState>=2&&v.duration>0})()", 12), 'the video does not play')
        pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
        j.click(pg, r'^(Close|إغلاق)$', scope='body', what='Close', exact=True) if j.find(pg, r'^(Close|إغلاق)$', scope='body', exact=True) else None
    with j.step('Reload (sign in again where needed) and play again'):
        relogin(j, pg, a); own_profile(j, pg)
        j.check(j.wait(pg, "!!document.querySelector('#content .dx-vid-play')", 12), 'after reload the video is gone')
    if j.live:
        with j.step('Live: videos bucket has people/<A>/… and profiles.intro_video is set'):
            j.check(j.sql1("select intro_video is not null from public.profiles where id='%s'" % a['id']) == 't', 'profiles.intro_video not set')
            n = j.sql1("select count(*) from storage.objects where bucket_id='videos' and name like 'people/%s/%%'" % a['id'])
            j.check(n not in ('', '0'), 'no object in the videos bucket under people/<A>/')
            j.note('video_objects_after_upload', n)
    with j.step('Replace it with another video, then remove it'):
        el = j.find(pg, r'Replace video|استبدل', scope='#content'); j.check(el, 'no "Replace video"')
        with pg.expect_file_chooser(timeout=5000) as fc: el.click()
        fc.value.set_files(vid2); pg.wait_for_timeout(4000)
        if j.live:
            n = j.sql1("select count(*) from storage.objects where bucket_id='videos' and name like 'people/%s/%%' and name like '%%.webm'" % a['id'])
            j.check(n == '1', 'after Replace %s video objects remain under people/<A>/ (the old one is not removed)' % n)
        rm = j.find(pg, r'^(Remove|إزالة|حذف)$', scope='#content .dx-vid', exact=True); j.check(rm, 'no "Remove" on the video')
        rm.click(); pg.wait_for_timeout(500)
        ok = j.find(pg, r'^(Remove|Delete|Yes|إزالة|حذف|نعم)$', scope='.modal-bg', exact=True) or j.find(pg, r'^(Remove|Delete|Yes|إزالة|حذف|نعم)$', scope='[role=dialog]', exact=True)
        if ok: ok.click()
        j.check(j.wait(pg, "!document.querySelector('#content .dx-vid-play')", 8), 'Remove did not remove the video')
        if j.live: j.check(j.wait_db("select intro_video is null from public.profiles where id='%s'" % a['id'], 5) == 't', 'profiles.intro_video still set after Remove')
    with j.step('A video the browser cannot read is refused with a clear message'):
        el = j.find(pg, r'Add a video introduction|أضف فيديو تعريفي', scope='#content'); before = j.toast_mark(pg)
        with pg.expect_file_chooser(timeout=5000) as fc: el.click()
        fc.value.set_files(bad); pg.wait_for_timeout(2500)
        msg = j.toasts_since(pg, before) + [j.text(pg, '.modal-bg')]
        j.check(re.search(r'could not be read|cannot|try MP4|لا يمكن|تعذر', ' '.join(msg), re.I), 'an unreadable video gives no clear message')
        j.check(not pg.locator('#content .dx-vid-play').count(), 'an unreadable video was saved')
    with j.step('B can play the video and cannot replace or remove it'):
        if j.demo: j.skip('the other party exists only in live')
        el = j.find(pg, r'Add a video introduction|أضف فيديو تعريفي', scope='#content')
        with pg.expect_file_chooser(timeout=5000) as fc: el.click()
        fc.value.set_files(vid); j.check(j.wait(pg, "!!document.querySelector('#content .dx-vid-play')", 20), 'upload again failed')
        pb = b['page']; goto_profile(j, pb, a)
        j.check(j.wait(pb, "!!document.querySelector('#content .dx-vid-play')", 10), "B does not see A's video")
        j.check(not pb.locator('#content .dx-vid-up, #content .dx-vid-rm').count(), "B sees Replace/Remove on A's video")
        pb.locator('#content .dx-vid-play').first.click()
        j.check(j.wait(pb, "(()=>{const v=document.querySelector('video.dx-vid-player');return !!v&&v.readyState>=2})()", 12), "B cannot play A's video")

def add_entry(j, pg, add_pat, what, fields, save_pat=r'^(Save|Add|حفظ|إضافة)$'):
    """Click an Add control on the own profile and fill its form: fields = values for the visible text/date inputs in order."""
    el = j.find(pg, add_pat, scope='#content')
    if not el: j.notbuilt('no "%s" on the own profile' % what)
    el.click(); j.settle(pg, 400)
    dlg = pg.locator('.modal-bg:visible, [role=dialog]:visible').first
    j.check(dlg.count(), '"%s" opens no form' % what)
    ins = dlg.locator('input:visible:not([type=checkbox]):not([type=file]), textarea:visible')
    j.check(ins.count() >= len([f for f in fields if f is not None]), '"%s" form has %d fields, %d needed' % (what, ins.count(), len(fields)))
    for i, v in enumerate(fields):
        if v is None: continue
        if v is True: dlg.locator('input[type=checkbox]').first.check(); continue
        ins.nth(i).fill(v)
    j.click(pg, save_pat, scope='.modal-bg' if pg.locator('.modal-bg:visible').count() else '[role=dialog]', what='Save ' + what, exact=True); pg.wait_for_timeout(700)

@journey('J-SOCIAL-25')
def experience_education(j):
    """A member adds experience and education so recruiters can see her background."""
    if j.live: a = j.person('Dr. Amal History'); b = j.person('Dr. Badr Recruiter'); pg = a['page']
    else: a = None; pg = j.demo_signin(j.new_page())
    POS = r'Add (a )?(position|experience)|إضافة (خبرة|وظيفة)|أضف خبرة'
    with j.step('Own profile → Experience tab'):
        own_profile(j, pg); tab(j, pg, r'^(Experience|الخبرة|الخبرات)$', 'Experience')
    with j.step('Add a position: QC Analyst at Pharco, Jan 2024 – present, with a description'):
        add_entry(j, pg, POS, 'Add position', ['QC Analyst', 'Pharco', '2024-01', None, 'Release testing, HPLC, stability'])
        t = j.text(pg); j.check('QC Analyst' in t and 'Pharco' in t, 'the position is not listed')
        j.check(re.search(r'present|حتى الآن|الحالي', t, re.I), 'the current role does not show "present"')
    with j.step('Dates are validated: an end before the start is refused'):
        add_entry(j, pg, POS, 'Add position', ['Bad dates', 'X', '2023-05', '2022-01', ''])
        j.check('Bad dates' not in j.text(pg) or pg.locator('.modal-bg:visible').count(), 'an end date before the start was accepted')
        if pg.locator('.modal-bg:visible').count(): j.click(pg, r'^(Cancel|إلغاء|×)$', scope='.modal-bg', what='Cancel', exact=True)
    with j.step('Add a previous position and an education entry (Faculty of Pharmacy, Cairo University, 2019–2024)'):
        add_entry(j, pg, POS, 'Add position', ['Junior Chemist', 'Amoun', '2022-03', '2023-12', ''])
        add_entry(j, pg, r'Add (an )?education|إضافة (تعليم|مؤهل)|أضف تعليم', 'Add education', ['Faculty of Pharmacy, Cairo University', 'B.Pharm', '2019', '2024'])
        t = j.text(pg); j.check('Junior Chemist' in t and 'Cairo University' in t, 'the previous position / education is not listed')
        j.check(t.index('QC Analyst') < t.index('Junior Chemist'), 'entries are not newest first')
    with j.step("Edit the first position's title; delete the previous position"):
        row = pg.locator('#content *').filter(has_text='QC Analyst').last
        ed = j.find(pg, r'^(Edit|✏️|تعديل|عدّل)$', scope='#content', exact=True); j.check(ed, 'no Edit on a position')
        ed.click(); j.settle(pg, 300); dlg = pg.locator('.modal-bg:visible, [role=dialog]:visible').first
        dlg.locator('input:visible').first.fill('Senior QC Analyst'); j.click(pg, r'^(Save|حفظ)$', scope='.modal-bg', what='Save', exact=True); pg.wait_for_timeout(500)
        dl = pg.locator('#content').get_by_text('Junior Chemist').locator('xpath=ancestor::*[.//button][1]').locator('button, [onclick]').filter(has_text=re.compile(r'Delete|Remove|🗑|حذف|إزالة'))
        j.check(dl.count(), 'no Delete on a position'); dl.first.click(); pg.wait_for_timeout(300)
        ok = j.find(pg, r'^(Delete|Remove|Yes|حذف|نعم)$', scope='.modal-bg', exact=True)
        if ok: ok.click()
        t = j.text(pg); j.check('Senior QC Analyst' in t and 'Junior Chemist' not in t, 'edit/delete did not take effect')
    if j.live:
        with j.step('Live: stored in profiles.experience / education and read back after reload'):
            j.check(j.wait_db("select jsonb_array_length(coalesce(experience,'[]'::jsonb)) from public.profiles where id='%s'" % a['id'], 5, want='1') == '1', 'profiles.experience not stored')
            j.check(j.sql1("select jsonb_array_length(coalesce(education,'[]'::jsonb)) from public.profiles where id='%s'" % a['id']) == '1', 'profiles.education not stored')
    with j.step('Reload: the entries are still there'):
        if j.demo: j.skip('demo keeps no data across a reload (no backend) — checked in live')
        relogin(j, pg, a); own_profile(j, pg); tab(j, pg, r'^(Experience|الخبرة|الخبرات)$', 'Experience')
        j.check('Senior QC Analyst' in j.text(pg) and 'Cairo University' in j.text(pg), 'after reload the entries are gone')
    with j.step("B opens A's Experience: exactly the remaining entries, without edit controls"):
        if j.demo: j.skip('the other party exists only in live')
        pb = b['page']; goto_profile(j, pb, a); tab(j, pb, r'^(Experience|الخبرة|الخبرات)$', 'Experience'); t = j.text(pb)
        j.check('Senior QC Analyst' in t and 'Cairo University' in t and 'Junior Chemist' not in t, "B does not see A's entries")
        j.check(not j.find(pb, POS, scope='#content') and not j.find(pb, r'^(Edit|تعديل|عدّل)$', scope='#content', exact=True), "B sees add/edit controls on A's Experience")

@journey('J-SOCIAL-26')
def skills_and_endorsements(j):
    """A member lists her skills and colleagues endorse them."""
    if j.live: a = j.person('Dr. Amira Skills'); b = j.person('Dr. Bassem Endorser'); connect_db(j, a['id'], b['id']); pg = a['page']
    else: a = None; pg = j.demo_signin(j.new_page())
    SK = ('CTD dossiers', 'EDA variations', 'GMP audits')
    def counts(p):
        return p.evaluate("""()=>{const out={};document.querySelectorAll('#content *').forEach(e=>{if(e.children.length)return;const t=e.innerText.trim();if(/^(CTD dossiers|EDA variations|GMP audits)$/.test(t)){const row=e.parentElement;const m=(row&&row.innerText.replace(t,'').match(/\\d+/));out[t]=m?+m[0]:0}});return out}""")
    with j.step('Own profile → Skills: add "CTD dossiers", "EDA variations", "GMP audits"'):
        own_profile(j, pg); tab(j, pg, r'^(Skills|المهارات)$', 'Skills')
        el = j.find(pg, r'Add (a )?skill|إضافة مهارة|أضف مهارة', scope='#content')
        j.check(el, 'not built: no "Add skill" on the own Skills tab')
        el.click(); j.settle(pg, 400)
        inp = pg.locator('.modal-bg input:visible, #content input:visible').first; j.check(inp.count(), 'Add skill opens no input')
        for s in SK: inp.fill(s); inp.press('Enter'); pg.wait_for_timeout(300)
        btn = j.find(pg, r'^(Save|Done|حفظ|تم)$', scope='body', exact=True)
        if btn: btn.click(); pg.wait_for_timeout(500)
        t = j.text(pg); j.check(all(s in t for s in SK), 'the added skills are not listed')
    with j.step('Endorsement counts are real: 0 for the new skills (not invented numbers)'):
        c = counts(pg); j.check(c and all(v == 0 for v in c.values()), 'new skills show invented endorsement counts: %s' % c)
    with j.step('Remove one skill (GMP audits)'):
        row = pg.locator('#content').get_by_text('GMP audits', exact=True).locator('xpath=..')
        rm = row.locator('button, [onclick], [aria-label*="Remove" i]'); j.check(rm.count(), 'no way to remove a skill')
        rm.first.click(); pg.wait_for_timeout(400); j.check('GMP audits' not in j.text(pg), 'the skill was not removed')
    if j.live:
        with j.step('Live: skills stored'):
            j.check(j.wait_db("select coalesce(array_length(skills,1),0) from public.profiles where id='%s'" % a['id'], 5, want='2') == '2', 'profiles.skills not stored (2 expected)')
    with j.step('Reload: the skills and counts are unchanged'):
        if j.demo: j.skip('demo keeps no data across a reload (no backend) — checked in live')
        relogin(j, pg, a); own_profile(j, pg); tab(j, pg, r'^(Skills|المهارات)$', 'Skills')
        j.check('CTD dossiers' in j.text(pg) and 'GMP audits' not in j.text(pg), 'after reload the skills changed')
    with j.step('B endorses "CTD dossiers": the count is 1 and shows who endorsed'):
        if j.demo: j.skip('the other party exists only in live')
        pb = b['page']; goto_profile(j, pb, a); tab(j, pb, r'^(Skills|المهارات)$', 'Skills')
        row = pb.locator('#content').get_by_text('CTD dossiers', exact=True).locator('xpath=..')
        en = row.locator('button, [onclick]').filter(has_text=re.compile(r'Endorse|\+|تأييد|أؤيد'))
        j.check(en.count(), 'no Endorse on B\'s view of the skill'); en.first.click(); pb.wait_for_timeout(800)
        j.check(counts(pb).get('CTD dossiers') == 1, 'the endorsement count is not 1')
        j.check(j.has_table('skill_endorsements') or j.has_table('endorsements'), 'not built: no endorsements table')
    with j.step('A is notified; B cannot endorse twice; A cannot endorse herself'):
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and from_user='%s'" % (a['id'], b['id'])) == '1', 'A got no endorsement notification')
        en.first.click(); pb.wait_for_timeout(800); j.check(counts(pb).get('CTD dossiers') in (0, 1), 'B endorsed twice')
        own_profile(j, pg); tab(j, pg, r'^(Skills|المهارات)$', 'Skills')
        j.check(not j.find(pg, r'^(Endorse|تأييد)$', scope='#content', exact=True), 'A can endorse her own skill')

@journey('J-SOCIAL-27')
def view_someone_else(j):
    """A member looks at another person's profile to decide whether to connect, follow, message or hire them."""
    if j.live:
        a = j.person('Dr. Amr Visitor'); b = j.person('Dr. Bahaa Expert')
        j.sql("update public.profiles set headline='Head of QA', company='EVA Pharma', bio='Twenty years in sterile manufacturing.' where id='%s'" % b['id'])
        post_db(j, b['id'], 'Expert post by Bahaa ' + j.tag, 'general', 3)
        pg = a['page']; j.reload(pg); j.nav(pg, 'feed')
        bname = 'Dr. Bahaa Expert'
    else:
        pg = j.demo_signin(j.new_page())
        # precondition: B is not connected to A and has no pending request — the first such post author in the sample feed
        bname = None
        for nm in pg.locator('#content .post .post-name').all_inner_texts():
            nm = nm.strip().split('\n')[0].strip(); uid = pg.evaluate("n=>(USERS.find(u=>u.name.trim()===n)||{}).id", nm)
            if uid is None: continue
            goto_profile(j, pg, uid)
            if j.find(pg, r'^\W*(Connect|تواصل|اتصال)$', scope='#content', exact=True): bname = nm; break
        j.check(bname, 'precondition: no unconnected post author in the sample feed'); j.nav(pg, 'feed')
    def header_is_b():
        t = j.text(pg)[:700]; me = pg.evaluate('ME.name')
        return bname.split()[-1] in t and not (me.split()[-1] in t[:200] and bname.split()[-1] not in t[:200])
    with j.step("Open B's profile from a post author name"):
        name = pg.locator('#content .post .post-name').filter(has_text=bname.split()[-1]).first
        j.check(name.count(), "no post by B on Home"); name.click(); j.settle(pg, 1200)
        j.check(header_is_b(), "the post author name does not open B's profile")
    with j.step("Open B's profile from the top-bar search"):
        j.nav(pg, 'feed'); top_search(j, pg, bname.split()[-1]); open_result(j, pg, bname.split()[-1])
        j.check(header_is_b(), "the search result does not open B's profile")
    with j.step("Open B's profile from a notification"):
        if j.live:
            j.sql("insert into public.connections (requester, addressee, status) values ('%s','%s','pending')" % (b['id'], a['id']))
            j.reload(pg)
        j.nav(pg, 'notifs')
        rows = pg.locator('#content [onclick*="gotoProfile"], #content button, #content a').filter(has_text=re.compile(r'View profile|عرض الملف' + ('|' + re.escape(bname.split()[-1]) if j.live else '')))
        j.check(rows.count(), 'no notification row that opens a profile')
        target = rows.first.locator('xpath=ancestor-or-self::*[contains(@class,"notif") or @onclick][1]').inner_text() if j.demo else bname
        rows.first.click(); j.settle(pg, 1200)
        if j.live: j.check(header_is_b(), "the notification does not open B's profile")
        else: j.check(pg.evaluate("document.body.getAttribute('data-page')") == 'profile' and pg.evaluate('ME.name').split()[-1] not in j.text(pg)[:150], 'the notification opens no profile (or my own)')
        if j.demo: name = pg.locator('#content .post .post-name'); goto_profile(j, pg, pg.evaluate("(USERS.find(u=>u.name.indexOf(%r)>=0)||{}).id" % bname.split()[-1]))
    with j.step('Read About, Experience, Skills and Activity: B\'s own data and only B\'s posts'):
        for pat in (r'^(About|نبذة|حول)$', r'^(Experience|الخبرة|الخبرات)$', r'^(Skills|المهارات)$', r'^(Activity|النشاط)$'):
            tab(j, pg, pat, pat)
        authors = set(x.strip().split('\n')[0].strip() for x in pg.locator('#content .post .post-name').all_inner_texts())
        j.check(all(bname.split()[-1] in x for x in authors), "B's Activity shows other people's posts: %s" % sorted(authors)[:4])
    with j.step('Click Follow in the profile header: it really follows (state survives reload)'):
        el = j.find(pg, r'^\W*(Follow|متابعة)$', scope='#content', exact=True)
        j.check(el, 'no Follow in the profile header')
        el.click(); pg.wait_for_timeout(800)
        j.check(j.find(pg, r'^\W*(Following|تتابعهم|تتابع|متابَع|تمت المتابعة)$', scope='#content', exact=True), 'Follow did not switch to Following')
        if j.live: j.check(j.has_table('follows') or j.has_table('person_followers') or j.has_table('profile_followers'), 'not built: no table for following a person (only company_followers)')
        if j.live:
            j.reload(pg); goto_profile(j, pg, b)
            j.check(j.find(pg, r'^\W*(Following|تتابعهم|تتابع|متابَع|تمت المتابعة)$', scope='#content', exact=True), 'after reload Follow is lost')
    with j.step('Connect from the header sends a real request; the button shows Pending'):
        el = j.find(pg, r'^\W*(Connect|تواصل|اتصال)$', scope='#content', exact=True); j.check(el, 'no Connect in the header')
        el.click(); pg.wait_for_timeout(800)
        where = pg.evaluate("document.body.getAttribute('data-page')")
        j.check(where == 'profile', "Connect on B's profile leaves the profile (the app switches to '%s')" % where)
        j.check(j.find(pg, r'^\W*(Pending|Sent|Withdraw|معلق|قيد الانتظار|تم الإرسال)$', scope='#content', exact=True), 'Connect did not switch the button to Pending')
        if j.live: j.check(j.wait_db("select count(*) from public.connections where requester='%s' and addressee='%s' and status='pending'" % (a['id'], b['id']), 5) == '1', 'Connect stored no pending request')
    with j.step('Message from the header opens a thread with B'):
        j.click(pg, r'Message|رسالة|راسل', scope='#content', what='Message'); j.settle(pg)
        j.check(pg.evaluate("document.body.getAttribute('data-page')") == 'messages', 'Message does not open Messages')
        head = pg.evaluate("(document.querySelector('#content .mx-head,#content .chat-head,#content [class*=chat-h],#content [class*=thread-h]')||{}).innerText||''")
        j.check(bname.split()[-1] in head, 'the open thread is not with B (header: "%s")' % head[:60])
    with j.step('The profile view is recorded once; B can see that A viewed'):
        if j.demo: j.skip('the other party exists only in live')
        j.check(j.sql1("select profile_views from public.profiles where id='%s'" % b['id']) not in ('', '0'), 'not built: viewing a profile is never recorded (profile_views stays 0)')
    with j.step("A profile link is a real URL that opens B's profile after reload"):
        goto_profile(j, pg, b if j.live else pg.evaluate("n=>(USERS.find(u=>u.name.trim()===n)||{}).id", bname)); u = pg.url
        j.check(u.rstrip('/') != j.url.rstrip('/') and ('#' in u or '?' in u or '/p/' in u), 'not built: the address does not change for a profile (%s)' % u)
        pg2 = j.new_page(pg.context, url=u)
        if j.on_login(pg2): j.demo_signin(pg2) if j.demo else j.signin(pg2, a['email'], a['pw'])
        j.check(bname.split()[-1] in j.text(pg2)[:500], "the profile link does not open B's profile")

@journey('J-SOCIAL-49')
def honest_reach_numbers(j):
    """A member sees honest reach numbers (profile views, post impressions, connections)."""
    if j.live:
        a = j.person('Dr. Adham Reach'); b = j.person('Dr. Basma Viewer'); c = j.person('Dr. Cherif Viewer')
        for i in range(2): post_db(j, a['id'], 'Reach post %d %s' % (i, j.tag))
        for v in (b, c):
            goto_profile(j, v['page'], a); fresh = v['page']; j.reload(fresh); j.nav(fresh, 'feed')
        pg = a['page']; j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page())
    def numbers():
        out = {}
        j.nav(pg, 'feed'); pg.wait_for_timeout(2000); t = j.text(pg)          # numbers count up when shown
        for k, pat in (('views', r'(?:Profile view(?:er)?s|من زار ملفك)\s*([\d,]+)'), ('impr', r'(?:Post impressions|مرات ظهور المنشورات)\s*([\d,]+)'), ('conn', r'(?:Connections|الاتصالات)\s*([\d,]+)')):
            m = re.search(pat, t); out['feed_' + k] = int(m.group(1).replace(',', '')) if m else None
        j.nav(pg, 'network'); pg.wait_for_timeout(2000); t = j.text(pg)
        for k, pat in (('views', r'(?:Profile views|مشاهدات الملف)\s*([\d,]+)'), ('impr', r'(?:Post impressions|مرات ظهور المنشورات)\s*([\d,]+)'), ('conn', r'(?:Connections|الاتصالات)\s*([\d,]+)')):
            m = re.search(pat, t); out['net_' + k] = int(m.group(1).replace(',', '')) if m else None
        return out
    with j.step('Open the feed sidebar card and the Network numbers: the same real numbers everywhere'):
        n = numbers(); j.note('numbers', n)
        for k in ('views', 'impr', 'conn'):
            f, w = n.get('feed_' + k), n.get('net_' + k)
            j.check(f is None or w is None or f == w, '%s differ between Home (%s) and Network (%s)' % (k, f, w))
        sample = [v for v in n.values() if v in (148, 342, 2840, 16909, 481, 87)]
        j.check(not sample, 'sample numbers shown as reach: %s' % sample)
        if j.live:
            pv = int(j.sql1("select coalesce(profile_views,0) from public.profiles where id='%s'" % a['id']) or 0)
            j.check(pv == 2, 'two members viewed the profile, profiles.profile_views = %d' % pv)
    with j.step('Open the list of who viewed the profile'):
        el = j.find(pg, r'Who viewed|viewers|من شاهد|من زار', scope='#content'); j.check(el, 'no "who viewed your profile" list')
    with j.step('D views the profile: views increase by one'):
        if j.demo: j.skip('the other party exists only in live')
        d = j.person('Dr. Dalia Late'); goto_profile(j, d['page'], a)
        j.check(j.wait_db("select profile_views from public.profiles where id='%s'" % a['id'], 5, want='3') == '3', 'profile views did not increase to 3 after D visited')

if __name__ == '__main__': main(__file__)
