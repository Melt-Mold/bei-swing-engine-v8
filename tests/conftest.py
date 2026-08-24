"""
Shared pytest fixtures.
"""

import os
import pytest

from bei_swing_engine_v8.data import load_ohlcv
from bei_swing_engine_v8.indicators import compute_all_indicators
from bei_swing_engine_v8.structure import analyze_structure


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data-csv-yfinance-cleaned")


@pytest.fixture
def sample_ticker_path():
    return os.path.join(DATA_DIR, "TLKM.JK_cleaned.csv")


@pytest.fixture
def sample_df(sample_ticker_path):
    return load_ohlcv(sample_ticker_path)


@pytest.fixture
def sample_indicators(sample_df):
    return compute_all_indicators(sample_df)


@pytest.fixture
def sample_structure(sample_df, sample_indicators):
    return analyze_structure(sample_df, sample_indicators)


@pytest.fixture
def default_params():
    return {
        "MODE": "A",
        "HORIZON": "SWING",
        "DIRECTION": "BOTH",
        "POSITION": "NO_POSITION",
        "MODAL": 10_000_000,
        "RISK": 2.0,
        "OUTPUT": "Chat",
        "IHSG": None,
    }
