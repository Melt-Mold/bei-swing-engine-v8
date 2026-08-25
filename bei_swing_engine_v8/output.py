"""
Output & rendering (Module 11).
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd
import numpy as np

from .setup import Setup
from .structure import Structure
from .decision import Decision
from .risk import TradePlan


DISCLAIMER = (
    "> Analisa ini bersifat edukatif untuk pembelajaran analisis teknikal, "
    "BUKAN rekomendasi investasi atau ajakan untuk membeli/menjual efek. "
    "Keputusan investasi dan risiko sepenuhnya menjadi tanggung jawab pengguna. "
    "Hasil masa lalu tidak menjamin hasil di masa depan."
)


def fmt_price(x: Optional[float]) -> str:
    if x is None or pd.isna(x):
        return "N/A"
    return f"{round(x):,}".replace(",", ".")


def fmt_float(x: Optional[float], decimals: int = 2) -> str:
    if x is None or pd.isna(x):
        return "N/A"
    return f"{x:.{decimals}f}"


def fmt_pct(x: Optional[float]) -> str:
    if x is None or pd.isna(x):
        return "N/A"
    return f"{x:.2f}%"


def last_valid(series: pd.Series) -> Optional[float]:
    """Return last non-NaN value."""
    s = series.dropna()
    return s.iloc[-1] if len(s) > 0 else None


def close_approx(close: float, ma: float, tolerance_pct: float = 0.005) -> bool:
    if pd.isna(ma):
        return False
    return abs(close - ma) / ma <= tolerance_pct


def build_indicator_table(df: pd.DataFrame, indicators: Dict, structure=None) -> List[Dict]:
    """
    Build exactly 42 rows × 6 columns for the indicator contract.
    Each row: Category, Indicator, Value, Signal, Interpretation, Standard/Reference.
    """
    close = df["Close"].iloc[-1]
    atr14 = last_valid(indicators["atr14"])

    rows = []

    def add(category, indicator, value, signal, interpretation, reference, badge=None):
        rows.append({
            "Category": category,
            "Indicator": indicator,
            "Value": value,
            "Signal": signal,
            "Interpretation": interpretation,
            "Standard / Reference": reference,
            "Badge": badge,
        })

    # Helpers for MA badges
    def ma_badge(close, ma):
        if pd.isna(ma):
            return "○"
        if close > ma and not close_approx(close, ma):
            return "✓"
        if close < ma and not close_approx(close, ma):
            return "✗"
        return "○"

    def ma_interp(close, ma, name):
        if pd.isna(ma):
            return f"N/A — {name} unavailable"
        if close > ma and not close_approx(close, ma):
            return f"Price above {name}"
        if close < ma and not close_approx(close, ma):
            return f"Price below {name}"
        return f"Price near {name}"

    # Divergence detection
    rsi_div = None
    macd_div = None
    obv_div = None
    try:
        from .indicators import detect_divergence
        rsi_div = detect_divergence(df["Close"], indicators["rsi14"], lookback=28)
        macd_div = detect_divergence(df["Close"], indicators["macd_line"], lookback=28)
        obv_div = detect_divergence(df["Close"], indicators["obv"], lookback=28)
    except Exception:
        pass

    # TREND
    ma_align = indicators["ma_alignment"]
    add("TREND", "MA Alignment", ma_align, "", ma_align, "Bullish: EMA9>SMA20>SMA50>SMA200")

    trend_class = indicators["trend_classification"]
    trend_badge = "✓" if trend_class == "Uptrend" else ("✗" if trend_class == "Downtrend" else "○")
    add("TREND", "Trend Classification", trend_class, trend_badge, trend_class, "Uptrend/Downtrend/Sideways from structure + MAs", badge=trend_badge)

    # 3M return badge mapped to Multi-TF Monthly row (confluence factor #14)
    close_now = df["Close"].iloc[-1]
    close_3m = df["Close"].iloc[-60] if len(df) >= 60 else None
    if close_3m is not None and close_3m != 0:
        ret_3m = (close_now - close_3m) / close_3m * 100.0
        ret3m_badge = "✓" if ret_3m > 5 else ("✗" if ret_3m < -5 else "○")
    else:
        ret_3m = None
        ret3m_badge = "○"
    add("TREND", "Multi-TF Monthly", indicators["multi_tf_monthly"], ret3m_badge, f"{indicators['multi_tf_monthly']} (3M return: {fmt_pct(ret_3m)})", "Monthly close slope / 3M return", badge=ret3m_badge)

    add("TREND", "Multi-TF Weekly", indicators["multi_tf_weekly"], "", indicators["multi_tf_weekly"], "Weekly close slope")
    add("TREND", "Multi-TF Daily", indicators["multi_tf_daily"], "", indicators["multi_tf_daily"], "Daily close slope")

    weinstein = indicators["weinstein_stage"]
    wein_badge = "✓" if weinstein == "Stage 2" else ("✗" if weinstein == "Stage 4" else "○")
    add("TREND", "Weinstein Stage", weinstein, wein_badge, weinstein, "Weekly MA30w slope", badge=wein_badge)

    ema9v = last_valid(indicators["ema9"])
    ema9_badge = ma_badge(close, ema9v)
    add("TREND", "EMA9", fmt_price(ema9v), ema9_badge, ma_interp(close, ema9v, "EMA9"), "Close vs EMA9", badge=ema9_badge)

    sma20v = last_valid(indicators["sma20"])
    sma20_badge = ma_badge(close, sma20v)
    add("TREND", "SMA20", fmt_price(sma20v), sma20_badge, ma_interp(close, sma20v, "SMA20"), "Close vs SMA20", badge=sma20_badge)

    sma50v = last_valid(indicators["sma50"])
    sma50_badge = ma_badge(close, sma50v)
    add("TREND", "SMA50", fmt_price(sma50v), sma50_badge, ma_interp(close, sma50v, "SMA50"), "Close vs SMA50", badge=sma50_badge)

    sma200v = last_valid(indicators["sma200"])
    sma200_badge = ma_badge(close, sma200v)
    if sma200v is None:
        add("TREND", "SMA200", "N/A", "○", "N/A — SMA200 requires ≥200 bars", "Close vs SMA200", badge="○")
    else:
        add("TREND", "SMA200", fmt_price(sma200v), sma200_badge, ma_interp(close, sma200v, "SMA200"), "Close vs SMA200", badge=sma200_badge)

    adxv = last_valid(indicators["adx"])
    adx_interp = "Strong" if adxv and adxv > 25 else ("Weak" if adxv is not None else "N/A")
    add("TREND", "ADX(14)", fmt_float(adxv), "", f"Trend strength: {adx_interp}", "Wilder smoothing; strength only")

    plus_div = last_valid(indicators["plus_di"])
    minus_div = last_valid(indicators["minus_di"])
    add("TREND", "+DI(14)", fmt_float(plus_div), "", "Bullish directional movement" if plus_div and minus_div and plus_div > minus_div else "Bearish directional movement" if plus_div and minus_div else "N/A", "100 × Smoothed(+DM) / ATR")
    add("TREND", "-DI(14)", fmt_float(minus_div), "", "", "100 × Smoothed(-DM) / ATR")

    st_dir = last_valid(indicators["supertrend_direction"])
    st_val = last_valid(indicators["supertrend_value"])
    st_sig = "Bullish" if st_dir == 1 else ("Bearish" if st_dir == -1 else "N/A")
    add("TREND", "Supertrend(10,3)", fmt_price(st_val), "", st_sig, "ATR10 × 3; direction flips on Close cross")

    sar_val = last_valid(indicators["parabolic_sar"])
    sar_sig = "Below price (bullish)" if sar_val and sar_val < close else ("Above price (bearish)" if sar_val and sar_val > close else "N/A")
    add("TREND", "Parabolic SAR", fmt_price(sar_val), "", sar_sig, "AF 0.02/0.02/0.20")

    # MOMENTUM
    rsiv = last_valid(indicators["rsi14"])
    if rsiv is None:
        rsi_badge = "○"
        rsi_interp = "N/A — RSI unavailable"
    elif rsiv > 50:
        rsi_badge = "✓"
        rsi_interp = f"Bullish momentum ({rsiv:.2f})"
    elif rsiv < 40:
        rsi_badge = "✗"
        rsi_interp = f"Bearish momentum ({rsiv:.2f})"
    else:
        rsi_badge = "○"
        rsi_interp = f"Neutral momentum ({rsiv:.2f})"
    rsi_signal = rsi_badge + (" ⚡ Div" if rsi_div else "")
    add("MOMENTUM", "RSI(14)", fmt_float(rsiv), rsi_signal, rsi_interp, ">50 ✓, <40 ✗, 40-50 ○", badge=rsi_badge)

    macd_line = last_valid(indicators["macd_line"])
    macd_signal = last_valid(indicators["macd_signal"])
    macd_hist = last_valid(indicators["macd_histogram"])
    if macd_line is None or macd_signal is None:
        macd_badge = "○"
        macd_interp = "N/A — MACD unavailable"
    elif macd_line > macd_signal:
        macd_badge = "✓"
        macd_interp = f"MACD line above signal ({macd_line:.2f} vs {macd_signal:.2f})"
    elif macd_line < macd_signal:
        macd_badge = "✗"
        macd_interp = f"MACD line below signal ({macd_line:.2f} vs {macd_signal:.2f})"
    else:
        macd_badge = "○"
        macd_interp = "MACD line near signal"
    macd_signal_str = macd_badge + (" ⚡ Div" if macd_div else "")
    add("MOMENTUM", "MACD(12,26,9)", f"L:{fmt_float(macd_line)} S:{fmt_float(macd_signal)} H:{fmt_float(macd_hist)}", macd_signal_str, macd_interp, "Line>Signal ✓", badge=macd_badge)

    stoch_k = last_valid(indicators["stoch_k"])
    stoch_d = last_valid(indicators["stoch_d"])
    add("MOMENTUM", "Stochastic %K(14,3)", fmt_float(stoch_k), "", f"%K = SMA3 of raw %K", "%K oscillator")
    add("MOMENTUM", "Stochastic %D(14,3)", fmt_float(stoch_d), "", f"%D = SMA3 of %K", "Signal line")

    rocv = last_valid(indicators["roc20"])
    if rocv is None:
        roc_badge = "○"
        roc_interp = "N/A"
    elif rocv > 5:
        roc_badge = "✓"
        roc_interp = f"Positive momentum ({rocv:.2f}%)"
    elif rocv < -5:
        roc_badge = "✗"
        roc_interp = f"Negative momentum ({rocv:.2f}%)"
    else:
        roc_badge = "○"
        roc_interp = f"Neutral momentum ({rocv:.2f}%)"
    add("MOMENTUM", "ROC(20)", fmt_pct(rocv), roc_badge, roc_interp, ">+5% ✓, <-5% ✗", badge=roc_badge)

    mfiv = last_valid(indicators["mfi14"])
    add("MOMENTUM", "MFI(14)", fmt_float(mfiv), "", f"Money Flow Index ({mfiv:.2f})" if mfiv is not None else "N/A", "0-100 only")

    # VOLATILITY
    add("VOLATILITY", "ATR(14)", fmt_float(atr14), "", f"14-bar average true range", "Wilder smoothing of TR")

    atr_pct = last_valid(indicators["atr_pct"])
    if atr_pct is None:
        atr_pct_label = "N/A"
    elif atr_pct <= 1.0:
        atr_pct_label = "Very Low"
    elif atr_pct <= 2.0:
        atr_pct_label = "Low"
    elif atr_pct <= 3.5:
        atr_pct_label = "Normal"
    elif atr_pct <= 5.0:
        atr_pct_label = "High"
    else:
        atr_pct_label = "Extreme"
    add("VOLATILITY", "ATR%", fmt_pct(atr_pct), "○", f"Volatility regime: {atr_pct_label}", "(ATR14 / Close) × 100", badge="○")

    add("VOLATILITY", "BB Upper(20,2σ)", fmt_price(last_valid(indicators["bb_upper"])), "", "Bollinger upper band", "SMA20 + 2σ")
    # Bollinger position confluence factor (always ○) mapped to BB Mid row
    add("VOLATILITY", "BB Mid(20,2σ)", fmt_price(last_valid(indicators["bb_mid"])), "○", "Bollinger middle band / position context", "SMA20 / Bollinger position", badge="○")
    add("VOLATILITY", "BB Lower(20,2σ)", fmt_price(last_valid(indicators["bb_lower"])), "", "Bollinger lower band", "SMA20 − 2σ")

    # VOLUME
    vol_vs = last_valid(indicators["volume_vs_ma20"])
    if vol_vs is None:
        vol_badge = "○"
        vol_interp = "N/A"
    elif vol_vs > 1.0:
        vol_badge = "✓"
        vol_interp = f"Volume above MA20 ({vol_vs:.2f}x)"
    elif vol_vs < 0.8:
        vol_badge = "✗"
        vol_interp = f"Volume below MA20 ({vol_vs:.2f}x)"
    else:
        vol_badge = "○"
        vol_interp = f"Volume near MA20 ({vol_vs:.2f}x)"
    add("VOLUME", "Volume vs MA20", fmt_float(vol_vs), vol_badge, vol_interp, ">1.0x ✓, <0.8x ✗, 0.8-1.0x ○", badge=vol_badge)

    obv_now = last_valid(indicators["obv"])
    obv_20 = indicators["obv"].iloc[-20] if len(indicators["obv"]) >= 20 else None
    if obv_now is None:
        obv_badge = "○"
        obv_interp = "N/A"
    elif obv_20 is not None and obv_now > obv_20:
        obv_badge = "✓"
        obv_interp = "OBV rising over 20 bars"
    elif obv_20 is not None and obv_now < obv_20:
        obv_badge = "✗"
        obv_interp = "OBV falling over 20 bars"
    else:
        obv_badge = "○"
        obv_interp = "OBV flat over 20 bars"
    obv_signal = obv_badge + (" ⚡ Div" if obv_div else "")
    add("VOLUME", "OBV 20-bar chg", f"{fmt_float(obv_now)}" if obv_now is not None else "N/A", obv_signal, obv_interp, "Rising ✓, Falling ✗, Flat ○", badge=obv_badge)

    cmfv = last_valid(indicators["cmf20"])
    if cmfv is None:
        cmf_badge = "○"
        cmf_interp = "N/A"
    elif cmfv > 0.10:
        cmf_badge = "✓"
        cmf_interp = f"Accumulation pressure ({cmfv:.2f})"
    elif cmfv < -0.10:
        cmf_badge = "✗"
        cmf_interp = f"Distribution pressure ({cmfv:.2f})"
    else:
        cmf_badge = "○"
        cmf_interp = f"Neutral CMF ({cmfv:.2f})"
    add("VOLUME", "CMF(20)", fmt_float(cmfv), cmf_badge, cmf_interp, ">+0.10 ✓, <-0.10 ✗", badge=cmf_badge)

    vol_syn = indicators["volume_synthesis"]
    if "Accumulation" in vol_syn:
        syn_badge = "✓"
    elif "Distribution" in vol_syn:
        syn_badge = "✗"
    else:
        syn_badge = "○"
    add("VOLUME", "Volume Synthesis", vol_syn, syn_badge, vol_syn, "Accumulation/Distribution/Neutral", badge=syn_badge)

    # STRUCTURE
    add("STRUCTURE", "Ichimoku Tenkan(9)", fmt_price(last_valid(indicators["ichimoku_tenkan"])), "", "(HH9 + LL9) / 2", "Conversion line")
    add("STRUCTURE", "Ichimoku Kijun(26)", fmt_price(last_valid(indicators["ichimoku_kijun"])), "", "(HH26 + LL26) / 2", "Base line")
    add("STRUCTURE", "Ichimoku Senkou A", fmt_price(last_valid(indicators["ichimoku_senkou_a"])), "", "(Tenkan + Kijun)/2 shifted +26", "Leading span A")
    add("STRUCTURE", "Ichimoku Senkou B(52)", fmt_price(last_valid(indicators["ichimoku_senkou_b"])), "", "(HH52 + LL52)/2 shifted +26", "Leading span B")
    add("STRUCTURE", "Ichimoku Chikou", fmt_price(last_valid(indicators["ichimoku_chikou"])), "", "Close shifted −26", "Lagging span")

    div_parts = []
    if rsi_div:
        div_parts.append(f"RSI: {rsi_div}")
    if macd_div:
        div_parts.append(f"MACD: {macd_div}")
    if obv_div:
        div_parts.append(f"OBV: {obv_div}")
    div_text = "; ".join(div_parts) if div_parts else "None"
    # Divergence is displayed in Value/Interpretation, not as a confluence badge
    add("STRUCTURE", "Divergence Scan", div_text, "", div_text, "Regular/Hidden Bullish/Bearish on RSI/MACD/OBV")

    # Simple candlestick detection
    candle = detect_candlestick_pattern(df)
    add("STRUCTURE", "Candlestick (Tier 1)", candle, "", candle, "Hammer, Engulfing, Doji, etc.")

    # Chart patterns (Tier 2) — use detected patterns from structure
    if structure and structure.patterns:
        from .patterns import best_pattern
        best = best_pattern(structure.patterns)
        if best:
            pattern_text = f"{best.name} ({best.direction}) — {best.status}"
            pattern_interp = f"{best.name}: {best.description}"
        else:
            pattern_text = "Detected (see list)"
            pattern_interp = "; ".join(f"{p.name} ({p.direction}) {p.status}" for p in structure.patterns)
    else:
        pattern_text = "None detected"
        pattern_interp = "No confirmed chart pattern"
    add("STRUCTURE", "Chart Patterns (Tier 2)", pattern_text, "", pattern_interp, "Double Top/Bottom, H&S, Triangle, Wedge, etc.")

    # WEEKLY
    add("WEEKLY", "MA20 Weekly", fmt_price(last_valid(indicators["weekly_sma20"])), "", "SMA20 of weekly closes", "Weekly trend")
    add("WEEKLY", "MA50 Weekly", fmt_price(last_valid(indicators["weekly_sma50"])), "", "SMA50 of weekly closes", "Weekly trend")
    add("WEEKLY", "RSI Weekly", fmt_float(last_valid(indicators["weekly_rsi14"])), "", "RSI14 of weekly closes", "Weekly momentum")

    w_macd_line = last_valid(indicators["weekly_macd_line"])
    w_macd_signal = last_valid(indicators["weekly_macd_signal"])
    add("WEEKLY", "MACD Weekly", f"L:{fmt_float(w_macd_line)} S:{fmt_float(w_macd_signal)}", "", f"MACD(12,26,9) of weekly closes", "Weekly momentum")

    return rows


def detect_candlestick_pattern(df: pd.DataFrame) -> str:
    """Simple candlestick pattern detection on last bar."""
    if len(df) < 3:
        return "N/A"

    last = df.iloc[-1]
    prev = df.iloc[-2]
    body = abs(last["Close"] - last["Open"])
    range_ = last["High"] - last["Low"]
    upper_shadow = last["High"] - max(last["Close"], last["Open"])
    lower_shadow = min(last["Close"], last["Open"]) - last["Low"]

    if range_ == 0:
        return "Doji"

    if body / range_ < 0.1:
        return "Doji"

    # Hammer / Inverted hammer
    if lower_shadow > 2 * body and upper_shadow < body:
        return "Hammer"
    if upper_shadow > 2 * body and lower_shadow < body:
        return "Inverted Hammer"

    # Engulfing
    if last["Close"] > last["Open"] and prev["Close"] < prev["Open"]:
        if last["Open"] < prev["Close"] and last["Close"] > prev["Open"]:
            return "Bullish Engulfing"
    if last["Close"] < last["Open"] and prev["Close"] > prev["Open"]:
        if last["Open"] > prev["Close"] and last["Close"] < prev["Open"]:
            return "Bearish Engulfing"

    if last["Close"] > last["Open"]:
        return "Bullish Candle"
    return "Bearish Candle"


def render_markdown(
    ticker: str,
    df: pd.DataFrame,
    indicators: Dict,
    structure: Structure,
    setup: Setup,
    tradeability: "Tradeability",
    decision: Decision,
    market_regime: Dict,
    params: Dict,
) -> str:
    """Render full markdown report for a single ticker."""
    close = df["Close"].iloc[-1]
    date = df.index[-1].strftime("%Y-%m-%d")
    bars = len(df)

    lines = []
    lines.append(f"# BEI Swing Engine v8.0 — Laporan Analisis: {ticker}")
    lines.append("")
    lines.append(f"**Tanggal analisis:** {date}  ")
    lines.append(f"**Jumlah bar:** {bars}  ")
    lines.append(f"**Rentang tanggal:** {df.index.min().strftime('%Y-%m-%d')} s/d {df.index.max().strftime('%Y-%m-%d')}  ")
    lines.append(f"**Parameter:** MODE={params.get('MODE','A')}, HORIZON={params.get('HORIZON','SWING')}, DIRECTION={params.get('DIRECTION','BOTH')}, POSITION={params.get('POSITION','UNKNOWN')}, MODAL=Rp {params.get('MODAL',10000000):,.0f}, RISK={params.get('RISK',2)}%  ".replace(",", "."))
    lines.append("")

    # Executive Summary
    lines.append("## 1. Executive Summary")
    lines.append("")
    lines.append(f"- **Keputusan:** `{decision.decision}`")
    if decision.decision_direction != "NONE":
        lines.append(f"- **Arah keputusan:** `{decision.decision_direction}`")
    lines.append(f"- **Thesis:** {decision.thesis_state}")
    lines.append(f"- **Setup utama:** {setup.type} ({setup.direction}) — {setup.status}")
    lines.append(f"- **Konfluensi:** {decision.confluence_state}")
    lines.append(f"- **Tradeability:** {decision.tradeability_state}")
    lines.append(f"- **Harga terakhir:** Rp {fmt_price(close)}")
    if decision.entry is not None:
        lines.append(f"- **Entry:** Rp {fmt_price(decision.entry)} | **SL:** Rp {fmt_price(decision.sl)} | **TP1:** Rp {fmt_price(decision.tp1)} | **TP2:** Rp {fmt_price(decision.tp2)} | **R/R:** {fmt_float(decision.rr_raw)}")
    lines.append("")

    # Market Context
    lines.append("## 2. Market Context (IHSG)")
    lines.append("")
    lines.append(f"- **Regime:** {market_regime['regime']}")
    if market_regime['trend'] != "N/A":
        lines.append(f"- **Trend IHSG:** {market_regime['trend']}")
    lines.append("")

    # Market Structure
    lines.append("## 3. Market Structure")
    lines.append("")
    lines.append(f"- **Struktur trend:** {structure.trend_structure}")
    lines.append(f"- **Swing high terakhir:** {structure.last_swing_high.price if structure.last_swing_high else 'N/A'} ({structure.last_swing_high.date.strftime('%Y-%m-%d') if structure.last_swing_high else 'N/A'})")
    lines.append(f"- **Swing low terakhir:** {structure.last_swing_low.price if structure.last_swing_low else 'N/A'} ({structure.last_swing_low.date.strftime('%Y-%m-%d') if structure.last_swing_low else 'N/A'})")
    lines.append("")
    lines.append("### Support Levels")
    if structure.support_levels:
        for s in structure.support_levels[:5]:
            lines.append(f"- Rp {fmt_price(s['price'])} — {s['touches']} touches")
    else:
        lines.append("- N/A")
    lines.append("")
    lines.append("### Resistance Levels")
    if structure.resistance_levels:
        for r in structure.resistance_levels[:5]:
            lines.append(f"- Rp {fmt_price(r['price'])} — {r['touches']} touches")
    else:
        lines.append("- N/A")
    lines.append("")
    lines.append("### Fibonacci Levels")
    if structure.fib_levels:
        for k, v in structure.fib_levels.items():
            if k not in {"direction", "anchor_high", "anchor_low"}:
                lines.append(f"- **{k}:** Rp {fmt_price(v)}")
    else:
        lines.append("- N/A")
    lines.append("")

    # Technical Indicators
    lines.append("## 4. Technical Indicators")
    lines.append("")
    rows = build_indicator_table(df, indicators)
    lines.append(render_indicator_table_markdown(rows))
    lines.append("")

    # Key Levels
    lines.append("## 5. Key Levels")
    lines.append("")
    lines.append("### Pivot Points")
    pivot = (df["High"].iloc[-2] + df["Low"].iloc[-2] + df["Close"].iloc[-2]) / 3.0 if len(df) >= 2 else None
    lines.append(f"- **Pivot (last completed bar):** Rp {fmt_price(pivot)}")
    lines.append("")

    # Pattern & Divergence Alerts
    lines.append("## 6. Pattern & Divergence Alerts")
    lines.append("")
    # Chart patterns
    if structure.patterns:
        lines.append("### Chart Patterns")
        for p in structure.patterns:
            lines.append(f"- **{p.name}** ({p.direction}) — {p.status}: {p.description}")
        lines.append("")
    else:
        lines.append("### Chart Patterns")
        lines.append("- None detected.")
        lines.append("")
    # BOS/CHoCH
    if structure.bos_choch:
        lines.append("### BOS / CHoCH")
        for e in structure.bos_choch[-3:]:
            lines.append(f"- **{e['type']}** {e['direction']} @ Rp {fmt_price(e['price'])} ({e['date'].strftime('%Y-%m-%d')}) — {e['description']}")
    else:
        lines.append("### BOS / CHoCH")
        lines.append("- Tidak ada BOS/CHoCH signifikan.")
    lines.append("")

    # Confluence & Conflict
    lines.append("## 7. Confluence & Conflict")
    lines.append("")
    lines.append(f"- **Evidence state:** {decision.evidence_state}")
    lines.append(f"- **Confluence state:** {decision.confluence_state}")
    if decision.warnings:
        lines.append("### Peringatan")
        for w in decision.warnings:
            lines.append(f"- {w}")
    lines.append("")

    # Setup Status
    lines.append("## 8. Setup Status")
    lines.append("")
    lines.append(f"- **Setup:** {setup.type}")
    lines.append(f"- **Direction:** {setup.direction}")
    lines.append(f"- **Status:** {setup.status}")
    lines.append(f"- **Basis level:** Rp {fmt_price(setup.basis_level)}")
    lines.append(f"- **Trigger price:** Rp {fmt_price(setup.trigger_price)}")
    lines.append(f"- **Invalidation price:** Rp {fmt_price(setup.invalidation_price)}")
    lines.append(f"- **Deskripsi:** {setup.description}")
    lines.append("")

    # Trading Plan
    lines.append("## 9. Trading Plan")
    lines.append("")
    plan = tradeability.plan
    if plan.entry is not None:
        lines.append(f"- **Entry:** Rp {fmt_price(plan.entry)}")
        lines.append(f"- **Stop Loss:** Rp {fmt_price(plan.sl)}")
        lines.append(f"- **TP1:** Rp {fmt_price(plan.tp1)}")
        lines.append(f"- **TP2:** Rp {fmt_price(plan.tp2)}")
        lines.append(f"- **R/R:** {fmt_float(plan.rr_raw)} ({plan.rr_status})")
        lines.append("")
        lines.append("### Position Sizing")
        ps = plan.position_sizing
        lines.append(f"- Modal: Rp {ps.get('modal', 0):,.0f}".replace(",", "."))
        lines.append(f"- Risk %%: {ps.get('risk_pct', 0) * 100:.2f}%")
        lines.append(f"- Risk budget: Rp {ps.get('risk_budget', 0):,.0f}".replace(",", "."))
        lines.append(f"- Risk per share: Rp {fmt_price(ps.get('risk_per_share', 0))}")
        lines.append(f"- Raw shares: {ps.get('raw_shares', 0):.2f}")
        lines.append(f"- Lots: {ps.get('lots', 0)}")
        lines.append(f"- Final shares: {ps.get('final_shares', 0)}")
        lines.append(f"- Actual risk: Rp {ps.get('actual_risk', 0):,.0f} ({ps.get('actual_risk_pct', 0) * 100:.2f}%)".replace(",", "."))
    else:
        lines.append("- Tidak ada rencana perdagangan yang valid.")
    lines.append("")

    # Decision Trace
    lines.append("## 10. Decision Trace")
    lines.append("")
    lines.append(f"- **Thesis state:** {decision.thesis_state}")
    lines.append(f"- **Primary setup:** {setup.type} {setup.direction} {setup.status}")
    lines.append(f"- **Evidence state:** {decision.evidence_state}")
    lines.append(f"- **Confluence state:** {decision.confluence_state}")
    lines.append(f"- **Tradeability state:** {decision.tradeability_state}")
    lines.append(f"- **Warnings:** {', '.join(decision.warnings) if decision.warnings else 'None'}")
    lines.append(f"- **Vetoes triggered:** {', '.join(decision.vetoes_triggered) if decision.vetoes_triggered else 'None'}")
    lines.append(f"- **Reason codes:** {', '.join(decision.reason_codes) if decision.reason_codes else 'None'}")
    lines.append(f"- **Position branch:** {decision.position_branch}")
    if decision.dual_branch:
        lines.append(f"- **Dual branch (UNKNOWN):** NO_POSITION={decision.dual_branch.get('no_position')}, EXISTING_POSITION={decision.dual_branch.get('existing_position')}")
    lines.append("")

    # Disclaimer
    lines.append("## 11. Disclaimer")
    lines.append("")
    lines.append(DISCLAIMER)
    lines.append("")

    return "\n".join(lines)


def _markdown_table_to_html(lines: List[str], start: int) -> Tuple[str, int]:
    """Convert a markdown table block to HTML table; return HTML and index after table."""
    import html
    rows = []
    i = start
    while i < len(lines) and lines[i].startswith("|"):
        rows.append(lines[i])
        i += 1

    if len(rows) < 2:
        return "", i

    html_rows = []
    for idx, row in enumerate(rows):
        cells = [c.strip() for c in row.split("|")][1:-1]
        # Skip markdown separator rows
        if idx == 1 and all(set(c) <= {"-", ":", " "} for c in cells):
            continue
        tag = "th" if idx == 0 else "td"
        html_rows.append("<tr>" + "".join(f"<{tag}>{html.escape(c)}</{tag}>" for c in cells) + "</tr>")

    return "<table>" + "".join(html_rows) + "</table>", i


def render_html_single(ticker: str, markdown_text: str) -> str:
    """Render single-ticker markdown into simple HTML with proper tables."""
    import html
    lines = markdown_text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("|"):
            table_html, i = _markdown_table_to_html(lines, i)
            out.append(table_html)
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            content = line.lstrip("# ").strip()
            out.append(f"<h{level}>{html.escape(content)}</h{level}>")
        elif line.startswith("**") and line.endswith("**"):
            out.append(f"<p><strong>{html.escape(line[2:-2])}</strong></p>")
        elif line.startswith("-"):
            out.append(f"<li>{html.escape(line[2:])}</li>")
        elif line:
            out.append(f"<p>{html.escape(line)}</p>")
        else:
            out.append("<br>")
        i += 1

    body = "\n".join(out)
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<title>BEI Swing Engine v8.0 — {ticker}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
h1 {{ color: #1a5276; }}
h2 {{ color: #2874a6; border-bottom: 1px solid #ccc; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
th, td {{ border: 1px solid #ddd; padding: 6px; text-align: left; }}
th {{ background-color: #f2f2f2; }}
ul {{ margin-top: 0; }}
</style>
</head>
<body>
{body}
</body>
</html>"""


