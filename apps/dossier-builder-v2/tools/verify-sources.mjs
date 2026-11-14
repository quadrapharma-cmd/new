// Part 1c: read the text of every source kept in the project and check each citation against it.
//   a quote          → is it in the source (word for word, or nearly)? on the page the citation names?
//   a place          → do the section numbers, pages, appendices, options and steps it names exist in the source?
//   the record itself → does its CTD number (or, for a variation, its wording) appear in the source?
// Writes knowledge/checks/citations.json (generated: never edit by hand). Texts are cached in dist/texts/.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { loadKnowledge, REPO, ROOT, KNOWLEDGE } from './load.mjs';
import { allRecords } from '../core/validate.js';
import { fold } from '../core/knowledge.js';

const CACHE = path.join(ROOT, 'dist', 'texts');

// ---------------------------------------------------------------- text of a source, page by page
async function pdfPages(file) {
  const { getDocument } = await import('pdfjs-dist/legacy/build/pdf.mjs');
  const task = getDocument({ data: new Uint8Array(fs.readFileSync(file)), disableFontFace: true, verbosity: 0, isEvalSupported: false });
  const doc = await task.promise;
  const pages = [];
  for (let p = 1; p <= doc.numPages; p++) {
    const page = await doc.getPage(p);
    const tc = await page.getTextContent();
    let s = '';
    for (const it of tc.items) s += it.str + (it.hasEOL ? '\n' : ' ');
    pages.push(s);
    page.cleanup();
  }
  await task.destroy();
  return pages;
}
function officeText(file) {
  const ext = path.extname(file).toLowerCase();
  if (ext === '.xlsx') {
    const py = 'import openpyxl,sys\nwb=openpyxl.load_workbook(sys.argv[1],read_only=True,data_only=True)\n' +
      'for ws in wb.worksheets:\n print("=== sheet",ws.title)\n for r in ws.iter_rows(values_only=True):\n  print(" | ".join("" if c is None else str(c) for c in r))';
    return [execFileSync('python3', ['-I', '-c', py, file], { maxBuffer: 1 << 28 }).toString()];
  }
  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'dbk-office-'));
  execFileSync('soffice', ['--headless', '--convert-to', 'txt:Text (encoded):UTF8', '--outdir', out, file], { stdio: 'ignore', timeout: 180000 });
  const txt = fs.readdirSync(out).find(f => f.endsWith('.txt'));
  const text = txt ? fs.readFileSync(path.join(out, txt), 'utf8') : '';
  fs.rmSync(out, { recursive: true, force: true });
  return [text];
}
async function zipPages(file) {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'dbk-zip-'));
  execFileSync('unzip', ['-q', '-o', file, '-d', out]);
  const pages = [];
  const walk = d => fs.readdirSync(d, { withFileTypes: true }).flatMap(e => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
  for (const f of walk(out).sort()) {
    const ext = path.extname(f).toLowerCase();
    if (ext === '.pdf') pages.push(...await pdfPages(f));
    else if (['.xlsx', '.docx', '.doc'].includes(ext)) pages.push(...officeText(f));
  }
  fs.rmSync(out, { recursive: true, force: true });
  return pages;
}
async function textOf(source) {
  const file = path.join(REPO, source.file);
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) return null;
  const sha = crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  const cached = path.join(CACHE, `${source.id}.json`);
  if (fs.existsSync(cached)) {
    const c = JSON.parse(fs.readFileSync(cached, 'utf8'));
    if (c.sha === sha) return c.pages;
  }
  const ext = path.extname(file).toLowerCase();
  let pages;
  if (ext === '.pdf') pages = await pdfPages(file);
  else if (ext === '.zip') pages = await zipPages(file);
  else if (['.xlsx', '.docx', '.doc'].includes(ext)) pages = officeText(file);
  else pages = [fs.readFileSync(file, 'utf8')];
  fs.mkdirSync(CACHE, { recursive: true });
  fs.writeFileSync(cached, JSON.stringify({ sha, pages }));
  return pages;
}

// ---------------------------------------------------------------- matching
const letters = s => fold(s).replace(/[^\p{L}\p{N}]+/gu, '');
const wordsOf = s => fold(s).match(/[\p{L}\p{N}]+/gu) || [];
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

