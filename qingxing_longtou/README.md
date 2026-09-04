# 清醒龙头战法 · 选股软件

按短视频《龙头战法到底最重要的是什么》的框架实现：

> 高度聚焦 → 不替市场提前下结论 → 看核心表现/结构失效 → 区分主线与支线 → 看懂弱势 → 接受回撤 → **交易的清醒（管理注意力）**

本工具输出「聚焦 / 观察 / 回避」候选列表，而不是喊单。

## 功能

- **策略引擎**：板块强度、带动性、连板质量、相对强度、弱势信号综合评分
- **数据源**
  - 东方财富：公开行情 / 涨停·炸板池（默认，免 Key）
  - 同花顺：扶摇 API（`FUYAO_API_KEY`）或 `plugins/ths_export/` CSV
  - 通达信：第三方插件导出 `plugins/tdx/export/`、本地 `TDX_HOME`、或 `TDX_PLUGIN_URL` HTTP 桥
- **一键截屏**：保存主窗口 PNG 到 `screenshots/`
- **导出 CSV** / CLI 无界面跑批

## 快速开始

```bash
cd qingxing_longtou
python -m pip install -r requirements.txt
cp .env.example .env   # 可选：填写同花顺 Key / TDX 路径
python run.py          # 桌面 GUI
# 或
python cli.py --source auto --json
python cli.py --source tdx --csv /tmp/out.csv
```

Windows 可双击 `run.bat`。

## 界面说明

| 操作 | 作用 |
|------|------|
| 数据源 | `auto` 自动选可用源；可强制 `eastmoney` / `tonghuashun` / `tdx` |
| 刷新选股 | 拉行情并按清醒龙头规则打分 |
| 一键截屏 | 截取当前窗口到 `screenshots/` |
| 导出 CSV | 保存当前结果表 |

行底色：绿=聚焦，黄=观察，红=回避。

## 通达信 / 同花顺插件

详见：

- `plugins/tdx/README.md`
- `plugins/ths_export/README.md`

仓库已带通达信样例 CSV，可用：

```bash
python cli.py --source tdx --limit 10
```

## 免责声明

学习研究用途，**不构成任何投资建议**。第三方数据可能延迟、缺失或与券商终端不一致。


## Windows 本地部署

1. 下载发布包 `qingxing_longtou_windows_portable.zip` 并解压
2. 安装 [Python 3.11/3.12 x64](https://www.python.org/downloads/)，勾选 Add to PATH
3. 若双击没反应：先跑 `CHECK.bat`，并关闭系统设置里 python 的「应用执行别名」
4. 双击 `INSTALL.bat`，再双击 **`START.bat`**（推荐英文入口）

离线依赖位于包内 `wheels_win/`（适配 Python 3.11 / 3.12）。详见 `本地部署说明.txt`。