def render_pdf_single(ticker: str, html_text: str, dest) -> bool:
    """Render HTML report to PDF using xhtml2pdf.

    dest can be a file path (str) or a file-like object opened in binary write mode.
    """
    try:
        from xhtml2pdf import pisa
    except ImportError:
        return False

    # Ensure self-closing tags and basic XHTML cleanliness
    html = html_text.replace("<br>", "<br/>")
    html = html.replace("<hr>", "<hr/>")

    if isinstance(dest, str):
        with open(dest, "wb") as f:
            pdf = pisa.CreatePDF(html, dest=f)
            return not pdf.err
    else:
        pdf = pisa.CreatePDF(html, dest=dest)
        return not pdf.err


def render_excel_single(ticker: str, rows: List[Dict], path: str):
    """Render 42-row indicator table to Excel."""
    df = pd.DataFrame(rows)
    df = df.drop(columns=["Badge"], errors="ignore")
    df.to_excel(path, index=False, sheet_name=ticker)


def render_indicator_table_markdown(rows: List[Dict]) -> str:
    """Render the 42-row indicator table as markdown."""
    lines = []
    lines.append("| Category | Indicator | Value | Signal | Interpretation | Standard / Reference |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        sig = r["Signal"]
        lines.append(f"| {r['Category']} | {r['Indicator']} | {r['Value']} | {sig} | {r['Interpretation']} | {r['Standard / Reference']} |")
    return "\n".join(lines)


def render_calc_only_markdown(
    ticker: str,
    df: pd.DataFrame,
    indicators: Dict,
    structure: Structure,
    setup: Setup,
    market_regime: Dict,
    params: Dict,
) -> str:
    """MODE=B: calc-only output (indicators, levels, setup status; no decision/trade plan)."""
    close = df["Close"].iloc[-1]
    date = df.index[-1].strftime("%Y-%m-%d")
    bars = len(df)

    lines = []
    lines.append(f"# BEI Swing Engine v8.0 — Kalkulasi: {ticker}")
    lines.append("")
    lines.append(f"**Tanggal analisis:** {date}  ")
    lines.append(f"**Jumlah bar:** {bars}  ")
    lines.append(f"**Rentang tanggal:** {df.index.min().strftime('%Y-%m-%d')} s/d {df.index.max().strftime('%Y-%m-%d')}  ")
    lines.append(f"**Parameter:** MODE={params.get('MODE','B')}, HORIZON={params.get('HORIZON','SWING')}, DIRECTION={params.get('DIRECTION','BOTH')}, POSITION={params.get('POSITION','UNKNOWN')}, MODAL=Rp {params.get('MODAL',10000000):,.0f}, RISK={params.get('RISK',2)}%  ".replace(",", "."))
    lines.append("")

    lines.append("## 1. Market Context (IHSG)")
    lines.append("")
    lines.append(f"- **Regime:** {market_regime['regime']}")
    if market_regime['trend'] != "N/A":
        lines.append(f"- **Trend IHSG:** {market_regime['trend']}")
    lines.append("")

    lines.append("## 2. Market Structure")
    lines.append("")
    lines.append(f"- **Struktur trend:** {structure.trend_structure}")
    lines.append(f"- **Swing high terakhir:** {structure.last_swing_high.price if structure.last_swing_high else 'N/A'} ({structure.last_swing_high.date.strftime('%Y-%m-%d') if structure.last_swing_high else 'N/A'})")
    lines.append(f"- **Swing low terakhir:** {structure.last_swing_low.price if structure.last_swing_low else 'N/A'} ({structure.last_swing_low.date.strftime('%Y-%m-%d') if structure.last_swing_low else 'N/A'})")
    lines.append("")
    lines.append("### Support Levels")
    if structure.support_levels:
        for s in structure.support_levels[:5]:
            lines.append(f"- Rp {fmt_price(s['price'])} — {s['touches']} touches")
    else:
        lines.append("- N/A")
    lines.append("")
    lines.append("### Resistance Levels")
    if structure.resistance_levels:
        for r in structure.resistance_levels[:5]:
            lines.append(f"- Rp {fmt_price(r['price'])} — {r['touches']} touches")
    else:
        lines.append("- N/A")
    lines.append("")
    lines.append("### Fibonacci Levels")
    if structure.fib_levels:
        for k, v in structure.fib_levels.items():
            if k not in {"direction", "anchor_high", "anchor_low"}:
                lines.append(f"- **{k}:** Rp {fmt_price(v)}")
    else:
        lines.append("- N/A")
    lines.append("")

    lines.append("## 3. Technical Indicators")
    lines.append("")
    rows = build_indicator_table(df, indicators)
    lines.append(render_indicator_table_markdown(rows))
    lines.append("")

    lines.append("## 4. Setup Status")
    lines.append("")
    lines.append(f"- **Setup:** {setup.type}")
    lines.append(f"- **Direction:** {setup.direction}")
    lines.append(f"- **Status:** {setup.status}")
    lines.append(f"- **Basis level:** Rp {fmt_price(setup.basis_level)}")
    lines.append(f"- **Trigger price:** Rp {fmt_price(setup.trigger_price)}")
    lines.append(f"- **Invalidation price:** Rp {fmt_price(setup.invalidation_price)}")
    lines.append(f"- **Deskripsi:** {setup.description}")
    lines.append("")

    lines.append("## 5. Disclaimer")
    lines.append("")
    lines.append(DISCLAIMER)
    lines.append("")

    return "\n".join(lines)


def render_screening_summary(tickers_data: List[Dict]) -> str:
    """MODE=C: screening-only aggregate summary."""
    lines = []
    lines.append("# BEI Swing Engine v8.0 — Screening Summary")
    lines.append("")
    lines.append("| Ticker | Thesis | Setup | Tradeability | Decision | Warnings |")
    lines.append("|---|---|---|---|---|---|")
    for d in tickers_data:
        warnings = "; ".join(d.get("warnings", []))[:80]
        lines.append(f"| {d['ticker']} | {d['thesis']} | {d['setup']} | {d['tradeability']} | {d['decision']} | {warnings} |")
    lines.append("")
    return "\n".join(lines)


def render_aggregate_summary(tickers_data: List[Dict]) -> str:
    """Render aggregate summary table for multi-ticker output."""
    lines = []
    lines.append("---")
    lines.append("## Aggregate Summary")
    lines.append("")
    lines.append("| Ticker | Thesis | Setup | Tradeability | Decision | Warnings |")
    lines.append("|---|---|---|---|---|---|")
    for d in tickers_data:
        warnings = "; ".join(d.get("warnings", []))[:80]
        lines.append(f"| {d['ticker']} | {d['thesis']} | {d['setup']} | {d['tradeability']} | {d['decision']} | {warnings} |")
    lines.append("")
    return "\n".join(lines)
