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

// ---- an InDesign package (IDML): the words of its stories (Stories/Story_*.xml, each <Content> a run of text, <Br/> a new line),
// in the order the package lists them — what a pack's artwork says (its name, strength, registration number), to know where it goes.
export async function idmlText(bytes) {
  const list = entries(bytes);
  const stories = list.filter(x => /^Stories\/Story_[^/]+\.xml$/.test(x.name));
  if (!list.some(x => x.name === 'designmap.xml')) throw fail('damaged', 'not an InDesign package (no designmap.xml)');
  const lines = [];
  for (const e of stories) {
    const xml = new TextDecoder().decode(await read(bytes, e));
    let line = '';
    for (const m of xml.matchAll(/<Content>([\s\S]*?)<\/Content>|<Br\s*\/>|<\/ParagraphStyleRange>/g)) {
      if (m[1] !== undefined) line += unxml(m[1]);
      else { if (line.trim()) lines.push(line.replace(/\s+/g, ' ').trim()); line = ''; }
    }
    if (line.trim()) lines.push(line.replace(/\s+/g, ' ').trim());
  }
  return [{ n: 1, text: lines.join('\n'), by: 'text' }];
}

// ---- spreadsheets: a number shown with a date format is a date (Excel's serial: days from 1899-12-30, or from 1904-01-01)
const BUILTIN_DATES = new Set([14, 15, 16, 17, 18, 19, 20, 21, 22, 45, 46, 47]);
const dateCode = code => /[dy]/i.test(String(code || '').replace(/"[^"]*"|\[[^\]]*\]|\\./g, ''));
function dateOf(serial, d1904) {
  const ms = Date.UTC(1899, 11, 30) + Math.round((serial + (d1904 ? 1462 : 0)) * 86400000), t = new Date(ms);
  const p = n => String(n).padStart(2, '0'), day = `${p(t.getUTCDate())}/${p(t.getUTCMonth() + 1)}/${t.getUTCFullYear()}`;
  return serial % 1 ? `${day} ${p(t.getUTCHours())}:${p(t.getUTCMinutes())}` : day;
}
const numText = v => (Number.isInteger(v) ? String(v) : String(+v.toPrecision(12)));
const MAX_ROWS = 5000;                                              // a sheet's first rows: what it is and for which product is there
function sheetPage(n, name, rows) {
  const lines = [name ? `[${name}]` : '', ...rows.slice(0, MAX_ROWS).map(r => r.filter(c => c !== '' && c != null).join(' | ')).filter(Boolean)];
  if (rows.length > MAX_ROWS) lines.push(`… ${rows.length - MAX_ROWS} more rows`);
  return { n, text: lines.filter(Boolean).join('\n'), by: 'sheet' };
}
const attr = (tag, name) => (tag.match(new RegExp(`\\s${name.replace(':', '\\:')}="([^"]*)"`)) || [])[1];

// ---- .xlsx (ECMA-376 SpreadsheetML): the sheets in the workbook's order, each row a line, its cells joined with « | »
export async function xlsxText(bytes) {
  const list = entries(bytes);
  const get = async name => { const e = list.find(x => x.name === name); return e ? new TextDecoder().decode(await read(bytes, e)) : null; };
  const wb = await get('xl/workbook.xml');
  if (wb === null) throw fail('damaged', 'not an Excel workbook (no xl/workbook.xml)');
  const target = {};
  for (const [tag] of ((await get('xl/_rels/workbook.xml.rels')) || '').matchAll(/<Relationship\b[^>]*>/g)) {
    const t = attr(tag, 'Target') || '';
    target[attr(tag, 'Id')] = t.startsWith('/') ? t.slice(1) : `xl/${t.replace(/^\.\//, '')}`;
  }
  const d1904 = /date1904="(1|true)"/.test(wb);
  const shared = [];
  for (const [, si] of ((await get('xl/sharedStrings.xml')) || '').matchAll(/<si>([\s\S]*?)<\/si>/g)) {
    shared.push(unxml([...si.replace(/<rPh\b[\s\S]*?<\/rPh>/g, '').matchAll(/<t(?:\s[^>]*)?>([\s\S]*?)<\/t>/g)].map(m => m[1]).join('')));
  }
  const styles = (await get('xl/styles.xml')) || '', custom = {};
  for (const [tag] of styles.matchAll(/<numFmt\b[^>]*>/g)) custom[+attr(tag, 'numFmtId')] = unxml(attr(tag, 'formatCode') || '');
  const xfs = [...((styles.match(/<cellXfs\b[\s\S]*?<\/cellXfs>/) || [''])[0]).matchAll(/<xf\b[^>]*>/g)].map(([tag]) => +(attr(tag, 'numFmtId') || 0));
  const isDate = s => { const f = xfs[+s || 0] || 0; return BUILTIN_DATES.has(f) || (f >= 164 && dateCode(custom[f])); };
  const pages = [];
  for (const [tag] of wb.matchAll(/<sheet\b[^>]*>/g)) {
    const xml = await get(target[attr(tag, 'r:id')]);
    if (xml === null) continue;
    const rows = [];
    for (const [, row] of xml.matchAll(/<row\b[^>]*>([\s\S]*?)<\/row>/g)) {
      const cells = [];
      for (const [, head, body = ''] of row.matchAll(/<c\b([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g)) {
        const t = attr(head, 't'), s = attr(head, 's'), v = (body.match(/<v>([\s\S]*?)<\/v>/) || [])[1];
        let text = '';
        if (t === 's') text = shared[+v] ?? '';
        else if (t === 'inlineStr') text = unxml([...body.matchAll(/<t(?:\s[^>]*)?>([\s\S]*?)<\/t>/g)].map(m => m[1]).join(''));
        else if (t === 'str' || t === 'e') text = unxml(v || '');
        else if (t === 'b') text = v === '1' ? 'TRUE' : v === '0' ? 'FALSE' : '';
        else if (v !== undefined && v !== '') text = isDate(s) ? dateOf(+v, d1904) : numText(+v);
        cells.push(text.trim());
      }
      rows.push(cells);
    }
    pages.push(sheetPage(pages.length + 1, unxml(attr(tag, 'name') || ''), rows));
  }
  return pages.length ? pages : [{ n: 1, text: '', by: 'sheet' }];
}

// ---- .pptx (ECMA-376 PresentationML): the slides in the presentation's order, each paragraph a line, a table's cells with « | »
function drawingText(xml) {
  const para = p => [...p.matchAll(/<a:t(?:\s[^>]*)?>([\s\S]*?)<\/a:t>|<a:br\b[^>]*\/>/g)].map(m => (m[1] !== undefined ? unxml(m[1]) : '\n')).join('');
  const lines = [];
  for (const [block] of xml.matchAll(/<a:tbl>[\s\S]*?<\/a:tbl>|<a:p\b[^>]*>[\s\S]*?<\/a:p>/g)) {
    if (block.startsWith('<a:tbl>')) for (const [tr] of block.matchAll(/<a:tr\b[\s\S]*?<\/a:tr>/g)) lines.push([...tr.matchAll(/<a:tc\b[\s\S]*?<\/a:tc>/g)].map(([tc]) => [...tc.matchAll(/<a:p\b[^>]*>[\s\S]*?<\/a:p>/g)].map(([p]) => para(p)).join(' ').trim()).join(' | '));
    else lines.push(para(block));
  }
  return lines.map(l => l.replace(/[ \t]+/g, ' ').trim()).filter(Boolean).join('\n');
}
export async function pptxText(bytes) {
  const list = entries(bytes);
  const get = async name => { const e = list.find(x => x.name === name); return e ? new TextDecoder().decode(await read(bytes, e)) : null; };
  const pres = await get('ppt/presentation.xml');
  if (pres === null) throw fail('damaged', 'not a PowerPoint presentation (no ppt/presentation.xml)');
  const target = {};
  for (const [tag] of ((await get('ppt/_rels/presentation.xml.rels')) || '').matchAll(/<Relationship\b[^>]*>/g)) {
    const t = attr(tag, 'Target') || '';
    target[attr(tag, 'Id')] = t.startsWith('/') ? t.slice(1) : `ppt/${t.replace(/^\.\//, '')}`;
  }
  const pages = [];
  for (const [tag] of pres.matchAll(/<p:sldId\b[^>]*>/g)) {
    const xml = await get(target[attr(tag, 'r:id')]);
    if (xml !== null) pages.push({ n: pages.length + 1, text: drawingText(xml), by: 'slides' });
  }
  return pages.length ? pages : [{ n: 1, text: '', by: 'slides' }];
}

// ---- .xls (Excel 97–2003, [MS-XLS] BIFF8 in the «Workbook» stream): its records — the shared strings (SST, continued in CONTINUE
// records, where a string cut in two starts its rest with its own flags), the cell formats (XF, FORMAT) and, for each sheet
// (BOUNDSHEET → its BOF), the cells: LABELSST, LABEL, NUMBER, RK, MULRK, FORMULA (+STRING), BOOLERR
function xlString(b, at, short = false) {                            // → [text, next]
  const cch = short ? b[at] : u16(b, at); at += short ? 1 : 2;
  const flags = b[at++], wide = flags & 1;
  let runs = 0, ext = 0;
  if (flags & 8) { runs = u16(b, at); at += 2; }
  if (flags & 4) { ext = u32(b, at); at += 4; }
  let s = '';
  for (let i = 0; i < cch && at < b.length; i++) { s += String.fromCharCode(wide ? u16(b, at) : b[at]); at += wide ? 2 : 1; }
  return [s, at + runs * 4 + ext];
}
function sstOf(segs) {
  let si = 0, pos = 8;
  const total = u32(segs[0], 4), out = [];
  const more = () => { si++; pos = 0; if (si >= segs.length) throw fail('damaged', 'Excel: the shared strings end early'); };
  const byte = () => { while (pos >= segs[si].length) more(); return segs[si][pos++]; };
  for (let i = 0; i < total; i++) {
    if (pos >= segs[si].length) { if (si + 1 >= segs.length) break; more(); }
    const cch = byte() | (byte() << 8);
    let flags = byte(), runs = 0, ext = 0;
    if (flags & 8) runs = byte() | (byte() << 8);
    if (flags & 4) ext = (byte() | (byte() << 8) | (byte() << 16) | (byte() << 24)) >>> 0;
    let s = '', left = cch;
    while (left > 0) {
      if (pos >= segs[si].length) { more(); flags = segs[si][pos++]; }          // the rest of a string cut by a CONTINUE: its own flags
      const seg = segs[si], wide = flags & 1, room = Math.floor((seg.length - pos) / (wide ? 2 : 1)), n = Math.min(left, room);
      if (!n) { pos = seg.length; continue; }
      for (let k = 0; k < n; k++) { s += String.fromCharCode(wide ? seg[pos] | (seg[pos + 1] << 8) : seg[pos]); pos += wide ? 2 : 1; }
      left -= n;
    }
    for (let skip = runs * 4 + ext; skip > 0;) { if (pos >= segs[si].length) more(); const k = Math.min(skip, segs[si].length - pos); pos += k; skip -= k; }
    out.push(s);
  }
  return out;
}
function rkValue(v) {
  let x;
  if (v & 2) x = (v | 0) >> 2;
  else { const dv = new DataView(new ArrayBuffer(8)); dv.setUint32(0, 0, true); dv.setUint32(4, (v & 0xfffffffc) >>> 0, true); x = dv.getFloat64(0, true); }
  return v & 1 ? x / 100 : x;
}
export function xlsText(bytes) {
  const c = cfb(bytes), wb = c.stream('Workbook') || c.stream('Book');
  if (!wb) throw fail('damaged', 'not an Excel 97–2003 workbook (no Workbook part)');
  const recs = [];
  for (let at = 0; at + 4 <= wb.length;) { const type = u16(wb, at), len = u16(wb, at + 2); recs.push({ type, start: at, data: wb.subarray(at + 4, at + 4 + len) }); at += 4 + len; }
  if (!recs.length || recs[0].type !== 0x0809 || u16(recs[0].data, 0) !== 0x0600) throw fail('unsupported', 'Excel: older than Excel 97 (BIFF5 or before)');
  let sst = [], d1904 = false;
  const xfs = [], formats = {}, sheets = [];
  for (let i = 0; i < recs.length; i++) {
    const r = recs[i];
    if (r.type === 0x000a) break;                                     // the end of the workbook's own part
    if (r.type === 0x00fc) { const segs = [r.data]; while (recs[i + 1]?.type === 0x003c) segs.push(recs[++i].data); sst = sstOf(segs); }
    else if (r.type === 0x00e0) xfs.push(u16(r.data, 2));
    else if (r.type === 0x041e) formats[u16(r.data, 0)] = xlString(r.data, 2)[0];
    else if (r.type === 0x0022) d1904 = u16(r.data, 0) === 1;
    else if (r.type === 0x0085 && r.data[5] === 0) sheets.push({ at: u32(r.data, 0), name: xlString(r.data, 6, true)[0] });
  }
  const isDate = ixfe => { const f = xfs[ixfe] ?? 0; return BUILTIN_DATES.has(f) || (f >= 164 && dateCode(formats[f])); };
  const show = (v, ixfe) => (isDate(ixfe) ? dateOf(v, d1904) : numText(v));
  return sheets.map((sh, k) => {
    let i = recs.findIndex(r => r.start === sh.at);
    const rows = [];
    const put = (row, col, text) => { (rows[row] = rows[row] || [])[col] = String(text).trim(); };
    let pending = null;                                               // a formula whose string result is in the next STRING record
    for (i = i < 0 ? recs.length : i + 1; i < recs.length && recs[i].type !== 0x000a; i++) {
      const { type, data: d } = recs[i];
      if (type === 0x00fd) put(u16(d, 0), u16(d, 2), sst[u32(d, 6)] ?? '');
      else if (type === 0x0204) put(u16(d, 0), u16(d, 2), xlString(d, 6)[0]);
      else if (type === 0x0203) put(u16(d, 0), u16(d, 2), show(new DataView(d.buffer, d.byteOffset + 6, 8).getFloat64(0, true), u16(d, 4)));
      else if (type === 0x027e) put(u16(d, 0), u16(d, 2), show(rkValue(u32(d, 6)), u16(d, 4)));
      else if (type === 0x00bd) { const row = u16(d, 0), first = u16(d, 2); for (let j = 0; 4 + j * 6 + 6 <= d.length - 2; j++) put(row, first + j, show(rkValue(u32(d, 4 + j * 6 + 2)), u16(d, 4 + j * 6))); }
      else if (type === 0x0006) {
        if (u16(d, 12) === 0xffff) {
          if (d[6] === 0) pending = [u16(d, 0), u16(d, 2)];
          else if (d[6] === 1) put(u16(d, 0), u16(d, 2), d[8] ? 'TRUE' : 'FALSE');
        } else put(u16(d, 0), u16(d, 2), show(new DataView(d.buffer, d.byteOffset + 6, 8).getFloat64(0, true), u16(d, 4)));
      } else if (type === 0x0207 && pending) { put(...pending, xlString(d, 0)[0]); pending = null; }
      else if (type === 0x0205 && !d[7]) put(u16(d, 0), u16(d, 2), d[6] ? 'TRUE' : 'FALSE');
    }
    return sheetPage(k + 1, sh.name, rows.filter(Boolean).map(r => Array.from(r, x => x ?? '')));
  });
}

// ---- .ppt (PowerPoint 97–2003, [MS-PPT]): the records of its «PowerPoint Document» part — each slide's text atoms (TextCharsAtom
// in UTF-16, TextBytesAtom in single bytes), from the slides themselves or else from the list of the slides' text; masters and notes
// left out. A paragraph ends with \r, a line inside one with \v.
export function pptText(bytes) {
  const c = cfb(bytes), s = c.stream('PowerPoint Document');
  if (!s) throw fail('damaged', 'not a PowerPoint 97–2003 presentation (no PowerPoint Document part)');
  const slides = [], listed = [];
  const textAt = (type, at, len) => {
    let t = '';
    if (type === 0x0fa0) for (let i = 0; i + 1 < len; i += 2) t += String.fromCharCode(u16(s, at + i));
    else for (let i = 0; i < len; i++) t += String.fromCharCode(s[at + i]);
    return t.replace(/[\r\v]/g, '\n');
  };
  (function walk(from, to, ctx, depth) {
    for (let at = from; at + 8 <= to;) {
      const ver = u16(s, at), type = u16(s, at + 2), len = u32(s, at + 4), body = at + 8, end = Math.min(to, body + len);
      if (type === 0x03ee) { const slide = []; slides.push(slide); walk(body, end, { slide }, depth + 1); }
      else if (type === 0x03f0 || type === 0x03f8 || type === 0x0fc9) { /* notes, masters, handouts */ }
      else if (type === 0x0ff0) { if ((ver >> 4) === 0) walk(body, end, { list: true }, depth + 1); }
      else if (type === 0x03f3 && ctx.list) listed.push([]);
      else if (type === 0x0fa0 || type === 0x0fa8) {
        const t = textAt(type, body, end - body);
        if (ctx.slide) ctx.slide.push(t); else if (ctx.list && listed.length) listed[listed.length - 1].push(t);
      } else if ((ver & 0xf) === 0xf && depth < 32) walk(body, end, ctx, depth + 1);
      at = body + len;
    }
  })(0, s.length, {}, 0);
  const use = slides.some(x => x.length) ? slides : listed;
  const pages = use.map((x, i) => ({ n: i + 1, text: x.join('\n').split('\n').map(l => l.replace(/\s+/g, ' ').trim()).filter(Boolean).join('\n'), by: 'slides' }));
  return pages.length ? pages : [{ n: 1, text: '', by: 'slides' }];
}
