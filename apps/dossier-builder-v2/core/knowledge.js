// The program's way into its knowledge: authorities, sources, requirements, review rules, variations, documents, countries.
// Pure JavaScript over the built data (dist/knowledge.json), so the desktop program and the browser library use the same code.
import { allRecords, citationsOf } from './validate.js';

// Arabic and English text folded for search: no diacritics or tatweel, one form of alef / ya / ta marbuta, Western digits.
export function fold(text) {
  return String(text ?? '')
    .normalize('NFKD')
    .replace(/[ً-ٰٟۖ-ۭـ]/g, '')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[أإآٱ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه').replace(/ؤ/g, 'و').replace(/ئ/g, 'ي')
    .replace(/[٠-٩]/g, d => String(d.charCodeAt(0) - 0x660))
    .replace(/[۰-۹]/g, d => String(d.charCodeAt(0) - 0x6f0))
    .toLowerCase();
}

const textOf = v => (v == null ? '' : typeof v === 'string' ? v : typeof v === 'object' ? Object.values(v).map(textOf).join(' ') : String(v));

export function createKnowledge(data) {
  const sources = new Map(data.sources.map(s => [s.id, s]));
  const authorities = new Map(data.authorities.map(a => [a.id, a]));
  const sets = new Map(data.sets.map(s => [s.id, s]));
  const records = allRecords(data);
  const byId = new Map(records.map(r => [r.id, r]));

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
      head: fold([textOf(r.title), r.code, r.name].join(' ')),
      codes: fold([r.id, r.ctd, textOf(r.numbers), (r.ectd || []).join(' '), r.pac, r.type].join(' ')),
      body: fold([r.acceptance, r.note, textOf(r.question), textOf(r.deficiency), textOf(r.conditions), textOf(r.requirements),
                  r.group, r.area, r.module1, r.criteria, r.scope, (r.cite || []).map(c => [c.at, c.quote].join(' ')).join(' ')].join(' ')),
    })),
    ...data.sources.map(s => ({
      type: 'source', id: s.id, kind: 'source', authority: s.authority,
      head: fold(textOf(s.title)), codes: fold([s.id, s.code, s.version, (s.aliases || []).join(' ')].join(' ')), body: fold([s.note, s.supersedes].join(' ')),
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
    // The records that cite a source.
    usedBy: sourceId => [...(users.get(sourceId) || [])].map(id => byId.get(id)),
    // Every word of the query must appear; a hit in the title ranks first, then in the codes, then in the body.
    search(query, { kind, authority, limit = 50 } = {}) {
      const words = fold(query).split(/[\s,،;؛]+/).filter(Boolean);
      if (!words.length) return [];
      const hits = [];
      for (const e of entries) {
        if ((kind && e.kind !== kind) || (authority && e.authority !== authority)) continue;
        let score = 0;
        let all = true;
        for (const w of words) {
          if (e.head.includes(w)) score += 5;
          else if (e.codes.includes(w)) score += 3;
          else if (e.body.includes(w)) score += 1;
          else { all = false; break; }
        }
        if (all) hits.push({ ...e, score, item: e.type === 'source' ? sources.get(e.id) : byId.get(e.id) });
      }
      return hits.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id)).slice(0, limit)
        .map(({ type, id, kind: k, score, item }) => ({ type, id, kind: k, score, item }));
    },
  };
}
