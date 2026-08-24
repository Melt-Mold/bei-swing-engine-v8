#!/usr/bin/env python
"""
BEI Swing Engine v8.0 — REST API Server CLI.
Start the FastAPI server for system integration.

Usage:
    python api_server_app.py --port 8000
    python api_server_app.py --host 0.0.0.0 --port 8080
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bei_swing_engine_v8.logging_config import setup_logging


def main():
    parser = argparse.ArgumentParser(
        description="BEI Swing Engine v8.0 — REST API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Endpoints:
  GET  /                  — API info
  GET  /health            — Health check
  POST /analyze           — Analyze uploaded CSV(s)
  POST /screening         — Multi-ticker screening
  POST /backtest          — Run backtest on uploaded CSV
  POST /portfolio         — Run portfolio backtest
  POST /clean             — Clean raw CSV
  POST /merge             — Merge existing + new CSV
  GET  /fetch/{ticker}   — Fetch from Yahoo Finance and analyze

Examples:
  # Start server on default port 8000
  python api_server_app.py

  # Custom host and port
  python api_server_app.py --host 0.0.0.0 --port 8080

  # Test with curl:
  curl http://localhost:8000/health
  curl -X POST http://localhost:8000/analyze -F "files=@TLKM.csv" -F "mode=A"
  curl "http://localhost:8000/fetch/BBRI?period=1y&mode=C"
        """,
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen (default: 8000)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    args = parser.parse_args()
    setup_logging(level=args.log_level)

    from bei_swing_engine_v8.api import run_api_server
    run_api_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
