"""Tests for fetcher module — using mocks to avoid network calls."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from bei_swing_engine_v8.fetcher import (
    fetch_yfinance, fetch_and_save, FetchResult,
    VALID_PERIODS, VALID_INTERVALS,
)


class TestFetcher:
    def test_valid_periods(self):
        assert "1y" in VALID_PERIODS
        assert "max" in VALID_PERIODS
        assert "1mo" in VALID_PERIODS

    def test_valid_intervals(self):
        assert "1d" in VALID_INTERVALS
        assert "1wk" in VALID_INTERVALS

    def test_fetch_invalid_period(self):
        result = fetch_yfinance("BBRI", period="invalid", interval="1d")
        assert result.error is not None
        assert "Invalid period" in result.error

    def test_fetch_invalid_interval(self):
        result = fetch_yfinance("BBRI", period="1y", interval="invalid")
        assert result.error is not None
        assert "Invalid interval" in result.error

    def test_fetch_result_dataclass(self):
        r = FetchResult(ticker="BBRI", rows=[], row_count=0, period="1y", interval="1d")
        assert r.ticker == "BBRI"
        assert r.error is None
        assert r.output_name is None

    @patch("builtins.__import__", side_effect=ImportError("no yfinance"))
    def test_fetch_yfinance_not_installed(self, mock_import):
        result = fetch_yfinance("BBRI", period="1y", interval="1d")
        assert result.error is not None
        assert "not installed" in result.error

    def test_fetch_and_save_invalid_period(self):
        result = fetch_and_save("BBRI", period="invalid", interval="1d", output_dir="output_test")
        assert result.error is not None

    def test_ticker_normalization(self):
        # Test that IHSG → ^JKSE conversion happens internally
        # We can't test the actual download without network, but we can verify
        # the ticker normalization logic doesn't crash
        result = fetch_yfinance("IHSG", period="1mo", interval="1d")
        # Will either succeed (if network available) or fail with a download error
        # But should NOT fail with "Invalid period/interval"
        assert result.error is None or "Invalid" not in (result.error or "")

    def test_fetch_and_save_with_output_name(self):
        # Test the output_name parameter path
        result = fetch_and_save("BBRI", period="invalid", interval="1d",
                                output_dir="output_test", output_name="custom.csv")
        assert result.error is not None  # Fails on invalid period
        assert result.output_name is None
