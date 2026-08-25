"""Minimal Fuyao (同花顺) REST client for A-share / meta endpoints."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

import requests

DEFAULT_BASE_URL = "https://fuyao.aicubes.cn"


class FuyaoError(RuntimeError):
    """Raised when the API returns a non-zero business code or HTTP failure."""

    def __init__(self, message: str, *, code: int | None = None, request_id: str | None = None):
        super().__init__(message)
        self.code = code
        self.request_id = request_id


class FuyaoClient:
    """Thin wrapper around https://fuyao.aicubes.cn REST APIs.

    Auth: send ``X-api-key`` on every request.
    Envelope: ``{code, message, request_id, data}`` — business payload is ``data``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("FUYAO_API_KEY") or os.environ.get("API_KEY")
        if not self.api_key:
            raise ValueError("Set FUYAO_API_KEY (or pass api_key=...)")
        self.base_url = (base_url or os.environ.get("FUYAO_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def _headers(self) -> dict[str, str]:
        return {"X-api-key": self.api_key, "Accept": "application/json"}

    def get(self, path: str, **params: Any) -> Any:
        cleaned = {k: v for k, v in params.items() if v is not None}
        url = f"{self.base_url}{path}"
        if cleaned:
            url = f"{url}?{urlencode(cleaned, doseq=True)}"
        resp = self.session.get(url, headers=self._headers(), timeout=self.timeout)
        resp.raise_for_status()
        payload = resp.json()
        code = payload.get("code")
        if code != 0:
            raise FuyaoError(
                payload.get("message") or f"Fuyao error code={code}",
                code=code,
                request_id=payload.get("request_id"),
            )
        return payload.get("data")

    # --- meta ---

    def search_tickers(self, q: str, *, limit: int = 10, asset_type: str | None = None) -> Any:
        return self.get("/api/meta/tickers/search", q=q, limit=limit, asset_type=asset_type)

    def list_tickers(
        self,
        *,
        market: str | None = None,
        asset_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Any:
        return self.get(
            "/api/meta/tickers/list",
            market=market,
            asset_type=asset_type,
            limit=limit,
            offset=offset,
        )

    # --- prices ---

    def prices_snapshot(self, thscodes: str | list[str] | None = None, *, limit: int | None = None, offset: int | None = None) -> Any:
        codes = ",".join(thscodes) if isinstance(thscodes, list) else thscodes
        return self.get("/api/a-share/prices/snapshot", thscodes=codes, limit=limit, offset=offset)

    def prices_historical(
        self,
        thscode: str,
        *,
        interval: str = "1d",
        start: int | None = None,
        end: int | None = None,
        adjust: str | None = "forward",
    ) -> Any:
        return self.get(
            "/api/a-share/prices/historical",
            thscode=thscode,
            interval=interval,
            start=start,
            end=end,
            adjust=adjust,
        )

    # --- calendar / financials ---

    def trading_days(self) -> Any:
        return self.get("/api/a-share/calendar/trading-days")

    def income_statements(
        self,
        thscode: str,
        *,
        period: str = "annual",
        limit: int | None = 4,
        start: int | None = None,
        end: int | None = None,
    ) -> Any:
        return self.get(
            "/api/a-share/financials/income-statements",
            thscode=thscode,
            period=period,
            limit=limit,
            start=start,
            end=end,
        )

    # --- special data (复盘常用) ---

    def limit_up_pool(self, *, date_ms: int | None = None, page: int = 1, size: int = 50) -> Any:
        return self.get("/api/a-share/special-data/limit-up-pool", date_ms=date_ms, page=page, size=size)

    def limit_down_pool(self, *, date_ms: int | None = None, page: int = 1, size: int = 50) -> Any:
        return self.get("/api/a-share/special-data/limit-down-pool", date_ms=date_ms, page=page, size=size)

    def limit_break_pool(self, *, date_ms: int | None = None, page: int = 1, size: int = 50) -> Any:
        return self.get("/api/a-share/special-data/limit-break-pool", date_ms=date_ms, page=page, size=size)

    def limit_up_ladder(self, *, date_ms: int | None = None) -> Any:
        return self.get("/api/a-share/special-data/limit-up-ladder", date_ms=date_ms)

    def hot_stock_list(self, *, period: str = "day") -> Any:
        """period: ``day`` (24h) or ``hour``."""
        return self.get("/api/a-share/special-data/hot-stock-list", period=period)

    def skyrocket_list(self, *, period: str = "day") -> Any:
        return self.get("/api/a-share/special-data/skyrocket-list", period=period)

    def dragon_tiger_list(self, *, date: str | None = None, board_type: str = "all") -> Any:
        """board_type: ``all`` / ``org`` / ``hot_money``; date: ``yyyy-MM-dd``."""
        return self.get(
            "/api/a-share/special-data/dragon-tiger-list",
            date=date,
            board_type=board_type,
        )

    def anomaly_analysis_stock(self, thscodes: str | list[str]) -> Any:
        codes = ",".join(thscodes) if isinstance(thscodes, list) else thscodes
        return self.get("/api/a-share/special-data/anomaly-analysis-stock", thscodes=codes)
