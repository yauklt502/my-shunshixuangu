# 通达信行情（eltdx）

TSP 后端通过 **eltdx** 直连通达信行情主站。`tdx-mcp` 为可选插件（需 Python ≥ 3.12），**不是启动必需**。

## 默认主站

```
115.238.90.165:7709
```

```bash
export TDX_HOST=115.238.90.165:7709
```

## 已验证能力

- 五档盘口
- 当日分时
- 1 分钟 / 5 分钟 / 日 K

## 安装

核心依赖（Python 3.10+ 均可）：

```bash
cd tsp
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
```

可选（仅 Python ≥ 3.12）：

```bash
pip install -r requirements-optional.txt
```
