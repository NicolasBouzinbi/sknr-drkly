"""Application configuration using Pydantic Settings.

Supports IBKR Gateway connection settings, yfinance fallback,
and all scanner parameters via environment variables or config file.
"""

from enum import StrEnum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

APP_DIR = Path.home() / ".trading_scanner"
APP_DIR.mkdir(exist_ok=True)


class DataSourceEnum(StrEnum):
    """Available data source backends."""

    IBKR = "ibkr"
    YFINANCE = "yfinance"


class ScannerConfig(BaseSettings):
    """Global scanner configuration.

    Loads from environment variables prefixed with SCANNER_,
    or from ~/.trading_scanner/config.env if present.
    """

    # --- Data source selection ---
    data_source: DataSourceEnum = Field(
        default=DataSourceEnum.IBKR,
        description="Primary data source: 'ibkr' or 'yfinance'",
    )

    # --- IBKR Gateway connection ---
    ibkr_host: str = Field(default="127.0.0.1", description="IB Gateway host")
    ibkr_port: int = Field(
        default=4001, description="IB Gateway port (4001=Gateway, 7497=TWS paper, 7496=TWS live)"
    )
    ibkr_client_id: int = Field(default=1, description="IBKR client ID (unique per connection)")
    ibkr_timeout: int = Field(default=10, description="Connection timeout in seconds")

    # --- Data fetching ---
    default_period: str = Field(
        default="6mo", description="Default lookback period (1d, 5d, 1mo, 6mo, 1y)"
    )
    default_interval: str = Field(
        default="1d", description="Default bar size (1m, 5m, 15m, 1h, 1d)"
    )
    max_concurrent_fetches: int = Field(default=5, description="Max parallel ticker fetches")
    cache_ttl_minutes: int = Field(default=15, description="Data cache TTL in minutes")

    # --- Indicator defaults ---
    rsi_period: int = Field(default=14, description="RSI lookback period")
    ema_fast: int = Field(default=9, description="Fast EMA period")
    ema_slow: int = Field(default=21, description="Slow EMA period")
    volume_sma_period: int = Field(default=20, description="Volume SMA lookback")
    volume_spike_threshold: float = Field(default=1.5, description="Relative volume threshold")

    # --- Paths ---
    app_dir: Path = Field(default=APP_DIR)
    watchlists_file: Path = Field(default=APP_DIR / "watchlists.json")

    model_config = {
        "env_prefix": "SCANNER_",
        "env_file": str(APP_DIR / "config.env"),
        "env_file_encoding": "utf-8",
    }


def get_config() -> ScannerConfig:
    """Load and return the scanner configuration."""
    return ScannerConfig()
