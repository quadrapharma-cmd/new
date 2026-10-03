"""Cross-reference parsing of the journal's free text: "افتراض N" (assumption) and "بند N" (open item).

Pattern notes (all verified on the structure of the real text, none of it is copied here):
  * assumption:  افتراض 14 / افتراض رقم 14
  * open item:   بند 64 / بند مفتوح 48 / (بند 58 / قيد الاستفسار 76 / استفسار 60
  * NOT a cross reference: a contract clause cited with the definite article or as N-M ("البند 2-7", "بند 4-5"),
    and counts of items ("41 بنداً").
"""
import re

from common import to_western

AR = 'ء-ي'
_ASSUMPTION = re.compile(rf'(?<![{AR}])افتراض(?:\s+رقم)?\s*(\d{{1,3}})(?!\d)(?!\s*[-–]\s*\d)')
_ITEM = re.compile(rf'(?<![{AR}])بند(?:\s+مفتوح)?\s*(\d{{1,3}})(?!\d)(?!\s*[-–]\s*\d)')
_INQUIRY = re.compile(rf'(?<![{AR}])(?:قيد\s+)?(?:ال)?استفسار\s*(\d{{1,3}})(?!\d)(?!\s*[-–]\s*\d)')
INQUIRY_TAG = 'استفسار'   # covers: قيد الاستفسار / استفسار N / للاستفسار


def parse_links(*texts):
    """-> (assumption numbers, open-item numbers) found in the given texts, each sorted and unique."""
    a, o = set(), set()
    for t in texts:
        if not t:
            continue
        t = to_western(t)
        a.update(int(m.group(1)) for m in _ASSUMPTION.finditer(t))
        o.update(int(m.group(1)) for m in _ITEM.finditer(t))
        o.update(int(m.group(1)) for m in _INQUIRY.finditer(t))
    return sorted(a), sorted(o)


def has_inquiry_tag(*texts):
    return any(t and INQUIRY_TAG in t for t in texts)
