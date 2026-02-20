"""VWAP (Volume Weighted Average Price) calculation."""

import pandas as pd


def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate VWAP and price position relative to it.

    For daily data, VWAP is computed as cumulative (typical_price * volume) / cumulative(volume).
    For intraday, it resets each day.

    Adds columns:
        - vwap: Volume Weighted Average Price.
        - price_vs_vwap: "above" or "below" VWAP.
        - vwap_distance_pct: Percentage distance from VWAP.

    Args:
        df: OHLCV DataFrame with 'high', 'low', 'close', 'volume' columns.

    Returns:
        DataFrame with VWAP columns appended.
    """
    df = df.copy()

    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    tp_volume = typical_price * df["volume"]

    # Detect if intraday (index has time component with multiple entries per day)
    is_intraday = _is_intraday(df)

    if is_intraday:
        # Reset VWAP each day
        day_groups = df.index.date
        df["vwap"] = tp_volume.groupby(day_groups).cumsum() / df["volume"].groupby(day_groups).cumsum()
    else:
        # Rolling VWAP over the full period for daily data
        df["vwap"] = tp_volume.cumsum() / df["volume"].cumsum()

    df["price_vs_vwap"] = "below"
    df.loc[df["close"] > df["vwap"], "price_vs_vwap"] = "above"

    df["vwap_distance_pct"] = ((df["close"] - df["vwap"]) / df["vwap"]) * 100

    return df


def _is_intraday(df: pd.DataFrame) -> bool:
    """Detect if a DataFrame contains intraday data."""
    if len(df) < 2:
        return False
    idx = df.index
    if hasattr(idx, "date"):
        unique_dates = len(set(idx.date))
        return unique_dates < len(idx)
    return False
