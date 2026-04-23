from __future__ import annotations

import html
import json
import logging
from urllib.request import Request, urlopen

from screener.config import Settings
from screener.models import Opportunity

LOGGER = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def close(self) -> None:
        return None

    async def send_opportunity(self, opportunity: Opportunity) -> None:
        text = self.format_opportunity(opportunity)
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
        is_positive = opportunity.spread > 0
        title = (
            "New Polymarket opportunity"
            if is_positive
            else "Diagnostic near-miss signal"
        )
        note = (
            "Signal only. Not guaranteed profit. No auto-execution."
            if is_positive
            else "Diagnostic only: current spread is not profitable. No auto-execution."
        )
        return "\n".join(
            [
                f"<b>{title}</b>",
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
                note,
            ]
        )
