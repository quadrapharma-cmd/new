// Word files read in the page or in Node, with nothing fetched: the text of a .doc (Word 97–2003: one compound file whose
// «WordDocument» part keeps the text in pieces listed in its table part) and of a .docx (ZIP, word/document.xml), with the text of
// their headers first (a company writes its name there). Paragraphs are lines; a table's cells are joined with « | », a row a line.
// A .doc has no pages until it is laid out: its pages here are the ones its author broke by hand (a .docx's also where Word last
// broke them on screen). A .docx's tracked deletions are left out; a .doc keeps them in its text, marked only in its formatting,
// which is not read. Written from Microsoft's published format notes ([MS-CFB], [MS-DOC], ECMA-376).
import { entries, read } from './zip.js';

const fail = (why, text) => Object.assign(new Error(text), { why });
const u16 = (b, o) => b[o] | (b[o + 1] << 8);
const u32 = (b, o) => (b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24)) >>> 0;

// ---- the compound file ([MS-CFB]): its streams by name
export function cfb(bytes) {
  const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  if (u32(b, 0) !== 0xe011cfd0 || u32(b, 4) !== 0xe11ab1a1) throw fail('damaged', 'not an Office 97–2003 file');
  const shift = u16(b, 0x1e), size = 1 << shift, mini = 1 << u16(b, 0x20), cutoff = u32(b, 0x38);
  const sector = n => b.subarray((n + 1) * size, (n + 2) * size);
  const fatSectors = [];
  for (let i = 0; i < 109; i++) { const s = u32(b, 0x4c + i * 4); if (s < 0xfffffffa) fatSectors.push(s); }
  for (let d = u32(b, 0x44), guard = 0; d < 0xfffffffa && guard < 1e5; guard++) {   // more of the table of sectors, chained
    const s = sector(d);
    for (let i = 0; i < size / 4 - 1; i++) { const v = u32(s, i * 4); if (v < 0xfffffffa) fatSectors.push(v); }
    d = u32(s, size - 4);
  }
  const fat = new Uint32Array(fatSectors.length * size / 4);
  fatSectors.forEach((s, k) => { const sec = sector(s); for (let i = 0; i < size / 4; i++) fat[k * size / 4 + i] = u32(sec, i * 4); });
  const chain = (start, table, cap) => {
    const out = [];
    for (let s = start, guard = 0; s < 0xfffffffa && guard < cap; guard++) { out.push(s); s = table[s]; }
    return out;
  };
  const join = (list, get, unit) => { const o = new Uint8Array(list.length * unit); list.forEach((s, i) => o.set(get(s), i * unit)); return o; };
  const dir = join(chain(u32(b, 0x30), fat, fat.length), sector, size);
  const items = [];
  for (let o = 0; o + 128 <= dir.length; o += 128) {
    const len = u16(dir, o + 0x40), type = dir[o + 0x42];
    if (!type || len < 2) continue;
    const name = String.fromCharCode(...Array.from({ length: len / 2 - 1 }, (_, i) => u16(dir, o + i * 2)));
    items.push({ name, type, start: u32(dir, o + 0x74), size: u32(dir, o + 0x78) });
  }
  const root = items.find(x => x.type === 5);
  const miniFat = (() => {
    const list = chain(u32(b, 0x3c), fat, fat.length), t = new Uint32Array(list.length * size / 4);
    list.forEach((s, k) => { const sec = sector(s); for (let i = 0; i < size / 4; i++) t[k * size / 4 + i] = u32(sec, i * 4); });
    return t;
  })();
  const miniStream = root ? join(chain(root.start, fat, fat.length), sector, size) : new Uint8Array(0);
  return {
    names: items.filter(x => x.type === 2).map(x => x.name),
    stream(name) {
      const e = items.find(x => x.type === 2 && x.name === name);
      if (!e) return null;
      const data = e.size < cutoff
        ? join(chain(e.start, miniFat, miniFat.length), s => miniStream.subarray(s * mini, (s + 1) * mini), mini)
        : join(chain(e.start, fat, fat.length), sector, size);
      return data.subarray(0, e.size);
    },
  };
}

