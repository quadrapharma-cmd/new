// Made-up documents as real PDFs with a text layer, written with pdf-lib in Node (no browser): each page of a fixture document one
// page of the PDF, in Helvetica — so only Latin text (an Arabic line is left out; the browser tests carry Arabic). Several
// documents can be written into one PDF, as a company sends a combined file.
import { PDFDocument, StandardFonts } from 'pdf-lib';

const latin = s => String(s).replace(/[^\x20-\x7e\n\u2013\u2014\u00b0\u00b5]/g, '').replace(/[ \t]+$/gm, '');   // what Helvetica (WinAnsi) can write
export async function pdfOf(docs) {
  const pdf = await PDFDocument.create();
  const font = await pdf.embedFont(StandardFonts.Helvetica);
  for (const doc of [docs].flat()) {
    for (const p of doc.pages) {
      const page = pdf.addPage([595, 842]);
      let y = 790;
      for (const line of latin(p.text).split('\n')) {
        if (!line.trim()) { y -= 8; continue; }
        page.drawText(line.slice(0, 95), { x: 50, y, size: 11, font });
        y -= 16;
        if (y < 40) break;
      }
    }
  }
  return pdf.save();
}
