"""Structured reading of EDA forms and other English-labelled certificates (intake rules, layer 2).

EDA prints its decisions as label : value tables — the Final Registration License (QF CAPP.041.04: Trade Name, Dosage Form,
Active Ingredient(s) & Strength(s), Shelf Life, Approved Pack, Price, Type of License, Registration No., Invalidation Date,
License Holder, Manufacturer, Manufacturer Of active substance…), the CADC Notification Letter (Product Name, Sample
Identification Code, Company Name, Supplier, Batch Number, Expiry date, Conformity) and the PPMA pricing letter (an inline
«Each 1g contains: A 3.5 mg + B 4.2 mg …» line with the public price). This module finds those blocks in the text (OCR
noise tolerated), lists every active substance with its strength, pairs each with the manufacturer printed for it, and
reads the composition table (ingredient · standard · quantity). Everything stays as printed; nothing is guessed."""
import difflib
import re

EACH_RX = r'each\s+[^:\n]{0,30}?contains?'
LABELS = [
    ('trade_name', [r'trade\s*name', r'product\s*name', r'invented\s*name', r'name\s*of\s*(?:the\s*)?product']),
    ('dosage_form', [r'dosage\s*form', r'pharmaceutical\s*form']),
    ('actives', [r'active\s*ingredient\(?s?\)?\s*(?:&|and)\s*strength\(?s?\)?', r'active\s*ingredient\(?s?\)?\s*&?\s*' + EACH_RX,
                 r'active\s*ingredient\(?s?\)?', r'active\s*substance\(?s?\)?', r'active\s*pharmaceutical\s*ingredient\(?s?\)?', r'strength\(?s?\)?', EACH_RX]),
    ('physical', [r'physical\s*character']),
    ('shelf_life', [r'shelf[\s-]*life']),
    ('storage', [r'storage\s*condition\(?s?\)?']),
    ('pack', [r'approved\s*pack\(?s?\)?', r'pack\s*size\(?s?\)?', r'presentation\(?s?\)?']),
    ('price', [r'price\(?s?\)?']),
    ('licence_type', [r'type\s*of\s*licen[cs]e']),
    ('marketing', [r'type\s*of\s*marketing']),
    ('reg_no', [r'registration\s*no\.?', r'registration\s*number', r'licen[cs]e\s*no\.?', r'licen[cs]e\s*number', r'notification\s*no\.?']),
    ('valid_until', [r'invalidation\s*date', r'valid\s*until', r'valid\s*to', r'expiry\s*date\s*/?\s*re-?\s*test\s*date', r'expiry\s*date']),
    ('holder', [r'licen[cs]e\s*holder', r'marketing\s*authori[sz]ation\s*holder', r'ma\s*holder', r'company\s*name', r'applicant']),
    ('api_manufacturers', [r'manufacturer\(?s?\)?\s*of\s*(?:the\s*)?active\s*substance\(?s?\)?', r'manufacturer\(?s?\)?\s*of\s*(?:the\s*)?active\s*ingredient\(?s?\)?',
                           r'api\s*manufacturer\(?s?\)?', r'active\s*substance\s*manufacturer\(?s?\)?', r'drug\s*substance\s*manufacturer\(?s?\)?', r'supplier\(?s?\)?']),
    ('manufacturer', [r'manufacturer\(?s?\)?(?!\s*of\s*(?:the\s*)?active)', r'manufactured\s*by', r'manufacturing\s*site']),
    ('packager', [r'packager']),
    ('storage_site', [r'storage\s*site']),
    ('issued', [r'issue\s*date', r'date\s*of\s*issue', r'issued\s*on']),
    ('sample_code', [r'sample\s*identification\s*code']),
    ('product_type', [r'type\s*of\s*product\(?s?\)?']),
    ('receipt', [r'date\s*of\s*receipt']),
    ('batch', [r'batch\s*number', r'batch\s*no\.?', r'lot\s*number', r'lot\s*no\.?']),
    ('conformity', [r'conformity']),
    ('country', [r'country\s*of\s*origin']),
]
LABEL_RX = [(key, re.compile(r'(?<![A-Za-z])(?:' + '|'.join(pats) + r')\s*[^:\n]{0,3}:', re.I)) for key, pats in LABELS]
UNIT = r'(?:mg|mcg|µg|ug|g|gm|iu|i\.u\.|%|ml|units?)'
STRENGTH = re.compile(r'^(?P<name>[A-Za-z][A-Za-z\s\-\.\(\)/,]*?)\s*(?P<amt>\d+(?:[.,]\d+)?)[!|]?\s?(?P<unit>' + UNIT + r')\b\s*(?:\(\s*(?P<eq>[^)]{1,60}?)\s*\))?', re.I)
EACH = re.compile(r'^\s*' + EACH_RX + r'\s*:?-?\s*', re.I)
SALTS = ['sulphate', 'sulfate', 'hydrochloride', 'zinc', 'sodium', 'potassium', 'calcium', 'magnesium', 'maleate', 'besylate', 'mesylate', 'tosylate',
         'acetate', 'citrate', 'phosphate', 'tartrate', 'fumarate', 'succinate', 'bromide', 'chloride', 'nitrate', 'stearate', 'trihydrate',
         'dihydrate', 'monohydrate', 'anhydrous', 'micronized', 'micronised', 'base', 'hemihydrate']
