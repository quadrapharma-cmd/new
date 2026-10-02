// POST { product, method: card|wallet|fawry|instapay, company_id?, listing_id? }  (Authorization: Bearer <user JWT>)
// Creates the order as the user (prices come from the database), then starts the payment with the provider.
import { rpc, select, env } from '../_shared/db.js';
import { fawryChargeSignature } from '../_shared/signatures.js';
const cors = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'authorization, apikey, content-type', 'Access-Control-Allow-Methods': 'POST, OPTIONS' };
const json = (b, s = 200) => new Response(JSON.stringify(b), { status: s, headers: { ...cors, 'Content-Type': 'application/json' } });
export async function handler(req) {
  if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
  if (req.method !== 'POST') return json({ error: 'POST only' }, 405);
  const jwt = (req.headers.get('authorization') || '').replace(/^Bearer /i, ''); if (!jwt) return json({ error: 'Sign in first' }, 401);
  let b; try { b = await req.json(); } catch { return json({ error: 'Bad request' }, 400); }
  if (!['card', 'wallet', 'fawry', 'instapay'].includes(b.method)) return json({ error: 'Choose a payment method' }, 400);
  let order; try { order = await rpc('create_order', { p_product: b.product, p_method: b.method, p_company: b.company_id ?? null, p_listing: b.listing_id ?? null }, jwt); }
  catch (e) { return json({ error: e.message }, e.status === 401 ? 401 : 400); }
  const [me] = await select(`profiles?select=name,email,phone&id=eq.${order.user_id}`, jwt).catch(() => [{}]);
  const [pr] = await select(`payment_products?select=label&code=eq.${order.product_code}`, jwt).catch(() => [{ label: order.product_code }]);
  const amount = order.amount_cents / 100, label = pr.label, fnBase = env('FUNCTIONS_URL', `${env('SUPABASE_URL')}/functions/v1`);
  try {
    if (b.method === 'card' || b.method === 'wallet') {
      const base = env('PAYMOB_BASE', 'https://accept.paymob.com'), integration = Number(env(b.method === 'card' ? 'PAYMOB_CARD_INTEGRATION_ID' : 'PAYMOB_WALLET_INTEGRATION_ID'));
      const [first, ...rest] = String(me.name || 'Drugbox Member').split(' ');
      const r = await fetch(`${base}/v1/intention/`, { method: 'POST', headers: { Authorization: `Token ${env('PAYMOB_SECRET_KEY')}`, 'Content-Type': 'application/json' }, body: JSON.stringify({
        amount: order.amount_cents, currency: 'EGP', payment_methods: [integration], items: [{ name: label, amount: order.amount_cents, description: label, quantity: 1 }],
        billing_data: { first_name: first, last_name: rest.join(' ') || 'NA', email: me.email || 'na@drugbox.app', phone_number: me.phone || b.phone || 'NA', apartment: 'NA', floor: 'NA', street: 'NA', building: 'NA', city: 'NA', country: 'EG', state: 'NA' },
        special_reference: order.merchant_ref, notification_url: `${fnBase}/paymob-webhook`, redirection_url: `${env('APP_URL')}?payment=${order.id}` }) });
      const j = await r.json(); if (!r.ok || !j.client_secret) return json({ error: 'Paymob did not start the payment', detail: j }, 502);
      await rpc('set_order_provider_ref', { p_id: order.id, p_ref: String(j.id || '') });
      return json({ order_id: order.id, reference: order.merchant_ref, amount, checkout_url: `${base}/unifiedcheckout/?publicKey=${encodeURIComponent(env('PAYMOB_PUBLIC_KEY'))}&clientSecret=${encodeURIComponent(j.client_secret)}` });
    }
    if (b.method === 'fawry') {
      const base = env('FAWRY_BASE', 'https://www.atfawry.com'), code = env('FAWRY_MERCHANT_CODE'), key = env('FAWRY_SECURE_KEY'), expiry = Date.now() + 48 * 3600 * 1000;
      const body = { merchantCode: code, merchantRefNum: order.merchant_ref, customerName: me.name || '', customerMobile: me.phone || b.phone || '', customerEmail: me.email || '', customerProfileId: '',
        paymentMethod: 'PAYATFAWRY', amount: amount.toFixed(2), currencyCode: 'EGP', description: label, paymentExpiry: expiry,
        chargeItems: [{ itemId: order.product_code, description: label, price: amount.toFixed(2), quantity: 1 }],
        signature: await fawryChargeSignature(code, order.merchant_ref, '', 'PAYATFAWRY', amount, key) };
      const r = await fetch(`${base}/ECommerceWeb/Fawry/payments/charge`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const j = await r.json(); if (!r.ok || !j.referenceNumber) return json({ error: 'Fawry did not issue a reference number', detail: j }, 502);
      await rpc('set_order_provider_ref', { p_id: order.id, p_ref: String(j.referenceNumber) });
      return json({ order_id: order.id, reference: order.merchant_ref, amount, fawry_reference: j.referenceNumber, expires_at: new Date(expiry).toISOString() });
    }
    return json({ order_id: order.id, reference: order.merchant_ref, amount, instapay: { address: env('INSTAPAY_ADDRESS', ''), name: env('INSTAPAY_NAME', 'Drugbox') } });
  } catch (e) { return json({ error: 'The payment provider could not be reached — try again' }, 502); }
}
if (import.meta.main) Deno.serve(handler);
