# Deployment

This project is prepared to run the MVP-0 Polymarket screener as a Railway worker.

## Runtime

- Docker image based on `python:3.12-slim`
- Start command: `python -m screener.main`
- Working app: `apps/screener`
- No web port is required because this is a background worker.

## Required Railway Variables

```bash
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
POLYMARKET_GAMMA_API_BASE=https://gamma-api.polymarket.com
POLYMARKET_CLOB_API_BASE=https://clob.polymarket.com
DATABASE_URL=sqlite:///./screener.sqlite3
MIN_SPREAD_BPS=1
MIN_SIZE_USD=10
ACTIVE_MARKET_SCAN_INTERVAL_SECONDS=2
MARKET_DISCOVERY_INTERVAL_SECONDS=60
ALERT_COOLDOWN_SECONDS=300
ALERT_MIN_INTERVAL_SECONDS=0
MAX_ALERTS_PER_CYCLE=3
MAX_PRICE_STALENESS_SECONDS=5
GAMMA_PAGE_LIMIT=200
MAX_MARKETS_PER_DISCOVERY=1000
CLOB_PRICE_BATCH_SIZE=250
LOG_LEVEL=INFO
LOG_MARKET_SAMPLES=true
LOG_MARKET_SAMPLE_SIZE=5
LOG_TOP_CANDIDATES=true
LOG_TOP_CANDIDATES_LIMIT=5
LOG_TOP_CANDIDATES_EVERY_CYCLES=6
TELEGRAM_DISABLE_WEB_PAGE_PREVIEW=true
```

## Notes

- The worker does not execute trades.
- The worker does not accept deposits or withdrawals.
- Keep `MIN_SPREAD_BPS` positive for real signals. It is applied to net spread after estimated Polymarket taker fees.
- The screener fetches CLOB fee rates dynamically and estimates `net_spread = 1 - yes_ask - no_ask - yes_fee - no_fee`.
- `MAX_ALERTS_PER_CYCLE` and `ALERT_MIN_INTERVAL_SECONDS` protect Telegram from alert floods.
- With `LOG_TOP_CANDIDATES=true`, logs include the closest markets by `YES ask + NO ask`, so it is visible why a cycle did or did not produce a signal.
- SQLite is acceptable for the first smoke deployment, but Railway filesystem persistence may be ephemeral. Move to Postgres after initial validation.
- Keep secrets in Railway Variables only. Do not commit `.env`.
