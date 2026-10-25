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
            if len(opts) > 1:   # B's option (it carries B's @username); a shared test database holds dozens of «Dr. Carim Audit»: type B's @username
                to.fill(next((o for o in opts if bco in o), '@' + j.sql1("select username from public.profiles where id='%s'" % b['id'])))
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
    with j.step('Sign-up refuses a name with characters that are not letters or that mix alphabets (U+FFFC, a Cyrillic а, a mark that '
                'cannot join its letter — e + U+0335, ı + U+0307 —, Ɥ U+A78D and Hausa Ɗ "not supported yet", Chinese letters, a dot '
                'standing alone, a spaced hyphen with the parentheses suggested), saying what to change with the quoted letter isolated '
                '(U+2068 … U+2069); real names (Arabic with harakat — stored without them —, titles written "د/", "د / " or glued "Dr.أحمد", '
                'a Latin title on a Cyrillic name, Greek and all-caps Cyrillic names that read as Latin, pasted hyphens, an em dash, ʿ, '
                'accents, apostrophes, brackets) sign up fine'):
        if j.demo: j.skip('the name rule is the database\'s and the live app\'s (the demo keeps its sample people)')
        def ui_signup(name):
            p2 = j.new_page(j.new_ctx()); j.open(p2); p2.click('#loginPage [onclick="showSignup()"]'); p2.wait_for_selector('#suName', state='visible', timeout=5000)
            email = j.email('names'); p2.fill('#suName', name); p2.fill('#suEmail', email); p2.fill('#suPw', PW)
            p2.click('#signupPage button.f-btn.dx-js-only'); p2.wait_for_timeout(1500)
            return p2, email, j.text(p2, '#suErr')
        for name, pat in (('Dr. Zeina Sign %s￼' % j.tag, r'remove “￼” \(U\+FFFC\)|احذف «￼» \(U\+FFFC\)'),
                          ('Ɗanjuma Sign %s' % j.tag, r'The letter “Ɗ” \(U\+018A\) is not supported in names yet|الحرف «Ɗ» \(U\+018A\) غير مدعوم في الأسماء بعد'),
                          ('Ahmed Sign %s - MBA' % j.tag, r'parentheses — write “Ahmed Sign %s \(MBA\)”|بين قوسين — اكتب «Ahmed Sign %s \(MBA\)»' % (j.tag, j.tag)),
                          ('Dr. Rаna Sign %s' % j.tag, r'one alphabet — “Rаna”|بأبجدية واحدة — «Rаna»'),
                          ('Dr. Ahme\u0335d Sign %s' % j.tag, r'Remove the mark added to “e\u0335” \(U\+0335\)|احذف العلامة المضافة إلى «e\u0335» \(U\+0335\)'),
                          ('Dr. Sal\u0131\u0307h Sign %s' % j.tag, r'Remove the mark added to “\u0131\u0307” \(U\+0307\)|احذف العلامة المضافة إلى «\u0131\u0307» \(U\+0307\)'),
                          ('\ua78dEXOB Sign %s' % j.tag, r'The letter “\ua78d”|الحرف «\ua78d»'),
                          ('张伟 Sign %s' % j.tag, r'Latin, Arabic, Greek or Cyrillic letters — “张”|بحروف عربية أو لاتينية أو يونانية أو سيريلية — «张»'),
                          ('د . أحمد %s' % j.tag, r'“\.” is not a word|«\.» ليست كلمة'),
                          # fifth version (v-spoof-r1): a bracket the bidi algorithm reorders — «(MBA) Ahmed» drew as «Ahmed (MBA)» in Arabic
                          ('(MBA) Ahmed Sign %s' % j.tag, r'after the name — write “Ahmed Sign %s \(MBA\)”|بعد الاسم — اكتب «Ahmed Sign %s \(MBA\)»' % (j.tag, j.tag)),
                          ('Ali %s (علي) محمد' % j.tag, r'after the name — write “Ali %s محمد \(علي\)”|بعد الاسم — اكتب «Ali %s محمد \(علي\)»' % (j.tag, j.tag)),
                          ('Hala Sign %s – Head of QA – Pharco' % j.tag, r'write “Hala Sign %s \(Head of QA, Pharco\)”|اكتب «Hala Sign %s \(Head of QA, Pharco\)»' % (j.tag, j.tag)),
                          # ninth version: a space on one side of a hyphen is refused with the fix, not joined silently
                          ('Abdel- Rahman Sign %s' % j.tag, r'without a space — write “Abdel-Rahman Sign %s”|بلا مسافة — اكتب «Abdel-Rahman Sign %s»' % (j.tag, j.tag))):
            p2, email, err0 = ui_signup(name); err = re.sub('[\u2068\u2069]', '', err0)
            j.check(re.search(pat, err), 'sign-up as %s is not refused with a clear message (said: "%s")' % (ascii(name), err[:140]))
            j.check(re.search('[“«]\u2068[^\u2069]+\u2069[”»]', err0), 'the refusal of %s does not isolate what it quotes (U+2068 … U+2069): %s' % (ascii(name), ascii(err0[:120])))
            j.check(j.ar == bool(re.search('[ء-ي]', re.sub('[“«][^”»]*[”»]', '', err.replace(name, '')))), 'the refusal is not in the interface language: "%s"' % err[:100])   # Arabic words outside what it quotes (the English one lists the comma ،)
            j.check(j.sql1("select count(*) from auth.users where email='%s'" % email) == '0', 'an account was created for %s' % ascii(name))
        # through the form, as a person signs up: an Arabic name with harakat, and a name with brackets, dots and a hyphen
        for name, stored in (('د. نرمين أبو زيدٍ %s' % j.tag, 'د. نرمين أبو زيد %s' % j.tag), ('Al-Hassan (Pharm.D.) %s' % j.tag, None), ('د/ هيثم دويدار %s' % j.tag, None),
                             ('ا.د / سامي فهمي %s' % j.tag, 'ا.د/ سامي فهمي %s' % j.tag), ('Saʿīd Ḥasan %s' % j.tag, 'Sa’īd Ḥasan %s' % j.tag),
                             ('Dr. Мария Иванова %s' % j.tag, None), ('Anne\u2011Marie O\'Brien %s' % j.tag, 'Anne-Marie O’Brien %s' % j.tag),
                             ('Άννα Βίσση %s' % j.tag, None), ('ОКСАНА КОРОТКОВА %s' % j.tag, None), ('Dr.أحمد Jean—Paul %s' % j.tag, 'Dr.أحمد Jean-Paul %s' % j.tag),
                             # fifth version: the bracket after the name, the Maghrebi ڭ, a Persian zero-width non-joiner (kept as a space)
                             ('Ahmed Ali (MBA) %s' % j.tag, None), ('ڭمال العلوي %s' % j.tag, None), ('علی\u200cرضا %s' % j.tag, 'علی رضا %s' % j.tag),
                             # ninth version (the owner's decision of 25 Oct): a name may look like another — «بىىىام» is a name like any other
                             ('بىىىام علي %s' % j.tag, None), ('هانىء سعيد %s' % j.tag, None)):
            me2 = j.person(name)
            j.check(j.sql1("select name || '|' || name_needs_fix from public.profiles where id='%s'" % me2['id']) == (stored or name) + '|false', 'the real name %s was not stored as typed' % name)
        # and the others the owner listed, through the sign-up trigger
        for name in ('د. هالة الشامي %s', 'Dr. Ahmed El-Sayed %s', "O'Brien %s", 'José Müller %s', 'Ünal %s', 'مُحَمَّد عَبْدُ اللَّه %s', 'O’Brien %s',
                     'م/ محمود %s', 'Мария Иванова (Maria Ivanova) %s', 'د. أحمد علي، صيدلي %s', 'Μαρία %s', 'Вера Кох %s', 'АННА АХМАТОВА %s', 'Dr. Νίκη Βίσση %s',
                     'د.Ahmed %s', 'Nguyễn Thị Ánh %s', 'İsmail Ñúñez %s', 'Al-Hassan (Pharm.D.) %s'):
            uid = j.sql1("insert into auth.users (email, raw_user_meta_data) values ('%s', jsonb_build_object('name', $q$%s$q$)) returning id" % (j.email('real'), name % j.tag))
            want = (name % j.tag).replace("'", '’')            # the apostrophe is stored as ’, the way the app shows it (0039)
            want = re.sub('[\u064b-\u0652\u0670]', '', want)   # Arabic diacritics are not stored (0039_names_rule_4)
            j.check(j.sql1("select (name = $q$%s$q$ and not name_needs_fix)::text from public.profiles where id='%s'" % (want, uid)) == 'true', 'the real name %s did not sign up as typed' % (name % j.tag))
    with j.step('Names may be alike (the owner\'s decision of 25 Oct, Facebook\'s rule): every member has a unique @username — the demo\'s '
                'sample members too: the picker\'s options read «name · @username · ✓» (a connection) or «name · @username · company · city», '
                'the profile says @username under the name (left to right), and «@username» typed in To sends to that member'):
        ISO = re.compile('[⁦-⁩]')
        def picker(typed):
            cancel(); to_list(j, pg); j.click(pg, r'✎|New message|رسالة جديدة', scope='#content', what='✎ New message')
            pg.locator('#nmTo:visible').first.fill(typed); pg.wait_for_timeout(1500 if j.live else 300)
            return pg.evaluate("(()=>{const i=document.querySelector('#nmTo');const l=i&&i.list;return l?[...l.options].map(o=>[o.value,o.label||'']):[]})()")
        def cancel():
            if pg.locator('.dbk-ov:visible').count(): j.click(pg, r'^(Cancel|إلغاء|×|✕)$', scope='.dbk-ov', what='Cancel', exact=True)
        def new_message(to_value, body):
            cancel(); to_list(j, pg); j.click(pg, r'✎|New message|رسالة جديدة', scope='#content', what='✎ New message')
            box = pg.locator('#nmTo:visible').first; box.fill(to_value); pg.wait_for_timeout(1200 if j.live else 300)
            pg.locator('#nmTx:visible').first.fill(body)
            mark = j.toast_mark(pg); j.click(pg, r'^(Send|إرسال)$', scope='.dbk-ov', what='Send', exact=True); j.settle(pg, 1500)
            return ' '.join(j.toasts_since(pg, mark))
        if j.demo:
            ol = picker('Omar'); j.note('demo options', [ISO.sub('', v) for v, _ in ol])
            vals = [ISO.sub('', v) for v, _ in ol]
            j.check('Eng. Omar Khaled · @omar.khaled · Medsinia Industries · 10th of Ramadan City, Egypt' in vals, 'the demo picker does not offer «name · @username · company · city» for a non-connection: %s' % vals[:4])
            j.check('Vivian Zhou · @vivian.zhou · ✓' in vals, 'the demo picker does not offer «name · @username · ✓» for a connection: %s' % vals[:4])
            cancel()
            body = 'By username ' + j.tag; new_message('@omar.khaled', body)
            j.check('Omar' in head(pg) and any(body in m for m in mine(pg)), 'typing @omar.khaled did not send to Eng. Omar Khaled (header: %s)' % head(pg)[:60])
            # s03-user2 (v-user1): a username typed WITHOUT its @ is read as a username too — and reaches its member only
            body = 'Bare username ' + j.tag; new_message('omar.khaled', body)
            j.check('Omar' in head(pg) and any(body in m for m in mine(pg)), 'typing omar.khaled (no @) did not send to Eng. Omar Khaled (header: %s)' % head(pg)[:60])
            said = new_message('@nobody.here', 'To nobody ' + j.tag)
            j.check(re.search(r'No member|لا يوجد', said), 'typing an @username nobody has is not refused with a clear message: %s' % said[:100]); cancel()
            pg.evaluate('gotoProfile(%d)' % demo_person(pg, 'Omar')); j.settle(pg, 700)
            un = pg.evaluate("(()=>{const e=document.querySelector('#content .profile-username');return e?[e.innerText,getComputedStyle(e.querySelector('bdi')).direction]:null})()")
            j.check(un and un[0].strip() == '@omar.khaled' and un[1] == 'ltr', 'the profile does not say @omar.khaled under the name, left to right: %s' % un)
        else:
            def member(name, company=None, city=None):   # a precondition: a member made by the sign-up trigger (handle_new_user)
                meta = {'name': name}
                if company: meta['company'] = company
                uid = j.sql1("insert into auth.users (email, raw_user_meta_data) values ('%s', $m$%s$m$::jsonb) returning id" % (j.email('twin'), json.dumps(meta)))
                if city: j.sql("update public.profiles set location = $q$%s$q$ where id = '%s'" % (city, uid))
                return uid
            uname = lambda uid: j.sql1("select username from public.profiles where id = '%s'" % uid)
            # the identical twins: the same name AND company AND city — only their @username tells them apart
            tname, tco, tcity = 'Dr. Lina Same %s' % j.tag, 'Twin Pharma %s' % j.tag, 'الإسكندرية'
            t1, t2 = member(tname, tco, tcity), member(tname, tco, tcity)
            u1, u2 = uname(t1), uname(t2); j.note('twin usernames', [u1, u2])
            j.check(u1 and u2 and u1 != u2 and j.sql1("select count(distinct username_key) from public.profiles where id in ('%s','%s')" % (t1, t2)) == '2', 'the two members called %s do not have two usernames: %s' % (tname, [u1, u2]))
            j.reload(pg); j.nav(pg, 'messages')
            ol = picker(tname); vals = [ISO.sub('', v) for v, _ in ol if ISO.sub('', v).startswith(tname)]; j.note('twin options', vals); cancel()
            want = sorted('%s · @%s · %s · %s' % (tname, u, tco, tcity) for u in (u1, u2))
            j.check(sorted(vals) == want, 'the picker does not offer the two twins as «name · @username · company · city»: %s (want %s)' % (vals, want))
            raw = [v for v, _ in ol if ISO.sub('', v).startswith(tname)]
            j.check(all(('⁦@%s⁩' % u) in ''.join(raw) for u in (u1, u2)) and all(('⁨' + tco + '⁩') in v for v in raw), 'the @username (left to right) and the company are not isolated in the options: %s' % [ascii(v) for v in raw])
            j.check(not any(re.search(r'Same name|نفس الاسم|⚠', l) for _, l in ol), 'an option still warns «Same name» (names may be alike now): %s' % [l for _, l in ol][:3])
            # s03-user2 (v-real1): only the members the text fits are offered — not every person loaded so far, each «≈ typed»
            j.check(ol and all(ISO.sub('', v).startswith(tname) for v, _ in ol), 'the picker offers members the typed name does not fit: %s' % [ISO.sub('', v) for v, _ in ol if not ISO.sub('', v).startswith(tname)][:4])
            for v in raw:                        # each option reaches its own member
                body = 'Twin option %s %s' % (ISO.sub('', v).split('@')[1].split(' ')[0], j.tag); new_message(v, body)
                got = j.wait_db("select string_agg(receiver_id::text, ',') from public.messages where sender_id='%s' and body=$q$%s$q$" % (a['id'], body), 8)
                exp = t1 if ('@' + u1 + '⁩') in v else t2
                j.check(got == exp, 'the option «%s» was stored for %s, not for the member whose @username it shows (%s)' % (ISO.sub('', v), got or 'nobody', exp))
                hd = head(pg); j.note('twin header', ascii(hd))
                j.check(('⁦@%s⁩' % uname(exp)) in hd and tco in hd and not re.search(r'Member since|عضو منذ|#[0-9a-f]{6}', hd), 'the chat header does not say the @username (isolated) and the company — or still says member since / #handle: %s' % ascii(hd[:160]))
                cancel()
            for typed, exp in (('@' + u2, t2), ('@' + u1.upper(), t1)):   # typing an exact @username (any case) sends to that member
                body = 'Typed %s %s' % (typed, j.tag); said = new_message(typed, body)
                got = j.wait_db("select string_agg(receiver_id::text, ',') from public.messages where sender_id='%s' and body=$q$%s$q$" % (a['id'], body), 8)
                j.check(got == exp, 'typing «%s» sent to %s, not to %s (toasts: %s)' % (typed, got or 'nobody', exp, said[:80])); cancel()
            body = 'Bare twin %s' % j.tag; said = new_message(tname, body)   # the bare shared name: nobody, pick one
            j.check(re.search(r'Several|أكثر من', said) and j.sql1("select count(*) from public.messages where body=$q$%s$q$" % body) == '0', 'typing a name two members share is not refused: %s' % said[:120]); cancel()
            body = 'Wrong pair %s' % j.tag; said = new_message('Dr. Someone Else %s · @%s' % (j.tag, u1), body)   # another name before an @username
            j.check(j.sql1("select count(*) from public.messages where body=$q$%s$q$" % body) == '0', 'a name that is not the member\'s, with their @username, was sent'); cancel()
            # s03-user2 (v-user1): a username typed without its @ is read as a username too — «ziad.<tag>» reaches Ziad, never a member
            # whose name is the last part; a text that is one member's username and another's name reaches nobody
            zname = 'Ziad %s' % j.tag; zid = member(zname); zu = uname(zid); kid = member(j.tag)   # «<Tag>»: a one-word name
            body = 'Bare username %s' % j.tag; said = new_message(zu, body)
            got = j.wait_db("select string_agg(receiver_id::text, ',') from public.messages where sender_id='%s' and body=$q$%s$q$" % (a['id'], body), 8)
            j.check(got == zid, 'typing «%s» (Ziad\'s username, no @) sent to %s, not to Ziad %s (the one-word «%s» is %s; toasts: %s)' % (zu, got or 'nobody', zid, j.tag, kid, said[:80])); cancel()
            mix = 'mx' + j.tag.lower()[:12]; xa = member('Sara Mix %s' % j.tag); j.sql("update public.profiles set username = '%s' where id = '%s'" % (mix, xa)); xb = member('Mx' + j.tag[:12].lower())
            body = 'Mixed fit %s' % j.tag; said = new_message(mix, body)
            j.check(j.sql1("select count(*) from public.messages where body=$q$%s$q$" % body) == '0' and re.search(r'more than one|أكثر من', said), 'a text that is one member\'s username and another\'s name was sent, or not explained: %s' % said[:140]); cancel()
            # a member nobody else is called: the bare name still reaches them
            sname, sco = 'Dr. Unique Single %s' % j.tag, 'Solo Pharma %s' % j.tag; s1 = member(sname, sco)
            body = 'Bare unique %s' % j.tag; new_message(sname, body)
            j.check(j.wait_db("select receiver_id from public.messages where sender_id='%s' and body=$q$%s$q$" % (a['id'], body), 8) == s1, 'the bare name of the one member called %s did not reach them' % sname); cancel()
            # free-text facts can never draw an @username or the separator
            fname = 'Dr. Fake Facts %s' % j.tag; f1 = member(fname, 'Pharco @%s · ✓' % u1, 'Cairo ＠%s' % u2)
            ol = picker(fname); vals = [ISO.sub('', v) for v, _ in ol if ISO.sub('', v).startswith(fname)]; cancel(); j.note('fact options', vals)
            j.check(len(vals) == 1 and vals[0].count('@') == 1 and vals[0].count(' · ') == 3 and '＠' not in vals[0], 'a company or city draws an @username or a separator in the option: %s' % vals)
    with j.step('A username change shows everywhere: the twin changes it in Edit Profile (the field says whether it is free and why not — a '
                'look-alike of a taken one is taken, a reserved word is refused, EN/AR), and A\'s picker, chat header and the profile say the new one; '
                'the old one is held for its member (nobody else can take it for 30 days)'):
        if j.demo:
            mep = j.demo_signin(j.new_page()); mep.evaluate('gotoProfile(ME.id)'); j.settle(mep, 600)
            j.click(mep, r'Edit Profile|تعديل الملف|عدّل الملف', scope='#content', what='Edit Profile')
            f = mep.locator('#ep-user'); j.check(f.count(), 'Edit Profile has no Username field'); f.fill('@alia.mourad'); mep.wait_for_timeout(200)
            j.check(re.search(r'taken|مستخدم بالفعل', j.text(mep, '#ep-user-st')), 'a taken username is not said to be taken: %s' % j.text(mep, '#ep-user-st'))
            f.fill('haytham.q' + j.tag.lower()[:6]); mep.wait_for_timeout(200)
            j.click(mep, r'^(Save Changes|حفظ التغييرات)$', scope='.modal-bg', what='Save Changes', exact=True); j.settle(mep, 600)
            j.check(('@haytham.q' + j.tag.lower()[:6]) in j.text(mep, '#content .profile-username'), 'the new username is not under the name on the profile: %s' % j.text(mep, '#content .profile-username'))
        else:
            p2 = j.person('Dr. Mona Change %s' % j.tag); m2 = p2['id']; old = uname(m2); pp = p2['page']
            goto_profile(j, pp, {'id': m2})
            j.check(('@' + old) in j.text(pp, '#content .profile-username'), 'my profile does not say my @username under my name: %s' % j.text(pp, '#content .profile-username'))
            j.click(pp, r'Edit Profile|تعديل الملف|عدّل الملف', scope='#content', what='Edit Profile')
            f = pp.locator('#ep-user'); j.check(f.count(), 'Edit Profile has no Username field')
            for typed, pat in (('@' + u1.replace('m', 'rn', 1) if 'm' in u1 else '@' + u1.replace('l', '1', 1), r'taken|مستخدم بالفعل'), ('drugbox.team', r'kept for Drugbox|محجوز لـ Drugbox'), ('ab', r'at least 5|5 أحرف')):
                f.fill(typed); pp.wait_for_timeout(1300)
                j.check(re.search(pat, j.text(pp, '#ep-user-st')), 'typing «%s» in Username does not say why it cannot be used: %s' % (typed, j.text(pp, '#ep-user-st')))
            new = 'mona.new.' + j.tag.lower()[:8]
            f.fill(new); pp.wait_for_timeout(1300)
            j.check(re.search(r'available|متاح', j.text(pp, '#ep-user-st')), 'a free username is not said to be available: %s' % j.text(pp, '#ep-user-st'))
            j.click(pp, r'^(Save Changes|حفظ التغييرات)$', scope='.modal-bg', what='Save Changes', exact=True); j.settle(pp, 1200)
            j.check(uname(m2) == new and ('@' + new) in j.text(pp, '#content .profile-username'), 'the new username was not saved and shown (db %s, profile %s)' % (uname(m2), j.text(pp, '#content .profile-username')))
            j.check(j.sql1("select count(*) from public.username_holds where profile_id = '%s' and username = '%s' and held_until > now() + interval '29 days'" % (m2, old)) == '1', 'the old username is not held for its member for 30 days')
            j.sql("insert into public.messages (sender_id, receiver_id, body) values ('%s','%s','Changed my username %s')" % (m2, a['id'], j.tag))
            j.reload(pg); j.nav(pg, 'messages'); open_thread(j, pg, 'Dr. Mona Change %s' % j.tag)
            j.check(('@' + new) in head(pg) and ('@' + old) not in head(pg), 'A\'s chat header does not say the new username: %s' % ascii(head(pg)[:120]))
            ol = picker('@' + new[:9]); vals = [ISO.sub('', v) for v, _ in ol]; cancel()
            j.check(any(('@' + new) in v for v in vals) and not any(('@' + old + ' ') in v for v in vals), 'A\'s picker does not offer the new username: %s' % vals[:4])
            goto_profile(j, pg, {'id': m2})
            j.check(('@' + new) in j.text(pg, '#content .profile-username'), 'the profile A opens does not say the new username: %s' % j.text(pg, '#content .profile-username'))
    with j.step('Two members with the same name write first: the list shows each conversation, the chat header says each one\'s '
                '@username, and 👤 opens the one whose conversation is open (the profile view is counted on them, not the other)'):
        if j.demo: j.skip('members with the same name exist only in live (the demo has one sample person per name)')
        def writer(name, company):
            return j.sql1("insert into auth.users (email, raw_user_meta_data) values ('%s', $m$%s$m$::jsonb) returning id" % (j.email('hoda'), json.dumps({'name': name, 'company': company})))
        oname, oco = 'Dr. Hoda Twin %s' % j.tag, 'Alpha Pharma %s' % j.tag
        o1, o2 = writer(oname, oco), writer(oname, oco)
        n1, n2 = (j.sql1("select username from public.profiles where id='%s'" % o) for o in (o1, o2))
        for o, w in ((o1, 'one'), (o2, 'two')):
            j.sql("insert into public.messages (sender_id, receiver_id, body) values ('%s','%s','Hoda %s writes first %s')" % (o, a['id'], w, j.tag))
        j.reload(pg); j.nav(pg, 'messages'); to_list(j, pg)
        rows = [t for t in threads(pg) if oname in t['text']]; j.note('same-name threads', [t['text'] for t in rows])
        j.check(len(rows) == 2, 'the two conversations with members called %s are not both in the list: %s' % (oname, [t['text'] for t in rows]))
        t = pg.locator('#threadList .mx-thread', has_text='Hoda one writes first'); j.check(t.count() == 1, 'no conversation that reads «Hoda one writes first»'); t.first.click(); j.settle(pg, 900)
        j.check(('@' + n1) in head(pg) and ('@' + n2) not in head(pg), "the chat header of the first Dr. Hoda does not say her @username %s: %s" % (n1, ascii(head(pg)[:120])))
        v1, v2 = (j.sql1("select profile_views from public.profiles where id='%s'" % o) for o in (o1, o2))
        el = j.find(pg, r'^👤$', scope='#content .chat-head', exact=True); j.check(el, 'no 👤 in the conversation header')
        el.click(); j.settle(pg, 1500)
        j.check(pg.evaluate("document.body.getAttribute('data-page')") == 'profile' and ('@' + n1) in j.text(pg, '#content .profile-username'),
                "👤 in the first Dr. Hoda's conversation did not open her profile (says %s)" % j.text(pg, '#content .profile-username'))
        j.check(j.wait_db("select profile_views - %s from public.profiles where id='%s'" % (v1, o1), 6) == '1' and j.sql1("select profile_views from public.profiles where id='%s'" % o2) == v2,
                'the profile view was not counted on the member whose conversation was open')
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
