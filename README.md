# my-shunshixuangu

A-share research tools. This branch backtests the six daily screeners from
[Sequoia-X V2](https://github.com/sngyai/Sequoia-X).

## Sequoia-X backtest

```bash
pip install -r requirements.txt
PYTHONPATH=src python scripts/run_sequoia_backtest.py --download
PYTHONPATH=src pytest tests -q
```

Report: [docs/sequoia_x_backtest.md](docs/sequoia_x_backtest.md)
