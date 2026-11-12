"""The Dossier Builder API inside the browser (Pyodide).

The same FastAPI app the desktop and cloud editions run is called here as an ASGI app, directly: no server,
no threads, no network. boot.js routes every fetch('/api/…') of the interface to `handle`, and the workspace
lives on /workspace (an IndexedDB-backed file system, synced by boot.js after each change)."""
import asyncio, json, os, sys, traceback
from urllib.parse import unquote

sys.path.insert(0, '/app/apps/dossier-builder/engine')

import anyio.to_thread


async def _inline(func, *args, **kwargs):             # Pyodide has no worker threads: «threadpool» work runs on the loop
    for k in ('limiter', 'cancellable', 'abandon_on_cancel'):
        kwargs.pop(k, None)
    return func(*args, **kwargs)


anyio.to_thread.run_sync = _inline

from dossier_engine.app.api import create_app          # noqa: E402  (after the patch: starlette binds run_sync at import)

os.environ.setdefault('DB_HOME', 'web')
APP = create_app('/workspace', auth_enabled=False)


PIECE = 8 << 20                                       # of a request's body, as a server's network hands it over


async def handle(method, path, query, headers_json, body):
    headers = json.loads(headers_json) if headers_json else {}
    page = body if hasattr(body, 'subarray') else None      # the page's own bytes stay where they are and reach the engine a piece at a time:
    if page is None:                                        # a large upload is never held whole in the engine's memory beside its copies
        body = bytes(body.to_py()) if hasattr(body, 'to_py') else bytes(body or b'')
    total, pos = (int(page.length) if page is not None else len(body)), 0
    scope = {'type': 'http', 'asgi': {'version': '3.0', 'spec_version': '2.3'}, 'http_version': '1.1', 'method': method,
             'scheme': 'http', 'path': unquote(path), 'raw_path': path.encode(), 'query_string': (query or '').encode(),   # as a server does: the path decoded (a file name with a space or in Arabic), the raw one kept
             'root_path': '', 'headers': [(k.lower().encode(), str(v).encode()) for k, v in headers.items()],
             'client': ('127.0.0.1', 0), 'server': ('127.0.0.1', 80), 'state': {}}
    sent = False
    never = asyncio.Event()

    async def receive():
        nonlocal sent, pos
        if not sent:
            a, pos = pos, min(total, pos + PIECE)
            piece = page.subarray(a, pos).to_bytes() if page is not None else body[a:pos]
            sent = pos >= total
            return {'type': 'http.request', 'body': piece, 'more_body': not sent}
        await never.wait()                               # a server keeps the connection open until the response ends

    status, resp_headers, chunks = 500, [], []

    async def send(msg):
        nonlocal status, resp_headers
        if msg['type'] == 'http.response.start':
            status, resp_headers = msg['status'], msg.get('headers', [])
        elif msg['type'] == 'http.response.body':
            chunks.append(bytes(msg.get('body', b'')))

    try:
        await APP(scope, receive, send)
    except MemoryError:                                  # a file larger than what the page can hold: said, not a crash
        status, resp_headers, chunks = 507, [(b'content-type', b'application/json')], [NO_MEMORY]
    except Exception:
        status, resp_headers = 500, [(b'content-type', b'application/json')]
        chunks = [json.dumps({'detail': {'code': 'E-INTERNAL', 'en': traceback.format_exc()[-1500:],
                                         'ar': 'حصل خطأ داخلي في المحرك.'}}).encode()]
    return _answer(status, resp_headers, b''.join(chunks))


NO_MEMORY = json.dumps({'detail': {'code': 'E-MEMORY', 'en': 'A file this large does not fit in the memory the browser gives the page. Close other tabs and try again, split the file, or use the desktop program, which takes it whole.',
                                   'ar': 'ملف بالحجم ده أكبر من الذاكرة اللي المتصفح بيديها للصفحة. اقفل تبويبات تانية وجرّب تاني، أو قسّم الملف، أو استخدم برنامج سطح المكتب — بياخده كامل.'}}).encode()


def _answer(status, resp_headers, out):
    from js import Uint8Array
    from pyodide.ffi import to_js
    u8 = Uint8Array.new(len(out))
    u8.assign(out)
    meta = json.dumps({'status': status, 'headers': [[k.decode('latin-1'), v.decode('latin-1')] for k, v in resp_headers]})
    return to_js([meta, u8])
