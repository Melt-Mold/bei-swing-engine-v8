"""Tests for risk module."""

import pytest
import pandas as pd
import numpy as np

from bei_swing_engine_v8.risk import (
    compute_sl, compute_trade_plan, assess_tradeability, TradePlan, Tradeability,
)
from bei_swing_engine_v8.setup import Setup
from bei_swing_engine_v8.structure import Structure, Swing
from bei_swing_engine_v8.data import load_ohlcv
from bei_swing_engine_v8.indicators import compute_all_indicators
from bei_swing_engine_v8.structure import analyze_structure


class TestRisk:
    def test_compute_sl_structural(self, sample_df, sample_indicators, sample_structure):
        setup = Setup(
            type="Pullback", direction="LONG", status="TRIGGERED",
            trigger_price=2610, invalidation_price=2600, basis_level=2634,
        )
        atr14 = sample_indicators["atr14"].iloc[-1]
        sl = compute_sl(2610, "LONG", setup, sample_structure, atr14)
        assert sl is not None
        assert sl < 2610  # SL below entry for LONG

    def test_compute_sl_short(self, sample_df, sample_indicators, sample_structure):
        setup = Setup(
            type="Range", direction="SHORT", status="TRIGGERED",
            trigger_price=7375, invalidation_price=7500, basis_level=7450,
        )
        atr14 = sample_indicators["atr14"].iloc[-1]
        sl = compute_sl(7375, "SHORT", setup, sample_structure, atr14)
        assert sl is not None
        assert sl > 7375  # SL above entry for SHORT

    def test_compute_sl_atr_fallback(self):
        structure = Structure()
        setup = Setup(type="Test", direction="LONG", status="TRIGGERED",
                      invalidation_price=None)
        sl = compute_sl(1000, "LONG", setup, structure, atr14=10)
        assert sl == 1000 - 2.0 * 10  # 980

    def test_compute_sl_short_atr_fallback(self):
        structure = Structure()
        setup = Setup(type="Test", direction="SHORT", status="TRIGGERED",
                      invalidation_price=None)
        sl = compute_sl(1000, "SHORT", setup, structure, atr14=10)
        assert sl == 1000 + 2.0 * 10  # 1020

    def test_assess_tradeability_no_setup(self):
        setup = Setup(type="None", direction="NONE", status="NONE")
        result = assess_tradeability(sample_df_fixture(), setup, Structure(), {}, 10000000, 2.0, [])
        assert result.state == "NO_SETUP"

    def test_assess_tradeability_developing(self):
        setup = Setup(type="Range", direction="LONG", status="DEVELOPING")
        result = assess_tradeability(sample_df_fixture(), setup, Structure(), {}, 10000000, 2.0, [])
        assert result.state in ("NOT_APPLICABLE", "NO_SETUP")

    def test_trade_plan_dataclass(self):
        plan = TradePlan()
        assert plan.entry is None
        assert plan.sl is None
        assert plan.rr_status == "N/A"

    def test_tradeability_dataclass(self):
        t = Tradeability()
        assert t.state == "NOT_APPLICABLE"
        assert isinstance(t.warnings, list)


def sample_df_fixture():
    """Helper to get a sample df without pytest fixture overhead."""
    return load_ohlcv("data-csv-yfinance-cleaned/TLKM.JK_cleaned.csv")
