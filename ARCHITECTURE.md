# Architecture

Формальная рабочая схема целевой архитектуры `v1` для проекта вокруг PolyMM / Polymarket.

## Summary

Архитектура делится на четыре основных слоя:

- `client layer`
- `api layer`
- `trading/risk layer`
- `data/ops layer`

Принципиальная идея: пользовательский контур и торговый контур разделены. UI и внешний API не должны напрямую зависеть от исполнения торговой логики в одном процессе.

Ближайший practical старт: [MVP_0_SCREENER.md](/Users/markvorobev/Documents/Codex/Pumpfun/MVP_0_SCREENER.md). Для MVP-0 строим только real-time screener Polymarket opportunities и Telegram alerts, без депозитов, dashboard и автотрейдинга.

## MVP-0 Architecture

Минимальные компоненты:

- `scanner-worker`
  Получает markets и market data.
- `market-registry`
  Хранит известные рынки и отслеживает новые.
- `opportunity-detector`
  Ищет `YES ask + NO ask < 1.00`.
- `telegram-alert-bot`
  Отправляет сигналы оператору.
- `storage`
  Хранит markets, snapshots, opportunities и alert history.

Поток MVP-0:

1. `scanner-worker` обновляет список рынков.
2. `scanner-worker` получает цены активных рынков.
3. `opportunity-detector` считает total cost и spread.
4. Фильтры отбрасывают stale / small / duplicate opportunities.
5. `telegram-alert-bot` отправляет alert.
6. `storage` сохраняет opportunity и alert event.

Архитектурные ограничения MVP-0:

- нет user-facing deposits;
- нет withdrawals;
- нет public dashboard;
- нет autonomous execution;
- все opportunities считаются observed signals, а не guaranteed profit.

## Основные сервисы

### `frontend`

Назначение:

- landing
- docs
- dashboard
- Telegram Mini App UI

Правила:

- не общается напрямую с trading layer
- работает только через `backend-api`

### `backend-api`

Назначение:

- единая внешняя API-точка
- auth и sessions
- user/business state
- portfolio and balances
- deposits / withdrawals
- referrals
- stats

Правила:

- пишет бизнес-состояние в `Postgres`
- публикует фоновые задачи в `Redis`
- отдает агрегаты и статус в UI

### `trading-worker`

Назначение:

- market scanning
- opportunity detection
- order placement
- fill tracking
- trade event processing

Правила:

- не является источником истины по пользовательским балансам
- пишет торговые события в систему учета

### `risk-worker`

Назначение:

- exposure checks
- trading limits
- anomaly detection
- kill switch / pause logic

Правила:

- может блокировать исполнение
- пишет `risk_events`

### `reconciliation-worker`

Назначение:

- сверка deposits
- сверка withdrawals
- сверка balances
- сверка ledger
- сверка orders / fills / trades

Правила:

- должен поднимать инцидент при расхождении источников истины

### `notification-worker`

Назначение:

- Telegram notifications
- пользовательские уведомления
- сервисные уведомления
- ops alerts routing

## Поток данных

1. Пользователь открывает `frontend`.
2. `frontend` вызывает `backend-api`.
3. Пользователь создает действие: deposit, withdraw, open app, view stats.
4. `backend-api` сохраняет состояние в `Postgres`.
5. `backend-api` публикует фоновую задачу в `Redis`.
6. `trading-worker` читает market data и исполняет strategy logic.
7. `risk-worker` проверяет лимиты и право на исполнение.
8. `trading-worker` пишет `orders`, `fills`, `trades` и связанные события.
9. `reconciliation-worker` сверяет внешнее и внутреннее состояние.
10. `backend-api` отдает агрегированные данные в dashboard.
11. `notification-worker` рассылает события пользователям и в ops-каналы.

## Доменные сущности

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
- `StrategyRun`
- `RiskEvent`
- `FeeEvent`
- `ReferralReward`
- `Notification`

## Хранилища

### `Postgres`

Источник истины для:

- users
- wallets
- deposits
- withdrawals
- pool positions
- ledger entries
- trades
- fees
- referrals
- risk events

### `Redis`

Использовать для:

- `deposit_processing`
- `withdraw_processing`
- `trade_execution`
- `trade_settlement`
- `reconciliation`
- `notifications`
- `risk_checks`
- distributed locks

## Архитектурные правила

- Не смешивать user-facing API и trading execution в одном процессе.
- Не хранить финансовое состояние только в памяти воркеров.
- Не использовать `Redis` как денежный источник истины.
- Все пользовательские агрегаты должны быть производны от ledger и торговых событий.
- Любая критичная операция должна быть идемпотентной.
- Должны существовать `global pause` и ручной `kill switch`.

## Observability

Обязательно с первого дня:

- `Sentry`
- `Prometheus + Grafana`
- централизованные логи
- health checks

Алерты:

- fill rate drop
- latency spike
- failed deposits
- failed withdrawals
- ledger mismatch
- external API degradation
- queue backlog
- global trading pause

## Security и контроль

- secrets только через env / secret manager
- RBAC для admin
- audit log для admin действий
- idempotency keys для deposits / withdrawals
- reconciliation jobs обязательны
- legal/disclaimer-sensitive тексты централизовать

## Ограничения v1

- Не дробить систему слишком рано на большое число микросервисов.
- Не строить сложный orchestration layer до появления реальной необходимости.
- Не давать frontend прямой доступ к trading engine.
- Не делать архитектуру зависимой от optimistic in-memory state.

## Что уточнить позже

После появления кода и интеграций нужно дополнить:

- фактические API contracts
- схему таблиц
- event schemas
- queue naming conventions
- env layout
- deployment topology по средам `local`, `staging`, `production`
