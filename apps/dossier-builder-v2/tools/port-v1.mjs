// One-time port of the old program's knowledge (apps/dossier-builder/rulepacks) into v2's records. From here on the files
// under knowledge/ are the source of truth and are edited directly; this script is kept as the record of where they came from.
// Every citation is matched to a registered source (knowledge/sources.yaml) by its alias; one that matches none stops the port.
import fs from 'node:fs';
import path from 'node:path';
import * as yaml from 'js-yaml';

const ROOT = path.resolve(import.meta.dirname, '..');
const REPO = path.resolve(ROOT, '..', '..');
const OLD = path.join(REPO, 'apps', 'dossier-builder', 'rulepacks');
const OUT = path.join(ROOT, 'knowledge');
const load = f => yaml.load(fs.readFileSync(f, 'utf8'));
// knowledge/ is the source of truth once ported: running this again would overwrite edits made there since.
if (fs.existsSync(path.join(OUT, 'sets.yaml')) && !process.argv.includes('--force')) {
  console.error('knowledge/ already holds the ported records, and they are edited there now. Run with --force only to redo the port from the old program.');
  process.exit(1);
}
const write = (rel, data, head) => {
  const f = path.join(OUT, rel);
  fs.mkdirSync(path.dirname(f), { recursive: true });
  fs.writeFileSync(f, (head ? head.split('\n').map(l => '# ' + l).join('\n') + '\n' : '') + yaml.dump(data, { lineWidth: 140, noRefs: true, sortKeys: false }));
};

