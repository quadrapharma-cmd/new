// Synthetic engine state for tests. EVERYTHING here is invented: company, parties, documents, amounts.
// Account codes/classes follow the chart scheme (configuration, not private data); names are generic.
import { CLS } from '../../src/engine/constants.js';
import { emptyState } from '../../src/engine/state.js';
import { trialBalance, incomeStatement } from '../../src/engine/statements.js';
import { yearStart, yearEnd, addDays } from '../../src/lib/dates.js';
import { fromCents } from '../../src/lib/money.js';

export const NOW = '2024-03-01T10:00:00.000Z';
export const USER = 'u_tester';

/** Account doc from a classification word (type/normal/contra/fsLine come from the class table). */
export function acc(code, name, cls, extra = {}) {
  const d = CLS[cls];
  if (!d) throw new Error(`unknown class ${cls}`);
  return {
    code, name, notes: '', cls, type: d.type, normal: d.normal, contra: d.contra, contraOf: null, fsLine: d.fsLine,
    parent: code.slice(0, 2), postable: true, active: true, partyRule: 'none', everUsed: false, ...extra,
  };
}

export function chartAccounts() {
  const list = [
    acc('1000', 'مجموعة الأصول (تجميعي)', 'أصول', { postable: false, parent: '1' }),
    acc('1120', 'أراضي', 'أصول'),
    acc('1130', 'آلات ومعدات', 'أصول'),
    acc('1140', 'مباني', 'أصول'),
    acc('1150', 'أثاث وتجهيزات', 'أصول'),
    acc('1180', 'مشروعات تحت التنفيذ', 'أصول'),
    acc('1250', 'سلف العاملين', 'أصول', { partyRule: 'required' }),
    acc('1290', 'أرصدة مدينة أخرى', 'أصول', { partyRule: 'required' }),
    acc('1310', 'خزينة رئيسية', 'أصول', { partyRule: 'recommended' }),
    acc('1320', 'خزينة المصنع', 'أصول', { partyRule: 'recommended' }),
    acc('1340', 'حساب البنك', 'أصول', { partyRule: 'recommended' }),
    acc('1191', 'مجمع إهلاك الآلات', 'مجمع إهلاك', { contraOf: '1130' }),
    acc('1192', 'مجمع إهلاك المباني', 'مجمع إهلاك', { contraOf: '1140' }),
    acc('1193', 'مجمع إهلاك الأثاث', 'مجمع إهلاك', { contraOf: '1150' }),
    acc('2110', 'موردون', 'التزامات', { partyRule: 'required' }),
    acc('2130', 'ضرائب ورسوم مستحقة', 'التزامات', { partyRule: 'recommended' }),
    acc('2160', 'أرصدة دائنة أخرى', 'التزامات', { partyRule: 'required' }),
    acc('2310', 'تمويل نقدي من طرف', 'التزامات', { partyRule: 'required' }),
    acc('2311', 'مستحقات الطرف', 'التزامات', { partyRule: 'required' }),
    acc('2322', 'مرتبات مستحقة', 'التزامات', { partyRule: 'required' }),
    acc('3110', 'رأس المال', 'حقوق ملكية'),
    acc('3120', 'رأس المال تحت الطلب', 'حقوق ملكية مدين'),
    acc('3150', 'أرباح مرحلة', 'حقوق ملكية', { fsLine: 'RETAINED' }),
    acc('3211', 'حصص التسوية', 'حقوق ملكية', { fsLine: 'SETTLEMENT_SHARES', partyRule: 'required' }),
    acc('4110', 'مبيعات', 'إيرادات'),
    acc('4130', 'مردودات مبيعات', 'إيرادات مدين'),
    acc('5130', 'تكلفة المبيعات', 'تكلفة مبيعات'),
    acc('5210', 'مرتبات', 'مصروفات'),
    acc('5211', 'مكافآت', 'مصروفات', { active: false }),
    acc('5250', 'صيانة', 'مصروفات'),
    acc('5290', 'مصروف الإهلاك', 'مصروفات'),
    acc('5330', 'غرامات', 'مصروفات غير واجبة الخصم'),
    acc('6110', 'حساب وسيط', 'وسيط'),
  ];
  const out = {};
  for (const a of list) out[a.code] = a;
  return out;
}

