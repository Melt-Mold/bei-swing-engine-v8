"""Tests for setup detection engine."""

import pytest
import pandas as pd

from bei_swing_engine_v8.setup import (
    detect_setups, select_primary_setup, apply_sma200_sufficiency_cap,
    _detect_breakout, _detect_pullback, _detect_range,
)


class TestSetupDetection:
    def test_detect_setups_returns_list(self, sample_df, sample_structure, sample_indicators):
        setups = detect_setups(sample_df, sample_structure, sample_indicators)
        assert isinstance(setups, list)
        assert len(setups) > 0

    def test_select_primary_setup(self, sample_df, sample_structure, sample_indicators):
        setups = detect_setups(sample_df, sample_structure, sample_indicators)
        primary = select_primary_setup(setups)
        assert primary.status in {"NONE", "DEVELOPING", "CONFIRMED", "TRIGGERED"}
        assert primary.direction in {"LONG", "SHORT", "NONE", "BOTH"}

    def test_sma200_sufficiency_cap(self):
        from bei_swing_engine_v8.setup import Setup
        s = Setup(type="Breakout", direction="LONG", status="TRIGGERED", trigger_price=100)
        capped = apply_sma200_sufficiency_cap([s], bars=100)
        assert capped[0].status == "CONFIRMED"

    def test_sma200_cap_no_effect_when_sufficient(self):
        from bei_swing_engine_v8.setup import Setup
        s = Setup(type="Breakout", direction="LONG", status="TRIGGERED", trigger_price=100)
        capped = apply_sma200_sufficiency_cap([s], bars=250)
        assert capped[0].status == "TRIGGERED"

    def test_breakout_long(self, sample_df, sample_structure, sample_indicators):
        # Force a breakout scenario by temporarily setting close above resistance
        close_backup = sample_df["Close"].iloc[-1]
        if sample_structure.resistance_levels:
            sample_df.iat[-1, sample_df.columns.get_loc("Close")] = sample_structure.resistance_levels[0]["price"] + 1000
            sample_df.iat[-1, sample_df.columns.get_loc("Open")] = sample_df["Close"].iloc[-2]
            sample_df.iat[-1, sample_df.columns.get_loc("High")] = sample_df["Close"].iloc[-1] + 10
            sample_df.iat[-1, sample_df.columns.get_loc("Low")] = sample_df["Close"].iloc[-1] - 10
            setup = _detect_breakout(sample_df, sample_structure, sample_indicators)
            assert setup is not None
            assert setup.direction == "LONG"
        # restore
        sample_df.iat[-1, sample_df.columns.get_loc("Close")] = close_backup
