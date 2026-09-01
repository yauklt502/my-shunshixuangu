# 顺时选股 · 高效交易系统

> 技术架构实现，**不构成投资建议**。

七层解耦架构，回测与实盘环境隔离，风控前置，策略与执行分离。

## 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│  前端复盘看板 (frontend/dashboard.html) + WebSocket          │
├─────────────────────────────────────────────────────────────┤
│  API 服务 (FastAPI) — 回测 / 实盘 / 实时推送                  │
├─────────────────────────────────────────────────────────────┤
│  策略引擎层 → 风控层 → 交易执行层 → 券商适配器               │
├─────────────────────────────────────────────────────────────┤
│  数据计算层 (指标预计算)                                      │
├─────────────────────────────────────────────────────────────┤
│  数据源层 (Tushare / Mootdx / 同花顺 / Mock + 实时流)         │
├─────────────────────────────────────────────────────────────┤
│  存储层 (时序 JSON + SQLite + 审计日志)                       │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

```bash
pip install -r requirements.txt

# 回测
python3 -m src.main --mode backtest --symbol 000001 --limit 200

# 实盘（Mock 券商，纸面交易）
python3 -m src.main --mode live --symbols 000001,600519 --poll-interval 5

# 启动 API + 看板（浏览器访问 http://localhost:8000）
python3 -m src.main --mode api --port 8000
```

也可直接打开 `frontend/dashboard.html` 进行本地轻量回测；通过 API 模式可使用后端回测、WebSocket 实时信号和实盘控制。

## 环境变量

| 变量 | 说明 |
|------|------|
| `TUSHARE_TOKEN` | Tushare Pro token |
| `BROKER_TYPE` | 券商类型：`mock`（默认）/ `rest` / `easytrader` |
| `BROKER_API_URL` | REST 券商网关地址 |
| `BROKER_API_TOKEN` | REST 网关鉴权 token |
| `BROKER_CLIENT` | easytrader 客户端类型（如 `yh_client`） |
| `BROKER_ACCOUNT` | easytrader 账户配置路径 |
| `THS_API_URL` | 同花顺开放平台 HTTP 地址 |
| `THS_API_TOKEN` | 同花顺 API token |

## 内置策略

| ID | 名称 |
|----|------|
| `ma5_climb` | 沿 5 日线台阶爬升 |
| `triple_volume` | 三倍量战法 |
| `shrink_limit_up` | 缩量涨停 |
| `macd_cross` | MACD 金叉死叉 |
| `kdj_oversold` | KDJ 超卖反弹 |

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/backtest` | 运行回测 |
| POST | `/api/live/start` | 启动实盘 |
| POST | `/api/live/stop` | 停止实盘 |
| GET | `/api/live/status` | 实盘状态 |
| GET | `/api/strategies` | 策略列表 |
| WS | `/ws` | 实时事件推送 |

## 目录结构

```
src/
├── api/             # FastAPI 服务
├── live/            # 实盘运行器
├── trading/         # 信号→风控→执行管道
├── execution/
│   └── broker/      # 券商适配器 (mock/rest/easytrader)
├── data_source/     # 数据源 + 实时流
├── strategy/        # 策略引擎 + 注册表
├── backtest/        # 回测运行器
└── main.py          # CLI 入口
frontend/
└── dashboard.html   # 复盘看板
```

## 扩展指南

1. **新增数据源**：继承 `DataSource`，注册到 `DataPipeline`
2. **新增策略**：继承 `Strategy`，加入 `strategy/registry.py`
3. **对接券商 REST**：配置 `BROKER_TYPE=rest` 和 `BROKER_API_URL`
4. **对接 easytrader**：`pip install easytrader`，配置 `BROKER_TYPE=easytrader`
