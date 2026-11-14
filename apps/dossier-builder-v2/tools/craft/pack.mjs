// Packs a built program for the claude.ai artifact, where one published file may hold 15 MB at most: every file is
// gzipped, and a file still over the limit is cut into numbered parts. The page puts the parts back together, unpacks them
// with the browser's own DecompressionStream and hands the bytes to the program — only when the user opens it.
//   node tools/craft/pack.mjs <app>   → vendor/craft/<app>-pack/ (files.json lists every file, its parts and its SHA-256)
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
export const PART = 14 * 1024 * 1024;   // under the artifact's 15 MB per file, with room

export function pack(app, src = path.join(ROOT, 'vendor', 'craft', `${app}-web`), out = path.join(ROOT, 'vendor', 'craft', `${app}-pack`)) {
  fs.rmSync(out, { recursive: true, force: true });
  fs.mkdirSync(out, { recursive: true });
  const files = [];
  const walk = dir => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) { walk(p); continue; }
      const rel = path.relative(src, p);
      const raw = fs.readFileSync(p);
      const gz = zlib.gzipSync(raw, { level: 9 });
      const parts = [];
      for (let i = 0, n = 0; i < gz.length; i += PART, n++) {
        const name = `${rel.replace(/[\\/]/g, '__')}.gz.${String(n).padStart(2, '0')}`;
        fs.writeFileSync(path.join(out, name), gz.subarray(i, i + PART));
        parts.push(name);
      }
      files.push({ path: rel, bytes: raw.length, gz_bytes: gz.length, sha256: crypto.createHash('sha256').update(raw).digest('hex'), parts });
    }
  };
  walk(src);
  fs.writeFileSync(path.join(out, 'files.json'), JSON.stringify({ app, part_bytes: PART, files }, null, 1));
  return files;
}

// The page side, as text to put in the page: fetch a packed file's parts, join them, unpack them, check the SHA-256.
export const LOADER = `async function dbkUnpack(base, entry){
  const parts = await Promise.all(entry.parts.map(p => fetch(base + p).then(r => { if (!r.ok) throw new Error(p + ': ' + r.status); return r.arrayBuffer(); })));
  const joined = new Blob(parts);
  const bytes = new Uint8Array(await new Response(joined.stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
  const sum = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2, '0')).join('');
  if (sum !== entry.sha256) throw new Error(entry.path + ': damaged in transit');
  return bytes;
}`;

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const app = process.argv[2];
  const files = pack(app);
  const mb = b => (b / 1048576).toFixed(1);
  for (const f of files) console.log(`${f.path}: ${mb(f.bytes)} MB → ${mb(f.gz_bytes)} MB gzipped in ${f.parts.length} part(s)`);
}