export const COST_CENTERS = {
  cc1: { id: 'cc1', name: 'عام', kind: 'own', active: true },
  cc2: { id: 'cc2', name: 'المصنع', kind: 'own', active: true },
  cc3: { id: 'cc3', name: 'أمانة — مشروع خاص', kind: 'fiduciary', active: true },
};
export const SECTORS = {
  sec1: { id: 'sec1', name: 'مشترك', active: true },
  sec2: { id: 'sec2', name: 'داخل ق.72', active: true },
  sec3: { id: 'sec3', name: 'خارج ق.72', active: true },
};

export function parties() {
  return {
    p0001: { id: 'p0001', name: 'شريك تجريبي أ', kind: 'shareholder', aliases: [], roles: [], taxId: '', active: true, mergedInto: null, defaultAccount: '3211', legacyTexts: [] },
    p0002: { id: 'p0002', name: 'ممول تجريبي ب', kind: 'financier', aliases: [], roles: [], taxId: '', active: true, mergedInto: null, defaultAccount: '2310', legacyTexts: [] },
    p0003: { id: 'p0003', name: 'مورد تجريبي ج', kind: 'supplier', aliases: [], roles: [], taxId: '', active: true, mergedInto: null, defaultAccount: '2110', legacyTexts: [] },
    p0004: { id: 'p0004', name: 'موظف تجريبي د', kind: 'employee', aliases: [], roles: [], taxId: '', active: true, mergedInto: null, defaultAccount: '2322', legacyTexts: [] },
    p0005: { id: 'p0005', name: 'بنك تجريبي', kind: 'bank', aliases: [], roles: [], taxId: '', active: true, mergedInto: null, defaultAccount: null, legacyTexts: [] },
    p0006: { id: 'p0006', name: 'مورد تجريبي ج (مكرر)', kind: 'supplier', aliases: [], roles: [], taxId: '', active: false, mergedInto: 'p0003', defaultAccount: null, legacyTexts: [] },
  };
}

export function documents() {
  const d = (id, ref, type, grade, status) => ({ id, ref, type, date: '2020-01-01', grade, status, note: '', files: [], legacyUseCount: 0 });
  return {
    D0001: d('D0001', 'كشف بنك تجريبي', 'bank_statement', 'A', 'received'),
    D0002: d('D0002', 'دفتر خزينة تجريبي', 'cash_book', 'B', 'received'),
    D0003: d('D0003', 'إقرار تجريبي', 'declaration', 'C', 'expected'),
    D0004: d('D0004', 'مذكرة تجريبية', 'memo', null, 'expected'),
  };
}

/**
 * Build an entry doc. spec: { no, date, desc, lines: [[acct, dr, cr, opts?], ...], docIds, cc, sector, status, source,
 * isLegacy, party (default party for lines), voidReason }.
 * line opts: { partyId, memo, cc, sector, docIds, needsReview, links }.
 */
export function makeEntry(spec) {
  const status = spec.status || 'posted';
  const lines = spec.lines.map((l, i) => {
    const [acct, dr, cr, o = {}] = l;
    return {
      n: i + 1, acct, dr: dr || 0, cr: cr || 0, memo: o.memo || '', partyId: o.partyId || null, docIds: o.docIds || [],
      cc: o.cc || null, sector: o.sector || null, valueDate: null, needsReview: !!o.needsReview, reviewReason: o.reviewReason || '',
      links: o.links || [], legacy: null,
    };
  });
  const legacy = !!spec.isLegacy;
  return {
    no: status === 'draft' ? null : spec.no,
    date: spec.date,
    fy: Number(spec.date.slice(0, 4)),
    status,
    desc: spec.desc || '',
    docIds: spec.docIds || ['D0001'],
    cc: spec.cc === undefined ? 'cc1' : spec.cc,
    sector: spec.sector === undefined ? 'sec1' : spec.sector,
    source: spec.source || (legacy ? 'legacy' : 'user'),
    isLegacy: legacy,
    legacyRow: legacy ? 100 + (spec.no || 0) : null,
    version: 1,
    voidReason: spec.voidReason || null,
    reversalOf: spec.reversalOf || null,
    createdBy: USER,
    createdAt: spec.createdAt || `${spec.date}T08:00:00.000Z`,
    postedBy: status === 'draft' ? null : USER,
    postedAt: status === 'draft' ? null : `${spec.date}T09:00:00.000Z`,
    lines,
    history: [],
  };
}

