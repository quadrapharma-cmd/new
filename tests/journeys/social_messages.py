"""Social journeys — messages: start a conversation from a profile and from ✎ New message, attachments, read receipts,
search, mute/block/report (J-SOCIAL-35 … 40). Run: python3 tests/journeys/social_messages.py --target demo|live --lang en|ar --width 1440|390"""
import re, sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW, APP_VISIBLE, LOGIN_VISIBLE, StepFail
from _social import *
import _dx

def head(pg): return pg.evaluate("(document.querySelector('#content .chat-head')||{}).innerText||''")
def mine(pg): return pg.eval_on_selector_all('#messagesArea .msg-row.mx-mine', 'e=>e.map(x=>x.innerText)')
def theirs(pg): return pg.eval_on_selector_all('#messagesArea .msg-row.mx-theirs', 'e=>e.map(x=>x.innerText)')
def threads(pg): return pg.eval_on_selector_all('#threadList .mx-thread', 'e=>e.map(x=>({key:x.dataset.person||"",text:x.innerText,unread:x.classList.contains("mx-unread"),active:x.classList.contains("active"),visible:x.getClientRects().length>0}))')
def msg_badge(pg):
    return pg.evaluate("(()=>{const e=[...document.querySelectorAll('#tnb-messages [class*=badge],#mb-messages [class*=badge],#snl-messages [class*=badge]')].find(e=>e.getClientRects().length);return e&&e.getClientRects().length?e.innerText.trim():''})()")
def send(j, pg, text):
    pg.fill('#composeInput', text); pg.press('#composeInput', 'Enter'); pg.wait_for_timeout(900)
def to_list(j, pg):
    """On a phone an open conversation covers the list: go back to it with the header's ←."""
    on_screen = pg.evaluate("[...document.querySelectorAll('#threadList .mx-thread')].some(e=>{const r=e.getBoundingClientRect();return r.width>1&&r.right>0&&r.left<innerWidth&&r.top<innerHeight})")
    if not on_screen:
        b = j.find(pg, r'←|→|Back|رجوع|العودة', scope='#content .chat-head')
        if b: b.click(); pg.wait_for_timeout(500)
def open_thread(j, pg, name):
    to_list(j, pg)
    t = pg.locator('#threadList .mx-thread', has_text=name)
    j.check(t.count(), 'no conversation with %s in the list' % name); t.first.click(); j.settle(pg, 900)
def demo_person(pg, needle): return pg.evaluate("n=>(USERS.find(u=>u.name.indexOf(n)>=0)||{}).id", needle)
def menu_btn(pg): return pg.locator('#content .chat-head [onclick*="toggleChatMenu"]:visible, #content .chat-head [aria-label*="More" i]:visible').first
def menu(j, pg, pattern, what):
    if not pg.locator('.ch-dd-item:visible, [role=menuitem]:visible').count():
        b = menu_btn(pg); j.check(b.count(), 'not built: no ⋯ menu in the conversation header'); b.click(); pg.wait_for_timeout(300)
    el = j.find(pg, pattern, scope='body', kinds='.ch-dd-item,[role=menuitem],button')
    if not el: j.notbuilt('no "%s" in the conversation menu' % what)
    return el

@journey('J-SOCIAL-35')
def message_from_profile(j):
    """A supplier starts a private conversation from the buyer's profile and the buyer receives it."""
    text = 'Hello Dr. Carim, we can supply Metformin HCl BP with CEP ' + j.tag
    if j.live:
        a = j.person('Dr. Amr Supplier'); b = j.person('Dr. Carim Buyer'); c = j.person('Dr. Chadi Third')
        pg = a['page']; j.reload(pg); bname = 'Carim'
        pb = b['page']; j.reload(pb); j.nav(pb, 'feed')
    else:
        pg = j.demo_signin(j.new_page()); bname = 'Omar'
    with j.step("Open B's profile → Message: Messages opens on a thread with B (header: name, headline, company)"):
        j.nav(pg, 'messages'); j.nav(pg, 'feed')                        # a previously open thread exists (it must not be reused)
        goto_profile(j, pg, b if j.live else demo_person(pg, bname))
        j.click(pg, r'Message|رسالة|راسل', scope='#content', what='Message')
        j.check(pg.evaluate("document.body.getAttribute('data-page')") == 'messages', 'Message does not open Messages')
        j.check(bname in head(pg), 'the open thread is not with B (header: "%s")' % head(pg)[:80])
    with j.step('Type the message and press Enter: it shows as mine'):
        send(j, pg, text); j.check(any(text in m for m in mine(pg)), 'the message is not shown as sent')
    if j.live:
        with j.step('Live: one messages row A→B; nobody else can read it (RLS)'):
            j.check(j.wait_db("select count(*) from public.messages where sender_id='%s' and receiver_id='%s' and body=$q$%s$q$" % (a['id'], b['id'], text), 5) == '1', 'no messages row from A to B')
            n = c['page'].evaluate("t=>dxLive.sb.from('messages').select('id').eq('body',t).then(r=>(r.data||[]).length)", text)
            j.check(n == 0, 'a third member can read the message (%s rows)' % n)
    with j.step("B, without reloading: the Messages badge increases within seconds; the thread is on top with A's name and preview"):
        if j.demo: j.skip('the other party exists only in live')
        got = j.wait(pb, "(()=>{const e=[...document.querySelectorAll('#tnb-messages [class*=badge],#mb-messages [class*=badge]')].find(e=>e.getClientRects().length);return e&&e.getClientRects().length&&+e.innerText.trim()>=1})()", 30)
        j.check(got, "B's Messages badge did not increase within 30 s without reload")
        j.nav(pb, 'messages'); th = threads(pb)
        j.check(th and 'Amr' in th[0]['text'] and 'Metformin' in th[0]['text'], "A's thread is not on top of B's list with a preview")
    with j.step('B replies; A sees the reply without reloading, on the other side'):
        if j.demo: j.skip('the other party exists only in live')
        open_thread(j, pb, 'Amr'); send(j, pb, 'Thanks, please send the CEP ' + j.tag)
        j.check(j.wait(pg, "t=>[...document.querySelectorAll('#messagesArea .msg-row.mx-theirs')].some(e=>e.innerText.includes(t))", 30, arg='please send the CEP ' + j.tag), "A does not see B's reply within 30 s")
    with j.step('Both reload: the full history in order'):
        if j.demo: j.skip('demo keeps no data across a reload (no backend) — checked in live')
        for p, other in ((pg, 'Carim'), (pb, 'Amr')):
            j.reload(p); j.nav(p, 'messages'); open_thread(j, p, other)
            t = j.text(p, '#messagesArea'); j.check(t.find('Metformin HCl BP') >= 0 and t.find('Metformin HCl BP') < t.find('please send the CEP'), 'after reload the history is missing or out of order')

