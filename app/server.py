#!/usr/bin/env python3
"""顺势竞价 · 本地选股软件。

用法:
  python3 app/server.py
  浏览器打开 http://127.0.0.1:8787/
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import traceback
import urllib.parse
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.service import (  # noqa: E402
    STRATEGIES,
    auction_phase,
    preopen_snapshot,
    scan_pool,
)

WEB = Path(__file__).resolve().parent / "web"
FORMULAS = ROOT / "formulas"

_scan_lock = threading.Lock()
_last_scan: dict[str, Any] = {}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[http] " + (fmt % args) + "\n")

    def _json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        q = urllib.parse.parse_qs(parsed.query)

        try:
            if path == "/api/health":
                return self._json(200, {"ok": True, "phase": auction_phase()})
            if path == "/api/phase":
                return self._json(200, {"ok": True, **auction_phase()})
            if path == "/api/strategies":
                return self._json(200, {"ok": True, "strategies": STRATEGIES})
            if path == "/api/formulas":
                items = []
                for p in sorted(FORMULAS.glob("*.txt")):
                    items.append({"name": p.name, "text": p.read_text(encoding="utf-8")})
                return self._json(200, {"ok": True, "formulas": items})
            if path == "/api/last":
                return self._json(200, {"ok": True, "result": _last_scan or None})
            if path == "/api/scan":
                mode = (q.get("mode") or ["weak"])[0]
                top = int((q.get("top") or ["5"])[0])
                if mode not in ("optimized", "wr100", "baseline", "yijin2", "weak"):
                    return self._json(400, {"ok": False, "error": "bad mode"})
                if not _scan_lock.acquire(blocking=False):
                    return self._json(409, {"ok": False, "error": "扫描进行中，请稍候"})
                try:
                    result = scan_pool(mode, top_n=top)
                    _last_scan.clear()
                    _last_scan.update(result)
                    return self._json(200, result)
                finally:
                    _scan_lock.release()
            if path == "/api/preopen":
                mode = (q.get("mode") or ["weak"])[0]
                top = int((q.get("top") or ["5"])[0])
                if mode not in ("optimized", "wr100", "baseline", "yijin2", "weak"):
                    return self._json(400, {"ok": False, "error": "bad mode"})
                if not _scan_lock.acquire(blocking=False):
                    return self._json(409, {"ok": False, "error": "扫描进行中，请稍候"})
                try:
                    result = preopen_snapshot(mode, top_n=top)
                    _last_scan.clear()
                    _last_scan.update(result)
                    return self._json(200, result)
                finally:
                    _scan_lock.release()
        except Exception as exc:  # noqa: BLE001
            return self._json(
                500,
                {"ok": False, "error": str(exc), "trace": traceback.format_exc()[-800:]},
            )

        if path == "/":
            self.path = "/index.html"
        return super().do_GET()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    if not (WEB / "index.html").exists():
        print(f"missing UI: {WEB / 'index.html'}", file=sys.stderr)
        return 1
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"顺势竞价选股  {url}")
    print("Ctrl+C 退出")
    if not args.no_open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
