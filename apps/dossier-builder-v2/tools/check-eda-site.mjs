// EDA's website: which documents it publishes now, and whether each EDA source the knowledge rests on is still the copy
// EDA publishes. The operator's routine check (see CLAUDE.md).
//   node tools/check-eda-site.mjs           read the website and report; nothing is written
//   node tools/check-eda-site.mjs --save    also keep this reading as the baseline the next check compares with
//                                           (knowledge/checks/eda-site.json), and date the «latest» check of every source
//                                           whose copy is still the one EDA publishes
//   node tools/check-eda-site.mjs --json    the report as JSON
// It reads EDA's two index pages (regulatory guidelines; notices to applicants), each department page they link to, and every
// document link on those pages with the row it sits in (type, date, title, version). Only the HTML pages are fetched, with
// curl (which follows the proxy settings); no document is downloaded. A source that is no longer at its address is reported
// with the published documents that look most like it: a person decides whether one of them is its new version.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { loadKnowledge, ROOT } from './load.mjs';

export const SITE = 'https://www.edaegypt.gov.eg';
export const INDEXES = [
  { kind: 'guidelines', segment: 'الأدلة-التنظيمية', url: `${SITE}/ar/المرجع-التنظيمي-لهيئة-الدواء-المصرية/الأدلة-التنظيمية/` },
  { kind: 'notices', segment: 'اشعارات-متلقى-الخدمة', url: `${SITE}/ar/المرجع-التنظيمي-لهيئة-الدواء-المصرية/اشعارات-متلقى-الخدمة/` },
];
export const BASELINE = path.join(ROOT, 'knowledge', 'checks', 'eda-site.json');
const SOURCES = path.join(ROOT, 'knowledge', 'sources.yaml');
const LINK = /<a\b[^>]*?href\s*=\s*"([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi;
const DOC = /\.(pdf|docx?|xlsx?|zip|rar)(?:[?#]|$)/i;

const decode = s => { try { return decodeURIComponent(s); } catch { return s; } };
const entities = s => s.replace(/&nbsp;/g, ' ').replace(/&quot;/g, '"').replace(/&#39;|&#x27;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>')
  .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(+n)).replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16))).replace(/&amp;/g, '&');
