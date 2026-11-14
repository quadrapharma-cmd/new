// The documents the workshop writes, kept as a small model of paragraphs and tables, then written as a Word file (.docx, Office Open
// XML that Word, LibreOffice and WordCraft open) and shown as a page in the workshop. Arabic runs right to left, English left to right
// in the same paragraph; what the program does not know yet is a highlighted gap «[ … ]» the person fills in Word.
//   model: {title, rtl, draft, blocks: [{t: 'p', parts, bold?, size?, align?, rtl?, bullet?} | {t: 'table', head, rows, rtl?} | {t: 'gap'}]}
//   part: a string, or {gap: 'what is missing'}, or {value, field} (a value the program filled, from the dossier)
import { zipOf } from './zipw.js';

const AR = /[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]/;
const xml = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const html = xml;

// A text cut into runs of one direction: Arabic words (and the spaces and signs between them) right to left, the rest left to right.
function runsOf(text) {
  const out = [];
  for (const piece of String(text).split(/([؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿][^A-Za-z0-9]*)/)) {
    if (!piece) continue;
    const rtl = AR.test(piece);
    const last = out[out.length - 1];
    if (last && last.rtl === rtl) last.text += piece; else out.push({ text: piece, rtl });
  }
  return out;
}

function runXml(text, { bold, size, gap, filled }) {
  return runsOf(text).map(r => {
    const pr = ['<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Arial"/>', bold ? '<w:b/><w:bCs/>' : '', gap ? '<w:highlight w:val="yellow"/>' : '',
                filled ? '<w:color w:val="1F4E79"/>' : '', size ? `<w:sz w:val="${size * 2}"/><w:szCs w:val="${size * 2}"/>` : '', r.rtl ? '<w:rtl/>' : ''].join('');
    return `<w:r><w:rPr>${pr}</w:rPr><w:t xml:space="preserve">${xml(r.text)}</w:t></w:r>`;
  }).join('');
}
const partsOf = parts => [parts].flat().filter(p => p !== null && p !== undefined && p !== '');
const plain = p => (typeof p === 'string' ? p : p.gap ? `[${p.gap}]` : String(p.value ?? ''));
const isRtl = (b, model) => b.rtl ?? (model.rtl && partsOf(b.parts).map(plain).join('').match(AR) !== null);

function paraXml(b, model) {
  const rtl = isRtl(b, model);
  const jc = b.align === 'center' ? 'center' : b.align === 'start' ? (rtl ? 'right' : 'left') : rtl ? 'right' : 'left';
  const ppr = `<w:pPr>${rtl ? '<w:bidi/>' : ''}<w:spacing w:after="${b.tight ? 40 : 120}"/>${b.bullet ? '<w:ind w:start="360" w:hanging="240"/>' : ''}<w:jc w:val="${jc}"/></w:pPr>`;
  const lead = b.bullet ? runXml('• ', {}) : '';
  const body = partsOf(b.parts).map(p => runXml(plain(p), { bold: b.bold, size: b.size, gap: typeof p === 'object' && !!p.gap, filled: typeof p === 'object' && 'value' in p })).join('');
  return `<w:p>${ppr}${lead}${body}</w:p>`;
}

function tableXml(b, model) {
  const cols = Math.max(b.head?.length || 0, ...b.rows.map(r => r.length));
  const rtl = b.rtl ?? model.rtl;
  const border = '<w:top w:val="single" w:sz="4" w:color="999999"/><w:bottom w:val="single" w:sz="4" w:color="999999"/><w:start w:val="single" w:sz="4" w:color="999999"/><w:end w:val="single" w:sz="4" w:color="999999"/><w:insideH w:val="single" w:sz="4" w:color="999999"/><w:insideV w:val="single" w:sz="4" w:color="999999"/>';
  const cell = (parts, head) => `<w:tc><w:tcPr><w:tcW w:w="${Math.floor(5000 / cols)}" w:type="pct"/>${head ? '<w:shd w:val="clear" w:color="auto" w:fill="E7EEF0"/>' : ''}</w:tcPr>${paraXml({ t: 'p', parts, bold: head, tight: true }, model)}</w:tc>`;
  const row = (r, head) => `<w:tr>${Array.from({ length: cols }, (_, i) => cell(r[i] ?? '', head)).join('')}</w:tr>`;
  return `<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/>${rtl ? '<w:bidiVisual/>' : ''}<w:tblBorders>${border}</w:tblBorders><w:tblCellMar><w:start w:w="80" w:type="dxa"/><w:end w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>${'<w:gridCol/>'.repeat(cols)}</w:tblGrid>${b.head ? row(b.head, true) : ''}${b.rows.map(r => row(r, false)).join('')}</w:tbl>${paraXml({ t: 'p', parts: '' }, model)}`;
}

