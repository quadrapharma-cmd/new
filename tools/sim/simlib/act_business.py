"""Business actions: companies, team, sites, certificates, verification, claims, deals (RFQ → quote → deal → rate, service,
questionnaire, dossier, surplus, buying groups), marketplace, intents and payments through the local stand-in (J-BUSINESS-01…49)."""
import datetime, hashlib, hmac, json, random, urllib.parse as up

from .catalog import action, Fail, Skip, NotBuilt, Limited
from .act_social import PCOLS, fixture
from .personas import APIS, FORMS
from . import safety

TODAY = lambda: datetime.date.today()


def my_companies(x, roles=None):
    """(id, slug, role) of the companies I own or am an accepted member of."""
    rows = x.db.q("select c.id, c.slug, case when c.owner_id=%s then 'owner' else m.role end from public.companies c left join public.company_members m on m.company_id=c.id and m.user_id=%s and m.accepted "
                  "where c.status <> 'suspended' and (c.owner_id=%s or m.user_id is not null)", (x.me, x.me, x.me))
    return [r for r in rows if roles is None or r[2] in roles]


def my_company(x, roles=None, why='not on a company team yet'):
    rows = my_companies(x, roles); return x.r.choice(rows) if rows else x.need(None, why)


def sim_company(x, exclude=(), types=None):
    """Another simulated company that can receive requests (claimed, not suspended)."""
    rows = x.db.q("select id, slug, type from public.companies where owner_id is not null and status <> 'suspended' and slug like 'sim-%%' and not (id = any(%s))" +
                  (" and type = any(%s)" if types else ''), (list(exclude),) + ((list(types),) if types else ()))
    return x.r.choice(rows) if rows else None


def ref(x, p): return '%s%s' % (p, x.r.getrandbits(40))


# ── directory and company pages ────────────────────────────────────────────────────────────────────────────────────────
@action('dir.search', 'business', ['J-BUSINESS-01', 'J-BUSINESS-02', 'J-SOCIAL-45'], dict(trade=3, social=0.5, hire=0.5))
def dir_search(x):
    q = x.r.choice([None, None, 'pharma', 'CMO', 'distribution', 'القاهرة', x.r.choice(APIS).split()[0], x.p.get('city', 'Cairo')])
    r = x.ok(x.acc.rpc('directory_companies_page', {'p_limit': 100, 'p_offset': 0, 'p_q': q}), 'the directory page')
    if not isinstance(r.data, (dict, list)): raise Fail('the directory did not answer a page: ' + r.repro())
    if x.r.random() < 0.4:
        x.ok(x.acc.rpc('search_companies', {'q': q or '', 'p_sector': x.r.choice([None, 'CMO / Toll', 'Manufacturer', 'Distributor']), 'p_gov': None, 'p_limit': 20, 'p_after': None}), 'filtered search (CMO with free capacity)')
    x.target = 'q=%r' % q


@action('co.view', 'business', ['J-BUSINESS-04', 'J-BUSINESS-06', 'J-BUSINESS-11'], dict(trade=3, social=1, seek=1))
def co_view(x):
    c = x.need(sim_company(x), 'no companies yet'); cid, slug = c[0], c[1]; x.target = slug
    sel = up.quote('*,products:company_products!company_products_company_id_fkey(name,ingredient:active_ingredient,ingredient_ar:active_ingredient_ar,form:dosage_form,strength,role)', safe=',*()!:')
    d = x.rows(x.acc.get('companies', 'select=%s&slug=eq.%s' % (sel, slug)), 'open the company page')[0]
    if d['id'] != cid: raise Fail('the page shows another company')
    x.ok(x.acc.rpc('company_sites_public', {'p_slug': slug}), 'sites and capacity')
    x.ok(x.acc.rpc('company_track_record', {'p_company': cid}), 'track record')
    x.ok(x.acc.rpc('company_ratings', {'p_ids': [cid]}), 'ratings')
    x.ok(x.acc.rpc('company_contacts', {'p_company': cid}), 'who to contact')
    x.ok(x.acc.get('jobs', 'select=id,title&active=eq.true&company=eq.%s&limit=20' % up.quote(d.get('name') or '')), 'its jobs')


@action('co.follow', 'business', ['J-BUSINESS-05'], dict(trade=1, social=0.5, seek=0.5))
def co_follow(x):
    c = x.need(sim_company(x)); cid = c[0]; x.target = c[1]
    if x.db.val("select 1 from public.company_followers where company_id=%s and user_id=%s", (cid, x.me)):
        x.ok(x.acc.delete('company_followers', 'company_id=eq.%s&user_id=eq.%s' % (cid, x.me), select=None), 'unfollow the company')
    else:
        x.ok(x.acc.insert('company_followers', {'company_id': cid, 'user_id': x.me}, select=None), 'follow the company')
    x.dbwait("select (select follower_count from public.companies where id=%s) = (select count(*) from public.company_followers where company_id=%s)", (cid, cid), True, 'follower_count equals followers')


@action('co.message', 'business', ['J-BUSINESS-06', 'J-BUSINESS-35'], dict(trade=2))
def co_message(x):
    c = x.need(sim_company(x, exclude=[r[0] for r in my_companies(x)])); cid = c[0]; x.target = c[1]
    x.ok(x.acc.rpc('company_contacts', {'p_company': cid}), 'who to contact')
    body = 'Hello, we are interested in %s. Could your team send a quotation? (simulated)' % x.r.choice(APIS)
    r = x.ok(x.acc.rpc('company_message', {'p_company': cid, 'p_body': body}), 'message the company')
    x.dbwait("select count(*) from public.messages where sender_id=%s and body=%s", (x.me, body), lambda v: v >= 1, 'the message reached a person on the team')


