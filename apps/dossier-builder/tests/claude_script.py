"""A stand-in for the Claude API in the tests: it answers each task's conversation with tool calls written in advance (or made
from the work folder by a function), as the real API would send them, and counts made-up usage. No network, no key, no cost.
It also keeps what the program sent back for each call, so a test can see the refusals Claude would have read."""
import itertools

from anthropic.types import Message, TextBlock, ToolUseBlock, Usage

TASK_OF = {'TASK 1 —': 'documents', 'TASK 2 —': 'product', 'TASK 3 —': 'pi', 'TASK 4 —': 'review', 'TASK 5 —': 'sequence'}
_ids = itertools.count(1)


def _message(blocks, stop):
    return Message.model_construct(id=f'msg_{next(_ids)}', type='message', role='assistant', model='claude-opus-5-5',
                                   content=blocks, stop_reason=stop, stop_sequence=None,
                                   usage=Usage.model_construct(input_tokens=1200, output_tokens=300,
                                                               cache_creation_input_tokens=800, cache_read_input_tokens=5000))


class _Stream:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        return iter(())

    def get_final_message(self):
        return self.msg


class ScriptedClient:
    """script: {task: [turn, …]}; a turn is a list of (tool name, input) or a function of the work folder that returns one."""

    def __init__(self, script, work=None):
        self.script = script
        self.work = work
        self.turn = {}
        self.sent = []                      # (task, tool results) the program sent back
        self.messages = self

    def stream(self, **kw):
        system = kw['system'][0]['text']
        task = next(v for k, v in TASK_OF.items() if k in system)
        last = kw['messages'][-1]
        if last['role'] == 'user' and isinstance(last['content'], list):
            self.sent.append((task, last['content']))
        n = self.turn.get(task, 0)
        self.turn[task] = n + 1
        turns = self.script.get(task, [])
        if n >= len(turns):
            return _Stream(_message([TextBlock.model_construct(type='text', text='(nothing more)')], 'end_turn'))
        calls = turns[n](self.work) if callable(turns[n]) else turns[n]
        blocks = [ToolUseBlock.model_construct(id=f'toolu_{next(_ids)}', type='tool_use', name=name, input=inp) for name, inp in calls]
        return _Stream(_message(blocks, 'tool_use'))

    def errors(self, task=None):
        """The refusals the program sent back (what Claude would read and correct)."""
        return [r['content'] for t, res in self.sent if task in (None, t) for r in res if r.get('is_error')]