COMPANY = re.compile(r'\b(?:co\.?|ltd|limited|inc|gmbh|s\.?a\.?|s\.?p\.?a|pharma\w*|industr\w*|laborator\w*|labs?|chemicals?|corp\w*|llc|plc|pvt|ag|b\.?v|srl|share|group|biochemistry|biotech\w*|science\w*)\b', re.I)
ABBR_DOT = re.compile(r'(?<!\bCo)(?<!\bCO)(?<!\bLtd)(?<!\bLTD)(?<!\bInc)(?<!\bCorp)(?<!\bS\.A)(?<!\bsa)\.(?=\s+[A-Z])')
COUNTRIES = {'egypt', 'china', 'india', 'italy', 'germany', 'spain', 'france', 'uk', 'united kingdom', 'usa', 'united states', 'switzerland', 'austria', 'netherlands',
             'belgium', 'portugal', 'greece', 'turkey', 'jordan', 'saudi arabia', 'uae', 'korea', 'south korea', 'japan', 'taiwan', 'ireland', 'denmark', 'sweden',
             'finland', 'poland', 'hungary', 'czech republic', 'slovenia', 'croatia', 'romania', 'bulgaria', 'israel', 'canada', 'brazil', 'argentina', 'mexico',
             'malaysia', 'indonesia', 'thailand', 'vietnam', 'pakistan', 'bangladesh', 'morocco', 'tunisia', 'algeria', 'south africa', 'australia', 'new zealand', 'cyprus', 'malta'}
STD = re.compile(r'(?P<std>\b(?:BP|USP|EP|JP|IP|NF)(?:\s?\d{4})?\b|\bPh\.?\s?Eur\.?\s?[\d.]*|\bIn[\s-]?house\b|\bIH\b)', re.I)
TITLE = re.compile(r'^(?:dr|mr|mrs|ms|prof|eng)(?:\.\s*|\s+)', re.I)                   # a signature, not a substance
QTY = re.compile(r'(?P<qty>\d+(?:[.,]\d+)?)\s?(?P<unit>' + UNIT + r')\b', re.I)
NOISE = re.compile(r'^(?:[^A-Za-z0-9؀-ۿ(]+|[a-z]{1,3}\s+(?=[A-Z؀-ۿ])|[a-z]{1,3}[^A-Za-z0-9؀-ۿ]+(?=[A-Z]))+')
PACK_WORDS = r'(?:jar|bottle|box|pack|tube|vial|amp\w*|strip|sachet|blister|can|bag|carton|syringe|pen|inhaler|dropper)'


def _clean(s):
    s = re.sub(r'[‎‏‪-‮]', '', s or '')
    return re.sub(r'\s+', ' ', s).strip(' .,;:|-‘’“”\'"*')


def _line(s):
    """A line as read, keeping a trailing colon: «Each 1g contains:» alone on a line is still a label."""
    s = re.sub(r'[‎‏‪-‮]', '', s or '')
    return re.sub(r'\s+', ' ', s).strip(' .,;|-‘’“”\'"*')


