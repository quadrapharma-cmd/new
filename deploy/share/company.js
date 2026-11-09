// AREA w-growth (the owner's decision 1, SEO basics): /c/<slug> — a company's title, description and Open Graph tags for search
// engines and link previews (which do not run the app's JavaScript), then the app opens the page (#/companies/<slug>).
// web/build/live.py writes this file to <live out>/api/company.js with the build's Supabase URL and ANON key (public by design);
// deploy/vercel.json rewrites /c/:slug to it. It reads only public_company_meta() (0103): name, description, logo, badges — no
// contact details. The local gateway (tools/local-supabase/gateway.mjs) serves it the same way.
const SUPABASE_URL = '__SUPABASE_URL__', ANON = '__ANON_KEY__';
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
module.exports = async function handler(req, res) {
  const slug = String((req.query && req.query.slug) || '').slice(0, 120);
  let meta = null;
  if (/^[^\s"'<>`&\\/?#]{1,120}$/.test(slug)) {
    try {
      const r = await fetch(SUPABASE_URL + '/rest/v1/rpc/public_company_meta', { method: 'POST', body: JSON.stringify({ p_slug: slug }),
        headers: { apikey: ANON, Authorization: 'Bearer ' + ANON, 'content-type': 'application/json' } });
      if (r.ok) meta = await r.json();
    } catch (e) { meta = null; }
  }
  const host = String((req.headers && (req.headers['x-forwarded-host'] || req.headers.host)) || '').replace(/[^\w.:-]/g, '');
  const proto = String((req.headers && req.headers['x-forwarded-proto']) || (/^(localhost|127\.)/.test(host) ? 'http' : 'https')).split(',')[0] === 'http' ? 'http' : 'https';
  const base = proto + '://' + host, app = '/#/companies/' + encodeURIComponent(slug);
  const title = meta ? meta.name + (meta.verified ? ' ✓' : '') + ' — Drugbox' : 'Drugbox — the B2B network of the pharmaceutical industry';
  const desc = meta ? (meta.description || 'A company on Drugbox, the B2B network of the pharmaceutical industry in Egypt and the Arab region.') + (meta.unclaimed ? ' · Listed from public industry sources (not yet claimed).' : '')
    : 'Drugbox — the B2B network of the pharmaceutical industry in Egypt and the Arab region.';
  const img = meta && /^https:\/\//.test(meta.image || '') ? meta.image : '';
  const html = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<title>' + esc(title) + '</title><meta name="description" content="' + esc(desc) + '"><link rel="canonical" href="' + esc(base + '/c/' + encodeURIComponent(slug)) + '">' +
    '<meta property="og:type" content="website"><meta property="og:site_name" content="Drugbox"><meta property="og:title" content="' + esc(title) + '">' +
    '<meta property="og:description" content="' + esc(desc) + '"><meta property="og:url" content="' + esc(base + '/c/' + encodeURIComponent(slug)) + '">' +
    (img ? '<meta property="og:image" content="' + esc(img) + '">' : '') + '<meta name="twitter:card" content="summary">' +
    (meta && meta.name_ar ? '<meta property="og:locale:alternate" content="ar_EG">' : '') +
    '<meta http-equiv="refresh" content="0;url=' + esc(app) + '"></head><body><p><a href="' + esc(app) + '">' + esc(meta ? meta.name : 'Drugbox') + ' on Drugbox</a></p>' +
    '<script>location.replace(' + JSON.stringify(app).replace(/</g, '\\u003c') + ')</script></body></html>';
  res.statusCode = meta ? 200 : 404;
  res.setHeader('content-type', 'text/html; charset=utf-8'); res.setHeader('cache-control', 'public, max-age=300');
  res.end(html);
};
