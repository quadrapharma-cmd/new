// A stand-in for the Anthropic API on this machine, for the workshop's browser tests: the models list, and the Messages API as the
// SDK streams it (server-sent events), with the CORS answers a page opened from the disk (origin «null») needs; the key checked
// as the API checks it (the SDK sends it as a Bearer token, which the API takes, as a wrong key's 401 from it shows). What it answers:
//   - a page sent as pictures («Page N of M of the file «name».»): that page's own text, from `pages` ({'name|N': text});
//   - «You sort the documents…»: the place `places` gives for the file named in the question;
//   - a request with tools: first a call of list_documents, then an answer naming how many documents the tool listed.
// Every request is kept (GET /calls). A key other than `key` is refused (401) as the API refuses it.
import http from 'node:http';

const sse = (res, events) => {
  res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache', 'access-control-allow-origin': '*' });
  for (const e of events) res.write(`event: ${e.type}\ndata: ${JSON.stringify(e)}\n\n`);
  res.end();
};
function stream(res, model, blocks, stop) {
  const events = [{ type: 'message_start', message: { id: `msg_${Date.now()}`, type: 'message', role: 'assistant', model, content: [], stop_reason: null, stop_sequence: null,
                                                       usage: { input_tokens: 120, output_tokens: 1 } } }];
  blocks.forEach((b, i) => {
    if (b.type === 'text') {
      events.push({ type: 'content_block_start', index: i, content_block: { type: 'text', text: '' } });
      for (let at = 0; at < b.text.length; at += 40) events.push({ type: 'content_block_delta', index: i, delta: { type: 'text_delta', text: b.text.slice(at, at + 40) } });
    } else {
      events.push({ type: 'content_block_start', index: i, content_block: { type: 'tool_use', id: b.id, name: b.name, input: {} } });
      events.push({ type: 'content_block_delta', index: i, delta: { type: 'input_json_delta', partial_json: JSON.stringify(b.input) } });
    }
    events.push({ type: 'content_block_stop', index: i });
  });
  events.push({ type: 'message_delta', delta: { stop_reason: stop, stop_sequence: null }, usage: { output_tokens: 42 } }, { type: 'message_stop' });
  sse(res, events);
}

export function fakeApi({ key = 'sk-ant-test-key', pages = {}, places = {} } = {}) {
  const calls = [];
  const server = http.createServer((req, res) => {
    const cors = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': 'GET, POST, OPTIONS' };
    if (req.method === 'OPTIONS') { res.writeHead(204, cors); return res.end(); }
    if (req.url === '/calls') { res.writeHead(200, { ...cors, 'content-type': 'application/json' }); return res.end(JSON.stringify(calls)); }
    let body = '';
    req.on('data', c => { body += c; });
    req.on('end', () => {
      const json = body ? JSON.parse(body) : null;
      // the SDK sends the key as «Authorization: Bearer <key>»; the API takes it so, or as x-api-key
      const authorised = req.headers['x-api-key'] === key || req.headers.authorization === `Bearer ${key}`;
      const text = (json?.messages || []).flatMap(m => (typeof m.content === 'string' ? [m.content] : m.content.filter(c => c.type === 'text').map(c => c.text))).join('\n');
      const images = (json?.messages || []).flatMap(m => (typeof m.content === 'string' ? [] : m.content.filter(c => c.type === 'image'))).length;
      calls.push({ path: req.url.split('?')[0], method: req.method, authorised, sent: String(req.headers['x-api-key'] || req.headers.authorization || '').slice(0, 20), images, tools: (json?.tools || []).map(t => t.name), prompt: text.slice(0, 300),
                   browser: req.headers['anthropic-dangerous-direct-browser-access'] || null, effort: json?.output_config?.effort || null });
      if (!authorised) {
        res.writeHead(401, { ...cors, 'content-type': 'application/json' });
        return res.end(JSON.stringify({ type: 'error', error: { type: 'authentication_error', message: 'invalid x-api-key' } }));
      }
      if (req.method === 'GET' && req.url.startsWith('/v1/models')) {
        res.writeHead(200, { ...cors, 'content-type': 'application/json' });
        return res.end(JSON.stringify({ data: [{ type: 'model', id: 'stand-in-large', display_name: 'Stand-in (large)', created_at: '2026-01-01T00:00:00Z' },
                                                { type: 'model', id: 'stand-in-small', display_name: 'Stand-in (small)', created_at: '2026-01-02T00:00:00Z' }],
                                        has_more: false, first_id: 'stand-in-large', last_id: 'stand-in-small' }));
      }
      if (req.method === 'POST' && req.url.startsWith('/v1/messages')) {
        const model = json.model;
        if (images) {
          const m = /Page (\d+) of \d+ of the file «(.+?)»/.exec(text);
          return stream(res, model, [{ type: 'text', text: (m && pages[`${m[2]}|${m[1]}`]) || '' }], 'end_turn');
        }
        if (/You sort the documents/.test(text)) {
          const file = /File: (.+)/.exec(text)?.[1] || '';
          const hit = Object.entries(places).find(([k]) => file.includes(k));
          return stream(res, model, [{ type: 'text', text: JSON.stringify({ place: hit ? hit[1] : '', type: 'document', type_ar: 'مستند', party: 'eda', sure: !!hit, why: 'كلمة الإيصال في أول الصفحة' }) }], 'end_turn');
        }
        if (json.tools?.length) {
          const last = json.messages[json.messages.length - 1];
          const result = Array.isArray(last.content) && last.content.find(c => c.type === 'tool_result');
          if (!result) return stream(res, model, [{ type: 'text', text: 'هشوف المستندات.' }, { type: 'tool_use', id: 'toolu_1', name: 'list_documents', input: {} }], 'tool_use');
          const n = JSON.parse(result.content).documents.length;
          return stream(res, model, [{ type: 'text', text: `في الملف ${n} مستندات.` }], 'end_turn');
        }
        return stream(res, model, [{ type: 'text', text: '{}' }], 'end_turn');
      }
      res.writeHead(404, cors); res.end();
    });
  });
  return new Promise(ok => server.listen(0, '127.0.0.1', () => ok({ server, url: `http://127.0.0.1:${server.address().port}`, calls })));
}
