"""Technical indicator calculations.

All indicator functions follow the same signature:
    func(df: pd.DataFrame, **kwargs) -> pd.DataFrame

They take a DataFrame with OHLCV columns and return it with new indicator columns appended.
"""

import pandas as pd

from trading_scanner.indicators.ema import add_ema_crossover
from trading_scanner.indicators.rsi import add_rsi
from trading_scanner.indicators.volume import add_relative_volume
from trading_scanner.indicators.vwap import add_vwap

__all__ = ["add_ema_crossover", "add_rsi", "add_relative_volume", "add_vwap", "apply_all"]


def apply_all(
    df: pd.DataFrame,
    rsi_period: int = 14,
    ema_fast: int = 9,
    ema_slow: int = 21,
    volume_sma_period: int = 20,
) -> pd.DataFrame:
    """Apply all indicators to a DataFrame in one call.

    Args:
        df: OHLCV DataFrame.
        rsi_period: RSI lookback period.
        ema_fast: Fast EMA period.
        ema_slow: Slow EMA period.
        volume_sma_period: Volume SMA lookback for relative volume.

    Returns:
        DataFrame with all indicator columns appended.
    """
    df = add_rsi(df, period=rsi_period)
    df = add_ema_crossover(df, fast=ema_fast, slow=ema_slow)
    df = add_relative_volume(df, period=volume_sma_period)
    df = add_vwap(df)
    return df
