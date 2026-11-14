// The first look at a dossier («الفحص الأول للملف»): every document's kind, place and facts, then the findings that come from
// reading the documents side by side. docs: [{id, name, pages: [{n, text, by}]}] (pages read by prep/read.js).
import { factsOf } from './facts.js';
import { typeOf } from './doctype.js';
import { check } from './checks.js';

export function prepare(docs, { today, knowledge } = {}) {
  const read = docs.map(d => {
    const t = typeOf(d.pages);
    const places = (t.places || []).map(id => { const r = knowledge?.record(id); return r ? { id, ctd: r.ctd, title: r.title } : { id }; });
    return { id: d.id, name: d.name, pages: d.pages.length, read: d.pages.filter(p => (p.text || '').trim()).length,
             type: t.type, type_ar: t.ar, doctype: t.doctype, places, facts: factsOf(d.pages),
             text: d.pages.map(p => p.text || '').join('\n') };
  });
  return { documents: read.map(({ text, ...d }) => d), findings: check(read, { today }) };
}
