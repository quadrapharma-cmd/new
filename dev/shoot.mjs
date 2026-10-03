// Playwright screenshots of the BUILT page (dist/index.html) against the mock runtime and synthetic data.
//   npm run build && npm run shoot [-- --routes dashboard,system] [--quick] [--private]
// Output: .local/shots/*.png + .local/shots/report.json (gitignored). Never runs `playwright install`:
// it launches the Chromium that already lives under /opt/pw-browsers (playwright-core + executablePath).
// For each page and viewport it reports: horizontal overflow (page + offending elements), console errors,
// failed same-origin requests, and text with contrast below 4.5:1 (3:1 for large text).
import { chromium } from 'playwright-core';
import { mkdirSync, readdirSync, existsSync, writeFileSync, rmSync, readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { startServer } from './serve.mjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, '.local/shots');

const args = process.argv.slice(2);
const opt = (name) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : null;
};
const ALL_ROUTES = ['dashboard', 'entries', 'entry-new', 'reports', 'reports-tb', 'parties', 'documents', 'registers', 'assets', 'reconciliation', 'close', 'import', 'audit', 'system', 'settings', 'no-such-page'];
const routes = opt('--routes') ? opt('--routes').split(',') : ALL_ROUTES;
const quick = args.includes('--quick');

const VIEWPORTS = [
  { name: 'w1280', width: 1280, height: 900 },
  { name: 'w400', width: 400, height: 860 },
];
const SCHEMES = ['light', 'dark'];
// extra variants only for the screens that react to them
const VARIANTS = [
  { name: 'ro', query: '?ro=1', routes: ['dashboard', 'system', 'entries'] },
  { name: 'nodb', query: '?nodb=1', routes: ['dashboard'] },
  { name: 'empty', query: '?empty=1', routes: ['dashboard', 'system'] },
  { name: 'dirty', query: '?dirty=1', routes: ['system'] },
];

function findChromium() {
  const base = process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/pw-browsers';
  if (!existsSync(base)) return undefined;
  const dirs = readdirSync(base);
  for (const prefix of ['chromium-', 'chromium_headless_shell-']) {
    for (const d of dirs.filter((x) => x.startsWith(prefix)).sort().reverse()) {
      for (const rel of ['chrome-linux/chrome', 'chrome-linux/headless_shell']) {
        const p = join(base, d, rel);
        if (existsSync(p)) return p;
      }
    }
  }
  return undefined;
}

// ---- in-page analysis (serialised into the browser) ----
function analyse() {
  const vw = document.documentElement.clientWidth;
  const sel = (el) => {
    const parts = [];
    for (let n = el, i = 0; n && n.nodeType === 1 && i < 4; n = n.parentElement, i++) {
      let s = n.tagName.toLowerCase();
      if (n.id) s += `#${n.id}`;
      else if (n.className && typeof n.className === 'string') s += '.' + n.className.trim().split(/\s+/).slice(0, 2).join('.');
      parts.unshift(s);
    }
    return parts.join(' > ');
  };
  const clipped = (el) => {
    for (let n = el.parentElement; n && n !== document.body; n = n.parentElement) {
      const o = getComputedStyle(n).overflowX;
      if (o === 'auto' || o === 'scroll' || o === 'hidden') return true;
    }
    return false;
  };
  const offenders = [];
  for (const el of document.body.querySelectorAll('*')) {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    if (getComputedStyle(el).visibility === 'hidden') continue;
    if ((r.right > vw + 1 || r.left < -1) && !clipped(el)) offenders.push({ el: sel(el), left: Math.round(r.left), right: Math.round(r.right) });
  }
  // contrast
  const parse = (c) => {
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const [r, g, b, a = 1] = m[1].split(/[ ,/]+/).filter(Boolean).map(Number);
    return { r, g, b, a };
  };
  const lin = (v) => {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  const L = ({ r, g, b }) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  const over = (top, under) => ({ r: top.r * top.a + under.r * (1 - top.a), g: top.g * top.a + under.g * (1 - top.a), b: top.b * top.a + under.b * (1 - top.a), a: 1 });
  const bgOf = (el) => {
    const stack = [];
    for (let n = el; n; n = n.parentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) stack.push(c);
      if (c && c.a === 1) break;
    }
    let base = { r: 255, g: 255, b: 255, a: 1 };
    for (const c of stack.reverse()) base = over(c, base);
    return base;
  };
  const low = new Map();
  for (const el of document.body.querySelectorAll('*')) {
    if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || el.closest('[hidden]')) continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    const fg = parse(cs.color);
    if (!fg) continue;
    const bg = bgOf(el);
    const f = over(fg, bg);
    const l1 = L(f);
    const l2 = L(bg);
    const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    const size = parseFloat(cs.fontSize);
    const large = size >= 24 || (size >= 18.66 && Number(cs.fontWeight) >= 700);
    if (ratio < (large ? 3 : 4.5) && !el.disabled && !el.closest('[disabled]') && cs.opacity === '1') {
      const key = `${sel(el)}|${cs.color}|${ratio.toFixed(2)}`;
      if (!low.has(key)) low.set(key, { el: sel(el), color: cs.color, ratio: Number(ratio.toFixed(2)), text: (el.textContent || '').trim().slice(0, 30) });
    }
  }
  return {
    pageOverflow: document.documentElement.scrollWidth > vw + 1 || document.body.scrollWidth > vw + 1,
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: vw,
    offenders: offenders.slice(0, 12),
    lowContrast: [...low.values()].slice(0, 15),
    title: document.title,
    dir: document.documentElement.getAttribute('dir'),
    h1: (document.querySelector('h1') || {}).textContent || null,
  };
}

