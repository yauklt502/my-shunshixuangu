#!/usr/bin/env python3
"""竞价弱转强回测：仓位干满、持股3天、冲高胜率。

规则（与软件一致，日K近似）:
- 一进二：昨涨停且高度=1，次日开盘未封死，开盘涨幅落在弱转强带
- 二进三：昨涨停且高度=2，开盘带更严
- 首板：昨「炸板代理」(最高触及涨停价附近但收盘未封死)

交易:
- 买入日 D 开盘买（近似竞价）
- 持股 3 个交易日：D / D+1 / D+2，于 D+2 收盘卖
- 仓位干满：当日入选等权占满 100%；组合用「非重叠」串行（持仓中不新开）

研究用，不构成投资建议。
"""

from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

import sys

sys.path.insert(0, str(ROOT))
from auction_screener.rules import is_main_board, is_st, limit_price  # noqa: E402


@dataclass
class WeakParams:
    cat: str = "一进二"  # 首板 / 一进二 / 二进三 / 全部
    open_lo: float = -2.0
    open_hi: float = 2.5
    zbc_max: int = 5
    fbt_max: int = 103000
    hs_max: float = 22.0
    mv_lo: float = 20.0
    mv_hi: float = 120.0
    top_n: int = 1
    hold_days: int = 3  # 含买入日，共 N 根K线后收盘卖 → 卖出偏移 hold_days-1
    cost: float = 0.0015
    prefer_open: float = 1.0  # 排序贴近该开盘涨幅


def load_bars() -> pd.DataFrame:
    kl = pd.read_parquet(DATA / "kline.parquet")
    kl["code"] = kl["code"].astype(str).str.zfill(6)
    kl["date"] = kl["date"].astype(str)
    kl = kl.loc[(kl["open"] > 0) & (kl["close"] > 0)].copy()

    names = pd.read_csv(DATA / "stock_list.csv", dtype={"code": str})
    names["code"] = names["code"].str.zfill(6)
    names["mv_yi"] = pd.to_numeric(names["nmc"], errors="coerce") / 10000.0
    names = names.drop_duplicates("code")
    name_map = dict(zip(names["code"], names["name"]))

    keep = {
        c
        for c in kl["code"].unique()
        if is_main_board(c, name_map.get(c, "")) and not is_st(name_map.get(c, ""))
    }
    k = kl.loc[kl["code"].isin(keep)].sort_values(["code", "date"]).copy()
    k["preclose"] = k.groupby("code")["close"].shift(1)
    k["pct"] = k["close"] / k["preclose"] - 1.0
    k["is_zt"] = (k["pct"] >= 0.095) & (k["close"] >= k["high"] * 0.997) & k["preclose"].notna()
    k["name"] = k["code"].map(name_map).fillna("")

    def board_height(s: pd.Series) -> pd.Series:
        cur, out = 0, []
        for v in s.tolist():
            cur = cur + 1 if v else 0
            out.append(cur)
        return pd.Series(out, index=s.index)

    k["lbc"] = k.groupby("code")["is_zt"].transform(board_height)
    k["one_word"] = k["is_zt"] & (k["low"] >= k["close"] * 0.997)
    k["range_pct"] = (k["high"] - k["low"]) / k["preclose"]
    k["zbc_proxy"] = np.where(
        ~k["is_zt"], 0, np.where(k["one_word"], 0, np.where(k["range_pct"] >= 0.04, 1, 0))
    )
    k["fbt_proxy"] = np.where(
        k["one_word"],
        93000,
        np.where(k["range_pct"] <= 0.02, 100000, np.where(k["range_pct"] <= 0.05, 103000, 140000)),
    )
    # 换手代理：用相对成交量（无流通股本时用20日量分位）
    k["vol_ma20"] = k.groupby("code")["volume"].transform(lambda s: s.rolling(20, min_periods=5).mean())
    k["hs_proxy"] = (k["volume"] / k["vol_ma20"].replace(0, np.nan) * 8.0).clip(0, 40)

    zt_path = DATA / "zt_pool.parquet"
    if zt_path.exists():
        zt = pd.read_parquet(zt_path)
        zt["code"] = zt["code"].astype(str).str.zfill(6)
        zt["date"] = zt["date"].astype(str)
        zt = zt.rename(
            columns={"lbc": "lbc_em", "zbc": "zbc_em", "fbt": "fbt_em", "hs": "hs_em", "ltsz": "ltsz_em"}
        )
        k = k.merge(
            zt[["date", "code", "lbc_em", "zbc_em", "fbt_em", "hs_em", "ltsz_em"]],
            on=["date", "code"],
            how="left",
        )
        k["lbc"] = k["lbc_em"].fillna(k["lbc"]).astype(int)
        k["zbc"] = k["zbc_em"].fillna(k["zbc_proxy"]).astype(int)
        k["fbt"] = k["fbt_em"].fillna(k["fbt_proxy"]).astype(int)
        k["hs"] = k["hs_em"].fillna(k["hs_proxy"])
        k["mv_yi_em"] = k["ltsz_em"] / 1e8
    else:
        k["zbc"] = k["zbc_proxy"].astype(int)
        k["fbt"] = k["fbt_proxy"].astype(int)
        k["hs"] = k["hs_proxy"]
        k["mv_yi_em"] = np.nan

    k = k.merge(names[["code", "mv_yi"]], on="code", how="left")
    k["mv_yi"] = k["mv_yi_em"].fillna(k["mv_yi"])

    # 炸板代理：最高触及涨停附近，收盘未封
    zt_px = [
        limit_price(float(pc), str(c), str(n)) if pc and pc > 0 else 0.0
        for pc, c, n in zip(k["preclose"].fillna(0), k["code"], k["name"])
    ]
    k["zt_price_today"] = zt_px
    k["is_zb"] = (
        k["preclose"].notna()
        & (k["high"] >= k["zt_price_today"] * 0.997)
        & (~k["is_zt"].fillna(False))
        & (k["close"] < k["zt_price_today"] * 0.997)
    )
    return k


