// Writing a ZIP file (the dossier saved as one file, the ready dossier's folder): names in UTF-8 (Arabic names open as they are
// on Windows and macOS), each file deflated where that makes it smaller (CompressionStream, in browsers and Node), a CRC-32 for
// each. No ZIP64: a file or an archive over 4 GB is refused with the reason.
const TABLE = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
export function crc32(bytes, crc = 0) {
  let c = ~crc >>> 0;
  for (let i = 0; i < bytes.length; i++) c = TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return ~c >>> 0;
}

async function deflate(bytes) {
  if (typeof CompressionStream === 'undefined') return null;
  const stream = new Blob([bytes]).stream().pipeThrough(new CompressionStream('deflate-raw'));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

function dosTime(d) {
  const t = (d.getHours() << 11) | (d.getMinutes() << 5) | Math.floor(d.getSeconds() / 2);
  const day = ((Math.max(1980, d.getFullYear()) - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
  return { t, day };
}

// files: [{name: 'Module 1/1.1.1 Application form.pdf', bytes: Uint8Array, date?: Date, store?: true}] → Uint8Array (the .zip)
export async function zipOf(files, { now = new Date() } = {}) {
  const enc = new TextEncoder();
  const parts = [], central = [];
  let offset = 0;
  const seen = new Set();
  for (const f of files) {
    const name = String(f.name).replace(/\\/g, '/').replace(/^\/+/, '');
    if (!name || seen.has(name)) throw new Error(`the archive would hold «${name}» twice`);
    seen.add(name);
    const data = f.bytes instanceof Uint8Array ? f.bytes : new Uint8Array(f.bytes);
    if (data.length >= 0xffffffff) throw new Error(`«${name}» is over 4 GB: too large for this archive`);
    const crc = crc32(data);
    let body = data, method = 0;
    if (!f.store && data.length > 64) {
      const z = await deflate(data);
      if (z && z.length < data.length) { body = z; method = 8; }
    }
    const nameBytes = enc.encode(name);
    const { t, day } = dosTime(f.date || now);
    const local = new DataView(new ArrayBuffer(30));
    local.setUint32(0, 0x04034b50, true); local.setUint16(4, 20, true); local.setUint16(6, 0x0800, true); local.setUint16(8, method, true);
    local.setUint16(10, t, true); local.setUint16(12, day, true); local.setUint32(14, crc, true);
    local.setUint32(18, body.length, true); local.setUint32(22, data.length, true); local.setUint16(26, nameBytes.length, true); local.setUint16(28, 0, true);
    parts.push(new Uint8Array(local.buffer), nameBytes, body);
    const cen = new DataView(new ArrayBuffer(46));
    cen.setUint32(0, 0x02014b50, true); cen.setUint16(4, 0x0314, true); cen.setUint16(6, 20, true); cen.setUint16(8, 0x0800, true); cen.setUint16(10, method, true);
    cen.setUint16(12, t, true); cen.setUint16(14, day, true); cen.setUint32(16, crc, true); cen.setUint32(20, body.length, true); cen.setUint32(24, data.length, true);
    cen.setUint16(28, nameBytes.length, true); cen.setUint32(38, (0o100644 << 16) >>> 0, true); cen.setUint32(42, offset, true);
    central.push(new Uint8Array(cen.buffer), nameBytes);
    offset += 30 + nameBytes.length + body.length;
    if (offset >= 0xffffffff) throw new Error('the archive is over 4 GB: too large');
  }
  const cenSize = central.reduce((n, p) => n + p.length, 0);
  const end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
  end.setUint32(12, cenSize, true); end.setUint32(16, offset, true);
  const all = [...parts, ...central, new Uint8Array(end.buffer)];
  const out = new Uint8Array(all.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of all) { out.set(p, at); at += p.length; }
  return out;
}
