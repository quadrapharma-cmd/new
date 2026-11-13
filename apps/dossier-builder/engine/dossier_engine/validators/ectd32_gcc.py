"""Validator — a GCC eCTD 3.2.2 sequence read back from the disk (updates list, item 39).

The GCC Module 1 specification v1.5 publishes the DTD, the folders and the codes, not a list of validation criteria; the checks
here are what those texts and the ICH specification decide: both backbones valid against their DTDs (gc-regional 1.1 of the
specification's Appendix 6, ICH 3.2), every leaf's file present with its MD5, index-md5.txt right, names and paths within the ICH
limits, one envelope per destination with that destination's agency (App. 5), and no country section for a destination the
sequence has no envelope for. → the report shape of the other validators."""
import hashlib, re
from pathlib import Path
from lxml import etree
from ..writers.ectd32_gcc import AGENCY, DEFAULT_PROFILE, REGIONAL

XLINK = '{http://www.w3c.org/1999/xlink}href'


def _md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def validate(seq_dir, profile_root=DEFAULT_PROFILE):
    seq = Path(seq_dir)
    res = []

    def rule(rid, text, fails, sev='pass_fail'):
        res.append({'rule': rid, 'severity': sev, 'text': text, 'provenance': 'GCC-M1-1.5', 'source': 'GCC Module 1 Specification v1.5 (SFDA, 2015); ICH eCTD 3.2.2',
                    'status': 'fail' if fails else 'pass', 'failures': [str(f) for f in fails][:20]})
    parser = etree.XMLParser(load_dtd=False, no_network=True, resolve_entities=False)
    reg, idx = seq / REGIONAL, seq / 'index.xml'
    for rid, path, dtd_name in (('GCC-1', reg, 'gc-regional.dtd'), ('GCC-2', idx, 'ich-ectd-3-2.dtd')):
        if not path.is_file():
            rule(rid, f'{path.name} is there and valid against {dtd_name}', [f'{path.relative_to(seq)} missing'])
            continue
        try:
            d = etree.DTD(str(seq / 'util' / 'dtd' / dtd_name))
            ok = d.validate(etree.parse(str(path), parser))
            rule(rid, f'{path.name} is valid against {dtd_name}', [] if ok else [str(e) for e in d.error_log.filter_from_errors()])
        except (OSError, etree.Error) as e:
            rule(rid, f'{path.name} is valid against {dtd_name}', [str(e)])
    bad_md5, missing = [], []
    for xml in (reg, idx):
        if not xml.is_file():
            continue
        for lf in etree.parse(str(xml), parser).iter('leaf'):
            href = lf.get(XLINK)
            if not href or lf.get('operation') == 'delete':
                continue
            f = (xml.parent / href).resolve()
            if not f.is_file():
                missing.append(href)
            elif (lf.get('checksum') or '').lower() != _md5(f):
                bad_md5.append(href)
    rule('GCC-3', 'Every leaf\'s file is in the sequence (or the earlier one it names)', missing)
    rule('GCC-4', 'Every leaf\'s MD5 checksum is the file\'s', bad_md5)
    im = seq / 'index-md5.txt'
    rule('GCC-5', 'index-md5.txt holds the MD5 of index.xml', [] if im.is_file() and idx.is_file() and im.read_text().strip() == _md5(idx) else ['index-md5.txt wrong or missing'])
    names, longp = [], []
    for f in seq.rglob('*'):
        rel = f.relative_to(seq).as_posix()
        if rel.startswith('util/'):
            continue
        if not re.fullmatch(r'[a-z0-9][a-z0-9._-]*', f.name) or len(f.name) > 64:
            names.append(rel)
        if len(f'{seq.name}/{rel}') > 180:
            longp.append(rel)
    rule('GCC-6', 'File and folder names in lower case (a-z, 0-9, «-»), at most 64 characters (App. 2; ICH)', names)
    rule('GCC-7', 'Paths at most 180 characters from the sequence folder (ICH)', longp)
    env_bad, orphan = [], []
    if reg.is_file():
        t = etree.parse(str(reg), parser)
        envs = {}
        for e in t.iter('envelope'):
            cc, ag = e.get('country'), e.find('agency')
            envs[cc] = ag.get('code') if ag is not None else None
            if AGENCY.get(cc) != envs[cc]:
                env_bad.append(f'{cc}: agency {envs[cc]} (expected {AGENCY.get(cc)})')
        for el in t.iter('specific', 'pi-doc'):
            cc = el.get('country')
            if cc != 'common' and cc not in envs:
                orphan.append(f'{el.tag} country {cc} has no envelope')
    rule('GCC-8', 'One envelope per destination, with that destination\'s receiving agency (App. 1, App. 5)', env_bad)
    rule('GCC-9', 'No country section for a destination without an envelope in this sequence', orphan)
    n_fail = sum(1 for r in res if r['status'] == 'fail')
    return {'ok': not n_fail, 'counts': {'pass': len(res) - n_fail, 'fail': n_fail, 'warning': 0, 'not_run': 0}, 'coverage': f'{len(res)}/{len(res)}',
            'label': 'Conforms to the GCC Module 1 v1.5 DTD and structure (no published GCC validation criteria).' if not n_fail
            else 'Does not conform to the GCC Module 1 v1.5 DTD / structure.', 'results': res}
