/* tesseract.js worker bootstrap (Dossier Builder — the browser edition's scan reading). The language data is served as base64 text (<lang>.traineddata.gz.b64.txt),
   because the artifact host serves text files; this shim decodes it inside the worker, then loads the real worker. */
(function () {
  const realFetch = self.fetch.bind(self);
  function fromBase64(s) {
    const bin = atob(s.replace(/\s+/g, ''));
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }
  self.fetch = async function (url, opts) {
    const u = typeof url === 'string' ? url : (url && url.url) || '';
    if (/\.traineddata(\.gz)?$/.test(u)) {
      const r = await realFetch(u + '.b64.txt', opts);
      if (!r.ok) return r;
      return new Response(fromBase64(await r.text()), { status: 200, headers: { 'content-type': 'application/octet-stream' } });
    }
    return realFetch(url, opts);
  };
  importScripts('worker.min.js');
})();
