from __future__ import annotations

from typing import Any

import httpx

from app.providers.base import MarketProvider, normalize_code, to_em_secid

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/",
}


class EastMoneyProvider(MarketProvider):
    name = "eastmoney"
    display_name = "东方财富 (免费)"

    def __init__(self) -> None:
        self._client = httpx.Client(timeout=20.0, headers=UA, follow_redirects=True)

    def health(self) -> dict[str, Any]:
        try:
            # lightweight ping instead of full pool
            r = self._client.get(
                "https://push2.eastmoney.com/api/qt/stock/get?secid=1.000001&fields=f43",
                timeout=8.0,
            )
            ok = r.status_code == 200
            return {"ok": ok, "provider": self.name, "detail": f"http={r.status_code}"}
        except Exception as e:
            return {"ok": False, "provider": self.name, "detail": str(e)}

    def limit_up_pool(self, trade_date: str) -> list[dict[str, Any]]:
        date = trade_date.replace("-", "")
        if not date:
            from datetime import datetime

            date = datetime.now().strftime("%Y%m%d")
        url = (
            "https://push2ex.eastmoney.com/getTopicZTPool"
            "?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
            f"&Pageindex=0&pagesize=200&sort=fbt%3Aasc&date={date}"
        )
        r = self._client.get(url)
        r.raise_for_status()
        payload = r.json().get("data") or {}
        pool = payload.get("pool") or []
        out: list[dict[str, Any]] = []
        for x in pool:
            market = "sh" if x.get("m") == 1 else "sz"
            code = str(x.get("c", "")).zfill(6)
            zttj = x.get("zttj") or {}
            boards = int(x.get("lbc") or zttj.get("ct") or 1)
            out.append(
                {
                    "code": code,
                    "market": market,
                    "symbol": f"{market}{code}",
                    "name": x.get("n") or "",
                    "price": (x.get("p") or 0) / 1000.0,
                    "change_pct": float(x.get("zdp") or 0),
                    "boards": boards,
                    "boards_days": int(zttj.get("days") or boards),
                    "first_time": _fmt_hm(x.get("fbt")),
                    "last_time": _fmt_hm(x.get("lbt")),
                    "amount": float(x.get("amount") or 0),
                    "float_mv": float(x.get("ltsz") or 0),
                    "turnover": float(x.get("hs") or 0),
                    "industry": x.get("hybk") or "未分类",
                    "fund": float(x.get("fund") or 0),
                    "break_count": int(x.get("zbc") or 0),
                    "trade_date": str(payload.get("qdate") or date),
                    "source": self.name,
                }
            )
        return out

    def quote(self, code: str) -> dict[str, Any]:
        secid = to_em_secid(code)
        url = (
            "https://push2.eastmoney.com/api/qt/stock/get"
            f"?secid={secid}&fields=f43,f44,f45,f46,f47,f48,f57,f58,f60,f169,f170"
        )
        r = self._client.get(url)
        r.raise_for_status()
        d = r.json().get("data") or {}
        m, pure = normalize_code(code)
        return {
            "code": pure,
            "market": m,
            "name": d.get("f58") or "",
            "price": _div(d.get("f43"), 100),
            "pre_close": _div(d.get("f60"), 100),
            "open": _div(d.get("f46"), 100),
            "high": _div(d.get("f44"), 100),
            "low": _div(d.get("f45"), 100),
            "change_pct": float(d.get("f170") or 0) / 100.0 if d.get("f170") is not None else 0,
            "amount": float(d.get("f48") or 0),
            "volume": float(d.get("f47") or 0),
            "source": self.name,
        }

    def depth(self, code: str) -> dict[str, Any]:
        secid = to_em_secid(code)
        url = (
            "https://push2.eastmoney.com/api/qt/stock/get"
            f"?secid={secid}&fields=f19,f20,f17,f18,f15,f16,f13,f14,f11,f12,"
            f"f39,f40,f37,f38,f35,f36,f33,f34,f31,f32"
        )
        r = self._client.get(url)
        r.raise_for_status()
        d = r.json().get("data") or {}
        asks = [
            {"price": _div(d.get(p), 100), "volume": float(d.get(v) or 0)}
            for p, v in [("f19", "f20"), ("f17", "f18"), ("f15", "f16"), ("f13", "f14"), ("f11", "f12")]
        ]
        bids = [
            {"price": _div(d.get(p), 100), "volume": float(d.get(v) or 0)}
            for p, v in [("f39", "f40"), ("f37", "f38"), ("f35", "f36"), ("f33", "f34"), ("f31", "f32")]
        ]
        m, pure = normalize_code(code)
        return {"code": pure, "market": m, "bids": bids, "asks": asks, "source": self.name}

    def daily_bars(self, code: str, count: int = 120) -> list[dict[str, Any]]:
        secid = to_em_secid(code)
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57"
            f"&klt=101&fqt=1&end=20500101&lmt={count}"
        )
        r = self._client.get(url)
        r.raise_for_status()
        kl = ((r.json().get("data") or {}).get("klines") or [])
        out = []
        for row in kl:
            parts = row.split(",")
            if len(parts) < 7:
                continue
            out.append(
                {
                    "date": parts[0],
                    "open": float(parts[1]),
                    "close": float(parts[2]),
                    "high": float(parts[3]),
                    "low": float(parts[4]),
                    "volume": float(parts[5]),
                    "amount": float(parts[6]),
                }
            )
        return out

    def minute_bars(self, code: str, period: str = "1m") -> list[dict[str, Any]]:
        secid = to_em_secid(code)
        klt = "5" if str(period).startswith("5") else "1"
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57"
            f"&klt={klt}&fqt=1&end=20500101&lmt=240"
        )
        r = self._client.get(url)
        r.raise_for_status()
        kl = ((r.json().get("data") or {}).get("klines") or [])
        out = []
        for row in kl:
            parts = row.split(",")
            if len(parts) < 6:
                continue
            out.append(
                {
                    "time": parts[0],
                    "open": float(parts[1]),
                    "close": float(parts[2]),
                    "high": float(parts[3]),
                    "low": float(parts[4]),
                    "volume": float(parts[5]),
                }
            )
        return out

    def intraday(self, code: str) -> list[dict[str, Any]]:
        secid = to_em_secid(code)
        url = (
            "https://push2.eastmoney.com/api/qt/stock/trends2/get"
            f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13"
            f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58&iscr=0&ndays=1"
        )
        r = self._client.get(url)
        r.raise_for_status()
        trends = ((r.json().get("data") or {}).get("trends") or [])
        out = []
        for row in trends:
            parts = row.split(",")
            if len(parts) < 3:
                continue
            t = parts[0]
            time_label = t.split(" ")[-1] if " " in t else t
            out.append(
                {
                    "time": time_label,
                    "price": float(parts[1]),
                    "avg_price": float(parts[2]) if parts[2] else float(parts[1]),
                    "volume": float(parts[5]) if len(parts) > 5 else 0,
                }
            )
        return out


def _div(v: Any, n: float) -> float:
    if v is None:
        return 0.0
    try:
        return float(v) / n
    except Exception:
        return 0.0


def _fmt_hm(v: Any) -> str:
    if v is None:
        return ""
    s = str(int(v)).zfill(6)
    return f"{s[:-4]}:{s[-4:-2]}:{s[-2:]}"