// FawryPay server notification V2: POST JSON with messageSignature. Activation only after the signature matches and status is PAID.
import { rpc, env } from '../_shared/db.js';
import { fawryNotificationSignature, safeEqual } from '../_shared/signatures.js';
export async function handler(req) {
  if (req.method !== 'POST') return new Response('POST only', { status: 405 });
  let b; try { b = await req.json(); } catch { return new Response('bad json', { status: 400 }); }
  if (!safeEqual(await fawryNotificationSignature(b, env('FAWRY_SECURE_KEY')), b.messageSignature)) return new Response('bad signature', { status: 401 });
  if (String(b.orderStatus).toUpperCase() !== 'PAID') return new Response('noted (' + b.orderStatus + ')', { status: 200 });
  const result = await rpc('confirm_payment', { p_merchant_ref: String(b.merchantRefNumber || b.merchantRefNum), p_provider_ref: String(b.fawryRefNumber), p_amount_cents: Math.round(Number(b.orderAmount) * 100),
    p_payload: { provider: 'fawry', fawryRefNumber: b.fawryRefNumber, paymentMethod: b.paymentMethod } });
  return new Response(String(result), { status: 200 });
}
if (import.meta.main) Deno.serve(handler);
