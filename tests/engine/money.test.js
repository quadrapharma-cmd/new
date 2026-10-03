import test from 'node:test';
import assert from 'node:assert/strict';
import {
  toCents, fromCents, round2, mulDivRound, applyRate, productCents, allocateCents, sumCents, sumMoney,
  formatMoney, parseAmount, isMoney, decimalPlaces,
} from '../../src/lib/money.js';
import { makeRng } from '../synthetic/rng.js';

test('toCents / fromCents basics', () => {
  assert.equal(toCents(0), 0);
  assert.equal(toCents(12.34), 1234);
  assert.equal(toCents(-12.34), -1234);
  assert.equal(toCents(0.1 + 0.2), 30); // float noise is absorbed
  assert.equal(toCents(1.005), 101); // decimal-string half-up, not binary float
  assert.equal(toCents(null), 0);
  assert.equal(toCents(''), 0);
  assert.equal(toCents('12.5'), 1250);
  assert.equal(toCents(1e-7), 0);
  assert.equal(toCents(1e21), 1e23);
  assert.throws(() => toCents(NaN), TypeError);
  assert.throws(() => toCents(Infinity), TypeError);
  assert.equal(fromCents(1234), 12.34);
  assert.equal(fromCents(-5), -0.05);
  assert.equal(Object.is(fromCents(0), 0), true);
  assert.equal(fromCents(toCents(292027.33)), 292027.33);
});

test('round2 is ROUND_HALF_UP (ties away from zero) on the decimal representation', () => {
  // generic half-cent vectors (ties must go up, banker rounding would give .82 / .87)
  assert.equal(round2(20553.825), 20553.83);
  assert.equal(round2(10271.875), 10271.88);
  assert.equal(round2(292027.329), 292027.33);
  assert.equal(round2(2.675), 2.68); // binary float says 2.67499999...
  assert.equal(round2(1.005), 1.01);
  assert.equal(round2(-2.675), -2.68);
  assert.equal(round2(-0.004), 0);
  assert.equal(Object.is(round2(-0.004), 0), true);
  assert.equal(round2(0.1 + 0.2), 0.3);
  assert.equal(round2(5), 5);
});

test('mulDivRound is integer half-up and exact beyond 2^53', () => {
  assert.equal(mulDivRound(100, 1, 2), 50);
  assert.equal(mulDivRound(1, 1, 2), 1); // 0.5 -> 1
  assert.equal(mulDivRound(1, 1, 3), 0);
  assert.equal(mulDivRound(2, 1, 3), 1);
  assert.equal(mulDivRound(-1, 1, 2), -1); // ties away from zero
  assert.equal(mulDivRound(-5, 1, 3), -2);
  assert.equal(mulDivRound(5, -1, 2), -3);
  // 320000 cents * 20% * 355/365 = 62246.575... -> 62247
  assert.equal(mulDivRound(320000, 20 * 355, 100 * 365), 62247);
  // huge product that overflows double precision
  const big = 9_000_000_000_000; // cents
  assert.equal(mulDivRound(big, 999_999_937, 1_000_000_000), 8_999_999_433_000);
  assert.throws(() => mulDivRound(1, 1, 0), RangeError);
  assert.throws(() => mulDivRound(1.5, 1, 2), TypeError);
});

test('applyRate multiplies cents by a decimal rate exactly', () => {
  assert.equal(applyRate(toCents(822153), 0.05, 1, 2), 2055383); // 20,553.825 -> .83
  assert.equal(applyRate(toCents(3200), 0.2, 355, 365), 62247); // 622.47
  assert.equal(applyRate(100, 0.07), 7);
  assert.equal(applyRate(1000, 0.123456, 1, 1), 123); // 123.456 -> 123
  assert.equal(applyRate(1000, '0.2'), 200);
});

test('productCents multiplies and divides decimals exactly', () => {
  assert.equal(productCents([3200, 0.2, 355], [365]), 62247);
  assert.equal(productCents([822153, 0.05], [2]), 2055383);
  assert.equal(productCents([12345.67, 3]), 3703701);
  assert.equal(productCents([100]), 10000);
  assert.equal(productCents([0.1, 3]), 30);
  assert.equal(productCents([-10, 0.5], [3]), -167);
  assert.throws(() => productCents([1], [0]), RangeError);
});

test('allocateCents (largest remainder) always sums to the total', () => {
  assert.deepEqual(allocateCents(100, [1, 1, 1]), [34, 33, 33]);
  assert.deepEqual(allocateCents(10, [1, 1]), [5, 5]);
  assert.deepEqual(allocateCents(0, [3, 2]), [0, 0]);
  assert.deepEqual(allocateCents(1000, [78.15, 12.88, 4, 1.77, 1.6, 1.6]).reduce((a, b) => a + b, 0), 1000);
  assert.deepEqual(allocateCents(-100, [1, 1, 1]), [-34, -33, -33]);
  assert.throws(() => allocateCents(100, [0, 0]), RangeError);
  assert.throws(() => allocateCents(100, [-1, 2]), RangeError);
  const rng = makeRng(7);
  for (let i = 0; i < 300; i++) {
    const n = 1 + rng.int(7);
    const weights = Array.from({ length: n }, () => 1 + rng.int(1000) / 10);
    const total = rng.int(10_000_000);
    const parts = allocateCents(total, weights);
    assert.equal(parts.reduce((a, b) => a + b, 0), total);
    assert.ok(parts.every((p) => Number.isInteger(p) && p >= 0));
  }
});

