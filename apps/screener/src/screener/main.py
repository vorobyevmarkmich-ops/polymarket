from __future__ import annotations

import asyncio
import logging
import signal
import sys
import time
from contextlib import suppress
from decimal import Decimal

from screener.config import load_settings
from screener.cross_venue import CrossVenueDetector, SemanticMatcher, _domain
from screener.detector import OpportunityDetector
from screener.implications import ImplicationDetector, ImplicationMatcher
from screener.kalshi import KalshiClient
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
            stream=sys.stdout,
            force=True,
        )
        self.polymarket = PolymarketClient(self.settings)
        self.detector = OpportunityDetector(self.settings)
        self.implication_matcher = ImplicationMatcher(self.settings)
        self.implication_detector = ImplicationDetector(self.settings)
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
        LOGGER.info(
            "Implication scanner enabled via --implications: max_markets=%s max_candidates=%s min_anchor_yes_bps=%s min_edge_bps=%s buffer_bps=%s openai_matcher=%s",
            self.settings.implication_max_markets,
            self.settings.implication_max_candidates,
            self.settings.implication_min_anchor_yes_bps,
            self.settings.implication_min_edge_bps,
            self.settings.implication_buffer_bps,
            bool(self.settings.use_openai_matcher and self.settings.openai_api_key),
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
        implication_opportunities = await self._scan_implications(prices) if "--implications" in sys.argv else []
        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        LOGGER.info(
            "Scan cycle #%s markets=%s tokens=%s prices=%s opportunities=%s implication_opportunities=%s discovery=%s elapsed_ms=%s",
            self._cycle_count,
            len(self._markets),
            len(token_ids),
            len(prices),
            len(opportunities),
            len(implication_opportunities),
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

    async def _scan_implications(self, prices: dict[str, PriceLevel]) -> list:
        markets = sorted(
            self._markets,
            key=lambda market: (market.volume, market.liquidity),
            reverse=True,
        )[: self.settings.implication_max_markets]
        LOGGER.info("stage=implication_matching_start markets=%s", len(markets))
        candidates = self.implication_matcher.find_candidates(markets, prices)
        LOGGER.info("stage=implication_matching_done candidates=%s", len(candidates))
        self._log_implication_candidates(candidates, prices)
        opportunities = self.implication_detector.detect(candidates, prices)
        LOGGER.info("stage=implication_detection_done opportunities=%s", len(opportunities))
        for opportunity in opportunities[: self.settings.max_alerts_per_cycle]:
            self.storage.save_implication_opportunity(opportunity)
            LOGGER.info(
                "stage=implication_opportunity net_edge_bps=%s anchor_yes=%s consequence_yes=%s relation=%s score=%.3f premise=%s consequence=%s reason=%s",
                opportunity.net_edge_bps,
                opportunity.premise_yes_price,
                opportunity.consequence_yes_ask,
                opportunity.candidate.relation_type,
                opportunity.candidate.score,
                opportunity.candidate.premise.question[:140],
                opportunity.candidate.consequence.question[:140],
                opportunity.candidate.reason[:300],
            )
            if time.monotonic() < self._next_alert_at:
                continue
            alert_market_id = (
                f"implication:{opportunity.candidate.premise.id}:"
                f"{opportunity.candidate.consequence.id}"
            )
            if not self.storage.should_alert_key(
                alert_market_id,
                cooldown_seconds=self.settings.alert_cooldown_seconds,
            ):
                continue
            await self.telegram.send_implication_opportunity(opportunity)
            self.storage.mark_alert_key(opportunity.key, alert_market_id)
            self._next_alert_at = time.monotonic() + self.settings.alert_min_interval_seconds
            LOGGER.info(
                "stage=implication_alert_sent net_edge_bps=%s premise_id=%s consequence_id=%s",
                opportunity.net_edge_bps,
                opportunity.candidate.premise.id,
                opportunity.candidate.consequence.id,
            )
        return opportunities

    def _log_implication_candidates(self, candidates: list, prices: dict[str, PriceLevel]) -> None:
        if not self.settings.log_implication_candidates:
            return
        for index, candidate in enumerate(candidates[: self.settings.log_top_candidates_limit], start=1):
            premise_yes = prices.get(candidate.premise.yes_token_id)
            consequence_yes = prices.get(candidate.consequence.yes_token_id)
            LOGGER.info(
                "stage=implication_candidate index=%s score=%.3f relation=%s anchor_yes=%s consequence_yes=%s premise=%s consequence=%s reason=%s",
                index,
                candidate.score,
                candidate.relation_type,
                premise_yes.ask_price if premise_yes else None,
                consequence_yes.ask_price if consequence_yes else None,
                candidate.premise.question[:140],
                candidate.consequence.question[:140],
                candidate.reason[:300],
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


class CrossVenueScreenerApp:
    def __init__(self) -> None:
        self.settings = load_settings()
        logging.basicConfig(
            level=getattr(logging, self.settings.log_level.upper(), logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            stream=sys.stdout,
            force=True,
        )
        self.polymarket = PolymarketClient(self.settings)
        self.kalshi = KalshiClient(self.settings)
        self.matcher = SemanticMatcher(self.settings)
        self.detector = CrossVenueDetector(self.settings)
        self.implication_matcher = ImplicationMatcher(self.settings)
        self.implication_detector = ImplicationDetector(self.settings)
        self.storage = Storage(self.settings.database_url)
        self.telegram = TelegramNotifier(self.settings)
        self._stop = asyncio.Event()
        self._cycle_count = 0
        self._next_alert_at = 0.0

    async def run(self) -> None:
        self.storage.init()
        LOGGER.info("Starting cross-venue screener MVP-0")
        LOGGER.info("Telegram enabled: %s", self.settings.telegram_enabled)
        LOGGER.info(
            "Config venues=Polymarket,Kalshi kalshi_limit=%s poly_limit=%s kalshi_scan_limit=%s max_candidates=%s min_match_score=%s min_net_edge_bps=%s openai_matcher=%s model=%s",
            self.settings.kalshi_market_limit,
            self.settings.cross_venue_max_polymarket_markets,
            self.settings.cross_venue_max_kalshi_markets,
            self.settings.cross_venue_max_candidates,
            self.settings.cross_venue_min_match_score,
            self.settings.cross_venue_min_net_edge_bps,
            bool(self.settings.use_openai_matcher and self.settings.openai_api_key),
            self.settings.openai_model,
        )
        if "--implications" in sys.argv:
            LOGGER.info(
                "Implication scanner enabled: max_markets=%s max_candidates=%s min_anchor_yes_bps=%s min_edge_bps=%s buffer_bps=%s",
                self.settings.implication_max_markets,
                self.settings.implication_max_candidates,
                self.settings.implication_min_anchor_yes_bps,
                self.settings.implication_min_edge_bps,
                self.settings.implication_buffer_bps,
            )
        while not self._stop.is_set():
            try:
                await self.scan_once()
            except Exception:
                LOGGER.exception("Cross-venue scan cycle failed")
            await self._sleep_or_stop(self.settings.active_market_scan_interval_seconds)
        await self.close()

    async def scan_once(self) -> None:
        started_at = time.monotonic()
        self._cycle_count += 1
        LOGGER.info("stage=cycle_start cycle=%s", self._cycle_count)

        LOGGER.info("stage=discovery_start venue=polymarket")
        polymarket_markets = await self.polymarket.discover_markets()
        polymarket_markets = self._select_polymarket_markets(
            polymarket_markets,
            limit=self.settings.cross_venue_max_polymarket_markets,
        )
        LOGGER.info("stage=discovery_done venue=polymarket markets=%s", len(polymarket_markets))
        self._log_polymarket_samples(polymarket_markets)

        LOGGER.info("stage=discovery_start venue=kalshi")
        kalshi_markets = await self.kalshi.discover_markets()
        kalshi_markets = sorted(
            kalshi_markets,
            key=lambda market: (market.volume, market.liquidity),
            reverse=True,
        )[: self.settings.cross_venue_max_kalshi_markets]
        LOGGER.info("stage=discovery_done venue=kalshi markets=%s", len(kalshi_markets))
        self._log_kalshi_samples(kalshi_markets)

        self.storage.upsert_markets(polymarket_markets)

        LOGGER.info("stage=matching_start poly_markets=%s kalshi_markets=%s", len(polymarket_markets), len(kalshi_markets))
        candidates = self.matcher.find_candidates(polymarket_markets, kalshi_markets)
        LOGGER.info("stage=matching_done candidates=%s", len(candidates))
        self._log_match_candidates(candidates)

        token_ids: list[str] = []
        for candidate in candidates:
            token_ids.extend([candidate.polymarket.yes_token_id, candidate.polymarket.no_token_id])
        if "--implications" in sys.argv:
            for market in polymarket_markets[: self.settings.implication_max_markets]:
                token_ids.extend([market.yes_token_id, market.no_token_id])
        LOGGER.info("stage=pricing_start polymarket_tokens=%s", len(set(token_ids)))
        prices = await self.polymarket.fetch_ask_prices(token_ids)
        LOGGER.info("stage=pricing_done polymarket_prices=%s kalshi_prices=%s", len(prices), len(kalshi_markets) * 2)

        LOGGER.info("stage=opportunity_detection_start candidates=%s", len(candidates))
        all_direction_count = len(candidates) * 2
        opportunities = self.detector.detect(candidates, prices)
        near_misses = self.detector.near_misses(candidates, prices) if self.settings.near_miss_enabled else []
        self.storage.save_cross_venue_near_misses(near_misses)
        LOGGER.info(
            "stage=opportunity_detection_done candidate_directions=%s opportunities=%s near_misses=%s",
            all_direction_count,
            len(opportunities),
            len(near_misses),
        )
        self._log_opportunity_rejections(candidates, prices)

        for opportunity in opportunities[: self.settings.max_alerts_per_cycle]:
            self.storage.save_cross_venue_opportunity(opportunity)
            LOGGER.info(
                "stage=opportunity direction=%s net_edge_bps=%s total=%s yes=%s:%s no=%s:%s match=%s score=%.3f poly=%s kalshi=%s reason=%s",
                opportunity.direction,
                opportunity.net_edge_bps,
                opportunity.total_cost,
                opportunity.buy_yes_venue,
                opportunity.buy_yes_price,
                opportunity.buy_no_venue,
                opportunity.buy_no_price,
                opportunity.candidate.match_type,
                opportunity.candidate.score,
                opportunity.candidate.polymarket.question[:140],
                opportunity.candidate.kalshi.title[:140],
                opportunity.candidate.reason[:300],
            )
            if time.monotonic() < self._next_alert_at:
                continue
            alert_market_id = (
                f"cross-venue:{opportunity.candidate.polymarket.id}:"
                f"{opportunity.candidate.kalshi.ticker}:{opportunity.direction}"
            )
            if not self.storage.should_alert_key(
                alert_market_id,
                cooldown_seconds=self.settings.alert_cooldown_seconds,
            ):
                continue
            await self.telegram.send_cross_venue_opportunity(opportunity)
            self.storage.mark_alert_key(opportunity.key, alert_market_id)
            self._next_alert_at = time.monotonic() + self.settings.alert_min_interval_seconds
            LOGGER.info(
                "stage=cross_venue_alert_sent direction=%s net_edge_bps=%s poly_id=%s kalshi=%s",
                opportunity.direction,
                opportunity.net_edge_bps,
                opportunity.candidate.polymarket.id,
                opportunity.candidate.kalshi.ticker,
            )

        implication_opportunities = (
            await self._scan_implications(polymarket_markets, prices)
            if "--implications" in sys.argv
            else []
        )

        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        LOGGER.info(
            "stage=cycle_done cycle=%s poly_markets=%s kalshi_markets=%s candidates=%s opportunities=%s implication_opportunities=%s elapsed_ms=%s",
            self._cycle_count,
            len(polymarket_markets),
            len(kalshi_markets),
            len(candidates),
            len(opportunities),
            len(implication_opportunities),
            elapsed_ms,
        )

    async def _scan_implications(
        self,
        polymarket_markets: list[Market],
        prices: dict[str, PriceLevel],
    ) -> list:
        markets = polymarket_markets[: self.settings.implication_max_markets]
        LOGGER.info("stage=implication_matching_start markets=%s", len(markets))
        candidates = self.implication_matcher.find_candidates(markets, prices)
        LOGGER.info("stage=implication_matching_done candidates=%s", len(candidates))
        self._log_implication_candidates(candidates, prices)
        opportunities = self.implication_detector.detect(candidates, prices)
        near_misses = (
            self.implication_detector.near_misses(candidates, prices)
            if self.settings.near_miss_enabled
            else []
        )
        self.storage.save_implication_near_misses(near_misses)
        LOGGER.info(
            "stage=implication_detection_done opportunities=%s near_misses=%s",
            len(opportunities),
            len(near_misses),
        )
        for opportunity in opportunities[: self.settings.max_alerts_per_cycle]:
            self.storage.save_implication_opportunity(opportunity)
            LOGGER.info(
                "stage=implication_opportunity net_edge_bps=%s anchor_yes=%s consequence_yes=%s relation=%s score=%.3f premise=%s consequence=%s reason=%s",
                opportunity.net_edge_bps,
                opportunity.premise_yes_price,
                opportunity.consequence_yes_ask,
                opportunity.candidate.relation_type,
                opportunity.candidate.score,
                opportunity.candidate.premise.question[:140],
                opportunity.candidate.consequence.question[:140],
                opportunity.candidate.reason[:300],
            )
            if time.monotonic() < self._next_alert_at:
                continue
            alert_market_id = (
                f"implication:{opportunity.candidate.premise.id}:"
                f"{opportunity.candidate.consequence.id}"
            )
            if not self.storage.should_alert_key(
                alert_market_id,
                cooldown_seconds=self.settings.alert_cooldown_seconds,
            ):
                continue
            await self.telegram.send_implication_opportunity(opportunity)
            self.storage.mark_alert_key(opportunity.key, alert_market_id)
            self._next_alert_at = time.monotonic() + self.settings.alert_min_interval_seconds
            LOGGER.info(
                "stage=implication_alert_sent net_edge_bps=%s premise_id=%s consequence_id=%s",
                opportunity.net_edge_bps,
                opportunity.candidate.premise.id,
                opportunity.candidate.consequence.id,
            )
        return opportunities

    def _log_implication_candidates(self, candidates: list, prices: dict[str, PriceLevel]) -> None:
        if not self.settings.log_implication_candidates:
            return
        for index, candidate in enumerate(candidates[: self.settings.log_top_candidates_limit], start=1):
            premise_yes = prices.get(candidate.premise.yes_token_id)
            consequence_yes = prices.get(candidate.consequence.yes_token_id)
            LOGGER.info(
                "stage=implication_candidate index=%s score=%.3f relation=%s anchor_yes=%s consequence_yes=%s premise=%s consequence=%s reason=%s",
                index,
                candidate.score,
                candidate.relation_type,
                premise_yes.ask_price if premise_yes else None,
                consequence_yes.ask_price if consequence_yes else None,
                candidate.premise.question[:140],
                candidate.consequence.question[:140],
                candidate.reason[:300],
            )

    async def close(self) -> None:
        await self.polymarket.close()
        await self.kalshi.close()
        await self.telegram.close()
        self.storage.close()

    def request_stop(self) -> None:
        self._stop.set()

    async def _sleep_or_stop(self, seconds: float) -> None:
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(self._stop.wait(), timeout=seconds)

    def _log_polymarket_samples(self, markets: list[Market]) -> None:
        for index, market in enumerate(markets[: self.settings.log_market_sample_size], start=1):
            LOGGER.info(
                "stage=market_sample venue=polymarket index=%s id=%s liquidity=%s volume=%s question=%s",
                index,
                market.id,
                market.liquidity,
                market.volume,
                market.question[:180],
            )

    def _select_polymarket_markets(self, markets: list[Market], limit: int) -> list[Market]:
        selected: dict[str, Market] = {}

        def add(items: list[Market], count: int) -> None:
            for market in items:
                if len(selected) >= limit:
                    break
                if len(selected) >= count and count < limit:
                    break
                selected.setdefault(market.id, market)

        top_by_volume = sorted(markets, key=lambda market: (market.volume, market.liquidity), reverse=True)
        add(top_by_volume, max(1, limit // 3))

        sports = [market for market in markets if _domain(market.question) == "sports"]
        sports = sorted(sports, key=lambda market: (market.volume, market.liquidity), reverse=True)
        target = min(limit, len(selected) + max(1, limit // 3))
        for market in sports:
            if len(selected) >= target:
                break
            selected.setdefault(market.id, market)

        for market in markets:
            if len(selected) >= limit:
                break
            selected.setdefault(market.id, market)

        return list(selected.values())[:limit]

    def _log_kalshi_samples(self, markets: list) -> None:
        for index, market in enumerate(markets[: self.settings.log_market_sample_size], start=1):
            LOGGER.info(
                "stage=market_sample venue=kalshi index=%s ticker=%s yes_ask=%s no_ask=%s liquidity=%s volume=%s title=%s",
                index,
                market.ticker,
                market.yes_ask,
                market.no_ask,
                market.liquidity,
                market.volume,
                market.title[:180],
            )

    def _log_match_candidates(self, candidates: list) -> None:
        if not self.settings.log_cross_venue_candidates:
            return
        for index, candidate in enumerate(candidates[: self.settings.log_top_candidates_limit], start=1):
            LOGGER.info(
                "stage=match_candidate index=%s score=%.3f match=%s poly_id=%s kalshi=%s poly=%s kalshi_title=%s reason=%s",
                index,
                candidate.score,
                candidate.match_type,
                candidate.polymarket.id,
                candidate.kalshi.ticker,
                candidate.polymarket.question[:140],
                candidate.kalshi.title[:140],
                candidate.reason[:300],
            )

    def _log_opportunity_rejections(self, candidates: list, prices: dict[str, PriceLevel]) -> None:
        if not self.settings.log_cross_venue_rejections:
            return
        preview_count = 0
        for candidate in candidates:
            if preview_count >= self.settings.log_top_candidates_limit:
                break
            poly_yes = prices.get(candidate.polymarket.yes_token_id)
            poly_no = prices.get(candidate.polymarket.no_token_id)
            if poly_yes is None or poly_no is None:
                continue
            preview_count += 1
            for direction, yes_price, no_price in [
                ("YES_KALSHI_NO_POLYMARKET", candidate.kalshi.yes_ask, poly_no.ask_price),
                ("YES_POLYMARKET_NO_KALSHI", poly_yes.ask_price, candidate.kalshi.no_ask),
            ]:
                total = yes_price + no_price
                buffer_bps = (
                    self.settings.exact_match_mismatch_buffer_bps
                    if candidate.match_type == "exact_equivalent"
                    else self.settings.near_match_mismatch_buffer_bps
                )
                buffer = Decimal(buffer_bps) / Decimal("10000")
                edge = Decimal("1") - total - buffer
                LOGGER.info(
                    "stage=opportunity_check direction=%s net_edge_bps=%s total=%s buffer=%s match=%s score=%.3f poly=%s kalshi=%s",
                    direction,
                    int(edge * Decimal("10000")),
                    total,
                    buffer,
                    candidate.match_type,
                    candidate.score,
                    candidate.polymarket.question[:120],
                    candidate.kalshi.title[:120],
                )

async def async_main() -> None:
    app = CrossVenueScreenerApp() if "--cross-venue" in sys.argv else ScreenerApp()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, app.request_stop)
    if "--once" in sys.argv:
        app.storage.init()
        if isinstance(app, CrossVenueScreenerApp):
            await app.scan_once()
        else:
            await app.scan_once(force_discovery=True)
        await app.close()
        return

    await app.run()


def run() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    run()
