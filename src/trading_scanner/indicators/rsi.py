"""RSI (Relative Strength Index) calculation."""

import pandas as pd
import pandas_ta as ta


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Calculate RSI and append it to the DataFrame.

    Adds columns:
        - rsi: RSI value (0-100)
        - rsi_zone: "oversold" (<30), "overbought" (>70), or "neutral"

    Args:
        df: OHLCV DataFrame with a 'close' column.
        period: RSI lookback period.

    Returns:
        DataFrame with RSI columns appended.
    """
    df = df.copy()
    df["rsi"] = ta.rsi(df["close"], length=period)

    df["rsi_zone"] = "neutral"
    df.loc[df["rsi"] < 30, "rsi_zone"] = "oversold"
    df.loc[df["rsi"] > 70, "rsi_zone"] = "overbought"

    return df
