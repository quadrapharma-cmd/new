// Reads the knowledge files from disk into the one object the program and the library use (Node only).
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import * as yaml from 'js-yaml';

export const ROOT = path.resolve(import.meta.dirname, '..');
export const REPO = path.resolve(ROOT, '..', '..');
export const KNOWLEDGE = path.join(ROOT, 'knowledge');

const read = rel => fs.readFileSync(path.join(KNOWLEDGE, rel), 'utf8');
const load = rel => yaml.load(read(rel));

export function loadKnowledge() {
  const sets = load('sets.yaml');
  const byKind = kind => sets.filter(s => s.kind === kind);
  const variations = load('variations/eg-eda.yaml');
  const doctypes = load('documents/eg-eda-validity.yaml');
  const countries = load('countries.yaml');
  const ectdIndex = load('ectd/index.yaml');
  const tables = {};
  for (const t of ectdIndex) {
    const f = path.join(KNOWLEDGE, t.file);
    if (fs.statSync(f).isDirectory()) {
      for (const name of fs.readdirSync(f)) tables[`${t.file}${name}`] = fs.readFileSync(path.join(f, name), 'utf8');
    } else tables[t.file] = fs.readFileSync(f, 'utf8');
  }
  const recognition = {};
  for (const name of fs.readdirSync(path.join(KNOWLEDGE, 'recognition'))) recognition[name.replace(/\.yaml$/, '')] = load(`recognition/${name}`);

  return {
    authorities: load('authorities.yaml'),
    sources: load('sources.yaml'),
    sets,
    requirements: byKind('requirements').flatMap(s => load(s.file)),
    rules: byKind('rules').flatMap(s => load(s.file)),
    variations: { class_order: variations.class_order, ectd_submission_type: variations.ectd_submission_type,
                  grouping_rule: variations.grouping_rule, items: variations.variations },
    doctypes: { warn_days_default: doctypes.warn_days_default, required: doctypes.required, items: doctypes.types },
    countries: { reviewed: countries.reviewed, items: countries.countries },
    ectd: { index: ectdIndex, tables },
    recognition,
    templates: load('templates/eg-eda.yaml'),
    vocab: { forms: load('vocab/forms.yaml'), countries: JSON.parse(read('vocab/countries.json')) },
    checks: {
      ...(fs.existsSync(path.join(KNOWLEDGE, 'checks', 'citations.json')) ? JSON.parse(read('checks/citations.json')) : { citations: [], sources: {}, summary: {} }),
      findings: fs.existsSync(path.join(KNOWLEDGE, 'checks', 'findings.yaml')) ? load('checks/findings.yaml') : { findings: [] },
    },
  };
}

// The copies of the sources kept in the repository: each must exist and, where the manifest lists it, match its fingerprint.
export function checkHeldFiles(data) {
  const errors = [];
  const manifest = new Map();
  const mf = path.join(REPO, 'docs', 'ctd', 'sources', 'MANIFEST.json');
  if (fs.existsSync(mf)) for (const m of JSON.parse(fs.readFileSync(mf, 'utf8'))) manifest.set(m.file, m.sha256);
  for (const s of data.sources) {
    if (!s.held) continue;
    const f = path.join(REPO, s.file);
    if (!fs.existsSync(f)) { errors.push(`source ${s.id}: its copy ${s.file} is missing`); continue; }
    const want = manifest.get(path.basename(s.file));
    if (want && fs.statSync(f).isFile()) {
      const got = crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
      if (got !== want) errors.push(`source ${s.id}: ${s.file} differs from the copy recorded in MANIFEST.json`);
    }
  }
  return errors;
}
