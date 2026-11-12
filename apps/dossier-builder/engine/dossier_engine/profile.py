"""Product profile: the facts that drive requirements (02-LOGIC §4)."""
from dataclasses import dataclass, field, asdict
from datetime import date

ENUMS = {
    'dossier_kind': {'innovator', 'generic'},
    'origin': {'local', 'imported'},
    'licence': {'own', 'toll', 'f_toll', 'under_licence', 'imported', 'imported_bulk'},
    'activity': {'new', 're_registration', 'renewal', 'variation', 'preliminary_reregistration'},
    'route': {'one_submission', 'rolling'},
    'reference_status': {'referenced', 'non_referenced'},
    'leaflet': {'english', 'non_english', 'pil_only'},
    'admin_route': {'oral', 'topical', 'parenteral', 'ophthalmic', 'otic', 'nasal', 'inhalation', 'rectal_vaginal', 'other'},
}
DOSAGE_SPECIFICS = {'coated', 'capsule_hard', 'pellets', 'premix', 'powder_inj_with_solvent',
                    'sterile', 'modified_release', 'inhalation'}
API_OPTIONS = {'CEP', 'DMF', 'PQ', 'FULL'}
ROLLING_CLOSES = date(2026, 12, 1)


class ProfileError(ValueError):
    def __init__(self, problems):
        self.problems = problems
        super().__init__('; '.join(p['en'] for p in problems))


@dataclass
class Api:
    name: str
    manufacturer: str
    option: str = 'FULL'

    @property
    def key(self):
        return f"{self.name}|{self.manufacturer}"


