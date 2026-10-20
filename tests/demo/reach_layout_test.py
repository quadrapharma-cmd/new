"""Everything a person must tap can be tapped, and the Arabic interface says it in Arabic (demo build, phase 1b round 2).
  python3 tests/demo/reach_layout_test.py en|ar          (DEMO_FILE = the build to test)
Phone 390 (touch): a conversation's Send is not under the floating ☰; the conversation ⋯ menu opens inside the screen; each group
card holds its Join button. Tablet 768: the ⋯ menu of a short post shows all its items (not cut off by the card); the chat window's
Send sits inside the window (768 and 1440). Desktop 1440: the reaction panel of a post whose Like sits just under the top bar and
ticker can be used (it opens below Like). Arabic: profile empty states, the Jobs badges and tools, the composer greeting after an
Arabic title, and "N أعضاء" after a number."""
from playwright.sync_api import sync_playwright
import os, sys
F = os.environ.get('DEMO_FILE', '/tmp/drugbox_brand.html'); LANG = sys.argv[1] if len(sys.argv) > 1 else 'en'; AR = LANG == 'ar'; R = []
def T(n, ok, d=''): R.append(bool(ok)); print(('✅ ' if ok else '❌ ') + n + ('' if ok else '  → ' + str(d)[:300]))
RECT = "e=>{const r=e.getBoundingClientRect();return [Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]}"
HIT = "e=>{const r=e.getBoundingClientRect(),h=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return !!h&&(h===e||e.contains(h))}"
WHO = "e=>{const r=e.getBoundingClientRect(),h=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return h?(h.id||String(h.className)||h.tagName):'nothing'}"

def page(b, w, touch=False):
    c = b.new_context(viewport={'width': w, 'height': 844 if w < 500 else 900}, has_touch=touch, is_mobile=touch)
    c.add_init_script("try{localStorage.setItem('dx_lang','%s');localStorage.setItem('dx_tour_done','1')}catch(e){}" % LANG)
    pg = c.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:150])); pg.errs = errs
    pg.goto('file://' + F, wait_until='load'); pg.wait_for_timeout(800)
    try: pg.evaluate('endSplash()')
    except Exception: pass
    pg.wait_for_timeout(400); (pg.wait_for_function("()=>!!(document.getElementById('app').getClientRects().length||document.querySelector('.lg-demo').getClientRects().length)", timeout=15000) and pg.locator('.lg-demo').is_visible()) and (pg.click('.lg-demo') or pg.click('#loginPage button.f-btn.dx-js-only')); pg.wait_for_timeout(2200)
    return c, pg

def short_posts(pg):   # every new post: no stats row, no picture, one line
    pg.evaluate("document.querySelectorAll('#content .post').forEach(x=>{x.querySelectorAll('.post-stats,img,.post-img,.post-imgs,.post-media').forEach(s=>s.remove());const t=x.querySelector('.post-body,.post-text');if(t)t.textContent='Short.'})")

