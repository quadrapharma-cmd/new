// A PDF page's text in reading order, from pdf.js's text items. pdf.js hands the items in the order they are drawn: Arabic comes
// glyph by glyph from left to right (a word's last letter first), in its presentation forms («ﺔ», «ﻸ»), and with no spaces where
// the file has none. Here the items are put on their lines, a space goes where the gap between two items is a word's, each line is
// put back in reading order (a right-to-left line read from the right, its numbers and Latin words kept left to right; a
// left-to-right line with its Arabic words turned), and the presentation forms become ordinary letters.
const RTL_LETTER = /[֐-׿؀-ٟٮ-ۓە-ۯۺ-ۿݐ-ݿࢠ-ࣿיִ-﷿ﹰ-ﻼ]/;
const LTR_LETTER = /[A-Za-zÀ-ɏͰ-ϿЀ-ӿ]/;
const DIGIT = /[0-9٠-٩۰-۹]/;
const FORMS = /[ﬀ-ﬆﭐ-﷿ﹰ-﻿]/g;      // Latin ligatures and Arabic presentation forms

// R: an Arabic or Hebrew letter; L: a Latin (Greek, Cyrillic) letter or a digit — numbers read left to right inside Arabic too;
// N: neither (spaces, punctuation), which takes the direction of what is around it.
function cls(s) {
  for (const ch of s) {
    if (RTL_LETTER.test(ch)) return 'R';
    if (LTR_LETTER.test(ch) || DIGIT.test(ch)) return 'L';
  }
  return 'N';
}

// Turns, in place, every run of tokens of class c (with the neutral tokens between two of them).
function turnRuns(tokens, c) {
  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].c !== c) continue;
    let end = i;
    for (let j = i + 1; j < tokens.length; j++) {
      if (tokens[j].c === c) end = j;
      else if (tokens[j].c !== 'N') break;
    }
    const run = tokens.slice(i, end + 1).reverse();
    tokens.splice(i, run.length, ...run);
    i = end;
  }
}

export function lineText(items) {
  const sorted = [...items].sort((a, b) => a.x - b.x);
  const tokens = [];
  sorted.forEach((it, k) => {
    if (k) {
      const prev = sorted[k - 1];
      const gap = it.x - (prev.x + prev.w);
      if (gap > 0.2 * Math.max(prev.h, it.h, 1) && !/\s$/.test(prev.s) && !/^\s/.test(it.s)) tokens.push({ s: ' ', c: 'N' });
    }
    tokens.push({ s: it.s, c: cls(it.s) });
  });
  let r = 0, l = 0;
  for (const t of tokens) for (const ch of t.s) { if (RTL_LETTER.test(ch)) r++; else if (LTR_LETTER.test(ch)) l++; }
  if (r > l) { tokens.reverse(); turnRuns(tokens, 'L'); }
  else if (r) turnRuns(tokens, 'R');
  return tokens.map(t => t.s).join('').replace(FORMS, ch => ch.normalize('NFKC')).replace(/\s+/g, ' ').trim();
}

// pdf.js's getTextContent() of one page → its text, a line per line, top to bottom.
export function pageTextOf(content) {
  const items = [];
  for (const it of content.items) {
    if (!it.str) continue;
    const [a, b, , d, x, y] = it.transform;
    items.push({ s: it.str, x, y, w: it.width || 0, h: it.height || Math.hypot(b, d) || Math.abs(a) || 1 });
  }
  items.sort((p, q) => q.y - p.y || p.x - q.x);
  const lines = [];
  for (const it of items) {
    const line = lines[lines.length - 1];
    if (line && Math.abs(line.y - it.y) < 0.5 * Math.max(line.h, it.h)) line.items.push(it);
    else lines.push({ y: it.y, h: it.h, items: [it] });
  }
  return lines.map(l => lineText(l.items)).filter(Boolean).join('\n');
}
