Fonts made to the measures of the fonts Word files name, for the Word program in the browser edition (17/11/2026).

A Word file names Times New Roman, Arial, Courier New, Calibri or Cambria; the page has none of them, and the Word program (WordCraft)
drew them with its own fonts, so lines and pages broke elsewhere than in Word (his SPC 4 pages instead of 3, his file index 3 instead
of 2). These fonts have the same widths as the ones they stand for; the Word program takes them (its command font.add) before it
turns a Word file into PDF (ui/assets/programs.js toPdf), and its PDF of his English files then has LibreOffice's pages and words.

  Liberation Serif, Sans, Mono 2.1.5   Times New Roman, Arial, Courier New   SIL Open Font License 1.1   LICENSE-Liberation.txt
  Carlito 20230309                     Calibri                               SIL Open Font License 1.1   LICENSE-Carlito.txt
  Caladea 20200211                     Cambria                               SIL Open Font License 1.1   LICENSE-Caladea.txt
  Noto Naskh Arabic (Regular, Bold)    the reports' and the Arabic leaflet's  SIL Open Font License 1.1   LICENSE-Noto.txt

Taken unchanged from the Debian packages fonts-liberation 1:2.1.5-3, fonts-crosextra-carlito 20230309-2 and
fonts-crosextra-caladea 20200211-2 (their copyright files are the LICENSE files here). web/build.py serves them beside the programs as
base64 text (assets/programs/fonts/*.ttf.b64.txt), fetched only when a Word file is turned into PDF.

The combined-dossier program (engine/dossier_engine/combined, 22/11/2026) prints its reports and the Arabic leaflet with Noto Naskh
Arabic and Liberation Sans taken from here (as @font-face, so a Mac with neither draws the same pages as Linux), and gives LibreOffice
a font table of its own (Times New Roman → Liberation Serif, Arial → Liberation Sans, Courier New → Liberation Mono, Calibri →
Carlito, Cambria → Caladea: what fontconfig does on Linux) so the product information's PDFs are the same on a Mac. Noto Naskh Arabic
is taken unchanged from the Debian package fonts-noto-core 20201225-2 (its copyright file is LICENSE-Noto.txt).
