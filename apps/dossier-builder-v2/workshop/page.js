// «تحضير الملف» — the workshop of Part 2 (docs/PART-2-PLAN.md §3.3), the page: a new dossier for a country and a product's case;
// the files received, read, cut, typed, named and placed on the board; each document checked on its rule card and against the
// others; the fixes the program makes by itself and the company papers it writes; «needs you» with its four actions; the ready
// folder with its readiness report; and Claude, through the person's own API key, where they give one: reading scans, placing what
// the rules cannot, and «اسأل Claude» with the workshop's tools. Everything stays on this computer (the browser's own database)
// except what goes to Claude, and only when the person has given a key.
// pdf.js runs on the page's own thread: a page opened from the disk cannot start a worker from a file.
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs';
import * as pdfjsWorker from 'pdfjs-dist/legacy/build/pdf.worker.mjs';
import { createKnowledge } from '../core/knowledge.js';
import { createOcr } from '../prep/ocr.js';
import { createClaudeReader } from '../prep/claude-read.js';
import { extract as unrarInWorker } from '../prep/rar.js';
import { readFiles, whyOf } from '../prep/read.js';
import { desktopAssets } from './desktop-assets.js';
import { boardOf, ruleCard, COUNTRIES, QUESTIONS, PARTY } from './board.js';
import { newDossier, addFiles, understand, moveDoc, log, partyFor } from './pipeline.js';
import { checkDossier, placeStatus } from './checks.js';
import { fixAll, writeDrafts } from './fixes.js';
import { needsOf, accept, actionName, count } from './needs.js';
import { readyZip, layoutOf, reportHtml, readiness } from './export.js';
import { GENERATORS, COMPANY_FIELDS, dataOf, draftFor } from './generators.js';
import { docxOf, htmlOf, gapsOf } from './docx.js';
import { connect, sampleOf, converse, WHY as CLAUDE_WHY, STOP as CLAUDE_STOP } from './claude.js';
import { workshopTools, ASK_SYSTEM } from './tools.js';
import * as store from './store.js';
import { createPrograms, programFor, available, PROGRAMS } from './programs.js';
import { docxText } from '../prep/office.js';
import { fold } from '../core/fold.js';

globalThis.pdfjsWorker = pdfjsWorker;
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const KNOW = globalThis.DB_KNOWLEDGE;
const knowledge = createKnowledge(KNOW);
const today = () => new Date().toISOString().slice(0, 10);
const KIND = { pdf: 'PDF', doc: 'Word قديم', docx: 'Word', png: 'صورة', jpeg: 'صورة', tiff: 'TIFF', gif: 'صورة', webp: 'صورة', text: 'نص', xls: 'Excel قديم',
               xlsx: 'Excel', ppt: 'PowerPoint قديم', pptx: 'PowerPoint', '7z': '7z', zip: 'ZIP', rar: 'RAR', heic: 'HEIC', unknown: 'مش معروف' };
const BY = { text: 'نص الملف', ocr: 'قارئ المسح', claude: 'Claude', word: 'Word', plain: 'نص', program: 'البرنامج' };
const FIELD = { product_name: 'المستحضر', trade_name: 'المستحضر', dosage_form: 'الشكل الصيدلي', manufacturer: 'المصنع', license_holder: 'صاحب الترخيص',
                applicant: 'مقدم الطلب', document_code: 'كود المستند', issue_date: 'تاريخ الإصدار', review_date: 'تاريخ المراجعة',
                invalidation_date: 'تاريخ الانتهاء', registration_number: 'رقم التسجيل', composition: 'التركيب', approved_limit: 'حد اتوافق عليه',
                decision: 'القرار', transfer_fee: 'رسوم نقل تصنيع', transfer_approval: 'موافقة نقل تصنيع', condition: 'شرط', issuer: 'الجهة اللي كاتبة المستند' };
const STAGES = [['new', 'ملف جديد'], ['receive', 'الاستلام والفتح'], ['read', 'القراءة والفهم'], ['place', 'التقطيع والتسكين'], ['check', 'الفحص'],
                ['fix', 'التصليح والإنشاء'], ['needs', 'محتاج منك'], ['ready', 'الملف الجاهز']];
const GEN_NAMES = Object.fromEntries(Object.entries(GENERATORS).map(([k, v]) => [k, v.name]));

// ------------------------------------------------------------------------------------------------ state
const state = {
  view: 'home', tab: 'board', d: null, board: null, findings: [], needs: [], drafts: {}, drawer: null, showAll: false,
  running: null, wizard: null, list: [], ask: { history: [], steps: [], text: '', busy: false },
  claude: { key: '', client: null, models: [], model: '', reader: 'claude', status: 'none', error: '' },
};
const local = { get(k, d) { try { return localStorage.getItem(`dbw.${k}`) ?? d; } catch { return d; } },
                set(k, v) { try { if (v === null) localStorage.removeItem(`dbw.${k}`); else localStorage.setItem(`dbw.${k}`, v); } catch { /* the page works without it */ } } };
state.claude.reader = local.get('reader', 'claude');
state.claude.model = local.get('model', '');

function toast(text, ms = 3500) {
  const el = $('#toast');
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toast.t);
  toast.t = setTimeout(() => { el.hidden = true; }, ms);
}
function download(name, bytes, type = 'application/octet-stream') {
  const url = URL.createObjectURL(new Blob([bytes], { type }));
  const a = Object.assign(document.createElement('a'), { href: url, download: name });
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
const TYPES = { pdf: 'application/pdf', docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', doc: 'application/msword', png: 'image/png', jpeg: 'image/jpeg' };

// ------------------------------------------------------------------------------------------------ reading: pages drawn, the scan reader, Claude
function canvasOf(w, h) { const c = document.createElement('canvas'); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h)); return c; }
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
const ocr = createOcr({ assets: desktopAssets('app/ocr/'), onLoad: e => { if (e.part !== 'ready' && state.running) say(`بيحمّل قارئ المسح… (أول مرة بس)`); } });
const claudeOn = () => state.claude.status === 'ready' && state.claude.client && state.claude.model;
const sample = () => (claudeOn() ? sampleOf(state.claude.client, state.claude.model) : null);

function readerFor() {
  if (!(claudeOn() && state.claude.reader === 'claude')) return { reader: ocr, how: { choice: 'ocr' } };
  const claude = createClaudeReader(sample());
  const how = { choice: 'claude', off: null, failed: 0 };
  return { how, reader: {
    lanes: 2,
    async page(canvas, info) {
      for (let attempt = 0; !how.off && attempt < 2; attempt++) {
        try { return await claude.page(canvas, info); } catch (e) {
          if (e?.code === 'rate_limited' && attempt === 0) { await new Promise(r => setTimeout(r, globalThis.__workshopRateWait ?? 20000)); continue; }
          if (CLAUDE_STOP.has(e?.code) || e?.code === 'rate_limited') how.off = e.code;
        }
      }
      how.failed++;
      const got = await ocr.page(canvas, info);
      return { text: typeof got === 'string' ? got : got.text, by: 'ocr' };
    } } };
}