def fix_salt(word):
    w = word.lower().strip('.,;')
    if w in SALTS or len(w) < 4:
        return word
    best = difflib.get_close_matches(w, SALTS, n=1, cutoff=0.72)
    if best and len(best[0]) >= 4 and abs(len(best[0]) - len(w)) <= 1 and best[0][0] == w[0]:
        b = best[0]
        return b.upper() if word.isupper() else b.capitalize() if word[:1].isupper() else b     # cased like the printed word
    return word


WORDS = ['pharmaceutical', 'pharmaceuticals', 'pharma', 'industries', 'industrial', 'laboratories', 'laboratory', 'company', 'limited', 'chemicals',
         'international', 'medical', 'healthcare', 'biotech', 'egypt', 'china', 'india', 'germany', 'manufacturing', 'trading', 'group', 'sciences']


def fix_words(text):
    """OCR slips in company names («gharmaceutical industries» → «pharmaceutical industries»); a word changes only when it is
    one letter away from a frequent corporate word of the same length."""
    out = []
    for w in re.split(r'(\s+)', text or ''):
        lw = w.lower()
        if lw.isalpha() and len(lw) >= 6 and lw not in WORDS:
            best = difflib.get_close_matches(lw, WORDS, n=1, cutoff=0.85)
            if best and len(best[0]) == len(lw):
                w = best[0].capitalize() if w[0].isupper() else best[0]
        out.append(w)
    return ''.join(out)


def norm_name(name):
    """An all-caps name as EDA prints it («NEOMYCIN SULPHATE») → «Neomycin Sulphate»; OCR'd salts repaired («Zine» → «Zinc»);
    a name printed in mixed case («Bisoprolol fumarate») stays as printed."""
    words = [fix_salt(w) for w in re.split(r'\s+', _clean(name)) if w]
    alpha = [w for w in words if w.isalpha()]
    if alpha and (all(w.isupper() for w in alpha) or all(w.islower() for w in alpha)):           # ALL CAPS or all lower → Title Case
        words = [w.capitalize() if len(w) > 2 else w for w in words]
    return ' '.join(words)


def _norm(s):
    return re.sub(r'[^a-z]', '', (s or '').lower())


def _first_label(line, pos):
    best = None
    for key, rx in LABEL_RX:
        m = rx.search(line, pos)
        if m and (best is None or m.start() < best[1].start()):
            best = (key, m)
    return best


def blocks(text):
    """{key: [lines]} for the label : value table of an EDA form. A label starts a block when it appears near the start of a
    line (OCR often prefixes lines with «| », «i », «ioe ‘»); the rest of the line may carry further labels."""
    out, cur = {}, None
    for raw in (text or '').splitlines():
        line = _line(NOISE.sub('', raw))
        if not line:
            continue
        best = _first_label(line, 0)
        if not best or best[1].start() > 28:
            if cur is not None:
                arabic_share = len(re.findall('[؀-ۿ]', line)) / max(1, len(line))
                if arabic_share > 0.5:
                    cur = None                      # the Arabic notes below the table end the value blocks
                else:
                    out[cur].append(_clean(line))
            continue
        pos = 0
        while best:
            key, m = best
            if m.start() > pos and cur is not None and pos == 0 and m.start() <= 28:
                pass                                # a few noise characters before the first label
            cur = key
            out.setdefault(cur, [])
            pos = m.end()
            nxt = _first_label(line, pos)
            seg = line[pos:nxt[1].start()] if nxt else line[pos:]
            if seg.strip():
                out[cur].append(seg.strip())
            best = nxt
            if nxt:
                pos = nxt[1].start()
    return out


def is_eda_form(text):
    return len(blocks(text)) >= 3


