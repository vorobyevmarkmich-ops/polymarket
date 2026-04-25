from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.request import Request, urlopen

from screener.config import Settings
from screener.kalshi import KalshiMarket
from screener.models import Market, PriceLevel, utc_now

LOGGER = logging.getLogger(__name__)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "before",
    "by",
    "during",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "will",
    "within",
    "with",
    "yes",
    "no",
    "above",
    "after",
    "below",
    "between",
    "finish",
    "game",
    "happen",
    "market",
    "match",
    "more",
    "over",
    "picked",
    "round",
    "season",
    "standings",
    "than",
    "under",
    "win",
    "wins",
}

GENERIC_MATCH_TERMS = {
    "2024",
    "2025",
    "2026",
    "2027",
    "2028",
    "2029",
    "2030",
    "1st",
    "2nd",
    "3rd",
    "april",
    "election",
    "final",
    "open",
    "presidential",
    "price",
    "rate",
    "rates",
    "relegated",
    "spread",
    "top",
    "united",
    "win",
    "wins",
}

SPORT_TERMS = {
    "basketball",
    "bundesliga",
    "champions",
    "cricket",
    "cs2",
    "epl",
    "esports",
    "fifa",
    "football",
    "game",
    "league",
    "liga",
    "match",
    "mlb",
    "nba",
    "nfl",
    "nhl",
    "overwatch",
    "premier",
    "serie",
    "soccer",
    "tennis",
    "tournament",
    "world cup",
}

ECON_TERMS = {
    "business climate",
    "cpi",
    "fed",
    "gdp",
    "ifo",
    "inflation",
    "interest",
    "payrolls",
    "rate cuts",
    "rates",
    "unemployment",
}

CRYPTO_TERMS = {
    "bitcoin",
    "btc",
    "crypto",
    "ethereum",
    "eth",
    "fdv",
    "launch",
    "market cap",
    "token",
}

POLITICS_TERMS = {
    "congress",
    "democratic",
    "election",
    "house",
    "midterm",
    "nomination",
    "president",
    "presidential",
    "republican",
    "senate",
}

ENTERTAINMENT_TERMS = {
    "album",
    "box office",
    "eurovision",
    "grammy",
    "movie",
    "oscars",
    "song",
}


@dataclass(frozen=True)
class EventCandidate:
    polymarket: Market
    kalshi: KalshiMarket
    score: float
    match_type: str
    reason: str


@dataclass(frozen=True)
class CrossVenueOpportunity:
    candidate: EventCandidate
    direction: str
    buy_yes_venue: str
    buy_yes_price: Decimal
    buy_no_venue: str
    buy_no_price: Decimal
    total_cost: Decimal
    estimated_fees: Decimal
    mismatch_buffer: Decimal
    net_edge: Decimal

    @property
    def net_edge_bps(self) -> int:
        return int(self.net_edge * Decimal("10000"))

    @property
    def key(self) -> str:
        return (
            f"cross-venue:{self.candidate.polymarket.id}:{self.candidate.kalshi.ticker}:"
            f"{self.direction}:{self.buy_yes_price}:{self.buy_no_price}"
        )


@dataclass(frozen=True)
class CrossVenueNearMiss:
    candidate: EventCandidate
    direction: str
    buy_yes_venue: str
    buy_yes_price: Decimal
    buy_no_venue: str
    buy_no_price: Decimal
    total_cost: Decimal
    estimated_fees: Decimal
    mismatch_buffer: Decimal
    net_edge: Decimal
    rejection_reason: str

    @property
    def net_edge_bps(self) -> int:
        return int(self.net_edge * Decimal("10000"))


