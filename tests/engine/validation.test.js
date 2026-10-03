import test from 'node:test';
import assert from 'node:assert/strict';
import { validateEntry, periodGate, buildDupIndex } from '../../src/engine/validation.js';
import { MSG } from '../../src/engine/constants.js';
import { buildState, makeEntry, entryId } from '../synthetic/build-state.js';

const state = buildState();
const L = (...a) => a;

/** A valid new (non-legacy) entry; override anything. */
function mk(over = {}) {
  return makeEntry({
    no: null, status: 'draft', date: '2023-12-01', desc: 'اختبار', cc: 'cc1', sector: 'sec2', docIds: ['D0001'],
    lines: [L('1340', 100, 0, { partyId: 'p0005' }), L('4110', 0, 100)], ...over,
  });
}
const codes = (list) => list.map((x) => x.code);

test('a complete balanced entry is valid and every chip says «سليم»', () => {
  const v = validateEntry(mk(), { state });
  assert.deepEqual(v.errors, []);
  assert.equal(v.ok, true);
  assert.equal(v.canPost, true);
  assert.equal(v.balanced, true);
  assert.deepEqual(v.lines.map((l) => [l.status, l.chip, l.ok]), [['ok', MSG.OK, true], ['ok', MSG.OK, true]]);
  assert.deepEqual(v.totals, { dr: 100, cr: 100, difference: 0, side: null });
  assert.equal(v.year, 2023);
  assert.equal(v.periodState, 'open');
  assert.deepEqual(v.warnings, []);
});

test('unbalanced: Arabic message names the larger side and the difference', () => {
  const dr = validateEntry(mk({ lines: [L('1340', 1350, 0, { partyId: 'p0005' }), L('4110', 0, 100)] }), { state });
  const e = dr.errors.find((x) => x.code === 'unbalanced');
  assert.equal(e.msg, 'القيد غير متوازن — الفرق 1,250.00 (المدين أكبر)');
  assert.equal(dr.balanced, false);
  assert.deepEqual(dr.totals, { dr: 1350, cr: 100, difference: 1250, side: 'D' });
  const cr = validateEntry(mk({ lines: [L('1340', 100, 0, { partyId: 'p0005' }), L('4110', 0, 100.5)] }), { state });
  assert.equal(cr.errors.find((x) => x.code === 'unbalanced').msg, 'القيد غير متوازن — الفرق 0.50 (الدائن أكبر)');
  assert.equal(cr.totals.side, 'C');
});

test('line statuses use the verbatim workbook messages', () => {
  const v = validateEntry(mk({ lines: [
    L('1340', 100, 100, { partyId: 'p0005' }),
    L('4110', 0, 0),
    L('9999', 50, 0),
    L('4110', 0, 100),
  ] }), { state });
  assert.deepEqual(v.lines.map((l) => l.status), ['both', 'noamount', 'unknown', 'ok']);
  assert.equal(v.lines[0].chip, 'السطر يحمل مدين ودائن معاً — اختر جانباً واحداً');
  assert.equal(v.lines[1].chip, 'بلا مبلغ — أدخل مدين أو دائن');
  assert.equal(v.lines[2].chip, 'كود غير موجود');
  assert.equal(v.lines[3].chip, 'سليم');
  assert.ok(codes(v.errors).includes('amount-both'));
  assert.ok(codes(v.errors).includes('amount-zero'));
  assert.ok(codes(v.errors).includes('account-unknown'));
  assert.equal(v.ok, false);
});

