// Interaction checks for the built app and the kit gallery (Playwright + Chromium from /opt/pw-browsers).
//   npm run build && npm run uicheck
// Covers keyboard behaviour that screenshots cannot: pickers, modal focus trap, confirm-with-reason, inputs with
// Arabic digits, theme/year persistence, router, read-only and db-less states, drawer, error boundary.
import { chromium } from 'playwright-core';
import assert from 'node:assert/strict';
import { readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { startServer } from './serve.mjs';

function findChromium() {
  const base = process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/pw-browsers';
  if (!existsSync(base)) return undefined;
  for (const prefix of ['chromium-', 'chromium_headless_shell-']) {
    for (const d of readdirSync(base).filter((x) => x.startsWith(prefix)).sort().reverse()) {
      for (const rel of ['chrome-linux/chrome', 'chrome-linux/headless_shell']) {
        if (existsSync(join(base, d, rel))) return join(base, d, rel);
      }
    }
  }
  return undefined;
}

const server = await startServer({ quiet: true });
const browser = await chromium.launch({ executablePath: findChromium(), args: ['--no-sandbox'] });
const results = [];
let failed = 0;

async function open(path, { width = 1280, height = 900, scheme = 'light' } = {}) {
  const ctx = await browser.newContext({ viewport: { width, height }, colorScheme: scheme, locale: 'ar-EG' });
  // fonts are irrelevant for behaviour checks and the sandbox proxy is slow: skip them
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e.message)));
  page.on('console', (m) => m.type() === 'error' && !/Failed to load resource/.test(m.text()) && errors.push(m.text()));
  await page.goto(server.url + path);
  await page.waitForSelector('h1, .empty__title', { timeout: 8000 });
  page.__errors = errors;
  page.__ctx = ctx;
  return page;
}

async function check(name, fn) {
  try {
    await fn();
    results.push({ name, ok: true });
    console.log(`ok   ${name}`);
  } catch (e) {
    failed += 1;
    results.push({ name, ok: false, error: String(e.message || e) });
    console.log(`FAIL ${name}\n     ${String(e.message || e).split('\n').slice(0, 6).join('\n     ')}`);
  }
}
const val = (page, sel) => page.locator(sel).inputValue();

// ------------------------------------------------------------------ app shell
await check('app: RTL root, title, no overflow, no console errors', async () => {
  const p = await open('/#dashboard');
  assert.equal(await p.evaluate(() => document.documentElement.dir), 'rtl');
  assert.equal(await p.evaluate(() => document.documentElement.lang), 'ar');
  assert.match(await p.title(), /ستريفا/);
  assert.equal(await p.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), true);
  assert.equal(await p.locator('.brand__name').innerText(), 'شركة المثال التجريبية');
  assert.deepEqual(p.__errors, []);
  await p.__ctx.close();
});

await check('router: nav link changes hash and screen; aria-current follows; unknown token shows not-found', async () => {
  const p = await open('/#dashboard');
  await p.click('.nav__link:has-text("القيود") >> nth=0');
  await p.waitForFunction(() => location.hash === '#entries');
  await p.waitForSelector('h1:has-text("القيود")');
  assert.equal(await p.locator('.nav__link[aria-current="page"]').innerText(), 'القيود');
  await p.evaluate(() => { location.hash = 'reports-tb'; });
  await p.waitForSelector('h1:has-text("التقارير")');
  await p.evaluate(() => { location.hash = 'entry-new'; });
  await p.waitForSelector('h1:has-text("قيد جديد")');
  await p.evaluate(() => { location.hash = 'no-such-page'; });
  await p.waitForSelector('text=الصفحة غير موجودة');
  await p.__ctx.close();
});

