// The tools Claude works with in the workshop («اسأل Claude», and the automatic run where the rules cannot settle a thing): the
// dossier's documents as the program read them, the board and its findings, the library — and the few changes Claude may make, each
// checked and logged: a fact is kept only if its words are on the page it names; a document is placed only on a place of the board;
// no paper of another party is ever changed. Each tool: {name, description, input_schema, writes, run(input)}.
import { preparePages, findInPages, parseQuery } from '../core/search.js';
import { onPage } from './understand.js';
import { moveDoc, log } from './pipeline.js';

const visible = d => d.docs.filter(x => !x.dup && !x.split);
const DOC = { type: 'string', description: 'the document id from list_documents (D1, D2…)' };
const PAGE = { type: 'integer', minimum: 1, description: 'page number, 1 for the first page' };

export function workshopTools(ctx) {
  // ctx: {dossier(): the dossier, board(): the board, findings(): the findings, knowledge: core/knowledge.js, changed(): save and redraw}
  const doc = id => { const x = visible(ctx.dossier()).find(y => y.id === id); if (!x) throw new Error(`no document «${id}» (list_documents gives the ids)`); return x; };
  const place = id => ctx.board().places.find(p => p.id === id);
  return [
    { name: 'list_documents', writes: false,
      description: 'The documents of the dossier: id, file name, kind, pages, how they were read (text layer, scan reader, Claude, Word), what the program found each is, and its place on the board.',
      input_schema: { type: 'object', properties: {}, additionalProperties: false },
      run: () => ({ documents: visible(ctx.dossier()).map(x => ({ id: x.id, name: x.name, kind: x.kind, pages: x.pages?.length || 0,
        read_by: [...new Set((x.pages || []).map(p => p.by))], type: x.type_ar || x.type || null, place: x.place ? `${place(x.place)?.ctd} ${place(x.place)?.title.en}` : null,
        place_id: x.place || null, sure: !!x.sure, unread: x.unread || null, made_by_program: x.madeBy === 'program' })) }) },
    { name: 'read_page', writes: false,
      description: 'The text of one page of a document, as the program read it (from its text layer, its scan, or its Word file). A page read from a scan may hold reading slips.',
      input_schema: { type: 'object', properties: { document: DOC, page: PAGE }, required: ['document', 'page'], additionalProperties: false },
      run: ({ document, page }) => {
        const x = doc(document), p = x.pages.find(q => q.n === page);
        if (!p) throw new Error(`«${x.name}» has ${x.pages.length} page(s)`);
        return { document, page, read_by: p.by, text: String(p.text || '').slice(0, 8000), ...(String(p.text || '').length > 8000 ? { truncated: true } : {}) };
      } },
    { name: 'find_in_documents', writes: false,
      description: 'Finds words in the documents\' pages (Arabic or English, every word must be on the page). Returns the best pages with the words around the hit, marked «like this».',
      input_schema: { type: 'object', properties: { query: { type: 'string', minLength: 1, maxLength: 300 }, limit: { type: 'integer', minimum: 1, maximum: 30 } }, required: ['query'], additionalProperties: false },
      run: ({ query, limit = 10 }) => {
        const { groups } = ctx.knowledge ? ctx.knowledge.parse(query) : parseQuery(query);
        if (!groups.length) throw new Error('the query has no words to look for');
        const hits = [];
        for (const x of visible(ctx.dossier())) {
          if (!x.pages?.length) continue;
          for (const p of findInPages(preparePages(x.pages.map(q => q.text || '')), groups, { limit }).pages)
            hits.push({ document: x.id, name: x.name, page: p.page, score: p.score, words: p.html.replace(/<mark>/g, '«').replace(/<\/mark>/g, '»').replace(/<[^>]+>/g, '') });
        }
        return { hits: hits.sort((a, b) => b.score - a.score).slice(0, limit).map(({ score, ...h }) => h) };
      } },
    { name: 'list_findings', writes: false,
      description: 'What the program\'s checks found in the dossier: each finding\'s level (red: blocks the file; amber: to be explained), its title, detail, documents and pages, its rule and whether the person accepted it.',
      input_schema: { type: 'object', properties: {}, additionalProperties: false },
      run: () => ({ findings: ctx.findings().slice(0, 80).map(f => ({ id: f.id, level: f.level, title: f.title, detail: f.detail, place: f.place ? place(f.place)?.ctd : null,
        evidence: (f.evidence || []).map(e => ({ document: e.doc, page: e.page, quote: e.quote })), rule: f.rule?.ar || null, accepted: f.accepted?.reason || null })) }) },
    { name: 'board', writes: false,
      description: 'The places of the dossier for this country and product: id, CTD number, title, whether required (R), optional (O), not required (NR) or not applying (NA), and the documents in each.',
      input_schema: { type: 'object', properties: { only_required: { type: 'boolean' } }, additionalProperties: false },
      run: ({ only_required = false }) => ({ column: ctx.board().column, places: ctx.board().places.filter(p => !only_required || p.level === 'R').map(p => ({ id: p.id, ctd: p.ctd, title: p.title.en, level: p.level,
        documents: visible(ctx.dossier()).filter(x => x.place === p.id).map(x => x.id) })) }) },
    { name: 'search_knowledge', writes: false,
      description: 'Searches the program\'s library (the authorities\' requirements, EDA\'s review questions and variations, document types, sources) in Arabic or English; get_record gives one record with its sources.',
      input_schema: { type: 'object', properties: { query: { type: 'string', minLength: 1, maxLength: 300 }, limit: { type: 'integer', minimum: 1, maximum: 30 } }, required: ['query'], additionalProperties: false },
      run: ({ query, limit = 10 }) => ({ results: ctx.knowledge.search(query, { limit }).map(({ type, id, kind, item }) => ({ id, kind: type === 'source' ? 'source' : kind, title: item.title?.en || item.title || item.name || null, ...(item.ctd ? { ctd: item.ctd } : {}) })) }) },
    { name: 'get_record', writes: false,
      description: 'One record of the library with what it asks and the sources it rests on (code, version, place, and the source\'s own words where the record quotes them).',
      input_schema: { type: 'object', properties: { id: { type: 'string', minLength: 1, maxLength: 120 } }, required: ['id'], additionalProperties: false },
      run: ({ id }) => {
        const r = ctx.knowledge.record(id);
        if (!r) throw new Error(`no record «${id}» (search_knowledge finds ids)`);
        const keep = ['id', 'kind', 'authority', 'ctd', 'status', 'acceptance', 'note', 'question', 'deficiency', 'conditions', 'validity_months'];
        const out = { title: r.title?.en || r.name || null };
        for (const k of keep) if (r[k] != null && r[k] !== '') out[k] = r[k];
        out.sources = ctx.knowledge.citations(r).map(c => ({ code: c.source?.code || c.src, version: c.source?.version || null, at: c.at || null, ...(c.quote ? { quote: c.quote } : {}) }));
        return out;
      } },
    { name: 'record_fact', writes: true,
      description: 'Records one fact read from a document page (a registration number, a date, a manufacturer, a batch…) with the page\'s own words that hold it. Refused unless those words are on that page — copy them from read_page.',
      input_schema: { type: 'object', properties: { document: DOC, page: PAGE, field: { type: 'string', minLength: 1, maxLength: 60 }, value: { type: 'string', minLength: 1, maxLength: 300 },
                     quote: { type: 'string', minLength: 2, maxLength: 500 } }, required: ['document', 'page', 'field', 'value', 'quote'], additionalProperties: false },
      run: ({ document, page, field, value, quote }) => {
        const x = doc(document);
        if (!onPage(x.pages, page, quote)) throw new Error(`these words are not on page ${page} of «${x.name}»: quote the page's own words (read_page shows them)`);
        x.facts = [...(x.facts || []), { field, value, page, quote, by: 'claude' }];
        log(ctx.dossier(), 'fact-by-claude', { doc: x.id, field });
        ctx.changed();
        return { recorded: true };
      } },
    { name: 'place_document', writes: true,
      description: 'Puts a document on a place of the board (the person sees it was Claude, and can move it back). Only places of this board; never a document of another party changed.',
      input_schema: { type: 'object', properties: { document: DOC, place_id: { type: 'string', minLength: 3, maxLength: 60 }, why: { type: 'string', maxLength: 300 } }, required: ['document', 'place_id'], additionalProperties: false },
      run: ({ document, place_id, why = '' }) => {
        const x = doc(document);
        if (!place(place_id)) throw new Error(`no place «${place_id}» on this board (the board tool lists them)`);
        moveDoc(ctx.dossier(), x.id, place_id);
        Object.assign(x, { placeBy: 'claude', sure: true, claudeWhy: String(why).slice(0, 300) });
        ctx.changed();
        return { placed: `${place(place_id).ctd} ${place(place_id).title.en}` };
      } },
  ];
}

export const ASK_SYSTEM = [
  'You are the agent inside Dossier Builder\'s workshop, which prepares a medicine\'s registration dossier (Egypt first).',
  'You act only through the workshop\'s tools. Rules:',
  '1. Every fact you state rests on a document page or a library record: quote the page (document and page) or name the record\'s source.',
  '2. Never invent a requirement: look it up with search_knowledge / get_record.',
  '3. A document of another party (an authority, a manufacturer, a laboratory) is never changed; you may only say what is wrong and what to ask for.',
  '4. A page read from a scan may hold reading slips: say so when a fact rests on one.',
  '5. Answer in the person\'s language (Egyptian Arabic when they write Arabic), briefly: what you did, what you found, what is missing.',
].join('\n');
