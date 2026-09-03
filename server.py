#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真龙识别本地服务：静态页 + 实时/历史复盘接口。"""

from __future__ import annotations

import argparse
import json
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from engine import build_review, list_known_dates, today_str

ROOT = Path(__file__).resolve().parent
HOST = "0.0.0.0"
PORT = 8765


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        print(f"[zhenlong] {self.address_string()} {fmt % args}")

    def _json(self, payload, status=200):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/api/health":
            self._json({"ok": True, "today": today_str()})
            return
        if path == "/api/dates":
            self._json({"dates": list_known_dates(), "today": today_str()})
            return
        if path == "/api/review":
            qs = parse_qs(parsed.query)
            date = (qs.get("date") or [today_str()])[0]
            refresh = (qs.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            try:
                review = build_review(date, refresh=refresh)
                self._json(review)
            except Exception as exc:
                self._json({"ok": False, "error": str(exc), "date": date}, status=502)
            return
        if path in ("/", "/index.html"):
            self.path = "/index.html"
        super().do_GET()


def open_browser_later(url: str, delay: float = 1.2) -> None:
    def _open() -> None:
        time.sleep(delay)
        webbrowser.open(url)

    threading.Thread(target=_open, daemon=True).start()


def main():
    parser = argparse.ArgumentParser(description="Zhenlong live review server")
    parser.add_argument("--open", action="store_true", help="Open browser after start")
    args = parser.parse_args()

    url = f"http://127.0.0.1:{PORT}/"
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[zhenlong] {url}  (bind {HOST})")
    if args.open:
        open_browser_later(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[zhenlong] stop")
        httpd.server_close()


if __name__ == "__main__":
    main()
