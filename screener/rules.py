"""Rules for 'quiet grind' names that still rise on down-market days.

The pattern is not 涨停接力. It is: small green candles, low turnover,
and a positive close on days when the index is red.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence


# Ignore tiny index wiggles; a real down day should be felt.
INDEX_DOWN_PCT = -0.30
# "几个点" — modest daily gains, not a limit-up impulse.
UP_DAY_MIN_PCT = 0.25
UP_DAY_MAX_PCT = 4.50
# Hard cap so a 7–9% spike cannot sneak through on ChiNext.
HARD_DAILY_CAP_PCT = 7.00
# Quiet turnover band (percent of float). Dead stocks sit near 0.
TURN_MIN_PCT = 0.15
TURN_MAX_PCT = 4.50
TURN_MEDIAN_MAX_PCT = 4.00
# Volume today vs 20-session average.
VOL_RATIO_MAX = 2.00
# Share of index-down days the stock itself closed green.
MIN_RS_UP_RATE = 0.60
MIN_DOWN_DAYS = 3
MIN_WINDOW_BARS = 12
MAX_WINDOW_DRAWDOWN_PCT = 8.00
NEAR_LIMIT_GAP_PCT = 0.50


@dataclass(frozen=True)
class Bar:
    d: str
    o: float
    c: float
    h: float
    l: float
    v: float  # lots (手)


@dataclass
class QuietMetrics:
    ok: bool
    reason: str = ""
    window_ret_pct: float = 0.0
    up_day_ratio: float = 0.0
    avg_up_pct: float = 0.0
    max_up_pct: float = 0.0
    avg_turn_pct: float = 0.0
    median_turn_pct: float = 0.0
    last_turn_pct: float = 0.0
    vol_ratio: float = 0.0
    max_dd_pct: float = 0.0
    rs_up_rate: float = 0.0
    rs_mean_pct: float = 0.0
    rs_excess_pct: float = 0.0
    down_days: int = 0
    up_on_down: int = 0
    near_limit_days: int = 0
    ma10_ok: bool = False
    score: float = 0.0
    down_day_detail: list[dict] = field(default_factory=list)


def board_limit_pct(code: str, name: str) -> float:
    n = name.upper()
    if "ST" in n or "退" in name:
        return 5.0
    c = code.zfill(6)
    if c.startswith(("300", "301", "302", "688", "689")):
        return 20.0
    if c.startswith(("920", "430", "830", "831", "832", "833", "834", "835", "836", "837", "838", "839", "870", "871", "872", "873")):
        return 30.0
    return 10.0


def is_near_limit(ret_pct: float, limit_pct: float, gap: float = NEAR_LIMIT_GAP_PCT) -> bool:
    return ret_pct >= (limit_pct - gap)


def daily_returns(bars: Sequence[Bar]) -> list[float]:
    out = [0.0]
    for i in range(1, len(bars)):
        prev = bars[i - 1].c
        out.append((bars[i].c / prev - 1.0) * 100.0 if prev else 0.0)
    return out


def turnover_pct(volume_lots: float, circ_shares: float) -> float:
    if circ_shares <= 0:
        return 0.0
    return volume_lots * 100.0 / circ_shares * 100.0


def max_drawdown_pct(closes: Sequence[float]) -> float:
    peak = closes[0]
    max_dd = 0.0
    for x in closes:
        if x > peak:
            peak = x
        dd = (x / peak - 1.0) * 100.0
        if dd < max_dd:
            max_dd = dd
    return max_dd


def _median(xs: Sequence[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def _mean(xs: Iterable[float]) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def score_quiet_rs(
    *,
    rs_up_rate: float,
    rs_excess_pct: float,
    avg_up_pct: float,
    avg_turn_pct: float,
    max_dd_pct: float,
    up_day_ratio: float,
    vol_ratio: float,
) -> float:
    """0-100. Higher = closer to quiet grind that ignores down days."""
    rs = max(0.0, min(rs_up_rate, 1.0)) * 34
    excess = max(0.0, min(rs_excess_pct, 2.5)) / 2.5 * 22
    # Prefer ~1-3% up days, fade both tiny noise and 冲高.
    if 0.8 <= avg_up_pct <= 3.2:
        grind = 16
    elif UP_DAY_MIN_PCT <= avg_up_pct <= UP_DAY_MAX_PCT:
        grind = 10
    else:
        grind = 0
    quiet = max(0.0, 1.0 - avg_turn_pct / TURN_MAX_PCT) * 12
    dd = max(0.0, 1.0 + max_dd_pct / MAX_WINDOW_DRAWDOWN_PCT) * 8  # max_dd is negative
    cons = max(0.0, min(up_day_ratio, 1.0)) * 8
    vol = 0.0 if vol_ratio > VOL_RATIO_MAX else max(0.0, 1.0 - (vol_ratio - 1.0) / VOL_RATIO_MAX) * 8
    return round(min(100.0, rs + excess + grind + quiet + dd + cons + vol), 2)


def evaluate_quiet_rs(
    bars: Sequence[Bar],
    index_ret_by_d: dict[str, float],
    *,
    circ_shares: float,
    limit_pct: float,
    window: int = 15,
) -> QuietMetrics:
    if len(bars) < MIN_WINDOW_BARS + 1:
        return QuietMetrics(False, "bars_short")
    use = list(bars[-(window + 1) :])
    # first bar only provides prev close
    body = use[1:]
    rets = []
    prev_c = use[0].c
    for b in body:
        rets.append((b.c / prev_c - 1.0) * 100.0 if prev_c else 0.0)
        prev_c = b.c
    turns = [turnover_pct(b.v, circ_shares) for b in body]
    near_limit = sum(1 for r in rets if is_near_limit(r, limit_pct))
    if near_limit:
        return QuietMetrics(False, "near_limit", near_limit_days=near_limit)
    max_up = max(rets) if rets else 0.0
    if max_up >= HARD_DAILY_CAP_PCT:
        return QuietMetrics(False, "spike", max_up_pct=max_up)

    up_rets = [r for r in rets if r > 0]
    down_idx = []
    for b, r in zip(body, rets):
        iret = index_ret_by_d.get(b.d)
        if iret is None:
            continue
        if iret <= INDEX_DOWN_PCT:
            down_idx.append((b.d, r, iret))
    if len(down_idx) < MIN_DOWN_DAYS:
        return QuietMetrics(False, "few_index_down_days", down_days=len(down_idx))

    up_on_down = sum(1 for _, r, _ in down_idx if r >= UP_DAY_MIN_PCT)
    rs_up_rate = up_on_down / len(down_idx)
    rs_mean = _mean(r for _, r, _ in down_idx)
    rs_excess = _mean(r - iret for _, r, iret in down_idx)
    if rs_up_rate + 1e-9 < MIN_RS_UP_RATE:
        return QuietMetrics(
            False,
            "rs_up_rate",
            rs_up_rate=rs_up_rate,
            rs_mean_pct=round(rs_mean, 3),
            down_days=len(down_idx),
            up_on_down=up_on_down,
        )
    if rs_mean <= 0:
        return QuietMetrics(False, "rs_mean_not_green", rs_mean_pct=round(rs_mean, 3), down_days=len(down_idx))

    avg_turn = _mean(turns)
    med_turn = _median(turns)
    if avg_turn > TURN_MAX_PCT or med_turn > TURN_MEDIAN_MAX_PCT:
        return QuietMetrics(False, "turnover_high", avg_turn_pct=round(avg_turn, 3), median_turn_pct=round(med_turn, 3))
    if avg_turn < TURN_MIN_PCT:
        return QuietMetrics(False, "turnover_dead", avg_turn_pct=round(avg_turn, 3))

    avg_up = _mean(up_rets) if up_rets else 0.0
    if not (UP_DAY_MIN_PCT <= avg_up <= UP_DAY_MAX_PCT):
        return QuietMetrics(False, "avg_up_out_of_band", avg_up_pct=round(avg_up, 3), max_up_pct=round(max_up, 3))

    window_ret = (body[-1].c / body[0].c - 1.0) * 100.0
    if window_ret <= 0:
        return QuietMetrics(False, "window_not_up", window_ret_pct=round(window_ret, 3))

    closes = [b.c for b in body]
    max_dd = max_drawdown_pct(closes)
    if max_dd < -MAX_WINDOW_DRAWDOWN_PCT:
        return QuietMetrics(False, "drawdown", max_dd_pct=round(max_dd, 3), window_ret_pct=round(window_ret, 3))

    vols = [b.v for b in body]
    avg_vol = _mean(vols) or 1.0
    vol_ratio = vols[-1] / avg_vol
    if vol_ratio > VOL_RATIO_MAX:
        return QuietMetrics(False, "volume_spike", vol_ratio=round(vol_ratio, 3))

    ma10 = _mean(closes[-10:]) if len(closes) >= 10 else _mean(closes)
    ma10_ok = body[-1].c >= ma10
    if not ma10_ok:
        return QuietMetrics(False, "below_ma10", window_ret_pct=round(window_ret, 3))

    up_ratio = len(up_rets) / len(rets) if rets else 0.0
    scr = score_quiet_rs(
        rs_up_rate=rs_up_rate,
        rs_excess_pct=rs_excess,
        avg_up_pct=avg_up,
        avg_turn_pct=avg_turn,
        max_dd_pct=max_dd,
        up_day_ratio=up_ratio,
        vol_ratio=vol_ratio,
    )
    return QuietMetrics(
        True,
        "ok",
        window_ret_pct=round(window_ret, 2),
        up_day_ratio=round(up_ratio, 3),
        avg_up_pct=round(avg_up, 2),
        max_up_pct=round(max_up, 2),
        avg_turn_pct=round(avg_turn, 2),
        median_turn_pct=round(med_turn, 2),
        last_turn_pct=round(turns[-1], 2),
        vol_ratio=round(vol_ratio, 2),
        max_dd_pct=round(max_dd, 2),
        rs_up_rate=round(rs_up_rate, 3),
        rs_mean_pct=round(rs_mean, 2),
        rs_excess_pct=round(rs_excess, 2),
        down_days=len(down_idx),
        up_on_down=up_on_down,
        near_limit_days=0,
        ma10_ok=True,
        score=scr,
        down_day_detail=[
            {"date": d, "stock_pct": round(r, 2), "index_pct": round(iret, 2)} for d, r, iret in down_idx
        ],
    )


def snapshot_today_quiet(
    *,
    stock_ret_pct: float,
    index_ret_pct: float,
    turnover_pct_today: float,
    limit_pct: float,
) -> bool:
    """Single-day gate: index red, stock quietly green, not near limit."""
    if index_ret_pct > INDEX_DOWN_PCT:
        return False
    if not (UP_DAY_MIN_PCT <= stock_ret_pct <= UP_DAY_MAX_PCT):
        return False
    if is_near_limit(stock_ret_pct, limit_pct):
        return False
    if not (TURN_MIN_PCT <= turnover_pct_today <= TURN_MAX_PCT):
        return False
    return True
