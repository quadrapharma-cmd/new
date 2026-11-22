"""eBOX on a Mac: one page in the browser, served from this computer only. The person chooses the folder of the dossier received,
presses «ابدأ», and the program does the rest, Claude included: the stages run in their own process, the page shows them as
they go, with Claude's decisions and their cost, and opens the delivery folder at the end.

The Claude API key is kept on this Mac only, in a file only the person's account can read (mode 0600); it goes to the program's
own process and to the Claude API, nowhere else. The server answers only 127.0.0.1, only requests carrying the token it was
started with, and only for this host and port (another web page cannot drive it)."""
import datetime
import json
import os
import re
import secrets
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ..common import FONTS

HERE = Path(__file__).resolve().parent
STAGES = ['read', 'repeats', 'ocr', 'split', 'assemble', 'checks', 'decide', 'fix', 'ectd', 'report']
STAGE_AR = {'read': 'قراءة الملفات الواردة صفحةً صفحة', 'repeats': 'الكتل المكررة', 'ocr': 'التعرف الضوئي على الصفحات الممسوحة',
            'split': 'تقسيم الملف إلى مستندات CTD', 'assemble': 'بناء مجلد CTD ومطابقة كل صفحة بأصلها', 'checks': 'الفحوص',
            'decide': 'قرارات Claude', 'fix': 'التصحيحات ومعلومات المستحضر', 'ectd': 'تسلسل eCTD والتحقق منه',
            'report': 'التقريران والتسليم'}
DEFAULT_BUDGET_USD = 25.0


def support_dir():
    d = Path(os.environ.get('EBOX_SUPPORT') or Path.home() / 'Library' / 'Application Support' / 'eBOX')
    d.mkdir(parents=True, exist_ok=True)
    return d


def home_dir():
    d = Path(os.environ.get('EBOX_HOME') or Path.home() / 'Documents' / 'eBOX')
    d.mkdir(parents=True, exist_ok=True)
    return d


# -- the key and the settings
def key_file():
    return support_dir() / 'claude-api-key'


def read_key():
    f = key_file()
    return f.read_text(encoding='utf-8').strip() if f.exists() else ''


def save_key(key):
    f = key_file()
    fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as h:
        h.write(key.strip())
    os.chmod(f, 0o600)


def forget_key():
    f = key_file()
    if f.exists():
        f.unlink()


def check_key(key):
    """The key tried on the Claude API's model list (free). Returns '' when it works, else why not (Arabic)."""
    try:
        import anthropic
        anthropic.Anthropic(api_key=key, max_retries=1, timeout=30).models.list(limit=1)
        return ''
    except Exception as e:                                          # noqa: BLE001 — every failure is said, none is fatal
        name = type(e).__name__
        if 'Authentication' in name or 'PermissionDenied' in name:
            return 'المفتاح غير صالح: لم يقبله Claude.'
        if 'Connection' in name or 'Timeout' in name:
            return 'تعذّر الاتصال بـ Claude: تحقّق من اتصال الجهاز بالإنترنت.'
        return f'تعذّر التحقق من المفتاح ({name}).'


def settings():
    f = support_dir() / 'settings.json'
    s = json.loads(f.read_text(encoding='utf-8')) if f.exists() else {}
    s.setdefault('budget_usd', DEFAULT_BUDGET_USD)
    return s


def save_settings(s):
    (support_dir() / 'settings.json').write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding='utf-8')


# -- the dossiers
def slug(s, n=40):
    s = re.sub(r'[^A-Za-z0-9؀-ۿ]+', '-', s).strip('-')
    return s[:n] or 'dossier'


def dossier_of(d):
    """What the page shows of one dossier (a folder in ~/Documents/eBOX)."""
    w = d / 'work'
    meta = json.loads((d / 'ebox.json').read_text(encoding='utf-8')) if (d / 'ebox.json').exists() else {}
    marks = {'read': 'read/pages.json', 'repeats': 'repeats.json', 'ocr': 'parts.json', 'split': 'plan.json', 'assemble': 'assembled.json',
             'checks': 'findings.json', 'decide': 'decide.json', 'fix': 'fixed.json', 'ectd': 'ectd.json', 'report': 'report.json'}
    done = [s for s in STAGES if (w / marks[s]).exists()]
    dec = json.loads((w / 'decide.json').read_text(encoding='utf-8')) if (w / 'decide.json').exists() else {}
    rep = json.loads((w / 'report.json').read_text(encoding='utf-8')) if (w / 'report.json').exists() else {}
    return {'id': d.name, 'name': meta.get('name', d.name), 'source': meta.get('source', ''), 'started': meta.get('started', ''),
            'done': done, 'finished': 'report' in done, 'claude': {'tasks': dec.get('tasks', {}), 'spent_usd': dec.get('spent_usd_total', 0),
                                                                     'skipped': dec.get('skipped')},
            'deliver': (rep.get('deliver') or {}).get('folder', '') if isinstance(rep.get('deliver'), dict) else str(rep.get('deliver') or ''),
            'report_pdf': ((rep.get('ctd') or {}).get('pdf') or '')}


