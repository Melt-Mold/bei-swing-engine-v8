"""
Main analysis engine orchestration.
"""

import os
import time
import traceback
from typing import Dict, List, Optional
from pathlib import Path

import pandas as pd

from .data import load_ohlcv, validate_data, load_ihsg
from .indicators import compute_all_indicators
from .structure import analyze_structure
from .setup import detect_setups, select_primary_setup, apply_sma200_sufficiency_cap
from .logging_config import get_logger
from concurrent.futures import ProcessPoolExecutor, as_completed
from .risk import assess_tradeability
from .decision import run_decision_engine, combine_unknown_branch, Decision
from .market_context import analyze_market_regime
from .output import (
    render_markdown,
    render_calc_only_markdown,
    render_html_single,
    render_pdf_single,
    render_excel_single,
    build_indicator_table,
    render_aggregate_summary,
    render_screening_summary,
)

_log = get_logger("engine")


def default_params() -> Dict:
    return {
        "MODE": "A",
        "HORIZON": "SWING",
        "DIRECTION": "BOTH",
        "POSITION": "UNKNOWN",
        "MODAL": 10_000_000,
        "RISK": 2.0,
        "OUTPUT": "Chat",
        "IHSG": None,
    }


def parse_params(param_text: str) -> Dict:
    """Parse KEY=VALUE parameters or inline format."""
    params = default_params()
    if not param_text:
        return params

    for line in param_text.strip().splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().upper()
        value = value.strip()

        if key in {"MODAL"}:
            # Support '10jt' / '20jt' shorthand
            value = value.lower().replace("jt", "000000").replace("m", "000000").replace(".", "")
            try:
                params[key] = float(value)
            except ValueError:
                pass
        elif key in {"RISK"}:
            try:
                params[key] = float(value)
            except ValueError:
                pass
        else:
            params[key] = value

    return params


def _slice_indicators(indicators: Dict, cutoff: pd.Timestamp) -> Dict:
    """Slice all indicator series up to and including cutoff."""
    sliced = {}
    for key, val in indicators.items():
        if isinstance(val, pd.Series):
            sliced[key] = val.loc[:cutoff].copy()
        elif isinstance(val, str):
            sliced[key] = val
        else:
            sliced[key] = val
    return sliced


def analyze_ticker(
    df: pd.DataFrame,
    params: Dict,
    ihsg_df: Optional[pd.DataFrame] = None,
    precomputed: Optional[Dict] = None,
    build_output_rows: bool = True,
) -> Dict:
    """Run full analysis pipeline for a single ticker.

    If precomputed is provided, it must contain 'indicators' and 'structure'
    computed on the full (untruncated) dataframe. They will be sliced/filtered
    to match the last date in df for fast walk-forward/backtest use.

    Set build_output_rows=False in backtest loops to skip expensive 42-row
    table construction and divergence scanning.
    """
    ticker = df["Ticker"].iloc[0]
    bars = len(df)
    _log.debug("analyze_ticker start | ticker=%s bars=%d", ticker, bars)

    # G0 DATA GATE
    validation = validate_data(df)
    if validation["status"] == "ERROR":
        _log.warning("INSUFFICIENT_DATA | ticker=%s bars=%d reason=%s", ticker, bars, "; ".join(validation["reasons"]))
        return {
            "ticker": ticker,
            "status": "INSUFFICIENT_DATA",
            "reason": "; ".join(validation["reasons"]),
            "validation": validation,
        }

    t0 = time.perf_counter()
    try:
        if precomputed is not None:
            cutoff = df.index[-1]
            indicators = _slice_indicators(precomputed["indicators"], cutoff)
            structure = precomputed["structure"].filter_as_of(cutoff, df, indicators)
            _log.debug("using precomputed indicators/structure | ticker=%s cutoff=%s", ticker, cutoff.date())
        else:
            # Compute indicators
            indicators = compute_all_indicators(df)
            # Structure
            structure = analyze_structure(df, indicators)
            _log.debug("indicators+structure computed | ticker=%s elapsed=%.3fs", ticker, time.perf_counter() - t0)
    except Exception as e:
        _log.error("indicator/structure computation failed | ticker=%s error=%s\n%s", ticker, e, traceback.format_exc())
        raise

    # Setups
    setups = detect_setups(df, structure, indicators)
    setups = apply_sma200_sufficiency_cap(setups, bars)
    primary_setup = select_primary_setup(setups)
    _log.info("setup detected | ticker=%s primary=%s %s %s", ticker, primary_setup.type, primary_setup.direction, primary_setup.status)

    # Tradeability
    tradeability = assess_tradeability(
        df,
        primary_setup,
        structure,
        indicators,
        modal=params.get("MODAL", 10_000_000),
        risk_pct=params.get("RISK", 2.0),
        warnings=[],
    )
    _log.info("tradeability | ticker=%s state=%s reason=%s", ticker, tradeability.state, tradeability.reason)

    # Decision based on POSITION
    position = params.get("POSITION", "UNKNOWN")

    held_direction = params.get("HELD_DIRECTION", "LONG")
    if position == "UNKNOWN":
        # Infer held direction from setup/thesis for dual-branch comparison
        inferred_held = primary_setup.direction if primary_setup.direction in {"LONG", "SHORT"} else held_direction
        no_pos_dec = run_decision_engine(df, indicators, structure, primary_setup, tradeability, params, position_branch="NO_POSITION")
        existing_dec = run_decision_engine(df, indicators, structure, primary_setup, tradeability, params, position_branch="EXISTING_POSITION", held_position_direction=inferred_held)
        decision = combine_unknown_branch(no_pos_dec, existing_dec)
    else:
        decision = run_decision_engine(df, indicators, structure, primary_setup, tradeability, params, position_branch=position, held_position_direction=held_direction)

    _log.info("decision | ticker=%s decision=%s direction=%s thesis=%s reason_codes=%s",
              ticker, decision.decision, decision.decision_direction, decision.thesis_state, decision.reason_codes)

    # Market context
    market_regime = analyze_market_regime(ihsg_df)

    # Build indicator table for output (skip in fast loops like backtest)
    indicator_rows = build_indicator_table(df, indicators, structure) if build_output_rows else []

    _log.debug("analyze_ticker done | ticker=%s total_elapsed=%.3fs", ticker, time.perf_counter() - t0)
    return {
        "ticker": ticker,
        "status": "OK",
        "validation": validation,
        "df": df,
        "indicators": indicators,
        "indicator_rows": indicator_rows,
        "structure": structure,
        "setups": setups,
        "primary_setup": primary_setup,
        "tradeability": tradeability,
        "decision": decision,
        "market_regime": market_regime,
        "params": params,
    }


