"""Hard guard for read-only document classes (02-LOGIC §6, PLAN principle 3).

Third-party, EDA and executed documents are evidence: the engine refuses any
operation that changes their content. Only placement-level technical
operations are allowed. Every refusal is an audit event."""
from .checks.pdf import LOCKED

CONTENT_OPS = {'edit_text', 'redact', 'replace_page', 'retype', 'regenerate', 'change_image', 'translate_in_place',
               'remove_signature', 'flatten_annotations', 'remove_pages', 'move_pages'}
TECH_OPS = {'rename', 'place', 'split_pages', 'merge_files', 'add_bookmarks', 'set_initial_view', 'linearise',
            'remove_security', 'pdf_version_normalise', 'remove_javascript', 'show_bookmarks', 'inherit_zoom', 'doc_info',
            'repair', 'remove_attachments', 'remove_comments', 'reduce_size', 'rotate_pages', 'make_searchable'}
# technical, but only the issuer may do them on evidence (they change how the document behaves, or what is in it)
COMPANY_ONLY = {'remove_security', 'remove_javascript', 'remove_attachments', 'remove_comments', 'reduce_size'}
# executed records: scan placement only (02-LOGIC §6); a damaged file's clean copy changes nothing on a page (it is compared page for page)
EXECUTED_OPS = {'rename', 'place', 'add_bookmarks', 'pdf_version_normalise', 'show_bookmarks', 'inherit_zoom', 'doc_info', 'repair',
                'rotate_pages', 'make_searchable'}            # an invisible text layer: the page itself is compared to look the same                       # a scan turned the right way up: placement, not content   # nothing on a page changes      # the version line alone (fixes.set_version_17: every other byte the same)


class LockedError(PermissionError):
    code = 'E-LOCKED'


def assert_allowed(doc_class, op, audit=None):
    if op not in CONTENT_OPS | TECH_OPS:
        raise ValueError(f'unknown operation {op!r}')
    allowed = True
    if doc_class in LOCKED:
        allowed = op in (EXECUTED_OPS if doc_class == 'executed_record' else TECH_OPS)
        if op in COMPANY_ONLY:
            allowed = False          # security / active content can only be removed by the issuer -> re-obtain
    if not allowed:
        if audit is not None:
            audit.append({'event': 'E-LOCKED', 'doc_class': doc_class, 'op': op})
        raise LockedError(f'E-LOCKED: {op} is not allowed on {doc_class} (read-only evidence). '
                          'Re-obtain the document from its issuer.')
    return True
