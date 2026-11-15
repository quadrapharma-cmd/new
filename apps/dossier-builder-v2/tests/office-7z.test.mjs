// Excel and PowerPoint files, old and new, and 7z archives: made here by LibreOffice and 7-Zip from made-up content, then read by the
// workshop's own readers (prep/office.js, prep/sevenz.js, prep/lzma.js) and compared with what was put in.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { xlsxText, xlsText, pptxText, pptText } from '../prep/office.js';
import { sevenz } from '../prep/sevenz.js';
import { readFiles } from '../prep/read.js';
import { kindOf } from '../agent/workspace.js';
import { zipOf } from '../workshop/zipw.js';

const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'db-office-'));
const has = cmd => spawnSync('sh', ['-c', `command -v ${cmd}`]).status === 0;
const soffice = (to, file) => execFileSync('soffice', ['--headless', `-env:UserInstallation=file://${TMP}/lo`, '--convert-to', to,
  ...(file.endsWith('.csv') ? ['--infilter=CSV:44,34,76,1,,1033'] : []), '--outdir', TMP, file], { stdio: 'pipe', timeout: 180000 });

const CSV = 'Batch,Test,Result,Date\nT-001,Assay,99.8,2024-03-12\nT-002,Assay,100.4,2024-06-30\nملخص,الثبات,12,2025-01-05\n';
const SHEET = '[stability]\nBatch | Test | Result | Date\nT-001 | Assay | 99.8 | 12/03/2024\nT-002 | Assay | 100.4 | 30/06/2024\nملخص | الثبات | 12 | 05/01/2025';
const FODP = `<?xml version="1.0" encoding="UTF-8"?>
<office:document xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" office:version="1.2" office:mimetype="application/vnd.oasis.opendocument.presentation"><office:body><office:presentation>
<draw:page draw:name="p1"><draw:frame svg:x="2cm" svg:y="2cm" svg:width="20cm" svg:height="4cm"><draw:text-box><text:p>Made-up Tablets 500 mg</text:p><text:p>Stability summary</text:p></draw:text-box></draw:frame></draw:page>
<draw:page draw:name="p2"><draw:frame svg:x="2cm" svg:y="2cm" svg:width="20cm" svg:height="4cm"><draw:text-box><text:p>Batch T-001: assay 99.8 %</text:p><text:p>ملخص الثبات</text:p></draw:text-box></draw:frame></draw:page>
</office:presentation></office:body></office:document>`;
const SLIDES = ['Made-up Tablets 500 mg\nStability summary', 'Batch T-001: assay 99.8 %\nملخص الثبات'];

test('Excel and PowerPoint, old and new, read as LibreOffice wrote them: sheets with their dates, slides in order', { timeout: 600000 }, async t => {
  if (!has('soffice')) { t.skip('LibreOffice is not on this machine'); return; }
  fs.writeFileSync(path.join(TMP, 'stability.csv'), CSV);
  fs.writeFileSync(path.join(TMP, 'slides.fodp'), FODP);
  soffice('xlsx:Calc MS Excel 2007 XML', path.join(TMP, 'stability.csv'));
  soffice('xls:MS Excel 97', path.join(TMP, 'stability.csv'));
  soffice('pptx:Impress MS PowerPoint 2007 XML', path.join(TMP, 'slides.fodp'));
  soffice('ppt:MS PowerPoint 97', path.join(TMP, 'slides.fodp'));
  const file = n => new Uint8Array(fs.readFileSync(path.join(TMP, n)));
  assert.deepEqual(['stability.xlsx', 'stability.xls', 'slides.pptx', 'slides.ppt'].map(n => kindOf(file(n))), ['xlsx', 'xls', 'pptx', 'ppt']);
  assert.equal((await xlsxText(file('stability.xlsx')))[0].text, SHEET);
  assert.equal(xlsText(file('stability.xls'))[0].text, SHEET);
  assert.deepEqual((await pptxText(file('slides.pptx'))).map(p => p.text), SLIDES);
  assert.deepEqual(pptText(file('slides.ppt')).map(p => p.text), SLIDES);
  // a workbook big enough for its strings to run over several records: the old format reads as the new
  const rows = ['Batch,Name,Value,Ratio'];
  for (let i = 0; i < 3000; i++) rows.push(`B-${String(i).padStart(5, '0')},${i % 3 ? `Made-up product number ${i} with a longer name to fill the table` : `مستحضر تجريبي رقم ${i}`},${i * 2},${(i / 7).toFixed(2)}`);
  fs.writeFileSync(path.join(TMP, 'big.csv'), rows.join('\n') + '\n');
  soffice('xlsx:Calc MS Excel 2007 XML', path.join(TMP, 'big.csv'));
  soffice('xls:MS Excel 97', path.join(TMP, 'big.csv'));
  const big = (await xlsxText(file('big.xlsx')))[0].text;
  assert.equal(big.split('\n').length, 3002);
  assert.equal(xlsText(file('big.xls'))[0].text, big);
});

