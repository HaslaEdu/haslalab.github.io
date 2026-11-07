/* haslalab-ai-egress: forwards the community Worker's requests to the AI providers that refuse its Hong Kong
 * placement. The target is in X-Egress-Url and must be one of AI_EGRESS_HOSTS; everything else is refused. */
export const AI_EGRESS_HOSTS = new Set(["generativelanguage.googleapis.com", "aiplatform.googleapis.com", "api.anthropic.com",
  "api.openai.com", "api.tavily.com"]);
export const egressHost = host => AI_EGRESS_HOSTS.has(host) || /^[a-z0-9-]+-aiplatform\.googleapis\.com$/.test(host);

export default {
  async fetch(req) {
    let target;
    try { target = new URL(req.headers.get("x-egress-url") || ""); } catch { return new Response("bad target", { status: 400 }); }
    if (target.protocol !== "https:" || target.username || target.password || target.port || !egressHost(target.hostname))
      return new Response("host not allowed", { status: 403 });
    const headers = new Headers();
    for (const [k, v] of req.headers) if (!/^(x-egress-|cf-|x-forwarded-|x-real-ip$|host$)/i.test(k)) headers.set(k, v);
    const redirect = ["follow", "manual", "error"].includes(req.headers.get("x-egress-redirect")) ? req.headers.get("x-egress-redirect") : "follow";
    const res = await fetch(target, { method: req.method, headers, body: ["GET", "HEAD"].includes(req.method) ? undefined : req.body, redirect });
    const out = new Response(res.body, res);
    out.headers.set("x-egress-colo", String(req.cf?.colo || ""));
    return out;
  },
};
