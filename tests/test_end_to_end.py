"""End-to-end integration tests."""

import os

from bei_swing_engine_v8.engine import run_analysis


class TestEndToEnd:
    def test_single_ticker_analysis(self):
        path = os.path.join("data-csv-yfinance-cleaned", "TLKM.JK_cleaned.csv")
        params = "MODE=A\nHORIZON=SWING\nDIRECTION=BOTH\nPOSITION=NO_POSITION\nMODAL=10000000\nRISK=2\nOUTPUT=Chat\nIHSG=None"
        output = run_analysis([path], params_text=params, output_dir="output_test")
        assert "BEI Swing Engine v8.0" in output
        assert "TLKM" in output

    def test_multi_ticker_screening(self):
        paths = [
            os.path.join("data-csv-yfinance-cleaned", "TLKM.JK_cleaned.csv"),
            os.path.join("data-csv-yfinance-cleaned", "BBRI.JK_cleaned.csv"),
        ]
        params = "MODE=C\nHORIZON=SWING\nDIRECTION=BOTH\nPOSITION=NO_POSITION\nMODAL=10000000\nRISK=2\nOUTPUT=Chat\nIHSG=None"
        output = run_analysis(paths, params_text=params, output_dir="output_test")
        assert "Screening Summary" in output
        assert "TLKM" in output
        assert "BBRI" in output
        assert "Executive Summary" not in output