def actives(block_lines):
    """[{name, strength, equivalent}] from «Each 1g contains: A 3.5 mg (3300 unit) / B 4.2 mg …» (lines or «+» separated)."""
    text = ' \n '.join(block_lines)
    per_unit = None
    m = EACH.search(text)
    if m:
        per_unit = _clean(m.group(0).rstrip(':-'))
        text = text[m.end():]
    items = [x for x in re.split(r'\s*\+\s*|\n|;', text) if x.strip()]
    out = []
    for it in items:
        it = _clean(it)
        if not it or EACH.match(it) or re.match(r'^(?:strength|each)\b', it, re.I):
            continue
        if STD.search(it) or TITLE.match(it) or re.search(r'\b(?:website|tel|email|fax|issue\s*date)\b', it, re.I):
            continue                                     # a composition-table row (composition() reads it), a signature, a footer
        m = STRENGTH.match(it)
        if m:
            name = norm_name(m.group('name').split('(')[0])
            if not re.search(r'[A-Za-z]{4}', name):
                continue
            s = f"{m.group('amt')} {m.group('unit').lower().replace('gm', 'g')}"
            out.append({'name': name, 'strength': s, 'equivalent': _clean(m.group('eq')) if m.group('eq') else None})
        elif re.fullmatch(r'[A-Za-z][A-Za-z\s\-\.]{2,60}', it) and re.search(r'[A-Za-z]{4}', it) and not COMPANY.search(it):
            out.append({'name': norm_name(it), 'strength': None, 'equivalent': None})
    seen, uniq = set(), []
    for a in out:
        k = _norm(a['name'])
        if k and k not in seen:
            seen.add(k)
            uniq.append(a)
    if any(re.search(r'\d\.\d{3}\b', a['strength'] or '') for a in uniq):     # 3-decimal style on the form: «10,000 mg» is OCR for «10.000 mg»
        for a in uniq:
            if a['strength'] and re.match(r'^\d+,\d{3}\b', a['strength']):
                a['strength'] = a['strength'].replace(',', '.', 1)
    return uniq, per_unit


def split_country(s):
    s = fix_words(re.sub(r'[\s\d|\[\]().,;:-]+$', '', _clean(s)))         # OCR noise after the last word («EGYPT 1 1 1»)
    m = re.search(r'[,،]\s*([^,،]+)$', s)                                     # only the last comma part is the country; «Co.,Ltd» stays as printed
    if m:
        tail = m.group(1).strip()
        if tail.lower().strip('. ') in COUNTRIES or (tail.isupper() and len(tail) <= 20):
            return _clean(s[:m.start()]), tail.strip('. ').title()
    return _clean(s), None


def api_manufacturers(block_lines, apis):
    """Pair the API names listed in the «Manufacturer Of active substance» block with the company printed after them.
    Lines that are neither a known API name nor a company are ignored; a company with no preceding API name is kept as a
    supplier, and assigned only when exactly one API still lacks a manufacturer."""
    names = {a['name']: _norm(a['name']) for a in apis}
    pending, assigned, suppliers = [], {}, []
    for raw in block_lines:
        for line in ABBR_DOT.split(raw):                   # «…china. Northchina …» (several suppliers on one line)
            line = _clean(line)
            if not line:
                continue
            n = _norm(line)
            hit = None
            for name, nn in names.items():
                if n == nn or difflib.SequenceMatcher(None, n, nn).ratio() >= 0.78 or (len(nn) >= 5 and n.startswith(nn[:5]) and len(n) <= len(nn) + 3):
                    hit = name
                    break
            if hit and not COMPANY.search(line):
                pending.append(hit)
                continue
            if COMPANY.search(line) or split_country(line)[1]:
                company, country = split_country(line)
                if pending:
                    for nm in pending:
                        assigned[nm] = {'manufacturer': company, 'country': country}
                    pending = []
                else:
                    suppliers.append({'manufacturer': company, 'country': country})
    missing = [a['name'] for a in apis if a['name'] not in assigned]
    if len(suppliers) == 1 and len(missing) == 1:
        assigned[missing[0]] = suppliers.pop()
    return assigned, suppliers


