// Shared vocabulary of the accounting engine: classification table, enums, defaults and Arabic messages.

/** The workbook's 11 account classifications, in presentation order, with the engine defaults they imply. */
export const CLS_ORDER = [
  'أصول',
  'مجمع إهلاك',
  'التزامات',
  'حقوق ملكية',
  'حقوق ملكية مدين',
  'إيرادات',
  'إيرادات مدين',
  'تكلفة مبيعات',
  'مصروفات',
  'مصروفات غير واجبة الخصم',
  'وسيط',
];

export const CLS = {
  'أصول': { type: 'asset', normal: 'D', contra: false, fsLine: 'ASSET' },
  'مجمع إهلاك': { type: 'asset', normal: 'C', contra: true, fsLine: 'ACCUM_DEP' },
  'التزامات': { type: 'liability', normal: 'C', contra: false, fsLine: 'LIABILITY' },
  'حقوق ملكية': { type: 'equity', normal: 'C', contra: false, fsLine: 'CAPITAL' },
  'حقوق ملكية مدين': { type: 'equity', normal: 'D', contra: true, fsLine: 'CAPITAL_CALLED' },
  'إيرادات': { type: 'revenue', normal: 'C', contra: false, fsLine: 'REVENUE' },
  'إيرادات مدين': { type: 'revenue', normal: 'D', contra: true, fsLine: 'REVENUE_CONTRA' },
  'تكلفة مبيعات': { type: 'expense', normal: 'D', contra: false, fsLine: 'COGS' },
  'مصروفات': { type: 'expense', normal: 'D', contra: false, fsLine: 'OPEX' },
  'مصروفات غير واجبة الخصم': { type: 'expense', normal: 'D', contra: false, fsLine: 'NONDEDUCTIBLE' },
  'وسيط': { type: 'suspense', normal: 'C', contra: false, fsLine: 'SUSPENSE' },
};

export const ACCOUNT_TYPES = ['asset', 'liability', 'equity', 'revenue', 'expense', 'suspense'];
export const FS_LINE_LIST = [
  'ASSET', 'ACCUM_DEP', 'LIABILITY', 'CAPITAL', 'CAPITAL_CALLED', 'SETTLEMENT_SHARES', 'RETAINED',
  'REVENUE', 'REVENUE_CONTRA', 'COGS', 'OPEX', 'NONDEDUCTIBLE', 'SUSPENSE',
];
/** fsLines whose movement forms the income statement (and the derived retained earnings). */
export const PL_LINES = new Set(['REVENUE', 'REVENUE_CONTRA', 'COGS', 'OPEX', 'NONDEDUCTIBLE']);
export const EQUITY_LINES = new Set(['CAPITAL', 'CAPITAL_CALLED', 'SETTLEMENT_SHARES', 'RETAINED']);

export const PARTY_RULES = ['none', 'recommended', 'required'];
export const PERIOD_STATES = ['open', 'closed_reserved', 'locked'];
export const ENTRY_STATUSES = ['draft', 'posted', 'void'];
export const COST_CENTER_KINDS = ['own', 'fiduciary'];
export const PARTY_KINDS = [
  'shareholder', 'financier', 'supplier', 'employee', 'government', 'bank', 'customer', 'professional', 'group', 'other',
];
export const OPEN_ITEM_STATUSES = ['open', 'partial', 'closed', 'inquiry'];
export const ASSUMPTION_STATUSES = ['pending', 'met', 'rejected'];
export const CONVENTIONS = ['half_year', 'day_count', 'full_next_year', 'full_year', 'none'];
export const EVIDENCE_GRADES = ['A', 'B', 'C'];

/** Defaults for the optional meta/config.rules block (data, not code: the owner may change them). */
export const DEFAULT_RULES = {
  fundingAccounts: ['2310', '2320', '2330', '2340'],
  evidenceGrades: ['A', 'B'],
  sharedSectorNames: ['مشترك'],
  draftMaxAgeDays: 7,
  maxEntryBytes: 240 * 1024,
  accrualAccountOf: {},
};

