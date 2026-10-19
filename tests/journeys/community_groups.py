"""Community journeys — groups as a member: find groups, open one, read and write its discussion, comment, like, members,
about, join/leave, private groups, invitations, creating a group (J-COMMUNITY-01 … 12).
Run: python3 tests/journeys/community_groups.py --target demo|live --lang en|ar --width 1440|390"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _community import *
import _dx

DISCUSS, DEAL = R('DISCUSS', 'Discussion', extra='DISCUSSION|نقاش'), R('DEAL ROOM', extra='صفقات|غرفة')
PUBLIC, PRIVATE = R('Public', extra='عامة|عام'), R('Private', extra='خاصة|خاص')
JOIN = r'^\W*(\+ ?Join|Join|Join Group|انضم|انضمام)\W*$'
JOINED = r'Joined|Leave|منضم|انضممت|غادر|مغادرة'

def world(j, me_id, n_extra=0):
    """Live: the groups another journey created: X is their admin; the user is a member of two of them."""
    t = j.tag[:4]
    x = seed_user(j, 'Dr. Xena Admin', 'Head of Regulatory Affairs', 'Pharco')
    g = {}
    g['stab'] = seed_group(j, 'Stability Testing Egypt %s' % t, x, desc='Zone IVb STABILITY studies, shelf life and EDA questions', emoji='🧪', rules='Cite the guideline')
    g['api'] = seed_group(j, 'API Sourcing Room %s' % t, x, deal=True, desc='Buyers and suppliers of APIs and excipients', emoji='⚗️')
    g['cos'] = seed_group(j, 'Cosmetics Formulators Club %s' % t, x, desc='Cosmetics and skin-care formulation', emoji='💄')
    g['pv'] = seed_group(j, 'Pharmacovigilance Circle %s' % t, x, private=True, desc='Private PV group', emoji='🛡️')
    g['qa'] = seed_group(j, 'QA Leaders %s' % t, x, desc='GMP audits and CAPA', emoji='✅')
    g['pack'] = seed_group(j, 'Packaging Deal Room %s' % t, x, deal=True, desc='Blisters and cartons', emoji='📦')
    g['reg'] = seed_group(j, 'Regulatory Affairs Cairo %s' % t, x, desc='Registration and variations', emoji='📋')
    g['sfda'] = seed_group(j, 'SFDA Filers %s' % t, x, desc='مجموعة لتسجيل الأدوية في السعودية', emoji='🌍')
    for k in ('stab', 'api'): add_member(j, g[k], me_id)
    seed_gpost(j, x, g['stab'], 'Today: new EDA stability circular %s' % t, 600)
    seed_gpost(j, x, g['api'], 'Last week offer %s' % t, 8 * 86400)
    names = {k: j.sql1('select name from public.groups where id=%d' % v) for k, v in g.items()}
    return x, g, names

@journey('J-COMMUNITY-01')
def find_groups(j):
    """A professional finds the communities that matter to her (by topic, type, sector and country) so she can join the right ones."""
    if j.live:
        me = j.person('Mona Fathy'); pg = me['page']
        x, g, names = world(j, me['id']); j.reload(pg)
        mine = sorted([names['stab'], names['api']]); search_hit = names['stab']; cos = names['cos']
    else:
        pg = j.demo_signin(j.new_page()); mine = None; search_hit = 'Regulatory Affairs Egypt'; cos = 'Cosmetics Formulators'
    with j.step('Open Groups from the navigation'):
        groups_page(j, pg); ui_ok(j, pg, 'Groups')
    with j.step('The Your Groups side list and the hero numbers come from my real groups'):
        side = sorted(sidebar(pg))
        joined = sorted(c['title'] for c in cards(pg) if re.search(JOINED, c['btn']))
        if j.live:
            j.check(side == mine, 'the Your Groups side list shows %s — my groups are %s' % (side, mine))
        else:
            j.check(side == joined, 'the Your Groups side list (%s) is not the groups I joined (%s)' % (side, joined))
        hero = pg.evaluate("(document.querySelector('#content .gx-hero, #content [class*=hero]')||{}).innerText||''")
        m = re.search(r'(\d+)\s*\n?\s*(of your groups|من مجموعاتك)', hero)
        if m: j.check(int(m.group(1)) <= len(side), 'the hero says %s of your groups have new posts today, but I am in %d' % (m.group(1), len(side)))
        if j.live:
            j.check(not m or int(m.group(1)) == 1, 'the hero says %s of my groups have new posts today (1 has: %s)' % (m.group(1) if m else '?', names['stab']))
            u = re.search(r'(\d+)\s*\n?\s*(unread|غير مقروء)', hero)
            j.check(not u or int(u.group(1)) <= 1, 'the hero says %s unread across my groups — my groups have 1 post today' % (u.group(1) if u else ''))
            tr = re.search(r'\n([^\n]+)\n[^\n]*(trending|رائج)', hero)
            j.check(not tr or tr.group(1).strip() in names.values() or not re.search(r'API Sourcing & Supply', hero), 'the hero shows the sample group "%s" as trending' % (tr.group(1).strip() if tr else ''))
    with j.step('My Groups (N): the chip count, the cards shown and my real memberships agree'):
        chip(j, pg, R('My Groups'), 'My Groups')
        n = num(chip_text(pg, R('My Groups'))); shown = cards(pg)
        j.check(n is not None, 'the My Groups chip shows no count')
        j.check(len(shown) == n, 'My Groups (%d) shows %d cards: %s' % (n, len(shown), ', '.join(c['title'] for c in shown)[:160]))
        j.check(all(re.search(JOINED, c['btn']) for c in shown), 'My Groups shows groups I am not in: %s' % ', '.join(c['title'] for c in shown if not re.search(JOINED, c['btn'])))
        if j.live: j.check(sorted(c['title'] for c in shown) == mine, 'My Groups shows %s — my groups are %s' % ([c['title'] for c in shown], mine))
    with j.step('Discussion and Deal Rooms show only groups of that type'):
        chip(j, pg, r'^\W*(Discussion|نقاش|النقاش|نقاشات)\W*$', 'Discussion')
        shown = cards(pg); j.check(shown, 'Discussion shows no group')
        wrong = [c['title'] for c in shown if re.search(DEAL, c['meta'])]
        j.check(not wrong, 'Discussion shows deal rooms: %s' % ', '.join(wrong))
        chip(j, pg, r'^\W*(Deal Rooms|غرف الصفقات|غرف صفقات)\W*$', 'Deal Rooms')
        shown = cards(pg); j.check(shown, 'Deal Rooms shows no group')
        wrong = [c['title'] for c in shown if not re.search(DEAL, c['meta'])]
        j.check(not wrong, 'Deal Rooms shows discussion groups: %s' % ', '.join(wrong))
    with j.step('Pharma and Cosmetics show only groups of that sector'):
        chip(j, pg, r'Cosmetics|تجميل', 'Cosmetics')
        shown = card_titles(pg)
        j.check(cos in shown, 'Cosmetics does not show the cosmetics group "%s" (shows %s)' % (cos, shown[:6]))
        wrong = [t for t in shown if not re.search(r'cosmet|beauty|skin|تجميل', t + ' ' + ' '.join(c['text'] for c in cards(pg) if c['title'] == t), re.I)]
        j.check(not wrong, 'Cosmetics shows groups that are not about cosmetics: %s' % ', '.join(wrong[:5]))
        chip(j, pg, r'^\W*(Pharma|دواء|أدوية|فارما)\W*$', 'Pharma')
        j.check(cos not in card_titles(pg), 'Pharma shows the cosmetics group "%s"' % cos)
    with j.step('By Country opens a country choice; Egypt, then UAE list only groups tagged with that country'):
        chip(j, pg, r'By Country|حسب الدولة|بالدولة', 'By Country')
        opts = pg.evaluate("""()=>{const vis=e=>e.getClientRects().length>0&&getComputedStyle(e).visibility!='hidden';
            return [...document.querySelectorAll('#content select option, .dbk-ov *, .modal-bg.show *, [role=listbox] *, [role=menu] *, #content .cf-tag')].filter(e=>(e.tagName=='OPTION'||vis(e))&&/^\\W*(Egypt|UAE|United Arab Emirates|مصر|الإمارات)\\W*$/.test((e.innerText||e.textContent||'').trim())).map(e=>e.textContent.trim())}""")
        j.check(opts, 'not built: By Country opens no country choice (no Egypt / UAE to pick)')
        for code, word in (('EG', r'Egypt|مصر'), ('AE', r'UAE|الإمارات')):
            if code == 'AE': chip(j, pg, r'By Country|حسب الدولة|بالدولة|Egypt|مصر', 'By Country')
            pick = pg.locator('.dbk-ov button').filter(has_text=re.compile(r'^\W*(%s)\W*\d*\s*$' % word))
            j.check(pick.count(), 'no %s in the country choice' % code); pick.first.click(); j.settle(pg, 700)
            got = pg.evaluate("[...document.querySelectorAll('#content .gcard')].filter(e=>e.getClientRects().length&&getComputedStyle(e).display!='none').map(e=>e.dataset.country||'')")
            j.check(all(code in c.split(',') for c in got), '%s lists groups not tagged with that country (%s)' % (code, got[:6]))
            if not got: j.check(re.search(r'No groups|لا توجد', j.text(pg)) and j.find(pg, r'Create Group|أنشئ مجموعة', scope='#content'), 'an empty country shows no "no groups" state with Create Group')
        chip(j, pg, r'^\W*(All Groups|كل المجموعات)\W*$', 'All Groups')
    with j.step('Search groups for "stability": found by its description (any case); a nonsense word shows "no results"'):
        box = pg.locator('#content input[type=search]:visible, #content input[placeholder*="earch" i]:visible, #content input[placeholder*="بحث"]:visible')
        if box.count():
            box.first.fill('stability'); box.first.press('Enter'); j.settle(pg, 1000)
            j.check(search_hit in card_titles(pg), 'searching "stability" does not find "%s"' % search_hit)
            box.first.fill('zzqxv'); box.first.press('Enter'); j.settle(pg, 800)
            j.check(not cards(pg) and re.search(r'No (groups|results)|لا توجد|لا نتائج', j.text(pg)), 'a search with no match shows no "no results" state')
            box.first.fill(''); box.first.press('Enter'); j.settle(pg, 800)
            j.check(cards(pg), 'clearing the search does not bring the groups back')
        else:
            pg.locator('#searchIn').fill('stability'); pg.locator('#searchIn').press('Enter'); j.settle(pg, 1200)
            t = j.text(pg)
            j.check(search_hit in t, 'not built: no groups search, and the top search for "stability" does not find the group "%s"' % search_hit)
            groups_page(j, pg)
    with j.step('Every "View all" opens the full list of its section'):
        alls = pg.locator('#content .sec-all:visible, #content a:visible:text-matches("View all|عرض الكل")')
        n = alls.count(); j.check(n, 'not built: no "View all" on the Groups page')
        for i in range(n):
            groups_page(j, pg); el = pg.locator('#content .sec-all:visible').nth(i)
            before = len(cards(pg)); txt0 = j.text(pg)
            j.act(pg, el, 'View all #%d' % (i + 1), lambda: dlg_open(pg) or len(cards(pg)) != before or j.text(pg) != txt0, expect='the full list of the section')
    with j.step('Reload: the same groups and the same My Groups count'):
        reopen(j, pg); groups_page(j, pg)
        chip(j, pg, R('My Groups'), 'My Groups')
        if j.live: j.check(sorted(card_titles(pg)) == mine, 'after reload My Groups shows %s' % card_titles(pg))

def check_header(j, pg, c):
    """The open group's header agrees with its card: name, type, privacy, members, membership button."""
    h = gd_header(pg); title = gd_title(pg)
    j.check(title == c['title'], 'the card "%s" opens the group "%s"' % (c['title'], title))
    j.check(bool(re.search(DEAL, c['meta'])) == bool(re.search(DEAL, h)), '"%s": the card says %s but the header says otherwise' % (c['title'], c['meta']))
    j.check(bool(re.search(PRIVATE, c['meta'])) == bool(re.search(PRIVATE, h)), '"%s": the card says %s but the header says %s' % (c['title'], c['meta'], 'Private' if re.search(PRIVATE, h) else 'Public'))
    cn = [n for n in nums(c['text']) if n >= 1]; hn = gd_members_n(pg)
    mc = re.search(r'([\d,٠-٩]+)\s*(members|عضو|أعضاء)', c['text'])
    if mc: j.check(hn == num(mc.group(1)), '"%s": the card says %s members, the header %s' % (c['title'], mc.group(1), hn))
    btns = ' | '.join(gd_buttons(pg)); cb = c['btn']
    if re.search(r'Join|انضم', cb) and not re.search(JOINED, cb): j.check(re.search(r'Join|انضم', btns) and not re.search(r'Leave|غادر|مغادرة', btns), '"%s" (not a member): the header shows %s' % (c['title'], btns))
    if re.search(r'Request|طلب', cb): j.check(re.search(r'Request|طلب', btns) and not re.search(r'Leave|غادر|مغادرة', btns), '"%s" (private, not a member): the header shows %s' % (c['title'], btns))
    if re.search(JOINED, cb): j.check(re.search(r'Leave|Manage|غادر|مغادرة|إدارة', btns), '"%s" (member): the header has no Leave/Manage (%s)' % (c['title'], btns))
    return h

