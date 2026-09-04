# my-shunshixuangu

A 股短线条件选股软件。研究笔记，不构成投资建议。

## 本机安装包

- [`deploy/顺势竞价选股-本机版.zip`](deploy/顺势竞价选股-本机版.zip)
- 重新打包：`python3 scripts/pack_portable.py`

解压 → 装 Python3（勾选 PATH）→ 双击 `启动选股.bat` → http://127.0.0.1:8787/

## 默认策略：一进二弱转强（9:30 前）

专抓 **昨首板 + 今开可买 + 微高开/小低开**（亚盛 +1%、海通发展 +1% 这类）。

| 条件 | 值 |
|---|---|
| 昨日 | 首板，封板 ≤10:30 |
| 今开 | 未涨停，涨幅 **-2% ~ +2.5%** |
| 市值 | 20~120 亿 |
| 数量 | 每天最多 **1~2** 只 |

问财：[`formulas/yijin2_weak_to_strong_iwencai.txt`](formulas/yijin2_weak_to_strong_iwencai.txt)  
说明：[`docs/review-yijin2-missed.md`](docs/review-yijin2-missed.md)

```bash
pip install -r requirements.txt
python3 -m app          # 默认策略即弱转强；9:15 后点「盘前盯盘」
python3 -m pytest -q
```
