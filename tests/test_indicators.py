"""Tests for technical indicator calculations."""

import numpy as np
import pandas as pd
import pytest

from bei_swing_engine_v8.indicators import (
    sma, ema, rsi_wilder, atr_wilder, adx_di, macd, roc, cmf, obv,
    bollinger, compute_all_indicators, detect_divergence,
)
from bei_swing_engine_v8.output import build_indicator_table


class TestIndicators:
    def test_sma_simple(self, sample_df):
        close = sample_df["Close"]
        s20 = sma(close, 20)
        # SMA20 should equal mean of last 20 closes
        expected = close.iloc[-20:].mean()
        assert np.isclose(s20.iloc[-1], expected)

    def test_rsi_in_range(self, sample_df):
        rsi = rsi_wilder(sample_df["Close"], 14)
        valid = rsi.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_atr_positive(self, sample_df):
        atr = atr_wilder(sample_df, 14)
        assert (atr.dropna() > 0).all()

    def test_adx_components(self, sample_df):
        res = adx_di(sample_df, 14)
        assert set(res.keys()) == {"ADX", "+DI", "-DI", "ATR"}
        adx = res["ADX"].dropna()
        assert (adx >= 0).all() and (adx <= 100).all()

    def test_macd_line_signal(self, sample_df):
        close = sample_df["Close"]
        m = macd(close)
        # Histogram = line - signal
        assert np.allclose(m["histogram"].dropna(), (m["line"] - m["signal"]).dropna())

    def test_bollinger_bands(self, sample_df):
        close = sample_df["Close"]
        bb = bollinger(close, 20)
        # upper >= mid >= lower
        valid = bb["upper"].dropna().index
        assert (bb["upper"].loc[valid] >= bb["mid"].loc[valid]).all()
        assert (bb["mid"].loc[valid] >= bb["lower"].loc[valid]).all()

    def test_roc_calculation(self, sample_df):
        close = sample_df["Close"]
        r = roc(close, 20)
        expected = (close.iloc[-1] - close.iloc[-21]) / close.iloc[-21] * 100
        assert np.isclose(r.iloc[-1], expected)

    def test_cmf_in_range(self, sample_df):
        c = cmf(sample_df, 20)
        valid = c.dropna()
        assert (valid >= -1).all() and (valid <= 1).all()

    def test_obv_monotonic_when_unchanged(self, sample_df):
        o = obv(sample_df)
        # OBV changes only when close changes
        for i in range(1, min(10, len(sample_df))):
            if sample_df["Close"].iloc[i] == sample_df["Close"].iloc[i - 1]:
                assert o.iloc[i] == o.iloc[i - 1]

    def test_42_row_table(self, sample_df, sample_indicators):
        rows = build_indicator_table(sample_df, sample_indicators)
        assert len(rows) == 42
        # Check expected columns
        assert set(rows[0].keys()) >= {"Category", "Indicator", "Value", "Signal", "Interpretation", "Standard / Reference"}
        # Check 16 badges
        badged = [r for r in rows if r["Badge"] is not None]
        assert len(badged) == 16

    def test_divergence_detection_none_on_flat(self):
        price = pd.Series(np.ones(50))
        indicator = pd.Series(np.ones(50))
        assert detect_divergence(price, indicator) is None
