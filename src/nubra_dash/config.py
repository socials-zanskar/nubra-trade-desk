"""Configuration helpers for the Nubra Streamlit dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Final


DEFAULT_APP_NAME: Final[str] = "Nubra Signal Discovery Dashboard"
DEFAULT_TIMEZONE: Final[str] = "Asia/Kolkata"
DEFAULT_ENVIRONMENT: Final[str] = "PROD"
DEFAULT_EXCHANGE: Final[str] = "NSE"
DEFAULT_LOOKBACK_DAYS: Final[int] = 10
DEFAULT_BREAKOUT_RANK: Final[int] = 20
DEFAULT_REFRESH_SECONDS: Final[int] = 45
DEFAULT_MULTI_WALL_TOP_N: Final[int] = 3
DEFAULT_VOLUME_INTERVAL: Final[str] = "5m"
DEFAULT_DEMO_SYMBOLS: Final[tuple[str, ...]] = (
    "RELIANCE",
    "HDFCBANK",
    "ICICIBANK",
    "INFY",
    "TCS",
    "SBIN",
    "AXISBANK",
    "BAJFINANCE",
    "TATAMOTORS",
    "ADANIENT",
    "MARUTI",
    "ULTRACEMCO",
)
INDICES_SYMBOLS: Final[tuple[str, ...]] = (
    "NIFTY",
    "BANKNIFTY",
    "FINNIFTY",
)
INDEX_WALL_SYMBOLS: Final[tuple[str, ...]] = (
    "NIFTY",
    "SENSEX",
)
TOP_FNO_SYMBOLS: Final[tuple[str, ...]] = (
    "RELIANCE",
    "HDFCBANK",
    "ICICIBANK",
    "INFY",
    "TCS",
    "SBIN",
    "AXISBANK",
    "BAJFINANCE",
    "TATAMOTORS",
    "MARUTI",
    "SUNPHARMA",
    "BHARTIARTL",
    "LT",
    "KOTAKBANK",
    "HCLTECH",
    "ADANIENT",
    "ADANIPORTS",
    "ULTRACEMCO",
    "HINDALCO",
    "NTPC",
    "ONGC",
    "POWERGRID",
    "TITAN",
    "ASIANPAINT",
)
LIQUID_STOCKS_SYMBOLS: Final[tuple[str, ...]] = (
    "RELIANCE",
    "HDFCBANK",
    "ICICIBANK",
    "INFY",
    "TCS",
    "SBIN",
    "AXISBANK",
    "BAJFINANCE",
    "TATAMOTORS",
    "ADANIENT",
    "ADANIPORTS",
    "LT",
    "KOTAKBANK",
    "MARUTI",
    "SUNPHARMA",
    "BHARTIARTL",
    "HCLTECH",
    "ULTRACEMCO",
    "HINDALCO",
    "NTPC",
    "ONGC",
    "POWERGRID",
    "TITAN",
    "ASIANPAINT",
    "COALINDIA",
    "JSWSTEEL",
    "INDUSINDBK",
    "TECHM",
    "M&M",
    "BAJAJFINSV",
    "TATASTEEL",
    "WIPRO",
    "NESTLEIND",
    "GRASIM",
    "CIPLA",
    "HEROMOTOCO",
    "EICHERMOT",
    "BEL",
    "SHRIRAMFIN",
    "DRREDDY",
)
BASKET_PRESETS: Final[dict[str, tuple[str, ...]]] = {
    "Top FNO Stocks": TOP_FNO_SYMBOLS,
    "Indices": INDICES_SYMBOLS,
    "Liquid Stocks": LIQUID_STOCKS_SYMBOLS,
    "Custom": (),
}

ENV_APP_ENVIRONMENT: Final[str] = "NUBRA_APP_ENV"
ENV_NUBRA_ENVIRONMENT: Final[str] = "NUBRA_OI_WALLS_ENV"
ENV_SUPABASE_URL: Final[str] = "SUPABASE_URL"
ENV_SUPABASE_SECRET_KEY: Final[str] = "SUPABASE_SECRET_KEY"
ENV_SUPABASE_DB_URL: Final[str] = "SUPABASE_DB_URL"
ENV_SUPABASE_DB_HOST: Final[str] = "SUPABASE_DB_HOST"
ENV_SUPABASE_DB_PORT: Final[str] = "SUPABASE_DB_PORT"
ENV_SUPABASE_DB_NAME: Final[str] = "SUPABASE_DB_NAME"
ENV_SUPABASE_DB_USER: Final[str] = "SUPABASE_DB_USER"
ENV_SUPABASE_DB_PASSWORD: Final[str] = "SUPABASE_DB_PASSWORD"
ENV_SCAN_BATCH_SIZE: Final[str] = "SCAN_BATCH_SIZE"
ENV_SCAN_REFRESH_MINUTES: Final[str] = "SCAN_REFRESH_MINUTES"
ENV_SCAN_SYMBOL_SOURCE: Final[str] = "SCAN_SYMBOL_SOURCE"
ENV_SCAN_SECTORS: Final[str] = "SCAN_SECTORS"
ENV_SCAN_SYMBOLS_CSV: Final[str] = "SCAN_SYMBOLS_CSV"
ENV_STREAMLIT_CACHE_SECONDS: Final[str] = "STREAMLIT_CACHE_SECONDS"
ENV_ENABLE_ADMIN_REFRESH: Final[str] = "NUBRA_ENABLE_ADMIN_REFRESH"
ENV_ENABLE_LIVE_DRILLDOWN: Final[str] = "NUBRA_ENABLE_LIVE_DRILLDOWN"


@dataclass(frozen=True, slots=True)
class AuthConfig:
    """Session or demo credentials for Nubra."""

    mode: str = "demo"
    environment: str = DEFAULT_ENVIRONMENT
    use_env_creds: bool = True
    username: str | None = None
    password: str | None = None
    api_key: str | None = None
    api_secret: str | None = None
    access_token: str | None = None
    extra: dict[str, str] = field(default_factory=dict)

    def resolved_environment(self) -> str:
        return self.environment.strip().upper() or DEFAULT_ENVIRONMENT


@dataclass(frozen=True, slots=True)
class ScanConfig:
    """Runtime defaults for scan pages and services."""

    exchange: str = DEFAULT_EXCHANGE
    lookback_days: int = DEFAULT_LOOKBACK_DAYS
    breakout_rank: int = DEFAULT_BREAKOUT_RANK
    refresh_seconds: int = DEFAULT_REFRESH_SECONDS
    multi_wall_top_n: int = DEFAULT_MULTI_WALL_TOP_N
    volume_interval: str = DEFAULT_VOLUME_INTERVAL
    timezone: str = DEFAULT_TIMEZONE
    demo_symbols: tuple[str, ...] = DEFAULT_DEMO_SYMBOLS
    default_basket: str = "Top FNO Stocks"
    enable_admin_refresh: bool = False
    enable_live_drilldown: bool = False

    @classmethod
    def from_env(cls) -> "ScanConfig":
        return cls(
            exchange=DEFAULT_EXCHANGE,
            lookback_days=DEFAULT_LOOKBACK_DAYS,
            breakout_rank=DEFAULT_BREAKOUT_RANK,
            refresh_seconds=int(os.getenv(ENV_STREAMLIT_CACHE_SECONDS, str(DEFAULT_REFRESH_SECONDS)) or DEFAULT_REFRESH_SECONDS),
            multi_wall_top_n=DEFAULT_MULTI_WALL_TOP_N,
            volume_interval=DEFAULT_VOLUME_INTERVAL,
            timezone=DEFAULT_TIMEZONE,
            demo_symbols=DEFAULT_DEMO_SYMBOLS,
            default_basket="Top FNO Stocks",
            enable_admin_refresh=_env_flag(ENV_ENABLE_ADMIN_REFRESH),
            enable_live_drilldown=_env_flag(ENV_ENABLE_LIVE_DRILLDOWN),
        )


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    url: str | None = None
    supabase_url: str | None = None
    secret_key: str | None = None
    host: str | None = None
    port: int = 5432
    name: str = "postgres"
    user: str = "postgres"
    password: str | None = None

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        return cls(
            url=os.getenv(ENV_SUPABASE_DB_URL) or None,
            supabase_url=os.getenv(ENV_SUPABASE_URL) or None,
            secret_key=os.getenv(ENV_SUPABASE_SECRET_KEY) or None,
            host=os.getenv(ENV_SUPABASE_DB_HOST) or None,
            port=int(os.getenv(ENV_SUPABASE_DB_PORT, "5432") or 5432),
            name=os.getenv(ENV_SUPABASE_DB_NAME, "postgres") or "postgres",
            user=os.getenv(ENV_SUPABASE_DB_USER, "postgres") or "postgres",
            password=os.getenv(ENV_SUPABASE_DB_PASSWORD) or None,
        )

    def connection_string(self) -> str | None:
        if self.host and self.password:
            host = _normalize_db_host(self.host)
            return f"postgresql://{self.user}:{self.password}@{host}:{self.port}/{self.name}"
        if self.url:
            return self.url
        return None


@dataclass(frozen=True, slots=True)
class SchedulerConfig:
    batch_size: int = 50
    refresh_minutes: int = 10
    symbol_source: str = "top_fno"
    sectors: tuple[str, ...] = ()
    symbols_csv: str | None = None

    @classmethod
    def from_env(cls) -> "SchedulerConfig":
        sectors = tuple(
            item.strip().upper()
            for item in (os.getenv(ENV_SCAN_SECTORS, "") or "").split(",")
            if item.strip()
        )
        symbols_csv = (os.getenv(ENV_SCAN_SYMBOLS_CSV, "") or "").strip() or None
        return cls(
            batch_size=int(os.getenv(ENV_SCAN_BATCH_SIZE, "50") or 50),
            refresh_minutes=int(os.getenv(ENV_SCAN_REFRESH_MINUTES, "10") or 10),
            symbol_source=(os.getenv(ENV_SCAN_SYMBOL_SOURCE, "top_fno") or "top_fno").strip().lower(),
            sectors=sectors,
            symbols_csv=symbols_csv,
        )


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Top-level app configuration."""

    app_name: str = DEFAULT_APP_NAME
    app_env: str = "development"
    demo_mode: bool = False
    auth: AuthConfig = field(default_factory=AuthConfig)
    scans: ScanConfig = field(default_factory=ScanConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)

    @classmethod
    def from_env(cls) -> "AppConfig":
        scan_config = ScanConfig.from_env()
        app_env = os.getenv(ENV_APP_ENVIRONMENT, "development").strip() or "development"
        auth = AuthConfig(
            mode="user",
            environment=os.getenv(ENV_NUBRA_ENVIRONMENT, DEFAULT_ENVIRONMENT).strip() or DEFAULT_ENVIRONMENT,
            use_env_creds=True,
        )
        return cls(
            app_env=app_env,
            demo_mode=False,
            auth=auth,
            scans=scan_config,
            database=DatabaseConfig.from_env(),
            scheduler=SchedulerConfig.from_env(),
        )


def load_app_config() -> AppConfig:
    """Convenience entry point used by the app shell later."""
    return AppConfig.from_env()


def get_basket_options() -> tuple[str, ...]:
    return tuple(BASKET_PRESETS.keys())


def resolve_symbols_for_basket(basket_name: str, custom_symbols: str = "") -> tuple[str, ...]:
    if basket_name == "Custom":
        values = [item.strip().upper() for item in custom_symbols.split(",")]
        return tuple(item for item in values if item)
    return BASKET_PRESETS.get(basket_name, DEFAULT_DEMO_SYMBOLS)


def _normalize_db_host(value: str) -> str:
    text = value.strip()
    if "://" in text:
        text = text.split("://", 1)[1]
    if "@" in text:
        text = text.rsplit("@", 1)[1]
    if "/" in text:
        text = text.split("/", 1)[0]
    if ":" in text and text.count(":") == 1:
        host_part, port_part = text.split(":", 1)
        if port_part.isdigit():
            return host_part
    return text


def _env_flag(name: str, *, default: bool = False) -> bool:
    raw = (os.getenv(name, "") or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}
