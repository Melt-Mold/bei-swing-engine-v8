"""Tests for the FINAL.md compliance checker."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from verify_final_compliance import (
    ComplianceReport,
    check_decision_object,
    check_indicator_table,
    check_locked_parameters,
    check_markdown_report,
    parse_indicator_table_from_markdown,
    MIN_RR,
    VALID_REASON_CODES,
)
from bei_swing_engine_v8.setup import Setup
from bei_swing_engine_v8.decision import Decision


class TestComplianceLockedParameters:
    def test_locked_parameters_pass(self):
        report = ComplianceReport()
        check_locked_parameters(report)
        assert report.ok(), report.summary()


class TestComplianceIndicatorTable:
    def test_valid_42_row_table(self):
        rows = [
            {"Category": "TREND", "Indicator": "MA Alignment", "Value": "Mixed", "Signal": "", "Interpretation": "Mixed", "Standard / Reference": "..."},
            {"Category": "TREND", "Indicator": "Trend Classification", "Value": "Uptrend", "Signal": "✓", "Interpretation": "Uptrend", "Standard / Reference": "..."},
            {"Category": "TREND", "Indicator": "EMA9", "Value": "100", "Signal": "✓", "Interpretation": "Above", "Standard / Reference": "..."},
            {"Category": "TREND", "Indicator": "SMA20", "Value": "95", "Signal": "✓", "Interpretation": "Above", "Standard / Reference": "..."},
            {"Category": "TREND", "Indicator": "SMA50", "Value": "90", "Signal": "✓", "Interpretation": "Above", "Standard / Reference": "..."},
            {"Category": "TREND", "Indicator": "SMA200", "Value": "80", "Signal": "✓", "Interpretation": "Above", "Standard / Reference": "..."},
            {"Category": "MOMENTUM", "Indicator": "RSI(14)", "Value": "55", "Signal": "✓", "Interpretation": "Bullish", "Standard / Reference": "..."},
            {"Category": "MOMENTUM", "Indicator": "MACD", "Value": "1", "Signal": "✓", "Interpretation": "Bullish", "Standard / Reference": "..."},
            {"Category": "MOMENTUM", "Indicator": "ROC(20)", "Value": "6%", "Signal": "✓", "Interpretation": "Bullish", "Standard / Reference": "..."},
            {"Category": "VOLUME", "Indicator": "Volume vs MA20", "Value": "1.1", "Signal": "✓", "Interpretation": "High", "Standard / Reference": "..."},
            {"Category": "VOLUME", "Indicator": "OBV 20-bar chg", "Value": "Rising", "Signal": "✓", "Interpretation": "Rising", "Standard / Reference": "..."},
            {"Category": "VOLUME", "Indicator": "CMF(20)", "Value": "0.12", "Signal": "✓", "Interpretation": "Accumulation", "Standard / Reference": "..."},
            {"Category": "VOLUME", "Indicator": "Volume Synthesis", "Value": "Accumulation", "Signal": "✓", "Interpretation": "Accumulation", "Standard / Reference": "..."},
            {"Category": "TREND", "Indicator": "Weinstein Stage", "Value": "Stage 2", "Signal": "✓", "Interpretation": "Stage 2", "Standard / Reference": "..."},
            {"Category": "TREND", "Indicator": "Multi-TF Monthly", "Value": "Up", "Signal": "✓", "Interpretation": "Up", "Standard / Reference": "..."},
            {"Category": "VOLATILITY", "Indicator": "ATR%", "Value": "2%", "Signal": "○", "Interpretation": "Normal", "Standard / Reference": "..."},
            {"Category": "VOLATILITY", "Indicator": "BB Mid(20,2σ)", "Value": "95", "Signal": "○", "Interpretation": "Middle", "Standard / Reference": "..."},
        ]
        # Need 42 rows, but we only test badge count logic with valid 16 badges.
        # Pad with non-badged rows.
        while len(rows) < 42:
            rows.append({
                "Category": "OTHER",
                "Indicator": f"Pad{len(rows)}",
                "Value": "0",
                "Signal": "",
                "Interpretation": "Pad",
                "Standard / Reference": "...",
            })
        report = ComplianceReport()
        check_indicator_table(report, rows)
        assert report.ok(), report.summary()

    def test_wrong_row_count(self):
        rows = [{"Category": "TREND", "Indicator": "X", "Value": "0", "Signal": "", "Interpretation": "X", "Standard / Reference": "..."}]
        report = ComplianceReport()
        check_indicator_table(report, rows)
        assert not report.ok()
        assert "42 rows" in str(report.issues[0])

    def test_wrong_badge_count(self):
        rows = [
            {"Category": "TREND", "Indicator": "Trend Classification", "Value": "Uptrend", "Signal": "✓", "Interpretation": "Uptrend", "Standard / Reference": "..."},
            {"Category": "TREND", "Indicator": "EMA9", "Value": "100", "Signal": "✓", "Interpretation": "Above", "Standard / Reference": "..."},
        ]
        while len(rows) < 42:
            rows.append({
                "Category": "OTHER",
                "Indicator": f"Pad{len(rows)}",
                "Value": "0",
                "Signal": "",
                "Interpretation": "Pad",
                "Standard / Reference": "...",
            })
        report = ComplianceReport()
        check_indicator_table(report, rows)
        assert not report.ok()
        assert "16 confluence badges" in str(report.issues[0])


class TestComplianceDecision:
    def test_valid_tradeable_decision(self):
        dec = Decision(
            decision="BUY",
            decision_direction="LONG",
            thesis_state="BULLISH",
            primary_setup=Setup(type="Breakout", direction="LONG", status="TRIGGERED"),
            evidence_state="Strong",
            confluence_state="Strong",
            tradeability_state="TRADEABLE",
            reason_codes=["BUY-01"],
            rr_raw=2.0,
        )
        report = ComplianceReport()
        check_decision_object(report, dec)
        assert report.ok(), report.summary()

    def test_invalid_reason_code(self):
        dec = Decision(
            decision="BUY",
            primary_setup=Setup(type="Breakout", direction="LONG", status="TRIGGERED"),
            tradeability_state="TRADEABLE",
            reason_codes=["INVALID-CODE"],
            rr_raw=2.0,
        )
        report = ComplianceReport()
        check_decision_object(report, dec)
        assert not report.ok()
        assert "Invalid reason codes" in str(report.issues[0])

    def test_rr_below_minimum_for_buy(self):
        dec = Decision(
            decision="BUY",
            primary_setup=Setup(type="Breakout", direction="LONG", status="TRIGGERED"),
            tradeability_state="TRADEABLE",
            reason_codes=["BUY-01"],
            rr_raw=1.2,
        )
        report = ComplianceReport()
        check_decision_object(report, dec)
        assert not report.ok()
        assert "below minimum" in str(report.issues[0])

    def test_active_decision_requires_reason_code(self):
        dec = Decision(
            decision="BUY",
            primary_setup=Setup(type="Breakout", direction="LONG", status="TRIGGERED"),
            tradeability_state="TRADEABLE",
            reason_codes=[],
            rr_raw=2.0,
        )
        report = ComplianceReport()
        check_decision_object(report, dec)
        assert not report.ok()
        assert "no reason code" in str(report.issues[0])


def _make_table(rows: int, with_badge_indices=None) -> str:
    lines = [
        "| Category | Indicator | Value | Signal | Interpretation | Standard / Reference |",
        "|---|---|---|---|---|---|---|",
    ]
    badge_rows = set(with_badge_indices or [])
    for i in range(rows):
        signal = "✓" if i in badge_rows else ""
        lines.append(f"| TREND | Indicator{i} | {i} | {signal} | Note{i} | Ref{i} |")
    return "\n".join(lines)


class TestComplianceMarkdown:
    def test_valid_mode_a_report(self):
        table = _make_table(42, with_badge_indices=list(range(16)))
        text = f"""# Report
