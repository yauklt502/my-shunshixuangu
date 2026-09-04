# 顺势选股 · 龙头确认（本地部署包）

网页版实时龙头确认工具。

- **一字板买不进**：只作高度锚
- **真龙头**：看竞价主动性 + 封板承接
- **主输出**：今日最可能确认的 2 只非一字

---

## 环境要求

- Python 3.10+（推荐 3.11 / 3.12）
- 能访问外网（拉取东方财富公开行情）

检查：

```bash
python3 --version
# Windows 可用：
python --version
```

---

## Windows 一键启动

1. 解压本压缩包到任意目录，例如 `D:\shunshi-leader`
2. 双击 `start.bat`
3. 浏览器打开：http://127.0.0.1:8000

首次会自动安装依赖（fastapi / uvicorn / httpx）。

---

## macOS / Linux 启动

```bash
cd shunshi-leader-confirm
chmod +x run.sh start.sh
./start.sh
```

浏览器打开：http://127.0.0.1:8000

---

## 手动启动（通用）

```bash
cd shunshi-leader-confirm
python3 -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
export PYTHONPATH=.
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

---

## 页面说明

| 区块 | 含义 |
|------|------|
| 确认榜 Top 2 | 今日最可能完成龙头确认的非一字 |
| 高度锚 | 含一字，只看结构，不可买 |
| 连板天梯 | 全市场连板，一字会标注「不可买」 |
| 候选评分 | 昨连板≥2 的评分明细 |

数据每约 60 秒自动刷新，也可点「刷新确认」。

---

## API

- `GET /api/health` 盘段状态
- `GET /api/leader` 龙头确认结果
- `GET /api/leader?date=20260904` 指定交易日（YYYYMMDD）

---

## 常见问题

**1. 页面能开但没有股票？**  
非交易时段或节假日，涨停池可能为空/稀少，属正常。

**2. 依赖安装失败？**  
换国内源：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**3. 端口被占用？**  

```bash
# macOS / Linux
PORT=8001 ./start.sh

# Windows：编辑 start.bat，把 8000 改成 8001
```

**4. 防火墙 / 公司网访问不了东财？**  
本工具需能访问 `push2ex.eastmoney.com` 与 `push2.eastmoney.com`。

---

数据来源：东方财富公开接口。仅供盘面结构与龙头确认参考，不构成投资建议。
