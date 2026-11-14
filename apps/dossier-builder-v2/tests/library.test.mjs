// Part 1b: the library, driven in a real browser the way a person uses it — desktop and phone, Arabic and English.
// Screenshots go to $SHOTS when it is set.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { build } from '../tools/build.mjs';
import { ROOT } from '../tools/load.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const PAGE = 'file://' + path.join(ROOT, 'dist', 'library', 'index.html');
const SHOTS = process.env.SHOTS || '';

let browser;
let data;
test.before(async () => {
  ({ data } = await build({ quiet: true }));
  browser = await chromium.launch();
});
test.after(async () => { await browser?.close(); });

async function open(hash = '', opts = {}) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, ...opts });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/fonts\.(googleapis|gstatic)/.test(m.text())) errors.push(m.text()); });
  await page.goto(PAGE + hash);
  await page.waitForSelector('#main h1');
  return { page, ctx, errors };
}
const shot = async (page, name) => { if (SHOTS) { fs.mkdirSync(SHOTS, { recursive: true }); await page.screenshot({ path: path.join(SHOTS, name + '.png') }); } };
const overflow = page => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

test('opens in Arabic, right to left, with every authority and the right counts', async () => {
  const { page, ctx, errors } = await open();
  assert.equal(await page.evaluate(() => document.documentElement.dir), 'rtl');
  assert.equal(await page.title(), 'Dossier Builder Library');
  assert.equal(await page.locator('.auth').count(), data.authorities.length);
  const count = v => page.locator(`.rail a[href="#${v}"] .n`).innerText();
  assert.equal(await count('sources'), String(data.sources.length));
  assert.equal(await count('requirements'), String(data.requirements.length));
  assert.equal(await count('rules'), String(data.rules.length));
  assert.equal(await count('variations'), String(data.variations.items.length));
  await shot(page, '01-home-ar');
  assert.deepEqual(errors, []);
  await ctx.close();
});

test('a search in Arabic finds the item, the item shows its source, and the source lists the items that rest on it', async () => {
  const { page, ctx, errors } = await open();
  await page.fill('#q', 'نموذج الطلب');
  await page.waitForFunction(() => document.querySelector('#main h1')?.textContent.includes('نتايج'));
  const first = page.locator('main .row').first();
  assert.match(await first.innerText(), /1\.1\.1/);
  await first.click();
  const detail = page.locator('#detail');
  await detail.waitFor();
  assert.match(await detail.innerText(), /NP\.CAPP\.065/);
  assert.match(await detail.innerText(), /Annex I/);
  await shot(page, '02-search-detail-ar');
  await detail.locator('.cite a').first().click();
  await page.waitForFunction(() => location.hash === '#s-eda-np-capp-065-v5');
  assert.match(await detail.locator('.used').innerText(), /1\.1\.1/);
  assert.deepEqual(errors, []);
  await ctx.close();
});

test('a guideline code and a section number are found too', async () => {
  const { page, ctx } = await open();
  await page.fill('#q', 'GL.CAPP.024');
  await page.waitForSelector('main a[href="#s-eda-gl-capp-024-v4"]');
  await page.fill('#q', '3.2.P.8');
  await page.waitForFunction(() => [...document.querySelectorAll('main .row .k')].some(k => k.textContent.trim() === '3.2.P.8'));
  await ctx.close();
});

test('a link to an entry opens it directly', async () => {
  const { page, ctx, errors } = await open('#r-EG-EDA-BE-01');
  const d = page.locator('#detail');
  await d.waitFor();
  const rule = data.rules.find(r => r.id === 'EG-EDA/BE-01');
  assert.match(await d.locator('h1').innerText(), new RegExp(rule.title.ar.slice(0, 8)));
  assert.ok(await d.locator('.cite').count() >= 1);
  await page.click('#closeDetail');
  assert.equal(await d.isHidden(), true);
  assert.deepEqual(errors, []);
  await ctx.close();
});

