"""The eCTD check for any country (validators/global_ectd.py): the ICH layer every eCTD must pass, then the authority's own criteria
where the program has them (the EU, Egypt, the GCC). Made-up sequences from the program's own writers; each defect is put in on
purpose and must fail its ICH rule."""
import hashlib
import re
import shutil
import pytest
from fixtures_pdf import make_pdf
from dossier_engine.validators import global_ectd as G
from dossier_engine.writers import ectd32 as eg, ectd32_eu as eu, ectd32_gcc as gc
from dossier_engine.writers.ectd32 import Doc, Product
from test_ectd32_eu import envelope, docs, PROD          # noqa: F401  (the EU fixture)
from test_ectd32_gcc import env as gcc_env
from test_validator_ectd32 import ENV as EG_ENV


def st(layer):
    return {r['rule']: r['status'] for r in layer['results']}


def ich(res):
    return res['layers']['1 · ICH — every country']


def own(res):
    return next(v for k, v in res['layers'].items() if k.startswith('2 · '))


@pytest.fixture()
def eu_seq(tmp_path, docs):
    e = envelope()
    eu.write(tmp_path / 'out', e, PROD, eu.resolve(docs, e))
    return tmp_path / 'out' / '0000'


def copy(seq, tmp_path, name='0000'):
    dest = tmp_path / 'copy' / name
    shutil.copytree(seq, dest)
    return dest


def md5(p):
    return hashlib.md5(p.read_bytes()).hexdigest()


def rewrite_index(seq, fn):
    """index.xml changed on purpose, with its index-md5.txt kept true (so only the rule under test fails)."""
    idx = seq / 'index.xml'
    idx.write_text(fn(idx.read_text(encoding='utf-8')), encoding='utf-8')
    (seq / 'index-md5.txt').write_text(md5(idx), encoding='utf-8')


def test_an_eu_sequence_passes_ich_and_the_eu_criteria(eu_seq):
    res = G.validate(eu_seq)
    assert res['region'] == 'eu' and res['country'] == 'EU' and res['own_criteria_run'] and 'EMA' in res['authority']
    s = st(ich(res))
    assert ich(res)['ok'], [r for r in ich(res)['results'] if r['status'] == 'fail']
    assert len(ich(res)['results']) == len(G.RULES) == 23
    for rule in ('ICH-Q36-01', 'ICH-Q36-02', 'ICH-Q36-03', 'ICH-Q36-04', 'ICH-Q36-05', 'ICH-Q36-07', 'ICH-Q36-11', 'ICH-Q36-12',
                 'ICH-Q36-13', 'ICH-Q36-15', 'ICH-Q36-16', 'ICH-Q36-17', 'ICH-Q36-18', 'ICH-Q36-19', 'ICH-Q36-20', 'ICH-Q36-21'):
        assert s[rule] == 'pass', (rule, next(r for r in ich(res)['results'] if r['rule'] == rule))
    assert own(res)['ok'] and own(res)['coverage'] == '108/111'            # the EU's own 111 criteria, as tests/test_ectd32_eu.py
    assert res['ok']
    html = G.html(res, 'Dermacure — any country')
    assert 'ICH-Q36-11' in html and 'EU-14.2' in html and 'QA 36 item 11' in html and 'Not an authority' in html


def test_a_gulf_and_an_egyptian_sequence_get_their_own_criteria(tmp_path):
    f = str(make_pdf(tmp_path / 'a.pdf', 'x'))
    gdocs = [Doc('1.0', f, 'Cover letter', country='sa'), Doc('1.2', f, 'Application form', country='sa'), Doc('1.3.1', f, 'SPC', lang='en'),
             Doc('3.2.P.1', f, 'Description and composition')]
    gc.write(tmp_path / 'gcc', gcc_env(countries=['sa']), Product('Examplol 500 mg', 'tablet', 'Example Pharm Co.'), gdocs)
    res = G.validate(tmp_path / 'gcc' / '0000')
    assert res['region'] == 'gc' and res['country'] == 'GCC' and res['own_criteria_run']
    assert ich(res)['ok'], [r for r in ich(res)['results'] if r['status'] == 'fail']
    assert any(r['rule'].startswith('GCC-') for r in own(res)['results'])
    edocs = [Doc('1.0', f, 'Cover letter'), Doc('1.0', f, 'Tracking table', name='tracking'), Doc('1.2.1', f, 'Application form'),
             Doc('1.3.1', f, 'SmPC', pi_type='spc', lang='en'), Doc('3.2.P.1', f, 'Description and composition')]
    eg.write(tmp_path / 'eg', EG_ENV, Product('Examplol 500 mg', 'tablet', 'Example Pharma'), edocs)
    res = G.validate(tmp_path / 'eg' / '0000')
    assert res['region'] == 'eg' and res['country'] == 'EG' and res['own_criteria_run'] and res['evidence'] == 'official-draft'
    assert ich(res)['ok'], [r for r in ich(res)['results'] if r['status'] == 'fail']
    assert any(r['rule'].startswith('EG-') for r in own(res)['results'])
    assert 'EDA' in G.note(res)[0] or 'EDA' in res['authority']


