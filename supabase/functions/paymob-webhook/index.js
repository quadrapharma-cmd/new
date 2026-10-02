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
  const ref = (obj.order && (obj.order.merchant_order_id || obj.order.special_reference)) || obj.special_reference;
  const result = await rpc('confirm_payment', { p_merchant_ref: String(ref || ''), p_provider_ref: String(obj.id), p_amount_cents: Number(obj.amount_cents), p_payload: { provider: 'paymob', id: obj.id, order: obj.order && obj.order.id, type: obj.source_data && obj.source_data.type } });
  return new Response(String(result), { status: 200 });      // 200 even for "already paid" so Paymob stops retrying
}
if (import.meta.main) Deno.serve(handler);