def check_tabs(j, pg, deal):
    tabs = gd_tabs(pg)
    want = ['disc', 'members', 'about'] + (['listings'] if deal else [])
    for k in want:
        if k == 'listings' and not any(t.startswith('list') for t in tabs): j.notbuilt('the deal room "%s" has no Listings tab (tabs: %s)' % (gd_title(pg), tabs))
        key = k if k in tabs else next((t for t in tabs if t.startswith(k[:4])), None)
        if not key: j.notbuilt('the group "%s" has no %s tab (tabs: %s)' % (gd_title(pg), k, tabs))
        txt = gd_tab(j, pg, key)
        j.check(len(txt.strip()) > 10, 'the %s tab of "%s" is empty (no content, no empty state)' % (key, gd_title(pg)))
    gd_tab(j, pg, 'disc')

@journey('J-COMMUNITY-02')
def open_any_group(j):
    """Any group a user sees can be opened into its own space, so the group is a place and not just a card."""
    if j.live:
        me = j.person('Mona Fathy'); pg = me['page']; x, g, names = world(j, me['id']); j.reload(pg)
        side_name = names['stab']; picks = [names['stab'], names['api'], names['pv'], names['qa'], names['pack']]
    else:
        pg = j.demo_signin(j.new_page()); side_name = 'Regulatory Affairs Egypt'
        picks = ['API Sourcing & Supply', 'Regulatory Affairs Egypt', 'GCC Market Access', 'Nutraceuticals MENA', 'Pharmacovigilance Egypt', 'Sterile Manufacturing Leaders', 'Packaging & Logistics Deal Room']
    groups_page(j, pg)
    with j.step('Open a group from the Your Groups side list: the interior of that group opens'):
        open_side(j, pg, side_name); j.check(gd_title(pg) == side_name, 'the side list entry "%s" opens "%s"' % (side_name, gd_title(pg)))
        gd_close(pg); j.check(not gd_open(pg), 'the × does not close the group')
    allc = {c['title']: c for c in cards(pg)}
    for t in picks:
        with j.step('Open "%s" from its card: the header matches the card and every tab has content' % t):
            groups_page(j, pg); c = allc.get(t) or next((x for x in cards(pg) if x['title'] == t), None)
            j.check(c, 'no card for "%s"' % t)
            y0 = pg.evaluate('scrollY'); open_card(j, pg, t); check_header(j, pg, c); ui_ok(j, pg, t)
            priv_out = re.search(PRIVATE, c['meta']) and not re.search(JOINED, c['btn'])
            if priv_out:
                tabs = gd_tabs(pg)
                j.check('about' in tabs or 'about' in gd_pane(pg, 'disc').lower() or len(j.text(pg, '#gpBox')) > 30, 'the private group "%s" shows nothing to a non-member (not even About)' % t)
            else:
                check_tabs(j, pg, bool(re.search(DEAL, c['meta'])))
            gd_close(pg); pg.wait_for_timeout(300)
            j.check(not gd_open(pg) and abs(pg.evaluate('scrollY') - y0) < 80, 'closing "%s" does not return to the list at the same place' % t)
    with j.step('Inside a group the browser Back button closes the group and stays in the app'):
        open_card(j, pg, picks[0]); pg.go_back(); pg.wait_for_timeout(1200)
        j.check(pg.evaluate("location.protocol") in ('file:', 'http:', 'https:') and j.in_app(pg), 'Back inside a group leaves the app')
        j.check(not gd_open(pg), 'Back does not close the group')
    with j.step('Reload while a group is open: the group (or the list) opens again without errors'):
        groups_page(j, pg); open_card(j, pg, picks[0]); reopen(j, pg)
        j.check(j.in_app(pg), 'after reload the app does not open')
        j.check(not [e for e in j.errors if e.startswith('pageerror')], 'page errors: %s' % '; '.join(j.errors[:3]))

