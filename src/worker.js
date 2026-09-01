/**
 * Cloudflare Worker: static web/ + proxy Tencent/Sina (same origin, no CORS).
 */
const TX_QUOTE = ["https://web.sqt.gtimg.cn/q=", "https://qt.gtimg.cn/q="];
const TX_KLINE = [
  "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=",
  "https://ifzq.gtimg.cn/appstock/app/fqkline/get?param=",
];
const SINA_NODES = new Set(["sh_a", "sz_a", "cyb"]);
const SINA_COUNT =
    "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeStockCount?node=";
const SINA_LIST =
    "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData";

function sinaNode(raw) {
  const n = (raw || "").trim();
  return SINA_NODES.has(n) ? n : "cyb";
}
function thsCode(raw) {
  const n = String(raw || "").replace(/^(sh|sz|bj)/i, "");
  return /^\d{6}$/.test(n) ? n : "";
}

async function proxy(url, init = {}) {
  const r = await fetch(url, {
    ...init,
    headers: {
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      Referer: "https://finance.sina.com.cn/",
      ...(init.headers || {}),
    },
  });
  const headers = new Headers(r.headers);
  headers.set("access-control-allow-origin", "*");
  headers.set("cache-control", "no-store");
  return new Response(r.body, { status: r.status, headers });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const p = url.pathname;

    if (p === "/api/quote") {
      const q = url.searchParams.get("q") || "";
      if (!q) return new Response("missing q", { status: 400 });
      let last;
      for (const base of TX_QUOTE) {
        try {
          return await proxy(base + q);
        } catch (e) {
          last = e;
        }
      }
      return new Response(String(last || "quote fail"), { status: 502 });
    }

    if (p === "/api/kline") {
      const code = url.searchParams.get("code") || "sh600519";
      const count = url.searchParams.get("count") || "130";
      const param = `${code},day,,,${count},qfq`;
      let last;
      for (const base of TX_KLINE) {
        try {
          return await proxy(base + param);
        } catch (e) {
          last = e;
        }
      }
      return new Response(String(last || "kline fail"), { status: 502 });
    }

    if (p === "/api/sina/count") {
      return proxy(SINA_COUNT + sinaNode(url.searchParams.get("node")));
    }

    if (p === "/api/sina/list") {
      const page = url.searchParams.get("page") || "1";
      const num = url.searchParams.get("num") || "80";
      const node = sinaNode(url.searchParams.get("node"));
      const u = `${SINA_LIST}?page=${page}&num=${num}&sort=symbol&asc=1&node=${node}&symbol=&_s_r_a=page`;
      return proxy(u);
    }

    if (p === "/api/ths/kline") {
      const code = thsCode(url.searchParams.get("code"));
      if (!code) return new Response("bad code", { status: 400 });
      const ths = `https://d.10jqka.com.cn/v8/line/hs_${code}/01/last180.js`;
      const r = await fetch(ths, {
        headers: {
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          Referer: `http://stockpage.10jqka.com.cn/${code}/`,
        },
      });
      let body = await r.text();
      const i = body.indexOf("{");
      const j = body.lastIndexOf("}");
      if (i >= 0 && j > i) body = body.slice(i, j + 1);
      return new Response(body, {
        status: r.status,
        headers: {
          "content-type": "application/json; charset=utf-8",
          "access-control-allow-origin": "*",
          "cache-control": "no-store",
        },
      });
    }

    if (env.ASSETS) return env.ASSETS.fetch(request);
    return new Response("not found", { status: 404 });
  },
};