test('missing document / cost center / sector -> incomplete chip with the missing list', () => {
  const v = validateEntry(mk({ docIds: [], cc: null, sector: null }), { state });
  assert.equal(v.lines[0].status, 'incomplete');
  assert.equal(v.lines[0].chip, 'ناقص — لا يُرحَّل: ينقص رقم المستند / مركز التكلفة / القطاع القانوني');
  assert.deepEqual(v.lines[0].missing, ['doc', 'cc', 'sector']);
  assert.equal(v.errors.filter((e) => e.code === 'dim-missing').length, 2);
  // a line-level override satisfies the requirement for that line only
  const partial = validateEntry(mk({ docIds: [], cc: null, sector: 'sec2', lines: [
    L('1340', 100, 0, { partyId: 'p0005', docIds: ['D0001'], cc: 'cc1' }), L('4110', 0, 100),
  ] }), { state });
  assert.equal(partial.lines[0].status, 'ok');
  assert.deepEqual(partial.lines[1].missing, ['doc', 'cc']);
  const onlyDoc = validateEntry(mk({ docIds: [] }), { state });
  assert.deepEqual(onlyDoc.lines[0].missing, ['doc']);
});

test('at least two lines, amounts one-sided / positive / at most 2 decimals', () => {
  assert.ok(codes(validateEntry(mk({ lines: [L('1340', 100, 0, { partyId: 'p0005' })] }), { state }).errors).includes('lines-min'));
  assert.ok(codes(validateEntry(mk({ lines: [] }), { state }).errors).includes('lines-min'));
  const neg = validateEntry(mk({ lines: [L('1340', -100, 0, { partyId: 'p0005' }), L('4110', 0, -100)] }), { state });
  assert.ok(codes(neg.errors).includes('amount-negative'));
  assert.equal(neg.lines[0].chip, MSG.AMOUNT_NEGATIVE);
  const dec = validateEntry(mk({ lines: [L('1340', 10.005, 0, { partyId: 'p0005' }), L('4110', 0, 10.005)] }), { state });
  assert.ok(codes(dec.errors).includes('amount-decimals'));
  const bad = mk();
  bad.lines[0].dr = NaN;
  assert.ok(codes(validateEntry(bad, { state }).errors).includes('amount-invalid'));
});

test('account must exist, be postable and (for new or edited lines) active', () => {
  const np = validateEntry(mk({ lines: [L('1000', 100, 0), L('4110', 0, 100)] }), { state });
  assert.ok(codes(np.errors).includes('account-nonpostable'));
  assert.equal(np.lines[0].chip, MSG.ACCOUNT_NONPOSTABLE);
  const inactive = validateEntry(mk({ lines: [L('5211', 100, 0), L('4110', 0, 100)] }), { state });
  assert.ok(codes(inactive.errors).includes('account-inactive'));
  // the same inactive line, unchanged from the stored entry, is only a warning
  const original = mk({ lines: [L('5211', 100, 0), L('4110', 0, 100)] });
  const unchanged = validateEntry(mk({ lines: [L('5211', 100, 0), L('4110', 0, 100)] }), { state, original });
  assert.equal(codes(unchanged.errors).includes('account-inactive'), false);
  assert.ok(codes(unchanged.warnings).includes('account-inactive'));
});

test('party rule: error on new/edited lines, warning only on unchanged legacy lines', () => {
  const entry = mk({ lines: [L('2110', 0, 100), L('1320', 100, 0, { partyId: 'p0005' })] });
  const v = validateEntry(entry, { state });
  const e = v.errors.find((x) => x.code === 'party-required');
  assert.equal(e.line, 1);
  assert.equal(v.lines[0].status, 'party');
  assert.match(v.lines[0].chip, /^ناقص — لا يُرحَّل/);
  // legacy: the stored entry already has this line without a party -> not blocked, flagged for review
  const stored = mk({ lines: [L('2110', 0, 100), L('1320', 100, 0, { partyId: 'p0005' })] });
  const legacy = validateEntry(JSON.parse(JSON.stringify(stored)), { state, original: stored });
  assert.equal(legacy.errors.length, 0);
  assert.ok(codes(legacy.warnings).includes('party-required-legacy'));
  assert.deepEqual(legacy.suggestedFlags.map((f) => f.n), [1]);
  assert.equal(legacy.suggestedFlags[0].needsReview, true);
  assert.equal(legacy.lines[0].status, 'ok');
  assert.equal(legacy.lines[0].needsReview, true);
  // editing that line (amount changed) makes the rule bind again (and the other line moves with it)
  const edited = JSON.parse(JSON.stringify(stored));
  edited.lines[0].cr = 120;
  edited.lines[1].dr = 120;
  const ev = validateEntry(edited, { state, original: stored });
  assert.ok(codes(ev.errors).includes('party-required'));
  // adding a party fixes it
  edited.lines[0].partyId = 'p0003';
  assert.equal(codes(validateEntry(edited, { state, original: stored }).errors).includes('party-required'), false);
});

