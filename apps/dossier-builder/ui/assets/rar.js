/* RAR archives opened inside the page — the program's own reader, no library and nothing fetched.
   It reads the two formats in use: RAR 1.5–4.x archives (the «RAR» of WinRAR 3 and 4, compression version 29: LZ with Huffman tables
   and the standard filters) and RAR5 (WinRAR 5 and later: LZ with four filters), stored files, solid archives, archives split in
   parts and names in any language. Every file is checked against the CRC-32 the archive keeps for it: a file that does not match is
   reported as unreadable, never handed over. It also reads the text method that «Best» compression used in old archives (PPMd
   variant H; the model follows Dmitry Shkarin's public-domain design as written out in 7-Zip's Ppmd7). Not read: files under a
   password and archives older than RAR 2.9 — each is reported with its reason.
   The work is done in a worker made from this same source, so the page keeps answering; where a worker cannot be made it runs on
   the page's own thread. The reader was written from the published format notes and the behaviour of the free unpackers; it holds
   no compression code. */
function DBRAR_MAIN(root) {
  'use strict';
  function core() {
    const E = (code, why) => { const e = new Error(code + (why ? ' ' + why : '')); e.rar = code; e.why = why || ''; return e; };
    const bad = () => E('damaged');

    /* ---------------- CRC-32 */
    const CRC = new Uint32Array(256);
    for (let i = 0; i < 256; i++) { let c = i; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; CRC[i] = c; }
    function crc32(crc, d, a, b) { for (let i = a; i < b; i++) crc = CRC[(crc ^ d[i]) & 0xff] ^ (crc >>> 8); return crc; }

    /* ---------------- bits, most significant first; reading past the end gives zeros */
    function Bits(buf) { this.b = buf; this.p = 0; this.i = 0; }
    Bits.prototype.peek = function () { const b = this.b, p = this.p; return (((b[p] << 16) | (b[p + 1] << 8) | b[p + 2]) >>> (8 - this.i)) & 0xffff; };
    Bits.prototype.add = function (n) { n += this.i; this.p += n >>> 3; this.i = n & 7; };
    Bits.prototype.get = function (n) { const v = this.peek() >>> (16 - n); this.add(n); return v; };            // n ≤ 16
    Bits.prototype.peek32 = function () { const b = this.b, p = this.p, i = this.i;
      return ((((b[p] << 24) | (b[p + 1] << 16) | (b[p + 2] << 8) | b[p + 3]) << i) | (b[p + 4] >>> (8 - i))) >>> 0; };

    /* ---------------- Huffman tables (canonical, lengths up to 15) with a quick table for the short codes */
    const QB = 10;
    function huff(lens, off, n) {
      const cnt = new Int32Array(16), dl = new Int32Array(16), dp = new Int32Array(16), num = new Uint16Array(n);
      for (let i = 0; i < n; i++) cnt[lens[off + i] & 15]++;
      cnt[0] = 0;
      let up = 0;
      for (let i = 1; i < 16; i++) { up += cnt[i]; dl[i] = up << (16 - i); up *= 2; dp[i] = dp[i - 1] + cnt[i - 1]; }
      const cp = dp.slice();
      for (let i = 0; i < n; i++) { const l = lens[off + i] & 15; if (l) num[cp[l]++] = i; }
      const ql = new Uint8Array(1 << QB), qn = new Uint16Array(1 << QB);
      for (let c = 0; c < (1 << QB); c++) {
        const bf = c << (16 - QB); let bits = 1; while (bits <= QB && bf >= dl[bits]) bits++;
        if (bits <= QB) { let pos = dp[bits] + ((bf - dl[bits - 1]) >>> (16 - bits)); if (pos >= n) pos = 0; ql[c] = bits; qn[c] = num[pos]; }
      }
      return { dl, dp, num, n, ql, qn };
    }
    function dec(inp, t) {
      const bf = inp.peek() & 0xfffe, c = bf >>> (16 - QB), q = t.ql[c];
      if (q) { inp.add(q); return t.qn[c]; }
      let bits = 15; for (let i = QB + 1; i < 15; i++) if (bf < t.dl[i]) { bits = i; break; }
      inp.add(bits);
      let pos = t.dp[bits] + ((bf - t.dl[bits - 1]) >>> (16 - bits));
      if (pos >= t.n) pos = 0;
      return t.num[pos];
    }
    /* the 20 lengths of the table that packs the other tables: the same in both formats */
    function preTable(inp) {
      const bl = new Uint8Array(20);
      for (let i = 0; i < 20; i++) {
        const l = inp.get(4);
        if (l === 15) { let z = inp.get(4); if (z === 0) bl[i] = 15; else { z += 2; while (z-- > 0 && i < 20) bl[i++] = 0; i--; } } else bl[i] = l;
      }
      return huff(bl, 0, 20);
    }

    /* ---------------- the window: positions only grow (pos & mask is the place in the window), so a file's offset is a subtraction */
    function newLz(size) { return { win: new Uint8Array(size), size, mask: size - 1, pos: 0, old: [0, 0, 0, 0], lastLen: 0, lastDist: 0, t: null, have: false,
      oldTable: new Uint8Array(404), f30: [], oldLen: [], lastFilter: 0, lowDist: 0, lowRep: 0, block: 'lz', ppm: null, ppmEsc: 2 }; }
    function copy(win, mask, pos, dist, len) {
      const s = pos - dist, d = pos & mask, si = s & mask;
      if (dist >= len && len > 12 && si + len <= win.length && d + len <= win.length) win.copyWithin(d, si, si + len);
      else for (let k = 0; k < len; k++) win[(pos + k) & mask] = win[(s + k) & mask];
      return pos + len;
    }

    let USED = {};                                                     // the filters that ran, by kind
    /* ---------------- what a file gives: the window's bytes in order, filters applied to their blocks, cut at the file's size */
    function Out(lz, unp, sink) {
      this.lz = lz; this.start = lz.pos; this.flushed = lz.pos; this.end = unp === null ? Infinity : lz.pos + unp;
      this.filters = []; this.sink = sink; this.step = Math.max(4096, Math.min(lz.size >> 1, 1 << 20)); this.next = lz.pos + this.step;
    }
    Out.prototype.raw = function (a, b) {                              // window bytes [a, b) as a new array
      const lz = this.lz, n = b - a, o = new Uint8Array(n), i = a & lz.mask, first = Math.min(n, lz.size - i);
      o.set(lz.win.subarray(i, i + first)); if (first < n) o.set(lz.win.subarray(0, n - first), first);
      return o;
    };
    Out.prototype.put = function (bytes, at) {                         // never past the file's size
      if (at >= this.end) return;
      this.sink(at + bytes.length > this.end ? bytes.subarray(0, this.end - at) : bytes);
    };
    Out.prototype.flush = function (last) {
      const lz = this.lz, pos = lz.pos;
      if (pos - this.flushed > lz.size) throw bad();                    // the window was overrun before its bytes were taken
      this.filters.sort((x, y) => x.start - y.start);
      while (this.flushed < pos) {
        const f = this.filters[0];
        if (f && f.start < this.flushed) { this.filters.shift(); continue; }
        if (!f || f.start >= pos) { this.put(this.raw(this.flushed, pos), this.flushed); this.flushed = pos; break; }
        if (f.start > this.flushed) { this.put(this.raw(this.flushed, f.start), this.flushed); this.flushed = f.start; }
        if (f.start + f.len > pos) { if (!last) break; this.put(this.raw(this.flushed, pos), this.flushed); this.flushed = pos; break; }      // the block is not whole yet
        let block = this.raw(f.start, f.start + f.len);
        this.filters.shift(); block = f.run(block, f.start - this.start); USED[f.kind] = (USED[f.kind] || 0) + 1;
        while (this.filters.length && this.filters[0].start === f.start && this.filters[0].len === block.length) { const g = this.filters.shift(); block = g.run(block, f.start - this.start); USED[g.kind] = (USED[g.kind] || 0) + 1; }
        this.put(block, f.start); this.flushed = f.start + f.len;
      }
      const f = this.filters[0];
      this.next = Math.min(pos + this.step, f && f.start + f.len > pos ? Math.max(f.start + f.len, pos + 1) : Infinity);
      if (lz.pos - this.flushed > lz.size - 0x2000) throw bad();        // a filter block the window cannot hold
      if (lz.pos - this.start > this.end - this.start + lz.size) throw bad();    // far more than the file's size: not a real stream
    };

    /* ---------------- filters. x86 calls (E8, E8/E9), ARM calls, delta; the old format's are found by the checksum of their program */
    function fE8(d, off, e9, wrap) {
      const n = d.length, fileSize = 0x1000000;
      for (let cur = 0; cur + 4 < n;) {
        const c = d[cur++];
        if (c === 0xe8 || (e9 && c === 0xe9)) {
          const offset = wrap ? (cur + off) % fileSize : (cur + off) >>> 0;
          const addr = (d[cur] | (d[cur + 1] << 8) | (d[cur + 2] << 16) | (d[cur + 3] << 24)) >>> 0;
          let v = -1;
          if (addr & 0x80000000) { if (((addr + offset) & 0x80000000) === 0) v = (addr + fileSize) >>> 0; }
          else if ((addr - fileSize) & 0x80000000) v = (addr - offset) >>> 0;
          if (v >= 0) { d[cur] = v & 255; d[cur + 1] = (v >>> 8) & 255; d[cur + 2] = (v >>> 16) & 255; d[cur + 3] = v >>> 24; }
          cur += 4;
        }
      }
      return d;
    }
    function fArm(d, off) {
      for (let cur = 0; cur + 3 < d.length; cur += 4) if (d[cur + 3] === 0xeb) {
        let o = d[cur] + d[cur + 1] * 0x100 + d[cur + 2] * 0x10000; o = (o - ((off + cur) >>> 2)) >>> 0;
        d[cur] = o & 255; d[cur + 1] = (o >>> 8) & 255; d[cur + 2] = (o >>> 16) & 255;
      }
      return d;
    }
    function fDelta(d, channels) {
      const n = d.length, o = new Uint8Array(n); let src = 0;
      for (let ch = 0; ch < channels; ch++) { let prev = 0; for (let p = ch; p < n; p += channels) o[p] = prev = (prev - d[src++]) & 255; }
      return o;
    }
    function fRgb(d, width, posR) {
      const n = d.length, o = new Uint8Array(n); let src = 0;
      if (n < 3 || width > n || posR > 2) return d;
      for (let ch = 0; ch < 3; ch++) {
        let prev = 0;
        for (let i = ch; i < n; i += 3) {
          let pred;
          if (i >= width + 3) { const up = o[i - width], ul = o[i - width - 3]; pred = prev + up - ul;
            const pa = Math.abs(pred - prev), pb = Math.abs(pred - up), pc = Math.abs(pred - ul);
            pred = pa <= pb && pa <= pc ? prev : pb <= pc ? up : ul; }
          else pred = prev;
          o[i] = prev = (pred - d[src++]) & 255;
        }
      }
      for (let i = posR, border = n - 2; i < border; i += 3) { const g = o[i + 1]; o[i] = (o[i] + g) & 255; o[i + 2] = (o[i + 2] + g) & 255; }
      return o;
    }
    function fAudio(d, channels) {
      const n = d.length, o = new Uint8Array(n); let src = 0;
      for (let ch = 0; ch < channels; ch++) {
        let prev = 0, prevDelta = 0, d1 = 0, d2 = 0, d3 = 0, k1 = 0, k2 = 0, k3 = 0; const dif = [0, 0, 0, 0, 0, 0, 0];
        for (let i = ch, count = 0; i < n; i += channels, count++) {
          d3 = d2; d2 = prevDelta - d1; d1 = prevDelta;
          let pred = ((8 * prev + k1 * d1 + k2 * d2 + k3 * d3) >>> 3) & 0xff;
          const cur = d[src++];
          pred = (pred - cur) & 0xff; o[i] = pred;
          prevDelta = ((pred - prev) << 24) >> 24; prev = pred;
          const D = ((cur << 24) >> 24) << 3;
          dif[0] += Math.abs(D); dif[1] += Math.abs(D - d1); dif[2] += Math.abs(D + d1); dif[3] += Math.abs(D - d2); dif[4] += Math.abs(D + d2); dif[5] += Math.abs(D - d3); dif[6] += Math.abs(D + d3);
          if ((count & 0x1f) === 0) {
            let min = dif[0], which = 0; dif[0] = 0;
            for (let j = 1; j < 7; j++) { if (dif[j] < min) { min = dif[j]; which = j; } dif[j] = 0; }
            if (which === 1) { if (k1 >= -16) k1--; } else if (which === 2) { if (k1 < 16) k1++; } else if (which === 3) { if (k2 >= -16) k2--; }
            else if (which === 4) { if (k2 < 16) k2++; } else if (which === 5) { if (k3 >= -16) k3--; } else if (which === 6) { if (k3 < 16) k3++; }
          }
        }
      }
      return o;
    }
    function fItanium(d, off) {
      const masks = [4, 4, 6, 6, 0, 0, 7, 7, 4, 4, 0, 0, 4, 4, 0, 0], n = d.length;
      const getBits = (base, pos, count) => { const b = base + (pos >>> 3), v = (d[b] | (d[b + 1] << 8) | (d[b + 2] << 16) | (d[b + 3] << 24)) >>> 0; return (v >>> (pos & 7)) & (0xffffffff >>> (32 - count)); };
      const setBits = (base, value, mask, pos) => { const b = base + (pos >>> 3), sh = pos & 7; let m = ~(mask << sh) >>> 0, v = (value << sh) >>> 0;
        for (let i = 0; i < 4; i++) { d[b + i] = (d[b + i] & (m & 255)) | (v & 255); m = (m >>> 8) | 0xff000000; v >>>= 8; } };
      let fo = off >>> 4;
      for (let cur = 0; n >= 21 && cur < n - 21; cur += 16, fo++) {
        const t = (d[cur] & 0x1f) - 0x10;
        if (t >= 0) { const cm = masks[t];
          if (cm) for (let i = 0; i <= 2; i++) if (cm & (1 << i)) { const sp = i * 41 + 5;
            if (getBits(cur, sp + 37, 4) === 5) { const o = getBits(cur, sp + 13, 20); setBits(cur, (o - fo) & 0xfffff, 0xfffff, sp + 13); } } }
      }
      return d;
    }
    const STD30 = [[53, 0xad576887, 'e8'], [57, 0x3cd7e57e, 'e8e9'], [120, 0x3769893f, 'itanium'], [29, 0x0e06077d, 'delta'], [149, 0x1c2c5dc8, 'rgb'], [216, 0xbc85e701, 'audio']];
    function program30(code) {                                         // which of the standard filters this program is
      let x = 0; for (let i = 1; i < code.length; i++) x ^= code[i];
      if (x !== code[0]) return 'none';
      const c = (crc32(0xffffffff, code, 0, code.length) ^ 0xffffffff) >>> 0;
      for (const [len, sum, type] of STD30) if (len === code.length && sum === c) return type;
      return 'none';
    }
    function run30(type, R) {
      return (d, off) => {
        const n = d.length;
        if (type === 'e8' || type === 'e8e9') return n < 4 || n > 0x40000 ? d : fE8(d, off, type === 'e8e9', false);
        if (type === 'itanium') return n < 21 || n > 0x40000 ? d : fItanium(d, off);
        if (n > 0x20000) return d;
        if (type === 'delta') return R[0] > 1024 || R[0] === 0 ? d : fDelta(d, R[0]);
        if (type === 'rgb') return fRgb(d, (R[0] - 3) >>> 0, R[1]);
        if (type === 'audio') return R[0] > 128 || R[0] === 0 ? d : fAudio(d, R[0]);
        return d;
      };
    }
    function vmData(v) {
      const d = v.peek();
      switch (d & 0xc000) {
        case 0: v.add(6); return (d >> 10) & 0xf;
        case 0x4000: if ((d & 0x3c00) === 0) { v.add(14); return (0xffffff00 | ((d >> 2) & 0xff)) >>> 0; } v.add(10); return (d >> 6) & 0xff;
        case 0x8000: { v.add(2); const x = v.peek(); v.add(16); return x; }
        default: { v.add(2); const hi = v.peek(); v.add(16); const lo = v.peek(); v.add(16); return ((hi << 16) | lo) >>> 0; }
      }
    }

    /* ---------------- RAR5 */
    function tables5(inp, lz) {
      const bd = preTable(inp), tab = new Uint8Array(430);
      for (let i = 0; i < 430;) {
        const n = dec(inp, bd);
        if (n < 16) tab[i++] = n;
        else if (n < 18) { let c = n === 16 ? inp.get(3) + 3 : inp.get(7) + 11; if (i === 0) throw bad(); while (c-- > 0 && i < 430) { tab[i] = tab[i - 1]; i++; } }
        else { let c = n === 18 ? inp.get(3) + 3 : inp.get(7) + 11; while (c-- > 0 && i < 430) tab[i++] = 0; }
      }
      lz.t = { ld: huff(tab, 0, 306), dd: huff(tab, 306, 64), ldd: huff(tab, 370, 16), rd: huff(tab, 386, 44) }; lz.have = true;
    }
    function unpack5(lz, data, unp, sink) {
      const inp = new Bits(data), win = lz.win, mask = lz.mask, old = lz.old, out = new Out(lz, unp, sink), n = data.length;
      let blockEnd = -1, blockBits = 0, last = false, pos = lz.pos;
      const header = () => {
        inp.add((8 - inp.i) & 7);
        const flags = inp.get(8), nb = ((flags >> 3) & 3) + 1; if (nb === 4) throw bad();
        const sum = inp.get(8); let size = 0; for (let i = 0; i < nb; i++) size += inp.get(8) << (i * 8);
        if (((0x5a ^ flags ^ size ^ (size >> 8) ^ (size >> 16)) & 0xff) !== sum) throw bad();
        blockEnd = inp.p + size - 1; blockBits = (flags & 7) + 1; last = !!(flags & 0x40);
        if (flags & 0x80) tables5(inp, lz);
      };
      const length = slot => { if (slot < 8) return 2 + slot; const lb = (slot >> 2) - 1; return 2 + ((4 | (slot & 3)) << lb) + inp.get(lb); };
      const fdata = () => { const c = inp.get(2) + 1; let v = 0; for (let i = 0; i < c; i++) v += inp.get(8) * Math.pow(2, 8 * i); return v; };
      header(); if (!lz.have) throw bad();
      let T = lz.t;
      for (;;) {
        if (inp.p >= blockEnd) {
          let done = false;
          while (inp.p > blockEnd || (inp.p === blockEnd && inp.i >= blockBits)) { if (last) { done = true; break; } if (inp.p > n) throw bad(); header(); T = lz.t; }
          if (done) break;
        }
        if (pos >= out.next) { lz.pos = pos; out.flush(false); }
        const s = dec(inp, T.ld);
        if (s < 256) { win[pos++ & mask] = s; continue; }
        if (s >= 262) {
          let len = length(s - 262), dist = 1; const slot = dec(inp, T.dd);
          if (slot < 4) dist += slot;
          else {
            const db = (slot >> 1) - 1; dist += (2 | (slot & 1)) * Math.pow(2, db);
            if (db >= 4) { if (db > 4) { dist += (inp.peek32() >>> (36 - db)) * 16; inp.add(db - 4); } dist += dec(inp, T.ldd); }
            else dist += inp.get(db);
          }
          if (dist > 0x100) { len++; if (dist > 0x2000) { len++; if (dist > 0x40000) len++; } }
          old[3] = old[2]; old[2] = old[1]; old[1] = old[0]; old[0] = dist; lz.lastLen = len;
          pos = copy(win, mask, pos, dist, len); continue;
        }
        if (s === 256) {
          const start = fdata(); let flen = fdata(); if (flen > 0x400000) flen = 0;
          const type = inp.get(3), ch = type === 0 ? inp.get(5) + 1 : 0;
          const run = type === 0 ? d => fDelta(d, ch) : type === 1 ? (d, off) => fE8(d, off, false, true) : type === 2 ? (d, off) => fE8(d, off, true, true) : type === 3 ? fArm : d => d;
          if (out.filters.length > 8192) throw bad();
          out.filters.push({ start: pos + start, len: flen, run, kind: ['delta', 'e8', 'e8e9', 'arm'][type] || 'none' }); out.next = Math.min(out.next, pos + start + flen);
          continue;
        }
        if (s === 257) { if (lz.lastLen) pos = copy(win, mask, pos, old[0], lz.lastLen); continue; }
        const k = s - 258, dist = old[k]; for (let i = k; i > 0; i--) old[i] = old[i - 1]; old[0] = dist;
        const len = length(dec(inp, T.rd)); lz.lastLen = len;
        pos = copy(win, mask, pos, dist, len);
      }
      lz.pos = pos; out.flush(true);
      return pos - out.start;
    }


    /* ---------------- PPMd variant H: the text method of old archives. One byte heap holds the model: contexts (12 bytes: number of
       symbols, sum of frequencies, their list, the shorter context) and symbol records (6 bytes: symbol, frequency, what follows). */
    function Ppmd() {
      const N = 38, UNIT = 12, MAXF = 124, SCALE = 1 << 14;
      const INIT_ESC = [0x3CDD, 0x1F3F, 0x59BF, 0x48F3, 0x64A1, 0x5ABC, 0x6632, 0x6051], EXP_ESC = [25, 14, 9, 7, 5, 5, 4, 4, 4, 3, 3, 3, 2, 2, 2, 2];
      const i2u = new Uint8Array(N), u2i = new Uint8Array(128), ns2i = new Uint8Array(256), ns2bs = new Uint8Array(256), hb2 = new Uint8Array(256);
      for (let i = 0, k = 0; i < N; i++) { let step = i >= 12 ? 4 : (i >> 2) + 1; do { u2i[k++] = i; } while (--step); i2u[i] = k; }
      ns2bs[1] = 2; ns2bs.fill(4, 2, 11); ns2bs.fill(6, 11);
      for (let i = 0; i < 3; i++) ns2i[i] = i;
      for (let i = 3, m = 3, k = 1; i < 256; i++) { ns2i[i] = m; if (--k === 0) k = (++m) - 2; }
      hb2.fill(8, 0x40);
      const free = new Uint32Array(N), seeSumm = new Uint16Array(401), seeShift = new Uint8Array(401), seeCount = new Uint8Array(401), bin = new Uint16Array(128 * 64), mask = new Uint8Array(256);
      let H = null, size = 0, align = 0, minC = 0, maxC = 0, found = 0, orderFall = 0, initEsc = 0, prevSuccess = 0, maxOrder = 0, hiBits = 0, runLength = 0, initRL = 0,
        glue = 0, lo = 0, hi = 0, text = 0, unitsStart = 0, range = 0, code = 0, low = 0, src = null;
      const g16 = o => H[o] | (H[o + 1] << 8), s16 = (o, v) => { H[o] = v & 255; H[o + 1] = (v >>> 8) & 255; };
      const g32 = o => (H[o] | (H[o + 1] << 8) | (H[o + 2] << 16) | (H[o + 3] << 24)) >>> 0;
      const s32 = (o, v) => { H[o] = v & 255; H[o + 1] = (v >>> 8) & 255; H[o + 2] = (v >>> 16) & 255; H[o + 3] = v >>> 24; };
      const swap = (a, b) => { for (let i = 0; i < 6; i++) { const t = H[a + i]; H[a + i] = H[b + i]; H[b + i] = t; } };
      const find = (c, sym) => { let st = g32(c + 4); for (let n = g16(c); n > 0; n--, st += 6) if (H[st] === sym) return st; throw bad(); };

      const insertNode = (node, indx) => { s32(node, free[indx]); free[indx] = node; };
      const removeNode = indx => { const node = free[indx]; free[indx] = g32(node); return node; };
      function splitBlock(ptr, oldIndx, newIndx) {
        const nu = i2u[oldIndx] - i2u[newIndx]; ptr += i2u[newIndx] * UNIT; let i = u2i[nu - 1];
        if (i2u[i] !== nu) { const k = i2u[--i]; insertNode(ptr + k * UNIT, nu - k - 1); }
        insertNode(ptr, i);
      }
      function glueFreeBlocks() {
        const head = align + size; let n = head;
        glue = 255;
        for (let i = 0; i < N; i++) {                                  // the free blocks in one list, each knowing its size
          const nu = i2u[i]; let next = free[i]; free[i] = 0;
          while (next !== 0) { const node = next; s32(node + 4, n); s32(n + 8, next); n = next; next = g32(node); s16(node, 0); s16(node + 2, nu); }
        }
        s16(head, 1); s32(head + 4, n); s32(n + 8, head);
        if (lo !== hi) s16(lo, 1);
        while (n !== head) {                                           // neighbours are joined
          const node = n; let nu = g16(node + 2);
          for (;;) {
            const node2 = node + nu * UNIT; nu += g16(node2 + 2);
            if (g16(node2) !== 0 || nu >= 0x10000) break;
            s32(g32(node2 + 8) + 4, g32(node2 + 4)); s32(g32(node2 + 4) + 8, g32(node2 + 8)); s16(node + 2, nu);
          }
          n = g32(node + 4);
        }
        for (n = g32(head + 4); n !== head;) {                          // and filed again by size
          let node = n; const next = g32(node + 4); let nu = g16(node + 2);
          for (; nu > 128; nu -= 128, node += 128 * UNIT) insertNode(node, N - 1);
          let i = u2i[nu - 1];
          if (i2u[i] !== nu) { const k = i2u[--i]; insertNode(node + k * UNIT, nu - k - 1); }
          insertNode(node, i); n = next;
        }
      }
      function allocUnitsRare(indx) {
        if (glue === 0) { glueFreeBlocks(); if (free[indx] !== 0) return removeNode(indx); }
        let i = indx;
        do { if (++i === N) { const nb = i2u[indx] * UNIT; glue--; return unitsStart - text > nb ? (unitsStart -= nb) : 0; } } while (free[i] === 0);
        const r = removeNode(i); splitBlock(r, i, indx); return r;
      }
      function allocUnits(indx) {
        if (free[indx] !== 0) return removeNode(indx);
        const nb = i2u[indx] * UNIT;
        if (nb <= hi - lo) { const r = lo; lo += nb; return r; }
        return allocUnitsRare(indx);
      }
      function shrinkUnits(oldPtr, oldNU, newNU) {
        const i0 = u2i[oldNU - 1], i1 = u2i[newNU - 1];
        if (i0 === i1) return oldPtr;
        if (free[i1] !== 0) { const ptr = removeNode(i1); H.copyWithin(ptr, oldPtr, oldPtr + newNU * UNIT); insertNode(oldPtr, i0); return ptr; }
        splitBlock(oldPtr, i0, i1); return oldPtr;
      }
      function restart() {
        free.fill(0); text = align; hi = text + size; lo = unitsStart = hi - Math.floor(Math.floor(size / 8) / UNIT) * 7 * UNIT; glue = 0;
        orderFall = maxOrder; runLength = initRL = -(maxOrder < 12 ? maxOrder : 12) - 1; prevSuccess = 0;
        hi -= UNIT; minC = maxC = hi; s32(minC + 8, 0); s16(minC, 256); s16(minC + 2, 257);
        found = lo; lo += 128 * UNIT; s32(minC + 4, found);
        for (let i = 0; i < 256; i++) { const st = found + i * 6; H[st] = i; H[st + 1] = 1; s32(st + 2, 0); }
        for (let i = 0; i < 128; i++) for (let k = 0; k < 8; k++) { const val = SCALE - Math.floor(INIT_ESC[k] / (i + 2)); for (let m = 0; m < 64; m += 8) bin[i * 64 + k + m] = val; }
        for (let i = 0; i < 25; i++) for (let k = 0; k < 16; k++) { const x = i * 16 + k; seeShift[x] = 3; seeSumm[x] = (5 * i + 10) << 3; seeCount[x] = 4; }
      }
      function createSuccessors(skip) {
        let c = minC; const upBranch = g32(found + 2), fsym = H[found], ps = [];
        if (!skip) ps.push(found);
        while (g32(c + 8)) {
          c = g32(c + 8);
          const st = g16(c) !== 1 ? find(c, fsym) : c + 2, successor = g32(st + 2);
          if (successor !== upBranch) { c = successor; if (ps.length === 0) return c; break; }
          ps.push(st);
        }
        const upSym = H[upBranch]; let upFreq;
        if (g16(c) === 1) upFreq = H[c + 3];
        else { const st = find(c, upSym), cf = H[st + 1] - 1, s0 = g16(c + 2) - g16(c) - cf;
          upFreq = (1 + (2 * cf <= s0 ? (5 * cf > s0 ? 1 : 0) : Math.floor((2 * cf + 3 * s0 - 1) / (2 * s0)))) & 255; }
        while (ps.length) {
          let c1;
          if (hi !== lo) c1 = (hi -= UNIT); else if (free[0] !== 0) c1 = removeNode(0); else { c1 = allocUnitsRare(0); if (!c1) return 0; }
          s16(c1, 1); H[c1 + 2] = upSym; H[c1 + 3] = upFreq; s32(c1 + 4, upBranch + 1); s32(c1 + 8, c);
          s32(ps.pop() + 2, c1); c = c1;
        }
        return c;
      }
      function updateModel() {
        let fSuccessor = g32(found + 2), successor, c; const fsym = H[found];
        if (H[found + 1] < 31 && g32(minC + 8) !== 0) {
          c = g32(minC + 8);
          if (g16(c) === 1) { if (H[c + 3] < 32) H[c + 3]++; }
          else {
            let st = g32(c + 4);
            if (H[st] !== fsym) { st = find(c, fsym); if (H[st + 1] >= H[st - 5]) { swap(st, st - 6); st -= 6; } }
            if (H[st + 1] < MAXF - 9) { H[st + 1] += 2; s16(c + 2, g16(c + 2) + 2); }
          }
        }
        if (orderFall === 0) { minC = maxC = createSuccessors(true); if (minC === 0) { restart(); return; } s32(found + 2, minC); return; }
        H[text++] = fsym; successor = text;
        if (text >= unitsStart) { restart(); return; }
        if (fSuccessor) {
          if (fSuccessor <= successor) { const cs = createSuccessors(false); if (cs === 0) { restart(); return; } fSuccessor = cs; }
          if (--orderFall === 0) { successor = fSuccessor; if (maxC !== minC) text--; }
        } else { s32(found + 2, successor); fSuccessor = minC; }
        const ns = g16(minC), s0 = g16(minC + 2) - ns - (H[found + 1] - 1);
        for (c = maxC; c !== minC; c = g32(c + 8)) {
          const ns1 = g16(c); let cf;
          if (ns1 !== 1) {
            if ((ns1 & 1) === 0) {                                     // one more unit for the list of symbols
              const oldNU = ns1 >> 1, i = u2i[oldNU - 1];
              if (i !== u2i[oldNU]) { const ptr = allocUnits(i + 1); if (!ptr) { restart(); return; }
                const oldPtr = g32(c + 4); H.copyWithin(ptr, oldPtr, oldPtr + oldNU * UNIT); insertNode(oldPtr, i); s32(c + 4, ptr); }
            }
            const sm = g16(c + 2); s16(c + 2, sm + (2 * ns1 < ns ? 1 : 0) + 2 * ((4 * ns1 <= ns ? 1 : 0) & (sm <= 8 * ns1 ? 1 : 0)));
          } else {
            const st = allocUnits(0); if (!st) { restart(); return; }
            H.copyWithin(st, c + 2, c + 8); s32(c + 4, st);
            if (H[st + 1] < 30) H[st + 1] <<= 1; else H[st + 1] = MAXF - 4;
            s16(c + 2, H[st + 1] + initEsc + (ns > 3 ? 1 : 0));
          }
          cf = 2 * H[found + 1] * (g16(c + 2) + 6); const sf = s0 + g16(c + 2);
          if (cf < 6 * sf) { cf = 1 + (cf > sf ? 1 : 0) + (cf >= 4 * sf ? 1 : 0); s16(c + 2, g16(c + 2) + 3); }
          else { cf = 4 + (cf >= 9 * sf ? 1 : 0) + (cf >= 12 * sf ? 1 : 0) + (cf >= 15 * sf ? 1 : 0); s16(c + 2, g16(c + 2) + cf); }
          const st = g32(c + 4) + ns1 * 6; s32(st + 2, successor); H[st] = fsym; H[st + 1] = cf; s16(c, ns1 + 1);
        }
        maxC = minC = fSuccessor;
      }
      function rescale() {
        const stats = g32(minC + 4); let st = found;
        { const t = H.slice(st, st + 6); for (; st !== stats; st -= 6) H.copyWithin(st, st - 6, st); H.set(t, st); }
        let escFreq = g16(minC + 2) - H[st + 1];
        H[st + 1] += 4; const adder = orderFall !== 0 ? 1 : 0; H[st + 1] = (H[st + 1] + adder) >> 1; let sumFreq = H[st + 1], i = g16(minC) - 1;
        do {
          st += 6; escFreq -= H[st + 1]; H[st + 1] = (H[st + 1] + adder) >> 1; sumFreq += H[st + 1];
          if (H[st + 1] > H[st - 5]) { let s1 = st; const t = H.slice(s1, s1 + 6); do { H.copyWithin(s1, s1 - 6, s1); s1 -= 6; } while (s1 !== stats && t[1] > H[s1 - 5]); H.set(t, s1); }
        } while (--i);
        if (H[st + 1] === 0) {
          const numStats = g16(minC);
          do { i++; st -= 6; } while (H[st + 1] === 0);
          escFreq += i; s16(minC, numStats - i);
          if (g16(minC) === 1) {
            const sym = H[stats], succ = g32(stats + 2); let freq = H[stats + 1];
            do { freq -= freq >> 1; escFreq >>= 1; } while (escFreq > 1);
            insertNode(stats, u2i[((numStats + 1) >> 1) - 1]);
            found = minC + 2; H[found] = sym; H[found + 1] = freq; s32(found + 2, succ);
            return;
          }
          const n0 = (numStats + 1) >> 1, n1 = (g16(minC) + 1) >> 1;
          if (n0 !== n1) s32(minC + 4, shrinkUnits(stats, n0, n1));
        }
        s16(minC + 2, sumFreq + escFreq - (escFreq >> 1)); found = g32(minC + 4);
      }
      const nextContext = () => { const c = g32(found + 2); if (orderFall === 0 && c > text) minC = maxC = c; else updateModel(); };
      /* the range decoder of RAR: bytes come from the unpacker's input */
      const byte = () => src.b[src.p++] | 0;
      const threshold = total => { range = Math.floor(range / total); if (range === 0) throw bad(); return Math.floor(((code - low) >>> 0) / range); };
      const rdecode = (start, n) => {
        low = (low + start * range) >>> 0; range = (range * n) >>> 0;
        for (let turns = 0; ; turns++) {
          if (((low ^ (low + range)) >>> 0) >= 0x1000000) { if (range >= 0x8000) break; range = ((-low) >>> 0) & 0x7fff; }
          if (turns > 8) throw bad();                                  // damaged data: the coder cannot settle
          code = ((code << 8) | byte()) >>> 0; range = (range << 8) >>> 0; low = (low << 8) >>> 0;
        }
      };
      function symbol() {                                              // the next byte, or -1 where the data cannot be right
        if (g16(minC) !== 1) {
          let st = g32(minC + 4), hiCnt = H[st + 1], i; const summ = g16(minC + 2), count = threshold(summ);
          if (count < hiCnt) {
            rdecode(0, hiCnt); found = st; const sym = H[st];
            prevSuccess = 2 * H[st + 1] > g16(minC + 2) ? 1 : 0; runLength += prevSuccess; s16(minC + 2, g16(minC + 2) + 4);
            if ((H[st + 1] += 4) > MAXF) rescale();
            nextContext(); return sym;
          }
          prevSuccess = 0; i = g16(minC) - 1;
          do {
            st += 6;
            if ((hiCnt += H[st + 1]) > count) {
              rdecode(hiCnt - H[st + 1], H[st + 1]); found = st; const sym = H[st];
              H[st + 1] += 4; s16(minC + 2, g16(minC + 2) + 4);
              if (H[st + 1] > H[st - 5]) { swap(st, st - 6); found = st -= 6; if (H[st + 1] > MAXF) rescale(); }
              nextContext(); return sym;
            }
          } while (--i);
          if (count >= summ) return -1;
          hiBits = hb2[H[found]];
          rdecode(hiCnt, summ - hiCnt);
          mask.fill(255); mask[H[st]] = 0; i = g16(minC) - 1;
          do { st -= 6; mask[H[st]] = 0; } while (--i);
        } else {
          const one = minC + 2; hiBits = hb2[H[found]];
          const idx = (H[one + 1] - 1) * 64 + prevSuccess + ns2bs[g16(g32(minC + 8)) - 1] + hiBits + 2 * hb2[H[one]] + ((runLength >> 26) & 0x20);
          const prob = bin[idx];
          if (threshold(SCALE) < prob) {
            rdecode(0, prob); bin[idx] = prob + 128 - ((prob + 32) >> 7); found = one; const sym = H[one];
            if (H[one + 1] < 128) H[one + 1]++;
            prevSuccess = 1; runLength++; nextContext(); return sym;
          }
          rdecode(prob, SCALE - prob);
          const np = prob - ((prob + 32) >> 7); bin[idx] = np; initEsc = EXP_ESC[np >> 10];
          mask.fill(255); mask[H[one]] = 0; prevSuccess = 0;
        }
        for (;;) {
          const numMasked = g16(minC), ps = [];
          do { orderFall++; const suf = g32(minC + 8); if (!suf) return -1; minC = suf; } while (g16(minC) === numMasked);
          let hiCnt = 0, st = g32(minC + 4), i = 0; const numStats = g16(minC), num = numStats - numMasked;
          for (let left = numStats; i !== num; st += 6) { if (left-- === 0) return -1; if (mask[H[st]]) { hiCnt += H[st + 1]; ps[i++] = st; } }
          let see, esc;
          if (numStats !== 256) {
            see = ns2i[num - 1] * 16 + (num < ((g16(g32(minC + 8)) - numStats) >>> 0) ? 1 : 0) + 2 * (g16(minC + 2) < 11 * numStats ? 1 : 0) + 4 * (numMasked > num ? 1 : 0) + hiBits;
            const r = seeSumm[see] >> seeShift[see]; seeSumm[see] -= r; esc = r + (r === 0 ? 1 : 0);
          } else { see = 400; esc = 1; }
          const freqSum = esc + hiCnt, count = threshold(freqSum);
          if (count < hiCnt) {
            let k = 0; for (hiCnt = 0; (hiCnt += H[ps[k] + 1]) <= count; k++);
            st = ps[k]; rdecode(hiCnt - H[st + 1], H[st + 1]);
            if (seeShift[see] < 7 && --seeCount[see] === 0) { seeSumm[see] <<= 1; seeCount[see] = 3 << seeShift[see]++; }
            found = st; const sym = H[st];
            s16(minC + 2, g16(minC + 2) + 4); if ((H[st + 1] += 4) > MAXF) rescale();
            runLength = initRL; updateModel(); return sym;
          }
          if (count >= freqSum) return -1;
          rdecode(hiCnt, freqSum - hiCnt); seeSumm[see] += freqSum;
          do { mask[H[ps[--i]]] = 0; } while (i !== 0);
        }
      }
      return {
        ready: () => !!H,
        /* a PPMd block begins: its flags byte, the memory and the escape byte where given, then the coder's first four bytes */
        start(inp, lz) {
          src = inp; const flags = byte(), reset = flags & 0x20; let mb = 0;
          if (reset) mb = byte(); else if (!H) throw bad();
          if (flags & 0x40) lz.ppmEsc = byte();
          low = 0; range = 0xffffffff; code = 0; for (let i = 0; i < 4; i++) code = ((code << 8) | byte()) >>> 0;
          if (reset) {
            let order = (flags & 0x1f) + 1; if (order > 16) order = 16 + (order - 16) * 3;
            if (order === 1) { H = null; throw bad(); }
            const want = (mb + 1) * 1048576;
            if (want > 268435456) throw E('unsupported', 'memory');
            if (!H || size !== want) { size = want; align = 4 - (size & 3); H = new Uint8Array(align + size + UNIT); }
            maxOrder = order; restart(); seeShift[400] = 7; seeSumm[400] = 0; seeCount[400] = 64;
          }
        },
        input(inp) { src = inp; },
        symbol,
      };
    }

    /* ---------------- RAR 2.9 – 4.x (compression version 29) */
    const LDEC = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224];
    const LBIT = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5];
    const SDDEC = [0, 4, 8, 16, 32, 64, 128, 192], SDBIT = [2, 2, 3, 4, 5, 6, 6, 6];
    const DDEC = new Int32Array(60), DBIT = new Uint8Array(60);
    (() => { const counts = [4, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 14, 0, 12]; let dist = 0, slot = 0;
      for (let b = 0; b < counts.length; b++) for (let j = 0; j < counts[b]; j++, slot++, dist += (1 << b)) { DDEC[slot] = dist; DBIT[slot] = b; } })();
    function tables30(inp, lz) {
      inp.add((8 - inp.i) & 7);
      const field = inp.peek();
      if (field & 0x8000) { lz.ppm = lz.ppm || Ppmd(); lz.ppm.start(inp, lz); lz.block = 'ppm'; return; }       // a block packed with the text method
      lz.block = 'lz'; lz.lowDist = 0; lz.lowRep = 0;
      if (!(field & 0x4000)) lz.oldTable.fill(0);
      inp.add(2);
      const bd = preTable(inp), tab = new Uint8Array(404), oldT = lz.oldTable;
      for (let i = 0; i < 404;) {
        const n = dec(inp, bd);
        if (n < 16) { tab[i] = (n + oldT[i]) & 15; i++; }
        else if (n < 18) { let c = n === 16 ? inp.get(3) + 3 : inp.get(7) + 11; if (i === 0) throw bad(); while (c-- > 0 && i < 404) { tab[i] = tab[i - 1]; i++; } }
        else { let c = n === 18 ? inp.get(3) + 3 : inp.get(7) + 11; while (c-- > 0 && i < 404) tab[i++] = 0; }
      }
      lz.t = { ld: huff(tab, 0, 299), dd: huff(tab, 299, 60), ldd: huff(tab, 359, 17), rd: huff(tab, 376, 28) }; lz.have = true;
      oldT.set(tab);
    }
    function unpack29(lz, data, unp, sink, solid) {
      const inp = new Bits(data), win = lz.win, mask = lz.mask, old = lz.old, out = new Out(lz, unp, sink), n = data.length;
      let pos = lz.pos;
      if (!solid) { lz.have = false; lz.oldTable.fill(0); lz.f30 = []; lz.oldLen = []; lz.lastFilter = 0; lz.block = 'lz'; lz.ppmEsc = 2; }
      if (lz.ppm) lz.ppm.input(inp);
      if (!solid || !lz.have) tables30(inp, lz);
      let T = lz.t;
      const pp = () => { const c = lz.ppm.symbol(); if (c < 0) throw bad(); return c; };
      const vm = (first, next) => {                                    // a filter for a block that follows; its program comes byte by byte
        let size = (first & 7) + 1; if (size === 7) size = next() + 7; else if (size === 8) { size = next() * 256; size += next(); }
        if (size === 0) throw bad();
        const code = new Uint8Array(size); for (let i = 0; i < size; i++) code[i] = next();
        const v = new Bits(code); let fp;
        if (first & 0x80) { fp = vmData(v); if (fp === 0) { lz.f30 = []; lz.oldLen = []; lz.lastFilter = 0; out.filters.length = 0; } else fp--; } else fp = lz.lastFilter;
        if (fp > lz.f30.length || fp > lz.oldLen.length) throw bad();
        lz.lastFilter = fp;
        const fresh = fp === lz.f30.length; let prg;
        if (fresh) { if (fp > 8192) throw bad(); prg = { type: 'none' }; lz.f30.push(prg); lz.oldLen.push(0); } else prg = lz.f30[fp];
        let start = vmData(v); if (first & 0x40) start += 258;
        let len; if (first & 0x20) { len = vmData(v); lz.oldLen[fp] = len; } else len = lz.oldLen[fp] || 0;
        const R = [0, 0, 0, 0, len, 0, 0];
        if (first & 0x10) { const m = v.get(7); for (let i = 0; i < 7; i++) if (m & (1 << i)) R[i] = vmData(v); }
        if (fresh) { const cs = vmData(v); if (cs >= 0x10000 || cs === 0 || v.p + cs > size) throw bad();
          const c = new Uint8Array(cs); for (let i = 0; i < cs; i++) c[i] = v.get(8); prg.type = program30(c); }
        if (out.filters.length > 8192) throw bad();
        out.filters.push({ start: pos + start, len, run: run30(prg.type, R), kind: prg.type }); out.next = Math.min(out.next, pos + start + len);
      };
      for (;;) {
        if (inp.p > n) break;                                           // the data ended
        if (pos >= out.next) { lz.pos = pos; out.flush(false); }
        if (lz.block === 'ppm') {
          const ch = lz.ppm.symbol(); if (ch < 0) throw bad();
          if (ch === lz.ppmEsc) {                                       // the escape byte: what follows is an order, not text
            const nx = pp();
            if (nx === 0) { tables30(inp, lz); T = lz.t; continue; }    // the text method ends here: new tables
            if (nx === 2) break;                                        // the file ends
            if (nx === 3) { lz.pos = pos; vm(pp(), pp); continue; }
            if (nx === 4) { let dist = 0; for (let i = 0; i < 3; i++) dist = dist * 256 + pp(); pos = copy(win, mask, pos, dist + 2, pp() + 32); continue; }
            if (nx === 5) { pos = copy(win, mask, pos, 1, pp() + 4); continue; }
          }
          win[pos++ & mask] = ch; continue;
        }
        let s = dec(inp, T.ld);
        if (s < 256) { win[pos++ & mask] = s; continue; }
        if (s >= 271) {
          s -= 271; let len = LDEC[s] + 3, bits = LBIT[s]; if (bits) len += inp.get(bits);
          const slot = dec(inp, T.dd); let dist = DDEC[slot] + 1; bits = DBIT[slot];
          if (bits) {
            if (slot > 9) {
              if (bits > 4) { dist += (inp.peek() >>> (20 - bits)) << 4; inp.add(bits - 4); }
              if (lz.lowRep > 0) { lz.lowRep--; dist += lz.lowDist; }
              else { const low = dec(inp, T.ldd); if (low === 16) { lz.lowRep = 15; dist += lz.lowDist; } else { dist += low; lz.lowDist = low; } }
            } else dist += inp.get(bits);
          }
          if (dist >= 0x2000) { len++; if (dist >= 0x40000) len++; }
          old[3] = old[2]; old[2] = old[1]; old[1] = old[0]; old[0] = dist; lz.lastLen = len; lz.lastDist = dist;
          pos = copy(win, mask, pos, dist, len); continue;
        }
        if (s === 256) {                                                // the end of a block: «1» new tables here; «00» / «01» the file ends
          const f = inp.peek();
          if (f & 0x8000) { inp.add(1); lz.have = false; tables30(inp, lz); T = lz.t; continue; }
          inp.add(2); lz.have = !(f & 0x4000); break;
        }
        if (s === 257) { lz.pos = pos; vm(inp.get(8), () => inp.get(8)); continue; }
        if (s === 258) { if (lz.lastLen) pos = copy(win, mask, pos, lz.lastDist, lz.lastLen); continue; }
        if (s < 263) {
          const k = s - 259, dist = old[k]; for (let i = k; i > 0; i--) old[i] = old[i - 1]; old[0] = dist;
          const ls = dec(inp, T.rd); let len = LDEC[ls] + 2; const bits = LBIT[ls]; if (bits) len += inp.get(bits);
          lz.lastLen = len; lz.lastDist = dist;
          pos = copy(win, mask, pos, dist, len); continue;
        }
        s -= 263; let dist = SDDEC[s] + 1; const bits = SDBIT[s]; if (bits) dist += inp.get(bits);
        old[3] = old[2]; old[2] = old[1]; old[1] = old[0]; old[0] = dist; lz.lastLen = 2; lz.lastDist = dist;
        pos = copy(win, mask, pos, dist, 2);
      }
      lz.pos = pos; out.flush(true);
      return pos - out.start;
    }

    /* ---------------- the archive: its headers, in both formats */
    const u16 = (d, p) => d[p] | (d[p + 1] << 8), u32 = (d, p) => (d[p] | (d[p + 1] << 8) | (d[p + 2] << 16) | (d[p + 3] << 24)) >>> 0;
    const utf8 = new TextDecoder('utf-8'), strict = new TextDecoder('utf-8', { fatal: true });
    function vint(d, p) { let v = 0, m = 1; for (let i = 0; i < 10; i++) { const b = d[p++]; if (b === undefined) throw bad(); v += (b & 0x7f) * m; m *= 128; if (!(b & 0x80)) return [v, p]; } throw bad(); }
    function name4(bytes, unicode) {                                   // the old format: a DOS name, and beside it the name in Unicode, packed
      let zero = bytes.indexOf(0);
      if (unicode && zero >= 0 && zero < bytes.length - 1) {
        const a = bytes.subarray(0, zero), e = bytes.subarray(zero + 1); let out = '', ep = 0, flags = 0, fb = 0; const high = e[ep++];
        const count = () => out.length;
        while (ep < e.length) {
          if (fb === 0) { flags = e[ep++]; fb = 8; }
          switch (flags >> 6) {
            case 0: out += String.fromCharCode(e[ep++]); break;
            case 1: out += String.fromCharCode(e[ep++] + (high << 8)); break;
            case 2: out += String.fromCharCode(e[ep] + (e[ep + 1] << 8)); ep += 2; break;
            default: { let len = e[ep++];
              if (len & 0x80) { const corr = e[ep++]; for (len = (len & 0x7f) + 2; len > 0; len--) out += String.fromCharCode(((a[count()] + corr) & 0xff) + (high << 8)); }
              else for (len += 2; len > 0; len--) out += String.fromCharCode(a[count()] || 0); }
          }
          flags = (flags << 2) & 0xff; fb -= 2;
        }
        return out;
      }
      const raw = zero >= 0 ? bytes.subarray(0, zero) : bytes;
      try { return strict.decode(raw); } catch (e) {}
      for (const cp of ['windows-1256', 'windows-1252']) { try { return new TextDecoder(cp).decode(raw); } catch (e) {} }
      return String.fromCharCode.apply(null, raw);
    }
    function parse4(vol, vi, list, st) {
      let p = 7; const n = vol.length;
      while (p + 7 <= n) {
        const type = vol[p + 2], flags = u16(vol, p + 3), hsize = u16(vol, p + 5);
        if (hsize < 7) break;
        let add = 0;
        if (type === 0x73) { if (flags & 0x80) throw E('password'); st.volume = !!(flags & 1); }
        else if (type === 0x74 || type === 0x7a) {
          let pack = u32(vol, p + 7), unp = u32(vol, p + 11), q = p + 32; const crc = u32(vol, p + 16), ver = vol[p + 24], method = vol[p + 25], ns = u16(vol, p + 26);
          const link = vol[p + 15] === 3 && (u32(vol, p + 28) & 0xf000) === 0xa000;      // packed on Unix: a symbolic link
          if (flags & 0x100) { pack += u32(vol, q) * 4294967296; unp += u32(vol, q + 4) * 4294967296; q += 8; }
          add = pack;
          if (type === 0x74) {
            const part = { vi, off: p + hsize, len: Math.max(0, Math.min(pack, n - p - hsize)) }, prev = list[list.length - 1];
            if ((flags & 1) && prev && prev.more) { prev.parts.push(part); prev.more = !!(flags & 2); prev.crc = crc; }
            else if (!(flags & 1)) list.push({ name: name4(vol.subarray(q, q + ns), !!(flags & 0x200)).replace(/\\/g, '/'), dir: (flags & 0xe0) === 0xe0, unp, crc, ver: 4,
              solid: !!(flags & 0x10), enc: !!(flags & 4), link, stored: method === 0x30, ok: method === 0x30 || ver === 29 || ver === 36, dict: 0x10000 << ((flags & 0xe0) >> 5), parts: [part], more: !!(flags & 2) });
          }
        }
        else if (type === 0x7b) break;
        else if (flags & 0x8000) add = u32(vol, p + 7);
        p += hsize + add;
      }
    }
    function parse5(vol, vi, list, st) {
      let p = 8; const n = vol.length;
      while (p + 7 <= n) {
        let q = p + 4, hsize, type, flags, extra = 0, dsize = 0;
        [hsize, q] = vint(vol, q); const hend = q + hsize; if (!hsize || hend > n) break;
        [type, q] = vint(vol, q); [flags, q] = vint(vol, q);
        if (flags & 1) [extra, q] = vint(vol, q);
        if (flags & 2) [dsize, q] = vint(vol, q);
        if (type === 4) throw E('password');
        if (type === 5) break;
        if (type === 2) {
          let ff, unp, attr, crc = null, comp, host, nl;
          [ff, q] = vint(vol, q); [unp, q] = vint(vol, q); [attr, q] = vint(vol, q);
          if (ff & 2) q += 4;
          if (ff & 4) { crc = u32(vol, q); q += 4; }
          [comp, q] = vint(vol, q); [host, q] = vint(vol, q); [nl, q] = vint(vol, q);
          const name = utf8.decode(vol.subarray(q, q + nl)); let enc = false, link = false, copyOf = null;
          for (let e = hend - extra; extra && e < hend;) { let sz, ty, r; [sz, e] = vint(vol, e); const next = e + sz; [ty, r] = vint(vol, e);
            if (ty === 1) enc = true;
            else if (ty === 5) { let kind, fl, tl; [kind, r] = vint(vol, r); [fl, r] = vint(vol, r); [tl, r] = vint(vol, r); link = true; if (kind === 4 || kind === 5) copyOf = utf8.decode(vol.subarray(r, r + tl)); }
            e = next; }
          const part = { vi, off: hend, len: Math.max(0, Math.min(dsize, n - hend)) }, prev = list[list.length - 1], method = (comp >> 7) & 7;
          if ((flags & 8) && prev && prev.more) { prev.parts.push(part); prev.more = !!(flags & 0x10); prev.crc = crc; }
          else if (!(flags & 8)) list.push({ name, dir: !!(ff & 1), unp: ff & 8 ? null : unp, crc, ver: 5, solid: !!(comp & 0x40), enc, link, copyOf, stored: method === 0,
            ok: (comp & 0x3f) === 0, dict: 0x20000 * Math.pow(2, (comp >> 10) & 15), parts: [part], more: !!(flags & 0x10) });
        }
        p = hend + dsize;
      }
    }
    function join(vols, parts) {
      if (parts.length === 1) return vols[parts[0].vi].subarray(parts[0].off, parts[0].off + parts[0].len);
      const o = new Uint8Array(parts.reduce((a, x) => a + x.len, 0)); let at = 0;
      for (const x of parts) { o.set(vols[x.vi].subarray(x.off, x.off + x.len), at); at += x.len; }
      return o;
    }

    /* vols: the parts of one archive in order (Uint8Array). opts: {maxFiles, maxTotal, maxFile, skip(name) → true to leave a file out}.
       onFile(name, parts) is called for each file as it is ready; → {skipped: [{name, why}], count} */
    function extract(vols, opts, onFile, onStatus) {
      opts = opts || {};
      const sig = v => { const lim = Math.min(v.length - 7, 1048576);            // the signature: at the start, or after a self-extracting program
        for (let i = 0; i <= lim; i++) if (v[i] === 0x52 && v[i + 1] === 0x61 && v[i + 2] === 0x72 && v[i + 3] === 0x21 && v[i + 4] === 0x1a && v[i + 5] === 0x07 && (v[i + 6] === 0 || (v[i + 6] === 1 && v[i + 7] === 0))) return i;
        return -1; };
      vols = vols.map((v, i) => { const at = sig(v); if (at < 0) throw E('damaged'); return at ? v.subarray(at) : v; });
      const head = String.fromCharCode.apply(null, vols[0].subarray(0, 8)), list = [], st = {};
      const v5 = head === 'Rar!\x1a\x07\x01\x00';
      vols.forEach((v, i) => { if (i && String.fromCharCode.apply(null, v.subarray(0, 7)) !== head.slice(0, 7)) throw E('damaged'); (v5 ? parse5 : parse4)(v, i, list, st); });
      const skipped = [], maxFiles = opts.maxFiles || Infinity, maxTotal = opts.maxTotal || Infinity, maxFile = opts.maxFile || Infinity;       // no limit unless one is asked for
      let lz = null, broken = null, total = 0, decoded = 0, count = 0; const kept = new Set();
      const packed = vols.reduce((a, v) => a + v.length, 0), ratio = opts.maxRatio || 250;       // a packed stream that expands hundreds of times past 100 MB is a «bomb»
      USED = {};
      for (const e of list) {
        const name = e.name.replace(/^[A-Za-z]:/, '').split('/').filter(x => x && x !== '.' && x !== '..').join('/') || 'file';
        if (e.dir) continue;
        const left = !!(opts.skip && opts.skip(name)), large = e.unp !== null && e.unp > maxFile;
        if (!e.solid && !e.copyOf) broken = null;                       // a file that does not lean on the ones before starts afresh
        if (e.copyOf) {                                                 // the same content as a file that came before
          const of = e.copyOf.split('/').filter(x => x && x !== '.' && x !== '..').join('/');
          if (kept.has(of) && !left && count < maxFiles) { count++; kept.add(name); onFile(name, null, of); } else if (!left) skipped.push({ name, why: 'link' });
          continue;
        }
        let why = e.more ? 'volume' : e.enc ? 'password' : e.link ? 'link' : !e.ok ? 'unsupported' : e.solid && broken ? broken : null;
        if (!why && !e.stored && e.dict > 2147483648) why = 'memory';     // a 4 GB dictionary: more than a page can hold
        if (why) { if (!left) skipped.push({ name, why }); if (!e.stored) broken = why; continue; }
        if ((left || large) && (e.stored || !list.some(x => x !== e && x.solid && list.indexOf(x) > list.indexOf(e)))) {     // nothing after it leans on it: no need to unpack it
          if (large && !left) skipped.push({ name, why: 'too large' });
          if (!e.stored) broken = 'unreadable';
          continue;
        }
        if (!left && !large && count >= maxFiles) throw E('big', 'files');
        if (onStatus && !left) onStatus(name);
        const data = join(vols, e.parts), parts = []; let size = 0, crc = 0xffffffff;
        const keep = !left && !large;
        const sink = b => { size += b.length; decoded += b.length; crc = crc32(crc, b, 0, b.length);
          if (decoded > 104857600 && decoded > ratio * packed) throw E('big', 'bomb');          // stopped at once, kept or not: nothing more is unpacked
          if (keep) { total += b.length; if (total > maxTotal) throw E('big', 'total'); parts.push(b); } };
        try {
          if (e.stored) sink(e.unp === null ? data.slice() : data.slice(0, e.unp));
          else {
            const need = e.solid || list.some(x => x.solid) ? e.dict : Math.min(e.dict, Math.max(0x40000, Math.pow(2, Math.ceil(Math.log2(Math.max(1, e.unp === null ? e.dict : e.unp))))));
            if (!e.solid || !lz || lz.ver !== e.ver || lz.size < need) { const keepWin = lz && e.solid && lz.ver === e.ver ? lz : null;
              try { lz = newLz(Math.max(need, keepWin ? keepWin.size : 0)); } catch (x) { lz = null; throw E('memory'); }          // the window itself does not fit in memory
              lz.ver = e.ver; }
            (e.ver === 5 ? unpack5 : unpack29)(lz, data, e.unp, sink, e.solid);
          }
        } catch (err) {
          if (err && err.rar === 'big') throw err;                                                   // the whole archive is refused
          if (err && !err.rar && /alloc|out of memory/i.test(String(err))) err = E('memory');        // the browser refused the memory for it
          if (!err || !err.rar) throw err;
          broken = err.rar === 'unsupported' ? 'unsupported' : err.rar === 'memory' ? 'memory' : 'unreadable'; lz = null;
          if (!left) skipped.push({ name, why: broken }); continue;
        }
        if ((e.unp !== null && size !== e.unp) || (e.crc !== null && ((crc ^ 0xffffffff) >>> 0) !== e.crc)) { broken = 'unreadable'; if (!left) skipped.push({ name, why: 'unreadable' }); continue; }
        if (keep) { count++; kept.add(name); onFile(name, parts, null); } else if (large && !left) skipped.push({ name, why: 'too large' });
      }
      if (st.missing) skipped.push({ name: '…', why: 'volume' });
      return { skipped, count, filters: USED, format: v5 ? 'RAR5' : 'RAR4' };
    }
    return { extract };
  }

  const api = core();
  /* what is left packed: system files, and names with an extension that is not among the ones worth taking */
  const skipOf = o => { const sys = o && o.skipRx ? new RegExp(o.skipRx, 'i') : null, keep = o && o.keepRx ? new RegExp(o.keepRx, 'i') : null;
    const f = n => { if (sys && sys.test(n)) return true; if (keep && /\.[A-Za-z0-9]{1,6}$/.test(n) && !keep.test(n)) { f.left++; return true; } return false; };
    f.left = 0; return f; };
  if (typeof document === 'undefined' && typeof root.importScripts === 'function') {       // inside the worker
    root.onmessage = ev => {
      const m = ev.data || {};
      try {
        const opts = Object.assign({}, m.opts, { skip: skipOf(m.opts) });
        const r = api.extract(m.vols.map(b => new Uint8Array(b)), opts,
          (name, parts, of) => { if (of) return root.postMessage({ t: 'copy', name, of });
            const bufs = parts.map(p => p.byteOffset === 0 && p.byteLength === p.buffer.byteLength ? p.buffer : p.slice().buffer); root.postMessage({ t: 'file', name, parts: bufs }, bufs); },
          name => root.postMessage({ t: 'status', name }));
        root.postMessage({ t: 'done', skipped: r.skipped, left: opts.skip.left, format: r.format, filters: r.filters });
      } catch (e) { root.postMessage({ t: 'error', rar: (e && e.rar) || (/alloc|out of memory/i.test(String(e)) ? 'memory' : 'damaged'), why: (e && e.why) || '' }); }
    };
    return;
  }
  /* files: the parts of one archive in order (File or Blob). → {files: [{name, parts}], skipped}; rejects with an Error whose .rar says why */
  let workers = null;                                                // can a worker run here? found out once, with a worker that only answers
  const canWork = () => workers || (workers = new Promise(res => {
    try {
      const w = new Worker(URL.createObjectURL(new Blob(['postMessage(1)'], { type: 'text/javascript' })));
      const t = setTimeout(() => { w.terminate(); res(false); }, 4000);
      w.onmessage = () => { clearTimeout(t); w.terminate(); res(true); }; w.onerror = () => { clearTimeout(t); res(false); };
    } catch (e) { res(false); }
  }));
  async function extract(files, opts, onStatus) {
    const bufs = [];
    try { for (const f of files) bufs.push(await f.arrayBuffer()); } catch (e) { const x = new Error('memory'); x.rar = 'memory'; throw x; }      // the archive itself does not fit in memory
    const out = []; let worker = null;
    if (await canWork()) { try { worker = new Worker(URL.createObjectURL(new Blob([DBRAR_MAIN.toString(), '\nDBRAR_MAIN(self);'], { type: 'text/javascript' }))); } catch (e) { worker = null; } }
    if (!worker) {                                                   // no worker here: the same work on this thread
      const o = Object.assign({}, opts, { skip: skipOf(opts) });
      const r = api.extract(bufs.map(b => new Uint8Array(b)), o, (name, parts, of) => out.push({ name, parts: of ? (out.find(x => x.name === of) || { parts: [] }).parts : parts }), onStatus);
      return { files: out, skipped: r.skipped, left: o.skip.left, format: r.format, filters: r.filters, thread: 'page' };
    }
    return new Promise((res, rej) => {
      const end = fn => { worker.terminate(); fn(); };
      worker.onmessage = ev => { const m = ev.data;
        if (m.t === 'file') out.push({ name: m.name, parts: m.parts });
        else if (m.t === 'copy') out.push({ name: m.name, parts: (out.find(x => x.name === m.of) || { parts: [] }).parts });
        else if (m.t === 'status') { if (onStatus) onStatus(m.name); }
        else if (m.t === 'done') end(() => res({ files: out, skipped: m.skipped, left: m.left, format: m.format, filters: m.filters, thread: 'worker' }));
        else end(() => { const e = new Error(m.rar); e.rar = m.rar; e.why = m.why; rej(e); }); };
      worker.onerror = ev => end(() => { const e = new Error('damaged'); e.rar = /memory|alloc/i.test(String(ev && ev.message)) ? 'memory' : 'damaged'; rej(e); });
      worker.postMessage({ vols: bufs, opts: opts || {} }, bufs);
    });
  }
  root.DBRAR = { extract, core: api };
}
DBRAR_MAIN(typeof self !== 'undefined' ? self : globalThis);
