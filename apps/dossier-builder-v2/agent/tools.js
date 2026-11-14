// The program's operations as tools, written once and used by both ways Claude reaches the program (docs/PART-2-PLAN.md §3.4,
// §3.8): inside the page (claude.ai's `sample`, the tools are page functions) and through the bridge (an MCP server, the Claude
// app's extension). Each tool: a name, its title in Arabic and English for the interface, a description for Claude, the input
// it takes (agent/schema.js checks it before the tool runs), whether it changes the dossier, and run(input, ctx).
// ctx: { ws: the workspace (agent/workspace.js), pdfjs: the pdf.js module, knowledge: core/knowledge.js over the library's data }.
// Nothing here reaches a disk or the network; a document of another party is never changed by any tool.
import { fold } from '../core/fold.js';
import { parseQuery, preparePages, findInPages } from '../core/search.js';
import { pageTextOf } from '../core/pdftext.js';

export class ToolError extends Error {}
const fail = msg => { throw new ToolError(msg); };
const squeeze = s => fold(s).replace(/\s+/g, '');
const TEXT_LIMIT = 12000;

// ------------------------------------------------------------------------------------------------ PDF, through pdf.js
async function pdfOf(ctx, file) {
  if (file.kind !== 'pdf') fail(`«${file.name}» is not a PDF (it is ${file.kind}); this tool reads PDFs`);
  const key = `${file.id}:pdf`;
  if (!ctx.ws.cache.has(key)) {
    const task = ctx.pdfjs.getDocument({ data: file.bytes.slice(), isEvalSupported: false, useSystemFonts: false, verbosity: 0 });
    ctx.ws.cache.set(key, task.promise.catch(e => {
      ctx.ws.cache.delete(key);
      fail(e?.name === 'PasswordException' ? `«${file.name}» asks for a password to open` : `«${file.name}» could not be opened as a PDF: ${e?.message || e}`);
    }));
  }
  return ctx.ws.cache.get(key);
}

async function pageText(ctx, file, n) {
  if (file.kind === 'text') {
    if (n !== 1) fail(`«${file.name}» is a text file: it has one page`);
    return new TextDecoder().decode(file.bytes);
  }
  const doc = await pdfOf(ctx, file);
  if (n > doc.numPages) fail(`«${file.name}» has ${doc.numPages} page(s), not ${n}`);
  const key = `${file.id}:text:${n}`;
  if (!ctx.ws.cache.has(key)) {
    ctx.ws.cache.set(key, pageTextOf(await (await doc.getPage(n)).getTextContent()));
  }
  return ctx.ws.cache.get(key);
}

async function pagesOf(ctx, file) {
  if (file.kind === 'text') return [await pageText(ctx, file, 1)];
  const doc = await pdfOf(ctx, file);
  const out = [];
  for (let n = 1; n <= doc.numPages; n++) out.push(await pageText(ctx, file, n));
  return out;
}

const scanned = text => text.replace(/\s/g, '').length < 20;
const plain = html => html.replace(/<mark>/g, '«').replace(/<\/mark>/g, '»').replace(/<[^>]+>/g, '')
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
const title = t => (t && typeof t === 'object' ? { en: t.en, ar: t.ar } : t);

// ------------------------------------------------------------------------------------------------ the tools
const FILE = { type: 'string', description: 'the file id from list_files (f1, f2…)', minLength: 1, maxLength: 300 };
const PAGE = { type: 'integer', minimum: 1, maximum: 100000, description: 'page number, 1 for the first page' };

