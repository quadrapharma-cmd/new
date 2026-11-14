// The PDF work of the workshop, with pdf-lib (MIT): what a PDF is as a file (its version, protection, fonts, pages, outline), and
// the technical changes that never touch what a page shows — cut a file into its documents, put files together, turn a page to its
// right direction, give a document its outline (bookmarks) and its title, make pictures into a PDF. A page's content is copied as it
// is, so a document of another party stays the paper it was.
import { PDFDocument, PDFName, PDFDict, PDFArray, PDFString, PDFHexString, PDFNumber, PDFRef, degrees } from 'pdf-lib';

const header = bytes => {
  const head = new TextDecoder('latin1').decode(bytes.subarray(0, 1024));
  const m = /%PDF-(\d\.\d)/.exec(head);
  return m ? m[1] : null;
};
const load = (bytes, opts = {}) => PDFDocument.load(bytes, { updateMetadata: false, ignoreEncryption: true, ...opts });

function lookup(doc, v) { return v instanceof PDFRef ? doc.context.lookup(v) : v; }
function fontEmbedded(doc, font) {
  font = lookup(doc, font);
  if (!(font instanceof PDFDict)) return true;
  const sub = font.get(PDFName.of('Subtype'))?.toString();
  if (sub === '/Type3') return true;
  if (sub === '/Type0') {
    const desc = lookup(doc, font.get(PDFName.of('DescendantFonts')));
    const first = desc instanceof PDFArray ? lookup(doc, desc.get(0)) : null;
    return first ? fontEmbedded(doc, first) : true;
  }
  const fd = lookup(doc, font.get(PDFName.of('FontDescriptor')));
  if (!(fd instanceof PDFDict)) return false;                    // the 14 standard fonts: named, not carried
  return ['FontFile', 'FontFile2', 'FontFile3'].some(k => fd.has(PDFName.of(k)));
}
function fontName(doc, font) {
  font = lookup(doc, font);
  const n = font instanceof PDFDict ? font.get(PDFName.of('BaseFont')) : null;
  return n ? n.toString().replace(/^\//, '').replace(/^[A-Z]{6}\+/, '') : '?';
}

// What the file is: {version, encrypted, pages, sizes: [{w, h, rotate}], outline, fonts: {total, missing: [names]}, title, producer, bytes}
export async function pdfInfo(bytes) {
  const out = { version: header(bytes), bytes: bytes.length, encrypted: false, pages: 0, sizes: [], outline: false, fonts: { total: 0, missing: [] }, title: '', producer: '' };
  let doc;
  try { doc = await load(bytes); } catch (e) { return { ...out, damaged: String(e.message || e).slice(0, 200) }; }
  out.encrypted = !!doc.isEncrypted;
  const catVersion = doc.catalog.get(PDFName.of('Version'));
  if (catVersion) out.version = catVersion.toString().replace(/^\//, '');
  out.pages = doc.getPageCount();
  const seen = new Set(), missing = new Set();
  for (const page of doc.getPages()) {
    const { width, height } = page.getSize();
    out.sizes.push({ w: Math.round(width), h: Math.round(height), rotate: page.getRotation().angle % 360 });
    const res = lookup(doc, page.node.Resources?.() ?? page.node.get(PDFName.of('Resources')));
    const fonts = res instanceof PDFDict ? lookup(doc, res.get(PDFName.of('Font'))) : null;
    if (fonts instanceof PDFDict) {
      for (const [, ref] of fonts.entries()) {
        const key = ref instanceof PDFRef ? ref.toString() : Math.random().toString();
        if (seen.has(key)) continue;
        seen.add(key);
        if (!fontEmbedded(doc, ref)) missing.add(fontName(doc, ref));
      }
    }
  }
  out.fonts = { total: seen.size, missing: [...missing] };
  const outlines = lookup(doc, doc.catalog.get(PDFName.of('Outlines')));
  out.outline = outlines instanceof PDFDict && outlines.has(PDFName.of('First'));
  try { out.title = doc.getTitle() || ''; out.producer = doc.getProducer() || ''; } catch { /* an odd info dictionary */ }
  return out;
}

// Pages from..to (counted from 1) as a PDF of their own.
export async function cutPdf(bytes, from, to) {
  const src = await load(bytes);
  if (src.isEncrypted) throw Object.assign(new Error('the file is protected: it cannot be cut here'), { code: 'encrypted' });
  const out = await PDFDocument.create({ updateMetadata: false });
  const idx = [];
  for (let i = from - 1; i < Math.min(to, src.getPageCount()); i++) idx.push(i);
  for (const p of await out.copyPages(src, idx)) out.addPage(p);
  return out.save({ useObjectStreams: false });
}

export async function mergePdfs(list) {
  const out = await PDFDocument.create({ updateMetadata: false });
  for (const bytes of list) {
    const src = await load(bytes);
    if (src.isEncrypted) throw Object.assign(new Error('a file is protected: it cannot be joined here'), { code: 'encrypted' });
    for (const p of await out.copyPages(src, src.getPageIndices())) out.addPage(p);
  }
  return out.save({ useObjectStreams: false });
}

// Turn pages: {index (from 0): quarter turns to add (1 = 90° clockwise)}. Only the page's /Rotate changes.
export async function turnPages(bytes, turns) {
  const doc = await load(bytes);
  if (doc.isEncrypted) throw Object.assign(new Error('the file is protected'), { code: 'encrypted' });
  doc.getPages().forEach((p, i) => { if (turns[i]) p.setRotation(degrees((p.getRotation().angle + 90 * turns[i]) % 360)); });
  return doc.save({ useObjectStreams: false });
}

const pdfText = s => (/^[\x20-\x7e]*$/.test(s) ? PDFString.of(s) : PDFHexString.fromText(s));
// The document's outline (bookmarks): [{title, page (from 1)}], one level, in order — and its title in the file's information.
export async function withOutline(bytes, items, { title } = {}) {
  const doc = await load(bytes);
  if (doc.isEncrypted) throw Object.assign(new Error('the file is protected'), { code: 'encrypted' });
  const pages = doc.getPages();
  const list = items.filter(it => it.title && it.page >= 1 && it.page <= pages.length);
  if (list.length) {
    const ctx = doc.context, root = ctx.nextRef(), refs = list.map(() => ctx.nextRef());
    list.forEach((it, i) => {
      const dict = ctx.obj({});
      dict.set(PDFName.of('Title'), pdfText(it.title));
      dict.set(PDFName.of('Parent'), root);
      dict.set(PDFName.of('Dest'), ctx.obj([pages[it.page - 1].ref, PDFName.of('XYZ'), null, null, null]));
      if (i > 0) dict.set(PDFName.of('Prev'), refs[i - 1]);
      if (i < list.length - 1) dict.set(PDFName.of('Next'), refs[i + 1]);
      ctx.assign(refs[i], dict);
    });
    const outlines = ctx.obj({});
    outlines.set(PDFName.of('Type'), PDFName.of('Outlines'));
    outlines.set(PDFName.of('First'), refs[0]);
    outlines.set(PDFName.of('Last'), refs[refs.length - 1]);
    outlines.set(PDFName.of('Count'), PDFNumber.of(list.length));
    ctx.assign(root, outlines);
    doc.catalog.set(PDFName.of('Outlines'), root);
    doc.catalog.set(PDFName.of('PageMode'), PDFName.of('UseOutlines'));
  }
  if (title) doc.setTitle(title, { showInWindowTitleBar: true });
  return doc.save({ useObjectStreams: false });
}

export async function withTitle(bytes, title) {
  const doc = await load(bytes);
  if (doc.isEncrypted) throw Object.assign(new Error('the file is protected'), { code: 'encrypted' });
  doc.setTitle(title, { showInWindowTitleBar: true });
  return doc.save({ useObjectStreams: false });
}

// Pictures (JPEG or PNG bytes) as the pages of one PDF, each page the picture's own shape at A4 width.
export async function picturesToPdf(pictures) {
  const doc = await PDFDocument.create();
  for (const { bytes, kind } of pictures) {
    const img = kind === 'png' ? await doc.embedPng(bytes) : await doc.embedJpg(bytes);
    const w = 595.28, h = (img.height / img.width) * w;
    const page = doc.addPage([w, h]);
    page.drawImage(img, { x: 0, y: 0, width: w, height: h });
  }
  return doc.save({ useObjectStreams: false });
}

export const A4 = { w: 595, h: 842 }, LETTER = { w: 612, h: 792 };
