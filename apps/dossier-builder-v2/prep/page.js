// The page of «الفحص الأول للملف» (Part 2): the viewer's files read in the browser (prep/read.js), each document typed and placed, the
// documents checked side by side (prep/index.js), every finding shown with the words on its pages. Scanned pages are read by Claude
// on the viewer's claude.ai account where the page may ask it (prep/claude-read.js, the `sample` capability with images), else — or
// when the viewer chooses, or Claude refuses or cannot answer — by the scan reader on the computer (prep/ocr.js).
// pdf.js's legacy build: the Claude apps show pages in the phone's own web view.
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs';
import { readFiles, whyOf, FIRST } from './read.js';
import { prepare } from './index.js';
import { createOcr } from './ocr.js';
import { createClaudeReader } from './claude-read.js';
import { extract as unrarInWorker } from './rar.js';

pdfjs.GlobalWorkerOptions.workerSrc = 'pdf.worker.min.js';
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const PLACES = JSON.parse($('#places').textContent);
const knowledge = { record: id => PLACES[id] || null };
const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
const KIND = { pdf: 'PDF', doc: 'Word قديم', docx: 'Word', png: 'صورة', jpeg: 'صورة', tiff: 'صورة TIFF', gif: 'صورة', webp: 'صورة', text: 'نص',
               xls: 'Excel قديم', xlsx: 'Excel', ppt: 'PowerPoint قديم', pptx: 'PowerPoint', '7z': '7z', zip: 'ZIP', rar: 'RAR', heic: 'صورة HEIC', unknown: 'مش معروف' };
const FIELD = { product_name: 'المستحضر', dosage_form: 'الشكل الصيدلي', manufacturer: 'المصنع', license_holder: 'صاحب الترخيص', applicant: 'مقدم الطلب',
                document_code: 'كود المستند', issue_date: 'تاريخ الإصدار', review_date: 'تاريخ المراجعة', invalidation_date: 'تاريخ الانتهاء',
                registration_number: 'رقم التسجيل', composition: 'التركيب', approved_limit: 'حد اتوافق عليه', decision: 'القرار', transfer_fee: 'رسوم نقل تصنيع إلى',
                transfer_approval: 'موافقة نقل تصنيع إلى', condition: 'شرط', issuer: 'الشركة اللي كاتبة المستند' };

// ---- the status line and the bar
let started = 0, ticker = null;
function status(text, kind = '') {
  const el = $('#status');
  el.hidden = false;
  el.className = `status ${kind}`;
  el.innerHTML = text;
}
function bar(part) {
  $('#bar').hidden = part == null;
  if (part != null) $('#bar-fill').style.width = `${Math.round(Math.min(1, Math.max(0, part)) * 100)}%`;
}

// ---- what the page gives the reader: the scan reader, pages drawn at 300 dpi, pictures, RAR in a worker
const ocr = createOcr({ base: 'ocr/', onLoad: e => { if (e.part !== 'ready') status(`بيحمّل قارئ المسح… <span class="fine">(أول مرة حوالي 35 م.ب، وبعدها بيبقى أسرع)</span>`); } });
function canvasOf(w, h) { const c = document.createElement('canvas'); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h)); return c; }
// A scanned page drawn with its long side 4,200 pixels — an A4 page at about 360 dpi — whatever size its PDF claims (a phone's scanner
// app writes pages of 28 × 42 inches): Tesseract is told that resolution when the page has the shape of an A4 or Letter sheet, and
// estimates it otherwise (a resolution read from such a PDF misled it into skipping a letter's heading). On real licences and
// letters, 360 dpi kept lines that 300 lost (an ingredient's line, a decision's limit) in about the same time.
const LONG_SIDE = 4200, LONG_DPI = Math.round(300 * 4200 / 3508);
async function drawPdf(page) {
  const v1 = page.getViewport({ scale: 1 }), k = LONG_SIDE / Math.max(1, v1.width, v1.height);
  const vp = page.getViewport({ scale: k }), c = canvasOf(vp.width, vp.height), g = c.getContext('2d');
  g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height);
  await page.render({ canvasContext: g, viewport: vp, canvas: c }).promise;
  const shape = Math.max(v1.width, v1.height) / Math.max(1, Math.min(v1.width, v1.height));
  c.dpi = Math.abs(shape - 1.414) < 0.08 || Math.abs(shape - 1.294) < 0.06 ? LONG_DPI : 0;
  return c;
}
async function drawImage(bytes, kind) {
  if (kind === 'tiff') throw Object.assign(new Error('TIFF'), { why: 'kind' });
  const bmp = await createImageBitmap(new Blob([bytes]));
  const L = Math.max(bmp.width, bmp.height), k = L < 2000 ? Math.min(3, 2000 / L) : L > 4200 ? 4200 / L : 1;
  const c = canvasOf(bmp.width * k, bmp.height * k), g = c.getContext('2d');
  g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height); g.imageSmoothingQuality = 'high'; g.drawImage(bmp, 0, 0, c.width, c.height);
  return [c];
}
async function unrar(bytes) {
  const r = await unrarInWorker([new Blob([bytes])], {});
  const join = parts => { const all = new Uint8Array(parts.reduce((n, p) => n + p.byteLength, 0)); let at = 0; for (const p of parts) { all.set(new Uint8Array(p), at); at += p.byteLength; } return all; };
  return { files: r.files.map(f => ({ name: f.name, bytes: join(f.parts) })), skipped: r.skipped };
}

