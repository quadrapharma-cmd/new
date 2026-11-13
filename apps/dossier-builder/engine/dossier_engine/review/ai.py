"""The AI assessor: a JSON-only prompt per section, answer parsing, suggestions that wait for human confirmation.
Browser edition: the page calls claude.ai's «sample» capability with this prompt. Server: the Anthropic SDK with a key."""
import json
import os
import time

MAX_CHARS = 90_000
SCHEMA = {'answers': [{'id': 'question id', 'verdict': 'adequate | deficient | not_assessable', 'finding_en': 'one or two sentences in the voice of a regulatory assessor',
                       'finding_ar': 'نفس الملاحظة بالعربية الفصحى', 'evidence': [{'doc': 'file name', 'page': 1, 'excerpt': 'verbatim text from that page (≤ 40 words)'}],
                       'confidence': 0.0}]}


def section_findings(findings, dept=None, ctd=None, ids=None):
    out = []
    for f in findings:
        if ids and f['id'] not in ids:
            continue
        if dept and f['dept'] != dept:
            continue
        if ctd and not (f['ctd'] == ctd or f['ctd'].startswith(ctd)):
            continue
        if f['question_id'].startswith('MISSING-') or f['question_id'].startswith('TECH-'):
            continue
        out.append(f)
    return out


def documents_for(findings, board):
    """Documents the questions point at: [{doc_id, filename, slot_id, ctd}] (deduplicated)."""
    want = set()
    for f in findings:
        want.update(f['payload'].get('slots') or [])
    seen, out = set(), []
    for s in board['slots']:
        if s['req_id'] in want or s['slot_id'] in want:
            for d in s['documents']:
                if d['id'] in seen or d['meta'].get('external'):
                    continue
                seen.add(d['id'])
                out.append({'doc_id': d['id'], 'filename': d['filename'], 'slot_id': s['slot_id'], 'ctd': s['ctd'], 'sha256': d['sha256']})
    return out


def build_prompt(findings, texts, lang='en'):
    """texts: [{filename, pages:[{page, text}], scanned}] — scanned documents come as images in the browser edition."""
    qs = [{'id': f['id'], 'question_id': f['question_id'], 'ctd': f['ctd'], 'severity': f['severity'], 'question': f['payload']['question']['en'],
           'deficiency_if_missing': f['payload']['deficiency']['en'], 'source': (f['payload'].get('source') or {}).get('code', ''),
           'current_verdict': f['verdict']} for f in findings]
    head = ('You are a regulatory assessor at a medicines authority reviewing part of a CTD registration dossier the way the Egyptian Drug Authority '
            'and international (ICH/WHO/EMA/FDA) assessors do. Answer ONLY the questions listed, from the document text (and page images) provided. '
            'Never invent content: if the documents do not answer a question, say not_assessable. Quote evidence verbatim with its page. '
            'Write finding_en in the voice of an authority letter ("The applicant should …") and finding_ar in formal Arabic. '
            'Return ONLY a JSON object of this exact shape, no prose:\n' + json.dumps(SCHEMA, ensure_ascii=False) + '\n\nQUESTIONS:\n' + json.dumps(qs, ensure_ascii=False, indent=1))
    body, used = [], 0
    for t in texts:
        if t.get('scanned'):
            body.append(f"\n=== DOCUMENT: {t['filename']} (scanned — see the page images if provided; otherwise not_assessable) ===")
            continue
        body.append(f"\n=== DOCUMENT: {t['filename']} ===")
        for p in t.get('pages') or []:
            chunk = f"\n--- page {p['page']} ---\n{p['text']}"
            if used + len(chunk) > MAX_CHARS:
                body.append('\n[… truncated: the remaining pages were not sent …]')
                used = MAX_CHARS
                break
            body.append(chunk)
            used += len(chunk)
        if used >= MAX_CHARS:
            break
    return head + '\n\nDOCUMENTS:' + ''.join(body)


def parse_answers(text):
    if isinstance(text, dict):
        obj = text
    else:
        s = str(text)
        obj = json.loads(s[s.index('{'):s.rindex('}') + 1])
    out = {}
    for a in obj.get('answers') or []:
        if a.get('id') and a.get('verdict') in ('adequate', 'deficient', 'not_assessable'):
            out[a['id']] = {'verdict': a['verdict'], 'en': a.get('finding_en') or '', 'ar': a.get('finding_ar') or '',
                            'evidence': [e for e in (a.get('evidence') or []) if isinstance(e, dict)][:5], 'confidence': float(a.get('confidence') or 0)}
    return out


def verify_excerpts(answer, texts):
    """An excerpt that is not in the document text is flagged (the assessor must not quote what is not there)."""
    corpus = {t['filename']: ' '.join(p['text'] for p in t.get('pages') or []).lower() for t in texts}
    for e in answer.get('evidence') or []:
        ex = (e.get('excerpt') or '').lower().strip()
        doc = corpus.get(e.get('doc'), '')
        e['verified'] = bool(ex) and (ex[:60] in doc or ex in doc)
    return answer


def suggest(storage, st, finding, answer):
    payload = dict(finding['payload'])
    payload['ai'] = {**answer, 'at': time.time()}
    storage.update_finding(st, finding['id'], payload=payload)
    return storage.finding(st, finding['id'])


def confirm(storage, st, finding, by):
    ai = (finding['payload'] or {}).get('ai')
    if not ai:
        return finding
    payload = dict(finding['payload'])
    if ai.get('en'):
        payload['deficiency'] = {'en': ai['en'], 'ar': ai.get('ar') or ai['en']}
    payload['evidence'] = (payload.get('evidence') or []) + [{'doc': e.get('doc'), 'page': e.get('page'), 'excerpt': e.get('excerpt'), 'verified': e.get('verified')} for e in ai.get('evidence') or []]
    payload['detail'] = {'en': f"AI assessor reading confirmed by {by}.", 'ar': f"قراءة المُقيِّم الذكي أكّدها {by}."}
    payload['needs_review'] = False
    status = 'closed' if ai['verdict'] == 'adequate' else 'open'
    storage.update_finding(st, finding['id'], verdict=ai['verdict'], origin='ai', confidence=ai.get('confidence'), confirmed_by=by, confirmed_at=time.time(), payload=payload, status=status)
    return storage.finding(st, finding['id'])


def assess_server(prompt, pdf_pairs, key=None, model=None):
    """Server-side reading with the Anthropic SDK: the PDFs are attached as documents so scans are read too. The key: the one given
    (the Assistant's settings), else the environment's."""
    key = key or os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        raise RuntimeError('E-NO-AI')
    import base64
    import anthropic
    content = [{'type': 'document', 'title': name, 'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': base64.standard_b64encode(data).decode()}}
               for name, data in pdf_pairs if data[:4] == b'%PDF']
    content.append({'type': 'text', 'text': prompt})
    client = anthropic.Anthropic(api_key=key)
    with client.beta.messages.stream(model=model or 'claude-opus-5-5', max_tokens=16000, output_config={'effort': 'medium'},
                                     betas=['server-side-fallback-2026-07-01'], fallbacks='default', messages=[{'role': 'user', 'content': content}]) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == 'refusal':
        raise RuntimeError('E-AI-REFUSED')
    return ''.join(b.text for b in msg.content if b.type == 'text')
