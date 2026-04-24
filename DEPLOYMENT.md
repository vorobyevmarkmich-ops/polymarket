# Deployment

This project currently has a deployable legacy Polymarket-only worker. The product direction has changed to cross-venue prediction-market arbitrage, so this deployment doc should be treated as transitional until the new `Polymarket + Kalshi` screener is implemented.

## Current Legacy Runtime

- Docker image based on `python:3.12-slim`
- Start command: `python -m screener.main`
- Working app: `apps/screener`
- No web port is required because this is a background worker.

## Current Legacy Railway Variables

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

## Target Cross-Venue Variables

Expected additional variables for the new MVP:

```bash
OPENAI_API_KEY=
KALSHI_API_BASE=https://api.elections.kalshi.com/trade-api/v2
MIN_NET_EDGE_BPS=300
MIN_EXACT_MATCH_CONFIDENCE=0.88
MIN_NEAR_MATCH_CONFIDENCE=0.75
EXACT_MATCH_MISMATCH_BUFFER_BPS=100
NEAR_MATCH_MISMATCH_BUFFER_BPS=500
PRICE_SCAN_INTERVAL_SECONDS=2
```

## Notes

- The worker must not execute trades in MVP-0.
- The worker must not accept deposits or withdrawals.
- Current legacy signals are Polymarket-only and do not validate the new cross-venue hypothesis.
- New cross-venue signals must include semantic match status, confidence, material differences and mismatch buffer.
- SQLite is acceptable for smoke validation, but Postgres is preferred once AI runs and operator reviews are stored.
- Keep secrets in Railway Variables only. Do not commit `.env`.
- Any API key pasted into chat or logs should be considered compromised and rotated.

