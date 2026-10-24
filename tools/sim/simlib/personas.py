"""Deterministic personas: Egyptian/Arab pharma professionals and their companies, from a seed.

Person i depends only on (seed, i), so the first 100 of a 1000-account run are the 100-account run's people. About one person
in eight owns a company (created through the app on the first day); most others work for an earlier owner's company (invited
to its team), the rest are independent (community pharmacists, consultants, job seekers, students).
Every name is checked with the database's own name rule (person_name_problem, 0038–0039) before it is used."""
import hashlib, random, re

from .safety import SIM_DOMAIN

M_AR = 'محمد أحمد محمود مصطفى عمرو كريم خالد طارق هشام شريف ياسر وائل أيمن حسام إسلام عمر يوسف إبراهيم حسن حسين سامح عادل ماجد رامي تامر باسم أسامة سيف زياد مينا جرجس بيشوي'.split()
F_AR = 'فاطمة مريم نورا سارة ياسمين هبة رانيا دينا منى إيمان شيماء آية نهى ريهام داليا هالة سلمى ملك رحاب أميرة نادية غادة لمياء مارينا كريستين'.split()
L_AR = ['عبد الله', 'الشريف', 'منصور', 'حسنين', 'السيد', 'عبد الرحمن', 'فهمي', 'رضوان', 'الجمال', 'زكي', 'عثمان', 'سليمان', 'البنا', 'النجار',
        'عبد العزيز', 'المصري', 'شاهين', 'رشدي', 'فوزي', 'صبري', 'حمدي', 'عزت', 'الدسوقي', 'جاد', 'حنا', 'عبد الملاك', 'القاضي', 'سالم']
M_EN = 'Mohamed Ahmed Mahmoud Mostafa Amr Karim Khaled Tarek Hesham Sherif Yasser Wael Ayman Hossam Eslam Omar Youssef Ibrahim Hassan Hussein Sameh Adel Maged Ramy Tamer Bassem Osama Seif Ziad Mina Girgis Bishoy'.split()
F_EN = 'Fatma Mariam Nora Sara Yasmine Heba Rania Dina Mona Eman Shaimaa Aya Noha Reham Dalia Hala Salma Malak Rehab Amira Nadia Ghada Lamiaa Marina Christine'.split()
L_EN = ['Abdallah', 'El-Sherif', 'Mansour', 'Hassanein', 'El-Sayed', 'Abdelrahman', 'Fahmy', 'Radwan', 'El-Gamal', 'Zaki', 'Osman', 'Soliman', 'El-Banna',
        'El-Naggar', 'Abdelaziz', 'El-Masry', 'Shahin', 'Roshdy', 'Fawzy', 'Sabry', 'Hamdy', 'Ezzat', 'El-Desouky', 'Gad', 'Hanna', 'Abdelmalak', 'El-Kady', 'Salem']
GULF = [('Faisal', 'Al-Otaibi', 'SA'), ('Abdulaziz', 'Al-Qahtani', 'SA'), ('Noura', 'Al-Harbi', 'SA'), ('Lina', 'Haddad', 'JO'), ('Rami', 'Khoury', 'JO'),
        ('Hamad', 'Al-Mansoori', 'AE'), ('Mariam', 'Al-Suwaidi', 'AE'), ('Yousef', 'Al-Sabah', 'KW'), ('Rasha', 'Nasser', 'LB'), ('Tariq', 'Al-Hashimi', 'IQ')]
T_AR = {'Dr': 'د.', 'Eng': 'م.', 'Ph': 'د/'}
CITIES = [('Cairo', 'Cairo', 'القاهرة'), ('Giza', 'Giza', 'الجيزة'), ('Alexandria', 'Alexandria', 'الإسكندرية'), ('6th of October City', 'Giza', 'السادس من أكتوبر'),
          ('10th of Ramadan City', 'Sharqia', 'العاشر من رمضان'), ('Sadat City', 'Menoufia', 'مدينة السادات'), ('Badr City', 'Cairo', 'مدينة بدر'),
          ('Obour City', 'Qalyubia', 'العبور'), ('Mansoura', 'Dakahlia', 'المنصورة'), ('Tanta', 'Gharbia', 'طنطا'), ('Assiut', 'Assiut', 'أسيوط'),
          ('Borg El Arab', 'Alexandria', 'برج العرب'), ('Zagazig', 'Sharqia', 'الزقازيق'), ('New Cairo', 'Cairo', 'القاهرة الجديدة')]
