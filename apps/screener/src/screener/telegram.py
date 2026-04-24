from __future__ import annotations

import html
import json
import logging
from typing import TYPE_CHECKING
from urllib.request import Request, urlopen

from screener.config import Settings
from screener.models import Opportunity

if TYPE_CHECKING:
    from screener.cross_venue import CrossVenueOpportunity
    from screener.implications import ImplicationOpportunity

LOGGER = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def close(self) -> None:
        return None

    async def send_opportunity(self, opportunity: Opportunity) -> None:
        text = self.format_opportunity(opportunity)
        await self.send_text(text)

    async def send_cross_venue_opportunity(self, opportunity: "CrossVenueOpportunity") -> None:
        text = self.format_cross_venue_opportunity(opportunity)
        await self.send_text(text)

    async def send_implication_opportunity(self, opportunity: "ImplicationOpportunity") -> None:
        text = self.format_implication_opportunity(opportunity)
        await self.send_text(text)

    async def send_text(self, text: str) -> None:
        if not self.settings.telegram_enabled:
            LOGGER.info("Telegram disabled. Opportunity:\n%s", text)
            return

        url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.settings.telegram_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": self.settings.telegram_disable_web_page_preview,
        }
        await __import__("asyncio").to_thread(self._sync_post_json, url, payload)

    def _sync_post_json(self, url: str, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            response.read()

    def format_opportunity(self, opportunity: Opportunity) -> str:
        market = opportunity.market
        return "\n".join(
            [
                "<b>New Polymarket opportunity</b>",
                "",
                f"<b>Market:</b> {html.escape(market.question)}",
                f"<b>YES ask:</b> {opportunity.yes_ask}",
                f"<b>NO ask:</b> {opportunity.no_ask}",
                f"<b>Raw total:</b> {opportunity.total_cost}",
                f"<b>Gross spread:</b> {opportunity.gross_spread_bps / 100:.2f}%",
                f"<b>Estimated fees:</b> {opportunity.total_fees:.6f} USDC/share",
                f"<b>Net spread:</b> {opportunity.spread_bps / 100:.2f}%",
                f"<b>Fee rates:</b> YES {opportunity.yes_fee_rate_bps}, NO {opportunity.no_fee_rate_bps}",
                f"<b>Estimated size:</b> ${opportunity.estimated_size_usd}",
                f"<b>Rough profit estimate:</b> ${opportunity.spread * opportunity.estimated_size_usd:.2f}",
                f"<b>Liquidity:</b> ${market.liquidity}",
                "",
                f"<b>URL:</b> {html.escape(market.url)}",
                f"<b>Detected:</b> {opportunity.detected_at.isoformat()}",
                "",
                "Signal only. Not guaranteed profit. No auto-execution.",
            ]
        )

    def format_cross_venue_opportunity(self, opportunity: "CrossVenueOpportunity") -> str:
        candidate = opportunity.candidate
        return "\n".join(
            [
                "<b>New cross-venue opportunity</b>",
                "",
                f"<b>Direction:</b> {html.escape(opportunity.direction)}",
                f"<b>Buy YES:</b> {html.escape(opportunity.buy_yes_venue)} @ {opportunity.buy_yes_price}",
                f"<b>Buy NO:</b> {html.escape(opportunity.buy_no_venue)} @ {opportunity.buy_no_price}",
                f"<b>Total cost:</b> {opportunity.total_cost}",
                f"<b>Estimated fees:</b> {opportunity.estimated_fees}",
                f"<b>Mismatch buffer:</b> {opportunity.mismatch_buffer}",
                f"<b>Net edge:</b> {opportunity.net_edge_bps / 100:.2f}%",
                "",
                f"<b>Match:</b> {html.escape(candidate.match_type)} ({candidate.score:.2f})",
                f"<b>Polymarket:</b> {html.escape(candidate.polymarket.question)}",
                f"<b>Kalshi:</b> {html.escape(candidate.kalshi.title)}",
                f"<b>Reason:</b> {html.escape(candidate.reason[:700])}",
                "",
                f"<b>Polymarket URL:</b> {html.escape(candidate.polymarket.url)}",
                f"<b>Kalshi URL:</b> {html.escape(candidate.kalshi.url)}",
                "",
                "Signal only. Not guaranteed profit. No auto-execution.",
            ]
        )

    def format_implication_opportunity(self, opportunity: "ImplicationOpportunity") -> str:
        candidate = opportunity.candidate
        return "\n".join(
            [
                "<b>New Polymarket implication opportunity</b>",
                "",
                f"<b>Premise YES:</b> {opportunity.premise_yes_price}",
                f"<b>Consequence YES ask:</b> {opportunity.consequence_yes_ask}",
                f"<b>Estimated fees:</b> {opportunity.estimated_fees}",
                f"<b>Implication buffer:</b> {opportunity.implication_buffer}",
                f"<b>Net edge:</b> {opportunity.net_edge_bps / 100:.2f}%",
                "",
                f"<b>Relation:</b> {html.escape(candidate.relation_type)} ({candidate.score:.2f})",
                f"<b>If YES:</b> {html.escape(candidate.premise.question)}",
                f"<b>Then YES:</b> {html.escape(candidate.consequence.question)}",
                f"<b>Reason:</b> {html.escape(candidate.reason[:700])}",
                "",
                f"<b>Premise URL:</b> {html.escape(candidate.premise.url)}",
                f"<b>Consequence URL:</b> {html.escape(candidate.consequence.url)}",
                "",
                "Signal only. Requires manual resolution-rule review. No auto-execution.",
            ]
        )
