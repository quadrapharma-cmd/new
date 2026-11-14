// The EDA website check reads EDA's pages as they are written and says what changed since the last check.
// Offline: every page here is made up; nothing is fetched.
import test from 'node:test';
import assert from 'node:assert/strict';
import { subPages, documents, compare, dateLatest, docKey, likeness, readSite, INDEXES } from '../tools/check-eda-site.mjs';

const dept = '/ar/المرجع-التنظيمي-لهيئة-الدواء-المصرية/الأدلة-التنظيمية/قسم-تجريبي/';
const INDEX = `<nav><a href="/ar/">الرئيسية</a><a href="/ar/المرجع-التنظيمي-لهيئة-الدواء-المصرية/الأدلة-التنظيمية/">الأدلة التنظيمية</a></nav>
<main><a href="${dept}">القسم التجريبي</a> <a href="${encodeURI(dept)}">القسم التجريبي مرة ثانية</a>
<a href="/media/aa11/sample.pdf">ملف</a> <a href="https://elsewhere.example/الأدلة-التنظيمية/x/">موقع آخر</a></main>`;
const NOTICES = `<main><a href="/ar/القوانين/اشعارات-متلقى-الخدمة/قسم-تجريبي-بعنوان-آخر/">نفس القسم بعنوان آخر</a></main>`;
const PAGE = `<h3 class="generic-title">القسم التجريبي</h3>
<p><strong>أدلة تجريبية للاختبار</strong></p>
<table><tbody>
<tr><td><strong>النوع</strong></td><td><strong>تاريخ الإصدار</strong></td><td><strong>الوصف</strong></td><td><strong>رقم الأصدار</strong></td></tr>
<tr><td>دليل تنظيمي</td><td>06-2026</td><td><a rel="noopener" href="/media/aa11/sample-guideline-v-2.pdf" target="_blank">دليل تجريبي أول</a></td><td>02</td></tr>
<tr><td>دليل تنظيمي</td><td>01-2025</td><td><a href="/media/bb22/other-sample-rules.pdf">دليل تجريبي ثانٍ</a></td><td>01</td></tr>
</tbody></table>
<p><strong>إشعارات تجريبية</strong></p>
<p><a href="https://edaegypt.gov.eg/media/cc33/sample-notice.pdf?v=2">إشعار تجريبي</a> <a href="/ar/صفحة/">صفحة</a></p>
<table><tr><td>تاريخ الإصدار</td><td>الأسم</td><td>رقم الإصدار</td></tr>
<tr><td>02/08/2026</td><td><a href="/media/aa11/sample-guideline-v-2.pdf">نفس الدليل مرة ثانية</a></td><td>02</td></tr></table>`;

test('an index page gives its department pages once each, whatever their escaping, and nothing from elsewhere', () => {
  const subs = subPages(INDEX, 'الأدلة-التنظيمية');
  assert.equal(subs.length, 1);
  assert.equal(subs[0].title, 'القسم التجريبي');
  assert.match(decodeURI(subs[0].url), /الأدلة-التنظيمية\/قسم-تجريبي\/$/);
});

test('a department page gives each document once, with the type, date, title and version of its row and the heading above it', () => {
  const docs = documents(PAGE);
  assert.deepEqual(docs.map(d => d.file), ['sample-guideline-v-2.pdf', 'other-sample-rules.pdf', 'sample-notice.pdf']);
  assert.deepEqual(
    { title: docs[0].title, type: docs[0].type, date: docs[0].date, version: docs[0].version, section: docs[0].section },
    { title: 'دليل تجريبي أول', type: 'دليل تنظيمي', date: '06-2026', version: '02', section: 'أدلة تجريبية للاختبار' });
  assert.equal(docs[2].section, 'إشعارات تجريبية');
  assert.equal(docs[2].version, '');
  assert.equal(docKey(docs[2].url), '/media/cc33/sample-notice.pdf');
  assert.equal(docKey('https://www.edaegypt.gov.eg/media/AA11/Sample-Guideline-V-2.pdf'), docKey('https://edaegypt.gov.eg/media/aa11/sample-guideline-v-2.pdf'));
});

test('the sources are told apart: still published, gone from their address (with what looks like them), and the changes since the last check', () => {
  const docs = documents(PAGE).map(d => ({ ...d, page: 'القسم التجريبي' }));
  const sources = [
    { id: 'kept', authority: 'EG-EDA', code: 'GL.TEST.001', version: '2', status: 'in-force', url: 'https://edaegypt.gov.eg/media/aa11/sample-guideline-v-2.pdf', latest: { result: 'current' } },
    { id: 'moved', authority: 'EG-EDA', code: 'GL.TEST.002', version: '1', status: 'in-force', url: 'https://www.edaegypt.gov.eg/media/zz99/other-sample-rules-old.pdf' },
    { id: 'replaced', authority: 'EG-EDA', status: 'superseded', url: 'https://edaegypt.gov.eg/media/yy88/gone.pdf' },
    { id: 'a-tool', authority: 'EG-EDA', status: 'in-force', url: 'https://eservices.edaegypt.gov.eg/SomeTool/' },
    { id: 'not-eda', authority: 'ICH', status: 'in-force', url: 'https://database.ich.org/media/x.pdf' },
  ];
  const previous = { checked_on: '2026-01-01', documents: [docs[0], { ...docs[1], version: '00' }, { url: 'https://edaegypt.gov.eg/media/dd44/withdrawn.pdf', title: 'مسحوب' }] };
  const r = compare({ sources, docs, previous });
  assert.deepEqual(r.published.map(p => p.id), ['kept']);
  assert.deepEqual(r.missing.map(m => m.id), ['moved']);
  assert.deepEqual(r.missing[0].candidates.map(c => c.file), ['other-sample-rules.pdf']);
  assert.deepEqual(r.added.map(d => d.file), ['sample-notice.pdf']);
  assert.deepEqual(r.removed.map(d => d.title), ['مسحوب']);
  assert.deepEqual(r.changed.map(c => [c.before.version, c.now.version]), [['00', '01']]);
  assert.ok(likeness(['variat', 'sixth'], ['variations', 'seventh']) >= 0.5, 'a shortened word still matches its whole');
  assert.equal(compare({ sources, docs, previous: null }).added.length, 0);
});

test('saving dates only the «latest» check of the sources named, and nothing else in the file', () => {
  const Y = '- id: a\n  url: "x"\n  latest: {on: "2026-01-01", where: "w", result: "current"}\n- id: ab\n  latest: {on: "2026-01-01", where: "w", result: "current"}\n- id: c\n  title: t\n';
  const { text, dated } = dateLatest(Y, ['ab', 'c'], '2026-11-14');
  assert.deepEqual(dated, ['ab']);
  assert.equal(text, Y.replace('- id: ab\n  latest: {on: "2026-01-01"', '- id: ab\n  latest: {on: "2026-11-14"'));
});

test('reading the site: the same department under two addresses is read once, and a page without departments stops the check', () => {
  const pages = { [INDEXES[0].url]: INDEX, [INDEXES[1].url]: NOTICES };
  const fetch = url => {
    const k = decodeURI(url);
    if (pages[k]) return pages[k];
    if (/قسم-تجريبي/.test(k)) return PAGE;
    throw new Error(`no page ${k}`);
  };
  const site = readSite(fetch);
  assert.equal(site.pages.length, 1);
  assert.equal(site.docs.length, 3);
  assert.deepEqual(site.failed, []);
  assert.throws(() => readSite(url => (decodeURI(url) === INDEXES[0].url ? '<p>nothing</p>' : NOTICES)), /changed its layout/);
});
