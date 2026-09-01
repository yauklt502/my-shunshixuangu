# 首板竞价选股

昨日 **首板**，次日 **9:25 集合竞价结束后、9:28 前** 出结果，每天 **不超过 5 只**（实盘取 3 只）。**不要竞价一字涨停**（本公式只做竞价低开 2%~8%）。

## 直接用

| 软件 | 文件 |
| --- | --- |
| 通达信条件选股 | [`formulas/tongdaxin.txt`](formulas/tongdaxin.txt) |
| 同花顺条件选股 | [`formulas/tonghuashun.txt`](formulas/tonghuashun.txt) |
| 同花顺问财 | [`formulas/tonghuashun_wencai.txt`](formulas/tonghuashun_wencai.txt) |
| 操作说明 | [`formulas/README.md`](formulas/README.md) |

选出后按 **开盘涨幅从小到大** 排序，取前 3 只。9:30 买入，挂 **+1.5%** 限价止盈，未成交则收盘卖。

## 回测结果（必须配合 +1.5% 止盈）

不复权日 K，主板+创业板，剔除 ST/科创/北交。买入开盘价；若当日最高价达到开盘价×1.015 则按 +1.5% 计成交，否则收盘价卖出。往返成本 0.15%。样本外起点 2025-08-29。

| 区间 | 笔数 | 日均只数 | 胜率 | 平均收益 | 盈亏比 | 最大回撤 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 全样本 2023-2026 | 1502 | 2.45 | **85.0%** | 0.51% | 1.80 | -16.3% |
| 样本内 ~2025-08-29 | 959 | 2.45 | **83.7%** | 0.42% | 1.59 | -16.3% |
| 样本外 2025-08-29 后 | 543 | 2.45 | **87.1%** | 0.67% | 2.31 | -8.6% |
| 2023 | 110 | 2.39 | 82.7% | 0.42% | 1.59 | -11.5% |
| 2024 | 483 | 2.43 | 83.6% | 0.37% | 1.49 | -8.1% |
| 2025 | 533 | 2.42 | 84.8% | 0.51% | 1.82 | -7.6% |
| 2026 至 9/1 | 376 | 2.52 | 87.5% | 0.70% | 2.45 | -8.6% |
| 同样股票拿到收盘 | 1502 | 2.45 | 50.1% | 0.99% | 1.54 | -30.5% |

明细：`results/best_report.json`、`results/best_trades.csv`。

同一套票若拿到收盘，胜率只有约 50%，平均收益反而更高（赢的时候赢更多）。**85% 胜率来自把反抽 1.5% 先兑现**；亏的那约 15% 平均大约 -4.2%。

日 K 上「最高价碰到 +1.5%」按能成交计，极端上影可能略乐观。历史结果不保证以后。

## 复现

```bash
pip install -r requirements.txt
python scripts/download_data.py --start 20240101
python scripts/download_all_klines.py
python scripts/backtest.py
python scripts/search_tp.py
python scripts/pick_today.py   # 9:25 后
python scripts/replay_screenshots.py  # 别人截图两套公式
```

## 别人截图里的两套公式

图1 自选名「开盘竞价 2-9%高…」= 竞价高开 2%–9%；图2 七只全是昨日涨停冲板。公式、对照和回测见 [`formulas/posted_README.md`](formulas/posted_README.md)。仓库里的低开首板公式选不出这些票。