def decisions_of(d, most=40):
    """Claude's latest decisions, as the log has them (tool, ok, short input)."""
    f = d / 'work' / 'decide' / 'log.jsonl'
    if not f.exists():
        return []
    out = []
    for line in f.read_text(encoding='utf-8').splitlines()[-400:]:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if 'tool' in e and e['tool'] not in ('read_pages', 'view_page', 'search_text'):
            out.append({'task': e.get('task'), 'tool': e['tool'], 'ok': e.get('ok'), 'input': e.get('input', '')[:220],
                        'error': e.get('error', '')[:300], 'time': e.get('time', '')})
    return out[-most:]


class Runner:
    """The one dossier being made ready: the program's own process, its log, its stop."""

    def __init__(self):
        self.proc = None
        self.dir = None
        self.lock = threading.Lock()

    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, source, resume=None):
        with self.lock:
            if self.running():
                raise ValueError('ملف آخر قيد الإعداد الآن.')
            src = Path(source)
            if resume:
                d = home_dir() / resume
                meta = json.loads((d / 'ebox.json').read_text(encoding='utf-8'))
                src = Path(meta['source'])
            else:
                if not src.is_dir() or not any(p.is_file() for p in src.rglob('*')):
                    raise ValueError('المجلد المختار لا يحوي ملفات.')
                today = datetime.date.today()
                d = home_dir() / f'{slug(src.name)} {today.isoformat()}'
                n = 2
                while d.exists():
                    d = home_dir() / f'{slug(src.name)} {today.isoformat()} ({n})'
                    n += 1
                (d / 'work').mkdir(parents=True)
                name = src.name
                (d / 'ebox.json').write_text(json.dumps({'name': name, 'source': str(src), 'started': datetime.datetime.now().isoformat(
                    timespec='seconds')}, ensure_ascii=False), encoding='utf-8')
                stamp = today.strftime('%d-%m-%Y')
                (d / 'work' / 'dossier.json').write_text(json.dumps({
                    'ctd_folder': f'{name} - eBOX {stamp}', 'deliver': {'name': f'{name} eCTD {stamp}', 'zip': f'{slug(name)}-eCTD-0000.zip'},
                    'ectd': {'today': today.isoformat()}}, ensure_ascii=False), encoding='utf-8')
            if not src.is_dir():
                raise ValueError('مجلد الملف الوارد لم يعد موجودًا.')
            env = dict(os.environ)
            key = read_key()
            if key:
                env['ANTHROPIC_API_KEY'] = key
            else:
                env.pop('ANTHROPIC_API_KEY', None)
            env['EBOX_CLAUDE_BUDGET_USD'] = str(settings()['budget_usd'])
            log = open(d / 'run.log', 'a', encoding='utf-8')
            self.proc = subprocess.Popen([sys.executable, '-m', 'dossier_engine.combined', 'run', str(src), str(d / 'work')],
                                         stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
            self.dir = d
            return d.name

    def stop(self):
        with self.lock:
            if self.running():
                os.killpg(self.proc.pid, signal.SIGTERM)
                try:
                    self.proc.wait(20)
                except subprocess.TimeoutExpired:
                    os.killpg(self.proc.pid, signal.SIGKILL)

    def state(self):
        if not self.dir:
            return None
        d = self.dir
        lines = (d / 'run.log').read_text(encoding='utf-8', errors='replace').splitlines() if (d / 'run.log').exists() else []
        stage = None
        for l in lines:
            m = re.search(r'— المرحلة «(\w+)»', l)
            if m:
                stage = m.group(1)
        code = self.proc.poll() if self.proc else None
        return {**dossier_of(d), 'running': self.running(), 'stage': stage, 'exit': code, 'log': lines[-14:],
                'decisions': decisions_of(d)}


class Handler(BaseHTTPRequestHandler):
    server_version = 'eBOX'

    def log_message(self, *a):
        pass

    def ok_request(self):
        app = self.server.app
        host_ok = self.headers.get('Host') == f'127.0.0.1:{self.server.server_address[1]}'
        token = self.headers.get('X-EBOX-Token') or ''
        return host_ok and secrets.compare_digest(token, app['token'])

    def send(self, code, body, kind='application/json; charset=utf-8'):
        data = body if isinstance(body, bytes) else (json.dumps(body, ensure_ascii=False) if not isinstance(body, str) else body).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        app = self.server.app
        if self.path.split('?')[0] == '/':
            if self.headers.get('Host') != f'127.0.0.1:{self.server.server_address[1]}' or f't={app["token"]}' not in self.path:
                return self.send(403, 'ممنوع', 'text/plain; charset=utf-8')
            page = (HERE / 'page.html').read_text(encoding='utf-8').replace('__TOKEN__', app['token'])
            return self.send(200, page, 'text/html; charset=utf-8')
        if self.path.startswith('/fonts/'):
            f = FONTS / Path(self.path).name
            if f.suffix == '.ttf' and f.exists():
                return self.send(200, f.read_bytes(), 'font/ttf')
            return self.send(404, {})
        if not self.ok_request():
            return self.send(403, {'error': 'forbidden'})
        if self.path == '/api/state':
            r = app['runner']
            runs = [dossier_of(d) for d in sorted(home_dir().iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
                    if d.is_dir() and (d / 'ebox.json').exists()][:30]
            return self.send(200, {'key': bool(read_key()), 'settings': settings(), 'home': str(home_dir()), 'current': r.state(),
                                   'runs': runs})
        return self.send(404, {})

    def do_POST(self):
        app = self.server.app
        if not self.ok_request():
            return self.send(403, {'error': 'forbidden'})
        n = int(self.headers.get('Content-Length') or 0)
        try:
            a = json.loads(self.rfile.read(n) or b'{}') if n else {}
        except ValueError:
            return self.send(400, {'error': 'bad json'})
        r = app['runner']
        try:
            if self.path == '/api/key':
                key = str(a.get('key', '')).strip()
                if not re.fullmatch(r'sk-ant-[A-Za-z0-9_\-]{20,}', key):
                    return self.send(200, {'ok': False, 'why': 'هذا ليس مفتاحًا لـ Claude: يبدأ المفتاح بـ sk-ant-.'})
                why = app['check_key'](key)
                if why:
                    return self.send(200, {'ok': False, 'why': why})
                save_key(key)
                return self.send(200, {'ok': True})
            if self.path == '/api/key/forget':
                forget_key()
                return self.send(200, {'ok': True})
            if self.path == '/api/settings':
                s = settings()
                b = float(a.get('budget_usd', s['budget_usd']))
                if not 1 <= b <= 500:
                    return self.send(200, {'ok': False, 'why': 'الحد بين 1 و500 دولار.'})
                s['budget_usd'] = b
                save_settings(s)
                return self.send(200, {'ok': True})
            if self.path == '/api/choose':
                return self.send(200, app['choose']())
            if self.path == '/api/start':
                return self.send(200, {'ok': True, 'id': r.start(a.get('source', ''), resume=a.get('resume'))})
            if self.path == '/api/stop':
                r.stop()
                return self.send(200, {'ok': True})
            if self.path == '/api/open':
                d = home_dir() / str(a.get('id', ''))
                if not (d.is_dir() and d.parent == home_dir()):
                    return self.send(404, {'ok': False})
                info = dossier_of(d)
                target = {'deliver': info['deliver'], 'report': info['report_pdf'], 'folder': str(d)}.get(a.get('what'))
                if not target or not Path(target).exists():
                    return self.send(200, {'ok': False, 'why': 'لم يُكتب بعد.'})
                app['open'](target)
                return self.send(200, {'ok': True})
            if self.path == '/api/quit':
                r.stop()
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return self.send(200, {'ok': True})
        except ValueError as e:
            return self.send(200, {'ok': False, 'why': str(e)})
        return self.send(404, {})


def choose_folder():
    """The Mac's own folder dialog (osascript)."""
    r = subprocess.run(['osascript', '-e', 'POSIX path of (choose folder with prompt "اختر مجلد الملف الوارد")'],
                       capture_output=True, text=True)
    path = r.stdout.strip()
    if r.returncode != 0 or not path:
        return {'ok': False}
    p = Path(path)
    files = [f for f in p.rglob('*') if f.is_file() and not f.name.startswith('.')]
    return {'ok': True, 'path': str(p), 'files': len(files), 'mb': round(sum(f.stat().st_size for f in files) / 1e6, 1)}


def serve(port=0, open_browser=True, choose=choose_folder, opener=None, check=check_key):
    httpd = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    httpd.app = {'token': secrets.token_urlsafe(24), 'runner': Runner(), 'choose': choose, 'check_key': check,
                 'open': opener or (lambda p: subprocess.run(['open', p]))}
    url = f'http://127.0.0.1:{httpd.server_address[1]}/?t={httpd.app["token"]}'
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    return httpd, url


def main(argv):
    if '--self-test' in argv:
        from .selftest import main as selftest
        return selftest()
    httpd, url = serve()
    (support_dir() / 'last-url.txt').write_text(url, encoding='utf-8')
    print(time.strftime('%H:%M:%S'), 'eBOX:', url.split('?')[0], flush=True)
    httpd.serve_forever()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
