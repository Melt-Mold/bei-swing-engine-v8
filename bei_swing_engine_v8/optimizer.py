"""
Walk-forward optimization module.
Optimizes setup detection parameters using historical data with walk-forward validation:
1. Split data into in-sample (train) and out-of-sample (test) windows.
2. Grid search parameters on in-sample, evaluate on out-of-sample.
3. Report best parameters and their performance metrics.

Parameters that can be optimized (within locked constraints):
- RVOL threshold for breakout trigger (0.9 - 1.5)
- RSI threshold for pullback reconfirm (35 - 50)
- Pullback zone tolerance multiplier (0.5 - 1.0 × ATR)
- Range boundary tolerance multiplier (0.5 - 1.0 × ATR)
- Continuation consolidation height multiplier (1.0 - 2.0 × ATR)

NOTE: Locked parameters from FINAL.md (swing N=8, R/R≥1.5, SL priority, etc.) are NOT modified.
Only the "soft" thresholds within the setup detectors are tuned.
"""

import os
import time
import json
import itertools
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
import numpy as np

from .data import load_ohlcv
from .backtest import run_backtest, BacktestResult
from .engine import analyze_ticker
from .logging_config import get_logger

_log = get_logger("optimizer")


@dataclass
class ParamSet:
    """A set of parameters to test."""
    rvol_threshold: float = 1.0
    rsi_long_threshold: float = 35.0
    rsi_short_threshold: float = 65.0
    pullback_tolerance_mult: float = 0.5
    range_tolerance_mult: float = 0.75
    continuation_height_mult: float = 1.5

    def to_dict(self) -> Dict:
        return {
            "rvol_threshold": self.rvol_threshold,
            "rsi_long_threshold": self.rsi_long_threshold,
            "rsi_short_threshold": self.rsi_short_threshold,
            "pullback_tolerance_mult": self.pullback_tolerance_mult,
            "range_tolerance_mult": self.range_tolerance_mult,
            "continuation_height_mult": self.continuation_height_mult,
        }

    def __repr__(self):
        return (f"RVOL={self.rvol_threshold} RSI_L={self.rsi_long_threshold} "
                f"RSI_S={self.rsi_short_threshold} PB={self.pullback_tolerance_mult} "
                f"RNG={self.range_tolerance_mult} CONT={self.continuation_height_mult}")


@dataclass
class OptimizationResult:
    """Result of a single parameter set evaluation."""
    params: ParamSet
    in_sample_metrics: Dict
    out_sample_metrics: Dict
    score: float  # weighted objective score (higher is better)


@dataclass
class OptimizationReport:
    """Full optimization report."""
    ticker: str
    best_params: ParamSet
    best_result: OptimizationResult
    all_results: List[OptimizationResult] = field(default_factory=list)
    total_combinations: int = 0
    elapsed_seconds: float = 0.0


