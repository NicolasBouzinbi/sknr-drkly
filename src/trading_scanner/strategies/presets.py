"""Built-in scanning strategy presets."""

import numpy as np
import pandas as pd

from trading_scanner.strategies.base import BaseStrategy, ScanResult


class ABCDPattern(BaseStrategy):
    """Detect classic ABCD equal-leg harmonic chart patterns.

    The bullish ABCD is a 4-point retracement structure:
        A (swing high) → B (swing low) → C (lower high) → D (projected low)

    Conditions:
        - B→C retraces 38.2–78.6% of the A→B leg
        - CD leg projected equal to AB (equal-leg symmetry)
        - Current price within 2% of projected D completion zone
        - Price starting to recover at D (last close > prior close)
        - RSI < 45 (compressed/oversold at D)
        - Volume pickup at D (rvol >= 1.3)
    """

    name = "abcd_pattern"
    description = "ABCD equal-leg harmonic pattern — pullback completing at D zone"

    _LOOKBACK = 40
    _BC_RETRACE_MIN = 0.382
    _BC_RETRACE_MAX = 0.786
    _D_TOLERANCE = 0.02

    def scan_ticker(self, ticker: str, df: pd.DataFrame) -> ScanResult | None:
        """Evaluate a ticker for the ABCD harmonic pattern.

        Args:
            ticker: Stock symbol.
            df: DataFrame with OHLCV data and all indicators already applied.

        Returns:
            ScanResult if ABCD pattern is detected near D completion, else None.
        """
        if len(df) < self._LOOKBACK:
            return None

        w = df.iloc[-self._LOOKBACK:]
        highs = w["high"].values
        lows = w["low"].values
        closes = w["close"].values
        n = len(highs)
        seg = n // 4

        # A: highest point in the first quarter
        a_pos = int(np.argmax(highs[:seg]))
        a_price = float(highs[a_pos])

        # B: lowest low after A, within the next quarter
        b_start = a_pos + 1
        b_end = min(a_pos + seg + 1, n - 8)
        if b_start >= b_end:
            return None
        b_pos = b_start + int(np.argmin(lows[b_start:b_end]))
        b_price = float(lows[b_pos])

        ab = a_price - b_price
        if ab <= 0:
            return None

        # C: highest high after B, leaving at least 5 bars for the D zone
        c_start = b_pos + 1
        c_end = n - 5
        if c_start >= c_end:
            return None
        c_pos = c_start + int(np.argmax(highs[c_start:c_end]))
        c_price = float(highs[c_pos])

        # C must be below A (lower high)
        if c_price >= a_price:
            return None

        # BC retracement of AB
        bc_retrace = (c_price - b_price) / ab
        if not (self._BC_RETRACE_MIN <= bc_retrace <= self._BC_RETRACE_MAX):
            return None

        # Project D as equal-leg (CD = AB)
        d_projected = c_price - ab
        if d_projected <= 0:
            return None

        # Current price must be near D
        current_close = float(closes[-1])
        if abs(current_close - d_projected) / d_projected > self._D_TOLERANCE:
            return None

        # Price recovering at D (last bar closed higher than prior)
        if closes[-1] <= closes[-2]:
            return None

        last = df.iloc[-1]
        rsi = last.get("rsi")
        rvol = float(last.get("rvol") or 0)

        if pd.isna(rsi) or float(rsi) >= 45:
            return None
        if rvol < 1.3:
            return None

        strength = "strong" if rvol >= 2.0 and float(rsi) < 35 else "moderate"

        return ScanResult(
            ticker=ticker,
            signal="ABCD Pattern",
            strength=strength,
            price=round(current_close, 2),
            rsi=round(float(rsi), 1),
            rvol=round(rvol, 2),
            ema_trend=last.get("ema_trend"),
            vwap_position=last.get("price_vs_vwap"),
            details=f"A={a_price:.2f} B={b_price:.2f} C={c_price:.2f} D≈{d_projected:.2f}",
        )