// ------------------------------------------------------------------------------------------------ the real programs
const programs = createPrograms({ base: 'programs/', mount: iframe => { iframe.hidden = true; $('#program-frames').appendChild(iframe); } });
function showProgram(app, title, note) {
  for (const f of document.querySelectorAll('#program-frames iframe')) f.hidden = true;
  programs.frame(app).hidden = false;
  $('#program-title').textContent = title;
  $('#program-note').textContent = note;
  $('#program').hidden = false;
}
function hideProgram() { $('#program').hidden = true; state.programDoc = null; }
async function openInProgram(docId) {
  const d = state.d, doc = d.docs.find(x => x.id === docId);
  if (!doc) return;
  const kind = doc.madeBy === 'program' ? 'docx' : doc.kind;
  const app = programFor(kind);
  if (!app || !available(app)) { await openDocFile(docId); toast('اتفتح (أو اتنزّل). عدّله في برنامجه على جهازك واحفظه، وبعدين «ارفع نسخة جديدة».', 7000); return; }
  const bytes = doc.madeBy === 'program' && !doc.editedBy ? await docxOf(draftFor(doc.place, d).model) : await store.getBlob(d.id, doc.fixed || doc.sha);
  const name = (doc.madeBy === 'program' ? doc.name : doc.name.split('/').pop()).replace(/[\\/:*?"<>|]/g, ' ');
  state.programDoc = { app, docId };
  showProgram(app, `${PROGRAMS[app].ar} — ${name}`, 'عدّل واحفظ من جوه البرنامج (Ctrl+S): كل حفظة بترجع للملف هنا كنسخة جديدة.');
  try { await programs.open(app, name, bytes); } catch (e) { toast(`${PROGRAMS[app].ar} ماقدرش يفتح: ${e.message}`, 9000); hideProgram(); }
}
// A file the program saved: a new version of the document it was given (a PDF the Word program exported is that Word file's PDF).
programs.onMessage(async m => {
  if (m.type !== `${m.app}:save` || !state.programDoc || state.programDoc.app !== m.app || state.converting) return;
  const bytes = new Uint8Array(m.bytes), docId = state.programDoc.docId;
  try {
    if (m.app === 'wordcraft' && /\.pdf$/i.test(m.name || '')) await keepPdfOf(docId, bytes);
    else await newVersion(docId, bytes, m.name, 'program');
    toast(`اتحفظ في الملف: ${m.name}`);
  } catch (e) { toast(`ماقدرتش أحفظ: ${e.message}`, 7000); }
});
async function keepPdfOf(docId, bytes) {
  const d = state.d, doc = d.docs.find(x => x.id === docId);
  const sha = await store.sha256(bytes);
  await store.putBlob(d.id, sha, bytes);
  doc.pdf = sha;
  log(d, 'pdf-made', { doc: docId });
  await changed();
}
async function wordToPdf(docId) {
  const d = state.d, doc = d.docs.find(x => x.id === docId);
  if (!available('wordcraft')) { toast('برنامج الـ Word مش موجود في النسخة دي.'); return; }
  const bytes = doc.madeBy === 'program' && !doc.editedBy ? await docxOf(draftFor(doc.place, d).model) : await store.getBlob(d.id, doc.fixed || doc.sha);
  const first = (doc.pages || []).map(p => p.text || '').join('\n').split('\n').map(l => l.trim()).find(l => l.length > 3) || '';
  state.converting = true;
  showProgram('wordcraft', `${PROGRAMS.wordcraft.ar} — بيعمل PDF`, `«${doc.name}» بيتحوّل PDF؛ استنى ثواني.`);
  try { await keepPdfOf(docId, await programs.wordToPdf(doc.name.split('/').pop(), bytes, first)); toast('اتعمل PDF من المستند، وهيتحط في الفولدر بداله.'); }
  catch (e) { toast(`ماقدرش يعمل PDF: ${e.message}`, 9000); }
  finally { state.converting = false; hideProgram(); }
}

// ------------------------------------------------------------------------------------------------ the dossier: worked out again after every change
const env = () => ({ knowledge: KNOW, getBlob: store.getBlob, putBlob: store.putBlob, today: today(), generators: GEN_NAMES });
async function recompute() {
  const d = state.d;
  state.board = boardOf(KNOW, { countryId: d.country, profile: d.profile });
  for (const doc of d.docs) if (!doc.dup && !doc.split) doc.party = partyFor(doc, state.board);
  state.findings = await checkDossier(d, state.board, env());
  state.drafts = {};
  for (const doc of d.docs.filter(x => x.madeBy === 'program' && x.place)) {
    const draft = draftFor(doc.place, d);
    if (draft) state.drafts[doc.place] = { doc: doc.id, gaps: doc.editedBy ? [] : gapsOf(draft.model), ar: draft.ar };   // an edited draft's gaps are the person's to know
  }
  state.needs = needsOf(d, state.board, state.findings, { drafts: state.drafts });
}
async function save() { if (state.d) await store.putDossier(state.d); }
async function changed() { await recompute(); await save(); render(); }

// ------------------------------------------------------------------------------------------------ running the line of work
function say(html, kind = '', part = null) {
  if (!state.running) return;
  state.running.html = html; state.running.kind = kind;
  if (part != null) state.running.part = part;
  const el = $('#run-status');
  if (el) { el.innerHTML = html; el.className = `status ${kind}`; }
  const bar = $('#run-bar');
  if (bar && part != null) bar.style.width = `${Math.round(part * 100)}%`;
}
function stage(id, s) { state.d.stages = { ...(state.d.stages || {}), [id]: s }; const li = document.querySelector(`.stages li[data-stage="${id}"]`); if (li) li.className = s; }

// files: [{name, bytes}] — the whole line, or the steps after receiving when no files are given. place: put the new documents there.
async function runLine(files = [], { place = null, auto = true } = {}) {
  if (state.running) return;
  const d = state.d;
  state.running = { html: '', kind: '', part: 0, started: Date.now() };
  render();
  const t0 = Date.now();
  const tick = setInterval(() => { const el = $('#run-time'); if (el) el.textContent = `${Math.round((Date.now() - t0) / 1000)} ث`; }, 1000);
  try {
    if (files.length) {
      stage('receive', 'run');
      say('بيفتح الملفات…', '', 0.05);
      const { reader, how } = readerFor();
      const readEnv = { pdfjs, ocr: reader, drawPdf, drawImage, unrar, onProgress: e => {
        if (e.stage === 'open') say(`بيفتح <bdi>${esc(e.name)}</bdi>…`);
        if (e.stage === 'ocr') say(`${how.choice === 'claude' && !how.off ? 'Claude بيقرا' : 'قارئ المسح بيقرا'} الصفحة الممسوحة ${e.page} من ${e.pages} في <bdi>${esc(e.name)}</bdi>…`);
      } };
      const added = await addFiles(d, files, { read: readEnv, putBlob: store.putBlob });
      if (readEnv.ocrFailed) log(d, 'ocr-failed', { why: readEnv.ocrFailed.why || String(readEnv.ocrFailed.message || '') });
      if (how.off) log(d, 'claude-stopped', { code: how.off });
      if (place) for (const x of added) if (!x.dup) Object.assign(x, { place, sure: true, placeBy: 'you', state: 'placed' });
      stage('receive', 'done');
      await save();
    }
    stage('read', 'run'); stage('place', 'run');
    say('بيقرا المستندات ويعرف نوعها ومكانها…', '', 0.45);
    const claudeSample = sample();
    const uEnv = { ...env(), claude: claudeSample ? { sample: claudeSample } : null, onProgress: e => say(e.stage === 'claude-place' ? `Claude بيقرا <bdi>${esc(e.name)}</bdi> علشان يعرف مكانه…` : `بيقرا <bdi>${esc(e.name)}</bdi>…`) };
    await understand(d, uEnv);
    if (uEnv.claudeOff) log(d, 'claude-stopped', { code: uEnv.claudeOff });
    stage('read', 'done'); stage('place', 'done');
    await save();
    stage('check', 'run');
    say('بيفحص كل مستند على كارت قواعده، وبيقارن المستندات ببعض…', '', 0.7);
    await recompute();
    stage('check', 'done');
    if (auto) {
      stage('fix', 'run');
      say('بيصلّح اللي ينفع يتصلّح، وبيعمل مسودات مستندات الشركة الناقصة…', '', 0.85);
      await fixAll(d, state.findings, env());
      await writeDrafts(d, state.board, env());
      await recompute();
      stage('fix', 'done');
    }
    stage('needs', state.needs.length ? 'warn' : 'done');
    const r = readiness(d, state.board, state.findings, state.needs);
    stage('ready', r.ready ? 'done' : '');
    await save();
    const secs = Math.round((Date.now() - t0) / 1000);
    state.running = null;
    clearInterval(tick);
    render();
    toast(`خلص في ${secs} ث. ${state.needs.length ? `فيه ${count(state.needs.length, 'حاجة محتاجاك', 'حاجتين محتاجينك', 'حاجات محتاجاك', 'حاجة محتاجاك')}.` : 'مفيش حاجة محتاجاك.'}`, 6000);
    window.__workshopDone = (window.__workshopDone || 0) + 1;
  } catch (e) {
    clearInterval(tick);
    state.running = null;
    log(d, 'failed', { error: String(e.message || e).slice(0, 300) });
    await save().catch(() => {});
    render();
    toast(`حصلت مشكلة وماقدرتش أكمّل: ${e.message || e}`, 9000);
    window.__workshopError = String(e.stack || e.message || e);
  }
}

// ------------------------------------------------------------------------------------------------ views
function render() {
  $('#top-name').textContent = state.d ? state.d.name : '';
  $('#save-copy').hidden = !state.d;
  $('#view').innerHTML = state.view === 'home' ? viewHome() : state.view === 'new' ? viewWizard() : viewDossier();
  $('#drawer').hidden = !state.drawer;
  if (state.drawer) $('#drawer').innerHTML = viewDrawer();
  renderClaudeChip();
}
function renderClaudeChip() {
  const c = state.claude;
  $('#claude-chip').textContent = c.status === 'ready' ? `Claude: جاهز` : c.status === 'checking' ? 'Claude: بيتأكد…' : c.status === 'error' ? 'Claude: فيه مشكلة' : 'Claude: من غير مفتاح';
  $('#claude-chip').className = `btn small ${c.status === 'ready' ? '' : 'quiet'}`;
}

function viewHome() {
  const list = state.list.map(x => `<div class="card"><b>${esc(x.name)}</b><span class="fine">${esc(COUNTRIES.find(c => c.id === x.country)?.ar || x.country)} · ${x.docs} مستند · ${esc(String(x.updated || '').slice(0, 16).replace('T', ' '))}</span>
    <div class="row"><button class="btn small" data-act="open" data-id="${esc(x.id)}">افتح</button><button class="btn small quiet" data-act="export" data-id="${esc(x.id)}">احفظ نسخة</button><button class="btn small danger" data-act="delete" data-id="${esc(x.id)}">امسح</button></div></div>`).join('');
  return `<section class="box"><h2>الورشة: تحضير الملف <small>الجزء التاني من البرنامج</small></h2>
    <p class="fine">تدوس «ملف جديد»، وتختار الدولة ونوع الطلب، وترمي كل الملفات اللي عندك. البرنامج بيعمل الباقي، وبيقف بس عند الحاجة اللي محتاجاك:</p>
    <ol class="steps8">${STAGES.map(([, ar]) => `<li>${ar}</li>`).join('')}</ol>
    <div class="row"><button class="btn" data-act="new">ملف جديد</button><label class="btn quiet"><input type="file" id="import-file" accept=".zip,.dossier">افتح نسخة محفوظة</label></div>
    ${store.persistent ? '' : '<div class="status warn">المتصفح ده مش بيحفظ البيانات (نافذة خاصة؟): الملف هيضيع لما تقفل الصفحة. احفظ نسخة قبل ما تقفل.</div>'}
  </section>
  <section class="box"><h2>ملفاتي <small>محفوظة في المتصفح ده على جهازك</small></h2>${list ? `<div class="cards">${list}</div>` : '<p class="empty">لسه مفيش ملفات. ابدأ بـ «ملف جديد».</p>'}</section>`;
}

function viewWizard() {
  const w = state.wizard;
  const c = COUNTRIES.find(x => x.id === w.country);
  const q = (key, val) => `<label class="field"><span>${esc(QUESTIONS[key].ar)}</span><select data-wiz="${key}">${Object.entries(QUESTIONS[key].options).map(([k, ar]) => `<option value="${k}"${val === k ? ' selected' : ''}>${esc(ar)}</option>`).join('')}</select></label>`;
  return `<section class="box"><h2>ملف جديد <small>١. الدولة</small></h2>
    <div class="choices">${COUNTRIES.map(x => `<button type="button" class="choice" data-act="wiz-country" data-id="${x.id}" aria-pressed="${x.id === w.country}"><b>${esc(x.ar)}</b><span class="fine">${x.full ? 'كامل' : 'عام'}</span></button>`).join('')}</div>
    <p class="fine">${esc(c.note)}</p></section>
  <section class="box"><h2>٢. الطلب والمنتج</h2>
    <div class="fields">
      <label class="field"><span>اسم الملف (اختياري؛ البرنامج بيطلّع اسم المستحضر من المستندات)</span><input data-wiz="name" value="${esc(w.name)}" placeholder="مثلاً: مستحضر X 500 مجم"></label>
      ${q('activity', w.profile.activity)}${q('dossier_kind', w.profile.dossier_kind)}${q('origin', w.profile.origin)}${q('licence', w.profile.licence)}${q('leaflet', w.profile.leaflet)}
    </div>
    <p class="fine">الإجابات دي بتحدد إيه المطلوب في ملفك من جدول NP.CAPP.065 (العمود: <span class="ltr">${esc(boardOf(KNOW, { countryId: w.country, profile: w.profile }).column)}</span>). تقدر تغيّرها بعدين من «المعلومات».</p></section>
  <section class="box"><h2>٣. ارمي كل اللي عندك هنا</h2>
    <div class="drop" id="drop"><p>اسحب الملفات أو الفولدر هنا</p>
      <div class="row" style="justify-content:center"><label class="btn"><input type="file" id="wiz-files" multiple>اختار ملفات</label><label class="btn quiet"><input type="file" id="wiz-folder" webkitdirectory multiple>اختار فولدر</label></div>
      <p class="fine">أي صيغة: PDF فيه نص أو ممسوح، Word قديم وجديد، صور، ZIP و RAR (ولو جوه بعض).</p>
      <p class="picked">${w.files.length ? `اخترت ${w.files.length} ${w.files.length === 1 ? 'ملف' : 'ملفات'}: ${esc(w.files.slice(0, 6).map(f => f.name).join('، '))}${w.files.length > 6 ? '…' : ''}` : 'لسه مااخترتش ملفات (تقدر تبدأ من غيرها وتضيفها بعدين).'}</p></div>
    <p class="fine">${claudeOn() ? (state.claude.reader === 'claude' ? 'Claude هيقرا الصفحات الممسوحة ويحط اللي القواعد ماعرفتهوش (على مفتاحك).' : 'قارئ المسح على الجهاز هيقرا الصفحات الممسوحة؛ Claude هيحط اللي القواعد ماعرفتهوش.') : 'من غير مفتاح Claude: قارئ المسح على الجهاز بيقرا الممسوح، والقواعد بس بتعرف الأماكن. تقدر تحط المفتاح من «الإعدادات».'}</p>
    <div class="row"><button class="btn" data-act="wiz-start" data-auto="1">شغّل لوحدك</button><button class="btn quiet" data-act="wiz-start" data-auto="0">خطوة بخطوة</button><button class="btn quiet" data-act="home">رجوع</button></div>
  </section>`;
}

const placeLabel = id => { const p = state.board?.places.find(x => x.id === id); return p ? `<span class="ctd">${esc(p.ctd)}</span> ${esc(p.title.ar)}` : '<span class="fine">مالوش مكان</span>'; };
const docsOf = d => d.docs.filter(x => !x.dup && !x.split);

function viewDossier() {
  const d = state.d, r = readiness(d, state.board, state.findings, state.needs);
  const tabs = [['board', 'اللوحة'], ['docs', `المستندات (${docsOf(d).length})`], ['data', 'المعلومات'], ['needs', 'محتاج منك'], ['ready', 'الملف الجاهز'], ['ask', 'اسأل Claude'], ['log', 'السجل']];
  const run = state.running;
  return `<section class="box">
    <div class="row" style="justify-content:space-between"><h2>${esc(d.name)} <small>${esc(state.board.country.ar)} · العمود <span class="ltr">${esc(state.board.column)}</span> · ${esc(QUESTIONS.activity.options[d.profile.activity] || '')}</small></h2>
      <div class="row"><label class="btn small quiet"><input type="file" id="add-files" multiple>ضيف ملفات</label><label class="btn small quiet"><input type="file" id="add-folder" webkitdirectory multiple>ضيف فولدر</label>
      <button class="btn small" data-act="run-all"${run ? ' disabled' : ''}>شغّل لوحدك</button></div></div>
    <ol class="stages">${STAGES.map(([id, ar]) => `<li data-stage="${id}" class="${id === 'new' ? 'done' : d.stages?.[id] || ''}"><b>${ar}</b></li>`).join('')}</ol>
    ${run ? `<div class="status ${run.kind}" id="run-status" role="status" aria-live="polite">${run.html || 'بيبدأ…'}</div><div class="bar"><span id="run-bar" style="width:${Math.round((run.part || 0) * 100)}%"></span></div><p class="fine">الوقت: <span id="run-time">0 ث</span></p>` : ''}
    <div class="tiles">
      <div class="tile ${r.filled === r.required ? 'ok' : ''}"><b>${r.filled}/${r.required}</b><span>أماكن مطلوبة فيها مستندات</span></div>
      <div class="tile ${r.red ? 'bad' : 'ok'}"><b>${r.red}</b><span>ملاحظات لازم تتحل</span></div>
      <div class="tile ${r.amber ? 'warn' : 'ok'}"><b>${r.amber}</b><span>لازم تتوضح</span></div>
      <div class="tile ${state.needs.length ? 'warn' : 'ok'}"><b>${state.needs.length}</b><span>حاجات محتاجاك</span></div>
      <div class="tile"><b>${docsOf(d).length}</b><span>مستندات</span></div>
    </div>
    <div class="tabs" role="tablist">${tabs.map(([id, ar]) => `<button class="tab" role="tab" data-act="tab" data-id="${id}" aria-selected="${state.tab === id}">${ar}${id === 'needs' && state.needs.length ? `<span class="n">${state.needs.length}</span>` : ''}</button>`).join('')}</div>
    <div id="tab-body">${({ board: tabBoard, docs: tabDocs, data: tabData, needs: tabNeeds, ready: tabReady, ask: tabAsk, log: tabLog })[state.tab]()}</div>
  </section>`;
}

function tabBoard() {
  const d = state.d;
  const docsIn = id => docsOf(d).filter(x => x.place === id);
  const lv = { R: 'مطلوب', O: 'اختياري', NR: 'مش مطلوب', NA: 'لا ينطبق' };
  const mods = state.board.modules.map(m => {
    const places = m.places.filter(p => state.showAll || p.level === 'R' || p.level === 'O' || docsIn(p.id).length);
    if (!places.length) return '';
    return `<div class="module"><h3>${esc(m.title)}</h3><ul class="places">${places.map(p => {
      const st = placeStatus(p.id, d, state.findings), ds = docsIn(p.id);
      return `<li><button class="place" data-act="place" data-id="${esc(p.id)}"><span class="dot ${st}" title="${st}"></span><span class="ctd">${esc(p.ctd)}</span><span class="t">${esc(p.title.ar)}</span><span class="lvl ${p.level}">${lv[p.level]}</span>
        ${ds.length ? `<span class="docs-in">${ds.map(x => `${x.madeBy === 'program' ? '✎ ' : ''}${esc(x.name)}`).join('، ')}</span>` : ''}</button></li>`;
    }).join('')}</ul></div>`;
  }).join('');
  return `<div class="legend"><span><span class="dot green"></span> سليم</span><span><span class="dot amber"></span> لازم يتوضح</span><span><span class="dot red"></span> لازم يتحل</span><span><span class="dot empty"></span> فاضي</span>
    <label><input type="checkbox" data-act="show-all"${state.showAll ? ' checked' : ''}> اعرض اللي مش مطلوب للمنتج ده</label></div>${mods}
    <p class="fine">دوس على أي مكان تشوف كارت قواعده: إزاي بيتعرف، ولازم يكون فيه إيه، وصلاحيته، وشكله كملف، ومين يعدّل فيه، والمصادر.</p>`;
}

function placeOptions(selected) {
  const places = state.board.places.filter(p => p.level !== 'NA');
  return `<option value="">— من غير مكان —</option>${places.map(p => `<option value="${esc(p.id)}"${p.id === selected ? ' selected' : ''}>${esc(p.ctd)} ${esc(p.title.ar)}${p.level === 'R' ? '' : ` (${p.level})`}</option>`).join('')}`;
}
function readLine(doc) {
  if (doc.unread) return `<span class="badge bad">ماتقراش: ${esc(whyOf(doc.unread))}</span>`;
  const n = doc.pages.length, by = [...new Set(doc.pages.map(p => p.by))].map(b => BY[b] || b).join('، ');
  return `${n} ${n === 1 ? 'صفحة' : 'صفحات'} · ${esc(by)}${doc.note ? ` <span class="badge warn">${doc.note === 'no-ocr' ? 'ممسوح ومااتقراش' : doc.note.startsWith('long:') ? 'طويل: اتقرا أوله بس' : 'فيه صفحات ممسوحة مااتقرتش'}</span>` : ''}`;
}
function factsTable(doc) {
  if (!doc.facts?.length) return '';
  return `<details><summary>اللي اتقرا منه (${doc.facts.length})</summary><div class="scroll"><table class="facts">${doc.facts.map(f => `<tr><td>${esc(FIELD[f.field] || f.field)}</td><td dir="auto">${esc(f.value)}</td><td>ص ${f.page}${f.by === 'claude' ? ' · Claude' : ''}</td></tr><tr><td colspan="3"><blockquote class="q" dir="auto">${esc(f.quote)}</blockquote></td></tr>`).join('')}</table></div></details>`;
}
function tabDocs() {
  const d = state.d, docs = docsOf(d);
  if (!docs.length) return '<p class="empty">لسه مفيش مستندات. ضيف ملفات من فوق.</p>';
  const dups = d.docs.filter(x => x.dup);
  return `<ul class="list">${docs.map(doc => {
    const fs = state.findings.filter(f => f.doc === doc.id && !f.accepted);
    const lvl = fs.some(f => f.level === 'red') ? 'red' : fs.some(f => f.level === 'amber') ? 'amber' : 'done';
    const from = doc.from ? `اتقطع من «${esc(d.docs.find(x => x.id === doc.from.doc)?.name || '')}» ص ${doc.from.pages[0]}–${doc.from.pages[1]}` : '';
    return `<li class="item ${lvl}"><div class="row" style="justify-content:space-between"><h3><bdi>${esc(doc.name)}</bdi></h3><span class="kind">${esc(KIND[doc.kind] || doc.kind)}</span></div>
      <div class="meta"><span>${doc.madeBy === 'program' ? 'مسودة عملها البرنامج' : esc(doc.type_ar || (doc.type === 'unknown' ? 'نوعه مش معروف' : ''))}</span><span>${readLine(doc)}</span>${from ? `<span>${from}</span>` : ''}
        <span>${esc(PARTY[state.board.places.find(p => p.id === doc.place)?.doc_class]?.party === 'third' ? 'جهة تانية' : doc.party === 'eda' ? 'هيئة الدواء' : doc.party === 'third' ? 'جهة تانية' : 'الشركة')}</span>
        ${doc.fixes?.length ? `<span class="badge ok">اتصلّح: ${esc(doc.fixes.map(f => f.ar).join('، '))}</span>` : ''}${doc.versions?.length ? `<span class="badge">${doc.versions.length + 1} نسخ</span>` : ''}</div>
      <label class="field"><span>مكانه ${doc.placeBy === 'claude' ? '(حطّه Claude)' : doc.placeBy === 'you' ? '(انت)' : doc.placeBy === 'rules' ? (doc.sure ? '(القواعد)' : '(القواعد، مش متأكدة)') : ''}</span><select data-act="move" data-id="${esc(doc.id)}">${placeOptions(doc.place)}</select></label>
      ${fs.length ? `<details${lvl === 'red' ? ' open' : ''}><summary>ملاحظات (${fs.length})</summary><ul class="list">${fs.map(f => `<li class="fine">● ${esc(f.title)}</li>`).join('')}</ul></details>` : ''}
      ${factsTable(doc)}
      <div class="row"><button class="btn small quiet" data-act="doc-open" data-id="${esc(doc.id)}">افتح</button>${doc.madeBy === 'program' ? `<button class="btn small quiet" data-act="draft-view" data-id="${esc(doc.place)}">شوف المسودة</button>` : ''}
        ${available(programFor(doc.madeBy === 'program' ? 'docx' : doc.kind)) ? `<button class="btn small quiet" data-act="doc-program" data-id="${esc(doc.id)}">افتحه في ${esc(PROGRAMS[programFor(doc.madeBy === 'program' ? 'docx' : doc.kind)].ar)}</button>` : ''}
        ${['docx', 'doc'].includes(doc.kind) && available('wordcraft') ? `<button class="btn small quiet" data-act="word-pdf" data-id="${esc(doc.id)}">${doc.pdf ? 'اعمله PDF تاني' : 'اعمله PDF'}</button>` : ''}${doc.pdf ? '<span class="badge ok">ليه PDF</span>' : ''}
        <label class="btn small quiet"><input type="file" data-act="doc-upload" data-id="${esc(doc.id)}">ارفع نسخة جديدة</label><button class="btn small danger" data-act="doc-remove" data-id="${esc(doc.id)}">شيله من الملف</button></div></li>`;
  }).join('')}</ul>${dups.length ? `<p class="fine">${dups.length} ${dups.length === 1 ? 'ملف مكرر اتعرف' : 'ملفات مكررة اتعرفت'} ومادخلتش تاني: ${esc(dups.map(x => x.name).join('، '))}</p>` : ''}`;
}

const PRODUCT_FIELDS = [['trade_name', 'product_name'], ['dosage_form', 'dosage_form'], ['registration_number', 'registration_number'], ['license_holder', 'license_holder'], ['manufacturer', 'manufacturer']];
function tabData() {
  const d = state.d, data = dataOf(d);
  const values = fact => {                                         // every value read for a field, by document
    const out = [];
    for (const doc of docsOf(d)) for (const f of doc.facts || []) if (f.field === fact) out.push({ doc, f });
    return out;
  };
  const rows = PRODUCT_FIELDS.map(([key, fact]) => {
    const all = values(fact), distinct = [...new Set(all.map(x => fold(x.f.value).replace(/\s+/g, ' ')))];
    const cur = data[key];
    return `<tr><td>${esc(FIELD[key])}</td><td><input class="pv" data-key="${key}" value="${esc(cur?.value || '')}" dir="auto" style="width:100%"></td>
      <td>${cur?.from === 'you' ? 'انت' : cur?.from?.name ? `<bdi>${esc(cur.from.name)}</bdi> ص ${cur.from.page}` : '—'}${distinct.length > 1 ? `<div class="badge warn">قيم مختلفة: ${esc(all.map(x => `«${x.f.value}» (${x.doc.name})`).join('، '))}</div>` : ''}</td></tr>`;
  }).join('');
  const comp = (data.composition?.value || []).map(c => `<li dir="auto">${esc(c.value)}</li>`).join('');
  const company = COMPANY_FIELDS.map(([k, ar]) => `<label class="field"><span>${esc(ar)}</span><input class="cv" data-key="${k}" value="${esc(d.company?.[k] || '')}" dir="auto"></label>`).join('');
  const q = key => `<label class="field"><span>${esc(QUESTIONS[key].ar)}</span><select class="qv" data-key="${key}">${Object.entries(QUESTIONS[key].options).map(([k, ar]) => `<option value="${k}"${d.profile[key] === k ? ' selected' : ''}>${esc(ar)}</option>`).join('')}</select></label>`;
  return `<div class="box"><h3>بيانات المنتج <small class="fine">من المستندات، وكل قيمة بمصدرها. تقدر تصحّحها.</small></h3>
      <div class="scroll"><table class="facts"><tr><th>المعلومة</th><th>القيمة</th><th>من فين</th></tr>${rows}</table></div>
      ${comp ? `<div><b>التركيب</b> <span class="fine">(من «${esc(data.composition.from?.name || '')}»)</span><ul>${comp}</ul></div>` : ''}
      <div class="row"><button class="btn small" data-act="save-product">احفظ بيانات المنتج</button></div></div>
    <div class="box"><h3>بيانات الشركة <small class="fine">البرنامج مابيقدرش يقراها من المستندات؛ بتتحط في المسودات.</small></h3><div class="fields">${company}</div>
      <div class="row"><button class="btn small" data-act="save-company">احفظ وحدّث المسودات</button></div></div>
    <div class="box"><h3>الطلب</h3><div class="fields">${q('activity')}${q('dossier_kind')}${q('origin')}${q('licence')}${q('leaflet')}</div>
      <div class="row"><button class="btn small" data-act="save-profile">احفظ (اللوحة هتتحدّث)</button></div></div>`;
}

function needActions(n) {
  return n.actions.map(a => {
    if (a === 'accept') return `<button class="btn small quiet" data-act="need-accept" data-id="${esc(n.id)}">${actionName(a)}</button>`;
    if (a === 'upload') return n.doc ? `<label class="btn small quiet"><input type="file" data-act="doc-upload" data-id="${esc(n.doc)}">${actionName(a)}</label>`
                                     : n.place ? `<label class="btn small quiet"><input type="file" multiple data-act="place-upload" data-id="${esc(n.place)}">ارفع المستند</label>` : '';
    if (a === 'program') return n.doc ? `<button class="btn small quiet" data-act="doc-program" data-id="${esc(n.doc)}">${actionName(a)}</button>` : '';
    if (a === 'claude') return n.doc && claudeOn() ? `<button class="btn small quiet" data-act="need-claude" data-id="${esc(n.id)}">${actionName(a)}</button>` : '';
    if (a === 'create') return `<button class="btn small" data-act="create" data-id="${esc(n.place)}">${actionName(a)}</button>`;
    if (a === 'pdf') return n.doc && available('wordcraft') ? `<button class="btn small" data-act="word-pdf" data-id="${esc(n.doc)}">${actionName(a)}</button>` : '';
    if (a === 'fill') return `<button class="btn small" data-act="tab" data-id="data">${actionName(a)}</button>`;
    if (a === 'place') return `<select data-act="move" data-id="${esc(n.doc)}">${placeOptions(null)}</select>${(n.suggestion || []).map(s => `<button class="chip" data-act="move-to" data-id="${esc(n.doc)}" data-place="${esc(s.id)}">${esc(s.ctd)} ${esc(s.ar)}</button>`).join('')}`;
    if (a === 'cut') return `<button class="btn small" data-act="cut-ok" data-id="${esc(n.doc)}">التقطيع صح</button><button class="btn small quiet" data-act="cut-undo" data-id="${esc(n.doc)}">رجّعه ملف واحد</button>`;
    return '';
  }).join('');
}
function tabNeeds() {
  if (!state.needs.length) return '<div class="status ok">مفيش حاجة محتاجاك دلوقتي.</div>';
  return `<ul class="list">${state.needs.map(n => `<li class="item ${n.level}" id="need-${esc(n.id)}"><h3>${esc(n.title)}</h3><p class="detail">${esc(n.detail || '')}</p>
    ${n.places ? `<details open><summary>الأماكن (${n.places.length})</summary><ul class="list">${n.places.map(p => `<li class="row"><span class="ctd">${esc(p.ctd)}</span> ${esc(p.ar)}
      <label class="btn small quiet"><input type="file" multiple data-act="place-upload" data-id="${esc(p.id)}">ارفع</label><button class="btn small quiet" data-act="need-accept" data-id="${esc(p.finding)}">مش مطلوب (بسبب)</button></li>`).join('')}</ul></details>` : ''}
    ${(n.evidence || []).length ? `<details><summary>الكلام اللي في الصفحات (${n.evidence.length})</summary>${n.evidence.map(e => `<div class="fine"><bdi>${esc(e.name)}</bdi> — ص ${e.page}</div><blockquote class="q" dir="auto">${esc(e.quote)}</blockquote>`).join('')}</details>` : ''}
    ${n.rule ? `<p class="cite">القاعدة: ${esc(n.rule.ar)}${n.rule.cite?.length ? ` — ${esc(n.rule.cite.map(c => [c.src, c.at].filter(Boolean).join(' ')).join('؛ '))}` : ''}</p>` : ''}
    <div class="row">${needActions(n)}</div>
    <div class="accept" data-accept="${esc(n.id)}" hidden><textarea placeholder="السبب (بيتكتب في تقرير الجاهزية)"></textarea><div class="row"><button class="btn small" data-act="accept-ok" data-id="${esc(n.id)}">اقبل بالسبب ده</button></div></div></li>`).join('')}</ul>`;
}

function tabReady() {
  const d = state.d, r = readiness(d, state.board, state.findings, state.needs), layout = layoutOf(d, state.board);
  const left = [r.required > r.filled ? count(r.required - r.filled, 'مكان مطلوب فاضي', 'مكانين مطلوبين فاضيين', 'أماكن مطلوبة فاضية', 'مكان مطلوب فاضي') : '',
                r.red ? count(r.red, 'ملاحظة لازم تتحل', 'ملاحظتين لازم يتحلوا', 'ملاحظات لازم تتحل', 'ملاحظة لازم تتحل') : ''].filter(Boolean).join('، و');
  return `<div class="status ${r.ready ? 'ok' : 'warn'}">${r.ready ? 'الملف جاهز: كل الأماكن المطلوبة فيها مستندات، ومفيش ملاحظة لازم تتحل.' : `لسه: ${left}. تقدر تنزّل الفولدر برضه، والتقرير بيقول الناقص.`}</div>
    <div class="row"><button class="btn" data-act="ready-zip">نزّل فولدر الملف (ZIP) وتقرير الجاهزية</button><button class="btn quiet" data-act="ready-report">افتح تقرير الجاهزية</button></div>
    <p class="fine">الفولدر بشكل ملف ${esc(state.board.country.ar)}: موديول، وجواه مكان كل مستند، وكل ملف متسمّي باسم مكانه. ${layout.files.length} ملف.</p>
    <div class="scroll"><table class="facts"><tr><th>المكان</th><th>الملف في الفولدر</th></tr>${layout.files.map(f => `<tr><td><span class="ctd">${esc(f.place.ctd)}</span></td><td class="ltr" style="direction:ltr">${esc(f.path)}</td></tr>`).join('')}</table></div>`;
}

function tabAsk() {
  const a = state.ask;
  if (!claudeOn()) return `<div class="status warn">«اسأل Claude» محتاج مفتاح API. حطّه من «الإعدادات».</div>`;
  return `<form id="ask-form" class="accept"><textarea class="askbox" id="ask-text" placeholder="مثلاً: الإخطار ساري لحد إمتى؟ أو: إيه اللي ناقص في الموديول 1؟ أو: حط المستند D7 في مكانه الصح">${esc(a.draft || '')}</textarea>
    <div class="row"><button class="btn" type="submit"${a.busy ? ' disabled' : ''}>اسأل</button>${a.busy ? '<button class="btn quiet" type="button" data-act="ask-stop">وقّف</button>' : ''}<button class="btn quiet" type="button" data-act="ask-clear">محادثة جديدة</button></div></form>
    <div class="answer" id="ask-answer" data-empty="الرد هيظهر هنا.">${esc(a.text)}</div>
    ${a.steps.length ? `<h3>خطوات Claude</h3><ol class="tsteps">${a.steps.map(s => `<li class="${s.ok ? '' : 'no'}">${esc(s.name)} <span class="fine">${esc(JSON.stringify(s.input).slice(0, 160))}</span></li>`).join('')}</ol>` : ''}
    ${a.usage ? `<p class="fine">الاستهلاك في المحادثة دي: ${a.usage.input.toLocaleString('en')} توكن داخل، ${a.usage.output.toLocaleString('en')} خارج.</p>` : ''}`;
}

const LOG = { new: 'ملف جديد', received: 'استلام ملفات', cut: 'تقطيع ملف مجمّع', understood: 'قراية وتسكين', 'placed-by-claude': 'Claude حط مستند', 'claude-failed': 'Claude ماردّش',
              'claude-stopped': 'Claude وقف', 'ocr-failed': 'قارئ المسح ماشتغلش', fixed: 'تصليح', created: 'مسودة', moved: 'نقل مستند', accepted: 'قبول بسبب', uploaded: 'نسخة جديدة',
              removed: 'شيل مستند', 'fact-by-claude': 'معلومة سجّلها Claude', failed: 'مشكلة', confirmed: 'تأكيد', 'cut-undone': 'رجوع عن تقطيع', company: 'بيانات الشركة', profile: 'تغيير الطلب' };
function tabLog() {
  return `<ol class="tsteps">${[...state.d.log].reverse().map(e => `<li><b>${esc(LOG[e.what] || e.what)}</b> <span class="fine">${esc(e.at.slice(0, 19).replace('T', ' '))}</span>${e.reason ? ` — «${esc(e.reason)}»` : ''}${e.code ? ` — ${esc(CLAUDE_WHY[e.code] || e.code)}` : ''}${e.error ? ` — ${esc(e.error)}` : ''}</li>`).join('')}</ol>`;
}

function viewDrawer() {
  const dr = state.drawer;
  if (dr.kind === 'draft') {
    const draft = draftFor(dr.id, state.d);
    return `<button class="btn small quiet close" data-act="drawer-close">اقفل ✕</button><h2>${esc(draft.ar)} <small class="fine">مسودة</small></h2>
      <div class="row"><button class="btn small" data-act="draft-docx" data-id="${esc(dr.id)}">نزّلها Word</button><button class="btn small quiet" data-act="doc-program" data-id="${esc(state.drafts[dr.id]?.doc || '')}">افتحها في برنامج الـ Word</button></div>
      ${gapsOf(draft.model).length ? `<div class="status warn">ناقص ${gapsOf(draft.model).length}: ${esc(gapsOf(draft.model).join('، '))}</div>` : ''}
      ${htmlOf(draft.model)}${draft.model.note ? `<p class="cite">${esc(draft.model.note)}</p>` : ''}`;
  }
  const card = ruleCard(KNOW, dr.id), p = state.board.places.find(x => x.id === dr.id);
  if (!card) return '<button class="btn small quiet close" data-act="drawer-close">اقفل ✕</button>';
  const docs = docsOf(state.d).filter(x => x.place === dr.id);
  const fs = state.findings.filter(f => f.place === dr.id || docs.some(x => x.id === f.doc));
  const cite = list => (list || []).map(c => { const s = KNOW.sources.find(x => x.id === c.src); return `${esc(s?.code || c.src)}${s?.version ? ` v${esc(s.version)}` : ''}${c.at ? `، ${esc(c.at)}` : ''}`; }).join(' · ');
  const gen = GENERATORS[dr.id];
  return `<button class="btn small quiet close" data-act="drawer-close">اقفل ✕</button>
    <h2><span class="ctd">${esc(card.ctd)}</span> ${esc(card.title.ar)}</h2><p class="fine" dir="ltr">${esc(card.title.en)}</p>
    <div class="row"><span class="lvl ${p.level}">${{ R: 'مطلوب', O: 'اختياري', NR: 'مش مطلوب', NA: 'لا ينطبق' }[p.level]}</span>${p.why ? `<span class="fine">الشرط: <span class="ltr">${esc(p.why)}</span></span>` : ''}</div>
    <div class="row"><label class="btn small"><input type="file" multiple data-act="place-upload" data-id="${esc(dr.id)}">ارفع مستند هنا</label>${gen ? `<button class="btn small quiet" data-act="create" data-id="${esc(dr.id)}">${state.drafts[dr.id] ? 'اعمل المسودة تاني' : 'اعمل المسودة'}</button>${state.drafts[dr.id] ? `<button class="btn small quiet" data-act="draft-view" data-id="${esc(dr.id)}">شوف المسودة</button>` : ''}` : ''}</div>
    <div class="card-rows">
      <div><span class="lab">المستندات هنا</span>${docs.length ? docs.map(x => `<span>● <bdi>${esc(x.name)}</bdi></span>`).join('') : '<span class="fine">مفيش</span>'}</div>
      ${fs.length ? `<div><span class="lab">الملاحظات</span>${fs.map(f => `<span class="${f.level === 'red' ? 'badge bad' : 'badge warn'}">${esc(f.title)}</span>`).join(' ')}</div>` : ''}
      <div><span class="lab">إزاي بيتعرف</span><span>${card.recognise.types.length ? esc(card.recognise.types.join('، ')) + ' · ' : ''}${card.recognise.words.length ? `كلمات: <span dir="ltr">${esc(card.recognise.words.join(' · '))}</span>` : 'من غير كلمات تعرّفه في المكتبة لسه: Claude أو انت بتحطوه'}</span></div>
      <div><span class="lab">لازم يكون فيه</span><span dir="ltr" style="text-align:left">${esc(card.must.en || '—')}</span>${card.must.note ? `<span class="fine" dir="ltr">${esc(card.must.note)}</span>` : ''}</div>
      ${card.validity ? `<div><span class="lab">صلاحيته</span><span>${card.validity.months ? `${card.validity.months} شهر` : 'التاريخ المكتوب عليه'}${card.validity.warn_days ? ` · تنبيه قبلها بـ ${card.validity.warn_days} يوم` : ''}</span><span class="cite" dir="ltr">${esc(card.validity.note)}</span><span class="cite">${cite(card.validity.cite)}</span></div>` : ''}
      ${card.format.length ? `<div><span class="lab">شكله كملف</span>${card.format.map(f => `<span>● ${esc(f.ar)} <span class="cite">(${cite(f.cite)})</span></span>`).join('')}</div>` : ''}
      <div><span class="lab">مين يعدّل فيه</span><span>${esc(card.party.ar)}</span></div>
      ${card.template?.example ? `<div><span class="lab">شكله المقبول</span><span>${esc(card.template.example.ar)}</span></div>` : ''}
      ${card.rebuild?.needs ? `<div><span class="lab">بيتعمل من</span><span dir="ltr" style="text-align:left">${esc(card.rebuild.needs)}</span></div>` : ''}
      <div><span class="lab">المصادر</span><span class="cite">${cite(card.cite)}${card.ectd_cite?.length ? ` · eCTD: ${cite(card.ectd_cite)}` : ''}</span></div>
    </div>`;
}

// ------------------------------------------------------------------------------------------------ actions
async function openDossier(id) {
  const d = await store.getDossier(id);
  if (!d) { toast('الملف ده مش موجود'); return; }
  state.d = d; state.view = 'dossier'; state.tab = 'board'; state.drawer = null; state.ask = { history: [], steps: [], text: '', busy: false };
  await recompute();
  render();
}
async function goHome() { state.view = 'home'; state.d = null; state.drawer = null; state.list = await store.listDossiers(); render(); }

async function filesFrom(list) { const out = []; for (const f of list) out.push({ name: f.webkitRelativePath || f.name, bytes: new Uint8Array(await f.arrayBuffer()) }); return out; }
const SKIP = /(^|\/)(\.|__MACOSX\/|Thumbs\.db$|desktop\.ini$)/i;
async function entriesOf(items) {
  const out = [];
  const walk = async (entry, at) => {
    if (entry.isFile) { const file = await new Promise((ok, no) => entry.file(ok, no)); out.push({ name: at + file.name, file }); return; }
    const reader = entry.createReader();
    for (;;) { const batch = await new Promise((ok, no) => reader.readEntries(ok, no)); if (!batch.length) break; for (const e of batch) await walk(e, `${at}${entry.name}/`); }
  };
  for (const it of items) { const e = it.webkitGetAsEntry?.(); if (e) await walk(e, ''); else if (it.getAsFile?.()) out.push({ name: it.getAsFile().name, file: it.getAsFile() }); }
  return out;
}
const pickedFiles = async list => (await filesFrom([...list])).filter(f => !SKIP.test(f.name));

async function newVersion(docId, bytes, name, how = 'upload') {
  const d = state.d, doc = d.docs.find(x => x.id === docId);
  const { reader } = readerFor();
  const [read] = await readFiles([{ name, bytes }], { pdfjs, ocr: reader, drawPdf, drawImage, unrar, keepBytes: true });
  const sha = await store.sha256(bytes);
  await store.putBlob(d.id, sha, bytes);
  doc.versions = [...(doc.versions || []), { sha: doc.fixed || doc.sha, at: new Date().toISOString(), name: doc.name }];
  const draft = doc.madeBy === 'program';
  Object.assign(doc, { sha, size: bytes.length, kind: read?.kind || doc.kind, pages: read?.pages || [], fixed: undefined, fixes: [], info: undefined, pdf: undefined });
  if (draft && how === 'program') doc.editedBy = 'you';          // a draft edited in the Word program: never written over by the program again
  else { doc.madeBy = undefined; doc.name = name; }               // an upload (the signed scan) takes the draft's place
  delete doc.unread; delete doc.note;
  if (read?.unread) doc.unread = read.unread;
  const { factsByRules } = await import('./understand.js');
  doc.facts = factsByRules(doc.pages);
  log(d, 'uploaded', { doc: doc.id, name, how });
  await changed();
}
async function uploadVersion(docId, file) {
  await newVersion(docId, new Uint8Array(await file.arrayBuffer()), file.name, 'upload');
  toast('النسخة الجديدة اتحطت مكان القديمة، والملف اتفحص تاني.');
}

async function openDocFile(docId) {
  const d = state.d, doc = d.docs.find(x => x.id === docId);
  if (!doc) return;
  if (doc.madeBy === 'program' && !doc.editedBy) { const draft = draftFor(doc.place, d); download(doc.name, await docxOf(draft.model), TYPES.docx); return; }
  const bytes = await store.getBlob(d.id, doc.fixed || doc.sha);
  if (!bytes) { toast('الملف ده مش محفوظ'); return; }
  if (doc.kind === 'pdf') { const url = URL.createObjectURL(new Blob([bytes], { type: TYPES.pdf })); window.open(url, '_blank'); setTimeout(() => URL.revokeObjectURL(url), 120000); return; }
  download(doc.name.split('/').pop(), bytes, TYPES[doc.kind] || 'application/octet-stream');
}

async function askClaude(text) {
  const a = state.ask;
  if (!text.trim() || a.busy) return;
  a.busy = true; a.steps = []; a.text = ''; a.draft = '';
  a.controller = new AbortController();
  a.history.push({ role: 'user', content: text });
  render();
  const tools = workshopTools({ dossier: () => state.d, board: () => state.board, findings: () => state.findings, knowledge, changed: () => { save(); } });
  try {
    const res = await converse(state.claude.client, state.claude.model, { system: ASK_SYSTEM, messages: a.history, tools, signal: a.controller.signal,
      onText: ({ text: t }) => { a.text = t; const el = $('#ask-answer'); if (el) el.textContent = t; },
      onStep: s => { a.steps.push(s); } });
    a.text = res.text; a.history = res.history; a.usage = { input: (a.usage?.input || 0) + res.usage.input, output: (a.usage?.output || 0) + res.usage.output };
  } catch (e) {
    a.history.pop();
    a.text = `${CLAUDE_WHY[e.code] || 'Claude ماردّش.'}${e.detail ? `\n(${e.detail})` : ''}`;
  }
  a.busy = false;
  await recompute(); await save();
  render();
}

async function claudeFixNeed(id) {
  const n = state.needs.find(x => x.id === id);
  if (!n) return;
  state.tab = 'ask';
  render();
  const doc = state.d.docs.find(x => x.id === n.doc);
  await askClaude(`الملاحظة دي في الملف: «${n.title}». ${n.detail || ''}\nالمستند: ${doc ? `${doc.id} (${doc.name})` : '—'}.\nاقرا المستند والمستندات المرتبطة بيه، وقولي بالظبط المطلوب علشان تتحل، ولو ينفع تصلّحها بأدواتك (مكان مستند، معلومة) صلّحها. ماتغيّرش مستند جهة تانية.`);
}

async function testKey(key, remember) {
  state.claude = { ...state.claude, key, status: 'checking', error: '' };
  renderSettings();
  try {
    const { client, models } = await connect(key, { baseURL: globalThis.__workshopApiBase || undefined });
    const model = models.some(m => m.id === state.claude.model) ? state.claude.model : models[0]?.id || '';
    state.claude = { ...state.claude, client, models, model, status: model ? 'ready' : 'error', error: model ? '' : 'المفتاح مش متاح له أي نموذج' };
    local.set('model', model || null);
    local.set('key', remember ? key : null);
  } catch (e) {
    state.claude = { ...state.claude, client: null, status: 'error', error: `${e.message}${e.detail ? ` (${e.detail})` : ''}`, code: e.code };
  }
  renderSettings(); render();
}
function renderSettings() {
  const c = state.claude;
  $('#settings-body').innerHTML = `<h2>الإعدادات</h2>
    <label class="field"><span>مفتاح Claude API (من console.anthropic.com؛ الاستهلاك على حسابك)</span><input type="password" id="api-key" autocomplete="off" value="${esc(c.key)}" placeholder="sk-ant-…" dir="ltr"></label>
    <label class="row fine"><input type="checkbox" id="api-remember"${local.get('key', '') ? ' checked' : ''}> افتكر المفتاح على الجهاز ده (أي صفحة تتفتح من ملفات الجهاز في المتصفح ده تقدر تقراه؛ من غيرها بيتنسى لما تقفل الصفحة)</label>
    <div class="row"><button class="btn" type="button" data-act="key-test">اختبر المفتاح</button><button class="btn quiet" type="button" data-act="key-forget">انسَ المفتاح</button></div>
    ${c.status === 'checking' ? '<div class="status">بيتأكد من المفتاح…</div>' : c.status === 'error' ? `<div class="status bad">${esc(c.error)}</div>` : c.status === 'ready' ? `<div class="status ok">المفتاح شغال. ${c.models.length} ${c.models.length === 1 ? 'نموذج متاح' : 'نماذج متاحة'}.</div>` : ''}
    ${c.models.length ? `<label class="field"><span>النموذج</span><select id="api-model">${c.models.map(m => `<option value="${esc(m.id)}"${m.id === c.model ? ' selected' : ''}>${esc(m.name)}</option>`).join('')}</select></label>` : ''}
    <fieldset class="box"><legend>مين يقرا الصفحات الممسوحة</legend>
      <label class="row"><input type="radio" name="reader" value="claude"${c.reader === 'claude' ? ' checked' : ''}> <span><b>Claude</b> <span class="fine">أدق (قِسناه 97–98%)، وصور الصفحات الممسوحة بس هي اللي بتتبعت له على مفتاحك.</span></span></label>
      <label class="row"><input type="radio" name="reader" value="ocr"${c.reader === 'ocr' ? ' checked' : ''}> <span><b>قارئ المسح على الجهاز</b> <span class="fine">مفيش حاجة بتخرج من جهازك. أبطأ وأضعف في العربي (93% على صفحاتنا التجريبية).</span></span></label></fieldset>
    <p class="fine">المفتاح بيروح لـ api.anthropic.com بس. البرنامج نفسه وملفاتك على جهازك؛ اللي بيتبعت لـ Claude: صور الصفحات الممسوحة (لو اخترته)، وأول صفحات المستند اللي القواعد ماعرفتش مكانه، وأسئلتك في «اسأل Claude» بالصفحات اللي بيطلبها.</p>
    <div class="row"><button class="btn" type="button" data-act="settings-close">تمام</button></div>`;
}

// ------------------------------------------------------------------------------------------------ wiring
document.addEventListener('click', async e => {
  const el = e.target.closest('[data-act]');
  if (!el || el.tagName === 'SELECT' || el.type === 'file' || el.type === 'checkbox' && el.dataset.act !== 'show-all') return;
  const act = el.dataset.act, id = el.dataset.id;
  try {
    if (act === 'new') { state.wizard = { country: 'EG', profile: { activity: 'new', dossier_kind: 'generic', origin: 'local', licence: 'own', leaflet: 'english' }, name: '', files: [] }; state.view = 'new'; render(); }
    else if (act === 'home') await goHome();
    else if (act === 'open') await openDossier(id);
    else if (act === 'export') download(`${(state.list.find(x => x.id === id)?.name || 'dossier').replace(/[\\/:*?"<>|]/g, ' ')}.dossier.zip`, await store.exportDossier(id), 'application/zip');
    else if (act === 'delete') { if (el.dataset.sure) { await store.deleteDossier(id); await goHome(); } else { el.dataset.sure = '1'; el.textContent = 'متأكد؟ دوس تاني'; } }
    else if (act === 'wiz-country') { state.wizard.country = id; render(); }
    else if (act === 'wiz-start') {
      const w = state.wizard;
      const d = newDossier({ country: w.country, profile: { ...w.profile }, name: w.name.trim() || 'ملف جديد' });
      state.d = d; state.view = 'dossier'; state.tab = 'board';
      await store.putDossier(d);
      await recompute(); render();
      await runLine(w.files, { auto: el.dataset.auto === '1' });
      if (!w.name.trim()) { const t = dataOf(d).trade_name?.value; if (t) { d.name = t; await save(); render(); } }
    }
    else if (act === 'tab') { state.tab = id; render(); }
    else if (act === 'show-all') { state.showAll = el.checked; render(); }
    else if (act === 'place') { state.drawer = { kind: 'place', id }; render(); }
    else if (act === 'drawer-close') { state.drawer = null; render(); }
    else if (act === 'draft-view') { state.drawer = { kind: 'draft', id }; render(); }
    else if (act === 'draft-docx') { const dr = draftFor(id, state.d); download(`${dr.ar} (مسودة).docx`, await docxOf(dr.model), TYPES.docx); }
    else if (act === 'run-all') await runLine([], { auto: true });
    else if (act === 'create') { await writeDrafts(state.d, state.board, env(), { only: [id] }); await changed(); state.drawer = { kind: 'draft', id }; render(); toast('المسودة اتعملت. كمّل الناقص فيها من «المعلومات».'); }
    else if (act === 'move-to') { moveDoc(state.d, id, el.dataset.place); await changed(); }
    else if (act === 'doc-open') await openDocFile(id);
    else if (act === 'doc-program') await openInProgram(id);
    else if (act === 'program-close') hideProgram();
    else if (act === 'word-pdf') await wordToPdf(id);
    else if (act === 'doc-remove') { if (el.dataset.sure) { const d = state.d; d.docs = d.docs.filter(x => x.id !== id); log(d, 'removed', { doc: id }); await changed(); } else { el.dataset.sure = '1'; el.textContent = 'متأكد؟'; } }
    else if (act === 'need-accept') { const box = document.querySelector(`[data-accept="${CSS.escape(id)}"]`) || el.closest('.item')?.querySelector('.accept'); if (box) { box.hidden = false; box.dataset.target = id; box.querySelector('textarea').focus(); } }
    else if (act === 'accept-ok') { const box = el.closest('.accept'); accept(state.d, box.dataset.target || id, box.querySelector('textarea').value); await changed(); toast('اتقبل، والسبب اتسجّل.'); }
    else if (act === 'need-claude') await claudeFixNeed(id);
    else if (act === 'cut-ok') { state.d.decisions[`cut-${id}`] = { reason: 'التقطيع صح', at: new Date().toISOString(), by: 'you' }; log(state.d, 'confirmed', { item: `cut-${id}` }); await changed(); }
    else if (act === 'cut-undo') { const d = state.d, doc = d.docs.find(x => x.id === id); d.docs = d.docs.filter(x => x.from?.doc !== id); doc.split = false; delete doc.cut; doc.state = 'read'; doc.from = undefined;
      const { typeAndPlace, factsByRules } = await import('./understand.js'); Object.assign(doc, typeAndPlace(doc.pages, {}), { facts: factsByRules(doc.pages), placeBy: 'rules', state: 'placed' }); log(d, 'cut-undone', { doc: id }); await changed(); }
    else if (act === 'save-product') { const d = state.d; d.product = d.product || {}; for (const i of document.querySelectorAll('.pv')) { if (i.value.trim()) d.product[i.dataset.key] = { value: i.value.trim(), from: 'you' }; else delete d.product[i.dataset.key]; } await changed(); toast('اتحفظ.'); }
    else if (act === 'save-company') { const d = state.d; d.company = {}; for (const i of document.querySelectorAll('.cv')) if (i.value.trim()) d.company[i.dataset.key] = i.value.trim(); log(d, 'company'); await writeDrafts(d, state.board, env(), { only: Object.keys(state.drafts) }); await changed(); toast('اتحفظت، والمسودات اتحدّثت.'); }
    else if (act === 'save-profile') { const d = state.d; for (const s of document.querySelectorAll('.qv')) d.profile[s.dataset.key] = s.value; log(d, 'profile'); await changed(); toast('الطلب اتغيّر، واللوحة اتحدّثت.'); }
    else if (act === 'ready-zip') { const r = await readyZip(state.d, state.board, state.findings, state.needs, { getBlob: store.getBlob, draftBytes: async doc => docxOf(draftFor(doc.place, state.d).model) }); download(`${r.layout.root}.zip`, r.zip, 'application/zip'); }
    else if (act === 'ready-report') { const html = reportHtml(state.d, state.board, state.findings, state.needs, layoutOf(state.d, state.board)); const url = URL.createObjectURL(new Blob([html], { type: 'text/html' })); window.open(url, '_blank'); }
    else if (act === 'ask-stop') state.ask.controller?.abort();
    else if (act === 'ask-clear') { state.ask = { history: [], steps: [], text: '', busy: false }; render(); }
    else if (act === 'settings') { renderSettings(); $('#settings').showModal(); }
    else if (act === 'settings-close') { const m = $('#api-model'); if (m) { state.claude.model = m.value; local.set('model', m.value); } const r = document.querySelector('input[name="reader"]:checked'); if (r) { state.claude.reader = r.value; local.set('reader', r.value); } $('#settings').close(); render(); }
    else if (act === 'key-test') await testKey($('#api-key').value.trim(), $('#api-remember').checked);
    else if (act === 'key-forget') { local.set('key', null); state.claude = { ...state.claude, key: '', client: null, models: [], status: 'none', error: '' }; renderSettings(); render(); }
    else if (act === 'save-copy') download(`${state.d.name.replace(/[\\/:*?"<>|]/g, ' ')}.dossier.zip`, await store.exportDossier(state.d.id), 'application/zip');
  } catch (err) { toast(`ماقدرتش: ${err.message || err}`, 7000); window.__workshopError = String(err.stack || err); }
});

document.addEventListener('change', async e => {
  const el = e.target;
  try {
    if (el.matches('[data-wiz]')) { const w = state.wizard; if (el.dataset.wiz === 'name') w.name = el.value; else w.profile[el.dataset.wiz] = el.value; if (el.dataset.wiz !== 'name') render(); return; }
    if (el.id === 'wiz-files' || el.id === 'wiz-folder') { state.wizard.files.push(...await pickedFiles(el.files)); el.value = ''; render(); return; }
    if (el.id === 'add-files' || el.id === 'add-folder') { const files = await pickedFiles(el.files); el.value = ''; if (files.length) await runLine(files, { auto: true }); return; }
    if (el.id === 'import-file') { const f = el.files[0]; el.value = ''; if (f) { const d = await store.importDossier(new Uint8Array(await f.arrayBuffer())); await openDossier(d.id); toast('الملف اتفتح.'); } return; }
    if (el.dataset.act === 'move' && el.tagName === 'SELECT') { moveDoc(state.d, el.dataset.id, el.value || null); await changed(); return; }
    if (el.dataset.act === 'doc-upload') { const f = el.files[0]; el.value = ''; if (f) await uploadVersion(el.dataset.id, f); return; }
    if (el.dataset.act === 'place-upload') { const files = await pickedFiles(el.files); el.value = ''; if (files.length) { state.drawer = null; await runLine(files, { place: el.dataset.id, auto: true }); } return; }
    if (el.id === 'api-model') { state.claude.model = el.value; local.set('model', el.value); }
  } catch (err) { toast(`ماقدرتش: ${err.message || err}`, 7000); window.__workshopError = String(err.stack || err); }
});
document.addEventListener('submit', e => { if (e.target.id === 'ask-form') { e.preventDefault(); askClaude($('#ask-text').value); } });
document.addEventListener('input', e => { if (e.target.id === 'ask-text') state.ask.draft = e.target.value; });
document.addEventListener('dragover', e => { const z = e.target.closest?.('#drop'); if (z) { e.preventDefault(); z.classList.add('over'); } });
document.addEventListener('dragleave', e => { const z = e.target.closest?.('#drop'); if (z) z.classList.remove('over'); });
document.addEventListener('drop', async e => {
  const z = e.target.closest?.('#drop');
  if (!z) return;
  e.preventDefault(); z.classList.remove('over');
  const got = await entriesOf([...e.dataTransfer.items]);
  state.wizard.files.push(...(await filesFrom(got.map(g => Object.assign(g.file, { webkitRelativePath: undefined })))).map((f, i) => ({ ...f, name: got[i].name })).filter(f => !SKIP.test(f.name)));
  render();
});
document.addEventListener('keydown', e => { if (e.key === 'Escape' && state.drawer) { state.drawer = null; render(); } });

// for the tests: the same steps as the buttons
window.__workshop = { state, runLine, openDossier, recompute, store, testKey, uploadVersion, askClaude, programs, openInProgram, wordToPdf };

(async () => {
  state.list = await store.listDossiers();
  render();
  const key = local.get('key', '');
  if (key) testKey(key, true);
})();