@journey('J-SOCIAL-36')
def new_message_to_named_person(j):
    """A member starts a new conversation from Messages by choosing a recipient by name; it goes to that person only."""
    if j.live:
        a = j.person('Dr. Aya Writer'); b = j.person('Dr. Carim Audit'); c = j.person('Dr. Chaker Open')
        j.sql("insert into public.messages (sender_id, receiver_id, body) values ('%s','%s','Earlier thread with Chaker %s')" % (c['id'], a['id'], j.tag))
        # real members carry their company; it is what tells two people with the same name apart in the picker (a shared
        # test database holds a "Dr. Carim Audit" from every earlier run)
        bco = 'Audit Labs ' + j.tag; j.sql("update public.profiles set company='%s' where id='%s'" % (bco, b['id']))
        pg = a['page']; j.reload(pg); cname, bname, bfull = 'Chaker', 'Carim', 'Dr. Carim Audit'
    else:
        pg = j.demo_signin(j.new_page()); cname, bname, bfull = 'Vivian', 'Omar', 'Eng. Omar Khaled'
    text = 'Price list for Q4 ' + j.tag
    with j.step('Open Messages and the thread with C'):
        j.nav(pg, 'messages'); open_thread(j, pg, cname)
    with j.step('Click ✎; type "%s" in To: real members are suggested (no demo names in live)' % bname[:3]):
        to_list(j, pg); j.click(pg, r'✎|New message|رسالة جديدة', scope='#content', what='✎ New message')
        to = pg.locator('#nmTo:visible, .dbk-ov input:visible, .modal-bg input:visible').first
        j.check(to.count(), 'New message has no To field'); to.fill(bname[:3]); pg.wait_for_timeout(1000)
        opts = pg.evaluate("(()=>{const i=document.querySelector('#nmTo');const l=i&&i.list;return l?[...l.options].map(o=>o.value):[]})()")
        ui = pg.eval_on_selector_all('.dbk-ov [role=option], .dbk-ov li, .modal-bg [role=option]', 'e=>e.filter(x=>x.getClientRects().length).map(x=>x.innerText)')
        sugg = opts + ui; j.note('suggestions', sugg[:10])
        j.check(any(bname in s for s in sugg), 'the recipient picker does not suggest %s (suggestions: %s)' % (bfull, sugg[:6]))
        if j.live:
            demo = [s for s in sugg if re.search(r'Vivian|Omar Khaled|Alia Mourad|Rahmani|Indovista|SkinBio', s)]
            j.check(not demo, 'the picker suggests demo people: %s' % demo[:4])
    with j.step('Pick B, write and send: the message goes to B only (not the previously open thread)'):
        to.fill(bfull); pg.wait_for_timeout(800)
        if j.live:      # choose B's suggestion, as a person does when several members share the name (the option shows the company)
            opts = [o for o in pg.evaluate("(()=>{const i=document.querySelector('#nmTo');const l=i&&i.list;return l?[...l.options].map(o=>o.value):[]})()") if o.startswith(bfull)]
            if len(opts) > 1: to.fill(next((o for o in opts if bco in o), bfull + ' · ' + bco))
        pg.locator('#nmTx:visible, .dbk-ov textarea:visible').first.fill(text)
        j.click(pg, r'^(Send|إرسال)$', scope='.dbk-ov', what='Send', exact=True); j.settle(pg, 1200)
        j.check(bname in head(pg), 'after sending, the open thread is not with B (header: "%s")' % head(pg)[:60])
        open_thread(j, pg, cname); j.check(not any(text in m for m in mine(pg)), 'the new message landed in the thread with C')
        if j.live:
            got = j.wait_db("select receiver_id from public.messages where sender_id='%s' and body=$q$%s$q$" % (a['id'], text), 6)
            j.check(got == b['id'], 'the message was stored for the wrong person (receiver %s, B is %s, C is %s)' % (got, b['id'], c['id']))
    with j.step('A name that is not a member cannot be sent to (clear message)'):
        to_list(j, pg); j.click(pg, r'✎|New message|رسالة جديدة', scope='#content', what='✎ New message')
        pg.locator('#nmTo:visible, .dbk-ov input:visible').first.fill('Nobody Unknownperson'); pg.locator('#nmTx:visible, .dbk-ov textarea:visible').first.fill('should not send ' + j.tag)
        mark = j.toast_mark(pg); j.click(pg, r'^(Send|إرسال)$', scope='.dbk-ov', what='Send', exact=True); pg.wait_for_timeout(800)
        msg = ' '.join(j.toasts_since(pg, mark)) + ' ' + j.text(pg, '.dbk-ov')
        j.check(re.search(r'not (a )?member|no one|not found|choose|لا يوجد|غير موجود|اختر', msg, re.I), 'sending to an unknown name gives no clear message')
        j.check(not re.search(r'Nobody Unknownperson', head(pg)), 'a thread was opened with an unknown name')
        if j.live: j.check(j.sql1("select count(*) from public.messages where body like 'should not send %s'" % j.tag) == '0', 'a message to an unknown name was stored')
    with j.step('Sign-up refuses a name with characters that are not letters or that mix alphabets (U+FFFC, a Cyrillic а, a Cyrillic word '
                'that reads as Latin, Chinese letters, a dot standing alone), saying what to change; real names (Arabic with harakat, '
                'titles written "د/", a Latin title on a Cyrillic name, pasted hyphens, accents, apostrophes, brackets) sign up fine'):
        if j.demo: j.skip('the name rule is the database\'s and the live app\'s (the demo keeps its sample people)')
        def ui_signup(name):
            p2 = j.new_page(j.new_ctx()); j.open(p2); p2.click('#loginPage [onclick="showSignup()"]'); p2.wait_for_selector('#suName', state='visible', timeout=5000)
            email = j.email('names'); p2.fill('#suName', name); p2.fill('#suEmail', email); p2.fill('#suPw', PW)
            p2.click('#signupPage button.f-btn.dx-js-only'); p2.wait_for_timeout(1500)
            return p2, email, j.text(p2, '#suErr')
        for name, pat in (('Dr. Zeina Sign %s￼' % j.tag, r'remove “￼” \(U\+FFFC\)|احذف «￼» \(U\+FFFC\)'),
                          ('Dr. Rаna Sign %s' % j.tag, r'one alphabet — “Rаna”|بأبجدية واحدة — «Rаna»'),
                          ('Dr. \u0405\u0430\u04cf\u0456\u04bb Sign %s' % j.tag, r'“\u0405\u0430\u04cf\u0456\u04bb” can be read as a Latin word|«\u0405\u0430\u04cf\u0456\u04bb» يمكن أن تُقرأ ككلمة لاتينية'),
                          ('张伟 Sign %s' % j.tag, r'Latin, Arabic, Greek or Cyrillic letters — “张”|بحروف عربية أو لاتينية أو يونانية أو سيريلية — «张»'),
                          ('د . أحمد %s' % j.tag, r'“\.” is not a word|«\.» ليست كلمة')):
            p2, email, err = ui_signup(name)
            j.check(re.search(pat, err), 'sign-up as %s is not refused with a clear message (said: "%s")' % (ascii(name), err[:140]))
            j.check(j.ar == bool(re.search('[ء-ي]', err.replace(name, ''))), 'the refusal is not in the interface language: "%s"' % err[:100])   # Arabic words (the English one lists the comma ،)
            j.check(j.sql1("select count(*) from auth.users where email='%s'" % email) == '0', 'an account was created for %s' % ascii(name))
        # through the form, as a person signs up: an Arabic name with harakat, and a name with brackets, dots and a hyphen
        for name, stored in (('د. نرمين أبو زيدٍ %s' % j.tag, None), ('Al-Hassan (Pharm.D.) %s' % j.tag, None), ('د/ هيثم دويدار %s' % j.tag, None),
                             ('Dr. Мария Иванова %s' % j.tag, None), ('Anne\u2011Marie O\'Brien %s' % j.tag, 'Anne-Marie O’Brien %s' % j.tag)):
            me2 = j.person(name)
            j.check(j.sql1("select name || '|' || name_needs_fix from public.profiles where id='%s'" % me2['id']) == (stored or name) + '|false', 'the real name %s was not stored as typed' % name)
        # and the others the owner listed, through the sign-up trigger
        for name in ('د. هالة الشامي %s', 'Dr. Ahmed El-Sayed %s', "O'Brien %s", 'José Müller %s', 'Ünal %s', 'مُحَمَّد عَبْدُ اللَّه %s', 'O’Brien %s',
                     'م/ محمود %s', 'Мария Иванова (Maria Ivanova) %s', 'د. أحمد علي، صيدلي %s'):
            uid = j.sql1("insert into auth.users (email, raw_user_meta_data) values ('%s', jsonb_build_object('name', $q$%s$q$)) returning id" % (j.email('real'), name % j.tag))
            want = (name % j.tag).replace("'", '’')            # the apostrophe is stored as ’, the way the app shows it (0039)
            j.check(j.sql1("select (name = $q$%s$q$ and not name_needs_fix)::text from public.profiles where id='%s'" % (want, uid)) == 'true', 'the real name %s did not sign up as typed' % (name % j.tag))
    with j.step('Look-alike members (same name + same company; same name, no company, same headline): every option is different, '
                'the connection comes first, each option sends to its own person only, and the bare shared name is refused'):
        if j.demo: j.skip('look-alike members exist only in live (the demo has one sample person per name)')
        def member(name, company=None, headline=None):   # a precondition: a member made by the sign-up trigger (handle_new_user)
            meta = {'name': name}
            if company: meta['company'] = company
            if headline: meta['specialty'] = headline
            return j.sql1("insert into auth.users (email, raw_user_meta_data) values ('%s', $m$%s$m$::jsonb) returning id" % (j.email('twin'), json.dumps(meta)))
        def new_message(to_value, body):
            to_list(j, pg); j.click(pg, r'✎|New message|رسالة جديدة', scope='#content', what='✎ New message')
            box = pg.locator('#nmTo:visible').first; box.fill(to_value); pg.wait_for_timeout(1200)
            pg.locator('#nmTx:visible').first.fill(body)
            mark = j.toast_mark(pg); j.click(pg, r'^(Send|إرسال)$', scope='.dbk-ov', what='Send', exact=True); j.settle(pg, 1500)
            return ' '.join(j.toasts_since(pg, mark))
        LBL = {}
        def options_for(name, also=()):
            to_list(j, pg); j.click(pg, r'✎|New message|رسالة جديدة', scope='#content', what='✎ New message')
            pg.locator('#nmTo:visible').first.fill(name); pg.wait_for_timeout(1500)
            ol = pg.evaluate("(()=>{const i=document.querySelector('#nmTo');const l=i&&i.list;return l?[...l.options].map(o=>[o.value,o.label||'']):[]})()")
            LBL.update(dict(ol)); o = [x for x, _ in ol if any(x.lower().startswith(n.lower()) for n in (name,) + tuple(also))]
            pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
            if pg.locator('.dbk-ov:visible').count(): j.click(pg, r'^(Cancel|إلغاء|×|✕)$', scope='.dbk-ov', what='Cancel', exact=True)
            return o
        lname, nname = 'Dr. Lina Twin %s' % j.tag, 'Dr. Nour Same %s' % j.tag
        co = 'Twin Pharma %s' % j.tag
        l1, l2 = member(lname, co), member(lname, co)                                   # same name AND same company
        n1, n2 = member(nname, None, 'Regulatory Affairs'), member(nname, None, 'Regulatory Affairs')   # same name, no company, same headline
        connect_db(j, a['id'], l2)                                                      # one of the twins is A's connection
        j.reload(pg); j.nav(pg, 'messages')
        for name, pair, conn in ((lname, (l1, l2), l2), (nname, (n1, n2), None)):
            opts = options_for(name); j.note('look-alike options ' + name[:14], opts)
            j.check(len(opts) == 2 and len(set(o.lower() for o in opts)) == 2, 'the picker does not offer two different options for the two members called %s: %s' % (name, opts))
            j.check(all(o.strip().lower() != name.lower() for o in opts), 'an option is the bare shared name (it fits both): %s' % opts)
            if conn:
                j.check(re.search(r'connection|اتصال', opts[0], re.I) and not re.search(r'connection|اتصال', opts[1], re.I), 'the connection is not marked and listed first: %s' % opts)
            got = []
            for i, o in enumerate(opts):
                body = 'Look-alike %d %s %s' % (i, name.split()[1], j.tag)
                said = new_message(o, body)
                rows = j.wait_db("select string_agg(receiver_id::text, ',') from public.messages where sender_id='%s' and body=$q$%s$q$" % (a['id'], body), 6)
                j.check(rows and ',' not in rows and rows in pair, 'option "%s" was stored for %s, not for exactly one of the two members (toasts: %s)' % (o, rows or 'nobody', said[:100]))
                got.append(rows)
                if conn and i == 0: j.check(rows == conn, 'the option marked as your connection went to the other member')
            j.check(set(got) == set(pair), 'the two options reached the same member (%s) — one of them was a guess' % got)
            # typing the shared name without choosing: refused, nothing stored
            body = 'Bare name %s %s' % (name.split()[1], j.tag); said = new_message(name, body)
            j.check(re.search(r'Several|أكثر من', said), 'typing a name two members share is not refused with a clear message (toasts: %s)' % said[:120])
            j.check(j.sql1("select count(*) from public.messages where body=$q$%s$q$" % body) == '0', 'a message to a name two members share was stored')
            if pg.locator('.dbk-ov:visible').count(): j.click(pg, r'^(Cancel|إلغاء|×|✕)$', scope='.dbk-ov', what='Cancel', exact=True)
        # look-alikes a person cannot tell apart. 0038: a name is letters (one script per word), so every look-alike the verifiers
        # used is refused at sign-up — nothing is created; names stored before 0038 that break the rule are kept but flagged, and
        # the picker groups names by their confusable SKELETON: a Cyrillic "Rаna" or a "Zeina￼" is the same name as the real one
        hname, hco = 'Dr. Hala Dup %s' % j.tag, 'Pharco %s' % j.tag
        h1, h2 = member(hname, hco), member(hname, hco)
        def refused(name):
            try: member(name); return False
            except StepFail as e: return bool(re.search(r'A name |Write each word|Write a name|is not a word|can be read as a Latin|accent or vowel', str(e)))
        bad = ['%s · %s' % (hname, hco)] + ['%s %s %s' % (hname, d, hco) for d in ('ꞏ', '⸳', '\U00011174', '\U0001f797', '\U000111d0', '∘', '▪', '￼჉')]
        bad += ['Dr. Zeina Inv %s￼' % j.tag, 'Dr. Rаna Eva %s' % j.tag, 'Dr. Hala Dup %s 2' % j.tag]
        for nm in bad: j.check(refused(nm), 'a member can sign up as %s' % ascii(nm))
        j.check(j.sql1("select count(*) from public.profiles where name like $q$Dr. Hala Dup %s%%$q$" % j.tag) == '2', 'a look-alike of "%s" was stored' % hname)
        zname = 'Dr. Zeina Inv %s' % j.tag; z1, z2, z3 = member(zname), member(zname + '​'), member(zname + '\U0001d173')   # U+1D173: default-ignorable
        j.check(j.sql1("select count(distinct name) from public.profiles where id in ('%s','%s','%s')" % (z1, z2, z3)) == '1', 'a name with an invisible character is stored as a different name')
        # stored before 0038 (a server write keeps a name that breaks the rule, and flags it): a U+FFFC twin of Zeina, a Cyrillic twin of Rana
        rname, rco = 'Dr. Rana Eva %s' % j.tag, 'Eva %s' % j.tag
        r1, r2, z4 = member(rname, rco), member('Dr. Later Named %s' % j.tag, rco), member('Dr. Later Named Z %s' % j.tag)
        j.sql("update public.profiles set name = $q$%s$q$ where id = '%s'" % (rname.replace('Rana', 'Rаna'), r2))
        j.sql("update public.profiles set name = $q$%s$q$ where id = '%s'" % (zname + '￼', z4))
        j.check(j.sql1("select string_agg(name_needs_fix::text, ',' order by name_needs_fix) from public.profiles where id in ('%s','%s')" % (r2, z4)) == 'true,true', 'a name stored before 0038 that breaks the rule is not flagged')
        j.check(j.sql1("select count(distinct name_key) from public.profiles where id in ('%s','%s')" % (r1, r2)) == '1', 'the Cyrillic "Rаna" does not have the skeleton of "Rana"')
        j.reload(pg); j.nav(pg, 'messages')
        opts = options_for(hname); j.note('Hala options', opts)
        canon = [o for o in opts if o.lower().startswith(('%s · %s' % (hname, hco)).lower())]
        j.check(len(canon) == 2 and len(opts) == 2, 'the two Pharco members are not the only options for "%s": %s' % (hname, opts))
        for i, o in enumerate(canon):
            body = 'Hala option %d %s' % (i, j.tag); new_message(o, body)
            got = j.wait_db("select receiver_id from public.messages where sender_id='%s' and body=$q$%s$q$" % (a['id'], body), 6)
            j.check(got in (h1, h2), 'the option "%s" went to %s — not to one of the two Pharco members' % (o, got or 'nobody'))
        labels = [LBL.get(o, '') for o in canon]
        j.check(labels and all(re.search(r'Same name|نفس الاسم', l) for l in labels), 'exact twins carry only a handle — the option does not warn that they look the same: %s' % labels[:2])
        j.check(re.search(r'Pharco', head(pg)) and not re.search(r'Last seen|آخر ظهور', head(pg)), 'after writing to a twin, the chat header does not say who it is (company): "%s"' % head(pg)[:80])
        # the Cyrillic twin (same skeleton): two different options, the flagged one warns, the bare name is refused, the real option reaches the real member
        opts = options_for(rname, (rname.replace('Rana', 'R\u0430na'),)); j.note('Rana options (Latin + Cyrillic)', [ascii(o) for o in opts])
        j.check(len(opts) == 2 and len(set(opts)) == 2 and all(' · ' in o for o in opts), 'the Cyrillic look-alike of "%s" is not told apart in the picker: %s' % (rname, [ascii(o) for o in opts]))
        odd = [o for o in opts if re.search(r'Drugbox does not allow|لا يسمح بها Drugbox', LBL.get(o, ''))]
        j.check(len(odd) == 1 and odd[0].startswith(rname.replace('Rana', 'Rаna')), 'the flagged (Cyrillic) name carries no warning: %s' % [ascii(LBL.get(o, '')) for o in opts])
        said = new_message(rname, 'Bare Rana %s' % j.tag)
        j.check(re.search(r'Several|أكثر من', said) and j.sql1("select count(*) from public.messages where body=$q$Bare Rana %s$q$" % j.tag) == '0', 'typing "%s" (a Cyrillic look-alike exists) is not refused: %s' % (rname, said[:120]))
        if pg.locator('.dbk-ov:visible').count(): j.click(pg, r'^(Cancel|إلغاء|×|✕)$', scope='.dbk-ov', what='Cancel', exact=True)
        real = [o for o in opts if o not in odd]; body = 'Real Rana %s' % j.tag
        if real: new_message(real[0], body)
        j.check(real and j.wait_db("select receiver_id from public.messages where sender_id='%s' and body=$q$%s$q$" % (a['id'], body), 6) == r1, 'the real Rana\'s option did not reach her')
        opts = options_for(zname); j.note('invisible twin options', [ascii(o) for o in opts])
        # what a person sees: without the characters that draw nothing (default-ignorable, format, control, U+FFFC)
        vis = set(re.sub('[­͏؜ᅟᅠ឴឵᠋-᠏​-‏‪-‮⁠-⁯ㅤ︀-️﻿ﾠ￼'
                             '\U0001bca0-\U0001bca3\U0001d173-\U0001d17a\U000e0000-\U000e0fff]', '', o).lower() for o in opts)
        j.check(len(opts) == 4 and len(vis) == 4, 'four members whose names look the same are offered as options that look the same: %s' % [ascii(o) for o in opts])
        said = new_message(zname, 'Bare Zeina %s' % j.tag)
        j.check(re.search(r'Several|أكثر من', said) and j.sql1("select count(*) from public.messages where body=$q$Bare Zeina %s$q$" % j.tag) == '0', 'typing a name four members look like is not refused: %s' % said[:120])
        if pg.locator('.dbk-ov:visible').count(): j.click(pg, r'^(Cancel|إلغاء|×|✕)$', scope='.dbk-ov', what='Cancel', exact=True)
        # the profile's Message button writes to that profile's own person (the no-company twin, opened by id)
        goto_profile(j, pg, {'id': n2}); j.click(pg, r'Message|رسالة|راسل', scope='#content', what='Message')
        body = 'From the profile %s' % j.tag; send(j, pg, body)
        j.check(j.wait_db("select receiver_id from public.messages where sender_id='%s' and body=$q$%s$q$" % (a['id'], body), 6) == n2, "the profile's Message button did not write to that profile's person")
    with j.step('Two members with the same name and different companies write first: the list and the chat header say which is '
                'which, and 👤 opens the one whose conversation is open (the profile view is counted on them, not the twin)'):
        if j.demo: j.skip('members with the same name exist only in live (the demo has one sample person per name)')
        def writer(name, company):
            return j.sql1("insert into auth.users (email, raw_user_meta_data) values ('%s', $m$%s$m$::jsonb) returning id" % (j.email('hoda'), json.dumps({'name': name, 'company': company})))
        oname = 'Dr. Hoda Twin %s' % j.tag; oco1, oco2 = 'Alpha Pharma %s' % j.tag, 'Beta Pharma %s' % j.tag
        o1, o2 = writer(oname, oco1), writer(oname, oco2)
        for o, w in ((o1, 'one'), (o2, 'two')):
            j.sql("insert into public.messages (sender_id, receiver_id, body) values ('%s','%s','Hoda %s writes first %s')" % (o, a['id'], w, j.tag))
        j.reload(pg); j.nav(pg, 'messages'); to_list(j, pg)
        rows = [t['text'] for t in threads(pg) if oname in t['text']]; j.note('twin threads', rows)
        j.check(len(rows) == 2 and any(oco1 in r for r in rows) and any(oco2 in r for r in rows), 'two conversations with members called %s do not say which company each is (list: %s)' % (oname, rows))
        t = pg.locator('#threadList .mx-thread', has_text=oco1); j.check(t.count() == 1, 'no conversation that reads %s' % oco1); t.first.click(); j.settle(pg, 900)
        j.check(oco1 in head(pg) and oco2 not in head(pg), "the chat header of Alpha's Dr. Hoda does not say Alpha (header: %s)" % head(pg)[:120])
        v1, v2 = (j.sql1("select profile_views from public.profiles where id='%s'" % o) for o in (o1, o2))
        el = j.find(pg, r'^👤$', scope='#content .chat-head', exact=True); j.check(el, 'no 👤 in the conversation header')
        el.click(); j.settle(pg, 1500)
        j.check(pg.evaluate("document.body.getAttribute('data-page')") == 'profile' and oco1 in j.text(pg, '#content')[:1500] and oco2 not in j.text(pg, '#content')[:1500],
                "👤 in Alpha's Dr. Hoda conversation did not open her profile (page: %s)" % j.text(pg, '#content')[:160])
        j.check(j.wait_db("select profile_views - %s from public.profiles where id='%s'" % (v1, o1), 6) == '1' and j.sql1("select profile_views from public.profiles where id='%s'" % o2) == v2,
                'the profile view was not counted on the member whose conversation was open')
    with j.step('Someone with the same name as a member A never met writes first: the list and the chat header still tell them apart '
                '(the database says the name is shared, the app fetches the other members with it)'):
        if j.demo: j.skip('members with the same name exist only in live (the demo has one sample person per name)')
        fname, fco = 'Dr. Famous Fame %s' % j.tag, 'Real Pharma %s' % j.tag
        real = writer(fname, fco); fake = writer(fname, fco)            # the impostor copies the name and the company
        j.sql("insert into public.messages (sender_id, receiver_id, body) values ('%s','%s','It is me, write back %s')" % (fake, a['id'], j.tag))
        j.check(j.sql1("select count(*) from public.messages where (sender_id='%s' and receiver_id='%s') or (sender_id='%s' and receiver_id='%s')" % (real, a['id'], a['id'], real)) == '0', 'precondition: A has a conversation with the real member')
        j.reload(pg); j.nav(pg, 'messages'); to_list(j, pg)
        rows = [t['text'] for t in threads(pg) if fname in t['text']]; j.note('impostor thread', rows)
        hd = '#' + fake.replace('-', '')[:6]
        j.check(len(rows) == 1 and hd in rows[0], 'the conversation with a member whose name another member has does not say which one it is (no %s; list: %s)' % (hd, rows))
        t = pg.locator('#threadList .mx-thread', has_text=fname); t.first.click(); j.settle(pg, 900)
        j.check(hd in head(pg), 'the chat header does not tell the impostor apart from the real %s (header: %s)' % (fname, head(pg)[:120]))
    with j.step("B receives it; C's thread is unchanged"):
        if j.demo: j.skip('the other party exists only in live')
        pb = b['page']; j.reload(pb); j.nav(pb, 'messages'); open_thread(j, pb, 'Aya')
        j.check(any(text in m for m in theirs(pb)), 'B did not receive the message')

