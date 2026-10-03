import test from 'node:test';
import assert from 'node:assert/strict';
import {
  parseDate, formatDate, fyOf, daysBetween, addDays, compareISO, todayISO, yearStart, yearEnd,
  isValidISO, isLeapYear, daysInYear, monthKey, isBetween, minISO, maxISO,
} from '../../src/lib/dates.js';
import { makeRng } from '../synthetic/rng.js';

test('parseDate accepts the supported shapes', () => {
  assert.equal(parseDate('04/03/2025'), '2025-03-04');
  assert.equal(parseDate('4/3/2025'), '2025-03-04');
  assert.equal(parseDate('4-3-2025'), '2025-03-04');
  assert.equal(parseDate('4.3.2025'), '2025-03-04');
  assert.equal(parseDate('2025-03-04'), '2025-03-04');
  assert.equal(parseDate('2025/3/4'), '2025-03-04');
  assert.equal(parseDate('2025-03-04T10:20:30Z'), '2025-03-04');
  assert.equal(parseDate('٠٤/٠٣/٢٠٢٥'), '2025-03-04');
  assert.equal(parseDate('٢٠٢٥-٠٣-٠٤'), '2025-03-04');
  assert.equal(parseDate(' 31/12/2025 '), '2025-12-31');
  assert.equal(parseDate('1/1/19'), '2019-01-01');
  assert.equal(parseDate('1/1/99'), '1999-01-01');
  assert.equal(parseDate('5/3', { defaultYear: 2022 }), '2022-03-05');
  assert.equal(parseDate('٥/٣', { defaultYear: 2022 }), '2022-03-05');
  assert.equal(parseDate('5/3', { defaultYear: '2022' }), '2022-03-05');
  assert.match(parseDate('5/3'), /^\d{4}-03-05$/);
  assert.equal(parseDate(new Date(2025, 2, 4, 23, 59)), '2025-03-04');
});

test('parseDate rejects invalid input', () => {
  for (const bad of ['', null, undefined, 'abc', '32/1/2025', '29/2/2025', '0/1/2025', '1/13/2025', '2025-02-30', '2025-13-01',
    '12/2025', '1/1/20255', '1/1/202', '31/04/2025', 12345, {}]) {
    assert.equal(parseDate(bad), null, String(bad));
  }
  assert.equal(parseDate('29/2/2024'), '2024-02-29');
  assert.equal(parseDate('29/2/1900'), null); // 1900 is not a leap year
  assert.equal(parseDate('29/2/2000'), '2000-02-29');
});

test('formatDate / fyOf / yearStart / yearEnd', () => {
  assert.equal(formatDate('2025-03-04'), '04/03/2025');
  assert.equal(formatDate('2025-03-04', { digits: 'arabic' }), '٠٤/٠٣/٢٠٢٥');
  assert.equal(formatDate(''), '');
  assert.equal(formatDate(null), '');
  assert.equal(formatDate('nonsense'), '');
  assert.equal(fyOf('2025-12-31'), 2025);
  assert.equal(fyOf('2019-01-01'), 2019);
  assert.equal(fyOf('bad'), null);
  assert.equal(fyOf(null), null);
  assert.equal(yearStart(2022), '2022-01-01');
  assert.equal(yearEnd(2022), '2022-12-31');
  assert.equal(yearStart('2022'), '2022-01-01');
});

test('daysBetween / addDays / compareISO', () => {
  assert.equal(daysBetween('2025-01-01', '2025-01-01'), 0);
  assert.equal(daysBetween('2025-01-01', '2025-12-31'), 364);
  assert.equal(daysBetween('2024-01-01', '2024-12-31'), 365);
  assert.equal(daysBetween('2025-12-31', '2025-01-01'), -364);
  assert.equal(daysBetween('2019-04-15', '2025-12-31'), 2452);
  assert.equal(daysBetween('2023-01-11', '2023-12-31') + 1, 355); // inclusive day count used by depreciation
  assert.equal(addDays('2025-12-31', 1), '2026-01-01');
  assert.equal(addDays('2024-02-28', 1), '2024-02-29');
  assert.equal(addDays('2025-03-01', -1), '2025-02-28');
  assert.equal(addDays('2025-01-01', 0), '2025-01-01');
  assert.equal(addDays('2025-01-01', 365), '2026-01-01');
  assert.equal(compareISO('2025-01-01', '2025-01-02'), -1);
  assert.equal(compareISO('2025-01-02', '2025-01-01'), 1);
  assert.equal(compareISO('2025-01-01', '2025-01-01'), 0);
  assert.equal(compareISO(null, '2025-01-01'), -1);
  assert.equal(compareISO('2025-01-01', null), 1);
  assert.equal(compareISO(null, null), 0);
});

test('todayISO uses the supplied clock with local components', () => {
  assert.equal(todayISO(new Date(2026, 9, 3, 23, 59, 59)), '2026-10-03');
  assert.match(todayISO(), /^\d{4}-\d{2}-\d{2}$/);
});

test('helpers', () => {
  assert.equal(isValidISO('2024-02-29'), true);
  assert.equal(isValidISO('2023-02-29'), false);
  assert.equal(isValidISO('2023-2-1'), false);
  assert.equal(isValidISO(null), false);
  assert.equal(isLeapYear(2024), true);
  assert.equal(isLeapYear(2100), false);
  assert.equal(daysInYear(2024), 366);
  assert.equal(daysInYear(2025), 365);
  assert.equal(monthKey('2026-10-03'), '2026-10');
  assert.equal(isBetween('2025-05-05', '2025-01-01', '2025-12-31'), true);
  assert.equal(isBetween('2024-12-31', '2025-01-01', '2025-12-31'), false);
  assert.equal(isBetween('2025-05-05', null, null), true);
  assert.equal(isBetween('2025-05-05', null, '2025-05-04'), false);
  assert.equal(minISO('2025-01-02', '2025-01-01'), '2025-01-01');
  assert.equal(maxISO('2025-01-02', '2025-01-01'), '2025-01-02');
});

test('property: addDays and daysBetween are inverse; formatDate/parseDate round-trip', () => {
  const rng = makeRng(5);
  for (let i = 0; i < 500; i++) {
    const base = addDays('2019-01-01', rng.int(3000));
    const n = rng.int(2000) - 1000;
    const other = addDays(base, n);
    assert.equal(daysBetween(base, other), n);
    assert.equal(compareISO(base, other), n === 0 ? 0 : Math.sign(-n));
    assert.equal(parseDate(formatDate(base)), base);
    assert.equal(parseDate(formatDate(base, { digits: 'arabic' })), base);
    assert.equal(fyOf(base), Number(base.slice(0, 4)));
  }
});
