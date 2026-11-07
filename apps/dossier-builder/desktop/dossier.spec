# PyInstaller spec — run from the repository root:  pyinstaller apps/dossier-builder/desktop/dossier.spec
# The engine is shipped as source inside the bundle with the repository layout, so its relative paths keep working.
import os, sys
from PyInstaller.utils.hooks import collect_all

REPO = os.path.abspath(os.getcwd())
APP = os.path.join(REPO, 'apps', 'dossier-builder')

datas, binaries, hidden = [], [], []
for rel in ['apps/dossier-builder/engine/dossier_engine', 'apps/dossier-builder/rulepacks', 'apps/dossier-builder/ui',
            'docs/ctd/ectd/EG-PROVISIONAL-PROFILE-v0', 'docs/ctd/ectd/EG-PROVISIONAL-PROFILE-v4-v0']:
    datas.append((os.path.join(REPO, rel), rel))
datas.append((os.path.join(REPO, 'docs/ctd/sources/ectd/ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip'), 'docs/ctd/sources/ectd'))

# libraries the engine imports at run time (it is not analysed, so collect them explicitly)
for pkg in ['fastapi', 'starlette', 'uvicorn', 'pydantic', 'pydantic_core', 'anyio', 'h11', 'multipart', 'python_multipart',
            'yaml', 'jsonschema', 'jsonschema_specifications', 'referencing', 'rpds', 'docx', 'pypdf', 'lxml', 'PIL',
            'annotated_types', 'typing_extensions', 'idna', 'sniffio', 'click', 'attrs']:
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hidden += h
    except Exception:
        pass

a = Analysis([os.path.join(APP, 'desktop', 'launcher.py')], pathex=[], binaries=binaries, datas=datas,
             hiddenimports=hidden + ['tkinter', 'sqlite3', 'email.mime.multipart', 'xml.etree.ElementTree'],
             excludes=['ocrmypdf', 'matplotlib', 'numpy', 'pandas', 'pytest', 'playwright'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='DossierBuilder', console=(sys.platform == 'win32'),
          disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, name='DossierBuilder')
if sys.platform == 'darwin':
    app = BUNDLE(coll, name='DossierBuilder.app', bundle_identifier='eg.quadra.dossierbuilder',
                 info_plist={'CFBundleDisplayName': 'Dossier Builder', 'NSHighResolutionCapable': True})