@journey('J-SOCIAL-37')
def attachments(j):
    """A member sends a document and a photo in a conversation; the other side can open them; nobody else can."""
    from PIL import Image
    d = os.path.join(j.cfg['out'], 'fixtures'); os.makedirs(d, exist_ok=True)
    pdf = os.path.join(_dx.FIXTURES, 'spec.pdf'); jpg = os.path.join(d, 'coa-photo.jpg'); Image.new('RGB', (640, 480), (10, 90, 160)).save(jpg)
    if j.live:
        a = j.person('Dr. Alaa Sender'); b = j.person('Dr. Bassem Getter'); c = j.person('Dr. Chadi Snoop')
        j.sql("insert into public.messages (sender_id, receiver_id, body) values ('%s','%s','Please send the CoA %s')" % (b['id'], a['id'], j.tag))
        pg = a['page']; j.reload(pg); bname = 'Bassem'
    else:
        pg = j.demo_signin(j.new_page()); bname = 'Vivian'
    with j.step('In the thread click 📎 and choose the PDF; send: name and size show'):
        j.nav(pg, 'messages'); open_thread(j, pg, bname)
        j.check(pg.locator('#fileInput').count(), 'no 📎 file picker in the conversation')
        with pg.expect_file_chooser(timeout=5000) as fc: j.click(pg, r'📎|Attach file|إرفاق ملف', scope='#content .compose-bar', what='📎')
        fc.value.set_files(pdf); pg.wait_for_timeout(600)
        if not any('spec.pdf' in m for m in mine(pg)): pg.press('#composeInput', 'Enter'); pg.wait_for_timeout(1500)
        last = (mine(pg) or [''])[-1]
        j.check('spec.pdf' in last and re.search(r'\d+\s?(KB|MB|kB|B)\b', last), 'the sent PDF does not show name and size (last: "%s")' % last[:60])
    with j.step('Click 📷 and choose the JPG; send: a thumbnail shows'):
        with pg.expect_file_chooser(timeout=5000) as fc: j.click(pg, r'📷|Attach photo|إرفاق صورة', scope='#content .compose-bar', what='📷')
        fc.value.set_files(jpg); pg.wait_for_timeout(600)
        if not pg.locator('#messagesArea .msg-row.mx-mine img').count(): pg.press('#composeInput', 'Enter'); pg.wait_for_timeout(1500)
        j.check(pg.locator('#messagesArea .msg-row.mx-mine img').count(), 'the photo shows no thumbnail')
    with j.step('Live: files stored in private message-media under <A>/<B>/…; messages rows reference them'):
        if j.demo: j.skip('the database exists only in live')
        n = j.wait_db("select count(*) from storage.objects where bucket_id='message-media' and name like '%s/%s/%%'" % (a['id'], b['id']), 6, want='2')
        j.check(n == '2', '%s objects under message-media/<A>/<B>/ (want 2)' % n)
        path = j.sql1("select name from storage.objects where bucket_id='message-media' and name like '%s/%s/%%' and name like '%%.pdf'" % (a['id'], b['id']))
    with j.step('B opens the thread: sees the image and downloads a PDF identical to the original'):
        if j.demo: j.skip('the other party exists only in live')
        pb = b['page']; j.reload(pb); j.nav(pb, 'messages'); open_thread(j, pb, 'Alaa')
        j.check(j.wait(pb, "[...document.querySelectorAll('#messagesArea .mx-theirs img')].some(i=>i.complete&&i.naturalWidth>10)", 10), 'B does not see the image')
        link = pb.locator('#messagesArea .mx-theirs a', has_text='spec.pdf'); j.check(link.count(), 'B sees no PDF link')
        href = link.first.get_attribute('href'); size = pb.evaluate("u=>fetch(u).then(r=>r.ok?r.arrayBuffer().then(b=>b.byteLength):-r.status)", href)
        j.check(size == os.path.getsize(pdf), 'B downloaded %s bytes, original %d' % (size, os.path.getsize(pdf)))
    with j.step('C and an anonymous visitor get 403/404 on the object'):
        if j.demo: j.skip('the other party exists only in live')
        r = c['page'].evaluate("p=>dxLive.sb.storage.from('message-media').createSignedUrl(p,60).then(r=>r.error?'refused':'signed')", path)
        j.check(r == 'refused', 'C can get a signed link to the PDF')
        st = c['page'].evaluate("u=>fetch(u).then(r=>r.status)", _dx.APP_URL + 'storage/v1/object/public/message-media/' + path)
        j.check(st in (400, 401, 403, 404), 'the private object is readable without a signed link (HTTP %s)' % st)
    with j.step('Too-large or dangerous file types are refused with a message'):
        exe = os.path.join(d, 'invoice.exe'); open(exe, 'wb').write(b'MZ' + os.urandom(2000))
        mark = j.toast_mark(pg)
        with pg.expect_file_chooser(timeout=5000) as fc: j.click(pg, r'📎|Attach file|إرفاق ملف', scope='#content .compose-bar', what='📎')
        fc.value.set_files(exe); pg.wait_for_timeout(1200)
        j.check(j.toasts_since(pg, mark) and not any('invoice.exe' in m for m in mine(pg)), 'an .exe is accepted (or refused silently)')

