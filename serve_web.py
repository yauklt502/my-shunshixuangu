#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local server: static web/ + Tencent/Sina proxy (same origin)."""
from __future__ import annotations

import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def _web_root() -> Path:
    here = Path(__file__).resolve().parent
    if (here / "index.html").is_file():
        return here
    web = here / "web"
    if (web / "index.html").is_file():
        return web
    return here.parent / "web"


ROOT = _web_root()
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
TX_QUOTE = ["https://web.sqt.gtimg.cn/q=", "https://qt.gtimg.cn/q="]
TX_KLINE = [
    "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=",
    "https://ifzq.gtimg.cn/appstock/app/fqkline/get?param=",
]
SINA_NODES = frozenset({"sh_a", "sz_a", "cyb"})
SINA_COUNT = (
    "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "Market_Center.getHQNodeStockCount?node="
)
SINA_LIST = (
    "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "Market_Center.getHQNodeData"
)


def _sina_node(raw: str) -> str:
    n = (raw or "").strip()
    return n if n in SINA_NODES else "cyb"


def _get(url: str) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://finance.sina.com.cn/"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        ctype = resp.headers.get("Content-Type", "application/octet-stream")
        return resp.status, resp.read(), ctype


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def _send(self, status: int, body: bytes, ctype: str):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/api/quote":
            codes = (q.get("q") or [""])[0]
            last = b"quote fail"
            for base in TX_QUOTE:
                try:
                    status, body, ctype = _get(base + codes)
                    return self._send(status, body, ctype or "text/plain; charset=gbk")
                except Exception as e:
                    last = str(e).encode()
            return self._send(502, last, "text/plain; charset=utf-8")
        if parsed.path == "/api/kline":
            code = (q.get("code") or ["sh600519"])[0]
            count = (q.get("count") or ["130"])[0]
            param = f"{code},day,,,{count},qfq"
            last = b"kline fail"
            for base in TX_KLINE:
                try:
                    status, body, ctype = _get(base + param)
                    return self._send(status, body, ctype or "application/json")
                except Exception as e:
                    last = str(e).encode()
            return self._send(502, last, "text/plain; charset=utf-8")
        if parsed.path == "/api/sina/count":
            node = _sina_node((q.get("node") or ["cyb"])[0])
            try:
                status, body, ctype = _get(SINA_COUNT + node)
                return self._send(status, body, ctype or "text/plain; charset=gbk")
            except Exception as e:
                return self._send(502, str(e).encode(), "text/plain; charset=utf-8")
        if parsed.path == "/api/sina/list":
            page = (q.get("page") or ["1"])[0]
            num = (q.get("num") or ["80"])[0]
            node = _sina_node((q.get("node") or ["cyb"])[0])
            url = (
                f"{SINA_LIST}?page={page}&num={num}&sort=symbol&asc=1&node={node}"
                f"&symbol=&_s_r_a=page"
            )
            try:
                status, body, ctype = _get(url)
                return self._send(status, body, ctype or "application/json; charset=gbk")
            except Exception as e:
                return self._send(502, str(e).encode(), "text/plain; charset=utf-8")
        return super().do_GET()


if __name__ == "__main__":
    port = 8787
    print(f"打开 http://127.0.0.1:{port}/")
    print(f"页面目录 {ROOT}")
    print("点「扫描主板」或「扫描创业板」，只扫该板块非 ST，不会扫全市场。")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
