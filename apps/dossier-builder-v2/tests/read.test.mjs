// Part 2, «الفحص الأول للملف»: the files opened by the program itself — ZIP archives, Word files old and new (and, in
// tests/read-browser.test.mjs, scans and PDFs in a real browser). Every file here is made up; the old Word file is written from a
// made-up .docx by LibreOffice, and LibreOffice's own reading of it is the check.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import { entries, unzip, crc32 } from '../prep/zip.js';
import { cfb, docText, docxText, xmlText } from '../prep/office.js';
import { core as rar } from '../prep/rar.js';

const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'db-read-'));
const W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"';
const DOC_XML = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document ${W}><w:body>
<w:p><w:r><w:t>Finished Product Specification</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Product Name: </w:t></w:r><w:r><w:t>Testamin powder for oral solution</w:t></w:r></w:p>
<w:p><w:r><w:t>Review Date: 01/02/2025</w:t></w:r></w:p>
<w:p><w:pPr><w:bidi/></w:pPr><w:r><w:rPr><w:rtl/></w:rPr><w:t>الشركة المصنعة: شركة سيناء التجريبية</w:t></w:r></w:p>
<w:p><w:r><w:t>Removed:</w:t></w:r><w:del w:id="1" w:author="x"><w:r><w:delText>old words</w:delText></w:r></w:del><w:r><w:t xml:space="preserve"> kept words</w:t></w:r></w:p>
<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Test</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Acceptance criteria</w:t></w:r></w:p></w:tc></w:tr>
<w:tr><w:tc><w:p><w:r><w:t>Assay of ascorbic acid</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>90.0 – 110.0 %</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
<w:p><w:r><w:t>Page two: R&amp;D notes</w:t></w:r></w:p>
<w:sectPr><w:headerReference w:type="default" r:id="rIdH1"/></w:sectPr>
</w:body></w:document>`;
const HEADER_XML = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr ${W}><w:p><w:r><w:t>SINAI TEST INDUSTRIES</w:t></w:r></w:p></w:hdr>`;
const FILES = {
  '[Content_Types].xml': `<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/></Types>`,
  '_rels/.rels': `<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>`,
  'word/_rels/document.xml.rels': `<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rIdH1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/></Relationships>`,
  'word/document.xml': DOC_XML,
  'word/header1.xml': HEADER_XML,
};
const PAGE_ONE = ['SINAI TEST INDUSTRIES', 'Finished Product Specification', 'Product Name: Testamin powder for oral solution',
  'Review Date: 01/02/2025', 'الشركة المصنعة: شركة سيناء التجريبية', 'Removed: kept words', 'Test | Acceptance criteria',
  'Assay of ascorbic acid | 90.0 – 110.0 %'];

function made() {
  const dir = path.join(TMP, 'docx');
  for (const [name, text] of Object.entries(FILES)) { fs.mkdirSync(path.dirname(path.join(dir, name)), { recursive: true }); fs.writeFileSync(path.join(dir, name), text); }
  const docx = path.join(TMP, 'specification.docx');
  execFileSync('zip', ['-q', '-X', '-r', docx, '[Content_Types].xml', '_rels', 'word'], { cwd: dir });
  return docx;
}
const soffice = (args, cwd) => execFileSync('soffice', ['--headless', `-env:UserInstallation=file://${TMP}/lo-profile`, ...args], { cwd, stdio: 'pipe', timeout: 120000 });

test('a .docx: its header first, paragraphs as lines, a table\'s cells joined, deleted words left out, its page break kept', async () => {
  const pages = await docxText(new Uint8Array(fs.readFileSync(made())));
  assert.deepEqual(pages.map(p => p.n), [1, 2]);
  assert.deepEqual(pages[0].text.split('\n'), PAGE_ONE);
  assert.equal(pages[1].text, 'Page two: R&D notes');
  assert.equal(pages[0].by, 'word');
  assert.equal(xmlText('<w:p><w:r><w:t>a</w:t></w:r><w:r><w:tab/><w:t>b</w:t></w:r></w:p>'), 'a\tb\n');
});