@journey('J-COMMUNITY-03')
def read_discussion(j):
    """A member reads what colleagues are discussing in a group, which is the reason the group exists."""
    t = j.tag[:4]
    if j.live:
        me = j.person('Mona Fathy'); pg = me['page']
        ppl = [seed_user(j, n, h, c) for n, h, c in (('Dr. Rania Saad', 'RA Manager', 'Eva Pharma'), ('Dr. Tamer Nabil', 'QA Director', 'Pharco'),
                                                     ('Dr. Hoda Kamel', 'Regulatory Specialist', 'Amoun'), ('Dr. Wael Fouad', 'Stability Lead', 'EIPICO'))]
        gname = 'Regulatory Affairs Egypt %s' % t
        gid = seed_group(j, gname, ppl[0], desc='EDA registration and variations', rules='Search before you ask')
        for p in ppl[1:]: add_member(j, gid, p)
        add_member(j, gid, me['id'])
        ids = []
        for i in range(25): ids.append(seed_gpost(j, ppl[i % 4], gid, 'RA post %02d %s: variation question number %d' % (i, t, i), (25 - i) * 3600))
        pin = ids[3]; j.sql("update public.groups set pinned_post_id=%d where id=%d" % (pin, gid))
        j.sql("insert into public.post_media (post_id, url, type, name) values (%d, 'http://localhost:54393/storage/v1/object/public/post-media/x/photo.png', 'image', 'photo.png'), (%d, 'http://localhost:54393/storage/v1/object/public/post-media/x/spec.pdf', 'file', 'spec.pdf')" % (ids[24], ids[23]))
        priv = seed_group(j, 'Private QA Board %s' % t, ppl[1], private=True, desc='Only vetted QA heads')
        seed_gpost(j, ppl[1], priv, 'SECRET private post %s' % t, 60)
        j.reload(pg); want = ['RA post %02d %s' % (i, t) for i in range(24, -1, -1)]
    else:
        pg = j.demo_signin(j.new_page()); gname = 'Regulatory Affairs Egypt'; want = None
    with j.step('Open the group on Discussion: the pinned post first (marked Pinned), then newest first; each post shows author, headline, time, counts'):
        groups_page(j, pg); open_card(j, pg, gname)
        ps = gposts(pg); j.check(ps, 'the Discussion shows no posts')
        j.check(re.search(r'Pinned|مثب', ps[0]['all']), 'the first post is not the pinned post (or is not marked Pinned)')
        if j.live:
            j.check('RA post 03 %s' % t in ps[0]['text'], 'the pinned post is not first')
            order = [re.search(r'RA post \d\d \w+', p['text']).group(0) for p in ps[1:] if re.search(r'RA post \d\d', p['text'])]
            j.check(order == [w for w in want if w != 'RA post 03 %s' % t][:len(order)], 'the posts are not newest first: %s' % order[:5])
        for p in ps[:3]:
            j.check(p['author'] and re.search(r'ago|just now|now|منذ|الآن|\d+[mhdw]', p['all']), 'a post shows no author or time: %s' % p['all'][:80])
    with j.step('Older posts load on scroll / "Show more" with no duplicates until the first post, then an end marker'):
        for _ in range(12):
            if not pg.locator('#gpBox .gp-loadmore').count(): break
            pg.evaluate("(()=>{const m=document.querySelector('#gpBox .gp-loadmore');if(m){m.scrollIntoView();m.click()}})()"); pg.wait_for_timeout(1500)
        ps = gposts(pg); ids_ = [p['id'] for p in ps]
        j.check(len(ids_) == len(set(ids_)), 'duplicate posts after loading more')
        if j.live: j.check(len(ps) == 25, '%d of 25 posts reachable' % len(ps))
        j.check(re.search(r"No more posts|You.re all caught up|end of|That.s all|beginning of|لا توجد منشورات أخرى|نهاية|وصلت", gd_pane(pg, 'disc')[-400:], re.I), 'no end marker after the last post')
    with j.step('The image opens in a viewer and the PDF opens / downloads'):
        if j.demo: j.skip("the demo's sample groups have no image or PDF post — checked in live")
        img = pg.locator('#gpBox .post img[src*="photo.png"]').first
        j.check(img.count(), 'the image of the post is not shown'); img.click(); pg.wait_for_timeout(600)
        j.check(dlg_open(pg) or pg.locator('.lightbox:visible, .viewer:visible, [class*=lightbox]:visible, #lightbox.show').count(), 'the image does not open in a viewer')
        lb = pg.locator('#lightbox.show').count()
        if lb:   # the approved page's viewer: it must show this post's image, then close (the group stays open)
            j.check('photo.png' in (pg.locator('#lbImg').get_attribute('src') or ''), 'the viewer does not show the post\'s image')
            pg.locator('#lightbox .lb-close').click(); pg.wait_for_timeout(300)
            j.check(not pg.locator('#lightbox.show').count(), 'the image viewer does not close')
        else: close_dialogs(pg)
        f = pg.locator('#gpBox .post a[href*="spec.pdf"], #gpBox .post [data-url*="spec.pdf"]')
        j.check(f.count(), 'the PDF of the post is not shown as an attachment')
        asked = []; pg.context.on('request', lambda r: asked.append(r.url))
        with pg.context.expect_page(timeout=8000) as pop: f.first.click()   # clicking it opens the file (the seeded link's host is not served here)
        pop.value.wait_for_timeout(800)
        j.check(any('spec.pdf' in u for u in asked + [pop.value.url]), 'clicking the PDF does not open it (%s)' % pop.value.url); pop.value.close()
    with j.step("Click an author's name: that person's profile opens"):
        p = pg.locator('#gpBox .post .post-name').filter(has_not_text=pg.evaluate('ME.name')).first
        name = p.inner_text().strip().split('\n')[0]; p.click(); j.settle(pg, 1500)
        j.check(pg.evaluate("document.body.getAttribute('data-page')") == 'profile' and name.split()[-1] in j.text(pg)[:600], "clicking %s does not open that person's profile" % name)
    with j.step('A non-member opens a public group: reads the discussion, sees Join instead of a composer'):
        if j.live:
            o = j.person('Omar Outsider'); po = o['page']; pub = gname
        else:
            po = pg; pub = 'QA/QC Professionals'
        groups_page(j, po); open_card(j, po, pub)
        j.check(gposts(po), 'a non-member cannot read the public group')
        j.check(not has_composer(po), 'a non-member sees the composer')
        j.check(re.search(r'Join|انضم', ' '.join(gd_buttons(po))), 'a non-member sees no Join')
    with j.step('A non-member opens a private group: only About and "Request to join" — no posts, no members (live: RLS returns 0 posts)'):
        priv_name = 'Private QA Board %s' % t if j.live else 'Pharmacovigilance Egypt'
        groups_page(j, po); open_card(j, po, priv_name)
        txt = j.text(po, '#gpBox')
        j.check('SECRET' not in txt and not gposts(po), 'a non-member reads the private group')
        j.check(re.search(r'Request|طلب', ' '.join(gd_buttons(po)) + txt), 'no "Request to join" for the private group')
        if 'members' in gd_tabs(po):
            mt = gd_tab(j, po, 'members'); j.check(not re.search(r'Dr\. Tamer|Message', mt), 'a non-member sees the private member list')
        if j.live:
            n = po.evaluate("g=>dxLive.sb.from('posts').select('id').eq('group_id',g).then(r=>(r.data||[]).length)", priv)
            j.check(n == 0, 'the REST call returns %s posts of the private group to a non-member' % n)
            n2 = po.evaluate("()=>dxLive.sb.from('posts').select('id,body').is('group_id',null).limit(200).then(r=>(r.data||[]).filter(x=>/RA post/.test(x.body)).length)")
            j.check(n2 == 0, 'group posts are mixed into the home feed query')

@journey('J-COMMUNITY-04')
def post_in_group(j):
    """A member starts a discussion in a group so that the other members see it and can answer."""
    t = j.tag[:4]; body = 'Has anyone filed a variation under the new EDA guideline? %s' % t
    if j.live:
        a = j.person('Mona Fathy'); b = j.person('Bassem Member'); c = j.person('Celine Outsider')
        x = seed_user(j, 'Dr. Xena Admin'); gname = 'RA Variations %s' % t
        gid = seed_group(j, gname, x, desc='Variations'); add_member(j, gid, a['id']); add_member(j, gid, b['id'])
        priv = seed_group(j, 'RA Private %s' % t, x, private=True, listed=False); add_member(j, priv, a['id'])
        pg = a['page']; j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); gname = 'Regulatory Affairs Egypt'
    with j.step('Empty text posts nothing and says why'):
        groups_page(j, pg); open_card(j, pg, gname); n0 = len(gposts(pg))
        gcompose(j, pg, '', submit=False); mark = j.toast_mark(pg)
        pg.locator('.modal-bg.show .btn-p').last.click(); pg.wait_for_timeout(700)
        j.check(len(gposts(pg)) == n0, 'an empty post was published')
        j.check(dlg_open(pg) or j.toasts_since(pg, mark), 'an empty post gives no message')
        close_dialogs(pg)
    with j.step('Write the question with an image and Post: it appears at the top (under a pinned post) with my name, the image and "just now"'):
        gcompose(j, pg, body, image=PNG)
        ps = gposts(pg); top = [p for p in ps if not re.search(r'Pinned|مثب', p['all'])][:1]
        j.check(top and body in top[0]['text'], 'the new post is not at the top of the Discussion')
        j.check(pg.evaluate('ME.name').split()[-1] in top[0]['author'], 'the post does not show my name')
        j.check(re.search(r'just now|now|الآن|0m|1m', top[0]['all']), 'the post does not say "just now"')
        j.check(gpost(j, pg, body).locator('img').count(), 'the image is not on the post')
    if j.live:
        with j.step('Live: a posts row with group_id and the image in post-media'):
            pid = j.wait_db("select id from public.posts where group_id=%d and user_id='%s' and body like 'Has anyone filed%%'" % (gid, a['id']), 6)
            j.check(pid, 'no posts row with group_id for the new post')
            j.check(j.sql1("select count(*) from public.post_media where post_id=%s and type='image'" % pid) == '1', 'no post_media image row')
    with j.step('Reload: the post is still there'):
        reopen(j, pg); groups_page(j, pg); open_card(j, pg, gname)
        j.check(any(body in p['text'] for p in gposts(pg)), 'after reload the post is gone')
    with j.step('Member B sees the post; the group card / side list shows it is new'):
        if j.demo: j.skip('the other member exists only in live')
        pb = b['page']; j.reload(pb); groups_page(j, pb)
        sig = pb.evaluate("n=>{const c=[...document.querySelectorAll('#content .gcard')].find(e=>(e.querySelector('.gcard-title')||{}).innerText==n);return c?c.innerText:''}", gname)
        j.check(re.search(r'new post|جديد', sig), "B's card of the group shows no new-post signal (%s)" % sig.replace('\n', ' ')[:120])
        open_card(j, pb, gname); j.check(any(body in p['text'] for p in gposts(pb)), 'B does not see the post')
        j.check(notif_rows(j, b['id'], extra=' and (group_id=%d or post_id=%s)' % (gid, pid)) >= 1, 'B (group notifications on) is not notified of the new post')
    with j.step('Non-member C has no composer and the database refuses a post with that group_id; C cannot read the private group'):
        if j.demo:
            groups_page(j, pg); open_card(j, pg, 'QA/QC Professionals'); j.check(not has_composer(pg), 'a non-member has a composer'); return_ = None
        else:
            pc = c['page']; j.reload(pc); groups_page(j, pc); open_card(j, pc, gname)
            j.check(not has_composer(pc), 'non-member C has a composer')
            err = pc.evaluate("g=>dxLive.sb.from('posts').insert({user_id:dxLive.uuidOf(ME.id),body:'intruder',group_id:g})" + _dx.ERR, gid)
            j.check(err and j.sql1("select count(*) from public.posts where group_id=%d and body='intruder'" % gid) == '0', 'a non-member could post into the group')
            seed_gpost(j, x, priv, 'Private RA note %s' % t, 30)
            n = pc.evaluate("g=>dxLive.sb.from('posts').select('id').eq('group_id',g).then(r=>(r.data||[]).length)", priv)
            j.check(n == 0, 'C (not a member) reads %s posts of the private group' % n)
    with j.step('Edit the post: the new text shows for everyone'):
        groups_page(j, pg); open_card(j, pg, gname)
        menu(j, pg, gpost(j, pg, body), r'Edit|تعديل', 'Edit')
        ed = pg.locator('.modal-bg.show textarea, .dbk-ov textarea, #gpBox textarea:visible, #edBody').first
        j.check(ed.count(), 'Edit opens no editor'); ed.fill(body + ' (edited)')
        j.click(pg, r'^\W*(Save|Update|حفظ|تحديث)', scope='body', what='Save'); j.settle(pg, 900)
        j.check(any('(edited)' in p['text'] for p in gposts(pg)), 'the edit does not show')
        if j.live: j.check(j.wait_db("select count(*) from public.posts where group_id=%d and body like '%%(edited)'" % gid, 5) == '1', 'the edit is not saved')
    with j.step('Delete the post after a confirmation: it is gone for everyone'):
        menu(j, pg, gpost(j, pg, body), r'Delete|Remove|حذف', 'Delete'); confirm(j, pg); j.settle(pg, 900)
        j.check(not any(body in p['text'] for p in gposts(pg)), 'the deleted post is still shown')
        if j.live:
            j.check(j.wait_db("select count(*) from public.posts where group_id=%d and body like 'Has anyone%%'" % gid, 5, want='0') == '0', 'the posts row is still there')
            pb = b['page']; j.reload(pb); groups_page(j, pb); open_card(j, pb, gname)
            j.check(not any(body[:30] in p['text'] for p in gposts(pb)), 'B still sees the deleted post')

