# my-shunshixuangu

筛选「大盘阴线时仍收红、每天只走几个点、不涨停、换手低」的 A 股。这是相对强势里偏安静的一类，不是涨停接力。

```bash
python3 -m screener --index sh000300 --days 15 --top 40
```

规则和读法见 [analysis/quiet-relative-strength.md](analysis/quiet-relative-strength.md)。单元测试：

```bash
python3 -m unittest tests.test_rules -v
```

输出：`analysis/data/quiet-rs-latest.csv`。文中名单只描述已经发生的价格，不是投资建议。
