# my-shunshixuangu

A 股短线条件选股软件。研究笔记，不构成投资建议。

## 本机安装包

- [`deploy/顺势竞价选股-本机版.zip`](deploy/顺势竞价选股-本机版.zip)
- 重新打包：`python3 scripts/pack_portable.py`

解压 → 装 Python3（勾选 PATH）→ 双击 `启动选股.bat` → http://127.0.0.1:8787/

## 默认策略：竞价弱转强（9:30 前）

点「扫描选股」后按三类展示，每类最多 2 只：

| 分类 | 宇宙 | 今开 |
|---|---|---|
| **首板** | 昨炸板 | -2% ~ +2.5% |
| **一进二** | 昨首板 | -2% ~ +2.5%（亚盛/海通≈1%） |
| **二进三** | 昨 2 板 | -2% ~ +2.2%（更严） |

问财：`formulas/weak_shouban_*.txt` / `weak_yijin2_*.txt` / `weak_erjinsan_*.txt`  
说明：[`docs/review-yijin2-missed.md`](docs/review-yijin2-missed.md)

```bash
pip install -r requirements.txt
python3 -m app          # 默认弱转强；9:15 后点「盘前盯盘」
python3 -m pytest -q
```
