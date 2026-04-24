# Agents Context

Короткая рабочая памятка по проекту после смены торговой гипотезы.

## Проект

- Проект строится вокруг cross-venue prediction-market arbitrage.
- Основная механика: находить одно и то же событие на разных площадках и покупать `YES` там, где он дешевле, а `NO` там, где он дешевле на другой площадке.
- Первый практический pair: `Polymarket + Kalshi`.
- `Opinion.trade` и `Predict.fun` остаются кандидатами следующих venues.
- ИИ используется для semantic event matching, потому что названия и wording событий могут отличаться.

## Базовые reference-файлы

- Главный продуктовый reference: [PROJECT_DOCS.md](/Users/markvorobev/Documents/Codex/Pumpfun/PROJECT_DOCS.md)
- Формальный стек: [STACK.md](/Users/markvorobev/Documents/Codex/Pumpfun/STACK.md)
- Формальная архитектура: [ARCHITECTURE.md](/Users/markvorobev/Documents/Codex/Pumpfun/ARCHITECTURE.md)
- План первого MVP: [MVP_0_SCREENER.md](/Users/markvorobev/Documents/Codex/Pumpfun/MVP_0_SCREENER.md)
- Деплой текущего worker: [DEPLOYMENT.md](/Users/markvorobev/Documents/Codex/Pumpfun/DEPLOYMENT.md)
- Роли агентов: [roles](/Users/markvorobev/Documents/Codex/Pumpfun/roles)

## Текущее состояние репозитория

- В корне есть начальный `apps/screener`.
- Текущий код `apps/screener` относится к старой Polymarket-only гипотезе `YES ask + NO ask < 1.00`.
- Новый MVP требует refactor под `Polymarket + Kalshi`, AI semantic matching и cross-venue opportunity detection.
- Папка `pumpbot/` неотслеживаемая и относится к отдельному направлению; без явной необходимости ее не трогать.

## Ближайший MVP-0

Текущий практический приоритет:

- [MVP_0_SCREENER.md](/Users/markvorobev/Documents/Codex/Pumpfun/MVP_0_SCREENER.md)

Что делаем первым:

- Polymarket collector;
- Kalshi collector;
- raw market registry;
- AI event normalizer;
- semantic match engine;
- deterministic rule verifier;
- cross-venue opportunity detector;
- Telegram alerts;
- storage для markets, matches, AI runs, opportunities и operator review.

Что специально не делаем в MVP-0:

- deposits;
- withdrawals;
- public user dashboard;
- autonomous execution;
- yield promises;
- trading pool.

## Целевой стек v1

Полная формализация вынесена в [STACK.md](/Users/markvorobev/Documents/Codex/Pumpfun/STACK.md).

Коротко:

- `Python` для collectors, AI matching, scanner, risk logic;
- OpenAI Responses API для semantic matching;
- `Postgres` как основной audit/business store;
- `Redis` позже для queues, locks, cache;
- Telegram Bot API для operator alerts;
- `Next.js` и `Node.js` позже для dashboard/backoffice.

## Архитектура v1

Полная формализация вынесена в [ARCHITECTURE.md](/Users/markvorobev/Documents/Codex/Pumpfun/ARCHITECTURE.md).

Коротко:

- `collector-workers`;
- `ai-matching-worker`;
- `scanner-worker`;
- `risk-worker`;
- `notification-worker`;
- `backend-api` later;
- `frontend` later;
- `postgres`;
- `redis` later.

Ключевые правила:

- AI output advisory, not authoritative.
- Event equivalence требует deterministic verification.
- `near_equivalent` pairs требуют manual review.
- Trading execution отделяется от matching/scanning.
- `Postgres` хранит audit trail по raw data, AI decisions и opportunities.

## Ключевые факты продукта

- Product thesis: cross-venue disagreement может быть практичнее, чем внутримаркетный `YES+NO < 1`.
- Главный риск: semantic mismatch, когда события похожи, но resolve по-разному.
- ИИ нужен для understanding wording, но edge/risk считаются обычным кодом.
- Возможность должна учитывать fees, slippage, liquidity, stale data и mismatch buffer.
- Любой сигнал в MVP-0 является observed opportunity, а не гарантированной прибылью.

## Роли агентов

Рекомендуемая рабочая модель:

- [roles/main-builder.md](/Users/markvorobev/Documents/Codex/Pumpfun/roles/main-builder.md)
- [roles/tester-reviewer.md](/Users/markvorobev/Documents/Codex/Pumpfun/roles/tester-reviewer.md)
- [roles/risk-ops.md](/Users/markvorobev/Documents/Codex/Pumpfun/roles/risk-ops.md)

Как использовать:

- `main-builder` — основная роль по умолчанию;
- `tester-reviewer` — review, regressions, test planning;
- `risk-ops` — semantic mismatch risk, execution safety, ledger/reconciliation later.

## Skills

Локальные проектные skills находятся в папке [skills](/Users/markvorobev/Documents/Codex/Pumpfun/skills).

Полезные будущие project-specific skills:

- `prediction-market-domain`
- `cross-venue-arbitrage`
- `semantic-event-matching`
- `polymarket-integration`
- `kalshi-integration`
- `trading-risk-runbook`
- `ledger-accounting`

## MCP

Текущие локальные MCP skeletons:

- [mcp/knowledge-mcp/server.py](/Users/markvorobev/Documents/Codex/Pumpfun/mcp/knowledge-mcp/server.py)
- [mcp/postgres-mcp/server.py](/Users/markvorobev/Documents/Codex/Pumpfun/mcp/postgres-mcp/server.py)
- [mcp/redis-mcp/server.py](/Users/markvorobev/Documents/Codex/Pumpfun/mcp/redis-mcp/server.py)

Priority later:

- knowledge / repository MCP;
- Postgres read-only MCP;
- Redis read-only MCP;
- market docs MCP if useful;
- Snyk/security MCP.

## Ключевые команды

Текущий legacy smoke run:

```bash
cd /Users/markvorobev/Documents/Codex/Pumpfun/apps/screener
PYTHONPATH=src python3 -m screener.main --once
```

После refactor сюда нужно добавить новые команды для cross-venue scanner.

## Рабочие правила

- Считать [PROJECT_DOCS.md](/Users/markvorobev/Documents/Codex/Pumpfun/PROJECT_DOCS.md) главным локальным источником по продукту.
- Считать [ARCHITECTURE.md](/Users/markvorobev/Documents/Codex/Pumpfun/ARCHITECTURE.md) главным источником по сервисным границам.
- Не использовать AI match как торговую истину без deterministic verifier.
- Не копировать внешнюю документацию большими фрагментами.
- Если информация о продукте или архитектуре меняется, сначала обновлять локальные reference-файлы.
- Secrets не хранить в документах, коде или git.

## Что помнить в следующих задачах

- Мы работаем вокруг cross-venue prediction arbitrage, а не абстрактного trading app.
- Главный moat MVP — semantic event matching + reliable verification + fast monitoring approved pairs.
- Для любой задачи по площадкам сначала смотреть официальные API docs.
- Для любой задачи по OpenAI API использовать актуальные OpenAI docs и хранить ключ только через env / secret manager.

