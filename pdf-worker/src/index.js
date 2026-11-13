/* haslalab-pdf: serves the problem sheets and solutions kept in GitHub Releases.
 *
 *   GET /pdf/IPhO_2025_E1_EN.pdf
 *     -> github.com/HaslaEdu/haslalab.github.io/releases/download/pdf-ipho/IPhO_2025_E1_EN.pdf
 *
 * GitHub sends release assets as downloads (attachment, octet-stream) and without
 * CORS, so a link straight to them saves the file instead of opening it.  This
 * passes the bytes through as an inline PDF, so the browser shows it as before.
 * The release is named after the part of the file name before the first
 * underscore, the same rule tools/pdf_release.py uploads by.
 */
const REPO = "HaslaEdu/haslalab.github.io";
const NAME = /^\/pdf\/(([A-Za-z]+)_[A-Za-z0-9._-]+\.pdf)$/;
const DAY = 86400;
/* Replacing assets in place keeps their download URLs, so cached copies would
 * outlive the swap.  Bump this after re-uploading files to drop every cached copy. */
const CACHE_V = 81;         // IZhO 2024 and IChO 2019 Korean matched to the original pages

export default {
  async fetch(req, env, ctx) {
    if (req.method !== "GET" && req.method !== "HEAD")
      return new Response("Method not allowed", { status: 405, headers: { Allow: "GET, HEAD" } });
    const url = new URL(req.url);
    const m = NAME.exec(url.pathname);
    if (!m) return new Response("Not found", { status: 404 });
    const [, name, prefix] = m;

    /* one cached copy per file at each edge; the query string never matters */
    const cache = caches.default;
    const key = new Request(`${url.origin}${url.pathname}?v=${CACHE_V}`, { method: "GET" });
    /* Cache.match slices complete entries when the lookup retains Range.
     * We do not publish validators, so If-Range must fall back to a full copy. */
    const range = req.method === "GET" && !req.headers.has("If-Range") ? req.headers.get("Range") : null;
    const lookup = range ? new Request(key, { headers: { Range: range } }) : key;
    let res = await cache.match(lookup);
    if (!res) {
      const up = await fetch(`https://github.com/${REPO}/releases/download/pdf-${prefix.toLowerCase()}/${name}?v=${CACHE_V}`,
                             { redirect: "follow", headers: range ? { Range: range } : {}, cf: { cacheEverything: true, cacheTtlByStatus: { "200-299": DAY, "404": 30, "500-599": 0 } } });
      if (range && up.status === 416) {
        const headers = { "Accept-Ranges": "bytes", "Access-Control-Allow-Origin": "*", "Access-Control-Expose-Headers": "Content-Length, Content-Range, Accept-Ranges" };
        const contentRange = up.headers.get("Content-Range");
        if (contentRange) headers["Content-Range"] = contentRange;
        return new Response(null, { status: 416, headers });
      }
      /* a file asked for before it was uploaded is «not found» for half a minute only, not for a day */
      if (!up.ok) return new Response("Not found", { status: up.status === 404 ? 404 : 502 });
      res = new Response(up.body, { status: up.status === 206 ? 206 : 200, headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `inline; filename="${name}"`,
        "Cache-Control": "public, max-age=3600",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Expose-Headers": "Content-Length, Content-Range, Accept-Ranges",
        "Accept-Ranges": "bytes",
        "X-Content-Type-Options": "nosniff",
      }});
      const len = up.headers.get("Content-Length");
      if (len) res.headers.set("Content-Length", len);
      const contentRange = up.headers.get("Content-Range");
      if (contentRange) res.headers.set("Content-Range", contentRange);
      /* A partial PDF must never replace the complete cached document. */
      if (res.status === 200) ctx.waitUntil(cache.put(key, res.clone()));
    }
    const headers = new Headers(res.headers);
    headers.set("Accept-Ranges", "bytes");
    headers.set("Access-Control-Expose-Headers", "Content-Length, Content-Range, Accept-Ranges");
    return new Response(req.method === "HEAD" ? null : res.body, { status: res.status, headers });
  },
};