test('party recommended (cash/bank) is a warning that sets needs-review; placeholders are not parties', () => {
  const v = validateEntry(mk({ lines: [L('1340', 100, 0), L('4110', 0, 100)] }), { state });
  assert.equal(v.ok, true);
  assert.ok(codes(v.warnings).includes('party-recommended'));
  assert.deepEqual(v.suggestedFlags.map((f) => f.n), [1]);
  const flagged = mk({ lines: [L('1340', 100, 0), L('4110', 0, 100)] });
  flagged.lines[0].needsReview = true;
  assert.deepEqual(validateEntry(flagged, { state }).suggestedFlags, []);
});

test('period states: open, closed_reserved needs a reason, locked refuses', () => {
  const locked = validateEntry(mk({ date: '2020-06-01' }), { state });
  const e = locked.errors.find((x) => x.code === 'period-locked');
  assert.equal(e.msg, MSG.periodLocked(2020));
  assert.equal(locked.periodState, 'locked');
  const closed = validateEntry(mk({ date: '2021-06-01' }), { state });
  assert.equal(closed.errors.find((x) => x.code === 'period-closed').msg, 'السنة 2021 مقفلة — اطلب إعادة فتحها مع ذكر السبب');
  assert.equal(closed.periodState, 'closed_reserved');
  const withReason = validateEntry(mk({ date: '2021-06-01' }), { state, reason: 'وصل المستند' });
  assert.equal(withReason.errors.length, 0);
  assert.ok(codes(withReason.warnings).includes('period-reserved'));
  assert.equal(validateEntry(mk({ date: '2022-06-01' }), { state }).errors.length, 0);
  assert.equal(validateEntry(mk({ date: '2030-06-01' }), { state }).periodState, 'open', 'a year with no doc is open');
  const noDate = validateEntry(mk({ date: '' }), { state });
  assert.ok(codes(noDate.errors).includes('date-invalid'));
  assert.equal(noDate.year, null);
  const lockedWithReason = validateEntry(mk({ date: '2020-06-01' }), { state, reason: 'x' });
  assert.ok(codes(lockedWithReason.errors).includes('period-locked'), 'a reason never overrides a lock');
});

test('periodGate', () => {
  assert.deepEqual(periodGate(state, 2022, {}), { ok: true, year: 2022, periodState: 'open', bump: false, revision: 0 });
  const g = periodGate(state, 2021, {});
  assert.equal(g.ok, false);
  assert.equal(g.code, 'period-closed');
  const g2 = periodGate(state, 2021, { reason: 'سبب' });
  assert.equal(g2.ok, true);
  assert.equal(g2.bump, true);
  assert.equal(g2.revision, 1);
  assert.equal(periodGate(state, 2020, { reason: 'سبب' }).code, 'period-locked');
  assert.equal(periodGate(state, null, {}).code, 'date-invalid');
});

