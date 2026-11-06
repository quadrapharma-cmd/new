#!/usr/bin/env python3
"""Print the requirements board for a profile.

  python3 tools/resolve.py examples/examplol.yaml [--lang ar] [--all] [--json]
"""
import argparse, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'engine'))
import yaml
from dossier_engine import packs
from dossier_engine.profile import Profile, ProfileError
from dossier_engine.resolver import resolve, summary

ap = argparse.ArgumentParser()
ap.add_argument('profile')
ap.add_argument('--pack', default='eda.ctd.nta065.v5')
ap.add_argument('--lang', default='en', choices=['en', 'ar'])
ap.add_argument('--all', action='store_true', help='also list NR / NA with the reason')
ap.add_argument('--json', action='store_true')
a = ap.parse_args()

prof = Profile.from_dict(yaml.safe_load(open(a.profile, encoding='utf-8')))
try:
    slots = resolve(prof, packs.load(a.pack))
except ProfileError as e:
    for p in e.problems:
        print(f"✖ {p['code']}: {p[a.lang]}")
    sys.exit(2)
if a.json:
    print(json.dumps([s.to_dict() for s in slots], ensure_ascii=False, indent=1))
    sys.exit(0)
col, assumed = prof.column()
print(f"Pack {a.pack} · column {col}{' (assumed)' if assumed else ''} · {summary(slots)}")
for s in slots:
    if not s.active and not a.all:
        continue
    item = f" [{s.item['manufacturer']} · {s.item['option']}]" if s.item else ''
    fl = f" ⚑{','.join(s.flags)}" if s.flags else ''
    why = f"  — {s.reasons[-1][a.lang] if a.lang in s.reasons[-1] else s.reasons[-1]['en']}" if not s.active or 'ASSUMPTION' in s.flags else ''
    print(f"{s.level:>2}  {s.ctd:<12} {s.req_id:<7} {s.title[a.lang]}{item}  ({s.doc_class}){fl}{why}")
