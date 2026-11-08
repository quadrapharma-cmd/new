"""Desktop launcher (macOS / Windows builds).

Runs the app on this computer only (127.0.0.1), keeps data in Documents/DossierBuilder, opens the browser,
and shows a small window: «Open» / «Stop». The bundle keeps the repository layout next to this file
(apps/dossier-builder/{engine,rulepacks,ui} + docs/ctd/...), so every path the engine computes still works.

    launcher.py            normal start
    launcher.py --smoke    start, call the API, create and read a product, exit 0/1 (used by CI on each OS)
"""
import os, socket, sys, threading, time, urllib.request, json, webbrowser
from pathlib import Path

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[3]))   # bundle root or repo root
APP = BASE / 'apps' / 'dossier-builder'
sys.path.insert(0, str(APP / 'engine'))
os.environ.setdefault('DB_HOME', 'suite')

TITLE = 'Dossier Builder — منشئ الملفات'


def workspace():
    home = Path.home()
    docs = home / 'Documents'
    ws = (docs if docs.exists() else home) / 'DossierBuilder'
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def free_port(start=8765):
    for p in range(start, start + 50):
        with socket.socket() as s:
            try:
                s.bind(('127.0.0.1', p))
                return p
            except OSError:
                continue
    raise RuntimeError('no free port')


def start_server(ws, port):
    import uvicorn
    from dossier_engine.app.api import create_app
    app = create_app(ws, auth_enabled=None)           # off until the owner turns sign-in on from the Users screen (auth.json in the workspace)
    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, log_level='warning'))
    threading.Thread(target=server.run, daemon=True).start()
    url = f'http://127.0.0.1:{port}'
    for _ in range(150):
        try:
            urllib.request.urlopen(url + '/api/health', timeout=1)
            return server, url
        except Exception:
            time.sleep(0.2)
    raise RuntimeError('the app did not start')


def smoke():
    import tempfile
    ws = Path(tempfile.mkdtemp())
    server, url = start_server(ws, free_port(18765))

    def call(method, path, body=None):
        req = urllib.request.Request(url + path, method=method, data=json.dumps(body).encode() if body else None,
                                     headers={'Content-Type': 'application/json', 'X-DB': '1'})
        return json.loads(urllib.request.urlopen(req, timeout=20).read())

    assert call('GET', '/api/suite/types')['types'], 'rules not loaded'
    p = call('POST', '/api/suite/products', {'name': 'Smoke', 'reg_date': '2022-11-10'})
    got = call('GET', f"/api/suite/products/{p['id']}")
    assert got['renewal']['due'] == '2032-11-10', got['renewal']
    assert len(call('GET', '/api/variations?q=')) > 0
    html = urllib.request.urlopen(url + '/suite/', timeout=10).read().decode('utf-8')
    assert 'ملف المنتجات' in html
    d = call('POST', '/api/dossiers', {'name': 'Smoke', 'product': {'name': 'X', 'dosageform': 'tablet', 'manufacturer': 'M'},
                                       'profile': {'dossier_kind': 'generic', 'origin': 'local', 'licence': 'own', 'activity': 'new',
                                                   'apis': [{'name': 'A', 'manufacturer': 'B', 'option': 'CEP'}]}})
    assert call('GET', f"/api/dossiers/{d['id']}/board")['counts'], 'resolver failed'
    for sub, f in (('tess', 'tesseract.min.js'), ('tess', 'worker.boot.js'), ('tess', 'ara.traineddata.gz.b64.txt'), ('pdfjs', 'pdf.min.mjs')):
        assert urllib.request.urlopen(f'{url}/assets/{sub}/{f}', timeout=20).status == 200, \
            f'browser OCR asset missing: {sub}/{f} — run web/vendor.sh ocr before the build'
    assert call('GET', '/api/capabilities')['ocr_browser'], 'capabilities must say the browser OCR engine is served'
    from dossier_engine.generate.docx_kit import find_soffice
    print('SMOKE OK', sys.platform, 'workspace', ws, 'libreoffice', find_soffice() or 'not installed')
    server.should_exit = True
    return 0


def gui(url, ws):
    try:
        import tkinter as tk
    except Exception:
        print(f'{TITLE}\nRunning at {url}\nData: {ws}\nClose this window to stop.')
        while True:
            time.sleep(3600)
    root = tk.Tk()
    root.title(TITLE)
    root.geometry('460x210')
    tk.Label(root, text='البرنامج شغال على الجهاز ده', font=('Arial', 15, 'bold')).pack(pady=(18, 4))
    tk.Label(root, text=url, fg='#0E7C86').pack()
    tk.Label(root, text=f'الملفات محفوظة في: {ws}', wraplength=430, fg='#5B6B7C').pack(pady=4)
    row = tk.Frame(root)
    row.pack(pady=12)
    tk.Button(row, text='افتح البرنامج  Open', width=18, command=lambda: webbrowser.open(url)).pack(side='left', padx=6)
    tk.Button(row, text='إيقاف  Stop', width=12, command=root.destroy).pack(side='left', padx=6)
    tk.Label(root, text='قفل النافذة دي = إيقاف البرنامج', fg='#8A97A6').pack()
    root.after(400, lambda: webbrowser.open(url))
    root.mainloop()


def main():
    if '--smoke' in sys.argv:
        sys.exit(smoke())
    ws = workspace()
    server, url = start_server(ws, free_port())
    gui(url, ws)
    server.should_exit = True


if __name__ == '__main__':
    main()
