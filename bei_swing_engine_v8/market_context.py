"""
Market context (IHSG/JKSE regime).
"""

from typing import Dict, Optional

import pandas as pd
import numpy as np

from . import indicators as ind


def analyze_market_regime(ihsg_df: Optional[pd.DataFrame]) -> Dict:
    """
    Analyze IHSG market regime from weekly data.
    Returns dict with regime, weekly_close, weekly_sma30, slope_pct.
    If no IHSG data, returns N/A with reason.
    """
    if ihsg_df is None or len(ihsg_df) == 0:
        return {
            "regime": "N/A — no IHSG/JKSE data uploaded",
            "weekly_close": None,
            "weekly_sma30": None,
            "slope_pct": None,
            "trend": "N/A",
        }

    weekly = ind.resample_weekly(ihsg_df)
    if len(weekly) < 34:
        return {
            "regime": "N/A — insufficient IHSG weekly data",
            "weekly_close": weekly["Close"].iloc[-1] if len(weekly) > 0 else None,
            "weekly_sma30": None,
            "slope_pct": None,
            "trend": "N/A",
        }

    weekly_close = weekly["Close"]
    weekly_sma30 = ind.sma(weekly_close, 30)

    close_now = weekly_close.iloc[-1]
    ma_now = weekly_sma30.iloc[-1]
    ma_prev = weekly_sma30.iloc[-5] if len(weekly_sma30) >= 5 else weekly_sma30.iloc[0]
    slope_pct = (ma_now - ma_prev) / ma_prev * 100.0 if ma_prev != 0 else 0.0

    if close_now > ma_now and slope_pct > 0.5:
        regime = "Bullish Stage 2"
        trend = "Uptrend"
    elif close_now < ma_now and slope_pct < -0.5:
        regime = "Bearish Stage 4"
        trend = "Downtrend"
    elif close_now > ma_now and slope_pct <= 0:
        regime = "Stage 3 (topping)"
        trend = "Sideways"
    elif close_now < ma_now and slope_pct >= 0:
        regime = "Stage 1 (bottoming)"
        trend = "Sideways"
    else:
        regime = "Neutral"
        trend = "Sideways"

    return {
        "regime": regime,
        "trend": trend,
        "weekly_close": close_now,
        "weekly_sma30": ma_now,
        "slope_pct": slope_pct,
    }
