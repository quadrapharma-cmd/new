// One way to compare Arabic and English text, for the search, the checks and the tools.
// Arabic and English text folded for search: no diacritics or tatweel, one form of alef / ya / ta marbuta, Western digits.
export function fold(text) {
  return String(text ?? '')
    .normalize('NFKD')
    .replace(/[ً-ٰٟۖ-ۭـ]/g, '')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[أإآٱ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه').replace(/ؤ/g, 'و').replace(/ئ/g, 'ي')
    .replace(/[٠-٩]/g, d => String(d.charCodeAt(0) - 0x660))
    .replace(/[۰-۹]/g, d => String(d.charCodeAt(0) - 0x6f0))
    .toLowerCase();
}

// A character's folded form, remembered: folding a long text one character at a time keeps track of where each folded
// character came from (for highlighting what was found in the original text).
const one = new Map();
export function foldChar(ch) {
  let f = one.get(ch);
  if (f === undefined) { f = fold(ch); one.set(ch, f); }
  return f;
}