test('a .doc (Word 97–2003) written by LibreOffice from the same .docx reads the same, and the same as LibreOffice reads it', async () => {
  const docx = made();
  soffice(['--convert-to', 'doc:MS Word 97', '--outdir', TMP, docx], TMP);
  const file = path.join(TMP, 'specification.doc');
  const bytes = new Uint8Array(fs.readFileSync(file));
  assert.ok(cfb(bytes).names.includes('WordDocument'));
  const pages = docText(bytes);
  const lines = pages.map(p => p.text).join('\n').split('\n');
  // a .doc keeps a tracked deletion in its text, marked only in its formatting (not read): the one known difference
  const expected = [...PAGE_ONE.map(l => (l === 'Removed: kept words' ? 'Removed:old words kept words' : l)), 'Page two: R&D notes'];
  assert.deepEqual(lines, expected);
  // LibreOffice's own text of the .doc: every word of it is in ours
  soffice(['--convert-to', 'txt:Text (encoded):UTF8', '--outdir', path.join(TMP, 'txt'), file], TMP);
  const theirs = fs.readFileSync(path.join(TMP, 'txt', 'specification.txt'), 'utf8').replace(/^﻿/, '');
  const ours = new Set(lines.join(' ').split(/\s+/));
  const words = theirs.split(/\s+/).filter(Boolean);
  assert.ok(words.length > 20);
  for (const w of words) assert.ok(ours.has(w), `LibreOffice reads «${w}», we do not`);
});

test('a .doc under a password, or not a Word file at all, is refused with its reason', () => {
  assert.throws(() => docText(new TextEncoder().encode('plain text, not Word')), e => e.why === 'damaged');
  const docx = made();
  soffice(['--convert-to', 'doc:MS Word 97', '--outdir', path.join(TMP, 'pw'), docx], TMP);
  const bytes = new Uint8Array(fs.readFileSync(path.join(TMP, 'pw', 'specification.doc')));
  const word = cfb(bytes).stream('WordDocument');
  // the same file marked as encrypted (the flag Word sets for a password, bit 8 of the flags at 0x0A): refused, never read as text
  let off = -1;
  for (let i = 0; i < bytes.length - 12 && off < 0; i += 512) if (bytes.subarray(i, i + 12).every((v, k) => v === word[k])) off = i;
  assert.ok(off >= 0);
  const locked = bytes.slice();
  locked[off + 0x0b] |= 0x01;
  assert.throws(() => docText(locked), e => e.why === 'password');
});

test('a ZIP archive: names in any language, every file checked, a damaged or locked file reported and never handed over', async () => {
  const dir = path.join(TMP, 'zipme');
  fs.mkdirSync(path.join(dir, 'ملفات الثبات'), { recursive: true });
  fs.copyFileSync(made(), path.join(dir, 'specification.docx'));
  fs.writeFileSync(path.join(dir, 'ملفات الثبات', 'تقرير.txt'), 'تقرير ثبات تجريبي\n'.repeat(200));
  const zip = path.join(TMP, 'dossier.zip');
  execFileSync('zip', ['-q', '-X', '-r', zip, '.'], { cwd: dir });
  const bytes = new Uint8Array(fs.readFileSync(zip));
  const names = entries(bytes).filter(e => !e.dir).map(e => e.name).sort();
  assert.deepEqual(names, ['specification.docx', 'ملفات الثبات/تقرير.txt']);
  const { files, skipped } = await unzip(bytes);
  assert.equal(skipped.length, 0);
  const report = files.find(f => f.name.endsWith('تقرير.txt'));
  assert.equal(new TextDecoder().decode(report.bytes), 'تقرير ثبات تجريبي\n'.repeat(200));
  assert.deepEqual((await docxText(files.find(f => f.name === 'specification.docx').bytes))[0].text.split('\n'), PAGE_ONE);
  // one byte changed inside the packed report: its check fails, it is reported, the others still come out
  const e = entries(bytes).find(x => x.name.endsWith('تقرير.txt'));
  const start = e.at + 30 + (bytes[e.at + 26] | (bytes[e.at + 27] << 8)) + (bytes[e.at + 28] | (bytes[e.at + 29] << 8));
  const broken = bytes.slice();
  broken[start + Math.floor(e.packed / 2)] ^= 0xff;
  const after = await unzip(broken);
  assert.deepEqual(after.skipped.map(s => s.name), ['ملفات الثبات/تقرير.txt']);
  assert.deepEqual(after.files.map(f => f.name), ['specification.docx']);
  // under a password: reported as such
  fs.writeFileSync(path.join(TMP, 'secret.txt'), 'made-up secret');
  execFileSync('zip', ['-q', '-X', '-P', 'made-up', path.join(TMP, 'locked.zip'), 'secret.txt'], { cwd: TMP });
  const locked = await unzip(new Uint8Array(fs.readFileSync(path.join(TMP, 'locked.zip'))));
  assert.deepEqual(locked.skipped, [{ name: 'secret.txt', why: 'password' }]);
  assert.throws(() => entries(new TextEncoder().encode('no archive here')), x => x.why === 'damaged');
  assert.equal(crc32(new TextEncoder().encode('123456789')), 0xcbf43926);
});

