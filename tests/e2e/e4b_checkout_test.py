"""E4b end-to-end in the browser: VIP upgrade → method choice → Fawry reference; card → Paymob page → signed callback → back
in the app (active); boost a listing with InstaPay (transfer number + receipt) → Drugbox confirms in Review → Payments. Demo unaffected."""
from playwright.sync_api import sync_playwright
import json, hmac, hashlib, functools, subprocess, time, os, urllib.request
U = os.environ.get('APP_URL', 'http://localhost:54321/'); DB = os.environ.get('DB_NAME', 'drugbox_live'); V = '/tmp/vids'; R = []
ENV = dict(l.split('=', 1) for l in open('/tmp/drugbox-fn.env').read().splitlines() if '=' in l and not l.startswith('#'))
def T(n, ok, d=''): R.append(ok); print(('✅ ' if ok else '❌ ') + n + ('' if ok else '  → ' + str(d)[:220]))
def sql(q):
    r = subprocess.run(['psql', '-h', '/tmp', '-p', '5433', '-U', 'postgres', '-d', DB, '-tA', '-v', 'ON_ERROR_STOP=1', '-c', q], capture_output=True, text=True)
    if r.returncode: raise SystemExit('SQL failed: ' + r.stderr.strip()[:300])
    return r.stdout.strip()
F = ['amount_cents', 'created_at', 'currency', 'error_occured', 'has_parent_transaction', 'id', 'integration_id', 'is_3d_secure', 'is_auth', 'is_capture', 'is_refunded', 'is_standalone_payment', 'is_voided', 'order.id', 'owner', 'pending', 'source_data.pan', 'source_data.sub_type', 'source_data.type', 'success']
def sign(o): return hmac.new(ENV['PAYMOB_HMAC_SECRET'].encode(), ''.join(('true' if v is True else 'false' if v is False else str(v)) for v in (functools.reduce(lambda a, k: a[k], f.split('.'), o) for f in F)).encode(), hashlib.sha512).hexdigest()
st = int(time.time()); PW = 'Strong-pass-2026'
def signup(pg, name, email):
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', name); pg.fill('#suEmail', email); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn'); pg.wait_for_timeout(3500)
    return pg.evaluate("dxLive.uuidOf(ME.id)")
