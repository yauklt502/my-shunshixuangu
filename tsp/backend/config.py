"""TSP 配置。"""

from __future__ import annotations

import os

TDX_HOST = os.environ.get("TDX_HOST", "115.238.90.165:7709")
TDX_TIMEOUT = float(os.environ.get("TDX_TIMEOUT", "8"))
DEFAULT_SOURCE = os.environ.get("TSP_SOURCE", "eastmoney")
HOST = os.environ.get("TSP_HOST", "127.0.0.1")
PORT = int(os.environ.get("TSP_PORT", "8765"))

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

SOURCES = [
    {"id": "eastmoney", "name": "东方财富", "desc": "涨停池/板块/K线最完整（推荐）"},
    {"id": "tonghuashun", "name": "同花顺", "desc": "同花顺公开涨停 + 腾讯行情"},
    {"id": "tdx", "name": "通达信", "desc": f"eltdx TCP {TDX_HOST}（五档/分时/日K）"},
]
