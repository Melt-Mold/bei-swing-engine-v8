"""
Command-line interface.
"""

import argparse
import os
import sys
import glob
from pathlib import Path

from .engine import run_analysis


def main(argv=None):
    parser = argparse.ArgumentParser(description="BEI Swing Engine v8.0")
    parser.add_argument("--data", nargs="+", required=True, help="Path(s) to OHLCV CSV file(s)")
    parser.add_argument("--params", default="", help="Parameter block in KEY=VALUE format")
    parser.add_argument("--ihsg", default=None, help="Optional IHSG/JKSE CSV path")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    parser.add_argument("--glob", action="store_true", help="Treat --data as glob patterns")
    parser.add_argument("--backtest", action="store_true", help="Run walk-forward backtest instead of live analysis")
    parser.add_argument("--backtest-step", type=int, default=1, help="Re-run engine every N bars during backtest (default: 1 for bar-by-bar walk-forward)")
    parser.add_argument("--portfolio", action="store_true", help="Run portfolio backtest across all tickers")
    parser.add_argument("--allocation", default="equal_weight", choices=["equal_weight", "risk_based"], help="Capital allocation mode")
    parser.add_argument("--parallel", action="store_true", help="Analyze multiple tickers in parallel")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Logging verbosity level")
    parser.add_argument("--log-file", default=None, help="Optional log file path")

    args = parser.parse_args(argv)

    # Configure logging
    from .logging_config import setup_logging
    setup_logging(level=args.log_level, log_file=args.log_file)

    data_paths = []
    if args.glob:
        for pattern in args.data:
            data_paths.extend(glob.glob(pattern))
    else:
        data_paths = args.data

    # Validate existence
    for p in data_paths:
        if not os.path.exists(p):
            print(f"ERROR: File not found: {p}", file=sys.stderr)
            sys.exit(1)

    if args.backtest:
        from .backtest import run_backtest, render_backtest_report, render_backtest_aggregate, validate_as_of_consistency
        from .data import load_ohlcv

        params = {"POSITION":"NO_POSITION","DIRECTION":"BOTH","MODAL":10000000,"RISK":2}
        # Parse user params
        for line in args.params.strip().splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip().upper()
            v = v.strip()
            if k in {"MODAL"}:
                v = v.lower().replace("jt", "000000").replace("m", "000000").replace(".", "")
                params[k] = float(v)
            elif k in {"RISK"}:
                params[k] = float(v)
            else:
                params[k] = v

        results = []
        reports = []
        for p in data_paths:
            df = load_ohlcv(p)
            ticker = df["Ticker"].iloc[0]
            result = run_backtest(df, params, step=args.backtest_step)
            results.append(result)
            reports.append(render_backtest_report(result))

            # Validate as-of consistency
            mismatches = validate_as_of_consistency(df, params)
            if mismatches:
                reports.append(f"**As-of validation mismatches for {ticker}:**")
                for m in mismatches:
                    reports.append(f"- {m}")
            else:
                reports.append(f"**As-of validation for {ticker}: OK**")
            reports.append("")

        reports.append(render_backtest_aggregate(results))

        output = "\n\n".join(reports)
        os.makedirs(args.output_dir, exist_ok=True)
        out_path = os.path.join(args.output_dir, "BEI_Backtest_Report.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(output)
        return

    if args.portfolio:
        from .portfolio import run_portfolio_backtest, render_portfolio_report
        from .data import load_ohlcv

        params = {"POSITION": "NO_POSITION", "DIRECTION": "BOTH", "MODAL": 10000000, "RISK": 2}
        for line in args.params.strip().splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip().upper()
            v = v.strip()
            if k in {"MODAL"}:
                v = v.lower().replace("jt", "000000").replace("m", "000000").replace(".", "")
                params[k] = float(v)
            elif k in {"RISK"}:
                params[k] = float(v)
            else:
                params[k] = v

        dataframes = [load_ohlcv(p) for p in data_paths]
        result = run_portfolio_backtest(
            dataframes=dataframes,
            params=params,
            step=args.backtest_step,
            allocation_mode=args.allocation,
        )

        output = render_portfolio_report(result)
        os.makedirs(args.output_dir, exist_ok=True)
        out_path = os.path.join(args.output_dir, "BEI_Portfolio_Backtest.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(output)
        return

    output = run_analysis(
        data_paths=data_paths,
        params_text=args.params,
        ihsg_path=args.ihsg,
        output_dir=args.output_dir,
        parallel=args.parallel,
    )

    print(output)


if __name__ == "__main__":
    main()
