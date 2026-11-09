"""Templates and «make it for me»: GET /api/templates (per requirement: can the program draft it), GET /api/dossiers/{did}/slots/{slot}/template
(the template, the requirement's words, which base documents are present, the prompt), POST /api/dossiers/{did}/slots/{slot}/draft
(the draft as an unsigned Word version; body.answers = the model's JSON from the browser edition, else the server's model or the data)."""
from fastapi import HTTPException
from pydantic import BaseModel

from ..generate import draft as _draft


def err(status, code, en, ar, **extra):
    raise HTTPException(status, detail={'code': code, 'en': en, 'ar': ar, **extra})


class DraftReq(BaseModel):
    answers: dict | str | None = None            # the model's JSON, or its raw text (parsed here)
    lang: str | None = None
    ai: bool = True


def install(app, st):
    def _slot(did, slot_id, need_active=True):
        for s in st.slots(did):
            if s.slot_id == slot_id:
                if need_active and not s.active:
                    err(422, 'E-SLOT-INACTIVE', 'This item is not required for this product.', 'البند ده مش مطلوب للمنتج ده.')
                return s
        err(404, 'E-SLOT', 'Unknown item.', 'بند غير معروف.')

    def _req_item(did, req_id):
        pack = st.pack(st.dossier(did)['pack'])
        for r in (getattr(pack, 'requirements', None) or getattr(pack, 'reqs', None) or (pack.get('requirements') if isinstance(pack, dict) else None) or []):
            if isinstance(r, dict) and r.get('id') == req_id:
                return r
        try:
            import yaml
            for r in yaml.safe_load((_draft.PACK / 'requirements.yaml').read_text(encoding='utf-8')):
                if r['id'] == req_id:
                    return r
        except Exception:
            pass
        return {}

    @app.get('/api/templates')
    def templates():
        return _draft.summary()

    @app.get('/api/dossiers/{did}/slots/{slot_id:path}/template')
    def slot_template(did: str, slot_id: str):
        s = _slot(did, slot_id, need_active=False)                  # the template of any item can be looked at
        return _draft.view(st, did, s, _req_item(did, s.req_id))

    @app.post('/api/dossiers/{did}/slots/{slot_id:path}/fill')
    def slot_fill(did: str, slot_id: str, body: DraftReq):
        """The filled template without storing: the page shows it as the live document for editing, then saves with /draft."""
        s = _slot(did, slot_id)
        e = _draft.template(s.req_id)
        if not e or e['draft'] not in ('full', 'partial'):
            err(422, 'E-NOT-DRAFTABLE', 'This document is not drafted by the program.', 'المستند ده مش بيتعمل كمسودة.')
        try:
            answers = _draft.parse_answers(body.answers) if body.answers is not None else None
        except ValueError as ex:
            err(422, 'E-ANSWERS', str(ex), 'إجابات الموديل مش بالشكل المتوقع.')
        try:
            answers, how, _ctx = _draft.compute(st, did, s, answers=answers, use_ai=body.ai)
        except ValueError as ex:
            err(422, 'E-DRAFT', str(ex), 'ما قدرتش أملي النموذج.')
        except Exception as ex:
            err(502, 'E-DRAFT-AI', f'The template could not be filled: {ex}', f'النموذج ما اتملاش: {ex}')
        return {'answers': answers, 'how': how}

    @app.post('/api/dossiers/{did}/slots/{slot_id:path}/draft', status_code=201)
    def slot_draft(did: str, slot_id: str, body: DraftReq):
        s = _slot(did, slot_id)
        e = _draft.template(s.req_id)
        if not e or e['draft'] not in ('full', 'partial'):
            err(422, 'E-NOT-DRAFTABLE', 'This document is not drafted by the program: it is issued by a third party or made by a generator.',
                'المستند ده مش بيتعمل كمسودة: صادر من جهة خارجية أو بيتولّد بمولّد جاهز.')
        try:
            answers = _draft.parse_answers(body.answers) if body.answers is not None else None
        except ValueError as ex:
            err(422, 'E-ANSWERS', str(ex), 'إجابات الموديل مش بالشكل المتوقع.')
        try:
            return _draft.draft(st, did, s, answers=answers, lang=body.lang, use_ai=body.ai, req_item=_req_item(did, s.req_id))
        except ValueError as ex:
            err(422, 'E-DRAFT', str(ex), 'ما قدرتش أعمل المسودة.')
        except Exception as ex:                                   # the model or the network
            err(502, 'E-DRAFT-AI', f'The draft could not be made: {ex}', f'المسودة ما اتعملتش: {ex}')
