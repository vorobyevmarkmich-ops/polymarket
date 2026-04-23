# Agents Context

Короткая рабочая памятка по проекту для последующих задач в этой папке. Этот файл нужен как оперативная схема проекта: продукт, стек, архитектура, сервисы, доступные инструменты и рабочие правила.

## Проект

- Проект опирается на PolyMM: AI market-making / spread arbitrage protocol для Polymarket.
- Основная механика: одновременная работа с `YES` и `NO` по одному событию при суммарной цене ниже `$1.00`.
- Основной пользовательский контур: `Telegram Mini App` + `dashboard`.
- Основные внешние зависимости по документации: `Polymarket`, `Polymarket Bridge`, `Polygon`, wallet providers.

## Базовые reference-файлы

- Главный продуктовый reference: [PROJECT_DOCS.md](/Users/markvorobev/Documents/Codex/Pumpfun/PROJECT_DOCS.md)
- Оперативная памятка по проекту: [agents.md](/Users/markvorobev/Documents/Codex/Pumpfun/agents.md)
- Формальный стек: [STACK.md](/Users/markvorobev/Documents/Codex/Pumpfun/STACK.md)
- Формальная архитектура: [ARCHITECTURE.md](/Users/markvorobev/Documents/Codex/Pumpfun/ARCHITECTURE.md)
- План первого MVP: [MVP_0_SCREENER.md](/Users/markvorobev/Documents/Codex/Pumpfun/MVP_0_SCREENER.md)
- Пример конфигурации MCP для Codex: [MCP_CONFIG_EXAMPLE.toml](/Users/markvorobev/Documents/Codex/Pumpfun/MCP_CONFIG_EXAMPLE.toml)
- Деплой screener worker: [DEPLOYMENT.md](/Users/markvorobev/Documents/Codex/Pumpfun/DEPLOYMENT.md)
- Роли агентов: [roles](/Users/markvorobev/Documents/Codex/Pumpfun/roles)

## Текущее состояние репозитория

- На текущий момент в репозитории нет исходного кода, `package.json`, `pyproject.toml`, `Cargo.toml`, `Dockerfile` или других manifest-файлов.
- Подтвержден только документарный слой проекта.
- Поэтому технический стек ниже пока считается целевым `v1`, а не подтвержденным локальными исходниками.

## Целевой стек v1

Полная формализация вынесена в [STACK.md](/Users/markvorobev/Documents/Codex/Pumpfun/STACK.md).

Коротко:

- `Next.js` для frontend
- `Node.js` для backend API
- `Python` для trading / risk / reconciliation workers
- `Postgres` как основная БД
- `Redis` для queues, locks, cache
- `Docker Compose` на старте
- `Prometheus + Grafana`
- `Sentry`

## Ближайший MVP-0

Текущий практический приоритет:

- [MVP_0_SCREENER.md](/Users/markvorobev/Documents/Codex/Pumpfun/MVP_0_SCREENER.md)

Что делаем первым:

- real-time Polymarket screener
- discovery новых рынков
- detector для `YES ask + NO ask < 1.00`
- Telegram alerts
- сохранение opportunities и alert history

Фактическая стартовая реализация:

- [apps/screener](/Users/markvorobev/Documents/Codex/Pumpfun/apps/screener)

Smoke run:

```bash
cd /Users/markvorobev/Documents/Codex/Pumpfun/apps/screener
PYTHONPATH=src python3 -m screener.main --once
```

Что специально не делаем в MVP-0:

- deposits
- withdrawals
- public user dashboard
- autonomous execution
- yield promises

## Архитектура v1

Полная формализация вынесена в [ARCHITECTURE.md](/Users/markvorobev/Documents/Codex/Pumpfun/ARCHITECTURE.md).

Коротко:

- `frontend`
- `backend-api`
- `trading-worker`
- `risk-worker`
- `reconciliation-worker`
- `notification-worker`
- `postgres`
- `redis`

Ключевое правило:

- пользовательский контур и trading execution должны быть разделены
- `Postgres` хранит бизнес-истину
- `Redis` используется для orchestration, но не для денежной истины

## Ключевые факты продукта

- Product thesis: low-latency execution важнее самой идеи стратегии.
- Окно возможности короткое: порядка `10-50 ms`.
- Заявленный ориентир доходности: `0.3% - 1.1%` в сутки.
- В документации это не гарантия, а исторический / расчетный ориентир.
- Емкость протокола ограничена и на сайте фигурирует около `$3M`.
- Документация прямо подчеркивает high-risk nature продукта: DeFi, smart contracts, third-party dependencies, regulatory risk.

## Роли агентов

Рекомендуемая рабочая модель на текущем этапе:

- [roles/main-builder.md](/Users/markvorobev/Documents/Codex/Pumpfun/roles/main-builder.md)
- [roles/tester-reviewer.md](/Users/markvorobev/Documents/Codex/Pumpfun/roles/tester-reviewer.md)
- [roles/risk-ops.md](/Users/markvorobev/Documents/Codex/Pumpfun/roles/risk-ops.md)

