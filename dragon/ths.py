"""同花顺热榜。人气主源，东财整榜备用。两套名次不混算。"""

from __future__ import annotations

from typing import Any

import httpx

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# 1小时更贴盘中；日榜当备用。dq 和 eq 是同一份热榜的两个门口。
HOT_URLS = (
    (
        "hour",
        "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock"
        "?stock_type=a&type=hour&list_type=normal",
    ),
    ("hour", "https://eq.10jqka.com.cn/open/api/hot_list/v1/hot_stock/a/hour/data.txt"),
    (
        "day",
        "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock"
        "?stock_type=a&type=day&list_type=normal",
    ),
    ("day", "https://eq.10jqka.com.cn/open/api/hot_list/v1/hot_stock/a/day/data.txt"),
)


def client_kwargs() -> dict[str, Any]:
    return {
        "headers": {
            "User-Agent": UA,
            "Referer": "https://eq.10jqka.com.cn/",
            "Accept": "application/json,text/plain,*/*",
        },
        "follow_redirects": True,
        "timeout": httpx.Timeout(16.0, connect=7.0),
        "trust_env": False,
    }


def _digits(raw: Any) -> str:
    return "".join(ch for ch in str(raw or "") if ch.isdigit())[-6:].zfill(6)


def _tag(item: dict) -> str:
    tag = item.get("tag")
    if isinstance(tag, dict):
        return str(tag.get("popularity_tag") or "")
    return str(tag or "")


def parse_hot_rows(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    code = data.get("status_code")
    if code not in (None, 0, "0"):
        return []
    rows = ((data.get("data") or {}).get("stock_list")) or []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, item in enumerate(rows, 1):
        if not isinstance(item, dict):
            continue
        stock = _digits(item.get("code"))
        if len(stock) != 6 or not stock.isdigit() or stock in seen:
            continue
        order = item.get("order")
        try:
            rank = int(order) if order not in (None, "") else i
        except (TypeError, ValueError):
            rank = i
        seen.add(stock)
        out.append(
            {
                "rank": rank,
                "code": stock,
                "name": str(item.get("name") or ""),
                "tag": _tag(item),
                "title": str(item.get("analyse_title") or ""),
            }
        )
    return out


def ranks_from_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {str(r["code"]): int(r["rank"]) for r in rows if r.get("code")}


def fuse_popularity(
    ths: dict[str, int] | None,
    em: dict[str, int] | None,
) -> tuple[dict[str, int], str]:
    """同花顺有榜就只用同花顺。东财只在热榜整路挂了时顶上。不把两套名次拼成一张表。"""
    if ths:
        return dict(ths), "tonghuashun"
    if em:
        return dict(em), "eastmoney"
    return {}, ""


async def fetch_hot(client: httpx.AsyncClient) -> dict[str, Any]:
    last: Exception | None = None
    for kind, url in HOT_URLS:
        try:
            r = await client.get(url)
            r.raise_for_status()
            rows = parse_hot_rows(r.json())
            if rows:
                return {"kind": kind, "rows": rows, "ranks": ranks_from_rows(rows)}
        except Exception as exc:  # noqa: BLE001
            last = exc
            continue
    if last is not None:
        raise last
    return {"kind": "", "rows": [], "ranks": {}}
