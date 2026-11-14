// Builds the Crafting Apps the dossier tools rest on, from their source at the pinned release (tools/craft/PINS.json):
//   node tools/craft/build.mjs <app> web [--keep]   → vendor/craft/<app>-web/  the program in the browser (index.html, .js, .wasm)
//   node tools/craft/build.mjs <app> wasi [--keep]  → vendor/craft/<app>-wasi/ the command-line program for the browser (WASI, gzipped)
//   node tools/craft/build.mjs <app> cli [--keep]   → vendor/craft/<app>-cli/  the command-line program for this machine
// The source is fetched once into .cache/<app>-src at the pinned commit (checked), our patches (tools/craft/patches/<app>/*.patch)
// are applied, and the program's licence files are copied beside what the build writes; build-info.json records the version,
// the files, their sizes and how long the build took. The compiler's work folder is removed afterwards (it takes gigabytes),
// unless --keep. Needs: cargo, the wasm32-unknown-unknown target, trunk and wasm-bindgen at the pinned versions, wasm-opt.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
const PINS = JSON.parse(fs.readFileSync(path.join(HERE, 'PINS.json'), 'utf8'));
const CACHE = path.join(ROOT, '.cache');
const VENDOR = path.join(ROOT, 'vendor', 'craft');

const run = (cmd, args, opts = {}) => execFileSync(cmd, args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], ...opts }).trim();

export function ensureSource(app) {
  const pin = PINS.apps[app];
  if (!pin) throw new Error(`unknown program «${app}» (one of: ${Object.keys(PINS.apps).join(', ')})`);
  const src = path.join(CACHE, `${app}-src`);
  if (!fs.existsSync(src)) {
    fs.mkdirSync(CACHE, { recursive: true });
    run('git', ['clone', '-q', '--depth', '1', '--branch', pin.tag, pin.repo, src]);
  }
  const head = run('git', ['-C', src, 'rev-parse', 'HEAD']);
  if (head !== pin.commit) throw new Error(`${app}: the source is at ${head}, the pin says ${pin.commit} (${pin.tag})`);
  return src;
}

// The font collection the programs' releases build with: their web builds embed its Arabic face (Noto Sans Arabic, OFL-1.1),
// the fallback for Arabic text; without it the browser builds draw Arabic as boxes.
export function ensureFonts() {
  const pin = PINS.fonts;
  const dir = path.join(CACHE, 'craft-fonts');
  if (!fs.existsSync(path.join(dir, '.git'))) {
    fs.mkdirSync(dir, { recursive: true });
    run('git', ['-C', dir, 'init', '-q']);
    run('git', ['-C', dir, 'remote', 'add', 'origin', pin.repo]);
    run('git', ['-C', dir, 'fetch', '-q', '--depth', '1', 'origin', pin.commit]);
    run('git', ['-C', dir, 'checkout', '-q', 'FETCH_HEAD']);
  }
  const head = run('git', ['-C', dir, 'rev-parse', 'HEAD']);
  if (head !== pin.commit) throw new Error(`craft-fonts: the checkout is at ${head}, the pin says ${pin.commit}`);
  return dir;
}

export function applyPatches(app, src) {
  const dir = path.join(HERE, 'patches', app);
  if (!fs.existsSync(dir)) return [];
  const applied = [];
  for (const name of fs.readdirSync(dir).filter(n => n.endsWith('.patch')).sort()) {
    const p = path.join(dir, name);
    const already = spawnSync('git', ['-C', src, 'apply', '--reverse', '--check', p]).status === 0;
    if (!already) run('git', ['-C', src, 'apply', p]);
    applied.push(name);
  }
  return applied;
}

function copyLicences(src, out) {
  const dest = path.join(out, 'licenses');
  fs.mkdirSync(dest, { recursive: true });
  for (const f of ['LICENSE-MIT', 'LICENSE-APACHE', 'NOTICE', 'ATTRIBUTION.md', 'LICENSES.toml']) {
    if (fs.existsSync(path.join(src, f))) fs.copyFileSync(path.join(src, f), path.join(dest, f));
  }
  if (fs.existsSync(path.join(src, 'licenses'))) fs.cpSync(path.join(src, 'licenses'), path.join(dest, 'third-party'), { recursive: true });
}

