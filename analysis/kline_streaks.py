"""用不复权日 K 识别涨停与连板（东方财富涨停池历史只有约 15 个交易日）。"""

from __future__ import annotations

import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Optional

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

_lock = Lock()


def _log(msg: str) -> None:
    with _lock:
        print(msg, flush=True)


def tx_symbol(code: str) -> str:
    if code.startswith(("600", "601", "603", "605", "688", "689")):
        return f"sh{code}"
    if code.startswith(("8", "4", "92")):
        return f"bj{code}"
    return f"sz{code}"


def zt_threshold(code: str, name: str) -> float:
    n = (name or "").upper()
    st = "ST" in n
    if code.startswith(("8", "4", "92")):
        return 0.05 if st else 0.30
    if code.startswith(("300", "301", "688", "689")):
        return 0.05 if st else 0.20
    return 0.05 if st else 0.10


def limit_up_price(preclose: float, thr: float) -> float:
    return float(
        (Decimal(str(preclose)) * (Decimal("1") + Decimal(str(thr)))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    )


def is_limit_up(preclose: float, close: float, high: float, volume: float, thr: float) -> bool:
    if volume <= 0 or preclose <= 0:
        return False
    lp = limit_up_price(preclose, thr)
    # 允许 1 分钱的价差/截断误差；收盘须在涨停价附近
    if close + 1e-8 >= lp - 0.011 and high + 1e-8 >= lp - 0.011:
        return True
    pct = close / preclose - 1
    return pct >= thr - 0.0012


def fetch_universe(session: requests.Session, cache_dir: Path) -> list[dict]:
    fp = cache_dir / "universe.json"
    if fp.exists():
        return json.loads(fp.read_text(encoding="utf-8"))
    rows: list[dict] = []
    fs = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:3136"
    page = 1
    total = None
    while True:
        r = session.get(
            "http://push2delay.eastmoney.com/api/qt/clist/get",
            params={
                "pn": str(page),
                "pz": "100",
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f12",
                "fs": fs,
                "fields": "f12,f14,f2,f20,f21",
            },
            timeout=25,
        )
        r.raise_for_status()
        data = (r.json() or {}).get("data") or {}
        total = total or int(data.get("total") or 0)
        diff = data.get("diff") or []
        if not diff:
            break
        for it in diff:
            code = str(it.get("f12") or "").zfill(6)
            if code.startswith(("200", "900")):
                continue
            rows.append(
                {
                    "code": code,
                    "name": it.get("f14") or "",
                    "price": it.get("f2"),
                    "total_mv": it.get("f20"),
                    "float_mv": it.get("f21"),
                }
            )
        if page * 100 >= total:
            break
        page += 1
        if page % 10 == 0:
            _log(f"  股票列表 {len(rows)}/{total}")
        time.sleep(0.05)
    fp.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def fetch_kline(session: requests.Session, code: str, cache_dir: Path, bars: int = 130) -> list[list]:
    fp = cache_dir / f"{code}.json"
    if fp.exists():
        return json.loads(fp.read_text(encoding="utf-8"))
    last: Optional[Exception] = None
    for i in range(4):
        try:
            r = session.get(
                "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
                params={"param": f"{tx_symbol(code)},day,,,{bars},bfq"},
                timeout=20,
            )
            r.raise_for_status()
            payload = r.json() or {}
            block = (payload.get("data") or {}).get(tx_symbol(code)) or {}
            day = block.get("day") or block.get("bfqday") or []
            out = []
            for row in day:
                out.append(
                    [
                        str(row[0]).replace("-", ""),
                        float(row[1]),
                        float(row[2]),
                        float(row[3]),
                        float(row[4]),
                        float(row[5]) if len(row) > 5 else 0.0,
                    ]
                )
            fp.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
            return out
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(0.6 * (2 ** i))
    raise RuntimeError(f"kline {code}: {last}")


_tls = threading.local()


def _thread_session() -> requests.Session:
    sess = getattr(_tls, "session", None)
    if sess is None:
        sess = requests.Session()
        sess.headers.update(HEADERS)
        _tls.session = sess
    return sess


def fetch_all_klines(
    session_factory: Callable[[], requests.Session],
    codes: list[str],
    cache_dir: Path,
    workers: int = 16,
) -> dict[str, list[list]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    out: dict[str, list[list]] = {}
    done = 0
    n = len(codes)

    def job(code: str) -> tuple[str, list[list]]:
        return code, fetch_kline(_thread_session(), code, cache_dir)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(job, c): c for c in codes}
        for fut in as_completed(futs):
            c = futs[fut]
            done += 1
            try:
                code, bars = fut.result()
                out[code] = bars
            except Exception as e:  # noqa: BLE001
                _log(f"  kline fail {c}: {e}")
                out[c] = []
            if done % 400 == 0 or done == n:
                _log(f"  日K {done}/{n}")
    return out


def detect_streaks(
    code: str,
    name: str,
    bars: list[list],
    window_dates: list[str],
) -> list[dict[str, Any]]:
    """返回与 90 日窗口有交集、且高度>=1 的连板周期。"""
    if not bars or len(bars) < 2:
        return []
    window = set(window_dates)
    thr = zt_threshold(code, name)
    runs: list[list[dict]] = []
    cur: list[dict] = []
    for i in range(1, len(bars)):
        d, o, c, h, l, v = bars[i]
        prev = bars[i - 1][2]
        zt = is_limit_up(prev, c, h, v, thr)
        rec = {
            "date": d,
            "open": o,
            "close": c,
            "high": h,
            "low": l,
            "volume": v,
            "preclose": prev,
            "pct": (c / prev - 1) * 100 if prev else None,
            "yiziban": bool(v > 0 and abs(o - c) <= 0.011 and abs(h - l) <= 0.011 and zt),
        }
        if zt:
            rec["lianban"] = len(cur) + 1
            cur.append(rec)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)

    out = []
    for run in runs:
        height = len(run)
        days_in = [x for x in run if x["date"] in window]
        if not days_in:
            continue
        # 窗口内见到的最大连板数（含从窗口前延续）
        max_in_window = max(x["lianban"] for x in days_in)
        if max_in_window < 5 and height < 5:
            continue
        peak = max(run, key=lambda x: x["lianban"])
        out.append(
            {
                "code": code,
                "name": name,
                "start": run[0]["date"],
                "end": run[-1]["date"],
                "days_in_window": len(days_in),
                "height": height,
                "height_in_window": max_in_window,
                "peak_date": peak["date"],
                "peak_price": peak["close"],
                "yiziban_days": int(sum(1 for x in run if x["yiziban"])),
                "avg_pct": sum(x["pct"] or 0 for x in run) / len(run),
                "dates": ",".join(x["date"] for x in run),
                "in_window_dates": ",".join(x["date"] for x in days_in),
                "run": run,
            }
        )
    return out
