# my-shunshixuangu

## 美股 × A股 盘前晨报

生成 HTML 晨报 → 输出到 `E:\Cursor\reports\` → 本地 HTTP 预览。

### 一键启动（Windows）

**第一次使用（推荐）：** 只生成文件到 `E:\Cursor\reports`，并自动打开浏览器

```text
scripts\generate-report-to-e-cursor.bat
```

**生成 + HTTP 服务（Cursor Simple Browser 预览用）：**

```text
scripts\start-morning-report.bat
```

浏览器打开：`http://127.0.0.1:8765/latest.html`

> **重要：** 报告不会自动出现在 `E:\Cursor\reports`。必须在本机 Windows 上运行上述 `.bat`，脚本才会创建 `latest.html`。

### 目录是空的？

1. 确认已 `git pull` 拉取含 `scripts/morning_report/` 的代码
2. 双击 `scripts\generate-report-to-e-cursor.bat`（不要只打开空文件夹等待）
3. 若提示找不到 Python：安装 [python.org](https://www.python.org/downloads/) 并勾选 **Add to PATH**
4. 仍失败：手动新建 `E:\Cursor\reports`，再运行 bat

### 手动命令

```bash
# 生成 + 启动服务
python scripts/morning_report/run.py

# 仅生成（不启动服务）
python scripts/morning_report/generate.py

# 仅服务已有报告
python scripts/morning_report/run.py --serve-only
```

### 输出目录

| 文件 | 说明 |
| --- | --- |
| `E:\Cursor\reports\us-ashare-morning-report-YYYYMMDD_HHMM.html` | 带时间戳的报告 |
| `E:\Cursor\reports\latest.html` | 始终指向最新一份 |
| `E:\Cursor\reports\index.html` | 历史列表 |

配置见 `scripts/morning_report/config.json`。

### Agent 技能

Cursor Agent 生成晨报时会遵循 `.cursor/skills/us-ashare-morning-report/SKILL.md` 中的流程与输出规范。