def build_signals(k: pd.DataFrame, hold_days: int = 3) -> pd.DataFrame:
    """信号日=昨，买入日=次日；卖出=买入日起 hold_days 根K线后的收盘。"""
    dates = sorted(k["date"].unique())
    idx = {d: i for i, d in enumerate(dates)}

    def shift_date(d: str, n: int) -> str | None:
        i = idx.get(d)
        if i is None or i + n >= len(dates):
            return None
        return dates[i + n]

    rows: list[dict[str, Any]] = []

    # ---- 一进二 / 二进三：昨涨停 ----
    zt = k.loc[k["is_zt"]].copy()
    for r in zt.itertuples(index=False):
        buy_d = shift_date(r.date, 1)
        sell_d = shift_date(r.date, hold_days)  # 昨→买(今)→…→第hold_days日收
        # 持股3天：买入日 D=date+1，卖出日 = D+(3-1)=date+3 → shift from signal = hold_days
        # signal date S, buy S+1, sell close of S+hold_days  where hold_days=3 → S+3 = buy+2
        # buy day sessions: S+1, S+2, S+3 = 3 days. Yes sell = shift_date(S, hold_days)
        if not buy_d or not sell_d:
            continue
        if int(r.lbc) == 1:
            cat = "一进二"
        elif int(r.lbc) == 2:
            cat = "二进三"
        else:
            continue
        rows.append(
            {
                "signal_date": r.date,
                "buy_date": buy_d,
                "sell_date": sell_d,
                "code": r.code,
                "name": r.name,
                "category": cat,
                "src": "zt",
                "lbc": int(r.lbc),
                "zbc": int(r.zbc),
                "fbt": int(r.fbt),
                "hs": float(r.hs) if pd.notna(r.hs) else 0.0,
                "mv_yi": float(r.mv_yi) if pd.notna(r.mv_yi) else 0.0,
                "signal_close": float(r.close),
            }
        )

    # ---- 首板：昨炸板 ----
    zb = k.loc[k["is_zb"]].copy()
    for r in zb.itertuples(index=False):
        buy_d = shift_date(r.date, 1)
        sell_d = shift_date(r.date, hold_days)
        if not buy_d or not sell_d:
            continue
        rows.append(
            {
                "signal_date": r.date,
                "buy_date": buy_d,
                "sell_date": sell_d,
                "code": r.code,
                "name": r.name,
                "category": "首板",
                "src": "zb",
                "lbc": 0,
                "zbc": int(getattr(r, "zbc", 0) or 0),
                "fbt": int(getattr(r, "fbt", 150000) or 150000),
                "hs": float(r.hs) if pd.notna(r.hs) else 0.0,
                "mv_yi": float(r.mv_yi) if pd.notna(r.mv_yi) else 0.0,
                "signal_close": float(r.close),
            }
        )

    sig = pd.DataFrame(rows)
    if sig.empty:
        return sig

    buy = k.rename(
        columns={"date": "buy_date", "open": "buy_open", "high": "buy_high", "low": "buy_low", "close": "buy_close"}
    )[["code", "buy_date", "buy_open", "buy_high", "buy_low", "buy_close"]]
    sell = k.rename(columns={"date": "sell_date", "close": "sell_close", "high": "sell_high", "low": "sell_low"})[
        ["code", "sell_date", "sell_close", "sell_high", "sell_low"]
    ]
    df = sig.merge(buy, on=["code", "buy_date"], how="inner").merge(sell, on=["code", "sell_date"], how="inner")
    df["open_pct"] = (df["buy_open"] / df["signal_close"] - 1.0) * 100.0
    df["zt_buy"] = [
        limit_price(float(pc), str(c), str(n))
        for pc, c, n in zip(df["signal_close"], df["code"], df["name"].fillna(""))
    ]
    df["is_auction_zt"] = df["buy_open"] >= (df["zt_buy"] - 0.011)
    # 弱转强分：贴近 1% 开盘 + 早封 + 低炸板
    op = df["open_pct"].to_numpy()
    score = np.where(
        (op >= 0.3) & (op <= 2.0),
        36.0,
        np.where(
            (op >= 0) & (op < 0.3),
            28.0,
            np.where((op >= -1) & (op < 0), 22.0, np.where((op > -2) & (op < -1), 12.0, 8.0)),
        ),
    )
    score = score + np.where(df["fbt"] <= 93030, 16, np.where(df["fbt"] <= 100000, 12, np.where(df["fbt"] <= 103000, 6, 0)))
    score = score + np.where(df["zbc"] == 0, 12, np.where(df["zbc"] == 1, 8, np.where(df["zbc"] <= 3, 2, -6)))
    hs = df["hs"].to_numpy()
    score = score + np.where((hs >= 3) & (hs <= 11), 14, np.where((hs >= 1.5) & (hs < 3), 8, np.where(hs > 16, -8, 2)))
    df["score"] = score
    return df.sort_values(["buy_date", "code"]).reset_index(drop=True)