// ---- citations → registered sources
const SOURCES = load(path.join(OUT, 'sources.yaml'));
const ALIASES = SOURCES.flatMap(s => (s.aliases || []).map(a => ({ a: a.toLowerCase(), id: s.id }))).sort((x, y) => y.a.length - x.a.length);
const unmatched = new Map();
const norm = text => String(text ?? '').replace(/\s+/g, ' ').trim();
// The alias a text starts with (a leading «EDA » is optional), or null.
function aliasAt(t) {
  const low = t.toLowerCase();
  return ALIASES.find(x => low.startsWith(x.a)) || (low.startsWith('eda ') ? ALIASES.find(x => low.slice(4).startsWith(x.a)) && { ...ALIASES.find(x => low.slice(4).startsWith(x.a)), skip: 4 } : null);
}
// One citation: the source its alias names, and what follows the alias as the place in it.
function cite(text, extra = {}) {
  const t = norm(text);
  const hit = aliasAt(t);
  if (!hit) { unmatched.set(t, (unmatched.get(t) || 0) + 1); return null; }
  let at = t.slice((hit.skip || 0) + hit.a.length).trim().replace(/^[,;:.\-–—/ ]+/, '').trim();
  if (/^\([^()]*\)$/.test(at)) at = '';   // «(2011)», «(in-use stability testing)»: the source restated, not a place in it
  return { src: hit.id, ...(at ? { at } : {}), ...extra };
}
// A text naming several sources («A §1 / B App. 2», «A; B»): cut where a separator is followed by another source's name.
function cites(text) {
  const t = norm(text);
  if (!t) return [];
  if (FIX.has(t)) return FIX.get(t);
  const parts = [];
  let start = 0;
  const re = / \/ |; | · /g;
  let m;
  while ((m = re.exec(t))) {
    const after = t.slice(m.index + m[0].length);
    if (aliasAt(after)) { parts.push(t.slice(start, m.index)); start = m.index + m[0].length; }
  }
  parts.push(t.slice(start));
  return parts.map(p => cite(p)).filter(Boolean);
}
// Citations the old records wrote as free text, matched by hand (the text is kept on the record as note_source).
const FIX = new Map([
  ['ICH M4 / App. 4', [{ src: 'ich-m4-r4' }, { src: 'ich-ectd-v322', at: 'Appendix 4' }]],
  ["General practice (ICH M4E; WHO TRS 1003 Annex 6 for the exemptions) — the authority's own bioequivalence guideline decides the exemption.",
   [{ src: 'general-practice', at: "the authority's own bioequivalence guideline decides the exemption" }, { src: 'ich-m4e-r2' }, { src: 'who-trs1003-annex6', at: 'the exemptions' }]],
]);
const DOC_CITES = {
  registration_licence: [{ src: 'eda-decree-150-guide-v7', at: 'p.3-4' }, { src: 'eda-np-capp-093-v1', at: 'p.3' }],
  variation_approval: [{ src: 'eda-gl-capp-026-v6' }],
  pricing_certificate: [{ src: 'eg-md-499-2012' }, { src: 'eda-pricing-decision-480-2026' }],
  stability_approval: [{ src: 'eda-np-capp-090-v2', at: 'zone IVa' }],
  eda_letter: [{ src: 'eda-np-capp-065-v5', at: '§1.1.6' }],
  analysis_conformity: [{ src: 'eda-np-capp-065-v5', at: '§1.1.11' }],
  import_approval: [{ src: 'eda-gl-ppma-004-v5', at: 'p.3, p.5, p.22-23' }],
  gmp_certificate: [{ src: 'eda-np-capp-065-v5', at: 'p.12' }, { src: 'eda-eg-m1-submission-guidance-draft', at: 'p.13' }],
  written_confirmation: [{ src: 'eda-np-capp-109-v2', at: 'p.8-10' }, { src: 'eu-dir-2011-62', at: 'Art. 46b' }],
  api_coa: [{ src: 'general-practice', at: 'the retest / expiry date of the batch printed on the CoA' }],
  dmf_cep: [{ src: 'edqm-cep-database' }],
  factory_licence: [{ src: 'eda-np-capp-065-v5', at: '§1.1.17.1' }],
  toll_card: [{ src: 'eda-gl-cao-005-v3', at: 'p.5, p.11' }],
  commercial_register: [{ src: 'eda-np-capp-109-v2', at: 'p.5, 7' }, { src: 'eda-np-capp-065-v5', at: '§1.1.17.2' }, { src: 'eg-law-34-1976' }, { src: 'eda-gl-cao-005-v3', at: 'p.11' }],
  tax_card: [{ src: 'general-practice', at: 'a company document' }],
  manufacturing_contract: [{ src: 'eda-np-capp-065-v5', at: '§1.1.17.7' }],
  leaflet: [{ src: 'eda-gl-cap-care-032-v4' }],
  artwork: [{ src: 'eda-np-capp-065-v5', at: '§1.1.10' }],
  stability_data: [{ src: 'ich-q1a-r2' }, { src: 'ich-m4q-r1', at: '3.2.P.8' }],
  specification: [{ src: 'ich-m4q-r1', at: '3.2.P.5 / 3.2.S.4' }],
  other: [{ src: 'general-practice' }],
};
const COUNTRY_CITES = {
  EG: [{ src: 'eda-ectd-technical-guidance-draft-v1', at: 'lines 165–166, 241–243, 597' }, { src: 'eda-np-capp-065-v5' }],
  EU: [{ src: 'eu-htg-v601', at: 'p. 6, 9' }, { src: 'eu-m1-spec-v311' }],
  US: [{ src: 'fda-ectd-submission-standards' }, { src: 'ich-ectd-stf-v261', at: 'p. 3' }],
  JP: [{ src: 'secondary-ectd-status', at: 'ectd-status.json, citing PMDA guidance' }],
  CH: [{ src: 'secondary-ectd-status', at: 'ectd-status.json, citing gmp-compliance.org' }],
  CA: [{ src: 'secondary-ectd-status', at: 'ectd-status.json' }],
  AU: [{ src: 'secondary-ectd-status', at: 'ectd-status.json' }],
  GCC: [{ src: 'gcc-m1-spec-v15', at: 'Appendices 1, 2, 5, 6' }],
  JO: [{ src: 'secondary-market-notes', at: 'COMPETITORS.md' }],
  ASEAN: [{ src: 'secondary-ectd-status', at: 'compare.json «actd»' }, { src: 'secondary-market-notes', at: 'COMPETITORS.md' }],
  IN: [{ src: 'secondary-ectd-status', at: 'ectd-status.json' }],
};
// The old provenance tags → a record's status.
function status(p) {
  const t = String(p || '').toUpperCase();
  if (!t || /-IN-FORCE$/.test(t) || ['ICH', 'CTD', 'SFDA'].includes(t)) return 'in-force';
  if (/-DRAFT$/.test(t)) return 'draft';
  if (/-DERIVED$/.test(t)) return 'derived';
  if (t === 'ASSUMPTION') return 'assumption';
  if (t === 'GENERAL') return 'general';
  throw new Error(`unknown provenance tag «${p}»`);
}
// Inside a record's logic (the cases of «required»), a provenance that names a source becomes a citation.
function citeInside(node) {
  if (Array.isArray(node)) return node.map(citeInside);
  if (!node || typeof node !== 'object') return node;
  const out = {};
  for (const [k, v] of Object.entries(node)) {
    if (k === 'provenance' && typeof v === 'string' && aliasAt(norm(v))) out.cite = cites(v);
    else if (k === 'provenance' && typeof v === 'string') out.status = status(v);
    else out[k] = citeInside(v);
  }
  return out;
}

