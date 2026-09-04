#!/usr/bin/env python3
"""启动清醒龙头战法选股软件。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from ui.app import main

if __name__ == "__main__":
    main()
