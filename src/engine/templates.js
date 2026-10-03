// Quick-entry templates are DATA rows (templates/<id>) interpreted here, so a new template needs no code.
//
// template = {
//   id, name, order, active,
//   inputs:   [{ key, label, type: 'amount'|'number'|'rate'|'date'|'text'|'party'|'account'|'select'|'docs', required, options?, default? }],
//   defaults: { cc, sector, docIds }            // 'fixed:<id>' | 'input:<key>' | null (docIds: array | 'input:docs')
//   lines:    [{ side: 'dr'|'cr', acctFrom, amountFrom, partyFrom, memo, cc, sector }],
//     acctFrom   'fixed:1320' | 'input:expenseAcct' | 'party.defaultAccount' | 'party.accrualAccount'
//     amountFrom 'input:amount' (default) or a product like 'input:monthly*input:months' / 'input:cost*input:rate*input:days/365'
//     partyFrom  'input:party' | 'fixed:<partyId>' | 'none'
//   descPattern: 'صرف {ref}[ — {payee}]'        // {key} placeholders; [...] groups vanish when a placeholder inside is empty
//   rule: 'cash-funding-evidence' | 'open-item-on-unknown-source' | null,  ruleOptions: {...}
// }
//
// Reserved input keys that need not be declared: date (always required), desc, docIds, cc, sector.
import { formatMoney, fromCents, toCents, parseAmount, productCents } from '../lib/money.js';
import { parseDate, formatDate, fyOf } from '../lib/dates.js';
import { MSG } from './constants.js';
import { coll, isNil, rulesOf, resolvePartyId, stampOf, clone, normalizeEntry } from './util.js';
import { validateEntry } from './validation.js';
import { planPost, planSaveDraft } from './posting.js';
import { normalizeRate } from './depreciation.js';

const e = (code, msg, extra = {}) => ({ code, msg, ...extra });

// ------------------------------------------------------------------ built-in rule hooks

/** Next number in a register keyed by item number (max + 1), considering writes already queued. */
function nextRegisterNo(registry, queued, collName) {
  let max = 0;
  for (const k of Object.keys(registry || {})) if (Number.isFinite(Number(k))) max = Math.max(max, Number(k));
  for (const w of queued || []) {
    const m = new RegExp(`^${collName}/(\\d+)$`).exec(w.path || '');
    if (m) max = Math.max(max, Number(m[1]));
  }
  return max + 1;
}

/**
 * cash-funding-evidence: a funding line (credit to one of the cash-funding accounts) is only booked as funding when
 * the input `evidence` says a bank deposit or a treasury receipt backs it ('bank' | 'treasury'). Anything else
 * ('none' or missing) is rerouted to the party's ACCRUAL account and flagged for review.
 * Accrual account lookup: ruleOptions.accrualAccountOf / config.rules.accrualAccountOf [fundingAcct -> accrualAcct],
 * else party.accrualAccount, else ruleOptions.accrualAcct.
 */
function cashFundingEvidence({ state, template, inputs, entry, party }) {
  const opts = template.ruleOptions || {};
  const rules = rulesOf(state);
  const funding = opts.fundingAccounts || rules.fundingAccounts;
  const map = { ...rules.accrualAccountOf, ...(opts.accrualAccountOf || {}) };
  const ev = inputs[opts.evidenceInput || 'evidence'];
  const warnings = [];
  const errors = [];
  if (ev === 'bank' || ev === 'treasury') return { entry, warnings, errors };
  const rerouted = [];
  for (const l of entry.lines) {
    if (!funding.includes(l.acct)) continue;
    const target = map[l.acct] || (party && party.accrualAccount) || opts.accrualAcct || null;
    if (!target) {
      errors.push(e('rule-no-accrual-account', 'لا يوجد حساب استحقاق مخصص لهذا الطرف — حدّده في إعدادات الطرف أو القالب', { line: l.n }));
      continue;
    }
    rerouted.push({ n: l.n, from: l.acct, to: target });
    l.acct = target;
    l.needsReview = true;
    l.reviewReason = 'تمويل بلا إثبات بنك أو خزينة — سُجِّل استحقاقاً على الطرف لا تمويلاً نقدياً';
  }
  if (rerouted.length) {
    const accts = rerouted.map((r) => `${r.from}→${r.to}`).join('، ');
    warnings.push(e('funding-rerouted', `لا يوجد إيصال بنك أو خزينة — حُوِّل المبلغ إلى حساب الاستحقاق (${accts})`, { rerouted }));
    entry.rerouted = rerouted;
  }
  return { entry, warnings, errors };
}

