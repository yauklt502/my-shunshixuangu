#!/usr/bin/env node
"use strict";
const http = require("http");
const fs = require("fs");
const path = require("path");

const WEB = path.join(__dirname, "web");
const PORT = Number(process.env.PORT || 8000);
const HOST = process.env.HOST || "127.0.0.1";
const UPSTREAM = "https://fuyao.aicubes.cn";
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".json": "application/json; charset=utf-8",
};

function send(res, status, headers, body) {
  res.writeHead(status, {
    "Cache-Control": "no-store",
    "Access-Control-Allow-Origin": "*",
    ...headers,
  });
  res.end(body);
}

const server = http.createServer(async (req, res) => {
  if (req.method === "OPTIONS") {
    return send(res, 204, {
      "Access-Control-Allow-Headers": "X-api-key, Content-Type",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
    });
  }

  const url = new URL(req.url || "/", `http://${HOST}:${PORT}`);
  if (url.pathname.startsWith("/api/")) {
    try {
      const headers = { "User-Agent": "duanxian-xunlong-local/1.2" };
      const key = req.headers["x-api-key"];
      if (key) headers["X-api-key"] = key;
      const upstream = await fetch(UPSTREAM + url.pathname + url.search, { headers });
      const buf = Buffer.from(await upstream.arrayBuffer());
      const out = {
        "Content-Type": upstream.headers.get("content-type") || "application/json",
      };
      for (const h of ["x-ratelimit-remaining", "x-ratelimit-limit", "x-ratelimit-reset"]) {
        const v = upstream.headers.get(h);
        if (v) out[h] = v;
      }
      return send(res, upstream.status, out, buf);
    } catch (err) {
      return send(
        res,
        502,
        { "Content-Type": "application/json; charset=utf-8" },
        Buffer.from(JSON.stringify({ code: -1, message: "代理失败: " + err }), "utf8")
      );
    }
  }

  let rel = url.pathname === "/" || url.pathname === "/dragon-monitor.html" ? "/index.html" : url.pathname;
  const file = path.normalize(path.join(WEB, rel));
  if (!file.startsWith(WEB)) return send(res, 403, { "Content-Type": "text/plain" }, "Forbidden");
  fs.readFile(file, (err, data) => {
    if (err) return send(res, 404, { "Content-Type": "text/plain; charset=utf-8" }, "Not found");
    send(res, 200, { "Content-Type": MIME[path.extname(file)] || "application/octet-stream" }, data);
  });
});

server.listen(PORT, HOST, () => {
  console.error("短线寻龙已启动  http://%s:%s/", HOST, PORT);
  console.error("数据接口经本地代理转发至 %s", UPSTREAM);
  console.error("按 Ctrl+C 停止");
});