// ---- who reads the scanned pages: Claude where this view lets the page ask it with pictures, else the scan reader
let claude = { state: 'checking' };
const WHY_CLAUDE = {
  not_granted: 'الصفحة مش مسموح لها تكلّم Claude (تقدر تسمح من قايمة الأذونات بتاعة الصفحة)', sampling_disabled: 'Claude مش متاح على الحساب ده',
  images_unavailable: 'العرض ده مش بيبعت صور لـ Claude', rate_limited: 'حد الاستخدام في اشتراكك خلص مؤقتاً', session_expired: 'جلستك على claude.ai خلصت',
  upstream_error: 'Claude مارجّعش رد', empty_completion: 'Claude مارجّعش رد',
};
const STOP = new Set(['not_granted', 'sampling_disabled', 'images_unavailable', 'session_expired', 'rate_limited']);   // no use asking again this time
function showReader() {
  const ready = claude.state === 'ready';
  $('#reader').hidden = !ready;
  $('#reader-note').textContent = ready ? '' : claude.state === 'checking' ? ''
    : 'Claude مش متاح في العرض ده، فالصفحات الممسوحة هيقراها قارئ المسح على الجهاز.';
}
(async () => {
  try {
    const sample = window.claude ? await window.claude.use('sample') : null;          // null: this view cannot ask Claude
    const caps = sample ? await sample.limits().catch(() => null) : null;
    claude = sample && (caps?.images?.maxCount || 0) >= 2 ? { state: 'ready', reader: createClaudeReader(sample) } : { state: sample ? 'no-images' : 'none' };
  } catch { claude = { state: 'none' }; }
  showReader();
})();
const chosenReader = () => (claude.state === 'ready' && document.querySelector('input[name="reader"]:checked')?.value === 'claude' ? 'claude' : 'ocr');
// Claude first, page by page; a page Claude cannot read goes to the scan reader, and after a refusal or a spent limit every page does
function readerFor(choice) {
  if (choice !== 'claude') return ocr;
  const state = { off: null, failed: 0 };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  return {
    lanes: 2, state,
    async page(canvas, info) {
      for (let attempt = 0; !state.off && attempt < 2; attempt++) {
        try { return await claude.reader.page(canvas, info); } catch (e) {
          const code = e?.code || 'error';
          if (code === 'rate_limited' && attempt === 0) { await sleep(window.__prepRateWait ?? 20000); continue; }   // a limit may come back soon
          if (STOP.has(code)) state.off = code;
        }
      }
      state.failed++;
      const got = await ocr.page(canvas, info);
      return { text: typeof got === 'string' ? got : got.text, by: 'ocr' };
    },
  };
}

