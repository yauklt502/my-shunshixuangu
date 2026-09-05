#!/usr/bin/env bash
# 仓库根目录一键启动入口
set -euo pipefail
cd "$(dirname "$0")"
exec bash "./tsp/start.sh"
