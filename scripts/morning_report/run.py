#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate morning report to E:/Cursor/reports and start local HTTP preview."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from generate import generate_report, load_config
from serve import start_server


def main() -> int:
    base = Path(__file__).resolve().parent
    config_path = base / "config.json"

    parser = argparse.ArgumentParser(
        description="Generate US×A-share morning report and serve via HTTP"
    )
    parser.add_argument("--output", help="Override output directory")
    parser.add_argument("--host", help="Bind host")
    parser.add_argument("--port", type=int, help="Bind port")
    parser.add_argument("--serve-only", action="store_true", help="Skip generation")
    parser.add_argument("--generate-only", action="store_true", help="Generate files and exit")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser")
    args = parser.parse_args()

    config = load_config(config_path)
    output_dir = Path(args.output or config["output_dir"])
    host = args.host or config.get("host", "127.0.0.1")
    port = args.port or config.get("port", 8765)
    open_browser = not args.no_browser and config.get("auto_open_browser", True)

    template_path = base / "template.html"
    if not args.serve_only:
        if not template_path.exists():
            print(f"Error: template missing: {template_path}", file=sys.stderr)
            return 1
        report_path = generate_report(output_dir, template_path)
        print(f"✓ Report written: {report_path}")
        print(f"✓ Latest copy:  {output_dir / 'latest.html'}")
        print(f"✓ Index:        {output_dir / 'index.html'}")

    if args.generate_only:
        return 0

    if not (output_dir / "latest.html").exists():
        print(f"Error: {output_dir / 'latest.html'} not found.", file=sys.stderr)
        print("Run without --serve-only to generate first.", file=sys.stderr)
        return 1

    server, url = start_server(
        output_dir,
        host=host,
        port=port,
        open_browser=open_browser,
        open_path="/latest.html",
    )
    print(f"✓ Preview: {url}")
    print("  Cursor Simple Browser: paste the URL above")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
