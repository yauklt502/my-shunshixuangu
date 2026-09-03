#!/bin/bash
cd "$(dirname "$0")"
echo ""
echo "Zhenlong review server starting..."
echo "Browser will open http://127.0.0.1:8765/"
echo "Press Ctrl+C to stop."
echo ""
python3 server.py --open
