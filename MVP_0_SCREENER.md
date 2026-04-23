# MVP-0: Real-Time Polymarket Screener

Первый практический этап проекта: не dashboard, не депозитный пул и не автотрейдинг, а real-time screener торговых возможностей на Polymarket с уведомлениями в Telegram.

## Цель

Проверить главную торговую гипотезу до строительства полной платформы:

- появляются ли на Polymarket реальные `YES + NO < $1.00` возможности;
- как часто они появляются;
- какая у них ликвидность;
- насколько быстро они исчезают;
- можно ли их исполнять вручную или полуавтоматически;
- есть ли смысл двигаться к execution layer.

## Что входит в MVP-0

- `scanner-worker`
  Мониторит рынки Polymarket, включая новые рынки.
- `market-registry`
  Хранит список известных рынков и обновляет их статус.
- `opportunity-detector`
  Ищет возможности по формуле `YES ask + NO ask < 1.00`.
- `telegram-alert-bot`
  Отправляет найденные возможности в Telegram.
- `storage`
  Сохраняет markets, opportunities, snapshots и alerts.

## Что не входит в MVP-0

- публичные депозиты пользователей;
- вывод средств;
- user dashboard;
- Telegram Mini App для пользователей;
- автотрейдинг;
- реальный execution engine;
- referral / tiers;
- обещания доходности.

## Минимальный стек MVP-0

- `Python`
- `asyncio`
- `httpx` или `aiohttp`
- `pydantic`
- `Postgres` или `SQLite` для самого первого прототипа
- Telegram Bot API
- `.env`

Можно отложить:

- `Next.js`
- `backend-api`
- `Redis`
- full observability stack
- admin dashboard

## Базовая логика opportunity

Первый фильтр:

```text
YES best ask + NO best ask < 1.00
```

Для CLOB `/prices` в текущей реализации используется `side=SELL`, потому что этот endpoint возвращает ask-сторону, по которой можно оценивать покупку outcome tokens.

Минимальные параметры:

- `market_id`
- `market_title`
- `market_url`
- `yes_ask`
- `no_ask`
- `total_cost`
- `spread`
- `estimated_size`
- `liquidity`
- `detected_at`
- `expires_or_stale_at`

## Фильтры MVP-0

Стартовые значения можно менять после первых замеров:

- `MIN_SPREAD_BPS=50`
- `MIN_SIZE_USD=10`
- `ACTIVE_MARKET_SCAN_INTERVAL_SECONDS=2`
- `MARKET_DISCOVERY_INTERVAL_SECONDS=60`
- `ALERT_COOLDOWN_SECONDS=300`
- `MAX_PRICE_STALENESS_SECONDS=5`

## Telegram alert format

Пример сообщения:

```text
New Polymarket opportunity

Market: BTC above $X today?
YES ask: 0.47
NO ask: 0.50
Total: 0.97
Spread: 3.0%
Size: ~$120
Liquidity: $8,400

URL: https://polymarket.com/event/...
Detected: 12:04:33.128
```

## Минимальные env-переменные

```bash
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
POLYMARKET_GAMMA_API_BASE=
POLYMARKET_CLOB_API_BASE=
DATABASE_URL=
MIN_SPREAD_BPS=50
MIN_SIZE_USD=10
ACTIVE_MARKET_SCAN_INTERVAL_SECONDS=2
MARKET_DISCOVERY_INTERVAL_SECONDS=60
ALERT_COOLDOWN_SECONDS=300
MAX_PRICE_STALENESS_SECONDS=5
```

## Предлагаемая структура кода

```text
apps/screener/
  pyproject.toml
  .env.example
  src/
    config.py
    main.py
    polymarket/
      client.py
      models.py
    market_registry.py
    detector.py
    telegram.py
    storage.py
```

Фактическая начальная реализация создана в [apps/screener](/Users/markvorobev/Documents/Codex/Pumpfun/apps/screener).

Smoke run:

```bash
cd /Users/markvorobev/Documents/Codex/Pumpfun/apps/screener
PYTHONPATH=src python3 -m screener.main --once
```

## Acceptance criteria

MVP-0 считается рабочим, когда:

- scanner запускается локально одной командой;
- scanner получает список рынков;
- scanner обновляет или обнаруживает новые рынки;
- detector считает `YES ask + NO ask`;
- detector фильтрует opportunities по spread и size;
- Telegram bot отправляет alert;
- повторные alerts не спамят чаще cooldown;
- opportunity сохраняется в storage;
- ошибки внешних API логируются и не валят процесс окончательно.

## Правила безопасности

- Не исполнять сделки автоматически.
- Не принимать пользовательские средства.
- Не обещать доходность.
- Не считать сигнал гарантированной возможностью.
- Помечать данные как estimated / observed.
- Сохранять timestamp и source для каждой цены.

## Следующий этап после MVP-0

Если скринер покажет реальные возможности:

- добавить operator dashboard;
- добавить manual trade logging;
- добавить PnL report;
- добавить controlled execution script;
- добавить risk limits;
- только потом думать о user-facing pool.
