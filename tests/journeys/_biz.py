"""Helpers shared by the business journeys (tests/journeys/business_*.py): company directory, company pages and workspace,
requests & deals, marketplace, payments. Everything a journey proves is done through the interface; the SQL helpers here only
set up preconditions that another journey owns (a supplier that already exists, a second company) and read the acceptance
rows in live."""
import re, os, json, time, hmac, hashlib, functools, urllib.request, urllib.error
from _j import StepFail
import _dx

FIX = _dx.FIXTURES
PDF, PNG = os.path.join(FIX, 'spec.pdf'), os.path.join(FIX, 'photo.png')
TOP_DLG = "[...document.querySelectorAll('.dbk-ov,.modal-bg,[role=dialog][aria-modal=true],#boostModalOverlay,#dxEditor')].filter(e=>{const r=e.getBoundingClientRect();return r.width>2&&r.height>2&&getComputedStyle(e).visibility!='hidden'&&getComputedStyle(e).display!='none'}).pop()"

# ---- dialogs -----------------------------------------------------------------------------------------------------------
def dlg_open(pg):
    return pg.evaluate("!!(%s)" % TOP_DLG)

def dlg_text(pg):
    return pg.evaluate("(()=>{const d=%s;return d?d.innerText:''})()" % TOP_DLG)

def dlg_click(j, pg, pattern, what=None, settle=600):
    """Click the visible button in the top dialog whose text matches pattern (fails 'not built' when there is none)."""
    j.check(dlg_open(pg), 'no dialog is open to choose "%s" in' % (what or pattern))
    return j.click(pg, pattern, scope='body', what=what, settle=settle)

def dlg_fill(pg, sel, val):
    loc = pg.locator(sel).last
    loc.fill(val)

def close_dialogs(pg):
    dock = pg.locator('#dxDock:visible [data-a=x]')            # the message dock (a person closes it before going on)
    if dock.count():
        try: dock.first.click(timeout=2000); pg.wait_for_timeout(300)
        except Exception: pass
    for _ in range(4):
        if not dlg_open(pg): return
        if pg.locator('#dxEditor:visible #edCancel').count(): pg.click('#dxEditor #edCancel'); pg.wait_for_timeout(300); continue
        pg.keyboard.press('Escape'); pg.wait_for_timeout(250)
    pg.evaluate("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")

def dlg_inputs(pg):
    return pg.evaluate("(()=>{const d=%s;return d?[...d.querySelectorAll('input,select,textarea')].filter(e=>e.getClientRects().length).map(e=>({id:e.id,name:e.name,type:e.type,ph:e.placeholder||'',label:((e.closest('label')||{}).innerText||(e.labels&&e.labels[0]&&e.labels[0].innerText)||'').trim().slice(0,60)})):[]})()" % TOP_DLG)

TASHKEEL = re.compile('[\u064B-\u0652\u0640]')
def _ar_pattern(pattern):
    """The pattern plus the Arabic translations (web/src/i18n.js) of its plain English alternatives, without tashkeel."""
    alts = pattern.split('|'); more = []
    for a in alts:
        w = a.strip('^$ ')
        if re.fullmatch(r"[A-Za-z][A-Za-z /&'%-]*", w or '-'):
            for k in (w, w + ' *'):
                t = ar(k)
                if t: more.append(re.escape(t.replace(' *', '').strip()))
    return TASHKEEL.sub('', '|'.join(alts + more))

def fill_by_label(j, pg, pattern, value, required=True):
    """Fill the input/select/textarea of the top dialog (or the page) whose label matches pattern — or, when no label
    matches, whose placeholder / id / aria-label does. Arabic labels match through web/src/i18n.js, ignoring tashkeel."""
    pattern = _ar_pattern(pattern)
    h = pg.evaluate_handle("""(p)=>{const re=new RegExp(p,'i');const N=s=>(s||'').replace(/[\u064B-\u0652\u0640]/g,'');const root=(%s)||document.querySelector('#content')||document;
        const vis=e=>e.getClientRects().length>0&&getComputedStyle(e).visibility!='hidden';
        const els=[...root.querySelectorAll('input,select,textarea')].filter(e=>vis(e)&&!['hidden','checkbox','radio','file'].includes(e.type));
        const lab=e=>{let l=(e.labels&&e.labels[0]&&e.labels[0].innerText)||'';if(!l){const c=e.closest('label');if(c)l=c.innerText}if(!l){const pr=e.previousElementSibling;if(pr&&pr.innerText)l=pr.innerText}return l.trim()};
        return els.find(e=>lab(e)&&re.test(N(lab(e))))||els.find(e=>re.test(N((e.placeholder||'')+' '+(e.id||'')+' '+(e.name||'')+' '+(e.getAttribute('aria-label')||''))))||null}""" % TOP_DLG, pattern)
    el = h.as_element()
    if not el:
        if required: j.notbuilt('no field "%s"' % pattern)
        return None
    tag = el.evaluate("e=>e.tagName")
    if tag == 'SELECT':
        opts = el.evaluate("e=>[...e.options].map(o=>o.value+'|'+o.textContent.trim())")
        vpat = _ar_pattern(value)
        pick = next((o.split('|')[0] for o in opts if re.search(vpat, TASHKEEL.sub('', o), re.I)), None)
        if pick is None:
            if required: j.fail('the "%s" list has no option "%s" (options: %s)' % (pattern, value, ', '.join(o.split('|')[1] for o in opts)[:200]))
            return None
        el.select_option(pick)
    else:
        el.fill(value)
    return el