const text = h => entities(h.replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ').trim();
const abs = href => new URL(entities(href).trim(), SITE + '/').href;
const fileOf = url => decode(new URL(url).pathname.split('/').filter(Boolean).pop() || '');
// One key per page, however its address is escaped.
const pageKey = url => decode(new URL(url).pathname).replace(/\/+$/, '').toLowerCase();

// One key per document, whatever the host is spelt (with or without www) and however the address is escaped.
export function docKey(url) {
  try {
    const p = decode(new URL(url, SITE + '/').pathname).toLowerCase();
    const i = p.indexOf('/media/');
    return i < 0 ? null : p.slice(i);
  } catch { return null; }
}

// The department pages an index page links to: addresses one step or more below the index's own segment.
export function subPages(html, segment) {
  const out = [];
  for (const m of html.matchAll(LINK)) {
    let url;
    try { url = abs(m[1]); } catch { continue; }
    if (!url.startsWith(SITE) && !url.startsWith(SITE.replace('www.', ''))) continue;
    const p = decode(new URL(url).pathname);
    const i = p.indexOf(`/${segment}/`);
    if (i < 0 || DOC.test(p)) continue;
    const rest = p.slice(i + segment.length + 2).replace(/\/+$/, '');
    if (!rest || out.some(x => pageKey(x.url) === pageKey(url))) continue;
    out.push({ url, title: text(m[2]) || rest.replace(/-/g, ' ') });
  }
  return out;
}

const cellsOf = row => [...row.matchAll(/<t[dh]\b[^>]*>([\s\S]*?)<\/t[dh]>/gi)].map(c => c[1]);
// A table's header names its columns; the columns are matched by their names, whatever their order.
function fieldsOf(head, cells) {
  const f = {};
  head.forEach((h, i) => {
    const v = cells[i] || '';
    if (!v) return;
    if (/تاريخ|date/i.test(h)) f.date ??= v;
    else if (/رقم|إصدار|اصدار|أصدار|version/i.test(h)) f.version ??= v;
    else if (/النوع|type/i.test(h)) f.type ??= v;
    else if (/الوصف|الاسم|الأسم|بشأن|العنوان|title|name/i.test(h)) f.title ??= v;
  });
  return f;
}
// The heading a table or a link sits under: the last bold line or heading before it, outside any table.
function sectionBefore(outside, at) {
  let last = '';
  for (const m of outside.slice(0, at).matchAll(/<(strong|b|h[2-4])\b[^>]*>([\s\S]*?)<\/\1>/gi)) { const t = text(m[2]); if (t) last = t; }
  return last;
}

// Every document a department page links to, with what its row says about it.
export function documents(html) {
  const found = [];
  const seen = new Set();
  const add = (at, href, linkHtml, f = {}) => {
    let url;
    try { url = abs(href); } catch { return; }
    const key = docKey(url) || url;
    if (seen.has(key)) return;
    seen.add(key);
    found.push({ at, url, file: fileOf(url), title: text(linkHtml) || f.title || '', type: f.type || '', date: f.date || '',
                 version: f.version || '', section: f.section || '' });
  };
  const outside = html.replace(/<table\b[\s\S]*?<\/table>/gi, m => ' '.repeat(m.length));
  for (const t of html.matchAll(/<table\b[\s\S]*?<\/table>/gi)) {
    const rows = [...t[0].matchAll(/<tr\b[\s\S]*?<\/tr>/gi)];
    if (!rows.length) continue;
    const head = cellsOf(rows[0][0]).map(text);
    const section = sectionBefore(outside, t.index);
    for (const r of rows) {
      const links = [...r[0].matchAll(LINK)].filter(l => DOC.test(l[1]));
      if (!links.length) continue;
      const f = { section, ...fieldsOf(head, cellsOf(r[0]).map(text)) };
      for (const l of links) add(t.index + r.index + l.index, l[1], l[2], f);
    }
  }
  for (const l of outside.matchAll(LINK)) if (DOC.test(l[1])) add(l.index, l[1], l[2], { section: sectionBefore(outside, l.index) });
  return found.sort((a, b) => a.at - b.at).map(({ at, ...d }) => d);
}

// How alike two documents' names are, from the words of their file names (and a source's code): 0 to 1.
const STOP = new Set(['pdf', 'doc', 'docx', 'xlsx', 'final', 'en', 'ar', 'up', 'the', 'of', 'for', 'and', 'in', 'on', 'to', 'version',
  'ver', 'edition', 'guideline', 'guidelines', 'guide', 'line', 'guidline', 'egyptian', 'human', 'pharmaceutical', 'pharmaceuticals',
  'products', 'product', 'notice', 'note', 'applicant', 'applicants', 'eda', 'compressed', 'new', 'updated', 'update', 'gl', 'np', 'edrex']);
const words = s => [...new Set(decode(s).toLowerCase().split(/[^\p{L}\p{N}]+/u)
  .filter(w => w.length > 1 && !STOP.has(w) && !/^(19|20)\d\d$/.test(w)))];
const same = (a, b) => a === b || (a.length >= 5 && b.length >= 5 && (a.startsWith(b) || b.startsWith(a)));
export function likeness(a, b) {
  if (!a.length || !b.length) return 0;
  const hit = a.filter(x => b.some(y => same(x, y))).length;
  return (2 * hit) / (a.length + b.length);
}
function candidates(source, docs) {
  const mine = [...new Set([...words(fileOf(source.url)), ...words((source.code || '').replace(/\./g, ' '))])];
  return docs.map(d => ({ d, score: likeness(mine, words(d.file)) }))
    .filter(x => x.score >= 0.34).sort((a, b) => b.score - a.score).slice(0, 3)
    .map(({ d, score }) => ({ ...d, score: Math.round(score * 100) / 100 }));
}

// The EDA sources with a document address, against the documents read now and the baseline of the last check.
export function compare({ sources, docs, previous }) {
  const now = new Map(docs.map(d => [docKey(d.url) || d.url, d]));
  const report = { published: [], missing: [], added: [], removed: [], changed: [] };
  for (const s of sources) {
    if (s.authority !== 'EG-EDA' || !s.url || !docKey(s.url)) continue;
    if (s.status === 'superseded' || s.superseded_by) continue;
    const d = now.get(docKey(s.url));
    const entry = { id: s.id, code: s.code || '', version: s.version || '', url: s.url, latest: s.latest || null };
    if (d) report.published.push({ ...entry, doc: d });
    else report.missing.push({ ...entry, candidates: candidates(s, docs) });
  }
  if (previous) {
    const before = new Map(previous.documents.map(d => [docKey(d.url) || d.url, d]));
    for (const [k, d] of now) {
      const p = before.get(k);
      if (!p) report.added.push(d);
      else if (['title', 'date', 'version'].some(f => (p[f] || '') !== (d[f] || ''))) report.changed.push({ before: p, now: d });
    }
    for (const [k, p] of before) if (!now.has(k)) report.removed.push(p);
  }
  return report;
}

// Dates the «latest» check of the given sources in sources.yaml, touching nothing else.
export function dateLatest(yamlText, ids, on) {
  let out = yamlText;
  const dated = [];
  for (const id of ids) {
    const esc = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp(`(^- id: ${esc}\\n(?:(?!- id: ).*\\n)*?  latest: \\{on: ")(\\d{4}-\\d{2}-\\d{2})(")`, 'm');
    out = out.replace(re, (m, a, d, b) => { dated.push(id); return a + on + b; });
  }
  return { text: out, dated };
}

function fetchPage(url) {
  return execFileSync('curl', ['-sS', '-f', '-L', '-m', '90', '--retry', '2', '--retry-delay', '3', url],
    { encoding: 'utf8', maxBuffer: 64 << 20, stdio: ['ignore', 'pipe', 'pipe'] });
}

export function readSite(fetch = fetchPage) {
  const pages = [];
  const failed = [];
  for (const ix of INDEXES) {
    let html;
    try { html = fetch(ix.url); } catch (e) { throw new Error(`EDA's ${ix.kind} page could not be read (${String(e.stderr || e.message).trim().split('\n')[0]})`); }
    const subs = subPages(html, ix.segment);
    if (!subs.length) throw new Error(`EDA's ${ix.kind} page links to no department page: the website may have changed its layout`);
    for (const s of subs) if (!pages.some(p => pageKey(p.url) === pageKey(s.url))) pages.push({ ...s, kind: ix.kind });
  }
  const docs = [];
  const seen = new Set();
  const signatures = new Set();
  const read = [];
  for (const p of pages) {
    let html;
    try { html = fetch(p.url); } catch (e) { failed.push({ ...p, error: String(e.stderr || e.message).trim().split('\n')[0] }); continue; }
    const list = documents(html);
    // the same department is linked from both indexes under two addresses: kept once
    const sig = list.map(d => docKey(d.url) || d.url).sort().join('|');
    if (sig && signatures.has(sig)) continue;
    signatures.add(sig);
    read.push({ ...p, documents: list.length });
    for (const d of list) {
      const k = docKey(d.url) || d.url;
      if (seen.has(k)) continue;
      seen.add(k);
      docs.push({ ...d, page: p.title, kind: p.kind });
    }
  }
  return { pages: read, docs, failed };
}

const today = () => new Date().toISOString().slice(0, 10);
const show = d => `${d.title || d.file}${d.version ? ` — v${d.version}` : ''}${d.date ? `, ${d.date}` : ''}  [${d.page || d.section || ''}]\n      ${decode(d.url)}`;

function main() {
  const args = new Set(process.argv.slice(2));
  const data = loadKnowledge();
  const previous = fs.existsSync(BASELINE) ? JSON.parse(fs.readFileSync(BASELINE, 'utf8')) : null;
  let site;
  try { site = readSite(); } catch (e) { console.error(`${e.message}. Nothing was written.`); process.exit(1); }
  const report = compare({ sources: data.sources, docs: site.docs, previous });
  const on = today();
  if (args.has('--json')) {
    console.log(JSON.stringify({ on, pages: site.pages, failed: site.failed, documents: site.docs.length, ...report }, null, 1));
  } else {
    const kinds = k => site.docs.filter(d => d.kind === k).length;
    console.log(`EDA website read on ${on}: ${site.pages.length} department pages, ${site.docs.length} documents (guidelines ${kinds('guidelines')}, notices ${kinds('notices')}).`);
    for (const f of site.failed) console.log(`  ! not read: ${f.title} (${f.error})`);
    console.log(`EDA sources with a document address: ${report.published.length + report.missing.length}`);
    console.log(`  still published as kept: ${report.published.length}`);
    console.log(`  not at their address any more — look for a new version: ${report.missing.length}`);
    for (const m of report.missing) {
      console.log(`    ${m.id}  ${m.code} v${m.version}\n      was ${decode(m.url)}`);
      for (const c of m.candidates) console.log(`      maybe (${c.score}): ${show(c)}`);
      if (!m.candidates.length) console.log('      nothing published looks like it');
    }
    if (previous) {
      console.log(`Since the last check (${previous.checked_on}): ${report.added.length} new, ${report.removed.length} removed, ${report.changed.length} changed.`);
      for (const d of report.added) console.log(`  + ${show(d)}`);
      for (const d of report.removed) console.log(`  - ${show(d)}`);
      for (const c of report.changed) console.log(`  ~ ${show(c.now)}\n      was: ${c.before.title} v${c.before.version} ${c.before.date}`);
    } else console.log('No earlier check is kept: run with --save to keep this one as the baseline.');
  }
  if (!args.has('--save')) { if (!args.has('--json')) console.log('Nothing was written (--save keeps this reading as the baseline).'); return; }
  if (site.failed.length && !args.has('--force')) { console.error('Some pages were not read: the baseline was not saved (--force saves it anyway).'); process.exit(1); }
  if (previous && site.docs.length < previous.documents.length / 2 && !args.has('--force')) {
    console.error(`Only ${site.docs.length} documents against ${previous.documents.length} last time: the website may have changed its layout. Not saved (--force saves it anyway).`);
    process.exit(1);
  }
  // addresses kept as they read (Arabic, not escaped), one document per line so the next check's changes show plainly
  const readable = u => { try { return decodeURI(u); } catch { return u; } };
  const lines = site.docs.map(d => ' ' + JSON.stringify({ ...d, url: readable(d.url) })).join(',\n');
  const pages = site.pages.map(p => ' ' + JSON.stringify({ kind: p.kind, title: p.title, url: readable(p.url), documents: p.documents ?? null })).join(',\n');
  fs.writeFileSync(BASELINE, `{"checked_on": ${JSON.stringify(on)},\n"pages": [\n${pages}\n],\n"documents": [\n${lines}\n]}\n`);
  const current = report.published.filter(p => p.latest?.result === 'current').map(p => p.id);
  const { text: yamlText, dated } = dateLatest(fs.readFileSync(SOURCES, 'utf8'), current, on);
  fs.writeFileSync(SOURCES, yamlText);
  console.log(`Saved knowledge/checks/eda-site.json (${site.docs.length} documents) and dated the «latest» check of ${dated.length} sources ${on}.`);
  console.log('Then: npm run build && npm test, and publish the library if anything changed.');
}

if (process.argv[1] === fileURLToPath(import.meta.url)) main();