class Text {
  constructor(pages) {
    this.pages = pages;
    this.flat = pages.map(letters);
    // «3.2. P.5.6» as some PDFs set it reads as 3.2.P.5.6
    this.folded = pages.map(p => fold(p).replace(/\s+/g, ' ').replace(/(\d)\.\s+(?=[a-z]\.\d)/g, '$1.'));
    this.words = [];
    this.pageOfWord = [];
    pages.forEach((p, i) => { for (const w of wordsOf(p)) { this.words.push(w); this.pageOfWord.push(i + 1); } });
    this.where = new Map();
    this.words.forEach((w, i) => { if (!this.where.has(w)) this.where.set(w, []); this.where.get(w).push(i); });
  }
  get chars() { return this.flat.reduce((n, p) => n + p.length, 0); }
  // Pages on which a phrase appears word for word (letters and digits only, so spacing and punctuation do not matter).
  pagesWith(phrase) {
    const k = letters(phrase);
    if (k.length < 4) return [];
    const hits = [];
    this.flat.forEach((p, i) => { if (p.includes(k)) hits.push(i + 1); });
    if (!hits.length) {   // across a page break
      for (let i = 0; i + 1 < this.flat.length; i++) if ((this.flat[i].slice(-k.length) + this.flat[i + 1].slice(0, k.length)).includes(k)) hits.push(i + 1);
    }
    return hits;
  }
  // The best share of a phrase's words found close together (for a phrase quoted with small differences).
  closest(phrase) {
    const ws = [...new Set(wordsOf(phrase).filter(w => w.length > 2))];
    if (ws.length < 4) return { share: 0 };
    const span = Math.ceil(ws.length * 1.6) + 4;
    const rare = ws.map(w => this.where.get(w) || []).filter(x => x.length).sort((a, b) => a.length - b.length)[0];
    if (!rare) return { share: 0 };
    let best = { share: 0 };
    const set = new Set(ws);
    for (const pos of rare.slice(0, 400)) {
      const from = Math.max(0, pos - span);
      const seen = new Set();
      for (let i = from; i < Math.min(this.words.length, pos + span); i++) if (set.has(this.words[i])) seen.add(this.words[i]);
      const share = seen.size / ws.length;
      if (share > best.share) best = { share, page: this.pageOfWord[pos] };
    }
    return best;
  }
  // A section number such as 1.1.6 or 3.2.P.8 — not inside a longer number. A CTD number also counts in its short
  // form (P.1 for 3.2.P.1), as EDA's own lists write it.
  hasNumber(num) {
    const forms = [num];
    const m = /^3\.2\.([SPA](?:\.\d+)*)$/i.exec(num);
    if (m) forms.push(m[1]);
    return forms.some(f => {
      const re = new RegExp(`(?<![\\w.])${esc(fold(f))}(?![\\w])(?!\\.\\d)`);
      return this.folded.some(p => re.test(p));
    });
  }
  // A wording the source may split into a heading and a lettered item: the longest run of its words, from either end,
  // found word for word, as a share of the whole.
  wording(phrase) {
    const ws = wordsOf(phrase);
    const total = letters(phrase).length;
    let best = 0;
    for (let i = 0; i < ws.length; i++) {
      const tail = ws.slice(i).join(' ');
      const head = ws.slice(0, ws.length - i).join(' ');
      for (const part of [tail, head]) {
        const k = letters(part).length;
        if (k >= 25 && k / total > best && this.pagesWith(part).length) best = k / total;
      }
      if (best) break;
    }
    return best;
  }
  // The first variation class (PAC-N, PAC-A, PAC-B, PAC-II) printed after a phrase — looked for after its section's
  // heading, since the same wording can sit under several sections.
  classAfter(phrase, section) {
    const k = letters(phrase);
    const all = this.flat.join('');
    let from = 0;
    if (section) {
      const head = new RegExp(`(?<![\\d.])${esc(section)}\\.?\\s+[a-z]`);
      const page = this.folded.findIndex(p => head.test(p));
      if (page >= 0) from = this.flat.slice(0, page).reduce((n, p) => n + p.length, 0);
    }
    const at = all.indexOf(k, from);
    if (at < 0) return null;
    const m = /pac(n|a|b|ii)/.exec(all.slice(at + k.length, at + k.length + 400));
    return m ? `PAC-${m[1].toUpperCase()}` : null;
  }
  hasPhrase(ph) { const k = fold(ph).replace(/\s+/g, ' '); return this.folded.some(p => p.includes(k)); }
}

