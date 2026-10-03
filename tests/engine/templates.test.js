import test from 'node:test';
import assert from 'node:assert/strict';
import { applyTemplate, builtinRules, defaultTemplates } from '../../src/engine/templates.js';
import { buildState, NOW, USER } from '../synthetic/build-state.js';
import { applyPlan } from '../synthetic/apply-plan.js';

const T = defaultTemplates();
const dims = { docIds: ['D0001'], cc: 'cc1', sector: 'sec2' };
const lineShape = (r) => r.entry.lines.map((l) => [l.acct, l.dr, l.cr, l.partyId]);
const codes = (r) => r.errors.map((e) => e.code);

function withTemplates() {
  const s = buildState();
  s.templates = T;
  return s;
}

test('defaultTemplates: five data rows with the launch names and rules', () => {
  assert.deepEqual(Object.values(T).map((t) => t.name), ['استحقاق مرتب', 'مصروف مدفوع', 'تمويل من طرف', 'إيداع غير محدد المصدر', 'سحب من البنك للخزينة']);
  assert.equal(T['tpl-funding'].rule, 'cash-funding-evidence');
  assert.equal(T['tpl-unknown-deposit'].rule, 'open-item-on-unknown-source');
  assert.deepEqual(Object.keys(builtinRules).sort(), ['cash-funding-evidence', 'open-item-on-unknown-source']);
  // data rows are plain JSON (storable in the db)
  assert.deepEqual(JSON.parse(JSON.stringify(T)), T);
});

test('salary accrual: monthly x months, account and party from the party master, generated description', () => {
  const state = buildState();
  const r = applyTemplate(T['tpl-salary-accrual'], { party: 'p0004', monthly: '12,345.67', months: '3', date: '31/12/2023', ...dims }, { state });
  assert.equal(r.ok, true, JSON.stringify(r.errors));
  assert.deepEqual(lineShape(r), [['5210', 37037.01, 0, null], ['2322', 0, 37037.01, 'p0004']]);
  assert.equal(r.entry.desc, 'استحقاق مرتب موظف تجريبي د عن 3 شهر');
  assert.equal(r.entry.date, '2023-12-31');
  assert.equal(r.entry.fy, 2023);
  assert.equal(r.entry.status, 'draft');
  assert.equal(r.entry.source, 'template:tpl-salary-accrual');
  assert.equal(r.entry.cc, 'cc1');
  assert.equal(r.entry.sector, 'sec2');
  assert.deepEqual(r.entry.docIds, ['D0001']);
  assert.equal(r.validation.ok, true, JSON.stringify(r.validation.errors));
  // default months = 1, Arabic digits accepted, other expense account
  const r2 = applyTemplate(T['tpl-salary-accrual'], { party: 'p0004', monthly: '٥٬٠٠٠٫٥٠', date: '٣١/١٢/٢٠٢٣', expenseAcct: '5250', ...dims }, { state });
  assert.deepEqual(lineShape(r2), [['5250', 5000.5, 0, null], ['2322', 0, 5000.5, 'p0004']]);
});

test('paid expense: optional description segments disappear when empty', () => {
  const state = buildState();
  const full = applyTemplate(T['tpl-expense-paid'], { expenseAcct: '5250', payAcct: '1320', amount: 250, payee: 'سباك تجريبي', ref: '114', date: '2023-12-01', ...dims }, { state });
  assert.equal(full.ok, true, JSON.stringify(full.errors));
  assert.equal(full.entry.desc, 'صرف 114 — سباك تجريبي');
  assert.deepEqual(lineShape(full), [['5250', 250, 0, null], ['1320', 0, 250, null]]);
  const bare = applyTemplate(T['tpl-expense-paid'], { expenseAcct: '5250', payAcct: '1340', amount: 250, date: '2023-12-01', ...dims }, { state });
  assert.equal(bare.entry.desc, 'صرف');
  const noPayee = applyTemplate(T['tpl-expense-paid'], { expenseAcct: '5250', payAcct: '1340', amount: 250, ref: '77', date: '2023-12-01', ...dims }, { state });
  assert.equal(noPayee.entry.desc, 'صرف 77');
});

