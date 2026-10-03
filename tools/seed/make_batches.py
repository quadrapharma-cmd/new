#!/usr/bin/env python3
"""Seed files -> ArtifactData batch payloads.

    python3 tools/seed/make_batches.py [--out DIR] [--seed DIR] [--max 50]

Writes <out>/batches/batch_NNN.json = {"writes": [{"op": "set", "collection": "...", "doc_id": "...", "file_path": "..."}]}
with at most --max writes per batch, ordered: meta, masters, entries, registers, import log. Plus batches/index.json with
the batch and document counts. The lead pastes each batch into one ArtifactData batch call; `file_path` points at the seed
JSON, so no data travels through this script's output.
"""
import argparse
import glob
import json
import os
import re
import sys

sys.dont_write_bytecode = True      # keep the repository free of __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SeedError, assert_outside_repo, dumps, eprint, private_dir  # noqa: E402

ORDER = ['meta', 'accounts', 'costCenters', 'sectors', 'parties', 'documents', 'fiscalYears', 'openItems', 'assumptions',
         'assets', 'templates', 'entries', 'registers', 'importRuns']
META_ORDER = {'config': 0, 'counters': 1, 'groups': 2}
DB_DOC_LIMIT = 5000


def natural(doc_id):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', doc_id)]


def collect(seed_dir):
    found = {}
    for path in glob.glob(os.path.join(seed_dir, '*', '*.json')):
        coll = os.path.basename(os.path.dirname(path))
        found.setdefault(coll, []).append((os.path.splitext(os.path.basename(path))[0], os.path.abspath(path)))
    unknown = sorted(set(found) - set(ORDER))
    if unknown:
        raise SeedError('unexpected collections in the seed directory: ' + ', '.join(unknown))
    ordered = []
    for coll in ORDER:
        docs = found.get(coll, [])
        key = (lambda d: META_ORDER.get(d[0], 99)) if coll == 'meta' else (lambda d: natural(d[0]))
        for doc_id, path in sorted(docs, key=key):
            ordered.append({'op': 'set', 'collection': coll, 'doc_id': doc_id, 'file_path': path})
    return ordered


def build_batches(writes, size):
    return [writes[i:i + size] for i in range(0, len(writes), size)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    ap.add_argument('--seed')
    ap.add_argument('--max', type=int, default=50)
    args = ap.parse_args(argv)
    out = args.out or private_dir()
    seed = args.seed or os.path.join(out, 'seed')
    try:
        assert_outside_repo(out)
        if not os.path.isdir(seed):
            raise SeedError('seed directory not found: run make_seed.py first')
        writes = collect(seed)
        if not writes:
            raise SeedError('seed directory is empty')
        if len(writes) > DB_DOC_LIMIT:
            raise SeedError('more documents than the artifact database allows')
        bdir = os.path.join(out, 'batches')
        os.makedirs(bdir, exist_ok=True)
        for old in glob.glob(os.path.join(bdir, 'batch_*.json')) + glob.glob(os.path.join(bdir, 'index.json')):
            os.remove(old)
        batches = build_batches(writes, max(1, args.max))
        summary = []
        for i, b in enumerate(batches, start=1):
            name = f'batch_{i:03d}.json'
            with open(os.path.join(bdir, name), 'w', encoding='utf-8') as fh:
                fh.write(dumps({'writes': b}) + '\n')
            per = {}
            for w in b:
                per[w['collection']] = per.get(w['collection'], 0) + 1
            summary.append({'file': name, 'writes': len(b), 'collections': per})
        index = {'batchCount': len(batches), 'docCount': len(writes), 'maxPerBatch': args.max,
                 'order': ORDER, 'batches': summary,
                 'perCollection': {c: sum(1 for w in writes if w['collection'] == c) for c in ORDER
                                   if any(w['collection'] == c for w in writes)}}
        with open(os.path.join(bdir, 'index.json'), 'w', encoding='utf-8') as fh:
            fh.write(dumps(index) + '\n')
    except SeedError as e:
        eprint(f'make_batches: {e}')
        return 2
    print(f'make_batches: {len(batches)} batches, {len(writes)} docs (max {args.max} per batch)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
