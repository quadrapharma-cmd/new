// Builds the workbench page for the claude.ai artifact (step 2.0: Claude with the program's tools inside the page):
//   node workbench/build.mjs   → dist/workbench-artifact.html (the page, without a document shell: the artifact adds it)
//                                dist/workbench/pdf.worker.min.js (pdf.js's worker, published beside the page)
// Needs dist/knowledge.json (npm run build). The page carries the knowledge and a made-up example certificate; pdf.js
// (Apache-2.0) is bundled into its script.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as esbuild from 'esbuild';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const DIST = path.join(ROOT, 'dist');
const FONTS = 'https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans+Arabic:wght@400;500;600&family=Readex+Pro:wght@500;600&display=swap';

// claude.ai refuses a published text file holding control characters (pdf.js keeps data tables as raw bytes in its strings):
// each one becomes its \xNN escape, which JavaScript reads back as the same character in a string, a template or a regex.
// A control character written after a backslash (an escape of itself) loses that backslash.
export function escapeControls(js) {
  let out = '';
  for (let i = 0; i < js.length; i++) {
    const c = js.charCodeAt(i);
    if ((c < 32 && c !== 9 && c !== 10 && c !== 13) || c === 127) {
      let k = 0;
      while (out.length - 1 - k >= 0 && out[out.length - 1 - k] === '\\') k++;
      if (k % 2 === 1) out = out.slice(0, -1);
      out += '\\x' + c.toString(16).padStart(2, '0');
    } else out += js[i];
  }
  return out;
}

const EXAMPLES = ['اعرضلي ملفات الملف، وقولي كل ملف فيه إيه',
                  'سجّل رقم التشغيلة ورقم التسجيل وتاريخ الانتهاء من شهادة التحليل',
                  'إيه المطلوب في بند 1.1.1 عند هيئة الدواء المصرية؟ وإيه مصدره؟'];

const BODY = `<div class="page" dir="rtl" lang="ar">
<header>
  <h1>ورشة Claude</h1>
  <p>Claude بيشتغل هنا بأدوات Dossier Builder نفسها: بيقرا صفحات الملفات، ويدوّر فيها وفي المكتبة، ويسجّل المعلومة بالكلام اللي في صفحتها. بيشتغل على حسابك في claude.ai، والملفات بتتقري في المتصفح، ونص الصفحة بيروح لـ Claude بس لما يطلبه.</p>
</header>
<div class="status" id="claude-status">بيتأكد إن Claude متاح…</div>
<div class="cols">
  <div class="col">
    <section class="box" aria-labelledby="ask-h">
      <h2 id="ask-h">اسأل Claude <small>وانت شايف كل خطوة بيعملها</small></h2>
      <form id="ask" class="col">
        <label for="task" class="fine">سؤالك أو المطلوب</label>
        <textarea id="task" placeholder="مثلاً: سجّل رقم التشغيلة وتاريخ الانتهاء من شهادة التحليل"></textarea>
        <div class="row"><button class="btn" id="send" type="submit">اسأل</button><button class="btn quiet" id="stop" type="button" hidden>وقّف</button><button class="btn quiet" id="resume" type="button" hidden>كمّل</button></div>
      </form>
      <div class="row" id="examples">${EXAMPLES.map(e => `<button type="button" class="chip">${e}</button>`).join('')}</div>
      <div class="answer" id="answer" data-empty="الرد هيظهر هنا."></div>
      <h2>خطوات Claude <small id="steps-count"></small></h2>
      <ol class="steps" id="steps"></ol>
      <p class="empty" id="steps-empty">لسه مفيش خطوات. كل أداة Claude يستخدمها هتظهر هنا، باللي طلبه منها.</p>
    </section>
  </div>
  <div class="col">
    <section class="box" aria-labelledby="files-h">
      <h2 id="files-h">ملفات الملف</h2>
      <label class="drop" id="drop"><input type="file" id="pick" multiple>اسحب الملفات هنا أو دوس تختارها (PDF فيه نص، أو ملف نص)</label>
      <div class="scroll"><table id="files"><thead><tr><th>#</th><th>الملف</th><th>نوعه</th><th>صفحات</th><th>الحجم</th></tr></thead><tbody></tbody></table></div>
      <div class="row"><button class="btn quiet" id="use-example" type="button" hidden>رجّع الملف الخيالي</button></div>
      <p class="fine">نوع كل ملف بيتعرف من محتواه، مش من اسمه. الصفحات الممسوحة لسه مابتتقريش هنا (الخطوة الجاية).</p>
    </section>
    <section class="box" aria-labelledby="facts-h">
      <h2 id="facts-h">المعلومات المسجّلة</h2>
      <ul class="facts" id="facts" hidden></ul>
      <p class="empty" id="facts-empty">لسه Claude ماسجّلش معلومة. المعلومة مابتتسجلش غير لو كلامها موجود فعلاً في صفحتها.</p>
      <div class="row"><button class="btn quiet" id="undo" type="button" disabled>شيل آخر معلومة</button></div>
    </section>
  </div>
</div>
</div>`;

export async function buildWorkbench() {
  const knowledge = path.join(DIST, 'knowledge.json');
  if (!fs.existsSync(knowledge)) throw new Error('dist/knowledge.json is missing: run npm run build first');
  const bundle = await esbuild.build({
    entryPoints: [path.join(HERE, 'page.js')], bundle: true, format: 'iife', minify: true, target: ['es2022'],
    write: false, legalComments: 'none', logLevel: 'error', define: { 'import.meta.url': '""' },
  });
  const js = escapeControls(bundle.outputFiles[0].text).replace(/<\/script/gi, '<\\/script');
  const css = fs.readFileSync(path.join(HERE, 'style.css'), 'utf8');
  const json = fs.readFileSync(knowledge, 'utf8').replace(/</g, '\\u003c');
  const pdf = fs.readFileSync(path.join(HERE, 'sample-certificate.pdf')).toString('base64');
  const page = [
    '<title>ورشة Claude</title>',
    '<meta name="claude:viewport-fit-sides" content="cover">',
    '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
    `<link rel="stylesheet" href="${FONTS}">`,
    `<style>${css}</style>`,
    BODY,
    `<script type="application/json" id="kdata">${json}</script>`,
    `<script type="text/plain" id="example-pdf">${pdf}</script>`,
    `<script>${js}</script>`,
  ].join('\n');
  fs.writeFileSync(path.join(DIST, 'workbench-artifact.html'), page);
  fs.mkdirSync(path.join(DIST, 'workbench'), { recursive: true });
  const worker = fs.readFileSync(path.join(ROOT, 'node_modules', 'pdfjs-dist', 'build', 'pdf.worker.min.mjs'), 'utf8');
  fs.writeFileSync(path.join(DIST, 'workbench', 'pdf.worker.min.js'), escapeControls(worker));
  return { page: path.join(DIST, 'workbench-artifact.html'), bytes: Buffer.byteLength(page) };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const { page, bytes } = await buildWorkbench();
  console.log(`${path.relative(process.cwd(), page)}: ${(bytes / 1048576).toFixed(1)} MB (+ dist/workbench/pdf.worker.min.js)`);
}
