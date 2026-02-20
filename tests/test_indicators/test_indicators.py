"""Tests for technical indicator calculations."""

import pandas as pd
import pytest

from trading_scanner.indicators.atr import add_atr
from trading_scanner.indicators.ema import add_ema_crossover, add_trend_ema
from trading_scanner.indicators.rsi import add_rsi
from trading_scanner.indicators.volume import add_relative_volume
from trading_scanner.indicators.vwap import add_vwap


class TestRSI:
    """Tests for RSI indicator."""

    def test_adds_rsi_column(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_rsi(sample_ohlcv)
        assert "rsi" in result.columns
        assert "rsi_zone" in result.columns

    def test_rsi_range(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_rsi(sample_ohlcv)
        valid_rsi = result["rsi"].dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_rsi_zones(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_rsi(sample_ohlcv)
        valid_zones = result["rsi_zone"].dropna().unique()
        assert all(z in ("oversold", "overbought", "neutral") for z in valid_zones)

    def test_does_not_modify_original(self, sample_ohlcv: pd.DataFrame) -> None:
        original_cols = set(sample_ohlcv.columns)
        add_rsi(sample_ohlcv)
        assert set(sample_ohlcv.columns) == original_cols


class TestEMACrossover:
    """Tests for EMA crossover indicator."""

    def test_adds_ema_columns(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_ema_crossover(sample_ohlcv)
        assert "ema_fast" in result.columns
        assert "ema_slow" in result.columns
        assert "ema_cross" in result.columns
        assert "ema_trend" in result.columns

    def test_ema_trend_values(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_ema_crossover(sample_ohlcv)
        valid_trends = result["ema_trend"].dropna().unique()
        assert all(t in ("bullish", "bearish") for t in valid_trends)

    def test_crossover_values(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_ema_crossover(sample_ohlcv)
        valid_crosses = result["ema_cross"].dropna().unique()
        assert all(c in ("bullish_cross", "bearish_cross") for c in valid_crosses)


class TestRelativeVolume:
    """Tests for relative volume indicator."""

    def test_adds_volume_columns(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_relative_volume(sample_ohlcv)
        assert "volume_sma" in result.columns
        assert "rvol" in result.columns
        assert "volume_spike" in result.columns

    def test_rvol_positive(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_relative_volume(sample_ohlcv)
        valid_rvol = result["rvol"].dropna()
        assert (valid_rvol > 0).all()

    def test_volume_spike_is_bool(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_relative_volume(sample_ohlcv)
        assert result["volume_spike"].dtype == bool


class TestVWAP:
    """Tests for VWAP indicator."""

    def test_adds_vwap_columns(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_vwap(sample_ohlcv)
        assert "vwap" in result.columns
        assert "price_vs_vwap" in result.columns
        assert "vwap_distance_pct" in result.columns

    def test_vwap_positive(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_vwap(sample_ohlcv)
        valid_vwap = result["vwap"].dropna()
        assert (valid_vwap > 0).all()

    def test_price_vs_vwap_values(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_vwap(sample_ohlcv)
        valid_positions = result["price_vs_vwap"].dropna().unique()
        assert all(p in ("above", "below") for p in valid_positions)


class TestATR:
    """Tests for ATR indicator."""

    def test_adds_atr_column(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_atr(sample_ohlcv)
        assert "atr" in result.columns

    def test_atr_positive(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_atr(sample_ohlcv)
        valid_atr = result["atr"].dropna()
        assert (valid_atr > 0).all()

    def test_atr_less_than_price(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_atr(sample_ohlcv)
        valid = result.dropna(subset=["atr"])
        assert (valid["atr"] < valid["close"]).all()

    def test_does_not_modify_original(self, sample_ohlcv: pd.DataFrame) -> None:
        original_cols = set(sample_ohlcv.columns)
        add_atr(sample_ohlcv)
        assert set(sample_ohlcv.columns) == original_cols


class TestTrendEMA:
    """Tests for trend EMA (EMA50) indicator."""

    def test_adds_ema_50_column(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_trend_ema(sample_ohlcv)
        assert "ema_50" in result.columns

    def test_ema_50_positive(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_trend_ema(sample_ohlcv)
        valid = result["ema_50"].dropna()
        assert (valid > 0).all()

    def test_custom_period(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_trend_ema(sample_ohlcv, period=20)
        assert "ema_20" in result.columns

    def test_does_not_modify_original(self, sample_ohlcv: pd.DataFrame) -> None:
        original_cols = set(sample_ohlcv.columns)
        add_trend_ema(sample_ohlcv)
        assert set(sample_ohlcv.columns) == original_cols
