// SYNTHETIC data for local screenshots and tests: every name and amount here is invented.
// Shape: { collection: { docId: doc } }, the same layout the mock runtime loads.

const acct = (code, name, cls, type, normal, fsLine, extra = {}) => ({
  code, name, notes: '', cls, type, normal, contra: false, contraOf: null, fsLine, parent: code.slice(0, 2) + '00',
  postable: true, active: true, partyRule: 'none', everUsed: true, ...extra,
});

const line = (n, accountCode, dr, cr, memo, extra = {}) => ({
  n, acct: accountCode, dr, cr, memo: memo || '', partyId: null, docIds: [], cc: 'cc_general', sector: 'sec_shared',
  valueDate: null, needsReview: false, reviewReason: '', links: [], ...extra,
});

const entry = (no, date, desc, lines, extra = {}) => ({
  no, date, fy: Number(date.slice(0, 4)), status: 'posted', desc, docIds: ['D0001'], cc: 'cc_general', sector: 'sec_shared',
  source: 'user', isLegacy: false, legacyRow: null, version: 1, voidReason: null, reversalOf: null,
  createdBy: 'u_demo', createdAt: `${date}T09:00:00.000Z`, postedBy: 'u_demo', postedAt: `${date}T09:05:00.000Z`,
  lines, history: [], ...extra,
});

