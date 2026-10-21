// POST (Authorization: Bearer <service role key>) — run every minute by a schedule (Supabase cron → this function).
// Sends the notices members chose to get by e-mail (Settings → Notifications) and their daily / weekly digests:
// email_outbox_claim hands out what is due, each one is sent through Resend, email_outbox_done records the outcome
// (a failure is tried again in 5 minutes, at most 5 times). Secrets: RESEND_API_KEY, MAIL_FROM (e.g. "Drugbox <notify@drugbox.app>"),
// APP_URL (the link in each e-mail); RESEND_URL only to point at a stand-in (tests).
import { rpc, env } from '../_shared/db.js';

const T = {
  en: {
    message: (f) => [`${f} sent you a message on Drugbox`, `${f} sent you a message.`, 'Open the conversation'],
    connection_request: (f) => [`${f} wants to connect on Drugbox`, `${f} sent you a connection request.`, 'See the request'],
    connection_accepted: (f) => [`${f} accepted your connection request`, `${f} accepted your connection request — you are now connected.`, 'View profile'],
    comment: (f) => [`${f} commented on your post`, `${f} commented on your post.`, 'See the comment'],
    reply: (f) => [`${f} replied to your comment`, `${f} replied to your comment.`, 'See the reply'],
    mention: (f) => [`${f} mentioned you in a post`, `${f} mentioned you in a post.`, 'See the post'],
    like: (f) => [`${f} reacted to your post`, `${f} reacted to your post.`, 'See the post'],
    comment_like: (f) => [`${f} liked your comment`, `${f} liked your comment.`, 'See the post'],
    repost: (f) => [`${f} reposted your post`, `${f} reposted your post.`, 'See the post'],
    follow: (f) => [`${f} started following you`, `${f} started following you on Drugbox.`, 'View profile'],
    job_application: (f) => [`${f} applied to your job`, `${f} applied to your job.`, 'See the application'],
    saved_search: (f, n) => ['New match for your saved search', String(n.message || 'A new listing matches your saved search.'), 'See it'],
    other: (f) => ['New activity on Drugbox', `${f} — new activity on Drugbox.`, 'Open Drugbox'],
    digest: ['Your Drugbox summary', 'Here is what you missed:', 'Open Drugbox'], someone: 'A member',
    foot: 'You get this e-mail because of your Drugbox notification settings.', manage: 'Change what Drugbox e-mails you'
  },
  ar: {
    message: (f) => [`${f} أرسل لك رسالة على Drugbox`, `${f} أرسل لك رسالة.`, 'افتح المحادثة'],
    connection_request: (f) => [`${f} يريد التواصل معك على Drugbox`, `${f} أرسل لك طلب تواصل.`, 'اعرض الطلب'],
    connection_accepted: (f) => [`${f} قبل طلب التواصل`, `${f} قبل طلب التواصل — أصبحتما متصلين.`, 'اعرض الملف'],
    comment: (f) => [`${f} علّق على منشورك`, `${f} علّق على منشورك.`, 'اعرض التعليق'],
    reply: (f) => [`${f} ردّ على تعليقك`, `${f} ردّ على تعليقك.`, 'اعرض الرد'],
    mention: (f) => [`${f} أشار إليك في منشور`, `${f} أشار إليك في منشور.`, 'اعرض المنشور'],
    like: (f) => [`${f} تفاعل مع منشورك`, `${f} تفاعل مع منشورك.`, 'اعرض المنشور'],
    comment_like: (f) => [`${f} أعجبه تعليقك`, `${f} أعجبه تعليقك.`, 'اعرض المنشور'],
    repost: (f) => [`${f} أعاد نشر منشورك`, `${f} أعاد نشر منشورك.`, 'اعرض المنشور'],
    follow: (f) => [`${f} بدأ متابعتك`, `${f} بدأ متابعتك على Drugbox.`, 'اعرض الملف'],
    job_application: (f) => [`${f} تقدّم لوظيفتك`, `${f} تقدّم لوظيفتك.`, 'اعرض الطلب'],
    saved_search: () => ['نتيجة جديدة لبحثك المحفوظ', 'عرض جديد يطابق بحثك المحفوظ.', 'اعرضه'],
    other: (f) => ['نشاط جديد على Drugbox', `${f} — نشاط جديد على Drugbox.`, 'افتح Drugbox'],
    digest: ['ملخص Drugbox', 'هذا ما فاتك:', 'افتح Drugbox'], someone: 'عضو',
    foot: 'تصلك هذه الرسالة حسب إعدادات الإشعارات في Drugbox.', manage: 'غيّر ما يرسله Drugbox إلى بريدك'
  }
};
const escH = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
function link(app, n) {
  if (!n) return app;
  if (n.post_id) return `${app}#/post/${n.post_id}`;
  if (n.type === 'message' && n.from_id) return `${app}#/messages/${n.from_id}`;
  if (/^(connection_request|connection_accepted|follow)$/.test(n.type) && n.from_id) return `${app}#/profile/${n.from_id}`;
  if (n.type === 'job_application' || (n.type === 'saved_search' && n.data && n.data.kind === 'jobs')) return `${app}#/jobs`;
  if (n.type === 'saved_search') return `${app}#/market`;
  return `${app}#/notifs`;
}
export function compose(m, app) {
  const L = T[m.lang === 'ar' ? 'ar' : 'en'], dir = m.lang === 'ar' ? 'rtl' : 'ltr';
  let subject, line, button, url, list = '';
  if (m.kind === 'digest') {
    [subject, line, button] = L.digest; url = `${app}#/notifs`;
    list = (m.digest || []).map((d) => `<li>${escH(d.from || L.someone)} — ${escH((L[d.type] || L.other)(d.from || L.someone, d)[0])}</li>`).join('');
  } else {
    const n = m.notice || {}, from = n.from || L.someone;
    [subject, line, button] = (L[n.type] || L.other)(from, n); url = link(app, n);
  }
  const html = `<div dir="${dir}" style="font-family:Arial,sans-serif;font-size:15px;color:#1c1e21;max-width:520px">` +
    `<p>${escH(line)}</p>${list ? `<ul>${list}</ul>` : ''}<p><a href="${escH(url)}" style="display:inline-block;background:#1a56db;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none">${escH(button)}</a></p>` +
    `<p style="font-size:12px;color:#65676b">${escH(L.foot)} <a href="${escH(app)}#/settings">${escH(L.manage)}</a></p></div>`;
  const text = `${line}\n${(m.digest || []).map((d) => '- ' + (d.from || L.someone) + ': ' + (L[d.type] || L.other)(d.from || L.someone, d)[0]).join('\n')}\n${button}: ${url}\n\n${L.foot} ${app}#/settings`;
  return { subject, html, text, url };
}
export async function handler(req) {
  const json = (b, s = 200) => new Response(JSON.stringify(b), { status: s, headers: { 'Content-Type': 'application/json' } });
  if (req.method !== 'POST') return json({ error: 'POST only' }, 405);
  const service = env('SUPABASE_SERVICE_ROLE_KEY'), auth = (req.headers.get('authorization') || '').replace(/^Bearer /i, '');
  if (!service || auth !== service) return json({ error: 'Not allowed' }, 401);         // only the schedule (service role) runs it
  const key = env('RESEND_API_KEY'), from = env('MAIL_FROM') || 'Drugbox <notify@drugbox.app>', api = env('RESEND_URL') || 'https://api.resend.com/emails';
  const app = (env('APP_URL') || '').replace(/#.*$/, '');
  if (!key) return json({ error: 'RESEND_API_KEY is not set' }, 500);
  let due; try { due = await rpc('email_outbox_claim', { p_limit: 50 }); } catch (e) { return json({ error: e.message }, 500); }
  let sent = 0, failed = 0;
  for (const m of due || []) {
    if (!m.to) { await rpc('email_outbox_done', { p_id: m.id, p_ok: false, p_error: 'no address' }); failed++; continue; }
    if (m.kind !== 'digest' && m.notice && m.notice.read) { await rpc('email_outbox_done', { p_id: m.id, p_ok: true }); continue; }   // already seen in the app
    const c = compose(m, app);
    try {
      const r = await fetch(api, { method: 'POST', headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ from, to: [m.to], subject: c.subject, html: c.html, text: c.text }) });
      if (!r.ok) throw new Error(`Resend ${r.status}: ${(await r.text()).slice(0, 200)}`);
      await rpc('email_outbox_done', { p_id: m.id, p_ok: true }); sent++;
    } catch (e) { await rpc('email_outbox_done', { p_id: m.id, p_ok: false, p_error: String(e.message || e) }); failed++; }
  }
  return json({ sent, failed });
}
if (import.meta.main) Deno.serve(handler);
