"""Volume analysis: relative volume and spike detection."""

import pandas as pd


def add_relative_volume(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Calculate relative volume (RVOL) compared to its moving average.

    Adds columns:
        - volume_sma: Simple moving average of volume over `period` bars.
        - rvol: Relative volume ratio (current volume / volume_sma).
        - volume_spike: True if rvol >= 1.5 (configurable via strategies).

    Args:
        df: OHLCV DataFrame with a 'volume' column.
        period: Lookback period for volume SMA.

    Returns:
        DataFrame with volume analysis columns appended.
    """
    df = df.copy()
    df["volume_sma"] = df["volume"].rolling(window=period).mean()
    df["rvol"] = df["volume"] / df["volume_sma"]
    df["volume_spike"] = df["rvol"] >= 1.5

    return df