def as_region(seq, tmp_path, code):
    """The EU sequence moved to region «code» (m1/<code>/<code>-regional.xml), its index.xml and index-md5.txt kept true: a region
    whose own criteria the program does not have."""
    s = copy(seq, tmp_path)
    (s / 'm1' / 'eu').rename(s / 'm1' / code)
    (s / 'm1' / code / 'eu-regional.xml').rename(s / 'm1' / code / f'{code}-regional.xml')
    reg = s / 'm1' / code / f'{code}-regional.xml'
    rewrite_index(s, lambda t: re.sub(r'(xlink:href="m1/)eu/eu-regional\.xml"[^>]*?checksum="[0-9a-f]+"',
                                      lambda m: m.group(0).replace('eu/eu-regional', f'{code}/{code}-regional')
                                      .replace(m.group(0)[m.group(0).rfind('checksum="') + 10:-1], md5(reg)), t)
                  .replace('xlink:href="m1/eu/eu-regional.xml"', f'xlink:href="m1/{code}/{code}-regional.xml"'))
    return s


def test_a_region_the_program_has_no_criteria_for_gets_the_ich_layer_and_says_so(eu_seq, tmp_path):
    s = as_region(eu_seq, tmp_path, 'ch')
    res = G.validate(s)
    assert res['region'] == 'ch' and res['country'] == 'CH' and res['authority'] == 'Swissmedic' and not res['own_criteria_run']
    assert list(res['layers']) == ['1 · ICH — every country']
    assert ich(res)['ok'], [r for r in ich(res)['results'] if r['status'] == 'fail']
    assert st(ich(res))['ICH-Q36-07'] == 'pass' and st(ich(res))['ICH-Q36-19'] == 'pass'       # its own DTD, its own sequence number
    en, ar = G.note(res)
    assert 'not in the program yet' in en and 'Swissmedic' in en and 'ليست في البرنامج بعد' in ar
    s2 = as_region(eu_seq, tmp_path / 'b', 'zz')
    res = G.validate(s2)
    assert res['region'] == 'zz' and res['country'] == 'ZZ' and 'zz' in res['authority'] and res['criteria'] == 'unknown'
    assert ich(res)['ok']


def test_japan_need_not_match_the_sequence_number(eu_seq, tmp_path):
    s = as_region(eu_seq, tmp_path, 'jp')
    s2 = s.parent / '0007'
    s.rename(s2)
    res = G.validate(s2)
    r19 = next(r for r in ich(res)['results'] if r['rule'] == 'ICH-Q36-19')
    assert r19['status'] == 'not_run' and 'Japan' in r19['reason']
    res = G.validate(as_region(eu_seq, tmp_path / 'b', 'ch').rename(tmp_path / 'b' / 'copy' / '0007'))
    assert st(ich(res))['ICH-Q36-19'] == 'fail'


DEFECTS = [
    ('ICH-Q36-01', lambda s: (s / 'index-md5.txt').unlink()),
    ('ICH-Q36-02', lambda s: open(s / 'util/dtd/ich-ectd-3-2.dtd', 'a').write('\n<!-- edited -->\n')),
    ('ICH-Q36-03', lambda s: rewrite_index(s, lambda t: t.replace('<m3-quality>', '<m3-quality><nothing/>', 1))),
    ('ICH-Q36-04', lambda s: rewrite_index(s, lambda t: t.replace('operation="new"', 'operation="replace"', 1))),
    ('ICH-Q36-05', lambda s: (s / 'm1/eu/eu-regional.xml').rename(s / 'm1/eu/regional.xml')),
    ('ICH-Q36-07', lambda s: (s / 'util/dtd/eu-regional.dtd').unlink()),
    ('ICH-Q36-11', lambda s: open(next((s / 'm3').rglob('*.pdf')), 'ab').write(b'\n%changed')),
    ('ICH-Q36-11', lambda s: (s / 'index-md5.txt').write_text('0' * 32)),
    ('ICH-Q36-12', lambda s: next((s / 'm3').rglob('*.pdf')).unlink()),
    ('ICH-Q36-13', lambda s: shutil.copyfile(next((s / 'm3').rglob('*.pdf')), next((s / 'm3').rglob('*.pdf')).parent / 'stray.pdf')),
    ('ICH-Q36-15', lambda s: shutil.copyfile(next((s / 'm3').rglob('*.pdf')), next((s / 'm3').rglob('*.pdf')).parent / 'Stray_File.pdf')),
    ('ICH-Q36-15', lambda s: (lambda d: (d.mkdir(parents=True), shutil.copyfile(next((s / 'm3').rglob('*.pdf')), d / 'x.pdf')))(
        s / 'm5' / '/'.join(['a' * 60] * 4))),
    ('ICH-Q36-16', lambda s: rewrite_index(s, lambda t: t.replace('</m3-quality>', '<m3-2-a-appendices/></m3-quality>', 1))),
    ('ICH-Q36-20', lambda s: rewrite_index(s, lambda t: re.sub(r'<title>[^<]+</title>', '<title> </title>', t, count=1))),
]


