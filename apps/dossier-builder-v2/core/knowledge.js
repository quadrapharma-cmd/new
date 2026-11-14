// The program's way into its knowledge: authorities, sources, requirements, review rules, variations, documents, countries.
// Pure JavaScript over the built data (dist/knowledge.json), so the desktop program and the browser library use the same code.
import { allRecords, citationsOf } from './validate.js';

import { fold } from './fold.js';
import { indexGlossary, parseQuery, hasAlt } from './search.js';
export { fold };

const textOf = v => (v == null ? '' : typeof v === 'string' ? v : typeof v === 'object' ? Object.values(v).map(textOf).join(' ') : String(v));

export function createKnowledge(data) {
  const sources = new Map(data.sources.map(s => [s.id, s]));
  const authorities = new Map(data.authorities.map(a => [a.id, a]));
  const sets = new Map(data.sets.map(s => [s.id, s]));
  const records = allRecords(data);
  const glossary = indexGlossary(data.vocab?.glossary);
  const byId = new Map(records.map(r => [r.id, r]));

  // What the review found for each citation (knowledge/checks/citations.json).
  const checks = new Map();
  for (const c of data.checks?.citations || []) checks.set(`${c.rec}|${c.field}|${c.src}|${c.at || ''}`, c);

  // Which records cite each source.
  const users = new Map();
  for (const r of records) for (const c of citationsOf(r)) {
    if (!users.has(c.src)) users.set(c.src, new Set());
    users.get(c.src).add(r.id);
  }

  // One search entry per record and per source: the title weighs most, then the codes, then the body.
  const entries = [
    ...records.map(r => ({
      type: 'record', id: r.id, kind: r.kind, authority: r.authority,
      head: fold([textOf(r.title), r.code, r.name].join(' ')).replace(/\s+/g, ' '),
      codes: fold([r.id, r.ctd, textOf(r.numbers), (r.ectd || []).join(' '), r.pac, r.type].join(' ')),
      body: fold([r.acceptance, textOf(r.note), textOf(r.question), textOf(r.deficiency), textOf(r.conditions), textOf(r.requirements),
                  r.group, r.area, r.type, r.module1, r.criteria, r.scope, r.note_source, textOf(r.evidence?.keywords), textOf(r.guideline),
                  textOf(r.check?.note), r.doc_class, r.produced_by, r.form_type,
                  [...(r.cite || []), ...(r.ectd_cite || []), ...(r.anchor_cite || [])].map(c => [c.at, c.quote, c.gist, c.note].join(' ')).join(' ')].join(' ')).replace(/\s+/g, ' '),
    })),
    ...data.sources.map(s => ({
      type: 'source', id: s.id, kind: 'source', authority: s.authority,
      head: fold(textOf(s.title)).replace(/\s+/g, ' '), codes: fold([s.id, s.code, s.version, (s.aliases || []).join(' ')].join(' ')),
      body: fold([s.note, s.supersedes, s.confirm, textOf(s.latest)].join(' ')).replace(/\s+/g, ' '),
    })),
  ];

  return {
    data,
    authorities: () => data.authorities,
    authority: id => authorities.get(id) || null,
    sources: ({ authority, status } = {}) => data.sources.filter(s => (!authority || s.authority === authority) && (!status || s.status === status)),
    source: id => sources.get(id) || null,
    sets: ({ authority, kind } = {}) => data.sets.filter(s => (!authority || s.authority === authority) && (!kind || s.kind === kind)),
    set: id => sets.get(id) || null,
    record: id => byId.get(id) || null,
    records: ({ kind, set, authority, module } = {}) =>
      records.filter(r => (!kind || r.kind === kind) && (!set || r.set === set) && (!authority || r.authority === authority) && (module == null || r.module === module)),
    // A record's citations, each with the source it names.
    citations: rec => citationsOf(rec).map(c => ({ ...c, source: sources.get(c.src) || null })),
    // What the review found for one citation of a record.
    check: (recId, field, cite) => checks.get(`${recId}|${field}|${cite.src}|${cite.at || ''}`) || null,
    // The records that cite a source.
    usedBy: sourceId => [...(users.get(sourceId) || [])].map(id => byId.get(id)),
    // Every group of the query must appear (each with its other forms and the other language's words); a hit in the title
    // ranks first, then in the codes, then in the body. With no record holding every group, the records holding most of them.
    parse: query => parseQuery(query, glossary),
    search(query, { kind, authority, limit = 50 } = {}) {
      const { groups } = typeof query === 'string' ? parseQuery(query, glossary) : query;
      if (!groups.length) return [];
      const hits = [];
      for (const e of entries) {
        if ((kind && e.kind !== kind) || (authority && e.authority !== authority)) continue;
        let score = 0;
        let found = 0;
        for (const g of groups) {
          const where = g.alts.some(a => hasAlt(e.head, a)) ? 5 : g.alts.some(a => hasAlt(e.codes, a)) ? 3 : g.alts.some(a => hasAlt(e.body, a)) ? 1 : 0;
          if (where) { found++; score += where; }
        }
        if (found === groups.length) hits.push({ ...e, score, item: e.type === 'source' ? sources.get(e.id) : byId.get(e.id) });
      }
      return hits.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id)).slice(0, limit)
        .map(({ type, id, kind: k, score, item }) => ({ type, id, kind: k, score, item }));
    },
  };
}
