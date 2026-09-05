# 顺势选股 · Role Ladder

实时识别并展示 **龙头 / 中位股 / 补涨龙** 的对照关系，支持东方财富 / 通达信(eltdx) / 同花顺口径切换，点击个股弹出 Tick Stock Panel 风格浮窗（日K、分时、五档），顶部可切历史日期复盘，并支持一键截图。浅色主题，避免深色底看不清。

## 一句话对照

| 角色 | 时机 | 位置 | 对龙头关系 |
|---|---|---|---|
| 龙头 | 主线初期~高潮 | 题材最高板 | 定价锚 |
| 中位股 | 主线中期 | 约 3~5 板中位开挂 | 伴随扩散 |
| 补涨龙 | 龙头末期/断板前后 | 低位重新启动 | 承接溢出 |

## 快速启动

```bash
# 后端
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=.
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload

# 前端（另开终端）
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

或：

```bash
bash scripts/dev.sh
```

打开 http://127.0.0.1:5173

## 数据源

- **eastmoney**：免费涨停池 + K线/分时（默认池源）
- **tdx**：`eltdx` TCP 通达信主站，优先用于报价/五档/日K/分时（默认探测可用主站；可用 `SSP_TDX_HOST=115.238.90.165:7709` 指定）
- **tonghuashun**：同花顺口径聚合（当前桥接东财免费接口，可扩展）

## 主要 API

- `GET /api/ladder?date=YYYYMMDD` — 角色梯队
- `GET /api/stock/panel/{code}` — 个股面板打包
- `POST /api/providers/{name}/activate` — 切换数据源

## 说明

仅供学习研究，不构成投资建议。市场数据来自公开免费接口/通达信公开行情主站。