test('sumCents / sumMoney', () => {
  assert.equal(sumCents([1, 2, 3]), 6);
  assert.equal(sumCents([]), 0);
  assert.throws(() => sumCents([1.5]), TypeError);
  assert.equal(sumMoney([0.1, 0.2, 0.3]), 0.6);
  assert.equal(sumMoney([]), 0);
  assert.equal(sumMoney([1234.5, -234.5]), 1000);
  let acc = 0;
  for (let i = 0; i < 1000; i++) acc += 0.1;
  assert.notEqual(acc, 100); // plain float accumulation drifts
  assert.equal(sumMoney(Array(1000).fill(0.1)), 100);
});

test('formatMoney', () => {
  assert.equal(formatMoney(1234.5), '1,234.50');
  assert.equal(formatMoney(-1234.5), '(1,234.50)');
  assert.equal(formatMoney(-1234.5, { parens: false }), '-1,234.50');
  assert.equal(formatMoney(0), '-');
  assert.equal(formatMoney(0, { zero: '0.00' }), '0.00');
  assert.equal(formatMoney(0.004), '-');
  assert.equal(formatMoney(1000000), '1,000,000.00');
  assert.equal(formatMoney(999.999), '1,000.00');
  assert.equal(formatMoney(12), '12.00');
  assert.equal(formatMoney(0.05), '0.05');
  assert.equal(formatMoney(null), '');
  assert.equal(formatMoney(undefined), '');
  assert.equal(formatMoney(1234.5, { digits: 'arabic' }), '١٬٢٣٤٫٥٠');
  assert.equal(formatMoney(-1234.5, { digits: 'arabic' }), '(١٬٢٣٤٫٥٠)');
});

test('parseAmount accepts Arabic-Indic digits, separators and spaces', () => {
  assert.equal(parseAmount('1234.5'), 1234.5);
  assert.equal(parseAmount('1,234.50'), 1234.5);
  assert.equal(parseAmount('١٢٣٤٫٥٠'), 1234.5);
  assert.equal(parseAmount('١٬٢٣٤٫٥٠'), 1234.5);
  assert.equal(parseAmount('۱۲۳۴.۵'), 1234.5);
  assert.equal(parseAmount(' 1 234 567.8 '), 1234567.8);
  assert.equal(parseAmount('1 234'), 1234);
  assert.equal(parseAmount('‏١٢٣‎'), 123);
  assert.equal(parseAmount('.5'), 0.5);
  assert.equal(parseAmount('5.'), 5);
  assert.equal(parseAmount('-12'), -12);
  assert.equal(parseAmount('−12'), -12);
  assert.equal(parseAmount('(1,234.50)'), -1234.5);
  assert.equal(parseAmount(42), 42);
  assert.equal(parseAmount('٠'), 0);
  assert.equal(parseAmount(''), null);
  assert.equal(parseAmount('   '), null);
  assert.equal(parseAmount(null), null);
  assert.equal(parseAmount('abc'), null);
  assert.equal(parseAmount('1.2.3'), null);
  assert.equal(parseAmount('12-3'), null);
  assert.equal(parseAmount('--5'), null);
  assert.equal(parseAmount(NaN), null);
  assert.equal(parseAmount('1.005'), 1.005);
  assert.equal(parseAmount('1.005', { round: true }), 1.01);
});

test('isMoney / decimalPlaces', () => {
  assert.equal(isMoney(12.34), true);
  assert.equal(isMoney(12), true);
  assert.equal(isMoney(-0.5), true);
  assert.equal(isMoney(12.345), false);
  assert.equal(isMoney(NaN), false);
  assert.equal(isMoney('12'), false);
  assert.equal(isMoney(null), false);
  assert.equal(isMoney(0.1 + 0.2), false);
  assert.equal(decimalPlaces(1.5), 1);
  assert.equal(decimalPlaces(100), 0);
  assert.equal(decimalPlaces(1e-7), 7);
});

test('round-trip property: parse(format(x)) == x for random cents', () => {
  const rng = makeRng(11);
  for (let i = 0; i < 500; i++) {
    const c = rng.int(2_000_000_000) - 1_000_000_000;
    const x = fromCents(c);
    assert.equal(parseAmount(formatMoney(x, { parens: false, zero: '0' })), x);
    assert.equal(parseAmount(formatMoney(x, { parens: true, zero: '0' })), x);
    assert.equal(parseAmount(formatMoney(x, { parens: false, zero: '0', digits: 'arabic' })), x);
    assert.equal(toCents(x), c);
    assert.equal(isMoney(x), true);
  }
});
