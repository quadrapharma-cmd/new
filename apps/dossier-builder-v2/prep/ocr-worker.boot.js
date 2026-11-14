/* tesseract.js's worker, started through this file (prep/ocr.js). The language data are published as gzip in base64 text, because
   the artifact host serves text: here a fetch of <lang>.traineddata.gz fetches <lang>.traineddata.gz.b64.txt and hands tesseract.js
   the gzip's bytes, which it unpacks itself. Then the real worker. */
(function () {
  const realFetch = self.fetch.bind(self);
  const fromB64 = s => { const bin = atob(s.replace(/\s+/g, '')), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; };
  self.fetch = async function (url, opts) {
    const u = typeof url === 'string' ? url : (url && url.url) || '';
    if (/\.traineddata(\.gz)?$/.test(u)) {
      const r = await realFetch(u + '.b64.txt', opts);
      if (!r.ok) return r;
      return new Response(fromB64(await r.text()), { status: 200, headers: { 'content-type': 'application/octet-stream' } });
    }
    return realFetch(url, opts);
  };
  importScripts('worker.min.js');
})();