test('bank to cash', () => {
  const r = applyTemplate(T['tpl-bank-to-cash'], { amount: '1000', ref: 'شيك تجريبي', date: '2023-12-05', ...dims }, { state: buildState() });
  assert.equal(r.ok, true);
  assert.deepEqual(lineShape(r), [['1320', 1000, 0, null], ['1340', 0, 1000, null]]);
  assert.equal(r.entry.desc, 'سحب من البنك للخزينة — شيك تجريبي');
});

test('required inputs and invalid values are reported in Arabic, keyed by input', () => {
  const state = buildState();
  const r = applyTemplate(T['tpl-expense-paid'], { payAcct: '1111', amount: '0', date: '99/99/2023' }, { state });
  assert.equal(r.ok, false);
  assert.deepEqual(r.errors.map((e) => [e.code, e.key]).sort(), [['input-invalid', 'amount'], ['input-invalid', 'date'], ['input-invalid', 'payAcct'], ['input-required', 'expenseAcct']].sort());
  assert.ok(r.errors.find((e) => e.key === 'expenseAcct').msg.includes('مطلوب'));
  const bad = applyTemplate(T['tpl-expense-paid'], { expenseAcct: '9999', payAcct: '1320', amount: 5, date: '2023-12-01' }, { state });
  assert.equal(bad.errors[0].msg.includes('كود غير موجود'), true);
  const nonPost = applyTemplate(T['tpl-expense-paid'], { expenseAcct: '1000', payAcct: '1320', amount: 5, date: '2023-12-01' }, { state });
  assert.equal(nonPost.ok, false);
  const noParty = applyTemplate(T['tpl-salary-accrual'], { monthly: 1, date: '2023-12-01' }, { state });
  assert.ok(codes(noParty).includes('input-required'));
  const unknownParty = applyTemplate(T['tpl-salary-accrual'], { party: 'p9999', monthly: 1, date: '2023-12-01' }, { state });
  assert.ok(codes(unknownParty).includes('input-invalid'));
  assert.equal(applyTemplate('nope', {}, { state }).errors[0].code, 'template-not-found');
  assert.equal(applyTemplate({ ...T['tpl-bank-to-cash'], active: false }, {}, { state }).errors[0].code, 'template-inactive');
});

test('a party without a default account cannot drive an account line', () => {
  const state = buildState();
  const r = applyTemplate(T['tpl-salary-accrual'], { party: 'p0005', monthly: 100, date: '2023-12-01', ...dims }, { state });
  assert.equal(r.ok, false);
  assert.deepEqual(codes(r), ['party-no-default-account']);
});

test('merged parties are resolved to the surviving party', () => {
  const state = buildState();
  state.parties.p0003.defaultAccount = '2110';
  const r = applyTemplate({
    id: 'x', name: 'x', inputs: [{ key: 'party', type: 'party', required: true, label: 'الطرف' }, { key: 'amount', type: 'amount', required: true, label: 'المبلغ' }],
    lines: [{ side: 'dr', acctFrom: 'fixed:5250' }, { side: 'cr', acctFrom: 'party.defaultAccount', partyFrom: 'input:party' }], descPattern: 'مورد {partyName}',
  }, { party: 'p0006', amount: 10, date: '2023-12-01', ...dims }, { state });
  assert.equal(r.ok, true, JSON.stringify(r.errors));
  assert.equal(r.entry.lines[1].partyId, 'p0003');
  assert.equal(r.entry.desc, 'مورد مورد تجريبي ج');
});

test('amount expressions are exact: cost x rate x days / 365 and cost x rate / 2', () => {
  const state = buildState();
  const tpl = (expr) => ({
    id: 'dep', name: 'إهلاك', inputs: [
      { key: 'cost', type: 'amount', required: true, label: 'التكلفة' }, { key: 'rate', type: 'rate', required: true, label: 'النسبة' },
      { key: 'days', type: 'number', required: false, label: 'الأيام' },
    ],
    lines: [{ side: 'dr', acctFrom: 'fixed:5290', amountFrom: expr }, { side: 'cr', acctFrom: 'fixed:1193', amountFrom: expr }],
    descPattern: 'إهلاك',
  });
  const day = applyTemplate(tpl('input:cost*input:rate*input:days/365'), { cost: 3200, rate: '20', days: 355, date: '2023-12-31', ...dims }, { state });
  assert.equal(day.ok, true, JSON.stringify(day.errors));
  assert.equal(day.entry.lines[0].dr, 622.47);
  assert.equal(day.entry.lines[1].cr, 622.47);
  const half = applyTemplate(tpl('input:cost*input:rate/2'), { cost: 822153, rate: 0.05, date: '2023-12-31', ...dims }, { state });
  assert.equal(half.entry.lines[0].dr, 20553.83);
  const missingDays = applyTemplate(tpl('input:cost*input:rate*input:days/365'), { cost: 3200, rate: '20', date: '2023-12-31', ...dims }, { state });
  assert.equal(missingDays.ok, false);
});

