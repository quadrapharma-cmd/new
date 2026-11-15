// The files inside a 7z archive, read in the page or in Node with nothing fetched. Written from the 7z format's public description
// (7zFormat.txt, in the public-domain LZMA SDK): a signature header pointing to the archive's header at its end (often itself packed:
// an «encoded header»), streams of packed data, «folders» (the coders a stream goes through: LZMA, LZMA2, the x86 branch filter,
// delta, or kept as it is), and the files cut out of each folder's output in order, each checked against its CRC-32.
//   sevenz(bytes) → {files: [{name, bytes}], skipped: [{name, why}]}   (throws {why} for an archive it cannot open)
import { lzma, lzma2, bcjX86, delta } from './lzma.js';
import { crc32 } from '../workshop/zipw.js';

const fail = (why, text) => Object.assign(new Error(text), { why });
const SIGNATURE = [0x37, 0x7a, 0xbc, 0xaf, 0x27, 0x1c];
const ID = { end: 0, header: 1, archiveProps: 2, additional: 3, main: 4, files: 5, pack: 6, unpack: 7, substreams: 8, size: 9, crc: 10,
             folder: 11, unpackSize: 12, numUnpack: 13, emptyStream: 14, emptyFile: 15, anti: 16, name: 17, dummy: 25, encoded: 0x17 };

class Reader {
  constructor(b, at = 0, end = b.length) { this.b = b; this.at = at; this.end = end; }
  byte() { if (this.at >= this.end) throw fail('damaged', '7z: the header ends early'); return this.b[this.at++]; }
  number() {                                                       // the 7z number: its first byte's leading ones say how many follow
    const first = this.byte();
    let mask = 0x80, value = 0;
    for (let i = 0; i < 8; i++) {
      if ((first & mask) === 0) return value + (first & (mask - 1)) * 2 ** (8 * i);
      value += this.byte() * 2 ** (8 * i);
      mask >>>= 1;
    }
    return value;
  }
  u32() { const v = (this.b[this.at] | (this.b[this.at + 1] << 8) | (this.b[this.at + 2] << 16) | (this.b[this.at + 3] << 24)) >>> 0; this.at += 4; return v; }
  bits(n) { const out = []; let mask = 0, byte = 0; for (let i = 0; i < n; i++) { if (!mask) { byte = this.byte(); mask = 0x80; } out.push(!!(byte & mask)); mask >>>= 1; } return out; }
  defined(n) { const all = this.byte(); return all ? new Array(n).fill(true) : this.bits(n); }
  skip(n) { this.at += n; if (this.at > this.end) throw fail('damaged', '7z: the header ends early'); }
}

function digests(r, n) { const def = r.defined(n); return def.map(d => (d ? r.u32() : null)); }

function packInfo(r) {
  const info = { pos: r.number(), sizes: [], crcs: [] };
  const n = r.number();
  for (let id = r.byte(); id !== ID.end; id = r.byte()) {
    if (id === ID.size) for (let i = 0; i < n; i++) info.sizes.push(r.number());
    else if (id === ID.crc) info.crcs = digests(r, n);
    else throw fail('damaged', `7z: unexpected ${id} in the pack info`);
  }
  return info;
}

function folder(r) {
  const coders = [];
  let ins = 0, outs = 0;
  for (let i = 0, n = r.number(); i < n; i++) {
    const flags = r.byte();
    if (flags & 0x80) throw fail('unsupported', '7z: alternative coders');
    const id = [...r.b.subarray(r.at, r.at + (flags & 0x0f))].map(x => x.toString(16).padStart(2, '0')).join(''); r.skip(flags & 0x0f);
    const coder = { id, ins: 1, outs: 1, props: new Uint8Array(0) };
    if (flags & 0x10) { coder.ins = r.number(); coder.outs = r.number(); }
    if (flags & 0x20) { const size = r.number(); coder.props = r.b.subarray(r.at, r.at + size); r.skip(size); }
    coder.firstIn = ins; coder.firstOut = outs; ins += coder.ins; outs += coder.outs;
    coders.push(coder);
  }
  const bonds = [];
  for (let i = 0; i < outs - 1; i++) bonds.push({ in: r.number(), out: r.number() });
  const packedCount = ins - bonds.length, packed = [];
  if (packedCount === 1) { for (let i = 0; i < ins; i++) if (!bonds.some(b => b.in === i)) { packed.push(i); break; } }
  else for (let i = 0; i < packedCount; i++) packed.push(r.number());
  return { coders, bonds, packed, ins, outs, sizes: [] };
}