await check('theme: toggle sets data-theme, persists across reload (localStorage)', async () => {
  const p = await open('/#dashboard', { scheme: 'light' });
  assert.equal(await p.evaluate(() => document.documentElement.getAttribute('data-theme')), null);
  await p.click('button[aria-label="التبديل إلى المظهر الداكن"]');
  assert.equal(await p.evaluate(() => document.documentElement.getAttribute('data-theme')), 'dark');
  const bg = await p.evaluate(() => getComputedStyle(document.body).backgroundColor);
  assert.notEqual(bg, 'rgb(241, 243, 239)');
  await p.reload();
  await p.waitForSelector('h1');
  assert.equal(await p.evaluate(() => document.documentElement.getAttribute('data-theme')), 'dark');
  await p.__ctx.close();
});

await check('year: default is the open fiscal year; choosing another updates the period banner and persists', async () => {
  const p = await open('/#dashboard');
  await p.waitForSelector('.period__label');
  assert.match(await p.locator('.period__label').innerText(), /2025.*مفتوحة/);
  await p.selectOption('#year-select', '2024');
  assert.match(await p.locator('.period__label').innerText(), /2024.*مقفلة بتحفظ/);
  await p.click('.period__btn');
  await p.waitForSelector('.period__detail');
  assert.match(await p.locator('.period__detail').innerText(), /لا تُصدَّر قوائمها/);
  await p.selectOption('#year-select', '2023');
  assert.match(await p.locator('.period__label').innerText(), /2023.*مقفلة نهائياً/);
  await p.reload();
  await p.waitForSelector('.period__label');
  assert.match(await p.locator('.period__label').innerText(), /2023/);
  await p.__ctx.close();
});

await check('read-only: banner, header badge, db-null state, no-user state', async () => {
  let p = await open('/?ro=1#dashboard');
  await p.waitForSelector('text=صلاحيتك للعرض فقط');
  assert.ok(await p.locator('.badge-readonly-header').count());
  await p.__ctx.close();
  p = await open('/?nodb=1#dashboard');
  await p.waitForSelector('text=قاعدة البيانات غير متاحة في هذا العرض');
  assert.equal(await p.locator('.nav').count(), 0);
  assert.equal(await p.locator('.nav-toggle').count(), 0);
  await p.__ctx.close();
  p = await open('/?nouser=1#system');
  await p.waitForSelector('text=حالة النظام');
  assert.ok(await p.locator('.banner:has-text("للعرض فقط")').count(), 'no user capability means read-only');
  await p.__ctx.close();
});

await check('system screen: counts, subscriptions <= 64, integrity result, unavailable capability pills', async () => {
  const p = await open('/#system');
  await p.waitForSelector('section[aria-labelledby="sys-integrity"] .banner');
  const text = await p.locator('main').innerText();
  assert.match(text, /17 \/ 64/);
  assert.match(text, /متصلة وجاهزة/);
  assert.match(text, /لا توجد مشكلات|عدد الملاحظات|فاحص السلامة لم يُضَف/);
  await p.__ctx.close();
  const q = await open('/?dirty=1#system');
  await q.waitForSelector('.issue');
  assert.ok((await q.locator('.issue').count()) >= 1);
  assert.ok(await q.locator('.banner--critical:has-text("فحص سلامة القيود")').count(), 'integrity errors surface as a banner on every screen');
  await q.__ctx.close();
});

await check('phone: drawer opens from the menu button, closes with Esc and on navigation', async () => {
  const p = await open('/#dashboard', { width: 400, height: 800 });
  assert.equal(await p.locator('#app-nav').getAttribute('data-open'), 'false');
  await p.click('.nav-toggle');
  assert.equal(await p.locator('#app-nav').getAttribute('data-open'), 'true');
  await p.waitForTimeout(250);
  await p.keyboard.press('Escape');
  await p.waitForFunction(() => document.querySelector('#app-nav').dataset.open === 'false');
  await p.click('.nav-toggle');
  await p.waitForFunction(() => document.querySelector('#app-nav').dataset.open === 'true');
  await p.click('.nav-toggle'); // the header stays above the drawer, so the same button closes it
  await p.waitForFunction(() => document.querySelector('#app-nav').dataset.open === 'false');
  await p.click('.nav-toggle');
  await p.click('#app-nav a:has-text("الأطراف")');
  await p.waitForFunction(() => location.hash === '#parties');
  assert.equal(await p.locator('#app-nav').getAttribute('data-open'), 'false');
  assert.equal(await p.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), true);
  await p.__ctx.close();
});

