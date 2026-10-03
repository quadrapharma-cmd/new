// Per-viewer conveniences in localStorage (theme, selected year). Every access is wrapped: storage may be blocked or empty.
const PREFIX = 'strifa.';

export function getPref(key, fallback = null) {
  try {
    const v = window.localStorage.getItem(PREFIX + key);
    return v == null ? fallback : v;
  } catch {
    return fallback;
  }
}
export function setPref(key, value) {
  try {
    if (value == null) window.localStorage.removeItem(PREFIX + key);
    else window.localStorage.setItem(PREFIX + key, String(value));
  } catch {
    /* storage unavailable: the preference just does not persist */
  }
}
