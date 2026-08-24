#!/usr/bin/env python
"""
BEI Swing Engine v8.0 — Walk-Forward Optimizer CLI.
Optimizes setup detection parameters using historical data.

Usage:
    python optimizer_app.py --data data-csv-yfinance-cleaned/TLKM.JK_cleaned.csv --step 5
    python optimizer_app.py --data BBRI.csv --step 1 --rvol 0.9 1.0 1.25 --output-dir output
    python optimizer_app.py --help
"""

import argparse
import sys
import os
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bei_swing_engine_v8.optimizer import (
    ParamSet, generate_param_grid, run_optimization,
    render_optimization_report, save_optimization_report,
)
from bei_swing_engine_v8.data import load_ohlcv
from bei_swing_engine_v8.logging_config import setup_logging


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="BEI Swing Engine v8.0 — Walk-Forward Optimizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Optimize single ticker
  python optimizer_app.py --data data-csv-yfinance-cleaned/TLKM.JK_cleaned.csv --step 5

  # Optimize with custom RVOL range
  python optimizer_app.py --data BBRI.csv --rvol 0.8 0.9 1.0 1.25 --step 5

  # Optimize with custom RSI range
  python optimizer_app.py --data TLKM.csv --rsi-long 30 35 40 --rsi-short 60 65 70
        """,
    )
    parser.add_argument("--data", nargs="+", required=True, help="Path(s) to OHLCV CSV file(s)")
    parser.add_argument("--step", type=int, default=5, help="Backtest step (bars)")
    parser.add_argument("--train-pct", type=float, default=0.6, help="Train data percentage (0.5-0.8)")
    parser.add_argument("--windows", type=int, default=3, help="Number of walk-forward windows")
    parser.add_argument("--rvol", nargs="+", type=float, default=[0.9, 1.0, 1.25], help="RVOL thresholds to test")
    parser.add_argument("--rsi-long", nargs="+", type=float, default=[35, 40], help="RSI long thresholds to test")
    parser.add_argument("--rsi-short", nargs="+", type=float, default=[60, 65], help="RSI short thresholds to test")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    args = parser.parse_args(argv)

    setup_logging(level=args.log_level)

    # Validate data files
    data_paths = []
    for p in args.data:
        if os.path.exists(p):
            data_paths.append(p)
        else:
            print(f"ERROR: File not found: {p}", file=sys.stderr)
            sys.exit(1)

    # Generate parameter grid
    param_grid = generate_param_grid(
        rvol_range=args.rvol,
        rsi_long_range=args.rsi_long,
        rsi_short_range=args.rsi_short,
    )

    print(f"=== BEI Swing Engine v8.0 — Walk-Forward Optimizer ===")
    print(f"Data files: {len(data_paths)}")
    print(f"Parameter combinations: {len(param_grid)}")
    print(f"Step: {args.step} | Train: {args.train_pct*100:.0f}% | Windows: {args.windows}")
    print()

    base_params = {
        "MODE": "A", "HORIZON": "SWING", "DIRECTION": "BOTH",
        "POSITION": "NO_POSITION", "MODAL": 10000000, "RISK": 2.0,
        "OUTPUT": "Chat", "IHSG": "None",
    }

    for path in data_paths:
        df = load_ohlcv(path)
        ticker = df["Ticker"].iloc[0]

        print(f"\n--- Optimizing {ticker} ({len(df)} bars) ---")

        report = run_optimization(
            df=df,
            base_params=base_params,
            step=args.step,
            train_pct=args.train_pct,
            n_windows=args.windows,
            param_grid=param_grid,
        )

        # Print summary
        print(f"\nBest Parameters: {report.best_params}")
        m = report.best_result.out_sample_metrics
        print(f"Best Score: {report.best_result.score:.3f}")
        print(f"  Win Rate: {m.get('win_rate', 0):.1f}%")
        print(f"  Expectancy: {m.get('expectancy', 0):.2f}R")
        print(f"  Profit Factor: {m.get('profit_factor', 0):.2f}")
        print(f"  Closed Trades: {m.get('closed_trades', 0):.0f}")
        print(f"  Max DD: {m.get('max_drawdown_pct', 0):.2f}%")
        print(f"  Total Return: {m.get('total_return_pct', 0):.2f}%")
        print(f"  Elapsed: {report.elapsed_seconds:.1f}s")

        # Save report
        save_optimization_report(report, args.output_dir)

    print(f"\nReports saved to: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