// Google Fonts through the sandbox proxy: Chromium cannot always tunnel to it, so node fetches (curl) and caches the files.
const FONT_CACHE = join(ROOT, '.local/fonts-cache');
const CHROME_UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36';
async function fontRoute(route) {
  const url = route.request().url();
  mkdirSync(FONT_CACHE, { recursive: true });
  const key = join(FONT_CACHE, createHash('sha1').update(url).digest('hex'));
  if (!existsSync(key)) {
    const r = spawnSync('curl', ['-sS', '-L', '-m', '40', '-A', CHROME_UA, '-o', key, '-w', '%{http_code}', url], { encoding: 'utf8' });
    if (r.status !== 0 || r.stdout.trim() !== '200') {
      rmSync(key, { force: true });
      return route.abort();
    }
  }
  const body = readFileSync(key);
  const type = url.includes('googleapis.com/css') ? 'text/css; charset=utf-8' : url.endsWith('.woff2') || /woff2/.test(url) || body.slice(0, 4).toString() === 'wOF2' ? 'font/woff2' : 'application/octet-stream';
  return route.fulfill({ status: 200, body, headers: { 'content-type': type, 'access-control-allow-origin': '*', 'cache-control': 'max-age=3600' } });
}

async function main() {
  rmSync(OUT, { recursive: true, force: true });
  mkdirSync(OUT, { recursive: true });
  const server = await startServer({ quiet: true, privateSeed: false });
  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  // Playwright's own `proxy` option proxies loopback too, so the flags go straight to Chromium: only Google Fonts leaves the box.
  const browser = await chromium.launch({
    executablePath: findChromium(),
    args: ['--no-sandbox', ...(proxy ? [`--proxy-server=${proxy}`, '--proxy-bypass-list=localhost;127.0.0.1'] : [])],
  });
  const report = { startedAt: new Date().toISOString(), shots: [], totals: { shots: 0, overflow: 0, consoleErrors: 0, lowContrast: 0 } };

  async function shoot({ name, url, vp, scheme, fullPage = true, before }) {
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, colorScheme: scheme, ignoreHTTPSErrors: true, locale: 'ar-EG', deviceScaleFactor: 1 });
    await ctx.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//, fontRoute);
    const page = await ctx.newPage();
    const errors = [];
    const failed = [];
    page.on('console', (m) => {
      if (m.type() === 'error' || m.type() === 'warning') errors.push(`${m.type()}: ${m.text()}`.slice(0, 300));
    });
    page.on('pageerror', (e) => errors.push(`pageerror: ${String(e.message || e).slice(0, 300)}`));
    page.on('requestfailed', (r) => {
      const u = r.url();
      if (u.startsWith(server.url)) failed.push(u);
    });
    await page.goto(url, { waitUntil: 'load' });
    await page.waitForSelector('h1, .empty, .err-box', { timeout: 8000 }).catch(() => {});
    await page.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
    await page.waitForTimeout(350);
    if (before) await before(page);
    const info = await page.evaluate(analyse);
    const file = `${name}__${vp.name}__${scheme}.png`;
    await page.screenshot({ path: join(OUT, file), fullPage });
    const entry = { file, url, viewport: vp.name, scheme, ...info, consoleErrors: errors, failedRequests: failed };
    report.shots.push(entry);
    report.totals.shots += 1;
    if (info.pageOverflow || info.offenders.length) report.totals.overflow += 1;
    report.totals.consoleErrors += errors.length;
    report.totals.lowContrast += info.lowContrast.length;
    await ctx.close();
  }

  const vps = quick ? [VIEWPORTS[0], VIEWPORTS[1]] : VIEWPORTS;
  const schemes = quick ? ['light'] : SCHEMES;

  for (const route of routes) {
    for (const vp of vps) for (const scheme of schemes) {
      await shoot({ name: `app-${route}`, url: `${server.url}/#${route}`, vp, scheme });
    }
  }
  for (const v of VARIANTS) {
    for (const route of v.routes.filter((r) => routes.includes(r))) {
      for (const vp of vps) for (const scheme of schemes) {
        await shoot({ name: `app-${route}-${v.name}`, url: `${server.url}/${v.query}#${route}`, vp, scheme });
      }
    }
  }
  // phone navigation drawer open
  for (const scheme of schemes) {
    await shoot({
      name: 'app-nav-open',
      url: `${server.url}/#dashboard`,
      vp: VIEWPORTS[1],
      scheme,
      fullPage: false,
      before: async (page) => {
        await page.click('.nav-toggle');
        await page.waitForTimeout(400);
      },
    });
  }

  // kit gallery: resting state, then the open states
  const gallery = `${server.url}/__gallery`;
  for (const vp of vps) for (const scheme of schemes) {
    await shoot({ name: 'gallery', url: gallery, vp, scheme });
    await shoot({
      name: 'gallery-account-open',
      url: gallery,
      vp,
      scheme,
      fullPage: false,
      before: async (page) => {
        await page.locator('#g-acct').scrollIntoViewIfNeeded();
        await page.locator('#g-acct').click();
        await page.keyboard.type('13');
        await page.waitForTimeout(150);
        await page.locator('#g-acct').evaluate((el) => el.scrollIntoView({ block: 'start' }));
      },
    });
    await shoot({
      name: 'gallery-modal',
      url: gallery,
      vp,
      scheme,
      fullPage: false,
      before: async (page) => {
        await page.click('#g-open-modal');
        await page.waitForTimeout(250);
      },
    });
    await shoot({
      name: 'gallery-confirm-reason',
      url: gallery,
      vp,
      scheme,
      fullPage: false,
      before: async (page) => {
        await page.click('#g-open-confirm');
        await page.waitForTimeout(250);
        await page.click('.modal__foot .btn--primary');
        await page.waitForTimeout(150);
      },
    });
    await shoot({
      name: 'gallery-toasts',
      url: gallery,
      vp,
      scheme,
      fullPage: false,
      before: async (page) => {
        await page.click('#g-toast');
        await page.waitForTimeout(250);
      },
    });
  }

  await browser.close();
  await server.close();
  report.finishedAt = new Date().toISOString();
  writeFileSync(join(OUT, 'report.json'), JSON.stringify(report, null, 2));

  // console summary
  const bad = report.shots.filter((s) => s.pageOverflow || s.offenders.length || s.consoleErrors.length || s.failedRequests.length || s.lowContrast.length);
  console.log(`shots: ${report.totals.shots}  with overflow: ${report.totals.overflow}  console errors: ${report.totals.consoleErrors}  low-contrast spots: ${report.totals.lowContrast}`);
  for (const s of bad) {
    console.log(`\n- ${s.file}`);
    if (s.pageOverflow) console.log(`    PAGE OVERFLOW scrollWidth=${s.scrollWidth} clientWidth=${s.clientWidth}`);
    for (const o of s.offenders.slice(0, 5)) console.log(`    offender ${o.el} [${o.left}..${o.right}]`);
    for (const e of s.consoleErrors.slice(0, 5)) console.log(`    console ${e}`);
    for (const f of s.failedRequests.slice(0, 3)) console.log(`    request failed ${f}`);
    for (const c of s.lowContrast.slice(0, 5)) console.log(`    contrast ${c.ratio} ${c.el} "${c.text}" ${c.color}`);
  }
  console.log(`\nscreenshots + report.json: ${OUT}`);
  if (report.totals.overflow || report.totals.consoleErrors) process.exitCode = 1;
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
