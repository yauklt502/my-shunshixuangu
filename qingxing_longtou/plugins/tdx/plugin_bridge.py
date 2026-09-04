"""通达信第三方插件桥接占位。

可在本文件实现：
- 调用本地插件 HTTP（如 http://127.0.0.1:端口/snapshot）
- 或 ctypes 加载 DLL

返回结构需符合 TdxSource._from_bridge 约定。
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.request import urlopen


def fetch_market_bundle(trade_date: str) -> dict[str, Any] | None:
    endpoint = (os.environ.get("TDX_PLUGIN_URL") or "").strip()
    if not endpoint:
        return None
    url = endpoint.rstrip("/") + f"?date={trade_date}"
    with urlopen(url, timeout=8) as resp:  # noqa: S310 — 用户显式配置的本地插件地址
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict):
        return None
    return payload
