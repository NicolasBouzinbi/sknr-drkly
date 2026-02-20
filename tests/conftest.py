"""Shared test fixtures and configuration."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """Generate a sample OHLCV DataFrame for testing.

    Creates 60 days of realistic-looking stock data.
    """
    np.random.seed(42)
    n = 60
    dates = pd.bdate_range(end=pd.Timestamp.now(), periods=n)

    # Generate a random walk for close prices starting around $100
    returns = np.random.normal(0.001, 0.02, n)
    close = 100 * np.cumprod(1 + returns)

    # Derive OHLV from close
    high = close * (1 + np.abs(np.random.normal(0, 0.01, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, n)))
    open_price = low + (high - low) * np.random.random(n)
    volume = np.random.randint(1_000_000, 10_000_000, n).astype(float)

    return pd.DataFrame(
        {"open": open_price, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


@pytest.fixture
def oversold_ohlcv() -> pd.DataFrame:
    """Generate OHLCV data that triggers an oversold condition.

    Creates a downtrend followed by a recovery with volume spike.
    """
    np.random.seed(123)
    n = 60
    dates = pd.bdate_range(end=pd.Timestamp.now(), periods=n)

    # Strong downtrend then bounce
    close = np.concatenate([
        100 * np.cumprod(1 + np.random.normal(-0.015, 0.005, 45)),  # Downtrend
        np.linspace(60, 65, 15),  # Recovery
    ])

    high = close * 1.01
    low = close * 0.99
    open_price = low + (high - low) * 0.5

    # Volume spike on last bars
    volume = np.concatenate([
        np.random.randint(1_000_000, 3_000_000, 50).astype(float),
        np.random.randint(5_000_000, 10_000_000, 10).astype(float),  # Spike
    ])

    return pd.DataFrame(
        {"open": open_price, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )
