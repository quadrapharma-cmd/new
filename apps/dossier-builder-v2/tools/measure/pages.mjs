// Made-up scanned pages with a known truth, for measuring the readers (step 2.0d). Every name, number and company here is
// invented. Each page is drawn by the browser from HTML and then «scanned»: straight, skewed 3°, sideways (90°) and faint with
// noise. Writes .cache/measure/pages/<page>-<variant>.png and truth.json (the facts each page holds, as a reader must give them).
//   node tools/measure/pages.mjs
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const OUT = path.join(ROOT, '.cache', 'measure', 'pages');
const require = createRequire(import.meta.url);

const STAMP = (text, color = '#1d3f8f') => `<div style="position:absolute;right:90px;bottom:120px;width:150px;height:150px;border:4px double ${color};
  border-radius:50%;color:${color};display:flex;align-items:center;justify-content:center;text-align:center;font:bold 15px serif;
  transform:rotate(-14deg);opacity:.75">${text}</div>`;
const SIGN = `<svg style="position:absolute;left:120px;bottom:150px" width="220" height="70"><path d="M5 50 C 40 5, 60 70, 95 30 S 150 10, 170 45 S 205 60, 215 20"
  stroke="#20307a" stroke-width="3" fill="none"/></svg>`;

// Each page: its HTML body, its direction, and the facts a reader must return (written as they are on the page).
export const PAGES = {
  'notice-ar': {
    dir: 'rtl',
    facts: ['إخطار تسجيل نهائي', 'تيستافين', 'أقراص مغلفة', 'باراسيتامول', '٥٠٠ مجم', '١٢٣٤٥/٢٠٢٥', '١٥/٠٣/٢٠٢٥',
            'شركة النيل التجريبية للأدوية', 'Testaphen', '36 شهر', 'علبة كرتون بها ٢ شريط × ١٠ أقراص'],
    html: `<div style="text-align:center;font:bold 26px serif">جمهورية مصر العربية<br>هيئة الدواء المصرية</div>
      <h2 style="text-align:center;font:bold 30px serif;margin:28px 0">إخطار تسجيل نهائي</h2>
      <p style="font:20px/1.9 serif">السادة / شركة النيل التجريبية للأدوية<br>تحية طيبة وبعد،<br>
      نفيد سيادتكم بأن اللجنة الفنية قررت الموافقة على تسجيل المستحضر الآتي برقم تسجيل <b>١٢٣٤٥/٢٠٢٥</b> بتاريخ <b>١٥/٠٣/٢٠٢٥</b>:</p>
      <table style="width:100%;border-collapse:collapse;font:19px serif" border="1" cellpadding="8">
       <tr><td>اسم المستحضر</td><td>تيستافين (Testaphen)</td></tr>
       <tr><td>الشكل الصيدلي</td><td>أقراص مغلفة</td></tr>
       <tr><td>المادة الفعالة</td><td>باراسيتامول ٥٠٠ مجم</td></tr>
       <tr><td>العبوة</td><td>علبة كرتون بها ٢ شريط × ١٠ أقراص</td></tr>
       <tr><td>مدة الصلاحية</td><td>36 شهر</td></tr></table>
      <p style="font:20px serif;margin-top:40px">وتفضلوا بقبول فائق الاحترام،</p>${STAMP('هيئة الدواء<br>المصرية<br>الإدارة المركزية')}${SIGN}`,
  },
  'spec-en': {
    dir: 'ltr',
    facts: ['Finished Product Specification', 'Testaphen 500 mg film-coated tablets', 'Assay', '95.0 - 105.0 %', 'Dissolution',
            'Q = 80 % in 30 minutes', 'Related substances', 'Any unspecified impurity: NMT 0.10 %', 'Water content', 'NMT 5.0 % w/w',
            'Batch TP-24A117'],
    html: `<h2 style="font:bold 26px sans-serif">Finished Product Specification</h2>
      <p style="font:18px sans-serif">Product: Testaphen 500 mg film-coated tablets &nbsp;·&nbsp; Batch TP-24A117 &nbsp;·&nbsp; Nile Test Pharma (made up)</p>
      <table style="width:100%;border-collapse:collapse;font:17px sans-serif" border="1" cellpadding="7">
       <tr style="font-weight:bold"><td>Test</td><td>Acceptance criteria</td><td>Method</td></tr>
       <tr><td>Appearance</td><td>White, round, film-coated tablet</td><td>Visual</td></tr>
       <tr><td>Assay</td><td>95.0 - 105.0 % of the labelled amount</td><td>HPLC</td></tr>
       <tr><td>Dissolution</td><td>Q = 80 % in 30 minutes</td><td>USP &lt;711&gt;</td></tr>
       <tr><td>Related substances</td><td>Any unspecified impurity: NMT 0.10 %</td><td>HPLC</td></tr>
       <tr><td>Water content</td><td>NMT 5.0 % w/w</td><td>KF</td></tr></table>`,
  },
  'gmp-en': {
    dir: 'ltr',
    facts: ['Certificate of GMP Compliance', 'No. GMP-2025/0417', 'Testland Medicines Agency', 'Delta Test Manufacturing Co.',
            '14 Industrial Zone, Port Example', 'tablets, capsules, oral powders', '02 June 2025', '01 June 2028'],
    html: `<div style="text-align:center;font:bold 22px serif">Testland Medicines Agency</div>
      <h2 style="text-align:center;font:bold 28px serif">Certificate of GMP Compliance</h2>
      <p style="text-align:center;font:18px serif">No. GMP-2025/0417</p>
      <p style="font:19px/1.8 serif">This is to certify that <b>Delta Test Manufacturing Co.</b>, 14 Industrial Zone, Port Example, was inspected and
      complies with Good Manufacturing Practice for the manufacture of: tablets, capsules, oral powders.</p>
      <p style="font:19px serif">Date of issue: 02 June 2025 &nbsp;&nbsp; Valid until: 01 June 2028</p>${STAMP('TESTLAND<br>MEDICINES<br>AGENCY', '#7a1d1d')}${SIGN}`,
  },
  'letter-mixed': {
    dir: 'rtl',
    facts: ['Request Decision Letter', 'Testaphen', 'Film-coated tablets', 'Nile Test Pharma', 'Delta Test Manufacturing Co.', '٢٠٢٥/٥/٢٠',
            'الإدارة العامة للثبات', 'بالإشارة إلى الطلب المقدم من سيادتكم'],
    html: `<div style="font:bold 20px serif">جمهورية مصر العربية<br>هيئة الدواء المصرية<br>الإدارة العامة للثبات</div>
      <h2 style="text-align:center;font:bold 24px sans-serif;direction:ltr">Request Decision Letter</h2>
      <p style="font:19px serif">التاريخ: ٢٠٢٥/٥/٢٠<br>بالإشارة إلى الطلب المقدم من سيادتكم بخصوص المستحضر الآتي:</p>
      <table style="width:100%;border-collapse:collapse;font:17px sans-serif;direction:ltr" border="1" cellpadding="7">
       <tr><td>Product Name</td><td>Testaphen</td></tr><tr><td>Dosage Form</td><td>Film-coated tablets</td></tr>
       <tr><td>Applicant</td><td>Nile Test Pharma</td></tr><tr><td>Manufacturer</td><td>Delta Test Manufacturing Co.</td></tr></table>
      <p style="font:19px serif">نحيط سيادتكم علماً بالموافقة على تعديل المواصفة المقترحة.</p>${STAMP('الإدارة العامة<br>للثبات')}`,
  },
};

