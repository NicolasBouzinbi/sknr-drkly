"""Data fetcher orchestrator — selects provider and handles fallback.

This module is the single entry point for all data fetching in the scanner.
It manages provider selection (IBKR primary, yfinance fallback) and provides
a unified interface regardless of the underlying data source.
"""

import structlog
import pandas as pd

from trading_scanner.config import ScannerConfig, get_config
from trading_scanner.data.providers import DataProvider, DataSource
from trading_scanner.data.providers.ibkr import IBKRProvider
from trading_scanner.data.providers.yfinance_provider import YFinanceProvider

logger = structlog.get_logger(__name__)


def _create_provider(source: DataSource, config: ScannerConfig) -> DataProvider:
    """Instantiate a data provider by source type.

    Args:
        source: Which data source to use.
        config: Scanner configuration.

    Returns:
        An instantiated (but not yet connected) DataProvider.
    """
    match source:
        case DataSource.IBKR:
            return IBKRProvider(config)
        case DataSource.YFINANCE:
            return YFinanceProvider(config)


def fetch_tickers(
    tickers: list[str],
    duration: str | None = None,
    bar_size: str | None = None,
    source: DataSource | None = None,
    use_rth: bool = True,
    config: ScannerConfig | None = None,
) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV data for a list of tickers using the configured provider.

    Attempts the primary data source first. If it fails to connect,
    automatically falls back to the secondary source.

    Fallback order:
        1. IBKR (if configured and Gateway is running)
        2. yfinance (always available)

    Args:
        tickers: List of stock symbols.
        duration: How far back to look (e.g., "6mo", "1y"). Defaults to config.
        bar_size: Bar size (e.g., "1d", "5m"). Defaults to config.
        source: Force a specific data source. If None, uses config default.
        use_rth: If True, only include Regular Trading Hours data.
        config: Scanner configuration. Defaults to global config.

    Returns:
        Dict mapping ticker symbols to their OHLCV DataFrames.
    """
    cfg = config or get_config()
    duration = duration or cfg.default_period
    bar_size = bar_size or cfg.default_interval
    source = source or cfg.data_source

    # Try primary source
    provider = _create_provider(source, cfg)
    try:
        provider.connect()
        logger.info("Using data source", source=provider.name)
        results = provider.fetch_multiple(tickers, duration, bar_size, use_rth)
        return results
    except ConnectionError:
        logger.warning("Primary source unavailable", source=provider.name)
    finally:
        provider.disconnect()

    # Fallback to yfinance if IBKR failed
    if source == DataSource.IBKR:
        logger.info("Falling back to yfinance")
        fallback = YFinanceProvider(cfg)
        fallback.connect()
        try:
            return fallback.fetch_multiple(tickers, duration, bar_size, use_rth)
        finally:
            fallback.disconnect()

    # If yfinance was primary and failed, nothing to fall back to
    logger.error("All data sources failed")
    return {}


def get_realtime_snapshot(
    ticker: str,
    config: ScannerConfig | None = None,
) -> dict | None:
    """Get a real-time quote snapshot from IBKR.

    Only available with IBKR connection. Returns None if not connected.

    Args:
        ticker: Stock symbol.
        config: Scanner configuration.

    Returns:
        Dict with bid, ask, last, volume — or None if unavailable.
    """
    cfg = config or get_config()
    provider = IBKRProvider(cfg)
    try:
        provider.connect()
        return provider.get_realtime_snapshot(ticker)
    except ConnectionError:
        logger.warning("Cannot get realtime data: IBKR not connected")
        return None
    finally:
        provider.disconnect()