## 1. Executive Summary
- **Keputusan:** `BUY`
## 2. Market Context (IHSG)
## 4. Technical Indicators
{table}
DISCLAIMER: edukatif
"""
        report = ComplianceReport()
        check_markdown_report(report, text, mode="A")
        assert report.ok(), report.summary()

    def test_missing_disclaimer(self):
        table = _make_table(42, with_badge_indices=list(range(16)))
        text = f"""# Report
## 1. Executive Summary
## 4. Technical Indicators
{table}
"""
        report = ComplianceReport()
        check_markdown_report(report, text, mode="A")
        assert not report.ok()
        messages = " ".join(str(i).lower() for i in report.issues)
        assert "disclaimer" in messages


class TestComplianceParser:
    def test_parse_indicator_table(self):
        text = """## 4. Technical Indicators
| Category | Indicator | Value | Signal | Interpretation | Standard / Reference |
|---|---|---|---|---|---|---|
| TREND | EMA9 | 100 | ✓ | Above | Close vs EMA9 |
| MOMENTUM | RSI(14) | 55 | ✓ | Bullish | >50 ✓ |
"""
        rows = parse_indicator_table_from_markdown(text)
        assert len(rows) == 2
        assert rows[0]["Indicator"] == "EMA9"
        assert rows[1]["Signal"] == "✓"
