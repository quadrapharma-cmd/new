// Part 2, the desktop workshop as the owner opens it: dist/workshop/index.html from the disk (file://) in Chromium, the made-up
// dossier as a company sends it (the EDA papers scanned, the specification as Word inside a RAR, the certificate in a ZIP). By the
// page's own buttons: a new Egyptian dossier, run by itself — read (the scan reader on the computer; or Claude through a key, with a
// local stand-in for the API), cut, typed, placed, checked (the five problems found again), the company papers drafted, «needs you»
// acted on (a document placed, a finding accepted with its reason), the ready folder downloaded with its report — kept across a
// reload, saved as one file and opened again; Claude asked with the workshop's tools; a wrong key refused by the real API; the Word
// and PDF programs opened from the page, a change saved back, a Word file made a PDF. Every name and number is made up.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { buildWorkshop } from '../workshop/build.mjs';
import { madeUpDossier, LICENCE, STABILITY, RECEIPTS } from './fixtures/scans.mjs';
import { fakeApi } from './helpers/fake-api.mjs';
import { unzip } from '../prep/zip.js';

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const INDEX = `file://${path.join(ROOT, 'dist', 'workshop', 'index.html')}`;
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'db-workshop-'));
const GPU = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
const READINGS = Object.fromEntries([['licence (scan).pdf', LICENCE], ['stability (scan).pdf', STABILITY], ['receipts (scan).pdf', RECEIPTS]]
  .flatMap(([name, doc]) => doc.pages.map(p => [`${name}|${p.n}`, p.text])));
const FIVE = ['cross-manufacturer-changed', 'cross-approved-limit-ascorbic-acid', 'cross-form-citric-acid', 'cross-review_date', 'cross-conditions'];

let built = null;
const ensureBuilt = async () => built || (built = await buildWorkshop());
let files = null;
async function dossierFiles(browser) { return files || (files = await madeUpDossier(browser, path.join(TMP, 'dossier'))); }

async function open(browser, { context = null, init = null } = {}) {
  const ctx = context || await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true, ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  if (init) await page.addInitScript(init.fn, init.arg);
  await page.goto(INDEX);
  await page.waitForSelector('[data-act="new"]', { timeout: 30000 });
  return { ctx, page, errors };
}
async function newDossier(page, chosen) {
  await page.click('[data-act="new"]');
  await page.setInputFiles('#wiz-files', chosen);
  await page.waitForFunction(n => document.querySelector('.picked')?.textContent.includes(String(n)), chosen.length);
  await page.click('[data-act="wiz-start"][data-auto="1"]');
  await page.waitForFunction(() => window.__workshopDone || window.__workshopError, null, { timeout: 600000 });
  assert.equal(await page.evaluate(() => window.__workshopError || null), null);
  return page.evaluate(() => JSON.parse(JSON.stringify(window.__workshop.state.d)));
}
const crossIds = page => page.evaluate(() => window.__workshop.state.findings.filter(f => f.kind === 'cross').map(f => f.id));

