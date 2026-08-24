"""
Technical indicator calculations for the 42-row indicator contract.
"""

from typing import Dict, Optional

import pandas as pd
import numpy as np


def wilder_smoothing(series: pd.Series, period: int) -> pd.Series:
    """Wilder smoothing: first value = SMA, then EMA with alpha=1/period."""
    return series.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """EMA with seed = SMA(n)."""
    return series.ewm(span=period, min_periods=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI using Wilder smoothing."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))

    avg_gain = wilder_smoothing(gain, period)
    avg_loss = wilder_smoothing(loss, period)

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def atr_wilder(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ATR using Wilder smoothing."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    return wilder_smoothing(tr, period)


def adx_di(df: pd.DataFrame, period: int = 14) -> Dict[str, pd.Series]:
    """ADX, +DI, -DI using Wilder smoothing and exclusive dominance."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    prev_high = high.shift(1)
    prev_low = low.shift(1)

    plus_dm = high - prev_high
    minus_dm = prev_low - low

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    atr = atr_wilder(df, period)

    plus_di = 100.0 * wilder_smoothing(plus_dm, period) / atr
    minus_di = 100.0 * wilder_smoothing(minus_dm, period) / atr

    # Clip to valid range
    plus_di = plus_di.clip(0, 100)
    minus_di = minus_di.clip(0, 100)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = wilder_smoothing(dx, period)

    return {"ADX": adx, "+DI": plus_di, "-DI": minus_di, "ATR": atr}


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    line = ema_fast - ema_slow
    signal_line = ema(line, signal)
    hist = line - signal_line
    return {"line": line, "signal": signal_line, "histogram": hist}


def roc(close: pd.Series, period: int = 20) -> pd.Series:
    return ((close - close.shift(period)) / close.shift(period).replace(0, np.nan)) * 100.0


def cmf(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Chaikin Money Flow."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    volume = df["Volume"]

    hl = high - low
    mfm = ((close - low) - (high - close)) / hl.replace(0, np.nan)
    mfv = mfm * volume

    cmf = mfv.rolling(window=period, min_periods=period).sum() / volume.rolling(window=period, min_periods=period).sum()
    return cmf


def obv(df: pd.DataFrame) -> pd.Series:
    """On Balance Volume."""
    close = df["Close"]
    volume = df["Volume"]
    direction = np.sign(close.diff()).fillna(0)
    obv_val = (direction * volume).cumsum()
    return obv_val


def bollinger(close: pd.Series, period: int = 20, std: float = 2.0) -> Dict[str, pd.Series]:
    mid = sma(close, period)
    # population std
    sigma = close.rolling(window=period, min_periods=period).std(ddof=0)
    upper = mid + std * sigma
    lower = mid - std * sigma
    return {"upper": upper, "mid": mid, "lower": lower, "sigma": sigma}


def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Dict[str, pd.Series]:
    """Supertrend direction and value."""
    atr = atr_wilder(df, period)
    hl2 = (df["High"] + df["Low"]) / 2.0
    close = df["Close"]

    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr

    direction = pd.Series(1, index=df.index, dtype=int)
    st = pd.Series(np.nan, index=df.index)

    # Initialize first valid bar where both atr and hl2 are available
    first_valid = max(upper.first_valid_index(), lower.first_valid_index(), atr.first_valid_index())
    if first_valid is None or first_valid not in df.index:
        return {"direction": direction, "value": st, "upper": upper, "lower": lower}

    start_i = df.index.get_loc(first_valid)
    if start_i >= len(df):
        return {"direction": direction, "value": st, "upper": upper, "lower": lower}

    # Initialize
    st.iloc[start_i] = lower.iloc[start_i]
    direction.iloc[start_i] = 1

    upper_values = upper.to_numpy().copy()
    lower_values = lower.to_numpy().copy()
    close_values = close.to_numpy().copy()
    direction_values = direction.to_numpy().copy()
    st_values = st.to_numpy().copy()

    for i in range(start_i + 1, len(df)):
        prev_i = i - 1

        # Adjust bands
        if upper_values[i] < upper_values[prev_i] or close_values[prev_i] > upper_values[prev_i]:
            upper_values[i] = upper_values[i]
        else:
            upper_values[i] = upper_values[prev_i]

        if lower_values[i] > lower_values[prev_i] or close_values[prev_i] < lower_values[prev_i]:
            lower_values[i] = lower_values[i]
        else:
            lower_values[i] = lower_values[prev_i]

        if close_values[i] > upper_values[prev_i]:
            direction_values[i] = 1
        elif close_values[i] < lower_values[prev_i]:
            direction_values[i] = -1
        else:
            direction_values[i] = direction_values[prev_i]

        st_values[i] = lower_values[i] if direction_values[i] == 1 else upper_values[i]

    return {
        "direction": pd.Series(direction_values, index=df.index),
        "value": pd.Series(st_values, index=df.index),
        "upper": pd.Series(upper_values, index=df.index),
        "lower": pd.Series(lower_values, index=df.index),
    }


def parabolic_sar(df: pd.DataFrame, af_start: float = 0.02, af_inc: float = 0.02, af_max: float = 0.20) -> pd.Series:
    """Parabolic SAR implementation."""
    high = df["High"].values
    low = df["Low"].values
    close = df["Close"].values
    n = len(df)

    psar = np.zeros(n)
    direction = np.zeros(n)  # 1 = long, -1 = short
    ep = np.zeros(n)
    af = np.zeros(n)

    # Initialize: assume long if first close change is up, else short
    if close[1] >= close[0]:
        direction[1] = 1
        psar[1] = min(low[0], low[1])
        ep[1] = max(high[0], high[1])
    else:
        direction[1] = -1
        psar[1] = max(high[0], high[1])
        ep[1] = min(low[0], low[1])
    af[1] = af_start

    for i in range(2, n):
        prev_dir = direction[i - 1]
        prev_psar = psar[i - 1]
        prev_ep = ep[i - 1]
        prev_af = af[i - 1]

        psar[i] = prev_psar + prev_af * (prev_ep - prev_psar)

        if prev_dir == 1:
            # Long: SAR cannot exceed last two lows
            psar[i] = min(psar[i], low[i - 1], low[i - 2])
            if high[i] > prev_ep:
                ep[i] = high[i]
                af[i] = min(prev_af + af_inc, af_max)
            else:
                ep[i] = prev_ep
                af[i] = prev_af
            if low[i] < psar[i]:
                direction[i] = -1
                psar[i] = max(high[i - 1], high[i], ep[i])
                ep[i] = min(low[i - 1], low[i])
                af[i] = af_start
            else:
                direction[i] = 1
        else:
            # Short: SAR cannot be below last two highs
            psar[i] = max(psar[i], high[i - 1], high[i - 2])
            if low[i] < prev_ep:
                ep[i] = low[i]
                af[i] = min(prev_af + af_inc, af_max)
            else:
                ep[i] = prev_ep
                af[i] = prev_af
            if high[i] > psar[i]:
                direction[i] = 1
                psar[i] = min(low[i - 1], low[i], ep[i])
                ep[i] = max(high[i - 1], high[i])
                af[i] = af_start
            else:
                direction[i] = -1

    # Use NaN for first bar; second bar onward valid
    psar[0] = np.nan
    return pd.Series(psar, index=df.index)


def stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
    low_min = df["Low"].rolling(window=k_period, min_periods=k_period).min()
    high_max = df["High"].rolling(window=k_period, min_periods=k_period).max()
    raw_k = 100.0 * (df["Close"] - low_min) / (high_max - low_min).replace(0, np.nan)
    k = raw_k.rolling(window=d_period, min_periods=d_period).mean()
    d = k.rolling(window=d_period, min_periods=d_period).mean()
    return {"%K": k, "%D": d}


def mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Money Flow Index."""
    typical = (df["High"] + df["Low"] + df["Close"]) / 3.0
    raw_mf = typical * df["Volume"]
    delta = typical.diff()
    pos_mf = raw_mf.where(delta > 0, 0.0)
    neg_mf = raw_mf.where(delta < 0, 0.0)

    pos_sum = pos_mf.rolling(window=period, min_periods=period).sum()
    neg_sum = neg_mf.rolling(window=period, min_periods=period).sum()

    ratio = pos_sum / neg_sum.replace(0, np.nan)
    mfi = 100.0 - (100.0 / (1.0 + ratio))
    # Recalculate/clamp if outside 0-100 due to data issues
    mfi = mfi.clip(0, 100)
    return mfi


def resample_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resample daily OHLCV to weekly. Weekly close = last trading day of the week.
    """
    w = df.resample("W-FRI").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }).dropna()
    return w


def ichimoku(df: pd.DataFrame) -> Dict[str, pd.Series]:
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    tenkan = (high.rolling(window=9, min_periods=9).max() + low.rolling(window=9, min_periods=9).min()) / 2.0
    kijun = (high.rolling(window=26, min_periods=26).max() + low.rolling(window=26, min_periods=26).min()) / 2.0
    senkou_a = ((tenkan + kijun) / 2.0).shift(26)
    senkou_b = ((high.rolling(window=52, min_periods=52).max() + low.rolling(window=52, min_periods=52).min()) / 2.0).shift(26)
    chikou = close.shift(-26)

    return {
        "tenkan": tenkan,
        "kijun": kijun,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b,
        "chikou": chikou,
    }


def detect_divergence(
    price: pd.Series,
    indicator: pd.Series,
    lookback: int = 28,
    swing_n: int = 5,
) -> Optional[str]:
    """
    Detect regular/hidden bullish/bearish divergence between price and indicator.
    Returns one of: 'Regular Bullish', 'Regular Bearish', 'Hidden Bullish', 'Hidden Bearish', None.
    """
    if len(price) < lookback + swing_n:
        return None

    p = price.iloc[-lookback:]
    ind = indicator.iloc[-lookback:]

    # Find local extrema using simple argrelextrema-like logic
    def local_minima(s: pd.Series, n: int):
        mins = []
        for i in range(n, len(s) - n):
            if s.iloc[i] == s.iloc[i - n:i + n + 1].min():
                mins.append(i)
        return mins

    def local_maxima(s: pd.Series, n: int):
        maxs = []
        for i in range(n, len(s) - n):
            if s.iloc[i] == s.iloc[i - n:i + n + 1].max():
                maxs.append(i)
        return maxs

    p_mins = local_minima(p, swing_n)
    p_maxs = local_maxima(p, swing_n)
    i_mins = local_minima(ind, swing_n)
    i_maxs = local_maxima(ind, swing_n)

    # Need at least two aligned extrema
    if len(p_mins) >= 2 and len(i_mins) >= 2:
        p_low1, p_low2 = p.iloc[p_mins[-2]], p.iloc[p_mins[-1]]
        i_low1, i_low2 = ind.iloc[i_mins[-2]], ind.iloc[i_mins[-1]]
        if p_low2 < p_low1 and i_low2 > i_low1:
            return "Regular Bullish"
        if p_low2 > p_low1 and i_low2 < i_low1:
            return "Hidden Bullish"

    if len(p_maxs) >= 2 and len(i_maxs) >= 2:
        p_high1, p_high2 = p.iloc[p_maxs[-2]], p.iloc[p_maxs[-1]]
        i_high1, i_high2 = ind.iloc[i_maxs[-2]], ind.iloc[i_maxs[-1]]
        if p_high2 > p_high1 and i_high2 < i_high1:
            return "Regular Bearish"
        if p_high2 < p_high1 and i_high2 > i_high1:
            return "Hidden Bearish"

    return None


def classify_trend_from_close(close: pd.Series, period: int = 20) -> str:
    """Classify as Up/Down/Sideways from slope of linear regression on last N closes."""
    if len(close) < period:
        return "N/A"
    y = close.iloc[-period:].values
    x = np.arange(len(y))
    slope = np.polyfit(x, y, 1)[0]
    avg = np.mean(y)
    slope_pct = (slope * period) / avg * 100.0 if avg != 0 else 0.0
    if slope_pct > 2.0:
        return "Up"
    elif slope_pct < -2.0:
        return "Down"
    return "Sideways"


def weinstein_stage(weekly_close: pd.Series, weekly_ma30: pd.Series) -> str:
    """
    Weinstein stage from weekly close and 30-week SMA slope.
    Stage 2: Close > MA30w AND slope > +0.5% -> bullish
    Stage 4: Close < MA30w AND slope < -0.5% -> bearish
    Stage 3: Close > MA30w AND slope <= 0 -> neutral
    Stage 1: Close < MA30w AND slope >= 0 -> neutral
    """
    if len(weekly_close) < 34:
        return "N/A"
    close_now = weekly_close.iloc[-1]
    ma_now = weekly_ma30.iloc[-1]
    ma_prev = weekly_ma30.iloc[-5] if len(weekly_ma30) >= 5 else weekly_ma30.iloc[0]
    slope_pct = (ma_now - ma_prev) / ma_prev * 100.0 if ma_prev != 0 else 0.0

    if pd.isna(close_now) or pd.isna(ma_now):
        return "N/A"

    if close_now > ma_now and slope_pct > 0.5:
        return "Stage 2"
    if close_now < ma_now and slope_pct < -0.5:
        return "Stage 4"
    if close_now > ma_now and slope_pct <= 0:
        return "Stage 3"
    if close_now < ma_now and slope_pct >= 0:
        return "Stage 1"
    return "N/A"


def volume_synthesis(df: pd.DataFrame, obv_series: pd.Series, cmf_series: pd.Series) -> str:
    """
    Accumulation / Distribution / Neutral based on OBV, CMF, and up/down volume ratios.
    """
    if len(df) < 20:
        return "N/A"

    recent = df.iloc[-20:].copy()
    recent["OBV"] = obv_series.iloc[-20:]
    vol_ma20 = df["Volume"].iloc[-20:].mean()
    if vol_ma20 == 0:
        return "Neutral"

    up_days = recent[recent["Close"] > recent["Close"].shift(1)]
    down_days = recent[recent["Close"] < recent["Close"].shift(1)]

    ratio_up = (up_days["Volume"].mean() / vol_ma20) if len(up_days) > 0 else 0.0
    ratio_down = (down_days["Volume"].mean() / vol_ma20) if len(down_days) > 0 else 0.0

    obv_rising = recent["OBV"].iloc[-1] > recent["OBV"].iloc[0]
    obv_falling = recent["OBV"].iloc[-1] < recent["OBV"].iloc[0]
    cmf_now = cmf_series.iloc[-1]

    if obv_rising and cmf_now > 0.10 and ratio_up > 1.2:
        return "Accumulation (High)"
    if obv_rising and cmf_now > 0.10 and ratio_up > 1.0:
        return "Accumulation (Medium)"
    if obv_falling and cmf_now < -0.10 and ratio_down > 1.2:
        return "Distribution (High)"
    if obv_falling and cmf_now < -0.10 and ratio_down > 1.0:
        return "Distribution (Medium)"
    return "Neutral"


def compute_all_indicators(df: pd.DataFrame) -> Dict:
    """
    Compute all indicators needed for the 42-row contract.
    Returns dict of pandas Series keyed by indicator name.
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # Trend
    ema9 = ema(close, 9)
    sma20 = sma(close, 20)
    sma50 = sma(close, 50)
    sma200 = sma(close, 200)

    adx_di_result = adx_di(df, 14)
    adx = adx_di_result["ADX"]
    plus_di = adx_di_result["+DI"]
    minus_di = adx_di_result["-DI"]
    atr14 = adx_di_result["ATR"]

    supertrend_result = supertrend(df, 10, 3.0)
    sar = parabolic_sar(df)

    # Momentum
    rsi14 = rsi_wilder(close, 14)
    macd_result = macd(close, 12, 26, 9)
    stoch = stochastic(df, 14, 3)
    roc20 = roc(close, 20)
    mfi14 = mfi(df, 14)

    # Volatility
    atr_pct = (atr14 / close.replace(0, np.nan)) * 100.0
    bb = bollinger(close, 20, 2.0)

    # Volume
    vol_ma20 = sma(volume, 20)
    volume_vs_ma20 = volume / vol_ma20.replace(0, np.nan)
    obv_series = obv(df)
    cmf20 = cmf(df, 20)
    vol_synthesis = volume_synthesis(df, obv_series, cmf20)

    # Structure
    ichimoku_result = ichimoku(df)

    # Weekly
    weekly = resample_weekly(df)
    if len(weekly) >= 30:
        weekly_close = weekly["Close"]
        weekly_sma20 = sma(weekly_close, 20)
        weekly_sma50 = sma(weekly_close, 50)
        weekly_rsi = rsi_wilder(weekly_close, 14)
        weekly_macd = macd(weekly_close, 12, 26, 9)
        weekly_ma30 = sma(weekly_close, 30)
        weinstein = weinstein_stage(weekly_close, weekly_ma30)
    else:
        weekly_close = weekly["Close"] if len(weekly) > 0 else None
        weekly_sma20 = pd.Series(np.nan, index=weekly.index) if len(weekly) > 0 else None
        weekly_sma50 = pd.Series(np.nan, index=weekly.index) if len(weekly) > 0 else None
        weekly_rsi = pd.Series(np.nan, index=weekly.index) if len(weekly) > 0 else None
        weekly_macd = {"line": pd.Series(np.nan, index=weekly.index), "signal": pd.Series(np.nan, index=weekly.index)} if len(weekly) > 0 else None
        weinstein = "N/A"

    # Trend classification from structure + MAs
    def trend_class():
        if len(close) < 20:
            return "N/A"
        c = close.iloc[-1]
        e9 = ema9.iloc[-1]
        s20 = sma20.iloc[-1]
        s50 = sma50.iloc[-1]
        s200 = sma200.iloc[-1] if not pd.isna(sma200.iloc[-1]) else None
        bullish = c > e9 and e9 > s20 and s20 > s50
        if s200 is not None:
            bullish = bullish and c > s200
        bearish = c < e9 and e9 < s20 and s20 < s50
        if s200 is not None:
            bearish = bearish and c < s200
        if bullish:
            return "Uptrend"
        if bearish:
            return "Downtrend"
        return "Sideways"

    # Multi-timeframe (monthly, weekly, daily) from close slope
    monthly = df.resample("ME").last()["Close"].dropna()
    monthly_trend = classify_trend_from_close(monthly, min(6, len(monthly))) if len(monthly) >= 3 else "N/A"
    weekly_trend = classify_trend_from_close(weekly_close, min(12, len(weekly_close))) if weekly_close is not None and len(weekly_close) >= 4 else "N/A"
    daily_trend = classify_trend_from_close(close, min(20, len(close)))

    # MA Alignment
    def ma_alignment():
        if len(close) < 200 or pd.isna(sma200.iloc[-1]):
            return "N/A"
        c = close.iloc[-1]
        e9v = ema9.iloc[-1]
        s20v = sma20.iloc[-1]
        s50v = sma50.iloc[-1]
        s200v = sma200.iloc[-1]
        if e9v > s20v > s50v > s200v:
            return "Bullish"
        if e9v < s20v < s50v < s200v:
            return "Bearish"
        return "Mixed"

    return {
        # Trend
        "ma_alignment": ma_alignment(),
        "trend_classification": trend_class(),
        "multi_tf_monthly": monthly_trend,
        "multi_tf_weekly": weekly_trend,
        "multi_tf_daily": daily_trend,
        "weinstein_stage": weinstein,
        "ema9": ema9,
        "sma20": sma20,
        "sma50": sma50,
        "sma200": sma200,
        "adx": adx,
        "plus_di": plus_di,
        "minus_di": minus_di,
        "supertrend_direction": supertrend_result["direction"],
        "supertrend_value": supertrend_result["value"],
        "parabolic_sar": sar,
        # Momentum
        "rsi14": rsi14,
        "macd_line": macd_result["line"],
        "macd_signal": macd_result["signal"],
        "macd_histogram": macd_result["histogram"],
        "stoch_k": stoch["%K"],
        "stoch_d": stoch["%D"],
        "roc20": roc20,
        "mfi14": mfi14,
        # Volatility
        "atr14": atr14,
        "atr_pct": atr_pct,
        "bb_upper": bb["upper"],
        "bb_mid": bb["mid"],
        "bb_lower": bb["lower"],
        # Volume
        "volume_vs_ma20": volume_vs_ma20,
        "obv": obv_series,
        "cmf20": cmf20,
        "volume_synthesis": vol_synthesis,
        # Structure
        "ichimoku_tenkan": ichimoku_result["tenkan"],
        "ichimoku_kijun": ichimoku_result["kijun"],
        "ichimoku_senkou_a": ichimoku_result["senkou_a"],
        "ichimoku_senkou_b": ichimoku_result["senkou_b"],
        "ichimoku_chikou": ichimoku_result["chikou"],
        # Weekly
        "weekly_close": weekly_close,
        "weekly_sma20": weekly_sma20,
        "weekly_sma50": weekly_sma50,
        "weekly_rsi14": weekly_rsi,
        "weekly_macd_line": weekly_macd["line"] if weekly_macd else None,
        "weekly_macd_signal": weekly_macd["signal"] if weekly_macd else None,
    }
