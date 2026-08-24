# 晴空万里云 · 个股买入点逻辑

把抖音号「晴空万里云」公开作品，以及同名淘股吧「晴空万里云为客」的每日计划/复盘，整理成**可执行的个股买入点状态机**。

> 研究笔记，不构成投资建议。A 股短线与 T+0 亏损概率很高，据此操作风险自担。

## 文档

- [docs/qingkong_buy_points.md](docs/qingkong_buy_points.md)：作品画像 + 买入点详细拆解
- [formulas/qingkong_tdx_xuangu.txt](formulas/qingkong_tdx_xuangu.txt)：通达信实用版（默认只选 B1）
- [formulas/qingkong_tdx_b1_only.txt](formulas/qingkong_tdx_b1_only.txt)：B1 最简（无 CAPITAL）
- [formulas/qingkong_tdx_xuangu_strict.txt](formulas/qingkong_tdx_xuangu_strict.txt)：通达信严格版
- [formulas/qingkong_tdx_futu.txt](formulas/qingkong_tdx_futu.txt)：通达信副图打点
- [formulas/qingkong_tdx_tchi.txt](formulas/qingkong_tdx_tchi.txt)：做 T 观察池（不是买点）

## 快速跑样本

```bash
python -m pip install -r requirements.txt
python scripts/run_buy_points.py
python -m pytest -q
```

样本里的票名只用来对照公开复盘里出现过的**形态**（急跌低吸、企稳确认、打地鼠、飘旗待涨、持仓做 T），不是荐股。