test('every entry of every kind opens without an error', async () => {
  const { page, ctx, errors } = await open();
  const result = await page.evaluate(() => {
    const links = [...new Set([...document.querySelectorAll('a[href^="#"]')].map(a => a.getAttribute('href')))];
    return links.length;
  });
  assert.ok(result > 5);
  const bad = await page.evaluate(async ({ sources }) => {
    const failed = [];
    const hashes = sources.map(id => '#s-' + id);
    // Move to a link and wait until the page has answered it.
    const go = h => (location.hash === h ? Promise.resolve()
      : new Promise(r => { window.addEventListener('hashchange', () => setTimeout(r, 0), { once: true }); location.hash = h; }));
    // every record's link: read them from each list view
    for (const v of ['requirements', 'rules', 'variations', 'documents', 'countries', 'ectd']) {
      await go('#' + v);
      if (v === 'requirements') {
        // Each click redraws the list, so find each set's chip afresh.
        for (const id of [...document.querySelectorAll('[data-set]')].map(c => c.dataset.set).filter(Boolean)) {
          document.querySelector(`[data-set="${id}"]`).click();
          hashes.push(...[...document.querySelectorAll('main a.row')].map(a => a.getAttribute('href')));
        }
      } else hashes.push(...[...document.querySelectorAll('main a.row')].map(a => a.getAttribute('href')));
    }
    const unique = [...new Set(hashes)];
    if (unique.length !== hashes.length) failed.push(`${hashes.length - unique.length} links listed twice`);
    for (const h of unique) {
      await go(h);
      const d = document.getElementById('detail');
      if (d.hidden || !d.querySelector('h1') || !d.querySelector('h1').textContent.trim()) failed.push(h);
    }
    return { failed, count: unique.length };
  }, { sources: data.sources.map(s => s.id) });
  assert.deepEqual(bad.failed, []);
  const records = data.requirements.length + data.rules.length + data.variations.items.length + data.doctypes.items.length
    + data.countries.items.length + data.ectd.index.length;
  assert.equal(bad.count, data.sources.length + records);
  assert.deepEqual(errors, []);
  await ctx.close();
});

test('English: left to right, the words change, and the choice is kept', async () => {
  const { page, ctx, errors } = await open('#sources');
  await page.click('#lang');
  assert.equal(await page.evaluate(() => document.documentElement.dir), 'ltr');
  assert.equal(await page.locator('#main h1').innerText(), 'Sources');
  await page.click('main a[href="#s-eda-np-capp-065-v5"]');
  await page.locator('#detail').waitFor();
  await shot(page, '03-source-en');
  await page.reload();
  await page.waitForSelector('#main h1');
  assert.equal(await page.evaluate(() => document.documentElement.lang), 'en');
  assert.deepEqual(errors, []);
  await ctx.close();
});

test('the authority filter narrows every section', async () => {
  const { page, ctx } = await open('#requirements');
  await page.click('.rail button[data-auth="US-FDA"]');
  const sets = await page.locator('[data-set]').evaluateAll(cs => cs.map(c => c.dataset.set).filter(Boolean));
  assert.deepEqual(sets, ['us-fda-m1']);
  await page.click('.rail a[href="#sources"]');
  await page.waitForFunction(() => location.hash === '#sources' && document.querySelector('#main h1').textContent === 'المراجع');
  const auths = await page.locator('main a.row').evaluateAll(rs => rs.length);
  assert.equal(auths, data.sources.filter(s => s.authority === 'US-FDA').length);
  await page.click('.rail button[data-auth=""]');
  await ctx.close();
});

test('on a phone: nothing runs off the side, and an entry opens over the list and closes', async () => {
  const phone = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true };
  const { page, ctx, errors } = await open('#requirements', phone);
  assert.equal(await overflow(page), 0);
  await shot(page, '04-phone-requirements-ar');
  await page.locator('main a.row').first().click();
  const d = page.locator('#detail');
  await d.waitFor();
  const box = await d.boundingBox();
  assert.ok(box.width >= 380, 'the entry takes the whole width');
  assert.equal(await overflow(page), 0);
  await shot(page, '05-phone-entry-ar');
  await page.click('#closeDetail');
  assert.equal(await d.isHidden(), true);
  for (const v of ['home', 'sources', 'rules', 'variations', 'documents', 'countries', 'ectd']) {
    await page.evaluate(h => { location.hash = h; }, v);
    await page.waitForTimeout(30);
    assert.equal(await overflow(page), 0, v);
  }
  assert.deepEqual(errors, []);
  await ctx.close();
});

test('dark theme: the page follows it', async () => {
  const { page, ctx } = await open('#rules', { colorScheme: 'dark' });
  const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  const [r, g, b] = bg.match(/\d+/g).map(Number);
  assert.ok(r + g + b < 120, `dark background, got ${bg}`);
  await shot(page, '06-rules-dark-ar');
  await ctx.close();
});

