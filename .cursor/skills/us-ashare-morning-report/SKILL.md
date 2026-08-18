---
name: us-ashare-morning-report
description: Generate US × A-share morning briefing HTML, write to E:/Cursor/reports, and serve via local HTTP so Cursor Simple Browser can preview. Use when the user asks for A股晨报、盘前分析、美股联动、morning report, or wants to open the report in a browser.
---

# US × A-Share Morning Report

## User preference (remember)

When yakult asks for A-share opportunity analysis or morning briefings:

1. **Deliverable**: standalone dark-theme HTML report (not markdown-only).
2. **Output path (Windows)**: `E:/Cursor/reports/`
3. **Filename**: `us-ashare-morning-report-YYYYMMDD_HHMM.html`
4. **Also write**: `E:/Cursor/reports/latest.html` (always points to newest)
5. **Preview**: start local HTTP server — do **not** rely on `file://` or Cursor Simple Browser opening remote workspace paths.
6. **Default URL**: `http://127.0.0.1:8765/latest.html`

## How to run (Windows)

Double-click or run from repo root:

```bat
scripts\start-morning-report.bat
```

Or:

```powershell
python scripts/morning_report/run.py
```

Options:

```text
--serve-only     Serve existing reports without regenerating
--no-browser     Skip auto-open browser
--port 8765      Override port
--output E:/Cursor/reports
```

## Report structure (required sections)

1. 一句话结论
2. 昨夜美股（指数 + 存储/油价/利率/AI 映射）
3. 昨日 A 股（指数、板块、资金流向）
4. 宏观联动 & 今日已知消息
5. 板块机会 P1–P4 + **个股表格**（代码/逻辑/看点/风险）
6. 回避方向
7. 盘中验证点
8. 风险提示 + 免责声明

## Content workflow

1. Gather **prior trading day A-share** close, **overnight US** close, and **today pre-market** public news.
2. Update `scripts/morning_report/template.html` placeholders or regenerate via `generate.py`.
3. Run `python scripts/morning_report/run.py` to write files under `E:/Cursor/reports/` and start server.
4. Tell user to open `http://127.0.0.1:8765/latest.html` in Cursor Simple Browser or system browser.

## File map

| Path | Role |
| --- | --- |
| `scripts/morning_report/template.html` | HTML template with `{{PLACEHOLDER}}` tokens |
| `scripts/morning_report/generate.py` | Render template → dated file + latest.html + index.html |
| `scripts/morning_report/serve.py` | Static HTTP server on 127.0.0.1 |
| `scripts/morning_report/run.py` | Generate + serve + open browser |
| `scripts/morning_report/config.json` | Default output_dir `E:/Cursor/reports`, port 8765 |
| `scripts/start-morning-report.bat` | Windows one-click launcher |

## Styling

Match existing reports: dark GitHub card theme, red-up/green-down (A-share), section nav anchors, priority tags P1–P4, stock tables.

## Notes

- Cloud Agent cannot write to user's `E:` drive directly; scripts run **on user's Windows machine** after clone/pull.
- If user only wants analysis in chat, still offer to regenerate HTML + serve command.
- Reports are research summaries, not buy/sell advice — include disclaimer in footer.
