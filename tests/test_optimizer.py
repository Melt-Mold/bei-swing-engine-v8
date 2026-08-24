"""Tests for optimizer module."""

import pytest
import pandas as pd
import numpy as np

from bei_swing_engine_v8.optimizer import (
    ParamSet, OptimizationResult, OptimizationReport,
    generate_param_grid, compute_score, split_walk_forward,
    evaluate_params, run_optimization, render_optimization_report,
    save_optimization_report, _average_metrics,
)
from bei_swing_engine_v8.data import load_ohlcv


class TestOptimizer:
    def test_param_set_defaults(self):
        p = ParamSet()
        assert p.rvol_threshold == 1.0
        assert p.rsi_long_threshold == 35.0
        assert p.rsi_short_threshold == 65.0

    def test_param_set_to_dict(self):
        p = ParamSet(rvol_threshold=1.25, rsi_long_threshold=40)
        d = p.to_dict()
        assert d["rvol_threshold"] == 1.25
        assert d["rsi_long_threshold"] == 40

    def test_param_set_repr(self):
        p = ParamSet()
        s = repr(p)
        assert "RVOL" in s
        assert "RSI_L" in s

    def test_generate_param_grid_default(self):
        grid = generate_param_grid()
        assert len(grid) == 12  # 3 rvol × 2 rsi_long × 2 rsi_short × 1 × 1 × 1

    def test_generate_param_grid_custom(self):
        grid = generate_param_grid(
            rvol_range=[0.9, 1.0],
            rsi_long_range=[35],
            rsi_short_range=[65],
        )
        assert len(grid) == 2

    def test_compute_score_no_trades(self):
        metrics = {"expectancy": 0, "win_rate": 0, "profit_factor": 0, "closed_trades": 0}
        score = compute_score(metrics)
        assert score == 0.0

    def test_compute_score_with_trades(self):
        metrics = {"expectancy": 1.0, "win_rate": 60.0, "profit_factor": 2.0, "closed_trades": 10}
        score = compute_score(metrics)
        assert score > 0

    def test_compute_score_inf_profit_factor(self):
        metrics = {"expectancy": 1.0, "win_rate": 100.0, "profit_factor": float("inf"), "closed_trades": 5}
        score = compute_score(metrics)
        assert score > 0
        assert score <= 1.0

    def test_split_walk_forward_single_window(self, sample_df):
        windows = split_walk_forward(sample_df, n_windows=1)
        assert len(windows) >= 1

    def test_split_walk_forward_multi_window(self, sample_df):
        windows = split_walk_forward(sample_df, n_windows=2)
        assert len(windows) >= 1
        for train, test in windows:
            assert len(train) > 0
            assert len(test) > 0

    def test_average_metrics(self):
        metrics_list = [
            {"win_rate": 50.0, "expectancy": 1.0, "profit_factor": 2.0,
             "max_drawdown_pct": 5.0, "total_return_pct": 10.0,
             "closed_trades": 5, "total_trades": 5,
             "avg_r_multiple": 1.0},
            {"win_rate": 60.0, "expectancy": 2.0, "profit_factor": 3.0,
             "max_drawdown_pct": 3.0, "total_return_pct": 15.0,
             "closed_trades": 10, "total_trades": 10,
             "avg_r_multiple": 1.5},
        ]
        avg = _average_metrics(metrics_list)
        assert avg["win_rate"] == 55.0
        assert avg["expectancy"] == 1.5

    def test_average_metrics_empty(self):
        avg = _average_metrics([])
        assert avg == {}

    def test_render_optimization_report(self):
        report = OptimizationReport(
            ticker="TEST",
            best_params=ParamSet(),
            best_result=OptimizationResult(
                ParamSet(),
                in_sample_metrics={"win_rate": 50, "expectancy": 1.0, "profit_factor": 2.0},
                out_sample_metrics={"win_rate": 45, "expectancy": 0.5, "profit_factor": 1.5,
                                    "avg_r_multiple": 0.5, "max_drawdown_pct": 5.0,
                                    "total_return_pct": 3.0, "closed_trades": 5},
                score=0.5,
            ),
            all_results=[],
            total_combinations=12,
            elapsed_seconds=10.0,
        )
        text = render_optimization_report(report)
        assert "Optimization Report" in text
        assert "TEST" in text
        assert "Best Parameters" in text

    def test_run_optimization_short_data(self):
        df = load_ohlcv("data-csv-yfinance-cleaned/TLKM.JK_cleaned.csv")
        params = {"POSITION": "NO_POSITION", "DIRECTION": "BOTH",
                  "MODAL": 10000000, "RISK": 2.0, "OUTPUT": "Chat", "IHSG": "None",
                  "MODE": "A", "HORIZON": "SWING"}
        grid = generate_param_grid(rvol_range=[1.0], rsi_long_range=[35], rsi_short_range=[65])
        report = run_optimization(df, params, step=5, n_windows=1, param_grid=grid)
        assert report.ticker == "TLKM"
        assert report.total_combinations == 1