test('the artifact edition (no document shell) works the same', async () => {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 860 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  const content = fs.readFileSync(path.join(ROOT, 'dist', 'library-artifact.html'), 'utf8');
  // The shell the artifact host wraps around a page.
  await page.setContent(`<!doctype html><html><head><meta charset="utf8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>[hidden]{display:none!important}</style></head><body>${content}</body></html>`);
  await page.waitForSelector('#main h1');
  assert.equal(await page.evaluate(() => document.documentElement.dir), 'rtl');
  assert.equal(await page.locator('.auth').count(), data.authorities.length);
  assert.deepEqual(errors, []);
  await ctx.close();
});

test('every source kept in the project opens from the library, at the cited page', async () => {
  const { page, ctx, errors } = await open('#r-EG-EDA-SC-SOFT-01');
  await page.waitForSelector('#detail a.openfile');
  const href = await page.getAttribute('#detail a.openfile', 'href');
  assert.match(href, /^sources\/EDA_NP\.CAPP\.065_v5_2025_CTD-submission-guidance\.pdf#page=13$/);
  // each held source has its button, and the file it names is beside the page
  const missing = [];
  for (const s of data.sources.filter(x => x.held && /\.pdf$/i.test(x.file))) {
    await page.evaluate(h => { location.hash = h; }, '#s-' + s.id);
    await page.waitForFunction(id => document.querySelector('#detail h1') && location.hash === '#s-' + id, s.id);
    const h = await page.getAttribute('#detail .openbar a.openfile', 'href').catch(() => null);
    if (!h || !fs.existsSync(path.join(ROOT, 'dist', 'library', decodeURIComponent(h.split('#')[0])))) missing.push(s.id);
  }
  assert.deepEqual(missing, []);
  assert.deepEqual(errors, []);
  await ctx.close();
});

test('the review page shows what the check found, and every finding links to its records', async () => {
  const { page, ctx, errors } = await open('#review');
  await page.waitForSelector('.results .res');
  const tiles = await page.$$eval('.results .res b', bs => bs.map(b => Number(b.textContent.replace(/,/g, ''))));
  assert.equal(tiles.reduce((a, b) => a + b, 0), data.checks.citations.length);
  assert.equal(await page.locator('.finding').count(), data.checks.findings.findings.length);
  await page.click('.finding a[href="#r-EG-EDA-var-H-21"]');
  await page.locator('#detail .checknote').waitFor();
  assert.match(await page.locator('#detail').innerText(), /PAC-A/);
  await shot(page, '07-review-ar');
  assert.deepEqual(errors, []);
  await ctx.close();
});

test('the variations the guideline classes differently can be listed on their own', async () => {
  const { page, ctx } = await open('#variations');
  await page.click('[data-verdict="differs"]');
  const n = await page.locator('main a.row').count();
  assert.equal(n, data.variations.items.filter(v => v.check?.verdict === 'differs').length);
  assert.equal(n, 15);
  await ctx.close();
});

test('search for anything: an Arabic word finds the English one, in the knowledge and inside the documents', async () => {
  const { page, ctx, errors } = await open();
  await page.fill('#q', 'ذوبان');
  await page.waitForSelector('#docResults .doccard', { timeout: 60000 });
  assert.match(await page.locator('main .lede').first().innerText(), /dissolution/);
  assert.ok(await page.locator('#inKnow a.row').count() > 10, 'the knowledge holds dissolution questions');
  assert.ok(await page.locator('#docResults mark').count() > 10, 'the words found are marked in the documents');
  // each page found opens at that page
  const href = await page.getAttribute('#docResults .hit a.openfile', 'href');
  assert.match(href, /^sources\/.+\.pdf#page=\d+$/);
  await shot(page, '08-search-docs-ar');
  // a phrase in quotes is looked for as written
  await page.fill('#q', '"soft copies must be fulfilled"');
  await page.waitForFunction(() => /NP\.CAPP\.065/.test(document.querySelector('#docResults .doccard')?.innerText || ''), null, { timeout: 30000 });
  assert.match(await page.locator('#docResults .doccard').first().innerText(), /soft copies must be fulfilled/i);
  assert.deepEqual(errors, []);
  await ctx.close();
});

test('search inside one document from its own page', async () => {
  const { page, ctx, errors } = await open('#s-eda-gl-capp-026-v6');
  await page.fill('#docq', 'score line');
  await page.waitForSelector('#docqOut .hit', { timeout: 60000 });
  const text = await page.locator('#docqOut').innerText();
  assert.match(text, /score line/i);
  assert.match(await page.getAttribute('#docqOut a.openfile', 'href'), /EDA_GL\.CAPP\.026_v6.+#page=\d+$/);
  assert.deepEqual(errors, []);
  await ctx.close();
});
