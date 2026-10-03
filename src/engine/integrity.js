// Integrity checker. There are no server-side constraints in this app, so every invariant the engine enforces on
// write is ALSO checked here, on load and on demand. checkIntegrity(state) -> [{ severity, code, msg, where }]
// with severity 'error' (the books are wrong), 'warn' (needs a look) or 'info'. `where` is a db path such as
// 'entries/e000312#2' (entry, line 2) or 'fiscalYears/2021' that the UI can link to.
import { toCents, fromCents, formatMoney, isMoney } from '../lib/money.js';
import { isValidISO, fyOf, yearEnd } from '../lib/dates.js';
import {
  CLS, FS_LINE_LIST, PARTY_RULES, PERIOD_STATES, ENTRY_STATUSES, COST_CENTER_KINDS, PARTY_KINDS, OPEN_ITEM_STATUSES,
  ASSUMPTION_STATUSES, CONVENTIONS,
} from './constants.js';
import { coll, isNil, rulesOf, entryIdFor, resolvePartyId, cents } from './util.js';
import { postedLines, balances } from './ledger.js';
import { balanceSheet } from './statements.js';
import { builtinRules } from './templates.js';

const SEV = { error: 0, warn: 1, info: 2 };

/** { error, warn, info, total, ok } counts of a findings list. */
export function summarizeIntegrity(findings) {
  const c = { error: 0, warn: 0, info: 0 };
  for (const f of findings) c[f.severity]++;
  return { ...c, total: findings.length, ok: c.error === 0 };
}

