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

from bei_swing_engine_v8.engine import analyze_ticker, run_analysis, parse_params, default_params
from bei_swing_engine_v8.data import load_ohlcv, load_ihsg
from bei_swing_engine_v8.fetcher import fetch_and_save, VALID_PERIODS
from bei_swing_engine_v8.chat import explain_decision, explain_decision_with_llm, explain_general, explain_screening_summary, parse_user_intent
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


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data-csv-yfinance-cleaned")


def find_or_fetch_csv(ticker: str, tmpdir: str) -> str:
    """Find existing cleaned CSV for ticker, or fetch from Yahoo Finance."""
    candidates = [
        os.path.join(DATA_DIR, f"{ticker}.JK_cleaned.csv"),
        os.path.join(DATA_DIR, f"{ticker}_cleaned.csv"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # Fetch from Yahoo
    result = fetch_and_save(ticker, period="1y", interval="1d", output_dir=tmpdir)
    if result.error:
        return ""
    return os.path.join(tmpdir, result.output_name)


def run_screening(tickers: list, ihsg_path: str = None) -> dict:
    """Run multi-ticker screening and return summary_data list."""
    if not tickers:
        return {"error": "No tickers provided for screening."}

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        data_paths = []
        failed = []
        for t in tickers:
            path = find_or_fetch_csv(t, tmpdir)
            if path:
                data_paths.append(path)
            else:
                failed.append(t)

        if not data_paths:
            return {"error": f"Could not load data for any ticker: {failed}"}

        ihsg_path_to_use = ihsg_path
        if not ihsg_path_to_use:
            default_ihsg = os.path.join(DATA_DIR, "IHSG-JKSE_cleaned.csv")
            if os.path.exists(default_ihsg):
                ihsg_path_to_use = default_ihsg

        params_text = "MODE=C\nHORIZON=SWING\nDIRECTION=BOTH\nPOSITION=NO_POSITION\nMODAL=10000000\nRISK=2\nOUTPUT=Chat\nIHSG=None"
        try:
            markdown_output = run_analysis(data_paths, params_text=params_text, ihsg_path=ihsg_path_to_use)
            return {"markdown": markdown_output, "failed": failed}
        except Exception as e:
            return {"error": str(e)}


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
            if intent["intent"] == "screen":
                tickers = intent.get("tickers", [])
                if not tickers:
                    st.warning("Ticker tidak dikenali. Contoh: 'Screening BBRI TLKM BBCA'")
                    response_text = "Ticker tidak dikenali. Silakan sebutkan ticker seperti 'Screening BBRI TLKM BBCA'."
                else:
                    with st.spinner(f"Screening {len(tickers)} ticker..."):
                        result = run_screening(tickers, ihsg_path=ihsg_path)

                    if "error" in result:
                        st.error(f"Gagal screening: {result['error']}")
                        response_text = f"Maaf, screening gagal: {result['error']}"
                    else:
                        st.markdown(result["markdown"])
                        failed = result.get("failed", [])
                        extra = f"\n\nTicker gagal: {', '.join(failed)}" if failed else ""
                        response_text = result["markdown"] + extra
                        st.info(
                            "**Disclaimer:** Analisis ini bersifat edukatif untuk pembelajaran analisis teknikal, "
                            "BUKAN rekomendasi investasi atau ajakan untuk membeli/menjual efek. "
                            "Keputusan investasi dan risiko sepenuhnya menjadi tanggung jawab pengguna."
                        )

            elif intent["intent"] == "analyze":
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
