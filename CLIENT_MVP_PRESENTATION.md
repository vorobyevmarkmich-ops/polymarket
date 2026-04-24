# Cross-Venue Prediction Arbitrage MVP: мини-презентация

## 1. Что мы делаем

Мы перестраиваем MVP из Polymarket-only скринера в cross-venue screener, который сравнивает одинаковые события на разных prediction-market площадках.

Первый фокус: `Polymarket + Kalshi`.

Система ищет ситуации, где одно и то же событие на разных площадках торгуется с заметно разными вероятностями.

## 2. Какую проблему решает

На prediction markets одно и то же событие может появляться на нескольких площадках, но с разными формулировками и разными ценами.

Пример:

```text
Polymarket: Will the US attack Iran before April 1?
Kalshi: Will the US begin military action in Iran in Q1?
```

Для человека это похоже на одно и то же событие, но вручную отслеживать сотни таких пар невозможно. Кроме того, простое сравнение названий не работает: wording, дедлайны и resolution rules могут отличаться.

## 3. Как работает MVP

MVP собирает рынки с Polymarket и Kalshi, нормализует их в canonical event format, использует ИИ для semantic matching, затем прогоняет deterministic rule checks.

Если события подтверждены как одинаковые или близкие, система сравнивает цены:

```text
Buy YES on venue A + Buy NO on venue B + fees + slippage + mismatch buffer < 1.00
```

Если edge остается положительным, оператор получает Telegram alert.

## 4. Что получает клиент

Клиент получает не обещание доходности, а исследовательский и операционный инструмент:

- discovery одинаковых событий между площадками;
- AI-explanation, почему события совпадают или отличаются;
- расчет cross-venue расхождения;
- оценку fees, slippage и semantic mismatch buffer;
- Telegram alerts для ручного review.

## 5. Почему нужен ИИ

События могут называться по-разному, но значить одно и то же:

- `US attacks Iran`
- `US invades Iran`
- `US begins military operation in Iran`
- `US military action in Iran in Q1`

ИИ нужен для извлечения смысла: actor, action, target, deadline, resolution source и exclusions.

Но финальный edge считает обычный код, а спорные пары требуют manual review.

## 6. Как на этом зарабатывать

Возможные модели монетизации:

- приватный Telegram-канал cross-venue сигналов;
- subscription для профессиональных prediction-market трейдеров;
- operator dashboard с историей и review queue;
- аналитика по расхождениям между площадками;
- later: controlled execution для проверенных approved pairs.

## 7. Почему это ценно уже сейчас

MVP не требует пользовательских депозитов, не исполняет сделки автоматически и не несет custody-risk.

Он позволяет быстро проверить, существуют ли реальные cross-venue opportunities и насколько надежно можно matching-ить события между площадками.

## 8. Следующий этап

После подтверждения гипотезы:

- refactor текущего `apps/screener` под venue adapters;
- добавить Kalshi collector;
- добавить OpenAI-based semantic matcher;
- добавить storage для AI runs и operator review;
- добавить paper-trading / manual trade logging;
- позже рассмотреть Opinion.trade и Predict.fun.

## Disclaimer

Это аналитический и исследовательский инструмент. Сигналы не являются финансовой рекомендацией, не гарантируют прибыль и не означают автоматическую исполнимость сделки.

