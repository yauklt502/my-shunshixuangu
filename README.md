# 首板竞价选股

A 股 **昨日首板**，在次日 **集合竞价结束（9:25）之后、9:28 之前** 选出不超过 5 只，排除 **竞价一字涨停**。

## 使用

- 通达信：`formulas/tongdaxin.txt`
- 同花顺：`formulas/tonghuashun.txt`
- 交易规则与回测说明：`formulas/README.md`
- 回测报告：`results/best_report.json`

## 复现回测

```bash
pip install -r requirements.txt
python scripts/download_data.py --start 20240101
python scripts/download_all_klines.py
python scripts/backtest.py
```

数据缓存在 `data/`（不入库）。选股公式可在无 Python 的情况下直接导入行情软件使用。
