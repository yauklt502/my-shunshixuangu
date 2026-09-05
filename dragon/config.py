"""服务端口、启动地址。改端口只改这里。"""

import os

PORT = 8688
HOST = "0.0.0.0"
LOCAL_URL = f"http://127.0.0.1:{PORT}"

# 通达信行情主站。用户实测 115.238.90.165:7709 五档/1m/5m/日K/分时都通。
TDX_HOST = os.environ.get("TDX_HOST", "115.238.90.165:7709")