test('warnings: before incorporation, shared sector, possible duplicate, funding evidence, fiduciary imbalance', () => {
  const early = validateEntry(mk({ date: '2019-12-31' }), { state });
  assert.ok(codes(early.warnings).includes('before-incorporation'));
  const shared = validateEntry(mk({ sector: 'sec1' }), { state });
  assert.ok(codes(shared.warnings).includes('sector-shared'));
  assert.equal(codes(validateEntry(mk({ sector: 'sec3' }), { state }).warnings).includes('sector-shared'), false);

  // duplicate of entry 30 (same date, accounts, amounts, party)
  const dup = mk({ date: '2023-03-03', lines: [L('1340', 500000, 0), L('4110', 0, 500000)] });
  const dv = validateEntry(dup, { state });
  const w = dv.warnings.find((x) => x.code === 'possible-duplicate');
  assert.ok(w);
  assert.deepEqual(w.refs, [30]);
  // the stored entry itself is not a duplicate of itself
  const self = JSON.parse(JSON.stringify(state.entries[entryId(30)]));
  assert.equal(codes(validateEntry(self, { state, id: entryId(30) }).warnings).includes('possible-duplicate'), false);

  // funding account without grade A/B evidence
  const fund = (docIds) => validateEntry(mk({ docIds, lines: [L('1320', 100, 0, { partyId: 'p0005' }), L('2310', 0, 100, { partyId: 'p0002' })] }), { state });
  assert.ok(codes(fund(['D0003']).warnings).includes('funding-no-evidence'));
  assert.ok(codes(fund(['D0004']).warnings).includes('funding-no-evidence'));
  assert.equal(codes(fund(['D0001']).warnings).includes('funding-no-evidence'), false);
  assert.equal(codes(fund(['D0002']).warnings).includes('funding-no-evidence'), false);
  assert.equal(codes(fund(['D0003', 'D0002']).warnings).includes('funding-no-evidence'), false);

  // fiduciary: lines in the trust center must net to zero inside it
  const fid = validateEntry(mk({ lines: [L('1340', 100, 0, { partyId: 'p0005', cc: 'cc3' }), L('4110', 0, 100)] }), { state });
  const fw = fid.warnings.find((x) => x.code === 'fiduciary-imbalance');
  assert.ok(fw);
  assert.equal(fid.ok, true, 'a warning only');
  const fidOk = validateEntry(mk({ cc: 'cc3', lines: [L('1340', 100, 0, { partyId: 'p0005' }), L('6110', 0, 100)] }), { state });
  assert.equal(codes(fidOk.warnings).includes('fiduciary-imbalance'), false);
});

test('unknown references are errors; merged or inactive ones are warnings', () => {
  const v = validateEntry(mk({ cc: 'ccX', sector: 'secX', docIds: ['D9999'], lines: [L('1340', 100, 0, { partyId: 'p9999' }), L('4110', 0, 100)] }), { state });
  for (const c of ['cc-unknown', 'sector-unknown', 'doc-unknown', 'party-unknown']) assert.ok(codes(v.errors).includes(c), c);
  const merged = validateEntry(mk({ lines: [L('1340', 100, 0, { partyId: 'p0006' }), L('4110', 0, 100)] }), { state });
  assert.equal(merged.errors.length, 0);
  assert.ok(codes(merged.warnings).includes('party-merged'));
  const s2 = buildState();
  s2.costCenters.cc1.active = false;
  assert.ok(codes(validateEntry(mk(), { state: s2 }).warnings).includes('cc-inactive'));
});

test('validation works on an empty state and does not mutate its input', () => {
  const e = mk();
  const before = JSON.stringify(e);
  const v = validateEntry(e, { state: {} });
  assert.equal(JSON.stringify(e), before);
  assert.ok(codes(v.errors).includes('account-unknown'));
  const v2 = validateEntry(e);
  assert.ok(v2.errors.length > 0);
});

test('dupIndex can be supplied for speed and gives the same answer', () => {
  const idx = buildDupIndex(state);
  const dup = mk({ date: '2023-03-03', lines: [L('1340', 500000, 0), L('4110', 0, 500000)] });
  assert.deepEqual(validateEntry(dup, { state, dupIndex: idx }).warnings, validateEntry(dup, { state }).warnings);
});
