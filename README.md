# 顺势选股 · Role Ladder

实时识别并展示 **日内总龙头 / 情绪龙头 / 龙二 / 龙三**，以及中位股、补涨龙。支持东方财富 / 通达信(eltdx) / 同花顺口径切换，点击个股弹出 Tick Stock Panel 风格浮窗（日K、分时、五档），顶部可切历史日期复盘，并支持一键截图。浅色主题。

## 下载

- ZIP：https://github.com/yauklt502/my-shunshixuangu/archive/refs/heads/cursor/role-ladder-stock-panel-a9f4.zip
- 克隆：`git clone -b cursor/role-ladder-stock-panel-a9f4 https://github.com/yauklt502/my-shunshixuangu.git`

## 一键启动

解压后**双击**即可打开网页。页面已预构建，**不需要 Node.js**。

| 系统 | 双击启动 | 停止 |
|---|---|---|
| **Windows** | `一键启动.bat` | Ctrl+C 或 `一键停止.bat` |
| **macOS** | `一键启动.command` | Ctrl+C 或 `./一键停止.sh` |
| **Linux** | `./一键启动.sh` | Ctrl+C 或 `./一键停止.sh` |

地址：**http://127.0.0.1:5173**

- 本机只需安装 **Python 3.10+**（Windows 勾选 Add to PATH）
- **第一次**会把运行库装到用户目录（Windows：`%LOCALAPPDATA%\shunshi-xuangu`），大约一两分钟
- **以后再双击、再解压一份 ZIP，都不会重新下载**，直接开网页
- 保持启动窗口不要关

### 出现「无法访问此网站」？

先双击启动脚本；地址必须带端口 `5173`。日志在 `.run/server.log`。

### macOS 首次无法打开

```bash
chmod +x 一键启动.command 一键启动.sh 一键停止.sh launcher.py
xattr -d com.apple.quarantine 一键启动.command 2>/dev/null || true
```

## 一句话对照

| 角色 | 怎么认 | 作用 |
|---|---|---|
| 日内总龙头 | 全市场最高连板（同高看先封） | 高度锚 |
| 情绪龙头 | 最宽主线的龙头；高度断档时与总龙可不是同一只 | 方向锚 |
| 龙二 / 龙三 | 情绪主线里排第 2、第 3 | 替补辨识 |
| 题材龙 | 其他题材的最高板 | 支线龙头 |
| 中位股 | 约 3~5 板且非龙头 | 中期扩散 |
| 补涨龙 | 高位龙头下的低位启动 | 承接溢出 |

## 数据源

- **eastmoney**：免费涨停池 + K线/分时（默认池源）
- **tdx**：`eltdx` TCP 通达信主站，优先用于报价/五档/日K/分时
- **tonghuashun**：同花顺口径聚合（当前桥接东财免费接口）

## 说明

仅供学习研究，不构成投资建议。
