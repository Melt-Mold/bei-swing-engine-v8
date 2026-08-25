"""
BEI Swing Engine v8.0 — REST API Server (FastAPI)
Exposes engine functionality as REST API endpoints for system integration.

Endpoints:
  GET  /                  — API info
  GET  /health            — Health check
  POST /analyze           — Analyze uploaded CSV(s)
  POST /screening         — Multi-ticker screening
  POST /backtest          — Run backtest on uploaded CSV
  POST /portfolio         — Run portfolio backtest on multiple CSVs
  POST /clean             — Clean raw CSV
  POST /merge             — Merge existing + new CSV
  GET  /fetch/{ticker}   — Fetch from Yahoo Finance and analyze
"""

import os
import io
import json
import tempfile
from typing import List, Optional, Dict
from pydantic import BaseModel

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse

from .data import load_ohlcv, load_ihsg
from .engine import analyze_ticker, run_analysis, parse_params, default_params
from .backtest import run_backtest, render_backtest_report
from .portfolio import run_portfolio_backtest, render_portfolio_report
from .cleaner import clean_csv_text, rows_to_csv_string
from .merger import merge_csv, parse_cleaned_csv
from .fetcher import fetch_and_save
from .logging_config import get_logger

_log = get_logger("api")

app = FastAPI(
    title="BEI Swing Engine v8.0 API",
    description="Deterministic swing trading analysis for Indonesian stocks (BEI/Bursa Efek Indonesia). "
    "Upload OHLCV CSV or fetch from Yahoo Finance to get swing-trading analysis with "
    "BUY/HOLD/SELL/WAIT/NO_SETUP decisions.",
    version="8.0.0",
    openapi_tags=[
        {"name": "info", "description": "API info and health check"},
        {"name": "analysis", "description": "Technical analysis and screening"},
        {"name": "backtest", "description": "Walk-forward and portfolio backtesting"},
        {"name": "data", "description": "CSV cleaning and merging utilities"},
    ],
)


# ============================================================
# Models
# ============================================================

class AnalysisRequest(BaseModel):
    mode: str = "A"
    horizon: str = "SWING"
    direction: str = "BOTH"
    position: str = "NO_POSITION"
    modal: float = 10_000_000
    risk: float = 2.0


class FetchRequest(BaseModel):
    ticker: str
    period: str = "1y"
    interval: str = "1d"
    mode: str = "C"
    direction: str = "BOTH"
    position: str = "NO_POSITION"
    modal: float = 10_000_000
    risk: float = 2.0


# ============================================================
# Endpoints
# ============================================================

@app.get("/", tags=["info"])
async def root():
    """API info."""
    return {
        "name": "BEI Swing Engine v8.0 API",
        "version": "8.0.0",
        "endpoints": [
            "GET /health",
            "POST /analyze",
            "POST /screening",
            "POST /backtest",
            "POST /portfolio",
            "POST /clean",
            "POST /merge",
            "GET /fetch/{ticker}",
        ],
    }


@app.get("/health", tags=["info"])
async def health():
    """Health check."""
    return {"status": "ok", "engine": "BEI Swing Engine v8.0"}