def comment_box(pg, post):
    pid = post.get_attribute('id').split('-')[-1]
    return pid, pg.locator('#ci-%s' % pid), pg.locator('#cmt-%s' % pid)

@journey('J-COMMUNITY-05')
def answer_in_group(j):
    """Members answer each other's group posts so that a question gets solved inside the group."""
    t = j.tag[:4]; q = 'Which stability zone does EDA require for a new site? %s' % t; ans = 'Zone IVb, 30C/75%% RH — see the 2024 guideline %s' % t
    if j.live:
        a = j.person('Vivian Zhou'); b = j.person('Bassem Member')
        x = seed_user(j, 'Dr. Xena Admin'); gname = 'Stability Q&A %s' % t
        gid = seed_group(j, gname, x); add_member(j, gid, a['id']); add_member(j, gid, b['id'])
        pid0 = seed_gpost(j, a['id'], gid, q, 300); c0 = j.sql1("insert into public.comments (post_id, user_id, body) values (%d, '%s', 'Earlier answer %s') returning id" % (pid0, x, t))
        pg = b['page']; j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); gname = 'Regulatory Affairs Egypt'; q = 'EDA e-submission reminder'
    with j.step("B opens the post's comments and writes an answer: it appears with B's name; the count +1"):
        groups_page(j, pg); open_card(j, pg, gname)
        post = gpost(j, pg, q); n0 = comment_count(post)
        pact(post, 2).click(); pg.wait_for_timeout(800)
        pid, inp, box = comment_box(pg, post)
        j.check(inp.count() and inp.is_visible(), 'the comment box does not open')
        inp.fill(ans); inp.press('Enter'); pg.wait_for_timeout(1000)
        j.check(ans in box.inner_text(), 'the answer does not appear under the post')
        j.check(pg.evaluate('ME.name').split()[-1] in box.inner_text(), "the answer does not show B's name")
        post = gpost(j, pg, q); j.check(comment_count(post) == n0 + 1, 'comment count %d → %d' % (n0, comment_count(post)))
    with j.step('B replies to an existing comment'):
        r = box.locator('.cmt [data-gpm=reply], .cmt [onclick*="reply" i], .cmt .cmt-reply, .cmt button:text-matches("^Reply$|^رد$", "i")').first
        j.check(r.count(), 'not built: no Reply on a comment'); r.click(); pg.wait_for_timeout(500)
        ri = pg.locator('#gpBox [id^=ri-]:visible').first
        if not ri.count(): ri = inp
        j.check(ri.is_visible(), 'Reply opens no reply box')
        pre = ri.input_value(); ri.press('End'); ri.type('Thanks, agreed ' + t); ri.press('Enter'); pg.wait_for_timeout(900)
        j.check(('Thanks, agreed ' + t) in box.inner_text(), 'the reply does not show')
        j.check(pre.strip().startswith('@') or box.locator('.cmt .cmt').count(), 'the reply is not linked to the comment (no @name, not nested)')
    if j.live:
        with j.step('Live: a comments row on the post; the author gets one notification with post_id'):
            j.check(j.wait_db("select count(*) from public.comments where post_id=%d and user_id='%s' and body like 'Zone IVb%%'" % (pid0, b['id']), 5) == '1', 'no comments row')
            j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and from_user='%s' and post_id=%d" % (a['id'], b['id'], pid0), 5) >= '1', 'the author got no notification with post_id')
    with j.step('A clicks the notification "B commented on your post": the group opens with the post and the comment in view'):
        if j.demo: j.skip('the other member exists only in live')
        pa = a['page']; j.reload(pa)
        open_notif(j, pa, r'comment|علّق|علق', 'commented on your post')
        j.check(gd_open(pa) and gd_title(pa) == gname, 'the notification does not open the group')
        j.check(ans[:20] in j.text(pa, '#gpBox'), 'the comment is not in view')
    with j.step('Both reload: the comment and the count stay'):
        reopen(j, pg); groups_page(j, pg); open_card(j, pg, gname)
        post = gpost(j, pg, q); pact(post, 2).click(); pg.wait_for_timeout(1000)
        pid, inp, box = comment_box(pg, post)
        j.check(ans[:20] in box.inner_text(), 'after reload the answer is gone')
    with j.step('B deletes own comment; the count goes back'):
        n1 = comment_count(gpost(j, pg, q))
        c = box.locator('.cmt', has_text=ans[:20]).first
        d = c.locator('[onclick*="del" i], [data-ca="delete"], button:text-matches("Delete|حذف", "i")')
        if not d.count():
            c.hover(); pg.wait_for_timeout(300); d = c.locator('[onclick*="del" i], [data-ca], button:text-matches("Delete|حذف|⋯", "i")')
        j.check(d.count(), 'not built: no Delete on my own comment'); d.first.click(); pg.wait_for_timeout(500)
        if dlg_open(pg) or pg.locator('.ctx-item:visible').count():
            el = j.find(pg, r'Delete|حذف', scope='body'); el and el.click(); pg.wait_for_timeout(700)
        confirm(j, pg)
        j.check(ans[:20] not in box.inner_text() and comment_count(gpost(j, pg, q)) == n1 - 1, 'deleting my comment did not remove it / update the count')

