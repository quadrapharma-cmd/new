// Loads the PRIVATE seed directory (real company data, outside the repo) into the shape the mock runtime expects.
// Never copies anything into the repo. Returns null when the directory does not exist.
//
// Accepted layouts under STRIFA_SEED_DIR (default /home/user/.strifa-private/seed):
//   seed.json                 -> { "<collection>": { "<docId>": doc } }  (complete)
//   <collection>.json         -> either { "<docId>": doc } or [doc, ...] (doc id taken from id | code | n | year | no)
//   meta.json                 -> { config, counters, groups }  (meta docs by id)
//   registers.json            -> { "<registerName>": { items, source } }
//   <collection>/<docId>.json -> one file per document
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, basename } from 'node:path';
import { COLLECTION_NAMES } from '../src/data/schema.js';

export const DEFAULT_SEED_DIR = '/home/user/.strifa-private/seed';

const idOf = (doc, name) => {
  if (name === 'entries' && Number.isInteger(doc.no)) return `e${String(doc.no).padStart(6, '0')}`;
  return doc.id ?? doc.code ?? doc.n ?? doc.year ?? doc.no ?? null;
};
function readJson(p) {
  return JSON.parse(readFileSync(p, 'utf8'));
}
function toMap(content, name) {
  if (Array.isArray(content)) {
    const out = {};
    content.forEach((doc, i) => {
      out[String(idOf(doc, name) ?? i)] = doc;
    });
    return out;
  }
  return content;
}

export function loadSeedDir(dir = process.env.STRIFA_SEED_DIR || DEFAULT_SEED_DIR) {
  if (!dir || !existsSync(dir) || !statSync(dir).isDirectory()) return null;
  const seed = {};
  const single = join(dir, 'seed.json');
  if (existsSync(single)) {
    for (const [name, map] of Object.entries(readJson(single))) seed[name] = toMap(map, name);
  }
  for (const f of readdirSync(dir)) {
    const p = join(dir, f);
    if (statSync(p).isDirectory()) {
      if (!COLLECTION_NAMES.includes(f)) continue;
      seed[f] = seed[f] || {};
      for (const g of readdirSync(p)) if (g.endsWith('.json')) seed[f][basename(g, '.json')] = readJson(join(p, g));
    } else if (f.endsWith('.json') && f !== 'seed.json') {
      const name = basename(f, '.json');
      if (COLLECTION_NAMES.includes(name)) seed[name] = { ...(seed[name] || {}), ...toMap(readJson(p), name) };
    }
  }
  return Object.keys(seed).length ? seed : null;
}
