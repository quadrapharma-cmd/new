// Finishes a program built quickly (WASM_OPT_SKIP=1 node tools/craft/build.mjs <app> web) without building it again: each
// WebAssembly file in vendor/craft/<app>-web/ goes through wasm-opt (binaryen 132, the wrapper in ~/.local/bin) at the level the
// program's own index.html asks for — data-wasm-opt and data-wasm-opt-params on its <link data-trunk rel="rust"> — as trunk does
// when it is not skipped. build-info.json records the sizes before and after and the time it took.
//   node tools/craft/optimize.mjs <app> [<app>…]
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
const PINS = JSON.parse(fs.readFileSync(path.join(HERE, 'PINS.json'), 'utf8'));

// The program's Rust targets as its index.html declares them: [{bin, worker, level, params}].
export function targets(html) {
  return [...html.matchAll(/<link\b[^>]*\brel="rust"[^>]*>/g)].map(([tag]) => {
    const attr = name => (tag.match(new RegExp(`\\b${name}="([^"]*)"`)) || [])[1];
    return { bin: attr('data-bin') || null, worker: attr('data-type') === 'worker', href: attr('href') || null,
             level: attr('data-wasm-opt') || null, params: (attr('data-wasm-opt-params') || '').split(/\s+/).filter(Boolean) };
  });
}

// Which target a built file belongs to: the one whose name starts the file's name (the worker's crate name for a worker),
// otherwise the one main target without a name.
export function targetOf(file, list) {
  const named = list.find(t => (t.bin && file.startsWith(t.bin + '-')) || (t.worker && t.href && file.startsWith(path.basename(path.dirname(t.href)) + '-')));
  return named || list.find(t => !t.bin && !t.worker) || null;
}

export function optimize(app) {
  const pin = PINS.apps[app];
  if (!pin) throw new Error(`unknown program «${app}»`);
  const out = path.join(ROOT, 'vendor', 'craft', `${app}-web`);
  const html = fs.readFileSync(path.join(ROOT, '.cache', `${app}-src`, pin.web, 'index.html'), 'utf8');
  const list = targets(html);
  const done = [];
  for (const file of fs.readdirSync(out).filter(f => f.endsWith('.wasm')).sort()) {
    const t = targetOf(file, list);
    if (!t || !t.level || t.level === '0') { done.push({ file, skipped: 'no level asked' }); continue; }
    const src = path.join(out, file), tmp = src + '.opt';
    const before = fs.statSync(src).size, t0 = Date.now();
    const r = spawnSync('wasm-opt', [`--output=${tmp}`, `-O${t.level}`, ...t.params, src],
                        { stdio: ['ignore', 'inherit', 'inherit'], env: { ...process.env, WASM_OPT_SKIP: '' } });
    if (r.status !== 0) { fs.rmSync(tmp, { force: true }); throw new Error(`${app}: wasm-opt failed on ${file} (exit ${r.status})`); }
    fs.renameSync(tmp, src);
    done.push({ file, level: t.level, params: t.params, before, after: fs.statSync(src).size, seconds: Math.round((Date.now() - t0) / 1000) });
  }
  const infoFile = path.join(out, 'build-info.json');
  const info = JSON.parse(fs.readFileSync(infoFile, 'utf8'));
  info.optimized = { on: new Date().toISOString().slice(0, 10), files: done };
  for (const f of info.files) { const d = done.find(x => x.file === f.name && x.after); if (d) f.bytes = d.after; }
  info.total_bytes = info.files.reduce((s, f) => s + f.bytes, 0);
  fs.writeFileSync(infoFile, JSON.stringify(info, null, 1));
  return done;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const mb = b => (b / 1048576).toFixed(1) + ' MB';
  for (const app of process.argv.slice(2)) {
    try {
      for (const d of optimize(app)) {
        console.log(d.after ? `${app}: ${d.file} -O${d.level} ${mb(d.before)} → ${mb(d.after)} in ${d.seconds} s` : `${app}: ${d.file} ${d.skipped}`);
      }
    } catch (e) { console.error(e.message); process.exitCode = 1; }
  }
}
