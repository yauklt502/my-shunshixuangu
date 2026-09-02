# Sequoia-X

网页选股 + 历史回测。选股规则来自 [sngyai/Sequoia-X](https://github.com/sngyai/Sequoia-X)，界面沿用本仓库 PR #19 的板块扫描页（数据源、截屏、测连接不变），**没有改 PR #19 分支**。

本页四套策略：

| 策略 | 规则 |
|---|---|
| 海龟突破 | 收盘创 20 日新高 + 成交额 > 1 亿 + 阳线且收盘 > 昨收 |
| 均线放量 | 5 日均线上穿 20 日均线 + 成交量 > 20 日均量 1.5 倍 |
| 高窄旗形 | 近 40 日高低点比 > 1.6，近 10 日振幅 < 15%，缩量 |
| 涨停洗盘 | 昨日涨停，今日阴线放量且最低价不破昨收 |

## 本地下载

先还原顺势选股（你现在打开它会看到 Sequoia-X，是因为网页文件被盖掉了）：

**顺势选股还原：https://github.com/yauklt502/my-shunshixuangu/raw/cursor/sequoia-x-backtest-b1c7/portable/shunshi-xuangu-restore.zip**

解压后进入 `顺势选股` 文件夹，双击 `打开选股.bat`，地址是 http://127.0.0.1:8787/ ，页顶应是「顺势选股」。

Sequoia-X 另解压到别的目录（不要再解压进顺势选股）：

**Sequoia-X：https://github.com/yauklt502/my-shunshixuangu/raw/cursor/sequoia-x-backtest-b1c7/portable/sequoia-x.zip**

双击 `打开Sequoia-X.bat`，地址是 http://127.0.0.1:9801/ ，页顶应是「Sequoia-X · 端口 9801」。

| 项目 | 还原包 | 地址 |
|---|---|---|
| 顺势选股 | `shunshi-xuangu-restore.zip` | http://127.0.0.1:8787/ |
| Sequoia-X | `sequoia-x.zip` | http://127.0.0.1:9801/ |

## 网页

```bash
python3 serve_web.py
```

Windows 可双击 `打开Sequoia-X.bat`，打开 http://127.0.0.1:9801/

顺势选股仍用 **8787**，本页用 **9801**，必须放在两个不同文件夹里。

- 「扫描主板」：新浪 `sh_a`+`sz_a`，只留 `600/601/603/605/000/001/002` 非 ST、非次新
- 「扫描创业板」：新浪 `cyb`，只留 `300` 开头非 ST、非次新
- 四套规则下各有「只扫这套」（跟当前板块走：先扫主板或创业板）
- 不扫科创 `688`、北交所、`301`、ST / 退市、次新
- 右上角数据源：同花顺+腾讯（默认）/ 腾讯 / 同花顺；一键截屏

## 回测（持股 3 日）

```bash
pip install -r requirements.txt
PYTHONPATH=src python scripts/run_sequoia_backtest.py --download --hold-days 3
PYTHONPATH=src pytest tests -q
```

报告：[docs/sequoia_x_backtest.md](docs/sequoia_x_backtest.md)
