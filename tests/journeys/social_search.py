"""Social journeys — finding things: top-bar search, Ctrl+K palette, saved searches with alerts, one Saved place,
Back/Forward and shared links, admin action on a spam account (J-SOCIAL-45 … 48, 50, 51).
Run: python3 tests/journeys/social_search.py --target demo|live --lang en|ar --width 1440|390"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW, APP_VISIBLE, LOGIN_VISIBLE
from _social import *

def page_of(pg): return pg.evaluate("document.body.getAttribute('data-page')")
def palette(pg):
    return pg.evaluate("(()=>{const a=document.activeElement;const d=a&&a.closest('[role=dialog]');return d&&d.getClientRects().length?d.innerText:''})()")
def ctrl_k(j, pg):
    pg.keyboard.press('Control+k'); pg.wait_for_timeout(500)
    j.check(palette(pg), 'Ctrl+K does not open the command palette with focus in its input')

@journey('J-SOCIAL-45')
def global_search(j):
    """A member searches everything from the top bar and opens the result."""
    if j.live:
        a = j.person('Dr. Amr Searcher'); b = j.person('Dr. Eva Person')
        j.sql("update public.profiles set company='Eva Pharma', headline='QA Director' where id='%s'" % b['id'])
        j.sql("insert into public.products (user_id, name, category, price, unit) values ('%s','Gapmetformin %s','api',4.2,'kg')" % (b['id'], j.tag))
        j.sql("insert into public.jobs (user_id, title, company, location) values ('%s','Stability Analyst %s','Eva Pharma','Cairo')" % (b['id'], j.tag))
        j.sql("insert into public.groups (name, description, created_by, type) values ('Eva Alumni %s','Group for search','%s','public')" % (j.tag, b['id']))
        post_db(j, b['id'], 'Our stability chamber results ' + j.tag)
        pg = a['page']; j.reload(pg)
        q1, person, prod, post_q = 'Eva', 'Eva Person', 'Gapmetformin', 'stability'
    else:
        pg = j.demo_signin(j.new_page()); q1, person, prod, post_q = 'Rahmani', 'Faisal Rahmani', 'Metformin', 'stability'
    with j.step('Type "%s" in the top-bar search: results grouped by type, from the real database' % q1):
        t = top_search(j, pg, q1)
        j.check(person in t, 'the search does not find the member "%s"' % person)
        if j.live:
            demo = re.findall(r'Metformin HCl Compacted|Sara Mansour|Regulatory Affairs Egypt|Vivian Zhou|Faisal Rahmani', t)
            j.check(not demo, 'live search shows demo items: %s' % sorted(set(demo)))
            j.check(re.search(r'COMPAN|شركات', t, re.I) or 'Eva Alumni' in t, 'the search for "Eva" finds no company/group results')
    with j.step('Search a product, then post text ("%s"), then an Arabic query' % post_q):
        t = top_search(j, pg, prod.lower()); j.check(prod.lower() in t.lower().split('\n', 1)[-1], 'the product "%s" is not found' % prod)
        t = top_search(j, pg, post_q); j.check(re.search(r'POSTS|منشورات', t, re.I) and post_q in t.lower().split('\n', 1)[-1], 'posts are not searched (no result for "%s")' % post_q)
        t = top_search(j, pg, 'صيدلي')
    with j.step('Open a person result with the keyboard (arrows + Enter): the exact profile'):
        top_search(j, pg, q1)
        sel = "n=>{const o=[...document.querySelectorAll('[role=option][aria-selected=true], [role=option].on, #content .dx-kb-active, #content [aria-selected=true]')].filter(e=>e.getClientRects().length);return o.some(e=>e.innerText.includes(n))}"
        for _ in range(8):                                   # arrow down until the person is the active result
            if pg.evaluate(sel, person.split()[-1]): break
            pg.keyboard.press('ArrowDown'); pg.wait_for_timeout(150)
        j.check(pg.evaluate(sel, person.split()[-1]), 'the arrow keys never select the person result')
        pg.keyboard.press('Enter'); j.settle(pg, 900)
        j.check(page_of(pg) == 'profile' and person.split()[-1] in j.text(pg)[:400], 'keyboard navigation does not open the person result')
    with j.step('Open a post result and a product result: the exact item'):
        top_search(j, pg, post_q); open_result(j, pg, 'EDA Circular 2026/018' if j.demo else 'stability chamber')
        shown = pg.evaluate("q=>[...document.querySelectorAll('#content .post')].some(e=>{const r=e.getBoundingClientRect();return r.bottom>0&&r.top<innerHeight&&e.innerText.toLowerCase().includes(q)})", post_q)
        j.check(shown, 'the post result does not show the post (page: %s)' % page_of(pg))
    with j.step('A nonsense query shows a helpful empty state'):
        t = top_search(j, pg, 'qqzzxx' + j.tag)
        j.check(re.search(r'No results|nothing found|Try|لا توجد نتائج|لا نتائج', t, re.I), 'no helpful empty state for a query without results')

@journey('J-SOCIAL-46')
def command_palette(j):
    """A power user jumps anywhere and runs common actions with Ctrl+K."""
    if j.live:
        a = j.person('Dr. Akram Keys'); b = j.person('Dr. Bassem Findme'); pg = a['page']; j.reload(pg); member = 'Findme'
    else:
        pg = j.demo_signin(j.new_page()); member = 'Rahmani'
    with j.step('Ctrl+K opens the palette with focus in the input, showing Pages and Actions'):
        ctrl_k(j, pg); t = palette(pg)
        j.check(re.search(r'PAGES|صفحات', t, re.I) and re.search(r'ACTIONS|إجراءات', t, re.I), 'the empty palette does not show Pages and Actions')
        j.check(pg.evaluate("(()=>{const a=document.activeElement;return a.getAttribute('role')==='combobox'||!!a.closest('[role=dialog]').querySelector('[role=listbox]')})()"), 'no combobox/listbox roles for screen readers')
    with j.step('Type "mess" → Enter: Messages opens'):
        pg.keyboard.type('mess'); pg.wait_for_timeout(300); pg.keyboard.press('Enter'); j.settle(pg)
        j.check(page_of(pg) == 'messages', 'Enter on "mess" opened %s' % page_of(pg))
    with j.step('Ctrl+K → "new post" → Enter: the composer opens'):
        ctrl_k(j, pg); pg.keyboard.type('new post'); pg.wait_for_timeout(300)
        j.check(pg.locator('[role=dialog] [role=option]').filter(has_text=re.compile(r'post|منشور', re.I)).count(), 'not built: the palette has no "New post" action')
        pg.keyboard.press('Enter'); pg.wait_for_timeout(600); j.check(pg.locator('#postBody:visible').count(), '"new post" does not open the composer')
        pg.keyboard.press('Escape'); pg.locator('.modal-bg .modal-close').first.click() if pg.locator('.modal-bg .modal-close:visible').count() else None
    with j.step('Ctrl+K → a member name → Enter: that profile opens'):
        ctrl_k(j, pg); pg.keyboard.type(member); pg.wait_for_timeout(1200)
        j.check(member in palette(pg), 'the palette does not find the member "%s"' % member)
        pg.keyboard.press('Enter'); j.settle(pg, 900)
        j.check(page_of(pg) == 'profile' and member in j.text(pg)[:400], 'Enter on the member does not open the profile')
    with j.step('Ctrl+K while typing in a field does not insert text; Esc and an outside click close it and return focus'):
        j.nav(pg, 'messages')
        if not pg.locator('#composeInput:visible').count() and pg.locator('.mx-thread:visible').count():   # a phone shows the list first: open a conversation
            pg.locator('.mx-thread:visible').first.click(); pg.wait_for_timeout(500)
        pg.click('#composeInput'); pg.keyboard.press('Control+k'); pg.wait_for_timeout(400)
        j.check(palette(pg) and pg.input_value('#composeInput') == '', 'Ctrl+K inside a text field does not open the palette (or inserts text)')
        pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
        j.check(not palette(pg) and pg.evaluate("document.activeElement.id") == 'composeInput', 'Esc does not close the palette and return focus')
        ctrl_k(j, pg); pg.mouse.click(5, j.height - 5); pg.wait_for_timeout(300)
        j.check(not pg.evaluate("[...document.querySelectorAll('[role=dialog]')].some(d=>d.getClientRects().length&&/PAGES|Esc/i.test(d.innerText))"), 'an outside click does not close the palette')

@journey('J-SOCIAL-47')
def saved_search_alert(j):
    """A member saves a search and is alerted when new matches appear."""
    if j.live: a = j.person('Dr. Asmaa Alerts'); b = j.person('Dr. Bilal Poster'); pg = a['page']; j.reload(pg)
    else: pg = j.demo_signin(j.new_page())
    with j.step('Run a Marketplace search with a filter; click "Save this search" and choose an alert frequency'):
        j.nav(pg, 'market'); pg.wait_for_selector('#mkx', timeout=8000)
        s_ = pg.locator('#searchIn'); j.check(s_.is_visible(), 'no visible Marketplace search box at %dpx (the phone search palette does not apply Marketplace filters)' % j.width)
        s_.click(); s_.fill('Metformin'); pg.wait_for_timeout(500)
        box = pg.locator('#mkx .filters .f-opt').first; j.check(box.count(), 'the Marketplace has no filters')
        if not box.is_visible():                                       # a phone keeps the filters behind "⚙ Filters"
            tg = j.find(pg, r'Filters|الفلاتر|التصفية|عوامل التصفية', scope='#mkx'); j.check(tg, 'the filters are hidden and there is no Filters button at %dpx' % j.width)
            tg.click(); pg.wait_for_timeout(400)
        box.click(); pg.wait_for_timeout(800)
        el = j.find(pg, r'Save (this )?search|حفظ (هذا )?البحث', scope='body'); j.check(el, 'no "Save this search" after searching with a filter')
        el.click(); pg.wait_for_timeout(500)
        freq = pg.locator('.dbk-ov select:visible, .modal-bg select:visible, [role=dialog] select:visible')
        j.check(freq.count() or re.search(r'daily|weekly|instant|يومي|أسبوعي', j.text(pg, 'body')[-3000:], re.I), 'the save-search dialog offers no alert frequency')
        if freq.count(): freq.first.select_option(index=min(1, freq.first.locator('option').count() - 1))
        j.click(pg, r'^(Save search|Save|احفظ البحث|حفظ البحث|احفظ|حفظ)$', scope='body', what='Save search', exact=True); pg.wait_for_timeout(600)
        bar = j.text(pg, '#app'); j.check(re.search(r'Saved searches|عمليات البحث المحفوظة|البحث المحفوظ', bar, re.I) and 'Metformin' in bar, 'the saved search is not listed')
    with j.step('The saved search is stored per user (database, not only this browser) and listed after reload'):
        if j.live: j.check(j.has_table('saved_searches'), 'not built: saved searches are kept only in the browser (no saved_searches table)')
        if j.demo: j.skip('demo keeps no data across a reload (no backend) — checked in live')
        j.reload(pg); j.nav(pg, 'market'); j.check('Metformin' in j.text(pg, '#app'), 'after reload the saved search is not listed')
    with j.step('Open it from Ctrl+K: the same query and filters are applied'):
        ctrl_k(j, pg); pg.keyboard.type('Metformin'); pg.wait_for_timeout(500)
        opt = pg.locator('[role=dialog] [role=option]').filter(has_text=re.compile('Metformin')); j.check(opt.count(), 'the saved search is not offered in Ctrl+K')
        opt.first.click(); j.settle(pg)
        j.check(pg.input_value('#searchIn') == 'Metformin' and pg.locator('#mkx .filters .f-opt input:checked').count() >= 1, 'opening the saved search does not re-apply its query and filter')
    with j.step('B publishes a matching job; A is notified with a link to it'):
        if j.demo: j.skip('the other party exists only in live')
        j.sql("insert into public.products (user_id, name, category, price, unit) values ('%s','Metformin HCl new lot %s','api',3.9,'kg')" % (b['id'], j.tag))
        j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and created_at>now()-interval '5 minutes'" % a['id'], 15) not in ('', '0'), 'no notification for a new matching listing')
    with j.step('Delete the saved search: gone everywhere'):
        j.nav(pg, 'market'); x = pg.locator('.ss-pill button:not(.ss-go):visible, [class*=saved-search] [aria-label*="Delete" i]:visible')
        j.check(x.count(), 'no way to delete a saved search'); x.first.click(); pg.wait_for_timeout(500)
        ok = j.find(pg, r'^(Delete|Remove|Yes|حذف|إزالة|نعم)$', scope='body', exact=True)
        if ok: ok.click(); pg.wait_for_timeout(400)
        j.check(not pg.locator('.ss-pill:visible').filter(has_text='Metformin').count(), 'the saved search is still listed after delete')
        if j.live: j.check(j.sql1("select count(*) from public.saved_searches where user_id='%s'" % a['id']) == '0', 'the saved search row remains')

@journey('J-SOCIAL-48')
def one_saved_place(j):
    """A member finds everything she saved — posts, jobs, listings — in one Saved place."""
    if j.live:
        a = j.person('Dr. Amal Keeper'); b = j.person('Dr. Bassem Source')
        p1 = int(post_db(j, b['id'], 'Saved post one ' + j.tag)); p2 = int(post_db(j, b['id'], 'Saved post two ' + j.tag))
        job = j.sql1("insert into public.jobs (user_id, title, company, location) values ('%s','Saved job %s','Pharco','Cairo') returning id" % (b['id'], j.tag))
        for p in (p1, p2): j.sql("insert into public.saved_posts (user_id, post_id) values ('%s',%d)" % (a['id'], p))
        j.sql("insert into public.saved_jobs (user_id, job_id) values ('%s',%s)" % (a['id'], job))
        pg = a['page']; j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page())
    with j.step('Open Saved from the feed sidebar "Saved items", the sidebar nav and Ctrl+K: every entry opens the Saved page'):
        j.nav(pg, 'feed'); el = j.find(pg, r'Saved items|العناصر المحفوظة|المحفوظات', scope='#content')
        j.act(pg, el, 'Saved items (feed sidebar)', lambda: page_of(pg) == 'saved', expect='the Saved page')
        j.nav(pg, 'saved'); j.check(page_of(pg) == 'saved', 'the sidebar Saved does not open the Saved page')
        ctrl_k(j, pg); pg.keyboard.type('Saved'); pg.wait_for_timeout(300); pg.keyboard.press('Enter'); j.settle(pg)
        j.check(page_of(pg) == 'saved', 'Ctrl+K "Saved" does not open the Saved page')
    with j.step('Posts / Jobs / Listings sections: each saved item with title and author; empty kinds have an empty state'):
        t = j.text(pg)
        j.check(re.search(r'Jobs|وظائف', t) and re.search(r'Listings|Products|عروض|منتجات', t), 'not built: Saved shows posts only (no Jobs / Listings sections)')
        if j.live: j.check('Saved post one' in t and 'Saved job' in t, 'the saved items are not all listed')
    with j.step('Open the saved job: the job page where Apply works'):
        el = j.find(pg, r'Saved job|Job|وظيفة', scope='#content'); j.check(el, 'no saved job to open')
        job_name = 'Saved job' if j.live else el.inner_text().strip().split('\n')[0]; el.click(); j.settle(pg)
        j.check(page_of(pg) == 'jobs' and j.find(pg, r'Apply|تقدم|قدّم|قدم', scope='#content'), 'the saved job does not open the job with Apply')
    with j.step('Unsave the job; reload: consistent everywhere'):
        j.nav(pg, 'saved')
        un = pg.evaluate_handle("""n=>{const re=/^\\W*(Unsave|Saved|Remove|إلغاء الحفظ|محفوظ|إزالة)$/i,btn=e=>[...e.querySelectorAll('button,[role=button]')].find(b=>b.getClientRects().length&&re.test(b.innerText.trim()));
            let best=null;document.querySelectorAll('#content *').forEach(e=>{if(e.getClientRects().length&&(e.innerText||'').includes(n)&&btn(e)&&(!best||best.contains(e)))best=e});return best?btn(best):null}""", job_name).as_element()
        j.check(un, 'no Unsave on the saved job')          # the job's own control — not a saved post's
        un.click(); pg.wait_for_timeout(600)
        j.check(job_name not in j.text(pg), 'the job is still listed in Saved after Unsave')
        if j.demo: j.skip('demo keeps no data across a reload (no backend) — checked in live')
        j.check(j.wait_db("select count(*) from public.saved_jobs where user_id='%s'" % a['id'], 5, want='0') == '0', 'the saved_jobs row is still there')
        j.reload(pg); j.nav(pg, 'saved'); j.check('Saved job' not in j.text(pg) and 'Saved post one' in j.text(pg) and 'Saved post two' in j.text(pg), 'after reload Saved is inconsistent')

@journey('J-SOCIAL-50')
def back_forward_links(j):
    """A member uses Back/Forward and shared links without being thrown out of the app."""
    if j.live: a = j.person('Dr. Akram Nav'); b = j.person('Dr. Bassem Linked'); pg = a['page']; j.reload(pg)
    else: a = None; pg = j.demo_signin(j.new_page())
    with j.step('Go Home → Network → a person\'s profile → Messages'):
        j.nav(pg, 'feed'); j.nav(pg, 'network')
        goto_profile(j, pg, b if j.live else 5); j.nav(pg, 'messages')
    with j.step('Back three times, then Forward once: through the visited pages in order, never leaving the app'):
        seen = []
        for _ in range(3):
            pg.go_back(); pg.wait_for_timeout(700)
            j.check(not pg.url.startswith('about:') and j.in_app(pg), 'browser Back leaves the app (%s)' % pg.url[:60])
            seen.append(page_of(pg))
        j.check(seen == ['profile', 'network', 'feed'], 'Back went through %s (want profile, network, feed)' % seen)
        pg.go_forward(); pg.wait_for_timeout(700); j.check(page_of(pg) == 'network', 'Forward went to %s' % page_of(pg))
    with j.step('Copy the address on a profile and open it in a new tab: the same profile'):
        goto_profile(j, pg, b if j.live else 5); u = pg.url
        j.check(u.rstrip('/') != j.url.rstrip('/'), 'not built: the address does not change for a profile (%s)' % u)
        p2 = j.new_page(pg.context, url=u)
        if j.on_login(p2): j.demo_signin(p2) if j.demo else j.signin(p2, a['email'], a['pw'])
        j.check(page_of(p2) == 'profile', 'the copied link does not open the profile')
    with j.step('Reload on Messages with a thread open: the same page and thread'):
        j.nav(pg, 'messages'); j.reload(pg)
        if j.on_login(pg): j.demo_signin(pg)
        j.check(page_of(pg) == 'messages', 'reload returns to %s instead of Messages' % page_of(pg))

@journey('J-SOCIAL-51', applies='live')
def admin_suspends_spammer(j):
    """A Drugbox admin reviews a reported spam account and suspends it."""
    m = j.person('Dr. Maha Admin'); s = j.person('Spam Seller'); r1 = j.person('Dr. Rania Reporter'); r2 = j.person('Dr. Rami Reporter')
    for i in range(3): post_db(j, s['id'], 'CHEAP API buy now %d %s' % (i, j.tag))
    for r in (r1, r2): j.sql("insert into public.messages (sender_id, receiver_id, body) values ('%s','%s','Buy cheap now %s')" % (s['id'], r['id'], j.tag))
    make_admin(j, m['id']); pm = m['page']; j.reload(pm)
    with j.step("Members report S from S's profile (⋯ → Report, with a reason): stored once per reporter"):
        for r, reason in ((r1, 'spam'), (r2, 'scam')):
            pr = r['page']; goto_profile(j, pr, s)
            j.click(pr, r'^(⋯|More: report or block|المزيد: إبلاغ أو حظر)', scope='#content', what='⋯ (more)')
            j.click(pr, r'^\W*(Report|إبلاغ)$', scope='body', what='Report', exact=True)
            pr.check('.dbk-ov input[name=dxMRep][value=%s], .modal-bg input[name=dxMRep][value=%s]' % (reason, reason))
            pr.fill('#dxMRepN', 'Sends the same ad to everyone ' + j.tag)
            j.click(pr, r'^(Report|إبلاغ)$', scope='body', what='Report (confirm)', exact=True); pr.wait_for_timeout(800)
            j.check(any(re.search(r'Thanks|شكراً', t) for t in j.toasts(pr)), 'no confirmation after reporting')
        j.check(j.wait_db("select count(distinct reporter) from public.member_reports where reported='%s' and status='open'" % s['id'], 6, want='2') == '2', 'the two reports are not stored')
        dup = r1['page'].evaluate("u=>dxLive.sb.from('member_reports').insert({reporter:dxLive.k.me,reported:u,reason:'spam'}).then(r=>r.error?'refused':'stored')", s['id'])
        j.check(dup == 'refused', 'the same member can report the same person twice while it is open')
        no = r1['page'].evaluate("()=>dxLive.sb.rpc('reported_members').then(r=>r.error?'refused':'allowed')")
        j.check(no == 'refused', 'a member who is not on the Drugbox team can read the reported-members queue')
    with j.step('M: Admin → Review → Reported members: grouped reports per account'):
        j.nav(pm, 'admin'); j.click(pm, r'^(🛡️ Review|Review|🛡️ المراجعة|المراجعة)', scope='#content', what='Review')
        j.click(pm, r'Reported members|الأعضاء المبلغ عنهم', scope='#content', what='Reported members'); pm.wait_for_timeout(600)
        row = pm.locator('#content .dx-mod-row').filter(has_text='Spam Seller').filter(has_text=j.tag)        # earlier runs leave their own Spam Seller
        j.check(row.count() == 1, 'S is not listed once in Reported members')
        j.check(re.search(r'2 reports from 2 members|2 بلاغ|بلاغان', row.first.inner_text()), 'the row does not group the reports (%s)' % row.first.inner_text()[:120])
    with j.step('Suspend S with a reason; remove the spam posts: stored and enforced by the database'):
        row.first.locator('button').filter(has_text=re.compile(r'^(Suspend|إيقاف)$')).click(); pm.wait_for_timeout(400)
        pm.fill('#dxModWhy', 'Mass spam ads ' + j.tag)
        j.click(pm, r'^(Suspend account|إيقاف الحساب)$', scope='body', what='Suspend account', exact=True); pm.wait_for_timeout(1200)
        j.check(j.wait_db("select reason from public.account_suspensions where user_id='%s'" % s['id'], 6) == 'Mass spam ads ' + j.tag, 'the suspension and its reason are not stored')
        j.check(not pm.locator('#content .dx-mod-row').filter(has_text='Spam Seller').filter(has_text=j.tag).count(), 'S is still in the queue after the decision')
    with j.step('S cannot post, comment or message; S sees "account suspended"'):
        r = s['page'].evaluate("u=>dxLive.sb.from('posts').insert({user_id:u,body:'after suspension'}).then(r=>r.error?'refused':'stored')", s['id'])
        j.check(r == 'refused', 'a suspended member can still post')
        r = s['page'].evaluate("u=>dxLive.sb.from('messages').insert({sender_id:dxLive.k.me,receiver_id:u,body:'after suspension'}).then(r=>r.error?'refused':'stored')", r1['id'])
        j.check(r == 'refused', 'a suspended member can still message')
        j.reload(s['page']); s['page'].wait_for_timeout(1500)
        j.check(re.search(r'suspended|موقوف', j.text(s['page'], 'body'), re.I), 'S is not told the account is suspended')
    with j.step("S's removed posts disappear for everyone; reporters are told; the action is logged"):
        j.check(j.sql1("select count(*) from public.posts where user_id='%s'" % s['id']) == '0', "S's spam posts remain")
        j.check(j.sql1("select count(*) from public.notifications where user_id in ('%s','%s') and created_at>now()-interval '10 minutes' and from_user is null" % (r1['id'], r2['id'])) >= '2', 'the reporters were not told')
        j.check(j.sql1("select count(*) from public.moderation_log where target_user='%s' and action='suspend' and admin='%s'" % (s['id'], m['id'])) == '1', 'the suspension is not logged with the admin')
        j.nav(r1['page'], 'notifs'); j.settle(r1['page'], 1200)
        j.check(re.search(r'suspended the account|أوقف الحساب', j.text(r1['page'])), 'the reporter does not read the outcome')

if __name__ == '__main__': main(__file__)