/** Arabic user-facing messages. The first group is verbatim from the build spec; do not reword. */
export const MSG = {
  OK: 'سليم',
  INCOMPLETE: 'ناقص — لا يُرحَّل: ينقص رقم المستند / مركز التكلفة / القطاع القانوني',
  NO_AMOUNT: 'بلا مبلغ — أدخل مدين أو دائن',
  BOTH_SIDES: 'السطر يحمل مدين ودائن معاً — اختر جانباً واحداً',
  UNKNOWN_ACCOUNT: 'كود غير موجود',
  UNBALANCED_PREFIX: 'القيد غير متوازن — الفرق',
  DEBIT_LARGER: 'المدين أكبر',
  CREDIT_LARGER: 'الدائن أكبر',
  periodClosed: (y) => `السنة ${y} مقفلة — اطلب إعادة فتحها مع ذكر السبب`,

  // validation (engine-owned wording)
  LINES_MIN: 'القيد يحتاج سطرين على الأقل',
  AMOUNT_NEGATIVE: 'المبلغ لا يقبل قيمة سالبة',
  AMOUNT_INVALID: 'المبلغ غير صالح',
  AMOUNT_DECIMALS: 'المبلغ لا يزيد عن خانتين عشريتين',
  DATE_INVALID: 'تاريخ غير صالح',
  ACCOUNT_NONPOSTABLE: 'حساب رئيسي — لا يقبل الترحيل المباشر',
  ACCOUNT_INACTIVE: 'الحساب غير نشط — لا يُستخدم في قيود جديدة',
  PARTY_REQUIRED: 'ناقص — لا يُرحَّل: ينقص الطرف (مطلوب لهذا الحساب)',
  PARTY_REQUIRED_LEGACY: 'سطر قديم بلا طرف رغم أن الحساب يشترطه — للمراجعة',
  PARTY_RECOMMENDED: 'يُفضَّل تحديد الطرف لهذا الحساب',
  PARTY_UNKNOWN: 'الطرف غير موجود',
  PARTY_MERGED: 'الطرف مدموج في طرف آخر — اختر الطرف الأصلي',
  DOC_UNKNOWN: 'المستند غير موجود في سجل المستندات',
  CC_UNKNOWN: 'مركز التكلفة غير موجود',
  SECTOR_UNKNOWN: 'القطاع القانوني غير موجود',
  CC_INACTIVE: 'مركز التكلفة غير نشط',
  SECTOR_INACTIVE: 'القطاع القانوني غير نشط',
  SECTOR_SHARED: 'القطاع «مشترك» — راجع التوزيع القانوني',
  BEFORE_INCORPORATION: 'التاريخ قبل تأسيس الشركة',
  POSSIBLE_DUPLICATE: 'تشابه محتمل مع قيد سابق (التاريخ والحساب والمبلغ والطرف)',
  FUNDING_NO_EVIDENCE: 'تمويل بلا مستند بنك أو خزينة (درجة أ/ب) — يُسجَّل استحقاقاً لا تمويلاً نقدياً',
  FIDUCIARY_IMBALANCE: 'القيد يمس مركز تكلفة أمانة ولا يتوازن داخله',
  periodLocked: (y) => `السنة ${y} مقفلة نهائياً — لا ترحيل ولا تعديل (فك القفل للمالك فقط)`,
  periodReservedNote: (y) => `السنة ${y} مقفلة بتحفظ — سيُسجَّل التغيير مع السبب`,
  REASON_REQUIRED: 'سبب التعديل مطلوب',
  VERSION_REQUIRED: 'رقم نسخة القيد مطلوب للتحقق من التعارض',
  VERSION_CONFLICT: 'عُدِّل هذا القيد من مستخدم آخر — أعد التحميل ثم أعد المحاولة',
  NOT_FOUND: 'العنصر غير موجود',
  ENTRY_NOT_POSTED: 'القيد غير مرحَّل',
  ENTRY_VOID: 'القيد ملغى — لا يمكن تعديله',
  ENTRY_ALREADY_POSTED: 'القيد مرحَّل بالفعل',
  NO_CHANGES: 'لا توجد تغييرات للحفظ',
  ENTRY_TOO_LARGE: 'سجل تعديلات هذا القيد بلغ الحد الأقصى — اعكس القيد بدلاً من تعديله',
  ALREADY_REVERSED: 'سبق عكس هذا القيد',
  NUMBER_COLLISION: 'رقم القيد التالي مستخدم — أعد تحميل البيانات',
  DRAFTS_PENDING: 'توجد مسودات مؤرخة في هذه السنة — رحِّلها أو احذفها قبل الإقفال',
  TB_UNBALANCED: 'ميزان المراجعة غير متوازن',
  YEAR_ALREADY_CLOSED: 'السنة مقفلة بالفعل',
  YEAR_NOT_OPEN: 'السنة ليست مفتوحة',
  YEAR_ALREADY_OPEN: 'السنة مفتوحة بالفعل',
  YEAR_LOCKED_UNLOCK_FIRST: 'السنة مقفلة نهائياً — يجب فك القفل أولاً',
  YEAR_NOT_LOCKED: 'السنة غير مقفلة نهائياً',
  CLOSE_FIRST: 'أقفل السنة (بتحفظ) أولاً قبل القفل النهائي',
  OWNER_ONLY: 'هذا الإجراء للمالك فقط',
  YEAR_INVALID: 'سنة غير صالحة',
  NOTHING_TO_DEPRECIATE: 'لا يوجد إهلاك مستحق لهذه السنة',
  DEPRUN_POSTED: 'قيد إهلاك هذه السنة مرحَّل بالفعل',
  DRAFT_ONLY: 'هذا الإجراء للمسودات فقط',
};

export const AUDIT_KINDS = [
  'post', 'amend', 'void', 'reverse', 'draft-delete', 'close', 'reopen', 'lock', 'unlock', 'depreciation-propose', 'depreciation-post',
];
