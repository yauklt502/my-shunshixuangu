from __future__ import annotations

from typing import Any

from app.providers.eastmoney import EastMoneyProvider


class TonghuashunProvider(EastMoneyProvider):
    name = "tonghuashun"
    display_name = "同花顺口径 (免费聚合)"

    def health(self) -> dict[str, Any]:
        h = super().health()
        h["provider"] = self.name
        h["detail"] = f"ths-bridge via eastmoney; {h.get('detail', '')}"
        return h