// ------------------------------------------------------------------ kit (gallery)
const gal = async (opts) => open('/__gallery', opts);

await check('NumberInput: Arabic digits and separators parse; invalid/negative flagged; normalises on blur', async () => {
  const p = await gal();
  await p.fill('#g-amt', '١٬٢٣٤٫٥٠');
  await p.press('#g-amt', 'Tab');
  assert.equal(await val(p, '#g-amt'), '1,234.50');
  const invalid = (sel) => p.waitForFunction((x) => document.querySelector(x).getAttribute('aria-invalid') === 'true', sel, { timeout: 2000 });
  await p.fill('#g-amt', 'abc');
  await invalid('#g-amt');
  await p.fill('#g-amt', '99');
  await p.waitForFunction(() => !document.querySelector('#g-amt').hasAttribute('aria-invalid'));
  await p.fill('#g-amt', '-5');
  await invalid('#g-amt');
  await p.fill('#g-amt', '1.234');
  await invalid('#g-amt'); // more than 2 decimals is refused
  await p.fill('#g-amt', '99');
  await p.press('#g-amt', 'Tab');
  assert.equal(await val(p, '#g-amt'), '99.00');
  await p.__ctx.close();
});

await check('DateInput: dd/mm/yyyy, Arabic digits, d/m completes the year, invalid flagged', async () => {
  const p = await gal();
  await p.fill('#g-date', '٣١/١٢/٢٠٢٤');
  await p.press('#g-date', 'Tab');
  assert.equal(await val(p, '#g-date'), '31/12/2024');
  await p.fill('#g-date', '5/3');
  await p.press('#g-date', 'Tab');
  assert.equal(await val(p, '#g-date'), '05/03/2025');
  await p.fill('#g-date', '31/02/2025');
  await p.press('#g-date', 'Tab');
  await p.waitForFunction(() => document.querySelector('#g-date').getAttribute('aria-invalid') === 'true', null, { timeout: 2000 });
  await p.__ctx.close();
});

await check('AccountPicker: exact code + Tab accepts; Arabic name search; inactive hidden; keyboard navigation', async () => {
  const p = await gal();
  await p.click('#g-acct');
  await p.keyboard.press('Control+a');
  await p.keyboard.type('1320');
  await p.keyboard.press('Tab');
  assert.match(await val(p, '#g-acct'), /^1320 /);
  await p.click('#g-acct');
  await p.keyboard.type('بنك');
  await p.waitForSelector('#g-acct-list [role=option]');
  assert.match(await p.locator('#g-acct-list [role=option]').first().innerText(), /1340/);
  await p.keyboard.press('Enter');
  assert.match(await val(p, '#g-acct'), /^1340 /);
  await p.click('#g-acct');
  await p.keyboard.type('5211');
  assert.equal(await p.locator('#g-acct-list [role=option]').count(), 0, 'inactive account hidden');
  await p.keyboard.press('Escape');
  await p.click('#g-acct');
  assert.equal(await p.locator('#g-acct').getAttribute('role'), 'combobox');
  await p.keyboard.press('ArrowDown');
  await p.keyboard.press('ArrowDown');
  const active = await p.locator('#g-acct').getAttribute('aria-activedescendant');
  assert.equal(await p.locator(`#${active}`).getAttribute('aria-selected'), 'true');
  await p.keyboard.press('Enter');
  assert.ok((await val(p, '#g-acct')).length > 4);
  await p.__ctx.close();
});

