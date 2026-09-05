# 先比独 · Tick Stock Panel

把「先 / 比 / 独」核心领涨理论做成可切换数据源的选股软件。

## 一键启动

### Windows（重要）
解压后双击根目录 **`START.cmd`**。装完依赖后会**自动打开网页**。

若提示 pip / tdx-mcp 失败（旧包问题）：
1. 删除文件夹 `tsp\.venv`
2. 重新下载最新 ZIP 后再双击 `START.cmd`  
   （新版本已去掉对 Python 3.12 的 tdx-mcp 强制依赖，3.11 可用）

其它排查：双击 `检查环境.bat`；需 Python 3.10+ 并勾选 PATH。

### macOS / Linux
```bash
chmod +x 一键启动.sh
./一键启动.sh
```

首次会自动建虚拟环境、装依赖，并打开浏览器：http://127.0.0.1:8765  
**启动后请勿关闭黑色命令行窗口。**

## 功能

- **先比独策略**：先锁共识赛道，比结构量价，独抓核心领涨
- **数据源可切换**：东方财富 / 同花顺 / 通达信（eltdx TCP）
- **Tick Stock Panel**：点击个股浮窗查看日K、分时、1m/5m、五档
- **顶部复盘日期**：方便历史回看
- **一键截图**：主页面与浮窗均可导出 PNG
- **浅色主题**：避免黑底看不清

## 下载

完整压缩包（本分支最新代码）：

```
https://github.com/yauklt502/my-shunshixuangu
/archive/refs/heads/cursor/xianbidu-tsp-33cc.zip
```

解压后运行根目录 `一键启动.bat`（Windows）或 `./一键启动.sh`（Mac/Linux）。

通达信主站默认：`115.238.90.165:7709`（可用环境变量 `TDX_HOST` 覆盖）。

## 说明

仅供学习研究，不构成投资建议。
