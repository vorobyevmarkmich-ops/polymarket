# Architecture

Формальная рабочая схема `v1` для cross-venue prediction-market arbitrage.

## Summary

Новая архитектура строится вокруг поиска одинаковых событий между площадками и сравнения цен `YES` / `NO` на разных venues.

Дополнительный MVP-поток внутри Polymarket ищет directed implication pairs: событие A почти реализовано, A логически влечет B, но `YES` B все еще дешевле с учетом буфера риска.

Первый MVP pair:

- `Polymarket`
- `Kalshi`

Ключевой принцип: AI используется для semantic matching и объяснения отличий между событиями, но не для финальной торговой математики и не для самостоятельного исполнения.

## High-Level Flow

```text
Venue collectors
  -> raw market store
  -> AI event normalizer
  -> semantic match engine
  -> deterministic rule verifier
  -> approved event pairs
  -> cross-venue price scanner
  -> opportunity calculator
  -> risk filters
  -> Telegram/operator alerts

Polymarket collector
  -> raw market store
  -> implication matcher
  -> deterministic implication verifier
  -> implication opportunity detector
  -> Telegram/operator alerts
```

## MVP-0 Architecture

Минимальные компоненты:

- `polymarket-adapter`
  Получает markets/events и orderbook data из Polymarket.
- `kalshi-adapter`
  Получает events/markets и orderbook data из Kalshi.
- `market-registry`
  Хранит raw markets и snapshots по площадкам.
- `ai-event-normalizer`
  Превращает title/rules/description в canonical event schema.
- `semantic-match-engine`
  Ищет одинаковые или близкие события между venues.
- `rule-verifier`
  Детерминированно проверяет даты, timezone, resolution rules и exclusions.
- `opportunity-detector`
  Считает cross-venue opportunity по `YES` на одной площадке и `NO` на другой.
- `implication-opportunity-detector`
  Считает Polymarket-only opportunity по направленной связи `premise YES -> consequence YES`.
- `telegram-alert-bot`
  Отправляет research/trade-candidate alerts оператору.
- `storage`
  Хранит рынки, matches, AI runs, snapshots, opportunities, alerts и operator review.

## AI Layer

AI-agent отвечает за:

- извлечение actor/action/target/time window из рыночных правил;
- поиск semantic candidates;
- классификацию пары как `exact_equivalent`, `near_equivalent`, `related_not_same`, `different`;
- объяснение material differences;
- выставление confidence;
- пометку `operator_review_required`.

AI-agent не отвечает за:

- расчет edge;
- принятие торгового решения;
- обход risk limits;
- размещение ордеров;
- хранение денежных балансов.

Для реализации использовать OpenAI Responses API с structured outputs / function calling. Prompt versions и результаты AI runs должны сохраняться.

## Deterministic Verification

`rule-verifier` проверяет:

- совпадение actor / target;
- совпадение или допустимую эквивалентность action;
- дедлайн и timezone;
- inclusive / exclusive boundary;
- settlement source;
- resolution text differences;
- exclusions;
- market status и close time;
- payout mechanics.

Если verification находит material mismatch, opportunity не попадает в trade-candidate alerts.

## Opportunity Formula

Базовая формула:

```text
buy_yes_price + buy_no_price + venue_fees + slippage + mismatch_buffer < 1.00
```

Где:

- `buy_yes_price` берется с venue, где `YES` дешевле;
- `buy_no_price` берется с другого venue, где `NO` дешевле;
- `venue_fees` считаются отдельно по площадкам;
- `slippage` оценивается по orderbook depth;
- `mismatch_buffer` зависит от качества semantic match.

Для implication opportunities:

```text
premise_yes_price - consequence_yes_ask - fees - implication_buffer >= min_edge
```

`implication_buffer` защищает от ошибки semantic direction и разных resolution rules. Такие сигналы требуют manual/operator review до исполнения.

## Match Status Policy

- `exact_equivalent`
  Можно мониторить автоматически после первичной проверки.
- `near_equivalent`
  Нужен manual review. До подтверждения это только research signal.
- `related_not_same`
  Не использовать для арбитража.
- `different`
  Игнорировать.

## Основные сервисы v1

### `frontend`

Назначение:

- operator dashboard;
- future Telegram Mini App;
- market-pair review UI;
- opportunity history.

### `backend-api`

Назначение:

- API для dashboard;
- operator review actions;
- opportunity history;
- auth/session/admin;
- settings для thresholds и venues.

### `collector-workers`

Назначение:

- Polymarket collector;
- Kalshi collector;
- позже Opinion/Predict collectors;
- нормализация market data;
- запись snapshots.

### `ai-matching-worker`

Назначение:

- canonical event extraction;
- candidate pair classification;
- explanation generation;
- storing AI runs.

### `scanner-worker`

Назначение:

- отслеживать approved event pairs;
- читать latest orderbooks;
- считать cross-venue edge;
- создавать opportunities.

### `risk-worker`

Назначение:

- фильтры semantic mismatch;
- min edge thresholds;
- liquidity/depth checks;
- stale data checks;
- venue degradation checks;
- global pause / kill switch.

### `notification-worker`

Назначение:

- Telegram alerts;
- ops alerts;
- alert cooldown and deduplication.

### `execution-worker` later

Назначение:

- controlled order placement;
- fill tracking;
- cancellation;
- reconciliation.

В MVP-0 этот сервис не включается.

## Доменные сущности

- `Venue`
- `RawMarket`
- `CanonicalEvent`
- `EventMatch`
- `AIMatchingRun`
- `RuleVerificationRun`
- `OperatorReview`
- `OrderbookSnapshot`
- `CrossVenueOpportunity`
- `AlertEvent`
- `VenueCredential` later
- `Order` later
- `Fill` later
- `Trade` later
- `LedgerEntry` later

## Хранилища

### `Postgres`

Источник истины для:

- venues;
- raw markets;
- canonical events;
- event matches;
- AI runs;
- operator reviews;
- snapshots;
- opportunities;
- alerts;
- later orders/fills/ledger.

### `Redis`

Использовать для:

- queues;
- locks;
- rate-limit coordination;
- short-lived latest market cache;
- notification deduplication.

Не использовать `Redis` как источник истины для денег, matches или audit data.

## Observability

Обязательные метрики:

- collector success/fail rate by venue;
- stale market data count;
- AI matching latency/cost/error rate;
- match confidence distribution;
- operator approval/rejection rate;
- opportunities by venue pair;
- net edge distribution;
- alert delivery failures;
- venue API degradation.

## Security

- Все API keys только через `.env` / secret manager.
- OpenAI API key хранить как `OPENAI_API_KEY`.
- Ключи, попавшие в чат или логи, считать скомпрометированными и ротировать.
- Trading credentials отделить от data-only credentials.
- AI output сохранять для аудита, но не хранить secrets в prompt inputs.
- Execution позже должен иметь отдельные лимиты, idempotency keys и kill switch.
