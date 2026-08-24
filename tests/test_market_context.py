"""Tests for market_context module."""

import pytest
import pandas as pd

from bei_swing_engine_v8.market_context import analyze_market_regime
from bei_swing_engine_v8.data import load_ohlcv


class TestMarketContext:
    def test_no_ihsg_data(self):
        result = analyze_market_regime(None)
        assert "N/A" in result["regime"]
        assert result["weekly_close"] is None

    def test_insufficient_ihsg(self):
        df = pd.DataFrame({
            "Open": [100, 101, 102],
            "High": [101, 102, 103],
            "Low": [99, 100, 101],
            "Close": [100, 101, 102],
            "Volume": [1000, 2000, 3000],
            "Ticker": "IHSG",
        }, index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]))
        result = analyze_market_regime(df)
        assert "N/A" in result["regime"]

    def test_ihsg_regime(self):
        path = "data-csv-yfinance-cleaned/IHSG-JKSE_cleaned.csv"
        import os
        if not os.path.exists(path):
            pytest.skip("IHSG data not available")
        df = load_ohlcv(path)
        result = analyze_market_regime(df)
        assert result["regime"] != "N/A — no IHSG/JKSE data uploaded"
        assert result["trend"] in ("Uptrend", "Downtrend", "Sideways", "N/A")
        assert result["weekly_close"] is not None
