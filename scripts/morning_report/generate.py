#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render morning report HTML from template."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

WEEKDAYS_CN = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
REPORT_PREFIX = "us-ashare-morning-report"


def load_config(config_path: Path) -> dict:
    import platform

    if platform.system() == "Windows":
        default_output = "E:/Cursor/reports"
    else:
        default_output = str(Path.home() / "Cursor" / "reports")

    defaults = {
        "output_dir": default_output,
        "host": "127.0.0.1",
        "port": 8765,
        "auto_open_browser": True,
    }
    if config_path.exists():
        with config_path.open(encoding="utf-8") as f:
            defaults.update(json.load(f))
    return defaults


def report_context(now: datetime | None = None) -> dict:
    now = now or datetime.now()
    iso_date = now.strftime("%Y-%m-%d")
    weekday = WEEKDAYS_CN[now.weekday()]
    report_date_cn = f"{now.year}年{now.month}月{now.day}日（{weekday}）"
    generated_time = now.strftime("%H:%M CST")
    generated_timestamp = now.strftime("%Y-%m-%d %H:%M CST")
    filename = f"{REPORT_PREFIX}-{now.strftime('%Y%m%d_%H%M')}.html"
    return {
        "ISO_DATE": iso_date,
        "REPORT_DATE_CN": report_date_cn,
        "GENERATED_TIME": generated_time,
        "GENERATED_TIMESTAMP": generated_timestamp,
        "FILENAME": filename,
    }


def render_template(template_path: Path, context: dict) -> str:
    html = template_path.read_text(encoding="utf-8")
    for key, value in context.items():
        html = html.replace(f"{{{{{key}}}}}", value)
    missing = re.findall(r"\{\{([A-Z_]+)\}\}", html)
    if missing:
        unique = sorted(set(missing))
        raise ValueError(f"Unresolved template placeholders: {', '.join(unique)}")
    return html


def build_index_html(output_dir: Path) -> str:
    reports = sorted(
        output_dir.glob(f"{REPORT_PREFIX}-*.html"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    items = "\n".join(
        f'    <li><a href="{p.name}">{p.name}</a></li>' for p in reports[:30]
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url=latest.html">
  <title>A股晨报索引</title>
  <style>
    body {{ font-family: sans-serif; background:#0d1117; color:#f0f6fc; padding:24px; }}
    a {{ color:#58a6ff; }}
    li {{ margin:8px 0; }}
  </style>
</head>
<body>
  <h1>美股 × A股 晨报索引</h1>
  <p>自动跳转到 <a href="latest.html">latest.html</a></p>
  <ul>
{items}
  </ul>
</body>
</html>
"""


def generate_report(
    output_dir: Path,
    template_path: Path,
    now: datetime | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    context = report_context(now)
    html = render_template(template_path, context)

    dated_path = output_dir / context["FILENAME"]
    latest_path = output_dir / "latest.html"
    index_path = output_dir / "index.html"

    dated_path.write_text(html, encoding="utf-8")
    shutil.copy2(dated_path, latest_path)
    index_path.write_text(build_index_html(output_dir), encoding="utf-8")

    return dated_path


def main() -> None:
    base = Path(__file__).resolve().parent
    config = load_config(base / "config.json")
    output_dir = Path(config["output_dir"])
    template_path = base / "template.html"

    if not template_path.exists():
        raise SystemExit(f"Template not found: {template_path}")

    path = generate_report(output_dir, template_path)
    print(f"Generated: {path}")
    print(f"Latest:    {output_dir / 'latest.html'}")


if __name__ == "__main__":
    main()
