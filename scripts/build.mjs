// Bundles src/ -> one IIFE, inlines CSS + JS into src/index.html.tpl -> dist/index.html.
// Fails when the page exceeds 12 MB or breaks a hard platform rule (see AGENTS.md).
import { build as esbuild, transform } from 'esbuild';
import { mkdirSync, readFileSync, writeFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { ROOT, ENTRY, bundleOptions, usedStubs } from '../esbuild.config.mjs';

const MAX_BYTES = 12 * 1024 * 1024;
const kb = (n) => `${(n / 1024).toFixed(1)} KB`;

// ---- lint: things that silently break the published page ------------------------------------
const FORBIDDEN = [
  [/\balert\s*\(/, 'alert()'],
  [/(^|[^.\w])confirm\s*\(/, 'confirm()'],
  [/(^|[^.\w])prompt\s*\(/, 'prompt()'],
  [/window\.print\s*\(/, 'window.print()'],
  [/\beval\s*\(/, 'eval()'],
  [/new\s+Function\s*\(/, 'new Function()'],
  [/<a\b[^>]*\sdownload[\s=>]/, '<a download>'],
  [/URL\.createObjectURL/, 'blob URL'],
  [/(^|[^\w])(mailto|tel):/, 'mailto:/tel: link'],
  [/serviceWorker/, 'service worker'],
  [/\bfetch\s*\(\s*["'`]https?:/, 'external fetch'],
  [/new\s+WebSocket/, 'WebSocket'],
];
function walk(dir, out = []) {
  for (const f of readdirSync(dir)) {
    const p = join(dir, f);
    if (statSync(p).isDirectory()) walk(p, out);
    else if (/\.(js|jsx|css|tpl)$/.test(f)) out.push(p);
  }
  return out;
}
function lintSources() {
  const bad = [];
  for (const file of walk(join(ROOT, 'src'))) {
    const rel = relative(ROOT, file);
    const text = readFileSync(file, 'utf8')
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/(^|[^:])\/\/.*$/gm, '$1');
    for (const [re, name] of FORBIDDEN) if (re.test(text)) bad.push(`${rel}: ${name}`);
  }
  return bad;
}

// ---- css -------------------------------------------------------------------------------------
function readCss() {
  const dir = join(ROOT, 'src/styles');
  const read = (f) => readFileSync(join(dir, f), 'utf8');
  const dark = read('dark.css').trim();
  const order = ['tokens.css', 'base.css', 'layout.css', 'components.css', 'screens.css'];
  let css = order.filter((f) => existsSync(join(dir, f))).map(read).join('\n');
  // per-screen styles: src/styles/screens/<name>.css (one file per screen owner), appended in name order
  const sdir = join(dir, 'screens');
  if (existsSync(sdir)) {
    for (const f of readdirSync(sdir).filter((n) => n.endsWith('.css')).sort()) css += '\n' + readFileSync(join(sdir, f), 'utf8');
  }
  css += `\n@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){${dark}}}\n:root[data-theme="dark"]{${dark}}\n`;
  return css;
}

/** Bundle + inline everything; returns the page without writing it (the dev gallery reuses this with another entry). */
export async function assemble({ entry = ENTRY, minify = true } = {}) {
  // The engine barrel must exist so UI imports resolve; the engine owner overwrites it.
  const barrel = join(ROOT, 'src/engine/index.js');
  if (!existsSync(barrel)) {
    mkdirSync(join(ROOT, 'src/engine'), { recursive: true });
    writeFileSync(barrel, '// Engine barrel: owned by F2 (engine). Placeholder created by the shell build.\n');
  }
  const result = await esbuild(bundleOptions({ minify, entry }));
  let js = result.outputFiles[0].text;
  js = js.replace(/<\/script/gi, '<\\/script').replace(/<!--/g, '\\x3C!--');

  const css = (await transform(readCss(), { loader: 'css', minify })).code;
  if (/<\/style/i.test(css)) throw new Error('CSS contains </style');

  const tpl = readFileSync(join(ROOT, 'src/index.html.tpl'), 'utf8');
  if (!tpl.trimStart().startsWith('<title>')) throw new Error('template must start with <title>');
  if (!tpl.includes('{{STYLE}}') || !tpl.includes('{{SCRIPT}}')) throw new Error('template placeholders missing');
  // function replacers: the bundle contains "$&"-style sequences that String.replace would expand
  const html = tpl.replace('{{STYLE}}', () => css).replace('{{SCRIPT}}', () => js);
  return { html, js, css, warnings: result.warnings };
}

async function main() {
  const problems = lintSources();
  if (problems.length) {
    console.error('Build blocked: forbidden patterns found in src/:\n  ' + problems.join('\n  '));
    process.exit(1);
  }
  const { html, js, css, warnings } = await assemble();
  const DISTDIR = process.env.STRIFA_DIST || 'dist';
  mkdirSync(join(ROOT, DISTDIR), { recursive: true });
  writeFileSync(join(ROOT, DISTDIR, 'index.html'), html);
  const size = Buffer.byteLength(html);

  console.log(`${DISTDIR}/index.html  ${kb(size)}  (${(size / 1048576).toFixed(2)} MB)  js ${kb(Buffer.byteLength(js))}  css ${kb(Buffer.byteLength(css))}`);
  if (usedStubs.size) console.log(`note: dev stubs used for not-yet-created modules: ${[...usedStubs].join(', ')}`);
  for (const w of warnings) console.warn('warning:', w.text);
  if (size > MAX_BYTES) {
    console.error(`Build failed: page is ${(size / 1048576).toFixed(2)} MB, over the 12 MB limit`);
    process.exit(1);
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch((e) => {
    console.error(e.message || e);
    process.exit(1);
  });
}
