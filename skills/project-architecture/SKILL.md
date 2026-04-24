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

- `Python` collectors, AI matching, scanner and risk workers
- OpenAI Responses API for semantic event matching
- `Postgres` as source of truth and audit store
- `Redis` later for queues, locks, and coordination
- `Next.js` frontend later for operator dashboard
- `Node.js` backend API later for review/admin workflows

## Service boundaries

- `collector-workers`
- `ai-matching-worker`
- `scanner-worker`
- `risk-worker`
- `notification-worker`
- `execution-worker` later
- `backend-api` later
- `frontend` later

## Architecture rules

- Do not let AI output directly trigger trading.
- Use deterministic verification for event equivalence.
- Store raw market data, AI runs and operator reviews in `Postgres`.
- Use `Redis` for orchestration, not for audit truth.
- Keep matching/scanning separate from execution.
- Assume `global pause` and `kill switch` are required features before execution.

## When scaffolding code

- Prefer venue adapters behind a shared interface.
- Keep AI prompts versioned and outputs structured.
- Keep opportunity calculation deterministic and testable.
- Separate market collection, matching, verification and scanning.
- Build for later observability, even in MVP.

## When making infra decisions

- Favor simple v1 deployment over premature microservice complexity.
- Prefer managed `Postgres` and managed `Redis`.
- Keep app hosts and trading hosts logically separated when possible.

## When in doubt

- Follow `ARCHITECTURE.md` over ad hoc structure.
- If a change affects service ownership or data flow, update the architecture docs too.
