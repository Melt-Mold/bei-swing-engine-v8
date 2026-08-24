"""
Risk & tradeability engine (Module 09).
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List

import pandas as pd
import numpy as np

from .setup import Setup
from .structure import Structure, structural_targets


@dataclass
class TradePlan:
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    rr_raw: Optional[float] = None
    rr_status: str = "N/A"
    position_sizing: Dict = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class Tradeability:
    state: str = "NOT_APPLICABLE"
    plan: TradePlan = field(default_factory=TradePlan)
    warnings: List[str] = field(default_factory=list)
    reason: str = ""


def compute_sl(
    entry: float,
    direction: str,
    setup: Setup,
    structure: Structure,
    atr14: float,
) -> Optional[float]:
    """
    Stop loss priority:
    1. Structural invalidation level.
    2. Valid S/R level (S1 for LONG, R1 for SHORT).
    3. ATR fallback = Entry ± 2.0×ATR14.
    """
    # 1. Structural invalidation
    if setup.invalidation_price is not None:
        invalidation = setup.invalidation_price
        if direction == "LONG" and invalidation < entry:
            return invalidation
        if direction == "SHORT" and invalidation > entry:
            return invalidation

    # 2. S/R level
    if direction == "LONG":
        # nearest support below entry
        supports = sorted(structure.support_levels, key=lambda x: abs(x["price"] - entry))
        for s in supports:
            if s["price"] < entry:
                return s["price"]
    else:
        resistances = sorted(structure.resistance_levels, key=lambda x: abs(x["price"] - entry))
        for r in resistances:
            if r["price"] > entry:
                return r["price"]

    # 3. ATR fallback
    if direction == "LONG":
        return entry - 2.0 * atr14
    else:
        return entry + 2.0 * atr14


def compute_trade_plan(
    df: pd.DataFrame,
    setup: Setup,
    structure: Structure,
    indicators: Dict,
    modal: float,
    risk_pct: float,
) -> TradePlan:
    """Compute full trade plan: entry, SL, TP1, TP2, R/R, position sizing."""
    plan = TradePlan()
    close = df["Close"].iloc[-1]
    atr14 = indicators["atr14"].iloc[-1]
    if pd.isna(atr14):
        plan.warnings.append("ATR unavailable; cannot compute trade plan.")
        return plan

    direction = setup.direction

    # Entry
    trigger = setup.trigger_price
    if trigger is not None:
        distance = abs(close - trigger)
        if distance <= 0.5 * atr14:
            plan.entry = close
        elif distance <= 1.5 * atr14:
            plan.entry = close
            plan.warnings.append(f"Entry displaced {distance/atr14:.1f}x ATR from trigger")
        else:
            plan.entry = None
            plan.warnings.append(f"Entry displaced >1.5x ATR from trigger; untradeable")
            return plan
    else:
        # No explicit trigger, use current close if setup allows
        if setup.status in {"CONFIRMED", "TRIGGERED"}:
            plan.entry = close
        else:
            plan.entry = None
            plan.warnings.append("No trigger price and setup not confirmed")
            return plan

    # SL
    plan.sl = compute_sl(plan.entry, direction, setup, structure, atr14)
    if plan.sl is None:
        plan.warnings.append("No defensible SL found")
        return plan

    if direction == "LONG" and plan.sl >= plan.entry:
        plan.warnings.append("SL not below entry for LONG")
        return plan
    if direction == "SHORT" and plan.sl <= plan.entry:
        plan.warnings.append("SL not above entry for SHORT")
        return plan

    # TP1 / TP2
    plan.tp1, plan.tp2 = structural_targets(structure, plan.entry, direction)

    if plan.tp1 is None:
        plan.warnings.append("No defensible target on correct side of entry")
        return plan

    # Validate TP1 >= risk distance
    risk_distance = abs(plan.entry - plan.sl)
    reward_distance = abs(plan.tp1 - plan.entry)
    if reward_distance < risk_distance:
        # Try TP2 as TP1 if it satisfies
        if plan.tp2 is not None and abs(plan.tp2 - plan.entry) >= risk_distance:
            plan.tp1 = plan.tp2
            plan.tp2 = None
        else:
            plan.warnings.append("TP1 reward less than risk distance")
            return plan

    # R/R
    if direction == "LONG":
        plan.rr_raw = (plan.tp1 - plan.entry) / (plan.entry - plan.sl) if (plan.entry - plan.sl) != 0 else None
    else:
        plan.rr_raw = (plan.entry - plan.tp1) / (plan.sl - plan.entry) if (plan.sl - plan.entry) != 0 else None

    if plan.rr_raw is not None and plan.rr_raw >= 1.5:
        plan.rr_status = "VALID"
    elif plan.rr_raw is not None:
        plan.rr_status = "UNFAVORABLE"
    else:
        plan.rr_status = "N/A"

    # Position sizing
    risk_budget = modal * (risk_pct / 100.0)
    risk_per_share = abs(plan.entry - plan.sl)
    if risk_per_share > 0:
        raw_shares = risk_budget / risk_per_share
        lots = int(np.floor(raw_shares / 100))
        final_shares = lots * 100
        actual_risk = final_shares * risk_per_share
        actual_risk_pct = actual_risk / modal if modal > 0 else 0.0
    else:
        raw_shares = 0
        lots = 0
        final_shares = 0
        actual_risk = 0
        actual_risk_pct = 0.0

    plan.position_sizing = {
        "modal": modal,
        "risk_pct": risk_pct / 100.0,
        "risk_budget": risk_budget,
        "risk_per_share": risk_per_share,
        "raw_shares": raw_shares,
        "lots": lots,
        "final_shares": final_shares,
        "actual_risk": actual_risk,
        "actual_risk_pct": actual_risk_pct,
    }

    if lots == 0:
        plan.warnings.append("Modal insufficient for 1 lot")

    return plan


def assess_tradeability(
    df: pd.DataFrame,
    setup: Setup,
    structure: Structure,
    indicators: Dict,
    modal: float,
    risk_pct: float,
    warnings: List[str],
) -> Tradeability:
    """Assess tradeability state and produce trade plan."""
    result = Tradeability()

    if setup.status == "NONE":
        result.state = "NO_SETUP"
        result.reason = "No actionable setup"
        return result

    if setup.status in {"DEVELOPING", "CONFIRMED"}:
        # Not yet triggered, still not actionable
        result.state = "NO_SETUP" if setup.status == "NONE" else "NOT_APPLICABLE"
        result.reason = f"Setup {setup.status}; not yet triggered"
        return result

    if setup.status != "TRIGGERED":
        result.state = "NOT_APPLICABLE"
        result.reason = f"Setup status {setup.status}"
        return result

    plan = compute_trade_plan(df, setup, structure, indicators, modal, risk_pct)
    result.plan = plan
    result.warnings = list(plan.warnings)
    result.warnings.extend(warnings)

    if plan.entry is None:
        result.state = "UNTRADEABLE"
        result.reason = "VETO-03: No defensible entry / entry displaced"
        return result

    if plan.sl is None:
        result.state = "UNTRADEABLE"
        result.reason = "VETO-03: No defensible SL"
        return result

    if plan.tp1 is None or plan.rr_status == "N/A":
        result.state = "UNTRADEABLE"
        result.reason = "VETO-03: No defensible target"
        return result

    if plan.rr_status == "UNFAVORABLE":
        result.state = "UNTRADEABLE"
        result.reason = "WAIT-02: R/R < 1.5"
        return result

    # Valid plan, R/R >= 1.5
    if result.warnings:
        result.state = "TRADEABLE_WITH_WARNING"
        result.reason = "BUY-02: Tradeable with warnings"
    else:
        result.state = "TRADEABLE"
        result.reason = "BUY-01: Standard tradeable entry"

    return result