def filter_select(uni: pd.DataFrame, p: WeakParams) -> pd.DataFrame:
    if uni.empty:
        return uni
    d = uni
    if p.cat != "全部":
        d = d.loc[d["category"] == p.cat]
    m = (
        ~d["is_auction_zt"].fillna(False)
        & (d["open_pct"] > p.open_lo)
        & (d["open_pct"] < p.open_hi)
        & (d["zbc"] <= p.zbc_max)
        & (d["mv_yi"].fillna(0) > p.mv_lo)
        & (d["mv_yi"].fillna(0) < p.mv_hi)
        & (d["buy_open"] > 0)
        & (d["sell_close"] > 0)
    )
    # 晋级类要求封板时间；首板不强制
    if p.cat in ("一进二", "二进三"):
        m = m & (d["fbt"] <= p.fbt_max) & (d["hs"].fillna(0) <= p.hs_max)
    elif p.cat == "首板":
        m = m & (d["hs"].fillna(0) <= p.hs_max)
    else:
        # 全部：按行类别
        m = m & (
            ((d["category"] == "首板") & (d["hs"].fillna(0) <= p.hs_max))
            | (
                (d["category"] != "首板")
                & (d["fbt"] <= p.fbt_max)
                & (d["hs"].fillna(0) <= p.hs_max)
            )
        )
    d = d.loc[m].copy()
    if d.empty:
        return d
    d["open_dist"] = (d["open_pct"] - p.prefer_open).abs()
    d = d.sort_values(["buy_date", "score", "open_dist"], ascending=[True, False, True], kind="mergesort")
    d["rank_in_day"] = d.groupby("buy_date").cumcount() + 1
    d = d.loc[d["rank_in_day"] <= p.top_n].copy()
    d["ret"] = d["sell_close"] / d["buy_open"] - 1.0 - p.cost
    d["win"] = d["ret"] > 0
    return d