export const entryId = (no) => `e${String(no).padStart(6, '0')}`;

/** The hand-written multi-year history. Hand-verified figures are asserted in tests/engine/statements.test.js. */
export function baseEntrySpecs() {
  const L = (...a) => a;
  return [
    // 2020 (locked)
    { no: 1, date: '2020-01-10', desc: 'إيداع رأس المال', isLegacy: true, lines: [L('1340', 1000000, 0), L('3110', 0, 1000000)] },
    { no: 2, date: '2020-02-01', desc: 'شراء آلات', isLegacy: true, lines: [L('1130', 600000, 0), L('1340', 0, 600000)] },
    { no: 3, date: '2020-03-15', desc: 'تمويل نقدي من الطرف', isLegacy: true, docIds: ['D0002'], lines: [L('1320', 50000, 0), L('2310', 0, 50000, { partyId: 'p0002' })] },
    { no: 4, date: '2020-06-30', desc: 'مرتب مستحق', isLegacy: true, lines: [L('5210', 30000, 0), L('2322', 0, 30000, { partyId: 'p0004' })] },
    { no: 5, date: '2020-07-01', desc: 'مبيعات', isLegacy: true, cc: 'cc2', lines: [L('1340', 200000, 0), L('4110', 0, 200000)] },
    { no: 6, date: '2020-07-05', desc: 'تكلفة مبيعات', isLegacy: true, cc: 'cc2', lines: [L('5130', 80000, 0), L('1340', 0, 80000)] },
    { no: 7, date: '2020-12-31', desc: 'إهلاك 2020', isLegacy: true, docIds: ['D0003'], lines: [L('5290', 60000, 0), L('1191', 0, 60000)] },
    // 2021 (closed with reservations)
    { no: 9, date: '2021-06-06', desc: 'سلفة بلا طرف (قديم)', isLegacy: true, lines: [L('1290', 8000, 0), L('1340', 0, 8000)] },
    { no: 10, date: '2021-01-15', desc: 'مبيعات', isLegacy: true, lines: [L('1340', 300000, 0), L('4110', 0, 300000)] },
    { no: 11, date: '2021-02-10', desc: 'مردودات مبيعات', isLegacy: true, lines: [L('4130', 10000, 0), L('1340', 0, 10000)] },
    { no: 12, date: '2021-03-01', desc: 'صيانة', isLegacy: true, cc: 'cc2', lines: [L('5250', 25000, 0), L('1320', 0, 25000)] },
    { no: 13, date: '2021-05-05', desc: 'وارد أمانة', isLegacy: true, cc: 'cc3', lines: [L('1340', 20000, 0), L('6110', 0, 20000)] },
    { no: 14, date: '2021-05-06', desc: 'صرف أمانة', isLegacy: true, cc: 'cc3', lines: [L('6110', 15000, 0), L('1340', 0, 15000)] },
    { no: 15, date: '2021-12-31', desc: 'إهلاك 2021', isLegacy: true, lines: [L('5290', 60000, 0), L('1191', 0, 60000)] },
    // 2022 (open)
    { no: 16, date: '2022-01-20', desc: 'سلفة موظف', lines: [L('1250', 5000, 0, { partyId: 'p0004' }), L('1320', 0, 5000)] },
    { no: 17, date: '2022-02-02', desc: 'زيادة رأس المال غير المسددة', lines: [L('3120', 100000, 0), L('3110', 0, 100000)] },
    { no: 18, date: '2022-12-31', desc: 'إهلاك 2022', lines: [L('5290', 70000, 0), L('1191', 0, 40000), L('1192', 0, 30000)] },
    // 2023 (open)
    { no: 30, date: '2023-03-03', desc: 'مبيعات', lines: [L('1340', 500000, 0), L('4110', 0, 500000)] },
    { no: 31, date: '2023-04-04', desc: 'مرتب مستحق', lines: [L('5210', 40000, 0), L('2322', 0, 40000, { partyId: 'p0004' })] },
    { no: 32, date: '2023-06-06', desc: 'سداد مرتب', lines: [L('2322', 25000, 0, { partyId: 'p0004' }), L('1340', 0, 25000, { partyId: 'p0005' })] },
    { no: 33, date: '2023-08-08', desc: 'تمويل بنكي', lines: [L('1340', 90000, 0, { partyId: 'p0005' }), L('2310', 0, 90000, { partyId: 'p0002' })] },
    { no: 34, date: '2023-09-09', desc: 'صيانة بالأجل', lines: [L('5250', 12000, 0), L('2110', 0, 12000, { partyId: 'p0003' })] },
    { no: 35, date: '2023-10-10', desc: 'قيد ملغى', status: 'void', voidReason: 'خطأ إدخال', lines: [L('1340', 7000, 0), L('4110', 0, 7000)] },
  ];
}

