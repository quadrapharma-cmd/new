// How much of a page's truth a reading holds. A fact counts when it appears in the reading once both are folded the same way:
// no spaces, Arabic letter shapes unified (أإآٱ → ا، ى → ي، ة → ه), no diacritics or tatweel, no direction marks, and the
// digits of every script read as 0–9 — so a reader is not punished for spacing or for how a digit is drawn, only for missing it.
const DIGITS = { '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
                 '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9' };

export function fold(s) {
  return String(s ?? '').normalize('NFKC')
    .replace(/[٠-٩۰-۹]/g, d => DIGITS[d])
    .replace(/[ً-ْٰـ‎‏‪-‮⁦-⁩]/g, '')
    .replace(/[أإآٱ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه')
    .toLowerCase().replace(/\s+/g, '');
}

export function score(facts, text) {
  const t = fold(text);
  const found = facts.filter(f => t.includes(fold(f)));
  return { found: found.length, of: facts.length, pct: Math.round((100 * found.length) / facts.length),
           missed: facts.filter(f => !found.includes(f)) };
}
