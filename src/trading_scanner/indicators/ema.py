"""EMA (Exponential Moving Average) crossover detection."""

import pandas as pd
import pandas_ta as ta


def add_ema_crossover(
    df: pd.DataFrame,
    fast: int = 9,
    slow: int = 21,
) -> pd.DataFrame:
    """Calculate EMAs and detect crossover signals.

    Adds columns:
        - ema_fast: Fast EMA values
        - ema_slow: Slow EMA values
        - ema_cross: "bullish_cross" (fast crosses above slow),
                     "bearish_cross" (fast crosses below slow), or None
        - ema_trend: "bullish" (fast > slow) or "bearish" (fast <= slow)

    Args:
        df: OHLCV DataFrame with a 'close' column.
        fast: Fast EMA period.
        slow: Slow EMA period.

    Returns:
        DataFrame with EMA columns appended.
    """
    df = df.copy()
    df["ema_fast"] = ta.ema(df["close"], length=fast)
    df["ema_slow"] = ta.ema(df["close"], length=slow)

    # Trend direction
    df["ema_trend"] = "bearish"
    df.loc[df["ema_fast"] > df["ema_slow"], "ema_trend"] = "bullish"

    # Crossover detection: compare current vs previous bar
    fast_above_now = df["ema_fast"] > df["ema_slow"]
    fast_above_prev = fast_above_now.shift(1, fill_value=False)

    df["ema_cross"] = None
    df.loc[fast_above_now & ~fast_above_prev, "ema_cross"] = "bullish_cross"
    df.loc[~fast_above_now & fast_above_prev, "ema_cross"] = "bearish_cross"

    return df


def add_trend_ema(df: pd.DataFrame, period: int = 50) -> pd.DataFrame:
    """Calculate a medium-term trend EMA for higher-timeframe direction.

    Adds columns:
        - ema_50: {period}-period EMA of close price.

    Args:
        df: OHLCV DataFrame with a 'close' column.
        period: EMA period (default 50).

    Returns:
        DataFrame with trend EMA column appended.
    """
    df = df.copy()
    df[f"ema_{period}"] = ta.ema(df["close"], length=period)
    return df
