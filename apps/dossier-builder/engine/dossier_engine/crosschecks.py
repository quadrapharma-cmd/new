"""Dossier-level checks on structured data (P2): the 11 cross-checks of the company
checklist (sheet «فحوص التطابق Cross-checks») and the NP.CAPP.040 deficiencies that
can be decided from data. Each finding: id, severity (block|warn), en/ar, the slots
it concerns (to show on the board), action, source. Nothing is inferred from
missing data: a check that lacks its inputs reports 'needs data' with the fields."""
import re
from dataclasses import dataclass, field

NON_NUMERIC = re.compile(r'^\s*(conform\w*|complies|pass(es)?|ok|meets|within limits?|يطابق|مطابق)\s*$', re.I)
SCALES = ('pilot', 'production')


@dataclass
class XFinding:
    id: str
    severity: str
    en: str
    ar: str
    slots: list = field(default_factory=list)
    action: str = 'user_fix'
    source: str = ''
    needs: list = field(default_factory=list)

    def to_dict(self):
        return self.__dict__.copy()


def _norm(s):
    return re.sub(r'[\s,.;:]+', ' ', (s or '').lower()).strip()


def _api_key(a):
    return f"{a.get('name')}|{a.get('manufacturer')}"


def run(data, profile):
    """data: the dossier's structured data (see DATA_SCHEMA in app/api.py); profile: Profile."""
    out = []
    add = out.append
    apis = data.get('apis') or []
    batches = data.get('batches') or []
    specs = data.get('specs') or {}
    results = data.get('results') or {}
    product = data.get('product') or {}
    comp = data.get('composition') or []

    # ---- XC-03 API standard in 3.2.P.1 = S-part specification standard
    for a in apis:
        c = next((x for x in comp if _norm(x.get('name')) in (_norm(a.get('name')), _norm(a.get('salt_name')))), None)
        if c and a.get('spec_standard') and c.get('standard') and _norm(c['standard']).split(' ')[0] != _norm(a['spec_standard']).split(' ')[0]:
            add(XFinding('XC-03', 'block', f"API standard differs: 3.2.P.1 says «{c['standard']}», 3.2.S.4.1 says «{a['spec_standard']}» ({a.get('name')}).",
                         f"مرجع المادة الفعالة مختلف بين 3.2.P.1 («{c['standard']}») و 3.2.S.4.1 («{a['spec_standard']}»).",
                         ['P-01', f"S-08@{_api_key(a)}"], 'rebuild', 'NP.CAPP.040 P.1'))
    # ---- XC-04 API name in composition = supplier CoA (else synonyms evidence)
    for a in apis:
        if a.get('coa_name') and comp:
            names = {_norm(x.get('name')) for x in comp}
            if _norm(a['coa_name']) not in names and not a.get('synonyms_evidence'):
                add(XFinding('XC-04', 'block', f"API name on the supplier CoA («{a['coa_name']}») is not the name in the composition certificate; "
                             'use the same name or attach synonyms evidence (1.2.8.7).',
                             f"اسم المادة في شهادة التحليل («{a['coa_name']}») مختلف عن شهادة التركيب؛ وحّد الاسم أو أرفق دليل المرادفات.",
                             ['M1-31', f"M1-35@{_api_key(a)}"], 'rebuild', 'NP.CAPP.065 1.2.1 N.B.'))
    # ---- XC-05 spec tests ↔ batch results (P.5.1 ↔ P.5.4; S.4.1 ↔ S.4.4) + NP.CAPP.040 numeric results
    def spec_vs_results(spec, batch_nos, scope, slots, src):
        tests = [t['test'] for t in spec if t.get('test')]
        for b in batch_nos:
            r = results.get(b) or {}
            miss = [t for t in tests if t not in r]
            if miss:
                add(XFinding('XC-05', 'block', f"Batch {b}: no result for {', '.join(miss[:6])} ({scope}).",
                             f"التشغيلة {b}: لا توجد نتيجة لـ {', '.join(miss[:6])} ({scope}).", slots, 'request_data', src))
            words = [t for t in tests if t in r and NON_NUMERIC.match(str(r[t])) and not _qualitative(spec, t)]
            if words:
                add(XFinding('NP040-NUM', 'block', f"Batch {b}: «{r[words[0]]}» instead of a numeric result for {', '.join(words[:6])}.",
                             f"التشغيلة {b}: «{r[words[0]]}» بدل نتيجة رقمية لـ {', '.join(words[:6])}.", slots, 'request_data',
                             'NP.CAPP.040 P.5.4 («Conform» instead of numeric results)'))
    fpp_batches = [b['no'] for b in batches if b.get('kind', 'fpp') == 'fpp']
    if specs.get('product'):
        spec_vs_results(specs['product'], fpp_batches, '3.2.P.5.1 ↔ 3.2.P.5.4', ['P-09', 'P-11'], 'NP.CAPP.040 P.5.4')
        if not any('dissolution' in _norm(t.get('test')) and re.search(r'\bq\b', _norm(t.get('limit'))) for t in specs['product']) \
                and any('dissolution' in _norm(t.get('test')) for t in specs['product']):
            add(XFinding('NP040-Q', 'block', 'Dissolution limit has no «Q» value.', 'حد الذوبان بدون قيمة «Q».', ['P-09'], 'user_fix',
                         'NP.CAPP.040 P.5.1 (dissolution «Q» missing)'))
    for a in apis:
        k = _api_key(a)
        sp = (specs.get('api') or {}).get(k)
        api_b = [b['no'] for b in batches if b.get('kind') == 'api' and b.get('api') == k]
        if sp:
            spec_vs_results(sp, api_b, f"3.2.S.4.1 ↔ 3.2.S.4.4 ({a.get('manufacturer')})", [f'S-08@{k}', f'S-10@{k}'], 'NP.CAPP.040 S.4.4')
        if len(api_b) < 2:
            add(XFinding('NP040-S44', 'block', f"{a.get('name')} / {a.get('manufacturer')}: {len(api_b)} API batch analyses — at least 2 required"
                         + (' (at least pilot scale, CEP route)' if a.get('option') == 'CEP' else '') + '.',
                         f"{a.get('name')} / {a.get('manufacturer')}: عدد تحاليل تشغيلات المادة الفعالة {len(api_b)} — المطلوب 2 على الأقل.",
                         [f'S-10@{k}'], 'request_data', 'NP.CAPP.040 S.4.4; CTD QM guideline v2 (CEP: 2 pilot-scale batches)'))
    # ---- NP.CAPP.040 P.5.4: ≥2 FPP batches of at least pilot scale, with number/size/date/site
    full = [b for b in batches if b.get('kind', 'fpp') == 'fpp']
    if len(full) < 2:
        add(XFinding('NP040-P54', 'block', f'{len(full)} finished-product batch(es) — at least 2 required (pilot or production scale).',
                     f'عدد تشغيلات المستحضر {len(full)} — المطلوب 2 على الأقل (تجريبي أو إنتاجي).', ['P-11', 'P-16'], 'request_data',
                     'NP.CAPP.040 P.5.4 («only 1 batch (minimum 2)»)'))
    for b in full:
        miss = [f for f in ('no', 'size', 'date', 'site', 'scale') if not b.get(f)]
        if miss:
            add(XFinding('NP040-BDESC', 'warn', f"Batch {b.get('no', '?')}: {', '.join(miss)} missing.",
                         f"التشغيلة {b.get('no', '?')}: ناقص {', '.join(miss)}.", ['P-11'], 'request_data', 'NP.CAPP.040 P.5.4 (batch description missing)'))
        elif b['scale'] not in SCALES and not data.get('uncomplicated_fpp'):
            add(XFinding('NP040-SCALE', 'warn', f"Batch {b['no']} is «{b['scale']}» scale; pilot or production expected "
                         '(smaller batches only for an uncomplicated FPP).', f"التشغيلة {b['no']} حجمها «{b['scale']}»؛ المتوقع تجريبي أو إنتاجي.",
                         ['P-11'], 'user_fix', 'WHO TRS 953 Annex 2 / KB §10.3'))
    # ---- XC-09 batch numbers consistent: BE / stability batches exist in the batch list; BE batch has executed BMR
    known = {b.get('no') for b in batches}
    for use, slot in (('be_batches', 'M5-04'), ('stability_batches', 'P-16')):
        for n in data.get(use) or []:
            if n not in known:
                add(XFinding('XC-09', 'block', f"Batch {n} used in {'the BE study' if use == 'be_batches' else 'stability'} is not in the batch list.",
                             f"التشغيلة {n} المستخدمة في {'دراسة التكافؤ' if use == 'be_batches' else 'الثبات'} غير موجودة في قائمة التشغيلات.",
                             [slot, 'P-11'], 'request_data', 'WHO QOS-PD P.2.2.1; NP.CAPP.040'))
    for n in data.get('be_batches') or []:
        b = next((x for x in batches if x.get('no') == n), None)
        if b and not b.get('executed_bmr'):
            add(XFinding('NP040-R11', 'block', f"No executed batch record for the BE batch {n} (3.2.R.1.1).",
                         f"لا يوجد سجل تشغيل منفّذ لتشغيلة التكافؤ {n} (3.2.R.1.1).", ['R-01'], 're_obtain',
                         'CTD QM guideline v2 3.2.R.1.1; NP.CAPP.040'))
    # ---- XC-06 API manufacturer name/address identical (GMP ↔ Annex I ↔ 3.2.S.2.1)
    for a in apis:
        vals = {k: _norm(a.get(k)) for k in ('address_gmp', 'address_annex', 'address_s21') if a.get(k)}
        if len(set(vals.values())) > 1:
            add(XFinding('XC-06', 'block', f"{a.get('manufacturer')}: the site address differs between "
                         + ', '.join(k.replace('address_', '') for k in vals) + '. Use the address exactly as on the GMP certificate.',
                         f"{a.get('manufacturer')}: عنوان الموقع مختلف بين المستندات؛ استخدم العنوان كما في شهادة الـ GMP بالضبط.",
                         ['M1-01', f"M1-38@{_api_key(a)}", f"S-04@{_api_key(a)}"], 'rebuild', 'NP.CAPP.065 Annex I; NP.CAPP.040 S.2.1'))
    # ---- XC-07 pack units Annex I = Pricing Certificate; packaging material = stability
    pk = data.get('pack') or {}
    if pk.get('units_annex') and pk.get('units_pricing') and _norm(pk['units_annex']) != _norm(pk['units_pricing']):
        add(XFinding('XC-07', 'block', f"Pack units differ: Annex I «{pk['units_annex']}» vs Pricing Certificate «{pk['units_pricing']}».",
                     f"عدد الوحدات مختلف: نموذج الطلب «{pk['units_annex']}» وشهادة التسعير «{pk['units_pricing']}».", ['M1-01', 'M1-05'],
                     'rebuild', 'NP.CAPP.065 Annex I note'))
    if pk.get('material_annex') and pk.get('material_stability') and _norm(pk['material_annex']) != _norm(pk['material_stability']):
        add(XFinding('XC-07', 'block', f"Packaging material differs: Annex I «{pk['material_annex']}» vs stability «{pk['material_stability']}».",
                     f"مادة العبوة مختلفة: نموذج الطلب «{pk['material_annex']}» والثبات «{pk['material_stability']}».", ['M1-01', 'P-16', 'P-15'],
                     'rebuild', 'NP.CAPP.065 Annex I note'))
    # ---- XC-08 CEP current + retest/storage covers the proposal
    for a in apis:
        if a.get('option') != 'CEP':
            continue
        if not a.get('cep_no'):
            add(XFinding('XC-08', 'block', f"{a.get('name')} / {a.get('manufacturer')}: CEP number missing.", 'رقم الـ CEP ناقص.',
                         [f"M1-39@{_api_key(a)}"], 'request_data', 'NP.CAPP.040 (CEP route)', needs=['cep_no']))
        if a.get('cep_status') and a['cep_status'].lower() in ('withdrawn', 'suspended', 'expired'):
            add(XFinding('XC-08', 'block', f"CEP {a.get('cep_no')} is {a['cep_status']} on the EDQM database — full 3.2.S data required.",
                         f"الـ CEP {a.get('cep_no')} حالته {a['cep_status']} — مطلوب بيانات 3.2.S كاملة.", [f"M1-39@{_api_key(a)}"], 're_obtain',
                         'NP.CAPP.040; CTD QM guideline v2'))
        if a.get('cep_retest_months') and a.get('proposed_retest_months') and int(a['proposed_retest_months']) > int(a['cep_retest_months']) \
                and not a.get('s7_data'):
            add(XFinding('XC-08', 'block', f"Proposed retest period {a['proposed_retest_months']} months exceeds the CEP's {a['cep_retest_months']} — 3.2.S.7 data required.",
                         'فترة إعادة الاختبار المقترحة أطول من الـ CEP — مطلوب بيانات 3.2.S.7.', [f"S-14@{_api_key(a)}"], 'request_data',
                         'CTD QM guideline v2 (CEP S.7 exception)'))
    # ---- XC-11 applicant spelled identically (envelope ↔ Annex I ↔ cover letter)
    names = {k: v for k, v in (data.get('applicant_names') or {}).items() if v}
    core = lambda v: re.sub(r'\b(egypt|s a e|sae|co|company|ltd|llc|for pharmaceutical industries)\b', '', _norm(v).replace('-', ' ')).strip()
    if len({_norm(v) for v in names.values()}) > 1:
        same_company = len({core(v) for v in names.values()}) == 1
        add(XFinding('XC-11', 'warn' if same_company else 'block', 'Applicant name is not spelled identically: ' + '; '.join(f'{k} «{v}»' for k, v in names.items()) + '.',
                     'اسم المتقدم غير مكتوب بنفس الطريقة في كل المستندات.', ['M1-01', 'M1-43'], 'rebuild', 'EG draft §3.2.2; EG-BP-E09'))
    # ---- XC-10 leaflet/layout vs product data: shelf life / storage given in data but differ
    lf = data.get('leaflet') or {}
    for k, label, label_ar in (('shelf_life', 'shelf life', 'الصلاحية'), ('storage', 'storage condition', 'ظروف التخزين')):
        if lf.get(k) and product.get(k) and _norm(lf[k]) != _norm(product[k]):
            add(XFinding('XC-10', 'block', f"Leaflet {label} «{lf[k]}» ≠ product data «{product[k]}».",
                         f"{label_ar} في النشرة «{lf[k]}» ≠ بيانات المنتج «{product[k]}».", ['M1-09', 'M1-11'], 'user_fix',
                         'NP.CAPP.065 Annex I undertaking'))
    return out


def _qualitative(spec, test):
    """A test whose result is a word by nature: marked so, or its acceptance criterion carries no number (a description, an
    identification, «complies with the test») — «Conforms» is then the result, not a missing figure."""
    t = next((x for x in spec if x.get('test') == test), {})
    limit = str(t.get('limit') or t.get('acceptance') or '')
    return bool(t.get('qualitative')) or (bool(limit) and not re.search(r'\d', limit)) or bool(re.match(r'\s*(?:\d+\s*[-.)]\s*)?(?:description|appearance|identification|identity|odou?r|colou?r)', str(test), re.I))
