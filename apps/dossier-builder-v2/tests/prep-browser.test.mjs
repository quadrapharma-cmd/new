// Part 2, «الفحص الأول للملف», the page itself (prep/build.mjs → dist/prep-site) in Chromium, under a content security policy like
// the claude.ai artifact frame's: the made-up dossier as a company sends it — the EDA papers scanned (pictures, no text), the
// specification as Word inside a RAR, the certificate in a ZIP — chosen with the page's own button, read (the scans by the page's
// scan reader, in WebAssembly), checked; the five problems must come out with the words on their pages. And a view that forbids
// WebAssembly: the page says the scan reader cannot run there and still checks what has text.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { buildPrep } from '../prep/build.mjs';
import { CSP, WASM_CSP as WASM } from '../tools/check-published.mjs';   // the frame's policy, with and without WebAssembly
import { madeUpDossier } from './fixtures/scans.mjs';

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SITE = path.join(ROOT, 'dist', 'prep-site');
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'db-prep-browser-'));
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.json': 'application/json', '.txt': 'text/plain; charset=utf-8' };

function serve(csp) {
  const server = http.createServer((req, res) => {
    const url = decodeURIComponent(req.url.split('?')[0]);
    const file = path.join(SITE, url === '/' ? 'index.html' : url.slice(1));
    if (!file.startsWith(SITE) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream', 'content-security-policy': csp });
    res.end(fs.readFileSync(file));
  });
  return new Promise(ok => server.listen(0, '127.0.0.1', () => ok(server)));
}

let files = null;
const dossier = async browser => files || (files = await madeUpDossier(browser, path.join(TMP, 'dossier')));

async function runPage(csp) {
  const { chromium } = require('playwright');
  const browser = await chromium.launch();
  const server = await serve(csp);
  try {
    const chosen = await dossier(browser);
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    await page.setInputFiles('#pick-files', chosen);
    await page.waitForFunction(() => window.__prep, null, { timeout: 300000 });
    const result = await page.evaluate(() => window.__prep);
    const shown = { status: await page.textContent('#status'), findings: await page.locator('#findings > li').count(),
                    ctd: await page.locator('.ctd').first().evaluate(el => getComputedStyle(el).direction) };
    // at phone width the page does not scroll sideways
    await page.setViewportSize({ width: 390, height: 800 });
    shown.overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    return { result, shown, errors };
  } finally { server.close(); await browser.close(); }
}

test('the page reads the made-up scanned dossier — scans, Word in a RAR, a PDF in a ZIP — and finds the five problems', { timeout: 600000 }, async () => {
  await buildPrep();
  const { result, shown, errors } = await runPage(WASM);
  assert.deepEqual(errors, []);
  assert.equal(result.ocrFailed, null);
  const { documents, findings, docs } = result;
  assert.deepEqual(documents.map(d => [d.name, d.type]), [
    ['licence (scan).pdf', 'registration_licence'], ['stability (scan).pdf', 'stability_approval'], ['receipts (scan).pdf', 'fee_receipt'],
    ['specification.rar/specification.docx', 'specification'], ['coa.zip/coa.pdf', 'coa']]);
  // the scans were read by the scan reader, every page
  for (const d of docs.slice(0, 3)) assert.ok(d.pages.every(p => p.by === 'ocr' && p.text.trim()), d.name);
  const ids = findings.map(f => f.id);
  for (const id of ['manufacturer-changed', 'approved-limit-ascorbic-acid', 'form-citric-acid-d4', 'review_date-d4', 'conditions-d1'])
    assert.ok(ids.includes(id), `${id} not in ${ids.join(', ')}`);
  const maker = findings.find(f => f.id === 'manufacturer-changed');
  assert.equal(maker.level, 'red');
  assert.match(maker.detail, /Delta Test Manufacturing/);
  assert.match(maker.detail, /Sinai Test/);
  assert.equal(findings.find(f => f.id === 'conditions-d1').evidence.length, 3);
  const squash = s => s.replace(/\s+/g, ' ').trim();
  for (const f of findings) for (const e of f.evidence) {
    const d = docs.find(x => x.id === e.doc);
    assert.ok(squash(d.pages.find(p => p.n === e.page).text).includes(squash(e.quote)), `${f.id}: «${e.quote}» not on ${d.name} p${e.page}`);
  }
  assert.match(shown.status, /خلص في \d+ ث/);
  assert.equal(shown.findings, findings.length);
  assert.equal(shown.ctd, 'ltr');                                   // «3.2.P.5.1» reads left to right inside the Arabic page
  assert.ok(shown.overflow <= 0, `the page scrolls sideways by ${shown.overflow}px at 390 wide`);
});

test('a view that forbids WebAssembly: the page says the scan reader cannot run, and checks what has text', { timeout: 600000 }, async () => {
  if (!fs.existsSync(path.join(SITE, 'index.html'))) await buildPrep();
  const { result, shown, errors } = await runPage(CSP);
  assert.deepEqual(errors, []);
  assert.equal(result.ocrFailed, 'wasm');
  assert.match(shown.status, /قارئ المسح ماقدرش يشتغل هنا/);
  const scans = result.docs.slice(0, 3);
  assert.ok(scans.every(d => d.note === 'no-ocr'), JSON.stringify(scans.map(d => d.note)));
  assert.deepEqual(result.documents.slice(3).map(d => d.type), ['specification', 'coa']);   // the Word file and the PDF with text are still read
  assert.ok(result.findings.some(f => f.id === 'review_date-d4'));
});
