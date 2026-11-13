# Third-party notices

Code in this program that comes from other projects, with each project's licence.

## PdfCraft — https://github.com/storytold/pdfcraft (MIT OR Apache-2.0; used under MIT)

**The program's PDF engine** (docs/ctd/PDFCRAFT-INTEGRATION.md): the PdfCraft command-line program, release v0.21.1 (commit in
`tools/pdfcraft/PIN`), built from source without its MCP server by `tools/pdfcraft/build.sh` and carried beside the engine in the desktop
and company editions (`vendor/pdfcraft/`, never committed). Shipped with it: PdfCraft's `LICENSE-MIT`, `LICENSE-APACHE`, `NOTICE`,
`ATTRIBUTION.md` and `licenses/`, and `THIRD-PARTY-LICENSES.txt` — every crate compiled into it with its own licence and notice files
(written at build time by `tools/pdfcraft/licenses.py`; all permissive: MIT, Apache-2.0, BSD, ISC, Zlib, Unicode-3.0, Unlicense, BSL-1.0).
The ArtCraft name, wordmark and logos are not covered by PdfCraft's licence and are not used.

**Modified:** the program builds PdfCraft with two changes of its own, in `tools/pdfcraft/patches/` (shipped beside the program):
`0001-ocr-arabic-and-language-lists.patch` — its OCR tools accept Tesseract's languages and lists of them («ar+en»); an Arabic or
Hebrew word is written right to left in the searchable text layer; the words of a right-to-left line share one baseline.
`0002-ocr-tesseract-one-thread.patch` — Tesseract reads on one thread unless the caller sets `OMP_THREAD_LIMIT`, which is passed
through to it (several readings at once no longer slow each other to a standstill).

## Tesseract OCR — https://github.com/tesseract-ocr/tesseract (Apache-2.0)

The text recognition PdfCraft drives for scans (Arabic and English). Installed in the company edition's image from Ubuntu's packages
(`tesseract-ocr`, `tesseract-ocr-ara`, `tesseract-ocr-eng`, the tessdata models under Apache-2.0); on a desktop, the copy installed on
that computer is used (not bundled).

Also used in `engine/dossier_engine/validators/ectd32_eu.py` (`permissions`): reading a PDF's `/P` permission flags the way the security
handler's revision reads them (ISO 32000-1:2008 Table 22), ported from Rust (`crates/crypt/src/lib.rs`) to Python and shortened.

```
MIT License

Copyright (c) 2026 ArtCraft Team and the PdfCraft contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## eCTD Dossier Builder — https://github.com/randomthingsonlineatsk-cloud/ectd-dossier-builder (Apache-2.0)

Used as **data**, not code: the map from the ICH CTD to the ASEAN Common Technical Dossier's parts and sections
(`src/data/compare.json`, «actd»), which `engine/dossier_engine/writers/actd.py` follows. The project's NOTICE, kept as
section 4(d) of the Apache License 2.0 asks:

> eCTD Dossier Builder
> Copyright 2026 Khan Gulrez Shagufa Fazal Ahmed
>
> This product includes software developed by Khan Gulrez Shagufa Fazal Ahmed
> (ORCID 0009-0009-6195-0329, https://github.com/randomthingsonlineatsk-cloud).
>
> Licensed under the Apache License, Version 2.0.
>
> Canada, Switzerland and ASEAN ACTD headings in the region comparison come from Health Canada, Swissmedic and ASEAN public guidance.

Its author notes that its output is not for a real submission: the map is checked against the ASEAN text (Organization of the
Dossier, Revision 1) and each member state's guidance before a filing.
