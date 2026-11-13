"""The Assistant's loop: Claude ⇄ the program's tools, in a background thread per dossier, with approvals, persistence,
context trimming and usage accounting. The conversation lives in the store (storage.py), so a closed window or a new
session continues where it stopped."""
import asyncio
import json
import threading
import time
import traceback

from ..app.store import ACTOR
from . import settings, storage, tools

PRICES = {'claude-opus-5-5': {'in': 4.0, 'out': 20.0, 'cache_read': 0.20, 'cache_write': 5.0},
          'claude-sonnet-5-5': {'in': 2.0, 'out': 10.0, 'cache_read': 0.20, 'cache_write': 2.5}}
BETAS = ['server-side-fallback-2026-07-01']
BUDGET_BETA = 'task-budgets-2026-03-13'
CONTEXT_CHARS = 600_000            # rough cap on the serialized conversation sent per request
CLIENT_FACTORY = None              # tests inject a fake: callable(api_key) → client with .beta.messages.stream(**kw)
_THREADS = {}

SYSTEM = """You are «المساعد» (the Assistant) inside Dossier Builder, a program that builds and reviews CTD/eCTD registration dossiers for the Egyptian Drug Authority (EDA) and other agencies, for a pharmaceutical company's regulatory affairs team. The user usually writes Egyptian Arabic: answer in Egyptian Arabic, direct and action-first; answer in English when they write English. Scientific names (INN, tests, standards) stay in English; Arabic trade names stay in Arabic (name_ar).

How you work
- The program is the system of record. You act only through the tools: read the dossier and its documents, write data, place documents, generate drafts, run and judge the review, draft letters. Every write is recorded in the program's audit trail under your name with your rationale, so give a real rationale (document and page).
- Never guess. A value you write must have been read in a document (or said by the user). A field you cannot read stays empty and you say so. A date you cannot read stays empty.
- Read before you write: open a document with read_document (text and the attached pages — scans and stamps are only visible on the pages), then write what it states. After reading a document, save a short digest with save_reading so later sessions do not re-read it; check get_readings first.
- One active substance per apis entry, with its strength, its manufacturer and country as printed; two substances may share one manufacturer; an unnamed manufacturer stays empty.
- EDA forms are label:value tables. Final Registration License: «Trade Name» (Latin and Arabic), «Dosage Form», «Active Ingredient(s) & Strength(s): Each 1g contains …» one substance per line, «Shelf Life», «Storage Condition», «Approved Pack», «Price» one line per pack, «Type of License: Toll/Own», «Type of Marketing: Local/Export», «Registration No.», «Invalidation Date» (valid_until), «License Holder» (applicant), «Manufacturer» (finished product), «Manufacturer Of active substance» (substance name, then its company and country on the next line; the Arabic notes may list other approved or not-permitted suppliers), «Issue Date». CADC Notification Letter: batch number · expiry/re-test · Conform/Non-conform. Pricing letter: «Each 1g contains: A x mg + B y mg …» and a price per pack.
- Export, signing a review and withdrawing a document pause for the user's approval: the program asks them; do not ask again in text, just call the tool when it is the right step and tell the user it waits for their approval.
- Review: run_review gives the deterministic findings; you judge the open ones from the documents (get_finding → read_document → act_on_finding with the evidence), draft responses with add_response, and reassess after data or documents change. Your assessments are provisional until the human reviewer confirms them.
- Budget: each of your turns has a limited number of steps and tokens. Do the most valuable work first; for a large job, finish a coherent part, report, and propose the next part. Read long documents by page ranges, only the pages you need.
- Reviewing ONE document per the rules: get_document_rubric gives the rules that apply to that document (the review pack's questions for its CTD item plus general document rules, each with its source); read the whole document (read_document by page ranges); then record_document_review with one finding per rule: verdict adequate | deficient | not_assessable, where (page, excerpt), what is wrong and the required change, in English and Arabic. Judge content, not presence: wording, values, consistency with the licence and the data, required statements, signatures and dates.
- Amending a document per the rules: a Word document → amend_document with precise edits (quote the paragraph to find, give the new text, name the rule and the reason); the program writes TRACKED CHANGES and a change log, and stores the result as a new unsigned draft version the company reviews in Word, accepts and signs. A PDF the company authored (no Word source) → amendment_memo listing rule · where · finding · required change; the company applies it in its source. A third-party document (certificate, licence, CPP, GMP, supplier CoA) is NEVER altered → amendment_memo for the issuer and request_reissue. A document the program generated → fix the data (put_data) and generate_document again.
- PDFs: the program's PDF engine is PdfCraft. For anything a document's PDF holds or needs — a phrase and where it is on the page, its fonts, bookmarks, links, comments, signatures, faux redactions, its text layer (OCR), its pages — find the tool with pdf_tools and run it with pdf_run (reading tools freely; changing tools with save: true, the company's own documents only, as a new version).
- Finish every turn with a short report: what you read, what you wrote (which items), what you found, and what the user must do (sign, approve, provide). Short sentences; lists for parallel items; no decoration.
"""