def non_overlap_full(trades: pd.DataFrame, hold_days: int = 3) -> pd.DataFrame:
    """仓位干满 + 非重叠：持仓未结束不新开；同日多只等权合成一笔组合收益。

    收盘卖出后，下一笔买入日须严格晚于卖出日。
    """
    if trades.empty:
        return trades
    daily = (
        trades.groupby("buy_date", as_index=False)
        .agg(
            ret=("ret", "mean"),
            n=("code", "count"),
            codes=("code", lambda s: ",".join(s.astype(str))),
            names=("name", lambda s: ",".join(s.astype(str))),
            categories=("category", lambda s: ",".join(sorted(set(s.astype(str))))),
            sell_date=("sell_date", "first"),
            open_pct=("open_pct", "mean"),
            score=("score", "mean"),
        )
        .sort_values("buy_date")
    )
    daily["win"] = daily["ret"] > 0
    out = []
    last_sell = ""
    for _, r in daily.iterrows():
        if last_sell and r["buy_date"] <= last_sell:
            continue
        out.append(r.to_dict())
        last_sell = str(r["sell_date"])
    return pd.DataFrame(out)


def summarize(trades: pd.DataFrame, tag: str, *, portfolio: bool = False) -> dict[str, Any]:
    if trades is None or trades.empty:
        return {
            "tag": tag,
            "n": 0,
            "days": 0,
            "win_rate": 0.0,
            "avg_ret": 0.0,
            "median_ret": 0.0,
            "sum_ret": 0.0,
            "comp_ret": 0.0,
            "max_dd": 0.0,
            "avg_per_day": 0.0,
        }
    date_col = "buy_date"
    daily = trades.groupby(date_col)["ret"].mean().sort_index()
    equity = (1.0 + daily).cumprod()
    peak = equity.cummax()
    dd = float((equity / peak - 1.0).min()) if len(equity) else 0.0
    return {
        "tag": tag,
        "n": int(len(trades)),
        "days": int(trades[date_col].nunique()),
        "win_rate": float(trades["win"].mean()),
        "avg_ret": float(trades["ret"].mean()),
        "median_ret": float(trades["ret"].median()),
        "sum_ret": float(trades["ret"].sum()),
        "comp_ret": float(equity.iloc[-1] - 1.0) if len(equity) else 0.0,
        "max_dd": dd,
        "avg_per_day": float(len(trades) / max(trades[date_col].nunique(), 1)),
        "portfolio": portfolio,
    }


