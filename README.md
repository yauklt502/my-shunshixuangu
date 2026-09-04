# my-shunshixuangu

A 股短线条件选股软件。研究笔记，不构成投资建议。

## 一键启动（选股软件）

```bash
pip install -r requirements.txt
python3 -m app
# 或
./启动选股.sh
# Windows: 双击 启动选股.bat
```

浏览器打开 [http://127.0.0.1:8787/](http://127.0.0.1:8787/)

| 功能 | 说明 |
|---|---|
| 连板优化 | 收紧量价 + 高度/炸板/市值，综合分 Top5 |
| 胜率100% | 回测全胜方案：涨幅 3–5%，每天最多 3 只，**开盘后 +0.8% 止盈** |
| 原版公式 | 你的原始「竞价涨停取反」条件 |
| 盘前盯盘 | 9:15–9:30 拉实时盘口 + 竞价走势标签，可 15 秒自动刷新 |

## 公式与回测

优化说明：[`docs/formula-optimization.md`](docs/formula-optimization.md)  
回测报告：[`results/lianban_backtest_report.md`](results/lianban_backtest_report.md)  
问财/通达信：`formulas/`

```bash
python3 -m pytest -q
python3 scripts/auction_screener.py
python3 scripts/preopen_pick.py --watch
```
