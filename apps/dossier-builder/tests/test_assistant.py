"""The Assistant («المساعد») with a scripted stand-in for the Anthropic client: settings (the key never comes back), a message
that makes Claude look at the board, read an attached scan (pages attached), write data, save a digest and place the file,
then ask to export — which waits for the user's approval — and finish; audit rows carry the actor «claude»."""
import io, json, os, re, time
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf_lines
from dossier_engine.app.api import create_app
from dossier_engine.assistant import runner, settings as asettings


class FakeStream:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    @property
    def text_stream(self):
        for b in self.msg.content:
            if b['type'] == 'text':
                yield b['text']

    def get_final_message(self):
        return self.msg


def msg(content, stop='end_turn'):
    return SimpleNamespace(content=content, stop_reason=stop, usage={'input_tokens': 1200, 'output_tokens': 150, 'cache_read_input_tokens': 800, 'cache_creation_input_tokens': 0}, model='fake')


def _last_user(kw):
    return [m for m in kw['messages'] if m['role'] == 'user'][-1]


def _results(kw):
    out = {}
    for b in _last_user(kw)['content']:
        if isinstance(b, dict) and b.get('type') == 'tool_result':
            out[b['tool_use_id']] = b
    return out


class FakeClient:
    """Each step is a function(kw) → message; kw is what the runner sent (system, tools, messages…)."""
    def __init__(self, steps):
        self.steps, self.calls = list(steps), []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))
        self.models = SimpleNamespace(retrieve=lambda m: SimpleNamespace(id=m, display_name='Fake model'))

    def _stream(self, **kw):
        self.calls.append(kw)
        step = self.steps.pop(0)
        return FakeStream(step(kw))


def script():
    def s1(kw):
        text = _last_user(kw)['content'][0]['text']
        doc = re.search(r'id ([0-9a-f-]{36})', text).group(1)
        return msg([{'type': 'text', 'text': 'هبص على اللوحة وأقرأ الملف.'},
                    {'type': 'tool_use', 'id': 'tu1', 'name': 'get_board', 'input': {'only_open': True}},
                    {'type': 'tool_use', 'id': 'tu2', 'name': 'read_document', 'input': {'doc_id': doc, 'pages': '1-1'}}], 'tool_use')

    def s2(kw):
        res = _results(kw)
        board = json.loads(res['tu1']['content'])
        slot = next(s['slot_id'] for s in board['slots'] if s['level'] == 'R' and s['status'] == 'not_started' and '@' not in s['slot_id'])
        doc = board['unassigned'][0]['id']
        assert 'Dermacure' in res['tu2']['content'] or 'document:' in res['tu2']['content']
        return msg([{'type': 'tool_use', 'id': 'tu3', 'name': 'put_data', 'input': {'data': {'apis': [{'name': 'Neomycin Sulphate', 'strength': '3.500 mg', 'manufacturer': 'Sichuan Example Pharmaceutical Co.Ltd', 'country': 'China'}]},
                                                                                       'rationale': 'Final Registration License p.1'}},
                    {'type': 'tool_use', 'id': 'tu4', 'name': 'save_reading', 'input': {'doc_id': doc, 'pages': '1', 'note': 'Licence 29925/2022: Dermacure topical powder; Neomycin Sulphate 3.500 mg.'}},
                    {'type': 'tool_use', 'id': 'tu5', 'name': 'place_document', 'input': {'doc_id': doc, 'slot_id': slot, 'rationale': 'it is the registration licence'}}], 'tool_use')

    def s3(kw):
        res = _results(kw)
        assert all(not r.get('is_error') for r in res.values()), res
        return msg([{'type': 'text', 'text': 'البيانات اتكتبت والملف اتحط في مكانه. هصدّر دلوقتي.'},
                    {'type': 'tool_use', 'id': 'tu6', 'name': 'export_dossier', 'input': {'rationale': 'the user asked for it', 'outputs': ['ctd']}}], 'tool_use')

    def s4(kw):
        res = _results(kw)
        assert 'tu6' in res
        return msg([{'type': 'text', 'text': 'خلصت: ' + ('التصدير اترفض' if res['tu6'].get('is_error') or 'declined' in str(res['tu6']['content']) else 'التصدير تم') + '.'}])
    return [s1, s2, s3, s4]


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    fake = FakeClient(script())
    runner.CLIENT_FACTORY = lambda key: fake
    try:
        c = TestClient(create_app(tmp_path / 'ws'))
        yield c, fake, tmp_path / 'ws'
    finally:
        runner.CLIENT_FACTORY = None