function listFiles(dir, base = dir) {
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...listFiles(p, base));
    else out.push({ name: path.relative(base, p), bytes: fs.statSync(p).size });
  }
  return out.sort((a, b) => b.bytes - a.bytes);
}

export function build(app, kind, { keep = false } = {}) {
  const pin = PINS.apps[app];
  const src = ensureSource(app);
  const patches = applyPatches(app, src);
  const target = path.join(CACHE, `target-${app}-${kind}`);
  const out = path.join(VENDOR, `${app}-${kind}`);
  fs.rmSync(out, { recursive: true, force: true });
  fs.mkdirSync(out, { recursive: true });
  const fonts = ensureFonts();
  const env = { ...process.env, CARGO_TARGET_DIR: target, TRUNK_SKIP_VERSION_CHECK: 'true', CRAFT_FONTS_DIR: fonts };
  const t0 = Date.now();
  let r;
  if (kind === 'web') {
    r = spawnSync('trunk', ['build', '--release', '--dist', out], { cwd: path.join(src, pin.web), env, stdio: 'inherit' });
  } else if (kind === 'cli') {
    r = spawnSync('cargo', ['build', '--release', '--locked', '-p', pin.cli], { cwd: src, env, stdio: 'inherit' });
    if (r.status === 0) {
      const exe = path.join(target, 'release', pin.cli + (process.platform === 'win32' ? '.exe' : ''));
      fs.copyFileSync(exe, path.join(out, path.basename(exe)));
      fs.chmodSync(path.join(out, path.basename(exe)), 0o755);
    }
  } else if (kind === 'wasi') {
    // The command-line program built for WebAssembly with a file system of its own (WASI): the browser runs it in a worker
    // over an in-memory folder, without its screen — the engine behind the automatic steps. No MCP server in it.
    r = spawnSync('cargo', ['build', '--release', '--locked', '--target', 'wasm32-wasip1', '-p', pin.cli, '--no-default-features'],
      { cwd: src, env: { ...env, CARGO_PROFILE_RELEASE_STRIP: 'symbols' }, stdio: 'inherit' });
    if (r.status === 0) {
      const wasm = fs.readFileSync(path.join(target, 'wasm32-wasip1', 'release', `${pin.cli}.wasm`));
      fs.writeFileSync(path.join(out, `${pin.cli}.wasm.gz`), zlib.gzipSync(wasm, { level: 9 }));
    }
  } else throw new Error(`build what? «web», «wasi» or «cli», not «${kind}»`);
  const seconds = Math.round((Date.now() - t0) / 1000);
  if (r.status !== 0) throw new Error(`${app} ${kind}: the build failed after ${seconds} s (exit ${r.status})`);
  copyLicences(src, out);
  // the embedded faces' licences (the web builds keep the Arabic and Georgian interface faces)
  for (const line of fs.readFileSync(path.join(fonts, 'fonts', 'manifest.txt'), 'utf8').split('\n')) {
    const f = line.split(' | ').map(x => x.trim());
    if (f.length < 6 || line.startsWith('#') || (kind === 'web' && !/\b(Arab|Geor)\b/.test(f[3]))) continue;
    const dest = path.join(out, 'licenses', 'fonts', path.basename(path.dirname(f[5])) + '-' + path.basename(f[5]));
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(path.join(fonts, f[5]), dest);
  }
  const files = listFiles(out).filter(f => !f.name.startsWith('licenses'));
  const info = { app, kind, tag: pin.tag, commit: pin.commit, patches, built_on: new Date().toISOString().slice(0, 10), seconds,
                 total_bytes: files.reduce((s, f) => s + f.bytes, 0), files };
  fs.writeFileSync(path.join(out, 'build-info.json'), JSON.stringify(info, null, 1));
  if (!keep) fs.rmSync(target, { recursive: true, force: true });
  return info;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [app, kind] = process.argv.slice(2).filter(a => !a.startsWith('--'));
  try {
    const info = build(app, kind, { keep: process.argv.includes('--keep') });
    const mb = b => (b / 1048576).toFixed(1) + ' MB';
    console.log(`${app} ${kind} ${info.tag}: built in ${info.seconds} s, ${mb(info.total_bytes)} → vendor/craft/${app}-${kind}/`);
    for (const f of info.files.slice(0, 6)) console.log(`  ${mb(f.bytes).padStart(9)}  ${f.name}`);
  } catch (e) { console.error(e.message); process.exit(1); }
}
