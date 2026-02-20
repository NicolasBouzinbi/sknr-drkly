"""Tests for scanning strategies."""

import pytest

from trading_scanner.indicators import apply_all
from trading_scanner.strategies.presets import (
    EMACrossover,
    MomentumSurge,
    OversoldBounce,
    VWAPBounce,
    get_strategy,
    STRATEGIES,
)


class TestStrategyRegistry:
    """Tests for the strategy registry."""

    def test_all_strategies_registered(self) -> None:
        assert len(STRATEGIES) >= 4

    def test_get_strategy_valid(self) -> None:
        strat = get_strategy("oversold_bounce")
        assert isinstance(strat, OversoldBounce)

    def test_get_strategy_invalid(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            get_strategy("nonexistent")

    def test_all_strategies_have_name_and_description(self) -> None:
        for name, cls in STRATEGIES.items():
            strat = cls()
            assert strat.name
            assert strat.description


class TestOversoldBounce:
    """Tests for the OversoldBounce strategy."""

    def test_no_signal_on_random_data(self, sample_ohlcv) -> None:
        df = apply_all(sample_ohlcv)
        strat = OversoldBounce()
        result = strat.scan_ticker("TEST", df)
        # Random data is unlikely to trigger oversold + volume spike
        # This is a smoke test — result can be None or a valid ScanResult
        if result is not None:
            assert result.ticker == "TEST"
            assert result.signal == "Oversold Bounce"

    def test_scan_multiple_returns_list(self, sample_ohlcv) -> None:
        df = apply_all(sample_ohlcv)
        strat = OversoldBounce()
        results = strat.scan_multiple({"TEST1": df, "TEST2": df})
        assert isinstance(results, list)


class TestEMACrossover:
    """Tests for the EMACrossover strategy."""

    def test_scan_returns_valid_or_none(self, sample_ohlcv) -> None:
        df = apply_all(sample_ohlcv)
        strat = EMACrossover()
        result = strat.scan_ticker("TEST", df)
        if result is not None:
            assert result.signal == "EMA Bullish Cross"
            assert result.ema_trend == "bullish"


class TestVWAPBounce:
    """Tests for the VWAPBounce strategy."""

    def test_scan_returns_valid_or_none(self, sample_ohlcv) -> None:
        df = apply_all(sample_ohlcv)
        strat = VWAPBounce()
        result = strat.scan_ticker("TEST", df)
        if result is not None:
            assert result.signal == "VWAP Bounce"


class TestMomentumSurge:
    """Tests for the MomentumSurge strategy."""

    def test_scan_returns_valid_or_none(self, sample_ohlcv) -> None:
        df = apply_all(sample_ohlcv)
        strat = MomentumSurge()
        result = strat.scan_ticker("TEST", df)
        if result is not None:
            assert result.signal == "Momentum Surge"
            assert result.strength in ("strong", "moderate")
