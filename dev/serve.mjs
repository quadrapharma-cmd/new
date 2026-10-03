// Dev server: serves dist/index.html wrapped like the claude.ai publisher does (doctype/head/body + safe-area reset),
// with the in-memory mock runtime injected BEFORE the app script (window.claude exists first, as on the real platform).
//   npm run dev [-- --port 5173] [--private] [--watch]
// Query flags: ?ro=1 read-only, ?nodb=1 no db, ?nouser=1, ?empty=1 empty db, ?seed=private, ?latency=200
import { createServer } from 'node:http';
import { readFileSync, existsSync, watch } from 'node:fs';
import { spawn } from 'node:child_process';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
import { loadSeedDir } from './load-seed.js';
import { assemble } from '../scripts/build.mjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DIST = join(ROOT, 'dist/index.html');

const SKELETON_HEAD =
  '<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">' +
  '<style>:root{color-scheme:light;padding:env(safe-area-inset-top,0px) 0 env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,sans-serif;background:#fafafa}img{max-width:100%}[hidden]{display:none!important}</style>' +
  '<script src="/__dev/mock.js"></script></head><body>';
const SKELETON_TAIL = '</body></html>';

async function bundleMock() {
  const r = await build({
    entryPoints: [join(ROOT, 'dev/mock-install.js')],
    bundle: true,
    write: false,
    format: 'iife',
    platform: 'browser',
    target: ['es2020'],
    charset: 'utf8',
    logLevel: 'warning',
  });
  return r.outputFiles[0].text;
}

export async function startServer({ port = 0, privateSeed = false, quiet = false } = {}) {
  const mockJs = await bundleMock();
  let seed = null;
  if (privateSeed || process.env.STRIFA_SEED_DIR) {
    try {
      seed = loadSeedDir();
    } catch (e) {
      console.warn('private seed could not be read:', e.message);
    }
  }
  const server = createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    const send = (code, type, body) => {
      res.writeHead(code, { 'content-type': type, 'cache-control': 'no-store' });
      res.end(body);
    };
    if (url.pathname === '/favicon.ico') return send(204, 'image/x-icon', '');
    if (url.pathname === '/__dev/mock.js') return send(200, 'text/javascript; charset=utf-8', mockJs);
    if (url.pathname === '/__dev/seed.json') return seed ? send(200, 'application/json', JSON.stringify(seed)) : send(404, 'text/plain', 'no private seed');
    if (url.pathname === '/__gallery') {
      assemble({ entry: join(ROOT, 'dev/gallery.jsx'), minify: false }).then(
        ({ html }) => send(200, 'text/html; charset=utf-8', SKELETON_HEAD + html + SKELETON_TAIL),
        (e) => send(500, 'text/plain; charset=utf-8', String(e.stack || e)),
      );
      return;
    }
    if (url.pathname === '/' || url.pathname === '/index.html') {
      if (!existsSync(DIST)) return send(500, 'text/plain', 'dist/index.html missing: run npm run build first');
      return send(200, 'text/html; charset=utf-8', SKELETON_HEAD + readFileSync(DIST, 'utf8') + SKELETON_TAIL);
    }
    return send(404, 'text/plain', 'not found');
  });
  await new Promise((r) => server.listen(port, '127.0.0.1', r));
  const actual = server.address().port;
  if (!quiet) console.log(`Strifa dev server: http://127.0.0.1:${actual}/  (private seed: ${seed ? 'loaded' : 'none'})`);
  return { url: `http://127.0.0.1:${actual}`, port: actual, close: () => new Promise((r) => server.close(r)), hasPrivateSeed: !!seed };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const port = Number(args[args.indexOf('--port') + 1]) || 5173;
  await startServer({ port, privateSeed: args.includes('--private') });
  if (args.includes('--watch')) {
    let t;
    watch(join(ROOT, 'src'), { recursive: true }, () => {
      clearTimeout(t);
      t = setTimeout(() => spawn(process.execPath, [join(ROOT, 'scripts/build.mjs')], { stdio: 'inherit' }), 200);
    });
    console.log('watching src/ for changes (rebuilds dist/index.html)');
  }
}