# ---- navigation ----------------------------------------------------------------------------------------------------------
def directory(j, pg):
    close_dialogs(pg)
    j.nav(pg, 'companies'); j.settle(pg, 900)
    if not pg.locator('#dxDir').count(): j.notbuilt('the Companies page has no directory')
    # a directory left on a company page comes back to the list
    if pg.locator('#hbQ').count() == 0:
        b = j.find(pg, r'^\W*(All companies|كل الشركات|جميع الشركات)\W*$', scope='#content')
        if b: b.click(); j.settle(pg, 700)
    j.check(pg.locator('#hbQ').count(), 'the Companies page shows no search box')
    return pg

def card_names(pg):
    return pg.evaluate("[...document.querySelectorAll('#dxDir .dr-card')].filter(e=>e.getClientRects().length).map(e=>(e.querySelector('.dr-name')||e).innerText.split('\\n')[0].trim())")

def card_slugs(pg):
    return pg.evaluate("[...document.querySelectorAll('#dxDir .dr-card')].filter(e=>e.getClientRects().length).map(e=>e.dataset.slug)")

def shown_count(pg):
    """The 'N companies' number the directory prints (None when it prints none)."""
    t = pg.evaluate("(document.querySelector('#dxDir')||{}).innerText||''")
    m = re.search(r'(\d[\d,]*)\s+(compan|شركة|شركات)', t)
    return int(m.group(1).replace(',', '')) if m else None

def search_dir(j, pg, q, wait=1300, want=None):
    """Type in the directory search; in live the database answers — wait (up to 10 s) until the cards settle, or until a
    card naming `want` (default: the query itself, for name searches) is shown."""
    pg.fill('#hbQ', q); pg.wait_for_timeout(wait)
    if j.live:
        end = time.time() + 10; last = None; stable = 0
        while time.time() < end:
            names = card_names(pg)
            if want and any(want in n for n in names): break
            stable = stable + 1 if names == last else 0; last = names
            if stable >= 3 and not want: break
            pg.wait_for_timeout(500)
    return card_names(pg)

def open_card(j, pg, name):
    """Open a company from its directory card ('View page') — searching for it first."""
    names = search_dir(j, pg, name, want=name)
    j.check(any(name in n for n in names), 'the directory search for "%s" does not list it (cards: %s)' % (name, ', '.join(names[:6])))
    card = pg.locator('#dxDir .dr-card', has_text=name).first
    btn = card.locator('[data-hopen], button:has-text("View page"), button:has-text("عرض الصفحة")').first
    j.check(btn.count(), 'not built: the card of %s has no "View page"' % name)
    btn.click(); j.settle(pg, 1200)
    j.check(name in j.text(pg)[:600], 'View page did not open the page of %s' % name)
    return pg

def company_tab(j, pg, pattern, what):
    """A tab of the company page (the tab bar scrolls sideways on a phone: the tab is scrolled into view first)."""
    t = pg.locator('#content [role=tab], #content .cp-tab, #content button').filter(has_text=re.compile(r'^\W*(%s)\W*(\(\d+\))?$' % pattern))
    if not t.count(): j.notbuilt('no "%s" tab on the company page' % what)
    t.first.scroll_into_view_if_needed(); t.first.click(); pg.wait_for_timeout(700)
    return j.text(pg)

def tab_count(pg, pattern):
    t = pg.evaluate("p=>{const re=new RegExp(p,'i');const b=[...document.querySelectorAll('#content button')].find(e=>e.getClientRects().length&&re.test(e.innerText));return b?b.innerText:''}", pattern)
    m = re.search(r'\((\d+)\)', t or '')
    return int(m.group(1)) if m else None

def workspace(j, pg, tab=None):
    """Open my company's workspace as a person does: the company page → 'Open company workspace' (or the top-bar company
    switcher → '<company>'s workspace')."""
    close_dialogs(pg)
    if not pg.locator('#content .hb-ws, #content [data-wtab]').count():
        sw = pg.locator('#dxCoSwitch:visible')
        if sw.count():
            sw.click(); pg.wait_for_timeout(300)
            it = pg.locator('#dxCoMenu [data-cs-ws]')
            if it.count(): it.click(); j.settle(pg, 900)
        if not re.search(r'COMPANY WORKSPACE|مساحة عمل الشركة|مساحة العمل', j.text(pg)[:300], re.I):
            directory(j, pg)
            mine = pg.evaluate("(window.dxDir&&dxDir.mine&&dxDir.mine())?dxDir.mine().name:''")
            j.check(mine, 'not built: this account has no company to open a workspace for')
            open_card(j, pg, mine)
            j.click(pg, r'Open company workspace|افتح مساحة عمل|مساحة عمل الشركة', scope='#content', what='Open company workspace', settle=900)
    j.check(re.search(r'COMPANY WORKSPACE|مساحة عمل|مساحة العمل', j.text(pg)[:400], re.I), 'the company workspace did not open')
    if tab:
        t = pg.locator('#content [data-wtab]').filter(has_text=re.compile(r'^\W*(%s)\W*$' % tab))
        if not t.count(): j.notbuilt('no "%s" tab in the company workspace' % tab.split('|')[0])
        t.first.scroll_into_view_if_needed(); t.first.click(); j.settle(pg, 800)
    return j.text(pg)

