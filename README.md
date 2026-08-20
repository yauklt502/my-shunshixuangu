# my-shunshixuangu

顺势选股 · **妖龙跟随策略（规则引擎）**

把「跟随市场、跟随资金」拆成可执行规则：情绪定仓位 → 主线定方向 → 龙头定标的 → 换手验真假 → 席位做确认 → 三种买点进场 → 硬卖点离场。

> 研究框架，不构成投资建议。短线博弈风险极高。

## 文档

- [妖龙跟随策略全文](docs/yaolong_strategy.md)

## 快速跑样本

```bash
python scripts/run_strategy.py --pretty
python -m pytest tests/ -q
```

## 模块

| 路径 | 作用 |
|------|------|
| `src/yaolong/emotion.py` | 六段情绪（ICE→EBB） |
| `src/yaolong/filters.py` | 市值/ST/一字后排/主线硬过滤 |
| `src/yaolong/seat.py` | 龙虎榜真合力 vs 假点火 |
| `src/yaolong/scorer.py` | 六维评分卡 |
| `src/yaolong/signal.py` | B1/B2/B3 买点与 S1–S6 卖点 |
| `data/samples/yaolong_cases.json` | 近一年骨架样本（研究用） |

## 总纲

**情绪定仓位，主线定方向，龙头定标的，换手定真假，席位做确认，买点只做三种，卖点无条件执行。**
