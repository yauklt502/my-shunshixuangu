# my-shunshixuangu

通达信选股脚本。实盘只维护三套，其余文件会转发过去。分段结论见 [ANALYSIS.md](ANALYSIS.md)。

## 实盘入口

| 用途 | 跑这个 | 不要每天满仓 | 持有 |
|---|---|---|---|
| 主板趋势 | `strategies/趋势稳健少.py` | 最多 3 只，无票空仓 | 3–5 日（回测显示隔夜更强） |
| 创业板趋势 | `strategies/趋势王创业板_放宽版.py` | 最多 8 只，扫全部 300 | 3–5 日 |
| 高标交易 | `strategies/主板妖龙优化.py` | 红灯空仓 | 只做隔夜 |
| 高标观察 | `strategies/龙头盯盘.py` | 不下单 | — |

`极速精简.py`、`极速精简优化版.py`、`趋势王主板精选.py` → 稳健少。  
`趋势王创业板_参数调整版.py` → 放宽版。  
`主板妖龙优化1.py` → 妖龙优化。

## 网页（主板 / 创业板分开扫）

数据源可选：同花顺+腾讯（默认，K 线走同花顺公开前复权，行情/量比/换手/流通市值走腾讯批量）、仅腾讯、仅同花顺。名单用新浪板块节点。页面走同源代理，避免浏览器跨域失败。不使用任何第三方付费 Key。

**不要扫全市场。** 点「扫描主板」或「扫描创业板」，或四套规则下的「只扫这套」：

- 主板：新浪 `sh_a`+`sz_a` 再留 `600/601/603/605/000/001/002`，非 ST、非次新
- 创业板：新浪 `cyb` 再留 `300` 开头，非 ST、非次新
- 不扫科创 `688`、北交所、`301`、ST / 退市、上市不足一年或不足 60 根 K 的次新
- **不拉** 新浪 `hs_a` 全 A（不会出现 4970）
- 右上角可切换数据源，并一键截屏

```text
python3 serve_web.py
# 打开 http://127.0.0.1:8787/
# Windows 也可双击 打开选股.bat
```

### 拷到 E 盘

下载 [portable/shunshi-xuangu-E.zip](portable/shunshi-xuangu-E.zip)，解压到 `E:\顺势选股\`，安装 [Python 3](https://www.python.org/downloads/)（勾选 Add to PATH），双击 `打开选股.bat`。不要用 `file://` 直接打开 html。

重新打包 zip：`python3 portable/pack_e_drive.py`

Cloudflare Workers 已接本仓库时，推送后会部署 `web/index.html`，并由 Worker 代理腾讯/新浪。

## 回测

```text
PYTHONPATH=. python3 backtest/download_data.py   # 拉日线
PYTHONPATH=. python3 backtest/sina_fill.py       # 补缺口
PYTHONPATH=. python3 backtest/run.py             # 三套 + 隔夜对照
PYTHONPATH=. python3 backtest/test_engine.py
PYTHONPATH=. python3 backtest/test_features.py
```
