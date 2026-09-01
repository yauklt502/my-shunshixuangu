# my-shunshixuangu

通达信选股脚本。实盘只维护三套，其余文件会转发过去。分段结论见 [ANALYSIS.md](ANALYSIS.md)。

## 实盘入口

| 用途 | 跑这个 | 不要每天满仓 | 持有 |
|---|---|---|---|
| 主板趋势 | `strategies/趋势稳健少.py` | 最多 3 只，无票空仓 | 3–5 日（回测显示隔夜更强） |
| 创业板趋势 | `strategies/趋势王创业板_放宽版.py` | 最多 8 只，扫全部 300 | 3–5 日 |
| 高标交易 | `strategies/主板妖龙优化.py` | 红灯空仓 | 只做隔夜 |
| 高标观察 | `strategies/龙头盯盘.py` | 不下单 | — |

`极速精简.py`、`极速精简优化版.py`、`趋势王主板精选.py` → 稳健少。  
`趋势王创业板_参数调整版.py` → 放宽版。  
`主板妖龙优化1.py` → 妖龙优化。

## 回测

```text
PYTHONPATH=. python3 backtest/download_data.py   # 拉日线
PYTHONPATH=. python3 backtest/sina_fill.py       # 补缺口
PYTHONPATH=. python3 backtest/run.py             # 三套 + 隔夜对照
PYTHONPATH=. python3 backtest/test_engine.py
PYTHONPATH=. python3 backtest/test_features.py
```