// ---- requirement sets
const SETS = [
  { dir: 'eda.ctd.nta065.v5', authority: 'EG-EDA', set: 'eg-eda-ctd', file: 'requirements/eg-eda.yaml', numbering: 'nta065_v5' },
  { dir: 'ich.ctd.m4.v1', authority: 'ICH', set: 'ich-m4-ctd', file: 'requirements/ich-m4.yaml' },
  { dir: 'eu.ctd.m1.v1', authority: 'EU', set: 'eu-m1', file: 'requirements/eu.yaml' },
  { dir: 'gcc.ctd.m1.v1', authority: 'GCC', set: 'gcc-m1', file: 'requirements/gcc.yaml' },
  { dir: 'us.ctd.m1.v1', authority: 'US-FDA', set: 'us-fda-m1', file: 'requirements/us-fda.yaml' },
  { dir: 'intl.ctd.m1.v1', authority: 'OTHER', set: 'intl-m1', file: 'requirements/intl.yaml' },
];
const sets = [];
for (const S of SETS) {
  const pack = load(path.join(OLD, S.dir, 'pack.yaml'));
  const items = load(path.join(OLD, S.dir, 'requirements.yaml'));
  const out = items.map(it => {
    const { id, module, group, ctd, ectd, title, sources, provenance, acceptance_text, condition_note, level_note, logic_provenance, required, item_cases, ...rest } = it;
    const numbers = ctd && typeof ctd === 'object' ? ctd : { [S.set]: ctd };
    const ectdNodes = ectd && typeof ectd === 'object' && !Array.isArray(ectd) ? ectd.nodes || [] : (ectd || []);
    const rec = { id: `${S.authority}/${id}`, kind: 'requirement', authority: S.authority, set: S.set, module, group,
                  ctd: String(Object.values(numbers)[0] ?? ''), ...(numbers.number === undefined ? { numbers } : {}), ectd: ectdNodes, title,
                  status: status(provenance) };
    if (acceptance_text) rec.acceptance = acceptance_text;
    if (condition_note || level_note) rec.note = condition_note || level_note;
    Object.assign(rec, rest);
    if (required !== undefined) rec.required = citeInside(required);
    if (item_cases !== undefined) rec.item_cases = citeInside(item_cases);
    if (logic_provenance) rec.logic_note = logic_provenance;
    rec.cite = (sources || []).flatMap(s => FIX.get(norm(s)) || cites(s));
    if (ectd && typeof ectd === 'object' && !Array.isArray(ectd) && ectd.source) {
      const cs = FIX.get(norm(ectd.source)) || cites(ectd.source); if (cs.length) rec.ectd_cite = cs.map(c => ({ ...c, status: status(ectd.provenance) }));
    }
    return rec;
  });
  write(S.file, out, `${pack.title.en}\n${pack.title.ar}\nPorted from the old program (rulepacks/${S.dir}); edit here from now on.`);
  sets.push({ id: S.set, kind: 'requirements', authority: S.authority, title: pack.title, status: pack.status, file: S.file,
              columns: pack.columns || null, valid_from: pack.valid_from || null, count: out.length });
}

// ---- review rules (EDA's assessors)
const RV = path.join(OLD, 'eda.review.v1');
const rvPack = load(path.join(RV, 'pack.yaml'));
const rules = [];
for (const f of rvPack.files) {
  for (const it of load(path.join(RV, f))) {
    const { id, dept, source, anchor, evidence, ...rest } = it;
    const s = source && typeof source === 'object' ? source : { code: source };
    const c = cite(s.code, { ...(s.section ? { at: String(s.section) } : {}), ...(s.quote ? { quote: s.quote } : {}) });
    const rec = { id: `EG-EDA/${id}`, kind: 'rule', authority: 'EG-EDA', set: 'eg-eda-review', area: dept, ...rest };
    if (evidence) rec.evidence = { ...evidence, ...(evidence.slots ? { slots: evidence.slots.map(x => `EG-EDA/${x}`) } : {}) };
    rec.cite = c ? [c] : [];
    if (anchor) {
      const a = typeof anchor === 'object' ? anchor : { code: anchor };
      const as = cites(a.code);
      if (as.length && a.section) as[0] = { ...as[0], at: String(a.section) };
      rec.anchor_cite = as;
    }
    rules.push(rec);
  }
}
write('review/eg-eda.yaml', rules, `${rvPack.title.en}\n${rvPack.title.ar}\nPorted from the old program (rulepacks/eda.review.v1); edit here from now on.`);
sets.push({ id: 'eg-eda-review', kind: 'rules', authority: 'EG-EDA', title: rvPack.title, status: rvPack.status, file: 'review/eg-eda.yaml', count: rules.length });

