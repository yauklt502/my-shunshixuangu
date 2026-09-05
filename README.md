# 顺势选股 · Role Ladder

实时识别并展示 **龙头 / 中位股 / 补涨龙** 的对照关系，支持东方财富 / 通达信(eltdx) / 同花顺口径切换，点击个股弹出 Tick Stock Panel 风格浮窗（日K、分时、五档），顶部可切历史日期复盘，并支持一键截图。浅色主题。

## 下载

- ZIP：https://github.com/yauklt502/my-shunshixuangu/archive/refs/heads/cursor/role-ladder-stock-panel-a9f4.zip
- 克隆：`git clone -b cursor/role-ladder-stock-panel-a9f4 https://github.com/yauklt502/my-shunshixuangu.git`

## 一键启动（推荐）

### Windows
1. 解压 ZIP  
2. **双击** `一键启动.bat`  
3. 浏览器自动打开 http://127.0.0.1:5173  
4. 停止：双击 `一键停止.bat`

### macOS
1. 解压 ZIP  
2. 首次若提示无执行：在终端运行 `chmod +x 一键启动.command 一键启动.sh`  
3. **双击** `一键启动.command`（或终端执行 `./一键启动.sh`）  
4. Ctrl+C 停止

### Linux
```bash
chmod +x 一键启动.sh
./一键启动.sh
```

> 首次启动会自动创建 Python 虚拟环境并 `npm install`，可能需要几分钟。  
> 环境要求：Python 3.10+、Node.js 18+。

## 手动启动（可选）

```bash
# 后端
cd backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export PYTHONPATH=.
uvicorn app.main:app --host 0.0.0.0 --port 8010

# 前端（另开终端）
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## 一句话对照

| 角色 | 时机 | 位置 | 对龙头关系 |
|---|---|---|---|
| 龙头 | 主线初期~高潮 | 题材最高板 | 定价锚 |
| 中位股 | 主线中期 | 约 3~5 板中位开挂 | 伴随扩散 |
| 补涨龙 | 龙头末期/断板前后 | 低位重新启动 | 承接溢出 |

## 数据源

- **eastmoney**：免费涨停池 + K线/分时（默认池源）
- **tdx**：`eltdx` TCP 通达信主站，优先用于报价/五档/日K/分时（可用环境变量 `SSP_TDX_HOST=115.238.90.165:7709`）
- **tonghuashun**：同花顺口径聚合（当前桥接东财免费接口）

## 说明

仅供学习研究，不构成投资建议。