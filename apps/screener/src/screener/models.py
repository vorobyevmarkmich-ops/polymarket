from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Market:
    id: str
    question: str
    slug: str
    url: str
    yes_token_id: str
    no_token_id: str
    liquidity: Decimal
    volume: Decimal
    accepting_orders: bool
    active: bool
    closed: bool
    updated_at: str | None = None


@dataclass(frozen=True)
class PriceLevel:
    token_id: str
    ask_price: Decimal
    observed_at: datetime


@dataclass(frozen=True)
class Opportunity:
    market: Market
    yes_ask: Decimal
    no_ask: Decimal
    total_cost: Decimal
    spread: Decimal
    estimated_size_usd: Decimal
    detected_at: datetime

    @property
    def spread_bps(self) -> int:
        return int(self.spread * Decimal("10000"))

    @property
    def key(self) -> str:
        return f"{self.market.id}:{self.yes_ask}:{self.no_ask}"
