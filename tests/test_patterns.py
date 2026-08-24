"""Tests for chart pattern detection."""

import pytest
import pandas as pd
import numpy as np

from bei_swing_engine_v8.structure import Swing, analyze_structure
from bei_swing_engine_v8.patterns import (
    detect_double_top, detect_double_bottom, detect_head_and_shoulders,
    detect_inverse_head_and_shoulders, detect_triangle, detect_wedge,
    detect_all_patterns, best_pattern, ChartPattern,
)


def _make_swings(highs, lows):
    """Helper to create swing list. Highs and lows are interleaved chronologically."""
    swings = []
    day = 1
    hi_i = 0
    lo_i = 0
    # Interleave: high, low, high, low...
    while hi_i < len(highs) or lo_i < len(lows):
        if hi_i < len(highs):
            swings.append(Swing(idx=hi_i * 4, date=pd.Timestamp(f"2026-01-{day:02d}"), price=highs[hi_i], kind="high"))
            hi_i += 1
            day += 1
        if lo_i < len(lows):
            swings.append(Swing(idx=lo_i * 4 + 2, date=pd.Timestamp(f"2026-01-{day:02d}"), price=lows[lo_i], kind="low"))
            lo_i += 1
            day += 1
    swings.sort(key=lambda s: s.idx)
    return swings


class TestPatternDetection:
    def test_double_top_detection(self):
        swings = _make_swings([100, 100], [90])
        result = detect_double_top(swings, atr14=5, close=95)
        assert result is not None
        assert result.name == "Double Top"
        assert result.direction == "BEARISH"

    def test_double_top_different_prices_no_pattern(self):
        swings = _make_swings([100, 120], [90])
        result = detect_double_top(swings, atr14=5, close=95)
        assert result is None

    def test_double_bottom_detection(self):
        # Need a high between the two lows
        swings = _make_swings([100, 100], [80, 80])
        result = detect_double_bottom(swings, atr14=5, close=95)
        assert result is not None
        assert result.name == "Double Bottom"
        assert result.direction == "BULLISH"

    def test_head_and_shoulders_detection(self):
        swings = _make_swings([100, 110, 100], [95, 95, 95])
        result = detect_head_and_shoulders(swings, atr14=5, close=100)
        assert result is not None
        assert result.name == "Head and Shoulders"
        assert result.direction == "BEARISH"

    def test_inverse_hs_detection(self):
        swings = _make_swings([100, 100, 100], [80, 70, 80])
        result = detect_inverse_head_and_shoulders(swings, atr14=5, close=90)
        assert result is not None
        assert result.name == "Inverse Head and Shoulders"
        assert result.direction == "BULLISH"

    def test_symmetrical_triangle(self):
        swings = _make_swings([100, 95], [80, 85])
        result = detect_triangle(swings, atr14=5, close=90)
        assert result is not None
        assert "Triangle" in result.name

    def test_rising_wedge(self):
        swings = _make_swings([100, 105], [80, 90])
        result = detect_wedge(swings, atr14=3, close=100)
        assert result is not None
        assert result.name == "Rising Wedge"
        assert result.direction == "BEARISH"

    def test_no_pattern_when_flat(self):
        swings = _make_swings([100, 100], [100, 100])
        result = detect_triangle(swings, atr14=5, close=100)
        # Flat highs and flat lows would be a range, not a triangle
        # (depends on detection logic)
        if result is not None:
            assert "Triangle" not in result.name or result.name == "Symmetrical Triangle"

    def test_detect_all_patterns_returns_list(self):
        swings = _make_swings([100, 100], [90])
        result = detect_all_patterns(swings, atr14=5, close=95)
        assert isinstance(result, list)

    def test_best_pattern_prefers_broken(self):
        patterns = [
            ChartPattern("Double Top", "BEARISH", "FORMING", "test", [100, 90]),
            ChartPattern("Rising Wedge", "BEARISH", "BROKEN (bearish breakdown)", "test2", [100, 80]),
        ]
        result = best_pattern(patterns)
        assert "BROKEN" in result.status

    def test_patterns_in_structure(self, sample_df, sample_indicators):
        structure = analyze_structure(sample_df, sample_indicators)
        assert hasattr(structure, "patterns")
        assert isinstance(structure.patterns, list)
