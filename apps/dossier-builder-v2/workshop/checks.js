// The checks (Part 2, step 2.5): each document against its rule card — as a file (PDF, searchable, its version, no protection, its
// size, its fonts, an outline where it has a table of contents), as a paper (still valid by its dates and its type's validity) —
// the documents against each other (prep/checks.js: the manufacturer, the approved limits, the forms of a substance, the dates, the
// licence's conditions), and the board (every required place filled). Each finding names its rule and the source that says it,
// and what can be done about it: fixed by the program, or a person's step.
import { check as crossCheck } from '../prep/checks.js';
import { fold } from '../core/fold.js';
import { FORMAT, DOCTYPE_OF } from './board.js';
import { pdfInfo } from './pdfops.js';

const fmt = id => FORMAT.find(f => f.id === id);
const ltr = s => `⁦${s}⁩`;
const letters = s => (String(s || '').match(/[\p{L}\p{N}]/gu) || []).length;
const TOC = /table of contents|^\s*contents\s*$|^\s*(ال)?فهرس(\s|$)|^\s*(ال)?محتويات(\s|$)/m;
const WORD_OK = new Set(['EG-EDA/M1-09']);           // the proposed leaflet is handed in as Word
const MB = 1024 * 1024;
// The 14 fonts every PDF reader has (PDF 1.7 §9.6.2.2): a PDF may name them without carrying them.
const BASE14 = /^(helvetica|times|courier|symbol|zapfdingbats|arial|timesnewroman|couriernew)([-,].*)?$/i;

const addMonths = (iso, m) => { const d = new Date(`${iso}T00:00:00Z`); d.setUTCMonth(d.getUTCMonth() + m); return d.toISOString().slice(0, 10); };
const daysBetween = (a, b) => Math.round((new Date(`${b}T00:00:00Z`) - new Date(`${a}T00:00:00Z`)) / 86400000);

// The PDF facts of a document, worked out once for each version of it.
export async function infoOf(d, doc, getBlob) {
  if (doc.kind !== 'pdf') return null;
  if (doc.info?.sha === (doc.fixed || doc.sha)) return doc.info;
  const bytes = await getBlob(d.id, doc.fixed || doc.sha);
  if (!bytes) return null;
  doc.info = { sha: doc.fixed || doc.sha, ...(await pdfInfo(bytes)) };
  return doc.info;
}

