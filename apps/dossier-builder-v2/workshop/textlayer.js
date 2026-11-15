// A scanned PDF made searchable: on each scanned page, the words the scan reader found, laid as an invisible layer exactly over the
// picture of them (prep/ocr.js layer(): Tesseract's text-only PDF of the page as it read it — turned upright and straightened). What a
// page shows does not change; only the words to find and copy are added. The page's own picture stays the paper it was.
//   withTextLayer(pdfBytes, [{index, pdf, rot, angle, w0, h0}]) → new PDF bytes
//   layerMatrix(...) → the PDF matrix [a b c d e f] that puts the text-only page onto the page (exported for the tests)
import { PDFDocument, pushGraphicsState, popGraphicsState, concatTransformationMatrix, drawObject } from 'pdf-lib';

// [a b c d e f]: (x, y) → (a·x + c·y + e, b·x + d·y + f), as a PDF «cm»; then(m, n): m first, then n
const then = (m, n) => [m[0] * n[0] + m[1] * n[2], m[0] * n[1] + m[1] * n[3], m[2] * n[0] + m[3] * n[2], m[2] * n[1] + m[3] * n[3],
  m[4] * n[0] + m[5] * n[2] + n[4], m[4] * n[1] + m[5] * n[3] + n[5]];
const move = (x, y) => [1, 0, 0, 1, x, y];
const turn = deg => { const r = deg * Math.PI / 180, c = Math.cos(r), s = Math.sin(r); return [c, s, -s, c, 0, 0]; };   // as a canvas turns (y down)
export const apply = (m, [x, y]) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];

// From the text-only page (points, y up) to the page's own space:
//  1. to the read picture's pixels (y down); 2. straightening undone (it turned the picture by −angle about its middle);
//  3. turning upright undone (rot clockwise, the picture's sides swapped); 4. to the drawn page (w0×h0 pixels for the page's
//  visual width × height in points, y up); 5. the page's own turn (/Rotate) undone, onto its crop box.
export function layerMatrix({ lw, lh, rot = 0, angle = 0, w0, h0, w2, h2, box, rotate = 0 }) {
  const visualW = rotate % 180 ? box.height : box.width, visualH = rotate % 180 ? box.width : box.height;
  const s = w2 / lw, k = w0 / visualW;
  const side = rot % 180 !== 0, w1 = side ? h0 : w0, h1 = side ? w0 : h0;
  let m = [s, 0, 0, -s, 0, h2];                                                         // 1
  m = then(m, then(then(move(-w2 / 2, -h2 / 2), turn(angle)), move(w2 / 2, h2 / 2)));   // 2 (w2 = w1, h2 = h1)
  m = then(m, then(then(move(-w1 / 2, -h1 / 2), turn(-rot)), move(w0 / 2, h0 / 2)));    // 3
  m = then(m, [1 / k, 0, 0, -1 / k, 0, visualH]);                                       // 4
  const r = ((rotate % 360) + 360) % 360;                                               // 5: visual (x, y) → page (u, v)
  const back = r === 90 ? [0, 1, -1, 0, box.width, 0]           // u = bw − y, v = x
    : r === 180 ? [-1, 0, 0, -1, box.width, box.height]          // u = bw − x, v = bh − y
    : r === 270 ? [0, -1, 1, 0, 0, box.height]                   // u = y, v = bh − x
    : [1, 0, 0, 1, 0, 0];
  return then(then(m, back), move(box.x, box.y));
}

export async function withTextLayer(bytes, layers) {
  const doc = await PDFDocument.load(bytes, { updateMetadata: false, ignoreEncryption: true });
  for (const l of layers) {
    const page = doc.getPage(l.index);
    const [text] = await doc.embedPdf(l.pdf, [0]);
    const m = layerMatrix({ lw: text.width, lh: text.height, rot: l.rot, angle: l.angle, w0: l.w0, h0: l.h0, w2: l.w2, h2: l.h2,
                            box: page.getCropBox(), rotate: page.getRotation().angle });
    const name = page.node.newXObject('TextLayer', text.ref);
    page.pushOperators(pushGraphicsState(), concatTransformationMatrix(...m), drawObject(name), popGraphicsState());
  }
  return doc.save({ useObjectStreams: false });
}