def render_ticker_report(result: Dict, output_format: str = "Chat", mode: str = "A") -> str:
    """Render report for one ticker in requested format and mode."""
    if result.get("status") in {"INSUFFICIENT_DATA", "ERROR"}:
        return f"## {result['ticker']}: {result.get('status', 'ERROR')}\n\n{result.get('reason', '')}\n"

    ticker = result["ticker"]

    if mode.upper() == "B":
        md = render_calc_only_markdown(
            ticker,
            result["df"],
            result["indicators"],
            result["structure"],
            result["primary_setup"],
            result["market_regime"],
            result["params"],
        )
    else:
        md = render_markdown(
            ticker,
            result["df"],
            result["indicators"],
            result["structure"],
            result["primary_setup"],
            result["tradeability"],
            result["decision"],
            result["market_regime"],
            result["params"],
        )

    if output_format.upper() in {"HTML", "PDF"}:
        return render_html_single(ticker, md)

    return md


def _analyze_one(path: str, params: Dict, ihsg_df: Optional[pd.DataFrame]) -> Dict:
    """Worker for parallel analysis."""
    try:
        _log.info("loading CSV | path=%s", path)
        df = load_ohlcv(path)
        return analyze_ticker(df, params, ihsg_df)
    except Exception as e:
        ticker = Path(path).stem.replace("_cleaned", "").replace(".JK", "").upper()
        _log.error("analysis failed | ticker=%s path=%s error=%s\n%s", ticker, path, e, traceback.format_exc())
        return {
            "ticker": ticker,
            "status": "ERROR",
            "reason": str(e),
        }


