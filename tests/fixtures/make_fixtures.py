"""Test files the suites upload (made here, not stored in git): short WebM clips, a photo and a PDF.
Usage: python3 tests/fixtures/make_fixtures.py [dir]   (default: $DRUGBOX_FIXTURES or /tmp/vids). Needs ffmpeg and Pillow.
WebM (VP8): the open-source Chromium used by Playwright cannot decode H.264."""
import os, sys, subprocess
OUT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('DRUGBOX_FIXTURES', '/tmp/vids')
os.makedirs(OUT, exist_ok=True)
def clip(name, seconds, color):
    path = os.path.join(OUT, name)
    if os.path.exists(path): return
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'testsrc=size=320x240:rate=25:duration={seconds}', '-f', 'lavfi', '-i', f'color=c={color}:size=320x240:rate=25:duration={seconds}',
                    '-filter_complex', '[0:v][1:v]blend=all_mode=overlay:all_opacity=0.3', '-c:v', 'libvpx', '-b:v', '60k', '-an', path], check=True)
clip('company_intro.webm', 4, 'blue')     # a 4-second company video
clip('me_intro.webm', 3, 'green')         # a 3-second personal introduction
clip('too_long.webm', 95, 'red')          # longer than the 90-second limit for personal videos
png = os.path.join(OUT, 'photo.png')
if not os.path.exists(png):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (640, 420), (26, 86, 219)); d = ImageDraw.Draw(im); d.rectangle((40, 40, 600, 380), outline=(255, 255, 255), width=8); im.save(png)
pdf = os.path.join(OUT, 'spec.pdf')
if not os.path.exists(pdf):   # a valid one-page PDF ("Specification")
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
            None, b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    text = b'BT /F1 24 Tf 72 760 Td (Specification - test file) Tj ET'
    objs[3] = b'<< /Length %d >>\nstream\n' % len(text) + text + b'\nendstream'
    out, offs = bytearray(b'%PDF-1.4\n'), []
    for i, o in enumerate(objs, 1): offs.append(len(out)); out += b'%d 0 obj\n' % i + o + b'\nendobj\n'
    x = len(out); out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1) + b''.join(b'%010d 00000 n \n' % o for o in offs)
    out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, x)
    open(pdf, 'wb').write(bytes(out))
print('fixtures in', OUT, ':', ', '.join(sorted(os.listdir(OUT))))
