import express from "express";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { fetchKline, fetchMinute, tdxAvailable } from "./tdx.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const dist = path.join(root, "dist");
const isProd =
  process.env.NODE_ENV === "production" ||
  (process.env.NODE_ENV !== "development" && fs.existsSync(path.join(dist, "index.html")));
const port = Number(process.env.PORT || (isProd ? 3000 : 8787));
const host = process.env.HOST || (isProd ? "127.0.0.1" : "0.0.0.0");

const HOSTS = {
  his: "https://apphis.longhuvip.com/w1/api/index.php",
  hq: "https://apphwhq.longhuvip.com/w1/api/index.php",
  shhq: "https://apphwshhq.longhuvip.com/w1/api/index.php",
  lhb: "https://applhb.longhuvip.com/w1/api/index.php",
};

const UA =
  "Dalvik/2.1.0 (Linux; U; Android 9; SHARK PRS-A0 Build/PQ3A.190605.01141736)";

const app = express();
app.disable("x-powered-by");
app.use(express.json({ limit: "1mb" }));

app.get("/api/health", (_req, res) => {
  res.json({ ok: true, tdx: tdxAvailable() });
});

app.get("/api/tdx/kline", async (req, res) => {
  try {
    const code = String(req.query.code || "").trim();
    if (!code) {
      res.status(400).json({ errcode: "400", errmsg: "缺少 code" });
      return;
    }
    const period = String(req.query.period || "day");
    const count = Math.min(800, Math.max(10, Number(req.query.count) || 120));
    const result = await fetchKline(code, period, count);
    res.json({ errcode: "0", ...result });
  } catch (error) {
    res.status(502).json({ errcode: "502", errmsg: error?.message || "通达信日K获取失败" });
  }
});

app.get("/api/tdx/minute", async (req, res) => {
  try {
    const code = String(req.query.code || "").trim();
    if (!code) {
      res.status(400).json({ errcode: "400", errmsg: "缺少 code" });
      return;
    }
    const date = String(req.query.date || "").replaceAll("-", "");
    const result = await fetchMinute(code, date);
    res.json({ errcode: "0", ...result });
  } catch (error) {
    res.status(502).json({ errcode: "502", errmsg: error?.message || "通达信分时获取失败" });
  }
});

app.post("/api/kpl", async (req, res) => {
  try {
    const { host: dataHost, method = "GET", params = {}, common = {} } = req.body || {};
    const url = HOSTS[dataHost];
    if (!url) {
      res.status(400).json({ errcode: "400", errmsg: "未知的数据源" });
      return;
    }

    const merged = {};
    for (const [key, value] of Object.entries({ ...common, ...params })) {
      if (value === undefined || value === null || value === "") continue;
      merged[key] = String(value);
    }

    const search = new URLSearchParams(merged);
    const verb = String(method).toUpperCase() === "POST" ? "POST" : "GET";
    const target = verb === "GET" ? `${url}?${search.toString()}` : url;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20000);

    const response = await fetch(target, {
      method: verb,
      headers: {
        "User-Agent": UA,
        Connection: "Keep-Alive",
        Accept: "*/*",
        "Accept-Encoding": "gzip",
        ...(verb === "POST"
          ? { "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8" }
          : {}),
      },
      body: verb === "POST" ? search.toString() : undefined,
      signal: controller.signal,
    });
    clearTimeout(timer);

    const text = await response.text();
    if (!text) {
      res.status(502).json({ errcode: "502", errmsg: "上游返回空响应" });
      return;
    }

    let data;
    try {
      data = JSON.parse(text);
    } catch {
      res.status(502).json({
        errcode: "502",
        errmsg: `上游返回非 JSON（HTTP ${response.status}）`,
      });
      return;
    }

    res.json(data);
  } catch (error) {
    const message =
      error?.name === "AbortError" ? "请求超时" : error?.message || "代理失败";
    res.status(502).json({ errcode: "502", errmsg: message });
  }
});

if (isProd) {
  if (!fs.existsSync(path.join(dist, "index.html"))) {
    console.error(`[kpl-proxy] missing ${path.join(dist, "index.html")}. Run npm run build first.`);
    process.exit(1);
  }
  app.use(express.static(dist));
  app.use((req, res, next) => {
    if (req.method !== "GET" && req.method !== "HEAD") {
      next();
      return;
    }
    if (req.path.startsWith("/api")) {
      next();
      return;
    }
    res.sendFile(path.join(dist, "index.html"));
  });
}

app.listen(port, host, () => {
  const origin = `http://${host === "0.0.0.0" ? "127.0.0.1" : host}:${port}`;
  console.log(`[kpl-proxy] ${origin} (${isProd ? "prod" : "dev"})`);
});