test('7z archives as 7-Zip writes them: every method it uses for documents, solid or not; what it cannot open says why', { timeout: 600000 }, async t => {
  if (!has('7z')) { t.skip('7-Zip is not on this machine'); return; }
  const src = path.join(TMP, '7z-in');
  fs.mkdirSync(path.join(src, 'sub'), { recursive: true });
  const files = {
    'notes.txt': Buffer.from('Made-up stability notes: batch T-001 assay 99.8 %, 6 months 25 C / 60 % RH.\n'.repeat(400)),
    'شهادة.txt': Buffer.from('شهادة تحليل لمستحضر تجريبي — Made-up Tablets 500 mg\n'.repeat(50)),
    'noise.bin': Buffer.from(Array.from({ length: 200000 }, (_, i) => (i * 2654435761 >>> 13) & 255)),
    'sub/inner.txt': Buffer.from('inside a folder\n'),
    'empty.txt': Buffer.alloc(0),
    'big.dat': Buffer.concat(Array.from({ length: 50000 }, (_, i) => (i % 7 ? Buffer.from(`row ${String(i).padStart(8, '0')} made-up data line for lzma2 chunks..\n`) : Buffer.from(Array.from({ length: 64 }, (_, k) => (i * 31 + k * 97) & 255))))),
  };
  for (const [n, b] of Object.entries(files)) fs.writeFileSync(path.join(src, n), b);
  const make = (name, ...opts) => { execFileSync('7z', ['a', '-t7z', ...opts, path.join(TMP, name), '.'], { cwd: src, stdio: 'pipe' }); return new Uint8Array(fs.readFileSync(path.join(TMP, name))); };
  const same = (r, label) => {
    assert.deepEqual(r.skipped, [], label);
    assert.deepEqual(r.files.map(f => f.name).sort(), Object.keys(files).sort(), label);
    for (const f of r.files) assert.ok(Buffer.from(f.bytes).equals(files[f.name]), `${label}: ${f.name}`);
  };
  for (const [name, opts] of [['default.7z', []], ['lzma.7z', ['-m0=LZMA']], ['copy.7z', ['-m0=Copy', '-mhc=off']], ['bcj.7z', ['-m0=BCJ', '-m1=LZMA2']],
    ['delta.7z', ['-m0=Delta:4', '-m1=LZMA2']], ['nonsolid.7z', ['-ms=off']], ['ultra.7z', ['-mx9']]]) {
    const b = make(name, ...opts);
    assert.equal(kindOf(b), '7z');
    same(sevenz(b), name);
  }
  const ppmd = sevenz(make('ppmd.7z', '-m0=PPMd'));
  assert.ok(ppmd.skipped.length === 5 && ppmd.skipped.every(s => s.why === 'unsupported'), 'PPMd: the files are listed as not read, with why');
  const locked = sevenz(make('locked.7z', '-pSecret'));
  assert.ok(locked.skipped.every(s => s.why === 'password') && locked.skipped.length === 5);
  assert.throws(() => sevenz(make('hidden.7z', '-pSecret', '-mhe=on')), e => e.why === 'password');
  execFileSync('7z', ['a', '-t7z', '-v8k', path.join(TMP, 'part.7z'), '.'], { cwd: src, stdio: 'pipe' });            // one part of several
  assert.ok(fs.existsSync(path.join(TMP, 'part.7z.002')), 'the archive came in parts');
  assert.throws(() => sevenz(new Uint8Array(fs.readFileSync(path.join(TMP, 'part.7z.001')))), e => e.why === 'volume');
  // in the reading: a 7z holding a PDF-less dossier's Excel, PowerPoint and a ZIP, each read as what it is
  if (fs.existsSync(path.join(TMP, 'stability.xlsx'))) {
    const pack = path.join(TMP, 'pack');
    fs.mkdirSync(pack, { recursive: true });
    fs.copyFileSync(path.join(TMP, 'stability.xlsx'), path.join(pack, 'stability.xlsx'));
    fs.copyFileSync(path.join(TMP, 'slides.ppt'), path.join(pack, 'slides.ppt'));
    fs.writeFileSync(path.join(pack, 'inner.zip'), await zipOf([{ name: 'readme.txt', bytes: new TextEncoder().encode('Made-up readme inside a zip inside a 7z') }]));
    execFileSync('7z', ['a', '-t7z', path.join(TMP, 'dossier.7z'), '.'], { cwd: pack, stdio: 'pipe' });
    const read = await readFiles([{ name: 'dossier.7z', bytes: new Uint8Array(fs.readFileSync(path.join(TMP, 'dossier.7z'))) }], {});
    const by = Object.fromEntries(read.map(r => [r.name, r]));
    assert.equal(by['dossier.7z/stability.xlsx'].pages[0].text, SHEET);
    assert.deepEqual(by['dossier.7z/slides.ppt'].pages.map(p => p.text), SLIDES);
    assert.match(by['dossier.7z/inner.zip/readme.txt'].pages[0].text, /inside a zip inside a 7z/);
  }
});
