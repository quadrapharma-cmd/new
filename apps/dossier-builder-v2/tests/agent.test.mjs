// Step 2.0c: the tool layer and the agent core (agent/), and the bridge (bridge/mcp.mjs) — the same tools for Claude inside the
// page and in the Claude app. Every file here is made up.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { TOOLS } from '../agent/tools.js';
import { check } from '../agent/schema.js';
import { createWorkspace, kindOf } from '../agent/workspace.js';
import { callTool, sampleTools, mcpTools, ask } from '../agent/agent.js';
import { lineText } from '../core/pdftext.js';
import { loadKnowledge } from '../tools/load.mjs';
import { createKnowledge } from '../core/knowledge.js';

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const knowledge = createKnowledge(loadKnowledge());

// A made-up certificate of analysis, two pages, English and Arabic, printed to PDF by the browser.
let pdfBytes = null;
async function madeUpPdf() {
  if (pdfBytes) return pdfBytes;
  const { chromium } = require('playwright');
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    await page.setContent(`<html><body style="font-family:sans-serif">
      <section style="page-break-after:always"><h1>Certificate of Analysis</h1>
        <p>Product: Testaphen 500 mg film-coated tablets</p><p>Batch TP-24A117</p><p>Expiry date: 02/2028</p>
        <p dir="rtl">الشركة المصنعة: شركة النيل التجريبية للأدوية</p><p dir="rtl">رقم التسجيل ١٢٣٤٥/٢٠٢٥</p></section>
      <section><h2>Results</h2><p>Assay: 99.1 % (95.0 - 105.0 %)</p><p>Dissolution: Q = 80 % in 30 minutes</p></section>
    </body></html>`);
    pdfBytes = new Uint8Array(await page.pdf({ format: 'A4' }));
  } finally { await browser.close(); }
  return pdfBytes;
}

async function setup() {
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
  // the certificate is named .docx on purpose: its kind comes from its content
  const ws = await createWorkspace({ files: [{ name: 'certificate.docx', bytes: await madeUpPdf() },
                                             { name: 'notes.txt', bytes: new TextEncoder().encode('Stability commitment for Testaphen: 36 months.') }] });
  return { ws, pdfjs, knowledge, by: 'test' };
}

test('the catalogue: unique names Claude accepts, a description, an input schema and both titles for every tool', () => {
  const names = TOOLS.map(t => t.name);
  assert.equal(new Set(names).size, names.length);
  for (const t of TOOLS) {
    assert.match(t.name, /^[a-z][a-z0-9_]{1,63}$/);
    assert.ok(t.description.length > 40, t.name);
    assert.equal(t.input.type, 'object', t.name);
    assert.ok(t.title.ar && t.title.en, t.name);
    assert.equal(typeof t.run, 'function');
  }
  assert.deepEqual(mcpTools().map(t => t.name), names);
  assert.equal(mcpTools().find(t => t.name === 'record_fact').annotations.readOnlyHint, false);
  assert.equal(mcpTools().find(t => t.name === 'read_page_text').annotations.readOnlyHint, true);
});

test('inputs are checked before a tool runs', () => {
  const read = TOOLS.find(t => t.name === 'read_page_text').input;
  assert.deepEqual(check(read, { file: 'f1', page: 2 }), []);
  assert.match(check(read, { file: 'f1', page: 0 }).join(), /at least 1/);
  assert.match(check(read, { file: 'f1' }).join(), /page is missing/);
  assert.match(check(read, { file: 'f1', page: 1.5 }).join(), /whole number/);
  assert.match(check(read, { file: 'f1', page: 1, extra: true }).join(), /not an input/);
});

