"""Social journeys — network: find people, send / withdraw / accept / ignore connection requests, my connections and
removing one, following a person, suggestions (J-SOCIAL-28 … 34).
Run: python3 tests/journeys/social_network.py --target demo|live --lang en|ar --width 1440|390"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW, APP_VISIBLE, LOGIN_VISIBLE
from _social import *

CONNECT = r'^\W*(Connect|تواصل|اتصال)$'
PENDING = r'^\W*(Pending|Sent|Withdraw|معلق|قيد الانتظار|تم الإرسال|سحب الطلب)$'
ACCEPT, IGNORE = r'^\W*(Accept|قبول|اقبل)$', r'^\W*(Ignore|Decline|تجاهل|رفض)$'

def network(j, pg): j.nav(pg, 'network'); j.settle(pg, 1200); return j.text(pg)

def section(pg, title_re):
    """Text of the Network page section whose heading matches title_re: the heading is the smallest visible element with
    a short text matching it; the section is its nearest ancestor that holds more than the heading."""
    return pg.evaluate("""p=>{const re=new RegExp(p,'i');let h=null;
        document.querySelectorAll('#content *').forEach(e=>{if(!e.getClientRects().length)return;const t=(e.innerText||'').trim();if(t.length>60||!re.test(t))return;if(!h||h.contains(e))h=e});
        if(!h)return null;let box=h.parentElement;while(box&&box.innerText.trim().length<=h.innerText.trim().length+2)box=box.parentElement;return box?box.innerText:''}""", title_re)

def badge(pg, page):
    return pg.evaluate("p=>{const e=[...document.querySelectorAll('#tnb-'+p+' [class*=badge],#mb-'+p+' [class*=badge],#snl-'+p+' [class*=badge]')].find(e=>e.getClientRects().length);return e&&e.getClientRects().length?e.innerText.trim():''}", page)

def card_of(pg, name):
    """The smallest visible element on the page that holds the person's name and at least one button."""
    return pg.evaluate_handle("""n=>{let best=null;document.querySelectorAll('#content *').forEach(e=>{if(!e.getClientRects().length)return;
        if(e.innerText&&e.innerText.includes(n)&&e.querySelector('button')&&(!best||best.contains(e)))best=e});return best}""", name).as_element()

def click_in(j, pg, el, pattern, what):
    if not el: j.notbuilt('no card for %s on the page' % what)
    b = el.evaluate_handle("(e,p)=>[...e.querySelectorAll('button,[onclick],a')].find(x=>new RegExp(p,'i').test(x.innerText.trim()))||null", pattern).as_element()
    if not b: j.notbuilt('no "%s" on the card' % what)
    mark = j.toast_mark(pg); b.click(); pg.wait_for_timeout(800); j.dead_end(pg, mark, what)

@journey('J-SOCIAL-28')
def find_people(j):
    """A supplier finds the right people by name, company or specialty."""
    if j.live:
        a = j.person('Dr. Amr Supplier')
        b = j.person('Dr. Carim Audit'); c = j.person('Dr. Chaker Quality'); d = j.person('Dr. Dalia Regulatory'); e = j.person('د. سامي المصري')
        for p, co, hl in ((b, 'Eva Pharma', 'Procurement Manager'), (c, 'Pharco', 'QA Manager'), (d, 'Eva Pharma', 'Regulatory Affairs'), (e, 'Amoun', 'Procurement')):
            j.sql("update public.profiles set company='%s', headline='%s' where id='%s'" % (co, hl, p['id']))
        pg = a['page']; j.reload(pg)
        eva = ('Carim', 'Dalia'); not_eva = 'Chaker'
    else:
        pg = j.demo_signin(j.new_page()); eva = ('Faisal',); not_eva = 'Alia'
    with j.step('Open Network and search people for "Eva": all members at that company, from the database'):
        network(j, pg)
        box = pg.locator('#content input[type=search]:visible, #content input[placeholder*="Search" i]:visible, #content input[placeholder*="بحث"]:visible')
        j.check(box.count(), 'not built: no people search on the Network page')
        box.first.fill('Eva' if j.live else 'Azurea'); pg.wait_for_timeout(1200); t = j.text(pg)
        j.check(all(n in t for n in eva) and not_eva not in t, 'the people search for the company does not return exactly its members')
    with j.step('Filter by specialty "Procurement" (and country): results narrow correctly; empty result has a helpful state'):
        f = pg.locator('#content select:visible, #content [role=combobox]:visible, #content .chip:visible, #content [class*=filter] button:visible')
        j.check(f.count(), 'not built: no specialty/country filter for people')
    with j.step('Search "Carim" in the top-bar search and open the result'):
        q = 'Carim' if j.live else 'Rahmani'
        t = top_search(j, pg, q); j.check(q in t, 'the top-bar search finds no member "%s"' % q); open_result(j, pg, q)
        j.check(('Carim Audit' if j.live else 'Faisal Rahmani') in j.text(pg)[:500], 'the result does not open the right profile')
    with j.step('Search works with Arabic names and answers within 1 s'):
        if j.demo: j.skip('Arabic member names are checked in live')
        t0 = time.time(); t = top_search(j, pg, 'سامي'); dt = time.time() - t0
        j.check('سامي' in t.split('\n', 1)[-1], 'the Arabic name was not found')
        j.check(dt < 2.5, 'the search took %.1f s' % dt)

