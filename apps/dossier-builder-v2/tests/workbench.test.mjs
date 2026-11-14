// The workbench (workbench/): the page where Claude works with the program's tools, in a real browser. claude.ai's `sample` is
// stood in for by a function that calls the page's tools the way Claude does; everything else is the page as published.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { fakeClaude } from './helpers/fake-claude.js';

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DIST = path.join(ROOT, 'dist');

async function serve() {
  if (!fs.existsSync(path.join(DIST, 'knowledge.json'))) await (await import('../tools/build.mjs')).build({ quiet: true });
  await (await import('../workbench/build.mjs')).buildWorkbench();
  const page = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>${fs.readFileSync(path.join(DIST, 'workbench-artifact.html'), 'utf8')}</body></html>`;
  const server = http.createServer((req, res) => {
    const url = req.url.split('?')[0];
    if (url === '/' || url === '/index.html') { res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }); return res.end(page); }
    if (url === '/workbench/pdf.worker.min.js') { res.writeHead(200, { 'content-type': 'text/javascript' }); return res.end(fs.readFileSync(path.join(DIST, 'workbench', 'pdf.worker.min.js'))); }
    res.writeHead(404); res.end();
  });
  await new Promise(ok => server.listen(0, '127.0.0.1', ok));
  return server;
}

async function open({ claude = true, mode = 'tools', width = 1280, theme = 'light' } = {}) {
  const { chromium } = require('playwright');
  const server = await serve();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width, height: 900 }, colorScheme: theme });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  if (claude) await page.addInitScript(fakeClaude, { mode });
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  await page.waitForFunction(() => document.querySelectorAll('#files tbody tr').length > 0);
  return { page, errors, close: async () => { await browser.close(); server.close(); } };
}

test('the workbench opens with the made-up certificate read in the browser, and Claude ready', { timeout: 120000 }, async () => {
  const { page, errors, close } = await open();
  try {
    const row = await page.textContent('#files tbody tr');
    assert.match(row, /f1/);
    assert.match(row, /pdf/);
    assert.match(row, /مثال خيالي/);
    assert.equal((await page.textContent('#files tbody tr td:nth-child(4)')).trim(), '2');
    await page.waitForFunction(() => /جاهز/.test(document.querySelector('#claude-status').textContent));
    assert.deepEqual(errors, []);
  } finally { await close(); }
});

test('Claude works with the tools in the page: every step shown, a fact kept only with the words on its page', { timeout: 120000 }, async () => {
  const { page, errors, close } = await open();
  try {
    await page.fill('#task', 'سجّل رقم التشغيلة من شهادة التحليل');
    await page.click('#send');
    await page.waitForFunction(() => /خلّص/.test(document.querySelector('#claude-status').textContent));
    assert.match(await page.textContent('#answer'), /TP-24A117 من صفحة 1\. \(الصفحة اتقرت\)/);
    const steps = await page.$$eval('#steps li', lis => lis.map(li => [li.className, li.querySelector('.t').textContent]));
    assert.deepEqual(steps.map(s => s[1]), ['ملفات الملف', 'نص صفحة', 'سجّل معلومة', 'سجّل معلومة']);
    assert.deepEqual(steps.map(s => s[0]), ['', '', 'no', '']);
    assert.match(await page.textContent('#steps li.no'), /not on page 1/);
    const facts = await page.textContent('#facts');
    assert.match(facts, /TP-24A117/);
    assert.match(facts, /صفحة 1: «Batch TP-24A117»/);
    assert.match((await page.evaluate(() => window.__prompts[0])), /Dossier Builder/);
    await page.click('#undo');
    assert.equal(await page.$$eval('#facts li', r => r.length), 0);
    assert.equal(await page.isVisible('#facts-empty'), true);
    assert.deepEqual(errors, []);
  } finally { await close(); }
});

test('the viewer\'s own files replace the example; their kind comes from the content', { timeout: 120000 }, async () => {
  const { page, errors, close } = await open();
  try {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wb-'));
    fs.writeFileSync(path.join(dir, 'commitment.pdf'), 'Stability commitment for Testaphen: 36 months.');   // a text file named .pdf
    await page.setInputFiles('#pick', path.join(dir, 'commitment.pdf'));
    await page.waitForFunction(() => document.querySelectorAll('#files tbody tr').length === 1 && /commitment/.test(document.querySelector('#files tbody').textContent));
    assert.match(await page.textContent('#files tbody tr'), /text/);
    assert.equal(await page.isVisible('#use-example'), true);
    assert.deepEqual(errors, []);
  } finally { await close(); }
});

test('without Claude the page says so and still reads the files', { timeout: 120000 }, async () => {
  const { page, errors, close } = await open({ claude: false });
  try {
    await page.waitForFunction(() => /مش متاح/.test(document.querySelector('#claude-status').textContent));
    await page.fill('#task', 'اعرضلي الملفات');
    await page.click('#send');
    assert.match(await page.textContent('#claude-status'), /افتح الصفحة على claude\.ai/);
    assert.deepEqual(errors, []);
  } finally { await close(); }
});

test('a view that cannot run page tools: the program reads the files for Claude and keeps only facts whose words are on their page', { timeout: 120000 }, async () => {
  for (const mode of ['no-tools', 'refuse-tools']) {
    const { page, errors, close } = await open({ mode });
    try {
      await page.waitForFunction(() => /جاهز/.test(document.querySelector('#claude-status').textContent));
      await page.fill('#task', 'سجّل رقم التشغيلة وتاريخ الانتهاء');
      await page.click('#send');
      await page.waitForFunction(() => /خلّص/.test(document.querySelector('#claude-status').textContent));
      assert.match(await page.textContent('#answer'), /سجّلت رقم التشغيلة من نص الصفحة/, mode);
      const facts = await page.textContent('#facts');
      assert.match(facts, /TP-24A117/, mode);
      assert.doesNotMatch(facts, /2029/, `${mode}: a date that is not on the page is not kept`);
      const steps = await page.$$eval('#steps li .t', l => l.map(x => x.textContent));
      assert.ok(steps.some(t => /البرنامج: نص صفحة/.test(t)), `${mode}: ${steps}`);
      assert.deepEqual(errors, [], mode);
    } finally { await close(); }
  }
});

test('a failed call says why in Arabic and keeps the code for the operator', { timeout: 120000 }, async () => {
  const { page, close } = await open({ mode: 'error' });
  try {
    await page.waitForFunction(() => /جاهز/.test(document.querySelector('#claude-status').textContent));
    await page.fill('#task', 'اعرضلي الملفات');
    await page.click('#send');
    await page.waitForFunction(() => /مشكلة مؤقتة/.test(document.querySelector('#claude-status').textContent));
    assert.match(await page.textContent('#claude-status .detail'), /upstream_error: connection dropped/);
    assert.equal(await page.isEnabled('#send'), true);
  } finally { await close(); }
});
