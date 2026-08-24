"""Tests for output renderers."""

import pytest

from bei_swing_engine_v8.engine import analyze_ticker, render_ticker_report
from bei_swing_engine_v8.output import (
    render_calc_only_markdown, render_screening_summary,
    build_indicator_table, render_html_single,
)
from bei_swing_engine_v8.setup import Setup


class TestOutputRenderers:
    def test_mode_a_has_42_rows(self, sample_df, default_params):
        result = analyze_ticker(sample_df, default_params)
        report = render_ticker_report(result, "Chat", mode="A")
        # Count markdown table rows for indicator table
        table_rows = [line for line in report.splitlines() if line.startswith("| TREND") or line.startswith("| MOMENTUM") or line.startswith("| VOLATILITY") or line.startswith("| VOLUME") or line.startswith("| STRUCTURE") or line.startswith("| WEEKLY")]
        assert len(table_rows) == 42

    def test_mode_a_has_disclaimer(self, sample_df, default_params):
        result = analyze_ticker(sample_df, default_params)
        report = render_ticker_report(result, "Chat", mode="A")
        assert "BUKAN rekomendasi investasi" in report

    def test_mode_b_no_decision(self, sample_df, default_params):
        result = analyze_ticker(sample_df, {**default_params, "MODE": "B"})
        report = render_ticker_report(result, "Chat", mode="B")
        assert "Executive Summary" not in report
        assert "Trading Plan" not in report
        assert "Decision Trace" not in report
        assert "Technical Indicators" in report
        assert "Setup Status" in report

    def test_mode_c_only_summary(self, sample_df, default_params):
        result = analyze_ticker(sample_df, {**default_params, "MODE": "C"})
        # render_screening_summary expects summary_data-like dict
        summary_data = [{
            "ticker": result["ticker"],
            "thesis": result["decision"].thesis_state,
            "setup": f"{result['primary_setup'].type} {result['primary_setup'].status}",
            "tradeability": result["decision"].tradeability_state,
            "decision": result["decision"].decision,
            "warnings": "",
        }]
        report = render_screening_summary(summary_data)
        assert "Screening Summary" in report
        assert result["ticker"] in report

    def test_html_contains_table(self, sample_df, default_params):
        result = analyze_ticker(sample_df, default_params)
        report = render_ticker_report(result, "HTML", mode="A")
        assert "<table>" in report
        assert "</table>" in report

    def test_indicator_table_badge_count(self, sample_df, sample_indicators):
        rows = build_indicator_table(sample_df, sample_indicators)
        badged = [r for r in rows if r["Badge"] is not None]
        assert len(badged) == 16

    def test_pdf_generation(self, sample_df, default_params):
        import io
        from bei_swing_engine_v8.output import render_pdf_single

        result = analyze_ticker(sample_df, default_params)
        report = render_ticker_report(result, "HTML", mode="A")
        pdf_bytes = io.BytesIO()
        ok = render_pdf_single(result["ticker"], report, pdf_bytes)
        assert ok
        pdf_bytes.seek(0)
        assert pdf_bytes.read(4) == b"%PDF"

    def test_logging_config(self):
        from bei_swing_engine_v8.logging_config import setup_logging, get_logger
        import logging

        logger = setup_logging(level="DEBUG")
        assert logger.level == logging.DEBUG
        child = get_logger("test")
        assert child.name == "bei_swing_engine.test"