// A RAR archive's files through the program's own reader: → {files: {name: bytes}, skipped, format}
function unrar(vols) {
  const files = {};
  const r = rar.extract(vols.map(v => new Uint8Array(fs.readFileSync(v))), {}, (name, parts, of) => {
    if (of) { files[name] = files[of]; return; }
    const all = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
    let at = 0;
    for (const p of parts) { all.set(p, at); at += p.length; }
    files[name] = all;
  });
  return { files, skipped: r.skipped, format: r.format };
}
const UTF8 = { ...process.env, LANG: 'C.UTF-8' };   // rar writes names as the locale spells them: the C locale loses Arabic
function noise(n, seed = 7) {            // the same bytes every run, and bytes no packer can shrink
  const out = new Uint8Array(n);
  let x = seed;
  for (let i = 0; i < n; i++) { x ^= x << 13; x ^= x >>> 17; x ^= x << 5; out[i] = x & 0xff; }
  return out;
}

test('a RAR archive (RAR5, as WinRAR 5 and later write it), solid, stored, in parts: every file as it was packed, names in any language', () => {
  const dir = path.join(TMP, 'rarme');
  fs.mkdirSync(path.join(dir, 'ملفات الثبات'), { recursive: true });
  fs.copyFileSync(made(), path.join(dir, 'specification.docx'));
  fs.writeFileSync(path.join(dir, 'ملفات الثبات', 'تقرير.txt'), 'تقرير ثبات تجريبي\n'.repeat(300));
  fs.writeFileSync(path.join(dir, 'scan.bin'), noise(150000));
  const want = { 'specification.docx': fs.readFileSync(path.join(dir, 'specification.docx')),
                 'ملفات الثبات/تقرير.txt': fs.readFileSync(path.join(dir, 'ملفات الثبات', 'تقرير.txt')), 'scan.bin': Buffer.from(noise(150000)) };
  const pack = (name, ...flags) => { execFileSync('rar', ['a', '-idq', '-r', ...flags, path.join(TMP, name), '*'], { cwd: dir, env: UTF8 }); return path.join(TMP, name); };
  for (const [name, flags, format] of [['five.rar', [], 'RAR5'], ['solid.rar', ['-s', '-m5'], 'RAR5'], ['stored.rar', ['-m0'], 'RAR5']]) {
    const r = unrar([pack(name, ...flags)]);
    assert.equal(r.format, format, name);
    assert.deepEqual(r.skipped, [], name);
    assert.deepEqual(Object.keys(r.files).sort(), Object.keys(want).sort(), name);
    for (const [k, v] of Object.entries(want)) assert.ok(Buffer.from(r.files[k]).equals(v), `${name}: ${k}`);
  }
  // in parts of 60 KB: the parts given in order make the whole
  pack('parts.rar', '-v60k');
  const parts = fs.readdirSync(TMP).filter(f => /^parts\.part\d+\.rar$/.test(f)).sort().map(f => path.join(TMP, f));
  assert.ok(parts.length >= 3, parts.join());
  const r = unrar(parts);
  assert.deepEqual(r.skipped, []);
  for (const [k, v] of Object.entries(want)) assert.ok(Buffer.from(r.files[k]).equals(v), `parts: ${k}`);
  // only the first part: what crosses into the next part is reported, never handed over cut
  const first = unrar(parts.slice(0, 1));
  assert.ok(first.skipped.some(x => x.why === 'volume'), JSON.stringify(first.skipped));
});