# ---- requests & deals ------------------------------------------------------------------------------------------------------
def deals_centre(j, pg, tab=None):
    close_dialogs(pg)
    b = pg.locator('#dxDealsBtn:visible')
    if not b.count():
        sw = pg.locator('#dxCoSwitch:visible')
        j.check(b.count(), 'not built: no visible "Requests & deals" entry at %dpx' % j.width)
    b.first.click(); pg.wait_for_timeout(900)
    j.check(re.search(r'Requests & deals|الطلبات والصفقات', dlg_text(pg)[:200]), 'the Requests & deals centre did not open')
    if tab: dlg_click(j, pg, r'^\W*(%s)\s*\(\d+\)' % tab, tab)
    return dlg_text(pg)

def open_deal(j, pg, title, tab=None):
    """Open a deal thread from the deals centre (Received/Sent tab tried in turn)."""
    pat = title[3:] if title.startswith('re:') else re.escape(title) + ('|' + re.escape(ar(title)) if ar(title) else '')
    for t in ([tab] if tab else [r'Received|المستلمة|الواردة', r'Sent|المرسلة|المُرسلة']):
        deals_centre(j, pg, t)
        el = j.find(pg, pat, scope='body')
        if el:
            el.click(); pg.wait_for_timeout(900)
            j.check(re.search(pat, dlg_text(pg)[:400]), 'the deal "%s" did not open' % title)
            return dlg_text(pg)
    j.fail('the deal "%s" is not in my Requests & deals' % title)

def deal_act(j, pg, label, fields=None, submit=None, attach=None):
    """In an open deal thread: click the action button (label = English action name), fill its form by label pattern (and
    attach the file `attach` to the form's file field) and submit with the form's own button (the same action name, or
    'Send answers'). Returns the thread text afterwards."""
    pat = L(label) if isinstance(label, str) and not label.startswith('^') else label
    j.check(dlg_open(pg), 'no deal is open')
    el = j.find(pg, pat, scope='body')
    if not el: j.notbuilt('no "%s" action in the deal (actions: %s)' % (label, ', '.join(pg.evaluate("(()=>{const d=%s;return d?[...d.querySelectorAll('button')].filter(b=>b.getClientRects().length).map(b=>b.innerText.trim()).filter(Boolean):[]})()" % TOP_DLG))[:200]))
    before = pg.evaluate("document.querySelectorAll('.dbk-ov').length")
    mark = j.toast_mark(pg); el.click(); pg.wait_for_timeout(700)
    if attach:
        f = pg.locator('.dbk-ov input[type=file]'); j.check(f.count(), 'not built: the "%s" form takes no file' % label); f.last.set_input_files(attach)
    if fields or attach:
        for pt, val in (fields or {}).items(): fill_by_label(j, pg, pt, val)
        sub = j.find(pg, submit or pat, scope='body') or j.find(pg, L('Send answers', 'Send', 'Save'), scope='body')
        j.check(sub, 'the "%s" form has no submit button' % label)
        sub.click(); pg.wait_for_timeout(900)
    j.dead_end(pg, mark, label)
    if j.live:
        try: pg.evaluate("window.dxLive&&dxLive.dealsBusy&&dxLive.dealsBusy()")
        except Exception: pass
        j.settle(pg, 1200)
    return dlg_text(pg)

def simulate(j, pg):
    """Demo: the other side's next step ('Simulate <them>'s reply (demo)')."""
    dlg_click(j, pg, r'Simulate|محاكاة', 'Simulate their reply'); pg.wait_for_timeout(700)
    return dlg_text(pg)

def deal_row(j, title_like, cols="status"):
    return j.sql1("select %s from public.deals where title like $q$%%%s%%$q$ order by id desc limit 1" % (cols, title_like))

# ---- live preconditions ------------------------------------------------------------------------------------------------------
def slugify(s): return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:40].rstrip('-')