export function checkIntegrity(state, opts = {}) {
  const out = [];
  const add = (severity, code, msg, where = '') => out.push({ severity, code, msg, where });
  const rules = rulesOf(state);
  const accounts = coll(state, 'accounts');
  const entries = coll(state, 'entries');
  const parties = coll(state, 'parties');
  const documents = coll(state, 'documents');
  const costCenters = coll(state, 'costCenters');
  const sectors = coll(state, 'sectors');
  const nowMs = Number.isFinite(Date.parse(opts.now)) ? Date.parse(opts.now) : Date.now();
  const usedByBooked = new Set();
  const noOwners = new Map(); // no -> [entryId]
  let maxNo = 0;
  let latest = null;

  // ------------------------------------------------------------ entries
  for (const [id, e] of Object.entries(entries)) {
    const at = `entries/${id}`;
    if (!e || typeof e !== 'object') {
      add('error', 'entry-malformed', 'مستند قيد غير صالح', at);
      continue;
    }
    if (!ENTRY_STATUSES.includes(e.status)) add('error', 'entry-bad-status', `حالة قيد غير معروفة: ${e.status}`, at);
    const booked = e.status === 'posted' || e.status === 'void';
    if (booked) {
      if (!Number.isInteger(e.no) || e.no < 1) add('error', 'entry-no-missing', 'قيد مرحَّل بلا رقم', at);
      else {
        maxNo = Math.max(maxNo, e.no);
        if (!noOwners.has(e.no)) noOwners.set(e.no, []);
        noOwners.get(e.no).push(id);
        if (id !== entryIdFor(e.no)) add('warn', 'entry-id-mismatch', `معرّف المستند لا يطابق رقم القيد ${e.no}`, at);
      }
      if (!isValidISO(e.date)) add('error', 'entry-bad-date', 'تاريخ القيد غير صالح', at);
      else if (e.fy !== undefined && e.fy !== null && e.fy !== fyOf(e.date)) add('warn', 'entry-fy-mismatch', 'السنة المالية لا تطابق تاريخ القيد', at);
      if (isValidISO(e.date) && (latest === null || e.date > latest)) latest = e.date;
      if (e.status === 'void' && isNil(e.voidReason)) add('warn', 'void-no-reason', 'قيد ملغى بلا سبب', at);
      if (!isNil(e.reversalOf) && !entries[e.reversalOf]) add('warn', 'reversal-orphan', 'القيد العاكس يشير إلى قيد غير موجود', at);
      const amends = (e.history || []).filter((h) => h && (h.kind === 'amend' || h.kind === 'void')).length;
      if (Number.isInteger(e.version) && e.version !== 1 + amends) add('warn', 'version-history-mismatch', `رقم النسخة ${e.version} لا يطابق سجل التعديلات (${amends})`, at);
    } else if (e.status === 'draft') {
      if (!isNil(e.no)) add('warn', 'entry-no-on-draft', 'مسودة تحمل رقم قيد', at);
      const created = Date.parse(e.createdAt);
      if (Number.isFinite(created) && (nowMs - created) / 86400000 > rules.draftMaxAgeDays) {
        add('warn', 'draft-stale', `مسودة أقدم من ${rules.draftMaxAgeDays} أيام`, at);
      }
    }
    const lines = Array.isArray(e.lines) ? e.lines : [];
    if (e.status === 'posted') {
      if (lines.length < 2) add('error', 'entry-few-lines', 'قيد مرحَّل بأقل من سطرين', at);
      let dr = 0;
      let cr = 0;
      for (const l of lines) {
        dr += cents(l.dr);
        cr += cents(l.cr);
      }
      if (dr !== cr) add('error', 'entry-unbalanced', `قيد مرحَّل غير متوازن — الفرق ${formatMoney(fromCents(Math.abs(dr - cr)), { parens: false })}`, at);
    }
    lines.forEach((l, i) => {
      const lw = `${at}#${l && Number.isInteger(l.n) ? l.n : i + 1}`;
      if (!l) return;
      if (booked) usedByBooked.add(String(l.acct));
      if (e.status === 'posted' || e.status === 'void') {
        const a = accounts[l.acct];
        if (!a) add('error', 'line-unknown-account', `كود الحساب ${l.acct} غير موجود`, lw);
        else if (a.postable === false) add('error', 'line-nonpostable-account', `الحساب ${l.acct} حساب رئيسي لا يقبل الترحيل`, lw);
        else if (a.active === false) add('info', 'line-inactive-account', `الحساب ${l.acct} غير نشط`, lw);
        const dr = typeof l.dr === 'number' ? l.dr : Number(l.dr || 0);
        const cr = typeof l.cr === 'number' ? l.cr : Number(l.cr || 0);
        if (!Number.isFinite(dr) || !Number.isFinite(cr) || dr < 0 || cr < 0) add('error', 'line-bad-amount', 'مبلغ غير صالح أو سالب', lw);
        else if (dr > 0 && cr > 0) add('error', 'line-bad-amount', 'سطر يحمل مدين ودائن معاً', lw);
        else if (dr === 0 && cr === 0) add('error', 'line-bad-amount', 'سطر بلا مبلغ', lw);
        else if (!isMoney(dr) || !isMoney(cr)) add('error', 'line-bad-amount', 'أكثر من خانتين عشريتين', lw);
      }
      if (!isNil(l.partyId)) {
        const p = parties[l.partyId];
        if (!p) add('warn', 'orphan-party', `الطرف ${l.partyId} غير موجود`, lw);
        else if (!isNil(p.mergedInto)) add('warn', 'party-merged-not-repointed', `الطرف ${l.partyId} مدموج في ${p.mergedInto} ولم يُعَد توجيه السطر`, lw);
      }
      for (const d of Array.isArray(l.docIds) ? l.docIds : []) if (!documents[d]) add('warn', 'orphan-doc', `المستند ${d} غير موجود`, lw);
      for (const dim of [[isNil(l.cc) ? null : l.cc, costCenters, 'orphan-cc', 'مركز التكلفة'], [isNil(l.sector) ? null : l.sector, sectors, 'orphan-sector', 'القطاع']]) {
        if (dim[0] !== null && !dim[1][dim[0]]) add('warn', dim[2], `${dim[3]} ${dim[0]} غير موجود`, lw);
      }
      for (const k of Array.isArray(l.links) ? l.links : []) {
        const c = k && k.t === 'a' ? 'assumptions' : k && k.t === 'o' ? 'openItems' : null;
        if (!c || !coll(state, c)[String(k.n)]) add('warn', 'orphan-link', `رابط إلى ${k && k.t === 'a' ? 'افتراض' : 'بند'} ${k && k.n} غير موجود`, lw);
      }
    });
    for (const d of Array.isArray(e.docIds) ? e.docIds : []) if (!documents[d]) add('warn', 'orphan-doc', `المستند ${d} غير موجود`, at);
    if (!isNil(e.cc) && !costCenters[e.cc]) add('warn', 'orphan-cc', `مركز التكلفة ${e.cc} غير موجود`, at);
    if (!isNil(e.sector) && !sectors[e.sector]) add('warn', 'orphan-sector', `القطاع ${e.sector} غير موجود`, at);
  }
  for (const [no, ids] of noOwners) {
    if (ids.length > 1) add('error', 'entry-no-duplicate', `رقم القيد ${no} مكرر في ${ids.length} قيود`, ids.map((x) => `entries/${x}`).join(','));
  }

  // ------------------------------------------------------------ counter
  const nextNo = state && state.counters ? state.counters.nextEntryNo : undefined;
  if (!Number.isInteger(nextNo)) add('error', 'counter-invalid', 'عدّاد أرقام القيود غير صالح', 'meta/counters');
  else if (nextNo <= maxNo) add('error', 'counter-behind', `عدّاد أرقام القيود (${nextNo}) لا يتجاوز أكبر رقم مرحَّل (${maxNo})`, 'meta/counters');

  // ------------------------------------------------------------ ledger-level
  const lines = postedLines(state);
  const all = balances({ state, lines });
  if (all.totals.closingDr !== all.totals.closingCr || all.totals.debit !== all.totals.credit) {
    add('error', 'tb-unbalanced', `ميزان المراجعة غير متوازن (مدين ${formatMoney(all.totals.closingDr, { parens: false })} / دائن ${formatMoney(all.totals.closingCr, { parens: false })})`, 'reports/tb');
  }
  if (latest) {
    const bs = balanceSheet({ state, asOf: latest, lines });
    if (!bs.check.balanced) add('error', 'bs-unbalanced', `الميزانية غير متوازنة بتاريخ ${latest} (الفرق ${formatMoney(bs.check.difference, { parens: false })})`, 'reports/bs');
    if (bs.suspense.total !== 0) add('warn', 'suspense-nonzero', `الحسابات الوسيطة غير مصفّرة (${formatMoney(bs.suspense.total, { parens: false })})`, 'reports/bs');
    for (const w of bs.wrongSide) add('info', 'wrong-side-balance', `الحساب ${w.acct} رصيده عكس طبيعته (${formatMoney(w.closing, { parens: false })})`, `accounts/${w.acct}`);
    for (const u of bs.unclassified) add('warn', 'account-unclassified', `الحساب ${u.acct} بلا بند في القوائم المالية`, `accounts/${u.acct}`);
  }

  // ------------------------------------------------------------ accounts
  for (const [code, a] of Object.entries(accounts)) {
    const at = `accounts/${code}`;
    if (!a) continue;
    if (!/^[1-9][0-9]{0,3}$/.test(code)) add('warn', 'account-bad-code', `كود حساب غير مألوف: ${code}`, at);
    const def = CLS[a.cls];
    if (!def) add('warn', 'account-class-unknown', `تصنيف الحساب ${code} غير معروف`, at);
    else {
      if (a.type && a.type !== def.type) add('warn', 'account-class-mismatch', `نوع الحساب ${code} لا يطابق تصنيفه`, at);
      if (a.normal && a.normal !== def.normal) add('warn', 'account-class-mismatch', `طبيعة الحساب ${code} لا تطابق تصنيفه`, at);
    }
    if (a.fsLine && !FS_LINE_LIST.includes(a.fsLine)) add('error', 'account-fsline-invalid', `بند القوائم ${a.fsLine} غير معروف للحساب ${code}`, at);
    if (a.partyRule && !PARTY_RULES.includes(a.partyRule)) add('warn', 'account-partyrule-invalid', `قاعدة الطرف ${a.partyRule} غير معروفة`, at);
    if (a.contra && !isNil(a.contraOf) && !accounts[a.contraOf]) add('warn', 'account-contraof-missing', `الحساب ${code} مقابل لحساب غير موجود (${a.contraOf})`, at);
    if (usedByBooked.has(code) && a.everUsed !== true) add('warn', 'account-everused-false', `الحساب ${code} مستخدم لكن علامة «استُخدم» غير مضبوطة`, at);
    else if (!usedByBooked.has(code) && a.everUsed === true) add('info', 'account-everused-unused', `الحساب ${code} موسوم «استُخدم» ولا توجد قيود مرحَّلة عليه`, at);
  }

  // ------------------------------------------------------------ dimensions and parties
  for (const [id, c] of Object.entries(costCenters)) if (c && !COST_CENTER_KINDS.includes(c.kind)) add('warn', 'cost-center-kind-invalid', `نوع مركز التكلفة ${id} غير معروف`, `costCenters/${id}`);
  for (const [id, p] of Object.entries(parties)) {
    if (!p) continue;
    if (p.kind && !PARTY_KINDS.includes(p.kind)) add('warn', 'party-kind-invalid', `نوع الطرف ${id} غير معروف`, `parties/${id}`);
    if (!isNil(p.mergedInto)) {
      const target = resolvePartyId(state, id);
      if (!parties[p.mergedInto]) add('warn', 'party-merge-broken', `الطرف ${id} مدموج في طرف غير موجود`, `parties/${id}`);
      else if (!parties[target] || !isNil(parties[target].mergedInto)) add('warn', 'party-merge-cycle', `سلسلة دمج الطرف ${id} دائرية`, `parties/${id}`);
    }
    if (!isNil(p.defaultAccount) && !accounts[p.defaultAccount]) add('warn', 'party-default-account-missing', `الحساب الافتراضي للطرف ${id} غير موجود`, `parties/${id}`);
  }

  // ------------------------------------------------------------ fiscal years
  for (const [y, fy] of Object.entries(coll(state, 'fiscalYears'))) {
    const at = `fiscalYears/${y}`;
    if (!fy) continue;
    if (!PERIOD_STATES.includes(fy.state)) {
      add('error', 'year-state-invalid', `حالة السنة ${y} غير معروفة: ${fy.state}`, at);
      continue;
    }
    const year = Number(y);
    if (fy.state === 'open') continue;
    const tb = balances({ state, to: yearEnd(year), lines });
    const live = new Map(tb.rows.filter((r) => r.closing !== 0).map((r) => [r.acct, `${toCents(r.closingDr)}/${toCents(r.closingCr)}`]));
    if (fy.state === 'locked') {
      if (!fy.snapshot) {
        add('error', 'locked-no-snapshot', `السنة ${y} مقفلة نهائياً بلا لقطة ميزان مراجعة`, at);
        continue;
      }
    }
    if (fy.state === 'locked' && fy.snapshot && Number.isInteger(fy.snapshot.revision) && fy.snapshot.revision !== fy.revision) {
      add('error', 'locked-year-revision-changed', `مراجعة السنة ${y} (${fy.revision}) تغيّرت منذ لقطة القفل (${fy.snapshot.revision})`, at);
    }
    if (fy.snapshot) {
      const snap = new Map((fy.snapshot.tb || []).map((r) => [String(r.acct), `${toCents(r.dr)}/${toCents(r.cr)}`]));
      const diffs = [];
      for (const k of new Set([...live.keys(), ...snap.keys()])) if (live.get(k) !== snap.get(k)) diffs.push(k);
      if (diffs.length) {
        if (fy.state === 'locked') add('error', 'locked-year-changed', `السنة ${y} مقفلة نهائياً لكن أرصدتها تغيّرت منذ اللقطة (${diffs.length} حساب: ${diffs.slice(0, 5).join('، ')})`, at);
        else add('info', 'closed-year-differs-from-snapshot', `أرصدة السنة ${y} الحالية تختلف عن لقطة الإقفال في ${diffs.length} حساب`, at);
      }
      const taken = Date.parse(fy.snapshot.takenAt);
      let changed = 0;
      for (const [id, e] of Object.entries(entries)) {
        if (!e || e.fy !== year || !Number.isFinite(taken)) continue;
        const stamps = [e.postedAt, ...(e.history || []).map((h) => h && h.at)].map(Date.parse).filter(Number.isFinite);
        if (stamps.some((t) => t > taken)) {
          changed++;
          if (fy.state === 'locked') add('error', 'locked-year-entry-edited', `قيد في سنة مقفلة نهائياً عُدِّل بعد اللقطة`, `entries/${id}`);
        }
      }
      if (fy.state === 'closed_reserved' && changed) add('info', 'closed-year-changes', `${changed} قيد تغيّر في السنة ${y} منذ الإقفال`, at);
    }
  }

  // ------------------------------------------------------------ possible duplicates (identical entries)
  const groups = new Map();
  for (const [id, e] of Object.entries(entries)) {
    if (!e || e.status !== 'posted' || !isValidISO(e.date)) continue;
    const key = `${e.date}|${(e.lines || []).map((l) => `${l.acct}:${cents(l.dr)}:${cents(l.cr)}:${l.partyId || ''}`).sort().join(';')}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(id);
  }
  for (const ids of groups.values()) {
    if (ids.length > 1) add('warn', 'possible-duplicate', `قيود متطابقة (التاريخ والأسطر): ${ids.map((i) => entries[i].no).join('، ')}`, ids.map((x) => `entries/${x}`).join(','));
  }

  // ------------------------------------------------------------ assets, depreciation runs
  for (const [id, a] of Object.entries(coll(state, 'assets'))) {
    const at = `assets/${id}`;
    if (!a) continue;
    if (!accounts[a.acct]) add('warn', 'asset-account-missing', `حساب الأصل ${a.acct} غير موجود`, at);
    if (!isNil(a.accumAcct) && !accounts[a.accumAcct]) add('warn', 'asset-account-missing', `حساب مجمع الإهلاك ${a.accumAcct} غير موجود`, at);
    if (!isNil(a.expenseAcct) && !accounts[a.expenseAcct]) add('warn', 'asset-account-missing', `حساب مصروف الإهلاك ${a.expenseAcct} غير موجود`, at);
    if (a.convention && !CONVENTIONS.includes(a.convention)) add('warn', 'asset-convention-invalid', `طريقة الإهلاك ${a.convention} غير معروفة`, at);
    if (!isValidISO(a.inServiceDate)) add('warn', 'asset-no-date', 'الأصل بلا تاريخ تشغيل صالح', at);
  }
  for (const [y, run] of Object.entries(coll(state, 'depRuns'))) {
    if (run && run.status === 'posted') {
      const found = Object.values(entries).find((e) => e && e.status === 'posted' && e.no === run.postedEntryNo);
      if (!found) add('warn', 'deprun-entry-missing', `قيد إهلاك سنة ${y} (${run.postedEntryNo}) غير موجود أو ملغى`, `depRuns/${y}`);
    }
  }

  // ------------------------------------------------------------ registers
  for (const [n, it] of Object.entries(coll(state, 'openItems'))) {
    if (it && it.status && !OPEN_ITEM_STATUSES.includes(it.status)) add('warn', 'open-item-bad-status', `حالة البند ${n} غير معروفة`, `openItems/${n}`);
    for (const no of (it && it.linkedEntries) || []) if (!Object.values(entries).some((e) => e && e.no === no)) add('warn', 'linked-entry-missing', `البند ${n} مرتبط بقيد غير موجود (${no})`, `openItems/${n}`);
  }
  for (const [n, it] of Object.entries(coll(state, 'assumptions'))) {
    if (it && it.status && !ASSUMPTION_STATUSES.includes(it.status)) add('warn', 'assumption-bad-status', `حالة الافتراض ${n} غير معروفة`, `assumptions/${n}`);
    for (const no of (it && it.linkedEntries) || []) if (!Object.values(entries).some((e) => e && e.no === no)) add('warn', 'linked-entry-missing', `الافتراض ${n} مرتبط بقيد غير موجود (${no})`, `assumptions/${n}`);
  }
  for (const [id, t] of Object.entries(coll(state, 'templates'))) {
    if (t && t.rule && !builtinRules[t.rule]) add('warn', 'template-rule-unknown', `القالب ${id} يشير إلى قاعدة غير معروفة (${t.rule})`, `templates/${id}`);
  }

  out.sort((a, b) => SEV[a.severity] - SEV[b.severity] || (a.code < b.code ? -1 : a.code > b.code ? 1 : 0) || (a.where < b.where ? -1 : a.where > b.where ? 1 : 0));
  return out;
}
