#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local static HTTP server for morning reports."""

from __future__ import annotations

import http.server
import socket
import socketserver
import webbrowser
from pathlib import Path


class ReportHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str | None = None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[HTTP] {self.address_string()} - {fmt % args}")

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()


def find_free_port(host: str, preferred: int) -> int:
    for port in (preferred, preferred + 1, preferred + 2, preferred + 3):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port near {preferred}")


def start_server(
    directory: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    open_path: str = "/latest.html",
) -> tuple[socketserver.TCPServer, str]:
    directory.mkdir(parents=True, exist_ok=True)
    port = find_free_port(host, port)

    handler = lambda *args, **kwargs: ReportHTTPRequestHandler(  # noqa: E731
        *args, directory=str(directory.resolve()), **kwargs
    )
    server = socketserver.TCPServer((host, port), handler)
    server.allow_reuse_address = True

    url = f"http://{host}:{port}{open_path}"

    print(f"Serving {directory.resolve()}")
    print(f"URL: {url}")
    print("Press Ctrl+C to stop.")

    if open_browser:
        webbrowser.open(url)

    return server, url


def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Serve morning reports over HTTP")
    parser.add_argument("--output", default=None, help="Report directory")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    config_path = base / "config.json"
    config = {}
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))

    directory = Path(args.output or config.get("output_dir", "E:/Cursor/reports"))
    host = args.host or config.get("host", "127.0.0.1")
    port = args.port or config.get("port", 8765)
    open_browser = not args.no_browser and config.get("auto_open_browser", True)

    server, _ = start_server(directory, host, port, open_browser)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.shutdown()


if __name__ == "__main__":
    main()
