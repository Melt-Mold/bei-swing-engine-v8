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

    def test_g0_insufficient_data_short_df(self, sample_df, sample_indicators, sample_structure, default_params):
        short_df = sample_df.iloc[:10].copy()
        setup = Setup(type="None", direction="NONE", status="NONE")
        tradeability = Tradeability()
        result = run_decision_engine(short_df, sample_indicators, sample_structure, setup, tradeability, default_params)
        assert result.decision == "INSUFFICIENT_DATA"
        assert "INS-D-01" in result.reason_codes

    def test_neutral_no_setup_returns_nosetup(self, sample_df, sample_indicators, sample_structure, default_params):
        # Force NEUTRAL thesis by using a NONE setup with no clear trend
        setup = Setup(type="None", direction="NONE", status="NONE")
        tradeability = Tradeability()
        result = run_decision_engine(sample_df, sample_indicators, sample_structure, setup, tradeability, default_params)
        if result.thesis_state == "NEUTRAL":
            assert result.decision == "NO_SETUP"
            assert "NOSETUP-01" in result.reason_codes

    def test_confirmed_setup_evidence_contract_failure(self, sample_df, sample_indicators, sample_structure, default_params):
        setup = Setup(type="Breakout", direction="LONG", status="CONFIRMED",
                      trigger_price=sample_df["Close"].iloc[-1], invalidation_price=sample_df["Close"].iloc[-1] - 100)
        tradeability = Tradeability(state="TRADEABLE", reason="BUY-01: Standard tradeable entry")
        result = run_decision_engine(sample_df, sample_indicators, sample_structure, setup, tradeability, default_params)
        # If evidence contract is not met, CONFIRMED should also emit WAIT-05
        if result.decision == "WAIT":
            assert "WAIT-05" in result.reason_codes

    def test_existing_position_held_short(self, sample_df, sample_indicators, sample_structure, default_params):
        setup = Setup(type="Breakout", direction="LONG", status="TRIGGERED",
                      trigger_price=sample_df["Close"].iloc[-1], invalidation_price=sample_df["Close"].iloc[-1] - 100)
        tradeability = Tradeability(state="TRADEABLE", reason="BUY-01: Standard tradeable entry")
        result = run_decision_engine(
            sample_df, sample_indicators, sample_structure, setup, tradeability, default_params,
            position_branch="EXISTING_POSITION", held_position_direction="SHORT",
        )
        # LONG setup vs held SHORT -> opposing setup -> SELL
        assert result.decision == "SELL"
        assert "SELL-02" in result.reason_codes

    def test_decision_trace_includes_trade_plan(self, sample_df, default_params):
        result = analyze_ticker(sample_df, default_params)
        dec = result["decision"]
        assert "trade_plan" in dec.trace
        assert dec.trace["trade_plan"]["entry"] == dec.entry