class SemanticMatcher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def find_candidates(
        self,
        polymarket_markets: list[Market],
        kalshi_markets: list[KalshiMarket],
    ) -> list[EventCandidate]:
        candidates: list[EventCandidate] = []
        raw_top: list[tuple[float, Market, KalshiMarket, str]] = []
        for poly in polymarket_markets:
            poly_terms = _terms(poly.question)
            if not poly_terms:
                continue
            for kalshi in kalshi_markets:
                kalshi_terms = _terms(kalshi.text)
                if not kalshi_terms:
                    continue
                score = _jaccard(poly_terms, kalshi_terms)
                shared_terms = poly_terms & kalshi_terms
                if not _compatible_domains(poly.question, kalshi.text):
                    continue
                if not _has_specific_overlap(shared_terms):
                    continue
                if score > 0:
                    shared = ", ".join(sorted(shared_terms)[:12])
                    raw_top.append((score, poly, kalshi, shared))
                if score < self.settings.cross_venue_min_match_score:
                    continue
                match_type = (
                    "exact_equivalent"
                    if score >= self.settings.cross_venue_min_exact_score
                    else "near_equivalent"
                )
                shared = ", ".join(sorted(shared_terms)[:12])
                candidates.append(
                    EventCandidate(
                        polymarket=poly,
                        kalshi=kalshi,
                        score=score,
                        match_type=match_type,
                        reason=f"heuristic token overlap; shared_terms={shared}",
                    )
                )

        raw_top.sort(key=lambda item: item[0], reverse=True)
        for index, (score, poly, kalshi, shared) in enumerate(raw_top[:10], start=1):
            LOGGER.info(
                "stage=match_raw_top index=%s score=%.3f shared_terms=%s poly=%s kalshi=%s",
                index,
                score,
                shared,
                poly.question[:140],
                kalshi.title[:140],
            )

        candidates.sort(key=lambda item: item.score, reverse=True)
        candidates = candidates[: self.settings.cross_venue_max_candidates]
        if self.settings.use_openai_matcher and self.settings.openai_api_key:
            return self._classify_with_openai(candidates)
        return candidates

    def _classify_with_openai(self, candidates: list[EventCandidate]) -> list[EventCandidate]:
        refined: list[EventCandidate] = []
        for candidate in candidates:
            try:
                refined.append(self._classify_one_with_openai(candidate))
            except Exception:
                LOGGER.exception(
                    "ai_match_failed poly_id=%s kalshi_ticker=%s fallback_score=%.3f",
                    candidate.polymarket.id,
                    candidate.kalshi.ticker,
                    candidate.score,
                )
                refined.append(
                    EventCandidate(
                        polymarket=candidate.polymarket,
                        kalshi=candidate.kalshi,
                        score=0.0,
                        match_type="related_not_same",
                        reason="ai classification failed; rejected instead of using heuristic fallback",
                    )
                )
        refined.sort(key=lambda item: item.score, reverse=True)
        return refined

    def _classify_one_with_openai(self, candidate: EventCandidate) -> EventCandidate:
        prompt = {
            "polymarket": {
                "title": candidate.polymarket.question,
                "url": candidate.polymarket.url,
            },
            "kalshi": {
                "title": candidate.kalshi.title,
                "subtitle": candidate.kalshi.subtitle,
                "rules_primary": candidate.kalshi.rules_primary,
                "rules_secondary": candidate.kalshi.rules_secondary,
                "close_time": candidate.kalshi.close_time,
                "expiration_time": candidate.kalshi.expiration_time,
                "url": candidate.kalshi.url,
            },
        }
        body = {
            "model": self.settings.openai_model,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You classify whether two prediction-market contracts represent the same economic event. "
                        "Return only compact JSON with keys match_type, confidence, material_differences, explanation. "
                        "match_type must be exact_equivalent, near_equivalent, related_not_same, or different. "
                        "Write explanation and material_differences in Russian."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=True)},
            ],
            "text": {"format": {"type": "json_object"}},
            "max_output_tokens": 500,
        }
        request = Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = _response_text(data)
        parsed = json.loads(text)
        match_type = str(parsed.get("match_type") or candidate.match_type)
        confidence = _confidence(parsed.get("confidence"), candidate.score)
        material_differences = parsed.get("material_differences") or []
        explanation = str(parsed.get("explanation") or "")
        reason = f"ai confidence={confidence:.2f}; {explanation}; differences={material_differences}"
        return EventCandidate(
            polymarket=candidate.polymarket,
            kalshi=candidate.kalshi,
            score=max(0.0, min(confidence, 1.0)),
            match_type=match_type,
            reason=reason,
        )