// How a page is «scanned»: the drawn sheet is turned and dimmed the way a scanner leaves it, then grain is laid over it.
export const VARIANTS = {
  clean: { rotate: 0, filter: 'none', noise: 0 },
  skew3: { rotate: 3, filter: 'none', noise: 0.04 },
  rot90: { rotate: 90, filter: 'none', noise: 0.03 },
  faint: { rotate: 1, filter: 'contrast(0.55) brightness(1.18) blur(0.6px)', noise: 0.12 },
};

// A page turned on its side is scanned as a landscape sheet; the others as the A4 portrait sheet (200 dpi).
const W = v => (v.rotate === 90 ? 2339 : 1654);
const H = v => (v.rotate === 90 ? 1654 : 2339);

function sheet(page, variant) {
  const p = PAGES[page], v = VARIANTS[variant];
  return `<!doctype html><html dir="${p.dir}" lang="${p.dir === 'rtl' ? 'ar' : 'en'}"><head><meta charset="utf-8"><style>
    html,body{margin:0;background:#fff;overflow:hidden} #page{position:absolute;left:50%;top:50%;width:1654px;height:2339px;box-sizing:border-box;
    padding:150px 140px;background:#fff;color:#111;transform:translate(-50%,-50%) rotate(${v.rotate}deg);filter:${v.filter}}
    #grain{position:fixed;inset:0;pointer-events:none}</style></head><body>
    <div id="page">${p.html}</div><canvas id="grain" width="${W(v)}" height="${H(v)}"></canvas>
    <script>const c=document.getElementById('grain').getContext('2d');const n=${v.noise};if(n>0){const d=c.createImageData(${W(v)},${H(v)});
    let s=7;const r=()=>(s=(s*16807)%2147483647)/2147483647;for(let i=0;i<d.data.length;i+=4){if(r()<n){const g=r()*160;d.data[i]=d.data[i+1]=d.data[i+2]=g;d.data[i+3]=110}}
    c.putImageData(d,0,0)}</script></body></html>`;
}

export async function makePages(out = OUT) {
  const { chromium } = require('playwright');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1654, height: 2339 }, deviceScaleFactor: 1 });
  const pg = await ctx.newPage();
  const made = [];
  for (const page of Object.keys(PAGES)) for (const variant of Object.keys(VARIANTS)) {
    await pg.setViewportSize({ width: W(VARIANTS[variant]), height: H(VARIANTS[variant]) });
    await pg.setContent(sheet(page, variant));
    const file = path.join(out, `${page}-${variant}.png`);
    await pg.screenshot({ path: file });
    made.push(path.basename(file));
  }
  await browser.close();
  fs.writeFileSync(path.join(out, 'truth.json'), JSON.stringify(Object.fromEntries(Object.entries(PAGES).map(([k, p]) => [k, p.facts])), null, 1));
  return made;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  makePages().then(m => console.log(`${m.length} pages → ${path.relative(ROOT, OUT)}/`)).catch(e => { console.error(e); process.exit(1); });
}
