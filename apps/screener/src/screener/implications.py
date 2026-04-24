from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.request import Request, urlopen

from screener.config import Settings
from screener.cross_venue import _confidence, _has_specific_overlap, _jaccard, _response_text, _terms
from screener.models import Market, PriceLevel

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImplicationCandidate:
    premise: Market
    consequence: Market
    score: float
    relation_type: str
    reason: str


@dataclass(frozen=True)
class ImplicationOpportunity:
    candidate: ImplicationCandidate
    premise_yes_price: Decimal
    consequence_yes_ask: Decimal
    estimated_fees: Decimal
    implication_buffer: Decimal
    net_edge: Decimal

    @property
    def net_edge_bps(self) -> int:
        return int(self.net_edge * Decimal("10000"))

    @property
    def key(self) -> str:
        return (
            f"implication:{self.candidate.premise.id}:{self.candidate.consequence.id}:"
            f"{self.premise_yes_price}:{self.consequence_yes_ask}"
        )


class ImplicationMatcher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def find_candidates(
        self,
        markets: list[Market],
        prices: dict[str, PriceLevel] | None = None,
    ) -> list[ImplicationCandidate]:
        raw_candidates: list[ImplicationCandidate] = []
        ranked_pairs: list[tuple[float, Market, Market, str]] = []
        limited = markets[: self.settings.implication_max_markets]

        for left_index, left in enumerate(limited):
            left_terms = _terms(left.question)
            if not left_terms:
                continue
            for right in limited[left_index + 1 :]:
                right_terms = _terms(right.question)
                if not right_terms:
                    continue
                score = _jaccard(left_terms, right_terms)
                if score <= 0:
                    continue
                shared = ", ".join(sorted(left_terms & right_terms)[:12])
                ranked_pairs.append((score, left, right, shared))
                nested = _nested_implication(left, right)
                if nested:
                    premise, consequence, reason = nested
                    raw_candidates.append(
                        ImplicationCandidate(
                            premise=premise,
                            consequence=consequence,
                            score=max(score, 0.95),
                            relation_type="strict_implication",
                            reason=reason,
                        )
                    )
                    continue
                if not _has_specific_overlap(left_terms & right_terms):
                    continue
                if _same_template_different_entity(left.question, right.question):
                    continue
                if score < self.settings.implication_min_match_score:
                    continue
                raw_candidates.extend(self._heuristic_directions(left, right, score, shared))

        ranked_pairs.sort(key=lambda item: item[0], reverse=True)
        for index, (score, left, right, shared) in enumerate(ranked_pairs[:10], start=1):
            LOGGER.info(
                "stage=implication_raw_top index=%s score=%.3f shared_terms=%s left=%s right=%s",
                index,
                score,
                shared,
                left.question[:140],
                right.question[:140],
            )

        raw_candidates.sort(
            key=lambda item: self._candidate_priority(item, prices),
            reverse=True,
        )
        raw_candidates = raw_candidates[: self.settings.implication_max_candidates]
        if self.settings.use_openai_matcher and self.settings.openai_api_key:
            return self._classify_with_openai(raw_candidates)
        return raw_candidates

    def _candidate_priority(
        self,
        candidate: ImplicationCandidate,
        prices: dict[str, PriceLevel] | None,
    ) -> float:
        if prices is None:
            return candidate.score
        premise_yes = prices.get(candidate.premise.yes_token_id)
        consequence_yes = prices.get(candidate.consequence.yes_token_id)
        if premise_yes is None or consequence_yes is None:
            return candidate.score
        raw_edge = premise_yes.ask_price - consequence_yes.ask_price
        edge_bonus = max(Decimal("0"), raw_edge) * Decimal("2")
        anchor_bonus = Decimal("0.25") if premise_yes.ask_price >= Decimal("0.80") else Decimal("0")
        relation_bonus = Decimal("1.5") if candidate.relation_type == "strict_implication" else Decimal("0")
        return float(Decimal(str(candidate.score)) + edge_bonus + anchor_bonus + relation_bonus)

    def _heuristic_directions(
        self,
        left: Market,
        right: Market,
        score: float,
        shared: str,
    ) -> list[ImplicationCandidate]:
        relation_type = "possible_implication" if self.settings.allow_heuristic_implications else "needs_ai_review"
        return [
            ImplicationCandidate(
                premise=left,
                consequence=right,
                score=score,
                relation_type=relation_type,
                reason=f"heuristic token overlap; shared_terms={shared}",
            ),
            ImplicationCandidate(
                premise=right,
                consequence=left,
                score=score,
                relation_type=relation_type,
                reason=f"heuristic token overlap; shared_terms={shared}",
            ),
        ]

    def _classify_with_openai(self, candidates: list[ImplicationCandidate]) -> list[ImplicationCandidate]:
        refined: list[ImplicationCandidate] = []
        for candidate in candidates:
            if candidate.reason.startswith("deterministic"):
                refined.append(candidate)
                continue
            try:
                refined.append(self._classify_one_with_openai(candidate))
            except Exception:
                LOGGER.exception(
                    "ai_implication_match_failed premise_id=%s consequence_id=%s fallback_score=%.3f",
                    candidate.premise.id,
                    candidate.consequence.id,
                    candidate.score,
                )
                refined.append(candidate)
        refined.sort(key=lambda item: item.score, reverse=True)
        return refined

    def _classify_one_with_openai(self, candidate: ImplicationCandidate) -> ImplicationCandidate:
        prompt = {
            "premise_market": {
                "title": candidate.premise.question,
                "url": candidate.premise.url,
            },
            "consequence_market": {
                "title": candidate.consequence.question,
                "url": candidate.consequence.url,
            },
        }
        body = {
            "model": self.settings.openai_model,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You classify directional logical relationships between two Polymarket contracts. "
                        "The key question is whether YES on the premise market necessarily or almost necessarily "
                        "implies YES on the consequence market under the market resolution rules. "
                        "Return only compact JSON with keys relation_type, confidence, material_risks, explanation. "
                        "relation_type must be strict_implication, likely_implication, equivalent, "
                        "related_no_implication, inverse_or_conflict, or different. "
                        "Be conservative: if wording, dates, venue, tournament stage, or resolution criteria differ "
                        "materially, do not classify as an implication."
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
        parsed = json.loads(_response_text(data))
        relation_type = str(parsed.get("relation_type") or candidate.relation_type)
        confidence = _confidence(parsed.get("confidence"), candidate.score)
        risks = parsed.get("material_risks") or []
        explanation = str(parsed.get("explanation") or "")
        reason = f"ai confidence={confidence:.2f}; {explanation}; risks={risks}"
        return ImplicationCandidate(
            premise=candidate.premise,
            consequence=candidate.consequence,
            score=max(0.0, min(confidence, 1.0)),
            relation_type=relation_type,
            reason=reason,
        )


class ImplicationDetector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def detect(
        self,
        candidates: list[ImplicationCandidate],
        prices: dict[str, PriceLevel],
    ) -> list[ImplicationOpportunity]:
        opportunities: list[ImplicationOpportunity] = []
        allowed = {"strict_implication", "likely_implication"}
        if self.settings.allow_heuristic_implications:
            allowed.add("possible_implication")

        min_anchor = Decimal(self.settings.implication_min_anchor_yes_bps) / Decimal("10000")
        min_edge_bps = self.settings.implication_min_edge_bps
        for candidate in candidates:
            if candidate.relation_type not in allowed:
                continue
            premise_yes = prices.get(candidate.premise.yes_token_id)
            consequence_yes = prices.get(candidate.consequence.yes_token_id)
            if premise_yes is None or consequence_yes is None:
                continue
            if premise_yes.ask_price < min_anchor:
                continue
            opportunity = self._build(candidate, premise_yes.ask_price, consequence_yes.ask_price)
            if opportunity.net_edge_bps >= min_edge_bps:
                opportunities.append(opportunity)

        return sorted(opportunities, key=lambda item: item.net_edge, reverse=True)

    def _build(
        self,
        candidate: ImplicationCandidate,
        premise_yes_price: Decimal,
        consequence_yes_ask: Decimal,
    ) -> ImplicationOpportunity:
        estimated_fees = consequence_yes_ask * Decimal(self.settings.implication_fee_bps) / Decimal("10000")
        implication_buffer = Decimal(self.settings.implication_buffer_bps) / Decimal("10000")
        net_edge = premise_yes_price - consequence_yes_ask - estimated_fees - implication_buffer
        return ImplicationOpportunity(
            candidate=candidate,
            premise_yes_price=premise_yes_price,
            consequence_yes_ask=consequence_yes_ask,
            estimated_fees=estimated_fees,
            implication_buffer=implication_buffer,
            net_edge=net_edge,
        )


def _nested_implication(left: Market, right: Market) -> tuple[Market, Market, str] | None:
    left_threshold = _threshold(left.question)
    right_threshold = _threshold(right.question)
    if left_threshold and right_threshold:
        left_subject, left_operator, left_value = left_threshold
        right_subject, right_operator, right_value = right_threshold
        if _similar_subject(left_subject, right_subject) and left_operator == right_operator:
            if left_operator in {">", ">="}:
                if left_value > right_value:
                    return left, right, "deterministic nested threshold: higher threshold implies lower threshold"
                if right_value > left_value:
                    return right, left, "deterministic nested threshold: higher threshold implies lower threshold"
            if left_operator in {"<", "<="}:
                if left_value < right_value:
                    return left, right, "deterministic nested threshold: lower threshold implies higher threshold"
                if right_value < left_value:
                    return right, left, "deterministic nested threshold: lower threshold implies higher threshold"

    left_top = _top_n(left.question)
    right_top = _top_n(right.question)
    if left_top and right_top:
        left_subject, left_n = left_top
        right_subject, right_n = right_top
        if _similar_subject(left_subject, right_subject):
            if left_n < right_n:
                return left, right, "deterministic nested rank: stricter top-N implies looser top-N"
            if right_n < left_n:
                return right, left, "deterministic nested rank: stricter top-N implies looser top-N"
    return None


def _threshold(text: str) -> tuple[str, str, Decimal] | None:
    normalized = text.lower().replace(",", "")
    match = re.search(r"(.+?)\s*(>=|<=|>|<|above|below|over|under|at least)\s*\$?([0-9]+(?:\.[0-9]+)?)\s*([kmb])?", normalized)
    if not match:
        return None
    subject = _normalize_subject(match.group(1))
    operator = match.group(2)
    value = Decimal(match.group(3))
    suffix = match.group(4)
    if suffix == "k":
        value *= Decimal("1000")
    elif suffix == "m":
        value *= Decimal("1000000")
    elif suffix == "b":
        value *= Decimal("1000000000")
    if operator in {"above", "over", "at least"}:
        operator = ">="
    elif operator in {"below", "under"}:
        operator = "<="
    return subject, operator, value


def _top_n(text: str) -> tuple[str, int] | None:
    normalized = text.lower()
    match = re.search(r"will\s+(.+?)\s+finish\s+in\s+the\s+top\s+([0-9]+)", normalized)
    if not match:
        return None
    return _normalize_subject(match.group(1)), int(match.group(2))


def _similar_subject(left: str, right: str) -> bool:
    left_terms = _terms(left)
    right_terms = _terms(right)
    if not left_terms or not right_terms:
        return False
    overlap = left_terms & right_terms
    return bool(overlap) and len(overlap) / max(len(left_terms), len(right_terms)) >= 0.60


def _normalize_subject(text: str) -> str:
    text = re.sub(r"^will\s+", "", text.strip().lower())
    text = re.sub(r"\?$", "", text)
    return text


def _same_template_different_entity(left: str, right: str) -> bool:
    left_normalized = _entity_stripped(left)
    right_normalized = _entity_stripped(right)
    if left_normalized != right_normalized:
        return False
    left_terms = _terms(left)
    right_terms = _terms(right)
    shared = left_terms & right_terms
    unique_left = left_terms - shared
    unique_right = right_terms - shared
    return bool(unique_left and unique_right)


def _entity_stripped(text: str) -> str:
    normalized = text.lower()
    normalized = re.sub(r"will\s+.+?\s+(finish in the top [0-9].*)", r"will ENTITY \1", normalized)
    normalized = re.sub(r"will\s+.+?\s+(be relegated.*)", r"will ENTITY \1", normalized)
    normalized = re.sub(r"will\s+.+?\s+(win the 20[0-9][0-9].*)", r"will ENTITY \1", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()