@action('co.create', 'business', ['J-BUSINESS-12'], dict(trade=1), who='owner')
def co_create(x):
    c = x.sim.company_of(x.p)
    if not c: raise Skip('no company in my persona')
    have = x.db.val("select slug from public.companies where owner_id=%s and name=%s", (x.me, c['name']))
    if have: raise Skip('my company exists (%s)' % have)
    row = {'owner_id': x.me, 'name': c['name'], 'slug': 'sim-' + c['slug'], 'type': c['type'], 'sectors': c['sectors'], 'city': c['city'], 'governorate': c['governorate'],
           'location': '%s, Egypt' % c['city'], 'phone': c['phone'], 'email': None, 'whatsapp': None, 'tagline': c['tagline']}
    d = x.rows(x.acc.insert('companies', row), 'create the company page')[0]
    x.target = d['slug']; c['id'] = d['id']; c['db_slug'] = d['slug']
    x.expect("select status||'|'||plan||'|'||(owner_id=%s)::text from public.companies where id=%s", (x.me, d['id']), 'pending|free|true', 'a new page starts pending, free, mine')
    # a member cannot make their page verified or VIP from the browser
    r = x.acc.update('companies', 'id=eq.%s' % d['id'], {'status': 'verified', 'plan': 'vip'}, select='id')
    if r.ok and r.data: raise Fail('the owner could verify / upgrade the page from the browser')
    x.expect("select status from public.companies where id=%s", (d['id'],), 'pending', 'still pending after a forged update')


@action('co.update', 'business', ['J-BUSINESS-16'], dict(trade=1), who='company')
def co_update(x):
    cid, slug, role = my_company(x, ('owner', 'admin'), 'not an owner or admin'); x.target = slug
    upd = {'tagline': x.r.choice(['GMP-certified since 1998', 'EU-GMP oral solids', 'Same-day delivery in Greater Cairo', 'WHO-PQ API supplier']),
           'bio': 'Simulated company page. We make and supply %s.' % ', '.join(x.r.sample(APIS, 2)), 'hours': 'Sun–Thu 9:00–17:00',
           'website': 'https://%s.example.org' % slug[:30], 'founded': x.r.randint(1975, 2022), 'employees': x.r.choice(['11–50', '51–200', '201–500'])}
    x.rows(x.acc.update('companies', 'id=eq.%s' % cid, upd), 'save the page')
    x.expect("select tagline from public.companies where id=%s", (cid,), upd['tagline'], 'the page is saved')


@action('co.invite', 'business', ['J-BUSINESS-15', 'J-BUSINESS-17'], dict(trade=1, hire=1), who='owner')
def co_invite(x):
    mine = [r for r in my_companies(x, ('owner',))]
    x.need(mine, 'no company yet'); cid, slug, _ = mine[0]
    want = [q for u, q in x.w.people.items() if q.get('company') == x.p.get('company') and q.get('uid') and q['company_role'] != 'owner']
    pending = [q for q in want if not x.db.val("select 1 from public.company_members where company_id=%s and user_id=%s", (cid, q['uid']))]
    q = x.need(x.r.choice(pending) if pending else None, 'everyone is invited'); x.target = '%s → %s' % (slug, q['email'])
    x.ok(x.acc.insert('company_members', {'company_id': cid, 'user_id': q['uid'], 'role': q['company_role'] if q['company_role'] != 'procurement' else 'member', 'accepted': False, 'show_public': True}, select=None), 'invite a colleague to the team')
    x.expect("select accepted from public.company_members where company_id=%s and user_id=%s", (cid, q['uid']), False, 'the invitation waits for them')


@action('co.join', 'business', ['J-BUSINESS-15'], dict(trade=2, social=2, hire=2, seek=2, learn=2, group=2), who='employee', path='api')
def co_join(x):
    row = x.need(x.pick("select company_id from public.company_members where user_id=%s and not accepted", (x.me,)), 'no team invitation')
    x.target = 'company %s' % row[0]
    x.rows(x.acc.update('company_members', 'company_id=eq.%s&user_id=eq.%s' % (row[0], x.me), {'accepted': True}, select='company_id'), 'accept the team invitation')
    x.expect("select accepted from public.company_members where company_id=%s and user_id=%s", (row[0], x.me), True, 'on the team')


@action('co.routing', 'business', ['J-BUSINESS-17'], dict(trade=0.5), who='owner', path='api')
def co_routing(x):
    cid, slug, _ = my_company(x, ('owner',))
    m = x.need(x.pick("select user_id, role from public.company_members where company_id=%s and accepted and user_id<>%s", (cid, x.me)), 'no team yet')
    t = {'sales': 'quote', 'quality': 'questionnaire', 'regulatory': 'dossier', 'admin': 'job', 'hr': 'job'}.get(m[1], x.r.choice(['quote', 'service', 'surplus']))
    x.target = '%s %s → %s' % (slug, t, m[0])
    x.ok(x.acc.insert('company_routing', {'company_id': cid, 'request_type': t, 'user_id': m[0]}, select=None, upsert='company_id,request_type'), 'route a request type to a colleague')
    x.expect("select user_id from public.company_routing where company_id=%s and request_type=%s", (cid, t), m[0], 'the routing is stored')


@action('co.site', 'business', ['J-BUSINESS-18', 'J-BUSINESS-02'], dict(trade=0.5), who='company', path='api')
def co_site(x):
    cid, slug, _ = my_company(x, ('owner', 'admin'))
    if x.db.val("select count(*) from public.company_sites where company_id=%s", (cid,)) >= 3: raise Skip('enough sites')
    row = {'company_id': cid, 'name': '%s plant %d' % (x.p.get('city', 'Cairo'), x.r.randint(1, 9)), 'type': x.r.choice(['factory', 'warehouse', 'lab']), 'city': x.p.get('city'),
           'governorate': x.p.get('governorate'), 'dosage_forms': x.r.sample(FORMS, 2), 'min_batch': '%dk units' % x.r.choice([20, 50, 100]),
           'capacity': '%d M units/yr' % x.r.randint(5, 120), 'free_slots': {'from': str(TODAY() + datetime.timedelta(days=30)), 'lines': x.r.randint(1, 3)}}
    d = x.rows(x.acc.insert('company_sites', row), 'add a manufacturing site')[0]; x.target = 'site %s' % d['id']
    s = x.ok(x.acc.rpc('company_sites_public', {'p_slug': slug}), 'the public sites list')
    if row['name'] not in json.dumps(s.data, ensure_ascii=False): raise Fail('the new site is not on the public page')