@dataclass
class Profile:
    dossier_kind: str = 'generic'
    origin: str = 'local'
    licence: str = 'own'
    activity: str = 'new'
    route: str = 'one_submission'
    reference_status: str = 'referenced'
    pharmacopoeial: bool = False
    dosage_specifics: list = field(default_factory=list)
    leaflet: str = 'english'
    admin_route: str = 'oral'          # route of administration (drives BE / biowaiver logic)
    local_action: bool = False         # acts locally (GL.CAPP.024 §3.13): equivalence by clinical/PD/in-vitro data, not PK BE
    aqueous_solution: bool = False     # simple aqueous solution (parenteral / oral / ophthalmic / otic)
    bcs_waiver: bool = False           # BCS biowaiver claimed (class I, III or II weak acid, IR oral — GL.CAPP.024 §4.5.1)
    store_separate_from_factory: bool = False
    biological: bool = False
    biological_origin_materials: bool = False
    novel_excipient: bool = False
    apis: list = field(default_factory=list)   # list[Api]
    extra: dict = field(default_factory=dict)  # the answers to the chosen authority's own questions (pack.yaml `questions`)

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        d['apis'] = [a if isinstance(a, Api) else Api(**a) for a in d.get('apis', [])]
        sp = d.get('dosage_specifics')
        if isinstance(sp, str):                          # «[]», «['coated']», «coated, sterile» from a model or a form: a list, never a character per value
            import re as _re
            d['dosage_specifics'] = [x for x in _re.split(r'[,\s]+', _re.sub(r'[\[\]\'"]', ' ', sp)) if x]
        elif isinstance(sp, (list, tuple)):
            d['dosage_specifics'] = [str(x).strip(" []'\"") for x in sp if str(x).strip(" []'\"")]
        return cls(**d)

    # ---- column of the NP.CAPP.065 matrix ----
    def column(self):
        """Returns (column, assumption_flag)."""
        if self.dossier_kind == 'innovator':
            return 'I', self.origin == 'local'   # local innovator not in the source matrix
        return ('G_IMP' if self.origin == 'imported' else 'G_LOC'), False

    def validate(self, today=None, pack=None):
        """`pack`: the authority the dossier is for. Egypt's own rules (the licence kinds, the rolling route) are checked for Egypt
        — and when no pack is given, as before."""
        today = today or date.today()
        egypt = pack is None or pack.egypt
        p = []

        def bad(code, en, ar):
            p.append({'code': code, 'en': en, 'ar': ar})

        for f, allowed in ENUMS.items():
            if getattr(self, f) not in allowed:
                bad('P-ENUM', f'{f}: {getattr(self, f)!r} is not one of {sorted(allowed)}',
                    f'قيمة غير مقبولة للحقل {f}')
        for s in self.dosage_specifics:
            if s not in DOSAGE_SPECIFICS:
                bad('P-ENUM', f'dosage_specifics: unknown {s!r}', f'صفة شكل صيدلي غير معروفة: {s}')
        if not self.apis:
            bad('P-NO-API', 'At least one API (name, manufacturer, option) is required.',
                'لازم مادة فعالة واحدة على الأقل (الاسم، المصنّع، طريقة التقديم).')
        seen = set()
        for a in self.apis:
            if a.option not in API_OPTIONS:
                bad('P-ENUM', f'API {a.name}: option {a.option!r} not in {sorted(API_OPTIONS)}',
                    f'طريقة تقديم غير مقبولة للمادة {a.name}')
            if a.key in seen:
                bad('P-DUP-API', f'API {a.name} / {a.manufacturer} is listed twice.',
                    f'المادة {a.name} من نفس المصنّع مكررة.')
            seen.add(a.key)
        for q in (pack.questions if pack is not None else []):
            v, allowed = self.extra.get(q['id'], q.get('default')), [o['id'] for o in q.get('options') or []]
            if allowed and v not in allowed:
                bad('P-ENUM', f"{q['id']}: {v!r} is not one of {allowed}", f"قيمة غير مقبولة للسؤال {q['id']}")
        if egypt and self.origin == 'local' and self.licence in ('imported', 'imported_bulk'):
            bad('P-CONTRA', 'A local product cannot have an imported / imported-bulk licence.',
                'المنتج المحلي لا يكون ترخيصه مستورد أو bulk مستورد.')
        if egypt and self.origin == 'imported' and self.licence in ('toll', 'f_toll'):
            bad('P-CONTRA', 'Toll manufacturing applies to local products only.',
                'التصنيع لدى الغير للمنتج المحلي فقط.')
        if egypt and self.route == 'rolling' and today >= ROLLING_CLOSES:
            bad('P-ROLLING-CLOSED', 'Rolling Submission closed on 01/12/2026; use One Submission.',
                'مسار Rolling اتقفل 01/12/2026؛ استخدم One Submission.')
        if self.biological:
            bad('P-UNSUPPORTED', 'Biological products are not supported in this version.',
                'المستحضرات البيولوجية غير مدعومة في الإصدار ده.')
        if p:
            raise ProfileError(p)
        return True

    def env(self, pack=None):
        """Namespace exposed to rule-pack expressions."""
        col, _ = self.column()
        d = {k: v for k, v in asdict(self).items() if k not in ('apis', 'extra')}
        for q in (pack.questions if pack is not None else []):          # the authority's own questions, each with its default
            d[q['id']] = self.extra.get(q['id'], q.get('default'))
        d['column'] = col
        d['api_options'] = sorted({a.option for a in self.apis})
        d['api_count'] = len(self.apis)
        d['biowaiver'] = self.biowaiver()
        d['local_equivalence'] = bool(self.local_action and not d['biowaiver'] and self.dossier_kind != 'innovator')
        return d

    def biowaiver(self):
        """Basis on which equivalence data are NOT required ('' = required).
        EDA GL.CAPP.024 v4/2026 §2.2 (p.25): aqueous solutions (parenteral, oral, otic/ophthalmic/nasal, topical,
        nebuliser), powders for reconstitution as a solution, gases. §4.5.1 (p.119-121): BCS class I, III and
        class II weak acids, immediate release, oral. §3.13 (p.111): a locally acting product that is NOT a solution
        is NOT exempt — equivalence data (clinical, pharmacodynamic, skin-PK or in-vitro) are still required."""
        if self.dossier_kind == 'innovator':
            return ''
        if self.aqueous_solution and self.admin_route in ('parenteral', 'oral', 'ophthalmic', 'otic', 'nasal', 'topical', 'inhalation'):
            return 'aqueous_solution'
        if self.bcs_waiver and self.admin_route == 'oral':
            return 'bcs'
        return ''
        if self.admin_route in ('topical', 'ophthalmic', 'otic', 'nasal', 'rectal_vaginal') and self.local_action:
            return 'local_action'
        if self.aqueous_solution and self.admin_route in ('parenteral', 'oral', 'ophthalmic', 'otic'):
            return 'aqueous_solution'
        if self.bcs_waiver and self.admin_route == 'oral':
            return 'bcs'
        return ''
