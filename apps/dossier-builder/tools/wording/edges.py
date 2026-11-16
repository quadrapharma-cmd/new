"""The spaces at the two ends of every reworded text. A text is often one piece of a sentence the code joins to the next piece,
so the new text must begin and end with the same spaces as the old one: 25 lost theirs in the first pass of 16/11/2026 and two
words ran together («نسخة PDFمنها»). Lists every pair where the ends differ; exit code 1 if any.
   python3 edges.py <ids.json> <tm,tm…> [<ids.json> <tm,tm…> …]"""
import json, pathlib, sys

SEP = ' ⇒ '
lead = lambda s: s[:len(s) - len(s.lstrip(' '))]
trail = lambda s: s[len(s.rstrip(' ')):]
bad = 0
args = sys.argv[1:]
for ids_file, tms in zip(args[0::2], args[1::2]):
    ids = json.loads(pathlib.Path(ids_file).read_text(encoding='utf-8'))
    for tm in tms.split(','):
        for line in pathlib.Path(tm).read_text(encoding='utf-8').split('\n'):
            if not line.strip() or line.startswith('#') or SEP not in line:
                continue
            i = line.index(SEP)
            k, new = line[:i].strip(), line[i + len(SEP):]
            old = ids.get(k.split('@@')[0])
            if old is not None and (lead(old) != lead(new) or trail(old) != trail(new)):
                bad += 1
                print(f'{tm} {k}\n   old: {old!r}\n   new: {new!r}')
print(bad, 'pair(s) whose ends differ')
sys.exit(1 if bad else 0)
