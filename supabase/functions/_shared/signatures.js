// Payment signatures (Web Crypto — runs in Supabase Edge Functions/Deno and in Node 18+). Formulas from the providers' docs:
// Paymob transaction callback: HMAC-SHA512, hex, over 20 fields in this exact order, no separators.
// Fawry server notification V2: SHA-256 of fawryRefNumber + merchantRefNumber + paymentAmount(0.00) + orderAmount(0.00)
//   + orderStatus + paymentMethod + paymentRefrenceNumber(if any) + secureKey.
// Fawry charge (PAYATFAWRY): SHA-256 of merchantCode + merchantRefNum + customerProfileId + paymentMethod + amount(0.00) + secureKey.
const enc = new TextEncoder();
const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
export async function sha256(s) { return hex(await crypto.subtle.digest('SHA-256', enc.encode(s))); }
export async function hmacSha512(secret, s) {
  const key = await crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-512' }, false, ['sign']);
  return hex(await crypto.subtle.sign('HMAC', key, enc.encode(s)));
}
export function safeEqual(a, b) { a = String(a || ''); b = String(b || ''); if (a.length !== b.length) return false; let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i); return d === 0; }
const PAYMOB_FIELDS = ['amount_cents', 'created_at', 'currency', 'error_occured', 'has_parent_transaction', 'id', 'integration_id', 'is_3d_secure', 'is_auth',
  'is_capture', 'is_refunded', 'is_standalone_payment', 'is_voided', 'order.id', 'owner', 'pending', 'source_data.pan', 'source_data.sub_type', 'source_data.type', 'success'];
export function paymobString(obj) {
  return PAYMOB_FIELDS.map((f) => { const v = f.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj); return v === undefined || v === null ? '' : String(v); }).join('');
}
export async function paymobHmac(obj, secret) { return hmacSha512(secret, paymobString(obj)); }
const two = (n) => Number(n).toFixed(2);
export async function fawryNotificationSignature(b, secureKey) {
  return sha256(String(b.fawryRefNumber ?? '') + String(b.merchantRefNumber ?? b.merchantRefNum ?? '') + two(b.paymentAmount) + two(b.orderAmount)
    + String(b.orderStatus ?? '') + String(b.paymentMethod ?? '') + String(b.paymentRefrenceNumber ?? b.paymentReferenceNumber ?? '') + secureKey);
}
export async function fawryChargeSignature(merchantCode, merchantRefNum, customerProfileId, paymentMethod, amount, secureKey) {
  return sha256(merchantCode + merchantRefNum + (customerProfileId || '') + paymentMethod + two(amount) + secureKey);
}
