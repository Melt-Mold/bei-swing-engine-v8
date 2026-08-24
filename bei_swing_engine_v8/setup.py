"""
Setup detection engine (Module 08).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional

import pandas as pd
import numpy as np

from . import indicators as ind
from .structure import Structure, nearest_level, SWING_FRACTAL_N


# ============================================================
# Configurable thresholds (can be overridden by optimizer)
# These are "soft" tuning parameters, NOT locked parameters.
# Locked parameters (swing N=8, R/R≥1.5, SL priority, etc.)
# are in engine.py / risk.py / structure.py and must not change.
# ============================================================
THRESHOLDS = {
    "rvol_breakout": 1.0,         # RVOL threshold for breakout TRIGGERED
    "rvol_reconfirm": 0.9,        # RVOL threshold for reconfirm (pullback/range/retest/continuation)
    "rsi_long_reconfirm": 35,     # RSI threshold for LONG reconfirm
    "rsi_short_reconfirm": 65,    # RSI threshold for SHORT reconfirm
    "pullback_tolerance": 0.5,    # ×ATR pullback zone tolerance (locked at 0.5)
    "range_tolerance": 0.75,     # ×ATR range boundary tolerance (locked at 0.75)
    "continuation_height": 1.5,  # ×ATR max consolidation height (locked at 1.5)
}


def set_thresholds(thresholds: Dict):
    """Override thresholds for optimization. Call reset_thresholds() to restore."""
    THRESHOLDS.update(thresholds)


def reset_thresholds():
    """Reset thresholds to defaults."""
    global THRESHOLDS
    THRESHOLDS = {
        "rvol_breakout": 1.0,
        "rvol_reconfirm": 0.9,
        "rsi_long_reconfirm": 35,
        "rsi_short_reconfirm": 65,
        "pullback_tolerance": 0.5,
        "range_tolerance": 0.75,
        "continuation_height": 1.5,
    }


# ============================================================


@dataclass
class Setup:
    type: str  # Breakout, BreakoutRetest, Pullback, Reversal, Continuation, Range, None
    direction: str  # LONG, SHORT, BOTH, NONE
    status: str  # NONE, DEVELOPING, CONFIRMED, TRIGGERED, FAILED, INVALIDATED
    trigger_price: Optional[float] = None
    invalidation_price: Optional[float] = None
    basis_level: Optional[float] = None
    description: str = ""
    reason: str = ""


def rvol(df: pd.DataFrame) -> float:
    """Relative volume vs 20-day average."""
    if len(df) < 20:
        return 1.0
    vol_today = df["Volume"].iloc[-1]
    vol_ma20 = df["Volume"].iloc[-20:].mean()
    return vol_today / vol_ma20 if vol_ma20 > 0 else 1.0


def candle_bullish(df: pd.DataFrame) -> bool:
    return df["Close"].iloc[-1] > df["Open"].iloc[-1]


def candle_bearish(df: pd.DataFrame) -> bool:
    return df["Close"].iloc[-1] < df["Open"].iloc[-1]


def ma_aligned_bullish(indicators: Dict) -> bool:
    """Check if EMA9 > SMA20 > SMA50 (bullish MA alignment)."""
    e9 = indicators["ema9"].iloc[-1]
    s20 = indicators["sma20"].iloc[-1]
    s50 = indicators["sma50"].iloc[-1]
    if pd.isna(e9) or pd.isna(s20) or pd.isna(s50):
        return False
    return e9 > s20 > s50


def ma_aligned_bearish(indicators: Dict) -> bool:
    """Check if EMA9 < SMA20 < SMA50 (bearish MA alignment)."""
    e9 = indicators["ema9"].iloc[-1]
    s20 = indicators["sma20"].iloc[-1]
    s50 = indicators["sma50"].iloc[-1]
    if pd.isna(e9) or pd.isna(s20) or pd.isna(s50):
        return False
    return e9 < s20 < s50


def macd_improving(indicators: Dict, direction: str = "bullish") -> bool:
    """Check if MACD histogram is improving over last 3 bars."""
    hist = indicators["macd_histogram"]
    if len(hist) < 3:
        return False
    h0, h1, h2 = hist.iloc[-3], hist.iloc[-2], hist.iloc[-1]
    if pd.isna(h0) or pd.isna(h1) or pd.isna(h2):
        return False
    if direction == "bullish":
        return h2 > h1 or (h1 > h0 and h2 >= h1)
    else:
        return h2 < h1 or (h1 < h0 and h2 <= h1)


def _detect_breakout(df: pd.DataFrame, structure: Structure, indicators: Dict) -> Optional[Setup]:
    """Breakout setup detection."""
    close = df["Close"].iloc[-1]
    atr14 = indicators["atr14"].iloc[-1]
    if pd.isna(atr14):
        return None

    rv = rvol(df)

    # LONG breakout
    for r in structure.resistance_levels:
        level = r["price"]
        if close > level + 0.75 * atr14:
            status = "CONFIRMED"
            if rv > THRESHOLDS["rvol_breakout"]:
                status = "TRIGGERED"
            return Setup(
                type="Breakout",
                direction="LONG",
                status=status,
                trigger_price=close,
                invalidation_price=level,
                basis_level=level,
                description=f"Close {close:.0f} above resistance {level:.0f} + 0.75×ATR ({0.75*atr14:.0f}); RVOL={rv:.2f}",
            )

    # SHORT breakout
    for s in structure.support_levels:
        level = s["price"]
        if close < level - 0.75 * atr14:
            status = "CONFIRMED"
            if rv > THRESHOLDS["rvol_breakout"]:
                status = "TRIGGERED"
            return Setup(
                type="Breakout",
                direction="SHORT",
                status=status,
                trigger_price=close,
                invalidation_price=level,
                basis_level=level,
                description=f"Close {close:.0f} below support {level:.0f} − 0.75×ATR ({0.75*atr14:.0f}); RVOL={rv:.2f}",
            )

    return None


def _detect_breakout_retest(df: pd.DataFrame, structure: Structure, indicators: Dict) -> Optional[Setup]:
    """Breakout + retest setup."""
    close = df["Close"].iloc[-1]
    atr14 = indicators["atr14"].iloc[-1]
    if pd.isna(atr14):
        return None

    rv = rvol(df)

    # LONG retest: old resistance -> new support
    for r in structure.resistance_levels:
        level = r["price"]
        # price near level and previously closed above it
        if abs(close - level) <= 0.5 * atr14 and close >= level - 0.5 * atr14:
            # Need evidence of prior breakout: recent close was above level + 0.75*ATR
            recent_breakout = any(
                df["Close"].iloc[-10:].values > level + 0.75 * atr14
            ) if len(df) >= 10 else False
            if recent_breakout and (candle_bullish(df) or rv > THRESHOLDS["rvol_reconfirm"]):
                return Setup(
                    type="Breakout + Retest",
                    direction="LONG",
                    status="TRIGGERED",
                    trigger_price=close,
                    invalidation_price=level - 0.5 * atr14,
                    basis_level=level,
                    description=f"Retest of broken resistance {level:.0f}; close {close:.0f} within ±0.5×ATR; reconfirmed.",
                )
            elif recent_breakout:
                return Setup(
                    type="Breakout + Retest",
                    direction="LONG",
                    status="DEVELOPING",
                    trigger_price=None,
                    invalidation_price=level - 0.5 * atr14,
                    basis_level=level,
                    description=f"Price near broken resistance {level:.0f}; awaiting bullish reconfirm.",
                )

    # SHORT retest: old support -> new resistance
    for s in structure.support_levels:
        level = s["price"]
        if abs(close - level) <= 0.5 * atr14 and close <= level + 0.5 * atr14:
            recent_breakout = any(
                df["Close"].iloc[-10:].values < level - 0.75 * atr14
            ) if len(df) >= 10 else False
            if recent_breakout and (candle_bearish(df) or rv > THRESHOLDS["rvol_reconfirm"]):
                return Setup(
                    type="Breakout + Retest",
                    direction="SHORT",
                    status="TRIGGERED",
                    trigger_price=close,
                    invalidation_price=level + 0.5 * atr14,
                    basis_level=level,
                    description=f"Retest of broken support {level:.0f}; close {close:.0f} within ±0.5×ATR; reconfirmed.",
                )
            elif recent_breakout:
                return Setup(
                    type="Breakout + Retest",
                    direction="SHORT",
                    status="DEVELOPING",
                    trigger_price=None,
                    invalidation_price=level + 0.5 * atr14,
                    basis_level=level,
                    description=f"Price near broken support {level:.0f}; awaiting bearish reconfirm.",
                )

    return None


def _detect_pullback(df: pd.DataFrame, structure: Structure, indicators: Dict) -> Optional[Setup]:
    """Pullback setup in active trend."""
    if len(df) < 20:
        return None

    close = df["Close"].iloc[-1]
    atr14 = indicators["atr14"].iloc[-1]
    if pd.isna(atr14):
        return None

    sma20 = indicators["sma20"].iloc[-1]
    sma50 = indicators["sma50"].iloc[-1]
    rsi = indicators["rsi14"].iloc[-1]

    trend = structure.trend_structure
    rv = rvol(df)

    # LONG pullback: uptrend or bullish MA alignment, price near SMA20/50 or prior HL
    if "Uptrend" in trend or ma_aligned_bullish(indicators):
        zones = []
        if not pd.isna(sma20):
            zones.append(("SMA20", sma20))
        if not pd.isna(sma50):
            zones.append(("SMA50", sma50))
        if structure.last_swing_low:
            zones.append(("Prior HL", structure.last_swing_low.price))
        if "0.618" in structure.fib_levels:
            zones.append(("Fib 0.618", structure.fib_levels["0.618"]))

        for name, zone in zones:
            if abs(close - zone) <= 0.5 * atr14:
                # Reconfirm: reversal candle, RSI bounce (>35), volume, or MACD improving
                reconfirm = (
                    candle_bullish(df)
                    or (not pd.isna(rsi) and rsi > THRESHOLDS["rsi_long_reconfirm"])
                    or (rv > THRESHOLDS["rvol_reconfirm"])
                    or macd_improving(indicators, "bullish")
                )
                status = "TRIGGERED" if reconfirm else "DEVELOPING"
                return Setup(
                    type="Pullback",
                    direction="LONG",
                    status=status,
                    trigger_price=close if status == "TRIGGERED" else None,
                    invalidation_price=zone - 0.5 * atr14,
                    basis_level=zone,
                    description=f"Pullback to {name} {zone:.0f} in uptrend; close {close:.0f} within ±0.5×ATR.",
                )

    # SHORT pullback: downtrend or bearish MA alignment, price near SMA20/50 or prior LH
    if "Downtrend" in trend or ma_aligned_bearish(indicators):
        zones = []
        if not pd.isna(sma20):
            zones.append(("SMA20", sma20))
        if not pd.isna(sma50):
            zones.append(("SMA50", sma50))
        if structure.last_swing_high:
            zones.append(("Prior LH", structure.last_swing_high.price))
        if "0.618" in structure.fib_levels:
            zones.append(("Fib 0.618", structure.fib_levels["0.618"]))

        for name, zone in zones:
            if abs(close - zone) <= 0.5 * atr14:
                reconfirm = (
                    candle_bearish(df)
                    or (not pd.isna(rsi) and rsi < THRESHOLDS["rsi_short_reconfirm"])
                    or (rv > THRESHOLDS["rvol_reconfirm"])
                    or macd_improving(indicators, "bearish")
                )
                status = "TRIGGERED" if reconfirm else "DEVELOPING"
                return Setup(
                    type="Pullback",
                    direction="SHORT",
                    status=status,
                    trigger_price=close if status == "TRIGGERED" else None,
                    invalidation_price=zone + 0.5 * atr14,
                    basis_level=zone,
                    description=f"Pullback to {name} {zone:.0f} in downtrend; close {close:.0f} within ±0.5×ATR.",
                )

    return None


def _detect_reversal(df: pd.DataFrame, structure: Structure, indicators: Dict) -> Optional[Setup]:
    """Reversal setup after CHoCH."""
    if len(structure.bos_choch) == 0:
        return None

    close = df["Close"].iloc[-1]
    atr14 = indicators["atr14"].iloc[-1]
    if pd.isna(atr14):
        return None

    last_event = structure.bos_choch[-1]
    rsi = indicators["rsi14"].iloc[-1]
    macd_line = indicators["macd_line"].iloc[-1]
    macd_signal = indicators["macd_signal"].iloc[-1]

    # Bullish reversal: CHoCH bullish, price near support/fib, momentum shift
    if last_event["direction"] == "bullish" and "Downtrend" in structure.trend_structure:
        # Location check
        near_support = False
        if structure.last_swing_low and abs(close - structure.last_swing_low.price) <= atr14:
            near_support = True
        for s in structure.support_levels:
            if abs(close - s["price"]) <= 0.5 * atr14:
                near_support = True
        if "0.618" in structure.fib_levels and abs(close - structure.fib_levels["0.618"]) <= 0.5 * atr14:
            near_support = True

        if not near_support:
            return None

        momentum_shift = (
            (not pd.isna(rsi) and rsi > THRESHOLDS["rsi_long_reconfirm"])
            or (not pd.isna(macd_line) and macd_line > macd_signal)
            or macd_improving(indicators, "bullish")
        )
        # Trigger: close beyond first swing high
        swing_highs = sorted(structure.swing_highs, key=lambda s: s.idx)
        first_swing_high = swing_highs[-1] if swing_highs else None
        if first_swing_high and close > first_swing_high.price and momentum_shift:
            return Setup(
                type="Reversal",
                direction="LONG",
                status="TRIGGERED",
                trigger_price=close,
                invalidation_price=last_event["price"],
                basis_level=last_event["price"],
                description=f"Bullish reversal after CHoCH at {last_event['price']:.0f}; close above swing high {first_swing_high.price:.0f}.",
            )
        elif momentum_shift:
            return Setup(
                type="Reversal",
                direction="LONG",
                status="DEVELOPING",
                trigger_price=None,
                invalidation_price=last_event["price"],
                basis_level=last_event["price"],
                description=f"Bullish CHoCH at {last_event['price']:.0f}; momentum shifting; awaiting trigger above swing high.",
            )

    # Bearish reversal
    if last_event["direction"] == "bearish" and "Uptrend" in structure.trend_structure:
        near_resistance = False
        if structure.last_swing_high and abs(close - structure.last_swing_high.price) <= atr14:
            near_resistance = True
        for r in structure.resistance_levels:
            if abs(close - r["price"]) <= 0.5 * atr14:
                near_resistance = True
        if "0.618" in structure.fib_levels and abs(close - structure.fib_levels["0.618"]) <= 0.5 * atr14:
            near_resistance = True

        if not near_resistance:
            return None

        momentum_shift = (
            (not pd.isna(rsi) and rsi < THRESHOLDS["rsi_short_reconfirm"])
            or (not pd.isna(macd_line) and macd_line < macd_signal)
            or macd_improving(indicators, "bearish")
        )
        swing_lows = sorted(structure.swing_lows, key=lambda s: s.idx)
        first_swing_low = swing_lows[-1] if swing_lows else None
        if first_swing_low and close < first_swing_low.price and momentum_shift:
            return Setup(
                type="Reversal",
                direction="SHORT",
                status="TRIGGERED",
                trigger_price=close,
                invalidation_price=last_event["price"],
                basis_level=last_event["price"],
                description=f"Bearish reversal after CHoCH at {last_event['price']:.0f}; close below swing low {first_swing_low.price:.0f}.",
            )
        elif momentum_shift:
            return Setup(
                type="Reversal",
                direction="SHORT",
                status="DEVELOPING",
                trigger_price=None,
                invalidation_price=last_event["price"],
                basis_level=last_event["price"],
                description=f"Bearish CHoCH at {last_event['price']:.0f}; momentum shifting; awaiting trigger below swing low.",
            )

    return None


def _detect_continuation(df: pd.DataFrame, structure: Structure, indicators: Dict) -> Optional[Setup]:
    """Continuation setup: trend + consolidation + breakout."""
    if len(df) < 25:
        return None

    close = df["Close"].iloc[-1]
    atr14 = indicators["atr14"].iloc[-1]
    if pd.isna(atr14):
        return None

    trend = structure.trend_structure
    rv = rvol(df)

    # Identify recent consolidation (last 10-30 bars)
    lookback = min(30, len(df) - 1)
    recent = df.iloc[-lookback:]
    consolidation_height = recent["High"].max() - recent["Low"].min()
    consolidation_bars = lookback

    if consolidation_height > 1.5 * atr14:
        return None
    if consolidation_bars < 10:
        return None

    # LONG continuation
    if "Uptrend" in trend or ma_aligned_bullish(indicators):
        upper = recent["High"].max()
        if close > upper - 0.25 * atr14 and rv > THRESHOLDS["rvol_reconfirm"]:
            return Setup(
                type="Continuation",
                direction="LONG",
                status="TRIGGERED",
                trigger_price=close,
                invalidation_price=recent["Low"].min(),
                basis_level=upper,
                description=f"Continuation breakout in uptrend from {consolidation_bars}-bar consolidation; RVOL={rv:.2f}.",
            )
        elif close > recent["Close"].mean():
            return Setup(
                type="Continuation",
                direction="LONG",
                status="CONFIRMED",
                trigger_price=None,
                invalidation_price=recent["Low"].min(),
                basis_level=upper,
                description=f"Uptrend continuation consolidation; awaiting breakout above {upper:.0f}.",
            )

    # SHORT continuation
    if "Downtrend" in trend or ma_aligned_bearish(indicators):
        lower = recent["Low"].min()
        if close < lower + 0.25 * atr14 and rv > THRESHOLDS["rvol_reconfirm"]:
            return Setup(
                type="Continuation",
                direction="SHORT",
                status="TRIGGERED",
                trigger_price=close,
                invalidation_price=recent["High"].max(),
                basis_level=lower,
                description=f"Continuation breakdown in downtrend from {consolidation_bars}-bar consolidation; RVOL={rv:.2f}.",
            )
        elif close < recent["Close"].mean():
            return Setup(
                type="Continuation",
                direction="SHORT",
                status="CONFIRMED",
                trigger_price=None,
                invalidation_price=recent["High"].max(),
                basis_level=lower,
                description=f"Downtrend continuation consolidation; awaiting breakdown below {lower:.0f}.",
            )

    return None


def _detect_range(df: pd.DataFrame, structure: Structure, indicators: Dict) -> Optional[Setup]:
    """Range-bound setup. Use precomputed range_info from structure if available."""
    range_info = structure.range_info
    if range_info is None:
        from .structure import detect_range as _detect_range_info
        range_info = _detect_range_info(df, structure.support_levels, structure.resistance_levels)
        if range_info is None:
            return None

    if range_info["duration_bars"] < 20:
        return None

    close = df["Close"].iloc[-1]
    atr14 = indicators["atr14"].iloc[-1]
    if pd.isna(atr14):
        return None

    upper = range_info["upper"]
    lower = range_info["lower"]

    rv = rvol(df)
    rsi = indicators["rsi14"].iloc[-1]

    # LONG at lower boundary
    if abs(close - lower) <= 0.75 * atr14:
        reconfirm = (
            candle_bullish(df)
            or (not pd.isna(rsi) and rsi > THRESHOLDS["rsi_long_reconfirm"])
            or (rv > THRESHOLDS["rvol_reconfirm"])
            or macd_improving(indicators, "bullish")
        )
        status = "TRIGGERED" if reconfirm else "DEVELOPING"
        return Setup(
            type="Range",
            direction="LONG",
            status=status,
            trigger_price=close if status == "TRIGGERED" else None,
            invalidation_price=lower - 0.75 * atr14,
            basis_level=lower,
            description=f"Bounce from lower range boundary {lower:.0f}; close {close:.0f} within ±0.75×ATR.",
        )

    # SHORT at upper boundary
    if abs(close - upper) <= 0.75 * atr14:
        reconfirm = (
            candle_bearish(df)
            or (not pd.isna(rsi) and rsi < THRESHOLDS["rsi_short_reconfirm"])
            or (rv > THRESHOLDS["rvol_reconfirm"])
            or macd_improving(indicators, "bearish")
        )
        status = "TRIGGERED" if reconfirm else "DEVELOPING"
        return Setup(
            type="Range",
            direction="SHORT",
            status=status,
            trigger_price=close if status == "TRIGGERED" else None,
            invalidation_price=upper + 0.75 * atr14,
            basis_level=upper,
            description=f"Rejection from upper range boundary {upper:.0f}; close {close:.0f} within ±0.75×ATR.",
        )

    return None


SETUP_ORDER = ["Continuation", "Breakout", "Reversal", "Pullback", "Range", "Breakout + Retest"]
SETUP_STATUS_ORDER = {"TRIGGERED": 0, "CONFIRMED": 1, "DEVELOPING": 2, "NONE": 3, "FAILED": 4, "INVALIDATED": 5}


def detect_setups(df: pd.DataFrame, structure: Structure, indicators: Dict) -> List[Setup]:
    """
    Detect all setups and return as a list.
    Detectors run in precedence order; early exit when a TRIGGERED setup is found
    because status precedes type and type precedence is enforced by detection order.
    """
    setups = []

    # Precedence order: Continuation > Breakout > Breakout + Retest > Reversal > Pullback > Range
    detectors = [
        _detect_continuation,
        _detect_breakout,
        _detect_breakout_retest,
        _detect_reversal,
        _detect_pullback,
        _detect_range,
    ]

    for detector in detectors:
        s = detector(df, structure, indicators)
        if s:
            setups.append(s)
            if s.status == "TRIGGERED":
                # Highest-status setup found; no need to run lower-precedence detectors
                return setups

    if not setups:
        setups.append(Setup(type="None", direction="NONE", status="NONE", description="No actionable setup detected."))

    return setups


def apply_sma200_sufficiency_cap(setups: List[Setup], bars: int) -> List[Setup]:
    """
    If SMA200 is unavailable due to insufficient data (<200 bars),
    cap setup status at CONFIRMED and mark tradeability warning.
    """
    if bars >= 200:
        return setups

    for s in setups:
        if s.status == "TRIGGERED":
            s.status = "CONFIRMED"
            s.description += " [SMA200 N/A — status capped at CONFIRMED]"
    return setups


def select_primary_setup(setups: List[Setup]) -> Setup:
    """Select primary setup by status precedence, then type precedence."""
    if not setups:
        return Setup(type="None", direction="NONE", status="NONE")

    # Filter out FAILED/INVALIDATED
    active = [s for s in setups if s.status not in {"FAILED", "INVALIDATED"}]
    if not active:
        return setups[0]

    # Sort by status precedence, then type precedence
    def sort_key(s):
        status_rank = SETUP_STATUS_ORDER.get(s.status, 99)
        type_rank = SETUP_ORDER.index(s.type) if s.type in SETUP_ORDER else 99
        return (status_rank, type_rank)

    active.sort(key=sort_key)
    return active[0]