def client_for(workspace):
    key = settings.api_key(workspace)
    if CLIENT_FACTORY is not None:
        return CLIENT_FACTORY(key)
    import anthropic
    return anthropic.Anthropic(api_key=key, max_retries=3)


def _dump(block):
    if hasattr(block, 'model_dump'):
        return block.model_dump(exclude_none=True)
    return dict(block)


def _u(usage, key):
    if usage is None:
        return 0
    v = usage.get(key) if isinstance(usage, dict) else getattr(usage, key, 0)
    return int(v or 0)


def cost_usd(model, u):
    p = PRICES.get(model) or PRICES['claude-opus-5-5']
    return round((u.get('input_tokens', 0) * p['in'] + u.get('output_tokens', 0) * p['out'] + u.get('cache_read_input_tokens', 0) * p['cache_read']
                  + u.get('cache_creation_input_tokens', 0) * p['cache_write']) / 1e6, 4)


class Ctx:
    def __init__(self, runner):
        self.st, self.did, self.user, self.never_send = runner.st, runner.did, runner.user, runner.cfg.get('never_send') or []
        self.call = runner.call
        self.run_async = runner.run_async


class Runner:
    def __init__(self, app, st, did, user='local'):
        self.app, self.st, self.did, self.user = app, st, did, user
        self.cfg = settings.load(st.root)
        self.loop = None
        self.rid = None

    # ---------------- in-process HTTP: the program's own API, as the screen uses it, with the actor «claude»
    async def _acall(self, method, path, json_body=None, params=None, files=None, data=None):
        import httpx
        headers = {'X-DB': '1', 'X-DB-Internal': getattr(self.app.state, 'internal_token', ''), 'X-DB-Actor': 'claude'}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://assistant.local', timeout=600) as c:
            r = await c.request(method, path, json=json_body, params=params, files=files, data=data, headers=headers)
        ct = r.headers.get('content-type', '')
        try:
            body = r.json() if 'json' in ct else {'text': r.text[:2000]}
        except ValueError:
            body = {'text': r.text[:2000]}
        return r.status_code, body

    def call(self, method, path, json=None, params=None, files=None, data=None):
        if self.loop is None:
            self.loop = asyncio.new_event_loop()
        return self.loop.run_until_complete(self._acall(method, path, json, params, files, data))

    def run_async(self, coro):
        if self.loop is None:
            self.loop = asyncio.new_event_loop()
        return self.loop.run_until_complete(coro)

    # ---------------- prompt
    def _context_block(self):
        d = self.st.dossier(self.did)
        b = self.st.board(self.did)
        latest = None
        try:
            from ..review import storage as rstore
            latest = rstore.latest(self.st, self.did)
        except Exception:
            pass
        prof = d.get('profile') or {}
        pk = self.st.pack(d['pack'])
        whom = pk.authority['name']['en'] + (f" — country of registration {(d.get('envelope') or {}).get('country')}" if (d.get('envelope') or {}).get('country') else '')
        lines = [f"Dossier «{d['name']}» (id {d['id']}), rule pack {d['pack']}.",
                 f"Authority this dossier is for: {whom}. Module 1 follows this authority; Modules 2 to 5 are the common CTD."
                 + ('' if pk.egypt else " This is NOT an Egyptian dossier: EDA's forms, decrees and NP.CAPP rules do not apply to it; the review desk, the variations planner and the"
                    " eCTD package are Egypt's and are not offered here — it exports as CTD folders."
                    + (" The program holds only a general Module 1 for this country: say what must be checked against the authority's own checklist." if pk.meta.get('verified') is False else '')),
                 f"Product: {json.dumps(d.get('product') or {}, ensure_ascii=False)}",
                 f"Applicant/envelope: {json.dumps(d.get('envelope') or {}, ensure_ascii=False)}",
                 f"Profile: {json.dumps({k: v for k, v in prof.items() if k != 'apis'}, ensure_ascii=False)}; APIs in profile: "
                 f"{', '.join((a.get('name') or '?') + ' / ' + (a.get('manufacturer') or '?') for a in prof.get('apis') or []) or 'none'}",
                 f"Items by status: {json.dumps(b['counts'])}; unplaced files: {len(b['unassigned'])}; saved readings: {len(storage.readings(self.st, self.did))}.",
                 f"Latest review: {latest['id'] + ' → ' + str(latest.get('verdict')) if latest else 'none yet'}.",
                 f"User: {self.user}. Date: {time.strftime('%Y-%m-%d')}. Steps allowed this turn: {self.cfg['max_steps']}."]
        return '\n'.join(lines)

    def _messages(self):
        msgs = [{'role': m['role'], 'content': m['content']} for m in storage.messages(self.st, self.did)]
        # attachments (PDF pages, images) stay only in the last two user turns; older ones become a note
        user_idx = [i for i, m in enumerate(msgs) if m['role'] == 'user']
        keep = set(user_idx[-2:])
        for i, m in enumerate(msgs):
            if m['role'] != 'user' or i in keep or not isinstance(m['content'], list):
                continue
            new = []
            for b in m['content']:
                if b.get('type') in ('document', 'image'):
                    new.append({'type': 'text', 'text': f"[{b.get('type')} «{b.get('title', '')}» was attached here earlier]"})
                elif b.get('type') == 'tool_result' and isinstance(b.get('content'), str) and len(b['content']) > 4000 and i not in set(user_idx[-6:]):
                    new.append({**b, 'content': b['content'][:1500] + ' … [older result shortened]'})
                else:
                    new.append(b)
            m['content'] = new
        # size cap: drop the oldest turns (from a user text message, so tool_use/tool_result pairs stay together)
        def size(ms):
            return sum(len(json.dumps(m['content'], ensure_ascii=False)) for m in ms)
        starts = [i for i, m in enumerate(msgs) if m['role'] == 'user' and not (isinstance(m['content'], list) and any(b.get('type') == 'tool_result' for b in m['content']))]
        while size(msgs) > CONTEXT_CHARS and len(starts) > 1:
            cut = starts[1]
            msgs = msgs[cut:]
            starts = [i - cut for i in starts[1:]]
        return msgs

    def _system(self):
        return [{'type': 'text', 'text': SYSTEM, 'cache_control': {'type': 'ephemeral'}}, {'type': 'text', 'text': self._context_block()}]

    # ---------------- the model
    def _call_model(self, msgs):
        client = client_for(self.st.root)
        kw = dict(model=self.cfg['model'], max_tokens=16000, system=self._system(), tools=tools.SPECS, messages=msgs,
                  betas=BETAS + [BUDGET_BETA], fallbacks='default',
                  output_config={'effort': self.cfg['effort'], 'task_budget': {'type': 'tokens', 'total': int(self.cfg['budget_tokens'])}})
        for attempt in (1, 2):
            try:
                return self._stream(client, kw)
            except Exception as e:                              # a platform that rejects the task budget: once more without it
                msg = str(e)
                if attempt == 1 and ('task_budget' in msg or 'task-budgets' in msg or 'output_config' in msg):
                    kw['betas'] = BETAS
                    kw['output_config'] = {'effort': self.cfg['effort']}
                    continue
                raise

    def _stream(self, client, kw):
        buf, last = '', 0.0
        with client.beta.messages.stream(**kw) as stream:
            for text in stream.text_stream:
                buf += text
                if time.time() - last > 0.7:
                    storage.update_run(self.st, self.rid, partial=buf[-4000:])
                    last = time.time()
            msg = stream.get_final_message()
        storage.update_run(self.st, self.rid, partial=None)
        return msg

    # ---------------- tools
    def _execute(self, tu):
        try:
            out = tools.run_tool(Ctx(self), tu['name'], tu.get('input') or {})
            return {'type': 'tool_result', 'tool_use_id': tu['id'], 'content': out['content']}, out.get('attach') or []
        except tools.ToolError as e:
            return {'type': 'tool_result', 'tool_use_id': tu['id'], 'content': f'Error: {e}', 'is_error': True}, []
        except Exception as e:                                  # a bug must not kill the run: Claude sees it and continues
            return {'type': 'tool_result', 'tool_use_id': tu['id'], 'content': f'Error: {type(e).__name__}: {str(e)[:500]}', 'is_error': True}, []

    @staticmethod
    def _user_turn(results, attach, names):
        content = list(results)
        if attach:
            content.append({'type': 'text', 'text': 'Attached: pages/images returned by ' + ', '.join(names) + ' (in the same order).'})
            content.extend(attach)
        return content

    # ---------------- the loop
    def start(self, rid):
        self.rid = rid
        t = threading.Thread(target=self._thread, args=(self._loop,), daemon=True, name=f'assistant-{self.did[:8]}')
        _THREADS[rid] = t
        t.start()
        return t

    def _thread(self, fn, *a):
        token = ACTOR.set('claude')
        try:
            fn(*a)
        except Exception as e:
            storage.update_run(self.st, self.rid, status='error', ended=time.time(), error=f'{type(e).__name__}: {str(e)[:800]}', partial=None)
            self.st.audit(self.did, 'assistant.error', run=self.rid, error=str(e)[:300])
            traceback.print_exc()
        finally:
            ACTOR.reset(token)
            if self.loop is not None:
                self.loop.close()
                self.loop = None

    def _loop(self):
        st, did, rid = self.st, self.did, self.rid
        while True:
            run = storage.run(st, rid)
            if run['stop']:
                storage.update_run(st, rid, status='stopped', ended=time.time(), partial=None)
                storage.add_message(st, did, rid, 'assistant', [{'type': 'text', 'text': '(stopped by the user)'}])
                return
            if run['steps'] >= int(self.cfg['max_steps']):
                storage.add_message(st, did, rid, 'assistant', [{'type': 'text', 'text': f"Reached the step limit for one turn ({self.cfg['max_steps']}). Send «continue» to go on."}])
                storage.update_run(st, rid, status='done', ended=time.time(), partial=None)
                return
            msg = self._call_model(self._messages())
            content = [_dump(b) for b in msg.content]
            usage = {k: _u(msg.usage, k) for k in ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens')}
            usage['cost_usd'] = cost_usd(self.cfg['model'], usage)
            storage.add_message(st, did, rid, 'assistant', content)
            storage.add_usage(st, rid, usage)
            stop = getattr(msg, 'stop_reason', None)
            if stop == 'pause_turn':
                continue
            if stop == 'refusal':
                det = getattr(msg, 'stop_details', None)
                why = getattr(det, 'explanation', None) or (det.get('explanation') if isinstance(det, dict) else None) or ''
                storage.add_message(st, did, rid, 'assistant', [{'type': 'text', 'text': 'Claude declined this request. ' + str(why)}])
                storage.update_run(st, rid, status='error', ended=time.time(), error='refusal', partial=None)
                return
            uses = [b for b in content if b.get('type') == 'tool_use']
            if stop != 'tool_use' or not uses:
                if stop == 'max_tokens':
                    storage.add_message(st, did, rid, 'assistant', [{'type': 'text', 'text': '(the answer was cut at the length limit; send «continue»)'}])
                storage.update_run(st, rid, status='done', ended=time.time(), partial=None)
                return
            results, attach, names, pending = {}, [], [], []
            for tu in uses:
                if tu['name'] in tools.APPROVAL:
                    storage.add_approval(st, did, rid, tu['id'], tu['name'], tu.get('input') or {})
                    pending.append(tu['id'])
                    continue
                res, att = self._execute(tu)
                results[tu['id']] = res
                if att:
                    attach.extend(att)
                    names.append(tu['name'])
            if pending:
                storage.update_run(st, rid, status='waiting_approval', pending={'results': results, 'attach': attach, 'names': names, 'order': [tu['id'] for tu in uses]})
                self.st.audit(did, 'assistant.approval_requested', run=rid, tools=[tu['name'] for tu in uses if tu['id'] in pending])
                return
            storage.add_message(st, did, rid, 'user', self._user_turn([results[tu['id']] for tu in uses], attach, names))

    # ---------------- approvals
    def continue_after_approvals(self, rid):
        self.rid = rid
        t = threading.Thread(target=self._thread, args=(self._resume,), daemon=True, name=f'assistant-{self.did[:8]}')
        _THREADS[rid] = t
        t.start()
        return t

    def _resume(self):
        st, did, rid = self.st, self.did, self.rid
        run = storage.run(st, rid)
        pend = run['pending'] or {}
        results, attach, names = dict(pend.get('results') or {}), list(pend.get('attach') or []), list(pend.get('names') or [])
        for ap in storage.approvals(st, did, run_id=rid):
            if ap['tool_use_id'] in results or ap['status'] == 'pending':
                continue
            if ap['status'] == 'approved':
                res, att = self._execute({'id': ap['tool_use_id'], 'name': ap['tool'], 'input': ap['args']})
                storage.decide_approval(st, ap['id'], 'approved', ap['by'], ap['note'], result=(res['content'] if isinstance(res['content'], str) else 'ok')[:2000])
                results[ap['tool_use_id']] = res
                attach.extend(att)
            else:
                results[ap['tool_use_id']] = {'type': 'tool_result', 'tool_use_id': ap['tool_use_id'],
                                              'content': 'The user declined this action.' + (f" Note: {ap['note']}" if ap.get('note') else ''), 'is_error': False}
        order = pend.get('order') or list(results)
        storage.add_message(st, did, rid, 'user', self._user_turn([results[i] for i in order if i in results], attach, names))
        storage.update_run(st, rid, status='running', pending={})
        self._loop()


# ---------------- entry points used by the API
def send(app, st, did, user, text, staged=None):
    """A new user message → a run in the background. Returns the run id."""
    if storage.active_run(st, did):
        raise RuntimeError('busy')
    note = ''
    if staged:
        note = '\n\n[Files uploaded with this message, stored as unplaced documents: ' + '; '.join(f"{d['filename']} (id {d['id']})" for d in staged) + ']'
    rid = storage.start_run(st, did, user)
    storage.add_message(st, did, rid, 'user', [{'type': 'text', 'text': (text or '').strip() + note}])
    st.audit(did, 'assistant.message', run=rid, chars=len(text or ''), files=[d['id'] for d in (staged or [])])
    Runner(app, st, did, user).start(rid)
    return rid


def decide(app, st, did, aid, decision, by, note=None):
    ap = storage.approval(st, aid)
    if not ap or ap['dossier_id'] != did:
        raise KeyError('approval')
    if ap['status'] != 'pending':
        raise ValueError('decided')
    run = storage.run(st, ap['run_id'])
    storage.decide_approval(st, aid, 'approved' if decision == 'approve' else 'denied', by, note)
    st.audit(did, 'assistant.approval', run=ap['run_id'], tool=ap['tool'], decision=decision, by=by, note=note)
    if run and run['status'] == 'waiting_approval' and not storage.approvals(st, did, status='pending', run_id=ap['run_id']):
        Runner(app, st, did, run.get('user') or by).continue_after_approvals(ap['run_id'])
        return 'resumed'
    return 'recorded'


def stop(st, did):
    run = storage.active_run(st, did)
    if not run:
        return None
    storage.update_run(st, run['id'], stop=1)
    if run['status'] == 'waiting_approval':                     # nothing is running: close it now
        for ap in storage.approvals(st, did, status='pending', run_id=run['id']):
            storage.decide_approval(st, ap['id'], 'denied', 'stop', 'stopped')
        storage.update_run(st, run['id'], status='stopped', ended=time.time(), pending={})
    return run['id']


def render(st, did):
    """The conversation for the screen: user text, assistant text + tool chips, compact tool results (attachments omitted)."""
    out = []
    for m in storage.messages(st, did):
        c = m['content']
        if m['role'] == 'user':
            if isinstance(c, list) and any(b.get('type') == 'tool_result' for b in c):
                items = []
                for b in c:
                    if b.get('type') != 'tool_result':
                        continue
                    txt = b['content'] if isinstance(b['content'], str) else ' '.join(x.get('text', '') for x in b['content'] if isinstance(x, dict))
                    items.append({'tool_use_id': b['tool_use_id'], 'error': bool(b.get('is_error')), 'summary': txt[:400]})
                out.append({'id': m['id'], 'kind': 'results', 'items': items, 'created': m['created']})
            else:
                text = c if isinstance(c, str) else ' '.join(b.get('text', '') for b in c if b.get('type') == 'text')
                out.append({'id': m['id'], 'kind': 'user', 'text': text, 'created': m['created']})
        else:
            text = ' '.join(b.get('text', '') for b in c if b.get('type') == 'text').strip()
            uses = [{'id': b['id'], 'name': b['name'], 'args': {k: (v if len(json.dumps(v, ensure_ascii=False)) < 160 else '…') for k, v in (b.get('input') or {}).items()}}
                    for b in c if b.get('type') == 'tool_use']
            if text or uses:
                out.append({'id': m['id'], 'kind': 'assistant', 'text': text, 'tools': uses, 'created': m['created']})
    return out
