from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from screener.config import Settings
from screener.models import Market, Opportunity, PriceLevel, utc_now


class OpportunityDetector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def detect(
        self,
        markets: list[Market],
        prices: dict[str, PriceLevel],
    ) -> list[Opportunity]:
        opportunities: list[Opportunity] = []
        now = utc_now()
        max_age = timedelta(seconds=self.settings.max_price_staleness_seconds)

        for market in markets:
            yes = prices.get(market.yes_token_id)
            no = prices.get(market.no_token_id)
            if yes is None or no is None:
                continue
            if now - yes.observed_at > max_age or now - no.observed_at > max_age:
                continue

            total_cost = yes.ask_price + no.ask_price
            spread = Decimal("1") - total_cost
            estimated_size_usd = market.liquidity

            if spread < Decimal(str(self.settings.min_spread)):
                continue
            if estimated_size_usd < Decimal(str(self.settings.min_size_usd)):
                continue

            opportunities.append(
                Opportunity(
                    market=market,
                    yes_ask=yes.ask_price,
                    no_ask=no.ask_price,
                    total_cost=total_cost,
                    spread=spread,
                    estimated_size_usd=estimated_size_usd,
                    detected_at=now,
                )
            )

        return sorted(opportunities, key=lambda item: item.spread, reverse=True)
