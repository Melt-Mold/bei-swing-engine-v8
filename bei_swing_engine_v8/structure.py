"""
Market structure: swings, support/resistance, Fibonacci, BOS/CHoCH, trend structure.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

import pandas as pd
import numpy as np


SWING_FRACTAL_N = 8


@dataclass
class Swing:
    idx: int
    date: pd.Timestamp
    price: float
    kind: str  # 'high' or 'low'


@dataclass
class Structure:
    swings: List[Swing] = field(default_factory=list)
    swing_highs: List[Swing] = field(default_factory=list)
    swing_lows: List[Swing] = field(default_factory=list)
    support_levels: List[Dict] = field(default_factory=list)
    resistance_levels: List[Dict] = field(default_factory=list)
    fib_levels: Dict[str, float] = field(default_factory=dict)
    bos_choch: List[Dict] = field(default_factory=list)
    range_info: Optional[Dict] = None
    trend_structure: str = "N/A"
    patterns: list = field(default_factory=list)
    last_swing_high: Optional[Swing] = None
    last_swing_low: Optional[Swing] = None

    def filter_as_of(
        self,
        cutoff: pd.Timestamp,
        truncated_df: pd.DataFrame,
        sliced_indicators: Dict,
    ) -> "Structure":
        """Return a new Structure containing only swings/events up to cutoff,
        with S/R recomputed from the truncated dataframe."""
        # Filter swings
        swings = [s for s in self.swings if s.date <= cutoff]
        swing_highs = [s for s in self.swing_highs if s.date <= cutoff]
        swing_lows = [s for s in self.swing_lows if s.date <= cutoff]

        # Filter bos_choch events
        bos_choch = [e for e in self.bos_choch if e["date"] <= cutoff]

        # Recompute trend structure from filtered swings
        trend_structure = determine_trend_structure(swings)

        # Recompute S/R from filtered swings using truncated df and sliced ATR
        atr14 = sliced_indicators["atr14"].iloc[-1]
        if pd.isna(atr14):
            atr14 = (truncated_df["High"] - truncated_df["Low"]).mean()
        support_levels, resistance_levels = find_support_resistance(truncated_df, swings, atr14)

        # Recompute fib and range info from filtered swings
        fib_levels = compute_fibonacci_from_swings(swing_highs, swing_lows)
        range_info = detect_range(truncated_df, support_levels, resistance_levels)

        return Structure(
            swings=swings,
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            fib_levels=fib_levels,
            bos_choch=bos_choch,
            range_info=range_info,
            trend_structure=trend_structure,
            patterns=self.patterns,
            last_swing_high=swing_highs[-1] if swing_highs else None,
            last_swing_low=swing_lows[-1] if swing_lows else None,
        )


def find_swings(df: pd.DataFrame, n: int = SWING_FRACTAL_N) -> List[Swing]:
    """
    Find swing highs and lows using n-bar fractal.
    A swing high at i if High[i] == max(High[i-n:i+n+1]).
    A swing low at i if Low[i] == min(Low[i-n:i+n+1]).

    Optimized: uses numpy sliding_window_view for vectorized computation.
    """
    from numpy.lib.stride_tricks import sliding_window_view

    high_arr = df["High"].to_numpy()
    low_arr = df["Low"].to_numpy()
    dates = df.index

    window = 2 * n + 1
    if len(high_arr) < window:
        return []

    # Vectorized rolling max/min over 2n+1 window
    high_windows = sliding_window_view(high_arr, window)
    low_windows = sliding_window_view(low_arr, window)

    window_max = high_windows.max(axis=1)
    window_min = low_windows.min(axis=1)

    # Center of window j is at position j+n
    centers_high = high_arr[n:n + len(window_max)]
    centers_low = low_arr[n:n + len(window_min)]

    swing_high_mask = centers_high == window_max
    swing_low_mask = centers_low == window_min

    swings = []
    for j in range(len(window_max)):
        idx = j + n
        if swing_high_mask[j]:
            swings.append(Swing(idx=idx, date=dates[idx], price=float(centers_high[j]), kind="high"))
        elif swing_low_mask[j]:
            swings.append(Swing(idx=idx, date=dates[idx], price=float(centers_low[j]), kind="low"))

    return swings


def cluster_levels(
    prices: List[float],
    tolerance: float,
    min_touches: int = 2,
    kind: str = "support",
) -> List[Dict]:
    """Cluster nearby prices into support/resistance levels."""
    if not prices:
        return []

    prices = sorted(prices)
    clusters = []
    current = [prices[0]]

    for p in prices[1:]:
        if p - current[0] <= tolerance:
            current.append(p)
        else:
            if len(current) >= min_touches:
                clusters.append({
                    "price": round(np.mean(current), 2),
                    "touches": len(current),
                    "min": round(min(current), 2),
                    "max": round(max(current), 2),
                    "kind": kind,
                })
            current = [p]

    if len(current) >= min_touches:
        clusters.append({
            "price": round(np.mean(current), 2),
            "touches": len(current),
            "min": round(min(current), 2),
            "max": round(max(current), 2),
            "kind": kind,
        })

    return clusters


def find_support_resistance(df: pd.DataFrame, swings: List[Swing], atr14: float) -> Tuple[List[Dict], List[Dict]]:
    """Find S/R clusters from swing lows/highs, labeled relative to current close."""
    close = df["Close"].iloc[-1]
    tolerance = max(0.005 * close, 0.5 * atr14)

    # Levels above current close act as resistance; below as support.
    support_prices = [s.price for s in swings if s.kind == "low" and s.price < close]
    resistance_prices = [s.price for s in swings if s.kind == "high" and s.price > close]

    supports = cluster_levels(support_prices, tolerance, min_touches=2, kind="support")
    resistances = cluster_levels(resistance_prices, tolerance, min_touches=2, kind="resistance")

    # Sort by proximity to current close
    supports.sort(key=lambda x: abs(x["price"] - close), reverse=True)
    resistances.sort(key=lambda x: abs(x["price"] - close))

    return supports, resistances


def compute_fibonacci(df: pd.DataFrame, swings: List[Swing]) -> Dict[str, float]:
    """
    Compute Fibonacci retracement/extension levels from last significant swing high-low.
    """
    if len(swings) < 2:
        return {}

    # Find the two most recent opposite swings
    recent = swings[-12:] if len(swings) >= 12 else swings
    highs = [s for s in recent if s.kind == "high"]
    lows = [s for s in recent if s.kind == "low"]

    if not highs or not lows:
        return {}

    last_high = highs[-1]
    last_low = lows[-1]

    if last_high.idx > last_low.idx:
        # Down wave: high to low
        anchor_high = last_high.price
        anchor_low = last_low.price
        diff = anchor_high - anchor_low
        levels = {
            "anchor_high": anchor_high,
            "anchor_low": anchor_low,
            "direction": "down",
            "0.0": anchor_high,
            "0.236": anchor_high - 0.236 * diff,
            "0.382": anchor_high - 0.382 * diff,
            "0.5": anchor_high - 0.5 * diff,
            "0.618": anchor_high - 0.618 * diff,
            "0.786": anchor_high - 0.786 * diff,
            "1.0": anchor_low,
            "1.272": anchor_low - 0.272 * diff,
            "1.618": anchor_low - 0.618 * diff,
        }
    else:
        # Up wave: low to high
        anchor_low = last_low.price
        anchor_high = last_high.price
        diff = anchor_high - anchor_low
        levels = {
            "anchor_low": anchor_low,
            "anchor_high": anchor_high,
            "direction": "up",
            "0.0": anchor_low,
            "0.236": anchor_low + 0.236 * diff,
            "0.382": anchor_low + 0.382 * diff,
            "0.5": anchor_low + 0.5 * diff,
            "0.618": anchor_low + 0.618 * diff,
            "0.786": anchor_low + 0.786 * diff,
            "1.0": anchor_high,
            "1.272": anchor_high + 0.272 * diff,
            "1.618": anchor_high + 0.618 * diff,
        }

    return {k: round(v, 2) if isinstance(v, (int, float)) else v for k, v in levels.items()}


def compute_fibonacci_from_swings(swing_highs: List[Swing], swing_lows: List[Swing]) -> Dict[str, float]:
    """Compute Fibonacci levels from the most recent opposite swings."""
    if not swing_highs or not swing_lows:
        return {}

    last_high = swing_highs[-1]
    last_low = swing_lows[-1]

    if last_high.idx > last_low.idx:
        anchor_high = last_high.price
        anchor_low = last_low.price
        diff = anchor_high - anchor_low
        levels = {
            "anchor_high": anchor_high,
            "anchor_low": anchor_low,
            "direction": "down",
            "0.0": anchor_high,
            "0.236": anchor_high - 0.236 * diff,
            "0.382": anchor_high - 0.382 * diff,
            "0.5": anchor_high - 0.5 * diff,
            "0.618": anchor_high - 0.618 * diff,
            "0.786": anchor_high - 0.786 * diff,
            "1.0": anchor_low,
            "1.272": anchor_low - 0.272 * diff,
            "1.618": anchor_low - 0.618 * diff,
        }
    else:
        anchor_low = last_low.price
        anchor_high = last_high.price
        diff = anchor_high - anchor_low
        levels = {
            "anchor_low": anchor_low,
            "anchor_high": anchor_high,
            "direction": "up",
            "0.0": anchor_low,
            "0.236": anchor_low + 0.236 * diff,
            "0.382": anchor_low + 0.382 * diff,
            "0.5": anchor_low + 0.5 * diff,
            "0.618": anchor_low + 0.618 * diff,
            "0.786": anchor_low + 0.786 * diff,
            "1.0": anchor_high,
            "1.272": anchor_high + 0.272 * diff,
            "1.618": anchor_high + 0.618 * diff,
        }

    return {k: round(v, 2) if isinstance(v, (int, float)) else v for k, v in levels.items()}


def detect_bos_choch(swings: List[Swing]) -> List[Dict]:
    """
    Detect Break of Structure (BOS) and Change of Character (CHoCH) from swing sequence.
    """
    if len(swings) < 4:
        return []

    events = []
    # We track last two significant swing highs and lows
    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]

    if len(highs) >= 2 and len(lows) >= 2:
        # BOS/CHoCH on highs
        prev_high = highs[-2]
        last_high = highs[-1]
        prev_low = lows[-2]
        last_low = lows[-1]

        if last_high.price > prev_high.price:
            events.append({
                "type": "BOS",
                "direction": "bullish",
                "date": last_high.date,
                "price": last_high.price,
                "description": f"Higher high above {prev_high.price}",
            })
        elif last_high.price < prev_high.price:
            events.append({
                "type": "CHoCH",
                "direction": "bearish",
                "date": last_high.date,
                "price": last_high.price,
                "description": f"Lower high below {prev_high.price}",
            })

        if last_low.price > prev_low.price:
            events.append({
                "type": "CHoCH",
                "direction": "bullish",
                "date": last_low.date,
                "price": last_low.price,
                "description": f"Higher low above {prev_low.price}",
            })
        elif last_low.price < prev_low.price:
            events.append({
                "type": "BOS",
                "direction": "bearish",
                "date": last_low.date,
                "price": last_low.price,
                "description": f"Lower low below {prev_low.price}",
            })

    return events


def determine_trend_structure(swings: List[Swing]) -> str:
    """
    Determine trend structure from recent swing highs/lows: Uptrend, Downtrend, Ranging, N/A.
    """
    if len(swings) < 4:
        return "N/A"

    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]

    if len(highs) < 2 or len(lows) < 2:
        return "N/A"

    last_two_highs = highs[-2:]
    last_two_lows = lows[-2:]

    hh = last_two_highs[-1].price > last_two_highs[0].price
    hl = last_two_lows[-1].price > last_two_lows[0].price
    lh = last_two_highs[-1].price < last_two_highs[0].price
    ll = last_two_lows[-1].price < last_two_lows[0].price

    if hh and hl:
        return "Uptrend (HH-HL)"
    if lh and ll:
        return "Downtrend (LH-LL)"
    return "Ranging"


def detect_range(df: pd.DataFrame, supports: List[Dict], resistances: List[Dict]) -> Optional[Dict]:
    """
    Detect if price is in a trading range.
    Min touches >=2 per boundary, min duration >=20 bars, height >= 1 ATR.
    """
    if not supports or not resistances:
        return None

    upper = resistances[0]["price"]
    lower = supports[0]["price"]
    height = upper - lower
    close = df["Close"].iloc[-1]

    # Range needs to contain current price or be near it
    if not (lower - height * 0.1 <= close <= upper + height * 0.1):
        return None

    # Find first touch date approximately by checking when price was near support/resistance
    # Optimized: vectorized numpy instead of per-bar iloc loop
    high_arr = df["High"].to_numpy()
    low_arr = df["Low"].to_numpy()
    upper_tol = height * 0.05
    upper_touches = int(np.sum(np.abs(high_arr - upper) <= upper_tol))
    lower_touches = int(np.sum(np.abs(low_arr - lower) <= upper_tol))

    if upper_touches < 2 or lower_touches < 2:
        return None

    return {
        "upper": upper,
        "lower": lower,
        "height": round(height, 2),
        "duration_bars": len(df),
        "upper_touches": upper_touches,
        "lower_touches": lower_touches,
    }


def analyze_structure(df: pd.DataFrame, indicators: Dict) -> Structure:
    """Full structure analysis."""
    swings = find_swings(df, n=SWING_FRACTAL_N)
    atr14 = indicators["atr14"].iloc[-1]
    if pd.isna(atr14):
        atr14 = (df["High"] - df["Low"]).mean()

    supports, resistances = find_support_resistance(df, swings, atr14)
    fib = compute_fibonacci(df, swings)
    events = detect_bos_choch(swings)
    trend_structure = determine_trend_structure(swings)
    range_info = detect_range(df, supports, resistances)

    swing_highs = [s for s in swings if s.kind == "high"]
    swing_lows = [s for s in swings if s.kind == "low"]

    return Structure(
        swings=swings,
        swing_highs=swing_highs,
        swing_lows=swing_lows,
        support_levels=supports,
        resistance_levels=resistances,
        fib_levels=fib,
        bos_choch=events,
        range_info=range_info,
        trend_structure=trend_structure,
        last_swing_high=swing_highs[-1] if swing_highs else None,
        last_swing_low=swing_lows[-1] if swing_lows else None,
        patterns=_detect_patterns_safe(swings, atr14, df["Close"].iloc[-1]),
    )


def _detect_patterns_safe(swings, atr14, close):
    """Safe wrapper for pattern detection."""
    try:
        from .patterns import detect_all_patterns
        return detect_all_patterns(swings, atr14, close)
    except Exception:
        return []


def nearest_level(price: float, levels: List[Dict], direction: str = "above") -> Optional[Dict]:
    """Find nearest level above/below price."""
    candidates = []
    for lvl in levels:
        p = lvl["price"]
        if direction == "above" and p > price:
            candidates.append(lvl)
        elif direction == "below" and p < price:
            candidates.append(lvl)

    if not candidates:
        return None

    candidates.sort(key=lambda x: abs(x["price"] - price))
    return candidates[0]


def structural_targets(structure: Structure, entry: float, direction: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Find TP1 (nearest structural level) and TP2 (next structural level / Fibonacci extension).
    For LONG: R1 = nearest resistance above entry; R2 = next resistance / 1.618 fib.
    For SHORT: S1 = nearest support below entry; S2 = next support / 1.618 fib.
    """
    if direction == "LONG":
        r1 = nearest_level(entry, structure.resistance_levels, "above")
        tp1 = r1["price"] if r1 else None

        # TP2: next resistance or fib 1.618 extension
        r2 = None
        if r1:
            others = [l for l in structure.resistance_levels if l["price"] > r1["price"]]
            if others:
                others.sort(key=lambda x: x["price"])
                r2 = others[0]
        tp2 = r2["price"] if r2 else None
        if tp2 is None and "1.618" in structure.fib_levels:
            fib618 = structure.fib_levels["1.618"]
            if fib618 > entry:
                tp2 = fib618
    else:
        s1 = nearest_level(entry, structure.support_levels, "below")
        tp1 = s1["price"] if s1 else None

        s2 = None
        if s1:
            others = [l for l in structure.support_levels if l["price"] < s1["price"]]
            if others:
                others.sort(key=lambda x: x["price"], reverse=True)
                s2 = others[0]
        tp2 = s2["price"] if s2 else None
        if tp2 is None and "1.618" in structure.fib_levels:
            fib618 = structure.fib_levels["1.618"]
            if fib618 < entry:
                tp2 = fib618

    return (tp1, tp2)