function formatFindings(doc, info) {
  const out = [];
  const add = (id, level, title, detail, rule, fix) => out.push({ id: `${id}-${doc.id}`, kind: 'format', level, doc: doc.id, place: doc.place, title, detail,
                                                                rule: { ar: rule.ar, cite: rule.cite }, fix });
  if (doc.kind !== 'pdf') {
    if (['doc', 'docx'].includes(doc.kind) && WORD_OK.has(doc.place)) return out;
    if (['doc', 'docx'].includes(doc.kind)) add('not-pdf', 'amber', `«${doc.name}» ملف Word، والملف لازم يبقى PDF`, 'المستند ده لازم يتقدّم PDF. افتحه في برنامج الـ Word واحفظه PDF، أو ارفع نسخته الـ PDF.', fmt('pdf'), { human: ['program', 'upload', 'accept'] });
    else if (['png', 'jpeg', 'tiff', 'gif', 'webp'].includes(doc.kind)) add('not-pdf', 'amber', `«${doc.name}» صورة، والملف لازم يبقى PDF`, 'البرنامج يقدر يحوّل الصورة لصفحة PDF.', fmt('pdf'), { auto: 'picture', human: ['upload', 'accept'] });
    return out;
  }
  if (!info) return out;
  if (info.damaged) { add('damaged', 'red', `«${doc.name}» ماقدرش يتفتح كـ PDF سليم`, `السبب: ${info.damaged}`, fmt('pdf'), { human: ['upload', 'program'] }); return out; }
  if (info.encrypted) add('encrypted', 'red', `«${doc.name}» عليه حماية`, 'الهيئة مابتقبلش ملف عليه كلمة سر أو حماية. محتاج نسخة من غير حماية من اللي أصدره، أو تشيلها في برنامج الـ PDF لو معاك الإذن.', fmt('open'), { human: ['program', 'upload'] });
  const v = Number(info.version || 0);
  if (v && v < 1.4) add('version', 'amber', `«${doc.name}» نسخة PDF قديمة (${ltr(info.version)})`, 'البرنامج يحفظه من جديد بنسخة 1.7 من غير ما يغيّر أي صفحة.', fmt('version'), { auto: 'version', human: ['accept'] });
  if (doc.size > 100 * MB) add('size', 'red', `«${doc.name}» حجمه ${ltr((doc.size / MB).toFixed(0) + ' MB')}`, 'أكبر من 100 ميجا: لازم يتقسم لأكتر من ملف.', fmt('size'), { human: ['program', 'upload'] });
  const blank = doc.pages.filter(p => p.by === 'text' && letters(p.text) < 40).length;
  const scanned = doc.pages.filter(p => p.by === 'ocr' || p.by === 'claude').length;
  if (scanned || blank === doc.pages.length) {
    add('no-text', 'amber', `«${doc.name}» ممسوح ومافيهوش نص يتبحث فيه`, `${scanned || blank} ${scanned || blank === 1 ? 'صفحة' : 'صفحات'} من غير طبقة نص. البرنامج قراها${scanned ? '' : ' (أو حاول)'}، لكن الملف نفسه لازم يتعمله OCR قبل التقديم: افتحه في برنامج الـ PDF واعمله طبقة نص.`,
        fmt('pdf'), { human: ['program', 'upload', 'accept'] });
  }
  const missingFonts = (info.fonts?.missing || []).filter(n => !BASE14.test(n.replace(/\s+/g, '')));
  if (missingFonts.length && !scanned) add('fonts', 'amber', `«${doc.name}» فيه خطوط مش جوه الملف`, `الخطوط: ${missingFonts.slice(0, 6).join('، ')}. الإرشاد بيقول «على قد ما يمكن»: لو المستند بتاع الشركة اعمله PDF تاني والخطوط جواه.`, fmt('fonts'), { human: ['program', 'accept'] });
  const head = fold(doc.pages.slice(0, 3).map(p => p.text || '').join('\n'));
  if (TOC.test(head) && !info.outline && doc.pages.length > 2) add('outline', 'amber', `«${doc.name}» فيه فهرس ومالوش bookmarks`, 'البرنامج يقدر يعمله bookmarks من سطور الفهرس اللي فيها رقم صفحة.', fmt('bookmarks'), { auto: 'outline', human: ['program', 'accept'] });
  return out;
}

// Still valid? From the dates read on it, or from its issue date and its type's validity in the library.
function validityFindings(doc, knowledge, today) {
  const out = [];
  const dtId = DOCTYPE_OF[doc.place];
  const dt = dtId ? knowledge.doctypes.items.find(x => x.id === `EG-EDA/doc/${dtId}`) : null;
  const end = doc.facts?.find(f => f.field === 'invalidation_date');
  const issued = doc.facts?.find(f => f.field === 'issue_date');
  const cite = dt?.cite || [];
  let until = end?.value || null, from = 'end';
  if (!until && issued && dt?.validity_months) { until = addMonths(issued.value, dt.validity_months); from = 'issue'; }
  if (!until) return out;
  const left = daysBetween(today, until), warn = dt?.warn_days ?? knowledge.doctypes.warn_days_default ?? 90;
  const evidence = [end || issued].map(f => ({ doc: doc.id, name: doc.name, page: f.page, quote: f.quote }));
  const how = from === 'end' ? `تاريخ الانتهاء المكتوب عليه ${ltr(until)}` : `صدر ${ltr(issued.value)}، وصلاحية النوع ده ${dt.validity_months} شهر، يعني لحد ${ltr(until)}`;
  if (left < 0) out.push({ id: `expired-${doc.id}`, kind: 'content', level: 'red', doc: doc.id, place: doc.place, title: `«${doc.name}» صلاحيته خلصت`,
                           detail: `${how}، والنهارده ${ltr(today)}. هات النسخة الجديدة من اللي أصدره.`, evidence, rule: { ar: 'المستند لازم يكون ساري وقت التقديم', cite }, fix: { human: ['upload', 'accept'] } });
  else if (left <= warn) out.push({ id: `expiring-${doc.id}`, kind: 'content', level: 'amber', doc: doc.id, place: doc.place, title: `«${doc.name}» صلاحيته هتخلص بعد ${left} يوم`,
                                    detail: `${how}. ابدأ في تجديده من دلوقتي.`, evidence, rule: { ar: `نبّه قبل ${warn} يوم من الانتهاء`, cite }, fix: { human: ['upload', 'accept'] } });
  return out;
}

