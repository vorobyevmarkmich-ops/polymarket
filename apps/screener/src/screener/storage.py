from __future__ import annotations

import sqlite3
from pathlib import Path

from screener.models import Market, Opportunity


class Storage:
    def __init__(self, database_url: str) -> None:
        if not database_url.startswith("sqlite:///"):
            raise ValueError("MVP-0 storage currently supports sqlite:/// URLs only.")
        self.path = Path(database_url.removeprefix("sqlite:///")).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self._conn.close()

    def init(self) -> None:
        self._conn.executescript(
            """
            create table if not exists markets (
              id text primary key,
              question text not null,
              slug text not null,
              url text not null,
              yes_token_id text not null,
              no_token_id text not null,
              liquidity text not null,
              volume text not null,
              accepting_orders integer not null,
              active integer not null,
              closed integer not null,
              updated_at text,
              seen_at text not null
            );

            create table if not exists opportunities (
              id integer primary key autoincrement,
              market_id text not null,
              yes_ask text not null,
              no_ask text not null,
              total_cost text not null,
              spread text not null,
              spread_bps integer not null,
              estimated_size_usd text not null,
              detected_at text not null,
              unique_key text not null
            );

            create index if not exists idx_opportunities_market_detected
              on opportunities (market_id, detected_at);

            create table if not exists alert_history (
              opportunity_key text primary key,
              market_id text not null,
              sent_at text not null
            );
            """
        )
        self._conn.commit()

    def upsert_markets(self, markets: list[Market]) -> None:
        rows = [
            (
                market.id,
                market.question,
                market.slug,
                market.url,
                market.yes_token_id,
                market.no_token_id,
                str(market.liquidity),
                str(market.volume),
                int(market.accepting_orders),
                int(market.active),
                int(market.closed),
                market.updated_at,
                "CURRENT_TIMESTAMP",
            )
            for market in markets
        ]
        self._conn.executemany(
            """
            insert into markets (
              id, question, slug, url, yes_token_id, no_token_id, liquidity, volume,
              accepting_orders, active, closed, updated_at, seen_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            on conflict(id) do update set
              question = excluded.question,
              slug = excluded.slug,
              url = excluded.url,
              yes_token_id = excluded.yes_token_id,
              no_token_id = excluded.no_token_id,
              liquidity = excluded.liquidity,
              volume = excluded.volume,
              accepting_orders = excluded.accepting_orders,
              active = excluded.active,
              closed = excluded.closed,
              updated_at = excluded.updated_at,
              seen_at = datetime('now')
            """,
            [row[:-1] for row in rows],
        )
        self._conn.commit()

    def save_opportunity(self, opportunity: Opportunity) -> None:
        self._conn.execute(
            """
            insert into opportunities (
              market_id, yes_ask, no_ask, total_cost, spread, spread_bps,
              estimated_size_usd, detected_at, unique_key
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                opportunity.market.id,
                str(opportunity.yes_ask),
                str(opportunity.no_ask),
                str(opportunity.total_cost),
                str(opportunity.spread),
                opportunity.spread_bps,
                str(opportunity.estimated_size_usd),
                opportunity.detected_at.isoformat(),
                opportunity.key,
            ),
        )
        self._conn.commit()

    def should_alert(self, opportunity: Opportunity, cooldown_seconds: int) -> bool:
        row = self._conn.execute(
            """
            select 1
            from alert_history
            where market_id = ?
              and sent_at > datetime('now', ?)
            """,
            (opportunity.market.id, f"-{cooldown_seconds} seconds"),
        ).fetchone()
        return row is None

    def mark_alert_sent(self, opportunity: Opportunity) -> None:
        self._conn.execute(
            """
            insert into alert_history (opportunity_key, market_id, sent_at)
            values (?, ?, datetime('now'))
            on conflict(opportunity_key) do update set
              sent_at = excluded.sent_at
            """,
            (opportunity.key, opportunity.market.id),
        )
        self._conn.commit()
