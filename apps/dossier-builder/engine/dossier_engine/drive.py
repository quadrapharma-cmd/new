"""Google Drive as a document source: paste a folder (or file) link, list what is there, read the files into the program.

Three ways in, chosen by what the workspace has (drive.json, mode 600):
* a **service account** key (JSON from Google Cloud): the company shares its Drive folder with the account's e-mail once, and
  private folders become readable — the recommended way for a company (server editions only; a private key never goes to a browser);
* a **Google API key**: folders shared «anyone with the link» (works in the browser edition too: the Drive API answers CORS);
* nothing: public folders through Google's embedded folder view and the public download URL (server editions only).
Google-native files are exported (Docs → DOCX so they can be amended, Sheets/Slides → PDF). Everything is read-only."""
import asyncio
import json
import os
import re
import sys
import time
import urllib.parse
from . import officefiles as _of

FILE = 'drive.json'
SCOPE = 'https://www.googleapis.com/auth/drive.readonly'
API = 'https://www.googleapis.com/drive/v3/'
FOLDER = 'application/vnd.google-apps.folder'
EXPORT = {'application/vnd.google-apps.document': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
          'application/vnd.google-apps.spreadsheet': ('application/pdf', '.pdf'),
          'application/vnd.google-apps.presentation': ('application/pdf', '.pdf')}
USABLE = set(_of.MIME.values()) | {'text/rtf', 'text/xml'} | set(EXPORT)        # every type the engine reads, old formats and new
EXT_MIME = dict(_of.MIME)
_SYSTEM = re.compile(r'^(~\$|\.~lock\.|\._)|^(thumbs\.db|desktop\.ini|\.ds_store)$', re.I)        # lock files and system files are never documents
FIELDS = 'nextPageToken,files(id,name,mimeType,size,modifiedTime,md5Checksum)'
HTTP = None            # tests inject: (method, url, headers, data) -> (status, content_type, bytes) — sync or async


class DriveError(Exception):
    def __init__(self, status, code, en, ar):
        super().__init__(en)
        self.status, self.code, self.en, self.ar = status, code, en, ar


# ---------------- links
def parse_link(url):
    """→ {'kind': 'folder' | 'file', 'id', 'native': doc|sheet|slides|None} or None."""
    u = (url or '').strip()
    if not u:
        return None
    m = re.search(r'/drive/(?:u/\d+/)?folders/([A-Za-z0-9_-]{10,})', u)
    if m:
        return {'kind': 'folder', 'id': m.group(1), 'native': None}
    m = re.search(r'/file/d/([A-Za-z0-9_-]{10,})', u)
    if m:
        return {'kind': 'file', 'id': m.group(1), 'native': None}
    for kind, nat in (('document', 'doc'), ('spreadsheets', 'sheet'), ('presentation', 'slides')):
        m = re.search(r'/' + kind + r'/d/([A-Za-z0-9_-]{10,})', u)
        if m:
            return {'kind': 'file', 'id': m.group(1), 'native': nat}
    m = re.search(r'[?&]id=([A-Za-z0-9_-]{10,})', u)
    if m:
        return {'kind': 'folder' if 'folder' in u else 'file', 'id': m.group(1), 'native': None}
    if re.fullmatch(r'[A-Za-z0-9_-]{20,}', u):
        return {'kind': 'folder', 'id': u, 'native': None}
    return None


# ---------------- settings
def path(workspace):
    from pathlib import Path
    return Path(workspace) / FILE


def load(workspace):
    p = path(workspace)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            pass
    return {}


def save(workspace, api_key=None, service_account=None):
    d = load(workspace)
    if api_key is not None:
        if api_key == '':
            d.pop('api_key', None)
        else:
            d['api_key'] = api_key.strip()
    if service_account is not None:
        if service_account in ('', None, {}):
            d.pop('service_account', None)
        else:
            sa = json.loads(service_account) if isinstance(service_account, str) else dict(service_account)
            for k in ('client_email', 'private_key', 'token_uri'):
                if not sa.get(k):
                    raise DriveError(422, 'E-DRIVE-SA', f'The service account JSON lacks «{k}».', f'ملف حساب الخدمة ناقصه «{k}».')
            d['service_account'] = {k: sa[k] for k in ('client_email', 'private_key', 'token_uri', 'project_id') if k in sa}
    p = path(workspace)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return status(workspace)


def status(workspace):
    d = load(workspace)
    browser = sys.platform == 'emscripten'
    sa = d.get('service_account') or {}
    mode = 'service_account' if sa and not browser else 'api_key' if d.get('api_key') else 'public'
    key = d.get('api_key') or ''
    return {'mode': mode, 'browser': browser, 'configured': mode != 'public' or not browser, 'service_account_email': sa.get('client_email'),
            'api_key_hint': (key[:6] + '…' + key[-4:]) if len(key) > 12 else ('set' if key else ''),
            'can_private': bool(sa) and not browser, 'can_public': True if not browser else bool(d.get('api_key'))}


