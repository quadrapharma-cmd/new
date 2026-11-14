// The library: browse and search everything the program knows, each entry with the guideline it comes from.
// Runs the same in the claude.ai artifact and opened from disk on the desktop; the knowledge is embedded in the page.
import { createKnowledge } from '../core/knowledge.js';
import { T, STATUS, STATUS_HINT, SEVERITY, AREA, KIND, SCOPE, ISSUER, HOW, FORMAT, FORMAT_VALUE, EVIDENCE, RESULT, RESULT_HINT, VERDICT } from './i18n.js';

const data = JSON.parse(document.getElementById('kdata').textContent);
const K = createKnowledge(data);

const VIEWS = ['home', 'review', 'sources', 'requirements', 'rules', 'variations', 'documents', 'countries', 'ectd'];
const VIEW_OF = { requirement: 'requirements', rule: 'rules', variation: 'variations', doctype: 'documents', country: 'countries', table: 'ectd' };
const KIND_ORDER = ['source', 'requirement', 'rule', 'variation', 'doctype', 'country', 'table'];

// Each record gets a link name the address bar keeps: letters, digits and hyphens only.
const slugOf = new Map();
const bySlug = new Map();
for (const r of [...data.requirements, ...data.rules, ...data.variations.items, ...data.doctypes.items, ...data.countries.items, ...data.ectd.index]) {
  let s = 'r-' + r.id.replace(/[^A-Za-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  while (bySlug.has(s)) s += '-b';
  bySlug.set(s, r.id);
  slugOf.set(r.id, s);
}
const recHref = id => '#' + slugOf.get(id);
// The copy of a source published beside the page (sources/<file>), opened at a page when one is known.
// The kinds of file each edition carries: the claude.ai artifact serves PDF and CSV only; the desktop folder holds them all.
const OPENABLE = new Set((window.DBK_OPEN || ['pdf', 'csv']).map(x => x.toLowerCase()));
const fileHref = (s, page) => {
  if (!s?.held || !s.file || !OPENABLE.has(s.file.split('.').pop().toLowerCase())) return null;
  return `sources/${encodeURIComponent(s.file.split('/').pop())}${page && /\.pdf$/i.test(s.file) ? `#page=${page}` : ''}`;
};
const pageOf = (c, check) => check?.pages?.[0] || (/\bp\.?\s*(\d+)/.exec(c.at || '') || [])[1] || null;
const srcHref = id => '#s-' + id;

const store = {
  get(k, d) { try { return localStorage.getItem('dbk.' + k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem('dbk.' + k, v); } catch { /* the page works without it */ } },
};
const state = {
  lang: store.get('lang', 'ar') === 'en' ? 'en' : 'ar',
  auth: store.get('auth', '') || null,
  view: 'home', q: '', open: null,
  reqSet: 'eg-eda-ctd', area: '', pac: '', verdict: '',
};
if (state.auth && !K.authority(state.auth)) state.auth = null;

// ---------------------------------------------------------------- helpers
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const t = (k, ...a) => { const v = T[state.lang][k]; return typeof v === 'function' ? v(...a) : v; };
const pick = o => (o && typeof o === 'object' ? (o[state.lang] ?? o.en ?? o.ar ?? '') : o ?? '');
// A bilingual text from the data; English shown in an Arabic page is marked and set left to right.
function L(o) {
  if (o == null) return '';
  if (typeof o !== 'object') return esc(o);
  if (state.lang === 'ar' && !o.ar && o.en) return `<span lang="en" dir="ltr" class="ltr">${esc(o.en)}</span>`;
  return esc(pick(o));
}
const word = (map, k) => esc(pick(map[k]) || k);
const en = s => (s ? `<span lang="en" dir="ltr" class="ltr">${esc(s)}</span>` : '');
const stamp = st => (st ? `<span class="st st-${esc(st)}" title="${esc(pick(STATUS_HINT[st]))}">${word(STATUS, st)}</span>` : '');
const code = s => `<code>${esc(s)}</code>`;
function srcLabel(s) {
  if (String(s.code).length <= 22) return s.code;
  const al = (s.aliases || []).filter(a => a.length >= 6).sort((a, b) => a.length - b.length)[0];
  return al || s.code;
}
const srcCodeVer = s => `<span class="ltr"><code>${esc(srcLabel(s))}</code>${s.version && s.version !== '—' && !srcLabel(s).includes(s.version) ? ` ${esc(s.version)}` : ''}</span>`;
const short = id => String(id).replace(/^[A-Z-]+\/(var\/|doc\/)?/, '');
const n = v => Number(v).toLocaleString('en');   // Western digits throughout, as in the codes (3.2.P.8)
const byAuth = list => (state.auth ? list.filter(x => x.authority === state.auth) : list);

function validityText(m) {
  if (!m) return t('noTerm');
  return m % 12 === 0 ? `${t('months', m)} · ${t('years', m / 12)}` : t('months', m);
}

// ---------------------------------------------------------------- what each view lists
const lists = {
  sources: () => byAuth(data.sources),
  requirements: () => byAuth(data.requirements),
  rules: () => byAuth(data.rules),
  variations: () => byAuth(data.variations.items),
  documents: () => byAuth(data.doctypes.items),
  countries: () => (state.auth ? data.countries.items.filter(c => countryAuthority(c) === state.auth) : data.countries.items),
  ectd: () => (state.auth && state.auth !== 'ICH' ? [] : data.ectd.index),
  review: () => data.checks?.findings?.findings || [],
};
function countryAuthority(c) {
  return { EG: 'EG-EDA', EU: 'EU', US: 'US-FDA', GCC: 'GCC' }[c.code] || 'OTHER';
}
const authCount = a => data.sources.filter(s => s.authority === a).length
  + [...data.requirements, ...data.rules, ...data.variations.items, ...data.doctypes.items].filter(r => r.authority === a).length;

// ---------------------------------------------------------------- the frame
const app = document.getElementById('app');
app.innerHTML = `
  <header class="top">
    <a class="brand" href="#home"><span class="mark" aria-hidden="true">§</span><span><b data-t="app"></b><small data-t="appSub"></small></span></a>
    <form class="search" role="search" id="searchForm">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <input id="q" type="search" autocomplete="off" spellcheck="false">
    </form>
    <button class="lang" id="lang" type="button"></button>
  </header>
  <div class="shell" id="shell">
    <nav class="rail" id="rail" aria-label="sections"></nav>
    <main id="main"></main>
    <aside class="detail" id="detail" hidden></aside>
  </div>`;
const $ = id => document.getElementById(id);

function frame() {
  const html = document.documentElement;
  html.lang = state.lang;
  html.dir = state.lang === 'ar' ? 'rtl' : 'ltr';
  for (const el of app.querySelectorAll('[data-t]')) el.textContent = t(el.dataset.t);
  $('q').placeholder = t('search');
  $('q').setAttribute('aria-label', t('search'));
  $('lang').textContent = t('switchLang');
  $('lang').lang = state.lang === 'ar' ? 'en' : 'ar';
}

// ---------------------------------------------------------------- the rail
function rail() {
  const count = v => (v === 'home' ? '' : `<span class="n">${n(lists[v]().length)}</span>`);
  const sec = VIEWS.map(v => `<a href="#${v}" class="${!state.q && state.view === v ? 'on' : ''}">${t(v)}${count(v)}</a>`).join('');
  const auths = [`<button type="button" data-auth="" class="${!state.auth ? 'on' : ''}">${t('all')}</button>`,
    ...data.authorities.map(a => `<button type="button" data-auth="${esc(a.id)}" class="${state.auth === a.id ? 'on' : ''}">
      <span>${L(a.short || a.name)}</span><span class="n">${n(authCount(a.id))}</span></button>`)].join('');
  $('rail').innerHTML = `<h2>${t('sections')}</h2><div class="nav">${sec}</div><h2>${t('authorities')}</h2><div class="nav">${auths}</div>`;
}

// ---------------------------------------------------------------- rows
function row(href, k, title, end = '', sub = '', on = false) {
  return `<a class="row${on ? ' on' : ''}" href="${href}"><span class="k">${k}</span><span class="t">${title}${sub ? `<small>${sub}</small>` : ''}</span><span class="end">${end}</span></a>`;
}
const isOpen = id => state.open && state.open.id === id;
const sourceRow = s => row(srcHref(s.id), esc(`${srcLabel(s)}${s.version && s.version !== '—' && !srcLabel(s).includes(s.version) ? ' · ' + s.version : ''}`), L(s.title),
  `${stamp(s.status)}<span class="tag" title="${esc(t('usedBy'))}">${n(K.usedBy(s.id).length)}</span>`, s.issued ? esc(s.issued) : '', isOpen(s.id));
const authTag = r => (state.q && r.authority ? `<span class="tag">${L(K.authority(r.authority)?.short || { en: r.authority })}</span>` : '');
function recordRow(r) {
  switch (r.kind) {
    case 'requirement':
      return row(recHref(r.id), esc(r.ctd), L(r.title), `${authTag(r)}${r.module ? `<span class="mod mod-${esc(r.module)}">M${esc(r.module)}</span>` : ''}${stamp(r.status)}`, '', isOpen(r.id));
    case 'rule':
      return row(recHref(r.id), esc(short(r.id)), L(r.title), `<span class="sev sev-${esc(r.severity)}">${word(SEVERITY, r.severity)}</span>`, state.q ? word(AREA, r.area) : '', isOpen(r.id));
    case 'variation':
      return row(recHref(r.id), esc(short(r.id)), L(r.title), `${authTag(r)}${r.check && r.check.verdict !== 'agrees' ? `<span class="vd vd-${esc(r.check.verdict)}">${word(VERDICT, r.check.verdict)}</span>` : ''}<span class="pac pac-${esc(r.pac)}">${esc(r.pac)}</span>`, en(r.type), isOpen(r.id));
    case 'doctype':
      return row(recHref(r.id), esc(validityText(r.validity_months)), L(r.title), stamp(r.status), word(SCOPE, r.scope), isOpen(r.id));
    case 'country':
      return row(recHref(r.id), esc(r.code), en(r.authority), `<span class="tag">${word(EVIDENCE, r.evidence)}</span>`,
        esc(Object.entries(r.formats || {}).filter(([, v]) => v !== 'no').map(([k, v]) => `${FORMAT[k] || k}${v !== 'yes' ? ` (${pick(FORMAT_VALUE[v]) || v})` : ''}`).join(' · ')), isOpen(r.id));
    case 'table':
      return row(recHref(r.id), esc(r.file), L(r.title), '', '', isOpen(r.id));
    default:
      return row(recHref(r.id), esc(r.id), L(r.title));
  }
}
const groupBlock = (title, items, render) => (items.length
  ? `<section class="group"><h3>${title}<span class="n">${n(items.length)}</span></h3><div class="rows">${items.map(render).join('')}</div></section>` : '');
const empty = () => `<p class="empty">${t('noResults')}</p>`;
function chips(name, values, current, label) {
  return `<div class="filters" role="group">${[['', t('filterAll'), null], ...values].map(([v, text, cnt]) =>
    `<button type="button" class="chip${current === v ? ' on' : ''}" data-${name}="${esc(v)}">${text}${cnt != null ? `<span class="n">${n(cnt)}</span>` : ''}</button>`).join('')}</div>`;
}

// ---------------------------------------------------------------- views
const views = {
  home() {
    const legend = ['in-force', 'draft', 'superseded', 'reference', 'data', 'general', 'secondary', 'assumption']
      .map(s => `<div>${stamp(s)}<span>${esc(pick(STATUS_HINT[s]))}</span></div>`).join('');
    const dir = data.authorities.map(a => {
      const src = data.sources.filter(s => s.authority === a.id).length;
      const rec = [...data.requirements, ...data.rules, ...data.variations.items, ...data.doctypes.items].filter(r => r.authority === a.id).length;
      return `<button type="button" class="auth" data-auth="${esc(a.id)}" data-go="sources"><b>${L(a.name)}</b>
        <span class="meta"><span>${t('srcCount', n(src))}</span>${rec ? `<span>${t('recCount', n(rec))}</span>` : ''}</span></button>`;
    }).join('');
    const reviewed = data.sources.map(s => s.checked?.on).filter(Boolean).sort().at(-1);
    return `<h1>${t('app')}</h1><p class="lede">${t('intro')}</p>
      <section class="group"><h3>${t('authorities')}</h3></section><div class="dir">${dir}</div>
      <section class="group"><h3>${t('statusLegend')}</h3></section><div class="legend">${legend}</div>
      <p class="foot">${esc(t('lastReview', reviewed))}</p>`;
  },
  sources() {
    const list = lists.sources();
    const groups = data.authorities.map(a => groupBlock(L(a.name), list.filter(s => s.authority === a.id), sourceRow)).join('');
    return `<h1>${t('sources')}</h1><p class="lede">${t('whereFromHint')}</p>${groups || empty()}`;
  },
  requirements() {
    const sets = K.sets({ kind: 'requirements' }).filter(s => !state.auth || s.authority === state.auth);
    if (!sets.some(s => s.id === state.reqSet)) state.reqSet = sets[0]?.id;
    const set = K.set(state.reqSet);
    if (!set) return `<h1>${t('requirements')}</h1>${empty()}`;
    const tabs = chips('set', sets.map(s => [s.id, L(s.short || s.title), s.count]), state.reqSet) + `<p class="lede"><b>${L(set.title)}</b></p>`;
    const recs = K.records({ set: set.id });
    const mods = [...new Set(recs.map(r => r.module))];
    const body = mods.map(m => {
      const inMod = recs.filter(r => r.module === m);
      const groups = [...new Set(inMod.map(r => r.group))];
      return groups.map(g => groupBlock(`<span class="mod mod-${esc(m)}">M${esc(m)}</span> ${en(g)}`, inMod.filter(r => r.group === g), recordRow)).join('');
    }).join('');
    return `<h1>${t('requirements')}</h1>${tabs}${setRestsOn(set)}${body}`;
  },
  rules() {
    const all = lists.rules();
    const areas = Object.keys(AREA).filter(a => all.some(r => r.area === a));
    const list = state.area ? all.filter(r => r.area === state.area) : all;
    const body = areas.filter(a => !state.area || a === state.area).map(a => groupBlock(word(AREA, a), list.filter(r => r.area === a), recordRow)).join('');
    const set = K.set('eg-eda-review');
    return `<h1>${t('rules')}</h1>${chips('area', areas.map(a => [a, word(AREA, a), all.filter(r => r.area === a).length]), state.area)}
      ${all.length ? setRestsOn(set) : ''}${body || empty()}`;
  },
  variations() {
    const all = lists.variations();
    const list = all.filter(v => (!state.pac || v.pac === state.pac) && (!state.verdict || v.check?.verdict === state.verdict));
    const verdicts = ['differs', 'split', 'tool-only'].map(k => [k, word(VERDICT, k), all.filter(v => v.check?.verdict === k).length]).filter(x => x[2]);
    const types = [...new Set(list.map(v => `${v.group} — ${v.type}`))];
    const body = types.map(g => groupBlock(en(g), list.filter(v => `${v.group} — ${v.type}` === g), recordRow)).join('');
    const rule = data.variations.grouping_rule;
    return `<h1>${t('variations')}</h1>
      ${chips('pac', data.variations.class_order.map(c => [c, `<span class="code">${esc(c)}</span>`, all.filter(v => v.pac === c).length]), state.pac)}
      ${verdicts.length ? chips('verdict', verdicts, state.verdict) : ''}
      ${all.length ? `<p class="lede">${L(rule)}</p>${setRestsOn(K.set('eg-eda-variations'))}` : ''}${body || empty()}`;
  },
  documents() {
    const list = lists.documents();
    const body = ['product', 'party', 'product_party'].map(s => groupBlock(word(SCOPE, s), list.filter(d => d.scope === s), recordRow)).join('');
    return `<h1>${t('documents')}</h1>${list.length ? setRestsOn(K.set('eg-eda-doctypes')) : ''}${body || empty()}`;
  },
  countries() {
    const list = lists.countries();
    return `<h1>${t('countries')}</h1>${groupBlock(t('countries'), list, recordRow) || empty()}`;
  },
  ectd() {
    const list = lists.ectd();
    return `<h1>${t('ectd')}</h1>${groupBlock(t('ectd'), list, recordRow) || empty()}`;
  },
  review() {
    const ch = data.checks || {};
    const f = ch.findings || {};
    const order = ['verified', 'located', 'read', 'nothing-to-check', 'no-copy', 'partly', 'not-found'];
    const total = (ch.citations || []).length;
    const tiles = order.filter(k => ch.summary?.[k]).map(k => `<div class="res res-${k}"><b>${n(ch.summary[k])}</b><span>${word(RESULT, k)}</span><small>${esc(pick(RESULT_HINT[k]))}</small></div>`).join('');
    const cards = (f.findings || []).map(x => `<section class="finding fd-${esc(x.kind)}"><h3>${L(x.title)}</h3><p class="prose">${L(x.text)}</p>
      ${x.records?.length ? `<div class="kw">${x.records.map(id => `<a href="${recHref(id)}" class="ltr">${esc(short(id))}</a>`).join('')}</div>` : ''}
      ${x.sources?.length ? `<div class="kw">${x.sources.map(id => `<a href="${srcHref(id)}">${srcCodeVer(K.source(id))}</a>`).join('')}</div>` : ''}</section>`).join('');
    const rows = data.sources.filter(s => !state.auth || s.authority === state.auth).map(s => {
      const r = ch.sources?.[s.id] || {};
      if (!r.citations && !s.latest) return '';
      const cells = ['verified', 'located', 'read', 'nothing-to-check', 'no-copy'].map(k => `<td>${r[k] ? n(r[k]) : ''}</td>`).join('');
      return `<tr><th><a href="${srcHref(s.id)}">${srcCodeVer(s)}</a></th><td>${n(r.citations || 0)}</td>${cells}<td>${s.latest ? esc(s.latest.result) : ''}</td></tr>`;
    }).join('');
    return `<h1>${t('review')}</h1><p class="lede">${esc(t('reviewLede', f.reviewed || ''))}</p>
      <section class="group"><h3>${t('byResult')}<span class="n">${n(total)}</span></h3></section><div class="results">${tiles}</div>
      <section class="group"><h3>${t('findings')}<span class="n">${n((f.findings || []).length)}</span></h3></section><div class="findings">${cards}</div>
      <section class="group"><h3>${t('perSource')}</h3></section>
      <div class="tbl"><table class="persrc"><tr><th>${t('sources')}</th><th>${t('citationsN')}</th>${['verified', 'located', 'read', 'nothing-to-check', 'no-copy'].map(k => `<th title="${esc(pick(RESULT_HINT[k]))}">${word(RESULT, k)}</th>`).join('')}<th>${t('online')}</th></tr>${rows}</table></div>`;
  },
  search() {
    const hits = K.search(state.q, { authority: state.auth || undefined, limit: 300 });
    if (!hits.length) return `<h1>${t('results')}</h1>${empty()}`;
    const body = KIND_ORDER.map(k => groupBlock(word(KIND, k), hits.filter(h => h.kind === k),
      h => (h.type === 'source' ? sourceRow(h.item) : recordRow(h.item)))).join('');
    return `<h1>${t('results')}</h1>${body}`;
  },
};
function setRestsOn(set) {
  if (!set?.cite?.length) return '';
  return `<p class="lede">${t('setRestsOn')}: ${set.cite.map(c => {
    const s = K.source(c.src);
    return `<a href="${srcHref(c.src)}">${srcCodeVer(s)}</a>${c.at ? ` <span class="ltr">(${esc(c.at)})</span>` : ''}`;
  }).join(state.lang === 'ar' ? '، ' : ', ')}</p>`;
}

// ---------------------------------------------------------------- an entry
function citeCard(c, rec, field) {
  const s = K.source(c.src);
  const check = rec ? K.check(rec.id, field, c) : null;
  const page = pageOf(c, check);
  const href = fileHref(s, page);
  const arabic = /[\u0600-\u06FF]/.test(c.quote || '');
  return `<div class="cite ${esc(s.status)}">
    <div class="line1"><a href="${srcHref(s.id)}">${srcCodeVer(s)}</a>${stamp(s.status)}${check ? `<span class="res-tag res-${esc(check.result)}" title="${esc(pick(RESULT_HINT[check.result]))}">${word(RESULT, check.result)}${check.pages?.length ? ` · ${esc(t('pages', check.pages.join(', ')))}` : ''}</span>` : ''}</div>
    <div class="ttl">${L(s.title)}</div>
    ${c.at ? `<div class="at">${t('at')}: <b class="ltr">${esc(c.at)}</b></div>` : ''}
    ${c.quote ? `<blockquote ${arabic ? 'lang="ar" dir="rtl"' : 'lang="en" dir="ltr"'}>${esc(c.quote)}</blockquote>` : ''}
    ${c.gist ? `<div class="gist"><span>${t('gist')}</span> <span lang="en" dir="ltr" class="ltr">${esc(c.gist)}</span></div>` : ''}
    ${c.note ? `<div class="at">${esc(c.note)}</div>` : ''}
    ${href ? `<a class="openfile" href="${href}" target="_blank" rel="noopener">${t('openDoc')}${page ? ` · ${esc(t('pages', page))}` : ''}</a>` : ''}
  </div>`;
}
const citeList = (title, list, rec, field = 'cite') => (list?.length ? `<section class="cites"><h3>${title}</h3>${list.map(c => citeCard(c, rec, field)).join('')}</section>` : '');
// What the review changed in a record, said plainly above its sources.
const checkNote = r => (r.check?.note ? `<div class="checknote"><b>${word(VERDICT, r.check.verdict)}</b> ${L(r.check.note)}</div>` : '');
const facts = pairs => {
  const rows = pairs.filter(([, v]) => v !== undefined && v !== null && v !== '').map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('');
  return rows ? `<dl class="facts">${rows}</dl>` : '';
};
const block = (title, inner) => (inner ? `<section class="block"><h3>${title}</h3>${inner}</section>` : '');
const bullets = list => (list?.length ? `<ul>${list.map(x => `<li>${typeof x === 'object' ? L(x) : esc(x)}</li>`).join('')}</ul>` : '');

// The cases inside a requirement's logic that name their own source.
function innerCases(node, out = []) {
  if (Array.isArray(node)) node.forEach(x => innerCases(x, out));
  else if (node && typeof node === 'object') {
    if (node.cite) out.push(node);
    for (const [k, v] of Object.entries(node)) if (k !== 'cite') innerCases(v, out);
  }
  return out;
}

const details = {
  source(s) {
    const users = K.usedBy(s.id);
    const usedSets = data.sets.filter(st => st.cite?.some(c => c.src === s.id));
    const usedList = users.length
      ? `<div class="used">${users.sort((a, b) => KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind) || a.id.localeCompare(b.id)).slice(0, 400)
        .map(r => `<a href="${recHref(r.id)}"><span class="k">${esc(r.ctd || short(r.id))}</span><span>${L(r.title || { en: r.code })}</span></a>`).join('')}</div>`
      : `<p class="lede">${t('noUsers')}</p>`;
    return `<div class="d-head"><div class="eyebrow">${word(KIND, 'source')} · ${L(K.authority(s.authority)?.name)}</div>
        <h1>${L(s.title)}</h1><div class="eyebrow">${code(s.code)}${stamp(s.status)}</div></div>
      ${s.confirm ? `<p class="confirm">${t('toConfirm')}: ${esc(s.confirm)}</p>` : ''}
      ${s.superseded_by ? `<div class="checknote"><b>${t('replacedBy')}</b> <a href="${srcHref(s.superseded_by)}">${srcCodeVer(K.source(s.superseded_by))}</a> — ${L(K.source(s.superseded_by).title)}</div>` : ''}
      ${fileHref(s) || s.url ? `<div class="openbar">${fileHref(s) ? `<a class="openfile big" href="${fileHref(s)}" target="_blank" rel="noopener">${t('openDoc')}</a>` : ''}${s.url ? `<a class="openfile big ghost" href="${esc(s.url)}" target="_blank" rel="noopener">${t('official')}</a>` : ''}</div>` : ''}
      ${facts([
        [t('version'), s.version && s.version !== '—' ? `<span class="ltr">${esc(s.version)}</span>` : ''],
        [t('issued'), esc(s.issued)], [t('effective'), esc(s.effective)], [t('supersedes'), esc(s.supersedes)],
        [t('status'), esc(pick(STATUS_HINT[s.status]))],
        [t('checked'), s.checked ? `${esc(s.checked.on)} — ${word(HOW, s.checked.how)}` : ''],
        [t('online'), s.latest ? `${esc(s.latest.on)} — ${esc(s.latest.result)}${s.latest.note ? ` <span class="at">(${esc(s.latest.note)})</span>` : ''}` : ''],
        [t('byResult'), (() => { const r = data.checks?.sources?.[s.id]; return r?.citations ? ['verified', 'located', 'read', 'nothing-to-check', 'no-copy'].filter(k => r[k]).map(k => `${word(RESULT, k)}: ${n(r[k])}`).join(' · ') : ''; })()],
        [t('copy'), s.held && s.file ? code(s.file) : ''],

        [t('note'), esc(s.note)],
      ])}
      ${usedSets.length ? block(t('setRestsOn'), bullets(usedSets.map(st => st.title))) : ''}
      ${block(`${t('usedBy')} (${n(users.length)})`, usedList)}`;
  },
  requirement(r) {
    const set = K.set(r.set);
    const cols = set?.columns ? Object.keys(set.columns) : [];
    const levels = r.matrix && cols.length
      ? `<div class="tbl"><table class="levels"><tr>${cols.map(c => `<th>${L(set.columns[c])}</th>`).join('')}</tr>
         <tr>${cols.map(c => `<td>${esc(typeof r.matrix[c] === 'object' ? JSON.stringify(r.matrix[c]) : r.matrix[c] ?? '—')}</td>`).join('')}</tr></table></div>
         <p class="eyebrow" style="margin-top:6px">${t('levelKey')}</p>` : '';
    const cases = innerCases(r.required).map(cs => `${cs.reason || cs.note ? `<p class="prose">${L(cs.reason || cs.note)}</p>` : ''}${cs.cite.map(c => citeCard(c, r, 'case')).join('')}`).join('');
    return `<div class="d-head"><div class="eyebrow">${word(KIND, 'requirement')} · ${L(set?.title)}</div>
        <h1>${L(r.title)}</h1><div class="eyebrow">${code(r.ctd)}${r.module ? `<span class="mod mod-${esc(r.module)}">M${esc(r.module)}</span>` : ''}${stamp(r.status)}</div></div>
      ${facts([
        [t('ctd'), code(r.ctd)],
        [t('ectdNodes'), r.ectd?.length ? r.ectd.map(code).join(' ') : ''],
        [t('group'), en(r.group)],
        [t('docClass'), en(r.doc_class)], [t('producedBy'), en(r.produced_by)],
      ])}
      ${block(t('acceptance'), r.acceptance ? `<p class="prose" lang="en" dir="ltr">${esc(r.acceptance)}</p>` : '')}
      ${block(t('note'), r.note ? `<p class="prose">${typeof r.note === 'object' ? L(r.note) : `<span lang="en" dir="ltr" class="ltr">${esc(r.note)}</span>`}</p>` : '')}
      ${block(t('levels'), levels)}
      ${citeList(t('whereFrom'), r.cite, r)}
      ${citeList(t('ectdFrom'), r.ectd_cite, r, 'ectd_cite')}
      ${cases ? `<section class="cites"><h3>${t('note')}</h3>${cases}</section>` : ''}`;
  },
  rule(r) {
    return `<div class="d-head"><div class="eyebrow">${word(KIND, 'rule')} · ${word(AREA, r.area)}</div>
        <h1>${L(r.title)}</h1><div class="eyebrow">${code(short(r.id))}<span class="sev sev-${esc(r.severity)}">${word(SEVERITY, r.severity)}</span>${r.ctd ? code(r.ctd) : ''}</div></div>
      ${checkNote(r)}
      ${block(t('question'), `<p class="prose">${L(r.question)}</p>`)}
      ${block(t('deficiency'), r.deficiency ? `<p class="prose">${L(r.deficiency)}</p>` : '')}
      ${block(t('keywords'), r.evidence?.keywords?.length ? `<div class="kw">${r.evidence.keywords.map(k => `<span>${esc(k)}</span>`).join('')}</div>` : '')}
      ${citeList(t('whereFrom'), r.cite, r)}
      ${citeList(t('anchorFrom'), r.anchor_cite, r, 'anchor_cite')}`;
  },
  variation(v) {
    const g = v.guideline;
    const gl = g ? facts([
      [t('guideline'), `<span class="ltr">§${esc(g.section)}</span> — <span lang="en" dir="ltr" class="ltr">${esc(g.heading)}</span>${g.item ? `<br><span lang="en" dir="ltr" class="ltr">${esc(g.item)}</span>` : ''}`],
      [t('guidelineClass'), `<span class="pac pac-${esc(g.pac)}">${esc(g.pac)}</span>`],
      [t('toolClass'), v.pac_tool ? `<span class="pac pac-${esc(v.pac_tool)}">${esc(v.pac_tool)}</span>` : ''],
      [t('classes'), g.classes?.length ? `<ul lang="en" dir="ltr">${g.classes.map(x => `<li>${esc(x.item || '—')} <span class="pac pac-${esc(x.pac)}">${esc(x.pac)}</span></li>`).join('')}</ul>` : ''],
    ]) : '';
    return `<div class="d-head"><div class="eyebrow">${word(KIND, 'variation')} · ${en(v.group)}</div>
        <h1>${L(v.title)}</h1><div class="eyebrow">${code(short(v.id))}<span class="pac pac-${esc(v.pac)}">${esc(v.pac)}</span>${state.lang === 'ar' && !v.title.ar ? `<span class="tag">${t('enOnly')}</span>` : ''}</div></div>
      ${checkNote(v)}
      ${facts([[t('pac'), `<span class="pac pac-${esc(v.pac)}">${esc(v.pac)}</span>`], [t('group'), en(v.group)], [t('type'), en(v.type)]])}
      ${gl}
      ${block(t('conditions'), v.conditions?.length ? `<div lang="en" dir="ltr">${bullets(v.conditions)}</div>` : `<p>${t('none')}</p>`)}
      ${block(t('docsNeeded'), v.requirements?.length ? `<div lang="en" dir="ltr">${bullets(v.requirements)}</div>` : `<p>${t('none')}</p>`)}
      ${citeList(t('whereFrom'), v.cite, v)}`;
  },
  doctype(d) {
    return `<div class="d-head"><div class="eyebrow">${word(KIND, 'doctype')} · ${word(SCOPE, d.scope)}</div>
        <h1>${L(d.title)}</h1><div class="eyebrow">${stamp(d.status)}</div></div>
      ${facts([
        [t('validity'), esc(validityText(d.validity_months))],
        [t('warnBefore'), d.warn_days ? esc(t('days', d.warn_days)) : ''],
        [t('scope'), word(SCOPE, d.scope)], [t('issuer'), word(ISSUER, d.issuer_kind)],
      ])}
      ${checkNote(d)}
      ${block(t('note'), d.note_source ? `<p class="prose" lang="en" dir="ltr">${esc(d.note_source)}</p>` : '')}
      ${citeList(t('whereFrom'), d.cite, d)}`;
  },
  country(c) {
    const formats = Object.entries(c.formats || {}).map(([k, v]) => `<tr><th>${esc(FORMAT[k] || k)}</th><td>${esc(pick(FORMAT_VALUE[v]) || v)}</td></tr>`).join('');
    return `<div class="d-head"><div class="eyebrow">${word(KIND, 'country')} · ${code(c.code)}</div>
        <h1>${en(c.authority)}</h1><div class="eyebrow"><span class="tag">${word(EVIDENCE, c.evidence)}</span></div></div>
      ${block(t('formats'), formats ? `<div class="tbl"><table class="levels">${formats}</table></div>` : '')}
      ${facts([[t('module1'), `<span lang="en" dir="ltr" class="ltr">${esc(c.module1)}</span>`], [t('criteria'), `<span lang="en" dir="ltr" class="ltr">${esc(c.criteria)}</span>`]])}
      ${block(t('note'), c.note ? `<p class="prose" lang="en" dir="ltr">${esc(c.note)}</p>` : '')}
      ${citeList(t('whereFrom'), c.cite, c)}`;
  },
  table(tb) {
    const files = Object.keys(data.ectd.tables).filter(f => f === tb.file || (tb.file.endsWith('/') && f.startsWith(tb.file)));
    const show = f => {
      const text = data.ectd.tables[f];
      if (!f.endsWith('.csv')) return `<div class="tbl"><pre style="margin:0;padding:10px;font-size:12px">${esc(text)}</pre></div>`;
      const rows = parseCsv(text);
      const [head, ...body] = rows;
      return `<p class="eyebrow">${esc(t('rows', n(body.length)))}</p><div class="tbl" style="max-height:60vh"><table lang="en" dir="ltr">
        <tr>${head.map(h => `<th>${esc(h)}</th>`).join('')}</tr>${body.map(r => `<tr>${r.map(x => `<td>${esc(x)}</td>`).join('')}</tr>`).join('')}</table></div>`;
    };
    return `<div class="d-head"><div class="eyebrow">${word(KIND, 'table')}</div><h1>${L(tb.title)}</h1><div class="eyebrow">${code(tb.file)}</div></div>
      ${citeList(t('whereFrom'), tb.cite, tb)}${files.map(f => block(code(f), show(f))).join('')}`;
  },
};

function parseCsv(text) {
  const rows = [];
  let row = [], cell = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; } else if (ch === '"') q = false; else cell += ch;
    } else if (ch === '"') q = true;
    else if (ch === ',') { row.push(cell); cell = ''; }
    else if (ch === '\n' || ch === '\r') { if (ch === '\r' && text[i + 1] === '\n') i++; row.push(cell); rows.push(row); row = []; cell = ''; }
    else cell += ch;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows.filter(r => r.some(x => x !== ''));
}

// ---------------------------------------------------------------- drawing and moving
function drawMain() {
  $('main').innerHTML = state.q.trim() ? views.search() : views[state.view]();
}
function drawDetail() {
  const d = $('detail');
  const o = state.open;
  if (!o) { d.hidden = true; d.innerHTML = ''; $('shell').classList.remove('has-detail'); return; }
  const item = o.type === 'source' ? K.source(o.id) : K.record(o.id);
  const kind = o.type === 'source' ? 'source' : item.kind;
  d.innerHTML = `<div class="d-bar"><span class="eyebrow">${word(KIND, kind)}</span><button type="button" class="x" id="closeDetail">${t('close')}</button></div>${details[kind](item)}`;
  d.hidden = false;
  d.scrollTop = 0;
  $('shell').classList.add('has-detail');
}
function draw() { frame(); rail(); drawMain(); drawDetail(); }

function route() {
  const h = decodeURIComponent(location.hash.slice(1));
  state.open = null;
  if (!h || h === 'home') state.view = 'home';
  else if (VIEWS.includes(h)) state.view = h;
  else if (h.startsWith('s-') && K.source(h.slice(2))) {
    state.open = { type: 'source', id: h.slice(2) };
    if (!state.q && state.view === 'home') state.view = 'sources';
  } else if (bySlug.has(h)) {
    const r = K.record(bySlug.get(h));
    state.open = { type: 'record', id: r.id };
    if (!state.q) {
      state.view = VIEW_OF[r.kind];
      if (r.kind === 'requirement') state.reqSet = r.set;
      if (r.kind === 'rule' && state.area && state.area !== r.area) state.area = '';
      if (r.kind === 'variation' && state.pac && state.pac !== r.pac) state.pac = '';
      if (state.auth && r.authority && r.authority !== state.auth) state.auth = null;
    }
  }
  rail(); drawMain(); drawDetail();
}

document.addEventListener('click', e => {
  const el = e.target.closest('button, a');
  if (!el) return;
  if (el.id === 'lang') {
    state.lang = state.lang === 'ar' ? 'en' : 'ar';
    store.set('lang', state.lang);
    return draw();
  }
  if (el.id === 'closeDetail') {
    const back = state.q ? '' : state.view;
    history.replaceState(null, '', back ? `#${back}` : location.pathname + location.search);
    state.open = null;
    return drawMain(), drawDetail();
  }
  if (el.dataset.auth !== undefined) {
    state.auth = el.dataset.auth || null;
    store.set('auth', state.auth || '');
    if (el.dataset.go) { state.q = ''; $('q').value = ''; location.hash = el.dataset.go; }
    rail(); drawMain();
    return;
  }
  if (el.dataset.set !== undefined) { state.reqSet = el.dataset.set || K.sets({ kind: 'requirements' })[0].id; return drawMain(); }
  if (el.dataset.area !== undefined) { state.area = el.dataset.area; return drawMain(); }
  if (el.dataset.pac !== undefined) { state.pac = el.dataset.pac; return drawMain(); }
  if (el.dataset.verdict !== undefined) { state.verdict = el.dataset.verdict; return drawMain(); }
  // A section link while a search is showing: leave the search.
  if (el.tagName === 'A' && VIEWS.includes((el.getAttribute('href') || '').slice(1)) && state.q) {
    state.q = ''; $('q').value = '';
    if (location.hash === el.getAttribute('href')) { route(); e.preventDefault(); }
  }
});
let timer;
$('q').addEventListener('input', () => {
  clearTimeout(timer);
  timer = setTimeout(() => { state.q = $('q').value; rail(); drawMain(); }, 120);
});
$('searchForm').addEventListener('submit', e => { e.preventDefault(); clearTimeout(timer); state.q = $('q').value; rail(); drawMain(); });
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && state.open) $('closeDetail')?.click();
  if (e.key === '/' && document.activeElement !== $('q')) { e.preventDefault(); $('q').focus(); }
});
window.addEventListener('hashchange', route);

frame();
route();
