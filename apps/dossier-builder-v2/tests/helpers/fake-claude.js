// window.claude as a claude.ai viewer gives it to a page (runtime contract 0.2.96), for tests and for tools/check-published.mjs.
// Its `sample` refuses whatever the real one refuses: options that are not a plain object or carry an empty or unknown
// modelTier, a signal that is not an AbortSignal, cache beside tools, malformed tools (name, a description over 1 KB, an
// inputSchema over 4 KB or not an object), more than 16 tools, a tool result over 32 KB, images on a page that does not declare
// them or more images than allowed. It is passed to page.addInitScript(fakeClaude, options) and runs inside the page.
//   options.mode: 'tools' (this view runs page tools), 'no-tools' (limits() reports none), 'refuse-tools' (limits() says yes, the
//                 call says tools_unavailable), 'error' (every call fails upstream_error)
//   options.images: the page declares images (limits().images, at most 2 a call)
//   options.pages: {"<file name>|<page>": text} — a call with pictures that names «Page N of M of the file «name»» is answered with
//                  that page's text (a stand-in for Claude's reading; the test knows what each made-up page says)
//   options.pictures: what a call with pictures does — 'read' (answers from `pages`), 'not_granted', 'rate_limited' (every time),
//                  'flaky' (the first call for each page fails upstream_error, the second answers)
// What the page asked is kept on window.__calls ({prompt, tools, images}) for the test to read.
export function fakeClaude({ mode = 'tools', images = false, pages = {}, pictures = 'read' } = {}) {
  window.__calls = [];
  window.__prompts = [];
  const reject = (code, message) => Promise.reject({ code, message });
  const KNOWN = ['onText', 'signal', 'tools', 'images', 'modelTier', 'model', 'effort', 'fast', 'cache'];
  const bytes = s => new TextEncoder().encode(s).length;
  function check(opts) {
    if (opts === undefined) return null;
    if (!opts || Object.getPrototypeOf(opts) !== Object.prototype) return 'options must be a plain object';
    if ('modelTier' in opts && !['default', 'complex', 'quick', 'inherit'].includes(opts.modelTier)) return `unknown modelTier ${opts.modelTier}`;
    if ('signal' in opts && !(opts.signal instanceof AbortSignal)) return 'signal must be an AbortSignal';
    if ('onText' in opts && typeof opts.onText !== 'function') return 'onText must be a function';
    if (opts.tools && 'cache' in opts && opts.cache !== false) return 'cache with tools';
    if ('cache' in opts && ![true, false].includes(opts.cache) && (typeof opts.cache !== 'object' || opts.cache === null)) return 'cache';
    for (const k of Object.keys(opts)) if (!KNOWN.includes(k)) console.warn('unknown option', k);
    const names = new Set();
    for (const t of opts.tools || []) {
      if (!/^[A-Za-z0-9_-]{1,128}$/.test(t.name) || names.has(t.name)) return `tool name ${t.name}`;
      names.add(t.name);
      if (typeof t.description !== 'string' || !t.description || bytes(t.description) > 1024) return `tool ${t.name}: description`;
      if (t.inputSchema && (t.inputSchema.type !== 'object' || bytes(JSON.stringify(t.inputSchema)) > 4096)) return `tool ${t.name}: inputSchema`;
      if (typeof t.execute !== 'function') return `tool ${t.name}: execute`;
    }
    if ((opts.tools || []).length > 16) return 'too many tools';
    return null;
  }
  function imagesOf(opts) {
    if (!opts || !('images' in opts)) return { list: [] };
    if (!images) return { error: ['images_unavailable', 'the page does not declare images'] };
    const list = opts.images instanceof Blob ? [opts.images] : Array.from(opts.images || []);
    if (!list.every(b => b instanceof Blob)) return { error: ['invalid_request', 'images must be Blobs'] };
    if (list.length > 2) return { error: ['image_rejected', 'too many images'] };
    return { list };
  }
  async function call(opts, name, input) {
    const t = opts.tools.find(x => x.name === name);
    try {
      const out = await t.execute(input, { signal: new AbortController().signal });
      if (bytes(typeof out === 'string' ? out : JSON.stringify(out)) > 32 * 1024) throw { code: 'invalid_request', message: `${name}: result over 32 KB` };
      return out;
    } catch (e) { if (e?.code) throw e; return `Error: ${e.message}`; }
  }
  const fake = async (prompt, opts) => {
    const bad = check(opts);
    if (bad) return reject('invalid_request', bad);
    if (typeof prompt !== 'string' || !prompt) return reject('invalid_request', 'input');
    const img = imagesOf(opts);
    if (img.error) return reject(...img.error);
    window.__prompts.push(prompt);
    window.__calls.push({ prompt: prompt.slice(0, 200), tools: (opts?.tools || []).length, images: img.list.length });
    if (mode === 'error') return reject('upstream_error', 'connection dropped');
    if (img.list.length) {
      const m = prompt.match(/^Page (\d+) of \d+ of the file «(.+?)»\./);
      const key = m ? `${m[2]}|${m[1]}` : '';
      if (pictures === 'not_granted') return reject('not_granted', 'the viewer said no');
      if (pictures === 'rate_limited') return reject('rate_limited', 'the limit is spent');
      if (pictures === 'flaky') { window.__seen = window.__seen || {}; if (!window.__seen[key]) { window.__seen[key] = 1; return reject('upstream_error', 'connection dropped'); } }
      if (!(key in pages)) return { text: '', truncated: false, modelTierApplied: 'default' };
      return { text: pages[key], truncated: false, modelTierApplied: 'default' };
    }
    if (!opts?.tools) return { text: 'Testaphen 500 mg film-coated tablets (stand-in reading)', truncated: false, modelTierApplied: 'default' };
    if (mode !== 'tools') return reject('tools_unavailable', 'this view cannot run page tools');
    await call(opts, 'list_files', {});
    const page = await call(opts, 'read_page_text', { file: 'f1', page: 1 });
    await call(opts, 'record_fact', { field: 'batch', value: 'TP-24A118', file: 'f1', page: 1, quote: 'Batch TP-24A118' });
    await call(opts, 'record_fact', { field: 'batch', value: 'TP-24A117', file: 'f1', page: 1, quote: 'Batch TP-24A117' });
    opts.onText?.({ text: 'سجّلت رقم التشغيلة', delta: 'سجّلت رقم التشغيلة' });
    return { text: `سجّلت رقم التشغيلة TP-24A117 من صفحة 1. (${String(page.text || '').includes('TP-24A117') ? 'الصفحة اتقرت' : 'الصفحة ماتقراتش'})`, truncated: false, modelTierApplied: 'default' };
  };
  fake.json = async (prompt, opts) => {
    const bad = check(opts);
    if (bad) return reject('invalid_request', bad);
    window.__prompts.push(prompt);
    window.__calls.push({ prompt: prompt.slice(0, 200), tools: 0, images: 0, json: true });
    if (bytes(prompt) > 262144) return reject('prompt_too_large', 'over 256 KiB');
    if (mode === 'error') return reject('upstream_error', 'connection dropped');
    return { answer: prompt.includes('Batch TP-24A117') ? 'سجّلت رقم التشغيلة من نص الصفحة.' : 'مالقيتش الصفحة.',
             facts: [{ field: 'batch', value: 'TP-24A117', file: 'f1', page: 1, quote: 'Batch TP-24A117' },
                     { field: 'expiry', value: '2029', file: 'f1', page: 1, quote: 'Expiry date: 02/2029' }] };
  };
  fake.limits = async () => ({ maxPromptBytes: 262144,
    ...(images ? { images: { maxCount: 2, maxInputBytes: 20 * 1024 * 1024, mediaTypes: ['image/jpeg', 'image/png', 'image/webp', 'image/gif'] } } : {}),
    ...(mode === 'no-tools' ? {} : { tools: { maxCount: 16 } }) });
  window.claude = { use: async name => (name === 'sample' ? fake : null) };
}
