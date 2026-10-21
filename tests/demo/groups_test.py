"""Groups (demo build): every group opens with its inside — Discussion (composer, posts, pinned first, like / comment / share),
Members (role pills, Message / Connect), About (description, rules, type, privacy, created, admins), Listings for deal rooms —
public preview + Join, private 'Request to join' (pending), invitations, what you write survives a reload, Escape closes,
phone width 390 px, no errors, and (Arabic) no untranslated interface text inside a group."""
from playwright.sync_api import sync_playwright
import os, sys, re
F = os.environ.get('DEMO_FILE', '/tmp/drugbox_brand.html'); LANG = sys.argv[1] if len(sys.argv) > 1 else 'en'; R = []
AR = LANG == 'ar'
def T(n, ok, d=''): R.append(bool(ok)); print(('✅ ' if ok else '❌ ') + n + ('' if ok else '  → ' + str(d)[:300]))

# interface text inside a group that is still English in Arabic (what people wrote, names and product data are not translated)
UNTR = r"""(() => {
  const SKIP = 'script,style,svg,input,textarea,select,option,[contenteditable],.post-body,.post-text,.cmt-text,.gcard-title,.gcard-desc,.lc-title,.dc-title,[data-noi18n],.post-name,.post-sub,.member-name,.member-meta,.badge-cat,.cert-p,.price,.moq,.mod-meta,.mod-reason,.dx-entity,.post-av,.av,.mini-av,.group-title,.cmt-name,.cmt-author';
  const roots = [...document.querySelectorAll('#groupDetail.show, .modal-bg, .dbk-modal, #dbkToast, .dbk-toast, .toast')].filter(r => r.offsetParent !== null || getComputedStyle(r).position === 'fixed');
  const out = new Set(), NAMES = new Set((window.USERS || []).map(u => u.name).concat([(window.ME || {}).name]));
  const UI = /^(URGENT|OPEN|NEW|RECOMMENDED|ARCHIVED|SUPPLY|DISCUSS|DEAL|ROOM|PINNED|ACTIVE)$/;
  for (const r of roots) {
    const w = document.createTreeWalker(r, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) {
      const n = w.currentNode, p = n.parentElement, v = n.nodeValue.replace(/\s+/g, ' ').trim();
      if (!p || !v || !/[A-Za-z]{2,}/.test(v) || /[\u0600-\u06FF]/.test(v) || p.closest(SKIP)) continue;   /* Arabic around a name or a product = translated */
      if (NAMES.has(v.replace(/ ✓$/, '')) || (p.closest('.cmt') && /^·/.test(v))) continue;   /* people's names; a commenter's job title */
      if (p.closest('#managePanel') && getComputedStyle(p.closest('#managePanel')).display === 'none') continue;
      if (!(p.offsetWidth || p.offsetHeight || p.getClientRects().length)) continue;
      const words = v.match(/[A-Za-z][A-Za-z'’-]*/g) || [];
      if (words.every(x => (/^[A-Z0-9-]{2,}$/.test(x) && !UI.test(x)) || /^(Drugbox|CoA|HCl|kg|mg|mL|IU|pcs|vs)$/.test(x))) continue;   /* acronyms (GMP, CEP, EDA, RFQ…) and units */
      out.add(v.slice(0, 90));
    }
  }
  return [...out];
})()"""

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); ctx = b.new_context(viewport={'width': 1440, 'height': 900})
    ctx.add_init_script("try{localStorage.setItem('dx_lang','%s')}catch(e){}" % LANG)
    pg = ctx.new_page(); errs = []; untr = set()
    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    pg.on("console", lambda m: errs.append('console: ' + m.text[:200]) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    E = pg.evaluate
    def W(ms=250): pg.wait_for_timeout(ms)
    def sweep():
        if AR: W(120); [untr.add(x) for x in E(UNTR)]
    def login():
        pg.goto('file://' + F, wait_until='load'); E('endSplash()'); W(700)
        pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); W(2800)
        if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
        E("goto('groups')"); W(700)
    def card(title): return f"[...document.querySelectorAll('#gx .gcard')].find(c=>dxOrigText(c.querySelector('.gcard-title')).trim()==={title!r})"
    def open_card(title):
        E(f"{card(title)}.querySelector('.gcard-title').click()")
        pg.wait_for_function("t=>{const c=window.dxGroups&&dxGroups.current();return !!c&&c.title===t&&document.getElementById('groupDetail').classList.contains('show')}", arg=title, timeout=8000); W(200)
    def tab(name):
        C(f"#gpBox [data-gpt={name}]"); pg.wait_for_function("n=>{const p=document.querySelector('#gpBox [data-pane='+n+']');return !!p&&!p.hidden&&p.children.length>0}", arg=name, timeout=8000); W(150)
    def cur(): return E("dxGroups.current()") or {}
    def toast(): return E("(()=>{const t=[...document.querySelectorAll('.dbk-toast,#dbkToast,.toast,[class*=toast]')].map(x=>x.textContent).join(' | ');return t})()")
    def close(): E("closeGroup()"); W(200)
    def C(sel):   # click once the element is there (slow machines)
        pg.wait_for_function("s=>!!document.querySelector(s)", arg=sel, timeout=8000); E("s=>document.querySelector(s).click()", sel)
    def confirm(): E("(()=>{const l=document.querySelectorAll('.dbk-ov');l[l.length-1].querySelector('[data-a=ok]').click()})()")
    def first_free_post(): return E("(()=>{const l=[...document.querySelectorAll('#gpBox .gp-posts .post')];const x=l.find(p=>!dxOrigText(p).includes('📌 Pinned'))||l[0];return x?x.getAttribute('data-gpp'):null})()")

    login()
    titles = E("[...document.querySelectorAll('#gx .gcard')].map(c=>dxOrigText(c.querySelector('.gcard-title')).trim())")
    T('the groups page has every group card (the approved nine + Cosmetics Formulators, a private group and an invitation)', len(titles) >= 12, titles)

    # 1 · every card opens its own group, with tabs and content
    bad = []
    for t in titles:
        open_card(t)
        st = E("(()=>({show:document.getElementById('groupDetail').classList.contains('show'),title:dxOrigText(document.getElementById('dt-title')).trim(),tabs:[...document.querySelectorAll('#gpBox [data-gpt]')].map(x=>x.dataset.gpt),posts:document.querySelectorAll('#gpBox .gp-posts .post').length,gate:!!document.querySelector('#gpBox .gp-lock, #gpBox .gp-gate'),deal:/deal/i.test(dxOrigText(document.getElementById('dt-type')))}))()")
        ok = st['show'] and st['title'] == t and st['tabs'][:3] == ['disc', 'members', 'about'] and (st['posts'] > 0 or st['gate']) and (('listings' in st['tabs']) == st['deal'])
        if not ok: bad.append((t, st))
        sweep(); close()
    T('every group card opens that group (title, Discussion / Members / About, posts or a join gate, Listings only in deal rooms)', not bad, bad)

    rows = E("[...document.querySelectorAll('#gx .mygroup .mg-name')].map(x=>dxOrigText(x).trim())"); bad = []
    for i, t in enumerate(rows):
        E(f"document.querySelectorAll('#gx .mygroup')[{i}].click()"); W(400)
        if (cur().get('title') != t): bad.append((t, cur()))
        close()
    T('every "Your Groups" side row opens its own group', rows and not bad, bad)

    # 2 · discussion in a group you are in
    open_card('API Sourcing & Supply')
    T('a member sees the composer (the Home composer) above the posts', E("!!document.querySelector('#gpBox .gp-comp .composer .comp-btn')"))
    T('the pinned post comes first', E("(()=>{const p=document.querySelector('#gpBox .gp-posts .post');return !!p&&dxOrigText(p).includes('📌 Pinned')})()"))
    C("#gpBox .gp-comp .comp-btn"); W(400)
    T('the composer opens the post window, addressed to the group', E("!!document.querySelector('.modal-bg[data-gpk] #postBody')"))
    sweep()
    pg.fill('.modal-bg[data-gpk] #postBody', 'Need 200 kg Azithromycin dihydrate USP — CoA and DMF letter please')
    C(".modal-bg[data-gpk] .btn-p"); W(600)
    T('the new post is published in the group, right under the pinned post', E("(()=>{const l=[...document.querySelectorAll('#gpBox .gp-posts .post')];return l.length>1&&l[1].textContent.includes('Azithromycin dihydrate USP')&&dxOrigText(l[0]).includes('📌 Pinned')})()"))
    T('the post window closed and the group is still open', not E("!!document.querySelector('.modal-bg[data-gpk]')") and E("document.getElementById('groupDetail').classList.contains('show')"))
    T('the post did not go to the Home feed', not E("POSTS.some(p=>String(p.body||'').includes('Azithromycin dihydrate USP'))"))
    sweep()
    pid = first_free_post()
    before = E(f"(()=>{{const p=document.querySelector('#gpBox [data-gpp=\"{pid}\"]');return p.querySelector('.post-stats')?p.querySelector('.post-stats').textContent:''}})()")
    C(f"#gpBox [data-gpp=\"{pid}\"] .pact[id^=like-] [data-gpm=react]"); W(300)
    T('Like works (the button is pressed and the count goes up)', E(f"document.querySelector('#gpBox [data-gpp=\"{pid}\"] .pact[id^=like-]').classList.contains('liked')"), before)
    seed = E("(()=>{const l=[...document.querySelectorAll('#gpBox .gp-posts .post')];const x=l.find(p=>p.textContent.includes('Q4 price update'));return x.getAttribute('data-gpp')})()")
    n0 = E(f"(()=>{{const s=document.querySelector('#gpBox [data-gpp=\"{seed}\"] .post-stats [data-gpm=reactors]');const m=s&&s.textContent.match(/([\\d,]+)/);return m?+m[1].replace(/,/g,''):0}})()")
    C(f"#gpBox [data-gpp=\"{seed}\"] .pact[id^=like-] [data-gpm=react]"); W(300)
    n1 = E(f"(()=>{{const s=document.querySelector('#gpBox [data-gpp=\"{seed}\"] .post-stats [data-gpm=reactors]');const m=s&&s.textContent.match(/([\\d,]+)/);return m?+m[1].replace(/,/g,''):0}})()")
    T('liking a sample post adds one reaction (112 → 113)', n1 == n0 + 1, (n0, n1))
    cnt = lambda: E(f"(()=>{{const s=document.querySelector('#gpBox [data-gpp=\"{seed}\"] .post-stats [data-gpm=reactors]');const m=s&&s.textContent.match(/([\\d,]+)/);return m?+m[1].replace(/,/g,''):0}})()")
    liked = lambda: E(f"document.querySelector('#gpBox [data-gpp=\"{seed}\"] .pact[id^=like-]').classList.contains('liked')")
    C(f"#gpBox [data-gpp=\"{seed}\"] .pact[id^=like-] [data-rk=celebrate]"); W(300)
    T('choosing another reaction from the panel replaces the like, as on Home (still one reaction: 113)', liked() and cnt() == n1, (liked(), cnt()))
    C(f"#gpBox [data-gpp=\"{seed}\"] .pact[id^=like-] [data-rk=celebrate]"); W(300)
    T('choosing the same reaction again takes it back (112)', not liked() and cnt() == n0, (liked(), cnt()))
    C(f"#gpBox [data-gpp=\"{seed}\"] .pact[id^=like-] [data-gpm=react]"); W(300)
    C(f"#gpBox [data-gpp=\"{seed}\"] [data-gpm=cmts]"); W(250)
    T('Comment opens the comments with an input', E(f"(()=>{{const c=document.querySelector('#gpBox [data-gpp=\"{seed}\"] [id^=cmt-]');return c.style.display!=='none'&&!!c.querySelector('.cmt-input')}})()"))
    pg.fill(f'#gpBox [data-gpp="{seed}"] .cmt-input', 'Thanks — very useful for our Q1 plan')
    pg.press(f'#gpBox [data-gpp="{seed}"] .cmt-input', 'Enter'); W(400)
    T('Enter posts the comment under the post', E(f"document.querySelector('#gpBox [data-gpp=\"{seed}\"] [id^=cmt-]').textContent.includes('very useful for our Q1 plan')"))
    sweep()
    C(f"#gpBox [data-gpp=\"{seed}\"] [data-gpm=share]"); W(300)
    T('Share opens a window: repost to your feed or copy the link', E("!!document.querySelector('[data-so=feed]') && !!document.querySelector('[data-so=link]')"))
    sweep()
    nfeed = E("POSTS.length"); C("[data-so=feed]"); W(300)
    T('Repost to your feed puts the post on Home', E("POSTS.length") == nfeed + 1 and E("POSTS[0].body.includes('Q4 price update')"))
    C(f"#gpBox [data-gpp=\"{seed}\"] [data-gpm=save]"); W(250)
    T('Save marks the post as saved', E(f"document.querySelector('#gpBox [data-gpp=\"{seed}\"] .post-acts [data-gpm=save]').classList.contains('dbk-saved')"))
    C(f"#gpBox [data-gpp=\"{seed}\"] [data-gpm=report]"); W(300)
    T('Report opens the report window with reasons', E("document.querySelectorAll('input[name=gpRep]').length") >= 4)
    sweep()
    pg.keyboard.press('Escape'); W(300)
    T('Escape closes the window on top and leaves the group open', not E("!!document.querySelector('input[name=gpRep]')") and E("document.getElementById('groupDetail').classList.contains('show')"))

    # 3 · Members, About, Listings
    tab('members'); sweep()
    T('Members: rows with role pills (admin first)', E("(()=>{const r=[...document.querySelectorAll('#gpBox [data-pane=members] .member-row')];return r.length>=4&&!!r[0].querySelector('.role-pill.rp-admin')&&!!document.querySelector('#gpBox [data-pane=members] .rp-member')})()"))
    T('Members: Message and Connect on other people, "You" on yourself', E("(()=>{const p=document.querySelector('#gpBox [data-pane=members]');return !!p.querySelector('[data-gpa=msg]')&&!!p.querySelector('[data-gpa=conn]')&&!!p.querySelector('.gp-you')})()"))
    E("(()=>{const i=document.querySelector('#gpBox .gp-msearch');i.value='vivian';i.dispatchEvent(new Event('input',{bubbles:true}))})()"); W(150)
    T('Members: search filters the list', E("[...document.querySelectorAll('#gpBox [data-pane=members] .member-row')].filter(r=>r.style.display!=='none').length") == 1)
    E("(()=>{const i=document.querySelector('#gpBox .gp-msearch');i.value='';i.dispatchEvent(new Event('input',{bubbles:true}))})()")
    uid = E("(()=>{const b=[...document.querySelectorAll('#gpBox [data-pane=members] [data-gpa=conn]')].find(b=>b.classList.contains('btn-join'));return b?+b.dataset.uid:0})()")
    if uid:
        C(f"#gpBox [data-pane=members] [data-gpa=conn][data-uid=\"{uid}\"]"); W(300)
        T('Members: Connect sends a request and the group stays open', E(f"CONN_STATE[{uid}]") == 'pending' and E("document.getElementById('groupDetail').classList.contains('show')"))
        sweep()
    tab('about'); sweep()
    T('About: description, rules, type, privacy, created and admins', E("(()=>{const a=document.querySelector('#gpBox [data-pane=about]');const t=dxOrigText(a);return a.querySelectorAll('.gp-rules li').length>=3&&/Deal Room/.test(t)&&/Public/.test(t)&&/Created/.test(t)&&/2021/.test(t)&&a.querySelectorAll('.member-row').length>=1&&t.includes('active pharmaceutical ingredients')})()"))
    tab('listings'); sweep()
    T('Listings (deal room): RFQs and offers with the marketplace cards', E("document.querySelectorAll('#gpBox [data-pane=listings] .dcard').length>=1 && document.querySelectorAll('#gpBox [data-pane=listings] .lcard').length>=1"))
    T('the marketplace card styles apply inside the group (cards have padding and a border)', E("(()=>{const c=document.querySelector('#gpBox .lcard .lc-inner')||document.querySelector('#gpBox .lcard');const s=getComputedStyle(c);return parseFloat(s.paddingTop)>0||parseFloat(getComputedStyle(document.querySelector('#gpBox .lcard')).borderTopWidth)>0})()"))
    lid = E("(()=>{const b=document.querySelector('#gpBox [data-pane=listings] [data-gpl=quote]:not([disabled])');return b?b.closest('[data-lid]').dataset.lid:null})()")
    C(f"#gpBox [data-lid=\"{lid}\"] [data-gpl=quote]"); W(300); sweep()
    pg.fill('#gpQp', '$5.30/kg CIF Alexandria'); pg.fill('#gpQl', '3 weeks')
    confirm(); W(400)
    T('Quote: sending a quote marks the request as quoted', E(f"document.querySelector('#gpBox [data-lid=\"{lid}\"] [data-gpl=quote]').disabled"))
    C("#gpBox [data-gpa=newlisting]"); W(300); sweep()
    E("document.getElementById('gpLk').value='surplus'"); pg.fill('#gpLt', 'Lactose monohydrate 200 mesh — 1.2 MT'); pg.fill('#gpLd', 'Sealed bags, expiry 08/2027, CoA available'); pg.fill('#gpLp', '$1.90/kg')
    confirm(); W(400)
    T('Listings: posting a surplus offer adds it to the group', E("document.querySelector('#gpBox [data-pane=listings]').textContent.includes('Lactose monohydrate 200 mesh')"))
    close()

    # 4 · public group you are not in: preview, Join, Leave
    t = 'QA/QC Professionals'
    cnt0 = E(f"parseInt(dxOrigText({card(t)}.querySelector('.member-count')).replace(/,/g,''))")
    open_card(t)
    T('not a member of a public group: read-only preview with Join, no composer', E("!!document.querySelector('#gpBox .gp-gate [data-gpa=join]') && !document.querySelector('#gpBox .gp-comp') && document.querySelectorAll('#gpBox .gp-posts .post').length>0"))
    sweep()
    p0 = first_free_post()
    C(f"#gpBox [data-gpp=\"{p0}\"] .pact[id^=like-] [data-gpm=react]"); W(250)
    T('a non-member cannot react (asked to join instead)', not E(f"document.querySelector('#gpBox [data-gpp=\"{p0}\"] .pact[id^=like-]').classList.contains('liked')"))
    C("#gpBox .gp-gate [data-gpa=join]"); W(400)
    T('Join inside the group: composer appears, header shows Leave', E("!!document.querySelector('#gpBox .gp-comp') && document.querySelector('#memberActions [data-gpj]').dataset.gpj==='leave'"))
    T('…and the card shows ✓ Joined with one more member', E(f"{card(t)}.querySelector('.gcard-btn').classList.contains('btn-joined')") and E(f"parseInt(dxOrigText({card(t)}.querySelector('.member-count')).replace(/,/g,''))") == cnt0 + 1)
    C("#memberActions [data-gpj]"); W(250)
    T('Leave asks first (the approved confirmation)', E("document.getElementById('leaveConfirm').classList.contains('show')"))
    sweep()
    C("#leaveConfirm .cp-btn-confirm"); W(400)
    T('Leave: the group closes and the card shows + Join again', not E("document.getElementById('groupDetail').classList.contains('show')") and E(f"{card(t)}.querySelector('.gcard-btn').classList.contains('btn-join')"))
    E(f"{card(t)}.querySelector('.gcard-btn').click()"); W(300)
    open_card(t)
    T('Join from the card: inside, you are a member', cur().get('member') is True and E("!!document.querySelector('#gpBox .gp-comp')"))
    close()

    # 5 · private group you are not in: Request to join → pending; invitation → accept
    t = 'Pharmacovigilance Egypt'
    T('a private group you are not in shows "Request" on its card', E(f"{card(t)}.querySelector('.gcard-btn').dataset.gpq") == 'request')
    open_card(t)
    T('private group: no posts, a lock with "Request to join"', E("!!document.querySelector('#gpBox .gp-lock [data-gpa=request]') && !document.querySelector('#gpBox .gp-posts .post')"))
    sweep()
    tab('members'); sweep()
    # J-COMMUNITY-03: an outsider sees no member list; the admins are shown under About
    T('private group: no member list, the admins are shown under About', E("(()=>{const r=document.querySelectorAll('#gpBox [data-pane=members] .member-row');return r.length===0&&!!document.querySelector('#gpBox [data-pane=members] .gp-more')})()"))
    tab('about')
    T('private group: About lists the admins', E("(()=>{const r=[...document.querySelectorAll('#gpBox [data-pane=about] .member-row')];return r.length>=1&&r.every(x=>x.querySelector('.rp-admin,.rp-subadmin'))})()"))
    T('private group: About is visible (rules and privacy)', E("document.querySelectorAll('#gpBox [data-pane=about] .gp-rules li').length>=3 && /Private/.test(dxOrigText(document.querySelector('#gpBox [data-pane=about]')))"))
    tab('disc')
    C("#gpBox [data-gpa=request]"); W(400)
    T('Request to join: the request is pending (inside and on the card)', E("!!document.querySelector('#gpBox [data-gpa=cancel]')") and E(f"{card(t)}.querySelector('.gcard-btn').dataset.gpq") == 'pending' and E("document.querySelector('#memberActions [data-gpj]').dataset.gpj") == 'pending')
    sweep(); close()
    t2 = 'Sterile Manufacturing Leaders'
    T('an invitation shows on its card (✉️ Accept)', E(f"{card(t2)}.querySelector('.gcard-btn').dataset.gpq") == 'accept' and E(f"!!{card(t2)}.querySelector('.why-banner')"))
    open_card(t2)
    T('invited: the group says so and offers Accept invitation', E("!!document.querySelector('#gpBox .gp-lock [data-gpa=accept]')"))
    sweep()
    C("#gpBox [data-gpa=accept]"); W(400)
    T('Accept invitation: you are a member and see the posts', cur().get('member') is True and E("document.querySelectorAll('#gpBox .gp-posts .post').length") >= 2)
    close()

    # 6 · admin tools in your own group
    open_card('Regulatory Affairs Egypt')
    T('admin: Manage Group in the header', E("getComputedStyle(document.getElementById('adminActions')).display!=='none'"))
    pid2 = E("(()=>{const l=[...document.querySelectorAll('#gpBox .gp-posts .post')];const x=l.find(p=>!dxOrigText(p).includes('📌 Pinned'));return x.getAttribute('data-gpp')})()")
    T('admin: each post menu has Pin and Remove post', E(f"!!document.querySelector('#gpBox [data-gpp=\"{pid2}\"] [data-gpm=pin]') && !!document.querySelector('#gpBox [data-gpp=\"{pid2}\"] [data-gpm=remove]')"))
    C(f"#gpBox [data-gpp=\"{pid2}\"] [data-gpm=pin]"); W(350)
    T('admin: Pin moves the post to the top', E("document.querySelector('#gpBox .gp-posts .post').getAttribute('data-gpp')") == pid2)
    E("toggleManage()"); W(250); sweep()
    T('admin: the Manage panel lists this group\'s members with roles', E("document.querySelectorAll('#tab-members .member-list .member-row .role-pill').length") >= 4)
    E("toggleManage()"); close()

    # 6b · a group you create opens with its inside too
    E("openCreate()"); W(250)
    pg.fill('#createModal .field-input', 'Biosimilars Egypt'); pg.fill('#createModal .field-textarea', 'Biosimilar development, comparability and EDA registration.')
    E("document.querySelector('#createModal .modal-footer .btn-create').click()"); W(500)
    open_card('Biosimilars Egypt')
    T('a group you create: you are its admin, it is empty with the composer, and About shows its description', cur().get('role') == 'admin' and E("!!document.querySelector('#gpBox .gp-comp') && !!document.querySelector('#gpBox .gp-empty')"))
    C("#gpBox .gp-comp .comp-btn"); W(300)
    pg.fill('.modal-bg[data-gpk] #postBody', 'Welcome — first meeting on comparability protocols next week')
    C(".modal-bg[data-gpk] .btn-p"); W(500)
    T('…and its first post appears', E("document.querySelector('#gpBox .gp-posts').textContent.includes('comparability protocols')"))
    close()

    # 7 · everything you did is still there after a reload
    login()
    open_card('API Sourcing & Supply')
    T('after a reload: your group post is still there', E("document.querySelector('#gpBox .gp-posts').textContent.includes('Azithromycin dihydrate USP')"))
    T('after a reload: your comment and your like are still there', E(f"document.querySelector('#gpBox [data-gpp=\"{seed}\"]').textContent.includes('very useful for our Q1 plan')") and E(f"document.querySelector('#gpBox [data-gpp=\"{pid}\"] .pact[id^=like-]').classList.contains('liked')"))
    tab('listings')
    T('after a reload: your quote and your listing are still there', E(f"document.querySelector('#gpBox [data-lid=\"{lid}\"] [data-gpl=quote]').disabled") and E("document.querySelector('#gpBox [data-pane=listings]').textContent.includes('Lactose monohydrate 200 mesh')"))
    close()
    T('after a reload: joined, requested and accepted groups keep their state', E(f"{card('QA/QC Professionals')}.querySelector('.gcard-btn').classList.contains('btn-joined')") and E(f"{card('Pharmacovigilance Egypt')}.querySelector('.gcard-btn').dataset.gpq") == 'pending' and E(f"{card('Sterile Manufacturing Leaders')}.querySelector('.gcard-btn').classList.contains('btn-joined')"))
    open_card('Biosimilars Egypt')
    T('after a reload: the group you created and its post are still there', E("document.querySelector('#gpBox .gp-posts').textContent.includes('comparability protocols')"))
    close()
    open_card('Regulatory Affairs Egypt')
    T('after a reload: the pinned post stays on top', E("document.querySelector('#gpBox .gp-posts .post').getAttribute('data-gpp')") == pid2)
    pg.keyboard.press('Escape'); W(300)
    T('Escape closes the group', not E("document.getElementById('groupDetail').classList.contains('show')"))
    open_card('Pharmacovigilance Egypt')
    C("#gpBox [data-gpa=cancel]"); W(300)
    confirm(); W(350)
    T('a pending request can be cancelled', E(f"{card('Pharmacovigilance Egypt')}.querySelector('.gcard-btn').dataset.gpq") == 'request')
    close()

    # 8 · Message from the members list goes to Messages
    open_card('API Sourcing & Supply'); tab('members')
    C("#gpBox [data-pane=members] [data-gpa=msg]"); W(700)
    T('Message (members list) opens Messages', E("document.body.getAttribute('data-page')") == 'messages')

    # 9 · phone width
    pg.set_viewport_size({'width': 390, 'height': 844}); E("goto('groups')"); W(600)
    open_card('API Sourcing & Supply'); W(300)
    T('390 px: the group opens with its tabs and posts, nothing wider than the screen', E("(()=>{const d=document.querySelector('#gpBox');const r=d.getBoundingClientRect();const posts=[...document.querySelectorAll('#gpBox .post')];return r.width<=391&&posts.length>0&&posts.every(p=>p.getBoundingClientRect().right<=391)&&document.documentElement.scrollWidth<=391})()"))
    for n in ('members', 'about', 'listings'):
        tab(n)
        ok = E("(()=>{const p=document.querySelector('#gpBox [data-pane]:not([hidden])');return [...p.querySelectorAll('*')].every(e=>e.getBoundingClientRect().right<=392||e.closest('.gp-tabs'))})()")
        T(f'390 px: {n} fits the screen', ok)
    sweep()
    close()

    if AR:
        if untr: print('untranslated:', ' | '.join(sorted(untr)))
        T('Arabic: no untranslated interface text inside a group, its windows and notices', not untr, len(untr))
    T('no errors in the page', not errs, errs)
    print(LANG, sum(R), '/', len(R)); b.close()
sys.exit(0 if R and all(R) else 1)