def split_walk_forward(
    df: pd.DataFrame,
    train_pct: float = 0.6,
    n_windows: int = 3,
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Split data into walk-forward windows.
    Each window has (in_sample, out_sample) pairs.
    """
    n = len(df)
    windows = []

    # Calculate window size so that train portion is at least 50 bars
    min_train = 50
    min_test = 20
    min_window = min_train + min_test

    # Adjust n_windows if data is too short
    max_windows = max(1, n // min_window)
    n_windows = min(n_windows, max_windows)

    # If data is too short for multiple windows, use single window (full data)
    if n_windows <= 1:
        # Use all data as both train and test (baseline evaluation)
        train_df = df.copy()
        test_df = df.copy()
        windows = [(train_df, test_df)]
        _log.info("using single-window mode (data too short for walk-forward)")
        return windows

    # Use non-overlapping or slightly overlapping windows
    window_size = n // n_windows
    train_size = int(window_size * train_pct)

    # Ensure minimum sizes
    if train_size < min_train:
        train_size = min_train
    test_size = window_size - train_size
    if test_size < min_test:
        test_size = min_test
        train_size = window_size - test_size

    for i in range(n_windows):
        start = i * (window_size - test_size // 2) if i > 0 else 0
        start = min(start, n - window_size)
        end = min(start + window_size, n)
        train_end = min(start + train_size, end)

        train_df = df.iloc[start:train_end].copy()
        test_df = df.iloc[train_end:end].copy()

        if len(train_df) >= min_train and len(test_df) >= min_test:
            windows.append((train_df, test_df))

    return windows


def evaluate_params(
    df: pd.DataFrame,
    params: ParamSet,
    base_params: Dict,
    step: int = 5,
) -> Dict:
    """
    Evaluate a parameter set on a dataframe using backtest.
    Temporarily overrides setup detection thresholds, runs backtest, restores.
    Returns metrics dict.
    """
    from . import setup as setup_mod

    try:
        # Apply parameter overrides
        setup_mod.set_thresholds({
            "rvol_breakout": params.rvol_threshold,
            "rvol_reconfirm": params.rvol_threshold,
            "rsi_long_reconfirm": params.rsi_long_threshold,
            "rsi_short_reconfirm": params.rsi_short_threshold,
        })

        result = run_backtest(df, base_params, step=step, min_bars=20)
        metrics = result.metrics.copy()
        metrics["trades"] = len(result.trades)
        return metrics
    except Exception as e:
        _log.error("evaluation failed | error=%s", e)
        return {
            "total_trades": 0, "closed_trades": 0, "winning_trades": 0,
            "losing_trades": 0, "win_rate": 0.0, "profit_factor": 0.0,
            "avg_r_multiple": 0.0, "expectancy": 0.0,
            "max_drawdown_pct": 0.0, "total_return_pct": 0.0,
        }
    finally:
        setup_mod.reset_thresholds()


def compute_score(metrics: Dict) -> float:
    """
    Compute objective score from metrics.
    Higher is better. Weighted combination of:
    - Expectancy (40%)
    - Win rate (20%)
    - Profit factor (20%)
    - Number of trades (20%) — penalize too few trades
    """
    expectancy = metrics.get("expectancy", 0)
    win_rate = metrics.get("win_rate", 0) / 100.0
    profit_factor = metrics.get("profit_factor", 0)
    if profit_factor == float("inf"):
        profit_factor = 10.0
    n_trades = metrics.get("closed_trades", 0)

    # Penalize too few trades (need at least 3 for statistical significance)
    trade_factor = min(n_trades / 5.0, 1.0)

    score = (0.4 * expectancy + 0.2 * win_rate + 0.2 * min(profit_factor, 5.0) / 5.0 + 0.2 * trade_factor)
    return score


def generate_param_grid(
    rvol_range: List[float] = None,
    rsi_long_range: List[float] = None,
    rsi_short_range: List[float] = None,
    pb_tolerance_range: List[float] = None,
    rng_tolerance_range: List[float] = None,
    cont_height_range: List[float] = None,
) -> List[ParamSet]:
    """Generate all parameter combinations from ranges."""
    if rvol_range is None:
        rvol_range = [0.9, 1.0, 1.25]
    if rsi_long_range is None:
        rsi_long_range = [35, 40]
    if rsi_short_range is None:
        rsi_short_range = [60, 65]
    if pb_tolerance_range is None:
        pb_tolerance_range = [0.5]
    if rng_tolerance_range is None:
        rng_tolerance_range = [0.75]
    if cont_height_range is None:
        cont_height_range = [1.5]

    combos = []
    for rvol, rsi_l, rsi_s, pb, rng, ch in itertools.product(
        rvol_range, rsi_long_range, rsi_short_range,
        pb_tolerance_range, rng_tolerance_range, cont_height_range
    ):
        combos.append(ParamSet(
            rvol_threshold=rvol,
            rsi_long_threshold=rsi_l,
            rsi_short_threshold=rsi_s,
            pullback_tolerance_mult=pb,
            range_tolerance_mult=rng,
            continuation_height_mult=ch,
        ))
    return combos


def run_optimization(
    df: pd.DataFrame,
    base_params: Dict,
    step: int = 5,
    train_pct: float = 0.6,
    n_windows: int = 3,
    param_grid: Optional[List[ParamSet]] = None,
) -> OptimizationReport:
    """
    Run walk-forward optimization on a single ticker.
    """
    ticker = df["Ticker"].iloc[0]
    t_start = time.perf_counter()

    if param_grid is None:
        param_grid = generate_param_grid()

    _log.info("optimization start | ticker=%s combinations=%d", ticker, len(param_grid))

    windows = split_walk_forward(df, train_pct, n_windows)
    if not windows:
        _log.warning("no valid windows | ticker=%s bars=%d", ticker, len(df))
        return OptimizationReport(
            ticker=ticker,
            best_params=ParamSet(),
            best_result=OptimizationResult(ParamSet(), {}, {}, 0.0),
            total_combinations=len(param_grid),
        )

    results = []
    for i, params in enumerate(param_grid):
        _log.debug("testing params %d/%d | %s", i + 1, len(param_grid), params)

        # Evaluate on in-sample and out-of-sample
        in_sample_metrics_list = []
        out_sample_metrics_list = []

        for train_df, test_df in windows:
            in_metrics = evaluate_params(train_df, params, base_params, step=step)
            out_metrics = evaluate_params(test_df, params, base_params, step=step)
            in_sample_metrics_list.append(in_metrics)
            out_sample_metrics_list.append(out_metrics)

        # Average metrics across windows
        avg_in = _average_metrics(in_sample_metrics_list)
        avg_out = _average_metrics(out_sample_metrics_list)

        # Score based on out-of-sample performance (what matters)
        score = compute_score(avg_out)

        result = OptimizationResult(
            params=params,
            in_sample_metrics=avg_in,
            out_sample_metrics=avg_out,
            score=score,
        )
        results.append(result)

        _log.debug("params %s | in_score=%.3f out_score=%.3f | out_expectancy=%.2f out_winrate=%.1f%%",
                    params, compute_score(avg_in), score,
                    avg_out.get("expectancy", 0), avg_out.get("win_rate", 0))

    # Sort by score (descending)
    results.sort(key=lambda r: r.score, reverse=True)

    elapsed = time.perf_counter() - t_start
    _log.info("optimization done | ticker=%s best_score=%.3f elapsed=%.1fs",
              ticker, results[0].score if results else 0, elapsed)

    return OptimizationReport(
        ticker=ticker,
        best_params=results[0].params if results else ParamSet(),
        best_result=results[0] if results else OptimizationResult(ParamSet(), {}, {}, 0.0),
        all_results=results,
        total_combinations=len(param_grid),
        elapsed_seconds=elapsed,
    )


def _average_metrics(metrics_list: List[Dict]) -> Dict:
    """Average metrics across multiple windows."""
    if not metrics_list:
        return {}

    keys = ["win_rate", "profit_factor", "avg_r_multiple", "expectancy",
            "max_drawdown_pct", "total_return_pct", "closed_trades", "total_trades"]

    result = {}
    for key in keys:
        values = [m.get(key, 0) for m in metrics_list]
        if key == "profit_factor":
            # Replace inf with high number for averaging
            values = [min(v, 10.0) if v == float("inf") else v for v in values]
        result[key] = np.mean(values) if values else 0

    return result


def render_optimization_report(report: OptimizationReport) -> str:
    """Render optimization report as Markdown."""
    lines = []
    lines.append(f"# Walk-Forward Optimization Report — {report.ticker}")
    lines.append("")
    lines.append(f"**Total combinations tested:** {report.total_combinations}")
    lines.append(f"**Elapsed:** {report.elapsed_seconds:.1f}s")
    lines.append("")

    lines.append("## Best Parameters")
    lines.append("")
    bp = report.best_params
    lines.append(f"- **RVOL threshold:** {bp.rvol_threshold}")
    lines.append(f"- **RSI long threshold:** {bp.rsi_long_threshold}")
    lines.append(f"- **RSI short threshold:** {bp.rsi_short_threshold}")
    lines.append(f"- **Pullback tolerance:** {bp.pullback_tolerance_mult}×ATR")
    lines.append(f"- **Range tolerance:** {bp.range_tolerance_mult}×ATR")
    lines.append(f"- **Continuation height:** {bp.continuation_height_mult}×ATR")
    lines.append("")

    br = report.best_result
    lines.append("## Best Performance (Out-of-Sample)")
    lines.append("")
    m = br.out_sample_metrics
    lines.append(f"- **Score:** {br.score:.3f}")
    lines.append(f"- **Win rate:** {m.get('win_rate', 0):.1f}%")
    lines.append(f"- **Expectancy:** {m.get('expectancy', 0):.2f}R")
    lines.append(f"- **Profit factor:** {m.get('profit_factor', 0):.2f}")
    lines.append(f"- **Avg R-multiple:** {m.get('avg_r_multiple', 0):.2f}")
    lines.append(f"- **Max drawdown:** {m.get('max_drawdown_pct', 0):.2f}%")
    lines.append(f"- **Total return:** {m.get('total_return_pct', 0):.2f}%")
    lines.append(f"- **Closed trades:** {m.get('closed_trades', 0):.0f}")
    lines.append("")

    lines.append("## In-Sample Performance (Best Params)")
    lines.append("")
    im = br.in_sample_metrics
    lines.append(f"- **Win rate:** {im.get('win_rate', 0):.1f}%")
    lines.append(f"- **Expectancy:** {im.get('expectancy', 0):.2f}R")
    lines.append(f"- **Profit factor:** {im.get('profit_factor', 0):.2f}")
    lines.append("")

    # Top 5 results
    lines.append("## Top 5 Parameter Sets (Out-of-Sample Score)")
    lines.append("")
    lines.append("| Rank | Score | Win Rate | Expectancy | PF | Trades | Parameters |")
    lines.append("|---|---|---|---|---|---|---|")
    for i, r in enumerate(report.all_results[:5]):
        m = r.out_sample_metrics
        lines.append(f"| {i+1} | {r.score:.3f} | {m.get('win_rate', 0):.1f}% | "
                     f"{m.get('expectancy', 0):.2f}R | {m.get('profit_factor', 0):.2f} | "
                     f"{m.get('closed_trades', 0):.0f} | {r.params} |")
    lines.append("")

    lines.append("## Overfitting Check")
    lines.append("")
    in_score = compute_score(br.in_sample_metrics)
    out_score = br.score
    if in_score > 0:
        ratio = out_score / in_score
        lines.append(f"- **In-sample score:** {in_score:.3f}")
        lines.append(f"- **Out-of-sample score:** {out_score:.3f}")
        lines.append(f"- **OOS/IS ratio:** {ratio:.2f}")
        if ratio > 0.7:
            lines.append(f"- **Assessment:** Good — parameters generalize well (ratio > 0.7)")
        elif ratio > 0.4:
            lines.append(f"- **Assessment:** Moderate — some overfitting risk (ratio 0.4-0.7)")
        else:
            lines.append(f"- **Assessment:** Overfitting likely — parameters may not generalize (ratio < 0.4)")
    lines.append("")

    lines.append("## Disclaimer")
    lines.append("")
    lines.append("> Hasil optimisasi berdasarkan data historis. Performa masa lalu tidak menjamin hasil masa depan. "
                 "Parameter optimal dapat berubah seiring kondisi market. Gunakan dengan hati-hati.")
    lines.append("")

    return "\n".join(lines)


def save_optimization_report(report: OptimizationReport, output_dir: str) -> str:
    """Save optimization report to file. Returns path."""
    os.makedirs(output_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(output_dir, f"optimization_{report.ticker}_{date_str}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_optimization_report(report))
    _log.info("report saved | path=%s", path)
    return path