@app.post("/analyze", tags=["analysis"], summary="Analyze uploaded CSV(s)")
async def analyze(
    files: List[UploadFile] = File(...),
    mode: str = Form("A"),
    horizon: str = Form("SWING"),
    direction: str = Form("BOTH"),
    position: str = Form("NO_POSITION"),
    modal: float = Form(10000000),
    risk: float = Form(2.0),
    output: str = Form("Chat"),
    ihsg_file: Optional[UploadFile] = File(None),
):
    """
    Analyze one or more CSV files.
    Upload CSV(s) + optional IHSG, get analysis report.
    """
    temp_dir = tempfile.mkdtemp()
    data_paths = []

    for f in files:
        path = os.path.join(temp_dir, f.filename)
        with open(path, "wb") as out:
            out.write(await f.read())
        data_paths.append(path)

    ihsg_path = None
    if ihsg_file:
        ihsg_path = os.path.join(temp_dir, ihsg_file.filename)
        with open(ihsg_path, "wb") as out:
            out.write(await ihsg_file.read())

    params_text = (
        f"MODE={mode}\nHORIZON={horizon}\nDIRECTION={direction}\n"
        f"POSITION={position}\nMODAL={int(modal)}\nRISK={risk}\n"
        f"OUTPUT={output}\nIHSG={'uploaded' if ihsg_path else 'None'}"
    )

    try:
        report = run_analysis(data_paths, params_text, ihsg_path, output_dir=temp_dir)
        return {"report": report, "tickers": [os.path.basename(p) for p in data_paths]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/screening", tags=["analysis"], summary="Multi-ticker screening")
async def screening(
    files: List[UploadFile] = File(...),
    modal: float = Form(10000000),
    risk: float = Form(2.0),
    direction: str = Form("BOTH"),
    ihsg_file: Optional[UploadFile] = File(None),
):
    """
    Multi-ticker screening (MODE=C).
    Returns aggregate summary table.
    """
    temp_dir = tempfile.mkdtemp()
    data_paths = []

    for f in files:
        path = os.path.join(temp_dir, f.filename)
        with open(path, "wb") as out:
            out.write(await f.read())
        data_paths.append(path)

    ihsg_path = None
    if ihsg_file:
        ihsg_path = os.path.join(temp_dir, ihsg_file.filename)
        with open(ihsg_path, "wb") as out:
            out.write(await ihsg_file.read())

    params_text = (
        f"MODE=C\nHORIZON=SWING\nDIRECTION={direction}\n"
        f"POSITION=NO_POSITION\nMODAL={int(modal)}\nRISK={risk}\n"
        f"OUTPUT=Chat\nIHSG={'uploaded' if ihsg_path else 'None'}"
    )

    try:
        report = run_analysis(data_paths, params_text, ihsg_path, output_dir=temp_dir)
        return {"screening": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/backtest", tags=["backtest"], summary="Run walk-forward backtest")
async def backtest(
    file: UploadFile = File(...),
    step: int = Form(1),
    modal: float = Form(10000000),
    risk: float = Form(2.0),
    direction: str = Form("BOTH"),
):
    """
    Run backtest on a single CSV file.
    Returns backtest report + metrics.
    """
    temp_dir = tempfile.mkdtemp()
    path = os.path.join(temp_dir, file.filename)
    with open(path, "wb") as out:
        out.write(await file.read())

    try:
        df = load_ohlcv(path)
        params = {
            "POSITION": "NO_POSITION", "DIRECTION": direction,
            "MODAL": modal, "RISK": risk, "OUTPUT": "Chat",
            "IHSG": "None", "MODE": "A", "HORIZON": "SWING",
        }
        result = run_backtest(df, params, step=step)
        report = render_backtest_report(result)
        return {
            "report": report,
            "metrics": result.metrics,
            "trades": len(result.trades),
            "snapshots": len(result.snapshots),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/portfolio", tags=["backtest"], summary="Run portfolio backtest")
async def portfolio(
    files: List[UploadFile] = File(...),
    step: int = Form(1),
    modal: float = Form(10000000),
    risk: float = Form(2.0),
    allocation: str = Form("equal_weight"),
    direction: str = Form("BOTH"),
):
    """
    Run portfolio backtest on multiple CSV files.
    Returns portfolio report + metrics + per-ticker breakdown.
    """
    temp_dir = tempfile.mkdtemp()
    dataframes = []

    for f in files:
        path = os.path.join(temp_dir, f.filename)
        with open(path, "wb") as out:
            out.write(await f.read())
        df = load_ohlcv(path)
        dataframes.append(df)

    params = {
        "POSITION": "NO_POSITION", "DIRECTION": direction,
        "MODAL": modal, "RISK": risk, "OUTPUT": "Chat",
        "IHSG": "None", "MODE": "A", "HORIZON": "SWING",
    }

    try:
        result = run_portfolio_backtest(dataframes, params, step=step, allocation_mode=allocation)
        report = render_portfolio_report(result)
        return {
            "report": report,
            "metrics": result.metrics,
            "per_ticker": {
                ticker: {
                    "trades": s.closed_trades,
                    "win_rate": s.win_rate,
                    "expectancy": s.expectancy,
                    "pnl": s.total_pnl,
                    "return_pct": s.return_pct,
                }
                for ticker, s in result.per_ticker.items()
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clean", tags=["data"], summary="Clean raw CSV")
async def clean_csv(
    file: UploadFile = File(...),
):
    """
    Clean a raw CSV file into standard OHLCV format.
    Returns cleaned CSV content + metadata.
    """
    content = (await file.read()).decode("utf-8-sig")
    result = clean_csv_text(content, file.filename)

    if result.error:
        raise HTTPException(status_code=400, detail=result.error)

    return {
        "csv": rows_to_csv_string(result.rows),
        "rows": result.row_count,
        "delimiter": result.delimiter,
        "date_format": result.date_format,
        "source": result.source,
        "output_name": result.output_name,
    }


@app.post("/merge", tags=["data"], summary="Merge CSV data")
async def merge_csv_endpoint(
    existing: UploadFile = File(...),
    new_files: List[UploadFile] = File(...),
):
    """
    Merge new raw CSV data into existing cleaned CSV.
    Returns merged CSV content + metadata.
    """
    existing_text = (await existing.read()).decode("utf-8-sig")
    new_texts = []
    for f in new_files:
        text = (await f.read()).decode("utf-8-sig")
        new_texts.append((f.filename, text))

    result = merge_csv(existing_text, new_texts)

    if result.error:
        raise HTTPException(status_code=400, detail=result.error)

    return {
        "csv": rows_to_csv_string(result.rows),
        "existing_count": result.existing_count,
        "new_count": result.new_count,
        "merged_count": result.merged_count,
        "new_dates": result.new_dates,
    }


@app.get("/fetch/{ticker}", tags=["analysis"], summary="Fetch from Yahoo Finance and analyze")
async def fetch_and_analyze(
    ticker: str,
    period: str = Query("1y", pattern="^(1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$"),
    interval: str = Query("1d", pattern="^(1d|1wk|1mo)$"),
    mode: str = Query("C"),
    direction: str = Query("BOTH"),
    position: str = Query("NO_POSITION"),
    modal: float = Query(10000000),
    risk: float = Query(2.0),
):
    """
    Fetch data from Yahoo Finance and run analysis.
    GET /fetch/BBRI?period=1y&mode=C
    """
    temp_dir = tempfile.mkdtemp()

    # Fetch data
    result = fetch_and_save(ticker, period=period, interval=interval, output_dir=temp_dir)
    if result.error:
        raise HTTPException(status_code=400, detail=result.error)

    path = os.path.join(temp_dir, result.output_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=500, detail="Fetched file not found")

    try:
        df = load_ohlcv(path)
        params = {
            "MODE": mode, "HORIZON": "SWING", "DIRECTION": direction,
            "POSITION": position, "MODAL": modal, "RISK": risk,
            "OUTPUT": "Chat", "IHSG": "None",
        }
        analysis = analyze_ticker(df, params)
        dec = analysis["decision"]

        return {
            "ticker": ticker,
            "bars": len(df),
            "decision": dec.decision,
            "direction": dec.decision_direction,
            "thesis": dec.thesis_state,
            "setup": f"{analysis['primary_setup'].type} {analysis['primary_setup'].status}",
            "tradeability": dec.tradeability_state,
            "entry": dec.entry,
            "sl": dec.sl,
            "tp1": dec.tp1,
            "rr": dec.rr_raw,
            "reason_codes": dec.reason_codes,
            "close": df["Close"].iloc[-1],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_api_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the API server."""
    import uvicorn
    _log.info("API server starting | host=%s port=%d", host, port)
    uvicorn.run(app, host=host, port=port)