def composition(text):
    """Rows of a composition table: «Neomycin Sulphate (Equivalent to 3300 units/g)  BP2018  3.5 mg» → name, standard, amount,
    role (active | excipient) from the «Active Ingredients» / «Inactive Ingredients» headers."""
    rows, role = [], None
    for raw in (text or '').splitlines():
        line = _clean(raw)
        low = line.lower()
        if re.search(r'\b(?:in)?active\s*ingredients?\b|excipients?\b', low) and not QTY.search(line):
            role = 'excipient' if re.search(r'inactive|excipient', low) else 'active'
            continue
        if role is None:
            continue
        ms = STD.search(line)
        mq = None
        for q in QTY.finditer(line):
            mq = q                                           # the last quantity on the line is the amount column
        if not ms or not mq or mq.start() < ms.start():
            continue
        name = line[:ms.start()]
        eq = re.search(r'\(([^)]*)\)?', name)
        name = _clean(re.sub(r'\([^)]*\)?', '', name))
        if not re.search(r'[A-Za-z]{3}', name):
            continue
        rows.append({'name': norm_name(name), 'standard': _clean(ms.group('std')).upper().replace('PH. EUR', 'Ph. Eur').replace('PH.EUR', 'Ph. Eur'),
                     'amount': f"{mq.group('qty')} {mq.group('unit').lower().replace('gm', 'g')}", 'role': role, 'equivalent': _clean(eq.group(1)) if eq else None})
    return rows


def prices(block_lines):
    """«34 L.E. / 1 Box/ 1 Bottle/ 10 Gm ; 60 L.E. / 1 Box/ 1 Jar/ 20 Gm» → [{price, pack}]."""
    out = []
    for raw in block_lines:
        for seg in re.split(r';|\n', raw):
            m = re.search(r'(\d+(?:[.,]\d+)?)\s*(L\.?\s?E\.?|LE|EGP|جنيه|ج\.م)\s*/?\s*(.*)', _clean(seg), re.I)
            if m:
                pack = _clean(re.sub(r'[|\[\]]', ' ', m.group(3)))
                pack = re.sub(r'\s+\d\s*$', '', pack)
                out.append({'price': f"{m.group(1)} EGP", 'pack': pack or None})
    return out


def _date(s):
    m = re.search(r'(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{4})|(\d{4})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{1,2})', s or '')
    if not m:
        return None
    d, mo, y = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(6), m.group(5), m.group(4))
    try:
        d, mo = int(d), int(mo)
    except ValueError:
        return None
    return f'{y}-{mo:02d}-{d:02d}' if 1 <= d <= 31 and 1 <= mo <= 12 else None


