---
name: prediction-market-domain
description: Use when working on product logic, terminology, UX copy, documentation, or business rules for this cross-venue prediction-market arbitrage project. Covers semantic event matching, cross-venue YES/NO arbitrage, risk wording, and local project references.
---

# Prediction Market Domain

Use this skill when the task touches product semantics rather than just code mechanics.

## Read first

- [PROJECT_DOCS.md](../../PROJECT_DOCS.md)
- [agents.md](../../agents.md)
- [MVP_0_SCREENER.md](../../MVP_0_SCREENER.md)

## What this skill covers

- cross-venue prediction-market arbitrage framing;
- semantic event matching;
- canonical event fields;
- YES/NO opportunity logic across venues;
- risk and disclaimer-sensitive language;
- domain vocabulary to keep consistent across code and docs.

## Core product model

- The project is modeled around finding equivalent events across venues.
- First target pair: `Polymarket + Kalshi`.
- Core trade idea: buy `YES` where it is cheap and buy `NO` where it is cheap on another venue, only when both markets resolve on the same economic event.
- AI helps understand wording and resolution rules.
- Deterministic code calculates edge, fees, slippage, stale data and mismatch buffer.
- Public-facing output must describe opportunities as observed signals, not guaranteed profit.

## Use these domain anchors

- `Venue`
- `RawMarket`
- `CanonicalEvent`
- `EventMatch`
- `AIMatchingRun`
- `RuleVerificationRun`
- `OperatorReview`
- `OrderbookSnapshot`
- `CrossVenueOpportunity`
- `AlertEvent`

## Product constraints to keep in mind

- Avoid language that implies guaranteed returns.
- Treat AI matches as advisory until verified.
- Separate `exact_equivalent`, `near_equivalent`, `related_not_same` and `different`.
- Require manual review for ambiguous event pairs.
- Include fees, slippage, stale data and semantic mismatch buffer before calling anything an opportunity.
- Keep legal and disclaimer-sensitive copy centralized and consistent.

## When writing copy or docs

- Prefer precise, neutral wording.
- Refer back to `PROJECT_DOCS.md` before inventing new terminology.
- Say `cross-venue opportunity`, `candidate`, or `observed signal`; avoid `risk-free profit`.
- Explain that titles may differ while economic meaning may match.
- Mention venue-specific resolution rules when relevant.

## When making product decisions

Check whether the decision affects:

- semantic equivalence;
- match confidence;
- operator review;
- fees/slippage;
- liquidity/capacity;
- trading semantics;
- custody or execution risk.

If yes, align with `PROJECT_DOCS.md` and `ARCHITECTURE.md` first.