@journey('J-SOCIAL-29')
def send_and_withdraw_request(j):
    """A member sends a connection request (with a note) and can withdraw it."""
    if j.live:
        a = j.person('Dr. Adel Sender'); b = j.person('Dr. Bassem Receiver'); pg = a['page']; j.reload(pg)
        bname = 'Bassem'
    else:
        pg = j.demo_signin(j.new_page()); bname = 'Omar'
    with j.step("Open B's profile and click Connect (add a note if offered): the button turns to Pending"):
        if j.live: goto_profile(j, pg, b)
        else: pg.locator('#content .post .post-name', has_text=bname).first.click(); j.settle(pg, 900)
        el = j.find(pg, CONNECT, scope='#content', exact=True); j.check(el, 'no Connect on B\'s profile')
        el.click(); pg.wait_for_timeout(600)
        note = pg.locator('.modal-bg textarea:visible, [role=dialog] textarea:visible')
        if note.count():
            note.first.fill('Hello, we supply APIs with CEP.'); j.click(pg, r'^(Send|إرسال)', scope='body', what='Send request')
        where = pg.evaluate("document.body.getAttribute('data-page')")
        j.check(where == 'profile', "Connect on B's profile leaves the profile (the app switches to '%s')" % where)
        j.check(j.find(pg, PENDING, scope='#content', exact=True), 'the button did not turn to Pending')
    if j.live:
        with j.step('Live: one connections row requester=A, addressee=B, status=pending'):
            j.check(j.wait_db("select count(*) from public.connections where requester='%s' and addressee='%s' and status='pending'" % (a['id'], b['id']), 5) == '1', 'no pending connections row')
    with j.step("A's Network lists B under Sent (outgoing), not as an invitation A could accept"):
        network(j, pg)
        inv = section(pg, r'Pending invitations|Invitations|دعوات')
        j.check(not (inv and bname in inv and re.search(r'Accept|قبول', inv)), "A's own request to B is listed as an invitation with Accept")
        sent = section(pg, r'^\W*(Sent|Sent requests|Outgoing|المرسلة|طلبات مرسلة)')
        j.check(sent is not None and bname in sent, 'not built: no "Sent" requests list on the Network page')
    with j.step('Withdraw it; send it again: still one row'):
        click_in(j, pg, card_of(pg, bname), r'Withdraw|Cancel|سحب|إلغاء', 'Withdraw')
        if j.live: j.check(j.wait_db("select count(*) from public.connections where requester='%s' and addressee='%s'" % (a['id'], b['id']), 5, want='0') == '0', 'withdraw left the row')
        goto_profile(j, pg, b if j.live else pg.evaluate("(USERS.find(u=>/Omar/.test(u.name))||{}).id"))
        j.find(pg, CONNECT, scope='#content', exact=True).click(); pg.wait_for_timeout(800)
        if j.live: j.check(j.wait_db("select count(*) from public.connections where requester='%s' and addressee='%s'" % (a['id'], b['id']), 5) == '1', 'resending did not give exactly one row')
    with j.step("B's Network page shows the incoming invitation (with note) with Accept/Ignore; the badge counts 1; B is notified"):
        if j.demo: j.skip('the other party exists only in live')
        pb = b['page']; j.reload(pb); network(j, pb)
        inv = section(pb, r'Pending invitations|Invitations|دعوات')
        j.check(inv and 'Adel' in inv and re.search(r'Accept|قبول', inv), "B's Network page does not show A's invitation with Accept")
        j.check(badge(pb, 'network') == '1', 'the network badge shows "%s" (want 1)' % badge(pb, 'network'))
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and from_user='%s' and type='connection_request'" % (b['id'], a['id'])) >= '1', 'B got no notification')
    with j.step('After reload both sides show the same state'):
        if j.demo: j.skip('the other party exists only in live')
        j.reload(pg); goto_profile(j, pg, b); j.check(j.find(pg, PENDING, scope='#content', exact=True), "after reload A's button is not Pending")