/** A draft that is deliberately incomplete (no document, no sector, one empty line). */
export function sampleDraft() {
  return makeEntry({
    no: null, status: 'draft', date: '2023-11-11', desc: 'مسودة ناقصة', docIds: [], cc: null, sector: null,
    createdAt: '2024-02-01T08:00:00.000Z',
    lines: [['1340', 1500, 0], ['4110', 0, 0]],
  });
}
export const DRAFT_ID = 'd_lq8x9z_ab12';

/**
 * Full synthetic state: chart with contra / suspense / inactive / non-postable accounts, a fiduciary cost center,
 * 4 fiscal years (2020 locked, 2021 closed_reserved, 2022-2023 open), parties incl. a merged duplicate, a void entry
 * and an incomplete draft. Options: { withDraft = true, withYears = true }.
 */
export function buildState({ withDraft = true, withYears = true } = {}) {
  const s = emptyState();
  s.config = {
    schemaVersion: 1,
    company: { name: 'شركة تجريبية', formerName: '', taxNo: '000-000-000', crNo: '000000', incorporated: '2020-01-05' },
    baseline: null,
    settings: { digits: 'western' },
    rules: { accrualAccountOf: { 2310: '2311' } },
  };
  s.accounts = chartAccounts();
  s.groups = [
    { code: '1', name: 'الأصول', level: 1 }, { code: '2', name: 'الالتزامات', level: 1 }, { code: '3', name: 'حقوق الملكية', level: 1 },
    { code: '4', name: 'الإيرادات', level: 1 }, { code: '5', name: 'التكاليف والمصروفات', level: 1 }, { code: '6', name: 'الحسابات الوسيطة', level: 1 },
  ];
  s.costCenters = JSON.parse(JSON.stringify(COST_CENTERS));
  s.sectors = JSON.parse(JSON.stringify(SECTORS));
  s.parties = parties();
  s.documents = documents();
  let max = 0;
  for (const spec of baseEntrySpecs()) {
    s.entries[entryId(spec.no)] = makeEntry(spec);
    max = Math.max(max, spec.no);
  }
  if (withDraft) s.entries[DRAFT_ID] = sampleDraft();
  s.counters = { nextEntryNo: max + 1 };
  // everUsed is true for every account used by a posted/void line
  for (const e of Object.values(s.entries)) {
    if (e.status === 'draft') continue;
    for (const l of e.lines) if (s.accounts[l.acct]) s.accounts[l.acct].everUsed = true;
  }
  if (withYears) addFiscalYears(s);
  return s;
}

function snapshotOf(state, year) {
  const tb = trialBalance({ state, mode: 'cumulative', asOf: yearEnd(year) });
  return {
    takenAt: `${year + 1}-01-15T08:00:00.000Z`,
    totals: { dr: tb.totals.closingDr, cr: tb.totals.closingCr },
    tb: tb.rows.filter((r) => r.closing !== 0).map((r) => ({ acct: r.acct, dr: r.closingDr, cr: r.closingCr })),
    netResult: incomeStatement({ state, year }).netResult,
  };
}