test('a RAR archive under a password is reported as such; a damaged one is refused', () => {
  const dir = path.join(TMP, 'rarlock');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'secret.txt'), 'made-up secret '.repeat(50));
  execFileSync('rar', ['a', '-idq', '-pmade-up', path.join(TMP, 'locked.rar'), 'secret.txt'], { cwd: dir, env: UTF8 });
  assert.deepEqual(unrar([path.join(TMP, 'locked.rar')]).skipped, [{ name: 'secret.txt', why: 'password' }]);
  assert.throws(() => rar.extract([new TextEncoder().encode('not an archive')], {}, () => {}), e => e.rar === 'damaged');
});

// The old program's archives (made up, «Dermacure»: tests/data/archives/rar, kept with their expected files) and, when they are
// here, libarchive's public test archives of the old format (RAR 2.9–4.x, which the rar on this machine no longer writes; fetched by
// the old program's web/vendor.sh, not kept in the repository): every file with its SHA-256.
const V1 = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..', 'dossier-builder');
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
function against(dir, expected, names) {
  for (const name of names) {
    const want = expected[name];
    const vols = want.vols.map(v => path.join(dir, v));
    if (want.error) { assert.throws(() => unrar(vols), e => e.rar === want.error, name); continue; }
    const r = unrar(vols);
    if (want.format) assert.equal(r.format, want.format, name);
    for (const [file, [size, hash]] of Object.entries(want.files)) {
      assert.ok(r.files[file], `${name}: ${file} missing (${Object.keys(r.files).join(', ')})`);
      assert.equal(r.files[file].length, size, `${name}: ${file}`);
      assert.equal(sha(r.files[file]), hash, `${name}: ${file}`);
    }
    for (const [file, why] of Object.entries(want.skipped || {})) assert.ok(r.skipped.some(x => x.name === file && x.why === why), `${name}: ${file} ${why}`);
  }
}
test('the old program\'s made-up RAR archives (filters, parts, password) read the same here', () => {
  const dir = path.join(V1, 'tests', 'data', 'archives', 'rar');
  const expected = JSON.parse(fs.readFileSync(path.join(dir, 'expected.json'), 'utf8'));
  against(dir, expected, ['dermacure.rar', 'dermacure-solid.rar', 'dermacure-stored.rar', 'dermacure-parts', 'dermacure-delta.rar', 'dermacure-e8.rar', 'dermacure-password.rar']);
});
test('the old RAR format (RAR 2.9–4.x: LZ, PPMd, filters, Unicode names) on libarchive\'s public test archives', t => {
  const dir = path.join(V1, 'web', 'vendor', 'arch', 'test');
  if (!fs.existsSync(path.join(dir, 'test_read_format_rar.rar'))) return t.skip('libarchive\'s test archives are not on this machine (the old program\'s web/vendor.sh fetches them)');
  const expected = JSON.parse(fs.readFileSync(path.join(V1, 'tests', 'data', 'archives', 'rar', 'public-expected.json'), 'utf8'));
  const names = ['test_read_format_rar.rar', 'test_read_format_rar_compress_normal.rar', 'test_read_format_rar_compress_best.rar',
                 'test_read_format_rar_unicode.rar', 'test_read_format_rar_filter.rar', 'test_read_format_rar_encryption_header.rar'];
  against(dir, expected, names);
  assert.equal(unrar([path.join(dir, 'test_read_format_rar.rar')]).format, 'RAR4');
});