// ---- variations (EDA's own tool)
const VR = path.join(OLD, 'eda.variations.gl026.v6');
const vrPack = load(path.join(VR, 'pack.yaml'));
const variations = load(path.join(VR, 'variations.yaml')).map(it => {
  const { id, source, request, ...rest } = it;
  return { id: `EG-EDA/var/${id}`, kind: 'variation', authority: 'EG-EDA', set: 'eg-eda-variations', title: { en: request, ar: null }, ...rest,
           cite: [{ src: 'eda-variation-tool', at: `Human, ID ${source?.row ?? '?'}` }, { src: 'eda-gl-capp-026-v6' }] };
});
write('variations/eg-eda.yaml', {
  class_order: vrPack.class_order, ectd_submission_type: vrPack.ectd_submission_type,
  grouping_rule: { en: vrPack.grouping_rule.en, ar: 'مجموعة التغييرات بتتصنف بأعلى فئة فيها.', cite: cites(vrPack.grouping_rule.source) },
  variations },  `${vrPack.title?.en || 'EDA variations'}\nPorted from the old program (rulepacks/eda.variations.gl026.v6); edit here from now on.`);
sets.push({ id: 'eg-eda-variations', kind: 'variations', authority: 'EG-EDA', title: vrPack.title || { en: 'EDA variations', ar: 'متغيرات هيئة الدواء' },
            status: vrPack.status, file: 'variations/eg-eda.yaml', count: variations.length });

// ---- documents and their validity
const DV = load(path.join(OLD, 'eda.doc-validity.v1', 'doc_types.yaml'));
const doctypes = DV.types.map(it => {
  const { id, en, ar, source, provenance, ...rest } = it;
  const cs = DOC_CITES[id];
  if (!cs) throw new Error(`documents: no citation written for ${id}`);
  return { id: `EG-EDA/doc/${id}`, kind: 'doctype', authority: 'EG-EDA', set: 'eg-eda-doctypes', title: { en, ar }, ...rest, status: status(provenance),
           note_source: source, cite: cs };
});
write('documents/eg-eda-validity.yaml', { warn_days_default: DV.warn_days_default, required: DV.required, types: doctypes },
      `${DV.title.en}\n${DV.title.ar}\nPorted from the old program (rulepacks/eda.doc-validity.v1); edit here from now on.`);
sets.push({ id: 'eg-eda-doctypes', kind: 'doctypes', authority: 'EG-EDA', title: DV.title, status: 'in-force', file: 'documents/eg-eda-validity.yaml', count: doctypes.length });

// ---- countries (what each country takes)
const CT = load(path.join(OLD, 'countries.yaml'));
const countries = CT.countries.map(c => {
  const text = String(c.source || '');
  const cs = COUNTRY_CITES[c.code];
  if (!cs) throw new Error(`countries: no citation written for ${c.code}`);
  const { source, ...rest } = c;
  return { id: `country/${c.code}`, kind: 'country', ...rest, note_source: text, cite: cs };
});
write('countries.yaml', { reviewed: String(CT.reviewed), countries },
      'What each country or region takes (formats, Module 1, validation criteria).\nPorted from the old program (rulepacks/countries.yaml); edit here from now on.');

// ---- the program's own knowledge (recognition keywords, templates, vocabularies): cited as the program's
const copyAs = (from, to, head) => { const d = load(from); write(to, d, head); return d; };
for (const S of SETS) {
  const f = path.join(OLD, S.dir, 'classify.yaml');
  if (fs.existsSync(f)) copyAs(f, `recognition/${S.set}.yaml`, `How the program recognises the documents of «${S.set}» (keywords, the program's own rule — source: program).\nPorted from rulepacks/${S.dir}/classify.yaml.`);
}
copyAs(path.join(OLD, 'eda.ctd.nta065.v5', 'templates', 'library.yaml'), 'templates/eg-eda.yaml',
       'The template or example in front of each EDA item (the program\'s own — source: program).\nPorted from rulepacks/eda.ctd.nta065.v5/templates/library.yaml.');
copyAs(path.join(OLD, 'vocab', 'forms.yaml'), 'vocab/forms.yaml', 'Dose forms with their routes and synonyms (the program\'s vocabulary — source: program, built on EDQM standard terms).');
fs.mkdirSync(path.join(OUT, 'vocab'), { recursive: true });
fs.copyFileSync(path.join(OLD, 'vocab', 'countries.json'), path.join(OUT, 'vocab', 'countries.json'));

