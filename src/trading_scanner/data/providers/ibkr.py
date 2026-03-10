"""Interactive Brokers data provider using ib_async.

Connects to IB Gateway (headless) or TWS to fetch historical bars,
intraday data, and real-time streaming quotes.

Requires a running IB Gateway with API enabled on the configured port.
Default port: 4001 (Gateway), 7497 (TWS paper), 7496 (TWS live).
"""

import time

import pandas as pd
import structlog
from ib_async import IB, Stock, util

from trading_scanner.config import ScannerConfig, get_config
from trading_scanner.data.providers import DataProvider, normalize_columns

logger = structlog.get_logger(__name__)

# IBKR rate-limits historical data requests: ~60 per 10 minutes.
# We add a small delay between requests to stay well within limits.
_REQUEST_DELAY_SECONDS = 0.5

# Mapping from our simplified bar sizes to IBKR's barSizeSetting strings
BAR_SIZE_MAP: dict[str, str] = {
    "1m": "1 min",
    "5m": "5 mins",
    "15m": "15 mins",
    "30m": "30 mins",
    "1h": "1 hour",
    "4h": "4 hours",
    "1d": "1 day",
    "1w": "1 week",
    "1M": "1 month",
}

# Mapping from our simplified duration to IBKR's durationStr strings
DURATION_MAP: dict[str, str] = {
    "1d": "1 D",
    "5d": "5 D",
    "1mo": "1 M",
    "3mo": "3 M",
    "6mo": "6 M",
    "1y": "1 Y",
    "2y": "2 Y",
}