GCC_CITY = {'SA': 'Riyadh', 'JO': 'Amman', 'AE': 'Dubai', 'KW': 'Kuwait City', 'LB': 'Beirut', 'IQ': 'Baghdad'}
ROLES = [  # (headline, archetype weights: social, trade, hire, seek, learn, group), share
    ('QA Manager', dict(social=3, trade=1, hire=1, seek=1, learn=3, group=2), 8), ('QC Analyst', dict(social=2, seek=3, learn=4, group=2), 8),
    ('Regulatory Affairs Specialist', dict(social=3, trade=1, learn=4, group=3), 8), ('Production Manager', dict(social=2, trade=2, hire=2, learn=2, group=1), 6),
    ('Medical Representative', dict(social=4, seek=3, learn=2, group=2), 10), ('Sales Manager', dict(social=3, trade=4, hire=1, group=2), 8),
    ('Procurement Manager', dict(social=2, trade=5, group=2), 6), ('Business Development Manager', dict(social=3, trade=5, group=3), 6),
    ('Community Pharmacist', dict(social=4, trade=1, seek=2, learn=3, group=3), 10), ('Hospital Pharmacist', dict(social=3, seek=2, learn=4, group=2), 5),
    ('R&D Formulation Scientist', dict(social=2, learn=4, seek=2, group=2), 5), ('Supply Chain Manager', dict(social=2, trade=4, group=1), 5),
    ('HR Manager', dict(social=2, hire=6, group=1), 3), ('Pharmacovigilance Officer', dict(social=2, learn=4, seek=2, group=2), 3),
    ('Pharmacy Student', dict(social=4, seek=4, learn=5, group=3), 4), ('Regulatory Consultant', dict(social=3, trade=3, learn=2, group=3), 3)]
CO_PREFIX = 'Nile Delta Pyramids Sinai Pharos Memphis Horus Lotus Misr Sphinx Amoun Medica October Ramadan Obour Badr Karnak Aswan Siwa Thebes Luxor Philae Abydos Edfu Rosetta Canopus Fayoum Dahab Taba Matrouh'.split()
CO_TYPES = [('Manufacturer', 'Pharma Industries', 'Manufacturer', 30), ('Distributor', 'Distribution', 'Distributor', 20),
            ('CMO', 'Contract Manufacturing', 'CMO / Toll', 12), ('Pharmacy', 'Pharmacies', 'Pharmacy', 14),
            ('Supplier', 'Chemicals', 'API Supplier', 10), ('Supplier', 'Packaging', 'Packaging', 6), ('Consultant', 'Regulatory Consulting', 'Consultancy', 8)]
APIS = ['Paracetamol', 'Metformin HCl', 'Amoxicillin trihydrate', 'Omeprazole pellets 8.5%', 'Atorvastatin calcium', 'Ibuprofen', 'Azithromycin dihydrate',
        'Ascorbic acid', 'Diclofenac sodium', 'Ceftriaxone sodium sterile', 'Microcrystalline cellulose PH102', 'Magnesium stearate', 'HPMC capsules size 0',
        'Alu-Alu blister foil', 'PVC/PVDC film 250 micron', 'Amber glass bottles 100 ml', 'Pantoprazole sodium', 'Esomeprazole magnesium', 'Clopidogrel bisulfate',
        'Sitagliptin phosphate', 'Vitamin D3 100,000 IU/g', 'Ferrous bisglycinate', 'Cetirizine HCl', 'Levofloxacin hemihydrate']
FORMS = ['tablets', 'capsules', 'syrup', 'sachets', 'injection', 'cream', 'eye drops', 'effervescent tablets']
INTERESTS = ['GMP', 'EDA registration', 'stability', 'pharmacovigilance', 'tenders', 'export to GCC', 'contract manufacturing', 'cold chain', 'cosmetics',
             'nutraceuticals', 'biosimilars', 'digital pharmacy', 'serialization', 'validation', 'bioequivalence', 'pricing']
