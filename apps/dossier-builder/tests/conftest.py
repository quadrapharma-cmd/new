import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
REPO = ROOT.parents[1]
CHECKLIST = REPO / 'docs' / 'ctd' / 'checklist' / 'EDA-eCTD-Company-Checklist.xlsx'
