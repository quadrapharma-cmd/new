"""C3 end-to-end: surplus and dossier listings through the real dialogs, group buying (open → join → target → confirm → member orders
created by the database), approved suppliers, and comparing quotes from two suppliers."""
from playwright.sync_api import sync_playwright
import subprocess, time, os
U = os.environ.get('APP_URL', 'http://localhost:54321/'); DB = os.environ.get('DB_NAME', 'drugbox_live'); R = []
def T(n, ok, d=''): R.append(ok); print(('✅ ' if ok else '❌ ') + n + ('' if ok else '  → ' + str(d)[:220]))
def sql(q):
    r = subprocess.run(['psql', '-h', '/tmp', '-p', '5433', '-U', 'postgres', '-d', DB, '-tA', '-v', 'ON_ERROR_STOP=1', '-c', q], capture_output=True, text=True)
    if r.returncode: raise SystemExit('SQL failed: ' + r.stderr.strip()[:300])
    return r.stdout.strip()
st = int(time.time()); PW = 'Strong-pass-2026'
OK = "(()=>{var o=[...document.querySelectorAll('.dbk-ov')].filter(e=>e.offsetWidth>0).pop();var b=o&&(o.querySelector('[data-a=ok]')||[...o.querySelectorAll('button')].filter(x=>!/^(×|Cancel|Close)$/.test(x.textContent.trim())).pop());b&&b.click();return b?b.textContent.trim():null})()"
CLOSE = "document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())"
def signup(pg, name, email):
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', name); pg.fill('#suEmail', email); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn'); pg.wait_for_timeout(3500)
    return pg.evaluate("dxLive.uuidOf(ME.id)")
