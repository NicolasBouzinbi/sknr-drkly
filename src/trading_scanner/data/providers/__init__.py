"""Abstract base class for market data providers."""

from abc import ABC, abstractmethod

import pandas as pd

# Re-export DataSourceEnum as DataSource for cleaner downstream imports
from trading_scanner.config import DataSourceEnum as DataSource

__all__ = ["DataProvider", "DataSource", "normalize_columns"]


class DataProvider(ABC):
    """Abstract interface for market data providers.

    All providers must normalize output DataFrames to have lowercase columns:
    open, high, low, close, volume — with a DatetimeIndex.
    """

    name: str

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the data source.

        Raises:
            ConnectionError: If the connection cannot be established.
        """

    @abstractmethod
    def disconnect(self) -> None:
        """Cleanly close the connection."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the provider is currently connected."""

    @abstractmethod
    def fetch_historical(
        self,
        ticker: str,
        duration: str,
        bar_size: str,
        use_rth: bool = True,
    ) -> pd.DataFrame:
        """Fetch historical OHLCV bars for a single ticker.

        Args:
            ticker: Stock symbol (e.g., "AAPL").
            duration: How far back to look (provider-specific format).
            bar_size: Bar size/interval (provider-specific format).
            use_rth: If True, only include Regular Trading Hours data.

        Returns:
            DataFrame with columns: open, high, low, close, volume.
            DatetimeIndex. Empty DataFrame if no data available.
        """

    @abstractmethod
    def fetch_multiple(
        self,
        tickers: list[str],
        duration: str,
        bar_size: str,
        use_rth: bool = True,
    ) -> dict[str, pd.DataFrame]:
        """Fetch historical data for multiple tickers.

        Args:
            tickers: List of stock symbols.
            duration: How far back to look.
            bar_size: Bar size/interval.
            use_rth: If True, only include RTH data.

        Returns:
            Dict mapping ticker symbols to DataFrames.
            Failed tickers are excluded with a log warning.
        """


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize DataFrame column names to lowercase.

    Args:
        df: Raw DataFrame from any provider.

    Returns:
        DataFrame with lowercase column names.
    """
    df.columns = [col.lower() for col in df.columns]
    return df
