from __future__ import annotations

import sqlite3
from pathlib import Path

from screener.cross_venue import CrossVenueOpportunity
from screener.implications import ImplicationOpportunity
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
              fees_enabled integer not null default 0,
              fee_type text,
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

            create table if not exists cross_venue_opportunities (
              id integer primary key autoincrement,
              polymarket_id text not null,
              kalshi_ticker text not null,
              match_type text not null,
              match_score real not null,
              direction text not null,
              buy_yes_venue text not null,
              buy_yes_price text not null,
              buy_no_venue text not null,
              buy_no_price text not null,
              total_cost text not null,
              estimated_fees text not null,
              mismatch_buffer text not null,
              net_edge text not null,
              net_edge_bps integer not null,
              reason text not null,
              detected_at text not null
            );

            create index if not exists idx_cross_venue_opportunities_detected
              on cross_venue_opportunities (detected_at);

            create table if not exists implication_opportunities (
              id integer primary key autoincrement,
              premise_market_id text not null,
              consequence_market_id text not null,
              relation_type text not null,
              match_score real not null,
              premise_yes_price text not null,
              consequence_yes_ask text not null,
              estimated_fees text not null,
              implication_buffer text not null,
              net_edge text not null,
              net_edge_bps integer not null,
              reason text not null,
              detected_at text not null
            );

            create index if not exists idx_implication_opportunities_detected
              on implication_opportunities (detected_at);
            """
        )
        self._ensure_column("markets", "fees_enabled", "integer not null default 0")
        self._ensure_column("markets", "fee_type", "text")
        self._conn.commit()

    def save_implication_opportunity(self, opportunity: ImplicationOpportunity) -> None:
        candidate = opportunity.candidate
        self._conn.execute(
            """
            insert into implication_opportunities (
              premise_market_id, consequence_market_id, relation_type, match_score,
              premise_yes_price, consequence_yes_ask, estimated_fees, implication_buffer,
              net_edge, net_edge_bps, reason, detected_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                candidate.premise.id,
                candidate.consequence.id,
                candidate.relation_type,
                candidate.score,
                str(opportunity.premise_yes_price),
                str(opportunity.consequence_yes_ask),
                str(opportunity.estimated_fees),
                str(opportunity.implication_buffer),
                str(opportunity.net_edge),
                opportunity.net_edge_bps,
                candidate.reason,
            ),
        )
        self._conn.commit()

    def save_cross_venue_opportunity(self, opportunity: CrossVenueOpportunity) -> None:
        candidate = opportunity.candidate
        self._conn.execute(
            """
            insert into cross_venue_opportunities (
              polymarket_id, kalshi_ticker, match_type, match_score, direction,
              buy_yes_venue, buy_yes_price, buy_no_venue, buy_no_price,
              total_cost, estimated_fees, mismatch_buffer, net_edge, net_edge_bps,
              reason, detected_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                candidate.polymarket.id,
                candidate.kalshi.ticker,
                candidate.match_type,
                candidate.score,
                opportunity.direction,
                opportunity.buy_yes_venue,
                str(opportunity.buy_yes_price),
                opportunity.buy_no_venue,
                str(opportunity.buy_no_price),
                str(opportunity.total_cost),
                str(opportunity.estimated_fees),
                str(opportunity.mismatch_buffer),
                str(opportunity.net_edge),
                opportunity.net_edge_bps,
                candidate.reason,
            ),
        )
        self._conn.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        columns = self._conn.execute(f"pragma table_info({table})").fetchall()
        if any(row["name"] == column for row in columns):
            return
        self._conn.execute(f"alter table {table} add column {column} {definition}")

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
                int(market.fees_enabled),
                market.fee_type,
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
              fees_enabled, fee_type, accepting_orders, active, closed, updated_at, seen_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            on conflict(id) do update set
              question = excluded.question,
              slug = excluded.slug,
              url = excluded.url,
              yes_token_id = excluded.yes_token_id,
              no_token_id = excluded.no_token_id,
              liquidity = excluded.liquidity,
              volume = excluded.volume,
              fees_enabled = excluded.fees_enabled,
              fee_type = excluded.fee_type,
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
        return self.should_alert_key(
            market_id=opportunity.market.id,
            cooldown_seconds=cooldown_seconds,
        )

    def should_alert_key(self, market_id: str, cooldown_seconds: int) -> bool:
        row = self._conn.execute(
            """
            select 1
            from alert_history
            where market_id = ?
              and sent_at > datetime('now', ?)
            """,
            (market_id, f"-{cooldown_seconds} seconds"),
        ).fetchone()
        return row is None

    def mark_alert_sent(self, opportunity: Opportunity) -> None:
        self.mark_alert_key(opportunity.key, opportunity.market.id)

    def mark_alert_key(self, opportunity_key: str, market_id: str) -> None:
        self._conn.execute(
            """
            insert into alert_history (opportunity_key, market_id, sent_at)
            values (?, ?, datetime('now'))
            on conflict(opportunity_key) do update set
              sent_at = excluded.sent_at
            """,
            (opportunity_key, market_id),
        )
        self._conn.commit()