def read(text):
    """The EDA-form reading of one document in the intake's shape (only what the form states)."""
    b = blocks(text)
    out = {'product': {}, 'profile': {}, 'envelope': {}, 'registration': {}, 'apis': [], 'batches': [], 'document': {}, 'composition': [], 'suppliers': []}
    P, R, E, D = out['product'], out['registration'], out['envelope'], out['document']
    if b.get('trade_name'):
        v = ' '.join(b['trade_name'])
        lat = re.search(r'[A-Za-z][A-Za-z0-9 .\-/%]{1,80}', v)
        ar = re.search('[؀-ۿ][؀-ۿ ]{1,60}', v)
        if lat:
            P['name'] = _clean(re.sub(r'\s+[a-z]{1,2}\s+\d+\s*$', '', lat.group(0)))     # «Wouncure ‘a 07» (OCR of the stamp)
        if ar:
            P['name_ar'] = _clean(ar.group(0))
    if not P.get('name') and re.search('اسم المستحضر', text or ''):                      # pricing letter: Arabic header, Latin name below
        tail = text[re.search('اسم المستحضر', text).end():]
        ml = re.search(r'\n[^\n]*?([A-Z][A-Za-z0-9]+(?:\s+[A-Za-z0-9]+){0,5})', tail)
        if ml:
            P['name'] = _clean(ml.group(1))
    if b.get('dosage_form'):
        P['dosage_form'] = _clean(re.sub('[؀-ۿ]+', '', b['dosage_form'][0]))
    if b.get('physical'):
        P['physical_character'] = _clean(b['physical'][0])
    if b.get('actives'):
        apis, per_unit = actives(b['actives'])
        out['apis'] = [{'name': a['name'], **{k: a[k] for k in ('strength', 'equivalent') if a.get(k)}} for a in apis]
        if per_unit:
            P['per_unit'] = per_unit
        if apis and len(apis) == 1 and apis[0]['strength']:
            P['strength'] = apis[0]['strength']
    if b.get('api_manufacturers'):
        assigned, suppliers = api_manufacturers(b['api_manufacturers'], out['apis'])
        for a in out['apis']:
            if a['name'] in assigned:
                a.update(assigned[a['name']])
        out['suppliers'] = suppliers
    if b.get('manufacturer'):
        P['manufacturer'], c = split_country(b['manufacturer'][0])
        if c:
            P['manufacturer_country'] = c
    if b.get('holder'):
        h = re.split(r';|[؀-ۿ]', b['holder'][0])[0]
        E['applicant'], _ = split_country(h)
    if b.get('shelf_life'):
        R['shelf_life'] = _clean(b['shelf_life'][0])
    if b.get('storage'):
        R['storage'] = _clean(b['storage'][0])
    if b.get('pack'):
        R['packs'] = [_clean(x) for x in b['pack'] if re.search(r'[A-Za-z؀-ۿ]{3}', x)]
    if b.get('price'):
        pr = prices(b['price'])
        if pr:
            R['prices'] = pr
            R['price'] = pr[0]['price']
            if not R.get('packs'):
                R['packs'] = [p['pack'] for p in pr if p['pack']]
    rows = []
    for mp in re.finditer(r'^(?P<pack>' + PACK_WORDS + r'[^\n\d]{0,30}?\d{0,3}\s?(?:g|gm|ml|mg)?)\s+(?P<pt>\d{1,2})\s+(?P<le>\d{1,5})\s*$', text or '', re.I | re.M):
        row = {'price': f"{mp.group('le')}.{int(mp.group('pt')):02d} EGP", 'pack': _clean(mp.group('pack'))}
        if row not in rows:
            rows.append(row)                                                              # pricing table rows «Jar of 10gm  00  51», one per pack
    if rows and not R.get('price'):
        R['prices'] = rows
        R['price'] = rows[0]['price']
        R.setdefault('packs', [r['pack'] for r in rows])
    if b.get('reg_no'):
        m = re.search(r'[A-Z0-9][A-Z0-9/\-.]{2,30}', ' '.join(b['reg_no']))
        if m:
            R['reg_no'] = D['number'] = m.group(0).strip('.')
    if b.get('valid_until'):
        D['valid_until'] = _date(' '.join(b['valid_until']))
    if b.get('issued'):
        D['issued'] = _date(' '.join(b['issued']))
        R['reg_date'] = D['issued']
    if b.get('licence_type'):
        v = b['licence_type'][0].lower()
        out['profile']['licence'] = 'toll' if 'toll' in v else 'under_licence' if 'licen' in v and 'under' in v else 'own' if 'own' in v else None
    if b.get('marketing'):
        v = b['marketing'][0].lower()
        out['profile']['origin'] = 'local' if 'local' in v else 'imported' if 'import' in v else None
    mb = re.search(r'batch\s*n(?:umber|o)\b[^A-Za-z0-9\n]{0,12}([A-Z0-9][A-Z0-9\-/]{3,19})', text or '', re.I)
    if mb:                                                                                 # CADC notification letter row, OCR noise tolerated
        bt = {'no': mb.group(1), 'kind': 'fpp'}
        me = re.search(r'(?:expiry|re-?\s?test)[^\d\n]{0,60}(\d{1,2}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*\d{4})', text, re.I)
        if me:
            bt['expiry'] = _date(me.group(1))
        row = text[text.rfind('\n', 0, mb.start()) + 1:text.find('\n', mb.end()) if text.find('\n', mb.end()) > 0 else len(text)]
        mc = re.search(r'\b(non-?\s?conform\w*|conform\w*)\s*[^A-Za-z\n]*$', row, re.I) or re.search(r'^\W*(non-?\s?conform(?:s|ing)?|conforms?)\W*$', text, re.I | re.M)
        if mc:
            bt['conformity'] = 'Non-conform' if mc.group(1).lower().startswith('non') else 'Conform'
        out['batches'].append(bt)
    if b.get('sample_code'):
        D['sample_code'] = _clean(b['sample_code'][0])
    comp = composition(text)
    if comp:
        out['composition'] = comp
    out['profile'] = {k: v for k, v in out['profile'].items() if v}
    found = any(out[k] for k in ('product', 'envelope', 'registration', 'apis', 'batches', 'composition')) or any(D.values())
    return out if found and (len(b) >= 2 or out['batches'] or out['apis']) else {}
