#!/usr/bin/env bash
# 兼容旧路径：转发到仓库根目录一键启动
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/launcher.py" "$@"