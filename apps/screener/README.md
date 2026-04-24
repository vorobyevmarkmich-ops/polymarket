# Cross-Venue Screener

This app currently contains the legacy Polymarket-only MVP worker. It discovers active Polymarket markets, checks the old `YES ask + NO ask < 1.00` condition, stores opportunities, and sends Telegram alerts.

The project direction has changed. The target MVP is now a cross-venue prediction-market screener:

- Polymarket + Kalshi first;
- AI semantic event matching;
- deterministic rule verification;
- cross-venue `YES` / `NO` opportunity detection;
- Telegram alerts for operator review.

See [MVP_0_SCREENER.md](/Users/markvorobev/Documents/Codex/Pumpfun/MVP_0_SCREENER.md) for the new plan.

## Legacy Run

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

One-shot cross-venue run:

```bash
PYTHONPATH=src python3 -m screener.main --once --cross-venue
```

Run the Polymarket implication scanner as part of the one-shot pass:

```bash
PYTHONPATH=src python3 -m screener.main --once --implications
```

The implication scanner looks for directional relationships inside Polymarket, for example
`team wins match -> team advances`, then checks whether the consequence `YES` price is still
materially cheaper than the nearly-resolved premise market after a risk buffer. AI classification is
recommended; without `OPENAI_API_KEY` it logs overlap candidates but does not treat them as trade
candidates unless `ALLOW_HEURISTIC_IMPLICATIONS=true`.

## Required Telegram env

```bash
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

If Telegram values are empty, the screener still runs and logs opportunities without sending messages.
Legacy Polymarket, cross-venue, and implication signals all use the same Telegram settings and alert cooldown.

## Safety

- No auto-trading.
- No deposits.
- No withdrawals.
- Signals are observed opportunities, not guaranteed profit.
- Do not store OpenAI or venue API keys in git.