def seed_company(j, owner, name, sectors=('Manufacturer',), status='verified', gov='Giza', city='6th of October', name_ar=None,
                 tagline='', plan='free', source='company', registry=None, phone='+20 2 3333 4444', email=None, website=None, whatsapp=None):
    """Live precondition: a company page another journey created (owner = a member uuid or None for an unclaimed page)."""
    slug = slugify(name)
    cols = "owner_id, name, slug, type, status, source, sectors, governorate, city, tagline, phone, email, website, whatsapp, name_ar, registry, licensed"
    vals = "%s, $q$%s$q$, '%s', '%s', '%s', '%s', '{%s}', '%s', '%s', $q$%s$q$, '%s', %s, %s, %s, %s, %s, %s" % (
        ("'%s'" % owner) if owner else 'null', name, slug, sectors[0], status, source, ','.join('"%s"' % s for s in sectors), gov, city, tagline, phone,
        ("'%s'" % email) if email else 'null', ("'%s'" % website) if website else 'null', ("'%s'" % whatsapp) if whatsapp else 'null',
        ("$q$%s$q$" % name_ar) if name_ar else 'null', ("'%s'" % registry) if registry else ("'%s'" % (str(_dx.STN)[-7:] + str(len(name)))) if status == 'verified' else 'null',
        'true' if status == 'verified' else 'false')
    cid = j.sql1("insert into public.companies (%s) values (%s) returning id" % (cols, vals))
    if plan == 'vip': j.sql("update public.companies set plan='vip', vip_until=now()+interval '30 days' where id=%s" % cid)
    slug = j.sql1("select slug from public.companies where id=%s" % cid)
    return {'id': cid, 'slug': slug, 'name': name}

def seed_member(j, cid, uid, role='sales', public=True):
    j.sql("insert into public.company_members (company_id, user_id, role, accepted, show_public) values (%s,'%s','%s',true,%s) on conflict (company_id,user_id) do update set role=excluded.role, accepted=true" % (cid, uid, role, 'true' if public else 'false'))

def seed_route(j, cid, kind, uid):
    j.sql("insert into public.company_routing (company_id, request_type, user_id) values (%s,'%s','%s') on conflict do nothing" % (cid, kind, uid))

def seed_site(j, cid, name='October plant', forms=('Tablets',), capacity='40 M tablets / month', min_batch='200,000 tablets', slots=None, gov='Giza', city='6th of October'):
    return j.sql1("insert into public.company_sites (company_id, name, type, city, governorate, dosage_forms, capacity, min_batch, free_slots) values (%s, $q$%s$q$, 'factory', '%s', '%s', '{%s}', '%s', '%s', '%s') returning id" % (
        cid, name, city, gov, ','.join('"%s"' % f for f in forms), capacity, min_batch, json.dumps([_month(i) for i in (slots or [])])))

