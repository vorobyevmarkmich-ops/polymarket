---
name: project-architecture
description: Use when implementing or refactoring code in this project and you need the agreed architecture, service boundaries, target stack, storage rules, and infrastructure assumptions for v1. Best for scaffold, system design, service layout, and operational decisions.
---

# Project Architecture

Use this skill when the task touches project structure, service boundaries, data ownership, or infrastructure.

## Read first

- [STACK.md](../../STACK.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [agents.md](../../agents.md)

## Target stack

- `Next.js` frontend
- `Node.js` backend API
- `Python` trading / risk / reconciliation workers
- `Postgres` as source of truth
- `Redis` for queues, locks, and coordination
- `Docker Compose` for v1 deployment baseline

## Service boundaries

- `frontend`
- `backend-api`
- `trading-worker`
- `risk-worker`
- `reconciliation-worker`
- `notification-worker`

## Architecture rules

- Do not couple frontend directly to trading execution.
- Do not make workers the source of truth for user balances.
- Use `Postgres` for money and business truth.
- Use `Redis` for orchestration, not for financial truth.
- Keep user-facing API and trading execution in separate processes.
- Assume `global pause` and `kill switch` are required features.

## When scaffolding code

- Prefer directories and modules that reflect the service boundaries above.
- Keep ledger-related logic explicit and auditable.
- Separate synchronous request handling from background processing.
- Build for later observability, even in v1.

## When making infra decisions

- Favor simple v1 deployment over premature microservice complexity.
- Prefer managed `Postgres` and managed `Redis`.
- Keep app hosts and trading hosts logically separated when possible.

## When in doubt

- Follow `ARCHITECTURE.md` over ad hoc structure.
- If a change affects service ownership or data flow, update the architecture docs too.
