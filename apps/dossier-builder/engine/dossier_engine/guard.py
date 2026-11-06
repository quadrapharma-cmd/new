"""Hard guard for read-only document classes (02-LOGIC §6, PLAN principle 3).

Third-party, EDA and executed documents are evidence: the engine refuses any
operation that changes their content. Only placement-level technical
operations are allowed. Every refusal is an audit event."""
from .checks.pdf import LOCKED

CONTENT_OPS = {'edit_text', 'redact', 'replace_page', 'retype', 'regenerate', 'change_image', 'translate_in_place',
               'remove_signature', 'flatten_annotations'}
TECH_OPS = {'rename', 'place', 'split_pages', 'merge_files', 'add_bookmarks', 'set_initial_view', 'linearise',
            'add_ocr_layer', 'remove_security', 'pdf_version_normalise'}
# executed records: scan placement only (02-LOGIC §6)
EXECUTED_OPS = {'rename', 'place', 'add_bookmarks'}


class LockedError(PermissionError):
    code = 'E-LOCKED'


def assert_allowed(doc_class, op, audit=None):
    if op not in CONTENT_OPS | TECH_OPS:
        raise ValueError(f'unknown operation {op!r}')
    allowed = True
    if doc_class in LOCKED:
        allowed = op in (EXECUTED_OPS if doc_class == 'executed_record' else TECH_OPS)
        if doc_class in ('third_party_certificate', 'eda_document') and op == 'remove_security':
            allowed = False          # security can only be removed by the issuer -> re-obtain
    if not allowed:
        if audit is not None:
            audit.append({'event': 'E-LOCKED', 'doc_class': doc_class, 'op': op})
        raise LockedError(f'E-LOCKED: {op} is not allowed on {doc_class} (read-only evidence). '
                          'Re-obtain the document from its issuer.')
    return True
