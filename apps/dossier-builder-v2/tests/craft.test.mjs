// The Crafting Apps built from source (tools/craft/build.mjs → vendor/craft/<app>-web/) in a real browser, hosted the way the
// program hosts them: in a frame of the same site, told to open a document with `<app>:open`, handing back what they save
// with `<app>:save`, and driven through their command API (`window.<app>`). A program not built on this machine is skipped
// (the builds are not in git); a program that is built must start, say it is ready and answer its command API.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const VENDOR = path.join(ROOT, 'vendor', 'craft');
const built = app => fs.existsSync(path.join(VENDOR, `${app}-web`, 'index.html'));
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.wasm': 'application/wasm', '.ico': 'image/x-icon',
                '.docx': 'application/octet-stream', '.json': 'application/json' };

// One local site: /<app>/… is the built program, /host.html the host page, /doc/<name> the document handed to it.
function serve(app, docPath) {
  const host = `<!doctype html><meta charset="utf-8"><style>html,body{margin:0;height:100%}iframe{width:1200px;height:850px;border:0}</style>
<iframe id="app" src="${app}/index.html?host=parent&webgl&control"></iframe><script>
window.__log=[];window.__saved=[];window.__ready=false;const frame=document.getElementById('app');
addEventListener('message',async e=>{const m=e.data||{};if(typeof m.type!=='string'||!m.type.startsWith('${app}:'))return;window.__log.push(m.type);
 if(m.type==='${app}:ready'){window.__ready=true;${docPath ? `const bytes=new Uint8Array(await(await fetch('doc/${path.basename(docPath)}')).arrayBuffer());
  frame.contentWindow.postMessage({type:'${app}:open',name:'${path.basename(docPath)}',bytes},location.origin);` : ''}}
 if(m.type==='${app}:save'){const b=new Uint8Array(m.bytes);let s='';for(let i=0;i<b.length;i+=0x8000)s+=String.fromCharCode.apply(null,b.subarray(i,i+0x8000));window.__saved.push({name:m.name,b64:btoa(s)})}});
</script>`;
  const server = http.createServer((req, res) => {
    const url = decodeURIComponent(req.url.split('?')[0]);
    let file = null;
    if (url === '/host.html') { res.writeHead(200, { 'content-type': 'text/html' }); return res.end(host); }
    if (docPath && url === `/doc/${path.basename(docPath)}`) file = docPath;
    else if (url.startsWith(`/${app}/`)) file = path.join(VENDOR, `${app}-web`, url.slice(app.length + 2));
    if (!file || !file.startsWith(file === docPath ? file : path.join(VENDOR, `${app}-web`)) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      res.writeHead(404); return res.end();
    }
    res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise(ok => server.listen(0, '127.0.0.1', () => ok(server)));
}

async function hosted(app, docPath, work) {
  const { chromium } = require('playwright');
  const server = await serve(app, docPath);
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  try {
    const page = await browser.newPage({ viewport: { width: 1220, height: 880 } });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(`http://127.0.0.1:${server.address().port}/host.html`);
    await page.waitForFunction(() => window.__ready, null, { timeout: 240000 }).catch(() => {});
    const ready = await page.evaluate(() => window.__ready);
    assert.ok(ready, `${app} never said it was ready: ${errors.join(' | ') || 'no error shown'}`);
    const frame = page.frames().find(f => f.url().includes(`/${app}/index.html`));
    return await work({ page, frame, errors });
  } finally { await browser.close(); server.close(); }
}

// A made-up cover letter in Word: Arabic (right to left), English and a small table.
function madeUpLetter() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'craft-'));
  const out = path.join(dir, 'cover-letter.docx');
  execFileSync('python3', ['-I', '-c', `
import sys
from docx import Document
from docx.oxml import OxmlElement
d = Document()
d.add_heading('Cover Letter — Testaphen 500 mg', level=1)
p = d.add_paragraph('نتشرف بتقديم ملف تسجيل المستحضر تيستافين من شركة النيل التجريبية للأدوية')
p._p.get_or_add_pPr().append(OxmlElement('w:bidi'))
for r in p.runs: r._r.get_or_add_rPr().append(OxmlElement('w:rtl'))
d.add_paragraph('We submit the registration dossier of Testaphen 500 mg film-coated tablets.')
t = d.add_table(rows=2, cols=2)
t.cell(0, 0).text = 'Batch'; t.cell(0, 1).text = 'TP-24A117'; t.cell(1, 0).text = 'Dosage form'; t.cell(1, 1).text = 'Film-coated tablets'
d.save(sys.argv[1])`, out]);
  return out;
}

