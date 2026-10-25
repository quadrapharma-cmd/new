// The phone verification codes (W-20, migration 0093). private.sms_outbox is filled by phone_verify_start; this function takes a batch
// (sms_claim, service role), sends each through the configured SMS provider and marks it (sms_done). A code is never older than its
// 10 minutes when it goes out and gets at most 3 tries.
// Provider-agnostic: SMS_PROVIDER = twilio | vonage, with SMS_ACCOUNT (Twilio Account SID / Vonage API key), SMS_TOKEN (auth token /
// API secret) and SMS_FROM (a sender number or an approved sender id) — function secrets only, never in the browser or in git.
// SMS_API_BASE points at another server (the local stand-in in tests). Called by a scheduler (every minute) with
// Authorization: Bearer <SMS_DISPATCH_SECRET>; nobody else can start it. The text is Drugbox's own (the code), nothing a member wrote.
import { rpc, env } from '../_shared/db.js';
import { safeEqual } from '../_shared/signatures.js';

const b64 = (s) => (globalThis.btoa ? btoa(s) : Buffer.from(s).toString('base64'));
const PROVIDERS = {
  twilio: (base, acc, tok, from, to, text) => fetch(`${base || 'https://api.twilio.com'}/2010-04-01/Accounts/${encodeURIComponent(acc)}/Messages.json`, { method: 'POST',
    headers: { Authorization: 'Basic ' + b64(acc + ':' + tok), 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ From: from, To: to, Body: text }).toString() }),
  vonage: (base, acc, tok, from, to, text) => fetch(`${base || 'https://rest.nexmo.com'}/sms/json`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: acc, api_secret: tok, from, to: to.replace(/^\+/, ''), text, type: 'unicode' }) }),
};
// Vonage answers 200 with a status per message; Twilio answers 201
async function okOf(name, r) {
  if (!r.ok) return [false, `provider answered ${r.status}: ${(await r.text()).slice(0, 200)}`];
  if (name === 'vonage') { const j = await r.json().catch(() => ({})); const m = (j.messages || [])[0] || {}; return m.status === '0' ? [true, ''] : [false, 'provider refused: ' + String(m['error-text'] || m.status || 'unknown').slice(0, 200)]; }
  return [true, ''];
}

export async function handler(req) {
  if (req.method !== 'POST') return new Response('POST only', { status: 405 });
  const name = env('SMS_PROVIDER', ''), provider = PROVIDERS[name], secret = env('SMS_DISPATCH_SECRET'), acc = env('SMS_ACCOUNT'), tok = env('SMS_TOKEN'), from = env('SMS_FROM');
  if (!secret || !provider || !acc || !tok || !from) return new Response('not configured', { status: 503 });   // fail closed
  const auth = (req.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (!safeEqual(auth, secret)) return new Response('not allowed', { status: 401 });
  let limit = 50; try { const b = await req.json(); if (b && Number.isInteger(b.limit)) limit = Math.min(Math.max(b.limit, 1), 200); } catch { /* no body: the default batch */ }
  const rows = await rpc('sms_claim', { p_limit: limit });
  let sent = 0, failed = 0;
  for (const row of rows || []) {
    let ok = false, err = '';
    if (!/^\+[1-9]\d{6,14}$/.test(String(row.phone || ''))) err = 'not a phone number';
    else try { [ok, err] = await okOf(name, await provider(env('SMS_API_BASE'), acc, tok, from, row.phone, String(row.body || '').slice(0, 300))); }
    catch (e) { err = String(e && e.message || e).slice(0, 200); }
    await rpc('sms_done', { p_id: row.id, p_ok: ok, p_error: ok ? null : err });
    ok ? sent++ : failed++;
  }
  return new Response(JSON.stringify({ sent, failed }), { status: 200, headers: { 'content-type': 'application/json' } });
}
if (import.meta.main) Deno.serve(handler);