def _month(i):
    """Free production months are stored as 'YYYY-MM' (0050); a journey names them as 0 = this month, 1 = next month…"""
    t = time.localtime(); m = t.tm_mon - 1 + int(i)
    return '%04d-%02d' % (t.tm_year + m // 12, m % 12 + 1)

def seed_cert(j, cid, sid, name='WHO-GMP', expiry='2027-06-30', checked=True):
    return j.sql1("insert into public.site_certificates (site_id, company_id, name, expiry, checked_at) values (%s,%s,'%s','%s',%s) returning id" % (sid, cid, name, expiry, 'now()' if checked else 'null'))

def seed_product(j, cid, name, ingredient, ingredient_ar='', form='Tablet', strength='500 mg', role='manufacturer'):
    return j.sql1("insert into public.company_products (company_id, name, active_ingredient, active_ingredient_ar, dosage_form, strength, role) values (%s,$q$%s$q$,$q$%s$q$,$q$%s$q$,'%s','%s','%s') returning id" % (cid, name, ingredient, ingredient_ar, form, strength, role))

def seed_listing(j, uid, name, type_='supply', category='api', price='5.80', unit='kg', moq='500 kg'):
    return j.sql1("insert into public.products (user_id, name, category, type, price, unit, moq, active) values ('%s',$q$%s$q$,'%s','%s','%s','%s','%s',true) returning id" % (uid, name, category, type_, price, unit, moq))

def make_admin(j, uid): j.sql("update public.profiles set role='admin' where id='%s'" % uid)

def acting(pg):
    return pg.evaluate("(window.dxDir&&dxDir.mine&&dxDir.mine())?dxDir.mine().slug:''")

def live_company_person(j, pname, cname, role=None, **kw):
    """Live: a fresh account (signed up through the UI) that owns a company page (precondition), page reloaded."""
    p = j.person(pname)
    c = seed_company(j, p['id'], cname, **kw)
    if role: seed_member(j, c['id'], p['id'], role)
    j.reload(p['page'])
    p['co'] = c
    return p

# ---- payments (live) -----------------------------------------------------------------------------------------------------------
PM_FIELDS = ['amount_cents', 'created_at', 'currency', 'error_occured', 'has_parent_transaction', 'id', 'integration_id', 'is_3d_secure', 'is_auth', 'is_capture', 'is_refunded',
             'is_standalone_payment', 'is_voided', 'order.id', 'owner', 'pending', 'source_data.pan', 'source_data.sub_type', 'source_data.type', 'success']
def fn_env():
    try: return _dx.fn_env()
    except SystemExit as e: raise StepFail('payments are not running: %s' % str(e)[:200])

def paymob_sign(o, secret):
    s = ''.join(('true' if v is True else 'false' if v is False else str(v)) for v in (functools.reduce(lambda a, k: a[k], f.split('.'), o) for f in PM_FIELDS))
    return hmac.new(secret.encode(), s.encode(), hashlib.sha512).hexdigest()

def paymob_callback(j, oid, success=True, integration=111111, forge=False, src_type='card'):
    env = fn_env()
    row = j.sql1("select merchant_ref||'|'||amount_cents||'|'||coalesce(provider_order,'') from public.payment_orders where id=%s" % oid)
    ref, cents, po = row.split('|')
    o = {'id': 880000 + int(oid), 'pending': False, 'amount_cents': int(cents), 'success': success, 'is_auth': False, 'is_capture': False, 'is_standalone_payment': True, 'is_voided': False,
         'is_refunded': False, 'is_3d_secure': True, 'integration_id': integration, 'has_parent_transaction': False, 'error_occured': not success, 'currency': 'EGP',
         'created_at': '2026-10-11T12:00:00.000000', 'owner': 4242, 'order': {'id': int(po) if po.isdigit() else 991000 + int(oid), 'merchant_order_id': ref},
         'source_data': {'pan': '2346', 'type': src_type, 'sub_type': 'MasterCard' if src_type == 'card' else 'wallet'}}
    sig = 'f' * 128 if forge else paymob_sign(o, env['PAYMOB_HMAC_SECRET'])
    return post(_dx.APP_URL.rstrip('/') + '/functions/v1/paymob-webhook?hmac=' + sig, {'type': 'TRANSACTION', 'obj': o})

def fawry_callback(j, oid, status='PAID', forge=False):
    env = fn_env()
    ref, cents, fref = j.sql1("select merchant_ref||'|'||amount_cents||'|'||coalesce(provider_ref,'') from public.payment_orders where id=%s" % oid).split('|')
    amt = int(cents) / 100.0
    b = {'requestId': 'r%s' % oid, 'fawryRefNumber': fref, 'merchantRefNumber': ref, 'customerMobile': '01000000000', 'customerMail': 'x@x.test', 'paymentAmount': amt, 'orderAmount': amt,
         'fawryFees': 0.0, 'orderStatus': status, 'paymentMethod': 'PAYATFAWRY', 'paymentTime': int(time.time() * 1000), 'paymentRefrenceNumber': '99%s' % oid}
    s = b['fawryRefNumber'] + b['merchantRefNumber'] + '%.2f' % b['paymentAmount'] + '%.2f' % b['orderAmount'] + b['orderStatus'] + b['paymentMethod'] + b['paymentRefrenceNumber'] + env['FAWRY_SECURE_KEY']
    b['messageSignature'] = 'ab' * 32 if forge else hashlib.sha256(s.encode()).hexdigest()
    return post(_dx.APP_URL.rstrip('/') + '/functions/v1/fawry-webhook', b)

def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as r: return r.status, r.read().decode()
    except urllib.error.HTTPError as e: return e.code, e.read().decode()
    except Exception as e: return 0, str(e)

def money(t):
    """Every 'EGP 1,653'-style amount in a text, as numbers."""
    t = (t or '').translate(str.maketrans('٠١٢٣٤٥٦٧٨٩٬', '0123456789,'))
    return [float(x.replace(',', '')) for x in re.findall(r'EGP\s*([\d,]+(?:\.\d+)?)', t) + re.findall(r'([\d,]+(?:\.\d+)?)\s*(?:ج\.م|جنيه)', t)]

# ---- language and phone checks --------------------------------------------------------------------------------------------------
_I18N = {}
def _load_i18n():
    if _I18N: return _I18N
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'web', 'src', 'i18n.js')
    try: s = open(p, encoding='utf-8').read()
    except Exception: return _I18N
    for m in re.finditer(r"'((?:[^'\\]|\\.){1,80})'\s*:\s*'((?:[^'\\]|\\.){1,120})'", s):
        _I18N.setdefault(m.group(1).replace("\\'", "'"), m.group(2).replace("\\'", "'"))
    for m in re.finditer(r'"((?:[^"\\]|\\.){1,80})"\s*:\s*"((?:[^"\\]|\\.){1,120})"', s):
        _I18N.setdefault(m.group(1), m.group(2))
    return _I18N

def ar(en): return _load_i18n().get(en)

def L(*labels, exact=True, extra=''):
    """A regex matching the interface label in English or its Arabic translation (from web/src/i18n.js)."""
    alts = []
    for en in labels:
        alts.append(re.escape(en))
        a = ar(en)
        if a: alts.append(re.escape(a))
    if extra: alts.append(extra)
    body = '|'.join(alts)
    return (r'^\W*(%s)\W*(\(\d+\))?$' % body) if exact else '(%s)' % body