test('a file\'s kind comes from its content, never from its name', async () => {
  assert.equal(kindOf(await madeUpPdf()), 'pdf');
  const enc = s => new TextEncoder().encode(s);
  assert.equal(kindOf(new Uint8Array([0x50, 0x4b, 0x03, 0x04, ...enc('....word/document.xml')])), 'docx');
  assert.equal(kindOf(new Uint8Array([0x50, 0x4b, 0x03, 0x04, ...enc('....xl/workbook.xml')])), 'xlsx');
  assert.equal(kindOf(new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])), 'png');
  assert.equal(kindOf(enc('Rar!\x1a\x07\x01\x00')), 'rar');
  assert.equal(kindOf(enc('plain words')), 'text');
});

test('a PDF line comes back in reading order: Arabic from the right, its numbers and Latin words left to right', () => {
  // as pdf.js hands a right-to-left line: glyphs drawn left to right, in presentation forms
  const items = [['١٢٣٤٥', 0, 20], ['/', 20, 3], ['٢٠٢٥', 23, 16], [' ', 39, 3], ['ﻞ', 42, 4], ['ﻴ', 46, 3], ['ﺠ', 49, 4], ['ﺴ', 53, 5],
                 ['ﺘ', 58, 3], ['ﻟ', 61, 2], ['ا', 63, 2], [' ', 65, 3], ['ﻢ', 68, 4], ['ﻗ', 72, 4], ['ر', 76, 3]]
    .map(([s, x, w]) => ({ s, x, w, h: 10 }));
  assert.equal(lineText(items), 'رقم التسجيل ١٢٣٤٥/٢٠٢٥');
  // a left-to-right line holding an Arabic word, and a gap with no space item between two words
  const mixed = [['Made', 0, 22], ['by', 26, 10], ['ﻞ', 40, 4], ['ﻴ', 44, 3], ['ﻨ', 47, 3], ['ﻟ', 50, 2], ['ا', 52, 2], ['Cairo', 60, 24]]
    .map(([s, x, w]) => ({ s, x, w, h: 10 }));
  assert.equal(lineText(mixed), 'Made by النيل Cairo');
});

test('the tools read a made-up PDF: its files, its pages, its words in Arabic and English', { timeout: 120000 }, async () => {
  const ctx = await setup();
  const files = await callTool('list_files', {}, ctx);
  assert.ok(files.ok, files.error);
  assert.deepEqual(files.result.files.map(f => [f.file, f.kind, f.pages ?? null]), [['f1', 'pdf', 2], ['f2', 'text', null]]);

  const info = await callTool('pdf_info', { file: 'f1' }, ctx);
  assert.equal(info.result.pages, 2);
  assert.deepEqual(info.result.pages_without_text, []);

  const p1 = await callTool('read_page_text', { file: 'f1', page: 1 }, ctx);
  assert.match(p1.result.text, /Batch TP-24A117/);
  assert.match(p1.result.text, /شركة النيل التجريبية للأدوية/);
  assert.match(p1.result.text, /رقم التسجيل ١٢٣٤٥\/٢٠٢٥/);
  const far = await callTool('read_page_text', { file: 'f1', page: 9 }, ctx);
  assert.equal(far.ok, false);
  assert.match(far.error, /has 2 page/);

  const en = await callTool('find_in_files', { query: 'dissolution minutes' }, ctx);
  assert.deepEqual(en.result.hits.map(h => [h.file, h.page]), [['f1', 2]]);
  assert.match(en.result.hits[0].words, /«Dissolution»/);
  const ar = await callTool('find_in_files', { query: 'النيل التجريبية' }, ctx);
  assert.deepEqual(ar.result.hits.map(h => [h.file, h.page]), [['f1', 1]]);
  const txt = await callTool('find_in_files', { query: 'stability commitment' }, ctx);
  assert.deepEqual(txt.result.hits.map(h => h.file), ['f2']);
});

