// Paymob "transaction processed" callback: POST { type: 'TRANSACTION', obj } with ?hmac=…  Activation only after the HMAC matches.
import { rpc, env } from '../_shared/db.js';
import { paymobHmac, safeEqual } from '../_shared/signatures.js';
export async function handler(req) {
  if (req.method !== 'POST') return new Response('POST only', { status: 405 });
  const hmac = new URL(req.url).searchParams.get('hmac'); let body; try { body = await req.json(); } catch { return new Response('bad json', { status: 400 }); }
  const obj = body && body.obj; if (!obj) return new Response('no transaction', { status: 400 });
  if (!safeEqual(await paymobHmac(obj, env('PAYMOB_HMAC_SECRET')), hmac)) return new Response('bad signature', { status: 401 });
  const ok = obj.success === true && obj.pending === false && !obj.is_voided && !obj.is_refunded && !obj.error_occured;
  if (!ok) return new Response('noted (not a successful payment)', { status: 200 });
  // The order is found by Paymob's order id: obj.order.id is part of the signed string, merchant_order_id is not (a valid
  // callback re-sent with another merchant_order_id must not pay another order). Amount and currency are checked against the order.
  const order = obj.order && typeof obj.order === 'object' ? obj.order : {};
  if (order.id === undefined || order.id === null || order.id === '') return new Response('unknown order', { status: 200 });
  const result = await rpc('confirm_payment', { p_provider: 'paymob', p_order_key: String(order.id), p_provider_ref: String(obj.id), p_amount_cents: Number(obj.amount_cents),
    p_currency: String(obj.currency || ''), p_payload: { provider: 'paymob', id: obj.id, order: order.id, merchant_order_id: order.merchant_order_id ?? null, type: obj.source_data && obj.source_data.type } });
  return new Response(String(result), { status: 200 });      // 200 even for "already paid" so Paymob stops retrying
}
if (import.meta.main) Deno.serve(handler);
