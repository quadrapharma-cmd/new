// Every file of a dossier opened by its content (never its name) and read page by page: a PDF's own text where it has one, a scanned
// page (or a picture) read by the page's scan reader when one is given (prep/ocr.js, in the browser), Word files old and new, and
// the files inside ZIP and RAR archives, as deep as archives go in archives. What cannot be read says why; nothing is guessed.
//   readFiles(files: [{name, bytes}], env) → [{id, name, kind, pages: [{n, text, by: 'text'|'ocr'|'word'|'plain'}], unread?, note?}]
//   env: {pdfjs, ocr?: {page(canvas) → text}, drawPdf?(page) → canvas, drawImage?(bytes, kind) → canvases, onProgress?, unrar?}
import { kindOf } from '../agent/workspace.js';
import { pageTextOf } from '../core/pdftext.js';
import { unzip } from './zip.js';
import { cfb, docText, docxText } from './office.js';
import { core as rarCore } from './rar.js';

// A PDF page with fewer letters than this in its own text is a scan (a stamp, a page number or a header line is not a text layer).
export const SCANNED = 40;
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

async function pdfPages(bytes, env, tell) {
  const task = env.pdfjs.getDocument({ data: bytes.slice(), isEvalSupported: false, useSystemFonts: false });
  const doc = await task.promise;
  try {
    const pages = [];
    let scans = 0;
    for (let n = 1; n <= doc.numPages; n++) {
      const page = await doc.getPage(n);
      const text = pageTextOf(await page.getTextContent());
      if (letters(text) >= SCANNED || !env.ocr || !env.drawPdf) {
        if (letters(text) < SCANNED) scans++;
        pages.push({ n, text, by: 'text' });
      } else {
        tell({ stage: 'ocr', page: n, pages: doc.numPages });
        const canvas = await env.drawPdf(page);
        const read = await env.ocr.page(canvas);
        pages.push({ n, text: letters(read) > letters(text) ? read : text, by: 'ocr' });
      }
      page.cleanup();
    }
    return { pages, scans };
  } finally { await task.destroy(); }
}

export async function readFiles(files, env = {}) {
  const out = [];
  const tell = e => { try { env.onProgress?.(e); } catch { /* the page's progress line only */ } };
  const add = (name, kind, extra) => { const d = { id: `d${out.length + 1}`, name, kind, pages: [], ...extra }; out.push(d); return d; };
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
        const { pages, scans } = await pdfPages(bytes, env, e => tell({ ...e, name }));
        const d = add(name, kind, { pages });
        if (scans) d.note = scans === pages.length ? 'no-ocr' : `no-ocr:${scans}`;
        return;
      }
      if (kind === 'doc') { add(name, kind, { pages: docText(bytes) }); return; }
      if (kind === 'docx') { add(name, kind, { pages: await docxText(bytes) }); return; }
      if (kind === 'text') { add(name, kind, { pages: [{ n: 1, text: new TextDecoder().decode(bytes), by: 'plain' }] }); return; }
      if (['png', 'jpeg', 'tiff', 'gif', 'webp'].includes(kind)) {
        if (!env.ocr || !env.drawImage) { add(name, kind, { unread: 'no-ocr' }); return; }
        const pics = await env.drawImage(bytes, kind);
        const pages = [];
        for (let i = 0; i < pics.length; i++) { tell({ stage: 'ocr', name, page: i + 1, pages: pics.length }); pages.push({ n: i + 1, text: await env.ocr.page(pics[i]), by: 'ocr' }); }
        add(name, kind, { pages });
        return;
      }
      add(name, kind, { unread: 'kind' });
    } catch (e) {
      add(name, kind, { unread: e.why || e.rar || 'damaged', error: String(e.message || e).slice(0, 200) });
    }
  }
  for (const f of files) await one(f.name, f.bytes instanceof Uint8Array ? f.bytes : new Uint8Array(f.bytes), 0);
  return out;
}