function unpackInfo(r) {
  if (r.byte() !== ID.folder) throw fail('damaged', '7z: no folders');
  const n = r.number();
  if (r.byte() !== 0) throw fail('unsupported', '7z: folders kept elsewhere');
  const folders = [];
  for (let i = 0; i < n; i++) folders.push(folder(r));
  if (r.byte() !== ID.unpackSize) throw fail('damaged', '7z: no unpacked sizes');
  for (const f of folders) for (let i = 0; i < f.outs; i++) f.sizes.push(r.number());
  for (let id = r.byte(); id !== ID.end; id = r.byte()) {
    if (id === ID.crc) digests(r, n).forEach((c, i) => { folders[i].crc = c; });
    else throw fail('damaged', `7z: unexpected ${id} in the unpack info`);
  }
  return folders;
}

function substreams(r, folders) {
  const counts = folders.map(() => 1);
  let id = r.byte();
  if (id === ID.numUnpack) { for (let i = 0; i < folders.length; i++) counts[i] = r.number(); id = r.byte(); }
  const sizes = [];
  const hasSizes = id === ID.size;
  folders.forEach((f, i) => {
    if (!counts[i]) return;
    const total = f.sizes[outOf(f)];
    let sum = 0;
    for (let k = 1; k < counts[i]; k++) { const s = hasSizes ? r.number() : 0; sizes.push(s); sum += s; }
    sizes.push(total - sum);
  });
  if (hasSizes) id = r.byte();
  // CRCs: for every stream whose folder has no CRC of its own as one stream
  let crcs = [];
  const unknown = folders.reduce((n, f, i) => n + (counts[i] === 1 && f.crc != null ? 0 : counts[i]), 0);
  if (id === ID.crc) {
    const list = digests(r, unknown);
    let k = 0;
    folders.forEach((f, i) => { for (let j = 0; j < counts[i]; j++) crcs.push(counts[i] === 1 && f.crc != null ? f.crc : list[k++]); });
    id = r.byte();
  } else folders.forEach((f, i) => { for (let j = 0; j < counts[i]; j++) crcs.push(counts[i] === 1 ? f.crc ?? null : null); });
  if (id !== ID.end) throw fail('damaged', `7z: unexpected ${id} in the substreams`);
  return { counts, sizes, crcs };
}

function streamsInfo(r) {
  const s = { pack: null, folders: [], sub: null };
  for (let id = r.byte(); id !== ID.end; id = r.byte()) {
    if (id === ID.pack) s.pack = packInfo(r);
    else if (id === ID.unpack) s.folders = unpackInfo(r);
    else if (id === ID.substreams) s.sub = substreams(r, s.folders);
    else throw fail('damaged', `7z: unexpected ${id} in the streams info`);
  }
  if (!s.sub) s.sub = { counts: s.folders.map(() => 1), sizes: s.folders.map(f => f.sizes[outOf(f)]), crcs: s.folders.map(f => f.crc ?? null) };
  return s;
}

const outOf = f => { for (let i = 0; i < f.outs; i++) if (!f.bonds.some(b => b.out === i)) return i; throw fail('damaged', '7z: a folder with no output'); };

// One folder's output: its coders run from the packed streams to the one output nobody else takes.
function decodeFolder(f, packedStreams) {
  const outputs = new Map();                                       // out index → bytes
  const inputOf = idx => {                                         // in index → bytes: a packed stream, or the output bound to it
    const p = f.packed.indexOf(idx);
    if (p >= 0) return packedStreams[p];
    const bond = f.bonds.find(b => b.in === idx);
    if (!bond) throw fail('damaged', '7z: a coder input with no source');
    return run(bond.out);
  };
  function run(outIdx) {
    if (outputs.has(outIdx)) return outputs.get(outIdx);
    const coder = f.coders.find(c => outIdx >= c.firstOut && outIdx < c.firstOut + c.outs);
    if (coder.ins !== 1 || coder.outs !== 1) throw fail('unsupported', `7z: the coder ${coder.id} (BCJ2 or another with more streams)`);
    const input = inputOf(coder.firstIn), size = f.sizes[outIdx];
    let out;
    if (coder.id === '00') out = input.slice(0, size);
    else if (coder.id === '21') out = lzma2(input, coder.props[0], size);
    else if (coder.id === '030101') out = lzma(input, coder.props, size);
    else if (coder.id === '03030103' || coder.id === '04') out = bcjX86(input.slice(0, size));
    else if (coder.id === '03') out = delta(input.slice(0, size), (coder.props[0] ?? 0) + 1);
    else if (coder.id === '06f10701') throw fail('password', '7z: encrypted');
    else throw fail('unsupported', `7z: the method ${coder.id} (PPMd, BZip2, Deflate or a filter for another processor)`);
    if (out.length !== size) throw fail('damaged', '7z: an output of the wrong size');
    outputs.set(outIdx, out);
    return out;
  }
  const out = run(outOf(f));
  if (f.crc != null && crc32(out) !== f.crc) throw fail('unreadable', '7z: a folder\'s CRC does not match');
  return out;
}