test('a fact is recorded only with words that are on its page, and every call is logged', { timeout: 120000 }, async () => {
  const ctx = await setup();
  const wrong = await callTool('record_fact', { field: 'batch', value: 'TP-24A118', file: 'f1', page: 1, quote: 'Batch TP-24A118' }, ctx);
  assert.equal(wrong.ok, false);
  assert.match(wrong.error, /not on page 1/);
  const elsewhere = await callTool('record_fact', { field: 'batch', value: 'TP-24A117', file: 'f1', page: 2, quote: 'Batch TP-24A117' }, ctx);
  assert.equal(elsewhere.ok, false);
  const right = await callTool('record_fact', { field: 'batch', value: 'TP-24A117', file: 'f1', page: 1, quote: 'Batch  TP-24A117' }, ctx);
  assert.ok(right.ok, right.error);
  const reg = await callTool('record_fact', { field: 'registration_number', value: '12345/2025', file: 'f1', page: 1, quote: 'رقم التسجيل ١٢٣٤٥/٢٠٢٥' }, ctx);
  assert.ok(reg.ok, reg.error);
  const facts = await callTool('list_facts', {}, ctx);
  assert.deepEqual(facts.result.facts.map(f => [f.field, f.value, f.page, f.by]), [['batch', 'TP-24A117', 1, 'test'], ['registration_number', '12345/2025', 1, 'test']]);
  assert.deepEqual(ctx.ws.log.map(e => [e.tool, e.ok]), [['record_fact', false], ['record_fact', false], ['record_fact', true], ['record_fact', true], ['list_facts', true]]);
  assert.equal(ctx.ws.undoLast(), true);
  assert.equal(ctx.ws.facts.length, 1);
  const bad = await callTool('record_fact', { field: 'batch', file: 'f1', page: 1, quote: 'x' }, ctx);
  assert.match(bad.error, /value is missing/);
  assert.equal((await callTool('no_such_tool', {}, ctx)).ok, false);
  assert.ok(!JSON.stringify(ctx.ws.toJSON()).includes('"bytes":{'), 'the saved workspace holds no file bytes');
});

test('the library through the tools: a requirement found in Arabic or English, with its source', async () => {
  const ctx = await setup();
  const en = await callTool('search_knowledge', { query: 'application form annex', authority: 'EG-EDA' }, ctx);
  assert.ok(en.result.results.some(r => r.id === 'EG-EDA/M1-01'), JSON.stringify(en.result).slice(0, 300));
  const ar = await callTool('search_knowledge', { query: 'نموذج الطلب', authority: 'EG-EDA' }, ctx);
  assert.ok(ar.result.results.some(r => r.id === 'EG-EDA/M1-01'));
  const rec = await callTool('get_record', { id: 'EG-EDA/M1-01' }, ctx);
  assert.equal(rec.result.ctd, '1.1.1');
  assert.ok(rec.result.sources.some(s => s.code === 'NP.CAPP.065'), JSON.stringify(rec.result.sources).slice(0, 300));
  assert.equal((await callTool('get_record', { id: 'NO/SUCH' }, ctx)).ok, false);
});

test('inside the page: the tools as claude.ai\'s sample takes them, and a paused or refused Claude', async () => {
  const ctx = await setup();
  const tools = sampleTools(ctx);
  assert.deepEqual(tools.map(t => t.name), TOOLS.map(t => t.name));
  const read = tools.find(t => t.name === 'read_page_text');
  assert.match((await read.execute({ file: 'f1', page: 2 })).text, /Assay/);
  await assert.rejects(read.execute({ file: 'f1', page: 0 }), /at least 1/);

  // a stand-in for sample(): it calls two tools the way Claude would, then answers
  const fake = async (prompt, opts) => {
    assert.match(prompt, /Dossier Builder/);
    const t = name => opts.tools.find(x => x.name === name);
    const hit = await t('find_in_files').execute({ query: 'batch' });
    await t('record_fact').execute({ field: 'batch', value: 'TP-24A117', file: hit.hits[0].file, page: hit.hits[0].page, quote: 'Batch TP-24A117' });
    return { text: 'Recorded the batch TP-24A117 from page 1.', truncated: false };
  };
  const done = await ask(fake, { task: 'Record the batch number of the certificate.', ctx });
  assert.equal(done.text, 'Recorded the batch TP-24A117 from page 1.');
  assert.equal(ctx.ws.facts.length, 1);

  const limited = async () => { throw Object.assign(new Error('limit'), { code: 'rate_limited', text: 'part' }); };
  assert.deepEqual(await ask(limited, { task: 'x', ctx }), { paused: true, reason: 'rate_limited', partial: 'part' });
  const refused = async () => { throw Object.assign(new Error('no'), { code: 'not_granted' }); };
  assert.deepEqual(await ask(refused, { task: 'x', ctx }), { unavailable: true, reason: 'not_granted' });
});