def run_analysis(
    data_paths: List[str],
    params_text: str = "",
    ihsg_path: Optional[str] = None,
    output_dir: str = ".",
    parallel: bool = False,
) -> str:
    """
    Run full analysis on one or more tickers and produce aggregated output.
    Returns the rendered markdown (or HTML if requested).

    parallel: if True, analyze tickers in parallel using process pool.
    """
    params = parse_params(params_text)
    output_format = params.get("OUTPUT", "Chat")
    mode = params.get("MODE", "A").upper()

    _log.info("run_analysis start | tickers=%d mode=%s output=%s parallel=%s",
              len(data_paths), mode, output_format, parallel)

    # Load IHSG if provided
    ihsg_df = load_ihsg(ihsg_path) if ihsg_path else None
    if ihsg_df is not None:
        _log.info("IHSG data loaded | bars=%d range=%s..%s", len(ihsg_df), ihsg_df.index.min().date(), ihsg_df.index.max().date())
    else:
        _log.info("no IHSG data provided; market regime will be N/A")

    t_start = time.perf_counter()

    if parallel and len(data_paths) > 1:
        max_workers = min(len(data_paths), (os.cpu_count() or 2))
        _log.info("parallel mode | workers=%d", max_workers)
        results = [None] * len(data_paths)
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_analyze_one, path, params, ihsg_df): idx for idx, path in enumerate(data_paths)}
            for future in as_completed(futures):
                idx = futures[future]
                results[idx] = future.result()
    else:
        results = []
        for path in data_paths:
            results.append(_analyze_one(path, params, ihsg_df))

    ok_count = sum(1 for r in results if r.get("status") == "OK")
    err_count = len(results) - ok_count
    _log.info("analysis complete | ok=%d errors=%d elapsed=%.2fs", ok_count, err_count, time.perf_counter() - t_start)

    mode = params.get("MODE", "A").upper()

    # Aggregate summary data (used for MODE=A and MODE=C)
    summary_data = []
    for result in results:
        if result.get("status") != "OK":
            summary_data.append({
                "ticker": result["ticker"],
                "thesis": "N/A",
                "setup": "N/A",
                "tradeability": "N/A",
                "decision": "INSUFFICIENT_DATA",
                "warnings": result.get("reason", ""),
            })
        else:
            dec = result["decision"]
            summary_data.append({
                "ticker": result["ticker"],
                "thesis": dec.thesis_state,
                "setup": f"{result['primary_setup'].type} {result['primary_setup'].status}",
                "tradeability": dec.tradeability_state,
                "decision": dec.decision,
                "warnings": "; ".join(dec.warnings),
            })

    if mode == "C":
        # Screening: aggregate summary only
        final_output = render_screening_summary(summary_data)
    else:
        # MODE=A full report or MODE=B calc-only
        reports = []
        for result in results:
            reports.append(render_ticker_report(result, output_format, mode=mode))

        summary = render_aggregate_summary(summary_data) if mode == "A" else ""

        if summary:
            final_output = "\n\n".join(reports) + "\n\n" + summary
        else:
            final_output = "\n\n".join(reports)

    # Write files if requested
    os.makedirs(output_dir, exist_ok=True)
    _log.info("writing output | mode=%s format=%s dir=%s", mode, output_format, output_dir)

    base_name = "BEI_Swing_Engine_Screening" if mode == "C" else "BEI_Swing_Engine_Report"

    if output_format.upper() == "HTML":
        out_path = os.path.join(output_dir, f"{base_name}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(final_output)
        _log.info("HTML written | path=%s", out_path)
    elif output_format.upper() == "PDF":
        # Generate PDF from HTML reports (one per ticker, merged)
        from pypdf import PdfWriter, PdfReader
        import io

        pdf_merger = PdfWriter()
        pdf_success = False
        pdf_pages = 0
        for result in results:
            if result.get("status") != "OK":
                continue
            ticker = result["ticker"]
            html_report = render_ticker_report(result, "HTML", mode=mode)
            pdf_bytes = io.BytesIO()
            try:
                ok = render_pdf_single(ticker, html_report, pdf_bytes)
            except Exception as e:
                _log.error("PDF render failed | ticker=%s error=%s", ticker, e)
                ok = False
            if ok:
                pdf_bytes.seek(0)
                try:
                    reader = PdfReader(pdf_bytes)
                    for page in reader.pages:
                        pdf_merger.add_page(page)
                        pdf_pages += 1
                    pdf_success = True
                except Exception as e:
                    _log.error("PDF merge failed | ticker=%s error=%s", ticker, e)

        out_path = os.path.join(output_dir, f"{base_name}.pdf")
        if pdf_success:
            with open(out_path, "wb") as f:
                pdf_merger.write(f)
            _log.info("PDF written | path=%s pages=%d", out_path, pdf_pages)
        else:
            # Fallback: write HTML if PDF generation failed
            out_path = os.path.join(output_dir, f"{base_name}.html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(final_output)
            _log.warning("PDF generation failed; fallback to HTML | path=%s", out_path)
    elif output_format.upper() == "EXCEL" and mode in {"A", "B"}:
        out_path = os.path.join(output_dir, f"{base_name}.xlsx")
        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            for result in results:
                if result.get("status") == "OK":
                    df_rows = pd.DataFrame(result["indicator_rows"]).drop(columns=["Badge"], errors="ignore")
                    df_rows.to_excel(writer, sheet_name=result["ticker"][:31], index=False)

    # Always also write markdown
    md_path = os.path.join(output_dir, f"{base_name}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(final_output)

    return final_output