# ---------------- HTTP (server: urllib; browser: pyodide's fetch)
def _urllib(method, url, headers, data):
    import urllib.request
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.headers.get('content-type', ''), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('content-type', '') if e.headers else '', e.read() or b''


async def ahttp(method, url, headers=None, data=None):
    if HTTP is not None:
        r = HTTP(method, url, headers or {}, data)
        return (await r) if asyncio.iscoroutine(r) else r
    if sys.platform == 'emscripten':
        from pyodide.http import pyfetch
        kw = {'method': method, 'headers': headers or {}}
        if data is not None:
            kw['body'] = data
        r = await pyfetch(url, **kw)
        return r.status, r.headers.get('content-type', ''), await r.bytes()
    return await asyncio.to_thread(_urllib, method, url, headers or {}, data)


# ---------------- the client
class Drive:
    def __init__(self, settings, browser=None):
        self.s = settings or {}
        self.browser = sys.platform == 'emscripten' if browser is None else browser
        self._tok, self._exp = None, 0

    @property
    def mode(self):
        if self.s.get('service_account') and not self.browser:
            return 'service_account'
        return 'api_key' if self.s.get('api_key') else 'public'

    async def _token(self):
        if self._tok and time.time() < self._exp - 60:
            return self._tok
        sa = self.s['service_account']
        try:
            import jwt
        except ImportError:
            raise DriveError(501, 'E-DRIVE-LIB', 'Install pyjwt and cryptography for service-account access.', 'ثبّت pyjwt وcryptography لاستخدام حساب الخدمة.')
        now = int(time.time())
        assertion = jwt.encode({'iss': sa['client_email'], 'scope': SCOPE, 'aud': sa['token_uri'], 'iat': now, 'exp': now + 3600}, sa['private_key'], algorithm='RS256')
        body = urllib.parse.urlencode({'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer', 'assertion': assertion}).encode()
        st, ct, data = await ahttp('POST', sa['token_uri'], {'content-type': 'application/x-www-form-urlencoded'}, body)
        if st != 200:
            raise DriveError(502, 'E-DRIVE-AUTH', f'Google refused the service account ({st}).', f'جوجل رفض حساب الخدمة ({st}).')
        j = json.loads(data)
        self._tok, self._exp = j['access_token'], time.time() + int(j.get('expires_in', 3600))
        return self._tok

    async def _api(self, p, params=None, raw=False):
        params = dict(params or {})
        headers = {}
        if self.mode == 'service_account':
            headers['Authorization'] = 'Bearer ' + await self._token()
        elif self.mode == 'api_key':
            params['key'] = self.s['api_key']
        else:
            raise DriveError(501, 'E-DRIVE-KEY', 'Set a Google API key (public folders) or a service account (private folders) in the Drive settings.',
                             'سجّل مفتاح Google API (للفولدرات العامة) أو حساب خدمة (للفولدرات الخاصة) في إعدادات Drive.')
        url = API + p + ('?' + urllib.parse.urlencode(params) if params else '')
        st, ct, data = await ahttp('GET', url, headers)
        if st == 404:
            raise DriveError(404, 'E-DRIVE-404', 'Not found on Drive: check the link and that it is shared.', 'مش موجود على Drive: راجع اللينك والمشاركة.')
        if st in (401, 403):
            who = 'the service account ' + self.s['service_account'].get('client_email', '') if self.mode == 'service_account' else 'anyone with the link'
            raise DriveError(403, 'E-DRIVE-FORBIDDEN', f'Drive refused ({st}): share the folder with {who}.', f'Drive رفض ({st}): شارك الفولدر مع {who}.')
        if st != 200:
            raise DriveError(502, 'E-DRIVE', f'Drive answered {st}.', f'Drive رد بـ {st}.')
        return data if raw else json.loads(data)

    @staticmethod
    def _entry(f, prefix=''):
        mt = f.get('mimeType') or EXT_MIME.get(os.path.splitext(f.get('name', ''))[1].lower(), '')
        return {'id': f['id'], 'name': f.get('name', f['id']), 'mimeType': mt, 'size': int(f['size']) if str(f.get('size', '')).isdigit() else None,
                'modified': f.get('modifiedTime'), 'kind': 'folder' if mt == FOLDER else 'file',
                'usable': mt != FOLDER and not _SYSTEM.search(f.get('name', '')) and (mt in USABLE or os.path.splitext(f.get('name', ''))[1].lower() in EXT_MIME), 'path': prefix + f.get('name', f['id']),
                'export': EXPORT.get(mt, (None, None))[1]}

    async def list_folder(self, folder_id, recursive=False, _prefix='', _depth=0):
        """Entries of a folder (sub-folders first); recursive walks sub-folders (≤ 3 levels) with their path."""
        if self.mode == 'public':
            if self.browser:
                raise DriveError(501, 'E-DRIVE-KEY', 'The browser edition needs a Google API key for Drive folders.', 'نسخة المتصفح محتاجة مفتاح Google API لفولدرات Drive.')
            entries = await self._public_list(folder_id, _prefix)
        else:
            entries, token = [], None
            while True:
                params = {'q': f"'{folder_id}' in parents and trashed=false", 'fields': FIELDS, 'pageSize': 200, 'orderBy': 'folder,name',
                          'supportsAllDrives': 'true', 'includeItemsFromAllDrives': 'true'}
                if token:
                    params['pageToken'] = token
                j = await self._api('files', params)
                entries += [self._entry(f, _prefix) for f in j.get('files', [])]
                token = j.get('nextPageToken')
                if not token:
                    break
        if recursive and _depth < 3:
            out = []
            for e in entries:
                out.append(e)
                if e['kind'] == 'folder':
                    out += await self.list_folder(e['id'], True, e['path'] + '/', _depth + 1)
            return out
        return entries

    async def meta(self, file_id):
        if self.mode == 'public':
            return None
        j = await self._api(f'files/{file_id}', {'fields': 'id,name,mimeType,size,modifiedTime', 'supportsAllDrives': 'true'})
        return self._entry(j)

    async def fetch(self, file_id, name=None, mime=None):
        """→ (filename, bytes, media_type). Google-native files are exported; a .gdoc becomes .docx."""
        if not name or not mime:
            m = await self.meta(file_id)
            if m:
                name, mime = name or m['name'], mime or m['mimeType']
        if mime in EXPORT:
            target, ext = EXPORT[mime]
            if self.mode == 'public':
                data = await self._public_get({'application/vnd.google-apps.document': f'https://docs.google.com/document/d/{file_id}/export?format=docx',
                                               'application/vnd.google-apps.spreadsheet': f'https://docs.google.com/spreadsheets/d/{file_id}/export?format=pdf',
                                               'application/vnd.google-apps.presentation': f'https://docs.google.com/presentation/d/{file_id}/export/pdf'}[mime])
            else:
                data = await self._api(f'files/{file_id}/export', {'mimeType': target}, raw=True)
            fname = re.sub(r'\.[A-Za-z0-9]{1,5}$', '', name or file_id) + ext
            return fname, data, target
        if self.mode == 'public':
            data = await self._public_get(f'https://drive.google.com/uc?export=download&id={file_id}')
        else:
            data = await self._api(f'files/{file_id}', {'alt': 'media', 'supportsAllDrives': 'true'}, raw=True)
        fname = name or file_id
        return fname, data, mime or EXT_MIME.get(os.path.splitext(fname)[1].lower(), 'application/octet-stream')

    # ---------------- public folders without any key (server editions): Google's embedded folder view + public download URL
    async def _public_list(self, folder_id, prefix):
        st, ct, data = await ahttp('GET', f'https://drive.google.com/embeddedfolderview?id={folder_id}#list', {'user-agent': 'Mozilla/5.0'})
        if st != 200:
            raise DriveError(403 if st in (401, 403) else 502, 'E-DRIVE-PUBLIC', f'The folder is not public ({st}): share it «anyone with the link», or set a key.',
                             f'الفولدر مش عام ({st}): شاركه «أي شخص معه اللينك»، أو سجّل مفتاح.')
        html = data.decode('utf-8', 'replace')
        out = []
        for m in re.finditer(r'<div class="flip-entry(?: [^"]*)?" id="entry-([A-Za-z0-9_-]+)"(.*?)flip-entry-title">([^<]*)<', html, re.S):
            fid, body, title = m.group(1), m.group(2), m.group(3).strip()
            is_folder = 'folder' in body.lower()[:400] and '.' not in title[-6:]
            out.append(self._entry({'id': fid, 'name': title, 'mimeType': FOLDER if is_folder else EXT_MIME.get(os.path.splitext(title)[1].lower(), '')}, prefix))
        return out

    async def _public_get(self, url):
        st, ct, data = await ahttp('GET', url, {'user-agent': 'Mozilla/5.0'})
        if st == 200 and 'text/html' in ct and b'confirm=' in data:                 # the virus-scan interstitial of large files
            m = re.search(rb'confirm=([0-9A-Za-z_-]+)', data)
            if m:
                st, ct, data = await ahttp('GET', url + '&confirm=' + m.group(1).decode(), {'user-agent': 'Mozilla/5.0'})
        if st != 200 or ('text/html' in ct and data[:5] != b'%PDF'):
            raise DriveError(403 if st in (401, 403) else 502, 'E-DRIVE-PUBLIC', f'The file is not public ({st}).', f'الملف مش عام ({st}).')
        return data
