#!/usr/bin/env python3
"""Add or reset a user for the hosted (cloud) mode.
  python3 tools/adduser.py <workspace> <username> [--role admin|user]   (asks for the password)"""
import argparse, getpass, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'engine'))
from dossier_engine.app.auth import Auth

ap = argparse.ArgumentParser()
ap.add_argument('workspace'); ap.add_argument('username'); ap.add_argument('--role', default='user', choices=['admin', 'user'])
a = ap.parse_args()
pw = getpass.getpass('Password (10+ characters): ')
if pw != getpass.getpass('Repeat: '):
    sys.exit('Passwords do not match.')
Auth(a.workspace, True).add_user(a.username, pw, a.role)
print(f'User {a.username!r} saved ({a.role}).')