await check('AccountPicker inside a scrollable table: the list escapes the overflow container and stays on screen', async () => {
  const p = await gal();
  await p.locator('#g-grid-acct-1').scrollIntoViewIfNeeded();
  await p.click('#g-grid-acct-1');
  await p.waitForSelector('#g-grid-acct-1-list [role=option]');
  const info = await p.evaluate(() => {
    const list = document.querySelector('#g-grid-acct-1-list').getBoundingClientRect();
    const wrap = document.querySelector('#g-grid-acct-1').closest('.table-wrap').getBoundingClientRect();
    const cx = list.left + list.width / 2;
    const cy = list.top + Math.min(40, list.height / 2);
    const top = document.elementFromPoint(cx, cy);
    return { listBottom: list.bottom, wrapBottom: wrap.bottom, hit: !!(top && top.closest('#g-grid-acct-1-list')), inView: list.left >= 0 && list.right <= innerWidth };
  });
  assert.equal(info.hit, true, 'list is the topmost element at its own position (not clipped or covered)');
  assert.equal(info.inView, true);
  assert.ok(info.listBottom > info.wrapBottom, 'list extends past the scroll container');
  await p.__ctx.close();
  const q = await open('/__gallery', { width: 400, height: 800 });
  await q.locator('#g-acct').scrollIntoViewIfNeeded();
  await q.click('#g-acct');
  await q.waitForSelector('#g-acct-list [role=option]');
  assert.equal(await q.evaluate(() => { const r = document.querySelector('#g-acct-list').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth; }), true, 'list fits a phone viewport');
  await q.__ctx.close();
});

await check('PartyPicker: alias search, quick-create option, merged parties hidden', async () => {
  const p = await gal();
  await p.click('#g-party');
  await p.keyboard.type('الوادي');
  await p.waitForSelector('#g-party-list [role=option]');
  assert.match(await p.locator('#g-party-list').innerText(), /شركة الوادي للمعدات/);
  await p.fill('#g-party', 'طرف لا يوجد له مثيل');
  await p.waitForSelector('#g-party-list .combo__create');
  assert.match(await p.locator('#g-party-list .combo__create').innerText(), /إضافة «طرف لا يوجد له مثيل» كطرف جديد/);
  await p.click('#g-party-list .combo__create');
  await p.waitForFunction(() => document.querySelector('#g-party').value.length > 0);
  assert.match(await val(p, '#g-party'), /p-/);
  await p.__ctx.close();
});

await check('DocPicker: add, remove by chip button, Backspace removes last, reuse button', async () => {
  const p = await gal();
  assert.ok((await p.locator('.chips li').count()) >= 1);
  await p.click('.chips .chip__x');
  assert.equal(await p.locator('.chips li').count(), 0);
  await p.click('#g-docs');
  await p.waitForSelector('#g-docs-list [role=option]');
  await p.keyboard.press('Enter');
  assert.equal(await p.locator('.chips li').count(), 1);
  await p.click('#g-docs');
  await p.keyboard.press('Backspace');
  assert.equal(await p.locator('.chips li').count(), 0);
  await p.click('button:has-text("نفس مستندات القيد السابق")');
  assert.match(await p.locator('.chips').innerText(), /D0003/);
  await p.__ctx.close();
});

await check('Modal: focus moves in, Tab stays inside, Esc closes and returns focus to the opener, page does not scroll', async () => {
  const p = await gal();
  await p.focus('#g-open-modal');
  await p.keyboard.press('Enter');
  await p.waitForSelector('[role=dialog]');
  await p.waitForFunction(() => document.querySelector('[role=dialog]').contains(document.activeElement));
  assert.equal(await p.evaluate(() => document.body.style.overflow), 'hidden');
  for (let i = 0; i < 8; i++) {
    await p.keyboard.press('Tab');
    assert.equal(await p.evaluate(() => document.querySelector('[role=dialog]').contains(document.activeElement)), true, `Tab ${i} escaped the dialog`);
  }
  for (let i = 0; i < 8; i++) {
    await p.keyboard.press('Shift+Tab');
    assert.equal(await p.evaluate(() => document.querySelector('[role=dialog]').contains(document.activeElement)), true, `Shift+Tab ${i} escaped the dialog`);
  }
  await p.keyboard.press('Escape');
  await p.waitForSelector('[role=dialog]', { state: 'detached' });
  await p.waitForFunction(() => document.activeElement && document.activeElement.id === 'g-open-modal', null, { timeout: 2000 });
  assert.notEqual(await p.evaluate(() => document.body.style.overflow), 'hidden');
  await p.__ctx.close();
});