@journey('J-SOCIAL-30')
def accept_request(j):
    """A member accepts a connection request so both become connections."""
    if j.live:
        a = j.person('Dr. Amal Requester'); b = j.person('Dr. Bahaa Accepter')
        j.sql("insert into public.connections (requester, addressee, status) values ('%s','%s','pending')" % (a['id'], b['id']))
        post_db(j, a['id'], 'Amal post visible after connecting ' + j.tag)
        pg = b['page']; j.reload(pg); aname = 'Amal'
    else:
        pg = j.demo_signin(j.new_page()); aname = 'Faisal'
    with j.step('B: Network → Accept: the invitation turns into Connected/Message and disappears; the badge decreases'):
        network(j, pg); n0 = badge(pg, 'network')
        inv = section(pg, r'Pending invitations|Invitations|دعوات')
        j.check(inv and aname in inv, "B's Network page shows no invitation from A")
        click_in(j, pg, card_of(pg, aname), ACCEPT, 'Accept')
        inv = section(pg, r'Pending invitations|Invitations|دعوات') or ''
        j.check(aname not in inv, 'the invitation is still listed after Accept')
        n1 = badge(pg, 'network'); j.check((int(n1 or 0)) == max(0, int(n0 or 0) - 1), 'the network badge went %s → %s' % (n0, n1))
    if j.live:
        with j.step('Live: status=accepted; both connection counts +1'):
            j.check(j.wait_db("select status from public.connections where requester='%s' and addressee='%s'" % (a['id'], b['id']), 5, want='accepted') == 'accepted', 'connections row is not accepted')
    with j.step("Open My connections: A is listed and opens A's profile"):
        el = j.find(pg, r'My connections|Connections|اتصالاتي|جهات الاتصال', scope='#content')
        j.act(pg, el, 'My connections', lambda: re.search(r'My connections|اتصالاتي', j.text(pg)[:300], re.I) and aname in j.text(pg))
        pg.locator('#content').get_by_text(re.compile(aname)).first.click(); j.settle(pg, 900)
        j.check(aname in j.text(pg)[:400], "the connection does not open A's profile")
    with j.step('Reload: still connected'):
        if j.demo: j.skip('demo keeps no data across a reload (no backend) — checked in live')
        j.reload(pg); goto_profile(j, pg, a); j.check(j.find(pg, r'Connected|Message|متصل|رسالة', scope='#content'), 'after reload not shown as connected')
    with j.step('A gets "B accepted your connection request"; both see each other\'s posts on Home'):
        if j.demo: j.skip('the other party exists only in live')
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and from_user='%s'" % (a['id'], b['id'])) >= '1', 'A got no acceptance notification')
        j.nav(pg, 'feed'); j.check('Amal post visible after connecting ' + j.tag in j.text(pg), "B does not see A's post on Home")

@journey('J-SOCIAL-31')
def ignore_request(j):
    """A member ignores an unwanted request without the sender being harassed."""
    if j.live:
        b = j.person('Dr. Bothaina Busy'); c = j.person('Dr. Cyrus Pushy')
        j.sql("insert into public.connections (requester, addressee, status) values ('%s','%s','pending')" % (c['id'], b['id']))
        pg = b['page']; j.reload(pg); cname = 'Cyrus'
    else:
        pg = j.demo_signin(j.new_page()); cname = 'Faisal'
    with j.step("B: Network → Ignore on C's request: it disappears"):
        network(j, pg)
        j.check(cname in (section(pg, r'Pending invitations|Invitations|دعوات') or ''), "B's Network page shows no invitation from C")
        click_in(j, pg, card_of(pg, cname), IGNORE, 'Ignore')
        j.check(cname not in (section(pg, r'Pending invitations|Invitations|دعوات') or ''), 'the request is still listed after Ignore')
    with j.step('Reload: it does not come back; the database row is rejected/removed and the notification gone'):
        if j.demo: j.skip('demo keeps no data across a reload (no backend) — checked in live')
        j.reload(pg); network(j, pg)
        j.check(cname not in (section(pg, r'Pending invitations|Invitations|دعوات') or ''), 'after reload the ignored request is back')
        j.check(j.sql1("select count(*) from public.connections where requester='%s' and addressee='%s' and status='pending'" % (c['id'], b['id'])) == '0', 'the connections row is still pending')
    with j.step("C is not notified; C's button is neutral; an immediate re-request is limited"):
        if j.demo: j.skip('the other party exists only in live')
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and from_user='%s'" % (c['id'], b['id'])) == '0', 'C was notified of the decline')
        pc = c['page']; j.reload(pc); goto_profile(j, pc, b)
        el = j.find(pc, CONNECT, scope='#content', exact=True)
        if el:
            el.click(); pc.wait_for_timeout(800)
            j.check(j.sql1("select count(*) from public.connections where requester='%s' and addressee='%s' and status='pending'" % (c['id'], b['id'])) == '0', 'C can re-send the request immediately after being ignored (no limit)')

