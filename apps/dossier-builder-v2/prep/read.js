// Every file of a dossier opened by its content (never its name) and read page by page: a PDF's own text where it has one, a scanned
// page (or a picture) read by the page's scan reader when one is given (prep/ocr.js, in the browser), Word files old and new, and
// the files inside ZIP and RAR archives, as deep as archives go in archives. What cannot be read says why; nothing is guessed.
//   readFiles(files: [{name, bytes}], env) → [{id, name, kind, pages: [{n, text, by: 'text'|'ocr'|'claude'|'word'|'plain'}], unread?, note?}]
//   env: {pdfjs, ocr?: {page(canvas, {dpi, name, page, pages}) → text or {text, by}, lanes?}, drawPdf?(page) → canvas,
//         drawImage?(bytes, kind) → canvases, onProgress?, unrar?}
import { kindOf } from '../agent/workspace.js';
import { pageTextOf } from '../core/pdftext.js';
import { unzip } from './zip.js';
import { cfb, docText, docxText } from './office.js';
import { core as rarCore } from './rar.js';

// A PDF page with fewer letters than this in its own text is a scan (a stamp, a page number or a header line is not a text layer).
export const SCANNED = 40;
// A long document (over LONG pages: a validation report with its chromatograms, a batch record) has only its first FIRST scanned
// pages read: who wrote it, what it is and for which product are on its first pages, and each scanned page takes seconds.
export const LONG = 20, FIRST = 4;
const letters = s => (String(s).match(/[\p{L}\p{N}]/gu) || []).length;
const WHY = {
  password: 'محمي بكلمة سر', damaged: 'الملف تالف أو مش كامل', unsupported: 'نوعه أو طريقة ضغطه مش بتتقري لسه', unreadable: 'محتواه مش مطابق للي متسجل له في الأرشيف',
  volume: 'جزء من أرشيف متقسم والأجزاء الباقية مش موجودة', memory: 'أكبر من اللي الصفحة تقدر تفتحه', link: 'اختصار لملف تاني', 'too large': 'أكبر من الحد',
  zip64: 'أرشيف ZIP أكبر من 4 جيجا', 'no-ocr': 'صفحات ممسوحة ومفيش قارئ للمسح هنا', kind: 'نوعه لسه مش بيتقري',
};
export const whyOf = code => WHY[code] || code;

function joinParts(parts) {
  if (parts.length === 1) return parts[0];
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) { out.set(new Uint8Array(p), at); at += p.byteLength ?? p.length; }
  return out;
}
// RAR on this thread (Node and the tests); the page passes `unrar` to read it in a worker
const rarHere = async bytes => {
  const files = [];
  const r = rarCore.extract([bytes], {}, (name, parts, of) => files.push({ name, bytes: of ? files.find(f => f.name === of)?.bytes : joinParts(parts) }));
  return { files, skipped: r.skipped };
};

// A reader's answer: its text, and who read it (the scan reader on the computer, or Claude)
const answer = got => (typeof got === 'string' ? { text: got, by: 'ocr' } : { text: String(got?.text || ''), by: got?.by || 'ocr' });

async function pdfPages(bytes, env, tell, name) {
  const task = env.pdfjs.getDocument({ data: bytes.slice(), isEvalSupported: false, useSystemFonts: false });
  const doc = await task.promise;
  try {
    const pages = [];
    let scans = 0, skipped = 0, read = 0;
    // the scanned pages are read as many at once as the scan reader has lanes (two on a computer with cores to spare)
    const lanes = Math.max(1, env.ocr?.lanes || 1), running = new Set();
    const scan = async (n, page, text, slot) => {
      try {
        if (env.ocrFailed) throw env.ocrFailed;
        const canvas = await env.drawPdf(page);
        page.cleanup();
        const got = answer(await env.ocr.page(canvas, { dpi: canvas.dpi ?? 300, name, page: n, pages: doc.numPages }));
        slot.text = letters(got.text) > letters(text) ? got.text : text;
        slot.by = got.by;
      } catch (e) {                                       // the scan reader cannot run here: the page stays unread, and says why
        env.ocrFailed = e;
        slot.unreadScan = true;
      }
    };
    for (let n = 1; n <= doc.numPages; n++) {
      const page = await doc.getPage(n);
      const text = pageTextOf(await page.getTextContent());
      if (letters(text) >= SCANNED || !env.ocr || !env.drawPdf || env.ocrFailed) {   // once the scan reader cannot run, it is not tried again
        if (letters(text) < SCANNED) scans++;
        pages.push({ n, text, by: 'text' });
        page.cleanup();
      } else if (doc.numPages > LONG && read >= FIRST) {
        skipped++;
        pages.push({ n, text, by: 'text' });
        page.cleanup();
      } else {
        read++;
        tell({ stage: 'ocr', page: n, pages: doc.numPages });
        const slot = { n, text, by: 'text' };
        pages.push(slot);
        const job = scan(n, page, text, slot).finally(() => running.delete(job));
        running.add(job);
        if (running.size >= lanes) await Promise.race(running);
      }
    }
    await Promise.all(running);
    for (const p of pages) if (p.unreadScan) { delete p.unreadScan; scans++; }
    return { pages, scans, skipped };
  } finally { await task.destroy(); }
}

