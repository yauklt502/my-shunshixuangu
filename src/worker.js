/**
 * Cloudflare Worker: static web/ + Fuyao API proxy (key stays on the server).
 */
const UPSTREAM = "https://fuyao.aicubes.cn";
const FALLBACK_KEY = "sk-fuyao-y8hq3i8OAmeBclqIG-PPdx978_F61Xia";

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "X-api-key, Content-Type",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Max-Age": "86400",
  };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/api/")) {
      if (request.method === "OPTIONS") {
        return new Response(null, { status: 204, headers: corsHeaders() });
      }
      const key = env.FUYAO_API_KEY || FALLBACK_KEY;
      const headers = {
        "User-Agent": "duanxian-xunlong/1.2",
        "X-api-key": key,
      };
      try {
        const resp = await fetch(UPSTREAM + url.pathname + url.search, { headers });
        const out = new Headers(resp.headers);
        out.set("Access-Control-Allow-Origin", "*");
        out.set("Cache-Control", "no-store");
        return new Response(resp.body, { status: resp.status, headers: out });
      } catch (err) {
        return new Response(
          JSON.stringify({ code: -1, message: "代理失败" }),
          {
            status: 502,
            headers: { "Content-Type": "application/json; charset=utf-8", ...corsHeaders() },
          }
        );
      }
    }
    return env.ASSETS.fetch(request);
  },
};
