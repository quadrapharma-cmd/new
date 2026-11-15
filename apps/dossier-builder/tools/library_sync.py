"""Bring the library's reviewed citations into the program's EDA review questions (rulepacks/eda.review.v1).

The library («المكتبة», apps/dossier-builder-v2/knowledge) took these 226 questions over and checked every citation against its
source, word for word: GL.CADC.002 version 3 is in force (its sections moved: §6.5.x became §5.6.x), several sections and quotes
were corrected, and a few questions now rest on EDA's own guideline instead of a WHO checklist. This writes each question's
`source` from the library's first citation (the other citations, when there are several, are named in its section), changing only
the `source:` line of each question, so the rest of the files stay as they are.

    python3 tools/library_sync.py           # write
    python3 tools/library_sync.py --check   # say what differs, change nothing (the tests run this)

The label of a document stays the program's own when it names the same document (one of the library's aliases for it); a
different document is named from the library: code, version and year."""
import json, pathlib, re, sys
import yaml

HERE = pathlib.Path(__file__).resolve().parents[1]
REVIEW = HERE / 'rulepacks' / 'eda.review.v1'
LIBRARY = HERE.parent / 'dossier-builder-v2' / 'knowledge'
SOURCE_LINE = re.compile(r'^(\s*)source:\s*\{.*\}\s*$')
ID_LINE = re.compile(r'^- id:\s*(\S+)\s*$')


def library():
    sources = {s['id']: s for s in yaml.safe_load((LIBRARY / 'sources.yaml').read_text(encoding='utf-8'))}
    rules = {r['id'].split('/', 1)[1]: r for r in yaml.safe_load((LIBRARY / 'review' / 'eg-eda.yaml').read_text(encoding='utf-8'))}
    return sources, rules


def same_document(src, old):
    """Does the program's own label name this document (this version)?"""
    if not old:
        return False
    o = old.lower()
    names = [a.lower() for a in (src.get('aliases') or [])] + [str(src.get('code') or '').lower()]
    if o in names:
        return True
    code, ver = str(src.get('code') or '').lower(), str(src.get('version') or '')
    if not code or not o.startswith(code):
        return False
    m = re.search(r'\bv0*(\d+)\b', o)                     # a version in the label must be this one (v02 is not v3)
    return not m or not re.fullmatch(r'0*\d+', ver) or int(m.group(1)) == int(ver)


def label(src, old=None):
    """The program's own label when it names this document; else the library's name for it: code, version and year."""
    if same_document(src, old):
        return old
    alias = next((a for a in src.get('aliases') or [] if re.search(r'\bv\d+(\.\d+)?/\d{4}$', a)), None)
    if alias:
        return alias
    code, ver, year = src.get('code'), str(src.get('version') or ''), str(src.get('issued') or '')[:4]
    if code and re.fullmatch(r'\d+(\.\d+)?', ver):
        return f'{code} v{ver}' + (f'/{year}' if year else '')
    return (src.get('title') or {}).get('en') or code or src['id']


def wanted(rule, old, sources):
    """The `source` a question should carry: the library's first citation; the others named in its section (another place in
    the same document first, then the other documents)."""
    cites = rule.get('cite') or []
    if not cites:
        return old
    first = cites[0]
    out = {'code': label(sources[first['src']], (old or {}).get('code'))}
    places = [first.get('at') or ''] + [c['at'] for c in cites[1:] if c['src'] == first['src'] and c.get('at')]
    section = '; '.join(p for p in places if p)
    more = [f"{label(sources[c['src']])}{' ' + c['at'] if c.get('at') else ''}" for c in cites[1:] if c['src'] != first['src']]   # the library's name: the same every run
    if more:
        section = (section + '; ' if section else '') + 'also ' + '; '.join(more)
    if section:
        out['section'] = section
    if first.get('quote'):
        out['quote'] = first['quote']
    return out


def line(indent, src):
    return indent + 'source: {' + ', '.join(f'{k}: {json.dumps(v, ensure_ascii=False)}' for k, v in src.items()) + '}'


def sync(write=True):
    sources, rules = library()
    changed, missing = [], []
    for f in sorted(REVIEW.glob('*.yaml')):
        if f.name == 'pack.yaml':
            continue
        old = {r['id']: r for r in yaml.safe_load(f.read_text(encoding='utf-8')) or []}
        lines, cur, out = f.read_text(encoding='utf-8').split('\n'), None, []
        for ln in lines:
            m = ID_LINE.match(ln)
            if m:
                cur = m.group(1)
            s = SOURCE_LINE.match(ln)
            if s and cur:
                if cur not in rules:
                    missing.append(cur)
                else:
                    new = wanted(rules[cur], old[cur].get('source'), sources)
                    if new != old[cur].get('source'):
                        changed.append((f.name, cur, old[cur].get('source'), new))
                        ln = line(s.group(1), new)
            out.append(ln)
        if write:
            text = '\n'.join(out)
            if text != f.read_text(encoding='utf-8'):
                f.write_text(text, encoding='utf-8')
                assert {r['id']: r.get('source') for r in yaml.safe_load(text)} is not None      # still YAML
    return changed, missing


if __name__ == '__main__':
    check = '--check' in sys.argv
    changed, missing = sync(write=not check)
    for name, rid, old, new in changed:
        print(f'{name} {rid}: {(old or {}).get("code")} {(old or {}).get("section", "")} → {new.get("code")} {new.get("section", "")}')
    print(f'{len(changed)} question(s) {"differ" if check else "brought to the library"}; not in the library: {missing or "none"}')
    sys.exit(1 if check and changed else 0)
