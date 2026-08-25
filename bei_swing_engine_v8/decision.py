"""
Decision engine (Module 07).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd
import numpy as np

from .setup import Setup
from .risk import Tradeability
from .structure import Structure


@dataclass
class Decision:
    decision: str = "INSUFFICIENT_DATA"
    decision_direction: str = "NONE"
    thesis_state: str = "INSUFFICIENT"
    primary_setup: Setup = field(default_factory=lambda: Setup(type="None", direction="NONE", status="NONE"))
    evidence_state: str = "None"
    confluence_state: str = "None"
    tradeability_state: str = "NOT_APPLICABLE"
    warnings: List[str] = field(default_factory=list)
    vetoes_triggered: List[str] = field(default_factory=list)
    reason_codes: List[str] = field(default_factory=list)
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    rr_raw: Optional[float] = None
    position_branch: str = "NO_POSITION"
    dual_branch: Optional[Dict] = None
    trace: Dict = field(default_factory=dict)


def badge_value(badge: str) -> int:
    if badge == "✓":
        return 1
    if badge == "✗":
        return -1
    return 0


def compute_evidence_state(
    indicators: Dict,
    structure: Structure,
    setup: Setup,
) -> str:
    """
    Compute evidence state from confluence dimensions.
    Returns: Strong, Moderate, Weak, None, Conflicted.
    Also stores dimension list in indicators for later use.
    """
    dimensions = []

    # 1. Structure
    if structure and structure.trend_structure.startswith("Uptrend"):
        dimensions.append(("Structure", 1))
    elif structure and structure.trend_structure.startswith("Downtrend"):
        dimensions.append(("Structure", -1))

    # 2. Trend (from MAs)
    ema9v = indicators["ema9"].iloc[-1]
    sma20v = indicators["sma20"].iloc[-1]
    sma50v = indicators["sma50"].iloc[-1]
    sma200v = indicators["sma200"].iloc[-1]

    ma_bullish = 0
    ma_bearish = 0
    if not pd.isna(ema9v) and not pd.isna(sma20v) and ema9v > sma20v:
        ma_bullish += 1
    if not pd.isna(ema9v) and not pd.isna(sma20v) and ema9v < sma20v:
        ma_bearish += 1
    if not pd.isna(sma20v) and not pd.isna(sma50v) and sma20v > sma50v:
        ma_bullish += 1
    if not pd.isna(sma20v) and not pd.isna(sma50v) and sma20v < sma50v:
        ma_bearish += 1
    if not pd.isna(sma50v) and not pd.isna(sma200v) and sma50v > sma200v:
        ma_bullish += 1
    if not pd.isna(sma50v) and not pd.isna(sma200v) and sma50v < sma200v:
        ma_bearish += 1

    if ma_bullish >= 2 and ma_bearish == 0:
        dimensions.append(("Trend", 1))
    elif ma_bearish >= 2 and ma_bullish == 0:
        dimensions.append(("Trend", -1))

    # 3. Trend Strength (ADX)
    adx = indicators["adx"].iloc[-1]
    plus_di = indicators["plus_di"].iloc[-1]
    minus_di = indicators["minus_di"].iloc[-1]
    if not pd.isna(adx) and adx > 25:
        if not pd.isna(plus_di) and not pd.isna(minus_di):
            if plus_di > minus_di:
                dimensions.append(("Trend Strength", 1))
            elif minus_di > plus_di:
                dimensions.append(("Trend Strength", -1))

    # 4. Momentum
    rsi = indicators["rsi14"].iloc[-1]
    macd_line = indicators["macd_line"].iloc[-1]
    macd_signal = indicators["macd_signal"].iloc[-1]
    roc = indicators["roc20"].iloc[-1]

    mom_bullish = 0
    mom_bearish = 0
    if not pd.isna(rsi):
        if rsi > 50:
            mom_bullish += 1
        elif rsi < 40:
            mom_bearish += 1
    if not pd.isna(macd_line) and not pd.isna(macd_signal):
        if macd_line > macd_signal:
            mom_bullish += 1
        elif macd_line < macd_signal:
            mom_bearish += 1
    if not pd.isna(roc):
        if roc > 5:
            mom_bullish += 1
        elif roc < -5:
            mom_bearish += 1

    if mom_bullish >= 2 and mom_bearish == 0:
        dimensions.append(("Momentum", 1))
    elif mom_bearish >= 2 and mom_bullish == 0:
        dimensions.append(("Momentum", -1))

    # 5. Participation/Volume
    vol_synth = indicators["volume_synthesis"]
    obv_change = indicators["obv"].iloc[-1] - indicators["obv"].iloc[-20] if len(indicators["obv"]) >= 20 else 0
    cmf = indicators["cmf20"].iloc[-1]
    vol_vs_ma = indicators["volume_vs_ma20"].iloc[-1]

    vol_bullish = 0
    vol_bearish = 0
    if "Accumulation" in vol_synth:
        vol_bullish += 1
    if "Distribution" in vol_synth:
        vol_bearish += 1
    if obv_change > 0:
        vol_bullish += 1
    elif obv_change < 0:
        vol_bearish += 1
    if not pd.isna(cmf) and cmf > 0.10:
        vol_bullish += 1
    elif not pd.isna(cmf) and cmf < -0.10:
        vol_bearish += 1
    if not pd.isna(vol_vs_ma) and vol_vs_ma > 1.0:
        vol_bullish += 1

    if vol_bullish >= 2 and vol_bearish == 0:
        dimensions.append(("Participation/Volume", 1))
    elif vol_bearish >= 2 and vol_bullish == 0:
        dimensions.append(("Participation/Volume", -1))

    # 6. Price Location
    bb_upper = indicators["bb_upper"].iloc[-1]
    bb_lower = indicators["bb_lower"].iloc[-1]
    sma200v = indicators["sma200"].iloc[-1]
    # Use EMA9 as proxy for current close (close ≈ ema9 on last bar)
    proxy_close = ema9v
    if not pd.isna(proxy_close) and not pd.isna(bb_upper) and not pd.isna(bb_lower):
        if proxy_close > bb_upper:
            dimensions.append(("Price Location", 1))
        elif proxy_close < bb_lower:
            dimensions.append(("Price Location", -1))
    if not pd.isna(proxy_close) and not pd.isna(sma200v):
        if proxy_close > sma200v:
            # If above SMA200, bullish price location
            if not any(d[0] == "Price Location" for d in dimensions):
                dimensions.append(("Price Location", 1))
        elif proxy_close < sma200v:
            if not any(d[0] == "Price Location" for d in dimensions):
                dimensions.append(("Price Location", -1))

    # 7. Pattern/Setup
    if setup.status == "TRIGGERED":
        if setup.direction == "LONG":
            dimensions.append(("Pattern/Setup", 1))
        elif setup.direction == "SHORT":
            dimensions.append(("Pattern/Setup", -1))

    # Store dimensions for later reference
    indicators["_evidence_dimensions"] = dimensions

    # Count aligned dimensions
    bullish_dims = [d for d in dimensions if d[1] == 1]
    bearish_dims = [d for d in dimensions if d[1] == -1]

    if len(bullish_dims) >= 4 and len(bearish_dims) == 0:
        return "Strong"
    if len(bearish_dims) >= 4 and len(bullish_dims) == 0:
        return "Strong"
    if len(bullish_dims) == 3 and len(bearish_dims) == 0:
        return "Moderate"
    if len(bearish_dims) == 3 and len(bullish_dims) == 0:
        return "Moderate"
    if len(bullish_dims) == 2 and len(bearish_dims) == 0:
        return "Weak"
    if len(bearish_dims) == 2 and len(bullish_dims) == 0:
        return "Weak"
    if len(bullish_dims) >= 2 and len(bearish_dims) >= 2:
        return "Conflicted"
    if len(bullish_dims) >= 1 or len(bearish_dims) >= 1:
        return "Weak"
    return "None"


def derive_thesis(
    indicators: Dict,
    structure: Structure,
    setup: Setup,
    evidence_state: str,
) -> str:
    """Derive directional thesis."""
    if evidence_state == "Conflicted":
        return "CONFLICTED"

    # Structure-based thesis
    if structure.trend_structure.startswith("Uptrend"):
        return "BULLISH"
    if structure.trend_structure.startswith("Downtrend"):
        return "BEARISH"

    # MA-based fallback
    close = indicators["ema9"].index[-1]
    ema9v = indicators["ema9"].iloc[-1]
    sma20v = indicators["sma20"].iloc[-1]
    sma50v = indicators["sma50"].iloc[-1]
    sma200v = indicators["sma200"].iloc[-1]

    if not pd.isna(ema9v) and not pd.isna(sma20v) and not pd.isna(sma50v):
        if ema9v > sma20v > sma50v:
            return "BULLISH"
        if ema9v < sma20v < sma50v:
            return "BEARISH"

    if setup.direction == "LONG":
        return "BULLISH"
    if setup.direction == "SHORT":
        return "BEARISH"

    return "NEUTRAL"


def check_warnings(indicators: Dict, setup: Setup, tradeability: Tradeability, evidence_state: str) -> List[str]:
    """Collect soft warnings."""
    warnings = []

    rsi = indicators["rsi14"].iloc[-1]
    if not pd.isna(rsi):
        if rsi > 70:
            warnings.append("RSI overbought")
        elif rsi < 30:
            warnings.append("RSI oversold")

    atr_pct = indicators["atr_pct"].iloc[-1]
    if not pd.isna(atr_pct):
        if atr_pct > 5.0:
            warnings.append("Extreme volatility")
        elif atr_pct > 3.5:
            warnings.append("High volatility")

    macd_line = indicators["macd_line"].iloc[-1]
    macd_signal = indicators["macd_signal"].iloc[-1]
    macd_hist = indicators["macd_histogram"].iloc[-1]
    if not pd.isna(macd_hist):
        prev_hist = indicators["macd_histogram"].iloc[-2] if len(indicators["macd_histogram"]) >= 2 else None
        if prev_hist is not None and abs(macd_hist) < abs(prev_hist):
            warnings.append("MACD weakening")

    if evidence_state == "Weak":
        warnings.append("Limited confluence")

    if tradeability.plan and tradeability.plan.warnings:
        warnings.extend(tradeability.plan.warnings)

    # Divergence alerts handled separately in indicators output
    return warnings


def run_decision_engine(
    df: pd.DataFrame,
    indicators: Dict,
    structure: Structure,
    setup: Setup,
    tradeability: Tradeability,
    params: Dict,
    position_branch: str = "NO_POSITION",
    held_position_direction: str = "LONG",
) -> Decision:
    """
    Run full decision engine for a given position branch.

    Args:
        held_position_direction: Direction of an existing held position.
            Only used when position_branch == "EXISTING_POSITION". Default LONG for backward compatibility.
    """
    dec = Decision(position_branch=position_branch)
    dec.primary_setup = setup
    dec.tradeability_state = tradeability.state

    # Pre-compute evidence state and thesis for all paths
    evidence_state = compute_evidence_state(indicators, structure, setup)
    dec.evidence_state = evidence_state
    dec.confluence_state = evidence_state
    thesis = derive_thesis(indicators, structure, setup, evidence_state)

    # G0 DATA GATE
    if len(df) < 20:
        dec.thesis_state = "INSUFFICIENT"
        dec.decision = "INSUFFICIENT_DATA"
        dec.reason_codes.append("INS-D-01")
        build_decision_trace(dec, setup)
        return dec

    required_indicators = ["ema9", "sma20", "sma50", "sma200", "atr14", "rsi14"]
    if any(
        indicators.get(k) is None or len(indicators[k]) == 0 or pd.isna(indicators[k].iloc[-1])
        for k in required_indicators
    ):
        dec.thesis_state = "INSUFFICIENT"
        dec.decision = "INSUFFICIENT_DATA"
        dec.reason_codes.append("INS-D-02")
        build_decision_trace(dec, setup)
        return dec

    # G1 DIRECTION ELIGIBILITY
    direction = params.get("DIRECTION", "BOTH")
    if setup.direction not in {"NONE", direction} and direction != "BOTH":
        dec.thesis_state = thesis
        dec.decision = "NO_SETUP"
        dec.reason_codes.append("NOSETUP-02")
        dec.vetoes_triggered.append("Direction not permitted")
        build_decision_trace(dec, setup)
        return dec

    # G2 STRUCTURAL VETO
    # Active structural invalidation vs setup direction
    # (Simplified: if setup invalidated)
    if setup.status == "INVALIDATED":
        dec.decision = "NO_SETUP"
        dec.reason_codes.append("VETO-01")
        dec.vetoes_triggered.append("VETO-01: Invalidated setup")
        build_decision_trace(dec, setup)
        return dec

    # G3 SETUP ACTIONABILITY
    if setup.status in {"DEVELOPING", "NONE"}:
        dec.thesis_state = derive_thesis(indicators, structure, setup, evidence_state)
        if dec.thesis_state == "NEUTRAL":
            dec.decision = "NO_SETUP"
            dec.reason_codes.append("NOSETUP-01")
        else:
            dec.decision = "WAIT"
            dec.reason_codes.append("WAIT-01")
        build_decision_trace(dec, setup)
        return dec

    if evidence_state == "Conflicted":
        dec.thesis_state = "CONFLICTED"
        dec.decision = "WAIT"
        dec.reason_codes.append("WAIT-03")
        build_decision_trace(dec, setup)
        return dec

    # Minimum evidence contract: >=2 independent dimensions, at least one must be Structure or Price Location
    dimensions = indicators.get("_evidence_dimensions", [])
    aligned_dims = [d for d in dimensions if d[1] == (1 if thesis == "BULLISH" else (-1 if thesis == "BEARISH" else 0))]
    has_structure_or_price = any(d[0] in {"Structure", "Price Location"} for d in aligned_dims)
    evidence_contract_met = len(aligned_dims) >= 2 and has_structure_or_price

    if not evidence_contract_met and setup.status in {"CONFIRMED", "TRIGGERED"}:
        dec.thesis_state = thesis
        dec.decision = "WAIT"
        dec.reason_codes.append("WAIT-05")
        build_decision_trace(dec, setup)
        return dec

    # G5 TRADEABILITY
    if tradeability.state == "UNTRADEABLE":
        dec.thesis_state = thesis
        dec.decision = "WAIT"
        reason = tradeability.reason
        if reason and reason.startswith("VETO-"):
            dec.vetoes_triggered.append(reason)
            dec.reason_codes.append(reason.split(":")[0])
        elif reason and reason.startswith("WAIT-"):
            dec.reason_codes.append(reason.split(":")[0])
        else:
            dec.reason_codes.append("WAIT-02")
        build_decision_trace(dec, setup)
        return dec

    if tradeability.state in {"NO_SETUP", "NOT_APPLICABLE"}:
        dec.thesis_state = thesis
        if dec.thesis_state == "NEUTRAL":
            dec.decision = "NO_SETUP"
            dec.reason_codes.append("NOSETUP-01")
        else:
            dec.decision = "WAIT"
            dec.reason_codes.append("WAIT-01")
        build_decision_trace(dec, setup)
        return dec

    # G6 POSITION MAPPING
    dec.thesis_state = thesis

    if position_branch == "NO_POSITION":
        if setup.status in {"CONFIRMED", "TRIGGERED"} and tradeability.state in {"TRADEABLE", "TRADEABLE_WITH_WARNING"} and evidence_contract_met:
            if setup.direction == "LONG":
                dec.decision = "BUY"
                dec.decision_direction = "LONG"
            elif setup.direction == "SHORT":
                dec.decision = "SELL"
                dec.decision_direction = "SHORT"
            dec.reason_codes.append("BUY-01" if tradeability.state == "TRADEABLE" else "BUY-02")
        elif setup.status in {"CONFIRMED", "TRIGGERED"}:
            dec.decision = "WAIT"
            dec.reason_codes.append("WAIT-02")
        else:
            dec.decision = "WAIT"
            dec.reason_codes.append("WAIT-01")

    elif position_branch == "EXISTING_POSITION":
        # held_position_direction tells us which position the user currently holds.
        if setup.status == "INVALIDATED":
            dec.decision = "SELL"
            dec.decision_direction = held_position_direction
            dec.reason_codes.append("SELL-01")
        elif setup.status == "FAILED":
            if held_position_direction != setup.direction and thesis != "NEUTRAL":
                # Failed setup with opposing outcome vs held position
                dec.decision = "SELL"
                dec.decision_direction = held_position_direction
                dec.reason_codes.append("SELL-03")
            else:
                # Setup failed but thesis still supports held position
                dec.decision = "HOLD"
                dec.decision_direction = held_position_direction
                dec.reason_codes.append("HOLD-03")
        elif tradeability.state in {"TRADEABLE", "TRADEABLE_WITH_WARNING"} and setup.direction != held_position_direction:
            # Confirmed opposing setup vs held position
            dec.decision = "SELL"
            dec.decision_direction = held_position_direction
            dec.reason_codes.append("SELL-02")
        elif dec.thesis_state == "NEUTRAL":
            dec.decision = "HOLD"
            dec.decision_direction = held_position_direction
            dec.reason_codes.append("HOLD-02")
        else:
            # Thesis intact; check warnings for HOLD-01 vs HOLD-02
            warnings = check_warnings(indicators, setup, tradeability, evidence_state)
            dec.decision = "HOLD"
            dec.decision_direction = held_position_direction
            dec.reason_codes.append("HOLD-02" if warnings else "HOLD-01")

    else:  # UNKNOWN
        dec.decision = "WAIT"
        dec.reason_codes.append("WAIT-01")

    # Fill trade plan numbers
    if tradeability.plan:
        dec.entry = tradeability.plan.entry
        dec.sl = tradeability.plan.sl
        dec.tp1 = tradeability.plan.tp1
        dec.tp2 = tradeability.plan.tp2
        dec.rr_raw = tradeability.plan.rr_raw

    dec.warnings = check_warnings(indicators, setup, tradeability, evidence_state)

    build_decision_trace(dec, setup)
    return dec


def build_decision_trace(dec: Decision, setup: Setup):
    """Build the decision trace from current decision state."""
    dec.trace = {
        "thesis_state": dec.thesis_state,
        "primary_setup": {"type": setup.type, "direction": setup.direction, "status": setup.status},
        "evidence_state": dec.evidence_state,
        "confluence_state": dec.confluence_state,
        "tradeability_state": dec.tradeability_state,
        "warnings": dec.warnings,
        "vetoes_triggered": dec.vetoes_triggered,
        "reason_codes": dec.reason_codes,
        "trade_plan": {
            "entry": dec.entry,
            "sl": dec.sl,
            "tp1": dec.tp1,
            "tp2": dec.tp2,
            "rr_raw": dec.rr_raw,
        },
    }


def combine_unknown_branch(no_position_dec: Decision, existing_dec: Decision) -> Decision:
    """
    UNKNOWN position dual-branch rule.
    If branches agree -> use that state.
    If differ -> WAIT with dual-branch detail.
    """
    if no_position_dec.decision == existing_dec.decision:
        return no_position_dec

    # Base combined decision on no_position branch for consistent metadata
    d = Decision()
    d.thesis_state = no_position_dec.thesis_state
    d.primary_setup = no_position_dec.primary_setup
    d.evidence_state = no_position_dec.evidence_state
    d.confluence_state = no_position_dec.confluence_state
    d.tradeability_state = no_position_dec.tradeability_state
    d.warnings = list(no_position_dec.warnings)
    d.vetoes_triggered = list(no_position_dec.vetoes_triggered)
    d.entry = no_position_dec.entry
    d.sl = no_position_dec.sl
    d.tp1 = no_position_dec.tp1
    d.tp2 = no_position_dec.tp2
    d.rr_raw = no_position_dec.rr_raw
    d.position_branch = "UNKNOWN"

    # If NO_POSITION says BUY and EXISTING says HOLD -> WAIT
    if no_position_dec.decision == "BUY" and existing_dec.decision == "HOLD":
        d.decision = "WAIT"
        d.decision_direction = no_position_dec.decision_direction
        d.reason_codes = list(no_position_dec.reason_codes) + list(existing_dec.reason_codes)

    # If NO_POSITION says WAIT and EXISTING says HOLD -> WAIT
    elif no_position_dec.decision == "WAIT" and existing_dec.decision == "HOLD":
        d.decision = "WAIT"
        d.decision_direction = no_position_dec.decision_direction
        d.reason_codes = list(no_position_dec.reason_codes) + list(existing_dec.reason_codes)

    # If NO_POSITION says NO_SETUP and EXISTING says HOLD -> NO_SETUP + detail
    elif no_position_dec.decision == "NO_SETUP" and existing_dec.decision == "HOLD":
        d.decision = "NO_SETUP"
        d.decision_direction = "NONE"
        d.reason_codes = list(no_position_dec.reason_codes) + list(existing_dec.reason_codes)

    # If EXISTING says SELL -> SELL
    elif existing_dec.decision == "SELL":
        d.decision = "SELL"
        d.decision_direction = existing_dec.decision_direction
        d.reason_codes = list(existing_dec.reason_codes)

    # Default WAIT
    else:
        d.decision = "WAIT"
        d.decision_direction = no_position_dec.decision_direction
        d.reason_codes = list(no_position_dec.reason_codes) + list(existing_dec.reason_codes)

    d.dual_branch = {
        "no_position": no_position_dec.decision,
        "existing_position": existing_dec.decision,
    }
    d.trace = {
        "no_position": no_position_dec.trace,
        "existing_position": existing_dec.trace,
    }
    return d
