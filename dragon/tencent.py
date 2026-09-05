"""腾讯行情。不封 IP，报价和指数挂了东财时补上。字段对齐东财 ulist，方便 merge_quote。"""

from __future__ import annotations

from typing import Any

import httpx

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def qq_code(code: str) -> str:
    digits = "".join(ch for ch in (code or "") if ch.isdigit()).zfill(6)
    if digits.startswith(("5", "6", "9")):
        return "sh" + digits
    if digits.startswith(("4", "8")):
        return "bj" + digits
    return "sz" + digits


def _num(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def parse_qq_line(line: str) -> dict | None:
    text = (line or "").strip()
    if "=" not in text:
        return None
    body = text.split("=", 1)[1].strip().strip(";").strip().strip('"')
    parts = body.split("~")
    if len(parts) < 39:
        return None
    code = str(parts[2] or "").zfill(6)
    if not code.isdigit():
        return None
    amount = 0.0
    blob = parts[35] if len(parts) > 35 else ""
    if "/" in blob:
        tail = blob.rsplit("/", 1)[-1]
        amount = _num(tail)
    if amount <= 0:
        amount = _num(parts[37] if len(parts) > 37 else 0) * 10000.0
    return {
        "f12": code,
        "f14": str(parts[1] or ""),
        "f2": _num(parts[3]),
        "f18": _num(parts[4]),
        "f17": _num(parts[5]),
        "f5": _num(parts[6]),
        "f3": _num(parts[32]) if len(parts) > 32 else 0.0,
        "f15": _num(parts[33]) if len(parts) > 33 else 0.0,
        "f16": _num(parts[34]) if len(parts) > 34 else 0.0,
        "f6": amount,
        "f8": _num(parts[38]) if len(parts) > 38 else 0.0,
        "f10": _num(parts[49]) if len(parts) > 49 else None,
        "f20": int(_num(parts[44]) * 1e8) if len(parts) > 44 else 0,
        "_src": "tencent",
    }


def parse_qq_text(text: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for line in (text or "").replace("\n", "").split(";"):
        row = parse_qq_line(line)
        if row:
            out[row["f12"]] = row
    return out


def quote_incomplete(quote: dict | None) -> bool:
    if not quote:
        return True
    return not (_num(quote.get("f2")) > 0 and _num(quote.get("f8")) >= 0)


async def qq_quotes(client: httpx.AsyncClient, codes: list[str]) -> dict[str, dict]:
    clean = []
    seen = set()
    for code in codes:
        digits = "".join(ch for ch in (code or "") if ch.isdigit()).zfill(6)
        if digits.isdigit() and digits not in seen:
            seen.add(digits)
            clean.append(digits)
    out: dict[str, dict] = {}
    headers = {"User-Agent": UA, "Referer": "https://gu.qq.com/"}
    for i in range(0, len(clean), 40):
        batch = ",".join(qq_code(c) for c in clean[i : i + 40])
        r = await client.get(f"https://qt.gtimg.cn/q={batch}", headers=headers)
        r.raise_for_status()
        text = r.content.decode("gbk", errors="replace")
        out.update(parse_qq_text(text))
    return out


async def qq_indexes(client: httpx.AsyncClient) -> list[dict]:
    # 000001 在个股接口是平安银行，上证必须带 sh。
    headers = {"User-Agent": UA, "Referer": "https://gu.qq.com/"}
    r = await client.get("https://qt.gtimg.cn/q=sh000001,sz399001,sz399006", headers=headers)
    r.raise_for_status()
    parsed = parse_qq_text(r.content.decode("gbk", errors="replace"))
    names = {"000001": "上证指数", "399001": "深证成指", "399006": "创业板指"}
    out = []
    for code, name in names.items():
        row = parsed.get(code)
        if not row:
            continue
        out.append({"code": code, "name": name, "pct": row.get("f3") or 0, "price": row.get("f2") or 0})
    return out


def board_ladder(zt_rows: list[dict]) -> list[dict[str, int]]:
    counts: dict[int, int] = {}
    for row in zt_rows:
        if not row.get("sealed", True):
            continue
        b = int(row.get("boards") or 1)
        if b <= 0:
            continue
        counts[b] = counts.get(b, 0) + 1
    return [{"boards": b, "count": counts[b]} for b in sorted(counts)]
