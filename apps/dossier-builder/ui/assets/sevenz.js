/* 7z archives opened inside the page — the program's own reader, no library and nothing fetched.
   Written from the 7z format's public description (7zFormat.txt) and the LZMA specification with the reference decoder Igor Pavlov
   placed in the public domain (the LZMA SDK). It reads what 7-Zip and the other packers write for documents: LZMA2 (7-Zip's default)
   and LZMA, the x86 branch filter and the delta filter, files kept as they are, solid and non-solid archives, a header that is itself
   packed, names in any language. Every file is checked against the CRC-32 the archive keeps for it: a file that does not match is
   reported as unreadable, never handed over. Not read: files under a password, archives split in parts, and the other methods (PPMd,
   BZip2, Deflate, BCJ2, the filters for other processors) — each is reported with its reason; in the desktop and server editions
   the machine's own unpacker is tried for them (archive.js).
   The work is done in a worker made from this same source, so the page keeps answering; where a worker cannot be made it runs on
   the page's own thread. The same shape as the RAR reader (rar.js). */
function DB7Z_MAIN(root) {
  'use strict';
  function core() {
    const E = (code, why) => { const e = new Error('7z ' + code + (why ? ' ' + why : '')); e.z7 = code; e.why = why || ''; return e; };

    /* ---------------- CRC-32 */
    const CRC = new Uint32Array(256);
    for (let i = 0; i < 256; i++) { let c = i; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; CRC[i] = c; }
    function crc32(d) { let c = 0xffffffff; for (let i = 0; i < d.length; i++) c = CRC[(c ^ d[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; }

    /* ---------------- LZMA: a range decoder, bits each with an adaptive probability, literals coded against the byte a match
       would give, lengths and distances from small bit trees. The whole output is one array (its size is known from the
       archive), which is also the dictionary. */
    const TOP = 1 << 24, BITS = 11, MOVE = 5, HALF = 1 << (BITS - 1);
    function Range(src, at, end) {
      this.src = src; this.at = at; this.end = end;
      if (src[this.at++] !== 0) throw E('damaged', 'range coder');
      this.range = 0xffffffff; this.code = 0;
      for (let i = 0; i < 4; i++) this.code = ((this.code << 8) | this.byte()) >>> 0;
      if (this.code === this.range) throw E('damaged', 'range coder');
    }
    Range.prototype.byte = function () { if (this.at >= this.end) throw E('damaged', 'data ends early'); return this.src[this.at++]; };
    Range.prototype.bit = function (p, i) {
      const bound = ((this.range >>> BITS) * p[i]) >>> 0;
      let b;
      if (this.code < bound) { p[i] += ((1 << BITS) - p[i]) >>> MOVE; this.range = bound; b = 0; }
      else { p[i] -= p[i] >>> MOVE; this.code = (this.code - bound) >>> 0; this.range = (this.range - bound) >>> 0; b = 1; }
      if (this.range < TOP) { this.range = (this.range << 8) >>> 0; this.code = ((this.code << 8) | this.byte()) >>> 0; }
      return b;
    };
    Range.prototype.direct = function (n) {
      let res = 0;
      while (n--) {
        this.range = this.range >>> 1;
        let t = 0;
        if (this.code >= this.range) { this.code = (this.code - this.range) >>> 0; t = 1; }
        res = ((res << 1) | t) >>> 0;
        if (this.range < TOP) { this.range = (this.range << 8) >>> 0; this.code = ((this.code << 8) | this.byte()) >>> 0; }
      }
      return res;
    };
    Range.prototype.tree = function (p, base, n) { let m = 1; for (let i = 0; i < n; i++) m = (m << 1) + this.bit(p, base + m); return m - (1 << n); };
    Range.prototype.reverse = function (p, base, n) { let m = 1, s = 0; for (let i = 0; i < n; i++) { const b = this.bit(p, base + m); m = (m << 1) + b; s |= b << i; } return s; };

    const probs = n => new Uint16Array(n).fill(HALF);
    function Len() { this.choice = probs(2); this.low = probs(16 << 3); this.mid = probs(16 << 3); this.high = probs(256); }
    Len.prototype.decode = function (rc, posState) {
      if (!rc.bit(this.choice, 0)) return rc.tree(this.low, posState << 3, 3);
      if (!rc.bit(this.choice, 1)) return 8 + rc.tree(this.mid, posState << 3, 3);
      return 16 + rc.tree(this.high, 0, 8);
    };

    /* one LZMA decoder over an output array it writes from `pos` on; LZMA2 keeps it across its chunks */
    function Decoder(out) { this.out = out; this.pos = 0; this.start = 0; }
    Decoder.prototype.props = function (lc, lp, pb) {
      if (lc > 8 || lp > 4 || pb > 4) throw E('damaged', 'properties');
      this.lc = lc; this.lp = lp; this.pb = pb;
      this.lit = probs(0x300 << (lc + lp));
      this.reset();
    };
    Decoder.prototype.reset = function () {
      this.lit.fill(HALF);
      this.isMatch = probs(12 << 4); this.isRep = probs(12); this.isRepG0 = probs(12); this.isRepG1 = probs(12); this.isRepG2 = probs(12);
      this.isRep0Long = probs(12 << 4); this.slot = probs(4 << 6); this.posProbs = probs(115); this.align = probs(16);
      this.len = new Len(); this.repLen = new Len();
      this.state = 0; this.rep0 = this.rep1 = this.rep2 = this.rep3 = 0;
    };
    Decoder.prototype.run = function (rc, size) {                      // `size` bytes from the range coder
      const out = this.out, end = this.pos + size, pbMask = (1 << this.pb) - 1, lpMask = (1 << this.lp) - 1;
      while (this.pos < end) {
        const done = this.pos - this.start, posState = done & pbMask;   // counted from the dictionary's start
        const state = this.state;
        if (!rc.bit(this.isMatch, (state << 4) + posState)) {
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
          if (this.pos === this.start) throw E('damaged', 'repeat with nothing before it');
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
          if (dist === 0xffffffff) {                                 // the end marker: allowed only at the very end
            if (this.pos === end) return;
            throw E('damaged', 'end marker before the end');
          }
          this.rep0 = dist;
          if (dist >= this.pos - this.start) throw E('damaged', 'distance before the start');
        }
        len += 2;
        if (this.pos + len > end) throw E('damaged', 'match past the end');
        const from = this.pos - this.rep0 - 1;
        for (let i = 0; i < len; i++) out[this.pos + i] = out[from + i];
        this.pos += len;
      }
    };
    Decoder.prototype.distance = function (rc, len) {
      const slot = rc.tree(this.slot, (len > 3 ? 3 : len) << 6, 6);
      if (slot < 4) return slot;
      const direct = (slot >>> 1) - 1;
      let dist = ((2 | (slot & 1)) << direct) >>> 0;
      if (slot < 14) dist = (dist + rc.reverse(this.posProbs, dist - slot, direct)) >>> 0;
      else dist = (dist + (rc.direct(direct - 4) << 4 >>> 0) + rc.reverse(this.align, 0, 4)) >>> 0;
      return dist;
    };

    function output(size) {                                          // the array a coder writes into: its size is the archive's word
      if (!(size >= 0) || size > 2147483647) throw E('memory');
      try { return new Uint8Array(size); } catch (e) { throw E('memory'); }
    }
    function lzma(src, props, size) {
      const out = output(size), d = new Decoder(out);
      let p = props[0];
      if (props.length < 5 || p >= 9 * 5 * 5) throw E('damaged', 'properties');
      const lc = p % 9; p = (p / 9) | 0;
      d.props(lc, p % 5, (p / 5) | 0);
      if (size) d.run(new Range(src, 0, src.length), size);
      return out;
    }
    function lzma2(src, propByte, size) {
      if (propByte > 40) throw E('damaged', 'dictionary size');
      const out = output(size), d = new Decoder(out);
      let at = 0, ready = false;
      for (;;) {
        if (at >= src.length) throw E('damaged', 'data ends early');
        const c = src[at++];
        if (c === 0) break;
        if (c === 1 || c === 2) {                                    // a chunk kept as it is (1: the dictionary starts again)
          const n = ((src[at] << 8) | src[at + 1]) + 1; at += 2;
          if (c === 1) d.start = d.pos;
          if (d.pos + n > size || at + n > src.length) throw E('damaged', 'chunk past the end');
          out.set(src.subarray(at, at + n), d.pos); d.pos += n; at += n;
          continue;
        }
        if (c < 0x80) throw E('damaged', 'chunk');
        const unpacked = ((c & 0x1f) << 16) + (src[at] << 8) + src[at + 1] + 1;
        const packed = (src[at + 2] << 8) + src[at + 3] + 1;
        at += 4;
        const reset = (c >>> 5) & 3;
        if (reset === 3) d.start = d.pos;
        if (reset >= 2) {
          let p = src[at++];
          const lc = p % 9; p = (p / 9) | 0;
          if (lc + (p % 5) > 4) throw E('damaged', 'properties');
          d.props(lc, p % 5, (p / 5) | 0); ready = true;
        } else if (reset === 1) { if (!ready) throw E('damaged', 'no properties'); d.reset(); }
        else if (!ready) throw E('damaged', 'no properties');
        if (d.pos + unpacked > size || at + packed > src.length) throw E('damaged', 'chunk past the end');
        d.run(new Range(src, at, at + packed), unpacked);
        at += packed;
      }
      if (d.pos !== size) throw E('damaged', 'shorter than its size');
      return out;
    }
    /* the x86 branch filter (BCJ): call and jump addresses written relative again — the LZMA SDK's filter, decoding */
    function bcjX86(data) {
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
    /* the delta filter: each byte stored as its difference from the byte `dist` before it */
    function delta(data, dist) { for (let i = dist; i < data.length; i++) data[i] = (data[i] + data[i - dist]) & 0xff; return data; }

    /* ---------------- the 7z structure: a signature header pointing to the archive's header at its end (often itself packed),
       streams of packed data, «folders» (the coders a stream goes through) and the files cut out of each folder's output in order */
    const SIG = [0x37, 0x7a, 0xbc, 0xaf, 0x27, 0x1c];
    const ID = { end: 0, header: 1, archiveProps: 2, additional: 3, main: 4, files: 5, pack: 6, unpack: 7, substreams: 8, size: 9, crc: 10,
                 folder: 11, unpackSize: 12, numUnpack: 13, emptyStream: 14, emptyFile: 15, anti: 16, name: 17, encoded: 0x17 };
    function Reader(b, at, end) { this.b = b; this.at = at || 0; this.end = end === undefined ? b.length : end; }
    Reader.prototype.byte = function () { if (this.at >= this.end) throw E('damaged', 'header ends early'); return this.b[this.at++]; };
    Reader.prototype.number = function () {                            // the 7z number: its first byte's leading ones say how many follow
      const first = this.byte();
      let mask = 0x80, value = 0;
      for (let i = 0; i < 8; i++) {
        if ((first & mask) === 0) return value + (first & (mask - 1)) * Math.pow(2, 8 * i);
        value += this.byte() * Math.pow(2, 8 * i);
        mask >>>= 1;
      }
      return value;
    };
    Reader.prototype.u32 = function () {
      if (this.at + 4 > this.end) throw E('damaged', 'header ends early');
      const b = this.b, v = (b[this.at] | (b[this.at + 1] << 8) | (b[this.at + 2] << 16) | (b[this.at + 3] << 24)) >>> 0; this.at += 4; return v;
    };
    Reader.prototype.bits = function (n) { const out = []; let mask = 0, byte = 0; for (let i = 0; i < n; i++) { if (!mask) { byte = this.byte(); mask = 0x80; } out.push(!!(byte & mask)); mask >>>= 1; } return out; };
    Reader.prototype.defined = function (n) { const all = this.byte(); return all ? new Array(n).fill(true) : this.bits(n); };
    Reader.prototype.skip = function (n) { this.at += n; if (this.at > this.end) throw E('damaged', 'header ends early'); };
    const digests = (r, n) => r.defined(n).map(d => (d ? r.u32() : null));

    function packInfo(r) {
      const info = { pos: r.number(), sizes: [], crcs: [] };
      const n = r.number();
      for (let id = r.byte(); id !== ID.end; id = r.byte()) {
        if (id === ID.size) for (let i = 0; i < n; i++) info.sizes.push(r.number());
        else if (id === ID.crc) info.crcs = digests(r, n);
        else throw E('damaged', 'pack info');
      }
      return info;
    }
    function folder(r) {
      const coders = [];
      let ins = 0, outs = 0;
      for (let i = 0, n = r.number(); i < n; i++) {
        const flags = r.byte();
        if (flags & 0x80) throw E('unsupported', 'alternative coders');
        let id = ''; for (let k = 0; k < (flags & 0x0f); k++) id += r.byte().toString(16).padStart(2, '0');
        const coder = { id, ins: 1, outs: 1, props: new Uint8Array(0) };
        if (flags & 0x10) { coder.ins = r.number(); coder.outs = r.number(); }
        if (flags & 0x20) { const size = r.number(); coder.props = r.b.subarray(r.at, r.at + size); r.skip(size); }
        coder.firstIn = ins; coder.firstOut = outs; ins += coder.ins; outs += coder.outs;
        coders.push(coder);
      }
      if (!coders.length || outs > 64 || ins > 64) throw E('damaged', 'folder');
      const bonds = [];
      for (let i = 0; i < outs - 1; i++) bonds.push({ in: r.number(), out: r.number() });
      const packedCount = ins - bonds.length, packed = [];
      if (packedCount === 1) { for (let i = 0; i < ins; i++) if (!bonds.some(b => b.in === i)) { packed.push(i); break; } }
      else for (let i = 0; i < packedCount; i++) packed.push(r.number());
      return { coders, bonds, packed, ins, outs, sizes: [], crc: null };
    }
    function unpackInfo(r) {
      if (r.byte() !== ID.folder) throw E('damaged', 'no folders');
      const n = r.number();
      if (r.byte() !== 0) throw E('unsupported', 'folders kept elsewhere');
      const folders = [];
      for (let i = 0; i < n; i++) folders.push(folder(r));
      if (r.byte() !== ID.unpackSize) throw E('damaged', 'no unpacked sizes');
      for (const f of folders) for (let i = 0; i < f.outs; i++) f.sizes.push(r.number());
      for (let id = r.byte(); id !== ID.end; id = r.byte()) {
        if (id === ID.crc) digests(r, n).forEach((c, i) => { folders[i].crc = c; });
        else throw E('damaged', 'unpack info');
      }
      return folders;
    }
    const outOf = f => { for (let i = 0; i < f.outs; i++) if (!f.bonds.some(b => b.out === i)) return i; throw E('damaged', 'folder with no output'); };
    function substreams(r, folders) {
      const counts = folders.map(() => 1);
      let id = r.byte();
      if (id === ID.numUnpack) { for (let i = 0; i < folders.length; i++) counts[i] = r.number(); id = r.byte(); }
      const sizes = [], hasSizes = id === ID.size;
      folders.forEach((f, i) => {
        if (!counts[i]) return;
        const total = f.sizes[outOf(f)];
        let sum = 0;
        for (let k = 1; k < counts[i]; k++) { const s = hasSizes ? r.number() : 0; sizes.push(s); sum += s; }
        if (sum > total) throw E('damaged', 'sizes');
        sizes.push(total - sum);
      });
      if (hasSizes) id = r.byte();
      const crcs = [];                                               // a CRC for every stream whose folder has none of its own as one stream
      const unknown = folders.reduce((n, f, i) => n + (counts[i] === 1 && f.crc !== null ? 0 : counts[i]), 0);
      if (id === ID.crc) {
        const list = digests(r, unknown);
        let k = 0;
        folders.forEach((f, i) => { for (let j = 0; j < counts[i]; j++) crcs.push(counts[i] === 1 && f.crc !== null ? f.crc : list[k++]); });
        id = r.byte();
      } else folders.forEach((f, i) => { for (let j = 0; j < counts[i]; j++) crcs.push(counts[i] === 1 ? f.crc : null); });
      if (id !== ID.end) throw E('damaged', 'substreams');
      return { counts, sizes, crcs };
    }
    function streamsInfo(r) {
      const s = { pack: null, folders: [], sub: null };
      for (let id = r.byte(); id !== ID.end; id = r.byte()) {
        if (id === ID.pack) s.pack = packInfo(r);
        else if (id === ID.unpack) s.folders = unpackInfo(r);
        else if (id === ID.substreams) s.sub = substreams(r, s.folders);
        else throw E('damaged', 'streams info');
      }
      if (!s.sub) s.sub = { counts: s.folders.map(() => 1), sizes: s.folders.map(f => f.sizes[outOf(f)]), crcs: s.folders.map(f => f.crc) };
      return s;
    }

    const METHOD = { '00': 'Copy', '21': 'LZMA2', '030101': 'LZMA', '03030103': 'BCJ', '04': 'BCJ', '03': 'Delta' };
    /* one folder's output: its coders run from the packed streams to the one output nobody else takes */
    function decodeFolder(f, packed, used) {
      const outputs = new Map();
      const inputOf = idx => {
        const p = f.packed.indexOf(idx);
        if (p >= 0) { if (!packed[p]) throw E('damaged', 'packed stream'); return packed[p]; }
        const bond = f.bonds.find(b => b.in === idx);
        if (!bond) throw E('damaged', 'coder input with no source');
        return run(bond.out);
      };
      function run(outIdx) {
        if (outputs.has(outIdx)) return outputs.get(outIdx);
        const coder = f.coders.find(c => outIdx >= c.firstOut && outIdx < c.firstOut + c.outs);
        if (!coder) throw E('damaged', 'no coder');
        if (coder.id === '06f10701') throw E('password');
        if (coder.ins !== 1 || coder.outs !== 1) throw E('unsupported', coder.id === '0303011b' ? 'BCJ2' : coder.id);
        const input = inputOf(coder.firstIn), size = f.sizes[outIdx];
        let out;
        if (coder.id === '00') { if (input.length < size) throw E('damaged', 'stored'); out = input.slice(0, size); }
        else if (coder.id === '21') out = lzma2(input, coder.props[0], size);
        else if (coder.id === '030101') out = lzma(input, coder.props, size);
        else if (coder.id === '03030103' || coder.id === '04') out = bcjX86(input.slice(0, size));
        else if (coder.id === '03') out = delta(input.slice(0, size), (coder.props.length ? coder.props[0] : 0) + 1);
        else throw E('unsupported', { '030401': 'PPMd', '040202': 'BZip2', '040108': 'Deflate', '040109': 'Deflate64' }[coder.id] || coder.id);
        if (out.length !== size) throw E('damaged', 'output size');
        if (used) used[METHOD[coder.id]] = true;
        outputs.set(outIdx, out);
        return out;
      }
      const out = run(outOf(f));
      if (f.crc !== null && crc32(out) !== f.crc) throw E('unreadable');
      return out;
    }
    function packedStreams(b, s) {
      if (!s.pack) return [];
      let at = 32 + s.pack.pos;
      const list = s.pack.sizes.map(n => { const x = b.subarray(at, at + n); at += n; return x; });
      if (at > b.length) throw E('volume');                            // cut short, or one part of several
      return list;
    }
    function folderPacked(s, list) { let k = 0; return s.folders.map(f => { const mine = list.slice(k, k + f.packed.length); k += f.packed.length; return mine; }); }
    function filesInfo(r) {
      const n = r.number();
      if (n > 10000000) throw E('damaged', 'files');
      const files = [];
      for (let i = 0; i < n; i++) files.push({ name: '', empty: false, emptyFile: false, anti: false });
      for (let id = r.byte(); id !== ID.end; id = r.byte()) {
        const size = r.number(), end = r.at + size;
        if (end > r.end) throw E('damaged', 'files');
        if (id === ID.emptyStream) r.bits(n).forEach((e, i) => { files[i].empty = e; });
        else if (id === ID.emptyFile || id === ID.anti) {
          const empties = files.filter(f => f.empty);
          r.bits(empties.length).forEach((e, i) => { if (id === ID.emptyFile) empties[i].emptyFile = e; else empties[i].anti = e; });
        } else if (id === ID.name) {
          if (r.byte() !== 0) throw E('unsupported', 'names kept elsewhere');
          for (const f of files) {
            const cs = [];
            for (;;) { if (r.at + 2 > end) throw E('damaged', 'names'); const c = r.b[r.at] | (r.b[r.at + 1] << 8); r.at += 2; if (!c) break; cs.push(c); }
            let s = ''; for (let k = 0; k < cs.length; k += 4096) s += String.fromCharCode.apply(null, cs.slice(k, k + 4096));
            f.name = s;
          }
        }
        r.at = end;
      }
      return files;
    }
    const clean = name => name.replace(/\\/g, '/').replace(/^[A-Za-z]:/, '').split('/').filter(x => x && x !== '.' && x !== '..').join('/') || 'file';

    /* vols: the archive's bytes (one part); opts.skip(name) → true for a file not worth taking; onFile(name, parts) for each file */
    function extract(vols, opts, onFile, onStatus) {
      opts = opts || {};
      if (vols.length !== 1) throw E('volume');
      const b = vols[0];
      if (b.length < 32 || SIG.some((x, i) => b[i] !== x)) throw E('damaged', 'signature');
      const start = new Reader(b, 12);
      const offset = start.u32() + start.u32() * 4294967296, size = start.u32() + start.u32() * 4294967296, headCrc = start.u32();
      if (32 + offset + size > b.length) throw E('volume');           // cut short, or the first of several parts
      const used = {}, skipped = [];
      if (!size) return { skipped, count: 0, methods: used, format: '7z' };
      let head = b.subarray(32 + offset, 32 + offset + size);
      if (crc32(head) !== headCrc) throw E('damaged', 'header CRC');
      let r = new Reader(head), id = r.byte();
      while (id === ID.encoded) {                                      // the header itself packed (7-Zip does so by default)
        const s = streamsInfo(r);
        if (!s.folders.length) throw E('damaged', 'encoded header');
        head = decodeFolder(s.folders[0], folderPacked(s, packedStreams(b, s))[0], null);
        r = new Reader(head); id = r.byte();
      }
      if (id !== ID.header) throw E('damaged', 'no header');
      let main = null, files = [];
      for (id = r.byte(); id !== ID.end; id = r.byte()) {
        if (id === ID.archiveProps) { for (let p = r.byte(); p; p = r.byte()) r.skip(r.number()); }
        else if (id === ID.additional) streamsInfo(r);
        else if (id === ID.main) main = streamsInfo(r);
        else if (id === ID.files) files = filesInfo(r);
        else throw E('damaged', 'header');
      }
      const maxFiles = opts.maxFiles || Infinity, maxTotal = opts.maxTotal || Infinity, maxFile = opts.maxFile || Infinity, ratio = opts.maxRatio || 250;
      const withData = files.filter(f => !f.empty);
      let count = 0, total = 0;
      if (main) {
        const declared = main.folders.reduce((a, f) => a + f.sizes[outOf(f)], 0);
        if (declared > 104857600 && declared > ratio * b.length) throw E('big', 'bomb');      // expands hundreds of times past 100 MB: a «bomb»
        if (main.sub.sizes.length !== withData.length) throw E('damaged', 'file count');
        const packs = folderPacked(main, packedStreams(b, main));
        let k = 0;
        main.folders.forEach((f, fi) => {
          const n = main.sub.counts[fi], mine = [];
          for (let j = 0; j < n; j++, k++) mine.push({ index: k, name: clean(withData[k].name) });
          mine.forEach(m => { m.want = !(opts.skip && opts.skip(m.name)); m.size = main.sub.sizes[m.index]; m.large = m.size > maxFile; });
          if (!mine.some(m => m.want && !m.large)) { mine.forEach(m => { if (m.want) skipped.push({ name: m.name, why: 'too large' }); }); return; }   // nothing wanted here: not unpacked at all
          if (onStatus) onStatus((mine.find(m => m.want) || mine[0]).name);
          let data;
          try { data = decodeFolder(f, packs[fi], used); }
          catch (e) {
            if (e.z7 === 'memory' || e.z7 === 'big') throw e;
            const why = e.z7 === 'password' ? 'password' : e.z7 === 'unsupported' ? 'unsupported' : e.z7 === 'volume' ? 'volume' : 'unreadable';
            mine.forEach(m => { if (m.want) skipped.push({ name: m.name, why, method: e.why || '' }); });
            return;
          }
          let at = 0;
          for (const m of mine) {
            const piece = data.subarray(at, at + m.size), crc = main.sub.crcs[m.index]; at += m.size;
            if (!m.want) continue;
            if (m.large) { skipped.push({ name: m.name, why: 'too large' }); continue; }
            if (piece.length !== m.size || (crc !== null && crc !== undefined && crc32(piece) !== crc)) { skipped.push({ name: m.name, why: 'unreadable' }); continue; }
            if (count >= maxFiles) throw E('big', 'files');
            total += m.size; if (total > maxTotal) throw E('big', 'total');
            count++; onFile(m.name, [piece]);
          }
        });
      }
      for (const f of files) {                                         // empty files (an empty stream that is not a folder)
        if (!f.empty || !f.emptyFile || f.anti) continue;
        const name = clean(f.name);
        if (opts.skip && opts.skip(name)) continue;
        if (count >= maxFiles) throw E('big', 'files');
        count++; onFile(name, [new Uint8Array(0)]);
      }
      return { skipped, count, methods: used, format: '7z' };
    }
    return { extract, crc32 };
  }

  const api = core();
  /* what is left packed: system files, and names with an extension that is not among the ones worth taking */
  const skipOf = o => { const sys = o && o.skipRx ? new RegExp(o.skipRx, 'i') : null, keep = o && o.keepRx ? new RegExp(o.keepRx, 'i') : null;
    const f = n => { if (sys && sys.test(n)) return true; if (keep && /\.[A-Za-z0-9]{1,6}$/.test(n) && !keep.test(n)) { f.left++; return true; } return false; };
    f.left = 0; return f; };
  const memoryError = e => /alloc|out of memory|invalid typed array length|array buffer/i.test(String(e && e.message || e));
  if (typeof document === 'undefined' && typeof root.importScripts === 'function') {       // inside the worker
    root.onmessage = ev => {
      const m = ev.data || {};
      try {
        const opts = Object.assign({}, m.opts, { skip: skipOf(m.opts) });
        const r = api.extract(m.vols.map(b => new Uint8Array(b)), opts,
          (name, parts) => { const bufs = parts.map(p => p.byteOffset === 0 && p.byteLength === p.buffer.byteLength ? p.buffer : p.slice().buffer); root.postMessage({ t: 'file', name, parts: bufs }, bufs); },
          name => root.postMessage({ t: 'status', name }));
        root.postMessage({ t: 'done', skipped: r.skipped, left: opts.skip.left, format: r.format, methods: r.methods });
      } catch (e) { root.postMessage({ t: 'error', z7: (e && e.z7) || (memoryError(e) ? 'memory' : 'damaged'), why: (e && e.why) || '' }); }
    };
    return;
  }
  /* files: the archive (one File or Blob). → {files: [{name, parts}], skipped}; rejects with an Error whose .z7 says why */
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
    try { for (const f of files) bufs.push(await f.arrayBuffer()); } catch (e) { const x = new Error('memory'); x.z7 = 'memory'; throw x; }      // the archive itself does not fit in memory
    const out = []; let worker = null;
    if (await canWork()) { try { worker = new Worker(URL.createObjectURL(new Blob([DB7Z_MAIN.toString(), '\nDB7Z_MAIN(self);'], { type: 'text/javascript' }))); } catch (e) { worker = null; } }
    if (!worker) {                                                   // no worker here: the same work on this thread
      const o = Object.assign({}, opts, { skip: skipOf(opts) });
      try {
        const r = api.extract(bufs.map(b => new Uint8Array(b)), o, (name, parts) => out.push({ name, parts }), onStatus);
        return { files: out, skipped: r.skipped, left: o.skip.left, format: r.format, methods: r.methods, thread: 'page' };
      } catch (e) { if (!e.z7) e.z7 = memoryError(e) ? 'memory' : 'damaged'; throw e; }
    }
    return new Promise((res, rej) => {
      const end = fn => { worker.terminate(); fn(); };
      worker.onmessage = ev => { const m = ev.data;
        if (m.t === 'file') out.push({ name: m.name, parts: m.parts });
        else if (m.t === 'status') { if (onStatus) onStatus(m.name); }
        else if (m.t === 'done') end(() => res({ files: out, skipped: m.skipped, left: m.left, format: m.format, methods: m.methods, thread: 'worker' }));
        else end(() => { const e = new Error(m.z7); e.z7 = m.z7; e.why = m.why; rej(e); }); };
      worker.onerror = ev => end(() => { const e = new Error('damaged'); e.z7 = memoryError(ev && ev.message) ? 'memory' : 'damaged'; rej(e); });
      worker.postMessage({ vols: bufs, opts: opts || {} }, bufs);
    });
  }
  root.DB7Z = { extract, core: api };
}
DB7Z_MAIN(typeof self !== 'undefined' ? self : globalThis);
