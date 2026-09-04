# my-shunshixuangu

A 股短线条件选股软件。研究笔记，不构成投资建议。

## 本机安装包

- [`deploy/顺势竞价选股-本机版.zip`](deploy/顺势竞价选股-本机版.zip)
- 重新打包：`python3 scripts/pack_portable.py`

解压 → 装 Python3（勾选 PATH）→ 双击 `启动选股.bat` → http://127.0.0.1:8787/

## 默认策略：竞价弱转强（满仓持股3日 · 冲高胜率）

回测（日K近似，仓位干满、持股3日）：一进二约 **73–78%**，二进三约 **75%**；首板约五成仅观察。

| 分类 | 今开 | 其它 |
|---|---|---|
| **一进二** | 0.5% ~ 1.5% | 炸板≤1，换手≤16%，每天1只 |
| **二进三** | 0% ~ 2.2% | 炸板≤1，换手≤8% |
| **首板** | 0.5% ~ 1.5% | 昨炸板；3日胜率不高 |

报告：[`results/weak_backtest_report.md`](results/weak_backtest_report.md) · 复现：`python3 scripts/backtest_weak.py`  
说明：[`docs/review-yijin2-missed.md`](docs/review-yijin2-missed.md)

```bash
pip install -r requirements.txt
python3 -m app
python3 -m pytest -q
python3 scripts/backtest_weak.py
```
