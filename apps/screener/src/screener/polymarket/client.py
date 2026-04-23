from __future__ import annotations

import json
import logging
from datetime import timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from screener.config import Settings
from screener.models import Market, PriceLevel, utc_now

LOGGER = logging.getLogger(__name__)


def _decimal(value: Any, default: str = "0") -> Decimal:
    try:
        if value is None or value == "":
            return Decimal(default)
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        loaded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return loaded if isinstance(loaded, list) else []


class PolymarketClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._fee_rate_cache: dict[str, int] = {}

    async def close(self) -> None:
        return None

    async def discover_markets(self) -> list[Market]:
        markets: list[Market] = []
        offset = 0
        limit = self.settings.gamma_page_limit

        while len(markets) < self.settings.max_markets_per_discovery:
            page = await self._fetch_markets_page(limit=limit, offset=offset)
            if not page:
                break

            for raw in page:
                market = self._parse_market(raw)
                if market is not None:
                    markets.append(market)
                    if len(markets) >= self.settings.max_markets_per_discovery:
                        break

            if len(page) < limit:
                break
            offset += limit

        return markets

    async def fetch_ask_prices(self, token_ids: list[str]) -> dict[str, PriceLevel]:
        unique_token_ids = list(dict.fromkeys(token_ids))
        prices: dict[str, PriceLevel] = {}

        for start in range(0, len(unique_token_ids), self.settings.clob_price_batch_size):
            batch = unique_token_ids[start : start + self.settings.clob_price_batch_size]
            # Polymarket CLOB /prices uses SELL to return the ask side from the
            # perspective of buying outcome tokens.
            payload = [{"token_id": token_id, "side": "SELL"} for token_id in batch]
            url = f"{self.settings.polymarket_clob_api_base.rstrip('/')}/prices"
            data = await self._post_json(url, payload)
            observed_at = utc_now()
            for token_id, sides in data.items():
                if not isinstance(sides, dict):
                    continue
                value = sides.get("SELL")
                if value is None:
                    continue
                prices[token_id] = PriceLevel(
                    token_id=token_id,
                    ask_price=_decimal(value),
                    observed_at=observed_at,
                )

        return prices

    async def fetch_fee_rates(self, token_ids: list[str]) -> dict[str, int]:
        unique_token_ids = list(dict.fromkeys(token_ids))
        rates: dict[str, int] = {}

        for token_id in unique_token_ids:
            if token_id not in self._fee_rate_cache:
                self._fee_rate_cache[token_id] = await self._fetch_fee_rate(token_id)
            rates[token_id] = self._fee_rate_cache[token_id]

        return rates

    async def _fetch_fee_rate(self, token_id: str) -> int:
        url = f"{self.settings.polymarket_clob_api_base.rstrip('/')}/fee-rate"
        try:
            data = await self._get_json(f"{url}?{urlencode({'token_id': token_id})}")
        except Exception:
            LOGGER.exception("Failed to fetch fee rate for token_id=%s", token_id)
            return 0
        if not isinstance(data, dict):
            return 0
        return int(_decimal(data.get("base_fee")))

    async def _fetch_markets_page(self, limit: int, offset: int) -> list[dict[str, Any]]:
        url = f"{self.settings.polymarket_gamma_api_base.rstrip('/')}/markets"
        params = {
            "active": "true",
            "closed": "false",
            "limit": limit,
            "offset": offset,
        }
        data = await self._get_json(f"{url}?{urlencode(params)}")
        if isinstance(data, list):
            return data
        LOGGER.warning("Unexpected Gamma markets response type: %s", type(data).__name__)
        return []

    async def _get_json(self, url: str) -> Any:
        return await __import__("asyncio").to_thread(self._sync_get_json, url)

    async def _post_json(self, url: str, payload: Any) -> Any:
        return await __import__("asyncio").to_thread(self._sync_post_json, url, payload)

    def _sync_get_json(self, url: str) -> Any:
        request = Request(url, headers={"User-Agent": "pumpfun-screener/0.1"})
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def _sync_post_json(self, url: str, payload: Any) -> Any:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "pumpfun-screener/0.1",
            },
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def _parse_market(self, raw: dict[str, Any]) -> Market | None:
        if not raw.get("enableOrderBook"):
            return None
        if not raw.get("acceptingOrders"):
            return None
        if raw.get("closed") or not raw.get("active"):
            return None

        outcomes = [str(item).lower() for item in _json_list(raw.get("outcomes"))]
        token_ids = [str(item) for item in _json_list(raw.get("clobTokenIds"))]
        if len(outcomes) != len(token_ids) or len(token_ids) < 2:
            return None

        try:
            yes_index = outcomes.index("yes")
            no_index = outcomes.index("no")
        except ValueError:
            return None

        market_id = str(raw.get("id") or raw.get("conditionId") or "")
        slug = str(raw.get("slug") or market_id)
        if not market_id or not slug:
            return None

        return Market(
            id=market_id,
            question=str(raw.get("question") or slug),
            slug=slug,
            url=f"https://polymarket.com/event/{slug}",
            yes_token_id=token_ids[yes_index],
            no_token_id=token_ids[no_index],
            liquidity=_decimal(raw.get("liquidityNum") or raw.get("liquidity")),
            volume=_decimal(raw.get("volumeNum") or raw.get("volume")),
            fees_enabled=bool(raw.get("feesEnabled")),
            fee_type=raw.get("feeType"),
            accepting_orders=bool(raw.get("acceptingOrders")),
            active=bool(raw.get("active")),
            closed=bool(raw.get("closed")),
            updated_at=raw.get("updatedAt"),
        )