Как использовать:

- `main-builder` — основная роль по умолчанию
- `tester-reviewer` — подключать на review, regressions, test planning, critical UI/API checks
- `risk-ops` — подключать на money logic, ledger, reconciliation, observability, safeguards

Почему не больше:

- на старте достаточно 3 ролей
- это дает разделение ответственности без перегруза
- дополнительные роли имеет смысл добавлять только когда появится реальный повторяемый workflow

## Skills

Локальные проектные skills находятся в папке [skills](/Users/markvorobev/Documents/Codex/Pumpfun/skills).

### Доступно сейчас в сессии

- `imagegen`
- `openai-docs`
- `plugin-creator`
- `skill-creator`
- `skill-installer`
- `Excel`
- `PowerPoint`

### Наиболее полезно для этого проекта

- `skill-creator`
  Чтобы позже сделать кастомные skills под PolyMM, Polymarket, risk rules, ops runbooks.
- `plugin-creator`
  Чтобы собрать локальный plugin под этот проект, если появится повторяемый workflow.
- `Excel`
  Для расчетов доходности, fee-моделей, capacity, backtest-сводок.
- `imagegen`
  Для схем архитектуры, визуалов, mockups.

### Рекомендуемые кастомные skills позже

- `polymm-domain`
  Продуктовые сущности, термины, ограничения, legal-safe wording.
- `project-architecture`
  Сервисные границы, стек, data ownership, v1 architecture rules.
- `polymarket-integration`
  Markets, execution semantics, bridge flow, settlement.
- `trading-risk-runbook`
  Алерты, инциденты, reconciliation, kill switch, ручные проверки.
- `ledger-accounting`
  Ledger, balances, fees, append-only money logic, auditability.
- `telegram-mini-app`
  Onboarding, dashboard, deposit/withdraw UX, mobile-first Telegram flow.

## Plugins

### Доступно сейчас в сессии

- `Computer Use`

### Наиболее полезно для этого проекта

- `Computer Use`
  Проверка `Telegram Mini App`, dashboard, onboarding, docs UI, админских flow и ручных сценариев.

## MCP

### Доступно сейчас в сессии

- В текущей сессии MCP-ресурсы не подключены.
- MCP templates тоже отсутствуют.
- В проекте заскелечен локальный read-only MCP: [mcp/knowledge-mcp/server.py](/Users/markvorobev/Documents/Codex/Pumpfun/mcp/knowledge-mcp/server.py)
- В проекте заскелечен локальный read-only MCP: [mcp/postgres-mcp/server.py](/Users/markvorobev/Documents/Codex/Pumpfun/mcp/postgres-mcp/server.py)
- В проекте заскелечен локальный read-only MCP: [mcp/redis-mcp/server.py](/Users/markvorobev/Documents/Codex/Pumpfun/mcp/redis-mcp/server.py)

### Рекомендуется подключить позже

- MCP priority 1:
  - repository / knowledge base
  - `Postgres`
  - `Redis`
- MCP priority 2:
  - `GitHub` или `GitLab`
  - observability stack
  - market / integration docs
  - `Supabase`
  - `Snyk`

- MCP к репозиторию / knowledge base
  Для быстрого доступа к исходникам, docs, ADR, конфигам и схемам.
- MCP к `Postgres`
  Для анализа users, balances, ledger, trades, fees, referrals.
- MCP к `Redis`
  Для очередей, locks и оперативной диагностики workers.
- MCP к `GitHub` или `GitLab`
  Для issues, PR, CI, review и релизного контекста.
- MCP к observability
  `Sentry`, `Grafana`, `Datadog`, `Loki` или аналогам.
- MCP к market/integration docs
  Для Polymarket API, внешних интеграций и runbooks.
- MCP к `Supabase`
  Для hosted Postgres, logs, advisors, functions и project-scoped development access.
- MCP к `Snyk`
  Для security scanning, dependency checks и guardrails в AI-assisted coding workflow.

### Локальный knowledge MCP

Текущий локальный MCP-сервер:

- `knowledge-mcp`

Назначение:

- читать `PROJECT_DOCS.md`
- читать `STACK.md`
- читать `ARCHITECTURE.md`
- читать `agents.md`
- перечислять и читать локальные project skills

Базовый запуск после установки зависимостей:

```bash
cd /Users/markvorobev/Documents/Codex/Pumpfun/mcp/knowledge-mcp
uv run server.py
```

Если подключать его как локальный stdio MCP, дальше имеет смысл добавить конфиг Codex с запуском через `uv`.

### Локальный postgres MCP

Текущий локальный MCP-сервер:

- `postgres-mcp`

Назначение:

- read-only доступ к Postgres
- introspection схемы и таблиц
- безопасные `SELECT/WITH/EXPLAIN` запросы
- просмотр последних строк и примерных counts