/**
 * open-item-on-unknown-source: a deposit with no identified source is booked normally AND opens a register item
 * (openItems/<n>, n = max + 1) linked from the line, so the question stays visible until a document arrives.
 * Returns the new doc as an extra write; planPost patches its linkedEntries with the entry number.
 */
function openItemOnUnknownSource({ state, template, inputs, entry, now, user, extraWrites }) {
  const opts = template.ruleOptions || {};
  const n = nextRegisterNo(coll(state, 'openItems'), extraWrites, 'openItems');
  const amountC = entry.lines.reduce((t, l) => t + toCents(Number.isFinite(l.dr) ? l.dr : 0), 0);
  const ref = inputs.ref ? ` — ${inputs.ref}` : '';
  const item = {
    n,
    year: fyOf(entry.date),
    item: `إيداع غير محدد المصدر — ${formatMoney(fromCents(amountC), { parens: false })} بتاريخ ${formatDate(entry.date)}${ref}`,
    effect: opts.effect || 'يُصنَّف الحساب بعد تحديد المصدر',
    docRequired: opts.docRequired || 'مستند يثبت مصدر الإيداع',
    status: 'open',
    linkedEntries: [],
    closedDocId: null,
    closedAt: null,
    createdBy: user || null,
    createdAt: stampOf(now),
  };
  const side = opts.linkSide || 'cr';
  const line = entry.lines.find((l) => (side === 'cr' ? l.cr > 0 : l.dr > 0)) || entry.lines[0];
  line.links = [...(line.links || []), { t: 'o', n }];
  line.needsReview = true;
  line.reviewReason = `إيداع غير محدد المصدر — بند مفتوح رقم ${n}`;
  return { entry, warnings: [e('open-item-created', `سيُفتح بند رقم ${n} في سجل البنود المفتوحة`, { n })], errors: [], extraWrites: [{ op: 'set', path: `openItems/${n}`, data: item }] };
}

/** Built-in rule hooks by id. Each is (ctx) => { entry, warnings, errors, extraWrites? }. */
export const builtinRules = {
  'cash-funding-evidence': cashFundingEvidence,
  'open-item-on-unknown-source': openItemOnUnknownSource,
};

// ------------------------------------------------------------------ interpretation

function renderPattern(pattern, values) {
  if (!pattern) return '';
  const empty = (v) => v === undefined || v === null || v === '';
  let out = String(pattern).replace(/\[([^[\]]*)\]/g, (_, inner) => {
    const keys = [...inner.matchAll(/\{(\w+)\}/g)].map((m) => m[1]);
    return keys.some((k) => empty(values[k])) ? '' : inner;
  });
  out = out.replace(/\{(\w+)\}/g, (_, k) => (empty(values[k]) ? '' : String(values[k])));
  return out.replace(/\s+/g, ' ').trim();
}

