r"""
BEI Swing Engine v8.0 — Chat AI Interface (Streamlit)

Conversational interface for the engine. The actual analysis is always performed
by the deterministic Python engine; this app only explains the result using
FINAL.md terminology.

Usage:
    .\venv\Scripts\python.exe -m streamlit run chat_app.py
"""

import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

# Add repository root to import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bei_swing_engine_v8.engine import analyze_ticker, parse_params, default_params
from bei_swing_engine_v8.data import load_ohlcv, load_ihsg
from bei_swing_engine_v8.fetcher import fetch_and_save, VALID_PERIODS
from bei_swing_engine_v8.chat import explain_decision, explain_decision_with_llm, explain_general, parse_user_intent
from bei_swing_engine_v8.logging_config import setup_logging


setup_logging(level="WARNING")

st.set_page_config(
    page_title="BEI Swing Engine v8.0 — Chat",
    page_icon="💬",
    layout="wide",
)


def get_default_params():
    """Return chat-friendly default params."""
    p = default_params()
    p["MODE"] = "A"
    p["OUTPUT"] = "Chat"
    return p


def run_analysis_for_ticker(ticker: str, ihsg_path: str = None) -> dict:
    """Fetch data and run engine analysis for a ticker."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = fetch_and_save(ticker, period="1y", interval="1d", output_dir=tmpdir)
        if result.error:
            return {"error": result.error}

        csv_path = os.path.join(tmpdir, result.output_name)
        return run_analysis_for_csv(csv_path, ihsg_path=ihsg_path)


def run_analysis_for_csv(csv_path: str, ihsg_path: str = None) -> dict:
    """Run engine analysis on a cleaned CSV file."""
    params = get_default_params()
    df = load_ohlcv(csv_path)
    ticker = df["Ticker"].iloc[-1] if "Ticker" in df.columns else Path(csv_path).stem
    ihsg_df = load_ihsg(ihsg_path) if ihsg_path else None

    try:
        result = analyze_ticker(csv_path, ticker, params, ihsg_df=ihsg_df)
        return result
    except Exception as e:
        return {"error": str(e)}


def render_chat_response(response):
    """Render a ChatResponse object in Streamlit."""
    st.markdown(response.summary)
    if response.detail:
        st.markdown(response.detail)
    if response.trade_plan:
        st.markdown(response.trade_plan)
    st.info(response.disclaimer)


def explain_with_optional_llm(decision, use_llm, api_key, model, base_url):
    """Explain decision using LLM if enabled and key provided, else template mode."""
    if use_llm and api_key:
        return explain_decision_with_llm(
            decision,
            api_key=api_key,
            model=model,
            base_url=base_url if base_url else None,
        )
    return explain_decision(decision)


def main():
    st.title("💬 BEI Swing Engine v8.0 — Chat AI")
    st.markdown(
        "Asisten analisis teknikal untuk saham Indonesia. "
        "Analisis angka dihasilkan oleh engine yang deterministik; "
        "asisten ini hanya menjelaskan hasil sesuai kontrak BEI Swing Engine v8.0."
    )

    # Sidebar: IHSG upload and settings
    with st.sidebar:
        st.header("⚙️ Pengaturan")
        ihsg_file = st.file_uploader("Upload IHSG/JKSE CSV (opsional)", type=["csv"])
        ihsg_path = None
        if ihsg_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as f:
                f.write(ihsg_file.getvalue())
                ihsg_path = f.name

        st.divider()
        st.subheader("🤖 LLM Backend (opsional)")
        use_llm = st.toggle("Gunakan LLM explanation", value=False)
        api_key = ""
        model = "gpt-4o-mini"
        base_url = ""
        if use_llm:
            api_key = st.text_input("OpenAI API Key", type="password")
            model = st.text_input("Model", value="gpt-4o-mini")
            base_url = st.text_input("Base URL (kosongkan untuk OpenAI resmi)", value="")
            if not api_key:
                st.warning("Masukkan API key untuk menggunakan LLM. Tanpa API key, mode template akan dipakai.")

        st.divider()
        st.markdown("**Perintah contoh:**")
        st.markdown("- 'Analisis BBRI'")
        st.markdown("- 'Upload CSV'")
        st.markdown("- 'Jelaskan reason code'")
        st.markdown("- 'Apa saja setup yang dideteksi?'")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Halo! Saya asisten BEI Swing Engine v8.0. "
                    "Silakan sebutkan ticker (contoh: BBRI) atau unggah CSV untuk dianalisis."
                ),
            }
        ]

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input("Ketik perintah di sini...")

    # File upload trigger (shown in chat area)
    uploaded_file = st.file_uploader("Atau upload CSV saham di sini", type=["csv"], key="chat_csv_upload")

    # Handle CSV upload
    if uploaded_file is not None and not st.session_state.get("upload_processed"):
        st.session_state.upload_processed = True
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as f:
            f.write(uploaded_file.getvalue())
            csv_path = f.name

        st.session_state.messages.append({"role": "user", "content": f"Upload CSV: {uploaded_file.name}"})
        with st.spinner("Menganalisis CSV..."):
            result = run_analysis_for_csv(csv_path, ihsg_path=ihsg_path)

        with st.chat_message("assistant"):
            if "error" in result:
                st.error(f"Gagal menganalisis: {result['error']}")
                response_text = f"Maaf, terjadi kesalahan: {result['error']}"
            else:
                decision = result.get("decision")
                if decision is None:
                    st.warning("Engine tidak mengembalikan decision.")
                    response_text = "Engine tidak mengembalikan keputusan."
                else:
                    response = explain_with_optional_llm(decision, use_llm, api_key, model, base_url)
                    render_chat_response(response)
                    response_text = f"{response.summary}\n\n{response.detail}\n\n{response.trade_plan}\n\n{response.disclaimer}"
            st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()

    # Handle text input
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        intent = parse_user_intent(user_input)

        with st.chat_message("assistant"):
            if intent["intent"] == "analyze":
                ticker = intent["ticker"]
                if not ticker:
                    st.warning("Ticker tidak dikenali. Contoh: 'Analisis BBRI'")
                    response_text = "Ticker tidak dikenali. Silakan sebutkan ticker seperti BBRI, TLKM, atau BBCA."
                else:
                    with st.spinner(f"Mengambil data dan menganalisis {ticker}..."):
                        result = run_analysis_for_ticker(ticker, ihsg_path=ihsg_path)

                    if "error" in result:
                        st.error(f"Gagal menganalisis {ticker}: {result['error']}")
                        response_text = f"Maaf, analisis {ticker} gagal: {result['error']}"
                    else:
                        decision = result.get("decision")
                        if decision is None:
                            st.warning("Engine tidak mengembalikan decision.")
                            response_text = "Engine tidak mengembalikan keputusan."
                        else:
                            response = explain_with_optional_llm(decision, use_llm, api_key, model, base_url)
                            render_chat_response(response)
                            response_text = f"{response.summary}\n\n{response.detail}\n\n{response.trade_plan}\n\n{response.disclaimer}"

            elif intent["intent"] in {"explain_reason_codes", "explain_setups", "explain_42row", "explain_locked"}:
                response_text = explain_general(user_input)
                st.markdown(response_text)

            else:
                response_text = explain_general(user_input)
                st.markdown(response_text)

            st.session_state.messages.append({"role": "assistant", "content": response_text})


if __name__ == "__main__":
    main()
