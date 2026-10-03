// Dev-only UI kit gallery (served at /__gallery by dev/serve.mjs, never part of dist/index.html).
// Renders every kit component with SYNTHETIC data so dev/shoot.mjs can inspect them in light/dark, desktop/phone.
import { render } from 'preact';
import { useState } from 'preact/hooks';
import { buildSyntheticSeed } from './synthetic-seed.js';
import { ErrorBoundary } from '../src/ui/ErrorBoundary.jsx';
import { setDigitsMode } from '../src/lib/digits.js';
import {
  AccountPicker, Banner, Button, Checkbox, ConfirmDialog, ConfirmHost, DataTable, DateInput, DocPicker, EmptyState, Field, IconButton, Loading,
  Modal, Money, NumberInput, PageHead, PartyPicker, PeriodBanner, Pill, Select, Spinner, Tabs, TextInput, Textarea, ToastHost, YearSelect, confirmAsync, toast,
} from '../src/ui/kit/index.js';

const seed = buildSyntheticSeed();
const accounts = seed.accounts;
const parties = seed.parties;
const documents = seed.documents;
const fiscalYears = seed.fiscalYears;

const rows = [
  { id: 1, acct: '1340', name: 'البنك — حساب جاري', dr: 500000, cr: 0 },
  { id: 2, acct: '1320', name: 'خزينة الورشة', dr: 0, cr: 3200 },
  { id: 3, acct: '2322', name: 'مستحقات الإدارة', dr: 0, cr: 15000.5 },
  { id: 4, acct: '4110', name: 'إيراد مبيعات', dr: 0, cr: 0 },
  { id: 5, acct: '1193', name: 'مجمع إهلاك آلات ومعدات', dr: 0, cr: -9000 },
];
const sum = (k) => rows.reduce((a, r) => a + r[k], 0);

function Section({ title, children }) {
  return (
    <section className="panel" style={{ marginBottom: 16 }}>
      <div className="panel__head"><h2 className="panel__title">{title}</h2></div>
      <div className="panel__body stack">{children}</div>
    </section>
  );
}

function Boom({ armed }) {
  if (armed) throw new Error('انهيار تجريبي لاختبار شاشة الخطأ');
  return <p className="muted">لا خطأ حالياً.</p>;
}