@journey('J-SOCIAL-38')
def read_receipts(j):
    """A sender knows whether the buyer has read her offer; the reader's unread badges clear."""
    if j.live:
        a = j.person('Dr. Amira Offer'); b = j.person('Dr. Badr Reader'); new = j.person('Dr. Nour Newcomer')
        pb = b['page']; j.nav(pb, 'feed')
        for i in (1, 2): j.sql("insert into public.messages (sender_id, receiver_id, body) values ('%s','%s','Offer part %d %s')" % (a['id'], b['id'], i, j.tag))
        pg = pb; aname = 'Amira'
    else:
        pg = j.demo_signin(j.new_page()); aname = None
    with j.step('B: the Messages badge shows the unread count; the thread is bold and listed under Unread'):
        if j.live: j.check(j.wait(pg, "(()=>{const e=[...document.querySelectorAll('#tnb-messages [class*=badge],#mb-messages [class*=badge]')].find(e=>e.getClientRects().length);return e&&e.getClientRects().length&&e.innerText.trim()==='2'})()", 30), 'B\'s Messages badge is "%s" (want 2) without reload' % msg_badge(pg))
        j.nav(pg, 'messages')
        if j.live: j.wait(pg, "[...document.querySelectorAll('#threadList .mx-thread')].some(e=>e.innerText.includes('Amira'))", 10)
        th = threads(pg); j.note('threads_on_open', th[:4])
        unread = [t for t in th if t['unread']]
        auto = [t for t in th if t['active'] and (aname or '') in t['text']] if j.live else []
        j.check(unread or not auto, 'opening Messages auto-opens the newest thread and marks it read — the unread conversation is never shown as unread')
        j.check(unread, 'no thread is marked unread')
        if j.live: j.check(any('Amira' in t['text'] for t in unread), "A's thread is not marked unread")
        aname = aname or unread[0]['text'].split('\n')[1].split()[0]
        f = j.find(pg, r'^Unread|^غير مقروء', scope='#content'); j.check(f, 'no Unread filter')
        n0 = int((re.findall(r'\d+', f.inner_text()) or ['0'])[0]); f.click(); pg.wait_for_timeout(400)
        vis = [t for t in threads(pg) if t['visible']]
        j.check(vis and all(t['unread'] for t in vis) and any(aname in t['text'] for t in vis), 'the Unread filter does not list exactly the unread threads')
    with j.step('Open the thread: badge and Unread count drop'):
        open_thread(j, pg, aname); pg.wait_for_timeout(800); to_list(j, pg)
        f = j.find(pg, r'^Unread|^غير مقروء', scope='#content'); n1 = int((re.findall(r'\d+', f.inner_text()) or ['0'])[0])
        j.check(n1 == n0 - 1, 'the Unread count went %d → %d after opening one unread thread' % (n0, n1))
        if j.live: j.check(msg_badge(pg) in ('', '0'), 'the Messages badge still shows "%s"' % msg_badge(pg))
    with j.step('Live: read_at set for exactly those two messages'):
        if j.demo: j.skip('the database exists only in live')
        j.check(j.wait_db("select count(*) from public.messages where receiver_id='%s' and read_at is not null" % b['id'], 5, want='2') == '2', 'read_at not set on the two messages')
    with j.step('A sees "Seen" / ✓✓ on the last message without reload'):
        if j.demo:
            open_thread(j, pg, threads(pg)[0]['text'].split('\n')[1].split()[0]); send(j, pg, 'receipt check ' + j.tag)
            last = pg.locator('#messagesArea .msg-row.mx-mine').last.inner_text()
            j.check(re.search(r'Seen|Read|Delivered|Sent|✓|تمت القراءة|شوهد', last), 'my messages show no delivery/read state')
        else:
            pa = a['page']; j.reload(pa); j.nav(pa, 'messages'); open_thread(j, pa, 'Badr')
            j.check(j.wait(pa, "(()=>{const m=[...document.querySelectorAll('#messagesArea .msg-row.mx-mine')].pop();return !!m&&/Seen|Read|✓✓|تمت القراءة|شوهد/.test(m.innerText)})()", 15), 'A sees no "Seen" on the last message')
    with j.step('A brand-new user sees "Unread (0)" and no demo leftovers'):
        if j.demo: j.skip('a brand-new account exists only in live')
        pn = new['page']; j.nav(pn, 'messages'); t = j.text(pn)
        j.check(re.search(r'Unread \(0\)|Unread$|غير مقروءة? \(0\)', t, re.M) and not re.search(r'Unread \([1-9]', t), 'a new user sees an unread count')
        demo = re.findall(r'ONLINE NOW \(\d\)|Vivian|Omar K|Shandong|Metformin HCl BP/USP', t)
        j.check(not demo, 'a new user sees demo leftovers on Messages: %s' % sorted(set(demo)))

