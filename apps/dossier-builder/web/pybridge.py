"""The Dossier Builder API inside the browser (Pyodide).

The same FastAPI app the desktop and cloud editions run is called here as an ASGI app, directly: no server,
no threads, no network. boot.js routes every fetch('/api/…') of the interface to `handle`, and the workspace
lives on /workspace (an IndexedDB-backed file system, synced by boot.js after each change)."""
import asyncio, json, os, sys, traceback

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


async def handle(method, path, query, headers_json, body):
    headers = json.loads(headers_json) if headers_json else {}
    if hasattr(body, 'to_bytes'):
        body = body.to_bytes()
    elif hasattr(body, 'to_py'):
        body = bytes(body.to_py())
    body = bytes(body or b'')
    scope = {'type': 'http', 'asgi': {'version': '3.0', 'spec_version': '2.3'}, 'http_version': '1.1', 'method': method,
             'scheme': 'http', 'path': path, 'raw_path': path.encode(), 'query_string': (query or '').encode(),
             'root_path': '', 'headers': [(k.lower().encode(), str(v).encode()) for k, v in headers.items()],
             'client': ('127.0.0.1', 0), 'server': ('127.0.0.1', 80), 'state': {}}
    sent = False
    never = asyncio.Event()

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {'type': 'http.request', 'body': body, 'more_body': False}
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
    except Exception:
        status, resp_headers = 500, [(b'content-type', b'application/json')]
        chunks = [json.dumps({'detail': {'code': 'E-INTERNAL', 'en': traceback.format_exc()[-1500:],
                                         'ar': 'حصل خطأ داخلي في المحرك.'}}).encode()]
    out = b''.join(chunks)
    from js import Uint8Array
    from pyodide.ffi import to_js
    u8 = Uint8Array.new(len(out))
    u8.assign(out)
    meta = json.dumps({'status': status, 'headers': [[k.decode('latin-1'), v.decode('latin-1')] for k, v in resp_headers]})
    return to_js([meta, u8])