UI_LABELS = ['View page', 'Request a quote', 'Message', '+ Follow', 'Questionnaire', 'Profile PDF', 'Share card', 'Report wrong information', 'Overview', 'Contact',
             'Send request', 'Open company workspace', 'Add or claim your company', 'Invite a colleague', 'Add a site', 'Edit page', 'Save', 'Send quote', 'Accept quote',
             'Counter-offer', 'Decline', 'Withdraw', 'Confirm order', 'Mark shipped', 'Confirm received', 'Rate supplier', 'Send proposal', 'Start work', 'Mark delivered',
             'Answer questionnaire', 'Approve supplier', 'Reject', 'Sign NDA', 'Share details', 'Agree terms', 'Post surplus', 'Make an offer', 'Clear filters', 'Close', 'Cancel',
             'Do it', 'Still correct', 'Claim', 'Claim this page', 'Ask to join the team', 'Get verified', 'Upgrade', 'Continue to payment', 'Mark fixed', 'Send questionnaire',
             'Back', 'Show more', 'Select', 'Directory health', 'Start group', 'Join', 'Reply', 'Next: review', 'Create my page', 'Add document', 'Hide me']

def ui_ok(j, pg, where=''):
    """Arabic: no interface label of this screen is left in English; phone: the screen fits (no sideways scroll)."""
    if j.ar:
        left = pg.evaluate("""(labels)=>{const d=%s;const root=d||document.querySelector('#content')||document.body;const vis=e=>e.getClientRects().length&&getComputedStyle(e).visibility!='hidden';
            return [...new Set([...root.querySelectorAll('button,a,[role=tab],label,h1,h2,h3')].filter(vis).map(e=>(e.innerText||'').replace(/\\s+/g,' ').trim()).filter(t=>labels.includes(t)))]}""" % TOP_DLG, UI_LABELS)
        j.check(not left, 'not translated in Arabic%s: %s' % ((' (' + where + ')') if where else '', ', '.join('"%s"' % x for x in left[:6])))
        j.check(pg.evaluate("(document.documentElement.getAttribute('dir')||document.body.getAttribute('dir')||getComputedStyle(document.body).direction)") in ('rtl',), 'the Arabic page is not right-to-left')
    if j.width <= 480:
        sw = pg.evaluate("Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - innerWidth")
        j.check(sw <= 2, 'at %dpx the screen%s scrolls sideways by %dpx' % (j.width, (' (' + where + ')') if where else '', sw))

def reopen(j, pg):
    """Reload the app. The demo keeps no session (its data stays in the browser): it signs in again with the demo account.
    Demo only: Playwright's instrumented reload of the file:// demo sometimes comes back without the page's last committed
    localStorage writes (0 of 24 plain reloads lose one; about 1 in 10 under the harness). A person's browser keeps them,
    so what the page had stored before the reload is put back when the reload lost it (recorded in the result as
    data.storage_restored) — anything the page never stored is not invented."""
    snap = None
    if j.demo:
        pg.wait_for_timeout(int(os.environ.get('BIZ_RELOAD_PAUSE', '1500')))
        snap = pg.evaluate("Object.fromEntries(Object.keys(localStorage).filter(k=>k.startsWith('dx_')||k.startsWith('dbx_')).map(k=>[k,localStorage.getItem(k)]))")
    for attempt in range(3):
        j.reload(pg)
        if not snap: break
        lost = pg.evaluate("s=>Object.keys(s).filter(k=>localStorage.getItem(k)!==s[k])", snap)   # gone, or back to an older value (the last write lost)
        if not lost: break
        j.data.setdefault('storage_restored', []).extend(lost)
        pg.evaluate("s=>{for(const k in s)if(localStorage.getItem(k)!==s[k])localStorage.setItem(k,s[k])}", snap)
        pg.wait_for_timeout(1500)
    if j.demo and j.on_login(pg): j.demo_signin(pg)
    return pg

if os.environ.get('BIZ_CAL'):                                # calibration only: report every failed check and carry on
    import _j as _jm
    def _cal_check(self, cond, reason):
        if not cond: print('   CAL-FAIL step %d: %s' % (self.n, reason), flush=True)
        return cond
    def _cal_fail(self, reason): print('   CAL-FAIL step %d: %s' % (self.n, reason), flush=True)
    def _cal_nb(self, what): print('   CAL-FAIL step %d: not built: %s' % (self.n, what), flush=True)
    _jm.J.check = _cal_check; _jm.J.fail = _cal_fail; _jm.J.notbuilt = _cal_nb