@journey('J-SOCIAL-39')
def search_messages(j):
    """A member finds an old conversation or a specific message by searching."""
    if j.live:
        a = j.person('Dr. Akram Finder'); b = j.person('Dr. Carim Prices'); c = j.person('Dr. Chadi Other'); d = j.person('Dr. Dina Third')
        for who, body in ((b, 'Our offer: USD 5.80/kg for 1 MT'), (c, 'Hello from Chadi'), (d, 'مرحبا من دينا')):
            j.sql("insert into public.messages (sender_id, receiver_id, body) values ('%s','%s',$q$%s$q$)" % (who['id'], a['id'], body))
        pg = a['page']; j.reload(pg); name, price, arname = 'Carim', '5.80', 'دينا'
    else:
        pg = j.demo_signin(j.new_page()); name, price, arname = 'Omar', '5.50', None
    box = None
    with j.step('Open Messages; type a name in the conversation search: the list filters to that person'):
        j.nav(pg, 'messages'); box = pg.locator('#content .tp-search input, #content input[placeholder*="Search conversations"], #content input[placeholder*="ابحث"]').first
        j.check(box.count() and box.is_visible(), 'no conversation search'); box.fill(name); pg.wait_for_timeout(600)
        vis = [t for t in pg.eval_on_selector_all('#threadList .mx-thread', 'e=>e.filter(x=>x.getClientRects().length).map(x=>x.innerText)')]
        j.check(vis and all(name in v for v in vis), 'the name search does not filter the list to %s (%d shown)' % (name, len(vis)))
    with j.step('Search a price that appears only inside a message: the message is found and opens scrolled to it'):
        box.fill(price); pg.wait_for_timeout(800)
        vis = pg.eval_on_selector_all('#threadList .mx-thread, #content [class*=search-hit], #content [class*=result]', 'e=>e.filter(x=>x.getClientRects().length).map(x=>x.innerText)')
        j.check(any(price in v or name in v for v in vis), 'not built: searching message text ("%s") finds nothing — only names are searched' % price)
        pg.locator('#threadList .mx-thread:visible, #content [class*=search-hit]:visible').first.click(); j.settle(pg, 800)
        j.check(pg.evaluate("p=>{const m=[...document.querySelectorAll('#messagesArea .msg-row')].find(e=>e.innerText.includes(p));if(!m)return false;const r=m.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight+2}", price), 'the thread does not open at the found message')
    with j.step('Arabic text search works; nonsense shows an empty state'):
        to_list(j, pg)                                   # on a phone the opened conversation covers the list and its search box
        if arname:
            box.fill(arname); pg.wait_for_timeout(600)
            j.check(any(arname in v or 'Dina' in v for v in pg.eval_on_selector_all('#threadList .mx-thread', 'e=>e.filter(x=>x.getClientRects().length).map(x=>x.innerText)')), 'the Arabic search finds nothing')
        box.fill('zzqqxx'); pg.wait_for_timeout(600)
        j.check(re.search(r'No (conversations|results|messages)|nothing|لا توجد|لا نتائج', j.text(pg), re.I), 'no empty state for a search without results')

