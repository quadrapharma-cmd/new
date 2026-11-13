# Third-party notices

Code in this program that comes from other projects, with each project's licence.

## PdfCraft — https://github.com/storytold/pdfcraft (MIT OR Apache-2.0; used under MIT)

Used in `engine/dossier_engine/validators/ectd32_eu.py` (`permissions`): reading a PDF's `/P` permission flags the way the security
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