@journey('J-COMMUNITY-06')
def like_group_post(j):
    """Members show agreement or usefulness of a group post with a like so useful posts surface."""
    t = j.tag[:4]
    if j.live:
        a = j.person('Vivian Zhou'); b = j.person('Bassem Member')
        x = seed_user(j, 'Dr. Xena Admin'); gname = 'Likes Group %s' % t; gid = seed_group(j, gname, x)
        add_member(j, gid, a['id']); add_member(j, gid, b['id']); q = 'Useful CEP checklist %s' % t; pid = seed_gpost(j, a['id'], gid, q, 120)
        pg = b['page']; j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); gname = 'Regulatory Affairs Egypt'; q = 'Zone IVb stability for a cosmetic serum'
    groups_page(j, pg); open_card(j, pg, gname)
    def like_btn(): return pact(gpost(j, pg, q), 1)
    with j.step('B likes the post: the count +1 and the button shows liked'):
        n0 = like_count(gpost(j, pg, q))
        j.act(pg, like_btn(), 'Like', lambda: like_count(gpost(j, pg, q)) == n0 + 1, expect='the count %d → %d' % (n0, n0 + 1))
    with j.step('Reload: still liked'):
        reopen(j, pg); groups_page(j, pg); open_card(j, pg, gname)
        j.check(like_count(gpost(j, pg, q)) == n0 + 1, 'after reload the like is gone (%d)' % like_count(gpost(j, pg, q)))
    with j.step('Unlike: the count -1'):
        like_btn().click(); pg.wait_for_timeout(1000)
        j.check(like_count(gpost(j, pg, q)) == n0, 'unlike leaves the count at %d' % like_count(gpost(j, pg, q)))
    with j.step('Double click Like: counted once'):
        like_btn().dblclick(); pg.wait_for_timeout(1500)
        n = like_count(gpost(j, pg, q)); j.check(n in (n0, n0 + 1), 'a double click counts %d' % (n - n0))
        if n == n0: like_btn().click(); pg.wait_for_timeout(1000)
        j.check(like_count(gpost(j, pg, q)) == n0 + 1, 'the post is not liked once')
        if j.live:
            pg.wait_for_timeout(1000)
            j.check(j.sql1("select count(*) from public.reactions where post_id=%d and user_id='%s'" % (pid, b['id'])) == '1', 'not exactly one reactions row')
            j.check(j.sql1("select like_count = (select count(*) from public.reactions where post_id=%d) from public.posts where id=%d" % (pid, pid)) == 't', 'posts.like_count does not equal the rows')
    with j.step('The six reactions of the panel (as on Home): on a phone a quick tap on Like toggles it and pressing and holding Like opens the panel; with the mouse hovering opens it; each reaction is inside the screen, can be chosen, and replaces the previous one (still one reaction)'):
        touch = j.width <= 480
        if touch:   # a phone: a new touch context for B (taps and long presses, no hover)
            tp = j.new_page(j.new_ctx(touch=True))
            if j.live: j.signin(tp, b['email'], b['pw'])
            else: j.demo_signin(tp)
            groups_page(j, tp); open_card(j, tp, gname)
        else: tp = pg
        def lk(): return pact(gpost(j, tp, q), 1)
        def on(): return 'liked' in (lk().get_attribute('class') or '') or lk().get_attribute('aria-pressed') == 'true'
        def main(): return lk().locator('[data-gpm=react]:not([data-rk]), [data-lp]').last
        lk().evaluate("e=>e.scrollIntoView({block:'center'})"); tp.wait_for_timeout(200)
        if touch:
            was, c0 = on(), like_count(gpost(j, tp, q))
            main().tap(); tp.wait_for_timeout(1200)
            j.check(on() != was and like_count(gpost(j, tp, q)) == c0 + (-1 if was else 1), 'a quick tap on Like did not toggle it')
            j.check(not lk().locator('.rxn-panel').is_visible(), 'a quick tap on Like also opened the reaction panel')
            if not on(): main().tap(); tp.wait_for_timeout(1200)
        elif not on(): main().click(); tp.wait_for_timeout(1200)
        j.check(on(), 'B\'s like is gone before choosing a reaction')
        n1 = like_count(gpost(j, tp, q))
        for k in ('support', 'celebrate', 'insightful', 'appreciation', 'curious', 'like'):   # each replaces the one before (ends on Like)
            if touch:
                j.long_press(tp, main())
                j.check(lk().locator('.rxn-panel').is_visible(), 'pressing and holding Like does not open the reaction panel')
            else:
                tp.mouse.move(1, 1); tp.wait_for_timeout(150); lk().hover(); tp.wait_for_timeout(400)
                j.check(lk().locator('.rxn-panel').is_visible(), 'hovering Like does not open the reaction panel')
            bad = [x for x in ('like', 'support', 'celebrate', 'insightful', 'appreciation', 'curious') if not lk().locator('[data-rk="%s"]' % x).evaluate(
                """e=>{const r=e.getBoundingClientRect();const h=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
                   return r.width>0&&r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight&&!!h&&(h===e||e.contains(h))}""")]
            j.check(not bad, 'at %dpx the reaction panel leaves %s outside the screen or covered' % (j.width, ', '.join(bad)))
            it = lk().locator('[data-rk="%s"]' % k); it.tap() if touch else it.click(); tp.wait_for_timeout(1200)
            j.check(on() and like_count(gpost(j, tp, q)) == n1, 'choosing "%s" left the post %s with %d reactions (want %d)' % (k, 'liked' if on() else 'not liked', like_count(gpost(j, tp, q)), n1))
            if j.live:
                got = j.wait_db("select string_agg(kind,',') from public.reactions where post_id=%d and user_id='%s'" % (pid, b['id']), 5, want=k)
                j.check(got == k, 'after choosing "%s" the database holds kind(s) "%s" (want one row "%s")' % (k, got, k))
        if not touch: tp.mouse.move(1, 1)
        if j.live: j.check(j.sql1("select like_count = (select count(*) from public.reactions where post_id=%d) from public.posts where id=%d" % (pid, pid)) == 't', 'posts.like_count does not equal the rows after changing the reaction')
    with j.step('The author gets one "liked your post" notification (not one per toggle)'):
        if j.demo: j.skip('the author exists only in live')
        n = j.sql1("select count(*) from public.notifications where user_id='%s' and from_user='%s' and post_id=%d" % (a['id'], b['id'], pid))
        j.check(n == '1', '%s notifications for the author (want 1)' % n)

@journey('J-COMMUNITY-07')
def group_members(j):
    """A member sees who is in the group so she can connect with the right people."""
    t = j.tag[:4]
    if j.live:
        me = j.person('Mona Fathy'); pg = me['page']
        names = ['Dr. Member%02d %s' % (i, t) for i in range(12)]
        ppl = [seed_user(j, n, 'Pharmacist', 'Co%02d' % i) for i, n in enumerate(names)]
        gname = 'Members Group %s' % t; gid = seed_group(j, gname, ppl[0]); add_member(j, gid, ppl[1], 'admin')
        for p in ppl[2:]: add_member(j, gid, p)
        add_member(j, gid, me['id']); j.reload(pg); look = names[7]
    else:
        pg = j.demo_signin(j.new_page()); gname = 'Regulatory Affairs Egypt'; look = 'Sara El-Amin'
    with j.step('Open the group → Members: real members (name, headline) with admins marked; the total equals the header count'):
        groups_page(j, pg); open_card(j, pg, gname); hn = gd_members_n(pg)
        txt = gd_tab(j, pg, 'members')
        rows = pg.locator('#gpBox [data-pane=members] .member-row:visible').count()
        j.check(rows, 'the Members tab lists nobody')
        j.check(re.search(r'ADMIN|Admin|مشرف|مدير', txt), 'no admin is marked')
        mt = num(re.search(r'\(([\d,]+)\)', txt).group(1)) if re.search(r'\(([\d,]+)\)', txt) else rows
        j.check(mt == hn, 'the Members tab says %s, the header %s' % (mt, hn))
        more = pg.locator('#gpBox [data-pane=members] .gp-more:visible, #gpBox [data-pane=members] [data-gpa=more]:visible')
        for _ in range(10):
            if rows >= hn or not more.count(): break
            more.first.click(); pg.wait_for_timeout(900); rows = pg.locator('#gpBox [data-pane=members] .member-row:visible').count()
        j.check(rows == hn, '%d of %d members can be reached in the list' % (rows, hn))
    with j.step('Search the member list for a name: the list filters'):
        s = pg.locator('#gpBox [data-pane=members] input:visible')
        j.check(s.count(), 'not built: no search in the member list')
        s.first.fill(look.split()[-1] if j.demo else look.split()[1]); pg.wait_for_timeout(800)
        vis = pg.locator('#gpBox [data-pane=members] .member-row:visible')
        j.check(vis.count() >= 1 and all(look.split()[1 if j.live else -1] in vis.nth(i).inner_text() for i in range(vis.count())), 'the search does not filter the member list')
    with j.step("Click the member: that person's real profile opens (not mine)"):
        row = pg.locator('#gpBox [data-pane=members] .member-row:visible', has_text=look).first
        row.locator('.member-name, .av').first.click(); j.settle(pg, 1500)
        j.check(pg.evaluate("document.body.getAttribute('data-page')") == 'profile' and look.split()[-1 if j.demo else 1] in j.text(pg)[:600], "the member row does not open that person's profile")
    with j.step('From the profile, Connect works'):
        el = j.find(pg, r'^\W*(Connect|\+ Connect|تواصل|اتصال)\W*$', scope='#content', exact=True)
        if not el and j.find(pg, r'Pending|Connected|Message|معلق|قيد الانتظار|متصل|رسالة', scope='#content'): return
        j.check(el, 'no Connect on the member\'s profile'); el.click(); pg.wait_for_timeout(1200)
        where = pg.evaluate("document.body.getAttribute('data-page')")
        j.check(where == 'profile', "Connect on the member's profile leaves the profile (the app switches to '%s')" % where)
        j.check(j.find(pg, r'Pending|Sent|Withdraw|معلق|قيد الانتظار|تم الإرسال|سحب', scope='#content'), 'Connect does not turn to Pending')
        if j.live:
            uid = ppl[7]
            j.check(j.wait_db("select count(*) from public.connections where requester='%s' and addressee='%s'" % (me['id'], uid), 5) == '1', 'no connections row')

@journey('J-COMMUNITY-08')
def group_about(j):
    """Before joining, a user understands what the group is for and its rules."""
    t = j.tag[:4]
    if j.live:
        me = j.person('Mona Fathy'); pg = me['page']; x = seed_user(j, 'Dr. Xena Admin', 'Head of RA', 'Pharco')
        gname = 'About Group %s' % t; desc = 'For RA pharmacists filing with EDA %s' % t; rules = 'Search before you ask; no dossier content'
        gid = seed_group(j, gname, x, desc=desc, rules=rules, emoji='📋')
        g2 = 'No Rules Group %s' % t; seed_group(j, g2, x, desc='Nothing special')
        j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); gname = 'Regulatory Affairs Egypt'; desc = 'For regulatory affairs professionals'; rules = 'Search before you ask'; g2 = None
    with j.step('Open the group → About: description, rules, type, privacy, created date, admins and member count from the group'):
        groups_page(j, pg); open_card(j, pg, gname); hn = gd_members_n(pg)
        a = gd_tab(j, pg, 'about'); ui_ok(j, pg, 'About')
        j.check(desc in a, 'About does not show the description')
        j.check(rules.split(';')[0] in a, 'About does not show the rules')
        j.check(re.search(DISCUSS, a) or re.search(DEAL, a), 'About does not show the type')
        j.check(re.search(PUBLIC, a) or re.search(PRIVATE, a), 'About does not show the privacy')
        j.check(re.search(r'CREATED|Created|أنشئت|تاريخ الإنشاء|تأسست', a), 'About does not show when the group was created')
        j.check(re.search(r'ADMINS|Admins|المشرفون|المديرون', a), 'About does not show the admins')
        j.check(str(hn) in a.replace(',', ''), 'About does not show the member count (%s)' % hn)
    with j.step('An admin in About opens their profile'):
        adm = pg.locator('#gpBox [data-pane=about] .member-row .gp-name, #gpBox [data-pane=about] [onclick*="gotoProfile"]').last
        j.check(adm.count(), 'the admins in About are not clickable'); nm = adm.inner_text().strip().split('\n')[0]
        adm.click(); j.settle(pg, 1200)
        j.check(pg.evaluate("document.body.getAttribute('data-page')") == 'profile' and nm.split()[-1] in j.text(pg)[:500], 'the admin does not open their profile')
    with j.step("A person's name on a group card opens their profile — not the group — with no JavaScript error (G-16)"):
        groups_page(j, pg); ent = pg.locator('#gx .gcard .dx-entity:visible')
        if not ent.count(): j.skip('no group card names a person here')
        nm = ent.first.inner_text().strip(); before = len(j.errors)
        ent.first.click(); j.settle(pg, 1200)
        j.check(pg.evaluate("document.body.getAttribute('data-page')") == 'profile' and nm.split()[-1] in j.text(pg)[:500], 'the name on the card does not open %s\'s profile' % nm)
        bad = [e for e in j.errors[before:] if e.startswith('pageerror')]
        j.check(not bad, 'clicking the name throws: %s' % (bad[0] if bad else ''))
    with j.step('A group without rules says so (no sample text)'):
        if j.demo: j.skip('every sample group has rules — checked in live')
        groups_page(j, pg); open_card(j, pg, g2); a = gd_tab(j, pg, 'about')
        j.check(not re.search(r'Search before you ask|Documents first', a), 'a group without rules shows sample rules')
        j.check(re.search(r'no rules|No rules yet|لا توجد قواعد|بدون قواعد', a, re.I), 'a group without rules does not say so')

