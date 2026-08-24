"""Tests for engine module — extended coverage."""

import pytest
import pandas as pd
import os
import tempfile

from bei_swing_engine_v8.engine import (
    analyze_ticker, render_ticker_report, run_analysis,
    parse_params, default_params, _slice_indicators, _analyze_one,
)
from bei_swing_engine_v8.data import load_ohlcv


class TestEngineExtended:
    def test_default_params(self):
        params = default_params()
        assert params["MODE"] == "A"
        assert params["HORIZON"] == "SWING"
        assert params["MODAL"] == 10_000_000

    def test_parse_params_basic(self):
        text = "MODE=B\nHORIZON=DAY\nDIRECTION=LONG\nPOSITION=EXISTING_POSITION\nMODAL=5000000\nRISK=1.5\nOUTPUT=HTML\nIHSG=None"
        params = parse_params(text)
        assert params["MODE"] == "B"
        assert params["HORIZON"] == "DAY"
        assert params["DIRECTION"] == "LONG"
        assert params["POSITION"] == "EXISTING_POSITION"
        assert params["MODAL"] == 5000000
        assert params["RISK"] == 1.5
        assert params["OUTPUT"] == "HTML"

    def test_parse_params_empty(self):
        params = parse_params("")
        assert params["MODE"] == "A"

    def test_parse_params_jt_shorthand(self):
        params = parse_params("MODAL=10jt")
        assert params["MODAL"] == 10000000

    def test_parse_params_invalid_modal(self):
        params = parse_params("MODAL=abc")
        assert params["MODAL"] == 10_000_000  # default

    def test_parse_params_invalid_risk(self):
        params = parse_params("RISK=xyz")
        assert params["RISK"] == 2.0  # default

    def test_slice_indicators(self, sample_df, sample_indicators):
        cutoff = sample_df.index[100]
        sliced = _slice_indicators(sample_indicators, cutoff)
        assert len(sliced["ema9"]) <= 101  # up to cutoff

    def test_slice_indicators_preserves_strings(self, sample_indicators):
        cutoff = sample_indicators["ema9"].index[100]
        sliced = _slice_indicators(sample_indicators, cutoff)
        # String values should be preserved
        assert isinstance(sliced.get("volume_synthesis", ""), str) or sliced.get("volume_synthesis") is not None

    def test_render_ticker_report_mode_a(self, sample_df, default_params):
        result = analyze_ticker(sample_df, default_params)
        report = render_ticker_report(result, "Chat", mode="A")
        assert "BEI Swing Engine" in report

    def test_render_ticker_report_mode_b(self, sample_df, default_params):
        result = analyze_ticker(sample_df, default_params)
        report = render_ticker_report(result, "Chat", mode="B")
        assert "Kalkulasi" in report

    def test_render_ticker_report_html(self, sample_df, default_params):
        result = analyze_ticker(sample_df, default_params)
        report = render_ticker_report(result, "HTML", mode="A")
        assert "<html" in report.lower() or "<!DOCTYPE" in report

    def test_render_ticker_report_error(self):
        result = {"ticker": "TEST", "status": "ERROR", "reason": "test error"}
        report = render_ticker_report(result, "Chat", mode="A")
        assert "ERROR" in report
        assert "test error" in report

    def test_analyze_one_success(self, sample_ticker_path, default_params):
        result = _analyze_one(sample_ticker_path, default_params, None)
        assert result["ticker"] == "TLKM"
        assert result["status"] == "OK"

    def test_analyze_one_error(self, default_params):
        result = _analyze_one("nonexistent.csv", default_params, None)
        assert result["status"] == "ERROR"

    def test_analyze_ticker_insufficient_data(self, default_params):
        df = pd.DataFrame({
            "Open": [100, 101],
            "High": [101, 102],
            "Low": [99, 100],
            "Close": [100, 101],
            "Volume": [1000, 2000],
            "Ticker": "TEST",
        }, index=pd.to_datetime(["2026-01-01", "2026-01-02"]))
        result = analyze_ticker(df, default_params)
        assert result["status"] == "INSUFFICIENT_DATA"

    def test_analyze_ticker_with_precomputed(self, sample_df, default_params):
        from bei_swing_engine_v8.indicators import compute_all_indicators
        from bei_swing_engine_v8.structure import analyze_structure
        full_inds = compute_all_indicators(sample_df)
        full_struct = analyze_structure(sample_df, full_inds)
        precomputed = {"indicators": full_inds, "structure": full_struct}
        # Use full df (cutoff = last date)
        result = analyze_ticker(sample_df, default_params, precomputed=precomputed)
        assert result["status"] == "OK"

    def test_analyze_ticker_build_output_rows_false(self, sample_df, default_params):
        result = analyze_ticker(sample_df, default_params, build_output_rows=False)
        assert result["indicator_rows"] == []

    def test_run_analysis_mode_c(self):
        params = "MODE=C\nHORIZON=SWING\nDIRECTION=BOTH\nPOSITION=NO_POSITION\nMODAL=10000000\nRISK=2\nOUTPUT=Chat\nIHSG=None"
        output = run_analysis(
            data_paths=["data-csv-yfinance-cleaned/TLKM.JK_cleaned.csv"],
            params_text=params,
            output_dir="output_test",
        )
        assert "Screening Summary" in output

    def test_run_analysis_mode_b(self):
        params = "MODE=B\nHORIZON=SWING\nDIRECTION=BOTH\nPOSITION=NO_POSITION\nMODAL=10000000\nRISK=2\nOUTPUT=Chat\nIHSG=None"
        output = run_analysis(
            data_paths=["data-csv-yfinance-cleaned/TLKM.JK_cleaned.csv"],
            params_text=params,
            output_dir="output_test",
        )
        assert "Kalkulasi" in output
        assert "Executive Summary" not in output