export function buildSyntheticSeed() {
  const accounts = [
    acct('1310', 'خزينة المقر', 'أصول', 'asset', 'D', 'ASSET'),
    acct('1320', 'خزينة الورشة', 'أصول', 'asset', 'D', 'ASSET'),
    acct('1340', 'البنك — حساب جاري', 'أصول', 'asset', 'D', 'ASSET'),
    acct('1290', 'أرصدة مدينة أخرى', 'أصول', 'asset', 'D', 'ASSET', { partyRule: 'recommended' }),
    acct('1180', 'آلات ومعدات', 'أصول', 'asset', 'D', 'ASSET'),
    acct('1193', 'مجمع إهلاك آلات ومعدات', 'مجمع إهلاك', 'asset', 'C', 'ACCUM_DEP', { contra: true, contraOf: '1180' }),
    acct('2130', 'مصروفات مستحقة', 'التزامات', 'liability', 'C', 'LIABILITY'),
    acct('2322', 'مستحقات الإدارة', 'التزامات', 'liability', 'C', 'LIABILITY', { partyRule: 'required' }),
    acct('2340', 'تمويل من أطراف', 'التزامات', 'liability', 'C', 'LIABILITY', { partyRule: 'required' }),
    acct('3110', 'رأس المال', 'حقوق ملكية', 'equity', 'C', 'CAPITAL'),
    acct('4110', 'إيراد مبيعات', 'إيرادات', 'revenue', 'C', 'REVENUE'),
    acct('5210', 'رواتب وأجور', 'مصروفات', 'expense', 'D', 'OPEX'),
    acct('5250', 'صيانة وإصلاح', 'مصروفات', 'expense', 'D', 'OPEX'),
    acct('5290', 'مصروف الإهلاك', 'مصروفات', 'expense', 'D', 'OPEX'),
    acct('5420', 'رسوم بنكية', 'مصروفات', 'expense', 'D', 'OPEX'),
    acct('5211', 'مصروف قديم متوقف', 'مصروفات', 'expense', 'D', 'OPEX', { active: false, everUsed: false }),
    acct('1210', 'حساب جديد لم يُستخدم', 'أصول', 'asset', 'D', 'ASSET', { everUsed: false }),
  ];

  const parties = [
    ['p0001', 'شركة الوادي للمعدات', 'supplier', ['الوادي للمعدات'], null],
    ['p0002', 'مها سليم', 'employee', ['أ/ مها سليم'], '2322'],
    ['p0003', 'مكتب النور للمحاماة', 'professional', [], '2130'],
    ['p0004', 'بنك المثال', 'bank', ['بنك المثال فرع الدقي'], null],
    ['p0005', 'رامز عوض', 'financier', ['ك/ رامز'], '2340'],
    ['p0006', 'المساهمون', 'group', [], null],
  ].map(([id, name, kind, aliases, defaultAccount]) => ({
    id, name, kind, aliases, roles: [], taxId: '', active: true, mergedInto: null, defaultAccount, legacyTexts: [],
  }));

  const documents = [
    ['D0001', 'كشف حساب البنك 2024', 'كشف بنك', '2024-12-31', 'A', 'received'],
    ['D0002', 'دفتر الخزينة اليومي', 'دفتر خزينة', '2024-06-30', 'B', 'expected'],
    ['D0003', 'عقد صيانة الآلات', 'عقد', '2024-03-01', 'B', 'received'],
    ['D0004', 'إقرار إدارة عن المستحقات', 'إقرار', '2025-12-31', 'C', 'expected'],
  ].map(([id, ref, type, date, grade, status]) => ({ id, ref, type, date, grade, status, note: '', files: [], legacyUseCount: 0 }));

  const entries = [
    entry(1, '2023-03-10', 'إيداع رأس المال في البنك', [line(1, '1340', 500000, 0, 'إيداع'), line(2, '3110', 0, 500000, 'رأس المال')]),
    entry(2, '2023-04-02', 'شراء آلة تعبئة', [line(1, '1180', 180000, 0, 'آلة تعبئة'), line(2, '1340', 0, 180000, 'تحويل بنكي')]),
    entry(3, '2023-12-31', 'إهلاك آلات 2023', [line(1, '5290', 9000, 0, 'إهلاك'), line(2, '1193', 0, 9000, 'مجمع إهلاك')], { source: 'depreciation' }),
    entry(4, '2024-01-15', 'مبيعات نقدية', [line(1, '1310', 42500.5, 0, 'تحصيل'), line(2, '4110', 0, 42500.5, 'مبيعات')]),
    entry(5, '2024-02-20', 'صيانة دورية للآلة', [line(1, '5250', 3200, 0, 'صيانة', { partyId: 'p0001' }), line(2, '1320', 0, 3200, 'صرف من الخزينة')]),
    entry(6, '2024-03-31', 'مرتب مستحق لشهر مارس', [line(1, '5210', 15000, 0, 'مرتب'), line(2, '2322', 0, 15000, 'مستحق', { partyId: 'p0002' })]),
    entry(7, '2024-06-05', 'تمويل نقدي من طرف', [line(1, '1320', 25000, 0, 'تمويل'), line(2, '2340', 0, 25000, 'تمويل', { partyId: 'p0005', needsReview: true, reviewReason: 'يحتاج إثبات إيداع' })]),
    entry(8, '2024-12-31', 'إهلاك آلات 2024', [line(1, '5290', 18000, 0, 'إهلاك'), line(2, '1193', 0, 18000, 'مجمع إهلاك')], { source: 'depreciation' }),
    entry(9, '2025-01-12', 'رسوم بنكية', [line(1, '5420', 350.75, 0, 'رسوم'), line(2, '1340', 0, 350.75, 'خصم بنكي', { partyId: 'p0004' })]),
    entry(10, '2025-02-08', 'قيد أُلغي للتصحيح', [line(1, '5250', 1000, 0, ''), line(2, '1320', 0, 1000, '')], { status: 'void', voidReason: 'أُدخل بالخطأ' }),
  ];
  const draft = entry(null, '2025-03-01', 'مسودة صيانة', [line(1, '5250', 800, 0, 'صيانة'), line(2, '1320', 0, 0, '')], {
    status: 'draft', no: null, postedBy: null, postedAt: null, docIds: [], createdAt: new Date().toISOString(),
  });

  const fiscalYears = [
    { year: 2023, state: 'locked', reservation: { sources: 'مستندات داخلية', notRecorded: 'لا شيء', text: 'سنة مقفلة نهائياً بعد المراجعة.', lastUpdate: '2025-01-15' }, revision: 0 },
    { year: 2024, state: 'closed_reserved', reservation: { sources: 'كشف البنك وإقرارات الإدارة', notRecorded: 'مستحقات لم تصل مستنداتها', text: 'مقفلة بتحفظ لحين وصول مستندات المستحقات.\nلا تُصدَّر قوائمها قبل استيفاء الافتراضات.', lastUpdate: '2025-02-10' }, revision: 2 },
    { year: 2025, state: 'open', reservation: { sources: '', notRecorded: '', text: '', lastUpdate: '' }, revision: 0 },
  ].map((y) => ({ ...y, startDate: `${y.year}-01-01`, endDate: `${y.year}-12-31`, legalStart: null, snapshot: null, neededDocs: [], closedAt: null, closedBy: null }));

  const openItems = [
    [1, 2024, 'مستحقات تحتاج مستنداً', 'open'], [2, 2024, 'إيداع بلا مصدر محدد', 'inquiry'], [3, 2023, 'فاتورة قديمة', 'closed'], [4, 2025, 'مطابقة البنك', 'partial'],
  ].map(([n, year, item, status]) => ({ n, year, item, effect: '', docRequired: '', status, closedDocId: null, closedAt: null, linkedEntries: [] }));
  const assumptions = [[1, 'افتراض عمر الآلة', 'pending'], [2, 'افتراض سعر الصرف', 'met'], [3, 'افتراض مصروف شهري', 'pending']].map(([n, text, status]) => ({
    n, text, effect: '', docRequired: '', ifNotReceived: '', status, closedDocId: null, closedAt: null, linkedEntries: [],
  }));

  // flags and snapshots derived from the entries so the synthetic books are internally consistent
  const used = new Set(entries.flatMap((e) => e.lines.map((l) => l.acct)));
  for (const a of accounts) a.everUsed = used.has(a.code);
  const snapshotFor = (year) => {
    const net = new Map();
    for (const e of entries) {
      if (e.status !== 'posted' || e.fy > year) continue;
      for (const l of e.lines) net.set(l.acct, (net.get(l.acct) || 0) + Math.round(l.dr * 100) - Math.round(l.cr * 100));
    }
    const tb = [...net].filter(([, c]) => c !== 0).sort(([a], [b]) => (a < b ? -1 : 1)).map(([acct, c]) => ({ acct, dr: c > 0 ? c / 100 : 0, cr: c < 0 ? -c / 100 : 0 }));
    return { takenAt: `${year + 1}-01-15T10:00:00.000Z`, totals: { dr: tb.reduce((n, r) => n + r.dr, 0), cr: tb.reduce((n, r) => n + r.cr, 0) }, tb, revision: 0 };
  };
  for (const y of fiscalYears) if (y.state !== 'open') y.snapshot = snapshotFor(y.year);

  const toMap = (arr, key) => Object.fromEntries(arr.map((d) => [d[key], d]));
  const entryMap = {};
  for (const e of entries) entryMap[`e${String(e.no).padStart(6, '0')}`] = e;
  entryMap.d_demo_0001 = draft;

  return {
    meta: {
      config: {
        schemaVersion: 1,
        company: { name: 'شركة المثال التجريبية', formerName: '', taxNo: '000-000-000', crNo: '000000', incorporated: '2023-01-01' },
        baseline: { file: 'synthetic-demo', sha256: '0'.repeat(64), importedAt: '2025-03-01T10:00:00.000Z', counts: { entries: entries.length } },
        settings: { digits: 'western' },
      },
      counters: { nextEntryNo: 11 },
      groups: { groups: [{ code: '1000', name: 'الأصول', level: 1 }, { code: '2000', name: 'الالتزامات', level: 1 }] },
    },
    accounts: toMap(accounts, 'code'),
    costCenters: {
      cc_general: { id: 'cc_general', name: 'عام', kind: 'own', active: true },
      cc_plant: { id: 'cc_plant', name: 'الورشة', kind: 'own', active: true },
      cc_trust: { id: 'cc_trust', name: 'أمانة — مشروع خاص', kind: 'fiduciary', active: true },
    },
    sectors: {
      sec_shared: { id: 'sec_shared', name: 'مشترك', active: true },
      sec_in: { id: 'sec_in', name: 'داخل ق.72', active: true },
      sec_out: { id: 'sec_out', name: 'خارج ق.72', active: true },
    },
    parties: toMap(parties, 'id'),
    documents: toMap(documents, 'id'),
    entries: entryMap,
    fiscalYears: toMap(fiscalYears, 'year'),
    openItems: toMap(openItems, 'n'),
    assumptions: toMap(assumptions, 'n'),
    importRuns: { r1: { at: '2025-03-01T10:00:00.000Z', by: 'u_demo', fileSha256: '0'.repeat(64), counts: { entries: entries.length, accounts: accounts.length }, warnings: ['تنبيه تجريبي'], differences: [] } },
    audit: { '2025-03': { events: [{ at: '2025-03-01T10:05:00.000Z', by: 'u_demo', kind: 'post', coll: 'entries', id: 'e000009', reason: '', summary: 'ترحيل قيد تجريبي' }] } },
  };
}
