"""
BEI Swing Engine v8.0 — Web UI (Streamlit)
Upload CSV or fetch from Yahoo Finance, run analysis, view reports.
"""

import os
import sys
import io
import tempfile
import time
from datetime import datetime

import streamlit as st
import pandas as pd

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bei_swing_engine_v8.engine import run_analysis, parse_params, default_params, analyze_ticker
from bei_swing_engine_v8.data import load_ohlcv, load_ihsg
from bei_swing_engine_v8.cleaner import clean_csv_text, rows_to_csv_string, write_cleaned_csv
from bei_swing_engine_v8.merger import merge_csv, parse_cleaned_csv
from bei_swing_engine_v8.fetcher import fetch_yfinance, fetch_and_save, VALID_PERIODS, VALID_INTERVALS
from bei_swing_engine_v8.backtest import run_backtest, render_backtest_report
from bei_swing_engine_v8.charts import render_backtest_charts, plot_equity_curve, plot_price_with_trades, plot_drawdown, plot_r_multiples
from bei_swing_engine_v8.logging_config import setup_logging


# Page config
st.set_page_config(
    page_title="BEI Swing Engine v8.0",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

setup_logging(level="WARNING")  # Reduce log noise in Streamlit


def main():
    st.title("📊 BEI Swing Engine v8.0")
    st.markdown("Deterministic swing trading analysis for Indonesian stocks (BEI)")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Parameters")

        input_mode = st.radio(
            "Data Input Mode",
            ["Manual Upload", "Yahoo Finance Fetch", "Portfolio Backtest", "Cleaner Tool", "Merger Tool"],
            index=0,
        )

        st.divider()

        if input_mode in ["Manual Upload", "Yahoo Finance Fetch"]:
            mode = st.selectbox("MODE", ["A — Full Analysis", "B — Calc Only", "C — Screening"], index=0)
            horizon = st.selectbox("HORIZON", ["SWING", "DAY", "POSITION"], index=0)
            direction = st.selectbox("DIRECTION", ["BOTH", "LONG", "SHORT"], index=0)
            position = st.selectbox("POSITION", ["NO_POSITION", "EXISTING_POSITION", "UNKNOWN"], index=0)
            modal = st.number_input("MODAL (Rp)", min_value=100000, value=10000000, step=1000000)
            risk = st.slider("RISK (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.5)
            output_fmt = st.selectbox("OUTPUT Format", ["Chat (Markdown)", "HTML", "PDF", "Excel"], index=0)

            run_backtest_opt = st.checkbox("Run Backtest (walk-forward)", value=False)
            if run_backtest_opt:
                bt_step = st.slider("Backtest step (bars)", min_value=1, max_value=20, value=1)

    # Main content based on mode
    if input_mode == "Manual Upload":
        render_manual_upload(mode, horizon, direction, position, modal, risk, output_fmt, run_backtest_opt, bt_step if run_backtest_opt else 1)
    elif input_mode == "Yahoo Finance Fetch":
        render_yfinance_fetch(mode, horizon, direction, position, modal, risk, output_fmt, run_backtest_opt, bt_step if run_backtest_opt else 1)
    elif input_mode == "Portfolio Backtest":
        render_portfolio_backtest_ui()
    elif input_mode == "Cleaner Tool":
        render_cleaner_tool()
    elif input_mode == "Merger Tool":
        render_merger_tool()


def _mode_letter(mode_str):
    return mode_str[0]  # "A", "B", or "C"


def _output_keyword(output_str):
    mapping = {"Chat (Markdown)": "Chat", "HTML": "HTML", "PDF": "PDF", "Excel": "Excel"}
    return mapping.get(output_str, "Chat")


def render_manual_upload(mode, horizon, direction, position, modal, risk, output_fmt, run_backtest_opt, bt_step):
    st.header("📁 Manual Upload")

    st.markdown("Upload CSV file(s) with OHLCV data. Format: `Date,Open,High,Low,Close,Volume`")
    uploaded_files = st.file_uploader(
        "Choose CSV file(s)",
        type=["csv"],
        accept_multiple_files=True,
    )

    ihsg_file = st.file_uploader("IHSG/JKSE CSV (optional)", type=["csv"], accept_multiple_files=False)

    if uploaded_files:
        st.info(f"{len(uploaded_files)} file(s) uploaded.")

        # Show preview
        with st.expander("Preview uploaded files"):
            for f in uploaded_files:
                df = pd.read_csv(f)
                st.text(f"{f.name} — {len(df)} rows")
                st.dataframe(df.head(5), use_container_width=True)
                f.seek(0)

        if st.button("🚀 Run Analysis", type="primary"):
            _run_analysis_from_uploads(uploaded_files, ihsg_file, mode, horizon, direction, position, modal, risk, output_fmt, run_backtest_opt, bt_step)


def render_yfinance_fetch(mode, horizon, direction, position, modal, risk, output_fmt, run_backtest_opt, bt_step):
    st.header("🌐 Yahoo Finance Fetch")

    st.markdown("Fetch OHLCV data directly from Yahoo Finance. Enter BEI tickers (e.g., `BBRI`, `BBCA`, `TLKM`).")

    col1, col2, col3 = st.columns(3)
    with col1:
        tickers_input = st.text_input("Tickers (comma-separated)", value="BBRI, TLKM")
    with col2:
        period = st.selectbox("Period", VALID_PERIODS, index=VALID_PERIODS.index("1y"))
    with col3:
        interval = st.selectbox("Interval", VALID_INTERVALS, index=0)

    fetch_ihsg = st.checkbox("Also fetch IHSG (JKSE)", value=True)

    if st.button("📡 Fetch & Analyze", type="primary"):
        _run_analysis_from_yfinance(tickers_input, period, interval, fetch_ihsg, mode, horizon, direction, position, modal, risk, output_fmt, run_backtest_opt, bt_step)


def render_portfolio_backtest_ui():
    st.header("📊 Portfolio Backtest")

    st.markdown("Backtest multiple tickers as a portfolio with capital allocation and position sizing.")

    tab1, tab2 = st.tabs(["📁 Upload CSVs", "🌐 Yahoo Finance Fetch"])

    with tab1:
        uploaded_files = st.file_uploader(
            "Upload multiple CSV files (one per ticker)",
            type=["csv"], accept_multiple_files=True, key="portfolio_upload",
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            portfolio_modal = st.number_input("Portfolio Capital (Rp)", min_value=100000, value=10000000, step=1000000, key="pf_modal")
        with col2:
            portfolio_risk = st.slider("Risk per trade (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.5, key="pf_risk")
        with col3:
            allocation_mode = st.selectbox("Allocation", ["equal_weight", "risk_based"], index=0, key="pf_alloc")

        bt_step = st.slider("Backtest step (bars)", min_value=1, max_value=20, value=1, key="pf_step")

        if uploaded_files and st.button("📊 Run Portfolio Backtest", type="primary"):
            _run_portfolio(uploaded_files, portfolio_modal, portfolio_risk, allocation_mode, bt_step, source="upload")

    with tab2:
        tickers_input = st.text_input("Tickers (comma-separated)", value="BBRI, BBCA, TLKM", key="pf_tickers")
        col1, col2 = st.columns(2)
        with col1:
            yf_period = st.selectbox("Period", ["1y", "2y", "5y", "max"], index=0, key="pf_period")
        with col2:
            yf_interval = st.selectbox("Interval", ["1d", "1wk"], index=0, key="pf_interval")

        col1, col2, col3 = st.columns(3)
        with col1:
            yf_modal = st.number_input("Portfolio Capital (Rp)", min_value=100000, value=10000000, step=1000000, key="yf_pf_modal")
        with col2:
            yf_risk = st.slider("Risk per trade (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.5, key="yf_pf_risk")
        with col3:
            yf_alloc = st.selectbox("Allocation", ["equal_weight", "risk_based"], index=0, key="yf_pf_alloc")

        yf_step = st.slider("Backtest step (bars)", min_value=1, max_value=20, value=1, key="yf_pf_step")

        if st.button("📡 Fetch & Run Portfolio", type="primary"):
            tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
            _run_portfolio_yfinance(tickers, yf_period, yf_interval, yf_modal, yf_risk, yf_alloc, yf_step)


def _run_portfolio(uploaded_files, modal, risk, allocation_mode, bt_step, source="upload"):
    from bei_swing_engine_v8.portfolio import run_portfolio_backtest, render_portfolio_report, plot_portfolio_equity, plot_portfolio_drawdown, plot_per_ticker_pnl

    temp_dir = tempfile.mkdtemp()
    dataframes = []

    for f in uploaded_files:
        path = os.path.join(temp_dir, f.name)
        with open(path, "wb") as out:
            out.write(f.read())
        df = load_ohlcv(path)
        dataframes.append(df)

    params = {"POSITION": "NO_POSITION", "DIRECTION": "BOTH", "MODAL": modal, "RISK": risk}

    with st.spinner("Running portfolio backtest..."):
        result = run_portfolio_backtest(dataframes, params, step=bt_step, allocation_mode=allocation_mode)

    # Metrics
    m = result.metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Trades", f"{m['total_trades']} ({m['closed_trades']} closed)")
    with col2:
        st.metric("Win Rate", f"{m['win_rate']:.1f}%")
    with col3:
        st.metric("Total Return", f"{m['total_return_pct']:.2f}%")
    with col4:
        st.metric("Max Drawdown", f"{m['max_drawdown_pct']:.2f}%")

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("Expectancy", f"{m['expectancy']:.2f}R")
    with col6:
        st.metric("Profit Factor", f"{m['profit_factor']:.2f}")
    with col7:
        st.metric("Sharpe Ratio", f"{m['sharpe_ratio']:.2f}")
    with col8:
        st.metric("Final Equity", f"Rp {m['final_equity']:,.0f}".replace(",", "."))

    # Charts
    st.plotly_chart(plot_portfolio_equity(result), use_container_width=True)
    st.plotly_chart(plot_portfolio_drawdown(result), use_container_width=True)
    st.plotly_chart(plot_per_ticker_pnl(result), use_container_width=True)

    # Per-ticker table
    st.subheader("Per-Ticker Breakdown")
    ticker_data = []
    for ticker in result.tickers:
        s = result.per_ticker.get(ticker)
        if s:
            ticker_data.append({
                "Ticker": s.ticker, "Trades": s.closed_trades,
                "Win Rate": f"{s.win_rate:.1f}%", "Expectancy": f"{s.expectancy:.2f}R",
                "PnL": f"Rp {s.total_pnl:,.0f}".replace(",", "."),
                "Return %": f"{s.return_pct:.2f}%",
            })
    if ticker_data:
        st.dataframe(pd.DataFrame(ticker_data), use_container_width=True)

    # Trade log
    if result.trades:
        with st.expander(f"Trade Log ({len(result.trades)} trades)"):
            trade_data = []
            for t in result.trades:
                trade_data.append({
                    "Ticker": t.ticker, "Entry Date": t.entry_date.strftime("%Y-%m-%d"),
                    "Exit Date": t.exit_date.strftime("%Y-%m-%d"), "Dir": t.direction,
                    "Entry Price": t.entry_price, "SL": t.sl_price, "Exit Price": t.exit_price,
                    "Reason": t.exit_reason, "R": f"{t.r_multiple:.2f}",
                    "PnL": f"Rp {t.pnl_rpiah:,.0f}".replace(",", "."),
                })
            st.dataframe(pd.DataFrame(trade_data), use_container_width=True)

    # Text report
    with st.expander("Text Report"):
        st.markdown(render_portfolio_report(result))


def _run_portfolio_yfinance(tickers, period, interval, modal, risk, allocation_mode, bt_step):
    from bei_swing_engine_v8.portfolio import run_portfolio_backtest, render_portfolio_report, plot_portfolio_equity, plot_portfolio_drawdown, plot_per_ticker_pnl
    from bei_swing_engine_v8.fetcher import fetch_and_save

    temp_dir = tempfile.mkdtemp()
    dataframes = []
    progress = st.progress(0)
    status = st.empty()

    for i, ticker in enumerate(tickers):
        status.text(f"Fetching {ticker}...")
        result = fetch_and_save(ticker, period=period, interval=interval, output_dir=temp_dir)
        if result.error:
            st.error(f"{ticker}: {result.error}")
        elif result.output_name:
            path = os.path.join(temp_dir, result.output_name)
            if os.path.exists(path):
                df = load_ohlcv(path)
                dataframes.append(df)
        progress.progress((i + 1) / len(tickers))
    status.text("")

    if not dataframes:
        st.error("No data fetched.")
        return

    params = {"POSITION": "NO_POSITION", "DIRECTION": "BOTH", "MODAL": modal, "RISK": risk}

    with st.spinner("Running portfolio backtest..."):
        result = run_portfolio_backtest(dataframes, params, step=bt_step, allocation_mode=allocation_mode)

    m = result.metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Trades", f"{m['total_trades']} ({m['closed_trades']} closed)")
    with col2:
        st.metric("Win Rate", f"{m['win_rate']:.1f}%")
    with col3:
        st.metric("Total Return", f"{m['total_return_pct']:.2f}%")
    with col4:
        st.metric("Max Drawdown", f"{m['max_drawdown_pct']:.2f}%")

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("Expectancy", f"{m['expectancy']:.2f}R")
    with col6:
        st.metric("Profit Factor", f"{m['profit_factor']:.2f}")
    with col7:
        st.metric("Sharpe Ratio", f"{m['sharpe_ratio']:.2f}")
    with col8:
        st.metric("Final Equity", f"Rp {m['final_equity']:,.0f}".replace(",", "."))

    st.plotly_chart(plot_portfolio_equity(result), use_container_width=True)
    st.plotly_chart(plot_portfolio_drawdown(result), use_container_width=True)
    st.plotly_chart(plot_per_ticker_pnl(result), use_container_width=True)

    st.subheader("Per-Ticker Breakdown")
    ticker_data = []
    for ticker in result.tickers:
        s = result.per_ticker.get(ticker)
        if s:
            ticker_data.append({
                "Ticker": s.ticker, "Trades": s.closed_trades,
                "Win Rate": f"{s.win_rate:.1f}%", "Expectancy": f"{s.expectancy:.2f}R",
                "PnL": f"Rp {s.total_pnl:,.0f}".replace(",", "."),
                "Return %": f"{s.return_pct:.2f}%",
            })
    if ticker_data:
        st.dataframe(pd.DataFrame(ticker_data), use_container_width=True)

    if result.trades:
        with st.expander(f"Trade Log ({len(result.trades)} trades)"):
            trade_data = []
            for t in result.trades:
                trade_data.append({
                    "Ticker": t.ticker, "Entry Date": t.entry_date.strftime("%Y-%m-%d"),
                    "Exit Date": t.exit_date.strftime("%Y-%m-%d"), "Dir": t.direction,
                    "Entry Price": t.entry_price, "SL": t.sl_price, "Exit Price": t.exit_price,
                    "Reason": t.exit_reason, "R": f"{t.r_multiple:.2f}",
                    "PnL": f"Rp {t.pnl_rpiah:,.0f}".replace(",", "."),
                })
            st.dataframe(pd.DataFrame(trade_data), use_container_width=True)

    with st.expander("Text Report"):
        st.markdown(render_portfolio_report(result))


def render_cleaner_tool():
    st.header("🧹 CSV Cleaner Tool")
    st.markdown("Clean CSV from any source (Yahoo Finance, Investing.com, TradingView, etc.) into standard format.")

    uploaded = st.file_uploader("Upload raw CSV file(s)", type=["csv"], accept_multiple_files=True, key="cleaner")

    if uploaded:
        results = []
        for f in uploaded:
            text = f.read().decode("utf-8-sig")
            result = clean_csv_text(text, f.name)
            results.append((f.name, result))
            f.seek(0)

        st.subheader("Results")
        for name, result in results:
            with st.expander(f"{name} — {'✅ ' + str(result.row_count) + ' rows' if not result.error else '❌ ' + result.error}"):
                if result.error:
                    st.error(result.error)
                else:
                    st.text(f"Delimiter: {result.delimiter}")
                    st.text(f"Date format: {result.date_format}")
                    st.text(f"Source: {result.source}")
                    st.text(f"Rows: {result.row_count}")
                    csv_str = rows_to_csv_string(result.rows)
                    st.text_area("Preview (first 5 rows)", csv_str.split("\n")[:7], height=150)
                    st.download_button(
                        f"⬇ Download {result.output_name}",
                        csv_str,
                        result.output_name,
                        "text/csv",
                    )


def render_merger_tool():
    st.header("🔀 CSV Merger Tool")
    st.markdown("Append new data from Yahoo Finance to an existing cleaned CSV file.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Existing Cleaned CSV")
        existing_file = st.file_uploader("Upload existing cleaned CSV", type=["csv"], key="merger_existing")
        if existing_file:
            existing_text = existing_file.read().decode("utf-8-sig")
            existing_rows, existing_dates = parse_cleaned_csv(existing_text)
            if existing_rows:
                st.success(f"{len(existing_rows)} rows, {existing_rows[0]['date']} to {existing_rows[-1]['date']}")
            else:
                st.error("Cannot parse existing CSV")
            existing_file.seek(0)

    with col2:
        st.subheader("2. New Raw CSV(s)")
        new_files = st.file_uploader("Upload new raw CSV file(s)", type=["csv"], accept_multiple_files=True, key="merger_new")
        if new_files:
            st.info(f"{len(new_files)} file(s) uploaded")

    if existing_file and new_files:
        if st.button("🔀 Merge", type="primary"):
            existing_text = existing_file.read().decode("utf-8-sig")
            new_texts = [(f.name, f.read().decode("utf-8-sig")) for f in new_files]

            result = merge_csv(existing_text, new_texts)

            if result.error:
                st.error(result.error)
            else:
                st.success(f"Merge complete! {result.new_count} new rows added.")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Existing", result.existing_count)
                with col2:
                    st.metric("New Added", result.new_count)
                with col3:
                    st.metric("Merged Total", result.merged_count)

                if result.new_dates:
                    st.text(f"New dates: {', '.join(result.new_dates)}")

                csv_str = rows_to_csv_string(result.rows)
                st.download_button(
                    "⬇ Download Merged CSV",
                    csv_str,
                    result.output_name,
                    "text/csv",
                )


def _run_analysis_from_uploads(uploaded_files, ihsg_file, mode, horizon, direction, position, modal, risk, output_fmt, run_backtest_opt, bt_step):
    # Save uploaded files to temp dir
    temp_dir = tempfile.mkdtemp()
    data_paths = []
    for f in uploaded_files:
        path = os.path.join(temp_dir, f.name)
        with open(path, "wb") as out:
            out.write(f.read())
        data_paths.append(path)

    ihsg_path = None
    if ihsg_file:
        ihsg_path = os.path.join(temp_dir, ihsg_file.name)
        with open(ihsg_path, "wb") as out:
            out.write(ihsg_file.read())

    _run_engine(data_paths, ihsg_path, mode, horizon, direction, position, modal, risk, output_fmt, run_backtest_opt, bt_step, temp_dir)


def _run_analysis_from_yfinance(tickers_input, period, interval, fetch_ihsg, mode, horizon, direction, position, modal, risk, output_fmt, run_backtest_opt, bt_step):
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    if not tickers:
        st.error("Please enter at least one ticker.")
        return

    temp_dir = tempfile.mkdtemp()
    data_paths = []
    progress = st.progress(0)
    status = st.empty()

    for i, ticker in enumerate(tickers):
        status.text(f"Fetching {ticker}...")
        result = fetch_and_save(ticker, period=period, interval=interval, output_dir=temp_dir)
        if result.error:
            st.error(f"{ticker}: {result.error}")
        elif result.output_name:
            path = os.path.join(temp_dir, result.output_name)
            if os.path.exists(path):
                data_paths.append(path)
        progress.progress((i + 1) / len(tickers))

    ihsg_path = None
    if fetch_ihsg:
        status.text("Fetching IHSG (JKSE)...")
        result = fetch_and_save("IHSG", period=period, interval=interval, output_dir=temp_dir)
        if not result.error:
            ihsg_path = os.path.join(temp_dir, "IHSG-JKSE_cleaned.csv")

    status.text("")

    if not data_paths:
        st.error("No data fetched. Check ticker symbols.")
        return

    _run_engine(data_paths, ihsg_path, mode, horizon, direction, position, modal, risk, output_fmt, run_backtest_opt, bt_step, temp_dir)


def _run_engine(data_paths, ihsg_path, mode, horizon, direction, position, modal, risk, output_fmt, run_backtest_opt, bt_step, output_dir):
    mode_letter = _mode_letter(mode)
    output_keyword = _output_keyword(output_fmt)

    params_text = (
        f"MODE={mode_letter}\n"
        f"HORIZON={horizon}\n"
        f"DIRECTION={direction}\n"
        f"POSITION={position}\n"
        f"MODAL={int(modal)}\n"
        f"RISK={risk}\n"
        f"OUTPUT={output_keyword}\n"
        f"IHSG={'None' if ihsg_path is None else 'uploaded'}"
    )

    with st.spinner("Running analysis..."):
        t0 = time.perf_counter()
        output = run_analysis(
            data_paths=data_paths,
            params_text=params_text,
            ihsg_path=ihsg_path,
            output_dir=output_dir,
        )
        elapsed = time.perf_counter() - t0

    st.success(f"Analysis complete in {elapsed:.2f}s")

    # Show report
    if output_keyword == "PDF":
        pdf_path = os.path.join(output_dir, "BEI_Swing_Engine_Report.pdf")
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.download_button("⬇ Download PDF Report", f, "BEI_Swing_Engine_Report.pdf", "application/pdf")
    elif output_keyword == "HTML":
        html_path = os.path.join(output_dir, "BEI_Swing_Engine_Report.html")
        if os.path.exists(html_path):
            with open(html_path, "r", encoding="utf-8") as f:
                st.download_button("⬇ Download HTML Report", f.read(), "BEI_Swing_Engine_Report.html", "text/html")
    elif output_keyword == "Excel":
        xlsx_path = os.path.join(output_dir, "BEI_Swing_Engine_Report.xlsx")
        if os.path.exists(xlsx_path):
            with open(xlsx_path, "rb") as f:
                st.download_button("⬇ Download Excel Report", f, "BEI_Swing_Engine_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        # Markdown
        st.markdown(output)

    # Backtest
    if run_backtest_opt and mode_letter in ("A", "B"):
        st.divider()
        st.header("📈 Backtest Results")
        with st.spinner("Running backtest..."):
            params = parse_params(params_text)
            all_results = []
            for path in data_paths:
                df = load_ohlcv(path)
                result = run_backtest(df, params, step=bt_step)
                all_results.append(result)

        # Display each ticker's backtest
        from bei_swing_engine_v8.charts import render_backtest_charts, plot_equity_curve, plot_price_with_trades, plot_drawdown, plot_r_multiples

        for i, result in enumerate(all_results):
            ticker = result.ticker
            df = load_ohlcv(data_paths[i])

            st.subheader(f"📊 {ticker}")

            # Metrics row
            m = result.metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Trades", f"{m['total_trades']} ({m['closed_trades']} closed)")
            with col2:
                st.metric("Win Rate", f"{m['win_rate']:.1f}%")
            with col3:
                st.metric("Expectancy (R)", f"{m['expectancy']:.2f}")
            with col4:
                st.metric("Max Drawdown", f"{m['max_drawdown_pct']:.2f}%")

            col5, col6 = st.columns(2)
            with col5:
                st.metric("Profit Factor", f"{m['profit_factor']:.2f}")
            with col6:
                st.metric("Total Return", f"{m['total_return_pct']:.2f}%")

            # Charts
            charts = render_backtest_charts(result, df)
            for chart_name, fig in charts:
                st.plotly_chart(fig, use_container_width=True)

            # Trade log table
            if result.trades:
                with st.expander(f"Trade Log — {ticker} ({len(result.trades)} trades)"):
                    trade_data = []
                    for t in result.trades:
                        trade_data.append({
                            "Entry": t.entry_date.strftime("%Y-%m-%d"),
                            "Exit": t.exit_date.strftime("%Y-%m-%d"),
                            "Dir": t.direction,
                            "Entry Price": t.entry_price,
                            "SL": t.sl_price,
                            "TP1": t.tp1_price if t.tp1_price else "",
                            "Exit Price": t.exit_price,
                            "Reason": t.exit_reason,
                            "R-multiple": f"{t.r_multiple:.2f}",
                            "PnL %": f"{t.pnl_pct:.2f}%",
                        })
                    st.dataframe(pd.DataFrame(trade_data), use_container_width=True)

            # Text report
            with st.expander(f"Text Report — {ticker}"):
                st.markdown(render_backtest_report(result))

            st.divider()

        # Aggregate summary
        if len(all_results) > 1:
            from bei_swing_engine_v8.backtest import render_backtest_aggregate
            st.subheader("📋 Aggregate Summary")
            st.markdown(render_backtest_aggregate(all_results))


if __name__ == "__main__":
    main()
