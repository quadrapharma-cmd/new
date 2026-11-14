// Search: a query becomes groups of words, each group with the forms that count as the same word — Arabic with or without
// «ال», English singular or plural, and the other language's words for the same thing (knowledge/vocab/glossary.yaml).
// Every group must be found; a phrase in quotes is looked for as written. Pure JavaScript: the library and the program share it.
import { fold, foldChar } from './fold.js';

const norm = s => fold(s).replace(/\s+/g, ' ').trim();

// term → every way of saying the same thing, in both languages
export function indexGlossary(glossary = []) {
  const index = new Map();
  for (const entry of glossary) {
    const terms = [...(entry.ar || []), ...(entry.en || [])].map(norm).filter(Boolean);
    for (const t of terms) {
      if (!index.has(t)) index.set(t, new Set());
      for (const u of terms) index.get(t).add(u);
    }
  }
  return index;
}

// The forms of one word that count as the same word.
function forms(w) {
  const out = new Set([w]);
  if (/^[؀-ۿ]/.test(w)) {
    for (const p of ['وال', 'بال', 'فال', 'كال', 'لل', 'ال']) if (w.startsWith(p) && w.length - p.length >= 3) out.add(w.slice(p.length));
    if (w.startsWith('و') && w.length >= 5) out.add(w.slice(1));
  } else if (/^[a-z]/.test(w) && w.length > 4) {
    if (w.endsWith('ies')) out.add(w.slice(0, -3) + 'y');
    else if (w.endsWith('es') && /(s|x|ch|sh)es$/.test(w)) out.add(w.slice(0, -2));
    else if (w.endsWith('s') && !w.endsWith('ss')) out.add(w.slice(0, -1));
  }
  return out;
}

// query → { groups: [{ text, alts }], also: [words the other language added] }
export function parseQuery(query, glossaryIndex = new Map()) {
  const groups = [];
  const also = [];
  let q = String(query ?? '');
  for (const m of q.matchAll(/["«“]([^"»”]+)["»”]/g)) {
    const t = norm(m[1]);
    if (t) groups.push({ text: m[1].trim(), alts: [t] });
  }
  q = norm(q.replace(/["«“][^"»”]+["»”]/g, ' ')).replace(/[,،;؛]+/g, ' ');
  if (!q) return { groups, also };
  // the longest glossary terms first, so «active substance» stays one thing
  const words = q.split(' ').filter(Boolean);
  for (let i = 0; i < words.length;) {
    let took = 0;
    for (let n = Math.min(4, words.length - i); n >= 1 && !took; n--) {
      const phrase = words.slice(i, i + n).join(' ');
      // an Arabic word is looked up with and without «ال»
      const lookups = new Set(forms(phrase));
      if (/^[\u0600-\u06FF]/.test(phrase) && !phrase.startsWith('ال')) lookups.add('ال' + phrase);
      const candidates = [...lookups].filter(f => glossaryIndex.has(f));
      if (n > 1 && !candidates.length) continue;
      const alts = new Set(forms(phrase));
      for (const c of candidates) for (const u of glossaryIndex.get(c)) { alts.add(u); for (const f of forms(u)) alts.add(f); if (!forms(phrase).has(u)) also.push(u); }
      groups.push({ text: phrase, alts: [...alts].filter(a => a.length >= 2) });
      took = n;
    }
    i += took || 1;
  }
  return { groups, also: [...new Set(also)] };
}

// Where an alternative sits in a folded text. A short Latin word (API, BE, PK, CEP…) must stand on its own, or «api» would
// be found inside «capillary».
const word = /[a-z0-9]/;
export function indexOfAlt(text, alt, from = 0) {
  if (!/^[a-z0-9.]{1,4}$/.test(alt)) return text.indexOf(alt, from);
  let at = text.indexOf(alt, from);
  while (at >= 0 && (word.test(text[at - 1] || '') || word.test(text[at + alt.length] || ''))) at = text.indexOf(alt, at + 1);
  return at;
}
export const hasAlt = (text, alt) => indexOfAlt(text, alt) >= 0;

// Does a folded text hold every group? → number of hits (0 when one group is missing)
export function matchAll(folded, groups) {
  let score = 0;
  for (const g of groups) {
    let best = 0;
    for (const a of g.alts) {
      let n = 0, at = indexOfAlt(folded, a);
      while (at >= 0 && n < 20) { n++; at = indexOfAlt(folded, a, at + a.length); }
      if (n > best) best = n;
    }
    if (!best) return 0;
    score += best;
  }
  return score;
}

// ---------------------------------------------------------------- inside the source documents
// One page folded once, with where each folded character came from in the original.
export function preparePages(pages) {
  return pages.map(raw => {
    let f = '';
    const map = [];
    let space = true;
    for (let i = 0; i < raw.length; i++) {
      const ch = raw[i];
      if (ch === ' ' || ch === '\n' || ch === '\t' || ch === '\r' || ch === '\f' || ch === ' ') {
        if (!space) { f += ' '; map.push(i); space = true; }
        continue;
      }
      const g = foldChar(ch);
      for (let k = 0; k < g.length; k++) { f += g[k]; map.push(i); }
      space = false;
    }
    return { raw, f, map };
  });
}

const escHtml = s => s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// The words around the first hit, with every hit in them marked.
function snippet(page, groups, width = 230) {
  const { raw, f, map } = page;
  let first = -1;
  for (const g of groups) for (const a of g.alts) { const at = indexOfAlt(f, a); if (at >= 0 && (first < 0 || at < first)) first = at; }
  if (first < 0) return '';
  let from = Math.max(0, map[first] - 90);
  let to = Math.min(raw.length, map[first] + width);
  while (from > 0 && !/\s/.test(raw[from - 1]) && map[first] - from < 120) from--;
  while (to < raw.length && !/\s/.test(raw[to]) && to - map[first] < width + 40) to++;
  // hits inside the window, in original positions
  const marks = [];
  for (const g of groups) for (const a of g.alts) {
    let at = indexOfAlt(f, a);
    while (at >= 0) {
      const s = map[at], e = map[Math.min(at + a.length - 1, map.length - 1)] + 1;
      if (s >= from && e <= to) marks.push([s, e]);
      at = indexOfAlt(f, a, at + a.length);
    }
  }
  marks.sort((x, y) => x[0] - y[0] || y[1] - x[1]);
  let html = '', pos = from;
  for (const [s, e] of marks) {
    if (s < pos) continue;
    html += escHtml(raw.slice(pos, s)) + '<mark>' + escHtml(raw.slice(s, e)) + '</mark>';
    pos = e;
  }
  html += escHtml(raw.slice(pos, to));
  return (from > 0 ? '… ' : '') + html.replace(/\s+/g, ' ').trim() + (to < raw.length ? ' …' : '');
}

// Pages of one prepared document that hold every group, best first.
export function findInPages(prepared, groups, { limit = 8 } = {}) {
  const hits = [];
  prepared.forEach((p, i) => {
    const score = matchAll(p.f, groups);
    if (score) hits.push({ page: i + 1, score });
  });
  hits.sort((a, b) => b.score - a.score || a.page - b.page);
  return { total: hits.length, score: hits.reduce((n, h) => n + h.score, 0),
           pages: hits.slice(0, limit).map(h => ({ ...h, html: snippet(prepared[h.page - 1], groups) })) };
}
