"""Market data: Sina snapshot + Tencent daily bars. Stdlib only."""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from screener.rules import Bar

ctx = ssl._create_unverified_context()
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
SINA_NODE = (
    "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "Market_Center.getHQNodeData"
)
TENCENT_KLINE = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline?param={symbol},day,,,{n},"


def _get(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Referer": "https://finance.sina.com.cn/"},
    )
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()


def fetch_a_share_snapshot(sleep: float = 0.12) -> list[dict]:
    """Paginate Sina hs_a. Fallback: empty list (caller may use a cache file)."""
    rows: list[dict] = []
    seen: set[str] = set()
    page = 1
    while True:
        url = (
            f"{SINA_NODE}?page={page}&num=80&sort=symbol&asc=1&node=hs_a"
            "&symbol=&_s_r_a=page"
        )
        try:
            raw = _get(url).decode("utf-8", "replace")
        except Exception:
            break
        if not raw.startswith("["):
            break
        chunk = json.loads(raw)
        if not chunk:
            break
        for s in chunk:
            sym = str(s.get("symbol") or "")
            if not sym or sym in seen:
                continue
            seen.add(sym)
            rows.append(s)
        if len(chunk) < 80:
            break
        page += 1
        time.sleep(sleep)
        if page > 80:
            break
    return rows


def tencent_symbol(code: str, symbol: str | None = None) -> str:
    if symbol and symbol[:2] in ("sh", "sz", "bj"):
        return symbol
    c = code.zfill(6)
    if c.startswith(("6", "9")):
        return "sh" + c
    return "sz" + c


def fetch_kline(symbol: str, n: int = 40) -> list[Bar]:
    url = TENCENT_KLINE.format(symbol=symbol, n=n)
    data = json.loads(_get(url, timeout=12).decode("utf-8", "replace"))
    node = (data.get("data") or {}).get(symbol) or {}
    raw = node.get("day") or node.get("qfqday") or []
    out: list[Bar] = []
    for b in raw:
        if len(b) < 6:
            continue
        out.append(
            Bar(
                d=str(b[0])[:10],
                o=float(b[1]),
                c=float(b[2]),
                h=float(b[3]),
                l=float(b[4]),
                v=float(b[5]),
            )
        )
    return out


def fetch_index_returns(symbol: str = "sh000300", n: int = 40) -> dict[str, float]:
    bars = fetch_kline(symbol, n=n)
    out: dict[str, float] = {}
    for i in range(1, len(bars)):
        prev = bars[i - 1].c
        if prev:
            out[bars[i].d] = (bars[i].c / prev - 1.0) * 100.0
    return out


def fetch_klines_many(
    symbols: list[str],
    *,
    n: int = 40,
    workers: int = 16,
    progress: Callable[[int, int, int], None] | None = None,
    cache_dir: Path | None = None,
) -> dict[str, list[Bar]]:
    cache_dir = Path(cache_dir) if cache_dir else None
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, list[Bar]] = {}
    errors = 0
    done = 0
    total = len(symbols)

    def one(sym: str) -> tuple[str, list[Bar] | None]:
        if cache_dir:
            fp = cache_dir / f"{sym}.json"
            if fp.exists():
                raw = json.loads(fp.read_text(encoding="utf-8"))
                return sym, [Bar(**x) for x in raw]
        bars = fetch_kline(sym, n=n)
        if cache_dir:
            fp = cache_dir / f"{sym}.json"
            fp.write_text(
                json.dumps([b.__dict__ for b in bars], ensure_ascii=False),
                encoding="utf-8",
            )
        return sym, bars

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(one, s) for s in symbols]
        for fut in as_completed(futs):
            done += 1
            try:
                sym, bars = fut.result()
                if bars:
                    result[sym] = bars
                else:
                    errors += 1
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError):
                errors += 1
            if progress and (done % 200 == 0 or done == total):
                progress(done, total, errors)
    return result
