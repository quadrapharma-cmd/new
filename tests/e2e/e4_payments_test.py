"""E4 payments, through the real Edge Functions (Paymob/Fawry replaced by a local stand-in). Signatures are computed here,
independently, from the providers' documented formulas. Card (Paymob), wallet, Fawry reference, InstaPay review; forged,
replayed and wrong-amount callbacks; nobody can activate without paying."""
import json, hmac, hashlib, subprocess, time, os, urllib.request, urllib.error
from _dx import APP_URL as U, DB, R, T, sql, ST, FIXTURES, fn_env, refused, ERR, wait_for, done   # shared settings: tests/e2e/_dx.py
G = U.rstrip('/')
ENV = fn_env()
ANON, HMAC_SECRET, FKEY = ENV['SUPABASE_ANON_KEY'], ENV['PAYMOB_HMAC_SECRET'], ENV['FAWRY_SECURE_KEY']
MOCK = ENV.get('PAYMOB_BASE', 'http://127.0.0.1:54500')   # the local Paymob/Fawry stand-in (it records requests at /log)
def http(method, path, body=None, token=None, raw=False):
    req = urllib.request.Request(G + path, method=method, data=None if body is None else json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'apikey': ANON, **({'Authorization': 'Bearer ' + token} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=15) as r: t = r.read().decode(); return r.status, (t if raw else (json.loads(t) if t else None))
    except urllib.error.HTTPError as e: t = e.read().decode(); return e.code, (t if raw else (json.loads(t) if t.startswith(('{', '[')) else t))
st = ST
def user(name):
    s, j = http('POST', '/auth/v1/signup', {'email': f'{name}{st}@x.test', 'password': 'Strong-pass-2026', 'data': {'name': name}})
    tok = j.get('access_token') or (j.get('session') or {}).get('access_token'); uid = (j.get('user') or {}).get('id')
    return tok, uid
def pm_order(oid):   # the Paymob order id stored when the payment started (signed in Paymob's callback); older schema: none stored
    v = sql(f"select coalesce(to_jsonb(o)->>'provider_order', '') from public.payment_orders o where id={oid}")
    return int(v) if v.isdigit() else 990000 + oid
def paymob_obj(order_id, merchant_ref, cents, success=True, pending=False):
    return {'id': 777000 + order_id, 'pending': pending, 'amount_cents': cents, 'success': success, 'is_auth': False, 'is_capture': False, 'is_standalone_payment': True,
            'is_voided': False, 'is_refunded': False, 'is_3d_secure': True, 'integration_id': 111111, 'has_parent_transaction': False, 'error_occured': not success,
            'currency': 'EGP', 'created_at': '2026-10-02T12:00:00.000000', 'owner': 4242, 'order': {'id': pm_order(order_id), 'merchant_order_id': merchant_ref},
            'source_data': {'pan': '2346', 'type': 'card', 'sub_type': 'MasterCard'}}
FIELDS = ['amount_cents', 'created_at', 'currency', 'error_occured', 'has_parent_transaction', 'id', 'integration_id', 'is_3d_secure', 'is_auth', 'is_capture', 'is_refunded',
          'is_standalone_payment', 'is_voided', 'order.id', 'owner', 'pending', 'source_data.pan', 'source_data.sub_type', 'source_data.type', 'success']
def pstr(v): return 'true' if v is True else 'false' if v is False else str(v)
def paymob_sign(o):
    s = ''.join(pstr(__import__('functools').reduce(lambda a, k: a[k], f.split('.'), o)) for f in FIELDS)
    return hmac.new(HMAC_SECRET.encode(), s.encode(), hashlib.sha512).hexdigest()
def fawry_sign(b): return hashlib.sha256((b['fawryRefNumber'] + b['merchantRefNumber'] + f"{b['paymentAmount']:.2f}" + f"{b['orderAmount']:.2f}" + b['orderStatus'] + b['paymentMethod'] + b.get('paymentRefrenceNumber', '') + FKEY).encode()).hexdigest()
owner_t, owner = user('payowner'); other_t, other = user('payother'); adm_t, adm = user('payadmin')
sql(f"update public.profiles set role='admin' where id='{adm}'")
sql(f"update public.profiles set phone='+20 100 123 4567' where id='{owner}'")   # Fawry needs the payer's mobile (written the way people do)
cid = sql(f"insert into public.companies (owner_id, name, slug, type, status, sectors) values ('{owner}','Pay Pharma {st}','pay-pharma-{st}','Manufacturer','verified','{{Manufacturer}}') returning id").split('\n')[0]
# ── card through Paymob ──
s, o = http('POST', '/functions/v1/payments-create', {'product': 'vip_month', 'method': 'card', 'company_id': int(cid)}, owner_t)
T('a card payment starts Paymob\'s unified checkout', s == 200 and 'unifiedcheckout/?publicKey=egy_pk_test_local&clientSecret=egy_csk_' in o.get('checkout_url', ''), (s, o))
log = json.loads(urllib.request.urlopen(MOCK + '/log').read())[-1]
T('Paymob is asked for the database price incl. VAT (EGP 2,850) with our reference and webhook', log['body']['amount'] == 285000 and log['body']['special_reference'] == o['reference'] and log['body']['notification_url'].endswith('/functions/v1/paymob-webhook') and log['auth_ok'], log)
oid, ref = o['order_id'], o['reference']
obj = paymob_obj(oid, ref, 285000)
s, t = http('POST', '/functions/v1/paymob-webhook?hmac=' + 'f' * 128, {'type': 'TRANSACTION', 'obj': obj}, raw=True)
T('a forged Paymob callback is refused (nothing activated)', s == 401 and sql(f"select status from public.payment_orders where id={oid}") == 'pending' and sql(f"select plan from public.companies where id={cid}") == 'free', (s, t))
s, t = http('POST', '/functions/v1/paymob-webhook?hmac=' + paymob_sign(obj), {'type': 'TRANSACTION', 'obj': obj}, raw=True)
T('a correctly signed callback (signature computed independently) marks the order paid', s == 200 and t == 'paid', (s, t))
T('…and the company becomes VIP for 30 days, with a notification', sql(f"select plan||'|'||(vip_until::date - now()::date) from public.companies where id={cid}") in ('vip|30', 'vip|29') and sql(f"select count(*) from public.notifications where user_id='{owner}' and type='payment'") == '1')
until1 = sql(f"select vip_until from public.companies where id={cid}")
s, t = http('POST', '/functions/v1/paymob-webhook?hmac=' + paymob_sign(obj), {'type': 'TRANSACTION', 'obj': obj}, raw=True)
T('a replayed callback does not activate twice', s == 200 and t == 'already paid' and sql(f"select vip_until from public.companies where id={cid}") == until1, (s, t))
# F-115: merchant_order_id is NOT part of Paymob's signed string — the paid callback re-sent with another (same-price) order's
# reference must not pay that order (FAILS before migration 0023: the order was looked up by merchant_order_id)
s, o3 = http('POST', '/functions/v1/payments-create', {'product': 'vip_month', 'method': 'card', 'company_id': int(cid)}, owner_t)
swapped = {**obj, 'order': {**obj['order'], 'merchant_order_id': o3.get('reference', '')}}
s, t = http('POST', '/functions/v1/paymob-webhook?hmac=' + paymob_sign(obj), {'type': 'TRANSACTION', 'obj': swapped}, raw=True)
T("a genuine callback re-sent with another order's reference does not pay that order", sql(f"select status from public.payment_orders where id={o3.get('order_id', 0)}") == 'pending', (s, t))
s, o2 = http('POST', '/functions/v1/payments-create', {'product': 'vip_year', 'method': 'wallet', 'company_id': int(cid)}, owner_t)
T('Vodafone Cash / wallets go through Paymob\'s wallet integration', s == 200 and json.loads(urllib.request.urlopen(MOCK + '/log').read())[-1]['body']['payment_methods'] == [222222], (s, o2))
cheap = paymob_obj(o2['order_id'], o2['reference'], 100)
s, t = http('POST', '/functions/v1/paymob-webhook?hmac=' + paymob_sign(cheap), {'type': 'TRANSACTION', 'obj': cheap}, raw=True)
T('a signed callback with the wrong amount does not activate', t == 'amount mismatch' and sql(f"select status from public.payment_orders where id={o2['order_id']}") == 'pending', (s, t))
# a declined payment (0055): the order is recorded as failed, nothing is activated, the buyer is told — on its own order (o3, a VIP
# month by card), so o2 stays pending for the checks below
n_pay = int(sql(f"select count(*) from public.notifications where user_id='{owner}' and type='payment'"))
failed = paymob_obj(o3['order_id'], o3['reference'], 285000, success=False)
s, t = http('POST', '/functions/v1/paymob-webhook?hmac=' + paymob_sign(failed), {'type': 'TRANSACTION', 'obj': failed}, raw=True)
T('a declined payment does not activate (the order is failed, the buyer is told)', s == 200 and t == 'failed' and sql(f"select status from public.payment_orders where id={o3['order_id']}") == 'failed'
  and sql(f"select vip_until from public.companies where id={cid}") == until1 and int(sql(f"select count(*) from public.notifications where user_id='{owner}' and type='payment'")) == n_pay + 1, (s, t))
# ── Fawry reference for a listing boost ──
lid = sql(f"insert into public.products (user_id, name, category, type, active) values ('{owner}','Boosted API {st}','api','supply',true) returning id").split('\n')[0]
s, f = http('POST', '/functions/v1/payments-create', {'product': 'boost', 'method': 'fawry', 'listing_id': int(lid)}, owner_t)
T('Fawry issues a reference number (charge signed correctly)', s == 200 and str(f.get('fawry_reference', '')).startswith('9'), (s, f))
nb = {'fawryRefNumber': str(f.get('fawry_reference')), 'merchantRefNumber': f.get('reference', ''), 'paymentAmount': 1653.0, 'orderAmount': 1653.0, 'orderStatus': 'PAID', 'paymentMethod': 'PAYATFAWRY', 'paymentRefrenceNumber': '123456'}
s, t = http('POST', '/functions/v1/fawry-webhook', {**nb, 'messageSignature': '0' * 64}, raw=True)
T('a forged Fawry notification is refused', s == 401 and sql(f"select boosted_until is null from public.products where id={lid}") == 't', (s, t))
s, t = http('POST', '/functions/v1/fawry-webhook', {**nb, 'messageSignature': fawry_sign(nb)}, raw=True)
T('a signed PAID notification boosts the listing for 7 days', s == 200 and t == 'paid' and sql(f"select boosted_until::date - now()::date from public.products where id={lid}") in ('7', '6'), (s, t))
b_until = sql(f"select boosted_until from public.products where id={lid}")
s, t = http('POST', '/functions/v1/fawry-webhook', {**nb, 'messageSignature': fawry_sign(nb)}, raw=True)
T('a replayed Fawry notification does not boost twice', s == 200 and t == 'already paid' and sql(f"select boosted_until from public.products where id={lid}") == b_until, (s, t))
lid2 = sql(f"insert into public.products (user_id, name, category, type, active) values ('{owner}','Second API {st}','api','supply',true) returning id").split('\n')[0]
s, f2 = http('POST', '/functions/v1/payments-create', {'product': 'boost', 'method': 'fawry', 'listing_id': int(lid2)}, owner_t)
cheap = {'fawryRefNumber': str(f2.get('fawry_reference')), 'merchantRefNumber': f2.get('reference', ''), 'paymentAmount': 1.0, 'orderAmount': 1.0, 'orderStatus': 'PAID', 'paymentMethod': 'PAYATFAWRY', 'paymentRefrenceNumber': '654321'}
s, t = http('POST', '/functions/v1/fawry-webhook', {**cheap, 'messageSignature': fawry_sign(cheap)}, raw=True)
T('a signed Fawry notification for the wrong amount does not boost', sql(f"select status from public.payment_orders where id={f2.get('order_id', 0)}") == 'pending' and sql(f"select boosted_until is null from public.products where id={lid2}") == 't', (s, t))
# a listing that is not yours cannot be boosted (the order would pay for someone else's listing)
other_lid = sql(f"insert into public.products (user_id, name, category, type, active) values ('{other}','Not yours {st}','api','supply',true) returning id").split('\n')[0]
s, x = http('POST', '/functions/v1/payments-create', {'product': 'boost', 'method': 'fawry', 'listing_id': int(other_lid)}, owner_t)
T("cannot buy a boost for someone else's listing", s >= 400 and sql(f"select count(*) from public.payment_orders where listing_id={other_lid}") == '0', (s, x))
# ── InstaPay: transfer + receipt, confirmed by Drugbox ──
s, ip = http('POST', '/functions/v1/payments-create', {'product': 'featured', 'method': 'instapay', 'listing_id': int(lid)}, owner_t)
T('InstaPay shows the address, amount and reference to write on the transfer', s == 200 and ip['instapay']['address'] == 'drugbox@instapay' and ip['amount'] == 4503 and ip['reference'].startswith('DBX'), (s, ip))
s, _ = http('POST', '/rest/v1/rpc/submit_instapay', {'p_id': ip['order_id'], 'p_transfer_ref': 'IPN-000000', 'p_receipt': f'payments/{other}/receipt.png'}, owner_t)
T("the receipt must be your own upload (not a file in someone else's folder)", s >= 400 and sql(f"select status from public.payment_orders where id={ip['order_id']}") == 'pending')
s, _ = http('POST', '/rest/v1/rpc/submit_instapay', {'p_id': ip['order_id'], 'p_transfer_ref': 'IPN-778899', 'p_receipt': f'payments/{owner}/receipt.png'}, owner_t)
T('the customer sends the transfer number and receipt → waiting for review', sql(f"select status||'|'||transfer_ref from public.payment_orders where id={ip['order_id']}") == 'review|IPN-778899')
s, _ = http('POST', '/rest/v1/rpc/review_instapay', {'p_id': ip['order_id'], 'p_ok': True}, other_t)
T('a non-admin cannot confirm a transfer', s >= 400 and sql(f"select status from public.payment_orders where id={ip['order_id']}") == 'review')
s, _ = http('POST', '/rest/v1/rpc/review_instapay', {'p_id': ip['order_id'], 'p_ok': True}, adm_t)
T('Drugbox confirms it → the listing is featured for 30 days', s < 300 and sql(f"select featured_until::date - now()::date from public.products where id={lid}") in ('30', '29'))
s, ip2 = http('POST', '/functions/v1/payments-create', {'product': 'featured', 'method': 'instapay', 'listing_id': int(lid2)}, owner_t)
http('POST', '/rest/v1/rpc/submit_instapay', {'p_id': ip2['order_id'], 'p_transfer_ref': 'IPN-NOPE', 'p_receipt': f'payments/{owner}/receipt2.png'}, owner_t)
n0 = int(sql(f"select count(*) from public.notifications where user_id='{owner}' and type='payment'"))
s, _ = http('POST', '/rest/v1/rpc/review_instapay', {'p_id': ip2['order_id'], 'p_ok': False}, adm_t)
T('Drugbox rejects an unmatched transfer → order failed, listing not featured, the customer is told', s < 300 and sql(f"select status from public.payment_orders where id={ip2['order_id']}") == 'failed'
  and sql(f"select featured_until is null from public.products where id={lid2}") == 't' and int(sql(f"select count(*) from public.notifications where user_id='{owner}' and type='payment'")) == n0 + 1, s)
# ── nobody activates without paying ──
s, _ = http('POST', '/functions/v1/payments-create', {'product': 'vip_month', 'method': 'card', 'company_id': int(cid)}, other_t)
T("cannot buy VIP for a company you don't manage", s == 400)
s, _ = http('POST', '/rest/v1/rpc/confirm_payment', {'p_merchant_ref': o2['reference'], 'p_provider_ref': 'x', 'p_amount_cents': 2850000, 'p_payload': {}}, owner_t)
s1, _ = http('POST', '/rest/v1/rpc/confirm_payment', {'p_provider': 'paymob', 'p_order_key': str(pm_order(o2['order_id'])), 'p_provider_ref': 'x', 'p_amount_cents': 2850000, 'p_currency': 'EGP', 'p_payload': {}}, owner_t)
T('a member cannot call the server-only confirmation', s >= 400 and s1 >= 400 and sql(f"select status from public.payment_orders where id={o2['order_id']}") == 'pending', (s, s1))
s, _ = http('PATCH', f"/rest/v1/payment_orders?id=eq.{o2['order_id']}", {'status': 'paid'}, owner_t)
s2, _ = http('POST', '/rest/v1/payment_orders', {'user_id': owner, 'product_code': 'vip_year', 'company_id': int(cid), 'method': 'card', 'amount_cents': 1, 'status': 'paid'}, owner_t)
T('orders cannot be written directly (no price or status tampering)', s < 500 and s2 >= 400 and sql(f"select status from public.payment_orders where id={o2['order_id']}") == 'pending'
  and sql(f"select count(*) from public.payment_orders where user_id='{owner}' and amount_cents=1") == '0', (s, s2))
T('a member sees only their own orders', http('GET', '/rest/v1/payment_orders?select=id', None, other_t)[1] == [])
# ── verification follow-ups (0055) ──
def mock_log(): return json.loads(urllib.request.urlopen(MOCK + '/log').read())
def lc(o): return sql(f"select status from public.payment_orders where id={o}")
lid3 = sql(f"insert into public.products (user_id, name, category, type, active) values ('{owner}','Third API {st}','api','supply',true) returning id").split('\n')[0]
olid = sql(f"insert into public.products (user_id, name, category, type, active) values ('{other}','Other API {st}','api','supply',true) returning id").split('\n')[0]
s, x = http('POST', '/functions/v1/payments-create', {'product': 'boost', 'method': 'fawry', 'listing_id': int(olid)}, other_t)
T('Fawry without a mobile in the profile is refused with a clear message — before any order exists', s == 400 and x.get('code') == 'mobile_required' and 'mobile' in x.get('error', '')
  and sql(f"select count(*) from public.payment_orders where listing_id={olid}") == '0', (s, x))
urllib.request.urlopen(urllib.request.Request(MOCK + '/control', data=json.dumps({'fawry_fail': 1}).encode(), method='POST', headers={'Content-Type': 'application/json'}))
s, x = http('POST', '/functions/v1/payments-create', {'product': 'boost', 'method': 'fawry', 'listing_id': int(lid3)}, owner_t)
T('Fawry refuses the charge: the buyer is told and the order is closed at once (failed, not pending)', s == 502 and sql(f"select string_agg(status, ',') from public.payment_orders where listing_id={lid3}") == 'failed', (s, x))
s, f3 = http('POST', '/functions/v1/payments-create', {'product': 'boost', 'method': 'fawry', 'listing_id': int(lid3)}, owner_t)
T('…the order that never got a reference blocks nothing: the retry gets a Fawry reference', s == 200 and f3.get('fawry_reference'), (s, f3))
ch = [l for l in mock_log() if l['path'].startswith('/ECommerceWeb')][-1]['body']
T("Fawry gets the buyer's real name, e-mail (auth record) and mobile (my_profile, normalised)", ch['customerName'] == 'payowner' and ch['customerEmail'] == f'payowner{st}@x.test' and ch['customerMobile'] == '01001234567', ch)
s, x = http('POST', '/functions/v1/payments-create', {'product': 'boost', 'method': 'fawry', 'listing_id': int(lid3)}, owner_t)
T('a second Fawry order is refused while the reference is payable — the message names the Fawry reference, not our order number',
  s == 400 and '(%s)' % f3.get('fawry_reference') in x.get('error', '') and 'DBX' not in x.get('error', ''), (s, x))
pm = [l for l in mock_log() if l['path'] == '/v1/intention/'][-1]['body']['billing_data']
T("Paymob gets the buyer's real name, e-mail and mobile (not 'Drugbox Member / na@drugbox.app / NA')", pm['first_name'] == 'payowner' and pm['email'] == f'payowner{st}@x.test' and pm['phone_number'] == '01001234567', pm)
# 10a: the buyer cancels a pending card order; nothing activates it afterwards
s, oc = http('POST', '/functions/v1/payments-create', {'product': 'featured', 'method': 'card', 'listing_id': int(lid3)}, owner_t)
s1, _ = http('POST', '/rest/v1/rpc/cancel_order', {'p_id': oc['order_id']}, other_t)
T("another member cannot cancel someone's order", s1 >= 400 and lc(oc['order_id']) == 'pending', s1)
s1, r1 = http('POST', '/rest/v1/rpc/cancel_order', {'p_id': oc['order_id']}, owner_t)
T('the buyer cancels their own pending order', s1 == 200 and lc(oc['order_id']) == 'cancelled', (s1, r1))
s1, _ = http('PATCH', f"/rest/v1/payment_orders?id=eq.{oc['order_id']}", {'status': 'pending'}, owner_t)
T('…and cannot set it back to pending through the API', lc(oc['order_id']) == 'cancelled', s1)
late = paymob_obj(oc['order_id'], oc['reference'], 450300)
s1, t1 = http('POST', '/functions/v1/paymob-webhook?hmac=' + paymob_sign(late), {'type': 'TRANSACTION', 'obj': late}, raw=True)
T('a signed callback for the cancelled order activates nothing (refund due, Drugbox told)', t1 == 'order is cancelled (refund due)' and lc(oc['order_id']) == 'cancelled'
  and sql(f"select featured_until is null from public.products where id={lid3}") == 't' and sql(f"select count(*) from public.notifications where user_id='{adm}' and message like '%{oc['reference']} was paid after the buyer cancelled%'") == '1', t1)
s1, _ = http('POST', '/rest/v1/rpc/cancel_order', {'p_id': oid}, owner_t)
T('a paid order cannot be cancelled', s1 >= 400 and lc(oid) == 'paid', s1)
# 10b / 10c: suspended company, inactive listing
cs = sql(f"insert into public.companies (owner_id, name, slug, type, status, sectors) values ('{owner}','Pay Susp {st}','pay-susp-{st}','Manufacturer','verified','{{Manufacturer}}') returning id").split('\n')[0]
sql(f"update public.companies set status='suspended' where id={cs}")
s1, x1 = http('POST', '/functions/v1/payments-create', {'product': 'vip_month', 'method': 'card', 'company_id': int(cs)}, owner_t)
s2, _ = http('POST', '/rest/v1/rpc/create_order', {'p_product': 'vip_year', 'p_method': 'instapay', 'p_company': int(cs)}, owner_t)
T('VIP cannot be bought for a suspended company (function and direct RPC)', s1 == 400 and s2 >= 400 and sql(f"select count(*) from public.payment_orders where company_id={cs}") == '0', (s1, x1, s2))
sql(f"update public.products set active=false where id={lid2}"); n_l2 = sql(f"select count(*) from public.payment_orders where listing_id={lid2}")
s1, _ = http('POST', '/functions/v1/payments-create', {'product': 'boost', 'method': 'card', 'listing_id': int(lid2)}, owner_t)
s2, _ = http('POST', '/rest/v1/rpc/create_order', {'p_product': 'featured', 'p_method': 'card', 'p_listing': int(lid2)}, owner_t)
T('a paid boost / Featured of an inactive listing is refused', s1 == 400 and s2 >= 400 and sql(f"select count(*) from public.payment_orders where listing_id={lid2}") == n_l2, (s1, s2))
# 10d / 10e: InstaPay — one order under review at a time, receipts only in my own folder
s1, i3 = http('POST', '/functions/v1/payments-create', {'product': 'boost', 'method': 'instapay', 'listing_id': int(lid3)}, owner_t)
for bad in (f'payments/{owner}/../{other}/r.png', f'payments/{owner}/sub/r.png', f'payments/{owner}/r .png', f'cv/{owner}/r.png'):
    s2, _ = http('POST', '/rest/v1/rpc/submit_instapay', {'p_id': i3['order_id'], 'p_transfer_ref': 'IPN-424242', 'p_receipt': bad}, owner_t)
    T('a receipt path like %s is refused' % bad.replace(owner, '<me>').replace(other, '<other>'), s2 >= 400 and lc(i3['order_id']) == 'pending', s2)
s2, _ = http('POST', '/rest/v1/rpc/submit_instapay', {'p_id': i3['order_id'], 'p_transfer_ref': 'IPN-424242', 'p_receipt': f'payments/{owner}/r-1.png'}, owner_t)
T('…my own payments/<me>/<file> is accepted (under review)', s2 < 300 and lc(i3['order_id']) == 'review', s2)
s2, x2 = http('POST', '/functions/v1/payments-create', {'product': 'boost', 'method': 'instapay', 'listing_id': int(lid3)}, owner_t)
T('a second InstaPay order for the same listing is refused while one is under review', s2 == 400 and sql(f"select count(*) from public.payment_orders where listing_id={lid3} and method='instapay'") == '1', (s2, x2))
# 8: an issued invoice keeps what it said
s1, inv1 = http('POST', '/rest/v1/rpc/order_invoice', {'p_id': oid}, owner_t)
sql("update public.payment_products set vat_rate=0.15, label='VIP renamed', duration_days=31 where code='vip_month'"); sql("update public.billing_settings set legal_name='Drugbox Renamed S.A.E.' where id")
s2, inv2 = http('POST', '/rest/v1/rpc/order_invoice', {'p_id': oid}, owner_t)
sql("update public.payment_products set vat_rate=0.14, label='VIP — monthly', duration_days=30 where code='vip_month'"); sql("update public.billing_settings set legal_name='Drugbox' where id")
T('an issued invoice does not change when the price list, VAT rate or seller details change later', s1 == 200 and inv1 == inv2 and inv1['product'] == 'VIP — monthly' and float(inv1['vat_rate']) == 0.14 and inv1['days'] == 30, (inv1, inv2))
sql(f"update public.payment_orders set status='refunded' where id={oid}")
s3, inv3 = http('POST', '/rest/v1/rpc/order_invoice', {'p_id': oid}, owner_t)
T("a refunded order's invoice still opens, marked refunded, same number", s3 == 200 and inv3.get('refunded') is True and inv3['invoice_no'] == inv1['invoice_no'], (s3, inv3))
sql(f"update public.payment_orders set status='paid' where id={oid}")
done()