test('the workshop opened from the disk prepares the made-up dossier by itself with the scan reader on the computer', { timeout: 900000 }, async () => {
  await ensureBuilt();
  const { chromium } = require('playwright');
  const browser = await chromium.launch();
  try {
    const chosen = await dossierFiles(browser);
    const { ctx, page, errors } = await open(browser);
    const d = await newDossier(page, chosen);
    const place = n => d.docs.find(x => x.name === n)?.place;
    assert.equal(place('licence (scan).pdf'), 'EG-EDA/M1-04');
    assert.equal(place('stability (scan).pdf'), 'EG-EDA/P-16');
    assert.equal(place('specification.rar/specification.docx'), 'EG-EDA/P-09');
    assert.equal(place('coa.zip/coa.pdf'), 'EG-EDA/P-11');
    assert.ok(d.docs.filter(x => x.name.includes('(scan)')).every(x => x.pages.every(p => p.by === 'ocr')), 'the scans read on the computer');
    const ids = await crossIds(page);
    for (const id of FIVE) assert.ok(ids.some(x => x.startsWith(id)), `${id} not in ${ids.join(' ')}`);
    const drafts = d.docs.filter(x => x.madeBy === 'program').map(x => x.place).sort();
    assert.deepEqual(drafts, ['EG-EDA/M1-01', 'EG-EDA/M1-31', 'EG-EDA/M1-32', 'EG-EDA/M1-43', 'EG-EDA/M1-44']);
    assert.equal(d.name, 'Testamin powder for oral solution');                     // named from its licence
    // «needs you»: the receipts the rules could not place, put in their place from the list
    await page.click('[data-act="tab"][data-id="needs"]');
    const receipts = d.docs.find(x => x.name === 'receipts (scan).pdf');
    assert.ok(await page.locator(`#need-place-${receipts.id}`).count(), 'the receipts are in «needs you»');
    await page.selectOption(`#need-place-${receipts.id} select[data-act="move"]`, 'EG-EDA/M1-03');
    await page.waitForFunction(id => window.__workshop.state.d.docs.find(x => x.id === id).placeBy === 'you', receipts.id);
    // a finding accepted, with its reason
    await page.click('[data-act="tab"][data-id="needs"]');
    const item = page.locator('#need-cross-manufacturer-changed');
    await item.locator('[data-act="need-accept"]').click();
    await item.locator('.accept textarea').fill('the transfer approval was requested; its receipt is attached');
    await item.locator('[data-act="accept-ok"]').click();
    await page.waitForFunction(() => window.__workshop.state.d.decisions['cross-manufacturer-changed']);
    // the rule card of a place
    await page.click('[data-act="tab"][data-id="board"]');
    await page.click('[data-act="place"][data-id="EG-EDA/M1-37"]');
    const card = await page.textContent('#drawer');
    assert.match(card, /شهادة GMP/);
    assert.match(card, /NP\.CAPP\.065/);
    await page.click('[data-act="drawer-close"]');
    // the ready folder
    await page.click('[data-act="tab"][data-id="ready"]');
    const [download] = await Promise.all([page.waitForEvent('download'), page.click('[data-act="ready-zip"]')]);
    const zip = new Uint8Array(fs.readFileSync(await download.path()));
    const names = (await unzip(zip)).files.map(f => f.name);
    assert.ok(names.includes('Testamin powder for oral solution/Module 1/1.1.4 Action Letter & Name Approval/1.1.4 Action Letter & Name Approval.pdf'), names.join('\n'));
    assert.ok(names.some(n => /Module 1\/1\.1\.3 .*\.pdf$/.test(n)), 'the receipts in 1.1.3');
    assert.ok(names.some(n => /Module 1\/1\.1\.1 .*\.docx$/.test(n)), 'the Annex I draft');
    const report = new TextDecoder().decode((await unzip(zip)).files.find(f => f.name.endsWith('تقرير الجاهزية.html')).bytes);
    assert.match(report, /the transfer approval was requested/);
    // at phone width the page does not scroll sideways
    await page.setViewportSize({ width: 390, height: 800 });
    for (const tab of ['board', 'docs', 'data', 'needs', 'ready']) {
      await page.click(`[data-act="tab"][data-id="${tab}"]`);
      const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      assert.ok(over <= 0, `${tab} scrolls sideways by ${over}px at 390 wide`);
    }
    // kept across a reload; saved as one file and opened again
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.reload();
    await page.waitForSelector(`[data-act="open"][data-id="${d.id}"]`);
    const [copy] = await Promise.all([page.waitForEvent('download'), page.click(`[data-act="export"][data-id="${d.id}"]`)]);
    await page.click(`[data-act="open"][data-id="${d.id}"]`);
    await page.waitForFunction(() => window.__workshop.state.view === 'dossier');
    assert.equal(await page.evaluate(() => window.__workshop.state.d.docs.length), d.docs.length);
    const fresh = await open(browser);
    await fresh.page.setInputFiles('#import-file', await copy.path());
    await fresh.page.waitForFunction(() => window.__workshop.state.view === 'dossier');
    assert.equal(await fresh.page.evaluate(() => window.__workshop.state.d.docs.length), d.docs.length);
    assert.deepEqual(await crossIds(fresh.page), await crossIds(page));
    assert.deepEqual([...errors, ...fresh.errors], []);
    await fresh.ctx.close();
    await ctx.close();
  } finally { await browser.close(); }
});

test('with a key, Claude reads the scans as pictures, places what the rules cannot, and answers with the workshop\'s tools', { timeout: 900000 }, async () => {
  await ensureBuilt();
  const { chromium } = require('playwright');
  const api = await fakeApi({ pages: READINGS, places: { receipts: 'EG-EDA/M1-03' } });
  const browser = await chromium.launch();
  try {
    const chosen = await dossierFiles(browser);
    const { ctx, page, errors } = await open(browser, { init: { fn: base => { window.__workshopApiBase = base; window.__workshopRateWait = 50; }, arg: api.url } });
    await page.click('#claude-chip');
    await page.fill('#api-key', 'sk-ant-wrong');
    await page.click('[data-act="key-test"]');
    await page.waitForSelector('#settings .status.bad');
    assert.match(await page.textContent('#settings .status.bad'), /المفتاح مش شغال/);
    await page.fill('#api-key', 'sk-ant-test-key');
    await page.click('[data-act="key-test"]');
    await page.waitForSelector('#settings .status.ok');
    // the models the key may use, the newest first within a family (the stand-in's two are of no family the page ranks)
    assert.deepEqual(await page.$$eval('#api-model option', o => o.map(x => x.value)), ['stand-in-small', 'stand-in-large']);
    await page.click('[data-act="settings-close"]');
    const d = await newDossier(page, chosen);
    const scans = d.docs.filter(x => x.name.includes('(scan)'));
    assert.ok(scans.every(x => x.pages.every(p => p.by === 'claude')), 'every scanned page read by Claude');
    const receipts = d.docs.find(x => x.name === 'receipts (scan).pdf');
    assert.equal(receipts.place, 'EG-EDA/M1-03');
    assert.equal(receipts.placeBy, 'claude');
    const ids = await crossIds(page);
    for (const id of FIVE) assert.ok(ids.some(x => x.startsWith(id)), `${id} not in ${ids.join(' ')}`);
    const pictures = api.calls.filter(c => c.images);
    assert.equal(pictures.length, 5);
    assert.ok(pictures.every(c => c.images === 2 && c.effort === 'low' && c.browser === 'true'));
    await page.click('[data-act="tab"][data-id="ask"]');
    await page.fill('#ask-text', 'كام مستند في الملف؟');
    await page.click('#ask-form button[type="submit"]');
    await page.waitForFunction(() => !window.__workshop.state.ask.busy && window.__workshop.state.ask.text);
    assert.match(await page.textContent('#ask-answer'), /في الملف \d+ مستندات/);
    assert.deepEqual(await page.$$eval('.tsteps li', l => l.map(x => x.textContent.trim().split(' ')[0])), ['list_documents']);
    assert.deepEqual(errors, []);
    await ctx.close();
  } finally { await browser.close(); api.server.close(); }
});