// What a citation's place names, as things one can look for.
function placeTokens(at) {
  const t = { numbers: [], pages: [], phrases: [] };
  if (!at) return t;
  const s = String(at);
  for (const m of s.matchAll(/(?<![\w.\/])(\d{1,2}(?:\.[0-9A-Z]{1,3}){1,6})(?![\w])(?!\.\d)/g)) {
    if (/^\d{1,2}\.\d{1,2}$/.test(m[1]) && /\d{1,2}\/\d{4}/.test(s)) continue;
    t.numbers.push(m[1]);
  }
  for (const m of s.matchAll(/\bp\.?\s*(\d+)(?:\s*[-–]\s*(\d+))?((?:\s*,\s*\d+)*)/g)) {
    t.pages.push(+m[1]);
    if (m[2]) t.pages.push(+m[2]);
    for (const x of (m[3] || '').split(',').map(Number).filter(Boolean)) t.pages.push(x);
  }
  for (const m of s.matchAll(/\b(Appendix|Appendices|App\.|Annex)\s*((?:[0-9]+|[IVX]+)(?:\s*,\s*(?:[0-9]+|[IVX]+))*)/g)) {
    const word = /^App/.test(m[1]) ? 'appendix' : 'annex';
    for (const x of m[2].split(',').map(v => v.trim())) t.phrases.push(`${word} ${x}`);
  }
  for (const m of s.matchAll(/\b(Option|Step)\s+(\d+)/gi)) t.phrases.push(`${m[1]} ${m[2]}`);
  return t;
}

// The variation tool: a table of sections (Human, Herbal, Veterinary), each numbered from 1.
function variationRow(pages, at) {
  const m = /^(\w+),\s*ID\s*(\d+)$/.exec(at || '');
  if (!m) return null;
  const text = pages.join('\n');
  const rows = [];
  let row = [], cell = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) { if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; } else if (ch === '"') q = false; else cell += ch; }
    else if (ch === '"') q = true;
    else if (ch === ',') { row.push(cell); cell = ''; }
    else if (ch === '\n') { row.push(cell); rows.push(row); row = []; cell = ''; }
    else if (ch !== '\r') cell += ch;
  }
  if (row.length || cell) { row.push(cell); rows.push(row); }
  const head = rows[0].map(h => h.replace(/^﻿/, ''));
  const col = n => head.indexOf(n);
  return rows.slice(1).find(r => r[col('Section')] === m[1] && r[col('ID')] === m[2]) ? Object.fromEntries(head.map((h, i) => [h, rows.slice(1).find(r => r[col('Section')] === m[1] && r[col('ID')] === m[2])[i]])) : undefined;
}

// ---------------------------------------------------------------- one citation
function check(rec, c, field, text, source) {
  const out = { rec: rec.id, field, src: c.src, ...(c.at ? { at: c.at } : {}) };
  if (!source.held) return { ...out, result: 'no-copy' };
  if (!text || text.chars < 200) return { ...out, result: 'no-text' };
  const notes = [];
  let strong = 0, found = 0, looked = 0;

  if (source.id === 'eda-variation-tool') {
    const row = variationRow(text.pages, c.at);
    looked++;
    if (!row) notes.push(`no row «${c.at}» in the table`);
    else if (letters(row['Variation request']) === letters(rec.title?.en)) { found++; strong++; }
    else notes.push(`row «${c.at}» reads «${row['Variation request']}»`);
  }

  if (c.quote) {
    const parts = String(c.quote).split(/\s*(?:·|…|\.\.\.|;)\s*/).filter(p => letters(p).length >= 10);
    let exact = 0, close = 0;
    const pages = new Set();
    for (const p of parts) {
      const hit = text.pagesWith(p);
      if (hit.length) { exact++; hit.forEach(x => pages.add(x)); continue; }
      const near = text.closest(p);
      if (near.share >= 0.85) { close++; pages.add(near.page); } else notes.push(`quote not found: «${p.slice(0, 70)}»`);
    }
    looked++;
    if (parts.length && exact + close === parts.length) { found++; strong++; out.quote = exact === parts.length ? 'exact' : 'close'; }
    else if (exact + close) { out.quote = 'part'; }
    else out.quote = parts.length ? 'missing' : 'short';
    if (pages.size) out.pages = [...pages].sort((a, b) => a - b).slice(0, 6);
  }

  // A variation's class: the class printed right after the guideline item the record quotes must be the record's own.
  if (rec.kind === 'variation' && rec.guideline?.pac && c.quote && source.id === 'eda-gl-capp-026-v6') {
    looked++;
    const pac = text.classAfter(rec.guideline.item || c.quote, rec.guideline.section);
    if (pac === rec.guideline.pac) { found++; out.pac = pac; }
    else notes.push(pac ? `the guideline prints ${pac} after this item, the record says ${rec.guideline.pac}` : 'no class found after the item');
  }

  const tk = placeTokens(c.at);
  for (const num of tk.numbers) { looked++; if (text.hasNumber(num)) found++; else notes.push(`section ${num} not found`); }
  for (const ph of tk.phrases) { looked++; if (text.hasPhrase(ph)) found++; else notes.push(`«${ph}» not found`); }
  for (const pg of tk.pages) { looked++; if (pg <= text.pages.length) found++; else notes.push(`page ${pg} is past the end (${text.pages.length} pages)`); }
  if (tk.pages.length && out.pages && c.quote && !out.pages.some(p => tk.pages.some(q => Math.abs(p - q) <= 1))) {
    notes.push(`the quote is on page ${out.pages.join(', ')}, the citation says ${tk.pages.join(', ')}`);
  }

  // The record's own number or wording, when the citation names no place — only in a source that sets the numbers.
  if (!tk.numbers.length && !c.quote && source.id !== 'eda-variation-tool' && (source.numbering || rec.kind === 'variation')) {
    if (rec.kind === 'variation' && rec.title?.en) {
      looked++;
      const share = text.pagesWith(rec.title.en).length ? 1 : text.wording(rec.title.en);
      if (share >= 0.5) { found++; if (share < 1) out.wording = Math.round(share * 100) / 100; }
      else notes.push('the variation\'s wording not found');
    } else if (field === 'ectd_cite') {
      for (const n of rec.ectd || []) { looked++; if (text.hasNumber(n.split(/[–-]/)[0])) found++; else notes.push(`eCTD node ${n} not found`); }
    } else if (rec.ctd && /^\d/.test(rec.ctd) && rec.kind === 'requirement') {
      for (const part of String(rec.ctd).split(/\s*·\s*/)) {
        const num = part.split(/[–-]/)[0].replace(/\s*\(.*\)$/, '').replace(/\.x$/i, '').trim();
        looked++;
        if (text.hasNumber(num)) found++; else notes.push(`section ${num} not found`);
      }
    }
  }

  let result;
  // A page whose text layer cannot be read by machine, read from its image by a person (recorded on the citation).
  if (c.read && !(strong && !notes.length)) return { ...out, result: 'read', read: c.read, ...(notes.length ? { notes } : {}) };
  if (!looked) result = 'nothing-to-check';
  else if (strong && !notes.length) result = 'verified';
  else if (found === looked) result = 'located';
  else if (found) result = 'partly';
  else result = 'not-found';
  return { ...out, result, ...(notes.length ? { notes } : {}) };
}

