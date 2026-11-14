// Claude in the desktop workshop: the Anthropic API called from the page with the viewer's own API key (his account, billed by
// use), through the official SDK. The key stays in this page's memory, or on this computer if the viewer asks it to be remembered;
// it is sent to the API only. Which models the key may use is asked of the API itself (models.list), and the viewer picks one.
//   connect(key) → {client, models}              (a wrong key is refused here, with the reason)
//   sampleOf(client, model) → sample(prompt, {images, signal, onText, maxTokens, effort}) → {text, truncated, usage}
//                                                  (the shape prep/claude-read.js takes, so scans are read the same way)
//   converse(client, model, {system, messages, tools, onText, signal, maxSteps}) → {text, steps, usage}   (a tool loop)
// Every failure comes back as an Error with a `code` the page explains (WHY below).
import Anthropic, { AuthenticationError, PermissionDeniedError, RateLimitError, BadRequestError, NotFoundError, InternalServerError,
  APIConnectionError, APIUserAbortError, APIError } from '@anthropic-ai/sdk';

export const WHY = {
  no_key: 'مفيش مفتاح API. حطّه من «الإعدادات».',
  key_invalid: 'المفتاح مش شغال (غلط أو اتلغى). اتأكد منه في console.anthropic.com.',
  not_granted: 'المفتاح مش مسموح له بالطلب ده.',
  no_credit: 'رصيد الحساب خلص. اشحن من console.anthropic.com وكمّل.',
  rate_limited: 'وصلت لحد الطلبات في الدقيقة. البرنامج هيستنى ويكمّل.',
  prompt_too_large: 'الكلام اللي اتبعت لـ Claude أكبر من اللي يقبله في مرة.',
  model_missing: 'النموذج المختار مش متاح للمفتاح ده. اختار غيره من «الإعدادات».',
  upstream_error: 'Claude مشغول أو فيه عطل مؤقت. جرّب بعد شوية.',
  network: 'مفيش اتصال بـ Claude (الإنترنت أو جدار حماية).',
  cancelled: 'اتوقف.',
  invalid_request: 'الطلب اترفض.',
  refused: 'Claude رفض يرد على الطلب ده.',
};
// No use asking again in this run after these: every later call would fail the same way.
export const STOP = new Set(['no_key', 'key_invalid', 'not_granted', 'no_credit', 'model_missing', 'network']);

const coded = (code, e) => Object.assign(new Error(WHY[code] || code), { code, detail: e ? String(e.message || e).slice(0, 300) : '' });
export function codeOf(e) {
  if (e?.code && WHY[e.code]) return e;
  if (e instanceof APIUserAbortError || e?.name === 'AbortError') return coded('cancelled', e);
  if (e instanceof AuthenticationError) return coded('key_invalid', e);
  if (e instanceof PermissionDeniedError) return coded('not_granted', e);
  if (e instanceof RateLimitError) return coded('rate_limited', e);
  if (e instanceof NotFoundError) return coded('model_missing', e);
  if (e instanceof BadRequestError) {
    const m = String(e.message || '');
    if (/credit balance/i.test(m)) return coded('no_credit', e);
    if (/prompt is too long|too many tokens|too large/i.test(m)) return coded('prompt_too_large', e);
    return coded('invalid_request', e);
  }
  if (e instanceof InternalServerError || (e instanceof APIError && (e.status >= 500 || e.status === 529))) return coded('upstream_error', e);
  if (e instanceof APIConnectionError) return coded('network', e);
  return coded('invalid_request', e);
}

// The key checked by asking the API which models it may use; the most capable family first (newest first within it).
export async function connect(key, { baseURL } = {}) {
  if (!key || !String(key).trim()) throw coded('no_key');
  const client = new Anthropic({ apiKey: String(key).trim(), dangerouslyAllowBrowser: true, maxRetries: 2, ...(baseURL ? { baseURL } : {}) });
  try {
    const models = [];
    for await (const m of client.models.list({ limit: 100 })) models.push({ id: m.id, name: m.display_name || m.id, created: m.created_at || '' });
    const rank = m => (/opus/i.test(m.id) ? 0 : /sonnet/i.test(m.id) ? 1 : 2);
    models.sort((a, b) => rank(a) - rank(b) || String(b.created).localeCompare(String(a.created)));
    return { client, models };
  } catch (e) { throw codeOf(e); }
}

const b64 = async blob => {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
};

// What a model of this key refuses once (an effort setting, a tool option) is not sent to it again in this page.
const refusedOptions = new Map();
async function streamed(client, model, params, { onText, signal } = {}) {
  const off = refusedOptions.get(model) || new Set();
  const body = { model, ...params };
  if (off.has('effort')) delete body.output_config;
  if (off.has('eager') && body.tools) body.tools = body.tools.map(({ eager_input_streaming, ...t }) => t);
  try {
    const stream = client.messages.stream(body, signal ? { signal } : undefined);
    if (onText) stream.on('text', (_, snapshot) => { try { onText({ text: snapshot }); } catch { /* the page's display only */ } });
    return await stream.finalMessage();
  } catch (e) {
    const m = String(e?.message || '');
    if (e instanceof BadRequestError && /effort|output_config/i.test(m) && body.output_config) { off.add('effort'); refusedOptions.set(model, off); return streamed(client, model, params, { onText, signal }); }
    if (e instanceof BadRequestError && /eager_input_streaming/i.test(m) && !off.has('eager')) { off.add('eager'); refusedOptions.set(model, off); return streamed(client, model, params, { onText, signal }); }
    throw codeOf(e);
  }
}
const textOf = msg => (msg.content || []).filter(b => b.type === 'text').map(b => b.text).join('');
const usageOf = msg => ({ input: msg.usage?.input_tokens || 0, output: msg.usage?.output_tokens || 0 });

