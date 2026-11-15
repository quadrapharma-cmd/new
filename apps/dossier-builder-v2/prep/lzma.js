// LZMA and LZMA2 decoding, for the 7z archives a dossier comes in (prep/sevenz.js). Written from the LZMA specification and the
// reference decoder Igor Pavlov placed in the public domain (LZMA SDK, «LzmaSpec»): a range decoder, bits each with an adaptive
// probability, literals coded against the byte a match would give, lengths and distances from small bit trees. The whole output is
// one array (its size is known from the archive), which is also the dictionary.
//   lzma(packed, props(5 bytes), size) → Uint8Array      lzma2(packed, propByte, size) → Uint8Array
const fail = (why, text) => Object.assign(new Error(text), { why });
const TOP = 1 << 24, BITS = 11, MOVE = 5, HALF = 1 << (BITS - 1);

class Range {
  constructor(src, at, end) {
    this.src = src; this.at = at; this.end = end;
    if (src[this.at++] !== 0) throw fail('damaged', 'LZMA: the range coder does not start with 0');
    this.range = 0xffffffff; this.code = 0;
    for (let i = 0; i < 4; i++) this.code = ((this.code << 8) | this.byte()) >>> 0;
    if (this.code === this.range) throw fail('damaged', 'LZMA: a bad start');
  }
  byte() { if (this.at >= this.end) throw fail('damaged', 'LZMA: the data ends early'); return this.src[this.at++]; }
  bit(p, i) {
    const bound = ((this.range >>> BITS) * p[i]) >>> 0;
    let b;
    if (this.code < bound) { p[i] += ((1 << BITS) - p[i]) >>> MOVE; this.range = bound; b = 0; }
    else { p[i] -= p[i] >>> MOVE; this.code = (this.code - bound) >>> 0; this.range = (this.range - bound) >>> 0; b = 1; }
    if (this.range < TOP) { this.range = (this.range << 8) >>> 0; this.code = ((this.code << 8) | this.byte()) >>> 0; }
    return b;
  }
  direct(n) {
    let res = 0;
    while (n--) {
      this.range = this.range >>> 1;
      let t = 0;
      if (this.code >= this.range) { this.code = (this.code - this.range) >>> 0; t = 1; }
      res = ((res << 1) | t) >>> 0;
      if (this.range < TOP) { this.range = (this.range << 8) >>> 0; this.code = ((this.code << 8) | this.byte()) >>> 0; }
    }
    return res;
  }
  tree(p, base, n) { let m = 1; for (let i = 0; i < n; i++) m = (m << 1) + this.bit(p, base + m); return m - (1 << n); }
  reverse(p, base, n) { let m = 1, s = 0; for (let i = 0; i < n; i++) { const b = this.bit(p, base + m); m = (m << 1) + b; s |= b << i; } return s; }
}

const probs = n => new Uint16Array(n).fill(HALF);
class Len {
  constructor() { this.choice = probs(2); this.low = probs(16 << 3); this.mid = probs(16 << 3); this.high = probs(256); }
  decode(rc, posState) {
    if (!rc.bit(this.choice, 0)) return rc.tree(this.low, posState << 3, 3);
    if (!rc.bit(this.choice, 1)) return 8 + rc.tree(this.mid, posState << 3, 3);
    return 16 + rc.tree(this.high, 0, 8);
  }
}

