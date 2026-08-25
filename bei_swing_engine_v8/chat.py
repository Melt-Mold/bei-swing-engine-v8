"""
Chat AI explainer for BEI Swing Engine v8.0.

This module provides deterministic, template-based explanations of engine output
using FINAL.md terminology. It is designed so that an LLM can be plugged in later
as an optional backend; by default it uses rule-based templates to guarantee
anti-fabrication compliance.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from .decision import Decision
from .setup import Setup


REASON_CODE_MEANING: Dict[str, str] = {
    "INS-D-01": "Invalid or insufficient source data.",
    "INS-D-02": "Upstream insufficiency propagated to decision.",
    "VETO-01": "Invalidated setup used as decision basis.",
    "VETO-02": "Structural invalidation vs planned entry.",
    "VETO-03": "No defensible stop-loss level.",
    "VETO-04": "No actionable setup present.",
    "VETO-05": "Invalid data encountered.",
    "BUY-01": "Standard tradeable entry.",
    "BUY-02": "Tradeable entry with warnings.",
    "BUY-03": "Range-boundary entry under neutral structure.",
    "WAIT-01": "Setup developing/absent with live thesis.",
    "WAIT-02": "Untradeable economics (R/R < 1.5 or missing target).",
    "WAIT-03": "Evidence conflict across dimensions.",
    "WAIT-04": "Entry displaced from trigger zone.",
    "WAIT-05": "Minimum evidence contract unmet.",
    "NOSETUP-01": "No thesis and no setup.",
    "NOSETUP-02": "Direction not permitted by parameter.",
    "HOLD-01": "Thesis intact, no warnings.",
    "HOLD-02": "Thesis intact, with warnings.",
    "HOLD-03": "Setup failed, thesis intact.",
    "SELL-01": "Structural invalidation.",
    "SELL-02": "Confirmed opposing setup.",
    "SELL-03": "Failed setup with opposing outcome.",
    "SELL-04": "New SHORT entry justified.",
}


@dataclass
class ChatResponse:
    """Structured response from the chat explainer."""
    summary: str
    detail: str
    trade_plan: str
    disclaimer: str
    raw_decision: Optional[Decision] = None


def fmt_price(value: Optional[float]) -> str:
    """Format price as Rupiah."""
    if value is None:
        return "N/A"
    return f"Rp {value:,.0f}".replace(",", ".")


def fmt_pct(value: Optional[float]) -> str:
    """Format percentage."""
    if value is None:
        return "N/A"
    return f"{value:.2f}%"


def explain_reason_codes(codes: List[str]) -> str:
    """Translate reason codes to human-readable bullet list."""
    if not codes:
        return "- Tidak ada reason code."
    lines = []
    for code in codes:
        meaning = REASON_CODE_MEANING.get(code, "Unknown reason code.")
        lines.append(f"- **{code}**: {meaning}")
    return "\n".join(lines)


def explain_decision(decision: Decision) -> ChatResponse:
    """
    Generate a ChatResponse explaining a Decision object.
    This is the core deterministic explainer (template mode).
    """
    setup = decision.primary_setup
    setup_text = f"{setup.type} ({setup.direction}) — {setup.status}" if setup else "No setup"

    # Executive summary
    summary_lines = [
        f"**Keputusan:** `{decision.decision}` {decision.decision_direction}",
        f"**Thesis:** {decision.thesis_state}",
        f"**Setup utama:** {setup_text}",
        f"**Evidence:** {decision.evidence_state} | **Confluence:** {decision.confluence_state}",
        f"**Tradeability:** {decision.tradeability_state}",
    ]
    summary = "\n".join(summary_lines)

    # Detail / reasoning
    detail_lines = [
        "### Alasan Keputusan",
        explain_reason_codes(decision.reason_codes),
    ]
    if decision.warnings:
        detail_lines.append("\n### Peringatan")
        for w in decision.warnings:
            detail_lines.append(f"- {w}")
    if decision.vetoes_triggered:
        detail_lines.append("\n### Vetoes")
        for v in decision.vetoes_triggered:
            detail_lines.append(f"- {v}")
    detail = "\n".join(detail_lines)

    # Trade plan
    if decision.entry is not None:
        rr_text = f"{decision.rr_raw:.2f}" if decision.rr_raw is not None else "N/A"
        trade_lines = [
            "### Rencana Perdagangan",
            f"- **Entry:** {fmt_price(decision.entry)}",
            f"- **Stop Loss:** {fmt_price(decision.sl)}",
            f"- **TP1:** {fmt_price(decision.tp1)}",
            f"- **TP2:** {fmt_price(decision.tp2)}",
            f"- **R/R:** {rr_text}",
        ]
        trade_plan = "\n".join(trade_lines)
    else:
        trade_plan = "### Rencana Perdagangan\nTidak ada rencana perdagangan yang dapat dibentuk untuk setup ini."

    disclaimer = (
        "**Disclaimer:** Analisis ini bersifat edukatif untuk pembelajaran analisis teknikal, "
        "BUKAN rekomendasi investasi atau ajakan untuk membeli/menjual efek. "
        "Keputusan investasi dan risiko sepenuhnya menjadi tanggung jawab pengguna."
    )

    return ChatResponse(
        summary=summary,
        detail=detail,
        trade_plan=trade_plan,
        disclaimer=disclaimer,
        raw_decision=decision,
    )


def explain_general(topic: str) -> str:
    """Answer general questions about the engine using FINAL.md terminology."""
    topic_lower = topic.lower()

    if "reason code" in topic_lower or "kode alasan" in topic_lower:
        lines = ["**Daftar Reason Codes (FINAL.md section 8.8):**"]
        for code, meaning in REASON_CODE_MEANING.items():
            lines.append(f"- `{code}`: {meaning}")
        return "\n".join(lines)

    if "setup" in topic_lower:
        return (
            "Engine mendeteksi 6 tipe setup: **Breakout, Breakout + Retest, Pullback, "
            "Reversal, Continuation, Range**. Setiap setup memiliki status lifecycle: "
            "NONE → DEVELOPING → CONFIRMED → TRIGGERED, dengan transisi FAILED atau INVALIDATED."
        )

    if "42 row" in topic_lower or "42 baris" in topic_lower:
        return (
            "Output indikator wajib memiliki **42 baris × 6 kolom**: "
            "`Category | Indicator | Value | Signal | Interpretation | Standard / Reference`. "
            "Tepat **16 confluence factors** yang memiliki badge (✓/✗/○)."
        )

    if "locked" in topic_lower or "parameter" in topic_lower:
        return (
            "Parameter yang di-lock dan tidak boleh diubah tanpa audit: "
            "Swing fractal N=8, ATR fallback multiplier=2.0, minimum R/R=1.5, "
            "S/R tolerance=max(0.5%×Close, 0.5×ATR14), S/R min touches=2, "
            "range min duration=20 bars, breakout approach tolerance=0.75×ATR14, "
            "pullback zone tolerance=0.5×ATR14."
        )

    return (
        "Saya adalah asisten BEI Swing Engine v8.0. Silakan tanyakan tentang: "
        "analisis ticker, reason code, tipe setup, kontrak 42-row, atau parameter locked. "
        "Untuk analisis, unggah CSV atau sebutkan ticker (contoh: 'Analisis BBRI')."
    )


def parse_user_intent(message: str) -> Dict[str, str]:
    """
    Simple intent parser for chat messages.
    Returns dict with 'intent' and optional 'ticker'.
    """
    msg_lower = message.lower().strip()

    if any(k in msg_lower for k in ["analisis", "analisa", "analyz", "check", "cek"]):
        # Try extract ticker like BBRI, TLKM, BBCA.JK, etc.
        # Strip common command words first to avoid matching them as tickers.
        import re
        command_words = {"ANALISIS", "ANALISA", "ANALYZE", "CHECK", "CEK", "DONG", "PLEASE", "TOLONG"}
        cleaned = " ".join(w for w in message.upper().split() if w not in command_words)
        match = re.search(r"\b([A-Z]{3,5})(?:\.JK)?\b", cleaned)
        ticker = match.group(1) if match else ""
        return {"intent": "analyze", "ticker": ticker}

    if any(k in msg_lower for k in ["reason code", "kode alasan", "alasan"]):
        return {"intent": "explain_reason_codes", "ticker": ""}

    if any(k in msg_lower for k in ["setup", "set up"]):
        return {"intent": "explain_setups", "ticker": ""}

    if any(k in msg_lower for k in ["42 row", "42 baris", "indicator contract"]):
        return {"intent": "explain_42row", "ticker": ""}

    if any(k in msg_lower for k in ["locked", "parameter", "parameter lock"]):
        return {"intent": "explain_locked", "ticker": ""}

    return {"intent": "general", "ticker": ""}


# ---------------------------------------------------------------------------
# Optional LLM backend (OpenAI-compatible)
# ---------------------------------------------------------------------------

def build_llm_system_prompt() -> str:
    """Return a concise system prompt for an LLM explainer."""
    return (
        "You are BEI Swing Engine v8.0 Assistant, an expert technical-analysis explainer "
        "for Indonesian stocks (BEI/Bursa Efek Indonesia).\n\n"
        "Rules:\n"
        "1. NEVER calculate indicators or invent numbers. Use only the provided Decision object.\n"
        "2. Use FINAL.md terminology: decision states (BUY/HOLD/SELL/WAIT/NO_SETUP/INSUFFICIENT_DATA), "
        "setup states (NONE/DEVELOPING/CONFIRMED/TRIGGERED/FAILED/INVALIDATED), reason codes (BUY-01, WAIT-03, etc.).\n"
        "3. Explain the thesis, evidence, primary setup, tradeability, reason codes, and trade plan clearly.\n"
        "4. Mention warnings and vetoes if present.\n"
        "5. Always end with the disclaimer: analysis is educational, NOT investment advice.\n"
        "6. Respond in the same language as the user's question (default Indonesian)."
    )


def decision_to_prompt_context(decision: Decision) -> Dict:
    """Serialize a Decision into a dict suitable for LLM prompt."""
    setup = decision.primary_setup
    return {
        "ticker": "",
        "decision": decision.decision,
        "direction": decision.decision_direction,
        "thesis": decision.thesis_state,
        "primary_setup": {
            "type": setup.type if setup else None,
            "direction": setup.direction if setup else None,
            "status": setup.status if setup else None,
        },
        "evidence_state": decision.evidence_state,
        "confluence_state": decision.confluence_state,
        "tradeability_state": decision.tradeability_state,
        "reason_codes": decision.reason_codes,
        "reason_code_meanings": [REASON_CODE_MEANING.get(c, "Unknown") for c in decision.reason_codes],
        "warnings": decision.warnings,
        "vetoes": decision.vetoes_triggered,
        "entry": decision.entry,
        "sl": decision.sl,
        "tp1": decision.tp1,
        "tp2": decision.tp2,
        "rr_raw": decision.rr_raw,
    }


def explain_decision_with_llm(
    decision: Decision,
    api_key: str,
    model: str = "gpt-4o-mini",
    base_url: Optional[str] = None,
) -> ChatResponse:
    """
    Generate a ChatResponse using an OpenAI-compatible LLM API.
    Falls back to deterministic template mode if the API call fails.
    """
    try:
        from openai import OpenAI
    except ImportError:
        return explain_decision(decision)

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    try:
        client = OpenAI(**client_kwargs)
        context = decision_to_prompt_context(decision)
        user_prompt = (
            "Jelaskan keputusan analisis teknikal berikut dalam bahasa Indonesia:\n\n"
            f"{context}\n\n"
            "Berikan: ringkasan eksekutif, alasan keputusan dengan reason code, "
            "peringatan/veto jika ada, rencana perdagangan, dan disclaimer edukatif."
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": build_llm_system_prompt()},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=800,
        )

        content = response.choices[0].message.content.strip()
        return ChatResponse(
            summary=content,
            detail="",
            trade_plan="",
            disclaimer=(
                "**Disclaimer:** Analisis ini bersifat edukatif untuk pembelajaran analisis teknikal, "
                "BUKAN rekomendasi investasi atau ajakan untuk membeli/menjual efek. "
                "Keputusan investasi dan risiko sepenuhnya menjadi tanggung jawab pengguna."
            ),
            raw_decision=decision,
        )
    except Exception as e:
        # Fall back to deterministic template on any LLM error
        fallback = explain_decision(decision)
        fallback.detail = f"_(LLM fallback karena {e})_\n\n{fallback.detail}"
        return fallback