def hunt_high_wr(uni: pd.DataFrame, hold_days: int = 3) -> list[dict[str, Any]]:
    """网格：优先胜率，其次样本数与均收益。仓位干满非重叠组合。"""
    cats = ["一进二", "二进三", "首板", "全部"]
    open_bands = [
        (-1.0, 2.0),
        (-0.5, 1.8),
        (0.0, 2.0),
        (0.3, 1.8),
        (0.5, 1.5),
        (-2.0, 2.5),
        (0.0, 2.5),
    ]
    top_ns = [1, 2]
    zbc_maxes = {"一进二": [0, 1, 3, 5], "二进三": [0, 1, 2], "首板": [2, 5, 8], "全部": [1, 3, 5]}
    fbt_maxes = [100000, 103000]
    hs_maxes = {"一进二": [12, 16, 22], "二进三": [8, 10, 12], "首板": [16, 22, 25], "全部": [12, 16, 22]}
    mv_bands = [(20, 120), (25, 100), (30, 90)]

    results: list[dict[str, Any]] = []
    best_by_cat: dict[str, dict[str, Any]] = {}

    for cat in cats:
        combos = list(
            itertools.product(
                open_bands,
                top_ns,
                zbc_maxes[cat],
                fbt_maxes,
                hs_maxes[cat],
                mv_bands,
            )
        )
        print(f"hunt {cat} combos={len(combos)}")
        best_key = (-1.0, -1, -9.0)
        best_rec = None
        for i, (ob, top_n, zbc, fbt, hs, mv) in enumerate(combos, 1):
            # 二进三默认更严开盘上限
            open_hi = min(ob[1], 2.2) if cat == "二进三" else ob[1]
            p = WeakParams(
                cat=cat,
                open_lo=ob[0],
                open_hi=open_hi,
                zbc_max=zbc,
                fbt_max=fbt,
                hs_max=hs,
                mv_lo=mv[0],
                mv_hi=mv[1],
                top_n=top_n,
                hold_days=hold_days,
            )
            raw = filter_select(uni, p)
            port = non_overlap_full(raw, hold_days)
            s = summarize(port, cat, portfolio=True)
            # 胜率优先；至少 15 笔非重叠；不够也记录
            key = (s["win_rate"], s["n"], s["avg_ret"])
            rec = {
                **asdict(p),
                **{k: s[k] for k in ("n", "days", "win_rate", "avg_ret", "median_ret", "comp_ret", "max_dd")},
                "raw_n": int(len(raw)),
                "raw_wr": float(raw["win"].mean()) if len(raw) else 0.0,
            }
            results.append(rec)
            min_n = 12 if cat != "全部" else 20
            if s["n"] >= min_n and key > best_key:
                best_key = key
                best_rec = {**rec, "trades": port, "raw": raw}
            if i % 200 == 0 or i == len(combos):
                print(f"\r  {cat} {i}/{len(combos)} best_wr={best_key[0]:.3f} n={best_key[1]}", end="", flush=True)
        print()
        if best_rec is None:
            # fallback: 不设最低笔数，取胜率最高且 n>=5
            fallback = [r for r in results if r["cat"] == cat and r["n"] >= 5]
            if fallback:
                fallback.sort(key=lambda r: (r["win_rate"], r["n"], r["avg_ret"]), reverse=True)
                top = fallback[0]
                p = WeakParams(**{k: top[k] for k in asdict(WeakParams()).keys()})
                raw = filter_select(uni, p)
                port = non_overlap_full(raw, hold_days)
                best_rec = {**top, "trades": port, "raw": raw}
        if best_rec:
            best_by_cat[cat] = best_rec
            print(
                f"  >> {cat} WR={best_rec['win_rate']:.2%} n={best_rec['n']} "
                f"avg={best_rec['avg_ret']:.2%} open=({best_rec['open_lo']},{best_rec['open_hi']}) top={best_rec['top_n']}"
            )
    return results, best_by_cat


def baseline_current(uni: pd.DataFrame, hold_days: int = 3) -> dict[str, Any]:
    """当前软件默认阈值对照。"""
    out = {}
    specs = {
        "一进二": WeakParams(cat="一进二", open_lo=-2, open_hi=2.5, zbc_max=5, fbt_max=103000, hs_max=22, top_n=2),
        "二进三": WeakParams(cat="二进三", open_lo=-2, open_hi=2.2, zbc_max=2, fbt_max=103000, hs_max=12, top_n=2),
        "首板": WeakParams(cat="首板", open_lo=-2, open_hi=2.5, zbc_max=8, fbt_max=150000, hs_max=25, top_n=2),
        "全部": WeakParams(cat="全部", open_lo=-2, open_hi=2.5, zbc_max=5, fbt_max=103000, hs_max=22, top_n=2),
    }
    for name, p in specs.items():
        p.hold_days = hold_days
        raw = filter_select(uni, p)
        port = non_overlap_full(raw, hold_days)
        out[name] = {
            "params": asdict(p),
            "raw": summarize(raw, name + "_raw"),
            "full_pos": summarize(port, name + "_full", portfolio=True),
            "trades": port,
            "raw_trades": raw,
        }
    return out


