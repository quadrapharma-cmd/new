// Rule 13's check of what claude.ai serves: a published page, read back with the Artifact tool into a folder, run in Chromium
// under a content security policy like the artifact frame's — scripts and styles inline or from the CDNs the page contract
// allows, fonts from Google Fonts, fetch and workers only from the page's own files (never a data: address), images from data:
// and blob: — with window.claude standing in for the viewer (tests/helpers/fake-claude.js: its `sample` refuses what claude.ai's
// contract refuses). It reports blocked loads, console errors and the page's own checks; it cannot reach Claude itself.
//   node tools/check-published.mjs <library|workbench|measure> <folder: index.html and the published files> [--old-measure]
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { fakeClaude } from '../tests/helpers/fake-claude.js';

const require = createRequire(import.meta.url);
export const CSP = ["default-src 'self'",
  "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com https://cdn.tailwindcss.com https://code.jquery.com blob:",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com", "font-src 'self' https://fonts.gstatic.com data:",
  "img-src 'self' data: blob:", "media-src 'self' data: blob:", "connect-src 'self'", "worker-src 'self' blob:",
  "frame-src 'none'", "object-src 'none'"].join('; ');
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
                '.pdf': 'application/pdf', '.csv': 'text/csv', '.txt': 'text/plain; charset=utf-8', '.png': 'image/png' };

function serve(folder, patch) {
  const server = http.createServer((req, res) => {
    const url = decodeURIComponent(req.url.split('?')[0].split('#')[0]);
    const file = path.join(folder, url === '/' ? 'index.html' : url.slice(1));
    if (!file.startsWith(folder) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end(); }
    let body = fs.readFileSync(file);
    if (patch && file.endsWith('index.html')) body = Buffer.from(patch(body.toString('utf8')));
    res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream', 'content-security-policy': CSP });
    res.end(body);
  });
  return new Promise(ok => server.listen(0, '127.0.0.1', () => ok(server)));
}

const SCENARIOS = {
  // the library: opens, finds an Arabic and an English search, opens an entry and shows the source it rests on
  async library(page) {
    await page.waitForSelector('#main h1', { timeout: 30000 });
    await page.fill('#q', 'نموذج الطلب');
    await page.waitForFunction(() => document.querySelector('#main h1')?.textContent.includes('نتايج'), null, { timeout: 15000 });
    const rows = await page.locator('main .row').count();
    await page.locator('main .row').first().click();
    await page.locator('#detail').waitFor({ timeout: 10000 });
    const detail = await page.locator('#detail').innerText();
    const links = await page.$$eval('#detail a[href]', as => as.map(a => a.getAttribute('href')).filter(h => /\.pdf/i.test(h)));
    await page.fill('#q', 'application form');
    await page.waitForFunction(() => /application form/.test(document.querySelector('#main h1')?.textContent || '') || document.querySelectorAll('main .row').length > 0, null, { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(800);
    const english = await page.locator('main .row').count();
    return { 'Arabic search rows': rows, 'entry opened': /NP\.CAPP\.065|1\.1\.1/.test(detail), 'source links in the entry': links.length,
             'English search rows': english };
  },
  // the workbench: the example certificate read in the browser, Claude's tools run, a fact kept with its words
  async workbench(page) {
    await page.waitForFunction(() => document.querySelectorAll('#files tbody tr').length > 0, null, { timeout: 30000 });
    const row = await page.textContent('#files tbody tr');
    const pages = (await page.textContent('#files tbody tr td:nth-child(4)')).trim();
    await page.waitForFunction(() => /جاهز/.test(document.querySelector('#claude-status').textContent), null, { timeout: 15000 });
    await page.fill('#task', 'سجّل رقم التشغيلة من شهادة التحليل');
    await page.click('#send');
    await page.waitForFunction(() => /خلّص|ماردّش|مش/.test(document.querySelector('#claude-status').textContent), null, { timeout: 60000 });
    return { 'example file read (pdf, 2 pages)': /pdf/.test(row) && pages === '2', status: (await page.textContent('#claude-status')).trim(),
             steps: await page.$$eval('#steps li .t', l => l.map(x => x.textContent)), facts: (await page.textContent('#facts')).trim() };
  },
  // the measuring page: each page goes to Claude whole and in two halves
  async measure(page) {
    await page.waitForFunction(() => !document.querySelector('#go')?.disabled, null, { timeout: 30000 });
    await page.click('#go');
    // every page measured: 16 pages, each whole and in two halves (or the page stops on a failure)
    await page.waitForFunction(() => (window.__calls || []).length >= 32 || !document.querySelector('#stop') || document.querySelector('#stop').hidden && document.querySelector('#go') && !document.querySelector('#go').disabled && (window.__calls || []).length > 0, null, { timeout: 180000 }).catch(() => {});
    await page.waitForTimeout(500);
    const calls = await page.evaluate(() => window.__calls);
    return { 'whole-page calls (1 image)': calls.filter(c => c.images === 1).length, 'two-halves calls (2 images)': calls.filter(c => c.images === 2).length,
             summary: (await page.textContent('#summary').catch(() => '')).replace(/\s+/g, ' ').trim().slice(0, 160) };
  },
};

export async function checkPublished(kind, folder, { patch, claude = {} } = {}) {
  const { chromium } = require('playwright');
  const server = await serve(path.resolve(folder), patch);
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const problems = [];
    page.on('pageerror', e => problems.push(`page error: ${e.message}`));
    page.on('console', m => { if (m.type() === 'error') problems.push(`console: ${m.text()}`); });
    await page.addInitScript(() => document.addEventListener('securitypolicyviolation', e => console.error(`blocked by the policy: ${e.violatedDirective} ${e.blockedURI}`)));
    await page.addInitScript(fakeClaude, claude);
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    const result = await SCENARIOS[kind](page);
    return { result, problems: problems.filter(p => !/fonts\.(googleapis|gstatic)/.test(p)) };   // no internet here for Google Fonts
  } finally { await browser.close(); server.close(); }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [kind, folder] = process.argv.slice(2);
  // --old-measure: the measuring page as first published (the whole page fetched from a data: address), to show the check sees
  // the failure the owner met
  const patch = process.argv.includes('--old-measure')
    ? html => html.replace(/function blobOf\(src\)\{return new Promise\(\(ok,no\)=>\{const im=new Image\(\);[\s\S]*?im\.src=src\}\)\}/, 'function blobOf(src){return fetch(src).then(r=>r.blob())}')
    : undefined;
  const claude = kind === 'measure' ? { images: true } : { mode: 'tools' };
  const out = await checkPublished(kind, folder, { patch, claude });
  console.log(JSON.stringify(out, null, 1));
  process.exitCode = out.problems.length ? 1 : 0;
}
