# MVP-0: Cross-Venue Prediction Arbitrage Screener

Первый практический этап проекта: не dashboard, не депозитный пул и не автотрейдинг, а screener одинаковых событий между prediction-market площадками с Telegram alerts.

## Цель

Проверить новую торговую гипотезу:

- существуют ли одинаковые или экономически эквивалентные события между Polymarket и Kalshi;
- можно ли reliably находить такие события с помощью AI semantic matching;
- появляются ли cross-venue расхождения цен после учета fees, slippage и semantic mismatch risk;
- появляются ли Polymarket-only implication opportunities между связанными событиями;
- достаточно ли ликвидности для практического исполнения;
- насколько часто нужны manual review и operator decisions.

## Первые venues

### Primary

- `Polymarket`
- `Kalshi`

### Later candidates

- `Opinion.trade`
- `Predict.fun`

Kalshi выбран первым, потому что у него лучше всего выглядит developer onboarding для MVP: public market data, orderbook endpoints, WebSocket/API reference и demo environment.

## Что входит в MVP-0

- `polymarket-adapter`
  Получает рынки, события, descriptions/rules и orderbooks.
- `kalshi-adapter`
  Получает events, markets и orderbooks.
- `market-registry`
  Сохраняет raw markets и snapshots.
- `ai-event-normalizer`
  Извлекает canonical event fields из title/rules.
- `semantic-match-engine`
  Ищет пары одинаковых/похожих событий между venues.
- `rule-verifier`
  Проверяет даты, timezone, settlement rules и material differences.
- `operator-review`
  Позволяет помечать пары как approved/rejected/needs-review.
- `opportunity-detector`
  Считает `YES` на одной площадке + `NO` на другой.
- `implication-scanner`
  Ищет внутри Polymarket направленные связи `premise YES -> consequence YES` и считает edge на дешевом consequence market.
- `telegram-alert-bot`
  Отправляет research/trade-candidate alerts.
- `storage`
  Хранит markets, canonical events, matches, AI runs, snapshots, opportunities и alerts.

## Что не входит в MVP-0

- публичные депозиты пользователей;
- вывод средств;
- user dashboard;
- Telegram Mini App для пользователей;
- автотрейдинг;
- execution engine;
- trading pool;
- обещания доходности.

## Opportunity Logic

Ищем пару рынков, которые resolve одинаково:

```text
venue_a_market == venue_b_market by economic meaning
```

Затем считаем:

```text
buy_yes_price + buy_no_price + fees + slippage + mismatch_buffer < 1.00
```

Пример:

```text
Kalshi YES ask:       0.70
Polymarket NO ask:    0.10
Fees/slippage:        0.03
Mismatch buffer:      0.05
Total cost:           0.88
Expected payout:      1.00
Net edge:             0.12
```

Если события не подтверждены как equivalent, сигнал должен быть research-only.

## Implication Opportunity Logic

Ищем directed pair внутри Polymarket:

```text
premise_yes => consequence_yes
```

Затем считаем:

```text
premise_yes_price - consequence_yes_ask - fees - implication_buffer >= min_edge
```

Стартовый режим консервативный: AI должен классифицировать пару как `strict_implication` или `likely_implication`; heuristic overlap без AI логируется как candidate, но не становится trade-candidate signal без явного `ALLOW_HEURISTIC_IMPLICATIONS=true`.

## AI Matching

AI-agent должен возвращать structured output:

```json
{
  "match_type": "exact_equivalent",
  "confidence": 0.93,
  "same_actor": true,
  "same_target": true,
  "same_action": true,
  "same_time_window": true,
  "same_resolution_source": "unknown",
  "material_differences": [],
  "operator_review_required": false,
  "explanation": "Both markets resolve YES if the same event happens before the same deadline."
}
```

Статусы:

- `exact_equivalent`
- `near_equivalent`
- `related_not_same`
- `different`

## MVP filters

Стартовые значения:

- `MIN_NET_EDGE_BPS=300`
- `MIN_EXACT_MATCH_CONFIDENCE=0.88`
- `MIN_NEAR_MATCH_CONFIDENCE=0.75`
- `EXACT_MATCH_MISMATCH_BUFFER_BPS=100`
- `NEAR_MATCH_MISMATCH_BUFFER_BPS=500`
- `MIN_SIZE_USD=10`
- `MAX_PRICE_STALENESS_SECONDS=5`
- `MARKET_DISCOVERY_INTERVAL_SECONDS=300`
- `PRICE_SCAN_INTERVAL_SECONDS=2`
- `ALERT_COOLDOWN_SECONDS=300`

## Telegram alert format

Пример:

```text
Cross-venue opportunity candidate

Pair: Polymarket / Kalshi
Canonical event: US military action against Iran before Apr 1
Match: near_equivalent, confidence 0.86
Review: required

Buy YES: Kalshi @ 0.70
Buy NO: Polymarket @ 0.10
Fees/slippage est: 0.03
Mismatch buffer: 0.05
Total: 0.88
Net edge: 12.0%

Material differences:
- Kalshi wording says "military operation"; Polymarket wording says "attack".

URLs:
Kalshi: ...
Polymarket: ...
```

## Минимальный стек MVP-0

- `Python`
- `asyncio`
- `httpx` или `aiohttp`
- `pydantic`
- OpenAI Responses API
- Telegram Bot API
- `Postgres` или временно `SQLite`
- `.env`

Можно отложить:

- `Next.js`
- full backend API;
- `Redis`;
- user dashboard;
- автотрейдинг.

## Минимальные env-переменные

```bash
OPENAI_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
POLYMARKET_GAMMA_API_BASE=https://gamma-api.polymarket.com
POLYMARKET_CLOB_API_BASE=https://clob.polymarket.com
KALSHI_API_BASE=https://api.elections.kalshi.com/trade-api/v2
DATABASE_URL=
MIN_NET_EDGE_BPS=300
MIN_SIZE_USD=10
MARKET_DISCOVERY_INTERVAL_SECONDS=300
PRICE_SCAN_INTERVAL_SECONDS=2
ALERT_COOLDOWN_SECONDS=300
IMPLICATION_MIN_ANCHOR_YES_BPS=9500
IMPLICATION_MIN_EDGE_BPS=500
IMPLICATION_BUFFER_BPS=300
MAX_PRICE_STALENESS_SECONDS=5
```

## Предлагаемая структура кода

```text
apps/screener/
  pyproject.toml
  .env.example
  src/
    screener/
      config.py
      main.py
      models.py
      venues/
        base.py
        polymarket.py
        kalshi.py
      ai/
        normalizer.py
        matcher.py
        prompts.py
      matching/
        verifier.py
        candidates.py
      opportunities/
        calculator.py
        detector.py
      telegram.py
      storage.py
```

Текущая реализация в [apps/screener](/Users/markvorobev/Documents/Codex/Pumpfun/apps/screener) является legacy Polymarket-only прототипом и должна быть refactored под новую архитектуру.

## Acceptance criteria

MVP-0 считается рабочим, когда:

- scanner запускается локально одной командой;
- получает рынки Polymarket;
- получает рынки Kalshi;
- сохраняет raw market metadata;
- AI normalizer создает canonical event для рынков;
- matcher находит candidate pairs;
- verifier помечает material differences;
- operator может approve/reject pair хотя бы через storage/config;
- detector считает cross-venue `YES + NO`;
- Telegram отправляет research/trade-candidate alerts;
- повторные alerts не спамят чаще cooldown;
- все AI decisions и opportunity calculations сохраняются.

## Правила безопасности

- Не исполнять сделки автоматически.
- Не принимать пользовательские средства.
- Не обещать доходность.
- Не считать AI match истиной без verification.
- Не считать сигнал guaranteed profit.
- Сохранять timestamp и source для каждой цены.
- Хранить API keys только в env / secret manager.

## Следующий этап после MVP-0

Если screener покажет реальные возможности:

- добавить operator dashboard;
- добавить ручной approval flow;
- добавить paper-trading ledger;
- добавить execution simulation;
- добавить venue-specific fees/slippage model;
- только потом думать о controlled execution.
