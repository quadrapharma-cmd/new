"""Controlled vocabularies: dose forms (EDQM standard terms with Arabic names and default routes), countries (ISO 3166-1 with
Arabic names), strength units, API submission options. A value read from a document is matched here so the screen shows a
dropdown with the standard entry selected; what does not match stays as printed and is marked non-standard. Lists for the
dropdowns and the names already used in this workspace (applicants, manufacturers, substances) come from `payload`."""
import json
import re
import unicodedata
from pathlib import Path

import yaml

DIR = Path(__file__).resolve().parents[2] / 'rulepacks' / 'vocab'
ROUTES = [{'id': 'oral', 'en': 'Oral', 'ar': 'فموي'}, {'id': 'topical', 'en': 'Topical (skin)', 'ar': 'موضعي (جلد)'}, {'id': 'parenteral', 'en': 'Parenteral (injection)', 'ar': 'حقن'},
          {'id': 'ophthalmic', 'en': 'Ophthalmic', 'ar': 'عين'}, {'id': 'inhalation', 'en': 'Inhalation / nasal', 'ar': 'استنشاق / أنف'}, {'id': 'other', 'en': 'Other', 'ar': 'أخرى'}]
UNITS = ['mg', 'g', 'mcg', 'IU', '%', 'mg/ml', 'mg/g', 'mg/5ml', 'mcg/dose', 'mg/dose', 'mmol', 'mEq', 'units/g', 'IU/ml']
API_OPTIONS = [{'id': 'CEP', 'en': 'CEP — certificate of suitability', 'ar': 'CEP — شهادة ملاءمة'}, {'id': 'DMF', 'en': 'DMF — master file with letter of access', 'ar': 'DMF — ملف رئيسي مع خطاب وصول'},
               {'id': 'PQ', 'en': 'WHO prequalified', 'ar': 'مؤهل مسبقاً من منظمة الصحة العالمية'}, {'id': 'FULL', 'en': 'Full 3.2.S data', 'ar': 'بيانات 3.2.S كاملة'}]
COUNTRY_SYN = {'uk': 'GB', 'u.k.': 'GB', 'england': 'GB', 'scotland': 'GB', 'great britain': 'GB', 'usa': 'US', 'u.s.a.': 'US', 'u.s.a': 'US', 'united states of america': 'US', 'america': 'US',
               'prc': 'CN', 'p.r. china': 'CN', 'p.r.china': 'CN', "people's republic of china": 'CN', 'peoples republic of china': 'CN', 'korea': 'KR', 'south korea': 'KR', 'republic of korea': 'KR',
               'uae': 'AE', 'u.a.e.': 'AE', 'ksa': 'SA', 'k.s.a.': 'SA', 'saudi': 'SA', 'turkey': 'TR', 'türkiye': 'TR', 'czech republic': 'CZ', 'russia': 'RU', 'vietnam': 'VN', 'viet nam': 'VN', 'iran': 'IR',
               'syria': 'SY', 'taiwan': 'TW', 'hong kong': 'HK', 'macau': 'MO', 'holland': 'NL', 'the netherlands': 'NL', 'bolivia': 'BO', 'venezuela': 'VE', 'tanzania': 'TZ', 'laos': 'LA',
               'moldova': 'MD', 'north macedonia': 'MK', 'macedonia': 'MK', 'palestine': 'PS', 'brunei': 'BN', 'ivory coast': 'CI', "cote d'ivoire": 'CI', 'swaziland': 'SZ', 'burma': 'MM',
               'مصر': 'EG', 'الصين': 'CN', 'الهند': 'IN', 'ألمانيا': 'DE', 'المانيا': 'DE', 'إيطاليا': 'IT', 'ايطاليا': 'IT', 'فرنسا': 'FR', 'إسبانيا': 'ES', 'اسبانيا': 'ES', 'سويسرا': 'CH', 'تركيا': 'TR',
               'الأردن': 'JO', 'الاردن': 'JO', 'السعودية': 'SA', 'الإمارات': 'AE', 'الامارات': 'AE', 'كوريا': 'KR', 'اليابان': 'JP', 'بريطانيا': 'GB', 'إنجلترا': 'GB', 'أمريكا': 'US', 'امريكا': 'US',
               'كندا': 'CA', 'البرازيل': 'BR', 'باكستان': 'PK', 'بنغلاديش': 'BD', 'إندونيسيا': 'ID', 'ماليزيا': 'MY', 'تايلاند': 'TH', 'فيتنام': 'VN', 'المغرب': 'MA', 'تونس': 'TN', 'الجزائر': 'DZ',
               'لبنان': 'LB', 'سوريا': 'SY', 'العراق': 'IQ', 'السودان': 'SD', 'اليونان': 'GR', 'هولندا': 'NL', 'بلجيكا': 'BE', 'النمسا': 'AT', 'بولندا': 'PL', 'المجر': 'HU', 'التشيك': 'CZ', 'البرتغال': 'PT',
               'الدنمارك': 'DK', 'السويد': 'SE', 'فنلندا': 'FI', 'أيرلندا': 'IE', 'روسيا': 'RU', 'أستراليا': 'AU', 'قبرص': 'CY', 'مالطا': 'MT', 'إسرائيل': 'IL', 'تايوان': 'TW'}