// The bridge as the Claude app runs it: a separate program speaking MCP over its standard input and output.
function bridge(root) {
  const child = spawn(process.execPath, [path.join(ROOT, 'bridge', 'mcp.mjs'), '--root', root], { cwd: ROOT, stdio: ['pipe', 'pipe', 'pipe'] });
  let buf = '';
  const waiting = new Map();
  const stray = [];
  child.stdout.on('data', d => {
    buf += d;
    let i;
    while ((i = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, i); buf = buf.slice(i + 1);
      const msg = JSON.parse(line);                 // anything that is not a JSON-RPC message fails the test here
      if (waiting.has(msg.id)) { waiting.get(msg.id)(msg); waiting.delete(msg.id); } else stray.push(msg);
    }
  });
  let next = 1;
  return {
    stray,
    request: (method, params) => new Promise(ok => { const id = next++; waiting.set(id, ok); child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n'); }),
    notify: (method, params) => child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method, params }) + '\n'),
    close: () => new Promise(ok => { child.on('exit', ok); child.stdin.end(); }),
  };
}

test('the bridge: the Claude app lists the same tools over MCP and runs them on a dossier folder', { timeout: 120000 }, async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'dossier-'));
  fs.mkdirSync(path.join(root, 'module3'));
  fs.writeFileSync(path.join(root, 'module3', 'coa.pdf'), await madeUpPdf());
  fs.writeFileSync(path.join(root, '.hidden'), 'not part of the dossier');
  const b = bridge(root);
  try {
    const init = await b.request('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'test', version: '1' } });
    assert.equal(init.result.protocolVersion, '2025-06-18');
    assert.equal(init.result.serverInfo.name, 'dossier-builder');
    assert.ok(init.result.capabilities.tools);
    b.notify('notifications/initialized');
    const list = await b.request('tools/list', {});
    assert.deepEqual(list.result.tools.map(t => t.name), TOOLS.map(t => t.name));
    const files = await b.request('tools/call', { name: 'list_files', arguments: {} });
    assert.equal(files.result.isError, false);
    assert.deepEqual(files.result.structuredContent.files.map(f => [f.name, f.kind, f.pages]), [['module3/coa.pdf', 'pdf', 2]]);
    const page = await b.request('tools/call', { name: 'read_page_text', arguments: { file: 'module3/coa.pdf', page: 1 } });
    assert.match(page.result.content[0].text, /TP-24A117/);
    const refused = await b.request('tools/call', { name: 'record_fact', arguments: { field: 'batch', value: 'X', file: 'f1', page: 1, quote: 'not there' } });
    assert.equal(refused.result.isError, true);
    assert.match(refused.result.content[0].text, /not on page 1/);
    const unknown = await b.request('tools/call', { name: 'delete_everything', arguments: {} });
    assert.equal(unknown.error.code, -32602);
    const nothing = await b.request('resources/list', {});
    assert.equal(nothing.error.code, -32601);
    assert.deepEqual(b.stray, [], 'nothing on standard output but answers');
  } finally { await b.close(); }
  assert.ok(fs.existsSync(path.join(root, 'module3', 'coa.pdf')), 'the dossier folder is left as it was');
});
