# my-shunshixuangu

## 美股 × A股 盘前晨报

生成 HTML 晨报 → 输出到 `E:\Cursor\reports\` → 本地 HTTP 预览。

### 一键启动（Windows）

双击：

```text
scripts\start-morning-report.bat
```

浏览器自动打开：`http://127.0.0.1:8765/latest.html`

在 Cursor 右侧 Simple Browser 中粘贴同一 URL 即可预览。

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
