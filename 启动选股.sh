#!/usr/bin/env bash
# 顺势竞价选股 · 一键启动
cd "$(dirname "$0")"
python3 -m app --host 127.0.0.1 --port 8787
