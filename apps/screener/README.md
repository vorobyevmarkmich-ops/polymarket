# Polymarket Screener

MVP-0 worker that discovers active Polymarket markets, checks `YES ask + NO ask < 1.00`, stores opportunities, and sends Telegram alerts.

## Run

```bash
cd /Users/markvorobev/Documents/Codex/Pumpfun/apps/screener
cp .env.example .env
python3 -m screener.main
```

If using a source checkout directly:

```bash
PYTHONPATH=src python3 -m screener.main
```

One-shot smoke run:

```bash
PYTHONPATH=src python3 -m screener.main --once
```

## Required Telegram env

```bash
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

If Telegram values are empty, the screener still runs and logs opportunities without sending messages.

## Safety

- No auto-trading.
- No deposits.
- No withdrawals.
- Signals are observed opportunities, not guaranteed profit.