function normalizeInputs(template, raw, state) {
  const inputs = {};
  const errors = [];
  const accounts = coll(state, 'accounts');
  const specs = [...(template.inputs || [])];
  if (!specs.some((s) => s.key === 'date')) specs.unshift({ key: 'date', label: 'التاريخ', type: 'date', required: true });
  for (const spec of specs) {
    let v = raw[spec.key];
    if (isNil(v) && !isNil(spec.default)) v = spec.default;
    const label = spec.label || spec.key;
    if (isNil(v) || (Array.isArray(v) && !v.length)) {
      if (spec.required) errors.push(e('input-required', `الحقل «${label}» مطلوب`, { key: spec.key }));
      continue;
    }
    switch (spec.type) {
      case 'amount': {
        const n = typeof v === 'number' ? v : parseAmount(v);
        if (n === null || !Number.isFinite(n) || n <= 0) errors.push(e('input-invalid', `«${label}»: أدخل مبلغاً أكبر من صفر`, { key: spec.key }));
        else inputs[spec.key] = n;
        break;
      }
      case 'number': {
        const n = typeof v === 'number' ? v : parseAmount(v);
        if (n === null || !Number.isFinite(n) || n <= 0) errors.push(e('input-invalid', `«${label}»: أدخل رقماً أكبر من صفر`, { key: spec.key }));
        else inputs[spec.key] = n;
        break;
      }
      case 'rate': {
        const n = typeof v === 'number' ? v : parseAmount(v);
        if (n === null || !(n > 0)) errors.push(e('input-invalid', `«${label}»: أدخل نسبة صحيحة`, { key: spec.key }));
        else inputs[spec.key] = normalizeRate(n);
        break;
      }
      case 'date': {
        const d = parseDate(String(v), { defaultYear: raw.defaultYear });
        if (!d) errors.push(e('input-invalid', MSG.DATE_INVALID, { key: spec.key }));
        else inputs[spec.key] = d;
        break;
      }
      case 'party': {
        const id = resolvePartyId(state, v);
        if (!coll(state, 'parties')[id]) errors.push(e('input-invalid', `«${label}»: ${MSG.PARTY_UNKNOWN}`, { key: spec.key }));
        else inputs[spec.key] = id;
        break;
      }
      case 'account': {
        const a = accounts[String(v)];
        if (!a) errors.push(e('input-invalid', `«${label}»: ${MSG.UNKNOWN_ACCOUNT}`, { key: spec.key }));
        else if (a.postable === false || a.active === false) errors.push(e('input-invalid', `«${label}»: ${a.postable === false ? MSG.ACCOUNT_NONPOSTABLE : MSG.ACCOUNT_INACTIVE}`, { key: spec.key }));
        else inputs[spec.key] = String(v);
        break;
      }
      case 'select': {
        const opts = (spec.options || []).map((o) => String(o && typeof o === 'object' ? o.value : o));
        if (!opts.includes(String(v))) errors.push(e('input-invalid', `«${label}»: قيمة غير مسموحة`, { key: spec.key }));
        else inputs[spec.key] = String(v);
        break;
      }
      case 'docs':
        inputs[spec.key] = Array.isArray(v) ? v.slice() : [v];
        break;
      default:
        inputs[spec.key] = String(v).trim();
    }
  }
  for (const k of ['desc', 'cc', 'sector']) if (!isNil(raw[k]) && inputs[k] === undefined) inputs[k] = raw[k];
  if (Array.isArray(raw.docIds) && inputs.docIds === undefined) inputs.docIds = raw.docIds.slice();
  return { inputs, errors };
}

const ref = (spec) => {
  const s = String(spec ?? '');
  const i = s.indexOf(':');
  return i < 0 ? [s, ''] : [s.slice(0, i), s.slice(i + 1)];
};

/** Amount in cents from an amountFrom expression, or null when an input is missing. */
function amountCentsOf(expr, inputs) {
  const text = expr || 'input:amount';
  const factors = [];
  const divisors = [];
  let op = '*';
  for (const tok of text.split(/([*/])/).map((t) => t.trim()).filter(Boolean)) {
    if (tok === '*' || tok === '/') {
      op = tok;
      continue;
    }
    let val;
    if (tok.startsWith('input:')) val = inputs[tok.slice(6)];
    else val = Number(tok);
    if (val === undefined || val === null || !Number.isFinite(Number(val))) return null;
    (op === '*' ? factors : divisors).push(Number(val));
    op = '*';
  }
  return productCents(factors, divisors);
}

function dimOf(spec, inputs, fallback) {
  if (isNil(spec)) return fallback;
  const [kind, rest] = ref(spec);
  if (kind === 'fixed') return rest;
  if (kind === 'input') return isNil(inputs[rest]) ? fallback : inputs[rest];
  return String(spec);
}