@journey('J-COMMUNITY-09')
def join_and_leave(j):
    """A user joins a public group to take part, and can leave it when it is no longer useful."""
    t = j.tag[:4]
    if j.live:
        me = j.person('Mona Fathy'); pg = me['page']; x = seed_user(j, 'Dr. Xena Admin')
        gname = 'Join Me Group %s' % t; gid = seed_group(j, gname, x, desc='Open to all'); j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); gname = 'QA/QC Professionals'
    with j.step("Click '+ Join' on the card: one toast, the button turns Joined, the count +1"):
        groups_page(j, pg); c = next((c for c in cards(pg) if c['title'] == gname), None); j.check(c, 'no card for %s' % gname)
        n0 = num(re.search(r'([\d,]+)\s*(members?|عضو|أعضاء)', c['text']).group(1)) if re.search(r'([\d,]+)\s*(members?|عضو|أعضاء)', c['text']) else None
        my0 = num(chip_text(pg, R('My Groups')))
        btn = pg.locator('#content .gcard').filter(has=pg.locator('.gcard-title', has_text=gname)).first.locator('.gcard-btn')
        before = set(pg.evaluate('window.__jt||[]')); cut = toast_cut(pg); btn.click(); j.settle(pg, 1200)
        ts = sorted(set(t for t in toasts_after(pg, cut) if t not in before))   # distinct texts: the toast log cannot tell a repeated toast apart
        j.check(len(ts) == 1, '%d different toasts for one Join: %s' % (len(ts), ts))
        c = next(c for c in cards(pg) if c['title'] == gname)
        j.check(re.search(JOINED, c['btn']), 'the button reads "%s" after Join' % c['btn'])
        n1 = num(re.search(r'([\d,]+)\s*(members?|عضو|أعضاء)', c['text']).group(1)) if re.search(r'([\d,]+)\s*(members?|عضو|أعضاء)', c['text']) else None
        j.check(n0 is None or n1 == n0 + 1, 'the member count went %s → %s' % (n0, n1))
    with j.step('Open the group: the header says member (Leave), the composer is there; it is in My Groups and the side list'):
        open_card(j, pg, gname)
        j.check(re.search(r'Leave|غادر|مغادرة', ' '.join(gd_buttons(pg))), 'the header has no Leave')
        j.check(has_composer(pg), 'no composer after joining')
        gd_close(pg)
        j.check(gname in sidebar(pg), 'the group is not in the Your Groups side list')
        j.check(num(chip_text(pg, R('My Groups'))) == (my0 or 0) + 1, 'My Groups went %s → %s' % (my0, chip_text(pg, R('My Groups'))))
    with j.step('Post a hello in the group'):
        open_card(j, pg, gname); gcompose(j, pg, 'Hello everyone %s' % t)
        j.check(any(('Hello everyone %s' % t) in p['text'] for p in gposts(pg)), 'the hello post does not show')
    if j.live:
        with j.step('Live: a group_members row; member_count = count(*)'):
            j.check(j.wait_db("select count(*) from public.group_members where group_id=%d and user_id='%s'" % (gid, me['id']), 5) == '1', 'no group_members row')
            mc = member_count_db(j, gid); j.check(mc.split('/')[0] == mc.split('/')[1], 'member_count/count = %s' % mc)
    with j.step('Reload: still a member, in My Groups and the side list'):
        reopen(j, pg); groups_page(j, pg)
        j.check(gname in sidebar(pg), 'after reload the group is not in the side list')
    with j.step('Open the group → Leave → confirm: count -1, gone from My Groups and the side list, no composer; my post stays'):
        open_card(j, pg, gname); hn = gd_members_n(pg)
        lb = pg.locator('#groupDetail .btn-leave:visible')
        j.check(lb.count(), 'no Leave in the header'); lb.first.click(); pg.wait_for_timeout(400)
        cf = pg.locator('#leaveConfirm.show .cp-btn-confirm, #leaveConfirm .cp-btn-confirm:visible')
        j.check(cf.count(), 'Leave asks for no confirmation'); cf.first.click(); j.settle(pg, 1200)
        if gd_open(pg):
            j.check(not has_composer(pg), 'the composer is still there after leaving')
            j.check(gd_members_n(pg) == hn - 1, 'the header count went %s → %s' % (hn, gd_members_n(pg)))
            j.check(any(('Hello everyone %s' % t) in p['text'] for p in gposts(pg)), 'my post disappeared when I left')
            gd_close(pg)
        j.check(gname not in sidebar(pg), 'the group is still in the side list after leaving')
        if j.live: j.check(j.wait_db("select count(*) from public.group_members where group_id=%d and user_id='%s'" % (gid, me['id']), 5, want='0') == '0', 'the group_members row is still there')
    with j.step('Reload: still left'):
        reopen(j, pg); groups_page(j, pg)
        j.check(gname not in sidebar(pg), 'after reload the group is back in the side list')
        c = next((c for c in cards(pg) if c['title'] == gname), None); j.check(c and re.search(r'Join|انضم', c['btn']), 'after reload the card is not Join')
    with j.step('Join from inside the group: the same result as from the card'):
        open_card(j, pg, gname)
        b = j.find(pg, r'Join|انضم', scope='#groupDetail', kinds='button'); j.check(b, 'no Join inside the group')
        b.click(); j.settle(pg, 1000)
        j.check(has_composer(pg) and re.search(r'Leave|غادر|مغادرة', ' '.join(gd_buttons(pg))), 'joining from inside does not make me a member')