export function fiscalYearDoc(year, over = {}) {
  return {
    year, state: 'open', startDate: yearStart(year), endDate: yearEnd(year), legalStart: null,
    reservation: { sources: '', notRecorded: '', text: '', lastUpdate: null }, revision: 0, snapshot: null, neededDocs: [],
    closedAt: null, closedBy: null, ...over,
  };
}

export function addFiscalYears(s) {
  s.fiscalYears = {
    2020: fiscalYearDoc(2020, { state: 'locked', snapshot: snapshotOf(s, 2020), closedAt: '2021-01-15T08:00:00.000Z', closedBy: USER, lockedAt: '2021-02-01T08:00:00.000Z', lockedBy: USER }),
    2021: fiscalYearDoc(2021, {
      state: 'closed_reserved', revision: 1, snapshot: snapshotOf(s, 2021), closedAt: '2022-01-15T08:00:00.000Z', closedBy: USER,
      reservation: { sources: 'مصادر تجريبية', notRecorded: 'بنود غير مسجلة تجريبية', text: 'تحفظ تجريبي', lastUpdate: '2022-01-15' },
      neededDocs: [{ text: 'مستند مطلوب تجريبي' }],
    }),
    2022: fiscalYearDoc(2022),
    2023: fiscalYearDoc(2023),
  };
  return s;
}

/** Fresh deep copy so a test can mutate freely. */
export const cloneState = (s) => JSON.parse(JSON.stringify(s));

// ------------------------------------------------------------------ random data for property tests

/** Postable, active accounts of a state. */
export function usableAccounts(state) {
  return Object.values(state.accounts).filter((a) => a.postable && a.active);
}

/**
 * Random balanced entry (2-6 lines) on random usable accounts, amounts in whole cents, dimensions and parties
 * random. Lines are random; one balancing line on the opposite side closes any difference.
 */
export function randomEntry(rng, state, { fromDate = '2020-01-01', toDate = '2023-12-31', no = null, status = 'posted' } = {}) {
  const accts = usableAccounts(state);
  const span = Math.round((Date.parse(`${toDate}T00:00:00Z`) - Date.parse(`${fromDate}T00:00:00Z`)) / 86400000);
  const date = addDays(fromDate, rng.int(span + 1));
  const k = 2 + rng.int(4);
  const lines = [];
  let diffC = 0; // debit - credit, in cents
  const opts = () => {
    const o = {};
    if (rng.chance(0.6)) o.partyId = rng.pick(['p0001', 'p0002', 'p0003', 'p0004', 'p0005']);
    if (rng.chance(0.2)) o.cc = rng.pick(['cc1', 'cc2', 'cc3']);
    if (rng.chance(0.2)) o.sector = rng.pick(['sec1', 'sec2', 'sec3']);
    return o;
  };
  for (let i = 0; i < k; i++) {
    const a = rng.pick(accts);
    const c = 1 + rng.int(5_000_000);
    const isDr = rng.chance(0.5);
    lines.push(isDr ? [a.code, fromCents(c), 0, opts()] : [a.code, 0, fromCents(c), opts()]);
    diffC += isDr ? c : -c;
  }
  if (diffC !== 0) {
    const a = rng.pick(accts);
    lines.push(diffC > 0 ? [a.code, 0, fromCents(diffC), opts()] : [a.code, fromCents(-diffC), 0, opts()]);
  }
  if (lines.length < 2) lines.push(['1340', 0, 0, {}]); // unreachable in practice (k >= 2)
  return makeEntry({
    no, date, status, desc: 'قيد عشوائي', lines, cc: rng.pick(['cc1', 'cc2', 'cc3']), sector: rng.pick(['sec1', 'sec2', 'sec3']),
    docIds: ['D0001'],
  });
}

/** Add n random balanced posted entries with consecutive numbers after the current max. Mutates and returns state. */
export function addRandomEntries(rng, state, n, opts = {}) {
  let no = state.counters.nextEntryNo;
  for (let i = 0; i < n; i++) {
    state.entries[entryId(no)] = randomEntry(rng, state, { ...opts, no });
    no++;
  }
  state.counters.nextEntryNo = no;
  return state;
}
