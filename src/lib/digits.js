// Digit helpers: input accepts Western, Arabic-Indic and Persian digits; display is Western unless the user chose Arabic.
const ARABIC_INDIC = '٠١٢٣٤٥٦٧٨٩';
const EXTENDED = '۰۱۲۳۴۵۶۷۸۹';

let mode = 'western';
export const getDigitsMode = () => mode;
export function setDigitsMode(m) {
  mode = m === 'arabic' ? 'arabic' : 'western';
  return mode;
}

/** ٠-٩ and ۰-۹ -> 0-9 (other characters untouched). */
export function toWesternDigits(input) {
  return String(input ?? '').replace(/[٠-٩۰-۹]/g, (c) => {
    const i = ARABIC_INDIC.indexOf(c);
    return String(i >= 0 ? i : EXTENDED.indexOf(c));
  });
}

/** 0-9 -> ٠-٩; with separators=true also . -> ٫ and , -> ٬ (for formatted numbers). */
export function toArabicDigits(input, { separators = true } = {}) {
  let s = String(input ?? '').replace(/\d/g, (d) => ARABIC_INDIC[Number(d)]);
  if (separators) s = s.replace(/\./g, '٫').replace(/,/g, '٬');
  return s;
}

/** Apply the user's display preference (mode defaults to the global one). */
export function localizeDigits(input, m = mode) {
  return m === 'arabic' ? toArabicDigits(input) : String(input ?? '');
}

/**
 * Normalise typed numeric text to plain ASCII: digits, "." decimal, no thousands separators, "-" sign.
 * Accepts ٫ (decimal), ٬ and "," and "،" (thousands), spaces incl. NBSP, U+2212 minus.
 * Returns '' for empty input. Does not validate.
 */
export function normalizeNumericInput(input) {
  return toWesternDigits(input)
    .replace(/[−‒–]/g, '-')
    .replace(/٫/g, '.')
    .replace(/[٬,،\s  ]/g, '')
    .trim();
}
