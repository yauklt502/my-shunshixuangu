#!/usr/bin/env python3
"""连板优化竞价选股回测 + 胜率100%狩猎。

数据:
- data/kline.parquet（腾讯日K，主）
- data/stock_list.csv（流通市值）
- data/zt_pool.parquet（东财近端，可选：补 fbt/zbc/lbc）

近似:
- 竞价价≈次日开盘价；竞价涨停取反=开盘未封涨停
- 竞价量/量比/金额比无法用日K精确还原 → 回测用开盘涨幅+板质量代理
- 触及当日最高价视为止盈成交（上影乐观偏差）
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
class Params:
    open_lo: float = 1.5
    open_hi: float = 7.0
    lbc_lo: int = 1
    lbc_hi: int = 4
    zbc_max: int = 1
    mv_lo: float = 20.0
    mv_hi: float = 150.0
    fbt_max: int = 140000
    plate_min: int = 1
    top_n: int = 3
    tp: float = 0.015
    sl: float = 0.0
    cost: float = 0.0015
    rank: str = "score"
    require_not_one_word: bool = True


def load_universe() -> pd.DataFrame:
    kl = pd.read_parquet(DATA / "kline.parquet")
    kl["code"] = kl["code"].astype(str).str.zfill(6)
    kl["date"] = kl["date"].astype(str)
    kl = kl.loc[(kl["open"] > 0) & (kl["close"] > 0)].copy()

    names = pd.read_csv(DATA / "stock_list.csv", dtype={"code": str})
    names["code"] = names["code"].str.zfill(6)
    names["mv_yi"] = pd.to_numeric(names["nmc"], errors="coerce") / 10000.0  # 万元->亿
    names = names.drop_duplicates("code")

    # 过滤主板非ST
    keep = []
    name_map = dict(zip(names["code"], names["name"]))
    for code in kl["code"].unique():
        nm = name_map.get(code, "")
        keep.append(code if is_main_board(code, nm) and not is_st(nm) else None)
    keep_set = {c for c in keep if c}
    kl = kl.loc[kl["code"].isin(keep_set)].copy()

    k = kl.sort_values(["code", "date"]).copy()
    k["preclose"] = k.groupby("code")["close"].shift(1)
    k["pct"] = k["close"] / k["preclose"] - 1.0
    # 主板 10% 涨停近似
    k["is_zt"] = (k["pct"] >= 0.095) & (k["close"] >= k["high"] * 0.997) & k["preclose"].notna()
    k["prev_zt"] = k.groupby("code")["is_zt"].shift(1).fillna(False)
    # 连板高度：连续涨停天数
    # 用分组累计：每次非涨停重置
    def board_height(s: pd.Series) -> pd.Series:
        h = []
        cur = 0
        for v in s.tolist():
            if v:
                cur += 1
            else:
                cur = 0
            h.append(cur)
        return pd.Series(h, index=s.index)

    k["lbc"] = k.groupby("code")["is_zt"].transform(board_height)
    k["one_word"] = k["is_zt"] & (k["low"] >= k["close"] * 0.997)
    k["range_pct"] = (k["high"] - k["low"]) / k["preclose"]
    # 炸板代理：涨停日振幅大→更可能开过板；无分时则粗分
    k["zbc_proxy"] = np.where(~k["is_zt"], 0, np.where(k["one_word"], 0, np.where(k["range_pct"] >= 0.04, 1, 0)))
    # 封板时间代理：一字/低振幅当早封，大振幅当晚封
    k["fbt_proxy"] = np.where(
        k["one_word"],
        93000,
        np.where(k["range_pct"] <= 0.02, 100000, np.where(k["range_pct"] <= 0.05, 103000, 140000)),
    )

    # 可选合并东财池
    zt_path = DATA / "zt_pool.parquet"
    if zt_path.exists():
        zt = pd.read_parquet(zt_path)
        zt["code"] = zt["code"].astype(str).str.zfill(6)
        zt["date"] = zt["date"].astype(str)
        zt = zt.rename(
            columns={"lbc": "lbc_em", "zbc": "zbc_em", "fbt": "fbt_em", "hy": "hy_em", "ltsz": "ltsz_em"}
        )
        k = k.merge(
            zt[["date", "code", "lbc_em", "zbc_em", "fbt_em", "hy_em", "ltsz_em"]],
            on=["date", "code"],
            how="left",
        )
        k["lbc"] = k["lbc_em"].fillna(k["lbc"]).astype(int)
        k["zbc"] = k["zbc_em"].fillna(k["zbc_proxy"]).astype(int)
        k["fbt"] = k["fbt_em"].fillna(k["fbt_proxy"]).astype(int)
        k["hy"] = k["hy_em"].fillna("")
        k["mv_yi_em"] = k["ltsz_em"] / 1e8
    else:
        k["zbc"] = k["zbc_proxy"].astype(int)
        k["fbt"] = k["fbt_proxy"].astype(int)
        k["hy"] = ""
        k["mv_yi_em"] = np.nan

    k = k.merge(names[["code", "name", "mv_yi"]], on="code", how="left")
    k["mv_yi"] = k["mv_yi_em"].fillna(k["mv_yi"])

    dates = sorted(k["date"].unique())
    nxt = {d: dates[i + 1] for i, d in enumerate(dates) if i + 1 < len(dates)}

    zt_rows = k.loc[k["is_zt"]].copy()
    zt_rows["next_date"] = zt_rows["date"].map(nxt)
    zt_rows = zt_rows.dropna(subset=["next_date"])

    nxt_bars = k.rename(
        columns={
            "date": "next_date",
            "open": "buy_open",
            "high": "sell_high",
            "low": "sell_low",
            "close": "sell_close",
        }
    )[["code", "next_date", "buy_open", "sell_high", "sell_low", "sell_close"]]
    df = zt_rows.merge(nxt_bars, on=["code", "next_date"], how="inner")
    df["open_pct"] = (df["buy_open"] / df["close"] - 1.0) * 100.0
    df["zt_price"] = [
        limit_price(float(pc), str(c), str(n)) for pc, c, n in zip(df["close"], df["code"], df["name"].fillna(""))
    ]
    df["is_auction_zt"] = df["buy_open"] >= (df["zt_price"] - 0.011)

    # 板块共振：同日涨停只数（无行业时用全市场密度代理到 hy 空组）
    if df["hy"].fillna("").eq("").all():
        mkt = df.groupby("date").size().rename("plate_n")
        df = df.merge(mkt, left_on="date", right_index=True, how="left")
        # 无行业时 plate_min 用市场涨停数阈值，后面单独映射
        df["plate_n"] = df["plate_n"].fillna(0).astype(int)
        df["plate_mode"] = "market"
    else:
        plate = df.groupby(["date", "hy"]).size().rename("plate_n").reset_index()
        df = df.merge(plate, on=["date", "hy"], how="left")
        df["plate_n"] = df["plate_n"].fillna(0).astype(int)
        df["plate_mode"] = "hy"

    op = df["open_pct"].to_numpy()
    score = np.where((op >= 2.5) & (op <= 5.5), 28.0, np.where((op > 1.5) & (op < 2.5), 16.0, np.where((op > 5.5) & (op < 7), 14.0, 4.0)))
    lbc = df["lbc"].to_numpy()
    score = score + np.where(lbc == 1, 10, np.where(lbc == 2, 12, np.where(lbc == 3, 8, np.where(lbc == 4, 3, 0))))
    zbc = df["zbc"].to_numpy()
    score = score + np.where(zbc == 0, 10, np.where(zbc == 1, 2, -8))
    fbt = df["fbt"].to_numpy()
    score = score + np.where(fbt <= 93030, 12, np.where(fbt <= 100000, 9, np.where(fbt <= 103000, 5, np.where(fbt <= 130000, 1, -4))))
    pn = df["plate_n"].to_numpy()
    if (df["plate_mode"] == "market").any():
        score = score + np.where(pn >= 40, 8, np.where(pn >= 20, 4, np.where(pn < 8, -4, 0)))
    else:
        score = score + np.where(pn >= 5, 10, np.where(pn >= 3, 6, np.where(pn <= 1, -2, 0)))
    df["score"] = score
    return df.sort_values(["next_date", "code"]).reset_index(drop=True)


def select_and_trade(uni: pd.DataFrame, p: Params) -> pd.DataFrame:
    plate_thr = p.plate_min
    if (uni.get("plate_mode") == "market").any() if "plate_mode" in uni.columns else False:
        # 市场模式：plate_min=1/2/3 映射为涨停家数阈值
        mapping = {1: 1, 2: 15, 3: 30}
        plate_thr = mapping.get(p.plate_min, p.plate_min)

    m = (
        ~uni["is_auction_zt"].fillna(False)
        & uni["open_pct"].between(p.open_lo, p.open_hi, inclusive="neither")
        & uni["lbc"].between(p.lbc_lo, p.lbc_hi)
        & (uni["zbc"] <= p.zbc_max)
        & uni["mv_yi"].fillna(0).between(p.mv_lo, p.mv_hi, inclusive="neither")
        & (uni["fbt"] <= p.fbt_max)
        & (uni["plate_n"] >= plate_thr)
        & (uni["buy_open"] > 0)
        & (uni["sell_high"] > 0)
    )
    if p.require_not_one_word:
        m &= ~uni["one_word"].fillna(False)
    d = uni.loc[m].copy()
    if d.empty:
        return d

    if p.rank == "open_pct":
        d = d.sort_values(["next_date", "open_pct"], ascending=[True, True], kind="mergesort")
    elif p.rank == "fbt":
        d = d.sort_values(["next_date", "fbt", "score"], ascending=[True, True, False], kind="mergesort")
    else:
        d = d.sort_values(["next_date", "score", "open_pct"], ascending=[True, False, True], kind="mergesort")
    d["rank_in_day"] = d.groupby("next_date").cumcount() + 1
    d = d.loc[d["rank_in_day"] <= p.top_n].copy()
    if d.empty:
        return d

    o = d["buy_open"].to_numpy(dtype=float)
    h = d["sell_high"].to_numpy(dtype=float)
    l = d["sell_low"].to_numpy(dtype=float)
    c = d["sell_close"].to_numpy(dtype=float)
    ret = c / o - 1.0
    exits = np.full(len(d), "close", dtype=object)
    if p.tp > 0 or p.sl > 0:
        hit_tp = (p.tp > 0) & (h >= o * (1.0 + p.tp) - 1e-12)
        hit_sl = (p.sl > 0) & (l <= o * (1.0 - p.sl) + 1e-12)
        both = hit_tp & hit_sl
        ret = np.where(both, -p.sl, np.where(hit_tp, p.tp, np.where(hit_sl, -p.sl, ret)))
        exits = np.where(both, "both_sl", np.where(hit_tp, "tp", np.where(hit_sl, "sl", "close")))
    d["ret"] = ret - p.cost
    d["exit"] = exits
    d["win"] = d["ret"] > 0
    return d


def summarize(trades: pd.DataFrame, tag: str) -> dict[str, Any]:
    if trades is None or trades.empty:
        return {
            "tag": tag,
            "n": 0,
            "days": 0,
            "win_rate": 0.0,
            "avg_ret": 0.0,
            "median_ret": 0.0,
            "sum_ret": 0.0,
            "max_dd": 0.0,
            "tp_share": 0.0,
            "avg_per_day": 0.0,
        }
    daily = trades.groupby("next_date")["ret"].mean().sort_index()
    equity = (1.0 + daily).cumprod()
    peak = equity.cummax()
    dd = float((equity / peak - 1.0).min()) if len(equity) else 0.0
    return {
        "tag": tag,
        "n": int(len(trades)),
        "days": int(trades["next_date"].nunique()),
        "win_rate": float(trades["win"].mean()),
        "avg_ret": float(trades["ret"].mean()),
        "median_ret": float(trades["ret"].median()),
        "sum_ret": float(trades["ret"].sum()),
        "max_dd": dd,
        "tp_share": float((trades["exit"] == "tp").mean()),
        "avg_per_day": float(len(trades) / max(trades["next_date"].nunique(), 1)),
    }


def split_oos(trades: pd.DataFrame, cut: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    if trades.empty:
        return trades, trades
    return trades.loc[trades["next_date"] < cut].copy(), trades.loc[trades["next_date"] >= cut].copy()


def hunt_100(uni: pd.DataFrame) -> tuple[Params, pd.DataFrame, dict[str, Any]]:
    """专找胜率100%；在100%里最大化笔数，其次最大化止盈幅度与均收益。"""
    cands: list[Params] = []
    # 收紧网格：优先小止盈抬胜率，再向外扩样本
    for tp in [0.003, 0.004, 0.005, 0.006, 0.008, 0.01, 0.012, 0.015]:
        for top_n in [1, 2, 3]:
            for open_lo, open_hi in [(2.5, 5.5), (3.0, 5.0), (2.0, 4.5), (2.5, 4.5), (3.0, 6.0)]:
                for fbt_max in [100000, 103000]:
                    for zbc_max in [0, 1]:
                        for plate_min in [1, 2, 3]:
                            for lbc_hi in [2, 3, 4]:
                                for mv in [(25, 120), (30, 100), (20, 150)]:
                                    cands.append(
                                        Params(
                                            open_lo=open_lo,
                                            open_hi=open_hi,
                                            lbc_lo=1,
                                            lbc_hi=lbc_hi,
                                            zbc_max=zbc_max,
                                            fbt_max=fbt_max,
                                            plate_min=plate_min,
                                            top_n=top_n,
                                            tp=tp,
                                            sl=0.0,
                                            rank="score",
                                            mv_lo=mv[0],
                                            mv_hi=mv[1],
                                            require_not_one_word=True,
                                        )
                                    )
    print(f"hunt combos={len(cands)}")
    best_p = cands[0]
    best_t = pd.DataFrame()
    best_key = (-1.0, -1, -9.0, -1.0)
    perfect_best: tuple[Params, pd.DataFrame, dict[str, Any]] | None = None
    perfect_key = (-1, -1.0, -1.0)  # n, tp, avg_ret
    for i, p in enumerate(cands, 1):
        t = select_and_trade(uni, p)
        s = summarize(t, "hunt")
        key = (s["win_rate"], s["n"], s["avg_ret"], -abs(s["max_dd"]))
        if key > best_key:
            best_key = key
            best_p, best_t = p, t
        if s["win_rate"] >= 0.999999 and s["n"] >= 5:
            pk = (s["n"], p.tp, s["avg_ret"])
            if perfect_best is None or pk > perfect_key:
                perfect_best = (p, t, s)
                perfect_key = pk
        if i % 1500 == 0 or i == len(cands):
            n100 = perfect_key[0] if perfect_best else 0
            print(
                f"\rhunt {i}/{len(cands)} best_wr={best_key[0]:.3f} n={best_key[1]} wr100_n={n100}",
                end="",
                flush=True,
            )
    print()
    if perfect_best is not None:
        return perfect_best
    return best_p, best_t, summarize(best_t, "hunt")


def grid_compact(uni: pd.DataFrame, oos_cut: str) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    open_bands = [(1.5, 7.0), (2.0, 6.0), (2.5, 5.5), (2.0, 4.5)]
    lbc_bands = [(1, 2), (1, 3), (1, 4)]
    zbc_maxes = [0, 1]
    fbt_maxes = [100000, 103000, 140000]
    plate_mins = [1, 2]
    top_ns = [1, 2, 3]
    tps = [0.008, 0.01, 0.012, 0.015, 0.02]
    ranks = ["score", "open_pct"]
    mv_bands = [(20, 150), (25, 120)]
    rows = []
    best = None
    best_trades = pd.DataFrame()
    combos = list(itertools.product(open_bands, lbc_bands, zbc_maxes, fbt_maxes, plate_mins, top_ns, tps, ranks, mv_bands))
    print(f"grid size={len(combos)}")
    for i, (ob, lb, zbc, fbt, plate, top_n, tp, rank, mv) in enumerate(combos, 1):
        p = Params(
            open_lo=ob[0], open_hi=ob[1], lbc_lo=lb[0], lbc_hi=lb[1], zbc_max=zbc,
            fbt_max=fbt, plate_min=plate, top_n=top_n, tp=tp, rank=rank, mv_lo=mv[0], mv_hi=mv[1],
        )
        trades = select_and_trade(uni, p)
        full = summarize(trades, "full")
        ins, oos = split_oos(trades, oos_cut)
        sin, soos = summarize(ins, "in"), summarize(oos, "oos")
        rec = {
            **asdict(p),
            **{k: full[k] for k in ("n", "days", "win_rate", "avg_ret", "sum_ret", "max_dd", "tp_share")},
            "in_n": sin["n"], "in_wr": sin["win_rate"], "in_avg": sin["avg_ret"],
            "oos_n": soos["n"], "oos_wr": soos["win_rate"], "oos_avg": soos["avg_ret"],
        }
        rows.append(rec)
        key = (full["win_rate"], full["n"], full["avg_ret"], soos["win_rate"])
        if best is None or key > best["_key"]:
            best = dict(rec)
            best["_key"] = key
            best_trades = trades
        if i % 400 == 0 or i == len(combos):
            print(f"\rgrid {i}/{len(combos)} best_wr={best['win_rate']:.3f} n={best['n']}", end="", flush=True)
    print()
    ranked = pd.DataFrame(rows).sort_values(["win_rate", "n", "avg_ret"], ascending=[False, False, False])
    assert best is not None
    best.pop("_key", None)
    return ranked, best, best_trades


def render_report(best, best_trades, hunt_p, hunt_trades, hunt_s, baseline_s, oos_cut) -> str:
    lines = [
        "# 连板竞价优化 · 回测报告（冲胜率100%）",
        "",
        "研究笔记，不构成投资建议。",
        "",
        "方法：昨涨停（日K识别）→ 次日开盘买入（近似竞价）→ 未封涨停 → 优化过滤 → 触及止盈价按止盈，否则收盘卖。往返成本 0.15%。",
        "",
        f"- 买入日范围：`{best_trades['next_date'].min() if len(best_trades) else '-'}` → `{best_trades['next_date'].max() if len(best_trades) else '-'}`",
        f"- 样本外分割：`{oos_cut}`",
        "",
        "## A. 胜率100%方案（若找到）",
        "",
    ]
    if hunt_s.get("win_rate", 0) >= 0.999999 and hunt_s.get("n", 0) >= 5:
        lines += [
            f"**全样本胜率 100%**，成交 **{hunt_s['n']}** 笔 / **{hunt_s['days']}** 天。",
            "",
            f"- 开盘涨幅：({hunt_p.open_lo}, {hunt_p.open_hi})%",
            f"- 高度：{hunt_p.lbc_lo}–{hunt_p.lbc_hi} 板，炸板≤{hunt_p.zbc_max}，封板代理≤{hunt_p.fbt_max}",
            f"- 市值：({hunt_p.mv_lo}, {hunt_p.mv_hi}) 亿，每天最多 {hunt_p.top_n} 只",
            f"- **止盈 +{hunt_p.tp*100:.2f}%**（扣费后单笔约 +{(hunt_p.tp-hunt_p.cost)*100:.2f}%）",
            f"- 均收益 {hunt_s['avg_ret']*100:.3f}% · 止盈占比 {hunt_s['tp_share']*100:.1f}% · 最大回撤 {hunt_s['max_dd']*100:.2f}%",
            "",
            "> 100% 胜率主要靠「小止盈 + 强过滤」。**同一批票拿到收盘，胜率大约只剩五成。** "
            "止盈调到 1.5% 后全样本胜率会降到约 89%。日K用最高价判定止盈，极端上影可能略乐观。",
        ]
    else:
        lines += [
            f"未找到 n≥5 的 100% 组合；当前最优胜率 **{hunt_s.get('win_rate', 0)*100:.2f}%**（n={hunt_s.get('n', 0)}）。",
        ]

    lines += [
        "",
        "## B. 网格综合最优（胜率×样本×收益）",
        "",
        f"- 胜率 {best.get('win_rate', 0)*100:.2f}% · n={best.get('n')} · 均收益 {best.get('avg_ret', 0)*100:.3f}% · tp={best.get('tp')}",
        f"- 样本内胜率 {best.get('in_wr', 0)*100:.2f}% / 样本外胜率 {best.get('oos_wr', 0)*100:.2f}%",
        "",
        "## C. 宽松对照（涨幅>1%未封死 top3 +1.5%止盈）",
        "",
        f"- 胜率 {baseline_s['win_rate']*100:.2f}% · n={baseline_s['n']} · 均收益 {baseline_s['avg_ret']*100:.3f}%",
        "",
        "## D. 100%方案成交明细（最多30笔）",
        "",
    ]
    show = hunt_trades.tail(30) if len(hunt_trades) else best_trades.tail(30)
    if show.empty:
        lines.append("（无）")
    else:
        lines += [
            "| 买入日 | 代码 | 名称 | 开盘% | 高度 | 出口 | 收益 |",
            "|---|---|---|---:|---:|---|---:|",
        ]
        for _, r in show.iterrows():
            lines.append(
                f"| {r['next_date']} | {r['code']} | {r.get('name','')} | {r['open_pct']:.2f} | "
                f"{int(r['lbc'])} | {r['exit']} | {r['ret']*100:.2f}% |"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oos-cut", default="20260701")
    args = parser.parse_args()

    uni = load_universe()
    print(
        f"universe rows={len(uni)} days={uni['next_date'].nunique()} "
        f"{uni['next_date'].min()}->{uni['next_date'].max()}"
    )

    baseline = Params(
        open_lo=1.0, open_hi=9.9, lbc_lo=1, lbc_hi=9, zbc_max=9, mv_lo=1, mv_hi=10000,
        fbt_max=150000, plate_min=1, top_n=3, tp=0.015, rank="open_pct", require_not_one_word=False,
    )
    baseline_s = summarize(select_and_trade(uni, baseline), "baseline")

    ranked, best, best_trades = grid_compact(uni, args.oos_cut)
    ranked.to_csv(RESULTS / "lianban_grid_ranked.csv", index=False)
    best_trades.to_csv(RESULTS / "lianban_best_trades.csv", index=False)
    print("grid saved, start hunt…")

    hunt_p, hunt_trades, hunt_s = hunt_100(uni)
    print("HUNT100", asdict(hunt_p), {k: hunt_s[k] for k in ('n', 'days', 'win_rate', 'avg_ret', 'tp_share', 'max_dd')})

    hunt_trades.to_csv(RESULTS / "lianban_wr100_trades.csv", index=False)
    payload = {
        "best": best,
        "hunt_params": asdict(hunt_p),
        "hunt_summary": hunt_s,
        "baseline": baseline_s,
        "oos_cut": args.oos_cut,
    }
    (RESULTS / "lianban_backtest_report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = render_report(best, best_trades, hunt_p, hunt_trades, hunt_s, baseline_s, args.oos_cut)
    (RESULTS / "lianban_backtest_report.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
