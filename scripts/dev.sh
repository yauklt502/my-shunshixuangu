#!/usr/bin/env bash
# 兼容旧路径：转发到仓库根目录一键启动
exec "$(cd "$(dirname "$0")/.." && pwd)/一键启动.sh"