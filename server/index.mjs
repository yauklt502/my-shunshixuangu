import express from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const isProd = process.env.NODE_ENV === "production";
const port = Number(process.env.PORT || (isProd ? 3000 : 8787));

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
  res.json({ ok: true });
});

app.post("/api/kpl", async (req, res) => {
  try {
    const { host, method = "GET", params = {}, common = {} } = req.body || {};
    const url = HOSTS[host];
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
  const dist = path.join(root, "dist");
  app.use(express.static(dist));
  app.get("*", (_req, res) => {
    res.sendFile(path.join(dist, "index.html"));
  });
}

app.listen(port, "0.0.0.0", () => {
  console.log(`[kpl-proxy] listening on http://0.0.0.0:${port} (${isProd ? "prod" : "dev"})`);
});
