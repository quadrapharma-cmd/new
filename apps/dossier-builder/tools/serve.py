#!/usr/bin/env python3
"""Run the app.
Local (default): python3 tools/serve.py [workspace]  → http://127.0.0.1:8765/ , no login, files stay on this computer.
Cloud:  DB_MODE=cloud DB_WORKSPACE=/data PORT=8765 python3 tools/serve.py  → binds 0.0.0.0, login required
        (first admin from DB_ADMIN_USER / DB_ADMIN_PASSWORD; put it behind HTTPS and set DB_COOKIE_SECURE=1)."""
import argparse, os, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
import uvicorn
from dossier_engine.app.api import create_app

cloud = os.environ.get('DB_MODE') == 'cloud'
ap = argparse.ArgumentParser()
ap.add_argument('workspace', nargs='?', default=os.environ.get('DB_WORKSPACE', str(pathlib.Path.home() / 'DossierBuilder')))
ap.add_argument('--port', type=int, default=int(os.environ.get('PORT', 8765)))
ap.add_argument('--host', default=os.environ.get('HOST', '0.0.0.0' if cloud else '127.0.0.1'))
a = ap.parse_args()
app = create_app(a.workspace)
if cloud and not app.state.auth.users():
    sys.exit('Cloud mode needs a user: set DB_ADMIN_USER and DB_ADMIN_PASSWORD (10+ characters) for the first start, '
             'or run tools/adduser.py on the workspace.')
print(f"Workspace: {a.workspace}\nMode: {'cloud (login required)' if cloud else 'local'}\nOpen http://{a.host}:{a.port}/")
uvicorn.run(app, host=a.host, port=a.port, log_level='warning', proxy_headers=True, forwarded_allow_ips='*')
