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

## Windows 一键部署（E 盘）

> 适用于 Windows 10/11，需先安装 [Python 3.10+](https://www.python.org/downloads/)（勾选 Add to PATH）

### 若 .bat 双击无反应

1. **优先试英文脚本**：双击 `deploy.bat`（自动选 E/D/C 盘）
2. **右键以管理员身份运行** `一键部署到E盘.bat`
3. **PowerShell 备用**：右键 `install.ps1` → 使用 PowerShell 运行
4. **不要直接双击** `frontend/dashboard.html`，应通过 http://127.0.0.1:8000 访问

### 若 WS 未连接

1. 先运行 `start.bat` 启动后端
2. 浏览器打开 http://127.0.0.1:8000
3. 右上角选数据端口 → 点击 **「连接」** 按钮

### 步骤（推荐用 deploy.bat）

1. 下载 ZIP 并解压到**纯英文路径**（如 `D:\shunshi`）  
   https://github.com/yauklt502/my-shunshixuangu/archive/refs/heads/cursor/trading-system-architecture-f820.zip

2. **双击 `deploy.bat`**（若无反应，见下方「故障排除」）

3. **双击 `start.bat`**，浏览器打开 http://127.0.0.1:8000

4. 看板**第二行**可选择「东方财富实时」数据端口，点击「连接后端」

> 详细说明见解压包内的 `部署说明.txt`

### 故障排除：bat 双击无反应

| 方法 | 操作 |
|------|------|
| A | 双击 **`deploy.bat`**（英文文件名，比中文 bat 更稳定） |
| B | 文件夹内 Shift+右键 → 终端，运行：`powershell -ExecutionPolicy Bypass -File install.ps1` |
| C | 确认已安装 Python 3.10+ 并勾选 **Add to PATH** |

### 安装目录（自动选择，不强制 E 盘）

```
有 E 盘 → E:\shunshi-trading
无 E 盘 → D:\shunshi-trading 或 C:\shunshi-trading
```

## 快速开始（开发者）

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
| `DATA_SOURCE` | 默认数据源，推荐 `eastmoney` |

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