function packedStreams(bytes, s) {
  let at = 32 + s.pack.pos;
  const list = s.pack.sizes.map(n => { const b = bytes.subarray(at, at + n); at += n; return b; });
  if (at > bytes.length) throw fail('damaged', '7z: the archive is cut short');
  return list;
}
function folderPacked(s, list) {                                   // each folder's packed streams, in order
  let k = 0;
  return s.folders.map(f => { const mine = list.slice(k, k + f.packed.length); k += f.packed.length; return mine; });
}

function filesInfo(r) {
  const n = r.number(), files = Array.from({ length: n }, () => ({ name: '', empty: false, emptyFile: false, anti: false }));
  for (let id = r.byte(); id !== ID.end; id = r.byte()) {
    const size = r.number(), end = r.at + size;
    if (id === ID.emptyStream) r.bits(n).forEach((e, i) => { files[i].empty = e; });
    else if (id === ID.emptyFile || id === ID.anti) {
      const empties = files.filter(f => f.empty);
      r.bits(empties.length).forEach((e, i) => { if (id === ID.emptyFile) empties[i].emptyFile = e; else empties[i].anti = e; });
    } else if (id === ID.name) {
      if (r.byte() !== 0) throw fail('unsupported', '7z: names kept elsewhere');
      for (const f of files) {
        let s = '';
        for (;;) { const c = r.b[r.at] | (r.b[r.at + 1] << 8); r.at += 2; if (!c) break; s += String.fromCharCode(c); }
        f.name = s;
      }
    }
    r.at = end;
  }
  return files;
}

export function sevenz(bytes) {
  const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  if (b.length < 32 || SIGNATURE.some((x, i) => b[i] !== x)) throw fail('damaged', 'not a 7z archive');
  const start = new Reader(b, 12);
  const lo = start.u32(), hi = start.u32(), offset = lo + hi * 2 ** 32;
  const size = start.u32() + start.u32() * 2 ** 32, headCrc = start.u32();
  if (32 + offset + size > b.length) throw fail('volume', '7z: the archive is cut short (or one part of several)');
  if (!size) return { files: [], skipped: [] };
  let head = b.subarray(32 + offset, 32 + offset + size);
  if (crc32(head) !== headCrc) throw fail('damaged', '7z: the header\'s CRC does not match');
  let r = new Reader(head);
  let id = r.byte();
  while (id === ID.encoded) {                                      // the header itself packed (as 7-Zip does by default)
    const s = streamsInfo(r);
    const packs = folderPacked(s, packedStreams(b, s));
    head = decodeFolder(s.folders[0], packs[0]);
    r = new Reader(head); id = r.byte();
  }
  if (id !== ID.header) throw fail('damaged', '7z: no header');
  let main = null, files = [];
  for (id = r.byte(); id !== ID.end; id = r.byte()) {
    if (id === ID.archiveProps) { for (let p = r.byte(); p; p = r.byte()) r.skip(r.number()); }
    else if (id === ID.additional) streamsInfo(r);
    else if (id === ID.main) main = streamsInfo(r);
    else if (id === ID.files) files = filesInfo(r);
    else throw fail('damaged', `7z: unexpected ${id} in the header`);
  }
  const out = [], skipped = [];
  const withData = files.filter(f => !f.empty);
  if (!main) { for (const f of files.filter(x => x.empty && x.emptyFile)) out.push({ name: f.name, bytes: new Uint8Array(0) }); return { files: out, skipped }; }
  const packs = folderPacked(main, packedStreams(b, main));
  let k = 0;                                                       // the next file with data
  main.folders.forEach((f, fi) => {
    const count = main.sub.counts[fi], mine = withData.slice(k, k + count);
    k += count;
    let data;
    try { data = decodeFolder(f, packs[fi]); } catch (e) { for (const m of mine) skipped.push({ name: m.name, why: e.why || 'damaged' }); return; }
    let at = 0;
    for (let j = 0; j < mine.length; j++) {
      const index = withData.indexOf(mine[j]), n = main.sub.sizes[index], crc = main.sub.crcs[index];
      const piece = data.subarray(at, at + n); at += n;
      if (crc != null && crc32(piece) !== crc) skipped.push({ name: mine[j].name, why: 'unreadable' });
      else out.push({ name: mine[j].name.replace(/\\/g, '/'), bytes: piece });
    }
  });
  for (const f of files.filter(x => x.empty && x.emptyFile && !x.anti)) out.push({ name: f.name, bytes: new Uint8Array(0) });
  return { files: out, skipped };
}
