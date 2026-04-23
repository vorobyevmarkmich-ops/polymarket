from __future__ import annotations

import asyncio
import logging
import signal
import sys
import time
from contextlib import suppress
from decimal import Decimal

from screener.config import load_settings
from screener.detector import OpportunityDetector
from screener.models import Market, PriceLevel
from screener.polymarket.client import PolymarketClient
from screener.storage import Storage
from screener.telegram import TelegramNotifier

LOGGER = logging.getLogger(__name__)


class ScreenerApp:
    def __init__(self) -> None:
        self.settings = load_settings()
        logging.basicConfig(
            level=getattr(logging, self.settings.log_level.upper(), logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        self.polymarket = PolymarketClient(self.settings)
        self.detector = OpportunityDetector(self.settings)
        self.storage = Storage(self.settings.database_url)
        self.telegram = TelegramNotifier(self.settings)
        self._stop = asyncio.Event()
        self._markets: list[Market] = []
        self._fee_rates: dict[str, int] = {}
        self._next_discovery_at = 0.0
        self._cycle_count = 0
        self._next_alert_at = 0.0

    async def run(self) -> None:
        self.storage.init()
        LOGGER.info("Starting Polymarket screener MVP-0")
        LOGGER.info("Telegram enabled: %s", self.settings.telegram_enabled)
        LOGGER.info(
            "Config scan_interval=%ss discovery_interval=%ss min_spread_bps=%s min_size_usd=%s max_markets=%s batch_size=%s max_alerts_per_cycle=%s alert_min_interval=%ss log_top_candidates=%s",
            self.settings.active_market_scan_interval_seconds,
            self.settings.market_discovery_interval_seconds,
            self.settings.min_spread_bps,
            self.settings.min_size_usd,
            self.settings.max_markets_per_discovery,
            self.settings.clob_price_batch_size,
            self.settings.max_alerts_per_cycle,
            self.settings.alert_min_interval_seconds,
            self.settings.log_top_candidates,
        )

        while not self._stop.is_set():
            try:
                await self.scan_once(force_discovery=False)
            except Exception:
                LOGGER.exception("Scan cycle failed")
            await self._sleep_or_stop(self.settings.active_market_scan_interval_seconds)

        await self.close()

    async def scan_once(self, force_discovery: bool = False) -> None:
        started_at = time.monotonic()
        self._cycle_count += 1
        discovery_ran = False

        if force_discovery or not self._markets or started_at >= self._next_discovery_at:
            self._markets = await self.polymarket.discover_markets()
            fee_token_ids = []
            for market in self._markets:
                if market.fees_enabled:
                    fee_token_ids.extend([market.yes_token_id, market.no_token_id])
            self._fee_rates = await self.polymarket.fetch_fee_rates(fee_token_ids)
            self.storage.upsert_markets(self._markets)
            self._next_discovery_at = started_at + self.settings.market_discovery_interval_seconds
            discovery_ran = True
            LOGGER.info(
                "Discovered %s active markets, fee_enabled=%s, fee_rates=%s",
                len(self._markets),
                sum(1 for market in self._markets if market.fees_enabled),
                len(self._fee_rates),
            )
            self._log_market_samples()

        token_ids: list[str] = []
        for market in self._markets:
            token_ids.extend([market.yes_token_id, market.no_token_id])

        prices = await self.polymarket.fetch_ask_prices(token_ids)
        opportunities = self.detector.detect(self._markets, prices, self._fee_rates)
        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        LOGGER.info(
            "Scan cycle #%s markets=%s tokens=%s prices=%s opportunities=%s discovery=%s elapsed_ms=%s",
            self._cycle_count,
            len(self._markets),
            len(token_ids),
            len(prices),
            len(opportunities),
            discovery_ran,
            elapsed_ms,
        )
        self._log_top_candidates(prices)

        alerts_sent = 0
        for opportunity in opportunities:
            self.storage.save_opportunity(opportunity)
            if alerts_sent >= self.settings.max_alerts_per_cycle:
                continue
            if time.monotonic() < self._next_alert_at:
                continue
            if not self.storage.should_alert(
                opportunity,
                cooldown_seconds=self.settings.alert_cooldown_seconds,
            ):
                continue

            await self.telegram.send_opportunity(opportunity)
            self.storage.mark_alert_sent(opportunity)
            alerts_sent += 1
            self._next_alert_at = time.monotonic() + self.settings.alert_min_interval_seconds
            LOGGER.info(
                "Alert sent for market=%s spread_bps=%s",
                opportunity.market.id,
                opportunity.spread_bps,
            )

    async def close(self) -> None:
        await self.polymarket.close()
        await self.telegram.close()
        self.storage.close()

    def request_stop(self) -> None:
        self._stop.set()

    async def _sleep_or_stop(self, seconds: float) -> None:
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(self._stop.wait(), timeout=seconds)

    def _log_market_samples(self) -> None:
        if not self.settings.log_market_samples or self.settings.log_market_sample_size <= 0:
            return

        sample = self._markets[: self.settings.log_market_sample_size]
        for index, market in enumerate(sample, start=1):
            LOGGER.info(
                "Market sample #%s id=%s liquidity=%s question=%s",
                index,
                market.id,
                market.liquidity,
                market.question[:140],
            )

    def _log_top_candidates(self, prices: dict[str, PriceLevel]) -> None:
        if not self.settings.log_top_candidates or self.settings.log_top_candidates_limit <= 0:
            return
        if self._cycle_count % self.settings.log_top_candidates_every_cycles != 0:
            return

        candidates: list[tuple[Decimal, Decimal, Market, PriceLevel, PriceLevel]] = []
        for market in self._markets:
            yes = prices.get(market.yes_token_id)
            no = prices.get(market.no_token_id)
            if yes is None or no is None:
                continue

            total_cost = yes.ask_price + no.ask_price
            gross_spread = Decimal("1") - total_cost
            yes_fee_rate_bps = self._fee_rates.get(market.yes_token_id, 0) if market.fees_enabled else 0
            no_fee_rate_bps = self._fee_rates.get(market.no_token_id, 0) if market.fees_enabled else 0
            spread = gross_spread - self._fee_for_price(yes.ask_price, yes_fee_rate_bps)
            spread -= self._fee_for_price(no.ask_price, no_fee_rate_bps)
            candidates.append((total_cost, spread, market, yes, no))

        candidates.sort(key=lambda item: item[1], reverse=True)
        for index, (total_cost, spread, market, yes, no) in enumerate(
            candidates[: self.settings.log_top_candidates_limit],
            start=1,
        ):
            LOGGER.info(
                "Closest candidate #%s total=%s net_spread_bps=%s yes_ask=%s no_ask=%s fees_enabled=%s liquidity=%s market=%s question=%s",
                index,
                total_cost,
                spread * Decimal("10000"),
                yes.ask_price,
                no.ask_price,
                market.fees_enabled,
                market.liquidity,
                market.id,
                market.question[:140],
            )

    @staticmethod
    def _fee_for_price(price: Decimal, fee_rate_bps: int) -> Decimal:
        fee_rate = Decimal(fee_rate_bps) / Decimal("1000")
        return fee_rate * price * (Decimal("1") - price)


async def async_main() -> None:
    app = ScreenerApp()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, app.request_stop)
    if "--once" in sys.argv:
        app.storage.init()
        await app.scan_once(force_discovery=True)
        await app.close()
        return

    await app.run()


def run() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    run()
