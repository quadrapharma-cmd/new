"""Claude's part through the real Anthropic library (the version the Mac runtime pins), against a stand-in of the Claude API on
this computer that answers as the API does, as a stream of server-sent events. It checks what the program sends (the model, the
effort, the two caching marks, every tool with its input streamed) and what it makes of the answers: Claude's thinking kept and
sent back as it came, a tool input that arrives in pieces, a page sent as a picture, an input that does not fit its tool sent
back to Claude instead of stopping the run, `finish` refused while a decision of the same turn is refused, an input cut off by
the output limit never run, the usage counted at its price, and the API's refusal ending the task with its reason. No network,
no key, no cost."""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import anthropic
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'engine'))

from dossier_engine.combined.decide import brain  # noqa: E402
from dossier_engine.combined.decide.case import READ_TOOLS  # noqa: E402
from dossier_engine.combined.decide.tasks import FINISH, TOOLS  # noqa: E402

PNG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
TURN_COST = (1000 * 4.00 + 120 * 20.00 + 2000 * 5.00 + 3000 * 0.20) / 1e6       # the usage every answer below reports


def answer(blocks, stop):
    """One answer as the API streams it. blocks: ('thinking', text, signature) | ('text', text) | ('tool', id, name, [pieces])"""
    out = []

    def ev(kind, **data):
        out.append(f'event: {kind}\ndata: {json.dumps({"type": kind, **data})}\n\n')
    ev('message_start', message={'id': 'msg_stand_in', 'type': 'message', 'role': 'assistant', 'model': 'claude-opus-5-5',
                                 'content': [], 'stop_reason': None, 'stop_sequence': None,
                                 'usage': {'input_tokens': 1000, 'output_tokens': 1, 'cache_creation_input_tokens': 2000,
                                           'cache_read_input_tokens': 3000}})
    for i, b in enumerate(blocks):
        if b[0] == 'thinking':
            ev('content_block_start', index=i, content_block={'type': 'thinking', 'thinking': '', 'signature': ''})
            ev('content_block_delta', index=i, delta={'type': 'thinking_delta', 'thinking': b[1]})
            ev('content_block_delta', index=i, delta={'type': 'signature_delta', 'signature': b[2]})
        elif b[0] == 'text':
            ev('content_block_start', index=i, content_block={'type': 'text', 'text': ''})
            ev('content_block_delta', index=i, delta={'type': 'text_delta', 'text': b[1]})
        else:
            ev('content_block_start', index=i, content_block={'type': 'tool_use', 'id': b[1], 'name': b[2], 'input': {}})
            for piece in b[3]:
                ev('content_block_delta', index=i, delta={'type': 'input_json_delta', 'partial_json': piece})
        ev('content_block_stop', index=i)
    ev('message_delta', delta={'stop_reason': stop, 'stop_sequence': None}, usage={'output_tokens': 120})
    ev('message_stop')
    return ''.join(out).encode()


class StandIn:
    """The Claude API's stand-in: each POST to /v1/messages gets the next answer (a stream, or (status, error body))."""

    def __init__(self, answers):
        self.answers, self.requests = list(answers), []
        stand = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                stand.requests.append({'path': self.path, 'headers': {k.lower(): v for k, v in self.headers.items()}, 'body': body})
                a = stand.answers.pop(0)
                code, kind, raw = (a[0], 'application/json', json.dumps(a[1]).encode()) if isinstance(a, tuple) else \
                    (200, 'text/event-stream', a)
                self.send_response(code)
                self.send_header('Content-Type', kind)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *a):
                pass

        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.client = anthropic.Anthropic(api_key='sk-ant-api03-stand-in', base_url=f'http://127.0.0.1:{self.httpd.server_address[1]}',
                                          max_retries=0)

    def close(self):
        self.httpd.shutdown()


@pytest.fixture()
def run():
    made = []

    def go(answers, handlers, budget_usd=5.0):
        stand = StandIn(answers)
        made.append(stand)
        log, budget = [], brain.Budget(budget_usd)
        tools = READ_TOOLS + TOOLS['documents'] + [FINISH]
        try:
            state = brain.converse(stand.client, 'documents', 'TASK 1 — the documents (a test)', tools, 'The case file.',
                                   {'finish': lambda a: 'Done.', **handlers}, budget, log.append)
        except brain.Stop as e:
            state = e
        return state, stand.requests, log, budget
    yield go
    for s in made:
        s.close()


