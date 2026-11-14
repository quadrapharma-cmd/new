// Part 2: the Operator — the button on every page and the conversation it opens. The claude.ai viewer is stood in for by a
// made-up `window.claude` whose «Claude Code Remote» connector answers like the real one (the shapes were read from real
// calls); the real connector can only be reached by a person viewing the artifact on claude.ai.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { build } from '../tools/build.mjs';
import { ROOT } from '../tools/load.mjs';
import { readEvents, sessionIdOf, TOOLS } from '../operator/session.js';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const PAGE = 'file://' + path.join(ROOT, 'dist', 'library', 'index.html');
const SHOTS = process.env.SHOTS || '';

let browser;
test.before(async () => { await build({ quiet: true }); browser = await chromium.launch(); });
test.after(async () => { await browser?.close(); });

// A stand-in viewer: `claude.use('mcp')` with the tools a test gives it; every call is kept in window.__calls.
function fakeViewer({ tools, fail } = {}) {
  return `(() => {
    const TOOLS = ${JSON.stringify(tools || TOOLS)};
    const FAIL = ${JSON.stringify(fail || null)};
    window.__calls = [];
    let turns = 0;
    const ev = (side, uuid, content, extra = {}) => ({ created_at: '2026-11-14T03:00:0' + uuid.length + 'Z',
      [side]: { uuid, internal_anthropic_catchall: { message: { role: side, content } }, ...extra } });
    const transcript = [];
    const mcp = {
      async listTools() { return { servers: [{ server: 'Claude Code Remote', authStatus: 'connected', tools: TOOLS.map(name => ({ name, description: '' })) }] }; },
      async callTool(server, tool, input) {
        window.__calls.push({ server, tool, input });
        if (FAIL && FAIL.tool === tool) throw { code: FAIL.code, message: 'refused' };
        if (tool === 'list_environments') return { payload: { environments: [{ environment_id: 'env_other', name: 'Default' }, { environment_id: 'env_ops', name: 'quadrapharma new' }] } };
        if (tool === 'create_session' || tool === 'send_message') {
          const text = tool === 'create_session' ? input.prompt : input.message;
          turns++;
          transcript.push(ev('user', 'u' + turns, [{ type: 'text', text: '<system-reminder>internal</system-reminder>' + text }]));
          transcript.push(ev('assistant', 'a' + turns, [{ type: 'tool_use', id: 'toolu_' + turns, name: 'Bash', input: {} }], { tool_use_meta: [{ id: 'toolu_' + turns, display_name: 'Bash' }] }));
          transcript.push(ev('user', 'r' + turns, [{ type: 'tool_result', tool_use_id: 'toolu_' + turns, content: 'secret output' }]));
          transcript.push(ev('assistant', 'b' + turns, [{ type: 'text', text: 'تمام، **خلصت** الطلب رقم ' + turns + ' \`npm test\`' }]));
          transcript.push({ created_at: 'x', result: { uuid: 'res' + turns } });
          return { payload: tool === 'create_session' ? { ccr: { id: 'session_01Test', session_status: 'SESSION_STATUS_RUNNING' } } : { delivered: true } };
        }
        if (tool === 'list_events') {
          const at = input.after_id ? transcript.findIndex(e => (e.user || e.assistant || e.result).uuid === input.after_id) + 1 : 0;
          const data = transcript.slice(at);
          const last = data.length ? (data.at(-1).user || data.at(-1).assistant || data.at(-1).result).uuid : input.after_id;
          return { payload: { ccr: { data, first_id: null, last_id: last, has_more: false } } };
        }
        throw { code: 'tool_error', message: 'unknown tool ' + tool };
      },
    };
    window.claude = { use: async name => (name === 'mcp' ? mcp : null) };
  })();`;
}

async function open(opts = {}, viewer) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, ...opts });
  if (viewer) await ctx.addInitScript(viewer);
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/fonts\.(googleapis|gstatic)/.test(m.text())) errors.push(m.text()); });
  await page.goto(PAGE);
  await page.waitForSelector('#main h1');
  return { page, ctx, errors };
}
const shot = async (page, name) => { if (SHOTS) { fs.mkdirSync(SHOTS, { recursive: true }); await page.screenshot({ path: path.join(SHOTS, name + '.png') }); } };
const overflow = page => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

test('the transcript reader keeps his words and the replies, and drops tool output and internal notes', () => {
  const r = readEvents({ ccr: { last_id: 'b', has_more: false, data: [
    { user: { uuid: 'u', internal_anthropic_catchall: { message: { content: [{ type: 'text', text: '<system-reminder>x</system-reminder>راجع الموقع' }] } } } },
    { assistant: { uuid: 'a', tool_use_meta: [{ id: 't1', display_name: 'Bash' }], internal_anthropic_catchall: { message: { content: [{ type: 'thinking', thinking: '' }, { type: 'tool_use', id: 't1', name: 'Bash' }] } } } },
    { user: { uuid: 'r', internal_anthropic_catchall: { message: { content: [{ type: 'tool_result', tool_use_id: 't1', content: 'out' }] } } } },
    { assistant: { uuid: 'b', internal_anthropic_catchall: { message: { content: [{ type: 'text', text: 'خلصت' }] } } } },
    { result: { uuid: 'z' } },
  ] } });
  assert.deepEqual(r.items.map(x => [x.kind, x.text]), [['you', 'راجع الموقع'], ['step', 'Bash'], ['op', 'خلصت'], ['done', undefined]]);
  assert.equal(r.last, 'b');
  assert.equal(sessionIdOf({ ccr: { id: 'session_01AbC' } }), 'session_01AbC');
  assert.equal(sessionIdOf({ nothing: true }), null);
});