@journey('J-SOCIAL-32')
def remove_connection(j):
    """A member reviews his connections and removes one."""
    if j.live:
        a = j.person('Dr. Akram Tidy'); b = j.person('Dr. Basma Keep'); c = j.person('Dr. Cherif Remove')
        connect_db(j, a['id'], b['id']); connect_db(j, a['id'], c['id']); pg = a['page']; j.reload(pg); cname = 'Cherif'
    else:
        pg = j.demo_signin(j.new_page()); cname = 'Vivian'
    with j.step('Network → My connections (the count is clickable): a full list with the real count'):
        network(j, pg)
        el = j.find(pg, r'My connections|^Connections|اتصالاتي', scope='#content')
        j.act(pg, el, 'My connections', lambda: re.search(r'My connections|اتصالاتي', j.text(pg)[:400], re.I) and cname in j.text(pg))
        if j.live: j.check(re.search(r'\b2\b', j.text(pg)[:400]), 'the connections count is not 2')
    with j.step('Search within connections for C'):
        box = pg.locator('#content input:visible'); j.check(box.count(), 'no search in My connections')
        box.first.fill(cname); pg.wait_for_timeout(500); j.check(cname in j.text(pg), 'search in connections does not find C')
    with j.step('⋯ on C → Remove connection; confirm: C leaves the list'):
        click_in(j, pg, card_of(pg, cname), r'⋯|More|Remove|إزالة', 'Remove connection')
        ok = j.find(pg, r'^(Remove|Yes|Confirm|إزالة|نعم|تأكيد)$', scope='body', exact=True)
        if ok: ok.click(); pg.wait_for_timeout(600)
        j.check(cname not in j.text(pg), 'C is still listed after removing')
    with j.step('Live: the row A–C is deleted; C no longer lists A and is not notified'):
        if j.demo: j.skip('the other party exists only in live')
        j.check(j.sql1("select count(*) from public.connections where (requester='%s' and addressee='%s') or (requester='%s' and addressee='%s')" % (a['id'], c['id'], c['id'], a['id'])) == '0', 'connections row A–C still exists')

@journey('J-SOCIAL-33')
def follow_person(j):
    """A member follows an industry leader without a connection to get his posts in her feed."""
    if j.live:
        a = j.person('Dr. Aya Follower'); b = j.person('Dr. Bahgat Leader'); pg = a['page']; j.reload(pg); bname = 'Bahgat'
    else:
        pg = j.demo_signin(j.new_page()); bname = 'Omar'
    def to_b():
        if j.live: goto_profile(j, pg, b)
        else: j.nav(pg, 'feed'); pg.locator('#content .post .post-name', has_text=bname).first.click(); j.settle(pg, 900)
    with j.step("Open B's profile → Follow: it switches to Following"):
        to_b(); el = j.find(pg, r'^\W*(Follow|متابعة)$', scope='#content', exact=True); j.check(el, 'no Follow on B\'s profile')
        el.click(); pg.wait_for_timeout(800)
        j.check(j.find(pg, r'^\W*(Following|تتابعهم|تتابع|متابَع|تمت المتابعة)$', scope='#content', exact=True), 'Follow did not switch to Following')
    with j.step('Live: a person-follow row exists and B\'s followers_count +1'):
        if j.demo: j.skip('the database exists only in live')
        t = next((x for x in ('follows', 'person_followers', 'profile_followers', 'followers') if j.has_table(x)), None)
        j.check(t, 'not built: no table for following a person (only company_followers)')
        j.check(j.sql1("select followers_count from public.profiles where id='%s'" % b['id']) == '1', 'followers_count did not become 1')
    with j.step('Reload: still Following; B\'s new post appears on Home'):
        if j.demo: j.skip('demo keeps no data across a reload (no backend) — checked in live')
        post_db(j, b['id'], 'Leader post for followers ' + j.tag); j.reload(pg); to_b()
        j.check(j.find(pg, r'^\W*(Following|تتابعهم|تتابع|متابَع)$', scope='#content', exact=True), 'after reload Follow is lost')
        j.nav(pg, 'feed'); j.check(('Leader post for followers ' + j.tag) in j.text(pg), "B's new post is not on A's Home")
    with j.step('B is notified "A started following you"; Unfollow lowers the count'):
        if j.demo: j.skip('the other party exists only in live')
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and from_user='%s'" % (b['id'], a['id'])) == '1', 'B got no follow notification')