_FORMS = None
_COUNTRIES = None


def forms():
    global _FORMS
    if _FORMS is None:
        _FORMS = yaml.safe_load((DIR / 'forms.yaml').read_text(encoding='utf-8')) or []
    return _FORMS


def countries():
    global _COUNTRIES
    if _COUNTRIES is None:
        _COUNTRIES = json.loads((DIR / 'countries.json').read_text(encoding='utf-8'))
    return _COUNTRIES


def _norm(s):
    s = unicodedata.normalize('NFKC', str(s or '')).lower()
    s = re.sub('[ً-ْـ]', '', s)                       # Arabic diacritics and tatweel
    s = s.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه').replace('ى', 'ي')
    s = re.sub(r'[^\w\s%/.-]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def match_form(text):
    """The standard dose form a printed value means: exact name/synonym first, then the longest synonym contained in the text."""
    t = _norm(text)
    if not t:
        return None
    best, best_len = None, 0
    for f in forms():
        names = [f['en'], f['ar'], f['id'].replace('-', ' ')] + list(f.get('syn') or [])
        for n in names:
            nn = _norm(n)
            if not nn:
                continue
            if nn == t:
                return {k: f[k] for k in ('id', 'en', 'ar', 'route')}
            if len(nn) >= 3 and re.search(r'(?<!\w)' + re.escape(nn) + r'(?!\w)', t) and len(nn) > best_len:
                best, best_len = f, len(nn)
    return {k: best[k] for k in ('id', 'en', 'ar', 'route')} if best else None


def match_country(text):
    t = _norm(text).strip(' .,')
    if not t:
        return None
    if t in COUNTRY_SYN:
        code = COUNTRY_SYN[t]
        return next(({'code': c['code'], 'en': c['en'], 'ar': c['ar']} for c in countries() if c['code'] == code), None)
    for c in countries():
        if t == c['code'].lower() or t == _norm(c['en']) or t == _norm(c['ar']):
            return {'code': c['code'], 'en': c['en'], 'ar': c['ar']}
    for c in countries():                                           # «Republic of India», «China (Mainland)»
        en = _norm(c['en'])
        if len(en) >= 4 and re.search(r'(?<!\w)' + re.escape(en) + r'(?!\w)', t):
            return {'code': c['code'], 'en': c['en'], 'ar': c['ar']}
    return None


def known_names(st):
    """Names already used in this workspace, for suggestions: applicants, finished-product manufacturers, substances, API manufacturers."""
    out = {'applicants': set(), 'manufacturers': set(), 'apis': set(), 'api_manufacturers': set()}
    try:
        rows = st.db.execute('select profile, product, envelope, data from dossier').fetchall()
    except Exception:
        return {k: [] for k in out}
    for r in rows:
        prof, prod, env, data = (json.loads(r[k]) if isinstance(r[k], str) else (r[k] or {}) for k in ('profile', 'product', 'envelope', 'data'))
        if (env or {}).get('applicant'):
            out['applicants'].add(env['applicant'])
        if (prod or {}).get('manufacturer'):
            out['manufacturers'].add(prod['manufacturer'])
        for a in (prof or {}).get('apis') or []:
            if a.get('name'):
                out['apis'].add(a['name'])
            if a.get('manufacturer'):
                out['api_manufacturers'].add(a['manufacturer'])
        for a in (data or {}).get('apis') or []:
            if a.get('name'):
                out['apis'].add(a['name'])
            if a.get('manufacturer'):
                out['api_manufacturers'].add(a['manufacturer'])
    return {k: sorted(v, key=str.lower) for k, v in out.items()}


def payload(st=None):
    return {'forms': [{k: f[k] for k in ('id', 'en', 'ar', 'route')} for f in forms()], 'routes': ROUTES, 'countries': countries(), 'units': UNITS,
            'api_options': API_OPTIONS, 'known': known_names(st) if st is not None else {}}
