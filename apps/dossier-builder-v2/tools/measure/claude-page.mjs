// The page that measures Claude's reading where it runs for the user: inside claude.ai, on the viewer's own account (the
// `sample` capability), never by the session that wrote the pages. It carries the made-up scanned pages (tools/measure/
// pages.mjs) and their facts; one click sends each page to Claude twice — whole, and in two halves along its long side (the
// platform shrinks every image to about 1.2 megapixels, so small Arabic text may need the halves) — and scores each reading
// with the same rule as the other readers (tools/measure/score.mjs). Every run is saved in the page's own store (`db`,
// runs/<time>), where the program's sessions read it back.
//   node tools/measure/claude-page.mjs   → .cache/measure/claude-page.html (published as a private artifact)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { fold, score } from './score.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const PAGES = path.join(ROOT, '.cache', 'measure', 'pages');
const OUT = path.join(ROOT, '.cache', 'measure', 'claude-page.html');

const truth = JSON.parse(fs.readFileSync(path.join(PAGES, 'truth.json'), 'utf8'));
const NAMES = { 'notice-ar': 'إخطار تسجيل (عربي)', 'spec-en': 'مواصفة (إنجليزي)', 'gmp-en': 'شهادة GMP', 'letter-mixed': 'خطاب عربي وإنجليزي' };
const VARIANTS = { clean: 'مستقيمة', skew3: 'مايلة ٣°', rot90: 'على جنبها', faint: 'باهتة' };
const pages = [];
for (const page of Object.keys(truth)) for (const variant of Object.keys(VARIANTS)) {
  const png = fs.readFileSync(path.join(PAGES, `${page}-${variant}.png`));
  pages.push({ page, variant, src: `data:image/png;base64,${png.toString('base64')}` });
}

