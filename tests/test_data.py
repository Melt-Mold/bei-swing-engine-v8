"""Tests for data ingestion and validation."""

import os
import pytest
import pandas as pd

from bei_swing_engine_v8.data import load_ohlcv, validate_data, extract_ticker_from_path


class TestDataIngestion:
    def test_extract_ticker_from_filename(self):
        assert extract_ticker_from_path("BBRI.JK_cleaned.csv") == "BBRI"
        assert extract_ticker_from_path("IHSG-JKSE_cleaned.csv") == "IHSG"
        assert extract_ticker_from_path("TLKM_cleaned.csv") == "TLKM"

    def test_load_ohlcv_columns(self, sample_df):
        assert set(sample_df.columns) >= {"Open", "High", "Low", "Close", "Volume", "Ticker"}
        assert sample_df["Ticker"].iloc[0] == "TLKM"

    def test_load_ohlcv_sorted(self, sample_df):
        assert sample_df.index.is_monotonic_increasing

    def test_validate_data_sufficient(self, sample_df):
        v = validate_data(sample_df)
        assert v["status"] in {"OK", "INSUFFICIENT"}
        assert v["bars"] == len(sample_df)
        assert v["bars"] >= 200  # sample data has 240 bars

    def test_validate_data_insufficient(self):
        df = pd.DataFrame({
            "Open": [100, 101],
            "High": [102, 103],
            "Low": [99, 100],
            "Close": [101, 102],
            "Volume": [1000, 2000],
            "Ticker": "TEST",
        }, index=pd.to_datetime(["2026-01-01", "2026-01-02"]))
        v = validate_data(df)
        assert v["status"] == "ERROR"
        assert v["bars"] < 20
