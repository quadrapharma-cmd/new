// Party name normalisation and merge suggestions. The engine NEVER merges parties: it proposes clusters with a
// confidence and an `identitySensitive` flag, and a person (or the importer, for `safe` clusters only) decides.

const TITLE_ABBR = { 'أ': 'ustaz', 'ا': 'ustaz', 'إ': 'ustaz', 'آ': 'ustaz', 'د': 'dr', 'ك': 'captain', 'م': 'eng' };
const TITLE_WORDS = [
  ['dr', ['الدكتور', 'دكتور', 'الدكتورة', 'دكتورة']],
  ['ustaz', ['الأستاذ', 'الأستاذة', 'الاستاذ', 'الاستاذة', 'الاستاذه', 'أستاذ', 'أستاذة', 'استاذ', 'استاذة', 'استاذه']],
  ['captain', ['الكابتن', 'كابتن']],
  ['eng', ['المهندس', 'المهندسة', 'مهندس', 'مهندسة']],
  ['mr', ['السيد', 'السيدة', 'الحاج', 'الحاجة']],
];
const ARABIC_INDIC = '٠١٢٣٤٥٦٧٨٩';
const EXTENDED = '۰۱۲۳۴۵۶۷۸۹';
const ABBR_RE = /^\s*([أاإآدكم])\s*[/.\\]\s*/;

/** Remove one leading title; returns { title, rest } (title: 'dr' | 'ustaz' | 'captain' | 'eng' | 'mr' | null). */
export function stripTitle(input) {
  let s = String(input ?? '');
  let m = ABBR_RE.exec(s);
  if (m) return { title: TITLE_ABBR[m[1]], rest: s.slice(m[0].length).trim() };
  s = s.trim();
  for (const [title, words] of TITLE_WORDS) {
    for (const w of words) {
      if (s.startsWith(`${w} `)) return { title, rest: s.slice(w.length).trim() };
    }
  }
  return { title: null, rest: s };
}

function baseClean(input) {
  return String(input ?? '')
    .replace(/[٠-٩۰-۹]/g, (c) => String(ARABIC_INDIC.indexOf(c) >= 0 ? ARABIC_INDIC.indexOf(c) : EXTENDED.indexOf(c)))
    .replace(/[(（[][^)）\]]*[)）\]]/g, ' ')
    .replace(/[ً-ٰٟۖ-ۭـ]/g, '');
}

/**
 * Canonical comparison key of a party name: notes in brackets, diacritics and tatweel removed; leading titles
 * (أ/ د/ ك/ م/ and the spelled-out forms) stripped; hamza forms, yaa, taa-marbuta unified; "عبد ال..." joined;
 * punctuation to spaces; lower-cased Latin. Idempotent.
 */
export function normalizeName(input) {
  let s = baseClean(input);
  for (let i = 0; i < 3; i++) {
    const { title, rest } = stripTitle(s);
    if (!title) break;
    s = rest;
  }
  s = s
    .replace(/[أإآٱ]/g, 'ا')
    .replace(/[ىیی]/g, 'ي')
    .replace(/ک/g, 'ك')
    .replace(/ة/g, 'ه')
    .replace(/[ؤئء]/g, '')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
    .replace(/(^| )عبد ال/g, '$1عبدال')
    .replace(/\s+/g, ' ');
  return s;
}

const ORG_WORDS = new Set(['بنك', 'مصرف', 'شركه', 'موسسه', 'مصنع', 'مكتب', 'مجموعه']);
const LEVEL = { high: 3, medium: 2, low: 1 };
const SCORE = { high: 0.95, medium: 0.7, low: 0.4 };
const NAME_LEVELS = ['low', 'medium', 'high'];

function prep(p) {
  const raw = p.name ?? '';
  const { title } = stripTitle(baseClean(raw));
  const core = normalizeName(raw);
  const tokens = core ? core.split(' ') : [];
  const orgWord = tokens.some((t) => ORG_WORDS.has(t));
  const looseTokens = tokens.filter((t) => !ORG_WORDS.has(t));
  const loose = looseTokens.length ? looseTokens.join(' ') : core;
  const keys = new Set([core, ...(p.aliases || []).map(normalizeName)].filter(Boolean));
  const isOrg = p.kind === 'bank' || p.kind === 'government' || orgWord;
  return { id: p.id, name: raw, kind: p.kind || 'other', title, core, tokens, tokenSet: new Set(tokens), loose, keys, isOrg, lineCount: p.lineCount || 0 };
}

const isSubset = (a, b) => a.tokens.length > 0 && a.tokens.every((t) => b.tokenSet.has(t));

function edgeOf(a, b) {
  if (!a.core || !b.core) return null;
  const alias = [...a.keys].some((k) => b.keys.has(k));
  if (a.core === b.core) return { level: 'high', reason: 'same-normalized' };
  if (alias) return { level: 'high', reason: 'alias' };
  if (a.loose && a.loose === b.loose && (a.isOrg || b.isOrg)) return { level: 'high', reason: 'same-without-org-words' };
  if (a.tokens.length > 1 && a.tokens.length === b.tokens.length && isSubset(a, b)) return { level: 'high', reason: 'same-tokens' };
  const [s, l] = a.tokens.length <= b.tokens.length ? [a, b] : [b, a];
  if (isSubset(s, l)) {
    const n = s.tokens.length;
    const org = a.isOrg && b.isOrg;
    if (n >= 3 || (org && n >= 2)) return { level: 'medium', reason: 'name-contained' };
    if (n === 2) return { level: 'medium', reason: 'name-contained', sensitive: true };
    return { level: 'low', reason: 'first-name-only', sensitive: true };
  }
  return null;
}

