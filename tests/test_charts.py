"""Tests for charts module."""

import pytest
import pandas as pd
import numpy as np

from bei_swing_engine_v8.charts import (
    plot_equity_curve, plot_price_with_trades, plot_drawdown,
    plot_r_multiples, render_backtest_charts,
)
from bei_swing_engine_v8.backtest import Trade, BacktestResult


class TestCharts:
    def test_plot_equity_curve_empty(self):
        fig = plot_equity_curve([])
        assert fig is not None

    def test_plot_equity_curve_with_data(self):
        curve = [
            (pd.Timestamp("2026-01-01"), 1000000),
            (pd.Timestamp("2026-01-02"), 1010000),
            (pd.Timestamp("2026-01-03"), 990000),
        ]
        fig = plot_equity_curve(curve)
        assert len(fig.data) >= 1
        assert len(fig.data[0].x) == 3

    def test_plot_price_with_trades_empty_df(self):
        df = pd.DataFrame()
        fig = plot_price_with_trades(df, [])
        assert fig is not None

    def test_plot_price_with_trades_and_markers(self, sample_df):
        trades = [
            Trade(
                entry_date=pd.Timestamp("2026-08-14"),
                exit_date=pd.Timestamp("2026-08-18"),
                ticker="TLKM",
                direction="LONG",
                entry_price=2620,
                sl_price=2613,
                tp1_price=2780,
                tp2_price=3205,
                exit_price=2613,
                exit_reason="SL",
                r_multiple=-1.0,
                pnl_pct=-0.25,
            ),
        ]
        fig = plot_price_with_trades(sample_df, trades)
        assert len(fig.data) >= 2  # price line + at least one marker trace

    def test_plot_drawdown_empty(self):
        fig = plot_drawdown([])
        assert fig is not None

    def test_plot_drawdown_with_data(self):
        curve = [
            (pd.Timestamp("2026-01-01"), 1000000),
            (pd.Timestamp("2026-01-02"), 990000),
            (pd.Timestamp("2026-01-03"), 950000),
        ]
        fig = plot_drawdown(curve)
        assert len(fig.data) >= 1

    def test_plot_r_multiples_empty(self):
        fig = plot_r_multiples([])
        assert fig is not None

    def test_plot_r_multiples_with_trades(self):
        trades = [
            Trade(
                entry_date=pd.Timestamp("2026-01-01"),
                exit_date=pd.Timestamp("2026-01-05"),
                ticker="TEST",
                direction="LONG",
                entry_price=100,
                sl_price=95,
                tp1_price=110,
                tp2_price=120,
                exit_price=110,
                exit_reason="TP1",
                r_multiple=2.0,
                pnl_pct=10.0,
            ),
            Trade(
                entry_date=pd.Timestamp("2026-01-06"),
                exit_date=pd.Timestamp("2026-01-10"),
                ticker="TEST",
                direction="LONG",
                entry_price=110,
                sl_price=105,
                tp1_price=120,
                tp2_price=130,
                exit_price=105,
                exit_reason="SL",
                r_multiple=-1.0,
                pnl_pct=-4.5,
            ),
        ]
        fig = plot_r_multiples(trades)
        assert len(fig.data) >= 1
        assert len(fig.data[0].x) == 2

    def test_render_backtest_charts(self, sample_df):
        result = BacktestResult(
            ticker="TLKM",
            trades=[],
            snapshots=[],
            equity_curve=[(pd.Timestamp("2026-01-01"), 1000000)],
            metrics={
                "total_trades": 0, "closed_trades": 0, "open_at_end": 0,
                "winning_trades": 0, "losing_trades": 0, "win_rate": 0.0,
                "profit_factor": 0.0, "avg_r_multiple": 0.0, "expectancy": 0.0,
                "max_drawdown_pct": 0.0, "total_return_pct": 0.0,
                "equity_curve": [(pd.Timestamp("2026-01-01"), 1000000)],
            },
        )
        charts = render_backtest_charts(result, sample_df)
        assert isinstance(charts, list)
        assert len(charts) >= 1
