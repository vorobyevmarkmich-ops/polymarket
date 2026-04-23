# Stack

Формальное описание целевого технологического стека проекта `v1`. Это рабочая целевая схема, а не подтвержденный набор исходников: в репозитории пока нет кодовой базы и manifest-файлов.

## Статус

- Репозиторий пока содержит knowledge-base слой, а не реализацию.
- Стек ниже принят как целевой baseline для дальнейшего scaffold и разработки.
- При появлении реального кода этот файл нужно обновить и отметить, что уже подтверждено исходниками.
- Ближайшая реализация начинается с MVP-0 screener: [MVP_0_SCREENER.md](/Users/markvorobev/Documents/Codex/Pumpfun/MVP_0_SCREENER.md).

## MVP-0 Stack

Первый этап intentionally проще полной v1-архитектуры:

- `Python`
- `asyncio`
- `httpx` или `aiohttp`
- `pydantic`
- Telegram Bot API
- `Postgres` или временно `SQLite`
- `.env`

Не требуется в MVP-0:

- `Next.js`
- `backend-api`
- `Redis`
- user dashboard
- автотрейдинг
- public deposit / withdrawal flow

## Product Surface

- Landing page
- Docs
- User dashboard
- Telegram Mini App
- Admin / backoffice позже при необходимости

## Frontend

- `Next.js`
- SSR / app-router подход допустим как базовый выбор
- Использовать для:
  - landing
  - docs
  - dashboard
  - Telegram Mini App UI
  - внутренних операторских экранов позже

## Backend API

- `Node.js`
- Предпочтительно `NestJS` или `Fastify`
- Зона ответственности:
  - auth
  - users
  - sessions
  - balances
  - portfolio
  - deposits
  - withdrawals
  - referrals
  - stats
  - admin-facing API

## Trading / Workers

- `Python`
- Использовать для:
  - market scanning
  - opportunity detection
  - order execution
  - fill tracking
  - reconciliation jobs
  - risk checks
  - notifications и фоновые задачи при необходимости

## Storage

### Main DB

- `Postgres`
- Главный источник истины для бизнес-сущностей и денежного учета

### Cache / Queue / Coordination

- `Redis`
- Использовать для:
  - queues
  - locks
  - short-lived state
  - operational coordination

Не использовать `Redis` как источник истины для финансового состояния.

## Infra

- `Docker Compose` на старте
- `Nginx` или cloud load balancer
- `S3-compatible storage` при необходимости
- managed `Postgres`
- managed `Redis`

## Observability

- `Prometheus + Grafana`
- `Sentry`
- централизованные логи
- health endpoints у всех сервисов

## Deployment Model v1

### App Host

- `frontend`
- `backend-api`
- `notification-worker`

### Trading Host

- `trading-worker`
- `risk-worker`
- `reconciliation-worker`

### Managed Services

- `Postgres`
- `Redis`
- object storage при необходимости

## Почему именно такой стек

- `Next.js` подходит для продукта с landing/docs/dashboard в одном контуре.
- `Node.js` удобен для product API, auth, Telegram flow и backoffice.
- `Python` удобен для trading logic, research, execution и reconciliation.
- `Postgres` нужен как единый источник истины по пользователям, деньгам, сделкам и комиссиям.
- `Redis` нужен для low-latency orchestration, очередей и блокировок.

## Что подтвердить позже кодом

После появления исходников нужно обновить этот файл и зафиксировать:

- фактический package manager
- фактический backend framework
- структуру monorepo / multirepo
- команды запуска
- команды тестов
- env/config conventions
- container layout
