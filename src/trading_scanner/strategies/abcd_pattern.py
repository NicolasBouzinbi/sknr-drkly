"""ABCD harmonic pattern strategy.

Based on Scott Carney's *Harmonic Trading* (AB=CD pattern), Andrew Aziz's
*How to Day Trade for a Living*, and standard Fibonacci harmonic theory.

Supports classic AB=CD (equal-leg) and alternate patterns (1.27x, 1.618x)
in both bullish and bearish directions, with BC projection convergence
validation and time symmetry scoring.
"""

from __future__ import annotations

from typing import ClassVar

import numpy as np
import pandas as pd

from trading_scanner.strategies.base import BaseStrategy, ScanResult

# Reciprocal pairs: BC retracement → expected BC projection (Carney).
_RECIPROCAL_PAIRS: list[tuple[float, float]] = [
    (0.382, 2.618),
    (0.500, 2.000),
    (0.618, 1.618),
    (0.786, 1.270),
    (0.886, 1.130),
]


def _find_swing_highs(highs: np.ndarray, order: int) -> list[int]:
    """Return indices of local swing highs (peak higher than *order* bars on each side)."""
    swings: list[int] = []
    for i in range(order, len(highs) - order):
        if highs[i] == max(highs[i - order : i + order + 1]):
            swings.append(i)
    return swings


def _find_swing_lows(lows: np.ndarray, order: int) -> list[int]:
    """Return indices of local swing lows (trough lower than *order* bars on each side)."""
    swings: list[int] = []
    for i in range(order, len(lows) - order):
        if lows[i] == min(lows[i - order : i + order + 1]):
            swings.append(i)
    return swings


def _reciprocal_ok(bc_retrace: float, bc_proj: float, tolerance: float = 0.25) -> bool:
    """Check whether BC projection is close to the reciprocal of BC retracement."""
    for retrace, proj in _RECIPROCAL_PAIRS:
        retrace_ok = abs(bc_retrace - retrace) / retrace <= tolerance
        proj_ok = abs(bc_proj - proj) / proj <= tolerance
        if retrace_ok and proj_ok:
            return True
    return False


def _variant_label(ratio: float) -> str:
    if ratio <= 1.05:
        return "classic"
    if ratio <= 1.40:
        return "1.27"
    return "1.618"


