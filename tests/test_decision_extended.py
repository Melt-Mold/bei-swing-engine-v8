"""Tests for decision engine — extended coverage."""

import pytest
import pandas as pd
import numpy as np

from bei_swing_engine_v8.decision import (
    run_decision_engine, combine_unknown_branch, compute_evidence_state,
    derive_thesis, check_warnings, build_decision_trace, Decision,
)
from bei_swing_engine_v8.setup import Setup
from bei_swing_engine_v8.risk import Tradeability, TradePlan
from bei_swing_engine_v8.structure import Structure
from bei_swing_engine_v8.data import load_ohlcv
from bei_swing_engine_v8.indicators import compute_all_indicators
from bei_swing_engine_v8.structure import analyze_structure
from bei_swing_engine_v8.engine import analyze_ticker


class TestDecisionExtended:
    def test_combine_unknown_both_wait(self):
        d1 = Decision(decision="WAIT", position_branch="NO_POSITION")
        d1.thesis_state = "BULLISH"
        d2 = Decision(decision="WAIT", position_branch="EXISTING_POSITION")
        d2.thesis_state = "BULLISH"
        result = combine_unknown_branch(d1, d2)
        # Both agree → return d1
        assert result.decision == "WAIT"

    def test_combine_unknown_buy_vs_hold(self):
        d1 = Decision(decision="BUY", decision_direction="LONG", position_branch="NO_POSITION")
        d1.thesis_state = "BULLISH"
        d1.evidence_state = "Weak"
        d1.confluence_state = "Weak"
        d2 = Decision(decision="HOLD", position_branch="EXISTING_POSITION")
        d2.thesis_state = "BULLISH"
        result = combine_unknown_branch(d1, d2)
        assert result.decision == "WAIT"
        assert result.dual_branch is not None

    def test_combine_unknown_sell(self):
        d1 = Decision(decision="WAIT", position_branch="NO_POSITION")
        d2 = Decision(decision="SELL", decision_direction="SHORT", position_branch="EXISTING_POSITION")
        d2.reason_codes = ["SELL-01"]
        result = combine_unknown_branch(d1, d2)
        assert result.decision == "SELL"

    def test_combine_unknown_no_setup_vs_hold(self):
        d1 = Decision(decision="NO_SETUP", position_branch="NO_POSITION")
        d2 = Decision(decision="HOLD", position_branch="EXISTING_POSITION")
        result = combine_unknown_branch(d1, d2)
        assert result.decision == "NO_SETUP"

    def test_derive_thesis_insufficient(self, sample_indicators, sample_structure):
        setup = Setup(type="None", direction="NONE", status="NONE")
        thesis = derive_thesis(sample_indicators, sample_structure, setup, "None")
        assert thesis in ("BULLISH", "BEARISH", "NEUTRAL", "INSUFFICIENT", "CONFLICTED")

    def test_derive_thesis_conflicted(self, sample_indicators, sample_structure):
        setup = Setup(type="None", direction="NONE", status="NONE")
        thesis = derive_thesis(sample_indicators, sample_structure, setup, "Conflicted")
        assert thesis == "CONFLICTED"

    def test_check_warnings(self, sample_indicators, sample_structure, default_params):
        setup = Setup(type="Pullback", direction="LONG", status="TRIGGERED")
        tradeability = Tradeability()
        tradeability.plan = TradePlan()
        tradeability.plan.warnings = ["test warning"]
        warnings = check_warnings(sample_indicators, setup, tradeability, "Weak")
        assert isinstance(warnings, list)

    def test_build_decision_trace(self):
        setup = Setup(type="Breakout", direction="LONG", status="TRIGGERED")
        dec = Decision()
        dec.decision = "BUY"
        dec.reason_codes = ["BUY-01"]
        build_decision_trace(dec, setup)
        assert "thesis_state" in dec.trace
        assert "reason_codes" in dec.trace
        assert dec.trace["primary_setup"]["type"] == "Breakout"

    def test_existing_position_hold(self, sample_df, default_params):
        params = {**default_params, "POSITION": "EXISTING_POSITION"}
        result = analyze_ticker(sample_df, params)
        dec = result["decision"]
        assert dec.decision in ("HOLD", "SELL", "WAIT")

    def test_unknown_position_dual_branch(self, sample_df, default_params):
        params = {**default_params, "POSITION": "UNKNOWN"}
        result = analyze_ticker(sample_df, params)
        dec = result["decision"]
        assert dec.position_branch == "UNKNOWN"