Переменная окружения для подключения:

```bash
POSTGRES_MCP_DSN=postgresql://user:password@host:5432/dbname
```

Базовый запуск после установки зависимостей:

```bash
cd /Users/markvorobev/Documents/Codex/Pumpfun/mcp/postgres-mcp
POSTGRES_MCP_DSN=postgresql://user:password@host:5432/dbname uv run server.py
```

Правило безопасности:

- использовать только read-only подключение и read-only SQL

### Локальный redis MCP

Текущий локальный MCP-сервер:

- `redis-mcp`

Назначение:

- read-only доступ к Redis
- server info и healthcheck
- scan по ключам
- introspection значений и queue-like структур

Переменная окружения для подключения:

```bash
REDIS_MCP_URL=redis://localhost:6379/0
```

Базовый запуск после установки зависимостей:

```bash
cd /Users/markvorobev/Documents/Codex/Pumpfun/mcp/redis-mcp
REDIS_MCP_URL=redis://localhost:6379/0 uv run server.py
```

Правило безопасности:

- не использовать MCP для удаления ключей, очистки очередей или любой другой мутации Redis

### Общий пример конфигурации

Единый пример конфигурации всех локальных MCP лежит здесь:

- [MCP_CONFIG_EXAMPLE.toml](/Users/markvorobev/Documents/Codex/Pumpfun/MCP_CONFIG_EXAMPLE.toml)

Что делать:

- скопировать нужные блоки в `~/.codex/config.toml`
- проставить реальные значения для `POSTGRES_MCP_DSN`
- при необходимости проставить реальный `REDIS_MCP_URL`
- для Supabase заменить `YOUR_PROJECT_REF` на реальный project ref

### Supabase MCP

Рекомендуемый hosted MCP:

- `https://mcp.supabase.com/mcp`

Безопасный рекомендуемый формат подключения:

```toml
[mcp_servers.supabase]
url = "https://mcp.supabase.com/mcp?project_ref=YOUR_PROJECT_REF&read_only=true"
```

Практические правила:

- использовать project-scoping через `project_ref`
- по умолчанию включать `read_only=true`
- не подключать production project без крайней необходимости
- лучше использовать development / staging project
- вручную подтверждать tool calls, если MCP client это поддерживает

### Snyk MCP

Рекомендуемый локальный MCP:

- через локальный `Snyk CLI`

Безопасный рекомендуемый формат подключения:

```toml
[mcp_servers.snyk]
command = "snyk"
args = ["mcp", "-t", "stdio"]
```

Практические правила:

- сначала установить `Snyk CLI`
- сначала выполнить `snyk auth`
- использовать локальный MCP, а не ждать hosted-версии
- проверять, что CLI умеет сканировать проект напрямую до диагностики MCP
- по возможности держать security checks как review/guardrail слой, а не как write-capable automation

## Ключевые команды

Пока нет проект-специфичных команд, поэтому использовать базовые команды навигации и анализа:

```bash
pwd
ls -la
rg --files
rg "pattern" .
sed -n '1,240p' PROJECT_DOCS.md
sed -n '1,260p' agents.md
```

Для сверки с официальной документацией при необходимости:

```bash
curl -L https://polymm.ai/docs
```

## Рабочие правила

- Считать `PROJECT_DOCS.md` основным локальным источником контекста по продукту.
- Считать `agents.md` основным локальным источником по архитектуре, стеку и workflow.
- Не копировать внешнюю документацию дословно большими фрагментами.
- Если появляется новый код, сначала сверять его с текущим reference и потом обновлять этот файл.
- Все новые проектные описания держать краткими, структурированными и пригодными для переиспользования.
- Если информация о продукте или архитектуре меняется, сначала обновлять локальные reference-файлы.

## Нюансы

- `https://polymm.ai/docs` отдается как SPA, и значимая часть контента приезжает через JS-бандл.
- Поэтому при повторном сборе контекста может понадобиться смотреть не только HTML страницы, но и связанные asset bundles.
- В корне проекта сейчас knowledge-base слой, а не кодовая база.
- На текущий момент самый полезный реальный plugin в сессии это `Computer Use`.
- Отдельный локальный plugin имеет смысл собирать позже, когда появится повторяемый workflow вокруг наших skills, runbooks и project-specific actions.
- После появления исходников сюда нужно добавить:
  - реальные команды запуска
  - реальные команды тестов
  - env/config conventions
  - структуру каталогов
  - соглашения по сервисам

## Что помнить в следующих задачах

- Мы работаем вокруг продукта PolyMM, а не абстрактного trading app.
- Любые продуктовые решения надо сверять с ограничениями из disclaimer, privacy и terms.
- Если задача касается стратегии, инфраструктуры, рисков, комиссии, capacity или пользовательского flow, сначала смотреть `PROJECT_DOCS.md`.
- Если задача касается реализации, сервисов, стека, observability, plugin/skill/MCP ландшафта, сначала смотреть `agents.md`.