def test_a_task_through_the_real_library(run):
    read = []
    handlers = {'read_pages': lambda a: read.append(a) or f"the text of pages {a['pages']}",
                'view_page': lambda a: [{'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png', 'data': PNG}}],
                'leave_out': lambda a: (_ for _ in ()).throw(brain.ToolError('Page 999 is not in the dossier (1-40).'))}
    state, sent, log, budget = run([
        answer([('thinking', 'The first pages first.', 'sig-1'),
                ('tool', 'toolu_1', 'read_pages', ['{"pag', 'es": "1-', '2"}']),       # the input arrives in pieces
                ('tool', 'toolu_2', 'view_page', ['{"page": 3}'])], 'tool_use'),
        answer([('tool', 'toolu_3', 'read_pages', ['{}']),                              # no «pages»: back to Claude
                ('tool', 'toolu_4', 'leave_out', ['{"pages": "999", "why": "blank"}']),  # refused by the program
                ('tool', 'toolu_5', 'finish', ['{"summary": "too early"}'])], 'tool_use'),
        answer([('text', 'Corrected.'), ('tool', 'toolu_6', 'finish', ['{"summary": "documents placed"}'])], 'tool_use')],
        handlers)
    assert state == {'finished': True, 'summary': 'documents placed', 'turns': 3}
    assert read == [{'pages': '1-2'}]                                                   # the empty input never reached it

    first = sent[0]
    assert first['path'] == '/v1/messages' and 'sk-ant-api03-stand-in' in first['headers']['authorization']
    b = first['body']
    assert b['model'] == 'claude-opus-5-5' and b['max_tokens'] == 32000 and b['stream'] is True
    assert b['output_config'] == {'effort': 'high'} and b['cache_control'] == {'type': 'ephemeral'}
    assert b['system'][0]['cache_control'] == {'type': 'ephemeral'} and 'thinking' not in b    # always on for this model
    assert b['messages'] == [{'role': 'user', 'content': 'The case file.'}]
    assert [t['name'] for t in b['tools']] == [t['name'] for t in READ_TOOLS + TOOLS['documents'] + [FINISH]]
    assert all(t['eager_input_streaming'] is True for t in b['tools'])

    mine, back = sent[1]['body']['messages'][1:]
    assert mine['role'] == 'assistant'
    assert mine['content'][0] == {'type': 'thinking', 'thinking': 'The first pages first.', 'signature': 'sig-1'}
    assert [(c['type'], c['id'], c['input']) for c in mine['content'][1:]] == \
        [('tool_use', 'toolu_1', {'pages': '1-2'}), ('tool_use', 'toolu_2', {'page': 3})]
    assert back['content'][0] == {'type': 'tool_result', 'tool_use_id': 'toolu_1', 'content': 'the text of pages 1-2'}
    assert back['content'][1]['content'][0]['source'] == {'type': 'base64', 'media_type': 'image/png', 'data': PNG}

    errors = sent[2]['body']['messages'][-1]['content']
    assert [(e['tool_use_id'], e['is_error']) for e in errors] == [('toolu_3', True), ('toolu_4', True), ('toolu_5', True)]
    assert 'input.pages is missing' in errors[0]['content'] and 'Page 999' in errors[1]['content']
    assert errors[2]['content'].startswith('Not finished: 2 of this turn')
    assert any(e.get('error') == 'input.pages is missing' for e in log)

    assert budget.calls == 3 and budget.spent == pytest.approx(3 * TURN_COST)
    assert budget.tokens == {'input_tokens': 3000, 'output_tokens': 360, 'cache_creation_input_tokens': 6000,
                             'cache_read_input_tokens': 9000}


def test_an_input_cut_off_by_the_output_limit_is_never_run(run):
    read = []
    state, sent, log, _ = run([
        answer([('tool', 'toolu_1', 'read_pages', ['{"pages": "1-'])], 'max_tokens'),   # cut in the middle of its input
        answer([('tool', 'toolu_2', 'finish', ['{"summary": "done"}'])], 'tool_use')],
        {'read_pages': lambda a: read.append(a) or 'text'})
    assert state['finished'] and read == []
    if len(sent) == 2 and sent[1]['body']['messages'][-1]['role'] == 'user' and \
            isinstance(sent[1]['body']['messages'][-1]['content'], list):           # the library gave the partial input
        cut = sent[1]['body']['messages'][-1]['content'][0]
        assert cut['is_error'] and 'cut off' in cut['content']


def test_the_api_refusing_ends_the_task_with_its_reason(run):
    state, sent, log, budget = run([(400, {'type': 'error', 'error': {'type': 'invalid_request_error',
                                                                         'message': 'messages: the request is not valid'}})], {})
    assert isinstance(state, brain.Stop) and state.why == 'api'
    assert 'BadRequestError' in str(state) and 'the request is not valid' in str(state)
    assert budget.calls == 0 and budget.spent == 0


def test_claude_declining_ends_the_task(run):
    state, *_ = run([answer([('text', 'I cannot help with this.')], 'refusal')], {})
    assert isinstance(state, brain.Stop) and state.why == 'refusal'


def test_the_budget_stops_the_next_call(run):
    state, sent, _, budget = run([answer([('tool', 'toolu_1', 'read_pages', ['{"pages": "1"}'])], 'tool_use')],
                                 {'read_pages': lambda a: 'text'}, budget_usd=TURN_COST / 2)
    assert isinstance(state, brain.Stop) and state.why == 'budget' and len(sent) == 1