// One LZMA decoder over an output array it writes from `out.pos` on: its properties (lc, lp, pb), its state and probabilities.
// LZMA2 keeps it across its chunks, resetting the state, the properties or the dictionary when a chunk says so.
export class Decoder {
  constructor(out) { this.out = out; this.pos = 0; this.start = 0; }
  props(lc, lp, pb) {
    if (lc > 8 || lp > 4 || pb > 4) throw fail('damaged', 'LZMA: bad properties');
    this.lc = lc; this.lp = lp; this.pb = pb;
    this.lit = probs(0x300 << (lc + lp));
    this.reset();
  }
  reset() {
    this.lit.fill(HALF);
    this.isMatch = probs(12 << 4); this.isRep = probs(12); this.isRepG0 = probs(12); this.isRepG1 = probs(12); this.isRepG2 = probs(12);
    this.isRep0Long = probs(12 << 4); this.slot = probs(4 << 6); this.posProbs = probs(115); this.align = probs(16);
    this.len = new Len(); this.repLen = new Len();
    this.state = 0; this.rep0 = this.rep1 = this.rep2 = this.rep3 = 0;
  }
  // `size` bytes from the range coder rc (end marker allowed when `marker`)
  run(rc, size, { marker = false } = {}) {
    const out = this.out, end = this.pos + size, pbMask = (1 << this.pb) - 1, lpMask = (1 << this.lp) - 1;
    while (this.pos < end || marker) {
      const done = this.pos - this.start, posState = done & pbMask;        // counted from the dictionary's start
      let state = this.state;
      if (!rc.bit(this.isMatch, (state << 4) + posState)) {
        if (this.pos >= end) throw fail('damaged', 'LZMA: more data than its size');
        const prev = this.pos > this.start ? out[this.pos - 1] : 0;
        const base = 0x300 * (((done & lpMask) << this.lc) + (prev >>> (8 - this.lc)));
        let sym = 1;
        if (state >= 7) {
          let match = out[this.pos - this.rep0 - 1];
          do {
            const mb = (match >>> 7) & 1; match <<= 1;
            const b = rc.bit(this.lit, base + ((1 + mb) << 8) + sym);
            sym = (sym << 1) | b;
            if (mb !== b) break;
          } while (sym < 0x100);
        }
        while (sym < 0x100) sym = (sym << 1) | rc.bit(this.lit, base + sym);
        out[this.pos++] = sym - 0x100;
        this.state = state < 4 ? 0 : state < 10 ? state - 3 : state - 6;
        continue;
      }
      let len;
      if (rc.bit(this.isRep, state)) {
        if (this.pos >= end || this.pos === this.start) throw fail('damaged', 'LZMA: a repeat with nothing before it');
        if (!rc.bit(this.isRepG0, state)) {
          if (!rc.bit(this.isRep0Long, (state << 4) + posState)) {     // one byte again, from the last distance
            this.state = state < 7 ? 9 : 11;
            out[this.pos] = out[this.pos - this.rep0 - 1]; this.pos++;
            continue;
          }
        } else {
          let dist;
          if (!rc.bit(this.isRepG1, state)) dist = this.rep1;
          else {
            if (!rc.bit(this.isRepG2, state)) dist = this.rep2;
            else { dist = this.rep3; this.rep3 = this.rep2; }
            this.rep2 = this.rep1;
          }
          this.rep1 = this.rep0; this.rep0 = dist;
        }
        len = this.repLen.decode(rc, posState);
        this.state = state < 7 ? 8 : 11;
      } else {
        this.rep3 = this.rep2; this.rep2 = this.rep1; this.rep1 = this.rep0;
        len = this.len.decode(rc, posState);
        this.state = state < 7 ? 7 : 10;
        const dist = this.distance(rc, len);
        if (dist === 0xffffffff) {                                   // the end marker
          if (marker || this.pos === end) return;
          throw fail('damaged', 'LZMA: an end marker before the end');
        }
        this.rep0 = dist;
        if (this.pos >= end) throw fail('damaged', 'LZMA: more data than its size');
        if (dist >= this.pos - this.start) throw fail('damaged', 'LZMA: a distance before the start');
      }
      len += 2;
      if (this.pos + len > end) throw fail('damaged', 'LZMA: a match past the end');
      const from = this.pos - this.rep0 - 1;
      for (let i = 0; i < len; i++) out[this.pos + i] = out[from + i];
      this.pos += len;
    }
  }
  distance(rc, len) {
    const slot = rc.tree(this.slot, (len > 3 ? 3 : len) << 6, 6);
    if (slot < 4) return slot;
    const direct = (slot >>> 1) - 1;
    let dist = ((2 | (slot & 1)) << direct) >>> 0;
    if (slot < 14) dist = (dist + rc.reverse(this.posProbs, dist - slot, direct)) >>> 0;
    else dist = (dist + (rc.direct(direct - 4) << 4 >>> 0) + rc.reverse(this.align, 0, 4)) >>> 0;
    return dist;
  }
}

const checkSize = size => { if (!(size >= 0) || size > 1.5e9) throw fail('memory', `7z: a file of ${size} bytes`); };