class CrossVenueDetector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def detect(
        self,
        candidates: list[EventCandidate],
        polymarket_prices: dict[str, PriceLevel],
    ) -> list[CrossVenueOpportunity]:
        opportunities: list[CrossVenueOpportunity] = []
        for candidate in candidates:
            allowed_match_types = {"exact_equivalent"}
            if self.settings.allow_near_match_opportunities:
                allowed_match_types.add("near_equivalent")
            if candidate.match_type not in allowed_match_types:
                continue
            if not _has_ai_confirmation(candidate):
                LOGGER.info(
                    "stage=match_rejected reason=no_ai_confirmation match=%s score=%.3f poly=%s kalshi=%s candidate_reason=%s",
                    candidate.match_type,
                    candidate.score,
                    candidate.polymarket.question[:120],
                    candidate.kalshi.title[:120],
                    candidate.reason[:180],
                )
                continue
            poly_yes = polymarket_prices.get(candidate.polymarket.yes_token_id)
            poly_no = polymarket_prices.get(candidate.polymarket.no_token_id)
            if poly_yes is None or poly_no is None:
                LOGGER.info(
                    "stage=pricing_skip reason=missing_polymarket_price poly_id=%s kalshi=%s",
                    candidate.polymarket.id,
                    candidate.kalshi.ticker,
                )
                continue
            opportunities.extend(self._directions(candidate, poly_yes.ask_price, poly_no.ask_price))

        opportunities = [
            item
            for item in opportunities
            if item.net_edge_bps >= self.settings.cross_venue_min_net_edge_bps
        ]
        return sorted(opportunities, key=lambda item: item.net_edge, reverse=True)

    def near_misses(
        self,
        candidates: list[EventCandidate],
        polymarket_prices: dict[str, PriceLevel],
    ) -> list[CrossVenueNearMiss]:
        rows: list[CrossVenueNearMiss] = []
        min_edge_bps = self.settings.cross_venue_min_net_edge_bps
        near_edge_bps = self.settings.near_miss_min_edge_bps
        for candidate in candidates:
            if candidate.match_type == "exact_equivalent":
                rejection_reason = ""
            elif candidate.match_type == "near_equivalent":
                rejection_reason = "near_match_not_allowed"
            else:
                continue

            if not _has_ai_confirmation(candidate):
                continue

            poly_yes = polymarket_prices.get(candidate.polymarket.yes_token_id)
            poly_no = polymarket_prices.get(candidate.polymarket.no_token_id)
            if poly_yes is None or poly_no is None:
                continue

            for opportunity in self._directions(candidate, poly_yes.ask_price, poly_no.ask_price):
                reason = rejection_reason
                if opportunity.net_edge_bps < min_edge_bps:
                    reason = "edge_below_threshold" if not reason else f"{reason};edge_below_threshold"
                if not reason or opportunity.net_edge_bps < near_edge_bps:
                    continue
                rows.append(
                    CrossVenueNearMiss(
                        candidate=candidate,
                        direction=opportunity.direction,
                        buy_yes_venue=opportunity.buy_yes_venue,
                        buy_yes_price=opportunity.buy_yes_price,
                        buy_no_venue=opportunity.buy_no_venue,
                        buy_no_price=opportunity.buy_no_price,
                        total_cost=opportunity.total_cost,
                        estimated_fees=opportunity.estimated_fees,
                        mismatch_buffer=opportunity.mismatch_buffer,
                        net_edge=opportunity.net_edge,
                        rejection_reason=reason,
                    )
                )

        rows.sort(key=lambda item: item.net_edge, reverse=True)
        return rows[: self.settings.near_miss_max_per_cycle]

    def _directions(
        self,
        candidate: EventCandidate,
        poly_yes: Decimal,
        poly_no: Decimal,
    ) -> list[CrossVenueOpportunity]:
        kalshi = candidate.kalshi
        rows = [
            ("YES_KALSHI_NO_POLYMARKET", "Kalshi", kalshi.yes_ask, "Polymarket", poly_no),
            ("YES_POLYMARKET_NO_KALSHI", "Polymarket", poly_yes, "Kalshi", kalshi.no_ask),
        ]
        return [
            self._build(candidate, direction, yes_venue, yes_price, no_venue, no_price)
            for direction, yes_venue, yes_price, no_venue, no_price in rows
        ]

    def _build(
        self,
        candidate: EventCandidate,
        direction: str,
        buy_yes_venue: str,
        buy_yes_price: Decimal,
        buy_no_venue: str,
        buy_no_price: Decimal,
    ) -> CrossVenueOpportunity:
        total_cost = buy_yes_price + buy_no_price
        estimated_fees = total_cost * Decimal(self.settings.cross_venue_fee_bps) / Decimal("10000")
        buffer_bps = (
            self.settings.exact_match_mismatch_buffer_bps
            if candidate.match_type == "exact_equivalent"
            else self.settings.near_match_mismatch_buffer_bps
        )
        mismatch_buffer = Decimal(buffer_bps) / Decimal("10000")
        net_edge = Decimal("1") - total_cost - estimated_fees - mismatch_buffer
        return CrossVenueOpportunity(
            candidate=candidate,
            direction=direction,
            buy_yes_venue=buy_yes_venue,
            buy_yes_price=buy_yes_price,
            buy_no_venue=buy_no_venue,
            buy_no_price=buy_no_price,
            total_cost=total_cost,
            estimated_fees=estimated_fees,
            mismatch_buffer=mismatch_buffer,
            net_edge=net_edge,
        )


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {
        word
        for word in words
        if len(word) > 2
        and word not in STOPWORDS
        and not re.fullmatch(r"20\d\d", word)
    }


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _has_specific_overlap(shared_terms: set[str]) -> bool:
    return any(term not in GENERIC_MATCH_TERMS for term in shared_terms)