def act_as(pg, slug):
    pg.evaluate(f"localStorage.setItem('dx_acting', JSON.stringify('{slug}'))"); pg.reload(wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(4500)
def settle(pg): pg.evaluate("dxLive.dealsBusy()"); pg.wait_for_timeout(1500)
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); errs = []
    A, B, S = [b.new_context(viewport={'width': 1440, 'height': 900}).new_page() for _ in range(3)]
    for pg in (A, B, S): pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    a = signup(A, 'Dr. Org Buyer', f'org{st}@x.test'); bm = signup(B, 'Dr. Member Buyer', f'mem{st}@x.test'); s = signup(S, 'Dr. Supplier Sales', f'sup{st}@x.test')
    SA, SB, SS, SS2 = f'org-pharma-{st}', f'member-labs-{st}', f'big-api-{st}', f'second-api-{st}'
    for uid, name, slug, sect in ((a, 'Org Pharma', SA, 'Manufacturer'), (bm, 'Member Labs', SB, 'Manufacturer'), (s, 'Big API', SS, 'API supplier'), (s, 'Second API', SS2, 'API supplier')):
        sql(f"insert into public.companies (owner_id, name, slug, type, status, registry, sectors, governorate) values ('{uid}','{name} {st}','{slug}','Manufacturer','verified','9{abs(hash(slug)) % 10**6}','{{{sect}}}','Giza')")
    act_as(A, SA); act_as(B, SB); act_as(S, SS)
    # surplus through the real dialogs
    S.evaluate("dxDir3.surplusDialog()"); S.wait_for_timeout(600); S.evaluate(OK); S.wait_for_timeout(700)
    for sel, v in (('#spP', f'MCC PH-101 {st}'), ('#spQ', '750 kg'), ('#spB', 'MC-24-0911'), ('#spR', 'US$ 2.40/kg'), ('#spO', '30')): S.fill(sel, v)
    S.evaluate(OK); S.wait_for_timeout(1800)
    T('surplus posted through the dialog is saved for the company', sql(f"select kind||'|'||price||'|'||off from public.company_listings where product='MCC PH-101 {st}'") == 'surplus|US$ 2.40/kg|30')
    B.reload(wait_until='load'); B.wait_for_timeout(400); B.evaluate('endSplash()'); B.wait_for_timeout(4500)
    T('another company sees the surplus (and no demo listings)', B.evaluate(f"dxDir3.surplus().some(x=>x.product==='MCC PH-101 {st}')") and not B.evaluate("dxDir3.surplus().some(x=>x.product==='Airless bottles 30 mL (white)')"))
    S.evaluate(CLOSE); S.evaluate(f"dxDir3.addDossier(dxDir.bySlug('{SS}'))"); S.wait_for_timeout(700)
    if S.locator('#dsP').count():
        S.fill('#dsP', f'Esomeprazole 40 mg {st}'); S.select_option('#dsS', index=0); S.select_option('#dsD', index=0); S.fill('#dsM', 'Egypt, GCC'); S.evaluate(OK); S.wait_for_timeout(1800)
    T('dossier listed through the dialog is saved', sql(f"select kind||'|'||markets from public.company_listings where product='Esomeprazole 40 mg {st}'") == 'dossier|Egypt, GCC')
    S.evaluate(CLOSE)
    # group buying
    A.evaluate("dxDir3.newGroup()"); A.wait_for_timeout(600)
    A.fill('#ngP', f'Metformin HCl {st}'); A.select_option('#ngS', SS); A.fill('#ngT', '1000'); A.fill('#ngQ', '400')
    for sel in ('#ngD', '#ngB'):
        if A.locator(sel).count(): A.fill(sel, '2099-12-31')
    A.evaluate(OK); A.wait_for_timeout(1000); settle(A)
    g = sql(f"select d.ref||'|'||d.status||'|'||coalesce((select sum(qty) from public.deal_members m where m.deal_id=d.id),0) from public.deals d where d.type='group' and d.lines->>'product'='Metformin HCl {st}'")
    T('the organiser opens a buying group with its share (open, 400)', g.split('|')[1:] == ['open', '400'], g)
    ref = g.split('|')[0]
    B.evaluate("dxLive.loadDeals()"); B.wait_for_timeout(1500)
    B.evaluate(f"dxDeals.joinGroup('{ref}',{{slug:'{SB}',name:'Member Labs {st}'}},700)"); B.wait_for_timeout(500); settle(B)
    T('a member joins with 700 → target reached in the database', sql(f"select status from public.deals where ref='{ref}'") == 'target_reached')
    T('the supplier is notified', sql(f"select count(*)>0 from public.notifications where user_id='{s}' and message like 'Buying group reached%'") == 't')
    S.evaluate("dxLive.loadDeals()"); S.wait_for_timeout(1500)
    S.evaluate(f"dxDeals.act('{ref}','confirm_group',{{}},'to')"); S.wait_for_timeout(500); settle(S)
    T('the supplier confirms the group price', sql(f"select status from public.deals where ref='{ref}'") == 'confirmed')
    T('one accepted order per member, created by the database', sql(f"select count(*) from public.deals where group_of=(select id from public.deals where ref='{ref}') and status='accepted'") == '2')
    B.evaluate("dxLive.loadDeals()"); B.wait_for_timeout(1500)
    T('the member sees its own 700 kg order', B.evaluate("dxDeals.all().some(d=>/700 kg \\(group order\\)/.test(d.title)&&d.status==='accepted')"))
    # approved suppliers
    A.evaluate(f"dxDir3.setAvl('{SS}','approved')"); A.wait_for_timeout(1500)
    T('adding a supplier to the approved list is saved', sql(f"select a.status from public.approved_suppliers a join public.companies b on b.id=a.buyer_company_id join public.companies c on c.id=a.supplier_company_id where b.slug='{SA}' and c.slug='{SS}'") == 'approved')
    # compare quotes from two suppliers
    G = f'G{st}'
    for sup in (SS, SS2): A.evaluate(f"dxDeals.create('quote','{sup}','Paracetamol DC — 5 MT {st}',{{qty:'5',unit:'MT',inc:'CIF'}},'Comparing suppliers',{{group:'{G}'}})"); A.wait_for_timeout(400)
    settle(A)
    T('one request to two suppliers is recorded as one group', sql(f"select count(*) from public.deals where group_key='{G}'") == '2')
    S.evaluate("dxLive.loadDeals()"); S.wait_for_timeout(1500)
    refs = dict((r.split('|')[1], r.split('|')[0]) for r in sql(f"select d.ref||'|'||c.slug from public.deals d join public.companies c on c.id=d.to_company_id where d.group_key='{G}'").split('\n'))
    S.evaluate(f"dxDeals.act('{refs[SS]}','quote',{{price:'US$ 3.10 / kg',validity:'14 days'}},'to')"); S.wait_for_timeout(300)
    S.evaluate(f"dxDeals.act('{refs[SS2]}','quote',{{price:'US$ 2.95 / kg',validity:'14 days'}},'to')"); S.wait_for_timeout(300); settle(S)
    A.evaluate("dxLive.loadDeals()"); A.wait_for_timeout(1500)
    A.evaluate(f"dxCompareQuotes('{G}')"); A.wait_for_timeout(800)
    cmp = A.evaluate("(()=>{var o=[...document.querySelectorAll('.dbk-ov')].filter(e=>e.offsetWidth>0).pop();return o?o.innerText:''})()")
    T('the comparison shows both quotes side by side', '3.10' in cmp and '2.95' in cmp, cmp[:200])
    A.evaluate(CLOSE); A.evaluate(f"dxDeals.act('{refs[SS2]}','accept',{{}},'from')"); A.wait_for_timeout(300); settle(A)
    T('accepting the cheaper quote is recorded; the other stays open', sql(f"select status from public.deals where ref='{refs[SS2]}'") == 'accepted' and sql(f"select status from public.deals where ref='{refs[SS]}'") == 'quoted')
    T('no errors in the pages', not errs, errs)
    print(sum(R), '/', len(R)); b.close()