// ---- the files chosen, dropped (folders too), read and checked
async function entriesOf(items) {                                  // dropped files and folders → [{name, file}]
  const out = [];
  const walk = async (entry, at) => {
    if (entry.isFile) { const file = await new Promise((ok, no) => entry.file(ok, no)); out.push({ name: at + file.name, file }); return; }
    const reader = entry.createReader();
    for (;;) {
      const batch = await new Promise((ok, no) => reader.readEntries(ok, no));
      if (!batch.length) break;
      for (const e of batch) await walk(e, `${at}${entry.name}/`);
    }
  };
  for (const it of items) { const e = it.webkitGetAsEntry?.(); if (e) await walk(e, ''); else if (it.getAsFile?.()) out.push({ name: it.getAsFile().name, file: it.getAsFile() }); }
  return out;
}
const SKIP = /(^|\/)(\.|__MACOSX\/|Thumbs\.db$|desktop\.ini$)/i;
async function run(chosen) {
  chosen = chosen.filter(c => !SKIP.test(c.name));
  if (!chosen.length) return;
  $('#summary-box').hidden = $('#findings-box').hidden = $('#docs-box').hidden = true;
  started = Date.now();
  let last = '';
  clearInterval(ticker);
  ticker = setInterval(() => { if (last) status(`${last} <span class="fine">· ${Math.round((Date.now() - started) / 1000)} ث</span>`); }, 1000);
  try {
    const files = [];
    for (const c of chosen) files.push({ name: c.name, bytes: new Uint8Array(await c.file.arrayBuffer()) });
    let opened = 0;
    window.__prepLog = [];
    const choice = chosenReader(), reader = readerFor(choice);
    const env = { pdfjs, ocr: reader, drawPdf, drawImage, unrar, onProgress: e => {
      window.__prepLog.push({ t: Date.now() - started, ...e });
      if (e.stage === 'open') { opened++; last = `بيفتح <bdi>${esc(e.name)}</bdi>…`; bar(Math.min(0.95, opened / (files.length + 4))); }
      if (e.stage === 'ocr') last = `${choice === 'claude' && !reader.state?.off ? 'Claude بيقرا' : 'قارئ المسح بيقرا'} الصفحة الممسوحة ${e.page} من ${e.pages} في <bdi>${esc(e.name)}</bdi>…`;
      status(`${last} <span class="fine">· ${Math.round((Date.now() - started) / 1000)} ث</span>`);
    } };
    status('بيفتح الملفات…'); bar(0.02);
    const docs = await readFiles(files, env);
    const result = prepare(docs, { today: today(), knowledge });
    clearInterval(ticker);
    bar(null);
    show(docs, result, env.ocrFailed, { choice, off: reader.state?.off || null, failed: reader.state?.failed || 0 });
  } catch (e) {
    clearInterval(ticker);
    bar(null);
    status(`حصلت مشكلة وماقدرتش أكمّل: <bdi>${esc(e.message || e)}</bdi>`, 'bad');
  }
}