def _new_dossier(c):
    r = c.post('/api/dossiers', json={'name': 'Dermacure 10 g', 'profile': {'dossier_kind': 'generic', 'origin': 'local', 'licence': 'own', 'activity': 'new', 'admin_route': 'topical',
                                                                           'leaflet': 'english', 'dosage_specifics': [], 'apis': [{'name': 'Neomycin Sulphate', 'manufacturer': 'Sichuan Example', 'option': 'FULL'}]},
                                      'product': {'name': 'Dermacure', 'dosage_form': 'Topical Powder'}, 'envelope': {'applicant': 'EXAMPLE PHARM'}})
    assert r.status_code in (200, 201), r.text
    return r.json()['id']


def _wait(c, did, states=('waiting_approval', 'done', 'error', 'stopped'), timeout=30):
    for _ in range(int(timeout * 10)):
        s = c.get(f'/api/dossiers/{did}/assistant').json()
        if s['run'] and s['run']['status'] in states:
            return s
        time.sleep(0.1)
    raise AssertionError('assistant did not reach ' + str(states) + ': ' + json.dumps(s['run']))


def test_settings_key_is_stored_privately(app_client):
    c, fake, ws = app_client
    s = c.get('/api/assistant/settings').json()
    assert s['configured'] is False and s['browser'] is False and s['model'] == 'claude-opus-5-5'
    assert c.get('/api/capabilities').json()['assistant']['configured'] is False
    r = c.put('/api/assistant/settings', json={'api_key': 'sk-ant-test-0123456789abcdef', 'effort': 'medium', 'budget_tokens': 60000})
    assert r.status_code == 200, r.text
    s = r.json()
    assert s['configured'] and s['source'] == 'file' and s['effort'] == 'medium' and s['budget_tokens'] == 60000
    assert 'sk-ant-test-0123456789abcdef' not in json.dumps(s) and s['key_hint'].startswith('sk-ant-') and '…' in s['key_hint']
    p = ws / 'assistant.json'
    assert p.exists() and (os.stat(p).st_mode & 0o777) == 0o600
    assert c.post('/api/assistant/settings/test').json()['ok'] is True
    # a dossier without a key: the Assistant says so instead of failing silently
    c.put('/api/assistant/settings', json={'api_key': ''})
    did = _new_dossier(c)
    r = c.post(f'/api/dossiers/{did}/assistant/messages', data={'text': 'اقرأ'})
    assert r.status_code == 501 and r.json()['detail']['code'] == 'E-NO-AI'


