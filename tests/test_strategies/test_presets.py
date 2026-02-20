"""Tests for scanning strategies."""

import pytest

from trading_scanner.indicators import apply_all
from trading_scanner.strategies.presets import (
    ABCDPattern,
    BullFlagMomentum,
    MovingAverageTrend,
    get_strategy,
    STRATEGIES,
)


class TestStrategyRegistry:
    """Tests for the strategy registry."""

    def test_exactly_three_strategies_registered(self) -> None:
        assert len(STRATEGIES) == 3

    def test_expected_strategy_keys(self) -> None:
        assert set(STRATEGIES.keys()) == {"abcd_pattern", "bull_flag_momentum", "ma_trend"}

    def test_get_strategy_valid(self) -> None:
        strat = get_strategy("abcd_pattern")
        assert isinstance(strat, ABCDPattern)

    def test_get_strategy_invalid(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            get_strategy("nonexistent")

    def test_all_strategies_have_name_and_description(self) -> None:
        for name, cls in STRATEGIES.items():
            strat = cls()
            assert strat.name
            assert strat.description


class TestABCDPattern:
    """Tests for the ABCDPattern strategy."""

    def test_scan_returns_valid_or_none(self, sample_ohlcv) -> None:
        df = apply_all(sample_ohlcv)
        strat = ABCDPattern()
        result = strat.scan_ticker("TEST", df)
        if result is not None:
            assert result.ticker == "TEST"
            assert result.signal == "ABCD Pattern"
            assert result.strength in ("strong", "moderate")

    def test_insufficient_data_returns_none(self, sample_ohlcv) -> None:
        # Pass raw (no indicators) short slice — strategy's len() guard fires first
        strat = ABCDPattern()
        result = strat.scan_ticker("TEST", sample_ohlcv.iloc[:10])
        assert result is None

    def test_scan_multiple_returns_list(self, sample_ohlcv) -> None:
        df = apply_all(sample_ohlcv)
        strat = ABCDPattern()
        results = strat.scan_multiple({"TEST1": df, "TEST2": df})
        assert isinstance(results, list)


class TestBullFlagMomentum:
    """Tests for the BullFlagMomentum strategy."""

    def test_scan_returns_valid_or_none(self, sample_ohlcv) -> None:
        df = apply_all(sample_ohlcv)
        strat = BullFlagMomentum()
        result = strat.scan_ticker("TEST", df)
        if result is not None:
            assert result.signal == "Bull Flag Breakout"
            assert result.vwap_position == "above"
            assert result.strength in ("strong", "moderate")

    def test_insufficient_data_returns_none(self, sample_ohlcv) -> None:
        # Pass raw (no indicators) short slice — strategy's len() guard fires first
        strat = BullFlagMomentum()
        result = strat.scan_ticker("TEST", sample_ohlcv.iloc[:10])
        assert result is None

    def test_scan_multiple_returns_list(self, sample_ohlcv) -> None:
        df = apply_all(sample_ohlcv)
        strat = BullFlagMomentum()
        results = strat.scan_multiple({"TEST1": df, "TEST2": df})
        assert isinstance(results, list)


class TestMovingAverageTrend:
    """Tests for the MovingAverageTrend strategy."""

    def test_scan_returns_valid_or_none(self, sample_ohlcv) -> None:
        df = apply_all(sample_ohlcv)
        strat = MovingAverageTrend()
        result = strat.scan_ticker("TEST", df)
        if result is not None:
            assert result.signal == "MA Trend Bounce"
            assert result.ema_trend == "bullish"
            assert result.strength in ("strong", "moderate")

    def test_scan_multiple_returns_list(self, sample_ohlcv) -> None:
        df = apply_all(sample_ohlcv)
        strat = MovingAverageTrend()
        results = strat.scan_multiple({"TEST1": df, "TEST2": df})
        assert isinstance(results, list)
