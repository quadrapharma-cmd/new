// POST { product, method: card|wallet|fawry|instapay, company_id?, listing_id? }  (Authorization: Bearer <user JWT>)
// Creates the order as the user (prices come from the database), then starts the payment with the provider.
import { rpc, select, env, cfg } from '../_shared/db.js';
import { fawryChargeSignature } from '../_shared/signatures.js';
// CORS: only the app's own site may call this from a browser — ALLOWED_ORIGINS (comma-separated) or else the origin of APP_URL.
// Calls without an Origin header (servers, tests) are not browser calls and are judged by the user's JWT alone.
const origins = () => (env('ALLOWED_ORIGINS') || env('APP_URL') || '').split(',').map((u) => { try { return new URL(u.trim()).origin; } catch { return ''; } }).filter(Boolean);
// an Egyptian mobile as Fawry and Paymob want it (01xxxxxxxxx), from what the person wrote (+20 100 …, 0020…, spaces, dashes)
export function egMobile(v) {
  let d = String(v || '').replace(/[^\d+]/g, '').replace(/^\+/, '').replace(/^00/, '');
  if (/^20\d{10}$/.test(d)) d = '0' + d.slice(2); if (/^1\d{9}$/.test(d)) d = '0' + d;
  return /^01[0125]\d{8}$/.test(d) ? d : '';
}
export async function handler(req) {
  const origin = req.headers.get('origin'), cors = { 'Access-Control-Allow-Headers': 'authorization, apikey, content-type', 'Access-Control-Allow-Methods': 'POST, OPTIONS', Vary: 'Origin' };
  if (origin && origins().includes(origin)) cors['Access-Control-Allow-Origin'] = origin;
  const json = (b, s = 200) => new Response(JSON.stringify(b), { status: s, headers: { ...cors, 'Content-Type': 'application/json' } });
  if (origin && !cors['Access-Control-Allow-Origin']) return json({ error: 'Origin not allowed' }, 403);
  if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
  if (req.method !== 'POST') return json({ error: 'POST only' }, 405);
  const jwt = (req.headers.get('authorization') || '').replace(/^Bearer /i, ''); if (!jwt) return json({ error: 'Sign in first' }, 401);
  let b; try { b = await req.json(); } catch { return json({ error: 'Bad request' }, 400); }
  if (!['card', 'wallet', 'fawry', 'instapay'].includes(b.method)) return json({ error: 'Choose a payment method' }, 400);
  // who pays (before any order exists): the name from profiles (named columns), the e-mail from the user's own auth record, the
  // mobile from my_profile() — phone is private since 0036, so it is read as the user, never with select=*
  const c = cfg(); let user;
  try { const r = await fetch(`${c.url}/auth/v1/user`, { headers: { apikey: c.anon, Authorization: `Bearer ${jwt}` } }); if (!r.ok) return json({ error: 'Sign in first' }, 401); user = await r.json(); }
  catch { return json({ error: 'Sign in first' }, 401); }
  if (!user || !user.id) return json({ error: 'Sign in first' }, 401);
  const [prof] = await select(`profiles?select=name&id=eq.${encodeURIComponent(user.id)}`, jwt).catch(() => [{}]);
  const mine = await rpc('my_profile', {}, jwt).catch(() => []), own = (Array.isArray(mine) ? mine[0] : mine) || {};
  const me = { name: String((prof && prof.name) || own.name || '').trim(), email: String(user.email || '').trim(), mobile: egMobile(own.phone) };
  // FawryPay issues a reference only with the payer's mobile (it is texted the reference): asked for before anything is created
  if (b.method === 'fawry' && !me.mobile) return json({ error: 'Add your mobile number (01…) to your profile to pay at Fawry — Fawry sends the reference to it', code: 'mobile_required' }, 400);
  let order; try { order = await rpc('create_order', { p_product: b.product, p_method: b.method, p_company: b.company_id ?? null, p_listing: b.listing_id ?? null }, jwt); }
  catch (e) { return json({ error: e.message }, e.status === 401 ? 401 : 400); }
  const [pr] = await select(`payment_products?select=label&code=eq.${order.product_code}`, jwt).catch(() => [{ label: order.product_code }]);
  const amount = order.amount_cents / 100, label = (pr && pr.label) || order.product_code, fnBase = env('FUNCTIONS_URL', `${env('SUPABASE_URL')}/functions/v1`);
  // the provider did not start the payment: the order is closed at once (server-side, payment_start_failed) so it never blocks the next try
  const failed = async (status, body, detail) => { await rpc('payment_start_failed', { p_id: order.id, p_detail: detail ?? null }).catch(() => {}); return json(body, status); };
  let issued = false;   // the provider accepted: from here an error never closes the order (its money may still come)
  try {
    if (b.method === 'card' || b.method === 'wallet') {
      const base = env('PAYMOB_BASE', 'https://accept.paymob.com'), integration = Number(env(b.method === 'card' ? 'PAYMOB_CARD_INTEGRATION_ID' : 'PAYMOB_WALLET_INTEGRATION_ID'));
      const [first, ...rest] = (me.name || 'Drugbox Member').split(/\s+/);
      const r = await fetch(`${base}/v1/intention/`, { method: 'POST', headers: { Authorization: `Token ${env('PAYMOB_SECRET_KEY')}`, 'Content-Type': 'application/json' }, body: JSON.stringify({
        amount: order.amount_cents, currency: 'EGP', payment_methods: [integration], items: [{ name: label, amount: order.amount_cents, description: label, quantity: 1 }],
        billing_data: { first_name: first, last_name: rest.join(' ') || 'NA', email: me.email, phone_number: me.mobile || 'NA', apartment: 'NA', floor: 'NA', street: 'NA', building: 'NA', city: 'NA', country: 'EG', state: 'NA' },
        special_reference: order.merchant_ref, notification_url: `${fnBase}/paymob-webhook`, redirection_url: `${env('APP_URL')}?payment=${order.id}` }) });
      // Paymob's order id (intention_order_id) is what its signed callback names: without it the payment could never be confirmed
      const j = await r.json().catch(() => ({}));
      if (!r.ok || !j.client_secret || !j.intention_order_id) return failed(502, { error: 'Paymob did not start the payment — nothing was charged; please try again' }, { provider: 'paymob', status: r.status });
      issued = true; await rpc('set_order_provider_ref', { p_id: order.id, p_ref: String(j.id || ''), p_order: String(j.intention_order_id) });
      return json({ order_id: order.id, reference: order.merchant_ref, amount, checkout_url: `${base}/unifiedcheckout/?publicKey=${encodeURIComponent(env('PAYMOB_PUBLIC_KEY'))}&clientSecret=${encodeURIComponent(j.client_secret)}` });
    }
    if (b.method === 'fawry') {
      const base = env('FAWRY_BASE', 'https://www.atfawry.com'), code = env('FAWRY_MERCHANT_CODE'), key = env('FAWRY_SECURE_KEY'), expiry = Date.now() + 48 * 3600 * 1000;
      const body = { merchantCode: code, merchantRefNum: order.merchant_ref, customerName: me.name, customerMobile: me.mobile, customerEmail: me.email, customerProfileId: '',
        paymentMethod: 'PAYATFAWRY', amount: amount.toFixed(2), currencyCode: 'EGP', description: label, paymentExpiry: expiry,
        chargeItems: [{ itemId: order.product_code, description: label, price: amount.toFixed(2), quantity: 1 }],
        signature: await fawryChargeSignature(code, order.merchant_ref, '', 'PAYATFAWRY', amount, key) };
      const r = await fetch(`${base}/ECommerceWeb/Fawry/payments/charge`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok || !j.referenceNumber) return failed(502, { error: 'Fawry did not issue a reference number — nothing was charged; please try again' }, { provider: 'fawry', statusCode: j.statusCode ?? r.status, statusDescription: j.statusDescription ?? null });
      issued = true; await rpc('set_order_provider_ref', { p_id: order.id, p_ref: String(j.referenceNumber), p_expires: new Date(expiry).toISOString() });   // found again in My payments until it expires
      return json({ order_id: order.id, reference: order.merchant_ref, amount, fawry_reference: j.referenceNumber, expires_at: new Date(expiry).toISOString() });
    }
    return json({ order_id: order.id, reference: order.merchant_ref, amount, instapay: { address: env('INSTAPAY_ADDRESS', ''), name: env('INSTAPAY_NAME', 'Drugbox') } });
  } catch (e) {
    if (issued) return json({ error: 'The payment started but could not be recorded yet — look in My payments in a minute' }, 502);
    return failed(502, { error: 'The payment provider could not be reached — nothing was charged; please try again' }, { error: 'unreachable' }); }
}
if (import.meta.main) Deno.serve(handler);