@journey('J-COMMUNITY-10')
def private_request(j):
    """A private group stays private: people ask to join and an admin decides, so only vetted members read it."""
    t = j.tag[:4]
    if j.demo:
        pg = j.demo_signin(j.new_page())
        with j.step("Open the private group → 'Request to join': the button shows Requested (cancelable) and the posts stay hidden"):
            groups_page(j, pg); open_card(j, pg, 'Pharmacovigilance Egypt')
            b = j.find(pg, r'Request|طلب', scope='#groupDetail', kinds='button'); j.check(b, 'no Request to join')
            b.click(); j.settle(pg, 900); close_dialogs(pg)
            j.check(re.search(r'Requested|Request sent|Pending|Cancel|تم الطلب|تم إرسال|أرسل|قيد|إلغاء', ' '.join(gd_buttons(pg)) + j.text(pg, '#groupDetail')[:600]), 'the button does not show Requested')
            j.check(not gposts(pg), 'posts are readable while the request is pending')
        with j.step('Reload: still Requested; cancel and request again'):
            reopen(j, pg); groups_page(j, pg)
            c = next(c for c in cards(pg) if c['title'] == 'Pharmacovigilance Egypt')
            j.check(re.search(r'Requested|Request sent|Pending|قيد|تم الطلب|تم إرسال', c['btn']), 'after reload the request is gone (%s)' % c['btn'])
        with j.step('The admin sees the request in Manage → Requests and approves it'):
            groups_page(j, pg); open_card(j, pg, 'Regulatory Affairs Egypt'); manage(j, pg)
            tabs = ' | '.join(pg.evaluate("[...document.querySelectorAll('#managePanel .panel-tabs .gx-ptab')].map(t=>t.innerText.trim())"))
            j.check(re.search(r'Requests|طلبات الانضمام|الطلبات', tabs), 'not built: Manage has no Requests list (tabs: %s)' % tabs)
        return
    r = j.person('Rana Requester'); s = j.person('Sami Second'); xa = j.person('Xavier Admin')
    gname = 'Private PV Board %s' % t; gid = seed_group(j, gname, xa['id'], private=True, desc='PV heads only', rules='Confidential')
    seed_gpost(j, xa['id'], gid, 'Private PV signal discussion %s' % t, 300)
    pr, ps_, px_ = r['page'], s['page'], xa['page']; j.reload(pr)
    with j.step("R opens P → 'Request to join' (with a note): Requested (cancelable), posts stay hidden"):
        groups_page(j, pr); open_card(j, pr, gname)
        b = j.find(pr, r'Request|طلب', scope='#groupDetail', kinds='button'); j.check(b, 'no Request to join')
        b.click(); pr.wait_for_timeout(700)
        if dlg_open(pr):
            ta = pr.locator('.dbk-ov textarea, .modal-bg.show textarea')
            if ta.count(): ta.first.fill('I run PV at Pharco')
            dlg_click(j, pr, r'Send|Request|إرسال|أرسل|طلب', 'Send request')
        j.settle(pr, 900)
        j.check(re.search(r'Requested|Request sent|Pending|Cancel|تم الطلب|تم إرسال|أرسل|قيد|إلغاء', ' '.join(gd_buttons(pr))), 'the button does not show Requested: %s' % gd_buttons(pr))
        j.check('Private PV signal' not in j.text(pr, '#gpBox'), 'the posts are readable while pending')
        j.check(j.wait_db("select status from public.group_join_requests where group_id=%d and user_id='%s'" % (gid, r['id']), 5) == 'pending', 'no pending group_join_requests row')
    with j.step('R reloads: still Requested; cancels and requests again'):
        j.reload(pr); groups_page(j, pr)
        c = next(c for c in cards(pr) if c['title'] == gname); j.check(re.search(r'Requested|Request sent|Pending|قيد|تم الطلب|تم إرسال', c['btn']), 'after reload the card shows %s' % c['btn'])
        open_card(j, pr, gname); b = j.find(pr, r'Requested|Request sent|Cancel|Pending|إلغاء|قيد|تم إرسال', scope='#groupDetail', kinds='button'); j.check(b, 'no way to cancel the request')
        b.click(); pr.wait_for_timeout(600); confirm(j, pr, r'Cancel request|Yes|Confirm|إلغاء|نعم'); j.settle(pr, 900)
        j.check(j.wait_db("select count(*) from public.group_join_requests where group_id=%d and user_id='%s' and status='pending'" % (gid, r['id']), 5, want='0') == '0', 'cancel left a pending request')
        b = j.find(pr, r'Request|طلب', scope='#groupDetail', kinds='button'); b.click(); pr.wait_for_timeout(700)
        if dlg_open(pr): dlg_click(j, pr, r'Send|Request|إرسال|أرسل|طلب', 'Send request')
        j.check(j.wait_db("select status from public.group_join_requests where group_id=%d and user_id='%s'" % (gid, r['id']), 5) == 'pending', 'requesting again did not work')
    with j.step('A private group cannot be joined directly (the database refuses R as a member)'):
        err = pr.evaluate("g=>dxLive.sb.from('group_members').insert({group_id:g,user_id:dxLive.uuidOf(ME.id),role:'member'})" + _dx.ERR, gid)
        j.check(err and j.sql1("select count(*) from public.group_members where group_id=%d and user_id='%s'" % (gid, r['id'])) == '0', 'R joined the private group directly')
        e2 = pr.evaluate("([g,u])=>dxLive.sb.rpc('group_decide_request',{p_group:g,p_user:u,p_approve:true})" + _dx.ERR, [gid, r['id']])
        j.check(e2 and j.sql1("select count(*) from public.group_members where group_id=%d and user_id='%s'" % (gid, r['id'])) == '0', 'a non-admin approved a request')
    with j.step("X gets 'R asked to join P' that opens the Requests list with R's name and note"):
        j.reload(px_); where = open_notif(j, px_, r'asked to join|طلب الانضمام', 'asked to join')
        j.check(gd_open(px_) and gd_title(px_) == gname, 'the notification does not open the group')
        txt = j.text(px_, '#groupDetail')
        j.check('Rana' in txt and re.search(r'Requests|طلبات', txt), "the Requests list with R's request is not shown")
    with j.step('X approves R: R becomes a member (count +1)'):
        hn = gd_members_n(px_)
        row = px_.locator('#groupDetail [data-uid], #groupDetail .member-row, #groupDetail .req-row').filter(has_text='Rana').first
        j.check(row.count(), 'no row for R in Requests')
        ok = row.locator('button').filter(has_text=re.compile(r'Approve|Accept|قبول|موافقة', re.I)); j.check(ok.count(), 'no Approve on the request')
        ok.first.click(); j.settle(px_, 1200)
        j.check(j.wait_db("select count(*) from public.group_members where group_id=%d and user_id='%s'" % (gid, r['id']), 5) == '1', 'R is not a member after approval')
        j.check(gd_members_n(px_) == hn + 1, 'the header count went %s → %s' % (hn, gd_members_n(px_)))
    with j.step("R gets 'Your request to join P was approved' that opens P; R reads and posts"):
        j.reload(pr); open_notif(j, pr, r'approved|قبول|وافق', 'request approved')
        j.check(gd_open(pr) and gd_title(pr) == gname, 'the approval notification does not open the group')
        j.check('Private PV signal' in j.text(pr, '#gpBox'), 'R cannot read the posts after approval')
        gcompose(j, pr, 'Thanks for having me %s' % t)
        j.check(j.wait_db("select count(*) from public.posts where group_id=%d and user_id='%s'" % (gid, r['id']), 5) == '1', 'R cannot post')
    with j.step('S requests; X rejects: S is told politely, stays out, cannot read'):
        j.reload(ps_); groups_page(j, ps_); open_card(j, ps_, gname)
        j.find(ps_, r'Request|طلب', scope='#groupDetail', kinds='button').click(); ps_.wait_for_timeout(700)
        if dlg_open(ps_): dlg_click(j, ps_, r'Send|Request|إرسال|أرسل|طلب', 'Send request')
        j.check(j.wait_db("select status from public.group_join_requests where group_id=%d and user_id='%s'" % (gid, s['id']), 5) == 'pending', 'no request from S')
        j.reload(px_); groups_page(j, px_); open_card(j, px_, gname); manage(j, px_)
        rq = px_.locator('#managePanel [data-gpq-tab]')   # the journey: Manage → Requests
        if rq.count(): rq.first.click(); px_.wait_for_timeout(500)
        row = px_.locator('#groupDetail [data-uid]:visible, #groupDetail .member-row:visible, #groupDetail .req-row:visible').filter(has_text='Sami').first
        j.check(row.count(), 'no request row for S')
        no = row.locator('button').filter(has_text=re.compile(r'Reject|Decline|رفض', re.I)); j.check(no.count(), 'no Reject on the request')
        no.first.click(); px_.wait_for_timeout(500); confirm(j, px_, r'Reject|Decline|Yes|رفض|نعم'); j.settle(px_, 1000)
        j.check(j.wait_db("select status from public.group_join_requests where group_id=%d and user_id='%s'" % (gid, s['id']), 5) == 'rejected', 'the request is not rejected')
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and group_id=%d" % (s['id'], gid)) >= '1', 'S is not told')
        j.check(j.sql1("select count(*) from public.group_members where group_id=%d and user_id='%s'" % (gid, s['id'])) == '0', 'S became a member')

