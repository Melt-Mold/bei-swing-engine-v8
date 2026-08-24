"""
Yahoo Finance data fetcher.
Downloads OHLCV data from Yahoo Finance using the yfinance library.
"""

import os
from typing import Optional, Dict
from dataclasses import dataclass

import pandas as pd

from .cleaner import clean_csv_text, write_cleaned_csv, rows_to_csv_string
from .logging_config import get_logger

_log = get_logger("fetcher")


# Valid period options for yfinance
VALID_PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]

# Valid intervals
VALID_INTERVALS = ["1d", "1wk", "1mo"]


@dataclass
class FetchResult:
    """Result of fetching data from Yahoo Finance."""
    ticker: str
    rows: list
    row_count: int
    period: str
    interval: str
    output_name: Optional[str] = None
    error: Optional[str] = None


def fetch_yfinance(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> FetchResult:
    """
    Fetch OHLCV data from Yahoo Finance.

    Args:
        ticker: Stock ticker (e.g., "BBRI.JK", "BBCA.JK", "JKSE" for IHSG).
        period: Data period ("1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max").
        interval: Data interval ("1d" daily, "1wk" weekly, "1mo" monthly).

    Returns:
        FetchResult with fetched rows.
    """
    if period not in VALID_PERIODS:
        return FetchResult(ticker, [], 0, period, interval, error=f"Invalid period: {period}. Valid: {VALID_PERIODS}")
    if interval not in VALID_INTERVALS:
        return FetchResult(ticker, [], 0, period, interval, error=f"Invalid interval: {interval}. Valid: {VALID_INTERVALS}")

    # Normalize ticker for Yahoo Finance
    yf_ticker = ticker.upper().strip()
    if yf_ticker in ("IHSG", "JKSE"):
        yf_ticker = "^JKSE"
    elif not yf_ticker.endswith(".JK") and not yf_ticker.startswith("^"):
        yf_ticker = f"{yf_ticker}.JK"

    try:
        import yfinance as yf
    except ImportError:
        return FetchResult(ticker, [], 0, period, interval, error="yfinance library not installed. Run: pip install yfinance")

    _log.info("fetching | ticker=%s yf_ticker=%s period=%s interval=%s", ticker, yf_ticker, period, interval)

    try:
        df = yf.download(yf_ticker, period=period, interval=interval, progress=False, auto_adjust=False)
    except Exception as e:
        _log.error("fetch failed | ticker=%s error=%s", ticker, e)
        return FetchResult(ticker, [], 0, period, interval, error=f"Download failed: {e}")

    if df is None or df.empty:
        return FetchResult(ticker, [], 0, period, interval, error=f"No data returned for {yf_ticker}. Check ticker or period.")

    # Flatten MultiIndex columns if present (yfinance returns MultiIndex for single tickers)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Convert yfinance DataFrame to our row format
    rows = []
    for idx, row in df.iterrows():
        try:
            date_str = idx.strftime("%Y-%m-%d")
            open_v = float(row.get("Open", 0))
            high_v = float(row.get("High", 0))
            low_v = float(row.get("Low", 0))
            close_v = float(row.get("Close", 0))
            volume_raw = row.get("Volume", 0)
            volume = int(volume_raw) if volume_raw is not None and not (isinstance(volume_raw, float) and pd.isna(volume_raw)) else 0

            # Validate
            if pd.isna(open_v) or pd.isna(high_v) or pd.isna(low_v) or pd.isna(close_v):
                continue
            if open_v <= 0 or high_v <= 0 or low_v <= 0 or close_v <= 0:
                continue
            if low_v > high_v:
                continue

            rows.append({
                "date": date_str,
                "open": open_v,
                "high": high_v,
                "low": low_v,
                "close": close_v,
                "volume": volume,
            })
        except (ValueError, TypeError):
            continue

    if not rows:
        return FetchResult(ticker, [], 0, period, interval, error="No valid rows after parsing")

    # Sort ascending and remove duplicates
    rows.sort(key=lambda r: r["date"])
    seen = set()
    unique = []
    for r in rows:
        if r["date"] not in seen:
            seen.add(r["date"])
            unique.append(r)

    _log.info("fetched | ticker=%s rows=%d", ticker, len(unique))

    return FetchResult(
        ticker=ticker,
        rows=unique,
        row_count=len(unique),
        period=period,
        interval=interval,
    )


def fetch_and_save(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    output_dir: str = ".",
    output_name: Optional[str] = None,
) -> FetchResult:
    """
    Fetch data from Yahoo Finance and save as cleaned CSV.
    """
    result = fetch_yfinance(ticker, period, interval)
    if result.error:
        return result

    # Generate output filename
    if output_name is None:
        upper = ticker.upper().strip()
        if upper in ("IHSG", "JKSE", "^JKSE"):
            output_name = "IHSG-JKSE_cleaned.csv"
        else:
            clean_ticker = upper.replace("^", "").replace(".JK", "")
            output_name = f"{clean_ticker}.JK_cleaned.csv"

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_name)
    write_cleaned_csv(result.rows, output_path)

    result.output_name = output_name
    return result
