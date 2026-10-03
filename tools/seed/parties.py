"""Party master: classify the free-text party column, cluster spelling variants, infer kinds and account owners.

Generic rules only (no names live in this code). Decisions that cannot be derived safely from the text alone come
from an OPTIONAL private overrides file (default <private>/config/party_overrides.json):
    {"merge":    [["raw a", "raw b", ...], ...],      # force these spellings into one party
     "separate": [["raw a", "raw b"], ...],           # never merge these two spellings (cannot-link between clusters)
     "kinds":    {"raw": "supplier", ...},            # force a party kind (any raw of the cluster)
     "null_parties":  ["raw", ...],                   # strings that are not a party (role words, document types): no party
     "group_parties": ["raw", ...],                   # strings that name a group of people: kind 'group'
     "owners":   {"2310": "raw spelling", ...}}       # force the owner party of an account
Spec rule: auto-merge only the SAFE clusters; identity-bearing look-alikes stay separate and are flagged for review.
"""
import re
from collections import Counter, defaultdict

from common import clean, norm_text

PARTY_KINDS = ('shareholder', 'financier', 'supplier', 'employee', 'government', 'bank', 'customer', 'professional',
               'group', 'other')

# Generic vocabulary (not names): strings that carry no identity. Data-specific strings of one workbook (a role-only word,
# a document type typed in the party column, a staff group) belong to the private overrides file, never to this code.
PLACEHOLDERS = {'', '—', '-', '–', 'عام', 'غير محدد', 'غير معروف', 'مورد', 'موردون', 'الموردون'}
TRADE_WORDS = {'مقاول', 'سباك', 'حداد', 'نقاش', 'فني تكييف', 'فني', 'كهربائي', 'عمالة يومية', 'عمالة'}
TRADE_PREFIXES = ('مورد ',)          # "مورد <goods>" describes a supplier, it is not a name
GROUP_WORDS = {'المساهمون', 'المساهمين', 'الشركاء', 'العاملون', 'العاملين', 'عملاء', 'العملاء'}
GROUP_PREFIXES = ('عملاء ',)

_HONORIFIC_PREFIX = re.compile(r'^\s*(?:د|أ|ا|ك|م)\s*[/.]\s*')
_HONORIFIC_CANON = {'د': 'dr', 'دكتور': 'dr', 'الدكتور': 'dr', 'دكتوره': 'dr', 'الدكتوره': 'dr',
                    'ك': 'capt', 'كابتن': 'capt', 'الكابتن': 'capt',
                    'ا': 'mr', 'استاذ': 'mr', 'الاستاذ': 'mr', 'استاذه': 'mr', 'الاستاذه': 'mr', 'السيد': 'mr',
                    'السيده': 'mr', 'م': 'eng', 'مهندس': 'eng', 'المهندس': 'eng', 'الحاج': 'haj', 'حاج': 'haj'}
_ORG_WORDS = {'بنك', 'شركه'}
_ROLE_SUFFIX = {'المحامي', 'المحاميه', 'المحاسب', 'المحاسبه', 'القانوني'}
_STOP_TOKENS = {'و', 'بن', 'ابن'}
COMMON_TOKEN_CLUSTERS = 3   # a token seen in this many clusters (or more) is too common to prove a look-alike


def classify(raw, extra_null=(), extra_group=()):
    """-> 'placeholder' | 'trade' | 'group' | 'party'  (extra_* come from the private overrides file)"""
    t = clean(raw)
    if t in PLACEHOLDERS:
        return 'placeholder'
    if t in TRADE_WORDS or t in extra_null or any(t.startswith(p) for p in TRADE_PREFIXES):
        return 'trade'
    if t in GROUP_WORDS or t in extra_group or any(t.startswith(p) for p in GROUP_PREFIXES):
        return 'group'
    return 'party'