def _has_ai_confirmation(candidate: EventCandidate) -> bool:
    return candidate.reason.startswith("ai confidence=")


def _domain(text: str) -> str:
    normalized = text.lower()
    if any(term in normalized for term in CRYPTO_TERMS):
        return "crypto"
    if any(term in normalized for term in ENTERTAINMENT_TERMS):
        return "entertainment"
    if any(term in normalized for term in ECON_TERMS):
        return "economics"
    if any(term in normalized for term in SPORT_TERMS):
        return "sports"
    if any(term in normalized for term in POLITICS_TERMS):
        return "politics"
    return "general"


def _compatible_domains(left: str, right: str) -> bool:
    left_domain = _domain(left)
    right_domain = _domain(right)
    if left_domain in {"economics", "sports", "politics", "crypto", "entertainment"} and right_domain in {
        "economics",
        "sports",
        "politics",
        "crypto",
        "entertainment",
    }:
        return left_domain == right_domain
    return (
        left_domain == right_domain
        or left_domain == "general"
        or right_domain == "general"
    )


def _response_text(data: dict[str, Any]) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    chunks: list[str] = []
    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "".join(chunks)


def _confidence(value: Any, fallback: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        labels = {
            "very high": 0.95,
            "high": 0.85,
            "medium": 0.60,
            "moderate": 0.60,
            "low": 0.30,
            "very low": 0.10,
        }
        if normalized in labels:
            return labels[normalized]
        try:
            return float(normalized)
        except ValueError:
            return fallback
    return fallback