function Gallery() {
  const [boom, setBoom] = useState(false);
  const [acct, setAcct] = useState('1340');
  const [party, setParty] = useState(null);
  const [docs, setDocs] = useState(['D0001']);
  const [amount, setAmount] = useState(12500.5);
  const [date, setDate] = useState('2025-03-05');
  const [tab, setTab] = useState('a');
  const [modal, setModal] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [year, setYear] = useState(2025);
  const [chk, setChk] = useState(true);
  const [sel, setSel] = useState('2');
  return (
    <div className="content" style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div className="stack">
        <PageHead title="معرض مكونات الواجهة" sub="بيانات تجريبية مخترعة" actions={<Button kind="primary" icon="plus">إجراء رئيسي</Button>} />

        <Section title="الأزرار">
          <div className="row">
            <Button kind="primary">ترحيل</Button>
            <Button>مسودة</Button>
            <Button kind="danger">حذف</Button>
            <Button kind="ghost">إلغاء</Button>
            <Button kind="primary" busy>جارٍ الحفظ</Button>
            <Button disabled>معطل</Button>
            <Button size="sm">صغير</Button>
            <IconButton icon="search" label="بحث" outline />
            <IconButton icon="trash" label="حذف" />
          </div>
        </Section>

        <Section title="الحقول">
          <div className="grid-2">
            <Field label="الوصف" hint="مثال: صيانة دورية" id="g-desc">{(p) => <TextInput {...p} value="صيانة دورية للآلة" onChange={() => {}} />}</Field>
            <Field label="المبلغ" id="g-amt" hint="يقبل الأرقام العربية">{(p) => <NumberInput {...p} value={amount} onChange={(v) => setAmount(v)} />}</Field>
            <Field label="التاريخ" id="g-date">{(p) => <DateInput {...p} value={date} onChange={setDate} defaultYear={2025} />}</Field>
            <Field label="الحالة" id="g-sel">{(p) => <Select {...p} value={sel} onChange={setSel} options={[{ value: '1', label: 'مسودة' }, { value: '2', label: 'مرحّل' }, { value: '3', label: 'ملغي' }]} />}</Field>
            <Field label="رقم الشيك" error="هذا الشيك مسجل في قيد سابق" id="g-err" required>{(p) => <TextInput {...p} value="114072" mono onChange={() => {}} />}</Field>
            <Field label="ملاحظة" id="g-note">{(p) => <Textarea {...p} value="" onChange={() => {}} placeholder="اكتب ملاحظة" />}</Field>
            <Field label="مبلغ غير صحيح" id="g-bad">{(p) => <NumberInput {...p} value={null} onChange={() => {}} invalid />}</Field>
            <Field label="السنة" id="g-year">{(p) => <YearSelect {...p} value={year} years={[2025, 2024, 2023]} onChange={setYear} />}</Field>
          </div>
          <div className="row">
            <Checkbox id="g-chk" checked={chk} onChange={setChk} label="يحتاج مراجعة" />
            <Checkbox id="g-chk2" checked={false} onChange={() => {}} label="استبعاد مركز الأمانة" />
          </div>
        </Section>

        <Section title="الاختيار الذكي (حساب، طرف، مستندات)">
          <div className="grid-2">
            <Field label="الحساب" id="g-acct" hint="اكتب 13 أو «بنك»">{(p) => <AccountPicker {...p} accounts={accounts} value={acct} recent={['1340', '1320']} onChange={setAcct} />}</Field>
            <Field label="الطرف" id="g-party">{(p) => <PartyPicker {...p} parties={parties} value={party} onChange={setParty} onCreate={async (name) => `p-${name}`} recent={['p0002']} />}</Field>
            <Field label="المستندات" id="g-docs">{(p) => <DocPicker {...p} documents={documents} value={docs} onChange={setDocs} reuse={['D0003']} onCreate={async () => 'D0004'} />}</Field>
          </div>
        </Section>

        <Section title="منتقي داخل جدول قابل للتمرير">
          <DataTable
            maxHeight="150px"
            ariaLabel="منتقي داخل جدول"
            columns={[
              { key: 'n', header: '#', align: 'center' },
              { key: 'pick', header: 'الحساب', render: (r) => <AccountPicker id={`g-grid-acct-${r.n}`} accounts={accounts} value={null} onChange={() => {}} /> },
              { key: 'amt', header: 'المبلغ', align: 'num', render: () => <Money value={120} /> },
            ]}
            rows={[{ n: 1 }, { n: 2 }, { n: 3 }]}
          />
        </Section>

        <Section title="التبويبات والشارات والتنبيهات">
          <Tabs tabs={[{ id: 'a', label: 'القيود', badge: 12 }, { id: 'b', label: 'المسودات' }, { id: 'c', label: 'الملغاة', badge: 1 }]} value={tab} onChange={setTab} label="عرض" idPrefix="g-tabs">
            <p style={{ paddingBlock: 12 }}>محتوى التبويب المحدد.</p>
          </Tabs>
          <div className="row">
            <Pill>محايد</Pill><Pill kind="accent">للمراجعة</Pill><Pill kind="good" dot>سليم</Pill><Pill kind="warn" dot>ناقص</Pill><Pill kind="critical" dot>غير متوازن</Pill>
          </div>
          <Banner kind="info" title="معلومة">رسالة معلومات عادية.</Banner>
          <Banner kind="good" title="تم">تم الترحيل بنجاح.</Banner>
          <Banner kind="warn" title="تنبيه" actions={<Button size="sm">عرض</Button>}>السنة 2024 مقفلة بتحفظ.</Banner>
          <Banner kind="critical" title="خطأ">القيد غير متوازن — الفرق 1,250.00 (المدين أكبر).</Banner>
        </Section>

        <Section title="حالة الفترة (ثلاث حالات)">
          <PeriodBanner year={2025} fiscalYears={fiscalYears} />
          <PeriodBanner year={2024} fiscalYears={fiscalYears} />
          <PeriodBanner year={2023} fiscalYears={fiscalYears} />
        </Section>

        <Section title="جدول بيانات مع إجمالي">
          <DataTable
            ariaLabel="جدول تجريبي"
            columns={[
              { key: 'acct', header: 'الكود', mono: true, sortable: true },
              { key: 'name', header: 'اسم الحساب', sortable: true },
              { key: 'dr', header: 'مدين', align: 'num', render: (r) => <Money value={r.dr} />, total: () => <Money value={sum('dr')} />, sortable: true },
              { key: 'cr', header: 'دائن', align: 'num', render: (r) => <Money value={r.cr} colorize />, total: () => <Money value={sum('cr')} colorize />, sortable: true },
            ]}
            rows={rows}
            totals
          />
          <div className="row">
            <span>موجب <Money value={1234.5} /></span>
            <span>سالب <Money value={-1234.5} colorize /></span>
            <span>صفر <Money value={0} colorize /></span>
            <span>بالأرقام العربية <Money value={1234567.89} digits="arabic" /></span>
          </div>
          <DataTable columns={[{ key: 'a', header: 'العمود' }]} rows={[]} empty="لا توجد قيود مطابقة" sticky={false} />
        </Section>

        <Section title="حالات فارغة وتحميل">
          <EmptyState icon="file" title="لا توجد مسودات" text="ابدأ قيداً جديداً وسيظهر هنا." action={<Button kind="primary" icon="plus">قيد جديد</Button>} />
          <div className="row"><Spinner /><Spinner small /><Loading text="جارٍ تحميل البيانات…" /></div>
        </Section>

        <Section title="النوافذ والإشعارات">
          <div className="row">
            <Button id="g-open-modal" onClick={() => setModal(true)}>نافذة</Button>
            <Button id="g-open-confirm" onClick={() => setConfirm(true)}>تأكيد بسبب</Button>
            <Button id="g-open-confirm2" onClick={() => confirmAsync({ title: 'حذف المسودة؟', message: 'لا يمكن التراجع عن هذا الإجراء.', danger: true, confirmLabel: 'حذف' }).then((v) => { window.__confirmResult = v; })}>تأكيد بسيط</Button>
            <Button id="g-boom" onClick={() => setBoom(true)}>إثارة خطأ</Button>
            <Button id="g-toast" onClick={() => { toast.success('تم حفظ المسودة'); toast.warn('السنة مقفلة بتحفظ'); toast.error('تعذر الحفظ: انتهت الجلسة'); }}>إشعارات</Button>
          </div>
          <ErrorBoundary key={boom ? 'b' : 'ok'}><Boom armed={boom} /></ErrorBoundary>
        </Section>
      </div>

      <Modal open={modal} onClose={() => setModal(false)} title="بيانات الطرف" footer={<><Button kind="primary" onClick={() => setModal(false)}>حفظ</Button><Button onClick={() => setModal(false)}>إلغاء</Button></>}>
        <Field label="الاسم" id="g-m-name" required>{(p) => <TextInput {...p} value="" onChange={() => {}} />}</Field>
        <Field label="النوع" id="g-m-kind">{(p) => <Select {...p} value="supplier" onChange={() => {}} options={[{ value: 'supplier', label: 'مورد' }, { value: 'bank', label: 'بنك' }]} />}</Field>
      </Modal>
      <ConfirmDialog open={confirm} title="تعديل قيد مرحّل" message="سيُحفظ التعديل كنسخة جديدة مع بقاء النسخة السابقة في السجل." confirmLabel="تعديل" reasonLabel="سبب التعديل" reasonHint="مثال: وصل المستند وتغير المبلغ" onConfirm={() => setConfirm(false)} onCancel={() => setConfirm(false)} />
      <ConfirmHost />
      <ToastHost />
    </div>
  );
}

setDigitsMode('western');
document.documentElement.setAttribute('dir', 'rtl');
document.documentElement.setAttribute('lang', 'ar');
const root = document.getElementById('root');
root.textContent = '';
render(<Gallery />, root);
