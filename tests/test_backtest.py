"""Tests for backtest engine."""

import pytest

from bei_swing_engine_v8.backtest import run_backtest, validate_as_of_consistency


class TestBacktest:
    def test_backtest_runs(self, sample_df, default_params):
        result = run_backtest(sample_df, default_params, step=5)
        assert result.ticker == "TLKM"
        assert result.metrics is not None
        assert "total_trades" in result.metrics

    def test_as_of_consistency(self, sample_df, default_params):
        mismatches = validate_as_of_consistency(sample_df, default_params, n_checks=3)
        assert len(mismatches) == 0

    def test_backtest_metrics_non_negative_counts(self, sample_df, default_params):
        result = run_backtest(sample_df, default_params, step=5)
        assert result.metrics["total_trades"] >= 0
        assert result.metrics["winning_trades"] >= 0
        assert result.metrics["losing_trades"] >= 0
        assert result.metrics["win_rate"] >= 0
