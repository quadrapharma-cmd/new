"""One task's conversation with Claude: the playbook (system prompt), the tools, the case file (first message). Claude reads
the dossier with the reading tools and records its decisions with the writing tools until it calls `finish`. Every call's
tokens and cost are counted against the dossier's budget; every tool call goes to the log, with its result."""
import json
import time
from collections import Counter

MODEL = 'claude-opus-5-5'
# US dollars per million tokens (the Claude API's price list for this model): input, output, cache write (5 minutes), cache read
PRICES = {'claude-opus-5-5': (4.00, 20.00, 5.00, 0.20)}


class ToolError(Exception):
    """A decision the program cannot apply as given: the message goes back to Claude, which corrects it."""


class Stop(Exception):
    """The task stops before it is finished: the budget is spent, Claude declined, or it does not finish."""

    def __init__(self, why, detail=''):
        super().__init__(f'{why}: {detail}' if detail else why)
        self.why = why


class Budget:
    """What the dossier may cost, and what it has cost so far (the Claude API's usage of every call, at its price)."""

    def __init__(self, limit_usd):
        self.limit = float(limit_usd)
        self.spent = 0.0
        self.tokens = Counter()
        self.calls = 0

    def add(self, model, usage):
        p_in, p_out, p_cw, p_cr = PRICES.get(model, PRICES[MODEL])
        u = {k: int(getattr(usage, k, 0) or 0)
             for k in ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')}
        cost = (u['input_tokens'] * p_in + u['output_tokens'] * p_out + u['cache_creation_input_tokens'] * p_cw
                + u['cache_read_input_tokens'] * p_cr) / 1e6
        self.tokens.update(u)
        self.spent += cost
        self.calls += 1
        return cost

    def left(self):
        return self.limit - self.spent

    def record(self):
        return {'limit_usd': self.limit, 'spent_usd': round(self.spent, 4), 'calls': self.calls, 'tokens': dict(self.tokens)}


def brief(x, n=300):
    """A short form of a tool's input or result for the log."""
    if isinstance(x, list):
        x = ' '.join(b.get('text', f"[{b.get('type')}]") if isinstance(b, dict) else str(b) for b in x)
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + f'… ({len(s)} characters)'


def _err(tool_id, text):
    return {'type': 'tool_result', 'tool_use_id': tool_id, 'content': text, 'is_error': True}


JSON_TYPES = {'string': str, 'integer': int, 'number': (int, float), 'boolean': bool, 'array': list, 'object': dict}


def misfit(schema, value, where='input'):
    """Why a tool's input does not fit the tool's schema (its required fields, its types and its allowed values, all the way
    down), or '' when it fits. A streamed input can arrive cut off, and the schema is not enforced by the API: every input is
    checked before its tool runs, and one that does not fit goes back to Claude to send again."""
    if not schema:
        return ''
    if 'anyOf' in schema:
        return '' if any(not misfit(s, value, where) for s in schema['anyOf']) else f'{where} is not of an allowed form'
    t = schema.get('type')
    py = JSON_TYPES.get(t)
    if py and (not isinstance(value, py) or (t in ('integer', 'number') and isinstance(value, bool))):
        return f'{where} should be of type {t}'
    if 'enum' in schema and value not in schema['enum']:
        return f'{where} should be one of {schema["enum"]}'
    if t == 'object':
        for k in schema.get('required', []):
            if k not in value:
                return f'{where}.{k} is missing'
        more = schema.get('additionalProperties')
        for k, v in value.items():
            why = misfit(schema.get('properties', {}).get(k, more if isinstance(more, dict) else None), v, f'{where}.{k}')
            if why:
                return why
    if t == 'array' and 'items' in schema:
        for i, v in enumerate(value):
            why = misfit(schema['items'], v, f'{where}[{i}]')
            if why:
                return why
    return ''


def converse(client, task, system, tools, first, handlers, budget, log, *, model=MODEL, effort='high', max_tokens=32000,
             max_turns=90):
    """Run one task to its `finish`. `handlers` maps each tool's name to a function of its input that returns a string (or a
    list of content blocks) or raises ToolError. Returns {'finished', 'summary', 'turns'}; raises Stop."""
    messages = [{'role': 'user', 'content': first}]
    schemas = {t['name']: t.get('input_schema') for t in tools}
    state = {'finished': False, 'summary': '', 'turns': 0}
    nudges = bad_json = 0
    for turn in range(max_turns):
        if budget.left() <= 0:
            raise Stop('budget', f'{budget.spent:.2f} of {budget.limit:.2f} USD spent')
        t0 = time.time()
        try:
            with client.messages.stream(model=model, max_tokens=max_tokens,
                                        system=[{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral'}}],
                                        tools=tools, messages=messages, output_config={'effort': effort},
                                        cache_control={'type': 'ephemeral'}) as stream:
                for _ in stream:
                    pass
                msg = stream.get_final_message()
            bad_json = 0
        except ValueError:                          # a tool input the library could not parse at all: the turn again (bounded)
            bad_json += 1
            if bad_json > 2:
                raise Stop('bad tool input')
            continue
        except Exception as e:                      # the API refused or could not be reached (after the library's retries)
            if type(e).__module__.split('.')[0] != 'anthropic':
                raise
            raise Stop('api', f'{type(e).__name__}: {e}'[:400]) from e
        cost = budget.add(model, msg.usage)
        state['turns'] = turn + 1
        log({'task': task, 'turn': turn + 1, 'stop': msg.stop_reason, 'seconds': round(time.time() - t0, 1),
             'cost_usd': round(cost, 4), 'spent_usd': round(budget.spent, 4)})
        messages.append({'role': 'assistant', 'content': msg.content})
        if msg.stop_reason == 'refusal':
            raise Stop('refusal', getattr(getattr(msg, 'stop_details', None), 'explanation', '') or '')
        if msg.stop_reason == 'pause_turn':
            continue
        uses = [b for b in msg.content if b.type == 'tool_use']
        if not uses:
            nudges += 1
            if nudges > 2:
                raise Stop('no tool call')
            messages.append({'role': 'user', 'content': 'Record your decisions with the tools; call finish when the task is done.'})
            continue
        results, finish = [], None
        for b in uses:
            if msg.stop_reason == 'max_tokens' and b is uses[-1]:          # its input was cut off: never run it
                results.append(_err(b.id, 'Your last tool input was cut off by the output limit. Send it again in smaller parts.'))
                log({'task': task, 'tool': b.name, 'ok': False, 'error': 'cut off'})
                continue
            fn = handlers.get(b.name)
            if fn is None or not isinstance(b.input, dict):
                results.append(_err(b.id, f'Unknown tool or input: {b.name}'))
                continue
            why = misfit(schemas.get(b.name), b.input)
            if why:
                results.append(_err(b.id, f'This input does not fit the tool: {why}. Send it again, whole.'))
                log({'task': task, 'tool': b.name, 'input': brief(b.input), 'ok': False, 'error': why})
                continue
            if b.name == 'finish':                                          # decided after the turn's other calls
                finish = (len(results), b)
                results.append(None)
                continue
            try:
                out = fn(b.input)
                log({'task': task, 'tool': b.name, 'input': brief(b.input), 'ok': True, 'result': brief(out, 200)})
                results.append({'type': 'tool_result', 'tool_use_id': b.id, 'content': out if isinstance(out, list) else str(out)})
            except ToolError as e:
                log({'task': task, 'tool': b.name, 'input': brief(b.input), 'ok': False, 'error': brief(str(e), 600)})
                results.append(_err(b.id, str(e)))
            except (KeyError, IndexError, TypeError, ValueError) as e:   # an input the schema allows but the program cannot use
                why = f'{type(e).__name__}: {e}'
                log({'task': task, 'tool': b.name, 'input': brief(b.input), 'ok': False, 'error': 'not usable: ' + brief(why, 600)})
                results.append(_err(b.id, f'This input could not be used ({brief(why, 300)}). Check it and send it again.'))
        if finish:
            i, b = finish
            refused = sum(1 for r in results if r and r.get('is_error'))
            if not refused:
                state['finished'] = True
                state['summary'] = str(b.input.get('summary', ''))
                return state
            results[i] = _err(b.id, f'Not finished: {refused} of this turn\'s decisions were refused. Correct them, then call finish again.')
            log({'task': task, 'tool': 'finish', 'ok': False, 'error': f'{refused} refused in the same turn'})
        messages.append({'role': 'user', 'content': results})
    raise Stop('too many turns', str(max_turns))
