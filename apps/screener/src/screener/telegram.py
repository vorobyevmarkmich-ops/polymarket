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
        return "\n".join(
            [
                "<b>New Polymarket opportunity</b>",
                "",
                f"<b>Market:</b> {html.escape(market.question)}",
                f"<b>YES ask:</b> {opportunity.yes_ask}",
                f"<b>NO ask:</b> {opportunity.no_ask}",
                f"<b>Total:</b> {opportunity.total_cost}",
                f"<b>Spread:</b> {opportunity.spread_bps / 100:.2f}%",
                f"<b>Estimated size:</b> ${opportunity.estimated_size_usd}",
                f"<b>Liquidity:</b> ${market.liquidity}",
                "",
                f"<b>URL:</b> {html.escape(market.url)}",
                f"<b>Detected:</b> {opportunity.detected_at.isoformat()}",
                "",
                "Signal only. Not guaranteed profit. No auto-execution.",
            ]
        )