// The PDF's text as a reader of PDFs takes it: poppler's pdftotext where the machine has it (it reads WordCraft's Arabic in
// order; pdf.js reads the same file's Arabic as broken letters and control characters — a known limit), pdf.js otherwise.
async function pdfText(bytes) {
  try {
    const f = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'craftpdf-')), 'out.pdf');
    fs.writeFileSync(f, bytes);
    return execFileSync('pdftotext', ['-enc', 'UTF-8', f, '-'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
  } catch { /* no poppler here: pdf.js below */ }
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
  const task = pdfjs.getDocument({ data: new Uint8Array(bytes), useSystemFonts: false });
  const doc = await task.promise;
  let text = '';
  for (let i = 1; i <= doc.numPages; i++) text += (await (await doc.getPage(i)).getTextContent()).items.map(x => x.str).join(' ') + '\n';
  await task.destroy();
  return text;
}

test('WordCraft opens a Word letter in Arabic and English and exports it as a PDF whose text can be read', { skip: !built('wordcraft') && 'WordCraft is not built here (node tools/craft/build.mjs wordcraft web)', timeout: 600000 }, async () => {
  const doc = madeUpLetter();
  await hosted('wordcraft', doc, async ({ page, frame, errors }) => {
    const api = await frame.evaluate(() => ['request', 'execute', 'commands', 'docInspect'].filter(f => typeof window.wordcraft?.[f] === 'function'));
    assert.ok(api.includes('execute'), `window.wordcraft has no command API: ${api}`);
    await page.waitForTimeout(3000);
    await frame.evaluate(() => window.wordcraft.execute('file.exportPdf', {}));
    await page.waitForFunction(() => window.__saved.some(s => /\.pdf$/i.test(s.name)), null, { timeout: 120000 });
    const pdf = await page.evaluate(() => window.__saved.find(s => /\.pdf$/i.test(s.name)).b64);
    const text = await pdfText(Buffer.from(pdf, 'base64'));
    assert.match(text, /Testaphen/);
    assert.match(text, /TP-24A117/);
    // Arabic may come out in presentation forms, with direction marks and with spaces inside words (glyph positions)
    const plain = text.normalize('NFKC').replace(/[\u200E\u200F\u202A-\u202E\u2066-\u2069\s]/g, '');
    assert.match(plain, /تيستافين/, 'the Arabic words are in the PDF\'s text');
    assert.match(plain, /شركةالنيلالتجريبيةللأدوية/);
    assert.deepEqual(errors, []);
  });
});

for (const app of ['pdfcraft', 'photocraft', 'designcraft']) {
  test(`${app} starts in the browser, says it is ready and answers its command API`, { skip: !built(app) && `${app} is not built here`, timeout: 600000 }, async () => {
    await hosted(app, null, async ({ frame, errors }) => {
      const api = await frame.evaluate(a => ['request', 'execute', 'commands', 'docInspect', 'uiInspect', 'screenshot'].filter(f => typeof window[a]?.[f] === 'function'), app);
      assert.ok(api.includes('request'), `window.${app} has no command API: ${api}`);
      const list = await frame.evaluate(async a => { try { const c = await window[a].commands?.(); const l = Array.isArray(c) ? c : (c?.commands || []); return l.length; } catch (e) { return String(e.message || e); } }, app);
      console.log(`${app}: functions ${api.join(', ')}; commands: ${list}`);
      assert.deepEqual(errors, []);
    });
  });
}
