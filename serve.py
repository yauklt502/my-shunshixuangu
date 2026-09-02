#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""短线寻龙 local server: static files + Tonghuashun API proxy."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "web")
UPSTREAM = "https://fuyao.aicubes.cn"
PORT = int(os.environ.get("PORT", "8000"))
HOST = os.environ.get("HOST", "127.0.0.1")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB, **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "X-api-key, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path.startswith("/api/"):
            return self._proxy()
        if path in ("/", "/dragon-monitor.html"):
            self.path = "/index.html" + (("?" + self.path.split("?", 1)[1]) if "?" in self.path else "")
        return super().do_GET()

    def _proxy(self):
        url = UPSTREAM + self.path
        headers = {"User-Agent": "duanxian-xunlong-local/1.2"}
        key = self.headers.get("X-api-key") or self.headers.get("X-Api-Key")
        if key:
            headers["X-api-key"] = key
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                self.send_response(resp.status)
                ctype = resp.headers.get("Content-Type", "application/json")
                self.send_header("Content-Type", ctype)
                for name in ("X-RateLimit-Remaining", "X-RateLimit-Limit", "X-RateLimit-Reset"):
                    val = resp.headers.get(name)
                    if val:
                        self.send_header(name, val)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
        except urllib.error.HTTPError as exc:
            body = exc.read()
            self.send_response(exc.code)
            self.send_header(
                "Content-Type",
                exc.headers.get("Content-Type", "application/json; charset=utf-8"),
            )
            for name in ("X-RateLimit-Remaining", "X-RateLimit-Limit"):
                val = exc.headers.get(name)
                if val:
                    self.send_header(name, val)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            payload = json.dumps(
                {"code": -1, "message": "代理失败: %s" % exc},
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)


def main():
    if not os.path.isdir(WEB):
        sys.stderr.write("缺少 web 目录: %s\n" % WEB)
        sys.exit(1)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    url = "http://%s:%s/" % (HOST, PORT)
    sys.stderr.write("短线寻龙已启动  %s\n" % url)
    sys.stderr.write("数据接口经本地代理转发至 %s\n" % UPSTREAM)
    sys.stderr.write("按 Ctrl+C 停止\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("\n已停止\n")
        httpd.server_close()


if __name__ == "__main__":
    main()