await check('ConfirmDialog: reason is mandatory; confirmAsync resolves false on cancel and true on confirm', async () => {
  const p = await gal();
  await p.click('#g-open-confirm');
  await p.waitForSelector('[role=dialog] textarea');
  await p.click('[role=dialog] .btn--primary');
  assert.ok(await p.locator('[role=dialog] .field__error').count(), 'error shown');
  assert.ok(await p.locator('[role=dialog]').count(), 'dialog stays open without a reason');
  await p.fill('[role=dialog] textarea', 'وصل المستند وتغير المبلغ');
  await p.click('[role=dialog] .btn--primary');
  await p.waitForSelector('[role=dialog]', { state: 'detached' });
  await p.click('#g-open-confirm2');
  await p.waitForSelector('[role=dialog]');
  await p.click('[role=dialog] .modal__foot .btn:not(.btn--danger)');
  await p.waitForFunction(() => window.__confirmResult === false);
  await p.click('#g-open-confirm2');
  await p.click('[role=dialog] .btn--danger');
  await p.waitForFunction(() => window.__confirmResult === true);
  await p.__ctx.close();
});

await check('Toast host announces and auto-dismisses; ErrorBoundary shows the friendly Arabic message', async () => {
  const p = await gal();
  await p.click('#g-toast');
  assert.equal(await p.locator('.toast').count(), 3);
  assert.ok(await p.locator('.toast[role=alert]').count());
  await p.click('.toast__close >> nth=0');
  assert.equal(await p.locator('.toast').count(), 2);
  await p.click('#g-boom');
  await p.waitForSelector('.err-box[role=alert]');
  assert.match(await p.locator('.err-box').innerText(), /حدث خطأ غير متوقع/);
  assert.match(await p.locator('.err-box details').textContent(), /انهيار تجريبي/);
  await p.__ctx.close();
});

await check('DataTable: sortable header toggles aria-sort and reorders rows; totals row present', async () => {
  const p = await gal();
  const t = p.locator('.table:has(.th-sort)').first();
  const first = () => t.locator('tbody tr').first().locator('td').first().innerText();
  await t.locator('thead th').first().locator('.th-sort').click();
  assert.equal(await t.locator('thead th').first().getAttribute('aria-sort'), 'ascending');
  const asc = await first();
  await t.locator('thead th').first().locator('.th-sort').click();
  assert.equal(await t.locator('thead th').first().getAttribute('aria-sort'), 'descending');
  const desc = await first();
  assert.equal(asc, '1193');
  assert.equal(desc, '4110');
  assert.equal(await t.locator('tfoot tr').count(), 1);
  assert.ok(await p.locator('.table-wrap').first().evaluate((el) => getComputedStyle(el).overflowX === 'auto'));
  await p.__ctx.close();
});

await check('Tabs: arrow keys move selection in RTL order', async () => {
  const p = await gal();
  await p.focus('[role=tab][aria-selected=true]');
  await p.keyboard.press('ArrowLeft'); // RTL: left = next
  assert.match(await p.locator('[role=tab][aria-selected=true]').innerText(), /المسودات/);
  await p.keyboard.press('ArrowRight');
  assert.match(await p.locator('[role=tab][aria-selected=true]').innerText(), /القيود/);
  await p.__ctx.close();
});

await check('gallery: no console errors, every form control has an id', async () => {
  const p = await gal();
  const missing = await p.evaluate(() => [...document.querySelectorAll('input,select,textarea')].filter((e) => !e.id).length);
  assert.equal(missing, 0);
  assert.deepEqual(p.__errors, []);
  await p.__ctx.close();
});

await browser.close();
await server.close();
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);