@pytest.mark.parametrize('rule,fn', DEFECTS, ids=[f'{r}-{i}' for i, (r, _) in enumerate(DEFECTS)])
def test_each_defect_fails_its_ich_rule(eu_seq, tmp_path, rule, fn):
    s = copy(eu_seq, tmp_path)
    fn(s)
    res = G.validate(s)
    r = next(x for x in ich(res)['results'] if x['rule'] == rule)
    assert r['status'] == 'fail' and r['failures'], r
    assert not ich(res)['ok'] and not res['ok']


def test_the_folder_and_the_stylesheet(eu_seq, tmp_path):
    res = G.validate(copy(eu_seq, tmp_path, '000a'))
    assert st(ich(res))['ICH-Q36-18'] == 'fail' and st(ich(res))['ICH-Q36-19'] == 'fail'
    s = copy(eu_seq, tmp_path / 'b')
    (s / 'util/style/ectd-2-0.xsl').write_text('<edited/>')
    r = next(x for x in ich(G.validate(s))['results'] if x['rule'] == 'ICH-Q36-02')
    assert r['status'] == 'warning' and 'ectd-2-0.xsl' in r['failures'][0]       # the stylesheet: a warning, never a failure


def test_what_published_samples_showed(eu_seq, tmp_path):
    """Three slips found in public sample sequences: the W3C's own xlink namespace (the ICH DTD fixes «w3c.org»), a sequence without
    the ICH DTD (its index.xml cannot be validated: said, not passed), and a later sequence without its regional index."""
    s = copy(eu_seq, tmp_path)
    rewrite_index(s, lambda t: t.replace('xmlns:xlink="http://www.w3c.org/1999/xlink"', 'xmlns:xlink="http://www.w3.org/1999/xlink"'))
    r = {x['rule']: x for x in ich(G.validate(s))['results']}
    assert r['ICH-Q36-03']['status'] == 'fail' and any('http://www.w3.org/1999/xlink' in f for f in r['ICH-Q36-03']['failures'])
    assert r['ICH-Q36-04']['status'] == 'pass' and r['ICH-Q36-12']['status'] == 'pass'      # the hrefs are still followed
    s = copy(eu_seq, tmp_path / 'b')
    (s / 'util' / 'dtd' / 'ich-ectd-3-2.dtd').unlink()
    r = {x['rule']: x for x in ich(G.validate(s))['results']}
    assert r['ICH-Q36-02']['status'] == 'fail' and r['ICH-Q36-03']['status'] == 'not_run' and 'could not be validated' in r['ICH-Q36-03']['reason']
    first = copy(eu_seq, tmp_path / 'c')
    later = first.parent / '0001'
    shutil.copytree(first, later)
    shutil.rmtree(later / 'm1')
    res = G.validate(later, previous=[first])
    assert st(ich(res))['ICH-Q36-05'] == 'fail' and res['region'] == 'eu' and res['region_from_earlier'] and res['own_criteria_run']


def test_the_pdf_rules_come_from_the_programs_pdf_check(eu_seq, tmp_path):
    s = copy(eu_seq, tmp_path)
    pdf = next((s / 'm3').rglob('*.pdf'))
    data = pdf.read_bytes()
    pdf.write_bytes(data.replace(b'%PDF-1.4', b'%PDF-1.3', 1) if data.startswith(b'%PDF-1.4') else b'%PDF-1.3' + data[8:])
    rewrite_index(s, lambda t: re.sub(r'checksum="[0-9a-f]{32}"(?=[^>]*xlink:href="' + re.escape(pdf.relative_to(s).as_posix()) + '")',
                                      f'checksum="{md5(pdf)}"', t))
    rewrite_index(s, lambda t: re.sub(r'(xlink:href="' + re.escape(pdf.relative_to(s).as_posix()) + r'"[^>]*?)checksum="[0-9a-f]{32}"',
                                      lambda m: m.group(1) + f'checksum="{md5(pdf)}"', t))
    res = G.validate(s)
    r = next(x for x in ich(res)['results'] if x['rule'] == 'ICH-FMT-01')
    assert r['status'] == 'fail' and '1.3' in r['failures'][0] and 'EDA' not in r['failures'][0]
    assert st(ich(res))['ICH-Q36-11'] == 'pass'


def test_the_command(eu_seq, tmp_path, capsys):
    out = tmp_path / 'r.html'
    assert G.main([str(eu_seq), '--html', str(out)]) == 0
    text = capsys.readouterr().out
    assert 'region: eu' in text and '1 · ICH — every country' in text and out.read_text(encoding='utf-8').count('ICH-Q36-') >= 18
    s = copy(eu_seq, tmp_path)
    (s / 'index-md5.txt').write_text('0' * 32)
    assert G.main([str(s)]) == 2 and 'ICH-Q36-11' in capsys.readouterr().out
    assert G.main([]) == 1
