# Stack

Формальное описание целевого технологического стека проекта `v1` после перехода на cross-venue prediction-market arbitrage.

## Статус

- В корне есть начальная реализация `apps/screener`, но она пока относится к старой Polymarket-only гипотезе.
- Новый MVP требует refactor под несколько venues и AI semantic matching.
- Ближайшая реализация описана в [MVP_0_SCREENER.md](/Users/markvorobev/Documents/Codex/Pumpfun/MVP_0_SCREENER.md).

## MVP-0 Stack

Первый этап intentionally простой:

- `Python`
- `asyncio`
- `httpx` или `aiohttp`
- `pydantic`
- OpenAI Responses API для semantic matching
- Telegram Bot API
- `Postgres` или временно `SQLite`
- `.env`

Не требуется в MVP-0:

- `Next.js`
- full `backend-api`
- `Redis`
- user dashboard
- автотрейдинг
- public deposit / withdrawal flow

## Venues

Первый production-research pair:

- `Polymarket`
- `Kalshi`

Кандидаты следующего этапа:

- `Opinion.trade`
- `Predict.fun`

Каждая площадка должна подключаться через отдельный adapter с единым internal interface.

## AI / Agent Layer

Использовать:

- OpenAI Responses API;
- structured outputs / function calling;
- versioned prompts;
- сохранение AI runs в storage.

Назначение:

- canonical event extraction;
- semantic event matching;
- explanation of material differences;
- confidence scoring;
- human-review routing.

AI не должен размещать ордера или обходить deterministic risk checks.

## Product Surface

MVP:

- Telegram ops alerts;
- simple operator review через storage/config.

Later:

- operator dashboard;
- admin/backoffice;
- Telegram Mini App;
- user dashboard;
- docs/landing.

## Frontend Later

- `Next.js`
- использовать для:
  - operator dashboard;
  - review queue;
  - opportunity history;
  - future Telegram Mini App UI;
  - docs/landing.

## Backend API Later

- `Node.js`
- предпочтительно `NestJS` или `Fastify`
- зона ответственности:
  - auth;
  - operator review actions;
  - opportunity history;
  - settings;
  - admin-facing API;
  - future user state.

## Workers

- `collector-workers`
  Venue-specific market and orderbook ingestion.
- `ai-matching-worker`
  Event normalization and semantic matching.
- `scanner-worker`
  Cross-venue price scanning for approved pairs.
- `risk-worker`
  Edge, liquidity, stale data, mismatch and venue-health filters.
- `notification-worker`
  Telegram and ops alerts.
- `execution-worker` later
  Controlled order placement and fill tracking.

## Storage

### Main DB

- `Postgres`
- источник истины для markets, matches, AI runs, operator reviews, opportunities, alerts and later trading records.

### Cache / Queue / Coordination

- `Redis`
- использовать позже для queues, locks, latest snapshots, rate-limit coordination and notification deduplication.

Не использовать `Redis` как источник истины для денег, matches или audit history.

## Infra

- `Docker Compose` на старте;
- Railway или аналогичный worker host для MVP;
- managed `Postgres` после smoke validation;
- managed `Redis` позже;
- secret manager для API keys.

## Observability

- structured logs с `venue`, `market_id`, `event_match_id`, `opportunity_id`;
- `Sentry`;
- `Prometheus + Grafana` later;
- health checks;
- AI cost/error metrics;
- venue API degradation alerts.

## Почему именно такой стек

- `Python` удобен для market data ingestion, matching, research и trading logic.
- OpenAI Responses API подходит для structured agentic workflows с tool/function calling.
- `Postgres` нужен для auditability: raw inputs, AI decisions, matches, opportunities.
- `Redis` нужен позже для orchestration, но не для business truth.
- `Next.js` и `Node.js` полезны позже, когда появится operator/user product surface.

