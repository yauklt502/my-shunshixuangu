# my-shunshixuangu

A 股短线条件选股软件。研究笔记，不构成投资建议。

## 本机安装包（推荐）

下载压缩包，解压后双击启动：

- 仓库内：[`deploy/顺势竞价选股-本机版.zip`](deploy/顺势竞价选股-本机版.zip)
- 重新打包：`python3 scripts/pack_portable.py`

**Windows**

1. 解压到例如 `D:\顺势竞价选股\`
2. 安装 [Python 3](https://www.python.org/downloads/)（勾选 Add to PATH）
3. 双击 `启动选股.bat`（首次自动装依赖）
4. 浏览器打开 http://127.0.0.1:8787/

**Mac / Linux**

```bash
unzip 顺势竞价选股-本机版.zip
cd 顺势竞价选股
./启动选股.sh
```

详细说明见压缩包内 `使用说明.txt`。

## 开发启动

```bash
pip install -r requirements.txt
python3 -m app
```

| 功能 | 说明 |
|---|---|
| 连板优化 | 收紧量价 + 高度/炸板/市值，综合分 Top5 |
| 胜率100% | 回测全胜方案：涨幅 3–5%，每天最多 3 只，**开盘后 +0.8% 止盈** |
| 原版公式 | 原始「竞价涨停取反」条件 |
| 盘前盯盘 | 9:15–9:30 实时盘口 + 走势标签，可 15 秒自动刷新 |

## 公式与回测

优化说明：[`docs/formula-optimization.md`](docs/formula-optimization.md)  
回测报告：[`results/lianban_backtest_report.md`](results/lianban_backtest_report.md)  
问财/通达信：`formulas/`

```bash
python3 -m pytest -q
python3 scripts/auction_screener.py
python3 scripts/preopen_pick.py --watch
```
