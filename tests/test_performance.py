"""Performance tests for BEI Swing Engine v8.0."""
import time
import os

import pytest

from bei_swing_engine_v8.data import load_ohlcv
from bei_swing_engine_v8.indicators import compute_all_indicators
from bei_swing_engine_v8.structure import analyze_structure, find_swings
from bei_swing_engine_v8.engine import analyze_ticker

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data-csv-yfinance-5y")


@pytest.fixture(scope="module")
def df_5y():
    path = os.path.join(DATA_DIR, "TLKM.JK_cleaned.csv")
    if not os.path.exists(path):
        pytest.skip("5-year dataset not available")
    return load_ohlcv(path)


class TestPerformance:
    def test_find_swings_under_50ms(self, df_5y):
        t0 = time.perf_counter()
        swings = find_swings(df_5y, n=8)
        elapsed = (time.perf_counter() - t0) * 1000
        assert elapsed < 50, f"find_swings took {elapsed:.1f}ms (expected <50ms)"
        assert len(swings) > 0

    def test_analyze_structure_under_100ms(self, df_5y):
        indicators = compute_all_indicators(df_5y)
        t0 = time.perf_counter()
        structure = analyze_structure(df_5y, indicators)
        elapsed = (time.perf_counter() - t0) * 1000
        assert elapsed < 100, f"analyze_structure took {elapsed:.1f}ms (expected <100ms)"
        assert len(structure.swings) > 0

    def test_full_analysis_under_500ms(self, df_5y):
        params = {
            "MODE": "A", "HORIZON": "SWING", "DIRECTION": "BOTH",
            "POSITION": "NO_POSITION", "MODAL": 10000000, "RISK": 2.0,
            "OUTPUT": "Chat", "IHSG": "None",
        }
        t0 = time.perf_counter()
        analyze_ticker(df_5y, params)
        elapsed = (time.perf_counter() - t0) * 1000
        assert elapsed < 500, f"analyze_ticker took {elapsed:.1f}ms (expected <500ms)"
