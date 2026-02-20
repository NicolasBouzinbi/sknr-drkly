"""Built-in scanning strategy presets."""

import pandas as pd

from trading_scanner.strategies.base import BaseStrategy, ScanResult


class OversoldBounce(BaseStrategy):
    """Detect oversold conditions with bullish reversal signals.

    Conditions:
        - RSI < 30 (oversold)
        - Price above fast EMA (showing recovery)
        - Volume spike (rvol >= 1.5)
    """

    name = "oversold_bounce"
    description = "RSI oversold + price recovering above EMA + volume confirmation"

    def scan_ticker(self, ticker: str, df: pd.DataFrame) -> ScanResult | None:
        last = df.iloc[-1]

        if pd.isna(last.get("rsi")) or pd.isna(last.get("rvol")):
            return None

        is_oversold = last["rsi"] < 30
        price_above_ema = last["close"] > last.get("ema_fast", float("inf"))
        has_volume = last.get("rvol", 0) >= 1.5

        if not (is_oversold and price_above_ema and has_volume):
            return None

        strength = "strong" if last["rsi"] < 25 and last["rvol"] >= 2.0 else "moderate"

        return ScanResult(
            ticker=ticker,
            signal="Oversold Bounce",
            strength=strength,
            price=round(float(last["close"]), 2),
            rsi=round(float(last["rsi"]), 1),
            rvol=round(float(last["rvol"]), 2),
            ema_trend=last.get("ema_trend"),
            vwap_position=last.get("price_vs_vwap"),
            details=f"RSI={last['rsi']:.1f}, RVOL={last['rvol']:.1f}x",
        )


class EMACrossover(BaseStrategy):
    """Detect EMA crossover signals with volume confirmation.

    Conditions:
        - Bullish EMA crossover (fast crosses above slow)
        - Relative volume > 1.2 (mild confirmation)
        - Optional: price above VWAP
    """

    name = "ema_crossover"
    description = "Bullish EMA crossover with volume confirmation"

    def scan_ticker(self, ticker: str, df: pd.DataFrame) -> ScanResult | None:
        last = df.iloc[-1]

        if last.get("ema_cross") != "bullish_cross":
            return None

        has_volume = last.get("rvol", 0) >= 1.2
        if not has_volume:
            return None

        above_vwap = last.get("price_vs_vwap") == "above"
        strength = "strong" if above_vwap and last.get("rvol", 0) >= 1.5 else "moderate"

        return ScanResult(
            ticker=ticker,
            signal="EMA Bullish Cross",
            strength=strength,
            price=round(float(last["close"]), 2),
            rsi=round(float(last["rsi"]), 1) if pd.notna(last.get("rsi")) else None,
            rvol=round(float(last["rvol"]), 2) if pd.notna(last.get("rvol")) else None,
            ema_trend="bullish",
            vwap_position=last.get("price_vs_vwap"),
            details=f"EMA{df.attrs.get('ema_fast', 9)} crossed above EMA{df.attrs.get('ema_slow', 21)}",
        )


class VWAPBounce(BaseStrategy):
    """Detect price bouncing off VWAP with momentum confirmation.

    Conditions:
        - Price crossed above VWAP (was below, now above)
        - RSI between 40-60 (neutral, room to run)
        - Volume confirmation (rvol >= 1.3)
    """

    name = "vwap_bounce"
    description = "Price reclaiming VWAP with momentum"

    def scan_ticker(self, ticker: str, df: pd.DataFrame) -> ScanResult | None:
        if len(df) < 2:
            return None

        last = df.iloc[-1]
        prev = df.iloc[-2]

        if pd.isna(last.get("vwap")) or pd.isna(prev.get("vwap")):
            return None

        crossed_above_vwap = (
            prev["close"] < prev["vwap"] and last["close"] > last["vwap"]
        )

        if not crossed_above_vwap:
            return None

        rsi_ok = 40 <= (last.get("rsi") or 0) <= 60
        has_volume = last.get("rvol", 0) >= 1.3

        if not (rsi_ok and has_volume):
            return None

        strength = "strong" if last.get("rvol", 0) >= 1.8 else "moderate"

        return ScanResult(
            ticker=ticker,
            signal="VWAP Bounce",
            strength=strength,
            price=round(float(last["close"]), 2),
            rsi=round(float(last["rsi"]), 1) if pd.notna(last.get("rsi")) else None,
            rvol=round(float(last["rvol"]), 2) if pd.notna(last.get("rvol")) else None,
            ema_trend=last.get("ema_trend"),
            vwap_position="above",
            details=f"Price reclaimed VWAP at {last['vwap']:.2f}",
        )


class MomentumSurge(BaseStrategy):
    """Detect strong momentum setups for day trading.

    Conditions:
        - EMA trend is bullish (fast > slow)
        - RSI between 50-70 (strong but not overbought)
        - Volume spike (rvol >= 2.0)
        - Price above VWAP
    """

    name = "momentum_surge"
    description = "High-volume momentum with bullish trend alignment"

    def scan_ticker(self, ticker: str, df: pd.DataFrame) -> ScanResult | None:
        last = df.iloc[-1]

        bullish_trend = last.get("ema_trend") == "bullish"
        rsi_range = 50 <= (last.get("rsi") or 0) <= 70
        big_volume = last.get("rvol", 0) >= 2.0
        above_vwap = last.get("price_vs_vwap") == "above"

        if not (bullish_trend and rsi_range and big_volume and above_vwap):
            return None

        strength = "strong" if last.get("rvol", 0) >= 3.0 else "moderate"

        return ScanResult(
            ticker=ticker,
            signal="Momentum Surge",
            strength=strength,
            price=round(float(last["close"]), 2),
            rsi=round(float(last["rsi"]), 1) if pd.notna(last.get("rsi")) else None,
            rvol=round(float(last["rvol"]), 2) if pd.notna(last.get("rvol")) else None,
            ema_trend="bullish",
            vwap_position="above",
            details=f"RVOL={last['rvol']:.1f}x, RSI={last['rsi']:.1f}",
        )


# Registry of all available strategies
STRATEGIES: dict[str, type[BaseStrategy]] = {
    "oversold_bounce": OversoldBounce,
    "ema_crossover": EMACrossover,
    "vwap_bounce": VWAPBounce,
    "momentum_surge": MomentumSurge,
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
