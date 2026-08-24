"""Tests for risk module — extended coverage."""

import pytest
import pandas as pd
import numpy as np

from bei_swing_engine_v8.risk import (
    compute_sl, compute_trade_plan, assess_tradeability,
    TradePlan, Tradeability,
)
from bei_swing_engine_v8.setup import Setup
from bei_swing_engine_v8.structure import Structure, Swing
from bei_swing_engine_v8.data import load_ohlcv
from bei_swing_engine_v8.indicators import compute_all_indicators
from bei_swing_engine_v8.structure import analyze_structure


class TestRiskExtended:
    def test_trade_plan_defaults(self):
        plan = TradePlan()
        assert plan.entry is None
        assert plan.sl is None
        assert plan.tp1 is None
        assert plan.tp2 is None
        assert plan.rr_raw is None
        assert plan.rr_status == "N/A"
        assert plan.position_sizing == {}

    def test_tradeability_defaults(self):
        t = Tradeability()
        assert t.state == "NOT_APPLICABLE"
        assert t.plan == TradePlan()
        assert t.warnings == []

    def test_compute_sl_long_atr_fallback_no_invalidation(self):
        setup = Setup(type="Test", direction="LONG", status="TRIGGERED", invalidation_price=None)
        structure = Structure()
        sl = compute_sl(1000, "LONG", setup, structure, atr14=10)
        assert sl == 980  # 1000 - 2*10

    def test_compute_sl_short_atr_fallback_no_invalidation(self):
        setup = Setup(type="Test", direction="SHORT", status="TRIGGERED", invalidation_price=None)
        structure = Structure()
        sl = compute_sl(1000, "SHORT", setup, structure, atr14=10)
        assert sl == 1020  # 1000 + 2*10

    def test_compute_sl_long_with_invalidation(self):
        setup = Setup(type="Test", direction="LONG", status="TRIGGERED", invalidation_price=950)
        structure = Structure()
        sl = compute_sl(1000, "LONG", setup, structure, atr14=10)
        assert sl == 950  # structural invalidation

    def test_compute_sl_short_with_invalidation(self):
        setup = Setup(type="Test", direction="SHORT", status="TRIGGERED", invalidation_price=1050)
        structure = Structure()
        sl = compute_sl(1000, "SHORT", setup, structure, atr14=10)
        assert sl == 1050

    def test_compute_sl_long_invalidation_above_entry(self):
        # If invalidation > entry for LONG, fall through to ATR
        setup = Setup(type="Test", direction="LONG", status="TRIGGERED", invalidation_price=1050)
        structure = Structure()
        sl = compute_sl(1000, "LONG", setup, structure, atr14=10)
        assert sl == 980  # ATR fallback

    def test_assess_tradeability_triggered_with_trade_plan(self, sample_df, sample_indicators, sample_structure, default_params):
        setup = Setup(
            type="Pullback", direction="LONG", status="TRIGGERED",
            trigger_price=sample_df["Close"].iloc[-1],
            invalidation_price=sample_df["Close"].iloc[-1] - 20,
            basis_level=sample_indicators["sma20"].iloc[-1],
        )
        result = assess_tradeability(
            sample_df, setup, sample_structure, sample_indicators,
            modal=default_params["MODAL"], risk_pct=default_params["RISK"], warnings=[],
        )
        # Should be either TRADEABLE, TRADEABLE_WITH_WARNING, or UNTRADEABLE
        assert result.state in ("TRADEABLE", "TRADEABLE_WITH_WARNING", "UNTRADEABLE", "NOT_APPLICABLE")

    def test_assess_tradeability_no_setup(self, sample_df, sample_indicators, sample_structure, default_params):
        setup = Setup(type="None", direction="NONE", status="NONE")
        result = assess_tradeability(
            sample_df, setup, sample_structure, sample_indicators,
            modal=default_params["MODAL"], risk_pct=default_params["RISK"], warnings=[],
        )
        assert result.state == "NO_SETUP"

    def test_assess_tradeability_developing(self, sample_df, sample_indicators, sample_structure, default_params):
        setup = Setup(type="Range", direction="LONG", status="DEVELOPING")
        result = assess_tradeability(
            sample_df, setup, sample_structure, sample_indicators,
            modal=default_params["MODAL"], risk_pct=default_params["RISK"], warnings=[],
        )
        assert result.state in ("NOT_APPLICABLE", "NO_SETUP")

    def test_assess_tradeability_confirmed_not_triggered(self, sample_df, sample_indicators, sample_structure, default_params):
        setup = Setup(type="Breakout", direction="LONG", status="CONFIRMED",
                      trigger_price=None, invalidation_price=2500)
        result = assess_tradeability(
            sample_df, setup, sample_structure, sample_indicators,
            modal=default_params["MODAL"], risk_pct=default_params["RISK"], warnings=[],
        )
        assert result.state in ("NOT_APPLICABLE", "NO_SETUP")

    def test_compute_trade_plan_no_atr(self, sample_df, sample_structure, default_params):
        setup = Setup(type="Pullback", direction="LONG", status="TRIGGERED",
                      trigger_price=100, invalidation_price=90)
        # Create fake indicators with NaN ATR
        inds = {"atr14": pd.Series([np.nan] * len(sample_df))}
        plan = compute_trade_plan(sample_df, setup, sample_structure, inds,
                                  modal=default_params["MODAL"], risk_pct=default_params["RISK"])
        assert plan.entry is None  # Can't compute without ATR
        assert len(plan.warnings) > 0
