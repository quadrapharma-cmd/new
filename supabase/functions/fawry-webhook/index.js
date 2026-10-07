// FawryPay server notification V2: POST JSON with messageSignature. Activation only after the signature matches and status is PAID.
import { rpc, env } from '../_shared/db.js';
import { fawryNotificationSignature, safeEqual } from '../_shared/signatures.js';
export async function handler(req) {
  if (req.method !== 'POST') return new Response('POST only', { status: 405 });
  let b; try { b = await req.json(); } catch { return new Response('bad json', { status: 400 }); }
  const key = env('FAWRY_SECURE_KEY'); if (!key) return new Response('not configured', { status: 503 });   // fail closed: a missing key would sign with "undefined"
  if (!safeEqual(await fawryNotificationSignature(b, key), b.messageSignature)) return new Response('bad signature', { status: 401 });
  if (String(b.orderStatus).toUpperCase() !== 'PAID') return new Response('noted (' + b.orderStatus + ')', { status: 200 });
  // F-115: the signed string joins the fields with no separator, so a signature for merchantRefNumber 'DBX18' + paymentAmount
  // '2850.00' also fits 'DBX182' + '850.00'. Both amounts must be the same real number (Drugbox pays Fawry's fee: the customer
  // pays exactly the order amount), and the database pays an order only for the Fawry reference issued for it (payments-create).
  const paid = Number(b.paymentAmount), ordered = Number(b.orderAmount);
  if (!Number.isFinite(paid) || !Number.isFinite(ordered) || paid <= 0 || paid.toFixed(2) !== ordered.toFixed(2)) return new Response('amount mismatch', { status: 400 });
  if (!b.fawryRefNumber) return new Response('no Fawry reference', { status: 400 });
  // merchantRefNumber, fawryRefNumber and the amounts are all in the signed string; FawryPay charges in EGP only (no currency field)
  const result = await rpc('confirm_payment', { p_provider: 'fawry', p_order_key: String(b.merchantRefNumber ?? b.merchantRefNum ?? ''), p_provider_ref: String(b.fawryRefNumber),
    p_amount_cents: Math.round(Number(b.orderAmount) * 100), p_currency: 'EGP', p_payload: { provider: 'fawry', fawryRefNumber: b.fawryRefNumber, paymentMethod: b.paymentMethod } });
  return new Response(String(result), { status: 200 });
}
if (import.meta.main) Deno.serve(handler);
