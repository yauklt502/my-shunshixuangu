# 通达信第三方插件（tdx-mcp / eltdx）

TSP 后端通过 `eltdx` 直连通达信行情主站，并在 venv 中安装 `tdx-mcp`（含 eltdx 依赖）。

## 默认主站

```
115.238.90.165:7709
```

可用环境变量覆盖：

```bash
export TDX_HOST=115.238.90.165:7709
```

## 已验证能力

- 五档盘口 `quotes.get_depth`
- 当日分时 `minutes.today`
- 1 分钟 / 5 分钟 / 日 K `bars.get`

## 安装

```bash
cd tsp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` 含：

- `eltdx[http]>=3.1.1`
- `tdx-mcp==0.1.5`（兼容声明的 0.1.x 插件链）
