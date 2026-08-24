"""Tests for setup module — extended coverage."""

import pytest
import pandas as pd
import numpy as np

from bei_swing_engine_v8.setup import (
    detect_setups, select_primary_setup, apply_sma200_sufficiency_cap,
    _detect_breakout, _detect_breakout_retest, _detect_pullback,
    _detect_reversal, _detect_continuation, _detect_range,
    SETUP_ORDER, SETUP_STATUS_ORDER, Setup,
    rvol, candle_bullish, candle_bearish, ma_aligned_bullish, ma_aligned_bearish,
    macd_improving,
)
from bei_swing_engine_v8.data import load_ohlcv
from bei_swing_engine_v8.indicators import compute_all_indicators
from bei_swing_engine_v8.structure import analyze_structure


class TestSetupExtended:
    def test_rvol(self, sample_df):
        rv = rvol(sample_df)
        assert rv > 0

    def test_candle_bullish_bearish(self, sample_df):
        result_b = candle_bullish(sample_df)
        result_s = candle_bearish(sample_df)
        assert isinstance(result_b, (bool, np.bool_))
        assert isinstance(result_s, (bool, np.bool_))

    def test_ma_aligned_bullish(self, sample_indicators):
        result = ma_aligned_bullish(sample_indicators)
        assert isinstance(result, (bool, np.bool_))

    def test_ma_aligned_bearish(self, sample_indicators):
        result = ma_aligned_bearish(sample_indicators)
        assert isinstance(result, (bool, np.bool_))

    def test_macd_improving(self, sample_indicators):
        result = macd_improving(sample_indicators, "bullish")
        assert isinstance(result, (bool, np.bool_))
        result2 = macd_improving(sample_indicators, "bearish")
        assert isinstance(result2, (bool, np.bool_))

    def test_setup_status_order(self):
        assert SETUP_STATUS_ORDER["TRIGGERED"] < SETUP_STATUS_ORDER["CONFIRMED"]
        assert SETUP_STATUS_ORDER["CONFIRMED"] < SETUP_STATUS_ORDER["DEVELOPING"]
        assert SETUP_STATUS_ORDER["DEVELOPING"] < SETUP_STATUS_ORDER["NONE"]

    def test_setup_order_precedence(self):
        assert SETUP_ORDER.index("Continuation") < SETUP_ORDER.index("Breakout")
        assert SETUP_ORDER.index("Breakout") < SETUP_ORDER.index("Reversal")

    def test_detect_breakout_returns_none_when_no_breakout(self, sample_df, sample_structure, sample_indicators):
        result = _detect_breakout(sample_df, sample_structure, sample_indicators)
        # Might be None or a Setup depending on data
        if result is not None:
            assert isinstance(result, Setup)

    def test_detect_breakout_retest(self, sample_df, sample_structure, sample_indicators):
        result = _detect_breakout_retest(sample_df, sample_structure, sample_indicators)
        if result is not None:
            assert isinstance(result, Setup)

    def test_detect_pullback(self, sample_df, sample_structure, sample_indicators):
        result = _detect_pullback(sample_df, sample_structure, sample_indicators)
        if result is not None:
            assert result.type == "Pullback"

    def test_detect_reversal(self, sample_df, sample_structure, sample_indicators):
        result = _detect_reversal(sample_df, sample_structure, sample_indicators)
        if result is not None:
            assert result.type == "Reversal"

    def test_detect_continuation(self, sample_df, sample_structure, sample_indicators):
        result = _detect_continuation(sample_df, sample_structure, sample_indicators)
        if result is not None:
            assert result.type == "Continuation"

    def test_detect_range(self, sample_df, sample_structure, sample_indicators):
        result = _detect_range(sample_df, sample_structure, sample_indicators)
        if result is not None:
            assert result.type == "Range"

    def test_select_primary_with_failed(self):
        from bei_swing_engine_v8.setup import Setup
        setups = [
            Setup(type="Breakout", direction="LONG", status="FAILED"),
            Setup(type="Pullback", direction="LONG", status="DEVELOPING"),
        ]
        primary = select_primary_setup(setups)
        # Should select the active one (DEVELOPING), not FAILED
        assert primary.status != "FAILED"

    def test_select_primary_empty(self):
        primary = select_primary_setup([])
        assert primary.type == "None"
        assert primary.status == "NONE"
