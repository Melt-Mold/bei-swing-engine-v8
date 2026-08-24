"""
Data ingestion, validation, and ticker extraction.
"""

import os
import re
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import numpy as np

from .logging_config import get_logger

_log = get_logger("data")


REQUIRED_COLUMNS = {"Date", "Open", "High", "Low", "Close", "Volume"}


def extract_ticker_from_path(path: str) -> str:
    """Extract ticker symbol from filename like BBRI.JK_cleaned.csv or IHSG-JKSE_cleaned.csv."""
    name = Path(path).stem
    # Remove '_cleaned' suffix
    name = name.replace("_cleaned", "")
    # Convert IHSG-JKSE to IHSG
    if name.upper() in {"IHSG-JKSE", "JKSE", "IHSG"}:
        return "IHSG"
    # Remove .JK suffix if present
    name = re.sub(r"\.JK$", "", name, flags=re.IGNORECASE)
    return name.upper()


def load_ohlcv(
    path: str,
    ticker: Optional[str] = None,
    cutoff: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """
    Load a single OHLCV CSV file.

    Returns DataFrame indexed by Date with columns:
    Open, High, Low, Close, Volume, Ticker
    """
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        _log.error("missing columns | path=%s missing=%s", path, missing)
        raise ValueError(f"Missing columns in {path}: {missing}")

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    df = df.set_index("Date")

    numeric_cols = ["Open", "High", "Low", "Close", "Volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows with any NaN in OHLCV
    before = len(df)
    df = df.dropna(subset=numeric_cols)
    dropped = before - len(df)
    if dropped > 0:
        _log.warning("dropped rows with NaN OHLCV | path=%s dropped=%d", path, dropped)

    if cutoff is not None:
        df = df[df.index <= cutoff].copy()
        _log.debug("applied cutoff | path=%s cutoff=%s bars_after=%d", path, cutoff, len(df))

    if ticker is None:
        ticker = extract_ticker_from_path(path)
    df["Ticker"] = ticker

    _log.debug("loaded OHLCV | path=%s ticker=%s bars=%d range=%s..%s",
               path, ticker, len(df), df.index.min().date(), df.index.max().date())
    return df


def validate_data(df: pd.DataFrame) -> dict:
    """
    Validate data sufficiency per indicator requirements.
    Returns dict with status and reasons.
    """
    n = len(df)
    reasons = []
    status = "OK"

    if n == 0:
        return {
            "status": "ERROR",
            "bars": 0,
            "date_range": (None, None),
            "sufficiency": {},
            "reasons": ["No data rows after loading."],
        }

    sufficiency = {
        "SMA200": n >= 200,
        "ADX14/ATR14/RSI14": n >= 28,
        "SMA20/CMF20/ROC20": n >= 20,
        "EMA9": n >= 9,
        "Ichimoku": n >= 52,
        "Bollinger20": n >= 20,
        "Stochastic14": n >= 14,
        "MFI14": n >= 14,
        "Weekly30": n >= 150,  # ~30 weeks of daily bars (rough)
    }

    if n < 20:
        status = "ERROR"
        reasons.append(f"Only {n} bars; minimum 20 required for actionable setup.")
    elif n < 28:
        status = "INSUFFICIENT"
        reasons.append(f"{n} bars < 28; ADX/ATR/RSI values may be unstable.")
    elif n < 200:
        status = "INSUFFICIENT"
        reasons.append(f"{n} bars < 200; SMA200 unavailable.")

    return {
        "status": status,
        "bars": n,
        "date_range": (df.index.min(), df.index.max()),
        "sufficiency": sufficiency,
        "reasons": reasons,
    }


def load_ihsg(ihsg_path: Optional[str]) -> Optional[pd.DataFrame]:
    """Load IHSG data if path provided, else None."""
    if ihsg_path is None or not os.path.exists(ihsg_path):
        return None
    return load_ohlcv(ihsg_path, ticker="IHSG")
