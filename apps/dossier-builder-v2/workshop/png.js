// RGBA pixels as a PNG file (the PNG specification, W3C): the signature, a header, the rows deflated (each with filter 0), the end.
// For a picture the browser cannot hand over as a PNG itself (a Photoshop file's picture, read in workshop/psd.js), here and in Node.
import { crc32 } from './zipw.js';

const be32 = n => [n >>> 24 & 255, n >>> 16 & 255, n >>> 8 & 255, n & 255];
function chunk(type, data) {
  const head = new Uint8Array([...be32(data.length), ...[...type].map(c => c.charCodeAt(0))]);
  const body = new Uint8Array(4 + data.length);
  body.set(head.subarray(4)); body.set(data, 4);
  return [head.subarray(0, 4), body, new Uint8Array(be32(crc32(body)))];
}
async function zlib(bytes) {
  return new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new CompressionStream('deflate'))).arrayBuffer());
}

export async function pngOf({ width, height, rgba }) {
  const row = width * 4, raw = new Uint8Array((row + 1) * height);
  for (let y = 0; y < height; y++) raw.set(rgba.subarray(y * row, (y + 1) * row), y * (row + 1) + 1);
  const header = new Uint8Array([...be32(width), ...be32(height), 8, 6, 0, 0, 0]);          // 8 bits, RGBA, deflate, filter 0, no interlace
  const parts = [new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10]), ...chunk('IHDR', header), ...chunk('IDAT', await zlib(raw)), ...chunk('IEND', new Uint8Array(0))];
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) { out.set(p, at); at += p.length; }
  return out;
}
