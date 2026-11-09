"""Assistant settings on the workspace: the Anthropic API key (never in git, never returned to the browser), model, effort,
per-task token budget, the document classes that are never sent to Claude. The environment variable ANTHROPIC_API_KEY wins."""
import json
import os
import sys
from pathlib import Path

FILE = 'assistant.json'
DEFAULTS = {'model': 'claude-opus-5-5', 'effort': 'high', 'budget_tokens': 120_000, 'max_steps': 40, 'never_send': []}
MODELS = ['claude-opus-5-5', 'claude-sonnet-5-5']
EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max']


def path(workspace):
    return Path(workspace) / FILE


def load(workspace):
    p = path(workspace)
    d = dict(DEFAULTS)
    if p.exists():
        try:
            d.update(json.loads(p.read_text(encoding='utf-8')))
        except (ValueError, OSError):
            pass
    return d


def save(workspace, **changes):
    d = load(workspace)
    for k, v in changes.items():
        if v is None:
            continue
        if k == 'api_key':
            if v == '':
                d.pop('api_key', None)
            else:
                d['api_key'] = v.strip()
        elif k == 'model' and v in MODELS:
            d['model'] = v
        elif k == 'effort' and v in EFFORTS:
            d['effort'] = v
        elif k == 'budget_tokens' and isinstance(v, int) and 20_000 <= v <= 1_000_000:
            d['budget_tokens'] = v
        elif k == 'max_steps' and isinstance(v, int) and 1 <= v <= 200:
            d['max_steps'] = v
        elif k == 'never_send' and isinstance(v, list):
            d['never_send'] = [str(x) for x in v]
    p = path(workspace)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return status(workspace)


def api_key(workspace):
    return os.environ.get('ANTHROPIC_API_KEY') or load(workspace).get('api_key') or None


def key_source(workspace):
    if os.environ.get('ANTHROPIC_API_KEY'):
        return 'env'
    if load(workspace).get('api_key'):
        return 'file'
    return None


def status(workspace):
    """What the UI may know: configured or not (never the key itself), where it comes from, the model and limits."""
    d = load(workspace)
    browser = sys.platform == 'emscripten'
    src = None if browser else key_source(workspace)
    key = d.get('api_key') or ''
    return {'configured': bool(src), 'source': src, 'browser': browser, 'model': d['model'], 'effort': d['effort'],
            'budget_tokens': d['budget_tokens'], 'max_steps': d['max_steps'], 'never_send': d['never_send'],
            'key_hint': (key[:7] + '…' + key[-4:]) if len(key) > 14 else ('set' if key else ''), 'models': MODELS, 'efforts': EFFORTS}