function innerCites(node, out = []) {
  if (Array.isArray(node)) node.forEach(x => innerCites(x, out));
  else if (node && typeof node === 'object') {
    if (node.cite) out.push(...node.cite);
    for (const [k, v] of Object.entries(node)) if (k !== 'cite') innerCites(v, out);
  }
  return out;
}

export async function verify({ quiet = false } = {}) {
  const log = quiet ? () => {} : console.log;
  const data = loadKnowledge();
  const sources = new Map(data.sources.map(s => [s.id, s]));
  const texts = new Map();
  for (const s of data.sources.filter(x => x.held)) {
    try {
      const pages = await textOf(s);
      texts.set(s.id, pages ? new Text(pages) : null);
      log(`text  ${s.id.padEnd(40)} ${pages ? `${pages.length} page(s)` : 'no file'}`);
    } catch (e) {
      texts.set(s.id, null);
      log(`text  ${s.id.padEnd(40)} could not be read: ${e.message.split('\n')[0]}`);
    }
  }
  const results = [];
  for (const rec of allRecords(data)) {
    for (const field of ['cite', 'ectd_cite', 'anchor_cite']) {
      for (const c of rec[field] || []) results.push(check(rec, c, field, texts.get(c.src), sources.get(c.src)));
    }
    for (const c of innerCites(rec.required)) results.push(check(rec, c, 'case', texts.get(c.src), sources.get(c.src)));
  }
  const per = {};
  for (const s of data.sources) {
    const t = texts.get(s.id);
    per[s.id] = { held: !!s.held, pages: t ? t.pages.length : 0, readable: !!(t && t.chars >= 200), citations: 0 };
  }
  for (const r of results) { per[r.src].citations++; per[r.src][r.result] = (per[r.src][r.result] || 0) + 1; }
  const summary = {};
  for (const r of results) summary[r.result] = (summary[r.result] || 0) + 1;
  const report = {
    note: 'Generated by tools/verify-sources.mjs — do not edit by hand.',
    generated: new Date().toISOString().slice(0, 10),
    summary, sources: per, citations: results,
  };
  fs.mkdirSync(path.join(KNOWLEDGE, 'checks'), { recursive: true });
  fs.writeFileSync(path.join(KNOWLEDGE, 'checks', 'citations.json'), JSON.stringify(report, null, 1) + '\n');
  log('\n' + Object.entries(summary).map(([k, v]) => `${k} ${v}`).join(' · '));
  return report;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  verify().catch(e => { console.error(e); process.exit(1); });
}
