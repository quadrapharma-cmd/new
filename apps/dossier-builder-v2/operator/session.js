// The Operator's dealings with Claude Code, without the page: which connector and tools it needs, where the program's
// repository is, and how a session's transcript is read. Kept apart from the panel so the tests can load it directly.
export const CONNECTOR = 'Claude Code Remote';
export const TOOLS = ['list_environments', 'create_session', 'send_message', 'list_events', 'get_session'];
export const REPO = { url: 'https://github.com/quadrapharma-cmd/new', branch: 'claude/new-session-8nmyo7' };

// ---------------------------------------------------------------- reading a session's transcript
// list_events gives {ccr: {data: [event…], first_id, last_id, has_more}}; each event carries one of user / assistant /
// result, the message under internal_anthropic_catchall.message (or message).
export function readEvents(payload) {
  const box = payload?.ccr ?? payload ?? {};
  const out = [];
  for (const e of box.data || []) {
    if (e.result) { out.push({ kind: 'done', id: e.result.uuid || e.created_at }); continue; }
    const side = e.user ? 'user' : e.assistant ? 'assistant' : null;
    if (!side) continue;
    const ev = e[side];
    const msg = ev.internal_anthropic_catchall?.message ?? ev.message ?? {};
    const content = typeof msg.content === 'string' ? [{ type: 'text', text: msg.content }] : (msg.content || []);
    const id = ev.uuid || e.created_at;
    if (side === 'user') {
      if (ev.isSynthetic || content.some(b => b.type === 'tool_result')) continue;
      const text = content.filter(b => b.type === 'text').map(b => b.text).join('\n')
        .replace(/<system-reminder>[\s\S]*?<\/system-reminder>/g, '').trim();
      if (text) out.push({ kind: 'you', id, text });
      continue;
    }
    const tools = ev.tool_use_meta || [];
    for (const b of content) {
      if (b.type === 'text' && b.text.trim()) out.push({ kind: 'op', id: id + ':' + out.length, text: b.text.trim() });
      if (b.type === 'tool_use') {
        const meta = tools.find(m => m.id === b.id);
        out.push({ kind: 'step', id: b.id, text: meta?.display_name || b.name.replace(/^mcp__[^_]+__/, '') });
      }
    }
  }
  return { items: out, last: box.last_id || null, more: !!box.has_more };
}
export const sessionIdOf = payload => (JSON.stringify(payload ?? '').match(/session_[A-Za-z0-9]+/) || [])[0] || null;

