---
name: trading-risk-runbook
description: Use when working on operational safety, trading risk controls, alerts, reconciliation, incident handling, or admin safeguards for this project. Covers the practical rules for kill switches, anomaly detection, observability, and high-risk money-moving workflows.
---

# Trading Risk Runbook

Use this skill when the task affects operational safety or money-moving correctness.

## Read first

- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [STACK.md](../../STACK.md)
- [PROJECT_DOCS.md](../../PROJECT_DOCS.md)
- [agents.md](../../agents.md)

## What this skill is for

- semantic mismatch risk controls
- venue/API degradation handling
- reconciliation later
- incident handling
- alert design
- admin safety features
- operational guardrails for matching, opportunities and later trading

## Critical principles

- Financial correctness beats speed.
- Reconciliation is mandatory, not optional.
- Every critical workflow must be observable.
- There must be a path to pause trading globally.
- Manual recovery and audit review must be possible.
- AI output must be treated as advisory until verified.

## Minimum controls to preserve

- `global pause`
- `kill switch`
- semantic match status and confidence
- deterministic rule verification
- manual review for ambiguous pairs
- idempotency for deposit / withdrawal flows
- audit log for sensitive admin actions
- explicit `risk_events`
- health checks for services
- alerting on degraded execution and ledger mismatch

## Alert categories

- semantic match confidence drop
- high mismatch rejection rate
- stale orderbook data
- venue API degradation
- fill rate drop
- latency spike
- failed deposits
- failed withdrawals
- ledger mismatch
- queue backlog
- external integration degradation
- repeated reconciliation failures

## When changing trading or money logic

- Ask whether the change can:
  - treat a near match as exact
  - ignore a material resolution-rule difference
  - create double-processing
  - desync internal and external state
  - hide a failed execution
  - weaken auditability
  - bypass pause controls
- If yes, preserve or strengthen the control before merging the change.

## Preferred operational posture

- favor explicit state transitions
- favor append-only financial event recording
- favor deterministic recovery paths
- favor investigation-friendly logs over opaque automation