def test_assistant_reads_writes_places_and_waits_for_approval(app_client, tmp_path):
    c, fake, ws = app_client
    c.put('/api/assistant/settings', json={'api_key': 'sk-ant-test-0123456789abcdef'})
    did = _new_dossier(c)
    lic = make_pdf_lines(tmp_path / 'licence.pdf', ['Egyptian Drug Authority', 'Final Registration License', 'Trade Name: Dermacure', 'Registration No.: 29925/2022'], 'Licence')
    r = c.post(f'/api/dossiers/{did}/assistant/messages', data={'text': 'اقرأ الإخطار ده واملأ البيانات وحطه في مكانه، وبعدين صدّر الملف.'},
               files=[('files', ('licence.pdf', io.BytesIO(lic.read_bytes()), 'application/pdf'))])
    assert r.status_code == 201, r.text
    assert r.json()['staged'][0]['filename'] == 'licence.pdf'
    assert c.post(f'/api/dossiers/{did}/assistant/messages', data={'text': 'تاني'}).status_code == 409        # one run at a time
    s = _wait(c, did)
    assert s['run']['status'] == 'waiting_approval', s['run']
    assert len(s['approvals']) == 1 and s['approvals'][0]['tool'] == 'export_dossier'
    # what Claude saw: the system prompt is cached, the tools are the program's, the scan pages were attached after the tool results
    kw1 = fake.calls[0]
    assert kw1['system'][0]['cache_control'] == {'type': 'ephemeral'} and 'Dermacure' in kw1['system'][1]['text']
    assert {t['name'] for t in kw1['tools']} >= {'get_board', 'read_document', 'put_data', 'place_document', 'export_dossier'}
    kw2 = fake.calls[1]
    blocks = _last_user(kw2)['content']
    assert blocks[0]['type'] == 'tool_result' and blocks[1]['type'] == 'tool_result' and any(b.get('type') == 'document' for b in blocks)
    # the work landed in the program
    d = c.get(f'/api/dossiers/{did}').json()
    assert d['data']['apis'][0]['strength'] == '3.500 mg' and d['data']['apis'][0]['country'] == 'China'
    board = c.get(f'/api/dossiers/{did}/board').json()
    assert not board['unassigned'] and any(doc['filename'] == 'licence.pdf' for s_ in board['slots'] for doc in s_['documents'])
    assert c.get(f'/api/dossiers/{did}/assistant/readings').json()[0]['note'].startswith('Licence 29925/2022')
    audit = c.get(f'/api/dossiers/{did}/audit').json()
    claude = [a for a in audit if a['actor'] == 'claude']
    assert {a['event'] for a in claude} >= {'data.updated', 'document.added', 'assistant.tool'}
    assert any(a['event'] == 'assistant.tool' and a['detail'].get('rationale') == 'Final Registration License p.1' for a in claude)
    # the user decides; the Assistant finishes its turn
    aid = s['approvals'][0]['id']
    r = c.post(f'/api/dossiers/{did}/assistant/approvals/{aid}', json={'decision': 'deny', 'note': 'not yet'})
    assert r.status_code == 200 and r.json()['result'] == 'resumed'
    s = _wait(c, did, states=('done', 'error'))
    assert s['run']['status'] == 'done', s['run']
    kinds = [m['kind'] for m in s['messages']]
    assert kinds[0] == 'user' and 'assistant' in kinds and 'results' in kinds
    assert s['messages'][-1]['kind'] == 'assistant' and 'اترفض' in s['messages'][-1]['text']
    assert 'declined' in str(_last_user(fake.calls[3])['content'][0]['content'])
    assert s['usage']['input_tokens'] == 4 * 1200 and s['usage']['cost_usd'] > 0 and s['run']['steps'] == 4
    assert any(a['event'] == 'assistant.approval' and a['detail']['decision'] == 'deny' for a in c.get(f'/api/dossiers/{did}/audit').json())
    # clear keeps the audit, removes the chat
    assert c.delete(f'/api/dossiers/{did}/assistant').json()['messages'] == []
    assert any(a['actor'] == 'claude' for a in c.get(f'/api/dossiers/{did}/audit').json())


def test_stop_and_tool_errors_do_not_kill_the_run(app_client):
    c, fake, ws = app_client
    c.put('/api/assistant/settings', json={'api_key': 'sk-ant-test-0123456789abcdef'})
    did = _new_dossier(c)
    fake.steps = [lambda kw: msg([{'type': 'tool_use', 'id': 'x1', 'name': 'get_slot', 'input': {'slot_id': 'NOPE'}},
                                  {'type': 'tool_use', 'id': 'x2', 'name': 'read_document', 'input': {'doc_id': 'missing'}}], 'tool_use'),
                  lambda kw: msg([{'type': 'text', 'text': 'errors seen: ' + str(sum(1 for r in _results(kw).values() if r.get('is_error')))}])]
    c.post(f'/api/dossiers/{did}/assistant/messages', data={'text': 'جرّب'})
    s = _wait(c, did, states=('done', 'error'))
    assert s['run']['status'] == 'done' and s['messages'][-1]['text'] == 'errors seen: 2'
    assert c.post(f'/api/dossiers/{did}/assistant/stop').json()['stopped'] is None           # nothing running