@action('co.cert', 'business', ['J-BUSINESS-19'], dict(trade=0.3), who='company', path='api')
def co_cert(x):
    cid, slug, _ = my_company(x, ('owner', 'admin', 'quality'))
    site = x.need(x.pick("select id from public.company_sites where company_id=%s", (cid,)), 'no site yet')
    d = x.rows(x.acc.insert('site_certificates', {'site_id': site[0], 'company_id': cid, 'name': x.r.choice(['EDA GMP', 'WHO GMP', 'ISO 9001', 'GDP']), 'expiry': str(TODAY() + datetime.timedelta(days=x.r.randint(90, 900))), 'source': 'company'}), 'add a certificate')[0]
    x.target = 'certificate %s' % d['id']
    x.acc.update('site_certificates', 'id=eq.%s' % d['id'], {'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}, select='id')
    x.expect("select checked_at is null from public.site_certificates where id=%s", (d['id'],), True, 'a company cannot mark its own certificate as checked by Drugbox')


@action('co.document', 'business', ['J-BUSINESS-20'], dict(trade=0.3), who='company', path='api')
def co_document(x):
    cid, slug, _ = my_company(x, ('owner', 'admin', 'regulatory', 'quality'))
    pdf = fixture('spec.pdf') or b'%PDF-1.4\n%%EOF\n'
    path = 'verification/%s/doc-%s.pdf' % (cid, x.r.getrandbits(40))
    num = 'SIM-%d' % x.r.randint(1000, 999999)
    # members write the table and read it through company_documents_public (no SELECT on the table: return=minimal, as the grants say)
    x.ok(x.acc.insert('company_documents', {'company_id': cid, 'type': x.r.choice(['CEP', 'DMF (US)', 'GDP certificate', 'ISO 9001']), 'product': x.r.choice(APIS), 'number': num,
                                            'expiry': str(TODAY() + datetime.timedelta(days=365)), 'status': 'declared', 'created_by': x.me}, select=None), 'declare a company document')
    x.target = 'document %s' % num
    x.expect("select count(*) from public.company_documents where company_id=%s and number=%s", (cid, num), 1, 'the document is stored')
    x.ok(x.acc.get('company_documents_public', 'select=*&company_id=eq.%s' % cid), 'the documents list on the page')


@action('co.product', 'business', ['J-BUSINESS-22'], dict(trade=0.5), who='company', path='api')
def co_product(x):
    cid, slug, _ = my_company(x, ('owner', 'admin', 'regulatory'))
    if x.db.val("select count(*) from public.company_products where company_id=%s", (cid,)) >= 8: raise Skip('enough products')
    api = x.r.choice(APIS)
    d = x.rows(x.acc.insert('company_products', {'company_id': cid, 'name': '%s %s' % (api.split()[0], x.r.choice(FORMS)), 'active_ingredient': api, 'dosage_form': x.r.choice(FORMS),
                                                  'strength': x.r.choice(['500 mg', '20 mg', '1 g', '250 mg/5 ml']), 'role': x.r.choice(['registration_holder', 'manufacturer', 'supplier'])}), 'add a product')[0]
    x.target = 'product %s' % d['id']


@action('co.verify', 'business', ['J-BUSINESS-21', 'J-COMMUNITY-41'], dict(trade=0.5), who='owner')
def co_verify(x):
    cid, slug, _ = my_company(x, ('owner',))
    st = x.db.val("select status from public.companies where id=%s", (cid,))
    if st != 'pending': raise Skip('page is %s' % st)
    if x.db.val("select 1 from public.verification_requests where company_id=%s and status='pending' and not claim", (cid,)): raise Skip('a request is under review')
    pdf = fixture('spec.pdf') or b'%PDF-1.4\n%%EOF\n'; docs = {}
    for k in ('registry', 'tax_card', 'licence'):
        path = 'verification/%s/%s-%s.pdf' % (cid, k, x.r.getrandbits(40))
        x.ok(x.acc.upload('documents', path, pdf, 'application/pdf'), 'upload the %s' % k); docs[k + '_path'] = path
    reg = str(x.r.randint(100000, 9999999))
    x.ok(x.acc.insert('verification_requests', dict(company_id=cid, submitted_by=x.me, registry=reg, **docs), select=None), 'send the verification request')
    x.target = slug
    x.expect("select count(*) from public.verification_requests where company_id=%s and status='pending' and registry=%s", (cid, reg), 1, 'the request waits for Drugbox')
    # the documents are private: another member cannot sign a link to them
    o = x.sim.acc_of(x.other())
    if o and o.ensure():
        s = o.sign('documents', docs['registry_path'])
        if s.ok: raise Fail('another member could open the verification documents: ' + s.repro())


@action('co.claim', 'business', ['J-BUSINESS-14', 'J-COMMUNITY-42'], dict(trade=0.3), rare=True)
def co_claim(x):
    if my_companies(x, ('owner',)): raise Skip('already runs a company')
    c = x.need(x.pick("select id, slug from public.companies where status='unclaimed' and owner_id is null and slug like 'sim-dir-%%' and not exists (select 1 from public.verification_requests v where v.company_id=companies.id and v.status='pending')"), 'no unclaimed pages')
    x.target = c[1]
    r = x.ok(x.acc.rpc('claim_company', {'p_company_id': c[0], 'p_note': 'I am the general manager (simulated)'}), 'claim the page')
    x.expect("select count(*) from public.verification_requests where company_id=%s and submitted_by=%s and claim and status='pending'", (c[0], x.me), 1, 'the claim waits for Drugbox')


@action('co.report', 'business', ['J-BUSINESS-09', 'J-COMMUNITY-43'], dict(trade=0.3, social=0.2), rare=True)
def co_report(x):
    c = x.need(sim_company(x, exclude=[r[0] for r in my_companies(x)])); x.target = c[1]
    d = x.rows(x.acc.insert('company_reports', {'company_id': c[0], 'reporter': x.me, 'section': x.r.choice(['About', 'Contact', 'Products', 'Sites']), 'issue': 'The phone number on this page does not answer (simulated)', 'correction': '+20 2 2345 6789'}), 'report wrong data')[0]
    x.expect("select status from public.company_reports where id=%s", (d['id'],), 'open', 'the report waits for review')


@action('co.rating_reply', 'business', ['J-BUSINESS-24'], dict(trade=0.2), who='company')
def co_rating_reply(x): raise NotBuilt('replying to company ratings: no table or request in the live app')


@action('deal.files', 'business', ['J-BUSINESS-29'], dict(trade=0.3), who='company')
def deal_files(x): raise NotBuilt('documents inside a deal: no request in the live app')


# ── deals ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
def deal_quota(x, to_id):
    """The app's flood limits (30 requests / person / hour, 10 to one company): respected, not hit."""
    n, m = x.db.one("select count(*), count(*) filter (where to_company_id=%s) from public.deals where from_user=%s and created_at > now() - interval '1 hour'", (to_id, x.me))
    if n >= 28 or m >= 9: raise Skip('respecting the deal flood limit (%d this hour, %d to this company)' % (n, m))


def create_deal(x, typ, to, frm, title, lines, msg):
    deal_quota(x, to[0])
    rf = ref(x, {'quote': 'Q', 'service': 'S', 'questionnaire': 'QN', 'dossier': 'DS', 'surplus': 'SP', 'group': 'G', 'job': 'J'}[typ])
    r = x.ok(x.acc.rpc('deal_create', {'p_type': typ, 'p_to_slug': to[1], 'p_from_slug': frm[1] if frm else None, 'p_title': title, 'p_lines': lines,
                                        'p_message': msg, 'p_group': lines.get('group') if typ == 'group' else None, 'p_ref': rf}), 'send the %s request' % typ)
    first = x.db.val("select public.deal_flow() -> %s ->> 'first'", (typ,))
    x.expect("select status from public.deals where ref=%s and from_user=%s and to_company_id=%s", (rf, x.me, to[0]), first, 'the %s request is stored as %s' % (typ, first))
    x.target = rf
    return rf


@action('deal.rfq', 'business', ['J-BUSINESS-03', 'J-BUSINESS-26', 'J-BUSINESS-23'], dict(trade=4), who='company')
def deal_rfq(x):
    frm = my_company(x)
    api = x.r.choice(APIS); n = 1 if x.r.random() < 0.6 else x.r.randint(2, 3)
    lines = {'product': api, 'qty': x.r.choice([25, 50, 100, 500, 1000]), 'unit': 'kg', 'inc': x.r.choice(['EXW', 'CIF Alexandria', 'DDP Cairo']), 'by': str(TODAY() + datetime.timedelta(days=30))}
    sent = []
    for _ in range(n):   # one RFQ to several suppliers at once
        to = sim_company(x, exclude=[frm[0]] + [s[0] for s in sent], types=['Supplier', 'Manufacturer', 'Distributor', 'CMO'])
        if not to: break
        create_deal(x, 'quote', to, frm, 'RFQ: %s %s %s' % (lines['qty'], lines['unit'], api), lines, 'Please quote with CoA and lead time (simulated).'); sent.append(to)
    x.need(sent, 'no supplier to ask')


@action('deal.service', 'business', ['J-BUSINESS-28'], dict(trade=1), who='company')
def deal_service(x):
    frm = my_company(x); to = x.need(sim_company(x, exclude=[frm[0]], types=['Consultant', 'CMO']), 'no consultant')
    create_deal(x, 'service', to, frm, x.r.choice(['Stability study design', 'EDA registration dossier', 'GMP mock inspection', 'Process validation']), {'timeline': '6 weeks', 'budget': 'to agree'}, 'We need support (simulated).')


@action('deal.questionnaire', 'business', ['J-BUSINESS-07'], dict(trade=0.6), who='company')
def deal_questionnaire(x):
    frm = my_company(x, ('owner', 'admin', 'quality'), 'not in quality'); to = x.need(sim_company(x, exclude=[frm[0]], types=['Supplier', 'Manufacturer']))
    create_deal(x, 'questionnaire', to, frm, 'Supplier qualification questionnaire', {'questions': ['GMP certificate?', 'DMF available?', 'Change control process?']}, 'Please answer (simulated).')


@action('deal.dossier', 'business', ['J-BUSINESS-08', 'J-BUSINESS-39'], dict(trade=0.6), who='company')
def deal_dossier(x):
    frm = my_company(x)
    lst = x.pick("select l.company_id, c.slug, l.product from public.company_listings l join public.companies c on c.id=l.company_id where l.kind='dossier' and l.active and l.company_id<>%s and c.owner_id is not null", (frm[0],))
    if not lst:   # put a dossier on the market instead
        cid, slug, _ = my_company(x, ('owner', 'admin', 'regulatory'), 'cannot list dossiers')
        prod = '%s %s' % (x.r.choice(APIS).split()[0], x.r.choice(FORMS))
        x.ok(x.acc.insert('company_listings', {'ref': ref(x, 'DL'), 'company_id': cid, 'kind': 'dossier', 'product': prod, 'reg_status': 'Registered EDA', 'deal_kind': 'Licence-out', 'markets': 'Egypt, GCC', 'created_by': x.me}, select=None), 'list a dossier for licensing')
        x.target = prod; return
    create_deal(x, 'dossier', (lst[0], lst[1]), frm, 'Dossier licence: %s' % lst[2], {'product': lst[2], 'markets': 'Egypt'}, 'Interested in licensing (simulated).')


@action('deal.surplus', 'business', ['J-BUSINESS-38'], dict(trade=1), who='company')
def deal_surplus(x):
    frm = my_company(x)
    lst = x.pick("select l.company_id, c.slug, l.product, l.price from public.company_listings l join public.companies c on c.id=l.company_id where l.kind='surplus' and l.active and l.company_id<>%s and c.owner_id is not null", (frm[0],))
    if not lst or x.r.random() < 0.3:
        cid, slug, _ = my_company(x, ('owner', 'admin', 'sales'), 'cannot list surplus')
        prod = '%s %s' % (x.r.choice(APIS).split()[0], x.r.choice(FORMS))
        x.ok(x.acc.insert('company_listings', {'ref': ref(x, 'SL'), 'company_id': cid, 'kind': 'surplus', 'product': prod, 'qty': '%d boxes' % x.r.randint(100, 5000), 'batch': 'B%d' % x.r.randint(1000, 9999),
                                               'expiry': str(TODAY() + datetime.timedelta(days=x.r.randint(60, 200))), 'price': 'EGP %d / box' % x.r.randint(20, 400), 'off': x.r.choice([10, 20, 30, 40]), 'created_by': x.me}, select=None), 'list near-expiry surplus')
        x.target = prod; return
    create_deal(x, 'surplus', (lst[0], lst[1]), frm, 'Surplus: %s' % lst[2], {'product': lst[2], 'price': lst[3] or 'as listed', 'qty': '200 boxes'}, 'We can take this lot (simulated).')


@action('deal.group', 'business', ['J-BUSINESS-31', 'J-BUSINESS-32', 'J-BUSINESS-33'], dict(trade=1.5), who='company')
def deal_group(x):
    frm = my_company(x)
    g = x.pick("select ref, to_company_id from public.deals where type='group' and status='open' and to_company_id<>%s and coalesce((lines->>'by')::date, current_date) >= current_date order by id desc limit 20", (frm[0],))
    if g and x.r.random() < 0.7:   # join an open buying group
        qty = x.r.randint(5, 60); x.target = g[0]
        q = "select coalesce((select qty from public.deal_members m join public.deals d on d.id=m.deal_id where d.ref=%s and m.company_id=%s), 0)"
        before = x.db.val(q, (g[0], frm[0]))
        r = x.acc.rpc('deal_join', {'p_ref': g[0], 'p_from_slug': frm[1], 'p_qty': qty})
        if not r.ok and 'closed' in (r.text or ''): raise Skip('the group closed meanwhile (target reached)')
        x.ok(r, 'join the buying group')
        x.expect(q, (g[0], frm[0]), lambda v: float(v) == float(before) + qty, "my company's quantity in the group grew by %d" % qty)
        x.expect("select status not in ('open','target_reached') or (status = 'target_reached') = (select sum(qty) >= (lines->>'target')::numeric from public.deal_members where deal_id=deals.id) from public.deals where ref=%s", (g[0],), True, 'target_reached exactly when the total reaches the target')
        return
    to = x.need(sim_company(x, exclude=[frm[0]], types=['Supplier', 'Manufacturer', 'Distributor']))
    api = x.r.choice(APIS)
    create_deal(x, 'group', to, frm, 'Buying group: %s' % api, {'product': api, 'unit': 'kg', 'target': x.r.choice([100, 200, 300]), 'price': 'To be confirmed', 'inc': 'EXW', 'by': str(TODAY() + datetime.timedelta(days=14)), 'group': 'grp-%s' % x.r.getrandbits(24)}, 'Who is in? (simulated)')


ACT_DATA = {'quote': lambda x: {'price': 'USD %d / kg' % x.r.randint(8, 400), 'validity': '%d days' % x.r.choice([7, 14, 30]), 'lead': '%d weeks' % x.r.randint(2, 8), 'note': 'CoA attached on order (simulated)'},
            'revise': lambda x: {'price': 'USD %d / kg' % x.r.randint(8, 400), 'validity': '14 days'},
            'propose': lambda x: {'price': 'EGP %d,000' % x.r.randint(20, 300), 'validity': '30 days', 'timeline': '%d weeks' % x.r.randint(3, 12)},
            'counter': lambda x: {'price': 'USD %d / kg' % x.r.randint(5, 300), 'note': 'Can you do better?'}, 'counter_offer': lambda x: {'price': 'EGP %d / box' % x.r.randint(10, 200)},
            'answer': lambda x: {'answers': {'GMP certificate?': 'Yes, EDA 2025', 'DMF available?': 'Yes', 'Change control process?': 'SOP-QA-012'}},
            'receive': lambda x: {'ontime': x.r.choice(['yes', 'yes', 'yes', 'no'])}, 'rate': lambda x: {'stars': x.r.choice([3, 4, 4, 5, 5]), 'note': 'Good partner'},
            'confirm_group': lambda x: {'price': 'USD %d / kg' % x.r.randint(8, 200)}}
PREFER = ['quote', 'propose', 'accept', 'accept_offer', 'accept_counter', 'confirm', 'ship', 'receive', 'rate', 'start', 'deliver', 'answer', 'approve', 'sign_nda', 'share', 'agree',
          'confirm_group', 'shortlist', 'interview', 'offer', 'accept_job', 'counter', 'counter_offer', 'revise']
NEG = ['decline', 'cancel', 'reject']


@action('deal.progress', 'business', ['J-BUSINESS-26', 'J-BUSINESS-27', 'J-BUSINESS-23', 'J-BUSINESS-30', 'J-BUSINESS-33', 'J-COMMUNITY-26'], dict(trade=5, hire=2), who='company')
def deal_progress(x):
    """Move one of my company's open deals one step, on whichever side I am, as the flow allows."""
    flow = x.sim.flow()
    ids = [r[0] for r in my_companies(x)]
    rows = x.db.q("select ref, type, status, from_company_id = any(%s) or (from_company_id is null and from_user=%s), to_company_id = any(%s) from public.deals "
                  "where (from_company_id = any(%s) or to_company_id = any(%s)) and status not in ('declined','cancelled','rated','approved','rejected','agreed','hired','accepted_job') "
                  "order by updated_at limit 60", (ids, x.me, ids, ids, ids))
    opts = []
    for rf, typ, st, is_from, is_to in rows:
        acts = (flow.get(typ, {}).get('acts', {}).get(st, {}))
        for side, ok in (('from', is_from), ('to', is_to)):
            for a in acts.get(side, []) if ok else []: opts.append((rf, typ, st, side, a))
    x.need(opts, 'no deal waiting on my company')
    pos = [o for o in opts if o[4] not in NEG]; neg = [o for o in opts if o[4] in NEG]
    rf, typ, st, side, a = x.r.choice(neg if neg and (not pos or x.r.random() < 0.08) else pos)
    if typ == 'questionnaire' and a in ('approve', 'reject') and not my_companies(x, ('owner', 'admin', 'quality')): raise Skip('only quality approves suppliers')
    if a == 'confirm_group':
        if typ != 'group': raise Skip('not a group')
    x.target = '%s %s:%s → %s' % (rf, typ, st, a)
    data = ACT_DATA.get(a, lambda x: {})(x)
    nxt = x.db.val("select public.deal_next_status(%s, %s)", (typ, a))
    r = x.acc.rpc('deal_act', {'p_ref': rf, 'p_action': a, 'p_data': dict(data, text=''), 'p_side': side})
    if not r.ok and 'expired' in (r.text or ''):   # an offer older than its validity (compressed days do not age offers, real ones do)
        raise Skip('offer expired')
    x.ok(r, 'deal step %s' % a)
    x.expect("select status from public.deals where ref=%s", (rf,), nxt, '%s moved %s → %s' % (rf, st, nxt))
    x.expect("select action from public.deal_events where deal_id=(select id from public.deals where ref=%s) order by id desc limit 1", (rf,), a, 'the step is in the deal history')
    if typ == 'group' and a == 'confirm_group':
        x.dbwait("select count(*) = (select count(*) from public.deal_members m where m.deal_id=(select id from public.deals where ref=%s)) from public.deals where group_of=(select id from public.deals where ref=%s)", (rf, rf), True, 'one order per member at the group price')
    if typ == 'questionnaire' and a == 'approve':
        x.expect("select status from public.approved_suppliers where buyer_company_id=(select from_company_id from public.deals where ref=%s) and supplier_company_id=(select to_company_id from public.deals where ref=%s)", (rf, rf), 'approved', 'the supplier is on the approved list')


@action('deal.inbox', 'business', ['J-BUSINESS-23', 'J-BUSINESS-25'], dict(trade=2), who='company')
def deal_inbox(x):
    sel = up.quote('*,deal_events(*),fc:companies!deals_from_company_id_fkey(slug,name),tc:companies!deals_to_company_id_fkey(slug,name),fu:profiles!deals_from_user_fkey(name)', safe=',*()!:')
    r = x.ok(x.acc.get('deals', 'select=%s&order=updated_at.desc&limit=300' % sel), 'the shared deals inbox')
    ids = set(r[0] for r in my_companies(x))
    bad = [d['ref'] for d in (r.data or []) if d.get('type') != 'group' and d.get('to_company_id') not in ids and d.get('from_company_id') not in ids and d.get('from_user') != x.me]
    if bad: raise Fail('deals of other companies are visible: %s' % bad[:3])


@action('deal.privacy', 'business', ['J-BUSINESS-30'], dict(trade=0.5, social=0.3))
def deal_privacy(x):
    ids = [r[0] for r in my_companies(x)]
    d = x.need(x.pick("select id, ref from public.deals where type<>'group' and not (to_company_id = any(%s)) and not (coalesce(from_company_id,0) = any(%s)) and from_user<>%s order by id desc limit 30", (ids, ids, x.me)), 'no foreign deals')
    x.target = d[1]
    r = x.ok(x.acc.get('deals', 'select=id,offer&id=eq.%s' % d[0]), 'try to read a deal of other companies')
    if r.data: raise Fail('a deal between other companies is readable: %s' % d[1])
    e = x.ok(x.acc.get('deal_events', 'select=id&deal_id=eq.%s' % d[0]), 'try to read its history')
    if e.data: raise Fail('the history of a deal between other companies is readable')


# ── marketplace ────────────────────────────────────────────────────────────────────────────────────────────────────────
MSEL = up.quote('*,seller:profiles!products_user_id_fkey(%s)' % PCOLS, safe=',*()!:')


@action('market.browse', 'business', ['J-BUSINESS-34'], dict(trade=3, social=0.5))
def market_browse(x):
    now = up.quote(datetime.datetime.now(datetime.timezone.utc).isoformat())
    cat = x.r.choice(['', '&category=eq.api', '&category=eq.finished', '&category=eq.cmo'])
    x.ok(x.acc.get('products', 'select=%s&active=eq.true&type=eq.supply%s&order=created_at.desc&limit=40' % (MSEL, cat)), 'supply listings')
    x.ok(x.acc.get('enquiries', 'select=*,buyer:profiles!enquiries_user_id_fkey(%s)&status=eq.active&type=eq.demand&order=created_at.desc&limit=40' % PCOLS), 'demand listings')
    x.ok(x.acc.get('products', 'select=%s&active=eq.true&type=eq.supply&or=(featured_until.gt.%s,boosted_until.gt.%s)&order=created_at.desc&limit=20' % (MSEL, now, now)), 'featured and boosted')
    w = x.r.choice(APIS).split()[0]
    x.ok(x.acc.get('products', 'select=id,name&active=eq.true&name=ilike.%s&limit=40' % up.quote('*%s*' % w)), 'search the market')
    x.ok(x.acc.get('company_listings', 'select=*,co:companies(slug)&active=eq.true&order=created_at.desc&limit=500'), 'surplus and dossiers')
    inactive = x.ok(x.acc.get('products', 'select=id&active=eq.false&user_id=neq.%s&limit=5' % x.me), "others' hidden listings")
    if inactive.data: raise Fail("another member's inactive listing is readable")


@action('market.supply', 'business', ['J-BUSINESS-36'], dict(trade=2))
def market_supply(x):
    api = x.r.choice(APIS)
    row = {'user_id': x.me, 'type': 'supply', 'category': x.r.choice(['api', 'api', 'finished', 'cmo', 'other']), 'name': api, 'price': 'USD %d / kg' % x.r.randint(5, 500),
           'moq': '%d kg' % x.r.choice([5, 25, 100]), 'description': 'CoA and DMF available. Simulated listing.', 'docs': ['CoA', 'DMF'], 'lead_time': '%d weeks' % x.r.randint(1, 8), 'active': True}
    d = x.rows(x.acc.insert('products', row), 'publish a supply listing')[0]; x.target = 'product %s' % d['id']
    x.expect("select active and boosted_until is null and featured_until is null from public.products where id=%s", (d['id'],), True, 'listed, not boosted for free')


@action('market.demand', 'business', ['J-BUSINESS-37'], dict(trade=2))
def market_demand(x):
    api = x.r.choice(APIS)
    d = x.rows(x.acc.insert('enquiries', {'user_id': x.me, 'type': 'demand', 'category': x.r.choice(['api', 'finished', 'cmo', 'service']), 'title': 'Need %s' % api,
                                          'body': '%d kg · delivery %s · simulated' % (x.r.choice([10, 50, 200]), x.p.get('city', 'Cairo')), 'status': 'active', 'country': 'EG'}), 'post a demand (RFQ)')[0]
    x.target = 'enquiry %s' % d['id']
    x.expect("select status from public.enquiries where id=%s", (d['id'],), 'active', 'the demand is live')


@action('market.manage', 'business', ['J-BUSINESS-40'], dict(trade=1))
def market_manage(x):
    a = x.acc
    x.ok(a.get('products', 'select=id,name,emoji,category,active,created_at,boosted_until,featured_until&user_id=eq.%s&order=created_at.desc&limit=100' % x.me), 'my listings')
    row = x.need(x.pick("select id from public.products where user_id=%s and active and created_at < now() - interval '1 minute' and boosted_until is null and featured_until is null", (x.me,)), 'no old listings')
    x.target = 'product %s' % row[0]
    x.rows(a.update('products', 'id=eq.%s' % row[0], {'active': False}, select='id'), 'hide a sold listing')
    x.expect("select active from public.products where id=%s", (row[0],), False, 'hidden')


@action('market.intents', 'business', ['J-BUSINESS-41'], dict(trade=1, seek=0.5))
def market_intents(x):
    keys = ['api', 'cosmetic', 'supplement', 'packaging', 'cmo', 'equipment', 'license', 'service', 'job', 'training']
    val = {k: x.r.choice(['i-have', 'i-need', 'both', 'na']) for k in x.r.sample(keys, x.r.randint(1, 4))}
    x.ok(x.acc.update('profiles', 'id=eq.%s' % x.me, {'intents': val}, select=None), 'save my intents')
    x.expect("select intents from public.profiles where id=%s", (x.me,), lambda v: v == val, 'the intents are stored')


# ── payments (local Paymob/Fawry stand-in only) ────────────────────────────────────────────────────────────────────────
PM_FIELDS = ['amount_cents', 'created_at', 'currency', 'error_occured', 'has_parent_transaction', 'id', 'integration_id', 'is_3d_secure', 'is_auth', 'is_capture', 'is_refunded',
             'is_standalone_payment', 'is_voided', 'order.id', 'owner', 'pending', 'source_data.pan', 'source_data.sub_type', 'source_data.type', 'success']


def _pstr(v): return 'true' if v is True else 'false' if v is False else str(v)


def _dig(o, k):
    for p in k.split('.'): o = o[p]
    return o


def pay(x, product, method, company_id=None, listing_id=None):
    ok, why = x.sim.payments
    if not ok: raise NotBuilt('payments are off: %s' % why)
    body = {'product': product, 'method': method}
    if company_id: body['company_id'] = int(company_id)
    if listing_id: body['listing_id'] = int(listing_id)
    o = x.ok(x.acc.fn('payments-create', body), 'start the %s payment (%s)' % (product, method)).data
    if not isinstance(o, dict) or not o.get('order_id'): raise Fail('payments-create did not return an order: %s' % str(o)[:200])
    if not safety.checkout_link_ok(o.get('checkout_url'), why):
        x.sim.stop('a checkout link left the stand-in: %s' % o.get('checkout_url')); raise Fail('checkout link outside the stand-in')
    oid = o['order_id']; x.target = 'order %s (%s/%s)' % (oid, product, method)
    cents = x.db.val("select amount_cents from public.payment_orders where id=%s and user_id=%s and status='pending'", (oid, x.me))
    if not cents: raise Fail('the order is not stored as pending for me')
    want = x.db.val("select round(amount_egp * (1 + coalesce(vat_rate, 0.14)) * 100)::int from public.payment_products where code=%s", (product,))
    if want and int(cents) != int(want): raise Fail('the order amount %s is not the database price incl. VAT %s' % (cents, want))
    env = x.sim.fn_env
    if method in ('card', 'wallet'):
        pmo = x.db.val("select coalesce(provider_order, '') from public.payment_orders where id=%s", (oid,))
        obj = {'id': 777000 + oid, 'pending': False, 'amount_cents': int(cents), 'success': True, 'is_auth': False, 'is_capture': False, 'is_standalone_payment': True, 'is_voided': False,
               'is_refunded': False, 'is_3d_secure': True, 'integration_id': int(env['PAYMOB_CARD_INTEGRATION_ID'] if method == 'card' else env['PAYMOB_WALLET_INTEGRATION_ID']),
               'has_parent_transaction': False, 'error_occured': False, 'currency': 'EGP', 'created_at': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000000'), 'owner': 4242,
               'order': {'id': int(pmo) if str(pmo).isdigit() else 990000 + oid, 'merchant_order_id': o['reference']}, 'source_data': {'pan': '2346', 'type': 'card' if method == 'card' else 'wallet', 'sub_type': 'MasterCard' if method == 'card' else 'VodafoneCash'}}
        sig = hmac.new(env['PAYMOB_HMAC_SECRET'].encode(), ''.join(_pstr(_dig(obj, f)) for f in PM_FIELDS).encode(), hashlib.sha512).hexdigest()
        cb = x.acc.c.call('POST', '/functions/v1/paymob-webhook?hmac=' + sig, {'type': 'TRANSACTION', 'obj': obj}, token=None); x.acc._rec(cb)
        x.ok(cb, 'the stand-in reports the payment')
    elif method == 'fawry':
        amt = int(cents) / 100.0
        nb = {'fawryRefNumber': str(o.get('fawry_reference')), 'merchantRefNumber': o['reference'], 'paymentAmount': amt, 'orderAmount': amt, 'orderStatus': 'PAID', 'paymentMethod': 'PAYATFAWRY', 'paymentRefrenceNumber': str(x.r.randint(100000, 999999))}
        nb['messageSignature'] = hashlib.sha256((nb['fawryRefNumber'] + nb['merchantRefNumber'] + '%.2f' % nb['paymentAmount'] + '%.2f' % nb['orderAmount'] + nb['orderStatus'] + nb['paymentMethod'] + nb['paymentRefrenceNumber'] + env['FAWRY_SECURE_KEY']).encode()).hexdigest()
        cb = x.acc.c.call('POST', '/functions/v1/fawry-webhook', nb, token=None); x.acc._rec(cb)
        x.ok(cb, 'Fawry reports the payment')
    else:  # InstaPay: the transfer number and a receipt; Drugbox confirms it in Admin → Review → Payments
        img = fixture('photo.png') or b'\x89PNG'
        path = 'payments/%s/receipt-%s.png' % (x.me, x.r.getrandbits(40))
        x.ok(x.acc.upload('documents', path, img, 'image/png'), 'upload the transfer receipt')
        x.ok(x.acc.rpc('submit_instapay', {'p_id': oid, 'p_transfer_ref': 'IPN-%d' % x.r.randint(100000, 999999), 'p_receipt': path}), 'send the transfer details')
        x.expect("select status from public.payment_orders where id=%s", (oid,), 'review', 'the transfer waits for Drugbox')
        return oid
    x.dbwait("select status from public.payment_orders where id=%s", (oid,), 'paid', 'the order is paid')
    return oid


def my_listing(x):
    r = x.pick("select id from public.products where user_id=%s and active and coalesce(boosted_until, now()) <= now() and coalesce(featured_until, now()) <= now()", (x.me,))
    return r[0] if r else None


@action('pay.boost', 'business', ['J-BUSINESS-42', 'J-BUSINESS-44'], dict(trade=0.5), rare=True)
def pay_boost(x):
    lid = x.need(my_listing(x), 'no listing to boost'); m = x.r.choice(['card', 'card', 'fawry'])
    pay(x, 'boost', m, listing_id=lid)
    x.expect("select boosted_until > now() + interval '6 days' from public.products where id=%s", (lid,), True, 'boosted for 7 days')


@action('pay.featured', 'business', ['J-BUSINESS-43', 'J-BUSINESS-45'], dict(trade=0.4), rare=True)
def pay_featured(x):
    lid = x.need(my_listing(x), 'no listing to feature'); m = x.r.choice(['wallet', 'instapay'])
    oid = pay(x, 'featured', m, listing_id=lid)
    if m != 'instapay': x.expect("select featured_until > now() + interval '29 days' from public.products where id=%s", (lid,), True, 'featured for 30 days')


@action('pay.vip', 'business', ['J-BUSINESS-13', 'J-BUSINESS-47'], dict(trade=0.3), who='owner', rare=True)
def pay_vip(x):
    cid, slug, _ = my_company(x, ('owner',))
    if x.db.val("select plan from public.companies where id=%s", (cid,)) == 'vip': raise Skip('already VIP')
    pay(x, 'vip_month', x.r.choice(['card', 'wallet', 'fawry']), company_id=cid)
    x.expect("select plan||'|'||(vip_until > now() + interval '29 days')::text from public.companies where id=%s", (cid,), 'vip|true', 'the page is VIP for 30 days')


@action('pay.history', 'business', ['J-BUSINESS-46'], dict(trade=0.3))
def pay_history(x):
    r = x.ok(x.acc.get('payment_orders', 'select=*&order=created_at.desc&limit=50'), 'my payments')
    if any(o.get('user_id') != x.me for o in (r.data or [])): raise Fail("another member's payment is in my history")
    x.ok(x.acc.get('payment_products', 'select=*&active=eq.true'), 'prices')


@action('pay.vip_boosts', 'business', ['J-BUSINESS-48'], dict(trade=0.1), who='owner')
def pay_vip_boosts(x): raise NotBuilt("VIP's free boosts: no request in the live app")
