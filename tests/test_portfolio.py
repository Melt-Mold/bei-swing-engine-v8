"""Tests for portfolio backtest module."""

import pytest
import pandas as pd
import numpy as np

from bei_swing_engine_v8.portfolio import (
    run_portfolio_backtest, render_portfolio_report,
    plot_portfolio_equity, plot_portfolio_drawdown, plot_per_ticker_pnl,
    PortfolioResult, PortfolioTrade, TickerStats,
)
from bei_swing_engine_v8.data import load_ohlcv


class TestPortfolio:
    def test_run_portfolio_single_ticker(self, sample_df, default_params):
        result = run_portfolio_backtest([sample_df], default_params, step=5)
        assert result.tickers == ["TLKM"]
        assert result.allocation_mode == "equal_weight"
        assert len(result.metrics) > 0

    def test_run_portfolio_multi_ticker(self, default_params):
        df1 = load_ohlcv("data-csv-yfinance-cleaned/TLKM.JK_cleaned.csv")
        df2 = load_ohlcv("data-csv-yfinance-cleaned/BBRI.JK_cleaned.csv")
        result = run_portfolio_backtest([df1, df2], default_params, step=5)
        assert len(result.tickers) == 2
        assert "TLKM" in result.tickers
        assert "BBRI" in result.tickers
        assert result.metrics["n_tickers"] == 2

    def test_portfolio_metrics_keys(self, sample_df, default_params):
        result = run_portfolio_backtest([sample_df], default_params, step=5)
        m = result.metrics
        assert "total_trades" in m
        assert "closed_trades" in m
        assert "win_rate" in m
        assert "expectancy" in m
        assert "profit_factor" in m
        assert "max_drawdown_pct" in m
        assert "total_return_pct" in m
        assert "sharpe_ratio" in m
        assert "final_equity" in m

    def test_portfolio_equal_weight_allocation(self, default_params):
        df1 = load_ohlcv("data-csv-yfinance-cleaned/TLKM.JK_cleaned.csv")
        df2 = load_ohlcv("data-csv-yfinance-cleaned/BBRI.JK_cleaned.csv")
        result = run_portfolio_backtest([df1, df2], default_params, step=5, allocation_mode="equal_weight")
        # Each ticker should get half the capital
        for ticker in result.tickers:
            stats = result.per_ticker.get(ticker)
            if stats:
                assert stats.allocated_capital == pytest.approx(default_params["MODAL"] / 2)

    def test_portfolio_report_rendering(self, sample_df, default_params):
        result = run_portfolio_backtest([sample_df], default_params, step=5)
        report = render_portfolio_report(result)
        assert "Portfolio Backtest Report" in report
        assert "TLKM" in report
        assert "Per-Ticker Breakdown" in report

    def test_portfolio_equity_chart(self, sample_df, default_params):
        result = run_portfolio_backtest([sample_df], default_params, step=5)
        fig = plot_portfolio_equity(result)
        assert fig is not None

    def test_portfolio_drawdown_chart(self, sample_df, default_params):
        result = run_portfolio_backtest([sample_df], default_params, step=5)
        fig = plot_portfolio_drawdown(result)
        assert fig is not None

    def test_portfolio_pnl_chart(self, sample_df, default_params):
        result = run_portfolio_backtest([sample_df], default_params, step=5)
        fig = plot_per_ticker_pnl(result)
        assert fig is not None

    def test_portfolio_empty(self, default_params):
        result = run_portfolio_backtest([], default_params, step=5)
        assert len(result.tickers) == 0
        assert result.metrics == {}

    def test_portfolio_risk_based_allocation(self, default_params):
        df1 = load_ohlcv("data-csv-yfinance-cleaned/TLKM.JK_cleaned.csv")
        df2 = load_ohlcv("data-csv-yfinance-cleaned/BBRI.JK_cleaned.csv")
        result = run_portfolio_backtest([df1, df2], default_params, step=5, allocation_mode="risk_based")
        assert result.allocation_mode == "risk_based"
