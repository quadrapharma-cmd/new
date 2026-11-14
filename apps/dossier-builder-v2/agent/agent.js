// The agent core: one way to run a tool (the input checked against what the tool declares, every call logged in the dossier),
// the catalogue handed to Claude in each of its forms — page functions for claude.ai's `sample`, tool listings for the MCP
// bridge — and the standing instruction Claude works under inside the program.
import { TOOLS, ToolError, tool } from './tools.js';
import { check } from './schema.js';

export const BRIEF = [
  'You are the agent inside Dossier Builder, a program that prepares registration dossiers for medicines (Egypt first).',
  'You act only through the program\'s tools. Rules:',
  '1. Every fact you state or record rests on a document page or a library record. Record facts with record_fact, quoting the page\'s own words.',
  '2. Never invent a requirement: look it up with search_knowledge and get_record, and name its source (code, version, place).',
  '3. A document of another party (an authority, a manufacturer, a laboratory) is never changed.',
  '4. A page without a text layer is scanned: say so; do not guess its content.',
  '5. Answer in the user\'s language (Arabic or English), briefly: what you did, what you found, what is missing.',
].join('\n');

const short = v => (typeof v === 'string' && v.length > 300 ? v.slice(0, 300) + '…' : v);

// Runs one tool for Claude or for the interface. → { ok: true, result } | { ok: false, error }: never throws for a tool's own
// refusal or a bad input, so Claude reads the reason and can correct itself.
export async function callTool(name, input, ctx) {
  const t = tool(name);
  if (!t) return { ok: false, error: `no tool «${name}»` };
  const given = input ?? {};
  const problems = check(t.input, given);
  const t0 = Date.now();
  const entry = { tool: name, by: ctx.by || 'claude', input: Object.fromEntries(Object.entries(given).map(([k, v]) => [k, short(v)])) };
  if (problems.length) {
    ctx.ws.record({ ...entry, ok: false, error: problems.join('; '), ms: 0 });
    return { ok: false, error: `the input does not fit the tool: ${problems.join('; ')}` };
  }
  try {
    const result = await t.run(given, ctx);
    ctx.ws.record({ ...entry, ok: true, writes: t.writes, ms: Date.now() - t0 });
    return { ok: true, result };
  } catch (e) {
    const error = e instanceof ToolError ? e.message : `the tool failed: ${e?.message || e}`;
    ctx.ws.record({ ...entry, ok: false, error, ms: Date.now() - t0 });
    return { ok: false, error };
  }
}

const pick = only => TOOLS.filter(t => !only || only.includes(t.name));

// The tools as claude.ai's `sample` takes them: page functions that return small data or throw.
export function sampleTools(ctx, { only } = {}) {
  return pick(only).map(t => ({
    name: t.name, description: t.description, inputSchema: t.input,
    async execute(input) { const r = await callTool(t.name, input, ctx); if (!r.ok) throw new Error(r.error); return r.result; },
  }));
}

// The tools as an MCP server lists them.
export function mcpTools({ only } = {}) {
  return pick(only).map(t => ({
    name: t.name, title: t.title.en, description: t.description, inputSchema: t.input,
    annotations: { title: t.title.en, readOnlyHint: !t.writes, destructiveHint: false, idempotentHint: !t.writes, openWorldHint: false },
  }));
}

// The options of one call to claude.ai's sample, as its contract (runtime 0.2.96) takes them: only members that have a value
// (an unknown or empty `modelTier` is refused as `invalid_request`), never `cache` beside `tools`, at most as many tools as
// this view runs.
export function sampleOptions({ tools, modelTier, signal, onText, maxTools } = {}) {
  const opts = {};
  if (tools?.length) opts.tools = maxTools ? tools.slice(0, maxTools) : tools;
  if (modelTier) opts.modelTier = modelTier;
  if (signal) opts.signal = signal;
  if (onText) opts.onText = onText;
  return opts;
}

// One request to Claude inside the page, on the viewer's own account, with the program's tools. The limit of the viewer's plan
// pauses the work (nothing is lost; it goes on from a click), and a viewer who said no to Claude gets the program without it.
export async function ask(sample, { task, ctx, only, modelTier, signal, onText, maxTools }) {
  try {
    const res = await sample(`${BRIEF}\n\n${task}`, sampleOptions({ tools: sampleTools(ctx, { only }), modelTier, signal, onText, maxTools }));
    return { text: res.text, truncated: !!res.truncated };
  } catch (e) {
    if (e?.code === 'rate_limited') return { paused: true, reason: 'rate_limited', partial: e.text || '' };
    if (e?.code === 'not_granted' || e?.code === 'sampling_disabled') return { unavailable: true, reason: e.code };
    throw e;
  }
}

// The same request where this view cannot run page tools: the program reads the files itself and hands Claude their text (as
// much as fits), Claude answers and lists the facts it read as JSON, and the program records each one only if its words are on
// the page Claude names — the same check record_fact makes.
export async function askWithoutTools(sample, { task, ctx, signal, onText, budget = 120000 }) {
  const parts = [];
  let used = 0;
  for (const f of ctx.ws.files) {
    if (f.kind !== 'pdf' && f.kind !== 'text') { parts.push(`[${f.id}] ${f.path} (${f.kind}: not read here)`); continue; }
    const info = await callTool('list_files', {}, { ...ctx, by: 'program' });
    const pages = info.ok ? (info.result.files.find(x => x.file === f.id)?.pages || 1) : 1;
    for (let p = 1; p <= pages && used < budget; p++) {
      const r = await callTool('read_page_text', { file: f.id, page: p }, { ...ctx, by: 'program' });
      if (!r.ok) continue;
      const text = r.result.no_text_layer ? '(scanned page: no text layer)' : r.result.text;
      used += text.length;
      parts.push(`[${f.id}] ${f.path} — page ${p}\n${text}`);
    }
  }
  const prompt = `${BRIEF}\n\nThe dossier's files, as the program read them:\n\n${parts.join('\n\n')}\n\nTask: ${task}\n\n`
    + 'Reply with only a JSON object: {"answer": "your answer to the user, in their language", "facts": [{"field": "...", "value": "...", "file": "f1", "page": 1, "quote": "the words on that page that hold it, copied exactly"}]}. Use [] when there is no fact to record.';
  try {
    const out = await sample.json(prompt, sampleOptions({ signal, onText }));
    const facts = Array.isArray(out?.facts) ? out.facts : [];
    for (const f of facts.slice(0, 50)) {
      await callTool('record_fact', { field: String(f.field ?? ''), value: String(f.value ?? ''), file: String(f.file ?? ''), page: Number(f.page), quote: String(f.quote ?? '') }, ctx);
    }
    return { text: String(out?.answer ?? ''), truncated: false };
  } catch (e) {
    if (e?.code === 'rate_limited') return { paused: true, reason: 'rate_limited', partial: e.text || '' };
    if (e?.code === 'not_granted' || e?.code === 'sampling_disabled') return { unavailable: true, reason: e.code };
    throw e;
  }
}
