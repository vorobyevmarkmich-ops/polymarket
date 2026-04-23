from __future__ import annotations

import asyncio
import logging
import signal
import sys
import time
from contextlib import suppress

from screener.config import load_settings
from screener.detector import OpportunityDetector
from screener.models import Market
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
        self._next_discovery_at = 0.0

    async def run(self) -> None:
        self.storage.init()
        LOGGER.info("Starting Polymarket screener MVP-0")
        LOGGER.info("Telegram enabled: %s", self.settings.telegram_enabled)

        while not self._stop.is_set():
            try:
                await self.scan_once(force_discovery=False)
            except Exception:
                LOGGER.exception("Scan cycle failed")
            await self._sleep_or_stop(self.settings.active_market_scan_interval_seconds)

        await self.close()

    async def scan_once(self, force_discovery: bool = False) -> None:
        now = time.monotonic()
        if force_discovery or not self._markets or now >= self._next_discovery_at:
            self._markets = await self.polymarket.discover_markets()
            self.storage.upsert_markets(self._markets)
            self._next_discovery_at = now + self.settings.market_discovery_interval_seconds
            LOGGER.info("Discovered %s active markets", len(self._markets))

        token_ids: list[str] = []
        for market in self._markets:
            token_ids.extend([market.yes_token_id, market.no_token_id])

        prices = await self.polymarket.fetch_ask_prices(token_ids)
        opportunities = self.detector.detect(self._markets, prices)
        LOGGER.info("Detected %s opportunities", len(opportunities))

        for opportunity in opportunities:
            self.storage.save_opportunity(opportunity)
            if not self.storage.should_alert(
                opportunity,
                cooldown_seconds=self.settings.alert_cooldown_seconds,
            ):
                continue

            await self.telegram.send_opportunity(opportunity)
            self.storage.mark_alert_sent(opportunity)
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
