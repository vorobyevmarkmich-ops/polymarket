---
name: ledger-accounting
description: Use when implementing balances, ledger entries, fees, pool accounting, reconciliation, or any money-moving workflow in this project. Focuses on financial correctness, append-only event modeling, idempotency, and auditability.
---

# Ledger Accounting

Use this skill when the task affects balances, accounting, or financial source-of-truth logic.

## Read first

- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [STACK.md](../../STACK.md)
- [PROJECT_DOCS.md](../../PROJECT_DOCS.md)
- [agents.md](../../agents.md)

## What this skill covers

- balances
- ledger entries
- fee accounting
- pool position accounting
- reconciliation-sensitive state changes
- auditable financial workflows

## Core rules

- `Postgres` is the source of truth for money state.
- Prefer append-only financial events over mutable balance shortcuts.
- Derived balances should come from ledger and validated aggregates.
- Every money-moving workflow should be idempotent.
- Every state transition should be reconstructible during incident review.

## Modeling guidance

- Separate user-facing balance views from underlying ledger records.
- Track deposits, withdrawals, fees, and trade effects explicitly.
- Do not hide accounting effects inside opaque worker state.
- Keep fee events first-class and queryable.

## When implementing money logic

- Ask:
  - can this be processed twice?
  - can this desync from external state?
  - can this lose auditability?
  - can this produce a dashboard number that is not ledger-backed?
- If yes, redesign before proceeding.

## Preferred posture

- favor explicit ledger events
- favor deterministic recomputation
- favor reconciliation-friendly schemas
- favor correctness over convenience
