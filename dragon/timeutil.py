from __future__ import annotations

from datetime import datetime, timedelta, timezone


def china_tz() -> timezone:
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("Asia/Shanghai")
    except Exception:  # noqa: BLE001
        return timezone(timedelta(hours=8), name="CST")


CN = china_tz()


def now_cn() -> datetime:
    return datetime.now(CN)


def yyyymmdd(dt: datetime | None = None) -> str:
    return (dt or now_cn()).strftime("%Y%m%d")


def fmt_hhmmss(raw: int | str | None) -> str:
    try:
        n = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "-"
    if n <= 0:
        return "-"
    s = f"{n:06d}"
    return f"{s[0:2]}:{s[2:4]}:{s[4:6]}"


def market_session(now: datetime | None = None) -> dict:
    now = now or now_cn()
    t = now.hour * 100 + now.minute
    weekday = now.weekday()
    if weekday >= 5:
        phase = "休市"
    elif t < 915:
        phase = "盘前"
    elif t < 925:
        phase = "集合竞价"
    elif t < 930:
        phase = "竞价撮合"
    elif t < 1130:
        phase = "上午交易"
    elif t < 1300:
        phase = "午间休市"
    elif t < 1500:
        phase = "下午交易"
    else:
        phase = "已收盘"
    live = phase in {"集合竞价", "竞价撮合", "上午交易", "下午交易"}
    return {
        "phase": phase,
        "live": live,
        "now": now.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday": weekday,
    }


def recent_weekdays(n: int = 10, start: datetime | None = None) -> list[str]:
    cur = start or now_cn()
    out: list[str] = []
    for _ in range(n * 2):
        if cur.weekday() < 5:
            out.append(cur.strftime("%Y%m%d"))
            if len(out) >= n:
                break
        cur -= timedelta(days=1)
    return out