# ---- Drugbox admin → Review ----------------------------------------------------------------------------------------------------
QUEUES = {'verifications': r'Verification requests|طلبات التوثيق', 'certs': r'Site certificates|شهادات', 'reports': r'Company reports|بلاغات', 'payments': r'Payments|المدفوعات', 'claims': r'Claims|المطالبات|Claim', 'documents': r'Compliance documents|مستندات الامتثال'}
def admin_review(j, pg, queue):
    """Admin → Review → the queue tab; returns the list text. A queue that does not exist fails 'not built'."""
    close_dialogs(pg)
    a = pg.locator("#app [onclick=\"goto('admin')\"]")
    if not a.count(): j.notbuilt('no Admin entry for a Drugbox admin')
    if not a.first.is_visible() and pg.locator('#sbToggle:visible').count(): pg.click('#sbToggle'); pg.wait_for_timeout(400)
    a.first.scroll_into_view_if_needed()
    try: a.first.click(timeout=5000)
    except Exception: a.first.evaluate('e=>e.click()')            # a phone sidebar footer that the page overlay covers
    j.settle(pg, 900)
    rv = pg.locator('.admin-nav [data-review]:visible')
    j.check(rv.count(), 'not built: Admin has no Review entry'); rv.first.click(); j.settle(pg, 1500)
    j.wait(pg, "!document.querySelector('.dx-mod-empty')||!/Loading/.test(document.querySelector('.dx-mod-empty').innerText)", 10)
    tab = pg.evaluate_handle("p=>[...document.querySelectorAll('.dx-mod-tab')].find(t=>new RegExp(p,'i').test(t.innerText))||null", QUEUES.get(queue, queue)).as_element()
    if not tab: j.notbuilt('Admin → Review has no "%s" queue (queues: %s)' % (queue, ', '.join(pg.evaluate("[...document.querySelectorAll('.dx-mod-tab')].map(t=>t.innerText.trim())"))))
    tab.click(); pg.wait_for_timeout(500)
    return pg.evaluate("(document.querySelector('.dx-mod-list')||{}).innerText||''")

def admin_decide(j, pg, needle, ok=True, reason='The document is not readable'):
    row = pg.locator('.dx-mod-row', has_text=needle)
    j.check(row.count(), 'the review queue has no row for "%s"' % needle)
    btn = row.first.locator('.dx-mod-ok' if ok else '.dx-mod-no')
    j.check(btn.count(), 'not built: the row has no %s button' % ('approve' if ok else 'reject'))
    if not ok: pg.once('dialog', lambda d: d.accept(reason))
    btn.first.click(); pg.wait_for_timeout(700)
    if dlg_open(pg):
        if not ok:                                              # the reason is written in the window (a kit window, not a browser prompt)
            f = pg.locator('.dbk-ov textarea:visible, .dbk-ov input[type=text]:visible')
            if f.count(): f.last.fill(reason)
        b = pg.locator('.dbk-ov [data-a=ok], .dbk-ov button.p, .dbk-ov button.danger, .dbk-ov .dbk-p').last
        if b.count(): b.click()
    j.settle(pg, 1200)

def dlg_buttons(pg):
    return pg.evaluate("(()=>{const d=%s;return d?[...d.querySelectorAll('button')].filter(b=>b.getClientRects().length).map(b=>b.innerText.trim()).filter(Boolean):[]})()" % TOP_DLG)

def deal_row_text(pg, title):
    """In the open deals centre: the text of the row for a deal."""
    return pg.evaluate("t=>{const d=%s;if(!d)return '';const b=[...d.querySelectorAll('button')].find(b=>b.innerText.includes(t));return b?b.innerText:''}" % TOP_DLG, title)

# ---- moved from the journey files (shared by several) -------------------------------------------------------------------
def buyer_and_supplier(j, sup_name, product=None, sup_sector='API & excipients', buyer_name=None):
    """Live: a buyer company and a supplier company (each a fresh account through the UI); the supplier routes quote
    requests to its owner and lists a product. Demo: Quadra Pharm (the demo account) and a sample supplier."""
    if j.demo:
        pg = j.demo_signin(j.new_page())
        return {'page': pg}, None, 'Medsinia Industries', 'Paracetamol 500 mg'
    b = live_company_person(j, 'Eng. Karim Buyer', buyer_name or 'Nile Valley Buyer %s' % j.tag, sectors=('Manufacturer',), gov='Giza')
    s = live_company_person(j, 'Hany Supplier Sales', '%s %s' % (sup_name, j.tag), sectors=(sup_sector,), gov='Cairo')
    seed_route(j, s['co']['id'], 'quote', s['id'])
    prod = product and '%s %s' % (product, j.tag)
    if prod: seed_product(j, s['co']['id'], prod, product, '', 'API powder', '', 'supplier')
    j.reload(b['page']); j.reload(s['page'])
    return b, s, s['co']['name'], prod


def request_quote(j, pg, sup, product=None, qty='500', unit='kg', to='Cairo, Egypt', inc='CIF', msg='CEP grade, CoA with each batch'):
    directory(j, pg); open_card(j, pg, sup)
    j.click(pg, L('Request a quote'), scope='#content', what='Request a quote')
    j.check(dlg_open(pg), 'Request a quote opened no form')
    if product: fill_by_label(j, pg, r'^(Product|منتج|المنتج)', re.escape(product))
    fill_by_label(j, pg, r'Quantity|الكمية', qty); fill_by_label(j, pg, r'^Unit|الوحدة', unit, required=False)
    fill_by_label(j, pg, r'Deliver to|التسليم إلى|التوصيل', to, required=False); fill_by_label(j, pg, r'Delivery terms|شروط', inc, required=False)
    by = pg.locator('#rqBy')
    if by.count(): by.fill('2026-12-15')
    fill_by_label(j, pg, r'Message|الرسالة', msg)
    mark = j.toast_mark(pg); dlg_click(j, pg, L('Send request'), 'Send request'); j.settle(pg, 1200)
    return j.toasts_since(pg, mark)