class IBKRProvider(DataProvider):
    """Interactive Brokers data provider.

    Uses ib_async to communicate with IB Gateway or TWS.
    Manages a single IB connection instance and handles contract qualification,
    historical data requests, and real-time market data subscriptions.
    """

    name = "ibkr"

    def __init__(self, config: ScannerConfig | None = None) -> None:
        self._config = config or get_config()
        self._ib = IB()

    def connect(self) -> None:
        """Connect to IB Gateway.

        Raises:
            ConnectionError: If IB Gateway is not running or refuses connection.
        """
        if self._ib.isConnected():
            logger.debug("Already connected to IBKR")
            return

        try:
            self._ib.connect(
                host=self._config.ibkr_host,
                port=self._config.ibkr_port,
                clientId=self._config.ibkr_client_id,
                timeout=self._config.ibkr_timeout,
                readonly=True,
            )
            logger.info(
                "Connected to IBKR",
                host=self._config.ibkr_host,
                port=self._config.ibkr_port,
                client_id=self._config.ibkr_client_id,
            )
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to IB Gateway at "
                f"{self._config.ibkr_host}:{self._config.ibkr_port}. "
                f"Is IB Gateway running with API enabled? Error: {e}"
            ) from e

    def disconnect(self) -> None:
        """Disconnect from IB Gateway."""
        if self._ib.isConnected():
            self._ib.disconnect()
            logger.info("Disconnected from IBKR")

    def is_connected(self) -> bool:
        """Check if connected to IB Gateway."""
        return self._ib.isConnected()

    def _make_contract(self, ticker: str) -> Stock:
        """Create and qualify a US stock contract.

        Args:
            ticker: Stock symbol (e.g., "AAPL").

        Returns:
            Qualified Stock contract.

        Raises:
            ValueError: If the contract cannot be qualified (invalid ticker).
        """
        contract = Stock(ticker, "SMART", "USD")
        qualified = self._ib.qualifyContracts(contract)
        if not qualified:
            raise ValueError(f"Could not qualify contract for ticker: {ticker}")
        return qualified[0]

    def _resolve_bar_size(self, bar_size: str) -> str:
        """Resolve our simplified bar size to IBKR format.

        Args:
            bar_size: Simplified bar size (e.g., "1d", "5m", "1h").

        Returns:
            IBKR barSizeSetting string (e.g., "1 day", "5 mins").
        """
        resolved = BAR_SIZE_MAP.get(bar_size, bar_size)
        logger.debug("Resolved bar size", input=bar_size, output=resolved)
        return resolved

    def _resolve_duration(self, duration: str) -> str:
        """Resolve our simplified duration to IBKR format.

        Args:
            duration: Simplified duration (e.g., "6mo", "1y").

        Returns:
            IBKR durationStr string (e.g., "6 M", "1 Y").
        """
        resolved = DURATION_MAP.get(duration, duration)
        logger.debug("Resolved duration", input=duration, output=resolved)
        return resolved

    def _bars_to_dataframe(self, bars: list) -> pd.DataFrame:
        """Convert ib_async BarData list to a normalized pandas DataFrame.

        Args:
            bars: List of BarData objects from reqHistoricalData.

        Returns:
            DataFrame with lowercase OHLCV columns and DatetimeIndex.
        """
        if not bars:
            return pd.DataFrame()

        df = util.df(bars)
        df = normalize_columns(df)

        # Set date as index
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")

        # Keep only OHLCV columns (IBKR may return average, barCount, etc.)
        ohlcv_cols = ["open", "high", "low", "close", "volume"]
        available_cols = [c for c in ohlcv_cols if c in df.columns]
        df = df[available_cols]

        return df

    def fetch_historical(
        self,
        ticker: str,
        duration: str = "6mo",
        bar_size: str = "1d",
        use_rth: bool = True,
    ) -> pd.DataFrame:
        """Fetch historical OHLCV bars from IBKR for a single ticker.

        Args:
            ticker: Stock symbol (e.g., "AAPL").
            duration: How far back (e.g., "6mo", "1y", "5d").
            bar_size: Bar size (e.g., "1d", "5m", "1h").
            use_rth: If True, only include Regular Trading Hours.

        Returns:
            Normalized OHLCV DataFrame with DatetimeIndex.
        """
        contract = self._make_contract(ticker)

        bars = self._ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=self._resolve_duration(duration),
            barSizeSetting=self._resolve_bar_size(bar_size),
            whatToShow="TRADES",
            useRTH=use_rth,
            formatDate=1,
        )

        df = self._bars_to_dataframe(bars)
        logger.info("Historical data fetched", ticker=ticker, rows=len(df))
        return df

    def fetch_multiple(
        self,
        tickers: list[str],
        duration: str = "6mo",
        bar_size: str = "1d",
        use_rth: bool = True,
    ) -> dict[str, pd.DataFrame]:
        """Fetch historical data for multiple tickers with rate limiting.

        Adds a small delay between requests to respect IBKR's rate limits
        (~60 historical requests per 10 minutes).

        Args:
            tickers: List of stock symbols.
            duration: How far back to look.
            bar_size: Bar size/interval.
            use_rth: If True, only include RTH data.

        Returns:
            Dict mapping ticker symbols to DataFrames.
        """
        results: dict[str, pd.DataFrame] = {}

        for i, ticker in enumerate(tickers):
            ticker = ticker.upper().strip()
            try:
                df = self.fetch_historical(ticker, duration, bar_size, use_rth)
                if not df.empty:
                    results[ticker] = df
            except Exception:
                logger.warning("Failed to fetch IBKR data", ticker=ticker, exc_info=True)

            # Rate limit: pause between requests (skip after last)
            if i < len(tickers) - 1:
                time.sleep(_REQUEST_DELAY_SECONDS)

        logger.info("IBKR batch fetch complete", total=len(tickers), success=len(results))
        return results

    def get_realtime_snapshot(self, ticker: str) -> dict | None:
        """Get a real-time market data snapshot for a ticker.

        Args:
            ticker: Stock symbol.

        Returns:
            Dict with bid, ask, last, volume, or None if unavailable.
        """
        contract = self._make_contract(ticker)
        self._ib.reqMktData(contract, "", False, False)
        self._ib.sleep(2)  # Wait for data to arrive

        ticker_data = self._ib.ticker(contract)
        if ticker_data is None:
            return None

        return {
            "bid": ticker_data.bid if ticker_data.bid > 0 else None,
            "ask": ticker_data.ask if ticker_data.ask > 0 else None,
            "last": ticker_data.last if ticker_data.last > 0 else None,
            "volume": ticker_data.volume if ticker_data.volume >= 0 else None,
            "high": ticker_data.high if ticker_data.high > 0 else None,
            "low": ticker_data.low if ticker_data.low > 0 else None,
        }

    def __enter__(self) -> "IBKRProvider":
        """Context manager: connect on entry."""
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager: disconnect on exit."""
        self.disconnect()