SKILLS = ['GMP', 'HPLC', 'CAPA', 'Validation', 'CTD dossiers', 'EDA submissions', 'Negotiation', 'Tendering', 'Key account management', 'ISO 9001',
          'Pharmacovigilance', 'Formulation', 'Dissolution testing', 'Supply planning', 'SAP', 'Clinical pharmacy', 'Inventory control', 'Team leadership']
UNIS = ['Cairo University', 'Ain Shams University', 'Alexandria University', 'Mansoura University', 'Tanta University', 'Assiut University',
        'Zagazig University', 'Future University in Egypt', 'MSA University', 'German University in Cairo', 'British University in Egypt']


def _rng(seed, *k): return random.Random(hashlib.sha256(('%s:' % seed + ':'.join(map(str, k))).encode()).digest())


def _wpick(r, items, wkey=lambda x: x[-1]): return r.choices(items, weights=[wkey(x) for x in items], k=1)[0]


def slugify(s): return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')


def make_name(r, attempt=0):
    """(display name, script, gender). Arabic or Latin script, an optional title, first + father + family or first + family."""
    gulf = r.random() < 0.08
    female = r.random() < 0.45
    if gulf:
        g = r.choice(GULF); first, fam = g[0], g[1]; female = first in ('Noura', 'Lina', 'Mariam', 'Rasha')
        title = r.choice(['', '', 'Dr. ', 'Eng. '])
        return (title + first + ' ' + fam).strip(), 'en', female, g[2]
    arabic = r.random() < 0.45
    title = _wpick(r, [('', 55), ('Dr', 30), ('Eng', 6), ('Ph', 9)], lambda x: x[1])[0]
    i = r.randrange(len(F_AR if female else M_AR)); j = r.randrange(len(M_AR)); k = r.randrange(len(L_AR))
    three = r.random() < 0.5
    if arabic:
        parts = [(F_AR if female else M_AR)[i]] + ([M_AR[j]] if three else []) + [L_AR[k]]
        t = T_AR.get(title, '')
        return ((t + ' ') if t else '') + ' '.join(parts), 'ar', female, 'EG'
    parts = [(F_EN if female else M_EN)[i]] + ([M_EN[j]] if three else []) + [L_EN[k]]
    t = {'Dr': 'Dr.', 'Eng': 'Eng.', 'Ph': 'Ph/'}.get(title, '')
    return ((t + ' ') if t else '') + ' '.join(parts), 'en', female, 'EG'


def person(seed, i):
    r = _rng(seed, 'p', i)
    name, script, female, country = make_name(r)
    role = _wpick(r, ROLES)
    city = r.choice(CITIES) if country == 'EG' else (GCC_CITY[country], '', '')
    start = r.choice([7, 8, 8, 9, 9, 9, 10, 10, 11, 12, 14, 17]); length = r.choice([6, 8, 9, 10, 12, 14])
    # most activity on a working day; some people are heavy users, most are light (a long tail)
    intensity = round(min(80.0, r.lognormvariate(2.3, 0.7)), 1)
    roll = r.random()
    kind = 'owner' if roll < 0.13 else 'employee' if roll < 0.68 else 'independent'
    if role[0] == 'Pharmacy Student': kind = 'independent'
    slug = slugify(re.sub(r'^(Dr|Eng|Ph)[./]\s*', '', name)) if script == 'en' else 'member'
    email = '%s.%04d@%s' % (slug or 'member', i, SIM_DOMAIN)
    pw = 'Sim-' + hashlib.sha256(('%s:pw:%d' % (seed, i)).encode()).hexdigest()[:20]
    yrs = 0 if role[0] == 'Pharmacy Student' else r.randint(1, 28)
    exp = [] if not yrs else [{'title': role[0], 'company': None, 'from': 2026 - min(yrs, r.randint(1, 6)), 'to': None}]
    return {
        'i': i, 'email': email, 'password': pw, 'name': name, 'script': script, 'lang': 'ar' if script == 'ar' or r.random() < 0.25 else 'en',
        'female': female, 'country': country, 'city': city[0], 'governorate': city[1], 'headline': role[0], 'arch': role[1],
        'kind': kind, 'company': None, 'company_role': None, 'hours': [start, min(24, start + length)], 'intensity': intensity,
        'interests': r.sample(INTERESTS, 3), 'skills': r.sample(SKILLS, r.randint(3, 6)), 'years': yrs, 'experience': exp,
        'education': [{'school': r.choice(UNIS), 'degree': 'B.Sc. Pharmaceutical Sciences' if r.random() < 0.8 else 'B.Sc. Chemistry', 'year': 2026 - yrs - 1}],
        'open_to_work': kind != 'owner' and r.random() < (0.5 if role[0] in ('Pharmacy Student', 'QC Analyst', 'Medical Representative') else 0.15),
        'ui_width': 390 if r.random() < 0.55 else 1440,
    }


