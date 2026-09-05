# 三条纪律看板

把「低吸纪律、二三板节奏、回撤时别乱动」做成白底实时看板。

## 功能

1. **低吸纪律** — 日内高低点位置 + **回踩 MA5**
2. **二三板节奏** — 涨停梯队；**点击二/三板股票**可加入低吸观察
3. **回撤不乱动** — 上证/创业板近高点回撤；可调软/硬冻结阈值
4. 数据源切换：东方财富 / 同花顺 / 通达信兼容（腾讯）
5. 一键截图（白底 PNG）

## Windows 本地完整包（推荐）

下载：

https://github.com/yauklt502/my-shunshixuangu/raw/cursor/three-discipline-dashboard-a337/web/download/three-discipline-local.zip

解压后**双击 `启动.bat`**，窗口会按 TSP 同款四步启动：

```
[1/4] Creating / checking venv ...
[2/4] Installing dependencies (first run 1-3 min) ...
[3/4] Starting server ...
[4/4] Browser will open automatically when ready.
```

浏览器自动打开 http://127.0.0.1:5177/

本机需要已安装 **Python 3.10+**（勾选 Add to PATH）。首次装依赖约 1–3 分钟，之后再开就快。

重新打包：

```bash
python3 scripts/pack_local.py
```

## 本地开发

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app:app --host 127.0.0.1 --port 5177
```

## Cloudflare Workers 部署

本仓库仍保留 Workers 入口：

- `wrangler.toml`（`name = "my-shunshixuangu"`）
- `src/worker.js`（`/api/*` 行情逻辑）
- `web/` 静态前端

```bash
npm i
npm run deploy
```

> 仅供纪律可视化，不构成投资建议。