test('cash-funding-evidence: bank or treasury evidence keeps cash funding', () => {
  const state = buildState();
  for (const evidence of ['bank', 'treasury']) {
    const r = applyTemplate(T['tpl-funding'], { party: 'p0002', amount: 90000, evidence, landAcct: '1340', date: '2023-12-01', ...dims }, { state });
    assert.equal(r.ok, true, JSON.stringify(r.errors));
    assert.deepEqual(lineShape(r), [['1340', 90000, 0, null], ['2310', 0, 90000, 'p0002']]);
    assert.equal(r.warnings.length, 0);
    assert.equal(r.entry.rerouted, undefined);
  }
});

test('cash-funding-evidence: without evidence the funding is rerouted to the accrual account and flagged', () => {
  const state = buildState(); // config.rules.accrualAccountOf maps 2310 -> 2311
  const r = applyTemplate(T['tpl-funding'], { party: 'p0002', amount: 90000, evidence: 'none', landAcct: '1320', date: '2023-12-01', ...dims }, { state });
  assert.equal(r.ok, true, JSON.stringify(r.errors));
  assert.deepEqual(lineShape(r), [['1320', 90000, 0, null], ['2311', 0, 90000, 'p0002']]);
  const w = r.warnings.find((x) => x.code === 'funding-rerouted');
  assert.ok(w);
  assert.deepEqual(w.rerouted, [{ n: 2, from: '2310', to: '2311' }]);
  assert.equal(r.entry.lines[1].needsReview, true);
  assert.match(r.entry.lines[1].reviewReason, /استحقاقاً/);
  assert.deepEqual(r.entry.rerouted, [{ n: 2, from: '2310', to: '2311' }]);
  assert.equal(r.validation.ok, true, JSON.stringify(r.validation.errors));
  // party-level accrual account, then a template-level one
  const s2 = buildState();
  s2.config.rules.accrualAccountOf = {};
  s2.parties.p0002.accrualAccount = '2160';
  assert.equal(applyTemplate(T['tpl-funding'], { party: 'p0002', amount: 10, evidence: 'none', landAcct: '1340', date: '2023-12-01', ...dims }, { state: s2 }).entry.lines[1].acct, '2160');
  delete s2.parties.p0002.accrualAccount;
  const noMap = applyTemplate(T['tpl-funding'], { party: 'p0002', amount: 10, evidence: 'none', landAcct: '1340', date: '2023-12-01', ...dims }, { state: s2 });
  assert.equal(noMap.ok, false);
  assert.deepEqual(codes(noMap), ['rule-no-accrual-account']);
  const viaTpl = applyTemplate({ ...T['tpl-funding'], ruleOptions: { accrualAcct: '2160' } }, { party: 'p0002', amount: 10, evidence: 'none', landAcct: '1340', date: '2023-12-01', ...dims }, { state: s2 });
  assert.equal(viaTpl.entry.lines[1].acct, '2160');
  // evidence is a required input
  assert.ok(codes(applyTemplate(T['tpl-funding'], { party: 'p0002', amount: 10, landAcct: '1340', date: '2023-12-01' }, { state })).includes('input-required'));
});

test('open-item-on-unknown-source: books the deposit and creates the openItems doc', () => {
  const state = buildState();
  state.openItems = { 5: { n: 5, status: 'open' }, 80: { n: 80, status: 'closed' } };
  state.parties.p0007 = { id: 'p0007', name: 'غير محدد', kind: 'other', aliases: [], roles: [], active: true, mergedInto: null, defaultAccount: null, legacyTexts: [] };
  const r = applyTemplate(T['tpl-unknown-deposit'], { amount: 70000, ref: 'تحويل 5521', party: 'p0007', date: '2023-12-01', ...dims }, { state, user: USER, now: NOW });
  assert.equal(r.ok, true, JSON.stringify(r.errors));
  assert.deepEqual(lineShape(r), [['1340', 70000, 0, null], ['2160', 0, 70000, 'p0007']]);
  assert.deepEqual(r.entry.lines[1].links, [{ t: 'o', n: 81 }]);
  assert.equal(r.entry.lines[1].needsReview, true);
  assert.equal(r.extraWrites.length, 1);
  const w = r.extraWrites[0];
  assert.deepEqual({ op: w.op, path: w.path }, { op: 'set', path: 'openItems/81' });
  assert.equal(w.data.n, 81);
  assert.equal(w.data.status, 'open');
  assert.equal(w.data.year, 2023);
  assert.match(w.data.item, /70,000\.00/);
  assert.match(w.data.item, /01\/12\/2023/);
  assert.equal(w.data.createdBy, USER);
  assert.ok(r.warnings.some((x) => x.code === 'open-item-created'));
});

