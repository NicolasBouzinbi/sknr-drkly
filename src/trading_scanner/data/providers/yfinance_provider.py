"""yfinance data provider — fallback when IBKR is unavailable.

Uses Yahoo Finance via the yfinance library. No authentication required,
but subject to rate limits and no real-time intraday data.
"""

import pandas as pd
import structlog
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from trading_scanner.config import ScannerConfig, get_config
from trading_scanner.data.providers import DataProvider, normalize_columns

logger = structlog.get_logger(__name__)

# yfinance uses different format strings than IBKR.
# We accept our simplified format and map if needed.
YF_PERIOD_MAP: dict[str, str] = {
    "1d": "1d",
    "5d": "5d",
    "1mo": "1mo",
    "3mo": "3mo",
    "6mo": "6mo",
    "1y": "1y",
    "2y": "2y",
}

YF_INTERVAL_MAP: dict[str, str] = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "1d": "1d",
    "1w": "1wk",
    "1M": "1mo",
}


class YFinanceProvider(DataProvider):
    """Yahoo Finance data provider via yfinance.

    Stateless provider that requires no connection management.
    Used as a fallback when IBKR is unavailable.
    """

    name = "yfinance"

    def __init__(self, config: ScannerConfig | None = None) -> None:
        self._config = config or get_config()

    def connect(self) -> None:
        """No-op: yfinance requires no connection."""
        logger.debug("yfinance provider ready (no connection needed)")

    def disconnect(self) -> None:
        """No-op: yfinance requires no connection."""

    def is_connected(self) -> bool:
        """Always True: yfinance is stateless."""
        return True

    @staticmethod
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _download_ticker(ticker: str, period: str, interval: str) -> pd.DataFrame:
        """Download data for a single ticker with retry.

        Args:
            ticker: Stock symbol.
            period: yfinance period string.
            interval: yfinance interval string.

        Returns:
            Normalized OHLCV DataFrame.

        Raises:
            ValueError: If no data is returned.
        """
        logger.info("Fetching from yfinance", ticker=ticker, period=period, interval=interval)
        data = yf.download(
            ticker, period=period, interval=interval, progress=False, auto_adjust=True,
        )

        if data.empty:
            raise ValueError(f"No data returned for {ticker}")

        return normalize_columns(data)

    def fetch_historical(
        self,
        ticker: str,
        duration: str = "6mo",
        bar_size: str = "1d",
        use_rth: bool = True,
    ) -> pd.DataFrame:
        """Fetch historical OHLCV bars from Yahoo Finance.

        Args:
            ticker: Stock symbol (e.g., "AAPL").
            duration: Period string (e.g., "6mo", "1y").
            bar_size: Interval string (e.g., "1d", "5m").
            use_rth: Ignored for yfinance (always returns RTH for daily).

        Returns:
            Normalized OHLCV DataFrame with DatetimeIndex.
        """
        period = YF_PERIOD_MAP.get(duration, duration)
        interval = YF_INTERVAL_MAP.get(bar_size, bar_size)

        return self._download_ticker(ticker, period, interval)

    def fetch_multiple(
        self,
        tickers: list[str],
        duration: str = "6mo",
        bar_size: str = "1d",
        use_rth: bool = True,
    ) -> dict[str, pd.DataFrame]:
        """Fetch historical data for multiple tickers.

        Args:
            tickers: List of stock symbols.
            duration: Period string.
            bar_size: Interval string.
            use_rth: Ignored for yfinance.

        Returns:
            Dict mapping ticker symbols to DataFrames.
        """
        results: dict[str, pd.DataFrame] = {}

        for ticker in tickers:
            ticker = ticker.upper().strip()
            try:
                df = self.fetch_historical(ticker, duration, bar_size, use_rth)
                if not df.empty:
                    results[ticker] = df
            except Exception:
                logger.warning("Failed to fetch yfinance data", ticker=ticker, exc_info=True)

        logger.info("yfinance batch fetch complete", total=len(tickers), success=len(results))
        return results

    def __enter__(self) -> "YFinanceProvider":
        return self

    def __exit__(self, *args: object) -> None:
        pass