def write_report(
    uni: pd.DataFrame,
    baseline: dict[str, Any],
    ranked: pd.DataFrame,
    best_by_cat: dict[str, Any],
    hold_days: int,
) -> None:
    buy_min = str(uni["buy_date"].min()) if len(uni) else "-"
    buy_max = str(uni["buy_date"].max()) if len(uni) else "-"

    lines = [
        "# 竞价弱转强 · 回测报告（仓位干满 / 持股3天 / 冲高胜率）",
        "",
        "研究笔记，不构成投资建议。",
        "",
        "方法：昨涨停或昨炸板（日K）→ 次日开盘买入（近似竞价，未封涨停）→ **持股3个交易日**，第3日收盘卖出 → 往返成本 0.15%。",
        "",
        f"- 买入日范围：`{buy_min}` → `{buy_max}`",
        f"- 持股：{hold_days} 个交易日（含买入日）",
        "- **仓位干满**：同日多标的等权占满；组合层面 **持仓未了结不新开**（串行满仓）",
        "- 近似：无真实竞价量；炸板/封板时间为日K代理；近端东财池可校正",
        "",
        "## A. 当前默认公式（软件阈值）· 满仓3日",
        "",
    ]
    for cat in ("首板", "一进二", "二进三", "全部"):
        b = baseline[cat]["full_pos"]
        r = baseline[cat]["raw"]
        lines.append(
            f"### {cat}\n"
            f"- 非重叠满仓：胜率 **{b['win_rate']:.2%}** · 笔数 {b['n']} · 均收益 {b['avg_ret']:.2%} · "
            f"复利 {b['comp_ret']:.2%} · 最大回撤 {b['max_dd']:.2%}\n"
            f"- 信号层（可重叠）：胜率 {r['win_rate']:.2%} · n={r['n']}\n"
        )

    lines += ["## B. 高胜率狩猎（网格最优，每类）", ""]
    for cat in ("一进二", "二进三", "首板", "全部"):
        rec = best_by_cat.get(cat)
        if not rec:
            lines.append(f"### {cat}\n- 未找到足够样本\n")
            continue
        lines.append(
            f"### {cat}\n"
            f"- **胜率 {rec['win_rate']:.2%}** · 满仓笔数 {rec['n']} · 均收益 {rec['avg_ret']:.2%} · "
            f"复利 {rec['comp_ret']:.2%} · 回撤 {rec['max_dd']:.2%}\n"
            f"- 开盘 ({rec['open_lo']}, {rec['open_hi']})% · top_n={rec['top_n']} · "
            f"zbc≤{rec['zbc_max']} · fbt≤{rec['fbt_max']} · hs≤{rec['hs_max']} · "
            f"市值 ({rec['mv_lo']},{rec['mv_hi']})\n"
            f"- 原始信号 n={rec['raw_n']} 胜率 {rec['raw_wr']:.2%}\n"
        )
        tr = rec.get("trades")
        if tr is not None and len(tr):
            lines.append("| 买入日 | 卖出日 | 标的 | 分类 | 开盘% | 收益 |")
            lines.append("|---|---|---|---|---:|---:|")
            for _, t in tr.head(25).iterrows():
                lines.append(
                    f"| {t['buy_date']} | {t['sell_date']} | {t.get('names', t.get('name',''))} | "
                    f"{t.get('categories', t.get('category',''))} | {t['open_pct']:.2f} | {t['ret']*100:.2f}% |"
                )
            lines.append("")

    # 总冠军：胜率优先且 n>=15
    cand = ranked.loc[ranked["n"] >= 15].copy()
    if len(cand):
        cand = cand.sort_values(["win_rate", "n", "avg_ret"], ascending=[False, False, False])
        champ = cand.iloc[0]
        lines += [
            "## C. 总冠军（n≥15，胜率优先）",
            "",
            f"- 分类 **{champ['cat']}** · 胜率 **{champ['win_rate']:.2%}** · n={int(champ['n'])} · "
            f"均收益 {champ['avg_ret']:.2%} · 复利 {champ['comp_ret']:.2%}",
            f"- 参数：open ({champ['open_lo']},{champ['open_hi']}) top={int(champ['top_n'])} "
            f"zbc≤{int(champ['zbc_max'])} fbt≤{int(champ['fbt_max'])} hs≤{champ['hs_max']} "
            f"mv ({champ['mv_lo']},{champ['mv_hi']})",
            "",
            "> 持股3日满仓的胜率，通常显著低于「当日小止盈」方案；本报告不以盘中止盈抬胜率。",
            "",
        ]

    path = RESULTS / "weak_backtest_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print("wrote", path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hold", type=int, default=3)
    ap.add_argument("--quick", action="store_true", help="只跑默认公式，不网格")
    args = ap.parse_args()

    print("load bars...")
    k = load_bars()
    print("bars=%d codes=%d %s->%s" % (len(k), k["code"].nunique(), k["date"].min(), k["date"].max()))
    print("build signals...")
    uni = build_signals(k, hold_days=args.hold)
    print(
        f"signals={len(uni)} "
        + ", ".join(f"{c}={int((uni['category']==c).sum())}" for c in ("首板", "一进二", "二进三"))
    )
    uni.to_parquet(RESULTS / "weak_universe.parquet", index=False)

    print("baseline…")
    baseline = baseline_current(uni, hold_days=args.hold)
    for cat, b in baseline.items():
        s = b["full_pos"]
        print(f"  default {cat}: WR={s['win_rate']:.2%} n={s['n']} avg={s['avg_ret']:.2%} comp={s['comp_ret']:.2%}")

    best_by_cat: dict[str, Any] = {}
    ranked = pd.DataFrame()
    if not args.quick:
        print("hunt high win-rate...")
        results, best_by_cat = hunt_high_wr(uni, hold_days=args.hold)
        ranked = pd.DataFrame([{k: v for k, v in r.items() if k not in ("trades", "raw")} for r in results])
        ranked = ranked.sort_values(["win_rate", "n", "avg_ret"], ascending=[False, False, False])
        ranked.to_csv(RESULTS / "weak_grid_ranked.csv", index=False)

        for cat, rec in best_by_cat.items():
            rec["trades"].to_csv(RESULTS / f"weak_best_{cat}_trades.csv", index=False)
            # 把最优参数写进 baseline 对照旁
    else:
        for cat, b in baseline.items():
            best_by_cat[cat] = {**b["params"], **b["full_pos"], "raw_n": b["raw"]["n"], "raw_wr": b["raw"]["win_rate"], "trades": b["trades"]}

    write_report(uni, baseline, ranked if len(ranked) else pd.DataFrame(best_by_cat.values()), best_by_cat, args.hold)

    summary = {
        "hold_days": args.hold,
        "buy_range": [str(uni["buy_date"].min()), str(uni["buy_date"].max())] if len(uni) else [],
        "baseline": {c: {"full_pos": baseline[c]["full_pos"], "raw": baseline[c]["raw"], "params": baseline[c]["params"]} for c in baseline},
        "best": {
            c: {k: v for k, v in rec.items() if k not in ("trades", "raw")}
            for c, rec in best_by_cat.items()
        },
    }
    (RESULTS / "weak_backtest_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # 导出默认一进二成交
    baseline["一进二"]["trades"].to_csv(RESULTS / "weak_default_yijin2_full_trades.csv", index=False)
    baseline["全部"]["trades"].to_csv(RESULTS / "weak_default_all_full_trades.csv", index=False)
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
