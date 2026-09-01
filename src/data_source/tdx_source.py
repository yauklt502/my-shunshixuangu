"""通达信 pytdx 行情源 — 服务器池、测速选优、线程本地连接（与桌面 tdx_source 同思路）."""

from __future__ import annotations

import logging
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

logger = logging.getLogger(__name__)

TDX_PORT = 7709

# 候选服务器（优先 pytdx 内置列表 + 近年实测可用 IP）
def _build_candidate_servers() -> list[str]:
    ips: list[str] = []
    try:
        from pytdx.config.hosts import hq_hosts

        for _name, ip, port in hq_hosts:
            if port == TDX_PORT and ip not in ips:
                ips.append(ip)
    except ImportError:
        pass
    extra = [
        "180.153.18.170",
        "218.75.126.9",
        "115.238.56.198",
        "60.191.117.167",
        "122.51.120.217",
        "123.60.186.45",
        "218.6.170.47",
        "117.34.114.13",
    ]
    for ip in extra:
        if ip not in ips:
            ips.append(ip)
    return ips[:40]


CANDIDATE_SERVERS: list[str] = _build_candidate_servers()

# 当前选中服务器（全局共享，pick_server 后写入）
_SERVER: dict = {"ip": "", "latency_ms": 0.0, "picked_at": 0.0}

_local = threading.local()
_probe_lock = threading.Lock()


def _market_of(code: str) -> int:
    """沪 1 / 深 0"""
    c = str(code).zfill(6)
    if c.startswith(("5", "6", "9")):
        return 1
    return 0


def _port_open(ip: str, port: int = TDX_PORT, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def _probe_server(ip: str, timeout: float = 3.0) -> tuple[str, float] | None:
    """测速：能连上且 pytdx 返回有效行情则返回 (ip, latency_ms)。"""
    t0 = time.perf_counter()
    if not _port_open(ip, TDX_PORT, timeout=min(timeout, 1.5)):
        return None
    try:
        from pytdx.hq import TdxHq_API

        api = TdxHq_API(heartbeat=False)
        if api.connect(ip, TDX_PORT, time_out=int(timeout)):
            q = api.get_security_quotes([(1, "600519")])
            api.disconnect()
            if q and float(q[0].get("price") or 0) > 0:
                ms = (time.perf_counter() - t0) * 1000
                return ip, ms
        else:
            try:
                api.disconnect()
            except Exception:
                pass
    except Exception as e:
        logger.debug("probe %s failed: %s", ip, e)
    return None


def pick_server(force: bool = False, max_workers: int = 12) -> Optional[str]:
    """
    并发探测候选服务器，选延迟最低的可用 IP。
    结果写入 _SERVER['ip']，供全局复用。
    """
    with _probe_lock:
        if _SERVER.get("ip") and not force:
            age = time.time() - float(_SERVER.get("picked_at") or 0)
            if age < 300:  # 5 分钟内复用
                return _SERVER["ip"]

        best_ip: Optional[str] = None
        best_ms = float("inf")
        candidates = CANDIDATE_SERVERS[:]

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {ex.submit(_probe_server, ip): ip for ip in candidates}
            for fut in as_completed(futs):
                res = fut.result()
                if res and res[1] < best_ms:
                    best_ip, best_ms = res

        if best_ip:
            _SERVER["ip"] = best_ip
            _SERVER["latency_ms"] = round(best_ms, 1)
            _SERVER["picked_at"] = time.time()
            logger.info("TDX server picked: %s (%.1fms)", best_ip, best_ms)
            return best_ip

        _SERVER["ip"] = ""
        return None


def get_server_ip() -> str:
    return _SERVER.get("ip") or ""


def get_server_info() -> dict:
    return {
        "ip": _SERVER.get("ip") or "",
        "port": TDX_PORT,
        "latency_ms": _SERVER.get("latency_ms"),
        "candidates": len(CANDIDATE_SERVERS),
    }


def get_api():
    """每线程独立 pytdx 连接（非线程安全）。"""
    ip = pick_server()
    if not ip:
        raise RuntimeError("未找到可用通达信行情服务器，请检查网络或更新 CANDIDATE_SERVERS")

    if getattr(_local, "api", None) is None or getattr(_local, "ip", None) != ip:
        from pytdx.hq import TdxHq_API

        api = TdxHq_API(heartbeat=True)
        if not api.connect(ip, TDX_PORT, time_out=5):
            _local.api = None
            raise RuntimeError(f"连接通达信服务器失败: {ip}:{TDX_PORT}")
        _local.api = api
        _local.ip = ip
    return _local.api


def health_check() -> dict:
    """探测通达信 7709 端口并选最优服务器。"""
    ip = pick_server(force=True)
    if not ip:
        return {
            "ok": False,
            "message": "未找到可用通达信服务器，请检查网络或更新服务器池",
            **get_server_info(),
        }
    try:
        from pytdx.hq import TdxHq_API

        api = TdxHq_API(heartbeat=False)
        ok = api.connect(ip, TDX_PORT, time_out=5)
        if ok:
            q = api.get_security_quotes([(1, "600519")])
            api.disconnect()
            if q and float(q[0].get("price") or 0) > 0:
                return {"ok": True, "message": f"通达信已连接 {ip}:{TDX_PORT}", **get_server_info()}
        return {"ok": False, "message": f"服务器 {ip} 无有效行情响应", **get_server_info()}
    except Exception as e:
        return {"ok": False, "message": str(e), **get_server_info()}
