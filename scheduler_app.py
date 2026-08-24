#!/usr/bin/env python
"""
BEI Swing Engine v8.0 — Scheduler CLI.
Auto-fetch data from Yahoo Finance, run analysis, and notify on BUY/SELL signals.

Usage:
    python scheduler_app.py --tickers BBRI BBCA TLKM --period 1y --once
    python scheduler_app.py --config scheduler_config.json
    python scheduler_app.py --tickers BBRI --interval-min 60    # recurring every 60 min
    python scheduler_app.py --help
"""

import argparse
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bei_swing_engine_v8.scheduler import (
    SchedulerConfig, run_scheduler, run_scheduler_loop,
    load_config_from_file, save_config_to_file,
)
from bei_swing_engine_v8.logging_config import setup_logging


DEFAULT_CONFIG_PATH = "scheduler_config.json"


def create_default_config(path: str):
    """Create a default scheduler config file."""
    config = SchedulerConfig()
    save_config_to_file(config, path)
    print(f"Default config saved to: {path}")
    print("Edit this file to customize tickers, email, and schedule settings.")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="BEI Swing Engine v8.0 — Scheduler (auto-fetch + analyze + notify)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run once with specific tickers
  python scheduler_app.py --tickers BBRI BBCA TLKM --period 1y --once

  # Run recurring every 60 minutes
  python scheduler_app.py --tickers BBRI BBCA --interval-min 60

  # Use config file
  python scheduler_app.py --config scheduler_config.json

  # Create default config file
  python scheduler_app.py --create-config
        """,
    )
    parser.add_argument("--tickers", nargs="+", help="BEI tickers to analyze (e.g., BBRI BBCA TLKM)")
    parser.add_argument("--ihsg", default="yes", choices=["yes", "no"], help="Fetch IHSG data (default: yes)")
    parser.add_argument("--period", default="1y", help="Data period (1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, max)")
    parser.add_argument("--interval", default="1d", choices=["1d", "1wk", "1mo"], help="Data interval")
    parser.add_argument("--output-dir", default="output", help="Output directory for reports")
    parser.add_argument("--data-dir", default="data-scheduled", help="Directory for fetched data")
    parser.add_argument("--mode", default="C", choices=["A", "B", "C"], help="Analysis mode (C=screening)")
    parser.add_argument("--direction", default="BOTH", choices=["LONG", "SHORT", "BOTH"])
    parser.add_argument("--position", default="NO_POSITION", choices=["NO_POSITION", "EXISTING_POSITION", "UNKNOWN"])
    parser.add_argument("--modal", type=float, default=10000000, help="Capital in Rupiah")
    parser.add_argument("--risk", type=float, default=2.0, help="Risk percent per trade")
    parser.add_argument("--notify-on", nargs="+", default=["BUY", "SELL"], help="Decisions to notify on")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval-min", type=int, default=0, help="Recurring interval in minutes (0 = once)")
    # Optimization options
    parser.add_argument("--optimize", action="store_true", help="Enable auto-optimization")
    parser.add_argument("--optimize-days", type=int, default=7, help="Optimization interval in days (default: 7 = weekly)")
    parser.add_argument("--optimize-step", type=int, default=5, help="Backtest step for optimization")
    parser.add_argument("--optimize-windows", type=int, default=2, help="Walk-forward windows")
    parser.add_argument("--optimize-now", action="store_true", help="Run optimization now and exit")
    parser.add_argument("--config", default=None, help="Path to JSON config file")
    parser.add_argument("--create-config", action="store_true", help="Create default config file and exit")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    # Email options
    parser.add_argument("--email", action="store_true", help="Enable email notification")
    parser.add_argument("--smtp-host", default="", help="SMTP server host")
    parser.add_argument("--smtp-port", type=int, default=587, help="SMTP server port")
    parser.add_argument("--email-user", default="", help="SMTP username")
    parser.add_argument("--email-pass", default="", help="SMTP password")
    parser.add_argument("--email-to", nargs="+", default=[], help="Recipient email addresses")

    args = parser.parse_args(argv)

    setup_logging(level=args.log_level)

    # Create default config and exit
    if args.create_config:
        create_default_config(DEFAULT_CONFIG_PATH)
        return

    # Load from config file or build from CLI args
    if args.config and os.path.exists(args.config):
        _log_msg = f"Loading config from {args.config}"
        print(_log_msg)
        config = load_config_from_file(args.config)
    else:
        config = SchedulerConfig(
            tickers=args.tickers or ["BBRI", "BBCA", "TLKM"],
            ihsg=(args.ihsg == "yes"),
            period=args.period,
            interval=args.interval,
            params={
                "MODE": args.mode,
                "HORIZON": "SWING",
                "DIRECTION": args.direction,
                "POSITION": args.position,
                "MODAL": args.modal,
                "RISK": args.risk,
                "OUTPUT": "Chat",
                "IHSG": "uploaded" if args.ihsg == "yes" else "None",
            },
            output_dir=args.output_dir,
            data_dir=args.data_dir,
            email_enabled=args.email,
            email_smtp_host=args.smtp_host,
            email_smtp_port=args.smtp_port,
            email_user=args.email_user,
            email_password=args.email_pass,
            email_to=args.email_to,
            run_once=args.once or (args.interval_min == 0),
            interval_minutes=args.interval_min,
            notify_on=args.notify_on,
            optimize_enabled=args.optimize or args.optimize_now,
            optimize_interval_days=args.optimize_days,
            optimize_step=args.optimize_step,
            optimize_windows=args.optimize_windows,
        )

    print(f"=== BEI Swing Engine v8.0 Scheduler ===")
    print(f"Tickers: {', '.join(config.tickers)}")
    print(f"IHSG: {'yes' if config.ihsg else 'no'}")
    print(f"Period: {config.period} | Interval: {config.interval}")
    print(f"Mode: {config.params.get('MODE', 'C')} | Direction: {config.params.get('DIRECTION', 'BOTH')}")
    print(f"Notify on: {', '.join(config.notify_on)}")
    print(f"Email: {'enabled' if config.email_enabled else 'disabled'}")
    print(f"Optimization: {'enabled (every %d days)' % config.optimize_interval_days if config.optimize_enabled else 'disabled'}")
    if config.interval_minutes > 0:
        print(f"Recurring: every {config.interval_minutes} minutes")
    else:
        print("Run: once")
    print()

    # Run optimization only and exit
    if args.optimize_now:
        from bei_swing_engine_v8.scheduler import run_optimization_cycle
        run_optimization_cycle(config)
        return

    # Run scheduler
    if config.interval_minutes > 0 and not config.run_once:
        run_scheduler_loop(config)
    else:
        run_scheduler(config)


if __name__ == "__main__":
    main()
