// The rules every piece of knowledge must keep. Pure JavaScript: the build, the tests and the library run the same checks.
// validate(data) → { errors: [...], warnings: [...] }; an error stops the build.

export const SOURCE_STATUS = ['in-force', 'draft', 'superseded', 'reference', 'data', 'general', 'secondary', 'assumption'];
export const RECORD_STATUS = ['in-force', 'draft', 'derived', 'assumption', 'general'];

// Every record of every kind, in one list.
export function allRecords(data) {
  return [
    ...data.requirements,
    ...data.rules,
    ...data.variations.items,
    ...data.doctypes.items,
    ...data.countries.items,
    ...data.ectd.index,
  ];
}

// Every citation a record carries, with the field it sits in.
export function citationsOf(rec) {
  const out = [];
  for (const field of ['cite', 'ectd_cite', 'anchor_cite']) for (const c of rec[field] || []) out.push({ field, ...c });
  return out;
}

export function validate(data) {
  const errors = [];
  const warnings = [];
  const err = (where, msg) => errors.push(`${where}: ${msg}`);
  const warn = (where, msg) => warnings.push(`${where}: ${msg}`);

  const authorities = new Set(data.authorities.map(a => a.id));
  if (authorities.size !== data.authorities.length) err('authorities', 'an id is used twice');

  // ---- sources
  const sources = new Map();
  const aliasOwner = new Map();
  for (const s of data.sources) {
    const where = `source ${s.id}`;
    if (sources.has(s.id)) err(where, 'id used twice');
    sources.set(s.id, s);
    if (!authorities.has(s.authority)) err(where, `unknown authority «${s.authority}»`);
    if (!SOURCE_STATUS.includes(s.status)) err(where, `unknown status «${s.status}»`);
    if (!s.title?.en || !s.title?.ar) err(where, 'needs a title in English and Arabic');
    if (!s.checked?.on) err(where, 'needs the date it was last checked (checked.on)');
    if (s.held && !s.file) err(where, 'held but names no file');
    for (const a of s.aliases || []) {
      const k = a.toLowerCase();
      if (aliasOwner.has(k) && aliasOwner.get(k) !== s.id) err(where, `alias «${a}» also names ${aliasOwner.get(k)}`);
      aliasOwner.set(k, s.id);
    }
  }

  // ---- sets
  const sets = new Map(data.sets.map(s => [s.id, s]));
  for (const s of data.sets) {
    if (!authorities.has(s.authority)) err(`set ${s.id}`, `unknown authority «${s.authority}»`);
    checkCites(`set ${s.id}`, s.cite, true);
  }

  // ---- records
  const ids = new Set();
  const requirementIds = new Set(data.requirements.map(r => r.id));
  const countBySet = new Map();
  for (const rec of allRecords(data)) {
    const where = `${rec.kind || 'record'} ${rec.id}`;
    if (!rec.id) { err('record', `no id: ${JSON.stringify(rec).slice(0, 80)}`); continue; }
    if (ids.has(rec.id)) err(where, 'id used twice');
    ids.add(rec.id);
    if (rec.authority !== undefined && rec.kind !== 'country' && !authorities.has(rec.authority)) err(where, `unknown authority «${rec.authority}»`);
    if (rec.set !== undefined) {
      if (!sets.has(rec.set)) err(where, `unknown set «${rec.set}»`);
      countBySet.set(rec.set, (countBySet.get(rec.set) || 0) + 1);
    }
    if (rec.status !== undefined && !RECORD_STATUS.includes(rec.status)) err(where, `unknown status «${rec.status}»`);
    if (rec.title !== undefined && !rec.title?.en) err(where, 'needs an English title');
    checkCites(where, rec.cite, true);
    if (rec.ectd_cite) checkCites(`${where} (eCTD placement)`, rec.ectd_cite, false);
    if (rec.anchor_cite) checkCites(`${where} (international anchor)`, rec.anchor_cite, false);
    walkInner(rec.required, where);
    walkInner(rec.item_cases, where);
    for (const slot of rec.evidence?.slots || []) if (!requirementIds.has(slot)) err(where, `evidence names «${slot}», which is no requirement`);

    // An in-force requirement must rest on at least one source that is itself in force (or published data): a draft alone is no rule.
    if (rec.kind === 'requirement' && rec.status === 'in-force') {
      const st = (rec.cite || []).map(c => sources.get(c.src)?.status);
      if (st.length && !st.some(x => x === 'in-force' || x === 'data')) warn(where, `in force, but every source it cites is ${[...new Set(st)].join(' / ')}`);
    }
  }
  for (const [id, n] of countBySet) {
    const s = sets.get(id);
    if (s && s.count !== n) err(`set ${id}`, `says ${s.count} records, holds ${n}`);
  }
  if (data.variations.grouping_rule) checkCites('variations grouping rule', data.variations.grouping_rule.cite, true);

  // The review's findings name only records and sources that exist; a replaced source names the one that replaced it.
  for (const f of data.checks?.findings?.findings || []) {
    for (const id of f.records || []) if (!ids.has(id)) err(`finding ${f.id}`, `names «${id}», which is no record`);
    for (const id of f.sources || []) if (!sources.has(id)) err(`finding ${f.id}`, `names «${id}», which is not registered`);
  }
  for (const s of data.sources) if (s.superseded_by && !sources.has(s.superseded_by)) err(`source ${s.id}`, `replaced by «${s.superseded_by}», which is not registered`);

  return { errors, warnings };

  // Citations inside a record's logic (a case of «required» that names its own source).
  function walkInner(node, where) {
    if (Array.isArray(node)) return node.forEach(n => walkInner(n, where));
    if (!node || typeof node !== 'object') return;
    if (node.cite) checkCites(`${where} (a case)`, node.cite, false);
    if (node.status !== undefined && !RECORD_STATUS.includes(node.status)) err(where, `a case has unknown status «${node.status}»`);
    for (const [k, v] of Object.entries(node)) if (k !== 'cite') walkInner(v, where);
  }

  function checkCites(where, list, required) {
    if (!Array.isArray(list) || !list.length) { if (required) err(where, 'cites no source'); return; }
    for (const c of list) {
      if (!c || !c.src) { err(where, 'a citation without a source'); continue; }
      if (!sources.has(c.src)) err(where, `cites «${c.src}», which is not registered`);
    }
  }
}
