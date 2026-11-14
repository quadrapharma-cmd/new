// The ready dossier (Part 2, step 2.8): the dossier's folder in the country's shape — one folder per module and per place, each
// document named by its place — and the readiness report: what the program did by itself, what was done by hand (with the reasons
// given), and what is still missing or wrong. EDA prescribes the CTD's numbering and searchable PDFs, but no folder or file names
// for the CTD soft copy (NP.CAPP.065 v5): the layout below is the program's own, and the report says so.
import { zipOf } from './zipw.js';
import { dataOf } from './generators.js';

const BAD = /[<>:"/\\|?*\x00-\x1f]/g;
// A Windows-safe name of at most n characters that does not end inside a word.
export function clean(s, n = 48) {
  let t = String(s || '').replace(/[—–]/g, '-').replace(/\s+/g, ' ').trim().replace(/\.$/, '');
  if (t.length > n) {
    const cut = t.slice(0, n);
    const at = Math.max(cut.lastIndexOf(' - '), cut.lastIndexOf(': '), cut.lastIndexOf(' ('), cut.lastIndexOf(', '));
    t = at >= n * 0.4 ? cut.slice(0, at) : (t[n] !== ' ' && cut.lastIndexOf(' ') >= n * 0.4 ? cut.slice(0, cut.lastIndexOf(' ')) : cut);
    if ((t.match(/\(/g) || []).length > (t.match(/\)/g) || []).length) t = t.slice(0, t.lastIndexOf('('));
    t = t.replace(/(\s+(of|the|for|and|or|in|on|to|a|an|with|by|from|at|per|&|-))+\s*$/i, '');
  }
  return t.replace(BAD, ' ').replace(/\s+/g, ' ').trim().replace(/[ \-.,:;+/&]+$/, '') || 'x';
}
const ext = doc => (doc.madeBy === 'program' ? 'docx' : doc.kind === 'docx' ? 'docx' : doc.kind === 'doc' ? 'doc' : ['png', 'jpeg', 'tiff', 'gif', 'webp'].includes(doc.kind) ? doc.kind.replace('jpeg', 'jpg') : 'pdf');
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// Where each document goes in the folder: [{doc, path}] (documents of one place numbered (2), (3)…).
export function layoutOf(d, board) {
  const root = clean(dataOf(d).trade_name?.value || d.name || 'Dossier', 60);
  const out = [];
  for (const place of board.places) {
    const docs = d.docs.filter(x => x.place === place.id && !x.dup && !x.split && !x.unread);
    if (!docs.length) continue;
    const sec = place.ctd.split(' (')[0];
    const folder = `${root}/Module ${place.module}/${clean(`${sec} ${place.title.en}`, 64)}`;
    docs.forEach((doc, i) => out.push({ doc, place, path: `${folder}/${clean(`${sec} ${place.title.en}`, 56)}${docs.length > 1 ? ` (${i + 1})` : ''}.${ext(doc)}` }));
  }
  return { root, files: out };
}

export function readiness(d, board, findings, needs) {
  const open = board.places.filter(p => p.level === 'R' || p.level === 'O');
  const filled = new Set(d.docs.filter(x => x.place && !x.dup && !x.split && !x.unread).map(x => x.place));
  const red = findings.filter(f => !f.accepted && f.level === 'red' && f.kind !== 'missing'), amber = findings.filter(f => !f.accepted && f.level === 'amber' && f.kind !== 'missing');
  const required = open.filter(p => p.level === 'R');
  return { required: required.length, filled: required.filter(p => filled.has(p.id)).length, red: red.length, amber: amber.length,
           accepted: findings.filter(f => f.accepted).length, needs: needs.length,
           ready: red.length === 0 && required.every(p => filled.has(p.id) || findings.some(f => f.place === p.id && f.kind === 'missing' && f.accepted)) };
}

const DONE = { received: 'استلم الملفات', cut: 'قطّع ملف مجمّع', understood: 'قرا المستندات وحطها في أماكنها', 'placed-by-claude': 'Claude حط مستند في مكانه',
               fixed: 'صلّح ملف', created: 'عمل مسودة', moved: 'نقلت مستند لمكان تاني', accepted: 'قبلت ملاحظة بسبب', uploaded: 'رفعت نسخة جديدة', confirmed: 'أكدت' };

export function reportHtml(d, board, findings, needs, layout) {
  const r = readiness(d, board, findings, needs);
  const place = id => board.places.find(p => p.id === id);
  const byProgram = d.log.filter(e => ['received', 'cut', 'understood', 'placed-by-claude', 'fixed', 'created'].includes(e.what));
  const byYou = d.log.filter(e => ['moved', 'accepted', 'uploaded', 'confirmed'].includes(e.what));
  const row = cells => `<tr>${cells.map(c => `<td>${c}</td>`).join('')}</tr>`;
  const missing = board.places.filter(p => p.level === 'R' && !layout.files.some(f => f.place.id === p.id));
  return `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>تقرير الجاهزية — ${esc(layout.root)}</title>
<style>body{font:14px/1.6 "Segoe UI",Tahoma,sans-serif;max-width:960px;margin:24px auto;padding:0 16px;color:#15212a}h1{font-size:22px}h2{font-size:17px;margin-top:28px}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{border:1px solid #ccd;padding:4px 8px;text-align:start;vertical-align:top}.ok{color:#1d7347}.bad{color:#a8203a}.warn{color:#965206}
.ltr{direction:ltr;unicode-bidi:isolate}small{color:#56646d}</style></head><body>
<h1>تقرير الجاهزية — <span class="ltr">${esc(layout.root)}</span></h1>
<p>${esc(board.country.ar)} · ${esc(board.country.note)} · العمود ${esc(board.column)} · ${esc(new Date().toISOString().slice(0, 10))}</p>
<p class="${r.ready ? 'ok' : 'bad'}"><b>${r.ready ? 'الملف جاهز: كل الأماكن المطلوبة فيها مستندات، ومفيش ملاحظة لازم تتحل.' : 'الملف لسه مش جاهز.'}</b>
الأماكن المطلوبة: ${r.filled} من ${r.required} فيها مستندات · ملاحظات لازم تتحل: ${r.red} · لازم تتوضح: ${r.amber} · اتقبلت بسبب: ${r.accepted}</p>
<h2>اللي البرنامج عمله لوحده</h2><ul>${byProgram.map(e => `<li>${esc(DONE[e.what] || e.what)} <small>${esc(e.at.slice(0, 16).replace('T', ' '))}</small></li>`).join('') || '<li>—</li>'}</ul>
<h2>اللي اتعمل بإيدك</h2><ul>${byYou.map(e => `<li>${esc(DONE[e.what] || e.what)}${e.reason ? `: «${esc(e.reason)}»` : ''} <small>${esc(e.at.slice(0, 16).replace('T', ' '))}</small></li>`).join('') || '<li>—</li>'}</ul>
<h2>لسه ناقص أو غلط</h2>
<table><tr><th>المستوى</th><th>الملاحظة</th><th>القاعدة</th></tr>${findings.filter(f => !f.accepted).map(f => row([`<span class="${f.level === 'red' ? 'bad' : 'warn'}">${f.level === 'red' ? 'لازم تتحل' : 'لازم تتوضح'}</span>`, esc(f.title), esc(f.rule?.ar || '')])).join('')}</table>
${missing.length ? `<p class="bad">أماكن مطلوبة فاضية: ${missing.map(p => `<span class="ltr">${esc(p.ctd)}</span> ${esc(p.title.ar)}`).join('، ')}</p>` : ''}
<h2>ملفات الفولدر</h2><table><tr><th>المكان</th><th>الملف</th><th>من</th></tr>${layout.files.map(f => row([`<span class="ltr">${esc(f.place.ctd)}</span> ${esc(f.place.title.ar)}`, `<span class="ltr">${esc(f.path)}</span>`, esc(f.doc.madeBy === 'program' ? 'مسودة من البرنامج' : f.doc.name)])).join('')}</table>
<p><small>هيئة الدواء بتحدد ترقيم الـ CTD وإن الملفات تبقى PDF يتبحث فيه (NP.CAPP.065 الإصدار 5، الملاحظة العامة 4)، لكن مابتحددش أسماء الفولدرات والملفات لنسخة الـ CTD: التقسيم ده من البرنامج. المسودات اللي البرنامج عملها Word: بتتطبع على ورق الشركة وتتمضي وتتختم وتترفع ممسوحة.</small></p>
</body></html>`;
}

// The folder as a ZIP: the documents (each in its latest version), the report and a checklist.
export async function readyZip(d, board, findings, needs, { getBlob, draftBytes }) {
  const layout = layoutOf(d, board);
  const files = [];
  for (const f of layout.files) {
    const bytes = f.doc.madeBy === 'program' && draftBytes ? await draftBytes(f.doc) : await getBlob(d.id, f.doc.fixed || f.doc.sha);
    if (bytes) files.push({ name: f.path, bytes });
  }
  const enc = s => new TextEncoder().encode(s);
  files.push({ name: `${layout.root}/00 تقرير الجاهزية.html`, bytes: enc(reportHtml(d, board, findings, needs, layout)) });
  const csv = ['place,ctd,level,files', ...board.places.filter(p => p.level !== 'NA').map(p => [p.id, p.ctd, p.level, layout.files.filter(f => f.place.id === p.id).length].map(x => `"${String(x).replace(/"/g, '""')}"`).join(','))].join('\r\n');
  files.push({ name: `${layout.root}/00 checklist.csv`, bytes: enc('﻿' + csv) });
  return { zip: await zipOf(files), layout, readiness: readiness(d, board, findings, needs) };
}
