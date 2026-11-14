// Checks every piece of knowledge and writes it as one file (dist/knowledge.json) for the program and the library.
// Stops on any error: a record without a source, a citation of an unregistered source, a broken reference, a missing copy.
import fs from 'node:fs';
import path from 'node:path';
import { loadKnowledge, checkHeldFiles, ROOT } from './load.mjs';
import { validate } from '../core/validate.js';

const data = loadKnowledge();
const { errors, warnings } = validate(data);
errors.push(...checkHeldFiles(data));

for (const w of warnings) console.warn('warning:', w);
if (errors.length) {
  for (const e of errors) console.error('error:', e);
  console.error(`\n${errors.length} error(s) — nothing written.`);
  process.exit(1);
}
fs.mkdirSync(path.join(ROOT, 'dist'), { recursive: true });
fs.writeFileSync(path.join(ROOT, 'dist', 'knowledge.json'), JSON.stringify(data));
console.log([
  `authorities ${data.authorities.length}`, `sources ${data.sources.length}`, `requirements ${data.requirements.length}`,
  `review rules ${data.rules.length}`, `variations ${data.variations.items.length}`, `document types ${data.doctypes.items.length}`,
  `countries ${data.countries.items.length}`, `eCTD tables ${Object.keys(data.ectd.tables).length}`,
  `warnings ${warnings.length}`,
].join(' · '));