test('the Operator button is on every page, and opened as a plain file it says plainly there is no connection', async () => {
  const { page, ctx, errors } = await open();
  for (const hash of ['#home', '#sources', '#variations', '#review']) {
    await page.goto(PAGE + hash);
    await page.waitForSelector('#main h1');
    assert.ok(await page.locator('#opFab').isVisible(), hash);
  }
  assert.equal(await page.locator('#opFab').innerText(), 'المشغّل');
  await page.click('#opFab');
  await page.waitForSelector('#opNote:not([hidden])');
  assert.match(await page.locator('#opNote').innerText(), /مفيش اتصال/);
  assert.ok(await page.locator('#opSend').isDisabled());
  await shot(page, 'op-01-file-ar');
  await page.keyboard.press('Escape');
  assert.ok(await page.locator('#opPanel').isHidden());
  assert.deepEqual(errors, []);
  await ctx.close();
});

test('on claude.ai: the first message opens an operator session on the repository, the reply shows, the next goes to the same session', async () => {
  const { page, ctx, errors } = await open({}, fakeViewer());
  await page.click('#opFab');
  await page.fill('#opText', 'راجع موقع الهيئة');
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => document.querySelectorAll('.op-msg.bot').length === 1);
  const calls = await page.evaluate(() => window.__calls);
  const made = calls.find(c => c.tool === 'create_session').input;
  assert.equal(made.prompt, 'راجع موقع الهيئة');
  assert.equal(made.environment_id, 'env_ops');
  assert.equal(made.source_url, 'https://github.com/quadrapharma-cmd/new');
  assert.equal(made.source_revision, 'claude/new-session-8nmyo7');
  assert.match(made.append_system_prompt, /operator of Dossier Builder v2/);
  assert.match(made.append_system_prompt, /apps\/dossier-builder-v2\/CLAUDE\.md/);
  assert.equal(await page.locator('.op-msg.you').count(), 1, 'his message is shown once');
  assert.match(await page.locator('.op-msg.bot').innerText(), /خلصت الطلب رقم 1/);
  assert.equal(await page.locator('.op-msg.bot b').nth(1).innerText(), 'خلصت');
  assert.doesNotMatch(await page.locator('#opLog').innerText(), /secret output|internal/);
  await page.waitForFunction(() => document.getElementById('opState').textContent === 'جاهز');
  assert.match(await page.locator('#opSid a').getAttribute('href'), /claude\.ai\/code\/session_01Test$/);

  await page.fill('#opText', 'انشر المكتبة');
  await page.click('#opSend');
  await page.waitForFunction(() => document.querySelectorAll('.op-msg.bot').length === 2);
  const sent = (await page.evaluate(() => window.__calls)).filter(c => c.tool === 'send_message');
  assert.deepEqual(sent.map(c => c.input), [{ session_id: 'session_01Test', message: 'انشر المكتبة' }]);
  assert.equal((await page.evaluate(() => window.__calls)).filter(c => c.tool === 'create_session').length, 1);
  await shot(page, 'op-02-conversation-ar');

  // Reopened later, the same session is picked up again.
  await page.reload();
  await page.waitForSelector('#main h1');
  await page.click('#opFab');
  await page.waitForFunction(() => window.__calls.some(c => c.tool === 'list_events'));
  assert.equal((await page.evaluate(() => window.__calls)).find(c => c.tool === 'list_events').input.session_id, 'session_01Test');
  assert.match(await page.locator('#opSid a').getAttribute('href'), /session_01Test/);
  assert.deepEqual(errors, []);
  await ctx.close();
});

test('a connector that lacks the tools, or refuses, is said plainly — never a silent failure', async () => {
  let r = await open({}, fakeViewer({ tools: ['list_environments', 'list_events'] }));
  await r.page.click('#opFab');
  await r.page.waitForSelector('#opNote:not([hidden])');
  const note = await r.page.locator('#opNote').innerText();
  assert.match(note, /create_session/);
  assert.match(note, /send_message/);
  assert.ok(await r.page.locator('#opSend').isDisabled());
  await r.ctx.close();

  r = await open({}, fakeViewer({ fail: { tool: 'create_session', code: 'approval_required' } }));
  await r.page.click('#opFab');
  await r.page.fill('#opText', 'سؤال');
  await r.page.click('#opSend');
  await r.page.waitForSelector('.op-msg.err');
  assert.match(await r.page.locator('.op-msg.err').innerText(), /ماوصلتش.*موافقتك/s);
  assert.equal(await r.page.locator('#opText').inputValue(), 'سؤال', 'the text is kept to send again');
  assert.deepEqual(r.errors, []);
  await r.ctx.close();
});

test('English, a phone and the dark theme: the panel follows the page', async () => {
  const { page, ctx, errors } = await open({ viewport: { width: 390, height: 844 }, colorScheme: 'dark' }, fakeViewer());
  await page.click('#lang');
  assert.equal(await page.locator('#opFab').innerText(), 'Operator');
  await page.click('#opFab');
  assert.equal(await page.locator('#opTitle').innerText(), 'Operator');
  assert.equal(await page.locator('#opSend').innerText(), 'Send');
  const box = await page.locator('#opPanel').boundingBox();
  assert.ok(box.x >= 0 && box.x + box.width <= 390.5, 'the panel fits the phone');
  assert.equal(await overflow(page), 0);
  await page.click('.op-ex >> nth=0');
  assert.match(await page.locator('#opText').inputValue(), /EDA/);
  await shot(page, 'op-03-phone-en-dark');
  await page.click('#lang');
  assert.equal(await page.locator('#opTitle').innerText(), 'المشغّل');
  assert.deepEqual(errors, []);
  await ctx.close();
});
