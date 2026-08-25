"""Tests for chat AI explainer module."""
import pytest

from unittest.mock import MagicMock, patch

from bei_swing_engine_v8.chat import (
    explain_decision,
    explain_decision_with_llm,
    explain_general,
    explain_reason_codes,
    parse_user_intent,
    REASON_CODE_MEANING,
)
from bei_swing_engine_v8.decision import Decision
from bei_swing_engine_v8.setup import Setup


class TestChatExplainer:
    def test_explain_reason_codes(self):
        text = explain_reason_codes(["BUY-01", "WAIT-02"])
        assert "BUY-01" in text
        assert "WAIT-02" in text
        assert "Standard tradeable entry" in text
        assert "Untradeable economics" in text

    def test_explain_decision_buy(self):
        dec = Decision(
            decision="BUY",
            decision_direction="LONG",
            thesis_state="BULLISH",
            primary_setup=Setup(type="Breakout", direction="LONG", status="TRIGGERED"),
            evidence_state="Strong",
            confluence_state="Strong",
            tradeability_state="TRADEABLE",
            reason_codes=["BUY-01"],
            entry=1000.0,
            sl=950.0,
            tp1=1100.0,
            tp2=1200.0,
            rr_raw=2.0,
        )
        response = explain_decision(dec)
        assert "BUY" in response.summary
        assert "BULLISH" in response.summary
        assert "Breakout" in response.summary
        assert "BUY-01" in response.detail
        assert "Entry:" in response.trade_plan
        assert "Stop Loss:" in response.trade_plan
        assert "Disclaimer" in response.disclaimer
        assert response.raw_decision is dec

    def test_explain_decision_wait(self):
        dec = Decision(
            decision="WAIT",
            thesis_state="BULLISH",
            primary_setup=Setup(type="Pullback", direction="LONG", status="DEVELOPING"),
            evidence_state="Weak",
            confluence_state="Weak",
            tradeability_state="NOT_APPLICABLE",
            reason_codes=["WAIT-01"],
        )
        response = explain_decision(dec)
        assert "WAIT" in response.summary
        assert "WAIT-01" in response.detail
        assert "Tidak ada rencana perdagangan" in response.trade_plan

    def test_explain_general_reason_codes(self):
        text = explain_general("Daftar reason code")
        assert "INS-D-01" in text
        assert "BUY-01" in text
        assert "SELL-04" in text

    def test_explain_general_setup(self):
        text = explain_general("Apa saja setup yang dideteksi?")
        assert "Breakout" in text
        assert "Continuation" in text

    def test_parse_user_intent_analyze(self):
        intent = parse_user_intent("Analisis BBRI dong")
        assert intent["intent"] == "analyze"
        assert intent["ticker"] == "BBRI"

    def test_parse_user_intent_analyze_with_jk(self):
        intent = parse_user_intent("Cek TLKM.JK")
        assert intent["intent"] == "analyze"
        assert intent["ticker"] == "TLKM"

    def test_parse_user_intent_reason_codes(self):
        intent = parse_user_intent("Jelaskan reason code")
        assert intent["intent"] == "explain_reason_codes"

    def test_parse_user_intent_general(self):
        intent = parse_user_intent("Halo")
        assert intent["intent"] == "general"

    def test_reason_code_meaning_complete(self):
        # Ensure all documented reason codes have a meaning
        required = {
            "INS-D-01", "INS-D-02",
            "VETO-01", "VETO-02", "VETO-03", "VETO-04", "VETO-05",
            "BUY-01", "BUY-02", "BUY-03",
            "WAIT-01", "WAIT-02", "WAIT-03", "WAIT-04", "WAIT-05",
            "NOSETUP-01", "NOSETUP-02",
            "HOLD-01", "HOLD-02", "HOLD-03",
            "SELL-01", "SELL-02", "SELL-03", "SELL-04",
        }
        assert required.issubset(set(REASON_CODE_MEANING.keys()))


class TestChatLLM:
    def _make_decision(self):
        return Decision(
            decision="BUY",
            decision_direction="LONG",
            thesis_state="BULLISH",
            primary_setup=Setup(type="Breakout", direction="LONG", status="TRIGGERED"),
            evidence_state="Strong",
            confluence_state="Strong",
            tradeability_state="TRADEABLE",
            reason_codes=["BUY-01"],
            entry=1000.0,
            sl=950.0,
            tp1=1100.0,
            tp2=1200.0,
            rr_raw=2.0,
        )

    @patch("openai.OpenAI")
    def test_explain_decision_with_llm_success(self, mock_openai_class):
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "LLM-generated explanation in Indonesian."
        mock_client.chat.completions.create.return_value.choices = [mock_choice]
        mock_openai_class.return_value = mock_client

        dec = self._make_decision()
        response = explain_decision_with_llm(dec, api_key="fake-key", model="gpt-4o-mini")

        assert "LLM-generated explanation" in response.summary
        assert "Disclaimer" in response.disclaimer
        assert response.raw_decision is dec
        mock_client.chat.completions.create.assert_called_once()

    @patch("openai.OpenAI")
    def test_explain_decision_with_llm_fallback_on_error(self, mock_openai_class):
        mock_openai_class.side_effect = Exception("API error")

        dec = self._make_decision()
        response = explain_decision_with_llm(dec, api_key="fake-key")

        # Should fall back to deterministic template
        assert "BUY" in response.summary
        assert "API error" in response.detail
        assert "Disclaimer" in response.disclaimer
