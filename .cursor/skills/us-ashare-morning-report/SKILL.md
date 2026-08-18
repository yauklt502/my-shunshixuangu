---
name: us-ashare-morning-report
description: Generate US × A-share morning briefing HTML, write to E:/Cursor/reports, and serve via local HTTP so Cursor Simple Browser can preview. Use when the user asks for A股晨报、盘前分析、美股联动、morning report, or wants to open the report in a browser.
---

# US × A-Share Morning Report

## User preference (remember)

When yakult asks for A-share opportunity analysis or morning briefings:

1. **Default deliverable**: **Markdown report directly in chat** (sections, tables, bullet lists) — user reads it in conversation history. **Do NOT** default to HTML, bat scripts, or `E:/Cursor/reports` unless they explicitly ask.
2. **Optional HTML** (only when requested): standalone dark-theme HTML + local HTTP to `E:/Cursor/reports/` — see file map below.

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

## Report structure (required sections — chat Markdown)

Use this structure with `##` headings, markdown tables, and bold emphasis:

1. 先说结论（3–5 条 bullet）
2. 昨日 A 股（指数表 + 领涨/领跌 + 资金）
3. 昨夜美股（指数表 + 结构映射）
4. 今日已知公开信息
5. 板块机会（按优先级 P1–P9，**含个股表格或 bullet**）
6. 今日交易地图（多头排序 / 回避 / 观察点）
7. 风险提示 + 免责声明一行
8. 一句话收尾

Style: 完整句子、表格清晰、板块后紧跟个股方向，与首版聊天晨报一致。

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