export const TOOLS = [
  {
    name: 'list_files',
    title: { ar: 'ملفات الملف', en: 'Files in the dossier' },
    description: 'Lists the files of the dossier being prepared: id, name, kind (read from the file\'s content, never from its name), size in bytes, and for a PDF its number of pages.',
    input: { type: 'object', properties: {}, additionalProperties: false },
    writes: false,
    async run(_, ctx) {
      const out = [];
      for (const f of ctx.ws.files) {
        const row = { file: f.id, name: f.path, kind: f.kind, bytes: f.size };
        if (f.kind === 'pdf') { try { row.pages = (await pdfOf(ctx, f)).numPages; } catch (e) { row.problem = e.message; } }
        out.push(row);
      }
      return { files: out };
    },
  },
  {
    name: 'pdf_info',
    title: { ar: 'معلومات الـ PDF', en: 'PDF details' },
    description: 'Details of one PDF: pages, PDF version, whether it is encrypted, its title/author/producer, and which pages have no text layer (scanned pages, which must be read as images).',
    input: { type: 'object', properties: { file: FILE }, required: ['file'], additionalProperties: false },
    writes: false,
    async run({ file }, ctx) {
      const f = ctx.ws.file(file);
      const doc = await pdfOf(ctx, f);
      const { info = {} } = await doc.getMetadata().catch(() => ({}));
      const noText = [];
      for (let n = 1; n <= doc.numPages; n++) if (scanned(await pageText(ctx, f, n))) noText.push(n);
      return { file: f.id, name: f.path, pages: doc.numPages, pdf_version: info.PDFFormatVersion || null, encrypted: !!info.EncryptFilterName,
               title: info.Title || null, author: info.Author || null, producer: info.Producer || null,
               pages_without_text: noText.length > 40 ? { count: noText.length, first: noText.slice(0, 40) } : noText };
    },
  },
  {
    name: 'read_page_text',
    title: { ar: 'نص صفحة', en: 'Text of a page' },
    description: 'The text layer of one page of a PDF (or of a text file, page 1), as the file holds it. A scanned page has no text layer: the result says so, and the page must be read as an image.',
    input: { type: 'object', properties: { file: FILE, page: PAGE }, required: ['file', 'page'], additionalProperties: false },
    writes: false,
    async run({ file, page }, ctx) {
      const f = ctx.ws.file(file);
      const text = await pageText(ctx, f, page);
      if (scanned(text)) return { file: f.id, page, text: '', no_text_layer: true, note: 'this page is scanned: it has no text to read here' };
      return { file: f.id, page, text: text.slice(0, TEXT_LIMIT), ...(text.length > TEXT_LIMIT ? { truncated: true, chars: text.length } : {}) };
    },
  },
  {
    name: 'find_in_files',
    title: { ar: 'دوّر جوه الملفات', en: 'Search inside the files' },
    description: 'Searches the text of the dossier\'s files for words (Arabic or English; the library\'s glossary also finds the other language\'s words). Every word must be on the page. Returns the best pages with the words around the hit, the hits marked «like this».',
    input: { type: 'object', properties: { query: { type: 'string', minLength: 1, maxLength: 300 },
             files: { type: 'array', items: FILE, maxItems: 200, description: 'only these files (default: all)' },
             limit: { type: 'integer', minimum: 1, maximum: 50, description: 'pages to return (default 10)' } },
             required: ['query'], additionalProperties: false },
    writes: false,
    async run({ query, files, limit = 10 }, ctx) {
      const { groups } = ctx.knowledge ? ctx.knowledge.parse(query) : parseQuery(query);
      if (!groups.length) fail('the query has no words to look for');
      const hits = [], skipped = [];
      for (const f of files ? files.map(id => ctx.ws.file(id)) : ctx.ws.files) {
        if (f.kind !== 'pdf' && f.kind !== 'text') { skipped.push({ file: f.id, kind: f.kind }); continue; }
        const found = findInPages(preparePages(await pagesOf(ctx, f)), groups, { limit });
        for (const p of found.pages) hits.push({ file: f.id, name: f.path, page: p.page, score: p.score, words: plain(p.html) });
      }
      hits.sort((a, b) => b.score - a.score);
      return { hits: hits.slice(0, limit).map(({ score, ...h }) => h), ...(skipped.length ? { not_searched: skipped } : {}) };
    },
  },
  {
    name: 'search_knowledge',
    title: { ar: 'دوّر في المكتبة', en: 'Search the library' },
    description: 'Searches the program\'s knowledge (the authorities\' requirements, EDA\'s review questions and variations, document types, sources) in Arabic or English. Returns record ids with their titles; get_record gives one record with its sources.',
    input: { type: 'object', properties: { query: { type: 'string', minLength: 1, maxLength: 300 },
             kind: { type: 'string', enum: ['requirement', 'rule', 'variation', 'doctype', 'country', 'source'], description: 'only this kind' },
             authority: { type: 'string', maxLength: 40, description: 'only this authority, e.g. EG-EDA, ICH, EU-EMA' },
             limit: { type: 'integer', minimum: 1, maximum: 50 } },
             required: ['query'], additionalProperties: false },
    writes: false,
    async run({ query, kind, authority, limit = 15 }, ctx) {
      if (!ctx.knowledge) fail('the library is not loaded here');
      return { results: ctx.knowledge.search(query, { kind, authority, limit }).map(({ type, id, kind: k, item }) =>
        ({ id, kind: type === 'source' ? 'source' : k, title: title(item.title) || item.name || null, ...(item.ctd ? { ctd: item.ctd } : {}),
           ...(item.code ? { code: item.code } : {}), ...(item.status ? { status: item.status } : {}) })) };
    },
  },
  {
    name: 'get_record',
    title: { ar: 'سجل من المكتبة', en: 'A library record' },
    description: 'One record of the program\'s knowledge (a requirement, a review question, a variation, a document type…) with what it asks and the sources it rests on: each source\'s code, version and title, the place in it, and its own words where the record quotes them.',
    input: { type: 'object', properties: { id: { type: 'string', minLength: 1, maxLength: 120 } }, required: ['id'], additionalProperties: false },
    writes: false,
    async run({ id }, ctx) {
      if (!ctx.knowledge) fail('the library is not loaded here');
      const r = ctx.knowledge.record(id);
      if (!r) fail(`no record «${id}» in the library (search_knowledge finds ids)`);
      const keep = ['id', 'kind', 'authority', 'set', 'module', 'ctd', 'ectd', 'status', 'acceptance', 'note', 'applies', 'doc_class',
                    'produced_by', 'question', 'deficiency', 'conditions', 'requirements', 'type', 'validity'];
      const out = { title: title(r.title) || r.name || null };
      for (const k of keep) if (r[k] != null && r[k] !== '') out[k] = r[k];
      out.sources = ctx.knowledge.citations(r).map(c => ({ source: c.src, code: c.source?.code || null, version: c.source?.version || null,
        title: title(c.source?.title) || null, status: c.source?.status || null, at: c.at || null,
        ...(c.quote ? { quote: c.quote } : {}), ...(c.gist ? { gist: c.gist } : {}) }));
      return out;
    },
  },
  {
    name: 'record_fact',
    title: { ar: 'سجّل معلومة', en: 'Record a fact' },
    description: 'Records one fact read from a document (a registration number, a date, a batch, a manufacturer…) with where it was read: the file, the page, and the page\'s own words that hold it. Refused unless those words are on that page — copy them from read_page_text.',
    input: { type: 'object', properties: { field: { type: 'string', minLength: 1, maxLength: 80, description: 'what the fact is, e.g. registration_number, expiry_date, batch' },
             value: { type: 'string', minLength: 1, maxLength: 500 }, file: FILE, page: PAGE,
             quote: { type: 'string', minLength: 2, maxLength: 600, description: 'the words on the page that hold the fact, as written there' } },
             required: ['field', 'value', 'file', 'page', 'quote'], additionalProperties: false },
    writes: true,
    async run({ field, value, file, page, quote }, ctx) {
      const f = ctx.ws.file(file);
      const text = await pageText(ctx, f, page);
      if (scanned(text)) fail(`page ${page} of «${f.path}» has no text layer: its words cannot be checked here (read it as an image first)`);
      if (!squeeze(text).includes(squeeze(quote))) fail(`these words are not on page ${page} of «${f.path}»: «${quote}». Quote the page's own words (read_page_text shows them).`);
      const fact = ctx.ws.addFact({ field, value, file: f.id, name: f.path, page, quote, by: ctx.by || 'claude' });
      return { recorded: fact.id };
    },
  },
  {
    name: 'list_facts',
    title: { ar: 'المعلومات المسجّلة', en: 'Recorded facts' },
    description: 'The facts recorded so far, each with its file, page and the words that hold it.',
    input: { type: 'object', properties: { field: { type: 'string', maxLength: 80, description: 'only this field' } }, additionalProperties: false },
    writes: false,
    async run({ field }, ctx) {
      return { facts: ctx.ws.facts.filter(x => !field || x.field === field).map(({ id, field: k, value, file, name, page, quote, by }) => ({ id, field: k, value, file, name, page, quote, by })) };
    },
  },
];

export const tool = name => TOOLS.find(t => t.name === name) || null;
