# my-shunshixuangu

对 9 个通达信选股脚本的逻辑复现与日线回测。分段结论见 [ANALYSIS.md](ANALYSIS.md)。

```text
PYTHONPATH=. python3 backtest/download_data.py   # 拉日线
PYTHONPATH=. python3 backtest/sina_fill.py       # 补缺口
PYTHONPATH=. python3 backtest/run.py             # 回测
```
