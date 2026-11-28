"""python3 -m dossier_engine.combined <stage> <work folder> [options]

  run <source> <work>      every stage, in order (a stage already done is not done again: delete its output to redo it)
  read <source> <work>     1. what was received, page by page
  repeats <work>           2. the pages received twice
  ocr <work>               3. the kept pages made searchable
  split <work>             4. the documents: proposal + the dossier's decisions → plan.json
  assemble <work>          5. the CTD folder, every page checked against its source
  checks <work>            6. the findings
  decide <work>            7. Claude makes the decisions the rules cannot (needs ANTHROPIC_API_KEY; options: --again,
                              --budget <US dollars>, --only <task>); a decisions file made by a person is left as it is
  fix <work>               8. the corrections (in the PDFs, the product information)
  ectd <work>              9. the eCTD 3.2.2 sequence, the same as eCTD 4.0 and as ctd.zip (CTD One Submission), each validated
  report <work>           10. the report (Arabic, Word and PDF)
"""
import sys
from pathlib import Path

from .common import Work, say


def main(argv):
    if len(argv) < 2 or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    stage = argv[0]
    opts = {}
    rest = []
    it = iter(argv[1:])
    for a in it:
        if a == '--again':
            opts['again'] = True
        elif a == '--budget':
            opts['budget_usd'] = float(next(it))
        elif a == '--only':
            opts['only'] = [next(it)]
        else:
            rest.append(a)
    if stage in ('run', 'read'):
        src, work = Path(rest[0]), Work(rest[1])
    else:
        src, work = None, Work(rest[0])
    stages = ['read', 'repeats', 'ocr', 'split', 'assemble', 'checks', 'decide', 'fix', 'ectd', 'report']
    todo = stages if stage == 'run' else [stage]
    for s in todo:
        if stage == 'run' and done(work, s):
            say(f'المرحلة «{s}» منجزة من قبل.')
            continue
        say(f'— المرحلة «{s}»')
        if s == 'read':
            from . import read
            if src is None:
                src = Path(work.load('read/source.json', {}).get('source', ''))
            work.save('read/source.json', {'source': str(src.resolve())})
            read.run(src, work)
        elif s == 'repeats':
            from . import repeats
            repeats.run(work)
        elif s == 'ocr':
            from . import ocr
            ocr.run(work)
        elif s == 'split':
            from . import split
            split.run(work)
        elif s == 'assemble':
            from . import assemble
            assemble.run(work)
        elif s == 'checks':
            from . import checks
            checks.run(work)
        elif s == 'decide':
            from . import decide
            decide.run(work, **opts)
        elif s == 'fix':
            from . import fix
            fix.run(work)
        elif s == 'ectd':
            from . import ectd
            ectd.run(work)
            from . import ctdzip, ectd40                     # the other two outputs, from the same documents (9b, 9c)
            import traceback
            w = work
            failed = {}
            for name, step in (('ectd40', ectd40.run), ('ctdzip', ctdzip.run)):
                stale = w.root / f'{name}.json'
                if stale.exists():
                    stale.unlink()
                try:
                    step(work)
                except Exception as ex:                      # the 3.2.2 sequence stands: the failure is said, kept and shown, never silent
                    traceback.print_exc()
                    failed[name] = f'{type(ex).__name__}: {ex}'
                    say(f'تعذّرت صيغة {"eCTD 4.0" if name == "ectd40" else "ctd.zip"}: {failed[name]}')
            w.save('outputs-failed.json', failed)
            from . import ebox                               # 11: eBOX's full program, for the country the dossier names (Egypt by default)
            try:
                ebox.run(work)
                from . import assess                         # 12: the assessor's review, and the missing items by party with their letters
                assess.run(work)
            except Exception as ex:                          # Egypt's three outputs stand whatever happens here: said, not fatal
                say(f'تعذّر تسليم الملف لبرنامج eBOX الكامل أو مراجعته: {ex}')
        elif s == 'report':
            from . import report
            report.run(work)
    return 0


def done(work, stage):
    marks = {'read': 'read/pages.json', 'repeats': 'repeats.json', 'ocr': 'parts.json', 'split': 'plan.json',
             'assemble': 'assembled.json', 'checks': 'findings.json', 'decide': 'decide.json', 'fix': 'fixed.json', 'ectd': 'ectd.json', 'report': 'report.json'}
    return (work.root / marks[stage]).exists()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
