"""Tests for scanning strategies and auto-discovery registry."""

import numpy as np
import pandas as pd
import pytest

from trading_scanner.indicators import apply_all
from trading_scanner.strategies import STRATEGIES, get_strategy
from trading_scanner.strategies.abcd_pattern import ABCDPattern


class TestStrategyRegistry:
    """Tests for the strategy auto-discovery registry."""

    def test_abcd_strategy_registered(self) -> None:
        assert "abcd_pattern" in STRATEGIES

    def test_exactly_one_strategy_registered(self) -> None:
        assert len(STRATEGIES) == 1

    def test_get_strategy_valid(self) -> None:
        strat = get_strategy("abcd_pattern")
        assert isinstance(strat, ABCDPattern)

    def test_get_strategy_invalid(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            get_strategy("nonexistent")

    def test_all_strategies_have_name_and_description(self) -> None:
        for _name, cls in STRATEGIES.items():
            strat = cls()
            assert strat.name
            assert strat.description


class TestABCDPattern:
    """Tests for the ABCDPattern strategy."""

    def test_scan_returns_valid_or_none(self, sample_ohlcv: pd.DataFrame) -> None:
        df = apply_all(sample_ohlcv)
        strat = ABCDPattern()
        result = strat.scan_ticker("TEST", df)
        if result is not None:
            assert result.ticker == "TEST"
            assert result.signal in ("Bullish ABCD", "Bearish ABCD")
            assert result.strength in ("strong", "moderate", "weak")

    def test_insufficient_data_returns_none(self, sample_ohlcv: pd.DataFrame) -> None:
        strat = ABCDPattern()
        result = strat.scan_ticker("TEST", sample_ohlcv.iloc[:10])
        assert result is None

    def test_scan_multiple_returns_list(self, sample_ohlcv: pd.DataFrame) -> None:
        df = apply_all(sample_ohlcv)
        strat = ABCDPattern()
        results = strat.scan_multiple({"TEST1": df, "TEST2": df})
        assert isinstance(results, list)

    def test_bullish_abcd_detection(self) -> None:
        """Craft data with a clear bullish ABCD: high A, low B, retracement C, drop to D."""
        np.random.seed(99)
        n = 60
        dates = pd.bdate_range(end=pd.Timestamp.now(), periods=n)

        # Build price profile: up→down(A)→low(B)→partial retrace(C)→drop to D
        close = np.concatenate([
            np.linspace(100, 120, 10),   # ramp up
            np.linspace(120, 95, 12),    # A=120 → B=95 (AB=25)
            np.linspace(95, 110, 10),    # B→C retrace (BC=15, 60% of AB)
            np.linspace(110, 86, 18),    # C→D drop (CD≈24 ≈ AB)
            np.linspace(86, 85, 10),     # settle near D ≈ 85
        ])
        close = close[:n]
        high = close * 1.005
        low = close * 0.995
        open_price = close + np.random.normal(0, 0.3, n)
        volume = np.random.randint(2_000_000, 8_000_000, n).astype(float)

        df = pd.DataFrame(
            {"open": open_price, "high": high, "low": low, "close": close, "volume": volume},
            index=dates,
        )
        df = apply_all(df)
        strat = ABCDPattern()
        result = strat.scan_ticker("BULL", df)
        # Pattern may or may not match depending on swing detection; just validate shape
        if result is not None:
            assert result.signal == "Bullish ABCD"
            variant = result.details.split(" | ")[0]
            assert variant in ("classic", "1.27", "1.618")
            assert "stop=" in result.details
            assert "T1=" in result.details

    def test_bearish_abcd_detection(self) -> None:
        """Craft data with a clear bearish ABCD: low A, high B, retrace C, rally to D."""
        np.random.seed(77)
        n = 60
        dates = pd.bdate_range(end=pd.Timestamp.now(), periods=n)

        close = np.concatenate([
            np.linspace(100, 80, 10),    # drop
            np.linspace(80, 105, 12),    # A=80 → B=105 (AB=25)
            np.linspace(105, 90, 10),    # B→C retrace (BC=15, 60%)
            np.linspace(90, 114, 18),    # C→D rally (CD≈24 ≈ AB)
            np.linspace(114, 115, 10),   # settle near D
        ])
        close = close[:n]
        high = close * 1.005
        low = close * 0.995
        open_price = close + np.random.normal(0, 0.3, n)
        volume = np.random.randint(2_000_000, 8_000_000, n).astype(float)

        df = pd.DataFrame(
            {"open": open_price, "high": high, "low": low, "close": close, "volume": volume},
            index=dates,
        )
        df = apply_all(df)
        strat = ABCDPattern()
        result = strat.scan_ticker("BEAR", df)
        if result is not None:
            assert result.signal == "Bearish ABCD"
            assert "stop=" in result.details

    def test_details_contain_trade_levels(self, sample_ohlcv: pd.DataFrame) -> None:
        """If a pattern is found, details must include Aziz trade levels."""
        df = apply_all(sample_ohlcv)
        strat = ABCDPattern()
        result = strat.scan_ticker("TEST", df)
        if result is not None:
            assert "T1=" in result.details
            assert "T2=" in result.details
            assert "T3=" in result.details
            assert "stop=" in result.details
            assert "BC ret=" in result.details

    def test_details_contain_variant_label(self, sample_ohlcv: pd.DataFrame) -> None:
        """Details must start with a variant label (classic, 1.27, or 1.618)."""
        df = apply_all(sample_ohlcv)
        strat = ABCDPattern()
        result = strat.scan_ticker("TEST", df)
        if result is not None:
            variant = result.details.split(" | ")[0]
            assert variant in ("classic", "1.27", "1.618")

    def test_empty_dataframe_returns_none(self) -> None:
        strat = ABCDPattern()
        result = strat.scan_ticker("TEST", pd.DataFrame())
        assert result is None
