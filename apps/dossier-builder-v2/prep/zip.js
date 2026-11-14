// ZIP archives (and the Office files built on them: .docx .xlsx .pptx) opened in the page or in Node, with nothing fetched: the
// central directory read from the end of the file, each entry stored or deflated (the browser's own DecompressionStream). Each
// entry is checked against the CRC-32 the archive keeps for it; one that does not match, or uses a method or an encryption the page
// cannot read, is reported with its reason and never handed over.
const CRC = new Uint32Array(256);
for (let i = 0; i < 256; i++) { let c = i; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; CRC[i] = c; }
export function crc32(d) { let c = 0xffffffff; for (let i = 0; i < d.length; i++) c = CRC[(c ^ d[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; }

const u16 = (b, o) => b[o] | (b[o + 1] << 8);
const u32 = (b, o) => (b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24)) >>> 0;

async function inflate(bytes) {
  const out = new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate-raw')));
  return new Uint8Array(await out.arrayBuffer());
}

// A name as the archive wrote it: UTF-8 when marked so, or given again in UTF-8 in the «Unicode path» extra field (0x7075, written
// by Info-ZIP and others), or written in UTF-8 unmarked (as most tools now do); else read as UTF-8 with the unreadable bytes shown
// as such (Windows' own ZIP writes Arabic names in a DOS code page the browser has no decoder for).
function nameOf(raw, flags, extra) {
  const utf8 = new TextDecoder('utf-8');
  if (flags & 0x800) return utf8.decode(raw);
  for (let i = 0; i + 4 <= extra.length;) {
    const id = u16(extra, i), len = u16(extra, i + 2);
    if (id === 0x7075 && len > 5 && extra[i + 4] === 1) return utf8.decode(extra.subarray(i + 9, i + 4 + len));
    i += 4 + len;
  }
  try { return new TextDecoder('utf-8', { fatal: true }).decode(raw); } catch { return utf8.decode(raw); }
}

// The names in the archive, in the order of its directory: [{name, size, packed, method, crc, at, flags, dir}].
export function entries(bytes) {
  const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let end = -1;
  for (let i = b.length - 22; i >= Math.max(0, b.length - 22 - 65535); i--) if (u32(b, i) === 0x06054b50) { end = i; break; }
  if (end < 0) throw Object.assign(new Error('not a ZIP archive, or a damaged one'), { why: 'damaged' });
  let count = u16(b, end + 10), at = u32(b, end + 16);
  if (count === 0xffff || at === 0xffffffff) throw Object.assign(new Error('a ZIP64 archive (over 4 GB or 65,535 files) is not read yet'), { why: 'zip64' });
  const out = [];
  while (count-- > 0) {
    if (u32(b, at) !== 0x02014b50) throw Object.assign(new Error('the ZIP directory is damaged'), { why: 'damaged' });
    const flags = u16(b, at + 8), method = u16(b, at + 10), crc = u32(b, at + 16), packed = u32(b, at + 20), size = u32(b, at + 24);
    const n = u16(b, at + 28), x = u16(b, at + 30), c = u16(b, at + 32), local = u32(b, at + 42);
    const raw = b.subarray(at + 46, at + 46 + n), extra = b.subarray(at + 46 + n, at + 46 + n + x);
    const name = nameOf(raw, flags, extra);
    out.push({ name: name.replace(/\\/g, '/').split('/').filter(p => p && p !== '.' && p !== '..').join('/'), size, packed, method, crc, at: local, flags,
               dir: raw[raw.length - 1] === 0x2f || raw[raw.length - 1] === 0x5c });
    at += 46 + n + x + c;
  }
  return out;
}

// One entry's content, checked: → Uint8Array, or throws an Error whose .why says why it cannot be read.
export async function read(bytes, e) {
  const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  if (e.flags & 1) throw Object.assign(new Error(`${e.name}: under a password`), { why: 'password' });
  if (u32(b, e.at) !== 0x04034b50) throw Object.assign(new Error(`${e.name}: damaged`), { why: 'damaged' });
  const start = e.at + 30 + u16(b, e.at + 26) + u16(b, e.at + 28);
  const data = b.subarray(start, start + e.packed);
  let out;
  if (e.method === 0) out = data.slice();
  else if (e.method === 8) out = await inflate(data);
  else throw Object.assign(new Error(`${e.name}: packed with method ${e.method}, which is not read yet`), { why: 'unsupported' });
  if (out.length !== e.size || crc32(out) !== e.crc) throw Object.assign(new Error(`${e.name}: its content does not match its check`), { why: 'unreadable' });
  return out;
}

// Every file in the archive: → {files: [{name, bytes}], skipped: [{name, why}]}.
export async function unzip(bytes, { skip = () => false } = {}) {
  const files = [], skipped = [];
  for (const e of entries(bytes)) {
    if (e.dir || skip(e.name)) continue;
    try { files.push({ name: e.name, bytes: await read(bytes, e) }); } catch (err) { skipped.push({ name: e.name, why: err.why || 'unreadable' }); }
  }
  return { files, skipped };
}
