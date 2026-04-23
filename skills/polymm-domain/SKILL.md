---
name: polymm-domain
description: Use when working on product logic, terminology, UX copy, documentation, or business rules for this PolyMM-based project. Covers the core spread-arbitrage model, user flow, product constraints, legal-safe wording, and the local project references to consult first.
---

# PolyMM Domain

Use this skill when the task touches product semantics rather than just code mechanics.

## Read first

- [PROJECT_DOCS.md](../../PROJECT_DOCS.md)
- [agents.md](../../agents.md)

## What this skill covers

- PolyMM product framing
- spread-arbitrage logic at a high level
- user journey through Telegram Mini App and dashboard
- capacity, fees, risks, and disclaimer-sensitive language
- domain vocabulary to keep consistent across code and docs

## Core product model

- The project is modeled around market-making / spread arbitrage on Polymarket.
- The core trade idea is capturing spread by completing `YES + NO` below `$1.00` total cost.
- Product value depends heavily on low-latency execution, not just strategy logic.
- Public-facing yield ranges are indicative, not guaranteed.
- Capacity is constrained by available liquidity and execution quality.

## Use these domain anchors

- `User`
- `Wallet`
- `Deposit`
- `Withdrawal`
- `PoolPosition`
- `LedgerEntry`
- `Market`
- `Order`
- `Fill`
- `Trade`
- `RiskEvent`
- `FeeEvent`

## Product constraints to keep in mind

- Avoid language that implies guaranteed returns.
- Treat all yield numbers as estimated / historical / indicative.
- Keep legal and disclaimer-sensitive copy centralized and consistent.
- The project should be described as high-risk DeFi / prediction-market infrastructure, not a guaranteed investment product.

## When writing copy or docs

- Prefer precise, neutral wording.
- Refer back to `PROJECT_DOCS.md` before inventing new terminology.
- Keep the user flow consistent: deposit -> pool participation -> stats -> withdrawal.
- Mention Polymarket, Polygon, bridge, and wallet dependencies where relevant.

## When making product decisions

- Check whether the decision affects:
  - risk disclosures
  - fees
  - capacity
  - user balances
  - trading semantics
- If yes, align with `PROJECT_DOCS.md` first.