// One question (with pictures when given) → its answer, in the shape the scan reading takes.
export function sampleOf(client, model) {
  return async function sample(prompt, { images = [], signal, onText, maxTokens = 8000, effort = 'low' } = {}) {
    if (!client) throw coded('no_key');
    const content = [];
    for (const img of images) content.push({ type: 'image', source: { type: 'base64', media_type: img.type || 'image/png', data: await b64(img) } });
    content.push({ type: 'text', text: String(prompt) });
    const msg = await streamed(client, model, { max_tokens: maxTokens, output_config: { effort }, messages: [{ role: 'user', content }] }, { onText, signal });
    if (msg.stop_reason === 'refusal') throw coded('refused');
    return { text: textOf(msg), truncated: msg.stop_reason === 'max_tokens', usage: usageOf(msg) };
  };
}

// The same, answering with JSON only: the reply parsed (a fenced or prefaced answer is read too).
export async function askJson(sample, prompt, opts = {}) {
  const res = await sample(`${prompt}\n\nReply with only the JSON, nothing before or after it.`, opts);
  const t = res.text.trim().replace(/^```(?:json)?\s*/i, '').replace(/```\s*$/, '');
  const at = Math.min(...['{', '['].map(c => (t.indexOf(c) < 0 ? Infinity : t.indexOf(c))));
  if (!Number.isFinite(at)) throw Object.assign(new Error('Claude did not answer with JSON'), { code: 'invalid_request' });
  try { return { value: JSON.parse(t.slice(at)), usage: res.usage }; } catch {
    const end = Math.max(t.lastIndexOf('}'), t.lastIndexOf(']'));
    return { value: JSON.parse(t.slice(at, end + 1)), usage: res.usage };
  }
}

// A conversation in which Claude works with the program's tools: tools = [{name, description, input_schema, run(input) → result}]
// (a tool's own refusal comes back to Claude as an error result, so it can correct itself). Stops at the answer, at maxSteps, or on
// the viewer's stop (signal).
export async function converse(client, model, { system, messages, tools = [], onText, onStep, signal, maxSteps = 24, maxTokens = 16000, effort = 'medium' }) {
  if (!client) throw coded('no_key');
  const spec = tools.map(t => ({ name: t.name, description: t.description, input_schema: t.input_schema, eager_input_streaming: true }));
  const history = [...messages];
  const usage = { input: 0, output: 0 };
  let steps = 0, text = '';
  for (;;) {
    const msg = await streamed(client, model, { max_tokens: maxTokens, system, output_config: { effort }, tools: spec, messages: history }, { onText, signal });
    usage.input += msg.usage?.input_tokens || 0;
    usage.output += msg.usage?.output_tokens || 0;
    text = textOf(msg) || text;
    if (msg.stop_reason === 'refusal') throw coded('refused');
    if (msg.stop_reason === 'pause_turn') { history.push({ role: 'assistant', content: msg.content }); continue; }
    const calls = (msg.content || []).filter(b => b.type === 'tool_use');
    if (msg.stop_reason !== 'tool_use' || !calls.length) return { text, steps, usage, history: [...history, { role: 'assistant', content: msg.content }] };
    history.push({ role: 'assistant', content: msg.content });
    const results = [];
    for (const call of calls) {
      steps++;
      const tool = tools.find(t => t.name === call.name);
      let content, isError = false;
      if (msg.stop_reason === 'max_tokens') { content = 'the request was cut off before this tool\'s input was complete: ask again'; isError = true; }
      else if (!tool) { content = `no tool «${call.name}»`; isError = true; }
      else {
        try { content = JSON.stringify(await tool.run(call.input ?? {})); } catch (e) { content = String(e?.message || e); isError = true; }
      }
      try { onStep?.({ name: call.name, input: call.input, ok: !isError, result: content.slice(0, 400) }); } catch { /* display only */ }
      results.push({ type: 'tool_result', tool_use_id: call.id, content: content.slice(0, 60000), ...(isError ? { is_error: true } : {}) });
    }
    if (steps >= maxSteps) {
      results.push({ type: 'text', text: 'That is the last tool call allowed for this question: answer now with what you have found.' });
      history.push({ role: 'user', content: results });
      const last = await streamed(client, model, { max_tokens: maxTokens, system, output_config: { effort }, tools: spec, tool_choice: { type: 'none' }, messages: history },
                                  { onText, signal });
      usage.input += last.usage?.input_tokens || 0;
      usage.output += last.usage?.output_tokens || 0;
      return { text: textOf(last) || text, steps, usage, history: [...history, { role: 'assistant', content: last.content }] };
    }
    history.push({ role: 'user', content: results });
  }
}