// ---- the result
function pagesLine(d) {
  if (d.unread) return `<span class="badge bad">ماتقراش: ${esc(whyOf(d.unread))}</span>`;
  const n = d.pages.length, read = d.pages.filter(p => (p.text || '').trim()).length;
  const byClaude = d.pages.filter(p => p.by === 'claude').length, byOcr = d.pages.filter(p => p.by === 'ocr').length;
  let s = `${read} من ${n} ${n === 1 ? 'صفحة' : 'صفحات'} اتقرت`;
  const how = [byClaude ? `${byClaude} ممسوحة قراها Claude` : '', byOcr ? `${byOcr} ممسوحة قراها قارئ المسح` : ''].filter(Boolean).join('، ');
  if (how) s += ` <span class="fine">(${how})</span>`;
  if (d.note) s += ` <span class="badge warn">${d.note === 'no-ocr' ? 'ممسوح ومااتقراش'
    : d.note.startsWith('long:') ? `مستند طويل: اتقرا أول ${FIRST} صفحات ممسوحة بس، و${d.note.split(':')[1]} مااتقرتش`
      : `فيه ${d.note.split(':')[1]} صفحات ممسوحة مااتقرتش`}</span>`;
  return s;
}
function evidence(e) {
  return `<li><div class="where"><bdi>${esc(e.name)}</bdi> — ص ${e.page}</div><blockquote dir="auto">${esc(e.quote)}</blockquote></li>`;
}
function show(docs, { documents, findings }, ocrFailed, how = {}) {
  const reds = findings.filter(f => f.level === 'red').length, ambers = findings.length - reds;
  const scanned = docs.reduce((n, d) => n + d.pages.filter(p => p.by === 'ocr' || p.by === 'claude').length, 0);
  const unread = docs.filter(d => d.unread || d.note).length;
  const secs = Math.round((Date.now() - started) / 1000);
  const notes = [];
  if (how.choice === 'claude' && how.off) notes.push(`Claude وقف (${esc(WHY_CLAUDE[how.off] || how.off)})، والصفحات الممسوحة الباقية قراها قارئ المسح على الجهاز`);
  else if (how.choice === 'claude' && how.failed) notes.push(`${how.failed} ${how.failed === 1 ? 'صفحة' : 'صفحات'} ممسوحة Claude ماقدرش يقراها، فقراها قارئ المسح على الجهاز`);
  if (ocrFailed) notes.push(`قارئ المسح ماقدرش يشتغل هنا (${esc(ocrFailed.why === 'wasm' ? 'العرض ده مانع WebAssembly اللي القارئ محتاجه' : ocrFailed.message)}): الصفحات الممسوحة اللي وصلت له مااتقرتش`);
  status(`خلص في ${secs} ث.${notes.length ? ' ' + notes.join('. ') + '.' : ''}`, ocrFailed || how.off || how.failed ? 'warn' : 'ok');
  $('#summary-when').textContent = `النهارده ${today()}`;
  $('#summary').innerHTML = [
    [documents.length, 'مستندات'], [reds, 'ملاحظات لازم تتحل', 'bad'], [ambers, 'ملاحظات لازم تتوضح', 'warn'],
    [scanned, 'صفحات ممسوحة اتقرت'], [unread, 'مستندات مااتقرتش كلها', unread ? 'warn' : ''],
  ].map(([n, t, k]) => `<div class="tile ${k || ''}"><b>${n}</b><span>${t}</span></div>`).join('');
  $('#findings').innerHTML = findings.map(f => `<li class="finding ${f.level}">
      <div class="lvl">${f.level === 'red' ? 'لازم تتحل' : 'لازم تتوضح'}</div>
      <h3>${esc(f.title)}</h3>
      <p class="detail">${esc(f.detail)}</p>
      <details${f.level === 'red' ? ' open' : ''}><summary>الكلام اللي في الصفحات (${f.evidence.length})</summary><ul class="evidence">${f.evidence.map(evidence).join('')}</ul></details>
    </li>`).join('');
  $('#findings-empty').hidden = findings.length > 0;
  $('#docs').innerHTML = documents.map((d, i) => {
    const raw = docs[i];
    const place = d.places.length ? d.places.map(p => `<span class="ctd">${esc(p.ctd || p.id)}</span> ${esc(p.title?.ar || p.title?.en || '')}`).join('<br>') : '<span class="fine">مكانه مش محدد</span>';
    const facts = d.facts.map(f => `<li><span class="f">${esc(FIELD[f.field] || f.field)}</span> <span class="v" dir="auto">${esc(f.value)}</span> <span class="fine">ص ${f.page}</span></li>`).join('');
    return `<li class="doc">
      <div class="doc-head"><bdi class="name">${esc(d.name)}</bdi><span class="kind">${esc(KIND[raw.kind] || raw.kind)}</span></div>
      <div class="doc-grid">
        <div><span class="label">نوعه</span>${esc(d.type_ar)}</div>
        <div><span class="label">مكانه في الـ CTD</span>${place}</div>
        <div><span class="label">القراية</span>${pagesLine(raw)}</div>
      </div>
      ${d.facts.length ? `<details><summary>اللي اتقرا منه (${d.facts.length})</summary><ul class="facts">${facts}</ul></details>` : ''}
    </li>`;
  }).join('');
  $('#summary-box').hidden = $('#findings-box').hidden = $('#docs-box').hidden = false;
  window.__prep = { documents, findings, docs: docs.map(d => ({ id: d.id, name: d.name, kind: d.kind, unread: d.unread || null, note: d.note || null,
                                                               pages: d.pages.map(p => ({ n: p.n, by: p.by, text: p.text })) })), ocrFailed: ocrFailed ? ocrFailed.why || ocrFailed.message : null,
                  reader: how };
}

// ---- wiring
for (const id of ['#pick-files', '#pick-folder']) {
  $(id).addEventListener('change', e => { const list = [...e.target.files].map(f => ({ name: f.webkitRelativePath || f.name, file: f })); e.target.value = ''; run(list); });
}
const drop = $('#drop');
drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('over'); });
drop.addEventListener('dragleave', () => drop.classList.remove('over'));
drop.addEventListener('drop', async e => { e.preventDefault(); drop.classList.remove('over'); run(await entriesOf([...e.dataTransfer.items])); });
window.__prepRun = list => run(list.map(f => ({ name: f.name, file: new Blob([f.bytes]) })));   // for the tests: the same run as a choice of files