test('a wrong key is refused by the real API from a page opened from the disk, and the page says so', { timeout: 120000 }, async t => {
  await ensureBuilt();
  const { chromium } = require('playwright');
  const browser = await chromium.launch();
  try {
    const { ctx, page } = await open(browser);
    await page.click('#claude-chip');
    await page.fill('#api-key', 'sk-ant-api03-made-up-key-for-a-test');
    await page.click('[data-act="key-test"]');
    await page.waitForFunction(() => window.__workshop.state.claude.status !== 'checking', null, { timeout: 60000 });
    const { code } = await page.evaluate(() => window.__workshop.state.claude);
    if (code === 'network') { t.skip('the API cannot be reached from here'); return; }
    assert.equal(code, 'key_invalid');
    assert.match(await page.textContent('#settings .status.bad'), /المفتاح مش شغال/);
    await ctx.close();
  } finally { await browser.close(); }
});

test('the Word and PDF programs open from the page: a change saved there comes back, a Word file is made a PDF', { timeout: 900000 }, async t => {
  const b = await ensureBuilt();
  if (!b.programs.includes('wordcraft') || !b.programs.includes('pdfcraft')) { t.skip('the programs are not built here (tools/craft/build.mjs)'); return; }
  const { chromium } = require('playwright');
  const browser = await chromium.launch({ args: GPU });
  try {
    const chosen = await dossierFiles(browser);
    const { ctx, page, errors } = await open(browser);
    const d = await newDossier(page, chosen);
    await page.click('[data-act="tab"][data-id="docs"]');
    const annex = d.docs.find(x => x.place === 'EG-EDA/M1-01').id;
    await page.click(`[data-act="doc-program"][data-id="${annex}"]`);
    await page.waitForFunction(() => !document.getElementById('program').hidden);
    const opened = await page.evaluate(async () => { for (let i = 0; i < 240; i++) { try { const r = await window.__workshop.programs.inspect('wordcraft'); if (r?.blocks) return r.blocks.map(x => x.text).join('\n'); } catch { /* not yet */ } await new Promise(r => setTimeout(r, 500)); } return ''; });
    assert.match(opened, /Annex I — Application form/);                   // the program's paragraphs (the tables' cells are not in them)
    assert.match(opened, /نتقدم لسيادتكم بملف التسجيل/);
    await page.evaluate(async () => { const p = window.__workshop.programs; await p.execute('wordcraft', 'text.insert', { text: 'Edited in the Word program. ' }); await p.execute('wordcraft', 'file.save', {}); });
    await page.waitForFunction(id => window.__workshop.state.d.docs.find(x => x.id === id).editedBy === 'you', annex, { timeout: 60000 });
    assert.match(await page.evaluate(id => window.__workshop.state.d.docs.find(x => x.id === id).pages.map(p => p.text).join(' '), annex), /Edited in the Word program/);
    await page.click('[data-act="program-close"]');
    const spec = d.docs.find(x => x.name === 'specification.rar/specification.docx').id;
    await page.click(`[data-act="word-pdf"][data-id="${spec}"]`);
    await page.waitForFunction(id => !!window.__workshop.state.d.docs.find(x => x.id === id).pdf, spec, { timeout: 240000 });
    assert.ok(!(await page.evaluate(() => window.__workshop.state.findings.map(f => f.id))).includes(`not-pdf-${spec}`), 'the Word file made a PDF is no longer a finding');
    const coa = d.docs.find(x => x.name === 'coa.zip/coa.pdf').id;
    await page.click('[data-act="tab"][data-id="docs"]');
    await page.click(`[data-act="doc-program"][data-id="${coa}"]`);
    const pdf = await page.evaluate(async () => { for (let i = 0; i < 240; i++) { try { const r = await window.__workshop.programs.inspect('pdfcraft'); if (r?.active?.doc) return r.active; } catch { /* not yet */ } await new Promise(r => setTimeout(r, 500)); } return null; });
    assert.ok(pdf, 'the PDF program has the certificate open');
    assert.deepEqual(errors, []);
    await ctx.close();
  } finally { await browser.close(); }
});