@journey('J-SOCIAL-40')
def mute_block_report(j):
    """A member protects herself from unwanted messages: mute, block, report; the moderator sees the report."""
    if j.live:
        a = j.person('Dr. Asmaa Protected'); c = j.person('Dr. Cyrus Spammer')
        for i in range(2): j.sql("insert into public.messages (sender_id, receiver_id, body) values ('%s','%s','Buy my product now %d %s')" % (c['id'], a['id'], i, j.tag))
        pg = a['page']; j.reload(pg); cname = 'Cyrus'
    else:
        pg = j.demo_signin(j.new_page()); cname = 'Vivian'
    with j.step("In C's thread: 👤 opens C's profile and 📞 does a real thing (no 'opens in the full app' message)"):
        j.nav(pg, 'messages'); open_thread(j, pg, cname)
        el = j.find(pg, r'^👤$', scope='#content .chat-head', exact=True); j.check(el, 'no 👤 in the conversation header')
        j.act(pg, el, '👤 (profile)', lambda: pg.evaluate("document.body.getAttribute('data-page')") == 'profile' and cname in j.text(pg)[:400], expect="C's profile to open")
        j.nav(pg, 'messages'); open_thread(j, pg, cname)
    with j.step('⋯ → Mute notifications: stored; the thread shows it is muted (the menu opens inside the screen, every item can be reached)'):
        el = menu(j, pg, r'Mute|كتم', 'Mute')
        out = pg.evaluate("[...document.querySelectorAll('.ch-dd-item')].filter(e=>e.getClientRects().length).map(e=>{const r=e.getBoundingClientRect(),h=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return (r.left<0||r.right>innerWidth||!h||!(h===e||e.contains(h)))?e.innerText.trim():null}).filter(Boolean)")
        j.check(not out, 'the conversation ⋯ menu is partly off the screen at %dpx — these items cannot be reached: %s' % (j.width, out[:6]))
        if j.live:
            j.check(not re.search(r'Last seen|آخر ظهور', head(pg)), 'the chat header claims a presence the live app does not have: "%s"' % head(pg)[:80])
        el.click(); pg.wait_for_timeout(600)
        el = menu(j, pg, r'Mute|كتم', 'Mute')
        j.check(re.search(r'Unmute|إلغاء الكتم', el.inner_text()), 'Mute did not take effect (the menu does not offer Unmute)')
        pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
        if pg.locator('.ch-dd-item:visible').count(): menu_btn(pg).click(); pg.wait_for_timeout(200)
        if j.live: j.check(j.has_table('conversation_mutes') or j.has_column('conversation_heads', 'muted'), 'not built: mute is not stored')
    with j.step("⋯ → Block: C can no longer message A (the database refuses)"):
        el = menu(j, pg, r'Block|حظر', 'Block'); el.click(); pg.wait_for_timeout(600)
        ok = j.find(pg, r'^(Block|Yes|Confirm|حظر|نعم)$', scope='body', exact=True)
        if ok: ok.click(); pg.wait_for_timeout(600)
        if j.live:
            r = c['page'].evaluate("([me,to])=>dxLive.sb.from('messages').insert({sender_id:me,receiver_id:to,body:'after block'}).then(r=>r.error?'refused':'stored')", [c['id'], a['id']])
            j.check(r == 'refused', 'after Block, C can still message A (the database stored it)')
            # C writes through the app: refused in C's language, nothing stored, and C's conversation list does not pretend it was sent
            pc = c['page']; j.reload(pc); j.nav(pc, 'messages'); open_thread(j, pc, 'Asmaa')
            before = [t['text'] for t in threads(pc) if 'Asmaa' in t['text']]
            body = 'after block UI ' + j.tag; mark = j.toast_mark(pc); send(j, pc, body); pc.wait_for_timeout(800)
            said = ' '.join(j.toasts_since(pc, mark))
            j.check(said, 'the blocked sender is not told the message was refused')
            if j.ar: j.check(not re.search(r'[A-Za-z]{4,}', said), 'the refusal is not in Arabic: "%s"' % said[:80])
            j.check(j.sql1("select count(*) from public.messages where body=$q$%s$q$" % body) == '0', 'the blocked sender\'s message was stored')
            after = [t['text'] for t in threads(pc) if 'Asmaa' in t['text']]
            j.check(not any(body in t for t in after), 'the conversation list shows the refused message as sent: %s (before: %s)' % (after[:1], before[:1]))
    with j.step('⋯ → Report (reason + text): a moderation item with the reported messages'):
        el = menu(j, pg, r'Report|إبلاغ', 'Report')
        j.act(pg, el, 'Report Conversation', lambda: pg.locator('.modal-bg:visible textarea, .dbk-ov:visible textarea, [role=dialog]:visible textarea').count(), expect='a report form with a reason')
        pg.locator('.modal-bg:visible textarea, .dbk-ov:visible textarea, [role=dialog]:visible textarea').first.fill('Repeated spam offers')
        mark = j.toast_mark(pg)
        j.click(pg, r'^(Send report|Submit|Report|Send|أرسل البلاغ|إرسال البلاغ|إرسال|إبلاغ)$', scope='body', what='Send report', exact=True); pg.wait_for_timeout(800)
        j.check(j.toasts_since(pg, mark) or re.search(r'Thanks|received|شكرًا|تم', j.text(pg, 'body')[:3000]), 'no confirmation after reporting')
        if j.live: j.check(j.has_table('message_reports') or j.has_table('reports'), 'not built: no table for message reports')
    with j.step('Moderator M finds the report in Admin → Review'):
        if j.demo: j.skip('the moderator exists only in live')
        m = j.person('Dr. Maha Moderator'); make_admin(j, m['id']); pm = m['page']; j.reload(pm)
        # Admin is reached as the business journeys reach it (the entry sits in the sidebar footer, which j.nav does not
        # find), and reported conversations are their own queue in Review — open it as M would
        from _biz import admin_review
        admin_review(j, pm, r'Message reports|بلاغات الرسائل')
        j.check('Cyrus' in j.text(pm) and 'Buy my product' in j.text(pm), 'the message report is not in Admin → Review')
    with j.step('Unblock restores messaging; states survive reload'):
        el = j.find(pg, r'Unblock|إلغاء الحظر', scope='#content') or menu(j, pg, r'Unblock|إلغاء الحظر', 'Unblock'); el.click(); pg.wait_for_timeout(600)
        j.check(pg.locator('#composeInput').is_enabled() and not re.search(r'blocked|محظور', pg.locator('#composeInput').get_attribute('placeholder') or ''), 'after Unblock the composer is still blocked')
        if j.live:
            r = c['page'].evaluate("([me,to])=>dxLive.sb.from('messages').insert({sender_id:me,receiver_id:to,body:'after unblock'}).then(r=>r.error?'refused':'stored')", [c['id'], a['id']])
            j.check(r == 'stored', 'after Unblock C still cannot message A')
            j.reload(pg); j.nav(pg, 'messages'); open_thread(j, pg, cname)
            j.check(re.search(r'Unmute|إلغاء الكتم', menu(j, pg, r'Mute|كتم', 'Mute').inner_text()), 'after reload the thread is no longer muted')

if __name__ == '__main__': main(__file__)
