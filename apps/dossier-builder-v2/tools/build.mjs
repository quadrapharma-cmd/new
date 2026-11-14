// Checks every piece of knowledge, then writes:
//   dist/knowledge.json           the knowledge as one file, for the program
//   dist/library/                 the library for the desktop: index.html and sources/ (the copies of the sources it opens)
//   dist/Dossier-Builder-Library.zip   the same folder in one file, to hand over
//   dist/library-artifact.html    the same page without the document shell, for the claude.ai artifact
//   dist/artifact-files.json      the source copies to publish beside it (sources/<file> → the copy in the repository)
// Stops on any error: a record without a source, a citation of an unregistered source, a broken reference, a missing copy.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import * as esbuild from 'esbuild';
import { loadKnowledge, checkHeldFiles, ROOT, REPO } from './load.mjs';
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
  // The text of each source kept in the project (read by tools/verify-sources.mjs into dist/texts/), for searching inside it.
  const textDir = path.join(dist, 'texts');
  data.textIds = data.sources.filter(s => s.held && fs.existsSync(path.join(textDir, `${s.id}.json`))).map(s => s.id);
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
  // The artifact wraps the page in its own document shell; the desktop page carries one. The artifact serves PDF and CSV
  // files only, so its page opens only those; the desktop folder holds every copy.
  fs.writeFileSync(path.join(dist, 'library-artifact.html'), `${head}\n<script>window.DBK_OPEN=['pdf','csv']</script>\n${body}\n`);
  const page = `<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<style>[hidden]{display:none!important}:root{padding:env(safe-area-inset-top,0px) 0 env(safe-area-inset-bottom,0px)}</style>
${head}
</head>
<body>
<script>window.DBK_OPEN=['pdf','csv','doc','docx','xlsx','zip','md']</script>
${body}
</body>
</html>
`;
  // The desktop library: the page and, beside it, the copies of the sources it opens.
  const held = data.sources.filter(s => s.held && s.file && fs.existsSync(path.join(REPO, s.file)) && fs.statSync(path.join(REPO, s.file)).isFile());
  const libDir = path.join(dist, 'library');
  fs.rmSync(libDir, { recursive: true, force: true });
  fs.mkdirSync(path.join(libDir, 'sources'), { recursive: true });
  fs.writeFileSync(path.join(libDir, 'index.html'), page);
  const files = {};
  for (const s of held) {
    const name = path.basename(s.file);
    fs.copyFileSync(path.join(REPO, s.file), path.join(libDir, 'sources', name));
    if (/\.(pdf|csv)$/i.test(name)) files[`sources/${name}`] = path.relative(REPO, path.join(REPO, s.file));
  }
  fs.mkdirSync(path.join(libDir, 'texts'), { recursive: true });
  for (const id of data.textIds) {
    // characters a PDF's text layer could not name (U+FFFD) carry nothing to find: dropped
    const pages = JSON.parse(fs.readFileSync(path.join(textDir, `${id}.json`), 'utf8')).pages.map(p => p.replace(/\uFFFD/g, ''));
    fs.writeFileSync(path.join(libDir, 'texts', `${id}.js`), `window.DBK_TEXT&&window.DBK_TEXT(${JSON.stringify(id)},${JSON.stringify(pages)});\n`);
    files[`texts/${id}.js`] = path.relative(REPO, path.join(libDir, 'texts', `${id}.js`));
  }
  fs.writeFileSync(path.join(dist, 'artifact-files.json'), JSON.stringify(files, null, 1));
  const zip = path.join(dist, 'Dossier-Builder-Library.zip');
  fs.rmSync(zip, { force: true });
  if (!quiet || process.env.LIBRARY_ZIP) {
    try { execFileSync('zip', ['-q', '-r', zip, '.'], { cwd: libDir }); }
    catch { execFileSync('python3', ['-I', '-c', 'import shutil,sys; shutil.make_archive(sys.argv[1][:-4], "zip", sys.argv[2])', zip, libDir]); }
  }
  log([
    `authorities ${data.authorities.length}`, `sources ${data.sources.length}`, `requirements ${data.requirements.length}`,
    `review rules ${data.rules.length}`, `variations ${data.variations.items.length}`, `document types ${data.doctypes.items.length}`,
    `countries ${data.countries.items.length}`, `eCTD tables ${Object.keys(data.ectd.tables).length}`, `warnings ${warnings.length}`,
  ].join(' · '));
  log(`library: dist/library/index.html ${(fs.statSync(path.join(libDir, 'index.html')).size / 1024).toFixed(0)} KB, ${held.length} source copies and ${data.textIds.length} source texts beside it`);
  return { data, warnings };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  build().catch(e => { console.error(e.message); process.exit(1); });
}