def _tokens(raw):
    s = clean(raw)
    s = re.sub(r'[\(（][^\)）]*[\)）]', ' ', s)           # qualifiers such as (قيد الاستفسار)
    honorific = ''
    m = _HONORIFIC_PREFIX.match(s)
    if m:
        honorific = _HONORIFIC_CANON.get(norm_text(m.group(0)).strip(' /.'), '')
        s = s[m.end():]
    s = norm_text(s.replace('—', ' ').replace('–', ' '))
    toks = [t for t in re.split(r'[\s/،,.\-]+', s) if t]
    if toks and not honorific and toks[0] in _HONORIFIC_CANON and len(toks) > 1:
        honorific = _HONORIFIC_CANON[toks[0]]
    toks = [t for t in toks if t not in _HONORIFIC_CANON and t not in _STOP_TOKENS
            and t not in _ORG_WORDS and t not in _ROLE_SUFFIX]
    joined, i = [], 0
    while i < len(toks):                                  # "عبد الفتاح" == "عبدالفتاح"
        if toks[i] == 'عبد' and i + 1 < len(toks):
            joined.append('عبد' + toks[i + 1])
            i += 2
        else:
            joined.append(toks[i])
            i += 1
    final = []
    for t in joined:                                      # drop the definite article
        if t.startswith('عبدال') and len(t) > 7:
            t = 'عبد' + t[5:]
        elif t.startswith('ال') and len(t) > 4 and not t.startswith('عبد'):
            t = t[2:]
        final.append(t)
    return tuple(final), honorific


def key_tokens(raw):
    """Normalised identity key of a spelling: tokens without honorifics, qualifiers, org words and articles."""
    return _tokens(raw)[0]


def honorific_of(raw):
    return _tokens(raw)[1]


def _is_subsequence(a, b):
    it = iter(b)
    return all(t in it for t in a)


class _UF:
    def __init__(self, items):
        self.p = {i: i for i in items}

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra

    def members(self, x):
        r = self.find(x)
        return [i for i in self.p if self.find(i) == r]


def cluster_parties(raw_stats, overrides=None):
    """raw_stats: {raw: {...}} for raws classified 'party'. Returns (clusters, review).
    clusters: list of {'raws': [...], 'confidence': 'high'|'medium'|'override'|'single'} (deterministic order)
    review:   {raw: {'confidence', 'identity_sensitive'}}"""
    overrides = overrides or {}
    raws = sorted(raw_stats)
    keys = {r: key_tokens(r) for r in raws}
    hon = {r: honorific_of(r) for r in raws}
    uf = _UF(raws)
    cannot = [tuple(p) for p in overrides.get('separate', []) if len(p) == 2 and all(x in raw_stats for x in p)]
    accepted = []   # (ra, rb, confidence)

    def blocked(ra, rb):
        ma, mb = set(uf.members(ra)), set(uf.members(rb))
        return any((x in ma and y in mb) or (y in ma and x in mb) for x, y in cannot)

    def try_merge(ra, rb, conf):
        if uf.find(ra) == uf.find(rb):
            accepted.append((ra, rb, conf))
            return
        if blocked(ra, rb):
            return
        uf.union(ra, rb)
        accepted.append((ra, rb, conf))

    # rule 1 (high): identical key after normalisation
    by_key = defaultdict(list)
    for r in raws:
        if keys[r]:
            by_key[keys[r]].append(r)
    for rs in by_key.values():
        for other in rs[1:]:
            try_merge(rs[0], other, 'high')
    # rule 2 (medium): >= 2 tokens, one key is a subsequence of the other, same first token, same honorific
    for i, ra in enumerate(raws):
        for rb in raws[i + 1:]:
            ka, kb = keys[ra], keys[rb]
            if not ka or not kb or ka == kb or hon[ra] != hon[rb]:
                continue
            short, long_ = (ka, kb) if len(ka) <= len(kb) else (kb, ka)
            if len(short) >= 2 and short[0] == long_[0] and _is_subsequence(short, long_):
                try_merge(ra, rb, 'medium')
    # forced merges from the private overrides
    for grp in overrides.get('merge', []):
        grp = [g for g in grp if g in raw_stats]
        for other in grp[1:]:
            try_merge(grp[0], other, 'override')

    rank = {'high': 3, 'medium': 2, 'override': 1}
    groups = defaultdict(list)
    for r in raws:
        groups[uf.find(r)].append(r)
    clusters = []
    for root, rs in sorted(groups.items(), key=lambda kv: min(kv[1])):
        rs = sorted(rs)
        confs = [c for a, b, c in accepted if uf.find(a) == root and a != b]
        conf = 'single' if len(rs) == 1 else min(confs, key=lambda c: rank[c]) if confs else 'single'
        clusters.append({'raws': rs, 'confidence': conf})
    cluster_of = {r: i for i, c in enumerate(clusters) for r in c['raws']}

    # identity-sensitive look-alikes: different clusters where one key contains the other, or that share a rare token
    token_clusters = defaultdict(set)
    for ci, c in enumerate(clusters):
        for r in c['raws']:
            for t in keys[r]:
                token_clusters[t].add(ci)
    sensitive = set()
    for ci, ca in enumerate(clusters):
        for cj in range(ci + 1, len(clusters)):
            cb = clusters[cj]
            hit = False
            for ra in ca['raws']:
                for rb in cb['raws']:
                    ka, kb = set(keys[ra]), set(keys[rb])
                    if not ka or not kb:
                        continue
                    shared = ka & kb
                    if not shared:
                        continue
                    if ka <= kb or kb <= ka:
                        hit = True
                    elif any(len(t) >= 3 and len(token_clusters[t]) < COMMON_TOKEN_CLUSTERS for t in shared):
                        hit = True
                    if hit:
                        break
                if hit:
                    break
            if hit:
                sensitive.update(ca['raws'])
                sensitive.update(cb['raws'])
    for x, y in cannot:
        sensitive.update((x, y))
    review = {r: {'confidence': clusters[cluster_of[r]]['confidence'], 'identity_sensitive': r in sensitive}
              for r in raws}
    return clusters, review