// ---- eCTD tables (as published): copied with an index that cites them
const ECTD = [
  ['ich.ectd.v322/app4.csv', 'ectd/ich-322-app4.csv', 'ich-ectd-v322', 'Appendix 4 — the CTD/eCTD headings, folders and file names'],
  ['ich.ectd.v40/context-of-use.csv', 'ectd/ich-40-context-of-use.csv', 'ich-ectd-v40-cv-v103', 'Context of use codes'],
  ['ich.ectd.v40/document-type.csv', 'ectd/ich-40-document-type.csv', 'ich-ectd-v40-cv-v103', 'Document type codes'],
  ['ich.ectd.v40/keyword-definition-type.csv', 'ectd/ich-40-keyword-definition-type.csv', 'ich-ectd-v40-cv-v103', 'Keyword definition types'],
  ['ich.ectd.v40/type-of-control.csv', 'ectd/ich-40-type-of-control.csv', 'ich-ectd-v40-cv-v103', 'Types of control'],
  ['ich.ectd.v40/oids.txt', 'ectd/ich-40-oids.txt', 'ich-ectd-v40-cv-v103', 'The OIDs of the code systems'],
];
const tables = [];
for (const [from, to, src, title] of ECTD) {
  const f = path.join(OLD, from);
  if (!fs.existsSync(f)) continue;
  fs.mkdirSync(path.join(OUT, path.dirname(to)), { recursive: true });
  fs.copyFileSync(f, path.join(OUT, to));
  tables.push({ id: `table/${path.basename(to)}`, kind: 'table', file: to, title: { en: title, ar: null }, cite: [{ src }] });
}
const stf = path.join(OLD, 'ich.ectd.v322', 'stf');
if (fs.existsSync(stf)) {
  fs.cpSync(stf, path.join(OUT, 'ectd', 'ich-stf'), { recursive: true });
  tables.push({ id: 'table/ich-stf', kind: 'table', file: 'ectd/ich-stf/', title: { en: 'Study tagging file vocabularies', ar: null }, cite: [{ src: 'ich-ectd-stf-v261' }] });
}
write('ectd/index.yaml', tables, 'The eCTD tables the program holds, as published, with their sources.');

const SET_CITES = {
  'eg-eda-ctd': ['eda-np-capp-065-v5', 'eda-ctd-qm-v2', 'eda-gl-capp-039-v1', 'eda-eg-m1-ectd-spec-draft-v1', 'eda-ectd-technical-guidance-draft-v1'],
  'ich-m4-ctd': ['ich-m4-r4', 'ich-m4q-r1', 'ich-m4s-r2', 'ich-m4e-r2'],
  'eu-m1': ['eu-m1-spec-v311', 'eu-nta-vol2b'],
  'gcc-m1': ['gcc-m1-spec-v15', 'sfda-data-requirements-v4'],
  'us-fda-m1': ['fda-comprehensive-toc-v233'],
  'intl-m1': ['general-practice'],
  'eg-eda-review': ['eda-np-capp-065-v5', 'eda-np-capp-040-v1', 'eda-gl-cadc-002-v2', 'eda-np-capp-090-v2', 'eda-gl-capp-024-v4', 'eda-gl-capp-039-v1',
                    'eda-ctd-qm-v2', 'eda-submission-procedures', 'who-pq-screening', 'who-trs986-annex6', 'ich-m4q-r1', 'who-trs992-annex9', 'who-trs1033-annex10'],
  'eg-eda-variations': ['eda-gl-capp-026-v6', 'eda-variation-tool', 'eda-np-capp-112-v1', ['eda-ectd-technical-guidance-draft-v1', 'Annex 6']],
  'eg-eda-doctypes': ['eda-np-capp-065-v5'],
};
for (const st of sets) {
  const cs = SET_CITES[st.id];
  if (!cs) throw new Error(`sets: no sources written for ${st.id}`);
  st.cite = cs.map(c => (Array.isArray(c) ? { src: c[0], at: c[1] } : { src: c }));
}
write('sets.yaml', sets, 'The sets of knowledge records and where each lives (made by tools/port-v1.mjs, kept up to date by hand).');

if (unmatched.size) {
  console.error('Citations that match no registered source (add an alias in knowledge/sources.yaml):');
  for (const [t, n] of [...unmatched].sort((a, b) => b[1] - a[1])) console.error(`  ${n}× ${t}`);
  process.exit(1);
}
console.log(sets.map(s => `${s.id}: ${s.count}`).join('\n'));
