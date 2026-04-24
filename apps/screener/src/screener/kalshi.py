from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from screener.config import Settings

LOGGER = logging.getLogger(__name__)

def _decimal(value: Any, default: str = "0") -> Decimal:
    try:
        if value is None or value == "":
            return Decimal(default)
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(default)


@dataclass(frozen=True)
class KalshiMarket:
    ticker: str
    event_ticker: str
    title: str
    subtitle: str
    rules_primary: str
    rules_secondary: str
    url: str
    yes_ask: Decimal
    no_ask: Decimal
    liquidity: Decimal
    volume: Decimal
    close_time: str | None
    expiration_time: str | None

    @property
    def text(self) -> str:
        return " ".join(
            part
            for part in [
                self.title,
                self.subtitle,
                self.rules_primary,
                self.rules_secondary,
            ]
            if part
        )


class KalshiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def close(self) -> None:
        return None

    async def discover_markets(self) -> list[KalshiMarket]:
        markets: list[KalshiMarket] = []
        cursor = ""
        page_number = 0

        while len(markets) < self.settings.kalshi_market_limit:
            if page_number >= self.settings.kalshi_max_pages:
                break
            page_number += 1
            page_limit = min(1000, self.settings.kalshi_market_limit - len(markets))
            url = f"{self.settings.kalshi_api_base.rstrip('/')}/markets"
            params = {
                "status": "open",
                "limit": page_limit,
                "mve_filter": "exclude",
            }
            if cursor:
                params["cursor"] = cursor

            data = await self._get_json(f"{url}?{urlencode(params)}")
            raw_markets = data.get("markets", []) if isinstance(data, dict) else []
            LOGGER.info(
                "stage=kalshi_page page=%s raw_markets=%s accepted_so_far=%s has_cursor=%s",
                page_number,
                len(raw_markets),
                len(markets),
                bool(data.get("cursor")) if isinstance(data, dict) else False,
            )
            rejected_multileg = 0
            rejected_unpriced = 0
            for raw in raw_markets:
                if not isinstance(raw, dict):
                    continue
                market = self._parse_market(raw)
                if market is not None:
                    markets.append(market)
                    continue
                selected_legs = raw.get("mve_selected_legs")
                if isinstance(selected_legs, list) and len(selected_legs) > 1:
                    rejected_multileg += 1
                elif _decimal(raw.get("yes_ask_dollars") or raw.get("yes_ask")) <= 0:
                    rejected_unpriced += 1
            LOGGER.info(
                "stage=kalshi_page_filter page=%s accepted=%s rejected_multileg=%s rejected_unpriced=%s",
                page_number,
                len(markets),
                rejected_multileg,
                rejected_unpriced,
            )

            next_cursor = str(data.get("cursor") or "") if isinstance(data, dict) else ""
            if not raw_markets or not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor

        return markets

    async def _get_json(self, url: str) -> Any:
        return await __import__("asyncio").to_thread(self._sync_get_json, url)

    def _sync_get_json(self, url: str) -> Any:
        request = Request(url, headers={"User-Agent": "pumpfun-cross-venue-screener/0.1"})
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def _parse_market(self, raw: dict[str, Any]) -> KalshiMarket | None:
        ticker = str(raw.get("ticker") or "")
        if not ticker:
            return None
        title = str(raw.get("title") or "")
        selected_legs = raw.get("mve_selected_legs")
        if not self.settings.kalshi_include_multileg:
            if isinstance(selected_legs, list) and len(selected_legs) > 1:
                return None
            if title.count(",") >= 1 and "yes " in title.lower():
                return None
        yes_ask = _decimal(raw.get("yes_ask_dollars") or raw.get("yes_ask"))
        no_ask = _decimal(raw.get("no_ask_dollars") or raw.get("no_ask"))
        if yes_ask <= 0 or no_ask <= 0:
            return None

        return KalshiMarket(
            ticker=ticker,
            event_ticker=str(raw.get("event_ticker") or ""),
            title=title,
            subtitle=str(raw.get("subtitle") or raw.get("sub_title") or ""),
            rules_primary=str(raw.get("rules_primary") or ""),
            rules_secondary=str(raw.get("rules_secondary") or ""),
            url=f"https://kalshi.com/markets/{ticker}",
            yes_ask=yes_ask,
            no_ask=no_ask,
            liquidity=_decimal(raw.get("liquidity_dollars") or raw.get("liquidity")),
            volume=_decimal(raw.get("volume_24h_fp") or raw.get("volume_fp") or raw.get("volume")),
            close_time=raw.get("close_time"),
            expiration_time=raw.get("expiration_time"),
        )
