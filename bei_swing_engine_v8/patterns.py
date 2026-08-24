"""
Chart pattern detection (Tier 2): Double Top/Bottom, Head & Shoulders, Triangle, Wedge.
Uses swing highs/lows from structure analysis.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass

from .structure import Swing


@dataclass
class ChartPattern:
    """Detected chart pattern."""
    name: str
    direction: str  # BULLISH, BEARISH, NEUTRAL
    status: str  # FORMING, CONFIRMED, BROKEN
    description: str
    key_levels: List[float]


def _price_tolerance(price1: float, price2: float, atr14: float) -> float:
    """Tolerance for considering two prices as the same level."""
    return abs(price1 - price2) <= max(0.015 * price1, 0.5 * atr14)


def detect_double_top(swings: List[Swing], atr14: float, close: float) -> Optional[ChartPattern]:
    """
    Double Top: two swing highs at approximately same price, trough between them.
    Bearish reversal. Confirmed when price breaks below the trough (neckline).
    """
    highs = [s for s in swings if s.kind == "high"]
    if len(highs) < 2:
        return None

    # Check last two swing highs
    h1 = highs[-2]
    h2 = highs[-1]

    # Prices should be similar
    if not _price_tolerance(h1.price, h2.price, atr14):
        return None

    # Find the trough between them
    troughs_between = [s for s in swings if s.kind == "low" and h1.idx < s.idx < h2.idx]
    if not troughs_between:
        return None

    neckline = min(t.price for t in troughs_between)
    peak = (h1.price + h2.price) / 2

    # Check if the pattern makes sense (trough significantly below peaks)
    if peak - neckline < 0.5 * atr14:
        return None

    # Status
    if close < neckline:
        status = "BROKEN"
    else:
        status = "FORMING"

    return ChartPattern(
        name="Double Top",
        direction="BEARISH",
        status=status,
        description=f"Two peaks at ~{peak:.0f} with neckline at {neckline:.0f}",
        key_levels=[peak, neckline],
    )


def detect_double_bottom(swings: List[Swing], atr14: float, close: float) -> Optional[ChartPattern]:
    """
    Double Bottom: two swing lows at approximately same price, peak between them.
    Bullish reversal. Confirmed when price breaks above the peak (neckline).
    """
    lows = [s for s in swings if s.kind == "low"]
    if len(lows) < 2:
        return None

    l1 = lows[-2]
    l2 = lows[-1]

    if not _price_tolerance(l1.price, l2.price, atr14):
        return None

    # Find the peak between them
    peaks_between = [s for s in swings if s.kind == "high" and l1.idx < s.idx < l2.idx]
    if not peaks_between:
        return None

    neckline = max(p.price for p in peaks_between)
    base = (l1.price + l2.price) / 2

    if neckline - base < 0.5 * atr14:
        return None

    if close > neckline:
        status = "BROKEN"
    else:
        status = "FORMING"

    return ChartPattern(
        name="Double Bottom",
        direction="BULLISH",
        status=status,
        description=f"Two troughs at ~{base:.0f} with neckline at {neckline:.0f}",
        key_levels=[base, neckline],
    )


def detect_head_and_shoulders(swings: List[Swing], atr14: float, close: float) -> Optional[ChartPattern]:
    """
    Head and Shoulders: three swing highs where middle (head) is highest.
    Bearish reversal. Confirmed when price breaks below neckline (line connecting the two troughs between shoulders).
    """
    highs = [s for s in swings if s.kind == "high"]
    if len(highs) < 3:
        return None

    # Last three highs: left shoulder, head, right shoulder
    ls = highs[-3]
    head = highs[-2]
    rs = highs[-1]

    # Head must be the highest
    if head.price <= ls.price or head.price <= rs.price:
        return None

    # Shoulders should be roughly equal
    if not _price_tolerance(ls.price, rs.price, atr14):
        return None

    # Find troughs between shoulders
    troughs_ls_head = [s for s in swings if s.kind == "low" and ls.idx < s.idx < head.idx]
    troughs_head_rs = [s for s in swings if s.kind == "low" and head.idx < s.idx < rs.idx]

    if not troughs_ls_head or not troughs_head_rs:
        return None

    t1 = min(t.price for t in troughs_ls_head)
    t2 = min(t.price for t in troughs_head_rs)
    neckline = (t1 + t2) / 2

    if head.price - neckline < 0.5 * atr14:
        return None

    if close < neckline:
        status = "BROKEN"
    else:
        status = "FORMING"

    return ChartPattern(
        name="Head and Shoulders",
        direction="BEARISH",
        status=status,
        description=f"Head at {head.price:.0f}, shoulders at ~{(ls.price+rs.price)/2:.0f}, neckline at {neckline:.0f}",
        key_levels=[head.price, neckline],
    )


def detect_inverse_head_and_shoulders(swings: List[Swing], atr14: float, close: float) -> Optional[ChartPattern]:
    """
    Inverse Head and Shoulders: three swing lows where middle (head) is lowest.
    Bullish reversal. Confirmed when price breaks above neckline.
    """
    lows = [s for s in swings if s.kind == "low"]
    if len(lows) < 3:
        return None

    ls = lows[-3]
    head = lows[-2]
    rs = lows[-1]

    # Head must be the lowest
    if head.price >= ls.price or head.price >= rs.price:
        return None

    if not _price_tolerance(ls.price, rs.price, atr14):
        return None

    # Find peaks between shoulders
    peaks_ls_head = [s for s in swings if s.kind == "high" and ls.idx < s.idx < head.idx]
    peaks_head_rs = [s for s in swings if s.kind == "high" and head.idx < s.idx < rs.idx]

    if not peaks_ls_head or not peaks_head_rs:
        return None

    p1 = max(p.price for p in peaks_ls_head)
    p2 = max(p.price for p in peaks_head_rs)
    neckline = (p1 + p2) / 2

    if neckline - head.price < 0.5 * atr14:
        return None

    if close > neckline:
        status = "BROKEN"
    else:
        status = "FORMING"

    return ChartPattern(
        name="Inverse Head and Shoulders",
        direction="BULLISH",
        status=status,
        description=f"Inverse head at {head.price:.0f}, shoulders at ~{(ls.price+rs.price)/2:.0f}, neckline at {neckline:.0f}",
        key_levels=[head.price, neckline],
    )


def detect_triangle(swings: List[Swing], atr14: float, close: float) -> Optional[ChartPattern]:
    """
    Triangle: converging trendlines.
    - Symmetrical: lower highs + higher lows
    - Ascending: flat highs + higher lows
    - Descending: lower highs + flat lows
    Requires at least 2 highs and 2 lows forming a converging pattern.
    """
    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]

    if len(highs) < 2 or len(lows) < 2:
        return None

    # Use last 2-3 of each
    recent_highs = highs[-3:] if len(highs) >= 3 else highs[-2:]
    recent_lows = lows[-3:] if len(lows) >= 3 else lows[-2:]

    # Check convergence: highs should be decreasing or flat, lows increasing or flat
    highs_decreasing = all(recent_highs[i].price > recent_highs[i + 1].price for i in range(len(recent_highs) - 1))
    highs_flat = all(_price_tolerance(recent_highs[i].price, recent_highs[i + 1].price, atr14) for i in range(len(recent_highs) - 1))
    lows_increasing = all(recent_lows[i].price < recent_lows[i + 1].price for i in range(len(recent_lows) - 1))
    lows_flat = all(_price_tolerance(recent_lows[i].price, recent_lows[i + 1].price, atr14) for i in range(len(recent_lows) - 1))

    if highs_decreasing and lows_increasing:
        pattern_type = "Symmetrical Triangle"
        direction = "NEUTRAL"
        # Breakout direction determines
        upper = recent_highs[-1].price
        lower = recent_lows[-1].price
        if close > upper:
            status = "BROKEN (bullish breakout)"
            direction = "BULLISH"
        elif close < lower:
            status = "BROKEN (bearish breakout)"
            direction = "BEARISH"
        else:
            status = "FORMING"
    elif highs_flat and lows_increasing:
        pattern_type = "Ascending Triangle"
        direction = "BULLISH"
        upper = recent_highs[-1].price
        lower = recent_lows[-1].price
        if close > upper:
            status = "BROKEN (bullish breakout)"
        else:
            status = "FORMING"
    elif highs_decreasing and lows_flat:
        pattern_type = "Descending Triangle"
        direction = "BEARISH"
        upper = recent_highs[-1].price
        lower = recent_lows[-1].price
        if close < lower:
            status = "BROKEN (bearish breakdown)"
        else:
            status = "FORMING"
    else:
        return None

    return ChartPattern(
        name=pattern_type,
        direction=direction,
        status=status,
        description=f"{pattern_type}: upper ~{upper:.0f}, lower ~{lower:.0f}",
        key_levels=[upper, lower],
    )


def detect_wedge(swings: List[Swing], atr14: float, close: float) -> Optional[ChartPattern]:
    """
    Wedge: both trendlines sloping in the same direction.
    - Rising wedge: higher highs + higher lows, but highs rising slower → bearish
    - Falling wedge: lower highs + lower lows, but lows falling slower → bullish
    """
    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]

    if len(highs) < 2 or len(lows) < 2:
        return None

    h1, h2 = highs[-2], highs[-1]
    l1, l2 = lows[-2], lows[-1]

    # Rising wedge: both highs and lows increasing, but highs slope < lows slope
    if h2.price > h1.price and l2.price > l1.price:
        high_slope = (h2.price - h1.price) / max(1, h2.idx - h1.idx)
        low_slope = (l2.price - l1.price) / max(1, l2.idx - l1.idx)
        if low_slope > high_slope:
            pattern_type = "Rising Wedge"
            direction = "BEARISH"
            if close < l1.price:
                status = "BROKEN (bearish breakdown)"
            else:
                status = "FORMING"
            return ChartPattern(
                name=pattern_type,
                direction=direction,
                status=status,
                description=f"Rising Wedge: highs {h1.price:.0f}→{h2.price:.0f}, lows {l1.price:.0f}→{l2.price:.0f}",
                key_levels=[h2.price, l2.price],
            )

    # Falling wedge: both highs and lows decreasing, but highs slope > lows slope (steeper lows)
    if h2.price < h1.price and l2.price < l1.price:
        high_slope = (h2.price - h1.price) / max(1, h2.idx - h1.idx)
        low_slope = (l2.price - l1.price) / max(1, l2.idx - l1.idx)
        if abs(high_slope) > abs(low_slope):
            pattern_type = "Falling Wedge"
            direction = "BULLISH"
            if close > h1.price:
                status = "BROKEN (bullish breakout)"
            else:
                status = "FORMING"
            return ChartPattern(
                name=pattern_type,
                direction=direction,
                status=status,
                description=f"Falling Wedge: highs {h1.price:.0f}→{h2.price:.0f}, lows {l1.price:.0f}→{l2.price:.0f}",
                key_levels=[h2.price, l2.price],
            )

    return None


def detect_all_patterns(swings: List[Swing], atr14: float, close: float) -> List[ChartPattern]:
    """
    Run all pattern detectors. Return list of detected patterns (may be empty).
    Only returns the first confirmed pattern from each detector.
    """
    patterns = []

    for detector in [
        detect_double_top,
        detect_double_bottom,
        detect_head_and_shoulders,
        detect_inverse_head_and_shoulders,
        detect_triangle,
        detect_wedge,
    ]:
        try:
            p = detector(swings, atr14, close)
            if p:
                patterns.append(p)
        except Exception:
            pass

    return patterns


def best_pattern(patterns: List[ChartPattern]) -> Optional[ChartPattern]:
    """Select the most relevant pattern (prefer BROKEN > FORMING)."""
    if not patterns:
        return None

    # Prefer BROKEN patterns
    broken = [p for p in patterns if "BROKEN" in p.status]
    if broken:
        return broken[0]

    return patterns[0]