function memberFlags(members) {
  const reasons = new Set();
  let sensitive = false;
  const titles = new Set(members.map((m) => m.title).filter(Boolean));
  if (titles.size > 1) {
    sensitive = true;
    reasons.add('title-conflict');
  }
  const kinds = new Set(members.map((m) => m.kind).filter((k) => k && k !== 'other'));
  if (kinds.size > 1) {
    sensitive = true;
    reasons.add('kind-differs');
  }
  const persons = members.filter((m) => !m.isOrg && m.tokens.length > 1);
  outer: for (let a = 0; a < persons.length; a++) {
    for (let b = a + 1; b < persons.length; b++) {
      const x = persons[a];
      const y = persons[b];
      if (x.tokens[0] === y.tokens[0] && !isSubset(x, y) && !isSubset(y, x)) {
        sensitive = true;
        reasons.add('first-name-collision');
        break outer;
      }
    }
  }
  return { sensitive, reasons };
}

/**
 * suggestMerges(parties, { includeInactive })
 * parties: array or {id: doc} of { id, name, kind, aliases, active, mergedInto, lineCount }.
 * Returns clusters [{ key, members: [{ id, name, normalized, title, kind, lineCount }], confidence: 'high'|'medium'|'low',
 * score, reasons, identitySensitive, safe, survivorId }], best first.
 *  high/medium clusters are the connected groups of same-name / contained-name spellings. A LONE FIRST NAME that
 *  merely appears inside longer names produces a separate 'low' cluster (lone name + every name containing it),
 *  always identity-sensitive; it may overlap a stronger cluster, so process tiers best-first and skip merged members.
 *  identitySensitive: titles conflict (e.g. أ/ vs ك/), party kinds differ, a two-token or lone first name is the
 *    only link, or two members share a first name without being spellings of one person.
 *  safe: high confidence and not identity-sensitive: the only clusters an importer may merge without asking.
 */
export function suggestMerges(parties, opts = {}) {
  const list = (Array.isArray(parties) ? parties : Object.entries(parties || {}).map(([id, p]) => ({ ...p, id: p.id ?? id })))
    .filter((p) => p && (isNilish(p.mergedInto)) && (opts.includeInactive || p.active !== false));
  const items = list.map(prep).filter((x) => x.core);
  const parent = items.map((_, i) => i);
  const find = (i) => (parent[i] === i ? i : (parent[i] = find(parent[i])));
  const strong = [];
  const lone = new Map(); // index of a lone first name -> indexes of longer names containing it
  for (let i = 0; i < items.length; i++) {
    for (let j = i + 1; j < items.length; j++) {
      const e = edgeOf(items[i], items[j]);
      if (!e) continue;
      if (e.level === 'low') {
        const [a, b] = items[i].tokens.length <= items[j].tokens.length ? [i, j] : [j, i];
        if (!lone.has(a)) lone.set(a, new Set());
        lone.get(a).add(b);
      } else {
        strong.push({ i, j, ...e });
        parent[find(i)] = find(j);
      }
    }
  }
  const groups = new Map();
  items.forEach((_, i) => {
    const r = find(i);
    if (!groups.has(r)) groups.set(r, []);
    groups.get(r).push(i);
  });
  const finish = (idxs, confidence, baseReasons, extraSensitive) => {
    const members = idxs.map((i) => items[i]);
    const flags = memberFlags(members);
    const reasons = new Set([...baseReasons, ...flags.reasons]);
    const sensitive = extraSensitive || flags.sensitive;
    members.sort((p, q) => q.lineCount - p.lineCount || q.name.length - p.name.length || (p.id < q.id ? -1 : 1));
    return {
      key: members.map((m) => m.id).sort().join('+'),
      members: members.map((m) => ({ id: m.id, name: m.name, normalized: m.core, title: m.title, kind: m.kind, lineCount: m.lineCount })),
      confidence,
      score: SCORE[confidence],
      reasons: [...reasons],
      identitySensitive: sensitive,
      safe: confidence === 'high' && !sensitive,
      survivorId: members[0].id,
    };
  };
  const clusters = [];
  for (const idxs of groups.values()) {
    if (idxs.length < 2) continue;
    const set = new Set(idxs);
    const es = strong.filter((e) => set.has(e.i));
    const confidence = NAME_LEVELS[Math.min(...es.map((e) => LEVEL[e.level])) - 1];
    clusters.push(finish(idxs, confidence, es.map((e) => e.reason), es.some((e) => e.sensitive)));
  }
  const seen = new Set();
  for (const [a, bs] of lone) {
    const idxs = [a, ...bs];
    const roots = new Set(idxs.map(find));
    if (roots.size === 1) continue; // already one strong cluster
    const key = idxs.map((i) => items[i].id).sort().join('+');
    if (seen.has(key)) continue;
    seen.add(key);
    clusters.push(finish(idxs, 'low', ['first-name-only'], true));
  }
  clusters.sort((p, q) => LEVEL[q.confidence] - LEVEL[p.confidence] || q.members.length - p.members.length || (p.key < q.key ? -1 : 1));
  return clusters;
}

function isNilish(v) {
  return v === null || v === undefined || v === '';
}