with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'])
    # ── phone 390, touch ──────────────────────────────────────────────────────────────────────────────────────
    c, pg = page(b, 390, touch=True); E = pg.evaluate
    E("goto('messages')"); pg.wait_for_timeout(900); pg.locator('.mx-thread').first.click(); pg.wait_for_timeout(600)
    sb = pg.query_selector('#mx .send-btn'); sb.scroll_into_view_if_needed(); pg.wait_for_timeout(200)
    T('390: a tap on a conversation\'s Send reaches Send (not the floating ☰)', E(HIT, sb), E(WHO, sb))
    pg.fill('#composeInput', 'Tapped send ' + LANG); n0 = E("document.querySelectorAll('#messagesArea .mx-mine').length")
    sb.tap(); pg.wait_for_timeout(500)
    T('390: tapping Send sends the message (and the side menu stays closed)', E("document.querySelectorAll('#messagesArea .mx-mine').length") > n0 and not E("document.querySelector('.sidebar').classList.contains('open')"))
    mb = pg.query_selector('#mx .ch-action-btn[onclick*=toggleChatMenu]'); mb.tap(); pg.wait_for_timeout(300)
    r = E(RECT, pg.query_selector('#chatMenu'))
    T('390: the conversation ⋯ menu opens inside the screen', r[0] >= 0 and r[2] <= 390, r)
    items = [x for x in pg.query_selector_all('#chatMenu .ch-dd-item') if x.is_visible()]
    T('390: every item of that menu can be tapped', items and all(E(HIT, x) for x in items), [E(WHO, x) for x in items])
    pg.mouse.click(5, 400); E("goto('groups')"); pg.wait_for_timeout(1000)
    bad = E("""()=>[...document.querySelectorAll('#gx .gcard')].filter(c=>c.getClientRects().length).map(c=>{const b=c.querySelector('.gcard-btn');if(!b)return null;const r=b.getBoundingClientRect(),q=c.getBoundingClientRect();return (r.right>q.right+1||r.left<q.left-1||q.right>innerWidth+1||q.left<-1)?c.querySelector('.gcard-title').textContent:null}).filter(Boolean)""")
    T('390: every group card (and its Join button) is inside the card and the screen', not bad, bad)
    if AR:
        E("ME.name='د. سلمى نيوكمر'"); E("goto('feed')"); pg.wait_for_timeout(600)
        g = E("(document.querySelector('.comp-btn')||{}).textContent||''")
        T('AR: the composer greets by the name after an Arabic title (never "يا د.")', 'سلمى' in g and 'يا د.' not in g, g)
    T('390: no page errors', not pg.errs, pg.errs); c.close()

    # ── tablet 768 and desktop 1440, mouse ─────────────────────────────────────────────────────────────────────
    for w in (768, 1440):
        c, pg = page(b, w); E = pg.evaluate
        E("goto('feed')"); pg.wait_for_timeout(900); short_posts(pg)
        btn = pg.query_selector('#content .post [data-mpid]'); btn.scroll_into_view_if_needed(); btn.click(); pg.wait_for_timeout(400)
        items = pg.query_selector_all('#content .post [id^="pm-"][data-dx-open] .ctx-item')
        T('%d: the ⋯ menu of a short post shows every item (Save, Copy link, Report)' % w, len(items) >= 3 and all(E(HIT, x) for x in items), [E(WHO, x) for x in items])
        pg.mouse.click(5, 5); E("goto('companies')"); pg.wait_for_timeout(500); E("window.dxOpenChat('Dr. Alia Mourad')"); pg.wait_for_timeout(500)
        sd, win = pg.query_selector('#dxDock .dk-f button'), pg.query_selector('#dxDock .dk-win')
        rs, rw = E(RECT, sd), E(RECT, win)
        T('%d: the chat window\'s Send button is inside the window and can be clicked' % w, rs[0] >= rw[0] and rs[2] <= rw[2] and E(HIT, sd), (rs, rw, E(WHO, sd)))
        if w == 1440:
            E("goto('feed')"); pg.wait_for_timeout(900)
            like = pg.query_selector('#content .post .pact[id^="like-"]'); off = 90   # just under the top bar and the ticker
            for _ in range(4):
                top = E("l=>l.getBoundingClientRect().top", like)
                if abs(top - off) < 2: break
                E("([l,y])=>{const t0=l.getBoundingClientRect().top;window.scrollBy(0,y);if(Math.abs(l.getBoundingClientRect().top-t0)<1){let e=l.parentElement;while(e&&!(e.scrollHeight>e.clientHeight+5&&/(auto|scroll)/.test(getComputedStyle(e).overflowY)))e=e.parentElement;if(e)e.scrollTop+=y}}", [like, top - off]); pg.wait_for_timeout(250)
            bb = like.bounding_box(); pg.mouse.move(bb['x'] + bb['width'] / 2, bb['y'] + bb['height'] / 2); pg.wait_for_timeout(400)
            rx = [x for x in like.query_selector_all('.rxn-panel > *') if x.is_visible()]
            T('1440: Like just under the top bar — all six reactions can be reached', len(rx) == 6 and all(E(HIT, x) for x in rx), [E(WHO, x) for x in rx])
        if AR and w == 1440:
            E("gotoProfile(7)"); pg.wait_for_timeout(800)
            tab = [t for t in pg.query_selector_all('.ptab') if 'الخبرة' in t.inner_text()]
            if tab: tab[0].click(); pg.wait_for_timeout(500)
            tx = E("document.getElementById('profileTabContent').innerText")
            T('AR: profile empty states and headings are Arabic (no "No education added." / "Education")', 'No education added' not in tx and 'Education' not in tx and 'التعليم' in tx, tx[:300])
            E("goto('jobs')"); pg.wait_for_timeout(1000); E("(()=>{const m=[...document.querySelectorAll('#jx .mode-opt')];m[1]&&m[1].click()})()"); pg.wait_for_timeout(600)
            badges = E("[...document.querySelectorAll('#jx .jcard .role-badge,#jx .jcard .level-badge')].filter(e=>e.getClientRects().length).map(e=>e.textContent.trim())")
            T('AR: the job cards\' badges (Hiring, Looking for a Job, levels) are Arabic', badges and not any(any(w in t for w in ('Hiring', 'Looking', 'Level', 'Junior', 'Senior', 'Executive')) for t in badges), badges[:8])
            sub = E("[...document.querySelectorAll('#jx .sec-sub,#jx .post-cta-title')].filter(e=>e.getClientRects().length).map(e=>e.textContent.trim())")
            T('AR: "Sorted by most recent" / "Looking for your next role?" are Arabic', not any(('Sorted by' in t or 'next role' in t) for t in sub), sub)
            E("goto('jobs')"); pg.wait_for_timeout(800)
            eng = []
            for i in range(E("document.querySelectorAll('#jx .jx-tool').length")):
                E("i=>document.querySelectorAll('#jx .jx-tool')[i].click()", i); pg.wait_for_timeout(500)
                eng += E("""()=>{const o=[];document.querySelectorAll('.dbk-modal-bg,.dbk-ov,.dbk-modal,[role=dialog]').forEach(m=>{const w=document.createTreeWalker(m,NodeFilter.SHOW_TEXT);while(w.nextNode()){const t=w.currentNode.nodeValue.trim();if(/^(Ranked only|🏅 Public|Preferred candidates|No one yet|Nothing here yet|No reviews yet|My lists|⚠️ Visible to)/.test(t))o.push(t.slice(0,60))}});return o}""")
                pg.keyboard.press('Escape'); pg.wait_for_timeout(200); E("document.querySelectorAll('.dbk-modal-bg,.dbk-ov').forEach(m=>m.remove())")
            T('AR: the Jobs tools (Top rated, Honor list, Warning list, My lists) are Arabic', not eng, eng[:6])
            E("goto('groups')"); pg.wait_for_timeout(800); E("(()=>{const c=document.querySelector('#gx .gcard');c&&c.click()})()"); pg.wait_for_timeout(800)
            st = E("(document.querySelector('.group-meta-stats')||{}).innerText||''")
            T('AR: a member count takes the Arabic plural after its number (not "9 عضو")', st and not __import__('re').search(r'\b([2-9]|10)\s*عضو', st), st)
        T('%d: no page errors' % w, not pg.errs, pg.errs); c.close()
    b.close()
print('%d / %d' % (sum(R), len(R)))
sys.exit(0 if all(R) else 1)
