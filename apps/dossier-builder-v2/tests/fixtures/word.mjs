// The specification of the made-up dossier as Word files: a .docx (a paragraph a line; its header carries the company), and the
// same as an old .doc written by LibreOffice. Every word is made up.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
// the specification as a .docx (a paragraph a line; the header carries the company), then as an old .doc by LibreOffice
export function wordOf(doc, TMP) {
  const dir = path.join(TMP, 'docx-' + doc.id);
  const [head, ...lines] = doc.pages[0].text.split('\n');
  const W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"';
  const para = l => `<w:p><w:r><w:t xml:space="preserve">${esc(l)}</w:t></w:r></w:p>`;
  const files = {
    '[Content_Types].xml': '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/></Types>',
    '_rels/.rels': '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
    'word/_rels/document.xml.rels': '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdH1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/></Relationships>',
    'word/document.xml': `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document ${W}><w:body>${lines.map(para).join('')}<w:sectPr><w:headerReference w:type="default" r:id="rIdH1"/></w:sectPr></w:body></w:document>`,
    'word/header1.xml': `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr ${W}>${para(head)}</w:hdr>`,
  };
  for (const [name, text] of Object.entries(files)) { fs.mkdirSync(path.dirname(path.join(dir, name)), { recursive: true }); fs.writeFileSync(path.join(dir, name), text); }
  const docx = path.join(TMP, `${doc.id}.docx`);
  execFileSync('zip', ['-q', '-X', '-r', docx, '[Content_Types].xml', '_rels', 'word'], { cwd: dir });
  execFileSync('soffice', ['--headless', `-env:UserInstallation=file://${TMP}/lo-profile`, '--convert-to', 'doc:MS Word 97', '--outdir', TMP, docx], { stdio: 'pipe', timeout: 120000 });
  return { docx: fs.readFileSync(docx), doc: fs.readFileSync(path.join(TMP, `${doc.id}.doc`)) };
}