class BullFlagMomentum(BaseStrategy):
    """Detect bull flag breakout setups for momentum continuation trading.

    The bull flag is a continuation pattern:
        Pole: strong upward price move with elevated volume
        Flag: orderly pullback/consolidation with declining volume
        Breakout: price reclaims the flag high with a volume surge

    Conditions:
        - Pole: 5%+ price gain from bar[-20] to the peak in bars[-20:-6]
        - Flag: shallow retracement (<38% of pole size), bars[-6:-1]
        - Breakout: current close > flag high, rvol >= 2.0
        - RSI 50–70 (trending momentum, not overbought)
        - Price above VWAP
    """

    name = "bull_flag_momentum"
    description = "Bull flag breakout — volume-confirmed pole/flag continuation"

    _MIN_POLE_GAIN = 0.05
    _MAX_FLAG_RETRACE = 0.38
    _MIN_RVOL = 2.0
    _RSI_MIN = 50
    _RSI_MAX = 70

    def scan_ticker(self, ticker: str, df: pd.DataFrame) -> ScanResult | None:
        """Evaluate a ticker for a bull flag breakout setup.

        Args:
            ticker: Stock symbol.
            df: DataFrame with OHLCV data and all indicators already applied.

        Returns:
            ScanResult if a bull flag breakout is detected, else None.
        """
        if len(df) < 20:
            return None

        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values
        volumes = df["volume"].values

        # Pole: bars [-20:-6]
        pole_start_price = float(closes[-20])
        pole_high = float(np.max(highs[-20:-6]))
        pole_gain = (pole_high - pole_start_price) / pole_start_price

        if pole_gain < self._MIN_POLE_GAIN:
            return None

        pole_size = pole_high - pole_start_price

        # Flag: bars [-6:-1]
        flag_high = float(np.max(highs[-6:-1]))
        flag_low = float(np.min(lows[-6:-1]))
        flag_retrace = (pole_high - flag_low) / pole_size if pole_size > 0 else 1.0

        if flag_retrace > self._MAX_FLAG_RETRACE:
            return None

        # Breakout: current close above flag high
        current_close = float(closes[-1])
        if current_close <= flag_high:
            return None

        last = df.iloc[-1]
        rvol = float(last.get("rvol") or 0)
        rsi = last.get("rsi")
        above_vwap = last.get("price_vs_vwap") == "above"

        if rvol < self._MIN_RVOL:
            return None
        if pd.isna(rsi) or not (self._RSI_MIN <= float(rsi) <= self._RSI_MAX):
            return None
        if not above_vwap:
            return None

        pole_avg_vol = float(np.mean(volumes[-20:-6]))
        flag_avg_vol = float(np.mean(volumes[-6:-1]))
        volume_contracted = flag_avg_vol < pole_avg_vol

        strength = "strong" if rvol >= 3.0 and volume_contracted else "moderate"

        return ScanResult(
            ticker=ticker,
            signal="Bull Flag Breakout",
            strength=strength,
            price=round(current_close, 2),
            rsi=round(float(rsi), 1),
            rvol=round(rvol, 2),
            ema_trend=last.get("ema_trend"),
            vwap_position="above",
            details=f"Pole={pole_gain:.1%} | Flag high={flag_high:.2f} | RVOL={rvol:.1f}x",
        )


class MovingAverageTrend(BaseStrategy):
    """Trend-following strategy using moving average alignment and pullback entries.

    Identifies stocks in confirmed uptrends where price has pulled back to
    a key moving average and is now bouncing, offering a low-risk entry point.

    Conditions:
        - EMA fast (9) > EMA slow (21): bullish MA alignment
        - Price pulled back near EMA slow (within 2% above it)
        - Previous close was at or below EMA slow (confirms the pullback)
        - Current close > previous close (bounce confirmation)
        - RSI 45–65 (healthy trend, not overbought)
        - Volume pickup (rvol >= 1.2)
    """

    name = "ma_trend"
    description = "MA trend bounce — pullback-to-EMA entry in a bullish alignment"

    _EMA_PROXIMITY = 0.02
    _RSI_MIN = 45
    _RSI_MAX = 65
    _MIN_RVOL = 1.2

    def scan_ticker(self, ticker: str, df: pd.DataFrame) -> ScanResult | None:
        """Evaluate a ticker for a moving average pullback-and-bounce entry.

        Args:
            ticker: Stock symbol.
            df: DataFrame with OHLCV data and all indicators already applied.

        Returns:
            ScanResult if MA trend bounce conditions are met, else None.
        """
        if len(df) < 5:
            return None

        last = df.iloc[-1]
        prev = df.iloc[-2]

        if pd.isna(last.get("ema_fast")) or pd.isna(last.get("ema_slow")):
            return None

        if last.get("ema_trend") != "bullish":
            return None

        ema_slow = float(last["ema_slow"])
        ema_fast = float(last["ema_fast"])
        close = float(last["close"])
        prev_close = float(prev["close"])

        # Price must be above ema_slow but within proximity (the pullback entry zone)
        if close < ema_slow:
            return None
        if (close - ema_slow) / ema_slow > self._EMA_PROXIMITY:
            return None

        # Previous bar at or below ema_slow, confirming the pullback happened
        prev_ema_slow = float(prev["ema_slow"]) if pd.notna(prev.get("ema_slow")) else ema_slow
        if prev_close > prev_ema_slow * 1.01:
            return None

        # Bounce: current bar closed higher than previous
        if close <= prev_close:
            return None

        rsi = last.get("rsi")
        rvol = float(last.get("rvol") or 0)

        if pd.isna(rsi) or not (self._RSI_MIN <= float(rsi) <= self._RSI_MAX):
            return None
        if rvol < self._MIN_RVOL:
            return None

        above_vwap = last.get("price_vs_vwap") == "above"
        strength = "strong" if rvol >= 1.8 and above_vwap else "moderate"
        spread_pct = (ema_fast - ema_slow) / ema_slow * 100

        return ScanResult(
            ticker=ticker,
            signal="MA Trend Bounce",
            strength=strength,
            price=round(close, 2),
            rsi=round(float(rsi), 1),
            rvol=round(rvol, 2),
            ema_trend="bullish",
            vwap_position=last.get("price_vs_vwap"),
            details=f"EMA9={ema_fast:.2f} EMA21={ema_slow:.2f} spread={spread_pct:.1f}%",
        )


# Registry of all available strategies
STRATEGIES: dict[str, type[BaseStrategy]] = {
    "abcd_pattern": ABCDPattern,
    "bull_flag_momentum": BullFlagMomentum,
    "ma_trend": MovingAverageTrend,
}


def get_strategy(name: str) -> BaseStrategy:
    """Get a strategy instance by name.

    Args:
        name: Strategy name.

    Returns:
        Instantiated strategy.

    Raises:
        KeyError: If strategy name is not found.
    """
    if name not in STRATEGIES:
        available = ", ".join(STRATEGIES.keys())
        raise KeyError(f"Strategy '{name}' not found. Available: {available}")
    return STRATEGIES[name]()
