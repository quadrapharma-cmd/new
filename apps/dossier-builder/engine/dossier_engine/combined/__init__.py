"""A dossier received as one or more combined files, made ready: read page by page, the repeated blocks left out, the pages
without text read by OCR, cut into its CTD documents and placed, every page checked against its source, the findings, the
corrections, the eCTD sequence with its validation, and the report — the steps that built the DTP-HB dossier by hand on
17/11/2026, as one program.

Runs where the tools are (the cloud edition or a computer with them): pikepdf, poppler (pdftotext, pdftoppm), OCRmyPDF with
Tesseract, LibreOffice, Chromium (Playwright). Not part of the browser edition.

    python3 -m dossier_engine.combined run <source folder> <work folder>

What the program decides by itself and what it takes from the dossier's decisions file is said in the report, decision by
decision (README, «A combined dossier made ready»)."""
