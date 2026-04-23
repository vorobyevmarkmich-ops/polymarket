---
name: telegram-mini-app
description: Use when building or reviewing the Telegram Mini App user experience in this project, including onboarding, balance views, deposit and withdrawal flows, dashboard interaction, notifications, and mobile-first UX constraints.
---

# Telegram Mini App

Use this skill when the task touches the Telegram Mini App experience or Telegram-linked user flows.

## Read first

- [PROJECT_DOCS.md](../../PROJECT_DOCS.md)
- [STACK.md](../../STACK.md)
- [agents.md](../../agents.md)

## What this skill covers

- onboarding
- dashboard UX
- deposit flow
- withdrawal flow
- real-time stats presentation
- Telegram-friendly constraints

## Product flow anchors

- launch app
- connect / identify user
- show balance and pool status
- deposit
- monitor stats
- withdraw
- receive notifications

## UX rules

- Assume mobile-first layout.
- Keep critical actions obvious and low-friction.
- Surface status clearly for pending, confirmed, failed, and paused states.
- Treat money-moving actions as high-trust flows: clarity beats novelty.
- Use concise copy and avoid overpromising financial outcomes.

## Integration rules

- UI should read from `backend-api`, not from trading workers directly.
- Show derived state only when it is backed by reliable backend data.
- Distinguish estimated metrics from confirmed balances.
- Preserve clear error states for bridge, wallet, and external dependency failures.

## Good defaults

- strong status labels
- explicit pending states
- visible timestamps for important balance-affecting events
- clear retry / support / incident messaging when needed
