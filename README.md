# my-shunshixuangu

A 股短线条件选股。研究笔记，不构成投资建议。

## 竞价涨停取反（昨日涨停）

条件（按顺序）：

1. 主板、非 ST
2. 竞价涨停取反（今开未封涨停）
3. 昨日涨停
4. 今日竞价量 / 自由流通股 **前 8**
5. 今日竞价量大于 100 万股、小于 1000 万股
6. 竞价涨幅大于 1%
7. 竞价量比大于 8、小于 100
8. 今日竞价成交金额 / 昨日竞价成交金额大于 0.8、小于 100
9. 竞价换手小于 2%
10. 今日竞价量 / 自由流通股 **前 5**

| 文件 | 用途 |
|---|---|
| [formulas/auction_zt_reversal_iwencai.txt](formulas/auction_zt_reversal_iwencai.txt) | 问财一句话 |
| [formulas/auction_zt_reversal_tdx.txt](formulas/auction_zt_reversal_tdx.txt) | 通达信 9:25 条件选股 |
| `python scripts/auction_screener.py` | 用东方财富昨涨停池 + 09:30 分时跑一遍 |

```bash
python -m pytest -q
python scripts/auction_screener.py
```

报告写在 `reports/auction-zt-reversal-YYYYMMDD.html`。自由流通用东方财富流通 A 股近似。
