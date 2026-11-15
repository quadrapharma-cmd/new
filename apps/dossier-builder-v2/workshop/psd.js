// The picture a Photoshop file shows: its merged image (the «composite» every PSD and PSB carries after its layers), as RGBA pixels.
// The photo program saves a picture opened from the workshop as a PSD (Ctrl+S keeps the layers); the workshop puts the picture it
// shows back into the dossier. Read from the file format's public description (Adobe Photoshop File Formats Specification): the
// header, three sections skipped by their lengths, then the image data — raw or PackBits (RLE) per row, one plane per channel.
//   psdComposite(bytes) → { width, height, rgba: Uint8ClampedArray }   (throws {why: 'psd-…'} for what it cannot read)
const MODES = { 1: 'gray', 3: 'rgb', 4: 'cmyk' };

export function psdComposite(bytes) {
  const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  const v = new DataView(b.buffer, b.byteOffset, b.byteLength);
  const fail = (why, detail = '') => { throw Object.assign(new Error(`${why}${detail ? `: ${detail}` : ''}`), { why }); };
  if (b.length < 26 || String.fromCharCode(b[0], b[1], b[2], b[3]) !== '8BPS') fail('psd-not-psd');
  const version = v.getUint16(4);                       // 1: PSD, 2: PSB (large document)
  if (version !== 1 && version !== 2) fail('psd-version', String(version));
  const channels = v.getUint16(12), height = v.getUint32(14), width = v.getUint32(18), depth = v.getUint16(22), mode = MODES[v.getUint16(24)];
  if (!mode) fail('psd-mode', String(v.getUint16(24)));
  if (depth !== 8 && depth !== 16) fail('psd-depth', String(depth));
  if (!width || !height || width * height > 200e6) fail('psd-size', `${width}×${height}`);
  let o = 26;
  const need = n => { if (o + n > b.length) fail('psd-short'); };
  const skip32 = () => { need(4); const n = v.getUint32(o); o += 4 + n; };
  skip32();                                             // colour mode data
  skip32();                                             // image resources
  if (version === 2) { need(8); const n = v.getUint32(o) * 2 ** 32 + v.getUint32(o + 4); o += 8 + n; } else skip32();   // layers and masks
  need(2);
  const compression = v.getUint16(o); o += 2;
  const colour = mode === 'gray' ? 1 : mode === 'rgb' ? 3 : 4;
  const planes = Math.min(channels, colour + 1);        // the colour channels, and alpha when there is one more
  const rowBytes = width * depth / 8;
  const plane = new Array(planes);
  if (compression === 0) {
    for (let c = 0; c < planes; c++) { need(rowBytes * height); plane[c] = b.subarray(o, o + rowBytes * height); o += rowBytes * height; }
  } else if (compression === 1) {
    const countBytes = version === 2 ? 4 : 2, counts = [];
    need(channels * height * countBytes);
    for (let i = 0; i < channels * height; i++) counts.push(countBytes === 4 ? v.getUint32(o + i * 4) : v.getUint16(o + i * 2));
    o += channels * height * countBytes;
    for (let c = 0; c < planes; c++) {
      const out = new Uint8Array(rowBytes * height);
      for (let y = 0; y < height; y++) {
        const n = counts[c * height + y];
        need(n);
        unpackBits(b, o, o + n, out, y * rowBytes, rowBytes);
        o += n;
      }
      plane[c] = out;
    }
  } else fail('psd-compression', String(compression));
  const rgba = new Uint8ClampedArray(width * height * 4);
  const at = depth === 8 ? (p, i) => p[i] : (p, i) => p[i * 2];      // 16 bits: the high byte
  for (let i = 0, n = width * height; i < n; i++) {
    let r, g, bl;
    if (mode === 'gray') r = g = bl = at(plane[0], i);
    else if (mode === 'rgb') { r = at(plane[0], i); g = at(plane[1], i); bl = at(plane[2], i); }
    else {                                              // CMYK as Photoshop stores it: 255 is no ink
      const k = at(plane[3], i) / 255;
      r = at(plane[0], i) * k; g = at(plane[1], i) * k; bl = at(plane[2], i) * k;
    }
    rgba[i * 4] = r; rgba[i * 4 + 1] = g; rgba[i * 4 + 2] = bl;
    rgba[i * 4 + 3] = planes > colour ? at(plane[colour], i) : 255;
  }
  return { width, height, rgba };
}

// PackBits: a count byte n, then n+1 bytes as they are (0…127) or one byte repeated 1−n times (−127…−1); −128 is nothing.
function unpackBits(src, from, to, out, at, length) {
  let i = from, j = at;
  const end = at + length;
  while (i < to && j < end) {
    const n = src[i++] << 24 >> 24;
    if (n >= 0) { for (let k = 0; k <= n && j < end; k++) out[j++] = src[i++]; }
    else if (n !== -128) { const x = src[i++]; for (let k = 0; k < 1 - n && j < end; k++) out[j++] = x; }
  }
}