def their_move(j, pg, other, title, label, fields=None, attach=None):
    """The other party's next step: in live, as that company in its own browser (deals centre → the deal → action);
    in the demo, 'Simulate <them>'s reply (demo)'."""
    if j.demo:   # the demo account is the other party's counterpart: its own request is under Sent (a received sample may share the title)
        try: open_deal(j, pg, title, r'Sent|المرسلة|المُرسلة')
        except StepFail: open_deal(j, pg, title)
        t = simulate(j, pg); close_dialogs(pg); return t
    op = other['page']; j.reload(op); open_deal(j, op, title, r'Received|الواردة')
    t = deal_act(j, op, label, fields, attach=attach); close_dialogs(op)
    j.reload(pg)                                             # the next time this side opens the app
    return t


def status_of(j, pg, title):
    """The status the deal centre shows for a deal (as the page's user sees it)."""
    t = open_deal(j, pg, title); close_dialogs(pg); return t


def live_deal(j, title, cols='status'):
    return j.sql1("select %s from public.deals where title like $q$%%%s%%$q$ order by id desc limit 1" % (cols, title))


def add_or_claim(j, pg, q):
    directory(j, pg)
    j.click(pg, L('Add or claim your company'), scope='#content', what='Add or claim your company')
    box = pg.locator('#acQ:visible'); j.check(box.count(), "'Add or claim your company' has no company-name search")
    box.fill(q); pg.wait_for_timeout(1200)
    if j.live:
        end = time.time() + 10
        while time.time() < end and not re.search(re.escape(q.split(' ')[0]), dlg_text(pg).split('Company name')[-1]): pg.wait_for_timeout(500)
        pg.wait_for_timeout(500)
    return dlg_text(pg)


def wizard_details(j, pg, name, sector=r'Manufacturer|مصنع', gov=r'Giza|الجيزة', city='Dokki', phone='+20 100 555 0101', email=None):
    fill_by_label(j, pg, r'legal name|الاسم القانوني|ccN', name)
    fill_by_label(j, pg, r'Main activity|النشاط', sector); fill_by_label(j, pg, r'Governorate|المحافظة', gov)
    fill_by_label(j, pg, r'City|المدينة', city); fill_by_label(j, pg, r'phone|الهاتف', phone)
    fill_by_label(j, pg, r'email|البريد', email or 'info.%s@newco.example' % j.tag)


def create_company(j, pg, name, plan='free', billing='month'):
    """The create wizard from 'Add or claim your company' up to its last step (returns the last step's text)."""
    t = add_or_claim(j, pg, name)
    dlg_click(j, pg, r'not listed|create it|غير مدرجة|أنشئ', 'My company is not listed — create it')
    pick = pg.locator('.dbk-ov input[name=plPick][value=%s]' % plan)
    j.check(pick.count(), 'the wizard offers no %s plan' % plan); pick.first.check()
    if plan == 'vip':
        bl = pg.locator('.dbk-ov input[name=plBill][value=%s]' % billing)
        if bl.count(): bl.first.check()
    dlg_click(j, pg, L('Next: company details'), 'Next: company details')
    return pg


def my_companies(j, pg):
    """Top-bar company switcher → 'Manage my companies' (the My companies dialog); returns its text."""
    close_dialogs(pg)
    sw = pg.locator('#dxCoSwitch:visible'); j.check(sw.count(), 'no company switcher in the top bar at %dpx' % j.width)
    sw.click(); pg.wait_for_timeout(400)
    it = pg.locator('#dxCoMenu [data-cs-all]'); j.check(it.count(), "the switcher has no 'Manage my companies'")
    it.click(); pg.wait_for_timeout(700)
    return dlg_text(pg)

def chip_info(pg, name):
    """What a person reads about a certificate on the page: the text around it plus the tooltips (title) of its chips."""
    return pg.evaluate("""n=>[...document.querySelectorAll('#content *')].filter(e=>e.children.length<4&&(e.innerText||'').includes(n)).map(e=>(e.innerText||'')+' '+(e.getAttribute('title')||'')+' '+[...e.querySelectorAll('[title]')].map(x=>x.title).join(' ')).join(' | ')""", name)

def editor_add_product(j, pg, name, photo=True):
    """In the open page editor: 'Add a product' → name (+ photo) → 'Add product'."""
    j.click(pg, r'^\W*(Add a product|أضف منتجًا)\W*$', scope='body', what='Add a product'); pg.wait_for_timeout(400)
    fill_by_label(j, pg, r'Product name|اسم المنتج', name)
    if photo:
        ph = pg.locator('#edPFile, #dxEditor input[type=file][id^=edP]')
        j.check(ph.count(), 'not built: a product cannot have a photo'); ph.first.set_input_files(PNG); pg.wait_for_timeout(500)
    mark = j.toast_mark(pg)
    j.click(pg, r'^\W*(Add product|أضف المنتج)\W*$', scope='body', what='Add product'); pg.wait_for_timeout(500)
    return j.toasts_since(pg, mark)

# (the reload-safe init script now lives in _j.J.new_ctx itself)
