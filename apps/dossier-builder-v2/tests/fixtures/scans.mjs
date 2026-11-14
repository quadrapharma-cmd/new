// The made-up dossier (tests/fixtures/dossier.mjs) as a company sends it: the EDA papers scanned — pictures of their pages in a PDF,
// a little crooked, with no text of their own — the specification as Word, the certificate of analysis as a PDF with its text, and
// the receipts and the certificate packed in a ZIP. Drawn by the browser; every name and number is made up.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { LICENCE, SPEC, STABILITY, RECEIPTS, COA } from './dossier.mjs';
import { wordOf } from './word.mjs';

const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
const lineHtml = l => `<p dir="${/[؀-ۿ]/.test(l) && !/^[A-Za-z]/.test(l) ? 'rtl' : 'ltr'}">${esc(l)}</p>`;
const STYLE = "font-family:'DejaVu Serif','Noto Naskh Arabic',serif;font-size:15pt;line-height:1.55;margin:0;padding:70px 80px;color:#1a1a1a";

// one page drawn, «scanned»: turned by `skew` degrees, a grey paper, at about 240 dpi → PNG bytes
async function scanOf(browser, text, skew) {
  const page = await browser.newPage({ viewport: { width: 794, height: 1123 }, deviceScaleFactor: 2.5 });
  await page.setContent(`<html><body style="margin:0;background:#f4f2ec"><div style="${STYLE};transform:rotate(${skew}deg);transform-origin:50% 40%">
    ${text.split('\n').map(lineHtml).join('')}</div></body></html>`);
  const png = await page.screenshot({ type: 'png' });
  await page.close();
  return png;
}
// pictures as the pages of a PDF with no text of its own
async function pdfOfPictures(browser, pngs) {
  const page = await browser.newPage();
  await page.setContent(`<html><head><style>@page{size:A4;margin:0}body{margin:0}img{display:block;width:210mm;height:297mm;page-break-after:always}</style></head><body>${
    pngs.map(p => `<img src="data:image/png;base64,${p.toString('base64')}">`).join('')}</body></html>`);
  const pdf = new Uint8Array(await page.pdf({ format: 'A4', printBackground: true }));
  await page.close();
  return pdf;
}
async function pdfOfText(browser, doc) {
  const page = await browser.newPage();
  await page.setContent(`<html><body style="${STYLE}">${doc.pages.map(p => `<section style="page-break-after:always">${p.text.split('\n').map(lineHtml).join('')}</section>`).join('')}</body></html>`);
  const pdf = new Uint8Array(await page.pdf({ format: 'A4' }));
  await page.close();
  return pdf;
}
export async function scannedPdf(browser, doc, skews = [1.2, -0.8, 0.6]) {
  const pngs = [];
  for (let i = 0; i < doc.pages.length; i++) pngs.push(await scanOf(browser, doc.pages[i].text, skews[i % skews.length]));
  return pdfOfPictures(browser, pngs);
}
// The whole made-up dossier as files in `dir`: three scans, the specification as Word inside a RAR, the certificate in a ZIP → paths
export async function madeUpDossier(browser, dir) {
  fs.mkdirSync(path.join(dir, 'in-rar'), { recursive: true });
  fs.mkdirSync(path.join(dir, 'in-zip'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'licence (scan).pdf'), await scannedPdf(browser, LICENCE));
  fs.writeFileSync(path.join(dir, 'stability (scan).pdf'), await scannedPdf(browser, STABILITY));
  fs.writeFileSync(path.join(dir, 'receipts (scan).pdf'), await scannedPdf(browser, RECEIPTS));
  fs.writeFileSync(path.join(dir, 'in-rar', 'specification.docx'), wordOf(SPEC, dir).docx);
  execFileSync('rar', ['a', '-idq', '-o+', path.join(dir, 'specification.rar'), 'specification.docx'], { cwd: path.join(dir, 'in-rar'), env: { ...process.env, LANG: 'C.UTF-8' } });
  fs.writeFileSync(path.join(dir, 'in-zip', 'coa.pdf'), await pdfOfText(browser, COA));
  fs.rmSync(path.join(dir, 'coa.zip'), { force: true });
  execFileSync('zip', ['-q', '-X', path.join(dir, 'coa.zip'), 'coa.pdf'], { cwd: path.join(dir, 'in-zip') });
  return ['licence (scan).pdf', 'stability (scan).pdf', 'receipts (scan).pdf', 'specification.rar', 'coa.zip'].map(f => path.join(dir, f));
}
export { pdfOfText, LICENCE, SPEC, STABILITY, RECEIPTS, COA };