export async function docxOf(model) {
  const blocks = [];
  if (model.draft) blocks.push(paraXml({ t: 'p', parts: 'مسودة من البرنامج — تتراجع وتتطبع على ورق الشركة وتتمضي وتتختم  ·  DRAFT — unsigned', size: 9, align: 'center' }, { rtl: true }));
  for (const b of model.blocks) blocks.push(b.t === 'table' ? tableXml(b, model) : b.t === 'gap' ? paraXml({ t: 'p', parts: '' }, model) : paraXml(b, model));
  const land = model.landscape;
  const sect = `<w:sectPr><w:pgSz w:w="${land ? 16838 : 11906}" w:h="${land ? 11906 : 16838}"${land ? ' w:orient="landscape"' : ''}/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="567" w:footer="567" w:gutter="0"/></w:sectPr>`;   // each paragraph carries its own direction; a bidi section would turn English tables round
  const doc = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>${blocks.join('')}${sect}</w:body></w:document>`;
  const styles = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Arial" w:eastAsia="Calibri"/><w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="en-GB" w:bidi="ar-EG"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="264" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>`;
  const now = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
  const core = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>${xml(model.title || '')}</dc:title><dc:creator>Dossier Builder</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">${now}</dcterms:created></cp:coreProperties>`;
  const enc = s => new TextEncoder().encode(s);
  return zipOf([
    { name: '[Content_Types].xml', bytes: enc(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>`) },
    { name: '_rels/.rels', bytes: enc(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>`) },
    { name: 'word/_rels/document.xml.rels', bytes: enc(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`) },
    { name: 'word/document.xml', bytes: enc(doc) },
    { name: 'word/styles.xml', bytes: enc(styles) },
    { name: 'docProps/core.xml', bytes: enc(core) },
  ]);
}

// The same model as HTML, for the workshop's own view of a draft (the gaps marked, the filled values shown as filled).
export function htmlOf(model) {
  const part = p => (typeof p === 'string' ? html(p) : p.gap ? `<mark class="gap">[${html(p.gap)}]</mark>` : `<span class="filled">${html(p.value)}</span>`);
  const parts = ps => partsOf(ps).map(part).join('');
  const out = [];
  if (model.draft) out.push('<p class="draft-note">مسودة من البرنامج — تتراجع وتتطبع على ورق الشركة وتتمضي وتتختم</p>');
  for (const b of model.blocks) {
    if (b.t === 'gap') { out.push('<p>&nbsp;</p>'); continue; }
    if (b.t === 'table') {
      const head = b.head ? `<thead><tr>${b.head.map(h => `<th>${parts(h)}</th>`).join('')}</tr></thead>` : '';
      out.push(`<table dir="${(b.rtl ?? model.rtl) ? 'rtl' : 'ltr'}">${head}<tbody>${b.rows.map(r => `<tr>${r.map(c => `<td dir="auto">${parts(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>`);
      continue;
    }
    const style = [b.bold ? 'font-weight:600' : '', b.size ? `font-size:${b.size}pt` : '', b.align === 'center' ? 'text-align:center' : ''].filter(Boolean).join(';');
    out.push(`<p dir="${isRtl(b, model) ? 'rtl' : 'ltr'}"${style ? ` style="${style}"` : ''}>${b.bullet ? '• ' : ''}${parts(b.parts)}</p>`);
  }
  return `<div class="doc-page" dir="${model.rtl ? 'rtl' : 'ltr'}">${out.join('\n')}</div>`;
}

// What the model still lacks: the gaps, each once.
export const gapsOf = model => [...new Set(model.blocks.flatMap(b => (b.t === 'table' ? [...(b.head || []), ...b.rows.flat()] : [b.parts]).flatMap(partsOf))
  .filter(p => typeof p === 'object' && p.gap).map(p => p.gap))];
