"""ATR (Average True Range) calculation."""

import pandas as pd
import pandas_ta as ta


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Calculate ATR using Wilder's smoothing and append it to the DataFrame.

    ATR measures volatility as the average of True Range over `period` bars.
    True Range = max(high-low, |high-prev_close|, |low-prev_close|).

    Adds columns:
        - atr: Average True Range (same units as price).

    Args:
        df: OHLCV DataFrame with 'high', 'low', 'close' columns.
        period: ATR lookback period.

    Returns:
        DataFrame with ATR column appended.
    """
    df = df.copy()
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=period)
    return df