const html = `<title>قياس قراية Claude</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;600&display=swap">
<style>
:root{--bg:#f6f5f2;--card:#fff;--fg:#1d2330;--muted:#5f6878;--line:#dcd9d2;--accent:#1f5f8b;--good:#1e7a4f;--warn:#9a6a00;--bad:#a8322d}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14171c;--card:#1c2027;--fg:#e8eaee;--muted:#9aa3b2;--line:#2f3540;--accent:#6fb1df;--good:#5cc49a;--warn:#e0b24a;--bad:#ef7d74;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#14171c;--card:#1c2027;--fg:#e8eaee;--muted:#9aa3b2;--line:#2f3540;--accent:#6fb1df;--good:#5cc49a;--warn:#e0b24a;--bad:#ef7d74;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font:15px/1.7 "IBM Plex Sans Arabic",system-ui,sans-serif;direction:rtl}
main{max-width:980px;margin:0 auto;padding-block:28px 48px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
h1{font-size:1.6rem;margin:0 0 6px;text-wrap:balance} p{margin:.4rem 0;max-width:68ch} .muted{color:var(--muted)}
.bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:18px 0}
button{font:inherit;font-weight:600;padding:9px 18px;border-radius:8px;border:1px solid var(--accent);background:var(--accent);color:var(--card);cursor:pointer}
button.ghost{background:transparent;color:var(--accent)} button:disabled{opacity:.45;cursor:default}
#status{color:var(--muted)} .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:14px 0}
.wrap{overflow-x:auto} table{border-collapse:collapse;width:100%;min-width:620px} th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:start;vertical-align:top}
th{font-weight:600;color:var(--muted);font-size:.85rem} .n{font-variant-numeric:tabular-nums;white-space:nowrap}
.good{color:var(--good)} .warn{color:var(--warn)} .bad{color:var(--bad)} details summary{cursor:pointer;color:var(--muted)}
.sum{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px} .sum div{min-width:0}
.big{font-size:1.5rem;font-weight:600}
</style>
<main>
  <h1>قياس قراية Claude</h1>
  <p>الصفحة دي بتبعت ${pages.length} صفحة ممسوحة خيالية لـ Claude بحسابك، زي البرنامج بالظبط. وبتحسب Claude قرا كام في المية من المعلومات اللي في كل صفحة، وفي كام ثانية.</p>
  <p class="muted">كل صفحة بتتبعت مرتين: الصفحة كلها، وبعدين نصّين. والنتيجة بتتحفظ هنا لوحدها، علشان البرنامج يقراها.</p>
  <div class="bar"><button id="go">ابدأ القياس</button><button id="stop" class="ghost" disabled>وقّف</button><span id="status" aria-live="polite"></span></div>
  <section class="card" id="summary" hidden></section>
  <section class="card"><div class="wrap"><table><thead><tr><th>الصفحة</th><th>الشكل</th><th>الصفحة كلها</th><th>نصّين</th><th>اللي فاته</th></tr></thead><tbody id="rows"></tbody></table></div></section>
</main>
<script>
const PAGES=${JSON.stringify(pages)};
const TRUTH=${JSON.stringify(truth)};
const NAMES=${JSON.stringify(NAMES)}, VARIANTS=${JSON.stringify(VARIANTS)};
${fold.toString()}
${score.toString()}
const DIGITS=${JSON.stringify({ '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9', '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9' })};
const ASK_WHOLE='The image is a scanned page of a pharmaceutical regulatory document. It may be rotated, skewed or faint. Read it in its correct orientation and transcribe every word on it exactly as written, in reading order: Arabic as Arabic, English as English, and every digit as it is drawn (keep Arabic-Indic digits as they are). Include headings, table cells and the text of stamps. Output only the transcription.';
const ASK_HALVES='The two images are the two halves of ONE scanned page of a pharmaceutical regulatory document, cut along its long side; they overlap a little. The page may be rotated, skewed or faint. Read it in its correct orientation and transcribe every word of the whole page once, exactly as written, in reading order: Arabic as Arabic, English as English, and every digit as it is drawn (keep Arabic-Indic digits as they are). Include headings, table cells and the text of stamps. Output only the transcription.';
const $=s=>document.querySelector(s);
const results=[]; let sample=null, db=null, stopper=null, startedAt=null, tier=null;
const cls=p=>p>=90?'good':p>=60?'warn':'bad';
function blobOf(src){return fetch(src).then(r=>r.blob())}
function halves(src){return new Promise((ok,no)=>{const im=new Image();im.onload=()=>{const w=im.naturalWidth,h=im.naturalHeight,wide=w>h;const out=[];
  for(const part of [0,1]){const c=document.createElement('canvas');const keep=0.55;
    if(wide){c.width=Math.round(w*keep);c.height=h;c.getContext('2d').drawImage(im,part?w-c.width:0,0,c.width,h,0,0,c.width,h)}
    else{c.width=w;c.height=Math.round(h*keep);c.getContext('2d').drawImage(im,0,part?h-c.height:0,w,c.height,0,0,w,c.height)}
    out.push(new Promise(r=>c.toBlob(r,'image/png')))}
  Promise.all(out).then(ok,no)};im.onerror=no;im.src=src})}
function draw(){const rows=$('#rows');rows.textContent='';
  for(const r of results){const tr=document.createElement('tr');
    const cell=x=>x?(x.error?'<span class="bad">'+x.error+'</span>':'<span class="n '+cls(x.pct)+'">'+x.pct+'%</span> <span class="n muted">'+x.seconds+' ث</span>'):'…';
    const missed=[...new Set([...(r.whole?.missed||[]),...(r.halves?.missed||[])])];
    tr.innerHTML='<td>'+NAMES[r.page]+'</td><td>'+VARIANTS[r.variant]+'</td><td>'+cell(r.whole)+'</td><td>'+cell(r.halves)+'</td><td></td>';
    if(missed.length){const d=document.createElement('details');d.innerHTML='<summary>'+missed.length+'</summary>';const ul=document.createElement('div');ul.textContent=missed.join(' · ');d.append(ul);tr.lastChild.append(d)}
    rows.append(tr)}
  const done=results.filter(r=>r.whole&&r.halves&&!r.whole.error&&!r.halves.error);
  if(!done.length){$('#summary').hidden=true;return}
  const avg=(k,f)=>Math.round(done.reduce((s,r)=>s+f(r[k]),0)/done.length*10)/10;
  $('#summary').hidden=false;$('#summary').innerHTML='<div class="sum"><div><div class="muted">الصفحة كلها</div><div class="big '+cls(avg('whole',x=>x.pct))+'">'+avg('whole',x=>x.pct)+'%</div><div class="muted n">'+avg('whole',x=>x.seconds)+' ث للصفحة</div></div>'
   +'<div><div class="muted">نصّين</div><div class="big '+cls(avg('halves',x=>x.pct))+'">'+avg('halves',x=>x.pct)+'%</div><div class="muted n">'+avg('halves',x=>x.seconds)+' ث للصفحة</div></div>'
   +'<div><div class="muted">اتقاس</div><div class="big">'+done.length+' من '+PAGES.length+'</div><div class="muted">'+(tier?('نموذج: '+tier):'')+'</div></div></div>'}
async function readOnce(images,ask,signal){const t0=performance.now();const res=await sample(ask,{images,signal,cache:false});tier=res.modelTierApplied||tier;return{text:res.text,truncated:res.truncated,seconds:Math.round((performance.now()-t0)/100)/10}}
async function save(){if(!db||!startedAt)return;try{await db.collection('runs').doc(startedAt.replace(/[:.]/g,'-')).set({startedAt,savedAt:new Date().toISOString(),tier,pages:PAGES.length,results:results.map(r=>({page:r.page,variant:r.variant,whole:r.whole||null,halves:r.halves||null}))})}catch(e){$('#status').textContent='النتيجة ماتحفظتش: '+(e.code||e.message)}}
async function run(){
  if(!sample){$('#status').textContent='Claude مش متاح هنا: افتح الصفحة دي على claude.ai.';return}
  const caps=await sample.limits().catch(()=>null);
  if(!caps?.images){$('#status').textContent='العرض ده مش بيقدر يبعت صور لـ Claude.';return}
  $('#go').disabled=true;$('#stop').disabled=false;stopper=new AbortController();startedAt=startedAt||new Date().toISOString();
  try{
    for(let i=0;i<PAGES.length;i++){const p=PAGES[i];let r=results.find(x=>x.page===p.page&&x.variant===p.variant);
      if(!r){r={page:p.page,variant:p.variant};results.push(r)}
      if(!r.whole||r.whole.error){$('#status').textContent='صفحة '+(i+1)+' من '+PAGES.length+': الصفحة كلها…';
        try{const one=await readOnce([await blobOf(p.src)],ASK_WHOLE,stopper.signal);r.whole={...score(TRUTH[p.page],one.text),seconds:one.seconds,truncated:one.truncated,text:one.text}}
        catch(e){if(e.code==='cancelled')throw e;r.whole={error:e.code||'error'};if(['rate_limited','not_granted','sampling_disabled','images_unavailable'].includes(e.code))throw e}
        draw();await save()}
      if(caps.images.maxCount>=2&&(!r.halves||r.halves.error)){$('#status').textContent='صفحة '+(i+1)+' من '+PAGES.length+': نصّين…';
        try{const two=await readOnce(await halves(p.src),ASK_HALVES,stopper.signal);r.halves={...score(TRUTH[p.page],two.text),seconds:two.seconds,truncated:two.truncated,text:two.text}}
        catch(e){if(e.code==='cancelled')throw e;r.halves={error:e.code||'error'};if(['rate_limited','not_granted','sampling_disabled'].includes(e.code))throw e}
        draw();await save()}}
    $('#status').textContent='خلص القياس، والنتيجة اتحفظت.'}
  catch(e){const why={rate_limited:'حدّ الاستخدام في حسابك خلص دلوقتي. اللي اتقاس اتحفظ، ودوس «كمّل» بعدين.',not_granted:'Claude مش مسموح للصفحة دي.',cancelled:'وقفت. اللي اتقاس اتحفظ.'}[e.code];
    $('#status').textContent=why||('وقف: '+(e.code||e.message));$('#go').textContent='كمّل'}
  finally{$('#go').disabled=false;$('#stop').disabled=true;draw()}}
$('#go').onclick=run;$('#stop').onclick=()=>stopper&&stopper.abort();
draw();
(async()=>{const C=window.claude;sample=C?await C.use('sample'):null;db=C?await C.use('db'):null;if(!sample)$('#status').textContent='Claude مش متاح هنا: افتح الصفحة دي على claude.ai.'})();
</script>
`;
fs.writeFileSync(OUT, html);
console.log(`${path.relative(ROOT, OUT)}: ${pages.length} pages, ${(html.length / 1048576).toFixed(1)} MB`);