export function lzma(src, props, size) {
  checkSize(size);
  const out = new Uint8Array(size), d = new Decoder(out);
  let p = props[0];
  if (p >= 9 * 5 * 5) throw fail('damaged', 'LZMA: bad properties');
  const lc = p % 9; p = (p / 9) | 0;
  d.props(lc, p % 5, (p / 5) | 0);
  if (size) d.run(new Range(src, 0, src.length), size);
  return out;
}

export function lzma2(src, propByte, size) {
  checkSize(size);
  if (propByte > 40) throw fail('damaged', 'LZMA2: bad dictionary size');
  const out = new Uint8Array(size), d = new Decoder(out);
  let at = 0, ready = false;
  for (;;) {
    if (at >= src.length) throw fail('damaged', 'LZMA2: the data ends early');
    const c = src[at++];
    if (c === 0) break;
    if (c === 1 || c === 2) {                                        // a chunk kept as it is (1: the dictionary starts again)
      const n = ((src[at] << 8) | src[at + 1]) + 1; at += 2;
      if (c === 1) d.start = d.pos;
      if (d.pos + n > size || at + n > src.length) throw fail('damaged', 'LZMA2: a chunk past the end');
      out.set(src.subarray(at, at + n), d.pos); d.pos += n; at += n;
      continue;
    }
    if (c < 0x80) throw fail('damaged', `LZMA2: a bad chunk (${c})`);
    const unpacked = ((c & 0x1f) << 16) + (src[at] << 8) + src[at + 1] + 1;
    const packed = (src[at + 2] << 8) + src[at + 3] + 1;
    at += 4;
    const reset = (c >>> 5) & 3;
    if (reset === 3) d.start = d.pos;
    if (reset >= 2) {
      let p = src[at++];
      const lc = p % 9; p = (p / 9) | 0;
      if (lc + (p % 5) > 4) throw fail('damaged', 'LZMA2: bad properties');
      d.props(lc, p % 5, (p / 5) | 0); ready = true;
    } else if (reset === 1) { if (!ready) throw fail('damaged', 'LZMA2: no properties'); d.reset(); }
    else if (!ready) throw fail('damaged', 'LZMA2: no properties');
    if (d.pos + unpacked > size || at + packed > src.length) throw fail('damaged', 'LZMA2: a chunk past the end');
    d.run(new Range(src, at, at + packed), unpacked);
    at += packed;
  }
  if (d.pos !== size) throw fail('damaged', 'LZMA2: shorter than its size');
  return out;
}

// The x86 branch filter (BCJ): call and jump addresses written relative again. The filter of the LZMA SDK, decoding.
export function bcjX86(data) {
  const size = data.length;
  if (size < 5) return data;
  const test = b => ((b + 1) & 0xfe) === 0;
  let pos = 0, mask = 0;
  const limit = size - 4, ip = 5;
  for (;;) {
    let p = pos;
    while (p < limit && (data[p] & 0xfe) !== 0xe8) p++;
    const d = p - pos;
    pos = p;
    if (p >= limit) break;
    if (d > 2) mask = 0;
    else {
      mask >>>= d;
      if (mask !== 0 && (mask > 4 || mask === 3 || test(data[p + (mask >>> 1) + 1]))) { mask = (mask >>> 1) | 4; pos++; continue; }
    }
    if (test(data[p + 4])) {
      let v = ((data[p + 4] << 24) | (data[p + 3] << 16) | (data[p + 2] << 8) | data[p + 1]) >>> 0;
      const cur = (ip + pos) >>> 0;
      pos += 5;
      v = (v - cur) >>> 0;
      if (mask !== 0) {
        const sh = (mask & 6) << 2;
        if (test((v >>> sh) & 0xff)) { v = (v ^ (((0x100 << sh) >>> 0) - 1)) >>> 0; v = (v - cur) >>> 0; }
        mask = 0;
      }
      data[p + 1] = v & 0xff; data[p + 2] = (v >>> 8) & 0xff; data[p + 3] = (v >>> 16) & 0xff; data[p + 4] = (0 - ((v >>> 24) & 1)) & 0xff;
    } else { mask = (mask >>> 1) | 4; pos++; }
  }
  return data;
}

// The delta filter: each byte stored as its difference from the byte `dist` before it.
export function delta(data, dist) {
  for (let i = dist; i < data.length; i++) data[i] = (data[i] + data[i - dist]) & 0xff;
  return data;
}
