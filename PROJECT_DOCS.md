# Cross-Venue Prediction Arbitrage Project Reference

Локальный рабочий справочник по новой продуктовой гипотезе проекта.

Дата обновления: 2026-04-24

## 1. Что строим

Проект больше не опирается на гипотезу `YES ask + NO ask < 1.00` внутри одного рынка Polymarket. Суточный smoke-run не показал реальных торговых случаев, поэтому практический фокус переносится на cross-venue arbitrage между разными prediction-market площадками.

Новая идея:

- искать одно и то же событие на нескольких площадках;
- понимать, что названия могут отличаться, но экономический смысл может совпадать;
- сравнивать вероятности / цены `YES` и `NO` между площадками;
- находить ситуации, где покупка `YES` на одной площадке и `NO` на другой дает суммарную стоимость ниже ожидаемой выплаты `$1.00`;
- сначала отправлять сигналы оператору, а не торговать автоматически.

Дополнительная Polymarket-only гипотеза для MVP-0: implication opportunities. Ищем пары рынков внутри Polymarket, где `YES` одного почти реализованного события логически влечет `YES` другого события, но второй рынок еще торгуется заметно дешевле. Пример: `team wins match` -> `team advances to semifinal`, или `US invades Iran` -> `US bombs Iran`, если resolution rules действительно делают второе событие неизбежным следствием первого.

Первый целевой pair для MVP:

- `Polymarket`
- `Kalshi`

Причина выбора `Kalshi`: есть официальная API-документация, public market data endpoints, orderbook endpoints, WebSocket/API reference и demo environment. Это делает Kalshi лучшим вторым venue для быстрой проверки гипотезы.

`Opinion.trade` и `Predict.fun` остаются кандидатами следующего этапа:

- `Opinion.trade` имеет OpenAPI, WebSocket и CLOB SDK, но требует API key через application form.
- `Predict.fun` имеет REST API и SDK, но mainnet API key запрашивается через Discord ticket.

## 2. Основная торговая механика

Prediction market обычно торгует бинарным исходом через цену вероятности:

- `YES = 0.70` означает покупку положительного исхода за `$0.70`;
- `NO = 0.20` означает покупку отрицательного исхода за `$0.20`;
- при корректном парном хедже одна из сторон должна выплатить `$1.00`.

Cross-venue opportunity возникает, когда две площадки по-разному оценивают одно и то же событие.

Пример:

```text
Polymarket:
Will the US attack Iran before April 1?
YES 0.90 / NO 0.10

Kalshi:
Will the US begin a military operation in Iran in Q1?
YES 0.70 / NO 0.30
```

Если после проверки resolution rules это одна и та же экономическая ставка, можно рассмотреть:

```text
Buy YES on Kalshi:      0.70
Buy NO on Polymarket:   0.10
Gross cost:             0.80
Expected payout:        1.00
Gross edge:             0.20
```

Финальная формула для сигнала:

```text
yes_ask_low + no_ask_low + taker_fees + slippage + mismatch_buffer < 1.00
```

Важно: opportunity считается только наблюдаемым сигналом. Это не гарантированная прибыль и не финансовая рекомендация.

Implication opportunity возникает, когда рынок-предпосылка уже оценивается почти как реализованный, а рынок-следствие стоит дешевле:

```text
premise_yes_price - consequence_yes_ask - fees - implication_buffer > min_edge
```

Такие сигналы требуют особенно строгой проверки resolution rules: AI может предложить направление `A -> B`, но детерминированная проверка и operator review должны подтвердить, что следствие действительно обязано реализоваться.

## 3. Главная проблема: semantic event matching

События редко называются одинаково:

```text
US attacks Iran
US invades Iran
US begins a military operation in Iran
US military action against Iran before April 1
US military action against Iran in Q1
```

Строковое сравнение здесь бесполезно. Нужно определить, совпадает ли экономический смысл:

- actor: кто действует;
- action: что должно произойти;
- target: на кого / где направлено действие;
- time window: до какой даты или в каком периоде;
- resolution source: кто и как определяет исход;
- exclusions: что явно не считается событием;
- settlement mechanics: когда и по каким правилам событие закрывается.

ИИ используется именно для этой задачи: он помогает извлекать смысл, искать похожие события и объяснять различия. Но торговая математика и risk checks должны оставаться детерминированными.

## 4. AI matching model

Для каждого рынка сохраняем сырой текст:

- title;
- description;
- resolution rules;
- close time;
- settlement date;
- source / oracle;
- category;
- outcomes;
- venue URL.

AI event normalizer превращает рынок в canonical event schema:

```json
{
  "actor": "United States",
  "action": "direct military attack / military operation",
  "target": "Iran",
  "condition": "direct military action by US forces",
  "time_window": "before 2026-04-01",
  "timezone": "UTC",
  "resolution_source": "market-specific rules",
  "exclusions": ["sanctions", "verbal threats", "proxy-only actions"]
}
```

AI semantic matcher сравнивает два canonical events и возвращает structured result:

```json
{
  "match_type": "near_equivalent",
  "confidence": 0.86,
  "same_actor": true,
  "same_target": true,
  "same_action": "uncertain",
  "same_time_window": true,
  "material_differences": [
    "One market says attack, the other says invasion; rules must confirm whether airstrikes qualify."
  ],
  "operator_review_required": true
}
```

Допустимые статусы:

- `exact_equivalent`: можно мониторить автоматически после проверки;
- `near_equivalent`: нужен ручной review;
- `related_not_same`: похожая тема, но арбитраж считать нельзя;
- `different`: не матч.

Для implication matching используются отдельные статусы:

- `strict_implication`: `YES` предпосылки должен означать `YES` следствия;
- `likely_implication`: вероятная импликация, но нужен ручной review;
- `equivalent`: рынки фактически одинаковые;
- `related_no_implication`: похожие события без направленной гарантии;
- `inverse_or_conflict` / `different`: игнорировать.

## 5. Deterministic verification

ИИ не должен единолично решать, что события одинаковые. После AI matching запускается rule verifier:

- сравнивает даты и timezone;
- проверяет inclusive / exclusive deadline;
- ищет разные пороги события;
- проверяет, совпадают ли actor и target;
- проверяет, не отличается ли settlement source;
- ищет исключения в правилах;
- оценивает, не является ли одна формулировка более широкой, чем другая.

Если есть существенное отличие, opportunity не считается risk-free даже при большом spread.

## 6. Mismatch buffer

Для защиты от semantic mismatch вводится дополнительный буфер:

```text
exact_equivalent: min edge 1-2%
operator_approved_near_equivalent: min edge 5-10%
unapproved_near_equivalent: alert only as research, no trade signal
related_not_same: ignore for arbitrage
```

Буфер хранится отдельно от fees/slippage. Это цена риска, что два рынка разрешатся по-разному.

## 7. MVP-0

MVP-0 теперь означает не исполнение, а проверку трех гипотез:

1. Есть ли достаточно пар одинаковых или почти одинаковых событий между Polymarket и Kalshi.
2. Возникают ли реальные cross-venue price divergences после учета fees/slippage.
3. Можно ли reliably отличать equivalent events от просто похожих событий с помощью AI + deterministic rules + manual review.
4. Можно ли внутри Polymarket находить implication pairs, где почти реализованное событие указывает на недооцененный рынок-следствие.

Что входит:

- Polymarket market collector;
- Kalshi market collector;
- canonical event registry;
- AI event normalizer;
- semantic match engine;
- deterministic rule verifier;
- cross-venue price scanner;
- opportunity calculator;
- Telegram alerts;
- manual review status в storage.

Что не входит:

- автотрейдинг;
- пользовательские депозиты;
- публичный dashboard;
- обещания доходности;
- trading pool;
- execution без ручного подтверждения.

## 8. Data model draft

Ключевые сущности:

- `Venue`
- `RawMarket`
- `CanonicalEvent`
- `EventMatch`
- `MarketSnapshot`
- `OrderbookSnapshot`
- `CrossVenueOpportunity`
- `AIMatchingRun`
- `RuleVerificationRun`
- `OperatorReview`
- `AlertEvent`

Для каждого AI-result обязательно хранить:

- model;
- prompt version;
- input hashes;
- structured output;
- confidence;
- reasons;
- timestamp.

Это нужно для auditability и последующего анализа ошибок matching.

## 9. Recommended sources

Официальные/первичные источники для интеграций:

- Polymarket API docs: https://docs.polymarket.com/api-reference/introduction
- Kalshi API docs: https://docs.kalshi.com/
- Opinion OpenAPI docs: https://docs.opinion.trade/developer-guide/opinion-open-api/overview
- Predict REST API docs: https://docs.predict.fun/developers/predict-rest-api
- OpenAI Responses API: https://platform.openai.com/docs/api-reference/responses
- OpenAI tools guide: https://platform.openai.com/docs/guides/tools

## 10. Security and operations notes

- API keys must never be committed to git.
- OpenAI key must be stored as `OPENAI_API_KEY` in `.env` locally and secret manager in deployment.
- Any key pasted into chat or logs should be treated as compromised and rotated.
- Trading credentials must be separated per venue and per environment.
- AI output is advisory; deterministic checks and operator approval gate tradeability.
- All signals are observed opportunities, not guaranteed profit.
