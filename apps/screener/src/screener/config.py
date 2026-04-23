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

        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./screener.sqlite3")

        self.min_spread_bps = _int("MIN_SPREAD_BPS", 50)
        self.min_size_usd = _float("MIN_SIZE_USD", 10)
        self.active_market_scan_interval_seconds = _float(
            "ACTIVE_MARKET_SCAN_INTERVAL_SECONDS",
            2,
        )
        self.market_discovery_interval_seconds = _float("MARKET_DISCOVERY_INTERVAL_SECONDS", 60)
        self.alert_cooldown_seconds = _int("ALERT_COOLDOWN_SECONDS", 300)
        self.max_price_staleness_seconds = _int("MAX_PRICE_STALENESS_SECONDS", 5)

        self.gamma_page_limit = max(1, min(_int("GAMMA_PAGE_LIMIT", 200), 1000))
        self.max_markets_per_discovery = max(1, _int("MAX_MARKETS_PER_DISCOVERY", 1000))
        self.clob_price_batch_size = max(1, min(_int("CLOB_PRICE_BATCH_SIZE", 250), 500))
        self.log_market_sample_size = max(0, min(_int("LOG_MARKET_SAMPLE_SIZE", 5), 20))
        self.log_top_candidates_limit = max(0, min(_int("LOG_TOP_CANDIDATES_LIMIT", 5), 20))
        self.log_top_candidates_every_cycles = max(1, _int("LOG_TOP_CANDIDATES_EVERY_CYCLES", 6))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def min_spread(self) -> float:
        return self.min_spread_bps / 10_000


def load_settings() -> Settings:
    return Settings()
