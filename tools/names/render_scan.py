"""Render check for the name rule (S-03): every Arabic letter the rule allows is drawn in its four joining positions (isolated,
initial, medial, final) with each installed font, and two letters that draw the SAME pixels but have DIFFERENT skeletons are
listed — a look-alike the skeleton would miss. Reads the live app's generated rule (web/src/live/adapter.js).
  python3 tools/names/render_scan.py            (Playwright 1.56 Chromium; prints the pairs, exit 0)
Found with it (0039): African noon ࢽ / ن and African qaf ࢼ / ف before a letter → Arabic letters only from the Arabic and Arabic
Supplement blocks. Left: ڒ / ۯ draw alike in FreeSerif only (a small v and an inverted v above reh; distinct in DejaVu Sans)."""
import json, subprocess, hashlib
from playwright.sync_api import sync_playwright
src=open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), '../../web/src/live/adapter.js'),encoding='utf8').read()
a=src.index('/* >>> generated'); b=src.index('/* <<< generated */'); gen=src[src.index('\n',a)+1:b]
with sync_playwright() as p:
    br=p.chromium.launch(args=['--no-sandbox']); pg=br.new_page()
    pg.set_content('<canvas id=c width=200 height=80></canvas>')
    res=pg.evaluate("""(gen)=>{ const F=new Function(gen+'\\nreturn {nmNorm,nmProblem,nmSkel};')();
      const L=[]; for(let c=0x620;c<=0x8FF;c++){const s=String.fromCodePoint(c); if(/\\p{L}/u.test(s)&&/\\p{Script=Arabic}/u.test(s)&&F.nmProblem(F.nmNorm('بب'+s+'بب'))==='') L.push(s);}
      const cv=document.getElementById('c'), x=cv.getContext('2d'); const out={};
      for (const font of ['32px "DejaVu Sans"','32px "FreeSerif"']) {
        for (const pos of ['init','medi','fina','isol']) {
          const g={};
          for (const s of L) { const t = pos==='init'? s+'\\u0640' : pos==='medi' ? '\\u0640'+s+'\\u0640' : pos==='fina' ? '\\u0640'+s : s;
            x.clearRect(0,0,200,80); x.font=font; x.fillStyle='#000'; x.direction='rtl'; x.fillText(t,150,50);
            const d=x.getImageData(0,0,200,80).data; let h=0; for(let i=3;i<d.length;i+=4){h=(h*31+d[i])|0;}
            (g[h]=g[h]||[]).push(s); }
          for (const h in g) if (g[h].length>1) { const ks=new Set(g[h].map(s=>F.nmSkel(s))); if (ks.size>1) (out[font+' '+pos]=out[font+' '+pos]||[]).push(g[h].map(s=>s+' U+'+s.codePointAt(0).toString(16)+' sk='+F.nmSkel(s)).join(' | ')); }
        }
      }
      return {n:L.length, out}; }""", gen)
    print('allowed Arabic letters', res['n'])
    for k,v in res['out'].items():
        print(k, len(v))
        for x in v[:40]: print('   ', x)
    br.close()
