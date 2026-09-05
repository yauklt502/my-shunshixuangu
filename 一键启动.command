#!/bin/bash
cd "$(dirname "$0")"
chmod +x "./一键启动.sh" "./一键停止.sh" "./launcher.py" 2>/dev/null || true
exec "./一键启动.sh"
