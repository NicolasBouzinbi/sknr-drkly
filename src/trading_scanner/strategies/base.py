"""Abstract base class for scanning strategies."""

from abc import ABC, abstractmethod

import pandas as pd
from pydantic import BaseModel


class ScanResult(BaseModel):
    """Result of a scan for a single ticker."""

    ticker: str
    signal: str
    strength: str  # "strong", "moderate", "weak"
    price: float
    rsi: float | None = None
    rvol: float | None = None
    ema_trend: str | None = None
    vwap_position: str | None = None
    details: str = ""


class BaseStrategy(ABC):
    """Abstract base class for all scanning strategies.

    Subclasses must implement `scan_ticker` which evaluates a single
    ticker's DataFrame and returns a ScanResult if conditions are met.
    """

    name: str = "base"
    description: str = ""

    @abstractmethod
    def scan_ticker(self, ticker: str, df: pd.DataFrame) -> ScanResult | None:
        """Evaluate a single ticker and return a result if conditions are met.

        Args:
            ticker: Stock symbol.
            df: DataFrame with OHLCV data and all indicators already applied.

        Returns:
            ScanResult if the ticker meets the strategy criteria, None otherwise.
        """

    def scan_multiple(
        self, data: dict[str, pd.DataFrame]
    ) -> list[ScanResult]:
        """Scan multiple tickers and collect results.

        Args:
            data: Dict mapping ticker symbols to their indicator-enriched DataFrames.

        Returns:
            List of ScanResults for tickers that met the criteria.
        """
        results: list[ScanResult] = []
        for ticker, df in data.items():
            if df.empty or len(df) < 2:
                continue
            result = self.scan_ticker(ticker, df)
            if result is not None:
                results.append(result)
        return results
