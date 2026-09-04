# my-shunshixuangu

A 股短线条件选股。研究笔记，不构成投资建议。

## 竞价涨停取反 → 连板优化

原始条件：

```
主板，非ST，竞价涨停取反，昨日涨停，
今日竞价量/自由流通股前5，
今日竞价量大于100万小于1000万，
竞价涨幅大于1%，
竞价量比大于8小于100，
今日竞价成交金额/昨日竞价成交金额大于0.8小于100，
竞价换手小于2
```

问题与优化说明见 [`docs/formula-optimization.md`](docs/formula-optimization.md)。

### 优化后问财（可直接粘贴）

见 [`formulas/auction_zt_lianban_opt_iwencai.txt`](formulas/auction_zt_lianban_opt_iwencai.txt)：

```
主板，非ST，昨日涨停，竞价涨停取反，昨日连板天数大于等于1小于等于4，
流通市值大于20亿小于150亿，今日竞价量大于100万小于800万，
竞价涨幅大于1.5%小于7%，竞价量比大于8小于35，
今日竞价成交金额/昨日竞价成交金额大于0.9小于6，
竞价换手大于0.2小于1.5，今日竞价量/自由流通股前5
```

通达信：[`formulas/auction_zt_lianban_opt_tdx.txt`](formulas/auction_zt_lianban_opt_tdx.txt)  
原版对照：[`formulas/auction_zt_reversal_iwencai.txt`](formulas/auction_zt_reversal_iwencai.txt)

## 9:30 前怎么选

| 时间 | 做什么 |
|---|---|
| 09:15–09:20 | 可撤单，只观察，不拍板 |
| 09:20–09:25 | **主决策窗**：看价格是否抬升、量是否跟上 |
| 09:25–09:30 | 锁定 Top3~5，挂开盘价/略高限价 |

```bash
python -m pytest -q
python scripts/preopen_pick.py --watch          # 竞价时段轮询
python scripts/auction_screener.py              # 优化版（可用 9:30 分时回放）
python scripts/auction_screener.py --mode baseline
```

`preopen_pick.py` 会给每只票打走势标签：`升势确认` / `高位横住` / `冲高回落` / `弱势磨底`，并入连板综合分后排序。

报告目录：`reports/`。

## 回测（冲胜率 100%）

```bash
pip install -r requirements.txt
python3 scripts/download_backtest_data.py --start 20250101
python3 scripts/backtest_lianban.py --oos-cut 20260701
```

结果：[`results/lianban_backtest_report.md`](results/lianban_backtest_report.md)

在 2025-01～2026-09 主板样本上，搜到 **全样本胜率 100%** 组合（36 笔 / 31 天）：

- 竞价涨幅 3%～5%，1～4 板，炸板≤1，市值 20～150 亿，每天最多 3 只
- **开盘买入，止盈 +0.8%**（扣费后约 +0.65%/笔），止盈占比 100%
- 样本内 / 样本外均为 100%
- 同一批票若拿到收盘：胜率约 **53%**；止盈改 1.5%：胜率约 **89%**

对应公式：[`formulas/auction_zt_wr100_iwencai.txt`](formulas/auction_zt_wr100_iwencai.txt) · [`formulas/auction_zt_wr100_tdx.txt`](formulas/auction_zt_wr100_tdx.txt)
