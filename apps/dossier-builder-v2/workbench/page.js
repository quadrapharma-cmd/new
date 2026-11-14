// The workbench (step 2.0, docs/PART-2-PLAN.md §3.8): Claude works with the program's own tools (agent/tools.js) inside the
// page, on the viewer's claude.ai account (the `sample` capability). The files are read in the browser; a page's text goes to
// Claude only when Claude asks for it with a tool. Every tool call is shown, and every fact is kept with the words on its page.
import * as pdfjs from 'pdfjs-dist/build/pdf.mjs';
import { createWorkspace } from '../agent/workspace.js';
import { tool } from '../agent/tools.js';
import { callTool, ask } from '../agent/agent.js';
import { createKnowledge } from '../core/knowledge.js';

pdfjs.GlobalWorkerOptions.workerSrc = 'workbench/pdf.worker.min.js';
const $ = s => document.querySelector(s);
const knowledge = createKnowledge(JSON.parse($('#kdata').textContent));
const EXAMPLE = { name: 'شهادة-تحليل-خيالية.pdf', example: true,
                  bytes: Uint8Array.from(atob($('#example-pdf').textContent.trim()), c => c.charCodeAt(0)) };
const KB = n => (n < 1024 * 1024 ? `${Math.max(1, Math.round(n / 1024))} ك.ب` : `${(n / 1048576).toFixed(1)} م.ب`);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

let files = [EXAMPLE];
let ctx = null;
let sample = null;
let from = 0;              // where the current question's steps start in the workspace's log
let controller = null;
let lastTask = '';

function status(text, kind = '') { const el = $('#claude-status'); el.textContent = text; el.className = `status ${kind}`; }

// ------------------------------------------------------------------ the files
async function load(list) {
  files = list;
  const ws = await createWorkspace({ files: files.map(f => ({ name: f.name, bytes: f.bytes })) });
  const record = ws.record.bind(ws);
  ws.record = entry => { record(entry); renderSteps(); };
  ctx = { ws, pdfjs, knowledge, by: 'claude' };
  from = ws.log.length;
  const r = await callTool('list_files', {}, { ...ctx, by: 'you' });
  from = ws.log.length;
  const rows = r.ok ? r.result.files : [];
  $('#files tbody').innerHTML = rows.map((f, i) => `<tr><td class="num">${esc(f.file)}</td><td><bdi>${esc(f.name)}</bdi>${files[i]?.example ? ' <span class="badge">مثال خيالي</span>' : ''}${f.problem ? `<div class="quote">${esc(f.problem)}</div>` : ''}</td>
    <td><span class="kind">${esc(f.kind)}</span></td><td class="num">${f.pages ?? '—'}</td><td class="num">${KB(f.bytes)}</td></tr>`).join('');
  $('#use-example').hidden = files.some(f => f.example);
  renderSteps();
  renderFacts();
}

async function add(fileList) {
  const added = [];
  for (const f of fileList) added.push({ name: f.name, bytes: new Uint8Array(await f.arrayBuffer()) });
  if (added.length) await load([...files.filter(f => !f.example), ...added]);
}

// ------------------------------------------------------------------ Claude's steps and the facts
function describe(e) {
  const i = e.input || {};
  const name = id => ctx.ws.files.find(f => f.id === id)?.path || id;
  const bits = [];
  if (i.file) bits.push(`<bdi>${esc(i.file)}</bdi> (<bdi>${esc(name(i.file))}</bdi>)`);
  if (i.page) bits.push(`صفحة ${esc(i.page)}`);
  if (i.query) bits.push(`«<bdi>${esc(i.query)}</bdi>»`);
  if (i.id) bits.push(`<bdi>${esc(i.id)}</bdi>`);
  if (i.field) bits.push(`<bdi>${esc(i.field)} = ${esc(i.value ?? '')}</bdi>`);
  return bits.join('، ');
}

