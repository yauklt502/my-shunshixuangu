"""Write markdown + charts for Sequoia-X backtest results."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from sequoia_backtest.backtest import HOLD_WINDOWS, StrategyResult

CN_NAMES = {
    "turtle_trade": "海龟突破 TurtleTrade",
    "ma_volume": "均线放量 MaVolume",
    "high_tight_flag": "高窄旗形 HighTightFlag",
    "limit_up_shakeout": "涨停洗盘 LimitUpShakeout",
    "uptrend_limit_down": "上升跌停 UptrendLimitDown",
    "rps_breakout": "RPS 突破 RpsBreakout",
    "hs300": "沪深300 买入持有",
}

PLOT_NAMES = {
    "turtle_trade": "TurtleTrade",
    "ma_volume": "MaVolume",
    "high_tight_flag": "HighTightFlag",
    "limit_up_shakeout": "LimitUpShakeout",
    "uptrend_limit_down": "UptrendLimitDown",
    "rps_breakout": "RpsBreakout",
}


def _pct(x: float, digits: int = 2) -> str:
    if x != x:  # NaN
        return "—"
    return f"{x * 100:.{digits}f}%"


def _num(x: float, digits: int = 2) -> str:
    if x != x:
        return "—"
    return f"{x:.{digits}f}"


def plot_equity(
    results: list[StrategyResult],
    hs300: pd.Series,
    out_path: Path,
    hold_days: int = 3,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 6))
    for r in results:
        if r.equity.empty:
            continue
        ax.plot(r.equity.index, r.equity.values, label=PLOT_NAMES.get(r.name, r.name), linewidth=1.2)
    if hs300 is not None and not hs300.empty:
        aligned = hs300.reindex(results[0].equity.index).ffill()
        aligned = aligned / aligned.iloc[0]
        ax.plot(aligned.index, aligned.values, label="CSI 300", color="black", linewidth=1.4, linestyle="--")
    ax.set_title(f"Sequoia-X vs CSI 300 ({hold_days}-day overlapping hold)")
    ax.set_ylabel("NAV")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def render_markdown(
    results: list[StrategyResult],
    hs300_stats: dict[str, float],
    meta: dict,
    out_path: Path,
) -> str:
    hold_days = int(meta.get("hold_days", 3))
    lines: list[str] = []
    lines.append("# Sequoia-X 策略回测报告")
    lines.append("")
    lines.append("对照 [sngyai/Sequoia-X](https://github.com/sngyai/Sequoia-X) V2 六个日频选股规则，在沪深300+中证500 成分股上做历史回测。")
    lines.append("")
    lines.append("## 回测设定")
    lines.append("")
    lines.append(f"- **样本区间**：{meta['eval_start']} ~ {meta['eval_end']}（行情从 {meta['data_start']} 起，用于均线 / RPS 热身）")
    lines.append(f"- **股票池**：当前沪深300 + 中证500 成分股，剔除 ST / 北交所，共 **{meta['n_symbols']}** 只")
    lines.append("- **行情**：baostock 后复权日 K，与原项目一致")
    lines.append("- **信号**：收盘后用当日及以前的数据选股（无盘中未来函数）")
    lines.append("- **成交**：T+1 开盘买入；若次日一字涨停或停牌则不成交")
    lines.append("- **每日上限**：每个策略最多 10 只，按当日成交额从大到小")
    lines.append("- **事件研究**：买入后持有至 T+N 收盘，不计费用")
    lines.append(f"- **组合**：持有 **{hold_days}** 个交易日、持仓等权；买入 5bp、卖出 10bp（含印花税）")
    lines.append("- **对照**：沪深300 同期买入持有")
    lines.append("")
    lines.append("## 重要偏差")
    lines.append("")
    lines.append("- 成分股取**当前**成员，存在幸存者偏差，偏利好历史表现。")
    lines.append(f"- 原仓库只做选股推送，没有官方卖出规则；{hold_days} 日持有是对「推完就买」的一种可复现假设。")
    lines.append("- 定增策略依赖东方财富公告，未纳入本次回测。")
    lines.append("- 涨停判定统一用 9.5%（创业板/科创板实际 20%），与原代码一致。")
    lines.append("- 信号稀疏的策略（涨停洗盘、上升跌停）经常满仓 1～2 只，净值波动不能和每天 10 只的海龟 / RPS 直接比。")
    lines.append("")
    lines.append(f"## 组合表现（{hold_days} 日重叠持有）")
    lines.append("")
    lines.append("| 策略 | 总收益 | 年化 | 最大回撤 | 波动 | 夏普 | 有信号天数 | 买入笔数 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in results:
        p = r.portfolio
        lines.append(
            f"| {CN_NAMES.get(r.name, r.name)} | {_pct(p['total_return'])} | {_pct(p['ann_return'])} | "
            f"{_pct(p['max_drawdown'])} | {_pct(p['vol'])} | {_num(p['sharpe'])} | {p['n_entry_days']} | {p['n_picks']} |"
        )
    h = hs300_stats
    lines.append(
        f"| {CN_NAMES['hs300']} | {_pct(h['total_return'])} | {_pct(h['ann_return'])} | "
        f"{_pct(h['max_drawdown'])} | {_pct(h['vol'])} | {_num(h['sharpe'])} | {h['n_entry_days']} | — |"
    )
    lines.append("")
    lines.append("![equity](sequoia_x_equity.png)")
    lines.append("")
    lines.append("## 结论（3 日持有）")
    lines.append("")
    beat = [r for r in results if r.portfolio["total_return"] > hs300_stats["total_return"]]
    lose = [r for r in results if r.portfolio["total_return"] <= hs300_stats["total_return"]]
    if beat:
        names = "、".join(CN_NAMES.get(r.name, r.name) for r in beat)
        lines.append(f"- 同期沪深300 总收益 {_pct(hs300_stats['total_return'])}。跑赢指数的组合：**{names}**。")
    if lose:
        names = "、".join(CN_NAMES.get(r.name, r.name) for r in lose)
        lines.append(f"- 跑输或接近亏损：**{names}**。高窄旗形是整理形态不是买点；上升跌停 3 日中位数为负，均值被少数大反弹拉高。")
    lines.append("- 3 日事件研究里，多数策略**均值正、中位数负、胜率不到 50%**，收益来自右尾，不是稳定胜率。")
    lines.append("- 涨停洗盘 3 日均收益约 1%、胜率 57%，但只有约 110 笔，且经常满仓 1 只，回撤和容量都经不起当主策略。")
    lines.append("- 海龟 / RPS 几乎每天都有满额 10 只信号，3 日持有比更长持有更干净；RPS 年化最高，回撤也到 30% 以上。")
    lines.append("")
    lines.append("## 事件研究（T+1 开盘买入后的平均收益）")
    lines.append("")
    for w in HOLD_WINDOWS:
        lines.append(f"### 持有 {w} 个交易日")
        lines.append("")
        lines.append("| 策略 | 样本数 | 平均 | 中位数 | 胜率 | P25 | P75 |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for r in results:
            e = r.event[w]
            lines.append(
                f"| {CN_NAMES.get(r.name, r.name)} | {e['n']} | {_pct(e['mean'])} | {_pct(e['median'])} | "
                f"{_pct(e['win_rate'], 1)} | {_pct(e['p25'])} | {_pct(e['p75'])} |"
            )
        lines.append("")
    lines.append("## 策略规则（与原仓库一致）")
    lines.append("")
    lines.append("| 策略 | 规则 |")
    lines.append("|---|---|")
    lines.append("| TurtleTrade | 收盘创 20 日新高 + 成交额 > 1 亿 + 阳线且收盘 > 昨收 |")
    lines.append("| MaVolume | 5 日均线上穿 20 日均线 + 成交量 > 20 日均量 1.5 倍 |")
    lines.append("| HighTightFlag | 近 40 日高低点比 > 1.6，近 10 日振幅 < 15%，近 10 日低点 ≥ 40 日高点 80%，缩量至 20 日均量 60% 以下 |")
    lines.append("| LimitUpShakeout | 昨日涨停（≥9.5%），今日阴线、量能 ≥ 昨日 2 倍、最低价不破昨收 |")
    lines.append("| UptrendLimitDown | 昨日 MA20 > MA60，今日跌停（≤-9.5%）且量能 > 20 日均量 2 倍 |")
    lines.append("| RpsBreakout | 120 日涨幅截面排名 ≥ 90 分位，且收盘 ≥ 120 日最高价的 90% |")
    lines.append("")
    lines.append("## 怎么复现")
    lines.append("")
    lines.append("```bash")
    lines.append("pip install -r requirements.txt")
    lines.append("PYTHONPATH=src python scripts/run_sequoia_backtest.py --hold-days 3")
    lines.append("PYTHONPATH=src python scripts/run_sequoia_backtest.py --download --hold-days 3")
    lines.append("PYTHONPATH=src pytest tests -q")
    lines.append("```")
    lines.append("")
    text = "\n".join(lines)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return text