test('mode "post": the plan creates entry, counters and the open item together; the item links back to the entry', () => {
  const state = buildState();
  state.openItems = { 80: { n: 80, status: 'closed', linkedEntries: [] } };
  state.parties.p0007 = { id: 'p0007', name: 'غير محدد', kind: 'other', aliases: [], roles: [], active: true, mergedInto: null, defaultAccount: null, legacyTexts: [] };
  const r = applyTemplate(T['tpl-unknown-deposit'], { amount: 70000, party: 'p0007', date: '2023-12-01', ...dims }, { state, user: USER, now: NOW, mode: 'post' });
  assert.equal(r.ok, true);
  assert.equal(r.plan.ok, true, JSON.stringify(r.plan.errors));
  assert.equal(r.plan.entryNo, 36);
  const paths = r.plan.writes.map((w) => w.path);
  assert.ok(paths.includes('entries/e000036'));
  assert.equal(paths.includes('meta/counters'), false);
  assert.ok(paths.includes('openItems/81'));
  assert.ok(paths.indexOf('openItems/81') > paths.indexOf('entries/e000036'));
  applyPlan(state, r.plan);
  assert.deepEqual(state.openItems['81'].linkedEntries, [36]);
  assert.equal(state.entries.e000036.lines[1].links[0].n, 81);
  assert.equal(state.entries.e000036.source, 'template:tpl-unknown-deposit');
});

test('mode "post" forwards the number allocated by the repo', () => {
  const state = buildState();
  const r = applyTemplate(T['tpl-bank-to-cash'], { amount: 10, date: '2023-12-05', ...dims }, { state, user: USER, now: NOW, mode: 'post', no: 500 });
  assert.equal(r.plan.ok, true);
  assert.equal(r.plan.entryNo, 500);
  assert.equal(r.plan.writes[0].path, 'entries/e000500');
});

test('mode "draft": the plan saves a draft', () => {
  const state = buildState();
  const r = applyTemplate(T['tpl-bank-to-cash'], { amount: 10, date: '2023-12-05' }, { state, user: USER, now: NOW, mode: 'draft', rand: () => 0.5 });
  assert.equal(r.ok, true);
  assert.equal(r.plan.ok, true);
  assert.match(r.plan.id, /^d_/);
  assert.equal(r.plan.writes[0].data.status, 'draft');
  assert.equal(r.validation.ok, false, 'dimensions are still missing: shown, not enforced, for a draft');
});

test('templates are looked up by id from the state, and unknown rules are reported', () => {
  const state = withTemplates();
  const r = applyTemplate('tpl-bank-to-cash', { amount: 10, date: '2023-12-05', ...dims }, { state });
  assert.equal(r.ok, true);
  const bad = applyTemplate({ ...T['tpl-bank-to-cash'], rule: 'does-not-exist' }, { amount: 10, date: '2023-12-05', ...dims }, { state });
  assert.equal(bad.ok, false);
  assert.deepEqual(codes(bad), ['rule-unknown']);
});

test('a generated entry posts through the normal validation', () => {
  const state = buildState();
  const r = applyTemplate(T['tpl-expense-paid'], { expenseAcct: '5250', payAcct: '1340', amount: 250, date: '2023-12-01', ...dims }, { state, user: USER, now: NOW, mode: 'post' });
  assert.equal(r.plan.ok, true, JSON.stringify(r.plan.errors));
  // 1340 recommends a party: that is a warning that flags the line, not an error
  assert.ok(r.plan.validation.warnings.some((w) => w.code === 'party-recommended'));
  assert.equal(r.plan.writes[0].data.lines[1].needsReview, true);
});
