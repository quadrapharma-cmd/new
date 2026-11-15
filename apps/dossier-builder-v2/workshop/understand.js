// Understanding a dossier's documents (Part 2, steps 2.3–2.4): what each document is and where it goes on the board, what it says
// (facts with the words on their page), and where a file that holds several documents is to be cut. The rules decide first: the
// preparation's own kinds (prep/doctype.js, tested on real scans) and the library's recognition words for every place; Claude,
// where the viewer gave it, answers what the rules cannot, and every answer is checked (a place must exist on the board, a fact's
// words must be on its page). What neither can settle goes to «needs you».
import { fold } from '../core/fold.js';
import { typeOf, TYPES, UNKNOWN } from '../prep/doctype.js';
import { factsOf } from '../prep/facts.js';

const titleOf = text => String(text || '').split('\n').map(l => l.trim()).filter(Boolean).slice(0, 12).join('\n');
const SHORT = 4;                                         // a recognition word this short («gmp», «cpp», «bp») counts only in a title

function hits(text, word) {
  const w = fold(word).trim();
  if (!w) return false;
  const esc = w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\s+/g, '\\s+');
  return new RegExp(`(^|[^\\p{L}\\p{N}])${esc}($|[^\\p{L}\\p{N}])`, 'u').test(text);
}

// The places the library's words point to, best first: [{place, score, words}] (a title counts three times as much as the body;
// a phrase more than a single word; a short word only in a title).
export function placesByWords(pages, recognition = {}, setPrefix = 'EG-EDA/') {
  const title = fold(titleOf(pages[0]?.text));
  const head = fold(pages.slice(0, 2).map(p => p.text || '').join('\n'));
  const out = [];
  for (const [short, words] of Object.entries(recognition)) {
    let score = 0;
    const found = [];
    for (const w of words) {
      const n = fold(w).trim().split(/\s+/).length, len = fold(w).replace(/\s/g, '').length;
      if (hits(title, w)) { score += 3 * n + (n > 1 ? 1 : 0); found.push(w); }
      else if (len > SHORT && n > 1 && hits(head, w)) { score += n; found.push(w); }
    }
    if (score) out.push({ place: short.includes('/') ? short : setPrefix + short, score, words: found });   // a key is a place's id, or Egypt's short id
  }
  return out.sort((a, b) => b.score - a.score);
}

// Places the library's words cannot tell apart, told apart by what the paper is about: a GMP certificate of an active substance's
// maker goes to 1.2.4.2, of the product's maker to 1.2.4.1; a stability paper about the active substance to 3.2.S.7.
const API = /\b(api|apis|active (pharmaceutical )?(ingredient|substance)s?|drug substance)\b|ماده فعاله|المواد الفعاله/;
// (by the places' short ids, so the same two places of the common modules are told apart in every country's dossier)
const TIES = [
  { places: ['M1-37', 'M1-38'], pick: head => (API.test(head) ? 'M1-38' : 'M1-37') },
  { places: ['P-16', 'S-14'], pick: head => (API.test(head) ? 'S-14' : 'P-16') },
];
const shortOf = id => String(id || '').split('/').pop();

// What a document is and where it goes, by the rules: {type, type_ar, doctype, place, sure, by: 'rules', words?}
export function typeAndPlace(pages, { recognition = {}, places = null } = {}) {
  const t = typeOf(pages);
  const allowed = id => !places || places.has(id);
  // the same place in the country's own sets: Module 2–5 places carry the same short id in every country (EG-EDA/P-09, ICH/P-09)
  const twin = id => (places ? [...places].find(x => shortOf(x) === shortOf(id)) || null : null);
  const typed = t !== UNKNOWN ? { type: t.type, type_ar: t.ar, doctype: t.doctype } : null;
  if (typed) {
    const place = (t.places || []).find(allowed) || (t.places || []).map(twin).find(Boolean) || null;
    if (place || !places) return { ...typed, place, sure: !!place, by: 'rules' };
  }
  // not a type the rules know, or its places are not in this dossier: the words that recognise the places of this country's dossier
  const ranked = placesByWords(pages, recognition).filter(r => allowed(r.place));
  const [first, second] = ranked;
  const tie = first && second && first.score === second.score && TIES.find(t => t.places.includes(shortOf(first.place)) && t.places.includes(shortOf(second.place)));
  if (tie) {
    const head = fold(pages.slice(0, 2).map(p => p.text || '').join('\n'));
    const pick = [first.place, second.place].find(x => shortOf(x) === tie.pick(head));
    if (pick && allowed(pick)) return { type: 'place', type_ar: null, doctype: null, ...typed, place: pick, sure: first.score >= 4, by: 'rules', words: first.words };
  }
  const [best, next] = ranked;
  if (best && best.score >= 3 && (!next || best.score >= next.score + 2)) {
    return { type: 'place', type_ar: null, doctype: null, ...typed, place: best.place, sure: best.score >= 4, by: 'rules', words: best.words };
  }
  return { type: UNKNOWN.type, type_ar: UNKNOWN.ar, doctype: null, ...typed, place: best?.place && allowed(best.place) ? best.place : null, sure: false, by: 'rules',
           ...(best ? { words: best.words, maybe: ranked.slice(0, 3).map(r => r.place) } : {}) };
}

// Where a file holding several documents is to be cut: a page whose title names a kind other than the one being read starts a
// new document; a page of the same kind starts one only when it says it is a first page («Page 1 of», «صفحة 1 من»). Pages that
// name nothing continue the document before them. → [{from, to, type, place, sure}] (pages numbered from 1); one segment = no cut.
const FIRST_PAGE = /\bpage\s*1\s*(of|\/)\s*\d+|صفحه\s*(1|١)\s*(من|\/)\s*[\d٠-٩]+/i;
export function segmentsOf(pages, opts = {}) {
  const segs = [];
  let cur = null;
  pages.forEach((p, i) => {
    const one = [p];
    const t = typeOf(one);
    const words = t === UNKNOWN ? typeAndPlace(one, opts) : null;
    const kind = t !== UNKNOWN ? t.type : words?.sure ? words.place : null;
    const firstPage = FIRST_PAGE.test(fold(titleOf(p.text)) + '\n' + fold(String(p.text || '').slice(-400)));
    if (!cur || (kind && (kind !== cur.kind || firstPage))) {
      cur = { from: i + 1, to: i + 1, kind, starts: [kind ? 'title' : 'start'] };
      segs.push(cur);
    } else cur.to = i + 1;
  });
  // one nearly empty unknown page at the front (a cover sheet, a blank page) joins the document after it
  const letters = s => (String(s || '').match(/[\p{L}\p{N}]/gu) || []).length;
  if (segs.length > 1 && !segs[0].kind && segs[0].to === segs[0].from && letters(pages[0].text) < 200) { segs[1].from = segs[0].from; segs.shift(); }
  return segs.map(s => ({ from: s.from, to: s.to, kind: s.kind, sure: segs.length === 1 || !!s.kind }));
}

// Facts by the rules, each with its page and words (prep/facts.js), for the whole document.
export const factsByRules = pages => factsOf(pages).map(f => ({ ...f, by: 'rules' }));

// Is this quote on this page? (as record_fact checks: letters and digits folded, spaces ignored)
export function onPage(pages, n, quote) {
  const page = pages.find(p => p.n === n);
  if (!page || !quote) return false;
  const squeeze = s => fold(String(s)).replace(/[\s‎‏⁦-⁩]+/g, '');
  return squeeze(page.text).includes(squeeze(quote));
}

export { TYPES, UNKNOWN };
