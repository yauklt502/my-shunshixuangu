# my-shunshixuangu

A-share short-term board / dragon-tiger list research.

## 近 90 日连板≥5 分析

```bash
pip install -r requirements.txt
python analysis/consecutive_limit_up.py
```

- 报告：`reports/lianban5_lhb_analysis.md`
- 名单与席位明细：`data/processed/`

窗口为最近 90 个交易日。连板用不复权日 K 识别（东方财富涨停池只能覆盖约两周）。ST 5% 连板与普通 10cm 五板会分开统计。
