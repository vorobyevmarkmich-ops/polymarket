from __future__ import annotations

import os
from pathlib import Path


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def _load_dotenv(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


class Settings:
    def __init__(self) -> None:
        _load_dotenv()
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.telegram_disable_web_page_preview = _bool("TELEGRAM_DISABLE_WEB_PAGE_PREVIEW", True)
        self.log_market_samples = _bool("LOG_MARKET_SAMPLES", True)
        self.log_top_candidates = _bool("LOG_TOP_CANDIDATES", True)

        self.polymarket_gamma_api_base = os.getenv(
            "POLYMARKET_GAMMA_API_BASE",
            "https://gamma-api.polymarket.com",
        )
        self.polymarket_clob_api_base = os.getenv(
            "POLYMARKET_CLOB_API_BASE",
            "https://clob.polymarket.com",
        )
        self.kalshi_api_base = os.getenv(
            "KALSHI_API_BASE",
            "https://api.elections.kalshi.com/trade-api/v2",
        )
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.use_openai_matcher = _bool("USE_OPENAI_MATCHER", bool(self.openai_api_key))

        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./screener.sqlite3")

        self.min_spread_bps = _int("MIN_SPREAD_BPS", 50)
        self.min_size_usd = _float("MIN_SIZE_USD", 10)
        self.active_market_scan_interval_seconds = _float(
            "ACTIVE_MARKET_SCAN_INTERVAL_SECONDS",
            120,
        )
        self.market_discovery_interval_seconds = _float("MARKET_DISCOVERY_INTERVAL_SECONDS", 60)
        self.alert_cooldown_seconds = _int("ALERT_COOLDOWN_SECONDS", 300)
        self.alert_min_interval_seconds = _float("ALERT_MIN_INTERVAL_SECONDS", 0)
        self.max_alerts_per_cycle = max(1, _int("MAX_ALERTS_PER_CYCLE", 3))
        self.max_price_staleness_seconds = _int("MAX_PRICE_STALENESS_SECONDS", 5)

        self.gamma_page_limit = max(1, min(_int("GAMMA_PAGE_LIMIT", 200), 1000))
        self.max_markets_per_discovery = max(1, _int("MAX_MARKETS_PER_DISCOVERY", 5000))
        self.clob_price_batch_size = max(1, min(_int("CLOB_PRICE_BATCH_SIZE", 250), 500))
        self.log_market_sample_size = max(0, min(_int("LOG_MARKET_SAMPLE_SIZE", 5), 20))
        self.log_top_candidates_limit = max(0, min(_int("LOG_TOP_CANDIDATES_LIMIT", 5), 20))
        self.log_top_candidates_every_cycles = max(1, _int("LOG_TOP_CANDIDATES_EVERY_CYCLES", 6))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        self.kalshi_market_limit = max(1, min(_int("KALSHI_MARKET_LIMIT", 1000), 1000))
        self.kalshi_max_pages = max(1, min(_int("KALSHI_MAX_PAGES", 3), 20))
        self.kalshi_include_multileg = _bool("KALSHI_INCLUDE_MULTILEG", False)
        self.cross_venue_max_polymarket_markets = max(1, _int("CROSS_VENUE_MAX_POLYMARKET_MARKETS", 1000))
        self.cross_venue_max_kalshi_markets = max(1, _int("CROSS_VENUE_MAX_KALSHI_MARKETS", 500))
        self.cross_venue_max_candidates = max(1, _int("CROSS_VENUE_MAX_CANDIDATES", 50))
        self.cross_venue_min_match_score = _float("CROSS_VENUE_MIN_MATCH_SCORE", 0.07)
        self.cross_venue_min_exact_score = _float("CROSS_VENUE_MIN_EXACT_SCORE", 0.72)
        self.cross_venue_min_net_edge_bps = _int("MIN_NET_EDGE_BPS", 200)
        self.cross_venue_fee_bps = _int("CROSS_VENUE_FEE_BPS", 0)
        self.exact_match_mismatch_buffer_bps = _int("EXACT_MATCH_MISMATCH_BUFFER_BPS", 100)
        self.near_match_mismatch_buffer_bps = _int("NEAR_MATCH_MISMATCH_BUFFER_BPS", 500)
        self.allow_near_match_opportunities = _bool("ALLOW_NEAR_MATCH_OPPORTUNITIES", True)
        self.log_cross_venue_candidates = _bool("LOG_CROSS_VENUE_CANDIDATES", True)
        self.log_cross_venue_rejections = _bool("LOG_CROSS_VENUE_REJECTIONS", True)

        self.implication_max_markets = max(1, _int("IMPLICATION_MAX_MARKETS", 1000))
        self.implication_max_candidates = max(1, _int("IMPLICATION_MAX_CANDIDATES", 20))
        self.implication_min_match_score = _float("IMPLICATION_MIN_MATCH_SCORE", 0.18)
        self.implication_min_anchor_yes_bps = _int("IMPLICATION_MIN_ANCHOR_YES_BPS", 8500)
        self.implication_min_edge_bps = _int("IMPLICATION_MIN_EDGE_BPS", 200)
        self.implication_buffer_bps = _int("IMPLICATION_BUFFER_BPS", 200)
        self.implication_fee_bps = _int("IMPLICATION_FEE_BPS", 0)
        self.allow_heuristic_implications = _bool("ALLOW_HEURISTIC_IMPLICATIONS", False)
        self.log_implication_candidates = _bool("LOG_IMPLICATION_CANDIDATES", True)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def min_spread(self) -> float:
        return self.min_spread_bps / 10_000


def load_settings() -> Settings:
    return Settings()
