import test from 'node:test';
import assert from 'node:assert/strict';
import { toWesternDigits, toArabicDigits, normalizeNumericInput, localizeDigits } from '../../src/lib/digits.js';
import { entryDocId, entryNoOf, isDraftId, newDraftId, nextSeqId, seqOf, deepClone } from '../../src/lib/ids.js';
import { cx, formatInt, formatBytes, normalizeText, matchesTokens, jsonBytes, timeAgo } from '../../src/lib/format.js';
import { fmt, S } from '../../src/lib/i18n.js';

test('digits: Arabic-Indic and Persian digits become Western; separators normalise', () => {
  assert.equal(toWesternDigits('١٢٣٤٥٦٧٨٩٠'), '1234567890');
  assert.equal(toWesternDigits('۱۲۳'), '123');
  assert.equal(normalizeNumericInput('١٬٢٣٤٫٥٠'), '1234.50');
  assert.equal(normalizeNumericInput(' 1,234.50 '), '1234.50');
  assert.equal(normalizeNumericInput('−٥'), '-5');
  assert.equal(toArabicDigits('1,234.50'), '١٬٢٣٤٫٥٠');
  assert.equal(localizeDigits('12', 'arabic'), '١٢');
  assert.equal(localizeDigits('12', 'western'), '12');
});

test('ids: entry and draft ids', () => {
  assert.equal(entryDocId(312), 'e000312');
  assert.equal(entryDocId(1234567), 'e1234567');
  assert.equal(entryNoOf('e000312'), 312);
  assert.equal(entryNoOf('d_abc_1234'), null);
  const d = newDraftId(1700000000000);
  assert.ok(isDraftId(d));
  assert.match(d, /^d_[a-z0-9]+_[a-z0-9]{4}$/);
  assert.equal(nextSeqId(['p0001', 'p0007', 'x'], 'p', 4), 'p0008');
  assert.equal(nextSeqId([], 'D', 4), 'D0001');
  assert.equal(seqOf('D0042', 'D'), 42);
  assert.equal(seqOf('x', 'D'), null);
  const o = { a: [1, { b: 2 }] };
  const c = deepClone(o);
  c.a[1].b = 3;
  assert.equal(o.a[1].b, 2);
});

test('format: cx, numbers, bytes, text normalisation', () => {
  assert.equal(cx('a', false, 'b', { c: true, d: 0 }, ['e']), 'a b c e');
  assert.equal(formatInt(1234567), '1,234,567');
  assert.equal(formatInt(1234567, 'arabic'), '١٬٢٣٤٬٥٦٧');
  assert.equal(formatBytes(512), '512 B');
  assert.equal(formatBytes(2048), '2.0 KiB');
  assert.equal(normalizeText('أَحمد  إبراهيم'), 'احمد ابراهيم');
  assert.equal(normalizeText('مدرسة'), 'مدرسه');
  assert.equal(normalizeText('١٣٤٠'), '1340');
  assert.ok(matchesTokens(normalizeText('بنك كريدي أجريكول'), normalizeText('كريدي بنك')));
  assert.ok(!matchesTokens(normalizeText('خزينة'), normalizeText('بنك')));
  assert.ok(jsonBytes({ a: 'ب' }) > 8);
  assert.equal(timeAgo(new Date(Date.now() - 5000).toISOString()), 'الآن');
});

test('i18n: fmt substitutes placeholders and leaves unknown ones', () => {
  assert.equal(fmt('{a} و {b}', { a: 'س', b: 'ص' }), 'س و ص');
  assert.equal(fmt('{n} عنصر', { n: 3 }), '3 عنصر');
  assert.equal(fmt('{x}', {}), '{x}');
  assert.ok(S.app.title.includes('ستريفا'));
});
