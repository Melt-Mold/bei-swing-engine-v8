"""Tests for backtest module — extended coverage."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from bei_swing_engine_v8.backtest import (
    run_backtest, generate_trades, compute_metrics, validate_as_of_consistency,
    render_backtest_report, render_backtest_aggregate, BacktestResult, Trade,
)
from bei_swing_engine_v8.data import load_ohlcv


class TestBacktestExtended:
    def test_generate_trades_empty(self):
        trades = generate_trades([], pd.DataFrame())
        assert trades == []

    def test_generate_trades_buy_then_sl(self):
        snapshots = [
            {"date": pd.Timestamp("2026-01-01"), "decision": "BUY", "entry": 100, "sl": 95, "tp1": 110, "tp2": 120, "ticker": "TEST"},
            {"date": pd.Timestamp("2026-01-02"), "decision": "WAIT", "entry": None, "sl": None, "tp1": None, "tp2": None, "ticker": "TEST"},
        ]
        df = pd.DataFrame({
            "Open": [100, 101],
            "High": [101, 102],
            "Low": [99, 94],  # Low hits SL at 95
            "Close": [100, 101],
            "Volume": [1000, 2000],
            "Ticker": "TEST",
        }, index=pd.to_datetime(["2026-01-01", "2026-01-02"]))

        trades = generate_trades(snapshots, df)
        assert len(trades) == 1
        assert trades[0].exit_reason == "SL"
        assert trades[0].r_multiple < 0

    def test_generate_trades_buy_then_tp2(self):
        snapshots = [
            {"date": pd.Timestamp("2026-01-01"), "decision": "BUY", "entry": 100, "sl": 95, "tp1": 110, "tp2": 120, "ticker": "TEST"},
            {"date": pd.Timestamp("2026-01-02"), "decision": "WAIT", "entry": None, "sl": None, "tp1": None, "tp2": None, "ticker": "TEST"},
        ]
        df = pd.DataFrame({
            "Open": [100, 101],
            "High": [101, 125],  # High hits TP2 at 120
            "Low": [99, 100],
            "Close": [100, 120],
            "Volume": [1000, 2000],
            "Ticker": "TEST",
        }, index=pd.to_datetime(["2026-01-01", "2026-01-02"]))

        trades = generate_trades(snapshots, df)
        assert len(trades) == 1
        assert trades[0].exit_reason == "TP2"

    def test_generate_trades_sell_signal_exit(self):
        snapshots = [
            {"date": pd.Timestamp("2026-01-01"), "decision": "BUY", "entry": 100, "sl": 95, "tp1": 110, "tp2": 120, "ticker": "TEST"},
            {"date": pd.Timestamp("2026-01-02"), "decision": "SELL", "entry": None, "sl": None, "tp1": None, "tp2": None, "ticker": "TEST"},
        ]
        df = pd.DataFrame({
            "Open": [100, 101],
            "High": [101, 102],
            "Low": [99, 100],
            "Close": [100, 101],
            "Volume": [1000, 2000],
            "Ticker": "TEST",
        }, index=pd.to_datetime(["2026-01-01", "2026-01-02"]))

        trades = generate_trades(snapshots, df)
        assert len(trades) == 1
        assert trades[0].exit_reason == "SELL_SIGNAL"

    def test_compute_metrics_no_trades(self):
        metrics = compute_metrics([])
        assert metrics["total_trades"] == 0
        assert metrics["win_rate"] == 0.0

    def test_compute_metrics_with_wins_losses(self):
        trades = [
            Trade(entry_date=pd.Timestamp("2026-01-01"), exit_date=pd.Timestamp("2026-01-05"),
                  ticker="TEST", direction="LONG", entry_price=100, sl_price=95,
                  tp1_price=110, tp2_price=120, exit_price=110, exit_reason="TP1",
                  r_multiple=2.0, pnl_pct=10.0),
            Trade(entry_date=pd.Timestamp("2026-01-06"), exit_date=pd.Timestamp("2026-01-10"),
                  ticker="TEST", direction="LONG", entry_price=110, sl_price=105,
                  tp1_price=120, tp2_price=130, exit_price=105, exit_reason="SL",
                  r_multiple=-1.0, pnl_pct=-4.5),
        ]
        metrics = compute_metrics(trades, initial_equity=1000000)
        assert metrics["total_trades"] == 2
        assert metrics["closed_trades"] == 2
        assert metrics["winning_trades"] == 1
        assert metrics["losing_trades"] == 1
        assert metrics["win_rate"] == 50.0
        assert metrics["profit_factor"] == 2.0
        assert 0 < metrics["max_drawdown_pct"] <= 100

    def test_compute_metrics_excludes_end_trades(self):
        trades = [
            Trade(entry_date=pd.Timestamp("2026-01-01"), exit_date=pd.Timestamp("2026-01-05"),
                  ticker="TEST", direction="LONG", entry_price=100, sl_price=95,
                  tp1_price=110, tp2_price=120, exit_price=100, exit_reason="END",
                  r_multiple=0.0, pnl_pct=0.0),
        ]
        metrics = compute_metrics(trades)
        assert metrics["closed_trades"] == 0
        assert metrics["open_at_end"] == 1

    def test_render_backtest_report(self, sample_df, default_params):
        result = run_backtest(sample_df, default_params, step=5)
        report = render_backtest_report(result)
        assert "Backtest Report" in report
        assert result.ticker in report

    def test_render_backtest_aggregate(self, sample_df, default_params):
        result = run_backtest(sample_df, default_params, step=5)
        report = render_backtest_aggregate([result])
        assert "Aggregate" in report
        assert result.ticker in report
