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
    local_action: bool = False         # acts locally, not intended for systemic absorption
    aqueous_solution: bool = False     # simple aqueous solution (parenteral / oral / ophthalmic / otic)
    bcs_waiver: bool = False           # company claims a BCS-based biowaiver (class I/III data supplied)
    store_separate_from_factory: bool = False
    biological: bool = False
    biological_origin_materials: bool = False
    novel_excipient: bool = False
    apis: list = field(default_factory=list)   # list[Api]

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        d['apis'] = [a if isinstance(a, Api) else Api(**a) for a in d.get('apis', [])]
        return cls(**d)

    # ---- column of the NP.CAPP.065 matrix ----
    def column(self):
        """Returns (column, assumption_flag)."""
        if self.dossier_kind == 'innovator':
            return 'I', self.origin == 'local'   # local innovator not in the source matrix
        return ('G_IMP' if self.origin == 'imported' else 'G_LOC'), False

    def validate(self, today=None):
        today = today or date.today()
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
        if self.origin == 'local' and self.licence in ('imported', 'imported_bulk'):
            bad('P-CONTRA', 'A local product cannot have an imported / imported-bulk licence.',
                'المنتج المحلي لا يكون ترخيصه مستورد أو bulk مستورد.')
        if self.origin == 'imported' and self.licence in ('toll', 'f_toll'):
            bad('P-CONTRA', 'Toll manufacturing applies to local products only.',
                'التصنيع لدى الغير للمنتج المحلي فقط.')
        if self.route == 'rolling' and today >= ROLLING_CLOSES:
            bad('P-ROLLING-CLOSED', 'Rolling Submission closed on 01/12/2026; use One Submission.',
                'مسار Rolling اتقفل 01/12/2026؛ استخدم One Submission.')
        if self.biological:
            bad('P-UNSUPPORTED', 'Biological products are not supported in this version.',
                'المستحضرات البيولوجية غير مدعومة في الإصدار ده.')
        if p:
            raise ProfileError(p)
        return True

    def env(self):
        """Namespace exposed to rule-pack expressions."""
        col, _ = self.column()
        d = {k: v for k, v in asdict(self).items() if k != 'apis'}
        d['column'] = col
        d['api_options'] = sorted({a.option for a in self.apis})
        d['api_count'] = len(self.apis)
        d['biowaiver'] = self.biowaiver()
        return d

    def biowaiver(self):
        """Basis on which an in-vivo BE study is not required ('' = BE study required)."""
        if self.dossier_kind == 'innovator':
            return ''
        if self.admin_route in ('topical', 'ophthalmic', 'otic', 'nasal', 'rectal_vaginal') and self.local_action:
            return 'local_action'
        if self.aqueous_solution and self.admin_route in ('parenteral', 'oral', 'ophthalmic', 'otic'):
            return 'aqueous_solution'
        if self.bcs_waiver and self.admin_route == 'oral':
            return 'bcs'
        return ''
