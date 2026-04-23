---
name: polymarket-integration
description: Use when implementing market-facing logic, external integrations, execution flows, bridge or wallet interactions, or documentation related to Polymarket and its surrounding dependencies in this project. Focuses on integration boundaries, external dependencies, and safe assumptions.
---

# Polymarket Integration

Use this skill for tasks involving external market interaction and settlement-adjacent flows.

## Read first

- [PROJECT_DOCS.md](../../PROJECT_DOCS.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [agents.md](../../agents.md)

## External systems in scope

- `Polymarket`
- `Polymarket Bridge`
- `Polygon`
- wallet providers

## Integration assumptions

- Market execution depends on external systems outside our control.
- Availability, latency, and market behavior can change.
- Deposits and withdrawals may depend on bridge and chain state.
- Execution outcomes should always be reconciled back into internal ledger state.

## Design rules

- Treat external responses as unreliable until reconciled.
- Make integration jobs idempotent where possible.
- Log every critical boundary event:
  - request sent
  - response received
  - order created
  - fill detected
  - settlement observed
  - deposit confirmed
  - withdrawal confirmed
- Preserve enough data for post-incident audit.

## Use this skill when building

- market data adapters
- execution clients
- deposit / withdrawal pipelines
- bridge-related flows
- wallet verification steps
- reconciliation logic tied to external systems

## Safe implementation posture

- Expect partial failure.
- Expect delayed confirmation.
- Expect external API degradation.
- Do not assume market-side state equals internal state until reconciled.
- Keep integration logic separate from UI-facing business aggregation.