/**
 * applyTemplate(template, inputs, ctx)
 *  template: the doc, or its id (looked up in ctx.state.templates)
 *  inputs:   raw user input by key (strings or typed values; Arabic digits accepted)
 *  ctx:      { state, user, now, rand, reason, no, mode: 'draft' | 'post' }   (no: number allocated by the repo, see planPost)
 * Returns { ok, entry, errors, warnings, extraWrites, validation, plan? }. `entry` is draft-shaped and unsaved.
 * With ctx.mode a ready plan is included: 'post' = planPost(entry + extraWrites), 'draft' = planSaveDraft.
 * Built-in rule hooks run after the lines are built (see builtinRules).
 */
export function applyTemplate(templateOrId, inputsRaw = {}, ctx = {}) {
  const state = ctx.state || {};
  const template = typeof templateOrId === 'string' ? coll(state, 'templates')[templateOrId] : templateOrId;
  if (!template) return { ok: false, entry: null, errors: [e('template-not-found', MSG.NOT_FOUND)], warnings: [], extraWrites: [], validation: null };
  if (template.active === false) return { ok: false, entry: null, errors: [e('template-inactive', 'القالب غير مفعّل')], warnings: [], extraWrites: [], validation: null };
  const { inputs, errors } = normalizeInputs(template, inputsRaw, state);
  const party = (() => {
    const pin = (template.inputs || []).find((s) => s.type === 'party');
    return pin && inputs[pin.key] ? coll(state, 'parties')[inputs[pin.key]] : null;
  })();
  const partyInputKey = (template.inputs || []).find((s) => s.type === 'party');
  const date = inputs.date;

  const lines = [];
  (template.lines || []).forEach((rl, i) => {
    const [akind, aval] = ref(rl.acctFrom);
    let acct = null;
    if (akind === 'fixed') acct = aval;
    else if (akind === 'input') acct = inputs[aval] ?? null;
    else if (rl.acctFrom === 'party.defaultAccount') acct = party ? party.defaultAccount : null;
    else if (rl.acctFrom === 'party.accrualAccount') acct = party ? party.accrualAccount : null;
    if (isNil(acct)) {
      if (!errors.some((x) => x.key === aval || x.code === 'party-no-default-account')) {
        if (String(rl.acctFrom).startsWith('party.') && party) errors.push(e('party-no-default-account', 'لا يوجد حساب افتراضي للطرف — اختر الحساب يدوياً', { line: i + 1 }));
        else if (!String(rl.acctFrom).startsWith('party.')) errors.push(e('input-required', `حساب السطر ${i + 1} غير محدد`, { line: i + 1 }));
      }
      acct = '';
    }
    const c = amountCentsOf(rl.amountFrom, inputs);
    if (c === null && !errors.length) errors.push(e('input-required', `مبلغ السطر ${i + 1} غير محدد`, { line: i + 1 }));
    const amount = c === null ? 0 : fromCents(c);
    const [pkind, pval] = ref(rl.partyFrom || (partyInputKey ? `input:${partyInputKey.key}` : 'none'));
    let partyId = null;
    if (pkind === 'input') partyId = inputs[pval] ?? null;
    else if (pkind === 'fixed') partyId = pval || null;
    lines.push({
      n: i + 1,
      acct: String(acct),
      dr: rl.side === 'dr' ? amount : 0,
      cr: rl.side === 'cr' ? amount : 0,
      memo: rl.memo ? renderPattern(rl.memo, inputs) : '',
      partyId: partyId && partyId !== 'none' ? resolvePartyId(state, partyId) : null,
      docIds: [],
      cc: rl.cc ? dimOf(rl.cc, inputs, null) : null,
      sector: rl.sector ? dimOf(rl.sector, inputs, null) : null,
      valueDate: null,
      needsReview: false,
      reviewReason: '',
      links: [],
      legacy: null,
    });
  });

  const defaults = template.defaults || {};
  const docIds = inputs.docIds || (Array.isArray(defaults.docIds) ? defaults.docIds.slice() : defaults.docIds ? dimOf(defaults.docIds, inputs, []) : []);
  const values = { ...inputs, partyName: party ? party.name : '', date: date ? formatDate(date) : '' };
  for (const spec of template.inputs || []) {
    if (spec.type === 'amount' && inputs[spec.key] !== undefined) values[spec.key] = formatMoney(inputs[spec.key], { parens: false });
    if (spec.type === 'party') values[spec.key] = party ? party.name : '';
  }
  let entry = {
    no: null,
    date: date || '',
    fy: date ? fyOf(date) : null,
    status: 'draft',
    desc: inputs.desc || renderPattern(template.descPattern, values),
    docIds: Array.isArray(docIds) ? docIds : [],
    cc: dimOf(inputs.cc ? `fixed:${inputs.cc}` : defaults.cc, inputs, null),
    sector: dimOf(inputs.sector ? `fixed:${inputs.sector}` : defaults.sector, inputs, null) ?? (state.config && state.config.defaults && state.config.defaults.sector) ?? null,
    source: `template:${template.id}`,
    isLegacy: false,
    legacyRow: null,
    version: 1,
    voidReason: null,
    reversalOf: null,
    createdBy: ctx.user || null,
    createdAt: null,
    postedBy: null,
    postedAt: null,
    lines,
    history: [],
  };

  const warnings = [];
  let extraWrites = [];
  if (template.rule && !errors.length) {
    const hook = builtinRules[template.rule];
    if (!hook) errors.push(e('rule-unknown', `قاعدة غير معروفة: ${template.rule}`));
    else {
      const out = hook({ state, template, inputs, entry, party, now: ctx.now, user: ctx.user, extraWrites });
      entry = out.entry || entry;
      warnings.push(...(out.warnings || []));
      errors.push(...(out.errors || []));
      extraWrites = [...extraWrites, ...(out.extraWrites || [])];
    }
  }
  entry = { ...entry, ...normalizeEntry(entry), rerouted: entry.rerouted };
  if (!entry.rerouted) delete entry.rerouted;
  const validation = validateEntry(entry, { state });
  const result = { ok: errors.length === 0, entry, errors, warnings, extraWrites, validation };
  if (result.ok && ctx.mode === 'post') {
    result.plan = planPost(state, { entry, no: ctx.no, user: ctx.user, now: ctx.now, reason: ctx.reason || '', extraWrites });
  } else if (result.ok && ctx.mode === 'draft') {
    result.plan = planSaveDraft(state, { entry, user: ctx.user, now: ctx.now, rand: ctx.rand, extraWrites });
  }
  return result;
}

