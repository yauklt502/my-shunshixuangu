from __future__ import annotations

from typing import Any

from app.config import settings
from app.providers.base import MarketProvider
from app.providers.eastmoney import EastMoneyProvider
from app.providers.tdx import TdxProvider
from app.providers.tonghuashun import TonghuashunProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, MarketProvider] = {
            "eastmoney": EastMoneyProvider(),
            "tdx": TdxProvider(),
            "tonghuashun": TonghuashunProvider(),
        }
        self._active = settings.default_provider
        self._pool_pref = "eastmoney"

    def list_providers(self) -> list[dict[str, Any]]:
        out = []
        for p in self._providers.values():
            try:
                health = p.health()
            except Exception as e:
                health = {"ok": False, "detail": str(e)}
            out.append(
                {
                    "name": p.name,
                    "display_name": p.display_name,
                    "active": p.name == self._active,
                    "health": health,
                }
            )
        return out

    def set_active(self, name: str) -> None:
        if name not in self._providers:
            raise KeyError(name)
        self._active = name

    def get(self, name: str | None = None) -> MarketProvider:
        return self._providers[name or self._active]

    def pool_provider(self) -> MarketProvider:
        if self._active == "tdx":
            return self._providers[self._pool_pref]
        return self.get()

    def quote_provider(self) -> MarketProvider:
        tdx = self._providers["tdx"]
        try:
            if tdx.health().get("ok"):
                return tdx
        except Exception:
            pass
        return self.get()


registry = ProviderRegistry()