from __future__ import annotations

import html
import json
import logging
import re
from decimal import Decimal
from typing import TYPE_CHECKING
from urllib.request import Request, urlopen

from screener.config import Settings
from screener.models import Opportunity

if TYPE_CHECKING:
    from screener.cross_venue import CrossVenueOpportunity
    from screener.implications import ImplicationOpportunity

LOGGER = logging.getLogger(__name__)


def _price(value: Decimal) -> str:
    return f"{value:.3f} ({value * Decimal('100'):.1f}%)"


def _pct_bps(value: int) -> str:
    return f"{value / 100:.2f}%"


def _money(value: Decimal) -> str:
    return f"${value:.2f}"


def _ru_match_type(value: str) -> str:
    labels = {
        "exact_equivalent": "одинаковое событие",
        "near_equivalent": "почти одинаковое событие",
        "related_not_same": "связано, но не то же самое",
        "different": "разные события",
    }
    return labels.get(value, value)


def _ru_relation_type(value: str) -> str:
    labels = {
        "strict_implication": "строгая логическая связка",
        "likely_implication": "вероятная связка",
        "equivalent": "эквивалентные события",
        "related_no_implication": "связано, но без логического следствия",
        "inverse_or_conflict": "обратная/конфликтующая связка",
        "different": "разные события",
        "possible_implication": "эвристическая связка",
    }
    return labels.get(value, value)


def _short_reason(reason: str) -> str:
    if reason.startswith("deterministic nested threshold"):
        return "Детерминированная проверка: более жесткий ценовой порог логически подразумевает более мягкий."
    if reason.startswith("deterministic nested rank"):
        return "Детерминированная проверка: более высокий результат в таблице логически подразумевает более широкий top-N."
    confidence = re.search(r"ai confidence=([0-9.]+)", reason)
    cleaned = re.sub(r"^ai confidence=[0-9.]+;\s*", "", reason).strip()
    cleaned = re.sub(r";\s*(risks|differences)=.*$", "", cleaned).strip()
    if cleaned:
        prefix = f"AI-проверка, уверенность {confidence.group(1)}: " if confidence else "AI-проверка: "
        return prefix + cleaned[:500]
    if confidence:
        return f"AI-проверка, уверенность {confidence.group(1)}."
    return reason[:500]


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
                "<b>Сигнал: внутрирыночный арбитраж Polymarket</b>",
                "",
                "<b>Что проверить:</b> можно купить YES и NO дешевле 1.00 с учетом комиссий.",
                f"<b>Рынок:</b> {html.escape(market.question)}",
                "",
                f"<b>YES ask:</b> {_price(opportunity.yes_ask)}",
                f"<b>NO ask:</b> {_price(opportunity.no_ask)}",
                f"<b>Сумма входа:</b> {opportunity.total_cost}",
                f"<b>Чистый спред:</b> {_pct_bps(opportunity.spread_bps)}",
                f"<b>Комиссии:</b> {opportunity.total_fees:.6f} USDC/share",
                f"<b>Оценка размера:</b> {_money(opportunity.estimated_size_usd)}",
                f"<b>Грубая оценка прибыли:</b> {_money(opportunity.spread * opportunity.estimated_size_usd)}",
                f"<b>Ликвидность:</b> {_money(market.liquidity)}",
                "",
                f"<b>Ссылка:</b> {html.escape(market.url)}",
                "",
                "Это сигнал для ручной проверки. Автосделок нет, прибыль не гарантирована.",
            ]
        )

    def format_cross_venue_opportunity(self, opportunity: "CrossVenueOpportunity") -> str:
        candidate = opportunity.candidate
        return "\n".join(
            [
                "<b>Сигнал: арбитраж между площадками</b>",
                "",
                "<b>Идея:</b> одно и то же событие оценено по-разному на Polymarket и Kalshi.",
                "<b>Что сделать после ручной проверки правил:</b>",
                f"1. Купить YES на {html.escape(opportunity.buy_yes_venue)} по {_price(opportunity.buy_yes_price)}",
                f"2. Купить NO на {html.escape(opportunity.buy_no_venue)} по {_price(opportunity.buy_no_price)}",
                "",
                f"<b>Сумма входа:</b> {opportunity.total_cost}",
                f"<b>Комиссии:</b> {opportunity.estimated_fees}",
                f"<b>Буфер на несовпадение правил:</b> {opportunity.mismatch_buffer}",
                f"<b>Чистый edge:</b> {_pct_bps(opportunity.net_edge_bps)}",
                "",
                f"<b>Тип совпадения:</b> {html.escape(_ru_match_type(candidate.match_type))} ({candidate.score:.2f})",
                f"<b>Polymarket:</b> {html.escape(candidate.polymarket.question)}",
                f"<b>Kalshi:</b> {html.escape(candidate.kalshi.title)}",
                f"<b>Почему бот связал рынки:</b> {html.escape(_short_reason(candidate.reason))}",
                "",
                f"<b>Polymarket:</b> {html.escape(candidate.polymarket.url)}",
                f"<b>Kalshi:</b> {html.escape(candidate.kalshi.url)}",
                "",
                "Это сигнал для ручной проверки. Особенно проверь resolution rules, даты и ликвидность. Автосделок нет.",
            ]
        )

    def format_implication_opportunity(self, opportunity: "ImplicationOpportunity") -> str:
        candidate = opportunity.candidate
        return "\n".join(
            [
                "<b>Сигнал: связка внутри Polymarket</b>",
                "",
                "<b>Идея:</b> если первый рынок почти уже YES, то второй рынок тоже должен стать YES, но стоит дешевле.",
                "<b>Что сделать после ручной проверки правил:</b>",
                f"1. Проверить, что YES в первом рынке действительно логически ведет к YES во втором.",
                f"2. Рассмотреть покупку YES во втором рынке по {_price(opportunity.consequence_yes_ask)}.",
                "",
                f"<b>Первый рынок уже оценивается как YES:</b> {_price(opportunity.premise_yes_price)}",
                f"<b>Цена YES во втором рынке:</b> {_price(opportunity.consequence_yes_ask)}",
                f"<b>Буфер на ошибку связки:</b> {opportunity.implication_buffer}",
                f"<b>Комиссии:</b> {opportunity.estimated_fees}",
                f"<b>Чистый edge:</b> {_pct_bps(opportunity.net_edge_bps)}",
                "",
                f"<b>Тип связки:</b> {html.escape(_ru_relation_type(candidate.relation_type))} ({candidate.score:.2f})",
                f"<b>Если YES:</b> {html.escape(candidate.premise.question)}",
                f"<b>То должен быть YES:</b> {html.escape(candidate.consequence.question)}",
                f"<b>Почему бот так решил:</b> {html.escape(_short_reason(candidate.reason))}",
                "",
                f"<b>Первый рынок:</b> {html.escape(candidate.premise.url)}",
                f"<b>Второй рынок:</b> {html.escape(candidate.consequence.url)}",
                "",
                "Это не гарантия прибыли. Перед входом обязательно сверить правила резолва обоих рынков. Автосделок нет.",
            ]
        )
