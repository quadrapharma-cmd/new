// Checks every piece of knowledge, then writes:
//   dist/knowledge.json           the knowledge as one file, for the program
//   dist/library.html             the library as one self-contained page, to open on the desktop
//   dist/library-artifact.html    the same page without the document shell, for the claude.ai artifact
// Stops on any error: a record without a source, a citation of an unregistered source, a broken reference, a missing copy.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as esbuild from 'esbuild';
import { loadKnowledge, checkHeldFiles, ROOT } from './load.mjs';
import { validate } from '../core/validate.js';

const FONTS = 'https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans+Arabic:wght@400;500;600&family=Readex+Pro:wght@500;600&display=swap';

export async function build({ quiet = false } = {}) {
  const log = quiet ? () => {} : console.log;
  const data = loadKnowledge();
  const { errors, warnings } = validate(data);
  errors.push(...checkHeldFiles(data));
  for (const w of warnings) console.warn('warning:', w);
  if (errors.length) {
    for (const e of errors) console.error('error:', e);
    throw new Error(`${errors.length} error(s) — nothing written.`);
  }
  const dist = path.join(ROOT, 'dist');
  fs.mkdirSync(dist, { recursive: true });
  const json = JSON.stringify(data);
  fs.writeFileSync(path.join(dist, 'knowledge.json'), json);

  // The library: one script, one style sheet and the knowledge, all inside the page.
  const bundle = await esbuild.build({
    entryPoints: [path.join(ROOT, 'library', 'app.js')], bundle: true, format: 'iife', minify: true,
    target: ['es2022'], write: false, legalComments: 'none',
  });
  const js = bundle.outputFiles[0].text.replace(/<\/script/gi, '<\\/script');
  const css = fs.readFileSync(path.join(ROOT, 'library', 'style.css'), 'utf8');
  const safeJson = json.replace(/</g, '\\u003c');
  const head = [
    '<title>Dossier Builder Library</title>',
    '<meta name="claude:viewport-fit-sides" content="cover">',
    '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
    `<link rel="stylesheet" href="${FONTS}">`,
    `<style>${css}</style>`,
  ].join('\n');
  const body = [
    '<div id="app"></div>',
    `<script type="application/json" id="kdata">${safeJson}</script>`,
    `<script>${js}</script>`,
  ].join('\n');
  // The artifact wraps the page in its own document shell; the desktop page carries one.
  fs.writeFileSync(path.join(dist, 'library-artifact.html'), `${head}\n${body}\n`);
  fs.writeFileSync(path.join(dist, 'library.html'), `<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<style>[hidden]{display:none!important}:root{padding:env(safe-area-inset-top,0px) 0 env(safe-area-inset-bottom,0px)}</style>
${head}
</head>
<body>
${body}
</body>
</html>
`);
  log([
    `authorities ${data.authorities.length}`, `sources ${data.sources.length}`, `requirements ${data.requirements.length}`,
    `review rules ${data.rules.length}`, `variations ${data.variations.items.length}`, `document types ${data.doctypes.items.length}`,
    `countries ${data.countries.items.length}`, `eCTD tables ${Object.keys(data.ectd.tables).length}`, `warnings ${warnings.length}`,
  ].join(' · '));
  log(`library: dist/library.html ${(fs.statSync(path.join(dist, 'library.html')).size / 1024).toFixed(0)} KB`);
  return { data, warnings };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  build().catch(e => { console.error(e.message); process.exit(1); });
}
