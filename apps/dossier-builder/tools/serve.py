#!/usr/bin/env python3
"""Run the local app: python3 tools/serve.py [workspace_dir] [--port 8765]
Opens nothing on the network beyond localhost (D1 local-first)."""
import argparse, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
import uvicorn
from dossier_engine.app.api import create_app

ap = argparse.ArgumentParser()
ap.add_argument('workspace', nargs='?', default=str(pathlib.Path.home() / 'DossierBuilder'))
ap.add_argument('--port', type=int, default=8765)
a = ap.parse_args()
print(f'Workspace: {a.workspace}\nOpen http://127.0.0.1:{a.port}/')
uvicorn.run(create_app(a.workspace), host='127.0.0.1', port=a.port, log_level='warning')
