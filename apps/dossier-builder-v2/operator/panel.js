// The Operator («المشغّل»): a fixed part of the program, on every page — a button that opens a conversation with the
// program's operator, a Claude Code session that runs the program, its operations and its code.
//
// How each edition reaches the operator:
//   claude.ai  — through the viewer's own «Claude Code Remote» connector (the page's `mcp` capability): the first message
//                opens an operator session on the program's repository, later messages go to that session, and the
//                replies are read back from its transcript. It runs on the viewer's own claude.ai account.
//   desktop    — the installed program carries its own operator (window.DBK_OPERATOR, see mountOperator). Opened as a plain
//                file there is no connection, and the panel says so.
import BRIEF from './brief.md';
import { CONNECTOR, TOOLS, REPO, readEvents, sessionIdOf } from './session.js';
const ENV_NAME = 'quadrapharma new';
const TAG = 'dossier-builder-operator';

const W = {
  ar: {
    open: 'المشغّل', title: 'المشغّل', sub: 'اطلب أي حاجة في البرنامج: سؤال، تعديل، مراجعة، نشر',
    placeholder: 'اكتب طلبك هنا… (Enter للإرسال، Shift+Enter لسطر جديد)', send: 'ابعت', close: 'قفل', fresh: 'محادثة جديدة',
    you: 'إنت', op: 'المشغّل', working: 'المشغّل شغال…', idle: 'جاهز', starting: 'بفتح جلسة المشغّل…',
    sending: 'ببعت…', step: s => `بيشتغل: ${s}`, empty: 'ابدأ بطلبك، والمشغّل هيرد هنا. أمثلة:',
    examples: ['راجع موقع الهيئة وقولي فيه جديد ولا لأ', 'إيه المطلوب في 3.2.P.8 عند الهيئة؟', 'انشر المكتبة بآخر تعديل'],
    session: id => `الجلسة: ${id}`, openSession: 'افتحها في Claude',
    noShell: 'النسخة دي اتفتحت كملف من غير برنامج المشغّل، فمفيش اتصال. المشغّل شغال في نسخة claude.ai، وفي نسخة الكمبيوتر بعد ما تتسطّب.',
    noMcp: 'الصفحة مش قادرة توصل لـ Claude Code من العرض ده. افتح المكتبة على claude.ai واسمح لها بـ «Claude Code Remote» لما تسألك.',
    missing: list => `ربط «Claude Code Remote» عندك ناقصه: ${list}. من غيرهم المشغّل مش هيقدر يشتغل من هنا.`,
    codes: {
      server_not_connected: 'ضيف «Claude Code Remote» من إعدادات claude.ai ← Connectors، وارجع جرّب.',
      needs_reauth: 'ربط «Claude Code Remote» محتاج تسجيل دخول تاني: من إعدادات claude.ai ← Connectors.',
      selection_required: 'عندك أكتر من ربط بنفس الاسم «Claude Code Remote»: اختار واحد لما claude.ai يسألك.',
      not_in_manifest: 'ربط «Claude Code Remote» مقفول للصفحة دي. افتحه من قايمة الصلاحيات بتاعة الصفحة.',
      blocked_by_policy: 'إعدادات مؤسستك مانعة الأداة دي من هنا.',
      approval_required: 'الطلب محتاج موافقتك: دوس «ابعت» تاني ووافق لما claude.ai يسألك.',
      server_unavailable: 'Claude Code مش بيرد دلوقتي. استنى شوية وجرّب تاني.',
      tool_error: 'Claude Code رفض الطلب:',
      other: 'حصلت مشكلة في الاتصال:',
    },
    notSent: 'الرسالة ماوصلتش.', maybeSent: 'مش متأكد الرسالة وصلت ولا لأ؛ هشوف الجلسة قبل ما تبعتها تاني.',
  },
  en: {
    open: 'Operator', title: 'Operator', sub: 'Ask for anything in the program: a question, a change, a check, a publish',
    placeholder: 'Write your request… (Enter to send, Shift+Enter for a new line)', send: 'Send', close: 'Close', fresh: 'New conversation',
    you: 'You', op: 'Operator', working: 'The operator is working…', idle: 'Ready', starting: 'Opening the operator session…',
    sending: 'Sending…', step: s => `Working: ${s}`, empty: 'Start with your request; the operator answers here. For example:',
    examples: ['Check EDA\'s website and tell me what is new', 'What does EDA want in 3.2.P.8?', 'Publish the library with the latest change'],
    session: id => `Session: ${id}`, openSession: 'Open it in Claude',
    noShell: 'This copy was opened as a file, without the operator program, so it has no connection. The operator works in the claude.ai edition, and in the desktop edition once installed.',
    noMcp: 'This view cannot reach Claude Code. Open the library on claude.ai and allow «Claude Code Remote» when it asks.',
    missing: list => `Your «Claude Code Remote» connector lacks: ${list}. Without them the operator cannot work from here.`,
    codes: {
      server_not_connected: 'Add «Claude Code Remote» in claude.ai Settings → Connectors, then try again.',
      needs_reauth: 'Reconnect «Claude Code Remote» in claude.ai Settings → Connectors.',
      selection_required: 'You have more than one «Claude Code Remote» connector: choose one when claude.ai asks.',
      not_in_manifest: '«Claude Code Remote» is turned off for this page. Turn it on in the page\'s permissions.',
      blocked_by_policy: 'Your organization blocks this tool here.',
      approval_required: 'This needs your approval: press Send again and allow it when claude.ai asks.',
      server_unavailable: 'Claude Code is not answering right now. Wait a little and try again.',
      tool_error: 'Claude Code refused the request:',
      other: 'The connection failed:',
    },
    notSent: 'The message was not sent.', maybeSent: 'Not sure the message arrived; I will read the session before you send it again.',
  },
};

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
// A reply's own light formatting: **bold**, `code`, line breaks. Everything else stays text.
const fmt = s => esc(s).replace(/`([^`\n]+)`/g, '<code>$1</code>').replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');
const store = {
  get(k) { try { return localStorage.getItem('dbk.operator.' + k); } catch { return null; } },
  set(k, v) { try { if (v == null) localStorage.removeItem('dbk.operator.' + k); else localStorage.setItem('dbk.operator.' + k, v); } catch { /* fine */ } },
};

// ---------------------------------------------------------------- the panel
export function mountOperator() {
  const lang = () => (document.documentElement.lang === 'en' ? 'en' : 'ar');
  const w = k => W[lang()][k];
  const root = document.createElement('div');
  root.className = 'op';
  root.innerHTML = `
    <button type="button" class="op-fab" id="opFab" aria-expanded="false" aria-controls="opPanel">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 5h16v11H9l-5 4z"/><path d="M8 10h8M8 13h5"/></svg>
      <span data-w="open"></span><i class="op-dot" id="opDot" hidden></i></button>
    <section class="op-panel" id="opPanel" role="dialog" aria-labelledby="opTitle" hidden>
      <header class="op-head">
        <div><h2 id="opTitle" data-w="title"></h2><p data-w="sub"></p></div>
        <button type="button" class="op-x" id="opClose"><span class="sr" data-w="close"></span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg></button>
      </header>
      <div class="op-note" id="opNote" hidden></div>
      <div class="op-log" id="opLog" aria-live="polite"></div>
      <div class="op-state" id="opState"></div>
      <form class="op-form" id="opForm">
        <textarea id="opText" rows="3"></textarea>
        <div class="op-actions">
          <button type="button" class="op-fresh" id="opFresh" data-w="fresh"></button>
          <span class="op-sid" id="opSid"></span>
          <button type="submit" class="op-send" id="opSend" data-w="send"></button>
        </div>
      </form>
    </section>`;
  document.body.appendChild(root);
  const $ = id => root.querySelector('#' + id);

  const st = {
    sid: store.get('session'), items: [], seen: new Set(), last: null, busy: false, working: false,
    step: '', note: '', mcp: undefined, ready: null, timer: null, open: false,
  };

  function words() {
    for (const el of root.querySelectorAll('[data-w]')) el.textContent = w(el.dataset.w);
    $('opText').placeholder = w('placeholder');
    $('opText').setAttribute('aria-label', w('placeholder'));
    $('opClose').title = w('close');
    root.dir = lang() === 'ar' ? 'rtl' : 'ltr';
    draw();
  }
  function draw() {
    const log = $('opLog');
    if (!st.items.length) {
      log.innerHTML = `<p class="op-empty">${esc(w('empty'))}</p>${w('examples').map(x => `<button type="button" class="op-ex" data-ex="${esc(x)}">${esc(x)}</button>`).join('')}`;
    } else {
      const html = [];
      for (const it of st.items) {
        if (it.kind === 'you') html.push(`<div class="op-msg you"><b>${esc(w('you'))}</b><div>${fmt(it.text)}</div></div>`);
        else if (it.kind === 'op') html.push(`<div class="op-msg bot"><b>${esc(w('op'))}</b><div dir="auto">${fmt(it.text)}</div></div>`);
        else if (it.kind === 'note') html.push(`<div class="op-msg err">${esc(it.text)}</div>`);
      }
      log.innerHTML = html.join('');
      log.scrollTop = log.scrollHeight;
    }
    $('opState').textContent = st.busy ? w(st.sid ? 'sending' : 'starting') : st.working ? (st.step ? w('step')(st.step) : w('working')) : (st.sid ? w('idle') : '');
    $('opState').className = 'op-state' + (st.busy || st.working ? ' live' : '');
    $('opDot').hidden = !(st.busy || st.working);
    $('opSid').innerHTML = st.sid ? `<a href="https://claude.ai/code/${esc(st.sid)}" target="_blank" rel="noopener">${esc(w('openSession'))}</a>` : '';
    $('opFresh').hidden = !st.sid;
    $('opNote').hidden = !st.note;
    $('opNote').textContent = st.note;
    const blocked = !!st.note && st.ready === false;
    $('opSend').disabled = st.busy || blocked;
    $('opText').disabled = blocked;
  }
  const say = text => { st.items.push({ kind: 'note', text }); draw(); };
  function failure(e) {
    const c = w('codes');
    if (e?.code === 'tool_error' || !c[e?.code]) return `${e?.code === 'tool_error' ? c.tool_error : c.other} ${e?.message || e}`;
    return c[e.code];
  }

  // Can this view reach the operator? Answered once, when the panel first opens.
  async function connect() {
    if (st.ready !== null) return st.ready;
    if (window.DBK_OPERATOR) { st.mcp = window.DBK_OPERATOR; st.ready = true; return true; }   // the installed desktop program
    if (!window.claude?.use) { st.note = w('noShell'); st.ready = false; draw(); return false; }
    st.mcp = await window.claude.use('mcp').catch(() => null);
    if (!st.mcp) { st.note = w('noMcp'); st.ready = false; draw(); return false; }
    try {
      const { servers } = await st.mcp.listTools(CONNECTOR);
      const have = new Set((servers[0]?.tools || []).map(x => x.name));
      const lack = servers[0] ? TOOLS.filter(x => !have.has(x)) : [];
      if (!servers[0]) { st.note = w('codes').server_not_connected; st.ready = false; draw(); return false; }
      if (lack.length) { st.note = w('missing')(lack.join('، ')); st.ready = false; draw(); return false; }
    } catch (e) { st.note = failure(e); st.ready = false; draw(); return false; }
    st.ready = true;
    return true;
  }
  const call = async (tool, input) => (await st.mcp.callTool(CONNECTOR, tool, input, { cache: false })).payload;

  // ---- reading the session
  async function poll() {
    clearTimeout(st.timer);
    if (!st.sid || !st.ready) return;
    try {
      let more = true;
      while (more) {
        const input = { session_id: st.sid, kinds: ['user', 'assistant', 'result'], limit: 100 };
        if (st.last) input.after_id = st.last;
        const r = readEvents(await call('list_events', input));
        for (const it of r.items) {
          if (st.seen.has(it.id)) continue;
          st.seen.add(it.id);
          if (it.kind === 'step') { st.working = true; st.step = it.text; continue; }
          if (it.kind === 'done') { st.working = false; st.step = ''; continue; }
          if (it.kind === 'you') { st.working = true; st.step = ''; }
          st.items.push(it);
        }
        if (r.last) st.last = r.last;
        more = !!input.after_id && r.more;
      }
    } catch (e) {
      if (['server_not_connected', 'needs_reauth', 'not_in_manifest', 'blocked_by_policy'].includes(e?.code)) { st.note = failure(e); draw(); return; }
    }
    draw();
    if (st.open || st.working) st.timer = setTimeout(poll, st.working ? 4000 : 20000);
  }

  // ---- sending
  async function send(text) {
    text = text.trim();
    if (!text || st.busy) return;
    if (!(await connect())) return;
    st.busy = true; st.note = ''; draw();
    try {
      if (!st.sid) {
        const envs = (await call('list_environments', {}))?.environments || [];
        const env = envs.find(x => x.name === ENV_NAME) || envs[0];
        const made = await call('create_session', {
          title: 'مشغّل Dossier Builder', prompt: text, append_system_prompt: BRIEF,
          source_url: REPO.url, source_revision: REPO.branch, outcome_branch: REPO.branch,
          ...(env ? { environment_id: env.environment_id } : {}), tags: [TAG],
        });
        st.sid = sessionIdOf(made);
        if (!st.sid) throw Object.assign(new Error(JSON.stringify(made).slice(0, 300)), { code: 'tool_error' });
        store.set('session', st.sid);
      } else {
        await call('send_message', { session_id: st.sid, message: text });
      }
      st.items.push({ kind: 'you', id: 'local:' + Date.now(), text, local: true });
      $('opText').value = '';
      st.working = true;
    } catch (e) {
      const unsure = ['server_unavailable', 'upstream_error', 'cancelled'].includes(e?.code);
      say(`${unsure ? w('maybeSent') : w('notSent')} ${failure(e)}`);
    } finally {
      st.busy = false;
      draw();
      poll();
    }
  }
  // The message just sent shows at once; when the transcript brings it back it is not shown twice.
  const seenText = new Set();
  const origPush = st.items.push.bind(st.items);
  st.items.push = it => {
    if (it.kind === 'you') { if (it.local) seenText.add(it.text); else if (seenText.delete(it.text)) return st.items.length; }
    return origPush(it);
  };

  async function show(open) {
    st.open = open;
    $('opPanel').hidden = !open;
    $('opFab').setAttribute('aria-expanded', String(open));
    root.classList.toggle('on', open);
    if (!open) return;
    $('opText').focus();
    if (await connect()) poll();
  }
  $('opFab').addEventListener('click', () => show(!st.open));
  $('opClose').addEventListener('click', () => { show(false); $('opFab').focus(); });
  $('opForm').addEventListener('submit', e => { e.preventDefault(); send($('opText').value); });
  $('opText').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send($('opText').value); } });
  $('opFresh').addEventListener('click', () => {
    st.sid = null; st.items.length = 0; st.seen.clear(); st.last = null; st.working = false; st.step = '';
    store.set('session', null); draw(); $('opText').focus();
  });
  root.addEventListener('click', e => { const b = e.target.closest('[data-ex]'); if (b) { $('opText').value = b.dataset.ex; $('opText').focus(); } });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && st.open && (root.contains(document.activeElement) || document.activeElement === document.body)) { show(false); $('opFab').focus(); } });
  new MutationObserver(words).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
  words();
  return { show, send, state: st };
}
