from __future__ import annotations

import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from redis import Redis

LOGGER = logging.getLogger("redis-mcp")

REDIS_URL_ENV = "REDIS_MCP_URL"
DEFAULT_SCAN_COUNT = 100
DEFAULT_RESULT_LIMIT = 100

mcp = FastMCP("redis-mcp", json_response=True)


def _redis_url() -> str:
    url = os.getenv(REDIS_URL_ENV)
    if not url:
        raise ValueError(
            f"{REDIS_URL_ENV} is not set. Configure a Redis URL before using redis-mcp."
        )
    return url


def _client() -> Redis:
    return Redis.from_url(_redis_url(), decode_responses=True)


def _limit(value: int, max_value: int = 1000) -> int:
    if value < 1:
        return 1
    return min(value, max_value)


@mcp.tool()
def redis_healthcheck() -> dict[str, Any]:
    """Ping Redis and return basic server info."""
    client = _client()
    pong = client.ping()
    info = client.info("server")
    return {
        "ping": pong,
        "redis_version": info.get("redis_version"),
        "process_id": info.get("process_id"),
        "tcp_port": info.get("tcp_port"),
    }


@mcp.tool()
def redis_info(section: str = "server") -> dict[str, Any]:
    """Return Redis INFO for a given section."""
    return dict(_client().info(section))


@mcp.tool()
def scan_keys(pattern: str = "*", limit: int = 100) -> dict[str, Any]:
    """Scan keys safely using SCAN, returning up to limit keys."""
    capped_limit = _limit(limit)
    client = _client()
    cursor = 0
    results: list[str] = []

    while True:
        cursor, batch = client.scan(cursor=cursor, match=pattern, count=DEFAULT_SCAN_COUNT)
        results.extend(batch)
        if len(results) >= capped_limit or cursor == 0:
            break

    return {
        "pattern": pattern,
        "count": min(len(results), capped_limit),
        "keys": results[:capped_limit],
    }


@mcp.tool()
def get_key_type(key: str) -> dict[str, Any]:
    """Return the Redis type and TTL for a key."""
    client = _client()
    return {
        "key": key,
        "type": client.type(key),
        "ttl": client.ttl(key),
        "exists": bool(client.exists(key)),
    }


@mcp.tool()
def get_string_value(key: str, max_chars: int = 10000) -> dict[str, Any]:
    """Read a string key safely."""
    client = _client()
    value = client.get(key)
    if value is None:
        return {"key": key, "exists": False}
    text = str(value)
    return {
        "key": key,
        "exists": True,
        "value": text[:max_chars],
        "truncated": len(text) > max_chars,
    }


@mcp.tool()
def get_list_items(key: str, limit: int = 50) -> dict[str, Any]:
    """Read items from a Redis list."""
    capped_limit = _limit(limit)
    client = _client()
    items = client.lrange(key, 0, capped_limit - 1)
    return {"key": key, "count": len(items), "items": items}


@mcp.tool()
def get_hash_fields(key: str, limit: int = 100) -> dict[str, Any]:
    """Read fields from a Redis hash."""
    capped_limit = _limit(limit)
    client = _client()
    data = client.hgetall(key)
    items = list(data.items())[:capped_limit]
    return {"key": key, "count": len(items), "fields": dict(items)}


@mcp.tool()
def get_set_members(key: str, limit: int = 100) -> dict[str, Any]:
    """Read members from a Redis set."""
    capped_limit = _limit(limit)
    client = _client()
    members = sorted(client.smembers(key))
    return {"key": key, "count": min(len(members), capped_limit), "members": members[:capped_limit]}


@mcp.tool()
def get_sorted_set_members(key: str, limit: int = 100) -> dict[str, Any]:
    """Read members from a Redis sorted set with scores."""
    capped_limit = _limit(limit)
    client = _client()
    members = client.zrange(key, 0, capped_limit - 1, withscores=True)
    return {
        "key": key,
        "count": len(members),
        "members": [{"member": member, "score": score} for member, score in members],
    }


@mcp.tool()
def list_expected_queue_names() -> list[dict[str, str]]:
    """Return the expected queue names for the planned project architecture."""
    return [
        {"queue": "deposit_processing", "domain": "money-movement"},
        {"queue": "withdraw_processing", "domain": "money-movement"},
        {"queue": "trade_execution", "domain": "trading"},
        {"queue": "trade_settlement", "domain": "trading"},
        {"queue": "reconciliation", "domain": "ops"},
        {"queue": "notifications", "domain": "messaging"},
        {"queue": "risk_checks", "domain": "risk"},
    ]


@mcp.prompt()
def redis_investigation_prompt(goal: str) -> str:
    """Generate a prompt for investigating Redis state safely."""
    return f"""You are investigating Redis state for this project.

Goal: {goal}

Rules:
- Use read-only inspection only.
- Prefer INFO, key discovery, and queue/state inspection.
- Do not mutate keys, clear queues, or acknowledge jobs from MCP.
- Treat Redis as operational state, not the source of truth for balances.
"""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    LOGGER.info("Starting redis-mcp with transport=%s", transport)
    mcp.run(transport=transport)