def pick_name(raws, raw_stats):
    """Display name of a cluster: the fullest spelling (most name tokens) without qualifiers; ties -> most used, longer."""
    def base(r):
        return clean(re.sub(r'[\(（][^\)）]*[\)）]', '', r))

    def score(r):
        return (-len(key_tokens(r)), -raw_stats[r]['lines'], -len(base(r)), base(r))
    return base(sorted(raws, key=score)[0])


# --------------------------------------------------------------------------- kinds
FUNDING_ACCOUNTS = ('2310', '2311', '2320', '2321', '2330', '2340')
SHAREHOLDER_PREFIX = '32'
PRO_WORDS = ('محامي', 'محاسب', 'مراجع')
SUPPLIER_ACCOUNTS = ('2110', '1270', '5250', '5260', '5240', '1130', '1131', '1140', '1150', '1180', '5130', '5420')


def infer_kind(raws, accts, group=False, forced=None):
    """Heuristic kind from the accounts a party is used on (Counter) and generic words in its spellings (editable later)."""
    if forced in PARTY_KINDS:
        return forced
    if group:
        return 'group'
    text = re.sub(r'(^| )ال', r'\1', ' '.join(norm_text(r) for r in raws))
    if any(a in FUNDING_ACCOUNTS for a in accts):
        return 'financier'
    if any(a.startswith(SHAREHOLDER_PREFIX) for a in accts):
        return 'shareholder'
    if 'بنك' in text.split():
        return 'bank'
    if any(a in ('2322', '2324') for a in accts):
        return 'employee'
    if any(w in text for w in PRO_WORDS) or any(a in ('5230', '5231') for a in accts):
        return 'professional'
    if any(a in ('4110', '4120', '4210', '1250') for a in accts):
        return 'customer'
    if any(a in SUPPLIER_ACCOUNTS for a in accts):
        return 'supplier'
    return 'other'


# --------------------------------------------------------------------------- account owners
def find_account_owner(account_name, clusters, cluster_keys, line_counts):
    """Owner cluster index of an account named after a person: the cluster with a spelling whose whole key appears in
    the account name (longest key wins, then most lines on the account). None when no cluster qualifies."""
    name_tokens = set(key_tokens(account_name)) | set(norm_text(account_name).replace('/', ' ').split())
    best, best_score = None, None
    for ci, c in enumerate(clusters):
        longest = 0
        for r in c['raws']:
            k = cluster_keys[r]
            if k and set(k) <= name_tokens:
                longest = max(longest, len(k))
        if not longest:
            continue
        score = (longest, line_counts.get(ci, 0), -ci)
        if best_score is None or score > best_score:
            best, best_score = ci, score
    return best
