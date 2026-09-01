# my-shunshixuangu

A-share research tools. This branch backtests the six daily screeners from
[Sequoia-X V2](https://github.com/sngyai/Sequoia-X).

## Sequoia-X backtest

默认持股 **3 个交易日**（T+1 开盘买，T+3 收盘卖）。

```bash
pip install -r requirements.txt
PYTHONPATH=src python scripts/run_sequoia_backtest.py --download --hold-days 3
PYTHONPATH=src pytest tests -q
```

Report: [docs/sequoia_x_backtest.md](docs/sequoia_x_backtest.md)
