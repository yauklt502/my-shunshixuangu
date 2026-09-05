#!/usr/bin/env python3
# 等服务真正起来后再打开浏览器，避免 Windows start 把 :5173 端口吃掉
from __future__ import annotations

import sys
import time
import urllib.request
import webbrowser

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5173/"
if not URL.endswith("/"):
    URL += "/"
HEALTH = URL + "api/health"


def ok(u: str) -> bool:
    try:
        with urllib.request.urlopen(u, timeout=1.5) as r:
            return 200 <= getattr(r, "status", 200) < 400
    except Exception:
        return False


def main() -> int:
    for _ in range(90):
        if ok(HEALTH) and ok(URL):
            webbrowser.open(URL)
            print(f"opened {URL}", flush=True)
            return 0
        time.sleep(0.5)
    print(f"timeout waiting for {HEALTH}", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
