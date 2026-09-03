#!/bin/bash
cd "$(dirname "$0")"
echo ""
echo "  真龙识别 · 正在启动..."
echo "  浏览器会自动打开 http://127.0.0.1:8765/"
echo "  按 Ctrl+C 或关闭终端即可停止"
echo ""
open "http://127.0.0.1:8765/" 2>/dev/null || xdg-open "http://127.0.0.1:8765/" 2>/dev/null &
python3 server.py
