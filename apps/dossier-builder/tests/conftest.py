import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
REPO = ROOT.parents[1]
CHECKLIST = REPO / 'docs' / 'ctd' / 'checklist' / 'EDA-eCTD-Company-Checklist.xlsx'


import pytest


@pytest.fixture(autouse=True)
def no_reading_kept_from_another_test():
    """The reader keeps what it read by the file's SHA-256 (extract.read_text): a test must not be answered from another test's
    reading of the same fixture, nor write into a workspace a finished test left behind."""
    from dossier_engine import extract
    extract._READ.clear(); extract._KEPT.clear(); extract.READ_DIR = None
    yield
    extract._READ.clear(); extract._KEPT.clear(); extract.READ_DIR = None