def company(seed, i, owner):
    r = _rng(seed, 'c', i)
    t = _wpick(r, CO_TYPES)
    pre = r.choice(CO_PREFIX); name = '%s %s' % (pre, t[1])
    name = ('%s %s' % (name, r.choice(['', 'Egypt', 'Co.', 'Group', 'S.A.E.']))).strip()
    city = r.choice(CITIES)
    prods = r.sample(APIS, r.randint(2, 5))
    return {'i': i, 'owner': owner['i'], 'name': name, 'slug': slugify(name) + '-%d' % i, 'type': t[0], 'sector': t[2], 'sectors': [t[2]],
            'city': city[0], 'governorate': city[1], 'tagline': {'Manufacturer': 'GMP-certified oral solids and liquids',
            'Distributor': 'Nationwide pharma distribution, cold chain included', 'CMO': 'Toll manufacturing with free capacity this quarter',
            'Pharmacy': 'Community pharmacies in %s' % city[0], 'Supplier': 'APIs, excipients and packaging with CoA and DMF',
            'Consultant': 'EDA registration and GMP readiness'}[t[0]], 'products': prods,
            'phone': '+20 1%d %03d %04d' % (r.choice([0, 1, 2, 5]), r.randrange(1000), r.randrange(10000))}


def build(seed, n, db=None):
    """People 0..n-1 and their companies. With db, every name is checked by the database rule (regenerated on refusal)."""
    people, companies, refused = [], [], []
    for i in range(n):
        p = person(seed, i)
        if db is not None:
            tries = 0
            while (db.val('select coalesce(public.person_name_problem(public.person_name_norm(%s)), \'\')', (p['name'],)) or '') != '':
                refused.append(p['name']); tries += 1
                p['name'] = make_name(_rng(seed, 'p', i, 'retry', tries))[0]
                if tries > 20: raise RuntimeError('no valid name for person %d' % i)
        people.append(p)
    owners = [p for p in people if p['kind'] == 'owner']
    for p in owners:
        c = company(seed, p['i'], p); companies.append(c); p['company'] = c['slug']; p['company_role'] = 'owner'
    for p in people:
        if p['kind'] != 'employee': continue
        earlier = [c for c in companies if c['owner'] < p['i']]
        if not earlier: p['kind'] = 'independent'; continue
        c = _rng(seed, 'emp', p['i']).choice(earlier); p['company'] = c['slug']
        p['company_role'] = {'Sales Manager': 'sales', 'QA Manager': 'quality', 'QC Analyst': 'quality', 'Regulatory Affairs Specialist': 'regulatory',
                             'Procurement Manager': 'procurement', 'HR Manager': 'admin'}.get(p['headline'], 'member')
    for p in people:
        p['company_name'] = next((c['name'] for c in companies if c['slug'] == p['company']), None)
    return people, companies, refused


ADMIN = {'i': -1, 'email': 'sim-admin@' + SIM_DOMAIN, 'name': 'Sim Moderator', 'headline': 'Drugbox moderation (simulated)', 'kind': 'admin',
         'lang': 'en', 'hours': [8, 22], 'intensity': 30.0, 'arch': {}, 'company': None, 'company_role': None, 'city': 'Cairo', 'country': 'EG'}