def fresh(pg, url=U): pg.goto(url, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(4500)
def last_ov(pg): return "[...document.querySelectorAll('.dbk-ov')].filter(e=>e.offsetWidth>0).pop()"
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); errs = []
    O, A = [b.new_context(viewport={'width': 1440, 'height': 900}).new_page() for _ in range(2)]
    for pg in (O, A): pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    o = signup(O, 'Dr. Paying Owner', f'po{st}@x.test'); adm = signup(A, 'Drugbox Finance', f'fin{st}@x.test'); sql(f"update public.profiles set role='admin' where id='{adm}'")
    slug = f'paying-pharma-{st}'
    cid = sql(f"insert into public.companies (owner_id, name, slug, type, status, sectors) values ('{o}','Paying Pharma {st}','{slug}','Manufacturer','verified','{{Manufacturer}}') returning id").split('\n')[0]
    lid = sql(f"insert into public.products (user_id, name, category, type, active) values ('{o}','Omeprazole pellets {st}','api','supply',true) returning id").split('\n')[0]
    fresh(O)
    def open_vip_pay(billing='month'):
        O.evaluate(f"dxDir.upgrade('{slug}')"); O.wait_for_timeout(600)
        if billing == 'year': O.evaluate(f"(()=>{{var o={last_ov(O)};var r=o.querySelector('input[name=plBill][value=year]');r&&r.click()}})()")
        O.evaluate(f"(()=>{{var o={last_ov(O)};[...o.querySelectorAll('button')].find(x=>/Continue to payment/.test(x.textContent)).click()}})()"); O.wait_for_timeout(900)
    open_vip_pay()
    T('the VIP payment window offers card, Vodafone Cash & wallets, Fawry and InstaPay', O.evaluate(f"[...({last_ov(O)}).querySelectorAll('.dx-pay-m input')].map(i=>i.value).join(',')") == 'card,wallet,fawry,instapay')
    T('the "Demo — no payment is taken" note is gone in the live app', 'no payment is taken' not in O.evaluate(f"({last_ov(O)}).innerText"))
    O.evaluate(f"(()=>{{var o={last_ov(O)};o.querySelector('input[value=fawry]').click();[...o.querySelectorAll('button')].find(x=>/^Pay EGP/.test(x.textContent.trim())).click()}})()"); O.wait_for_timeout(3000)
    fr = O.evaluate(f"(()=>{{var o={last_ov(O)};return o?o.innerText:''}})()")
    T('Fawry: the reference number is shown with the amount (EGP 2,850)', 'Fawry reference number' in fr and '2,850' in fr, fr[:160])
    T('…and the order waits in the database with that reference', sql(f"select method||'|'||status||'|'||(provider_ref is not null) from public.payment_orders where company_id={cid} order by id desc limit 1") == 'fawry|pending|true')
    O.evaluate("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
    # card → Paymob page → signed callback → back in the app
    open_vip_pay()
    O.evaluate(f"(()=>{{var o={last_ov(O)};o.querySelector('input[value=card]').click();[...o.querySelectorAll('button')].find(x=>/^Pay EGP/.test(x.textContent.trim())).click()}})()"); O.wait_for_timeout(3500)
    T('card: the person is taken to Paymob\'s secure page', 'unifiedcheckout/?publicKey=' in O.url, O.url)
    oid, ref = sql(f"select id||'|'||merchant_ref from public.payment_orders where company_id={cid} and method='card' order by id desc limit 1").split('|')
    obj = {'id': 880000 + int(oid), 'pending': False, 'amount_cents': 285000, 'success': True, 'is_auth': False, 'is_capture': False, 'is_standalone_payment': True, 'is_voided': False, 'is_refunded': False, 'is_3d_secure': True,
           'integration_id': 111111, 'has_parent_transaction': False, 'error_occured': False, 'currency': 'EGP', 'created_at': '2026-10-02T13:00:00.000000', 'owner': 4242,
           'order': {'id': 991000 + int(oid), 'merchant_order_id': ref}, 'source_data': {'pan': '2346', 'type': 'card', 'sub_type': 'MasterCard'}}
    req = urllib.request.Request(U.rstrip('/') + '/functions/v1/paymob-webhook?hmac=' + sign(obj), data=json.dumps({'type': 'TRANSACTION', 'obj': obj}).encode(), headers={'Content-Type': 'application/json'}, method='POST')
    T('Paymob\'s signed callback activates the order', urllib.request.urlopen(req, timeout=10).read().decode() == 'paid')
    fresh(O, U + f'?payment={oid}'); O.wait_for_timeout(2500)
    toast = O.evaluate("(document.getElementById('toast')||{}).textContent||''")
    T('back in the app, the person is told it is active — and the company is VIP', 'Payment received' in toast and sql(f"select plan from public.companies where id={cid}") == 'vip', toast)
    # boost a listing with InstaPay
    O.evaluate("goto('market')"); O.wait_for_timeout(1500); O.evaluate("openBoostModal('boost')"); O.wait_for_timeout(2500)
    opts = O.evaluate("[...document.querySelectorAll('#dxPayListing option')].map(o=>o.textContent)")
    T('the boost window lists my listings and the four methods', f'Omeprazole pellets {st}' in opts and O.evaluate("document.querySelectorAll('#boostModalOverlay .dx-pay-m').length") == 4, opts)
    O.evaluate(f"document.getElementById('dxPayListing').value='{lid}';document.querySelector('#boostModalOverlay input[value=instapay]').click();document.getElementById('bmPayBtn').click()"); O.wait_for_timeout(3000)
    ip = O.evaluate(f"({last_ov(O)}).innerText")
    T('InstaPay: address, amount (EGP 1,653) and the note to write are shown', 'drugbox@instapay' in ip and '1,653' in ip and 'DBX' in ip, ip[:200])
    O.fill('.dbk-ov #dxIpRef', 'IPN-55667788'); O.set_input_files('.dbk-ov #dxIpRc', V + '/photo.png')
    O.evaluate(f"(()=>{{var o={last_ov(O)};[...o.querySelectorAll('button')].find(x=>/Send for confirmation/.test(x.textContent)).click()}})()"); O.wait_for_timeout(3000)
    pid = sql(f"select id from public.payment_orders where listing_id={lid} order by id desc limit 1")
    T('the transfer and receipt are sent for confirmation', sql(f"select status||'|'||transfer_ref||'|'||(receipt_path like 'payments/{o}/%') from public.payment_orders where id={pid}") == 'review|IPN-55667788|true')
    # Drugbox confirms
    fresh(A); A.evaluate("goto('admin')"); A.wait_for_timeout(700); A.evaluate("switchAdminTab('review')"); A.wait_for_timeout(2500)
    A.evaluate("document.querySelector('.dx-mod-tab[data-q=payments]').click()"); A.wait_for_timeout(400)
    lst = A.inner_text('.dx-mod-list')
    T('Review → Payments shows the transfer with its receipt', 'IPN-55667788' in lst and A.evaluate("!!document.querySelector('.dx-mod-doc[data-bucket=documents]')"), lst[:200])
    link = A.evaluate("dxModeration.link(document.querySelector('.dx-mod-doc').dataset.doc,'documents')")
    T('the receipt opens through a short-lived link', bool(link) and urllib.request.urlopen(link, timeout=5).status == 200)
    A.evaluate(f"document.querySelector('.dx-mod-ok[data-k=payments][data-id=\"{pid}\"]').click()"); A.wait_for_timeout(2500)
    T('confirming it boosts the listing for 7 days', sql(f"select status from public.payment_orders where id={pid}") == 'paid' and sql(f"select boosted_until::date - now()::date from public.products where id={lid}") in ('7', '6'))
    T('no errors in the pages', not [e for e in errs if 'unifiedcheckout' not in e], errs)
    print(sum(R), '/', len(R)); b.close()