// ------------------------------------------------------------------ default data rows

const dimInputs = [
  { key: 'docIds', label: 'المستند', type: 'docs', required: false },
  { key: 'cc', label: 'مركز التكلفة', type: 'select-cc', required: false },
  { key: 'sector', label: 'القطاع القانوني', type: 'select-sector', required: false },
];
const dims = () => dimInputs.map((d) => ({ ...d }));

/**
 * The five launch templates as data rows (account codes are chart configuration). The seed step stores them under
 * templates/<id>; the owner may edit them or add more. Cost center, sector and document come from the user's header
 * input (or the template defaults once the owner sets them).
 */
export function defaultTemplates() {
  const t = [
    {
      id: 'tpl-salary-accrual', name: 'استحقاق مرتب', order: 1, active: true,
      inputs: [
        { key: 'party', label: 'الموظف', type: 'party', required: true },
        { key: 'monthly', label: 'المرتب الشهري', type: 'amount', required: true },
        { key: 'months', label: 'عدد الأشهر', type: 'number', required: true, default: 1 },
        { key: 'expenseAcct', label: 'حساب المصروف', type: 'account', required: true, default: '5210' },
        { key: 'date', label: 'التاريخ', type: 'date', required: true },
        ...dims(),
      ],
      defaults: { cc: 'input:cc', sector: 'input:sector', docIds: [] },
      lines: [
        { side: 'dr', acctFrom: 'input:expenseAcct', amountFrom: 'input:monthly*input:months', partyFrom: 'none' },
        { side: 'cr', acctFrom: 'party.defaultAccount', amountFrom: 'input:monthly*input:months', partyFrom: 'input:party' },
      ],
      descPattern: 'استحقاق مرتب {partyName} عن {months} شهر',
      rule: null,
    },
    {
      id: 'tpl-expense-paid', name: 'مصروف مدفوع', order: 2, active: true,
      inputs: [
        { key: 'expenseAcct', label: 'حساب المصروف', type: 'account', required: true },
        { key: 'payAcct', label: 'الدفع من', type: 'select', required: true, options: ['1320', '1340'] },
        { key: 'amount', label: 'المبلغ', type: 'amount', required: true },
        { key: 'payee', label: 'المستلم', type: 'text', required: false },
        { key: 'ref', label: 'رقم الشيك / المرجع', type: 'text', required: false },
        { key: 'date', label: 'التاريخ', type: 'date', required: true },
        ...dims(),
      ],
      defaults: { cc: 'input:cc', sector: 'input:sector', docIds: [] },
      lines: [
        { side: 'dr', acctFrom: 'input:expenseAcct', amountFrom: 'input:amount', partyFrom: 'none' },
        { side: 'cr', acctFrom: 'input:payAcct', amountFrom: 'input:amount', partyFrom: 'none' },
      ],
      descPattern: 'صرف[ {ref}][ — {payee}]',
      rule: null,
    },
    {
      id: 'tpl-funding', name: 'تمويل من طرف', order: 3, active: true,
      inputs: [
        { key: 'party', label: 'الممول', type: 'party', required: true },
        { key: 'amount', label: 'المبلغ', type: 'amount', required: true },
        { key: 'evidence', label: 'ما الذي يثبته؟', type: 'select', required: true, options: ['bank', 'treasury', 'none'] },
        { key: 'landAcct', label: 'دخل إلى', type: 'select', required: true, options: ['1340', '1320'], default: '1340' },
        { key: 'ref', label: 'المرجع', type: 'text', required: false },
        { key: 'date', label: 'التاريخ', type: 'date', required: true },
        ...dims(),
      ],
      defaults: { cc: 'input:cc', sector: 'input:sector', docIds: [] },
      lines: [
        { side: 'dr', acctFrom: 'input:landAcct', amountFrom: 'input:amount', partyFrom: 'none' },
        { side: 'cr', acctFrom: 'party.defaultAccount', amountFrom: 'input:amount', partyFrom: 'input:party' },
      ],
      descPattern: 'تمويل من {partyName}[ — {ref}]',
      rule: 'cash-funding-evidence',
    },
    {
      id: 'tpl-unknown-deposit', name: 'إيداع غير محدد المصدر', order: 4, active: true,
      inputs: [
        { key: 'amount', label: 'المبلغ', type: 'amount', required: true },
        { key: 'landAcct', label: 'دخل إلى', type: 'select', required: true, options: ['1340', '1320'], default: '1340' },
        { key: 'party', label: 'الطرف («غير محدد»)', type: 'party', required: true },
        { key: 'ref', label: 'المرجع', type: 'text', required: false },
        { key: 'date', label: 'التاريخ', type: 'date', required: true },
        ...dims(),
      ],
      defaults: { cc: 'input:cc', sector: 'input:sector', docIds: [] },
      lines: [
        { side: 'dr', acctFrom: 'input:landAcct', amountFrom: 'input:amount', partyFrom: 'none' },
        { side: 'cr', acctFrom: 'fixed:2160', amountFrom: 'input:amount', partyFrom: 'input:party' },
      ],
      descPattern: 'إيداع غير محدد المصدر[ — {ref}]',
      rule: 'open-item-on-unknown-source',
    },
    {
      id: 'tpl-bank-to-cash', name: 'سحب من البنك للخزينة', order: 5, active: true,
      inputs: [
        { key: 'amount', label: 'المبلغ', type: 'amount', required: true },
        { key: 'ref', label: 'رقم الشيك / المستلم', type: 'text', required: false },
        { key: 'date', label: 'التاريخ', type: 'date', required: true },
        ...dims(),
      ],
      defaults: { cc: 'input:cc', sector: 'input:sector', docIds: [] },
      lines: [
        { side: 'dr', acctFrom: 'fixed:1320', amountFrom: 'input:amount', partyFrom: 'none' },
        { side: 'cr', acctFrom: 'fixed:1340', amountFrom: 'input:amount', partyFrom: 'none' },
      ],
      descPattern: 'سحب من البنك للخزينة[ — {ref}]',
      rule: null,
    },
  ];
  const out = {};
  for (const x of t) out[x.id] = clone(x);
  return out;
}