function renderSteps() {
  if (!ctx) return;
  const steps = ctx.ws.log.slice(from).filter(e => e.by === 'claude');
  $('#steps').innerHTML = steps.map(e => `<li class="${e.ok ? '' : 'no'}"><span class="t">${esc(tool(e.tool)?.title.ar || e.tool)}</span>
    <span class="d">${describe(e)}${e.ok ? '' : ` — <bdi>${esc(e.error)}</bdi>`}</span></li>`).join('');
  $('#steps-empty').hidden = steps.length > 0;
  $('#steps-count').textContent = steps.length ? `${steps.length} خطوة` : '';
  renderFacts();
}

function renderFacts() {
  const facts = ctx ? ctx.ws.facts : [];
  $('#facts').innerHTML = facts.map(f => `<li><div class="fv"><span class="f"><bdi>${esc(f.field)}</bdi></span><span class="v"><bdi>${esc(f.value)}</bdi></span></div>
    <div class="quote"><bdi>${esc(f.name)}</bdi>، صفحة ${f.page}: «<bdi>${esc(f.quote)}</bdi>»</div></li>`).join('');
  $('#facts').hidden = !facts.length;
  $('#facts-empty').hidden = facts.length > 0;
  $('#undo').disabled = !facts.length;
}

// ------------------------------------------------------------------ asking
function busy(on) {
  $('#send').disabled = on;
  $('#stop').hidden = !on;
  $('#task').readOnly = on;
  for (const c of document.querySelectorAll('.chip')) c.disabled = on;
}

async function run(task) {
  task = task.trim();
  if (!task) return;
  if (!sample) { status('Claude مش متاح هنا. افتح الصفحة على claude.ai وانت داخل بحسابك.', 'warn'); return; }
  lastTask = task;
  $('#resume').hidden = true;
  $('#answer').textContent = '';
  from = ctx.ws.log.length;
  renderSteps();
  controller = new AbortController();
  busy(true);
  status('Claude شغال…');
  try {
    const res = await ask(sample, { task, ctx, signal: controller.signal, onText: ({ text }) => { $('#answer').textContent = text; } });
    if (res.paused) {
      if (res.partial) $('#answer').textContent = res.partial;
      status('حد الاستخدام في اشتراكك خلص مؤقتاً. الشغل اتحفظ؛ لما الحد يرجع دوس «كمّل».', 'warn');
      $('#resume').hidden = false;
    } else if (res.unavailable) {
      status(res.reason === 'not_granted' ? 'الصفحة مش مسموح لها تكلّم Claude. تقدر تسمح من قايمة الأذونات بتاعة الصفحة.' : 'Claude مش متاح على الحساب ده.', 'warn');
    } else {
      $('#answer').textContent = res.text + (res.truncated ? '\n…(الرد اتقطع)' : '');
      status('Claude خلّص.', 'ok');
    }
  } catch (e) {
    status(e?.code === 'cancelled' || e?.name === 'AbortError' ? 'وقّفت Claude.' : `Claude ماردّش: ${e?.code || e?.message || e}`, e?.code === 'cancelled' ? '' : 'bad');
  } finally {
    busy(false);
    renderFacts();
  }
}

// ------------------------------------------------------------------ wiring
$('#ask').addEventListener('submit', e => { e.preventDefault(); run($('#task').value); });
$('#stop').addEventListener('click', () => controller?.abort());
$('#resume').addEventListener('click', () => run(lastTask));
for (const c of document.querySelectorAll('.chip')) c.addEventListener('click', () => { $('#task').value = c.textContent.trim(); run(c.textContent); });
$('#pick').addEventListener('change', e => { add(e.target.files); e.target.value = ''; });
const drop = $('#drop');
drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('over'); });
drop.addEventListener('dragleave', () => drop.classList.remove('over'));
drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('over'); add(e.dataTransfer.files); });
$('#use-example').addEventListener('click', () => load([...files, EXAMPLE]));
$('#undo').addEventListener('click', () => { ctx?.ws.undoLast(); renderFacts(); });

load(files);
(async () => {
  try { sample = window.claude?.use ? await window.claude.use('sample') : null; } catch { sample = null; }
  if (sample) status('Claude جاهز على حسابك. أول مرة تسأله، claude.ai هيطلب موافقتك.', 'ok');
  else status('Claude مش متاح في العرض ده. افتح الصفحة على claude.ai وانت داخل بحسابك.', 'warn');
})();