@journey('J-COMMUNITY-11')
def invite_members(j):
    """A group admin invites the right people so the group grows with relevant members."""
    t = j.tag[:4]
    if j.demo:
        pg = j.demo_signin(j.new_page())
        with j.step('X opens G → Invite, finds a connection and sends: the invitation shows as sent'):
            groups_page(j, pg); open_card(j, pg, 'Regulatory Affairs Egypt')
            b = j.find(pg, r'Invite|ادع|دعوة', scope='#groupDetail', kinds='button'); j.check(b, 'no Invite for the admin')
            b.click(); pg.wait_for_timeout(700); j.check(dlg_open(pg), 'Invite opens nothing')
            box = pg.locator('.dbk-ov input, .modal-bg.show input').first
            if box.count(): box.fill('Omar'); pg.wait_for_timeout(500)
            pick = pg.locator('.dbk-ov, .modal-bg.show').last.locator('[data-uid], label, .inv-row, input[type=checkbox]').first
            j.check(pick.count(), 'the invite dialog lists no connection'); pick.click(); pg.wait_for_timeout(300)
            mark = j.toast_mark(pg); dlg_click(j, pg, r'Send|Invite|إرسال|أرسل|دعوة|الدعوات', 'Send invitations')
            j.check(j.toasts_since(pg, mark), 'sending gives no confirmation')
        with j.step("An invited group shows an 'Invited' label with Accept / Decline; Accept makes me a member"):
            groups_page(j, pg); c = next((c for c in cards(pg) if c['title'] == 'Sterile Manufacturing Leaders'), None)
            j.check(c and re.search(r'Invited|Invitation|مدعو|دعوة', c['text']), "the invited group's card has no 'Invited' label")
            btn = pg.locator('#content .gcard').filter(has=pg.locator('.gcard-title', has_text='Sterile Manufacturing Leaders')).first.locator('.gcard-btn')
            btn.click(); j.settle(pg, 900)
            c = next((c for c in cards(pg) if c['title'] == 'Sterile Manufacturing Leaders'), None)
            j.check(c and re.search(JOINED, c['btn']), 'accepting the invitation does not make me a member (the card shows %s)' % (c['btn'] if c else 'nothing'))
        return
    xa = j.person('Xavier Admin'); i1 = j.person('Ibrahim Invitee %s' % t); i2 = j.person('Ismail Decliner %s' % t)
    j.sql("insert into public.connections (requester, addressee, status) values ('%s','%s','accepted'), ('%s','%s','accepted')" % (xa['id'], i1['id'], xa['id'], i2['id']))
    gname = 'Invite Group %s' % t; gid = seed_group(j, gname, xa['id'], desc='Invite only fun'); pname = 'Invite Private %s' % t
    pid = seed_group(j, pname, xa['id'], private=True, listed=False, desc='Private invite group')
    px_ = xa['page']; j.reload(px_)
    def invite(g, who):
        groups_page(j, px_); open_card(j, px_, g)
        b = j.find(px_, r'Invite|ادع|دعوة', scope='#groupDetail', kinds='button'); j.check(b, 'no Invite for the admin')
        b.click(); px_.wait_for_timeout(800); j.check(dlg_open(px_), 'Invite opens nothing')
        names = px_.locator('.dbk-ov textarea, .modal-bg.show textarea').first
        if names.count():                                    # the approved Invite dialog: names or e-mails, one per line
            names.fill(who)
        else:
            box = px_.locator('.dbk-ov input[type=search], .dbk-ov input[type=text], .modal-bg.show input[type=text]').first
            if box.count(): box.fill(who); px_.wait_for_timeout(700)
            row = px_.locator('.dbk-ov, .modal-bg.show').last.locator('label, [data-uid], .inv-row').filter(has_text=who)
            j.check(row.count(), 'the invite dialog does not list my connection %s' % who); row.first.click(); px_.wait_for_timeout(300)
        dlg_click(j, px_, r'Send|Invite|إرسال|أرسل|دعوة|الدعوات', 'Send invitations'); j.settle(px_, 1000)
    with j.step('X opens G → Invite, searches connections for I, sends: a group_invites row'):
        invite(gname, 'Ibrahim Invitee %s' % t)
        j.check(j.wait_db("select count(*) from public.group_invites where group_id=%d and user_id='%s'" % (gid, i1['id']), 5) == '1', 'no group_invites row')
    with j.step('X cannot invite the same person twice'):
        groups_page(j, px_); open_card(j, px_, gname)
        cut = toast_cut(px_); invite(gname, 'Ibrahim Invitee %s' % t); ts = ' '.join(toasts_after(px_, cut))
        j.check(j.sql1("select count(*) from public.group_invites where group_id=%d and user_id='%s'" % (gid, i1['id'])) == '1', 'a second invitation row')
        j.check(re.search(r'already|Already|مدعو|سبق', ts), 'inviting the same person again gives no "already invited" message (%s)' % ts[:100])
    with j.step("I gets 'X invited you to join G' that opens G with Accept / Decline"):
        pi = i1['page']; j.reload(pi); open_notif(j, pi, r'invited you|دعاك|دعوة', 'invited you')
        j.check(gd_open(pi) and gd_title(pi) == gname, 'the invitation notification does not open the group')
        j.check(re.search(r'Accept|قبول', ' '.join(gd_buttons(pi)) + j.text(pi, '#groupDetail')[:800]), 'the group shows no Accept for the invitation')
    with j.step("In I's groups list the group shows an 'Invited' label until answered"):
        groups_page(j, pi); c = next((c for c in cards(pi) if c['title'] == gname), None)
        j.check(c and re.search(r'Invited|Invitation|مدعو|دعوة', c['text']), "the invited group's card has no 'Invited' label")
    with j.step('I accepts: a member; the invitation is gone'):
        open_card(j, pi, gname); b = j.find(pi, r'Accept|Join|قبول|انضم', scope='#groupDetail', kinds='button'); j.check(b, 'no Accept')
        b.click(); j.settle(pi, 1000)
        j.check(j.wait_db("select count(*) from public.group_members where group_id=%d and user_id='%s'" % (gid, i1['id']), 5) == '1', 'accepting does not make I a member')
        j.check(j.sql1("select count(*) from public.group_invites where group_id=%d and user_id='%s'" % (gid, i1['id'])) == '0', 'the invitation row remains after accepting')
    with j.step('Private group: invite I, I accepts directly (no request); a second invitee declines'):
        invite(pname, 'Ibrahim Invitee %s' % t); invite(pname, 'Ismail Decliner %s' % t)
        j.reload(pi); open_notif(j, pi, r'invited you.*Private|دعاك', 'private invitation')
        b = j.find(pi, r'Accept|Join|قبول|انضم', scope='#groupDetail', kinds='button'); j.check(b, 'no Accept for the private group'); b.click(); j.settle(pi, 1000)
        j.check(j.wait_db("select count(*) from public.group_members where group_id=%d and user_id='%s'" % (pid, i1['id']), 5) == '1', 'I is not a member of the private group')
        p2 = i2['page']; j.reload(p2); open_notif(j, p2, r'invited you|دعاك', 'invitation')
        d = j.find(p2, r'Decline|رفض', scope='#groupDetail', kinds='button'); j.check(d, 'not built: no Decline for an invitation'); d.click(); j.settle(p2, 900)
        j.check(j.wait_db("select count(*) from public.group_invites where group_id=%d and user_id='%s'" % (pid, i2['id']), 5, want='0') == '0', 'Decline does not remove the invitation')

@journey('J-COMMUNITY-12')
def create_group(j):
    """A professional creates a new community for a topic and becomes its admin."""
    t = j.tag[:4]; name = 'Pharmacovigilance Egypt %s' % t
    if j.live: me = j.person('Mona Fathy'); pg = me['page']
    else: pg = j.demo_signin(j.new_page())
    def open_create():
        groups_page(j, pg); b = j.find(pg, r'^\W*(Create Group|Create New Group|إنشاء مجموعة|أنشئ مجموعة|أنشئ مجموعة جديدة)\W*$', scope='#content')
        j.check(b, 'no Create Group'); b.click(); pg.wait_for_timeout(700)
        j.check(pg.locator('#createModal.show, .modal-bg.show, .dbk-ov').count(), 'Create Group opens nothing')
    def submit():
        b = pg.locator('#createModal .btn-create, #createModal .btn-p, #createModal button.primary').last
        mark = j.toast_mark(pg); b.click(); j.settle(pg, 1200); return j.toasts_since(pg, mark)
    with j.step('Create with an empty name: a clear message, nothing created'):
        open_create(); n0 = len(cards(pg)); ts = submit()
        j.check(len(cards(pg)) == n0, 'a group with an empty name was created')
        j.check(ts or pg.locator('#createModal .err:visible, #createModal [aria-invalid=true]').count() or pg.locator('#createModal.show').count(), 'an empty name gives no message')
    with j.step('Fill name, description, type Discussion, privacy Private, topic, country, rules and emoji'):
        if not pg.locator('#createModal.show').count(): open_create()
        inp = pg.locator('#createModal input[type=text]:visible, #createModal input:not([type]):visible').first; inp.fill(name)
        ta = pg.locator('#createModal textarea:visible')
        if ta.count(): ta.first.fill('Signal detection, ICSRs and PSURs for EDA %s' % t)
        opt = pg.locator('#createModal .type-opt:visible').filter(has_text=re.compile(r'Discussion|نقاش'))
        if opt.count(): opt.first.click()
        pv = pg.locator('#createModal .privacy-opt').filter(has_text=re.compile(r'Private|خاصة|خاص'))
        j.check(pv.count(), 'not built: no privacy choice in Create Group'); pv.first.click()
        labels = ' '.join(x['label'] + ' ' + x['ph'] for x in pg.evaluate("[...document.querySelectorAll('#createModal input,#createModal select,#createModal textarea')].filter(e=>e.getClientRects().length).map(e=>({label:((e.labels&&e.labels[0]&&e.labels[0].innerText)||(e.closest('.form-group,.field')||{}).innerText||'').slice(0,40),ph:e.placeholder||''}))"))
        missing = [w for w, p in (('rules', r'rule|قواعد'), ('country', r'country|دولة|بلد'), ('topic', r'topic|sector|موضوع|قطاع')) if not re.search(p, labels + ' ' + j.text(pg, '#createModal'), re.I)]
        j.check(not missing, 'not built: Create Group has no field for %s' % ', '.join(missing))
    with j.step('Create: the new group opens; I am its admin (Manage) and the only member'):
        submit()
        j.check(gd_open(pg) and gd_title(pg) == name, 'the new group does not open after Create')
        j.check(pg.locator('#groupDetail .btn-manage:visible').count(), 'the creator has no Manage')
        j.check(gd_members_n(pg) == 1, 'the new group has %s members (want 1)' % gd_members_n(pg))
        gd_close(pg)
        j.check(name in sidebar(pg), 'the new group is not in the Your Groups side list')
        chip(j, pg, R('My Groups'), 'My Groups'); j.check(name in card_titles(pg), 'the new group is not in My Groups')
    if j.live:
        with j.step('Live: a groups row (private, the topic, rules) and an admin group_members row; slug unique'):
            gid = j.wait_db("select id from public.groups where name=$q$%s$q$" % name, 5); j.check(gid, 'no groups row')
            j.check(j.sql1("select type from public.groups where id=%s" % gid) == 'private', 'the group is not private in the database')
            j.check(j.sql1("select role from public.group_members where group_id=%s and user_id='%s'" % (gid, me['id'])) == 'admin', 'no admin row for the creator')
    with j.step('Reload: the group is still in My Groups and the side list'):
        reopen(j, pg); groups_page(j, pg); j.check(name in sidebar(pg), 'after reload the new group is gone')
    with j.step('A duplicate name is refused with a clear message'):
        open_create(); pg.locator('#createModal input[type=text]:visible, #createModal input:not([type]):visible').first.fill(name)
        ts = submit(); n = len([c for c in cards(pg) if c['title'] == name])
        j.check(n <= 1, 'a second group with the same name was created')
        j.check(ts and re.search(r'exist|already|taken|موجود|مستخدم', ' '.join(ts), re.I), 'a duplicate name gives no clear message (%s)' % ts)
    with j.step('Another user does not find the private unlisted group'):
        if j.demo: j.skip('the other user exists only in live')
        o = j.person('Omar Other'); po = o['page']; groups_page(j, po)
        j.check(name not in card_titles(po), 'another user sees the private group in the list')

if __name__ == '__main__': main(__file__)