// The board: a required place with nothing in it.
function boardFindings(d, board, generators) {
  const out = [];
  const filled = new Set(d.docs.filter(x => !x.dup && !x.split && x.place).map(x => x.place));
  for (const p of board.places) {
    if (p.level !== 'R' || filled.has(p.id)) continue;
    const gen = generators[p.id];
    out.push({ id: `missing-${p.id}`, kind: 'missing', level: gen ? 'amber' : 'red', place: p.id, title: `${p.ctd} ${p.title.ar}: مفيش مستند`,
               detail: gen ? 'البرنامج يقدر يعمله مسودة Word من معلومات الملف، وانت تراجعها وتطبعها على ورق الشركة وتمضيها.' : 'المكان ده مطلوب للمنتج ده. ارفع المستند، أو اكتب سبب إنه مش مطلوب.',
               rule: { ar: `مطلوب (${board.column}) في جدول NP.CAPP.065`, cite: [{ src: 'eda-np-capp-065-v5' }] },
               fix: gen ? { auto: 'create', human: ['upload', 'accept'] } : { human: ['upload', 'accept'] } });
  }
  return out;
}

// All the findings of a dossier (worked out again whenever it changes). env: {knowledge, getBlob, today, generators: {placeId: name}}
export async function checkDossier(d, board, env) {
  const today = env.today || new Date().toISOString().slice(0, 10);
  const docs = d.docs.filter(x => !x.dup && !x.split);
  const out = [];
  for (const doc of docs) {
    if (doc.unread) {
      out.push({ id: `unread-${doc.id}`, kind: 'format', level: 'red', doc: doc.id, title: `«${doc.name}» ماتقراش`, detail: doc.whyUnread || doc.unread,
                 rule: { ar: 'كل مستند لازم يتفتح ويتقري', cite: [] }, fix: { human: ['upload', 'accept'] } });
      continue;
    }
    out.push(...formatFindings(doc, await infoOf(d, doc, env.getBlob)));
    out.push(...validityFindings(doc, env.knowledge, today));
  }
  const read = docs.filter(x => x.pages?.length).map(x => ({ id: x.id, name: x.name, type: x.type, facts: x.facts || [], pages: x.pages.length,
                                                            text: x.pages.map(p => p.text || '').join('\n'), pageTexts: x.pages.map(p => ({ n: p.n, text: p.text || '' })) }));
  out.push(...crossCheck(read, { today }).map(f => ({ ...f, kind: 'cross', id: `cross-${f.id}`, doc: f.evidence?.[0]?.doc,
                                                      rule: { ar: 'المستندات لازم تقول نفس الكلام', cite: [] }, fix: { human: ['upload', 'claude', 'accept'] } })));
  out.push(...boardFindings(d, board, env.generators || {}));
  // the viewer's own decisions: a finding accepted with a reason stays, marked so
  for (const f of out) if (d.decisions?.[f.id]) f.accepted = d.decisions[f.id];
  const rank = f => (f.accepted ? 2 : f.level === 'red' ? 0 : 1);
  return out.sort((a, b) => rank(a) - rank(b));
}

// The status of a place on the board: empty, red, amber or green.
export function placeStatus(placeId, d, findings) {
  const docs = d.docs.filter(x => x.place === placeId && !x.dup && !x.split);
  const fs = findings.filter(f => !f.accepted && (f.place === placeId || docs.some(x => x.id === f.doc)));
  if (fs.some(f => f.level === 'red')) return docs.length ? 'red' : 'empty';
  if (fs.some(f => f.level === 'amber')) return 'amber';
  return docs.length ? 'green' : 'empty';
}
