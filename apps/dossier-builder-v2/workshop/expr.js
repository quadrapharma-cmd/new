// The conditions the library's requirements carry («activity == 're_registration'», «'CEP' in api_options», «licence in ['toll',
// 'f_toll']», «column != 'G_LOC' or licence == 'under_licence'»): a small reader of that language — names, strings, numbers, lists,
// ==, !=, in, not in, and, or, not, brackets — evaluated against the dossier's profile. A name the profile lacks is empty (false).
// Never `eval`: the text comes from the library's data, and only this language is understood; anything else is an error.
const TOKEN = /\s*(?:(==|!=|\(|\)|\[|\]|,)|('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")|(-?\d+(?:\.\d+)?)|([A-Za-z_][A-Za-z0-9_]*))/y;

function tokens(text) {
  const out = [];
  TOKEN.lastIndex = 0;
  let at = 0;
  while (at < text.length) {
    if (/^\s*$/.test(text.slice(at))) break;
    TOKEN.lastIndex = at;
    const m = TOKEN.exec(text);
    if (!m) throw new Error(`the condition «${text}» cannot be read at «${text.slice(at, at + 12)}»`);
    at = TOKEN.lastIndex;
    if (m[1]) out.push({ op: m[1] });
    else if (m[2]) out.push({ str: m[2].slice(1, -1).replace(/\\(.)/g, '$1') });
    else if (m[3]) out.push({ num: Number(m[3]) });
    else if (['and', 'or', 'not', 'in', 'True', 'False', 'None', 'true', 'false'].includes(m[4])) out.push({ op: m[4] });
    else out.push({ name: m[4] });
  }
  return out;
}

export function evaluate(text, env = {}) {
  const t = tokens(String(text));
  let i = 0;
  const peek = () => t[i], take = () => t[i++];
  const expect = op => { const x = take(); if (!x || x.op !== op) throw new Error(`«${text}»: «${op}» expected`); };
  const truthy = v => (Array.isArray(v) ? v.length > 0 : !!v);
  function or() { let v = and(); while (peek()?.op === 'or') { take(); const r = and(); v = truthy(v) || truthy(r); } return v; }
  function and() { let v = not(); while (peek()?.op === 'and') { take(); const r = not(); v = truthy(v) && truthy(r); } return v; }
  function not() { if (peek()?.op === 'not') { take(); return !truthy(not()); } return compare(); }
  function compare() {
    const a = value();
    const p = peek();
    if (p?.op === '==' || p?.op === '!=') { take(); const b = value(); const eq = equal(a, b); return p.op === '==' ? eq : !eq; }
    if (p?.op === 'in') { take(); return within(a, value()); }
    if (p?.op === 'not' && t[i + 1]?.op === 'in') { take(); take(); return !within(a, value()); }
    return a;
  }
  function value() {
    const x = take();
    if (!x) throw new Error(`«${text}» ends too soon`);
    if (x.str !== undefined) return x.str;
    if (x.num !== undefined) return x.num;
    if (x.name) return env[x.name] ?? '';
    if (x.op === 'True' || x.op === 'true') return true;
    if (x.op === 'False' || x.op === 'false') return false;
    if (x.op === 'None') return '';
    if (x.op === '(' || x.op === '[') {
      const close = x.op === '(' ? ')' : ']';
      const items = [];
      if (peek()?.op === close) { take(); return items; }
      const first = or();
      if (x.op === '(' && peek()?.op === ')') { take(); return first; }   // a bracketed expression, not a tuple
      items.push(first);
      while (peek()?.op === ',') { take(); if (peek()?.op === close) break; items.push(or()); }
      expect(close);
      return items;
    }
    throw new Error(`«${text}»: unexpected «${x.op}»`);
  }
  const v = or();
  if (i < t.length) throw new Error(`«${text}»: unexpected words after the condition`);
  return truthy(v);
}

const equal = (a, b) => (Array.isArray(a) || Array.isArray(b) ? JSON.stringify(a) === JSON.stringify(b) : String(a) === String(b));
function within(a, b) {
  if (Array.isArray(b)) return b.some(x => equal(a, x));
  if (typeof b === 'string') return typeof a === 'string' && a !== '' && b.includes(a);
  return false;
}
