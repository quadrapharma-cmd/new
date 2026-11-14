// Part 2, «الفحص الأول للملف», from files: the made-up dossier (tests/fixtures/dossier.mjs) as real files — PDFs with their own text
// (printed by the browser, Arabic among them), a .docx, an old .doc written by LibreOffice, packed in a ZIP inside a RAR — opened and
// read by prep/read.js, then checked. The five problems must come out of the files as they came out of the texts. (Scanned pages
// need the scan reader, which runs in the browser: tests/prep-browser.test.mjs.)
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { readFiles } from '../prep/read.js';
import { prepare } from '../prep/index.js';
import { LICENCE, SPEC, STABILITY, RECEIPTS, COA } from './fixtures/dossier.mjs';
import { wordOf } from './fixtures/word.mjs';

const require = createRequire(import.meta.url);
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'db-prep-files-'));
const TODAY = '2026-11-14';
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');

// a document's pages as a PDF with its own text, printed by the browser (Arabic lines right to left)
async function pdfOf(browser, doc) {
  const page = await browser.newPage();
  const body = doc.pages.map(p => `<section style="page-break-after:always">${p.text.split('\n').map(l =>
    `<p dir="${/[؀-ۿ]/.test(l) && !/^[A-Za-z]/.test(l) ? 'rtl' : 'ltr'}">${esc(l)}</p>`).join('')}</section>`).join('');
  await page.setContent(`<html><body style="font-family:'DejaVu Sans',sans-serif;font-size:12pt">${body}</body></html>`);
  const bytes = new Uint8Array(await page.pdf({ format: 'A4' }));
  await page.close();
  return bytes;
}
test('the made-up dossier as files — PDFs, Word old and new, a ZIP inside a RAR — read and checked: the same five problems', async () => {
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
  const { chromium } = require('playwright');
  const browser = await chromium.launch();
  let files;
  try {
    const word = wordOf(SPEC, TMP);
    // the COA and the receipts go in a ZIP, and the ZIP with the old Word specification in a RAR (as companies send them)
    const pack = path.join(TMP, 'pack');
    fs.mkdirSync(pack, { recursive: true });
    fs.writeFileSync(path.join(pack, 'coa.pdf'), await pdfOf(browser, COA));
    fs.writeFileSync(path.join(pack, 'إيصالات.pdf'), await pdfOf(browser, RECEIPTS));
    execFileSync('zip', ['-q', '-X', path.join(TMP, 'quality.zip'), 'coa.pdf', 'إيصالات.pdf'], { cwd: pack });
    const outer = path.join(TMP, 'outer');
    fs.mkdirSync(outer, { recursive: true });
    fs.copyFileSync(path.join(TMP, 'quality.zip'), path.join(outer, 'quality.zip'));
    fs.writeFileSync(path.join(outer, 'specification (old).doc'), word.doc);
    execFileSync('rar', ['a', '-idq', path.join(TMP, 'dossier.rar'), 'quality.zip', 'specification (old).doc'], { cwd: outer, env: { ...process.env, LANG: 'C.UTF-8' } });
    files = [
      { name: 'licence.pdf', bytes: await pdfOf(browser, LICENCE) },
      { name: 'stability.pdf', bytes: await pdfOf(browser, STABILITY) },
      { name: 'specification.docx', bytes: word.docx },
      { name: 'dossier.rar', bytes: fs.readFileSync(path.join(TMP, 'dossier.rar')) },
      { name: 'picture.png', bytes: new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 0]) },   // a picture's first bytes
    ];
  } finally { await browser.close(); }

  const seen = [];
  const docs = await readFiles(files, { pdfjs, onProgress: e => seen.push(e.stage) });
  assert.deepEqual(docs.map(d => d.name), ['licence.pdf', 'stability.pdf', 'specification.docx', 'dossier.rar/quality.zip/coa.pdf',
    'dossier.rar/quality.zip/إيصالات.pdf', 'dossier.rar/specification (old).doc', 'picture.png']);
  assert.deepEqual(docs.map(d => d.kind), ['pdf', 'pdf', 'docx', 'pdf', 'pdf', 'doc', 'png']);
  assert.deepEqual(docs.map(d => d.pages.length), [2, 1, 1, 1, 2, 1, 0]);
  assert.equal(docs[6].unread, 'no-ocr');                      // a picture with no scan reader here: said so, not guessed
  assert.ok(docs.slice(0, 6).every(d => !d.note && !d.unread));
  assert.ok(seen.includes('open'));
  // the Arabic receipt read from its PDF's own text, in reading order
  assert.match(docs[4].pages[0].text, /البيان: رسوم نقل تصنيع إلى Sinai Test Industries/);

  const { documents, findings } = prepare(docs, { today: TODAY });
  assert.deepEqual(documents.map(d => d.type), ['registration_licence', 'stability_approval', 'specification', 'coa', 'fee_receipt', 'specification', 'unknown']);
  const ids = findings.map(f => f.id);
  for (const id of ['manufacturer-changed', 'approved-limit-ascorbic-acid', 'form-citric-acid-d3', 'review_date-d3', 'review_date-d6', 'conditions-d1'])
    assert.ok(ids.includes(id), `${id} not found in ${ids.join(', ')}`);
  // the specification given twice (Word old and new), the same form and amount: one finding naming both
  const form = findings.filter(f => f.id.startsWith('form-'));
  assert.equal(form.length, 1);
  assert.deepEqual(form[0].evidence.map(e => e.doc), ['d1', 'd3', 'd6']);
  const maker = findings.find(f => f.id === 'manufacturer-changed');
  assert.equal(maker.level, 'red');
  assert.match(maker.detail, /إيصالات سداد رسوم «نقل تصنيع إلى Sinai Test Industries» بس/);
  // every quote is on its page, as read from the file
  const squash = s => s.replace(/\s+/g, ' ').trim();
  for (const f of findings) for (const e of f.evidence) {
    const d = docs.find(x => x.id === e.doc);
    assert.ok(squash(d.pages.find(p => p.n === e.page).text).includes(squash(e.quote)), `${f.id}: «${e.quote}» not on ${d.name} p${e.page}`);
  }
});

test('a long scanned document has its first scanned pages read, and says how many were not; a short one is read whole', async () => {
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
  const { chromium } = require('playwright');
  const browser = await chromium.launch();
  let long, short;
  try {
    const page = await browser.newPage();
    const blank = n => page.setContent(`<html><body>${'<section style="page-break-after:always">&nbsp;</section>'.repeat(n)}</body></html>`).then(() => page.pdf({ format: 'A4' }));
    long = new Uint8Array(await blank(22));
    short = new Uint8Array(await blank(3));
  } finally { await browser.close(); }
  let calls = 0;
  const env = { pdfjs, drawPdf: async () => ({}), ocr: { page: async () => { calls++; return `Scanned page text read by the scan reader ${calls}`; } } };
  const [a, b] = await readFiles([{ name: 'validation report.pdf', bytes: long }, { name: 'letter.pdf', bytes: short }], env);
  assert.equal(a.pages.length, 22);
  assert.equal(a.pages.filter(p => p.by === 'ocr').length, 4);
  assert.equal(a.note, 'long:18');
  assert.equal(b.pages.filter(p => p.by === 'ocr').length, 3);
  assert.equal(b.note, undefined);
  assert.equal(calls, 7);
});