// ---- Word 97–2003 ([MS-DOC]): the text in its pieces, special marks turned to lines, cells and pages
const W1252 = new TextDecoder('windows-1252');
function pieces(word, table) {
  const fcClx = u32(word, 0x1a2), lcbClx = u32(word, 0x1a6);
  if (!lcbClx || fcClx + lcbClx > table.length) throw fail('damaged', 'the Word file has no list of its text');
  let o = fcClx;
  while (o < fcClx + lcbClx && table[o] === 0x01) o += 3 + (table[o + 1] | (table[o + 2] << 8));   // formatting kept beside the text
  if (table[o] !== 0x02) throw fail('damaged', 'the Word file\'s list of its text is damaged');
  const lcb = u32(table, o + 1), plc = table.subarray(o + 5, o + 5 + lcb), n = (lcb - 4) / 12;
  return Array.from({ length: n }, (_, i) => {
    const cp = u32(plc, i * 4), next = u32(plc, (i + 1) * 4), fc = u32(plc, (n + 1) * 4 + i * 8 + 2);
    return { cp, next, compressed: !!(fc & 0x40000000), fc: fc & 0x3fffffff };
  });
}
function textAt(word, list, from, to) {
  let out = '';
  for (const p of list) {
    const a = Math.max(from, p.cp), z = Math.min(to, p.next);
    if (a >= z) continue;
    if (p.compressed) out += W1252.decode(word.subarray(p.fc / 2 + (a - p.cp), p.fc / 2 + (z - p.cp)));
    else { const s = p.fc + (a - p.cp) * 2; out += new TextDecoder('utf-16le').decode(word.subarray(s, s + (z - a) * 2)); }
  }
  return out;
}
// Word's marks: fields (\x13 code \x14 result \x15: the code dropped, the result kept), cells (\x07; a row ends with one more),
// paragraphs (\r), line and column breaks (\x0b \x0e), pages (\x0c), objects and notes' marks (dropped)
function plain(t) {
  let out = '', depth = 0;
  const code = [];                                   // for each open field: still in its code?
  for (const ch of t) {
    if (ch === '\x13') { code.push(true); depth++; continue; }
    if (ch === '\x14') { if (depth) code[code.length - 1] = false; continue; }
    if (ch === '\x15') { if (depth) { code.pop(); depth--; } continue; }
    if (code.includes(true)) continue;
    out += ch;
  }
  return out.replace(/\x07\x07/g, '\n').replace(/\x07/g, ' | ').replace(/[\r\x0b\x0e]/g, '\n').replace(/\x1e/g, '-')
    .replace(/[\x00-\x08\x1f]/g, '').replace(/ /g, ' ').replace(/[ \t]+\n/g, '\n');
}
export function docText(bytes) {
  const f = cfb(bytes), word = f.stream('WordDocument');
  if (!word || u16(word, 0) !== 0xa5ec) throw fail('damaged', 'not a Word document');
  if (u16(word, 2) < 101) throw fail('unsupported', 'a Word 6 or Word 95 file: save it again from Word to read it');
  const flags = u16(word, 0x0a);
  if (flags & 0x0100) throw fail('password', 'the Word file is under a password');
  const table = f.stream(flags & 0x0200 ? '1Table' : '0Table');
  if (!table) throw fail('damaged', 'the Word file has no table part');
  const list = pieces(word, table);
  const ccpText = u32(word, 0x4c), ccpFtn = u32(word, 0x50), ccpHdd = u32(word, 0x54);
  const body = plain(textAt(word, list, 0, ccpText));
  const head = ccpHdd ? plain(textAt(word, list, ccpText + ccpFtn, ccpText + ccpFtn + ccpHdd)) : '';
  return pagesOf(body, head, 'word');
}

// ---- .docx (ECMA-376): word/document.xml and the headers, read by their tags
const ENT = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'" };
const unxml = s => s.replace(/&(#x[0-9a-f]+|#\d+|\w+);/gi, (m, e) => (e[0] === '#' ? String.fromCodePoint(e[1] === 'x' || e[1] === 'X' ? parseInt(e.slice(2), 16) : +e.slice(1)) : ENT[e] ?? m));
export function xmlText(xml) {
  const src = xml.replace(/<w:del\b[\s\S]*?<\/w:del>/g, '').replace(/<w:instrText\b[\s\S]*?<\/w:instrText>/g, '')
    .replace(/<mc:Fallback\b[\s\S]*?<\/mc:Fallback>/g, '');   // a text box is written twice, the second time for old readers
  let out = '';
  const cells = [];                                   // how many cells deep, per open table
  for (const m of src.matchAll(/<(\/?)(w:t|w:p|w:tc|w:tr|w:tab|w:br|w:cr|w:noBreakHyphen|w:lastRenderedPageBreak|w:tbl)\b([^>]*?)(\/?)>|([^<]+)/g)) {
    const [, close, tag, attrs, self, text] = m;
    if (text !== undefined) { if (out.endsWith('\u0001')) { out = out.slice(0, -1) + unxml(text); } continue; }
    if (tag === 'w:t' && !close && !self) { out += '\u0001'; continue; }            // the text that follows is a run's
    if (tag === 'w:t' && close) { if (out.endsWith('\u0001')) out = out.slice(0, -1); continue; }
    if (tag === 'w:tab') out += '\t';
    else if (tag === 'w:br') out += /w:type="page"/.test(attrs) ? '\f' : '\n';
    else if (tag === 'w:cr') out += '\n';
    else if (tag === 'w:noBreakHyphen') out += '-';
    else if (tag === 'w:lastRenderedPageBreak') out += '\f';
    else if (tag === 'w:tbl') { if (close) cells.pop(); else if (!self) cells.push(0); }
    else if (tag === 'w:p' && close) out += cells.length ? ' ' : '\n';
    else if (tag === 'w:tc' && close) out = out.replace(/ $/, '') + ' | ';
    else if (tag === 'w:tr' && close) out = out.replace(/ \| $/, '') + '\n';
  }
  return out.replace(/\u0001/g, '').replace(/[ \t]+\n/g, '\n');
}
export async function docxText(bytes) {
  const list = entries(bytes);
  const get = async name => { const e = list.find(x => x.name === name); return e ? new TextDecoder().decode(await read(bytes, e)) : null; };
  const doc = await get('word/document.xml');
  if (doc === null) throw fail('damaged', 'not a Word document (no word/document.xml)');
  const heads = [];
  for (const e of list.filter(x => /^word\/header\d*\.xml$/.test(x.name)).sort((a, c) => a.name.localeCompare(c.name, 'en', { numeric: true }))) {
    heads.push(xmlText(await get(e.name)));
  }
  return pagesOf(xmlText(doc), heads.join('\n'), 'word');
}

// The text cut at its page breaks, the headers' lines (each once) on top of the first page.
function pagesOf(body, head, by) {
  const tidy = s => s.split('\n').map(l => l.replace(/\s+/g, ' ').trim()).filter(Boolean);
  const top = [...new Set(tidy(head))];
  const parts = body.split('\f');
  return parts.map((t, i) => ({ n: i + 1, text: (i === 0 ? [...top, ...tidy(t)] : tidy(t)).join('\n'), by })).filter((p, i) => i === 0 || p.text);
}
