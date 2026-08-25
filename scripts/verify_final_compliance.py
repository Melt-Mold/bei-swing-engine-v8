#!/usr/bin/env python
"""
Compliance verifier for BEI Swing Engine v8.0.

Validates engine output and/or generated reports against the contracts in
BEI_Swing_Engine_v8.0_FINAL.md:
- 42-row indicator table (6 columns, exactly 16 badges)
- Valid decision / tradeability / setup states
- Valid reason codes
- R/R >= 1.5 for tradeable entries
- Locked parameters unchanged
- Disclaimer present in Mode A reports

Usage:
    python scripts/verify_final_compliance.py --data data-csv-yfinance-cleaned/TLKM.JK_cleaned.csv
    python scripts/verify_final_compliance.py --report output/BEI_Swing_Engine_Report.md
    python scripts/verify_final_compliance.py --locked
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add repository root to import path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bei_swing_engine_v8 import engine
from bei_swing_engine_v8.data import load_ohlcv, validate_data, extract_ticker_from_path
from bei_swing_engine_v8.indicators import compute_all_indicators
from bei_swing_engine_v8.structure import analyze_structure, SWING_FRACTAL_N
from bei_swing_engine_v8.setup import detect_setups, select_primary_setup, apply_sma200_sufficiency_cap, THRESHOLDS
from bei_swing_engine_v8.risk import assess_tradeability
from bei_swing_engine_v8.decision import run_decision_engine
from bei_swing_engine_v8.output import build_indicator_table, render_markdown
from bei_swing_engine_v8.market_context import analyze_market_regime


# ---------------------------------------------------------------------------
# Contract constants from FINAL.md
# ---------------------------------------------------------------------------
VALID_DECISIONS = {"BUY", "HOLD", "SELL", "WAIT", "NO_SETUP", "INSUFFICIENT_DATA"}
VALID_SETUP_STATUSES = {"NONE", "DEVELOPING", "CONFIRMED", "TRIGGERED", "FAILED", "INVALIDATED"}
VALID_TRADEABILITY_STATES = {"TRADEABLE", "TRADEABLE_WITH_WARNING", "UNTRADEABLE", "NOT_APPLICABLE", "NO_SETUP"}
VALID_REASON_CODES = {
    "INS-D-01", "INS-D-02",
    "VETO-01", "VETO-02", "VETO-03", "VETO-04", "VETO-05",
    "BUY-01", "BUY-02", "BUY-03",
    "WAIT-01", "WAIT-02", "WAIT-03", "WAIT-04", "WAIT-05",
    "NOSETUP-01", "NOSETUP-02",
    "HOLD-01", "HOLD-02", "HOLD-03",
    "SELL-01", "SELL-02", "SELL-03", "SELL-04",
}
BADGE_SYMBOLS = {"✓", "✗", "○", "⚡"}
EXPECTED_INDICATOR_COLUMNS = ["Category", "Indicator", "Value", "Signal", "Interpretation", "Standard / Reference"]
MIN_RR = 1.5


class ComplianceIssue:
    """Single compliance violation."""

    def __init__(self, category: str, message: str, detail: str = ""):
        self.category = category
        self.message = message
        self.detail = detail

    def __str__(self) -> str:
        s = f"[{self.category}] {self.message}"
        if self.detail:
            s += f" | {self.detail}"
        return s


class ComplianceReport:
    """Collection of compliance check results."""

    def __init__(self):
        self.issues: List[ComplianceIssue] = []
        self.checks_run = 0

    def add(self, category: str, message: str, detail: str = "") -> None:
        self.issues.append(ComplianceIssue(category, message, detail))

    def ok(self) -> bool:
        return len(self.issues) == 0

    def summary(self) -> str:
        lines = [
            f"Checks run: {self.checks_run}",
            f"Issues found: {len(self.issues)}",
        ]
        if self.issues:
            lines.append("")
            for issue in self.issues:
                lines.append(f"  - {issue}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Locked parameter checks
# ---------------------------------------------------------------------------
def check_locked_parameters(report: ComplianceReport) -> None:
    """Verify locked parameters match FINAL.md section 5."""
    report.checks_run += 1
    if SWING_FRACTAL_N != 8:
        report.add("LOCKED", f"SWING_FRACTAL_N must be 8, got {SWING_FRACTAL_N}")

    report.checks_run += 1
    if THRESHOLDS.get("rvol_breakout") != 1.25:
        report.add("LOCKED", f"rvol_breakout must be 1.25, got {THRESHOLDS.get('rvol_breakout')}")

    report.checks_run += 1
    if THRESHOLDS.get("pullback_tolerance") != 0.5:
        report.add("LOCKED", f"pullback_tolerance must be 0.5, got {THRESHOLDS.get('pullback_tolerance')}")

    report.checks_run += 1
    if THRESHOLDS.get("range_tolerance") != 0.75:
        report.add("LOCKED", f"range_tolerance must be 0.75, got {THRESHOLDS.get('range_tolerance')}")

    report.checks_run += 1
    if THRESHOLDS.get("continuation_height") != 1.5:
        report.add("LOCKED", f"continuation_height must be 1.5, got {THRESHOLDS.get('continuation_height')}")


# ---------------------------------------------------------------------------
# Indicator table checks
# ---------------------------------------------------------------------------
def check_indicator_table(report: ComplianceReport, rows: List[Dict]) -> None:
    """Verify 42-row indicator contract."""
    report.checks_run += 1
    if len(rows) != 42:
        report.add("42-ROW", f"Indicator table must have 42 rows, got {len(rows)}")

    report.checks_run += 1
    badge_count = sum(1 for r in rows if r.get("Signal") and r.get("Signal").strip() in BADGE_SYMBOLS)
    # Divergence row uses '⚡ Div' which contains a badge symbol
    badge_count = sum(
        1 for r in rows
        if r.get("Signal") and any(sym in r.get("Signal", "") for sym in BADGE_SYMBOLS)
    )
    if badge_count != 16:
        report.add("42-ROW", f"Exactly 16 confluence badges required, found {badge_count}")

    report.checks_run += 1
    missing_cols = [c for c in EXPECTED_INDICATOR_COLUMNS if c not in (rows[0].keys() if rows else [])]
    if missing_cols:
        report.add("42-ROW", f"Missing indicator table columns: {missing_cols}")


# ---------------------------------------------------------------------------
# Decision / tradeability checks
# ---------------------------------------------------------------------------
def check_decision_object(report: ComplianceReport, decision) -> None:
    """Verify Decision dataclass against contract."""
    report.checks_run += 1
    if decision.decision not in VALID_DECISIONS:
        report.add("DECISION", f"Invalid decision state: {decision.decision}")

    report.checks_run += 1
    setup_status = decision.primary_setup.status if decision.primary_setup else "NONE"
    if setup_status not in VALID_SETUP_STATUSES:
        report.add("DECISION", f"Invalid setup status: {setup_status}")

    report.checks_run += 1
    if decision.tradeability_state not in VALID_TRADEABILITY_STATES:
        report.add("DECISION", f"Invalid tradeability state: {decision.tradeability_state}")

    report.checks_run += 1
    invalid_codes = [c for c in decision.reason_codes if c not in VALID_REASON_CODES]
    if invalid_codes:
        report.add("DECISION", f"Invalid reason codes: {invalid_codes}")

    report.checks_run += 1
    if decision.decision in {"BUY", "SELL"} and decision.rr_raw is not None and decision.rr_raw < MIN_RR:
        report.add(
            "R/R",
            f"Tradeable entry R/R {decision.rr_raw:.2f} below minimum {MIN_RR}",
            f"decision={decision.decision}",
        )

    report.checks_run += 1
    if decision.decision in {"BUY", "SELL"} and not decision.reason_codes:
        report.add("DECISION", f"Active decision {decision.decision} has no reason code")


# ---------------------------------------------------------------------------
# Report (markdown) checks
# ---------------------------------------------------------------------------
def parse_indicator_table_from_markdown(text: str) -> List[Dict]:
    """Extract the 42-row indicator table from a markdown report."""
    rows: List[Dict] = []
    lines = text.splitlines()
    in_table = False
    header: List[str] = []
    for line in lines:
        if not in_table:
            if line.startswith("| Category | Indicator |"):
                header = [c.strip() for c in line.split("|") if c.strip()]
                in_table = True
            continue
        if line.startswith("|---|"):
            continue
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.split("|")][1:-1]
        if len(cells) == len(header):
            rows.append(dict(zip(header, cells)))
    return rows


def check_markdown_report(report: ComplianceReport, text: str, mode: str = "A") -> None:
    """Verify a generated markdown report."""
    rows = parse_indicator_table_from_markdown(text)
    check_indicator_table(report, rows)

    report.checks_run += 1
    if mode == "A":
        if "## 1. Executive Summary" not in text:
            report.add("REPORT", "Mode A report missing Executive Summary")
        if "## 2. Market Context" not in text:
            report.add("REPORT", "Mode A report missing Market Context section")
        if "## 4. Technical Indicators" not in text:
            report.add("REPORT", "Mode A report missing Technical Indicators section")

        report.checks_run += 1
        if "DISCLAIMER" not in text.upper() and "edukatif" not in text.lower():
            report.add("REPORT", "Mode A report missing disclaimer")

    report.checks_run += 1
    if "Keputusan:" not in text and "Decision:" not in text:
        report.add("REPORT", "Report missing decision statement")


# ---------------------------------------------------------------------------
# End-to-end engine compliance check
# ---------------------------------------------------------------------------
def check_engine_on_csv(report: ComplianceReport, csv_path: str, ihsg_path: Optional[str] = None) -> None:
    """Run the engine on a CSV and verify the result."""
    ticker = extract_ticker_from_path(csv_path)
    df = load_ohlcv(csv_path)
    validation = validate_data(df)
    if validation.get("status") == "ERROR":
        report.add("DATA", f"Data validation failed for {ticker}: {validation.get('reasons')}")
        return

    indicators = compute_all_indicators(df)
    structure = analyze_structure(df, indicators)
    setups = detect_setups(df, structure, indicators)
    setups = apply_sma200_sufficiency_cap(setups, len(df))
    primary_setup = select_primary_setup(setups)

    params = engine.parse_params(
        "MODE=A\nHORIZON=SWING\nDIRECTION=BOTH\nPOSITION=NO_POSITION\nMODAL=10000000\nRISK=2\nOUTPUT=Chat\nIHSG=None"
    )

    ihsg_df = None
    if ihsg_path:
        ihsg_df = load_ohlcv(ihsg_path)
    market_regime = analyze_market_regime(ihsg_df)

    tradeability = assess_tradeability(
        df=df,
        setup=primary_setup,
        structure=structure,
        indicators=indicators,
        modal=params["MODAL"],
        risk_pct=params["RISK"],
        warnings=[],
    )

    decision = run_decision_engine(
        df=df,
        indicators=indicators,
        structure=structure,
        setup=primary_setup,
        tradeability=tradeability,
        params=params,
        position_branch="NO_POSITION",
    )

    check_decision_object(report, decision)

    # Also verify rendered markdown
    try:
        md = render_markdown(ticker, df, indicators, structure, primary_setup, tradeability, decision, market_regime, params)
        check_markdown_report(report, md, mode="A")
    except Exception as e:
        report.add("RENDER", f"Markdown rendering failed: {e}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify BEI Swing Engine v8.0 FINAL.md compliance")
    parser.add_argument("--data", help="Path to cleaned OHLCV CSV to analyze")
    parser.add_argument("--ihsg", help="Optional IHSG/JKSE cleaned CSV")
    parser.add_argument("--report", help="Path to existing markdown report to validate")
    parser.add_argument("--locked", action="store_true", help="Only run locked-parameter checks")
    parser.add_argument("--quiet", action="store_true", help="Print only issues and summary")

    args = parser.parse_args(argv)

    report = ComplianceReport()

    if args.locked:
        check_locked_parameters(report)
    elif args.report:
        text = Path(args.report).read_text(encoding="utf-8")
        check_markdown_report(report, text)
        check_locked_parameters(report)
    elif args.data:
        check_engine_on_csv(report, args.data, args.ihsg)
        check_locked_parameters(report)
    else:
        check_locked_parameters(report)

    if not args.quiet:
        print(report.summary())
    else:
        for issue in report.issues:
            print(issue)
        print(f"Issues: {len(report.issues)}")

    return 0 if report.ok() else 1


if __name__ == "__main__":
    sys.exit(main())
