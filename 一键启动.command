#!/bin/bash
# macOS 双击启动：解压后双击本文件即可
cd "$(dirname "$0")"
chmod +x "./一键启动.sh" "./scripts/dev.sh" 2>/dev/null || true
exec "./一键启动.sh"