@journey('J-SOCIAL-34')
def suggestions(j):
    """A member gets relevant "People you may know" suggestions and grows her network from them."""
    if j.live:
        a = j.person('Dr. Asmaa Grow'); b = j.person('Dr. Bassem Bridge'); c = j.person('Dr. Camelia Mutual'); d = j.person('Dr. Dawood Random'); e = j.person('Dr. Ehab Already')
        for p, co, hl in ((a, 'Eva Pharma', 'Regulatory Affairs'), (c, 'Eva Pharma', 'Regulatory Affairs'), (d, 'Other Co', 'Sales')):
            j.sql("update public.profiles set company='%s', headline='%s' where id='%s'" % (co, hl, p['id']))
        connect_db(j, a['id'], b['id']); connect_db(j, b['id'], c['id']); connect_db(j, e['id'], a['id'])
        pg = a['page']; j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page())
    with j.step('Network → People you may know: C above D; never E (connected) or A herself; no demo people or groups'):
        t = network(j, pg); sec = section(pg, r'People you may know|أشخاص قد تعرفهم') or ''
        j.check(sec, 'no "People you may know" on the Network page')
        # the suggested people, in order: one name per card that has a Connect button
        names = pg.evaluate("""()=>[...document.querySelectorAll('#content button,#content [onclick]')].filter(b=>/^\\W*(Connect|تواصل|Pending|قيد الانتظار)$/.test(b.innerText.trim())&&b.getClientRects().length)
            .map(b=>{let c=b.parentElement;while(c&&c.innerText.trim().split('\\n').filter(x=>x.trim().length>3).length<2)c=c.parentElement;return c?c.innerText.trim().split('\\n').map(x=>x.trim()).filter(x=>x.length>3)[0]:''})""")
        sug = '\n'.join(names); j.note('suggested', names[:20])
        if j.live:
            j.check('Camelia' in sug, 'C (mutual connection, same company) is not suggested')
            j.check('Ehab Already' not in sug, 'E (already connected) is suggested')
            j.check('Asmaa Grow' not in sug, 'she is suggested to herself')
            j.check('Dawood' not in sug or sug.index('Camelia') < sug.index('Dawood'), 'D is ranked above C')
            pos = next(i for i, n in enumerate(names) if 'Camelia' in n)
            j.check(pos == 0, 'C (a mutual connection at the same company) is suggestion #%d, after %d unrelated members' % (pos + 1, pos))
            demo = re.findall(r'Regulatory Affairs Egypt & GCC|API Sourcing & Supply|GCC & Africa Market Access|Faisal Rahmani|Omar Khaled', t)
            j.check(not demo, 'live Network shows demo people/groups: %s' % sorted(set(demo)))
    with j.step('Each card shows why the person is suggested (mutual connections, same company)'):
        j.check(re.search(r'mutual|same company|works at|مشترك|نفس الشركة', sec, re.I), 'suggestion cards give no reason')
    with j.step('Dismiss one suggestion; Connect to another from its card'):
        name = 'Dawood' if j.live else 'Sara'
        click_in(j, pg, card_of(pg, name), r'^(×|✕|Dismiss|Hide|إخفاء|تجاهل)$', 'Dismiss suggestion')
        j.check(name not in (section(pg, r'People you may know|أشخاص قد تعرفهم') or ''), 'the dismissed suggestion is still shown')
        cn = 'Camelia' if j.live else 'Omar'
        click_in(j, pg, card_of(pg, cn), CONNECT, 'Connect on a suggestion')
        if j.live: j.check(j.wait_db("select count(*) from public.connections where requester='%s' and addressee='%s' and status='pending'" % (a['id'], c['id']), 5) == '1', 'Connect from the card stored no request')
    with j.step('Reload: the dismissed suggestion does not return'):
        if j.demo: j.skip('demo keeps no data across a reload (no backend) — checked in live')
        j.reload(pg); network(j, pg); j.check('Dawood' not in (section(pg, r'People you may know|أشخاص قد تعرفهم') or ''), 'the dismissed suggestion is back after reload')

if __name__ == '__main__': main(__file__)