export async function readFiles(files, env = {}) {
  const out = [];
  const tell = e => { try { env.onProgress?.(e); } catch { /* the page's progress line only */ } };
  // env.keepBytes: each document also carries the bytes it was read from (not enumerable: never in what is saved or compared)
  const add = (name, kind, extra, bytes) => {
    const d = { id: `d${out.length + 1}`, name, kind, pages: [], ...extra };
    if (env.keepBytes && bytes) Object.defineProperty(d, 'bytes', { value: bytes, enumerable: false });
    out.push(d);
    return d;
  };
  async function one(name, bytes, depth) {
    tell({ stage: 'open', name });
    let kind = kindOf(bytes);
    if (kind === 'office-old' || kind === 'doc') {
      try { kind = cfb(bytes).names.includes('WordDocument') ? 'doc' : kind; } catch { /* reported below as it is */ }
    }
    try {
      if ((kind === 'zip' || kind === 'rar') && depth < 4) {
        const { files: inner, skipped } = kind === 'zip' ? await unzip(bytes) : await (env.unrar || rarHere)(bytes);
        for (const s of skipped) add(`${name}/${s.name}`, 'unknown', { unread: s.why });
        for (const f of inner) if (f.bytes) await one(`${name}/${f.name}`, f.bytes, depth + 1);
        return;
      }
      if (kind === 'pdf') {
        const { pages, scans, skipped } = await pdfPages(bytes, env, e => tell({ ...e, name }), name);
        const d = add(name, kind, { pages }, bytes);
        if (scans) d.note = scans === pages.length ? 'no-ocr' : `no-ocr:${scans}`;
        else if (skipped) d.note = `long:${skipped}`;
        return;
      }
      if (kind === 'doc') { add(name, kind, { pages: docText(bytes) }, bytes); return; }
      if (kind === 'docx') { add(name, kind, { pages: await docxText(bytes) }, bytes); return; }
      if (kind === 'text') { add(name, kind, { pages: [{ n: 1, text: new TextDecoder().decode(bytes), by: 'plain' }] }, bytes); return; }
      if (['png', 'jpeg', 'tiff', 'gif', 'webp'].includes(kind)) {
        if (!env.ocr || !env.drawImage) { add(name, kind, { unread: 'no-ocr' }, bytes); return; }
        const pics = await env.drawImage(bytes, kind);
        const pages = [];
        for (let i = 0; i < pics.length; i++) {                     // a failure: the file is unread (below)
          tell({ stage: 'ocr', name, page: i + 1, pages: pics.length });
          const got = answer(await env.ocr.page(pics[i], { name, page: i + 1, pages: pics.length }));
          pages.push({ n: i + 1, text: got.text, by: got.by });
        }
        add(name, kind, { pages }, bytes);
        return;
      }
      add(name, kind, { unread: 'kind' }, bytes);
    } catch (e) {
      add(name, kind, { unread: e.why || e.rar || 'damaged', error: String(e.message || e).slice(0, 200) }, bytes);
    }
  }
  for (const f of files) await one(f.name, f.bytes instanceof Uint8Array ? f.bytes : new Uint8Array(f.bytes), 0);
  return out;
}