class ABCDPattern(BaseStrategy):
    """Detect ABCD harmonic patterns per Carney / Aziz / Fibonacci theory.

    Scans for both bullish and bearish patterns using classic equal-leg
    AB=CD as well as alternate 1.27x and 1.618x extensions.  BC projection
    convergence is validated against Carney's reciprocal pairs, and time
    symmetry between AB and CD legs is used for strength scoring.

    Strength rating:
        strong   — geometry + reciprocal convergence + tight time symmetry
                   + confirming indicator (RSI < 40 or RVOL >= 2.0)
        moderate — geometry + at least partial confirmation
        weak     — geometry matches but no indicator confirmation
    """

    name = "abcd_pattern"
    description = "ABCD harmonic pattern (classic + alternate) — Carney / Aziz rules"

    _LOOKBACK = 50
    _SWING_ORDER = 5
    _BC_RETRACE_MIN = 0.382
    _BC_RETRACE_MAX = 0.886
    _BC_PROJ_MIN = 1.13
    _BC_PROJ_MAX = 2.618
    _CD_RATIOS: ClassVar[list[float]] = [1.0, 1.27, 1.618]
    _D_TOLERANCE = 0.03
    _TIME_SYM_MIN = 0.5
    _TIME_SYM_MAX = 2.0
    _TIME_SYM_TIGHT_MIN = 0.75
    _TIME_SYM_TIGHT_MAX = 1.5

    def scan_ticker(self, ticker: str, df: pd.DataFrame) -> ScanResult | None:
        """Evaluate a ticker for ABCD harmonic patterns.

        Args:
            ticker: Stock symbol.
            df: DataFrame with OHLCV data and all indicators already applied.

        Returns:
            ScanResult if an ABCD pattern is detected, else None.
        """
        if len(df) < self._LOOKBACK:
            return None

        w = df.iloc[-self._LOOKBACK :]
        highs = w["high"].values.astype(float)
        lows = w["low"].values.astype(float)
        closes = w["close"].values.astype(float)
        n = len(highs)

        swing_highs = _find_swing_highs(highs, self._SWING_ORDER)
        swing_lows = _find_swing_lows(lows, self._SWING_ORDER)

        if not swing_highs or not swing_lows:
            return None

        best: ScanResult | None = None
        best_score = -1

        for direction in ("bullish", "bearish"):
            result, score = self._scan_direction(
                direction, highs, lows, closes, n,
                swing_highs, swing_lows, df, ticker,
            )
            if result is not None and score > best_score:
                best = result
                best_score = score

        return best

    def _scan_direction(
        self,
        direction: str,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        n: int,
        swing_highs: list[int],
        swing_lows: list[int],
        df: pd.DataFrame,
        ticker: str,
    ) -> tuple[ScanResult | None, int]:
        """Try to find an ABCD pattern in the given direction.

        Returns (ScanResult | None, strength_score).
        """
        half = n // 2
        current_close = float(closes[-1])
        last = df.iloc[-1]

        if direction == "bullish":
            # Bullish: A=swing high, B=swing low, C=lower high, D=projected low
            a_candidates = [i for i in swing_highs if i < half]
            if not a_candidates:
                return None, 0
            a_pos = max(a_candidates, key=lambda i: highs[i])
            a_price = float(highs[a_pos])

            b_candidates = [i for i in swing_lows if i > a_pos]
            if not b_candidates:
                return None, 0
            b_pos = min(b_candidates, key=lambda i: lows[i])
            b_price = float(lows[b_pos])

            ab = a_price - b_price
            if ab <= 0:
                return None, 0

            c_candidates = [
                i for i in swing_highs if i > b_pos and i < n - 3
            ]
            if not c_candidates:
                return None, 0
            c_pos = max(c_candidates, key=lambda i: highs[i])
            c_price = float(highs[c_pos])

            if c_price >= a_price:
                return None, 0

            bc = c_price - b_price
            sign = -1  # D is below C for bullish
        else:
            # Bearish: A=swing low, B=swing high, C=higher low, D=projected high
            a_candidates = [i for i in swing_lows if i < half]
            if not a_candidates:
                return None, 0
            a_pos = min(a_candidates, key=lambda i: lows[i])
            a_price = float(lows[a_pos])

            b_candidates = [i for i in swing_highs if i > a_pos]
            if not b_candidates:
                return None, 0
            b_pos = max(b_candidates, key=lambda i: highs[i])
            b_price = float(highs[b_pos])

            ab = b_price - a_price
            if ab <= 0:
                return None, 0

            c_candidates = [
                i for i in swing_lows if i > b_pos and i < n - 3
            ]
            if not c_candidates:
                return None, 0
            c_pos = min(c_candidates, key=lambda i: lows[i])
            c_price = float(lows[c_pos])

            if c_price <= a_price:
                return None, 0

            bc = b_price - c_price
            sign = 1  # D is above C for bearish

        if bc <= 0:
            return None, 0

        bc_retrace = bc / ab
        if not (self._BC_RETRACE_MIN <= bc_retrace <= self._BC_RETRACE_MAX):
            return None, 0

        # Time symmetry
        ab_bars = b_pos - a_pos
        cd_bars = (n - 1) - c_pos
        if ab_bars <= 0:
            return None, 0
        time_ratio = cd_bars / ab_bars
        if not (self._TIME_SYM_MIN <= time_ratio <= self._TIME_SYM_MAX):
            return None, 0
        tight_time = self._TIME_SYM_TIGHT_MIN <= time_ratio <= self._TIME_SYM_TIGHT_MAX

        # Try each CD ratio (classic + alternates)
        for cd_ratio in self._CD_RATIOS:
            d_projected = c_price + sign * (ab * cd_ratio)
            if d_projected <= 0:
                continue

            # Check price is near projected D
            if abs(current_close - d_projected) / d_projected > self._D_TOLERANCE:
                continue

            # BC projection convergence (Carney)
            actual_cd = abs(current_close - c_price)
            if bc > 0:
                bc_proj = actual_cd / bc
            else:
                continue

            if not (self._BC_PROJ_MIN <= bc_proj <= self._BC_PROJ_MAX):
                continue

            reciprocal_match = _reciprocal_ok(bc_retrace, bc_proj)

            # --- Pattern matched — compute strength ---
            rsi = last.get("rsi")
            rvol = float(last.get("rvol") or 0)
            rsi_val = float(rsi) if pd.notna(rsi) else None

            score = 0
            if reciprocal_match:
                score += 2
            if tight_time:
                score += 1
            if (direction == "bullish" and rsi_val is not None and rsi_val < 40) or (
                direction == "bearish" and rsi_val is not None and rsi_val > 60
            ):
                score += 1
            if rvol >= 2.0:
                score += 1

            if score >= 3:
                strength = "strong"
            elif score >= 1:
                strength = "moderate"
            else:
                strength = "weak"

            # Trade levels (Aziz)
            atr = last.get("atr")
            atr_val = float(atr) if pd.notna(atr) else None
            ad_range = abs(a_price - d_projected)

            if direction == "bullish":
                stop = (d_projected - atr_val) if atr_val else d_projected * 0.98
                t1 = d_projected + ad_range * 0.382
                t2 = d_projected + ad_range * 0.500
                t3 = d_projected + ad_range * 0.618
                signal = "Bullish ABCD"
            else:
                stop = (d_projected + atr_val) if atr_val else d_projected * 1.02
                t1 = d_projected - ad_range * 0.382
                t2 = d_projected - ad_range * 0.500
                t3 = d_projected - ad_range * 0.618
                signal = "Bearish ABCD"

            variant = _variant_label(cd_ratio)
            details = (
                f"{variant} | "
                f"A={a_price:.2f} B={b_price:.2f} C={c_price:.2f} D~{d_projected:.2f} | "
                f"BC ret={bc_retrace:.1%} proj={bc_proj:.2f} | "
                f"stop={stop:.2f} T1={t1:.2f} T2={t2:.2f} T3={t3:.2f}"
            )

            result = ScanResult(
                ticker=ticker,
                signal=signal,
                strength=strength,
                price=round(current_close, 2),
                rsi=round(rsi_val, 1) if rsi_val is not None else None,
                rvol=round(rvol, 2) if rvol else None,
                ema_trend=last.get("ema_trend"),
                vwap_position=last.get("price_vs_vwap"),
                details=details,
            )
            return result, score

        return None, 0
