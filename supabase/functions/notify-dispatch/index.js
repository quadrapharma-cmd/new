// E-mails for the notifications people may be waiting for (B-13, migration 0059). notification_outbox is filled by the database;
// this function takes a batch (outbox_claim, service role), sends each through the configured provider and marks it (outbox_done).
// Provider-agnostic: EMAIL_PROVIDER = resend | postmark | sendgrid, with EMAIL_API_KEY and EMAIL_FROM — function secrets only,
// never in the browser or in git. EMAIL_API_BASE points at another server (the local stand-in in tests).
// Called by a scheduler (Supabase cron → POST with Authorization: Bearer <NOTIFY_DISPATCH_SECRET>); nobody else can start it.
// An e-mail carries only Drugbox's own words for the kind of notice and the person's name — never text another member wrote
// (a company's name is set by its owner: in an e-mail from Drugbox it could pose as a warning). The details stay behind sign-in.
import { rpc, env } from '../_shared/db.js';
import { safeEqual } from '../_shared/signatures.js';

const SUBJECT = {
  deal: ['A request or deal needs you', 'طلب أو صفقة في انتظارك'], payment: ['Payment update', 'تحديث بخصوص الدفع'],
  company_invite: ['You are invited to a company team', 'دعوة للانضمام إلى فريق شركة'], company_join_request: ['Someone asked to join your company', 'طلب انضمام إلى شركتك'],
  company_join_answer: ['Your request to join a team was answered', 'تم الرد على طلب انضمامك'], company_message: ['New message to your company', 'رسالة جديدة لشركتك'],
  verification: ['Verification update', 'تحديث بخصوص التوثيق'], cert_checked: ['Certificate checked', 'تمت مراجعة شهادة'], cert_rejected: ['A certificate was not accepted', 'لم تُقبل شهادة'],
  document_reviewed: ['Compliance document checked', 'تمت مراجعة مستند امتثال'], review_reply: ['A company replied to your review', 'ردّت شركة على تقييمك'],
  review_decided: ['A review was checked by Drugbox', 'راجع Drugbox تقييمًا'], report_decided: ['Your report was checked', 'تمت مراجعة بلاغك'],
  company_listing: ['New listing from a company you follow', 'إعلان جديد من شركة تتابعها'],
};
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const clean = (s, n) => String(s ?? '').replace(/[\u0000-\u001f\u007f​-‏‪-‮⁦-⁩]/g, ' ').trim().slice(0, n);

export function compose(row, appUrl) {
  const [en, ar] = SUBJECT[row.kind] || ['New on Drugbox', 'جديد على Drugbox'];
  const name = clean(row.name, 80), link = String(appUrl || '').replace(/\/?$/, '/');
  const subject = 'Drugbox — ' + en;
  const text = `${name ? 'Hello ' + name + ',' : 'Hello,'}\n\n${en}.\nOpen Drugbox to see it: ${link}\n\n${ar}.\nافتح Drugbox لتراه: ${link}\n\n` +
               'You get these e-mails for requests, deals, payments and your company. Turn them off in Drugbox → Settings → Notifications.';
  const html = `<p>${name ? 'Hello ' + esc(name) + ',' : 'Hello,'}</p><p><b>${esc(en)}</b>.</p><p><a href="${esc(link)}">Open Drugbox</a></p>` +
               `<p dir="rtl" lang="ar"><b>${esc(ar)}</b>.<br><a href="${esc(link)}">افتح Drugbox</a></p>` +
               '<p style="color:#64748B;font-size:12px">You get these e-mails for requests, deals, payments and your company. Turn them off in Drugbox → Settings → Notifications.</p>';
  return { subject, text, html };
}

const PROVIDERS = {
  resend: (base, key, from, to, m) => fetch(`${base || 'https://api.resend.com'}/emails`, { method: 'POST', headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ from, to: [to], subject: m.subject, text: m.text, html: m.html }) }),
  postmark: (base, key, from, to, m) => fetch(`${base || 'https://api.postmarkapp.com'}/email`, { method: 'POST', headers: { 'X-Postmark-Server-Token': key, 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ From: from, To: to, Subject: m.subject, TextBody: m.text, HtmlBody: m.html, MessageStream: 'outbound' }) }),
  sendgrid: (base, key, from, to, m) => fetch(`${base || 'https://api.sendgrid.com'}/v3/mail/send`, { method: 'POST', headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ personalizations: [{ to: [{ email: to }] }], from: { email: from.replace(/^.*<|>.*$/g, '') }, subject: m.subject, content: [{ type: 'text/plain', value: m.text }, { type: 'text/html', value: m.html }] }) }),
};

export async function handler(req) {
  if (req.method !== 'POST') return new Response('POST only', { status: 405 });
  const secret = env('NOTIFY_DISPATCH_SECRET'), provider = PROVIDERS[env('EMAIL_PROVIDER', '')], key = env('EMAIL_API_KEY'), from = env('EMAIL_FROM');
  if (!secret || !provider || !key || !from) return new Response('not configured', { status: 503 });          // fail closed
  const auth = (req.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (!safeEqual(auth, secret)) return new Response('not allowed', { status: 401 });
  let limit = 50; try { const b = await req.json(); if (b && Number.isInteger(b.limit)) limit = Math.min(Math.max(b.limit, 1), 200); } catch { /* no body: the default batch */ }
  const rows = await rpc('outbox_claim', { p_limit: limit });
  let sent = 0, failed = 0;
  for (const row of rows || []) {
    const to = clean(row.email, 254);
    if (!/^[^\s@<>"]+@[^\s@<>"]+\.[^\s@<>"]+$/.test(to)) { await rpc('outbox_done', { p_id: row.id, p_ok: false, p_error: 'no valid e-mail address' }); failed++; continue; }
    let ok = false, err = '';
    try { const r = await provider(env('EMAIL_API_BASE'), key, from, to, compose(row, env('APP_URL'))); ok = r.ok; if (!ok) err = `provider answered ${r.status}: ${(await r.text()).slice(0, 200)}`; }
    catch (e) { err = String(e && e.message || e).slice(0, 200); }
    await rpc('outbox_done', { p_id: row.id, p_ok: ok, p_error: ok ? null : err });
    ok ? sent++ : failed++;
  }
  return new Response(JSON.stringify({ sent, failed }), { status: 200, headers: { 'content-type': 'application/json' } });
}
if (import.meta.main) Deno.serve(handler);
