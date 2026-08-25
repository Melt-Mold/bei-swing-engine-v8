# AGENTS.md — BEI Swing Engine v8.0

> Panduan untuk coding agents yang mengerjakan project ini. Berisi struktur, build steps, testing, dan konvensi.

## Project Overview

**BEI Swing Engine v8.0** adalah engine analisis teknikal deterministik untuk saham Indonesia (BEI/Bursa Efek Indonesia). Engine menerima data OHLCV CSV dan menghasilkan laporan swing-trading analysis dengan keputusan BUY/HOLD/SELL/WAIT/NO_SETUP.

**System prompt final:** `BEI_Swing_Engine_v8.0_FINAL.md` — sumber kebenaran tunggal untuk semua kontrak (42-row indicator, locked parameters, decision matrix, setup contracts).

## Quick Start

```powershell
# Setup virtual environment
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# Run single-ticker analysis
.\venv\Scripts\python.exe run.py --data data-csv-yfinance-cleaned\TLKM.JK_cleaned.csv --params "MODE=A`nHORIZON=SWING`nDIRECTION=BOTH`nPOSITION=NO_POSITION`nMODAL=10000000`nRISK=2`nOUTPUT=Chat`nIHSG=None" --ihsg data-csv-yfinance-cleaned\IHSG-JKSE_cleaned.csv --output-dir output

# Run multi-ticker screening
.\venv\Scripts\python.exe run.py --glob --data "data-csv-yfinance-cleaned\*.JK_cleaned.csv" --params "MODE=C`nHORIZON=SWING`nDIRECTION=BOTH`nPOSITION=NO_POSITION`nMODAL=10000000`nRISK=2`nOUTPUT=Chat`nIHSG=None" --output-dir output

# Run backtest
.\venv\Scripts\python.exe run.py --data data-csv-yfinance-cleaned\TLKM.JK_cleaned.csv --backtest --output-dir output

# Run Web UI
.\venv\Scripts\python.exe -m streamlit run webui.py

# Run Chat AI
.\venv\Scripts\python.exe -m streamlit run chat_app.py

# Run tests
.\venv\Scripts\python.exe -m pytest tests/ -v
```

## Project Structure

```
C:\Opencode4\
├── BEI_Swing_Engine_v8.0_FINAL.md   # System prompt final (sumber kebenaran)
├── run.py                            # Entry point CLI
├── webui.py                          # Streamlit Web UI (4 mode)
├── chat_app.py                       # Streamlit Chat AI interface
├── csv_cleaner_app.py                # Standalone CSV cleaner CLI
├── csv_merger_app.py                 # Standalone CSV merger CLI
├── scheduler_app.py                  # Standalone scheduler CLI (auto-fetch + notify)
├── scheduler_config.json             # Scheduler default config
├── optimizer_app.py                  # Standalone walk-forward optimizer CLI
├── api_server_app.py                 # Standalone REST API server CLI
├── requirements.txt                  # Dependencies
├── AGENTS.md                         # File ini
│
├── scripts/                          # Utility scripts
│   └── verify_final_compliance.py    # FINAL.md contract compliance checker
│
├── bei_swing_engine_v8/             # Engine package (21 modul + __init__)
│   ├── __init__.py
│   ├── api.py                        # REST API endpoints (FastAPI)
│   ├── backtest.py                   # Walk-forward backtest
│   ├── charts.py                     # Plotly visualization
│   ├── chat.py                       # Chat AI explainer (deterministic templates)
│   ├── cleaner.py                    # CSV cleaner (port dari TA V2.15)
│   ├── cli.py                        # Command-line interface
│   ├── data.py                       # Ingesti & validasi OHLCV
│   ├── decision.py                   # G0-G6 gates + decision matrices
│   ├── engine.py                     # Orkestrasi & multi-ticker
│   ├── fetcher.py                    # Yahoo Finance fetcher
│   ├── indicators.py                 # 42-row indicator contract
│   ├── logging_config.py             # Structured logging
│   ├── market_context.py             # IHSG regime (opsional)
│   ├── merger.py                     # CSV merger (append new data)
│   ├── optimizer.py                  # Walk-forward parameter optimizer
│   ├── output.py                     # Renderer MD/HTML/PDF/Excel
│   ├── patterns.py                   # Chart pattern detection
│   ├── portfolio.py                  # Multi-ticker portfolio backtest
│   ├── risk.py                       # Entry, SL, TP, R/R, position sizing
│   ├── scheduler.py                  # Auto-fetch + analyze scheduler
│   ├── setup.py                      # Deteksi setup (6 tipe)
│   └── structure.py                  # Swing, S/R, Fibonacci, BOS/CHoCH
│
├── tests/                            # Unit tests (255 test, 29 file)
│   ├── __init__.py
│   ├── conftest.py                   # Shared fixtures
│   ├── test_api.py
│   ├── test_backtest.py
│   ├── test_backtest_extended.py
│   ├── test_charts.py
│   ├── test_cleaner.py
│   ├── test_cleaner_extended.py
│   ├── test_data.py
│   ├── test_decision.py
│   ├── test_decision_extended.py
│   ├── test_end_to_end.py
│   ├── test_engine_extended.py
│   ├── test_fetcher.py
│   ├── test_indicators.py
│   ├── test_market_context.py
│   ├── test_merger.py
│   ├── test_merger_extended.py
│   ├── test_optimizer.py
│   ├── test_output.py
│   ├── test_patterns.py
│   ├── test_portfolio.py
│   ├── test_risk.py
│   ├── test_risk_extended.py
│   ├── test_scheduler.py
│   ├── test_setup.py
│   └── test_setup_extended.py
│
├── data-csv-yfinance-cleaned/        # Sample data (9 file)
│   ├── BBCA.JK_cleaned.csv
│   ├── BBRI.JK_cleaned.csv
│   ├── BMRI.JK_cleaned.csv
│   ├── HRUM.JK_cleaned.csv
│   ├── ICBP.JK_cleaned.csv
│   ├── INDF.JK_cleaned.csv
│   ├── PTRO.JK_cleaned.csv
│   ├── TLKM.JK_cleaned.csv
│   └── IHSG-JKSE_cleaned.csv
│
└── output_test/                      # Sample output
    ├── BEI_Swing_Engine_Report.md
    ├── BEI_Swing_Engine_Report.html
    ├── BEI_Swing_Engine_Report.pdf
    ├── BEI_Swing_Engine_Report.xlsx
    ├── BEI_Swing_Engine_Screening.md
    ├── BEI_Backtest_Report.md
    └── engine.log
```

## Architecture

### Data Flow

```
Manual Upload CSV ──────────────────┐
                                    ↓
Yahoo Finance Fetch → Cleaner ──────→ Engine v8.0 → Report (MD/HTML/PDF/Excel)
                                    ↑               ↓
Existing Cleaned + New Raw → Merger ┘          Backtest (walk-forward) → Charts
```

### Engine Pipeline (per-ticker)

```
load_ohlcv() → validate_data() → compute_all_indicators() → analyze_structure()
    → detect_setups() → apply_sma200_cap() → select_primary_setup()
    → assess_tradeability() → run_decision_engine() → render_report()
```

### Key Modules

| Modul | Tanggung Jawab |
|---|---|---|
| `data.py` | Load CSV, extract ticker, validate sufficiency |
| `indicators.py` | Semua indikator teknikal (EMA, RSI, MACD, ADX, ATR, BB, OBV, CMF, Ichimoku, dll.) |
| `structure.py` | Swing detection (N=8 fractal), S/R clusters, Fibonacci, BOS/CHoCH |
| `setup.py` | Deteksi 6 setup: Breakout, Breakout+Retest, Pullback, Reversal, Continuation, Range |
| `risk.py` | Entry contract, SL priority (struktural → S/R → 2×ATR), TP1/TP2, R/R ≥ 1.5, position sizing |
| `decision.py` | G0-G6 gate pipeline, NO_POSITION/EXISTING_POSITION/UNKNOWN matrices, reason codes |
| `output.py` | Renderer: `render_markdown()`, `render_calc_only_markdown()`, `render_screening_summary()`, `render_html_single()`, `render_pdf_single()`, `render_excel_single()` |
| `engine.py` | Orkestrasi: `analyze_ticker()`, `run_analysis()`, `parse_params()`, parallel processing |
| `backtest.py` | Walk-forward: `run_backtest()`, `generate_trades()`, `compute_metrics()`, `validate_as_of_consistency()` |
| `cleaner.py` | `clean_csv_text()`, `clean_csv_file()` — porting dari SwingFlow v7.0 HTML |
| `merger.py` | `merge_csv()`, `merge_csv_files()` — append data baru ke existing |
| `fetcher.py` | `fetch_yfinance()`, `fetch_and_save()` — download dari Yahoo Finance |
| `charts.py` | `plot_equity_curve()`, `plot_price_with_trades()`, `plot_drawdown()`, `plot_r_multiples()` |
| `chat.py` | Deterministic chat explainer using FINAL.md terminology |
| `patterns.py` | Double Top/Bottom, Head & Shoulders, Triangle, Wedge detection |
| `portfolio.py` | Multi-ticker portfolio backtest dengan equal-weight / risk-based allocation |
| `optimizer.py` | Walk-forward parameter grid search & in-sample/out-of-sample validation |
| `scheduler.py` | Auto-fetch + analyze harian, notifikasi sinyal BUY/SELL |
| `api.py` | REST API endpoints (FastAPI) untuk analyze, screen, clean, merge, backtest |
| `cli.py` | Command-line interface untuk run.py |
| `logging_config.py` | Structured logging factory |
| `market_context.py` | IHSG regime detection (opsional context only) |

## Build & Test

### Dependencies

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Key dependencies: `pandas`, `numpy`, `openpyxl`, `jinja2`, `xhtml2pdf`, `pypdf`, `yfinance`, `streamlit`, `plotly`, `fastapi`, `uvicorn`, `httpx`, `pytest`, `pytest-cov`, `flake8`.

### Run Tests

```powershell
# Full suite
.\venv\Scripts\python.exe -m pytest tests/ -v

# Specific module
.\venv\Scripts\python.exe -m pytest tests/test_indicators.py -v

# With coverage
.\venv\Scripts\python.exe -m pytest tests/ --cov=bei_swing_engine_v8 --cov-report=term-missing

# Linting
.\venv\Scripts\python.exe -m flake8 bei_swing_engine_v8/ tests/ run.py webui.py chat_app.py csv_cleaner_app.py csv_merger_app.py scheduler_app.py api_server_app.py optimizer_app.py scripts/verify_final_compliance.py --count --statistics

# FINAL.md compliance
.\venv\Scripts\python.exe scripts/verify_final_compliance.py --locked
.\venv\Scripts\python.exe scripts/verify_final_compliance.py --data data-csv-yfinance-cleaned/TLKM.JK_cleaned.csv --ihsg data-csv-yfinance-cleaned/IHSG-JKSE_cleaned.csv
```

**Current status:** 255 tests, all passing. Coverage: 81% (run `pytest --cov` for report). Linting: 0 errors with flake8.

### CI/CD

GitHub Actions workflow di `.github/workflows/ci.yml` menjalankan:
- Test suite pada Python 3.11, 3.12, 3.13 (Windows)
- Coverage report (XML + HTML artifact)
- flake8 linting pada semua source files
- `scripts/verify_final_compliance.py` — locked-parameter + end-to-end compliance check

## Coding Conventions

### Style
- Python 3.13+.
- 4-space indentation.
- Type hints di signature fungsi publik.
- Dataclasses untuk structured data (`Setup`, `Decision`, `Trade`, `BacktestResult`, dll.).
- Docstrings pendek di setiap fungsi publik.

### Anti-Fabrication Protocol (MANDATORY)
- Setiap angka di output HARUS berasal dari CSV atau formula deterministik.
- Jangan pernah estimate, guess, atau fabricate nilai.
- Jika nilai tidak dapat dihitung, output `N/A` dengan alasan deterministik.
- Lihat section 0 di `BEI_Swing_Engine_v8.0_FINAL.md` untuk detail.

### Locked Parameters
Parameter berikut di-lock di `BEI_Swing_Engine_v8.0_FINAL.md` section 5. **Jangan ubah tanpa audit baru:**
- Swing fractal N = 8
- ATR fallback multiplier = 2.0
- Minimum R/R = 1.5
- S/R tolerance = max(0.5% × Close, 0.5 × ATR14)
- S/R minimum touches = 2
- Range minimum duration = 20 bars
- Breakout approach tolerance = 0.75 × ATR14
- Pullback zone tolerance = 0.5 × ATR14

### 42-Row Indicator Contract
- Tepat 42 baris, 6 kolom: `Category, Indicator, Value, Signal, Interpretation, Standard / Reference`.
- Tepat 16 confluence factors dengan badge (✓/✗/○/⚡Div).
- Lihat `BEI_Swing_Engine_v8.0_FINAL.md` section 7 untuk daftar lengkap.

### Decision States
- Primary: `BUY`, `HOLD`, `SELL`
- Operational: `WAIT`, `NO_SETUP`, `INSUFFICIENT_DATA`
- Reason codes wajib untuk setiap decision (lihat section 8.8 di FINAL.md).

### Output Formats
| `OUTPUT` | File | Renderer |
|---|---|---|
| Chat/Markdown | `.md` | `render_markdown()` |
| HTML | `.html` | `render_html_single()` |
| PDF | `.pdf` | `render_pdf_single()` (xhtml2pdf + pypdf merge) |
| Excel | `.xlsx` | `render_excel_single()` (openpyxl) |

### MODE
| MODE | Output |
|---|---|
| A | Full report (Executive Summary → Decision Trace → Disclaimer) |
| B | Calc-only (Market Context, Structure, Indicators, Setup Status — tanpa decision/trade plan) |
| C | Screening summary table only |

### Logging
- Gunakan `get_logger("module_name")` dari `logging_config.py`.
- CLI: `--log-level` (DEBUG/INFO/WARNING/ERROR), `--log-file`.
- Format: `timestamp | LEVEL | module | message`.

### Performance
- Backtest menggunakan precomputed indicators (`precomputed` parameter di `analyze_ticker()`).
- `build_output_rows=False` di backtest loop untuk skip 42-row table construction.
- Early exit di `detect_setups()` ketika TRIGGERED setup ditemukan.
- Parallel multi-ticker: `--parallel` flag (ProcessPoolExecutor).

## Key Design Decisions

1. **No numerical scoring** — Confluence adalah cross-dimensional evidence, bukan point total.
2. **Market Regime (IHSG) is context only** — tidak dapat override stock-specific decision.
3. **SMA200 sufficiency cap** — jika < 200 bars, setup maksimal CONFIRMED (tidak TRIGGERED), tradeability UNTRADEABLE.
4. **Historical as-of analysis** — hanya data ≤ cutoff D, no look-ahead. `Engine(truncated at D) == Engine(complete data as-of D)`.
5. **SL priority** — Structural invalidation → S/R level → ATR fallback (2.0×ATR14). Jangan pilih SL arbitrary demi R/R favorable.

## Pre-Commit Checklist

Sebelum commit perubahan, jalankan:

1. **Tests**
   ```powershell
   .\venv\Scripts\python.exe -m pytest tests/ -q
   ```

2. **Linting**
   ```powershell
   .\venv\Scripts\python.exe -m flake8 bei_swing_engine_v8/ tests/ run.py webui.py chat_app.py csv_cleaner_app.py csv_merger_app.py scheduler_app.py api_server_app.py optimizer_app.py scripts/verify_final_compliance.py --count --statistics
   ```

3. **FINAL.md Compliance**
   ```powershell
   .\venv\Scripts\python.exe scripts/verify_final_compliance.py --locked
   .\venv\Scripts\python.exe scripts/verify_final_compliance.py --data data-csv-yfinance-cleaned/TLKM.JK_cleaned.csv --ihsg data-csv-yfinance-cleaned/IHSG-JKSE_cleaned.csv
   .\venv\Scripts\python.exe scripts/verify_final_compliance.py --data data-csv-yfinance-cleaned/BBRI.JK_cleaned.csv --ihsg data-csv-yfinance-cleaned/IHSG-JKSE_cleaned.csv
   ```

4. **Manual review** (jika mengubah output/report)
   - Apakah 42-row table masih 6 kolom?
   - Apakah badge count tepat 16?
   - Apakah decision memiliki reason code valid?
   - Apakah disclaimer ada di Mode A?

## Files to Update When Modifying

| Jika mengubah... | Update juga... |
|---|---|---|
| `indicators.py` | `tests/test_indicators.py`, `output.py` (42-row table) |
| `setup.py` | `tests/test_setup.py`, `engine.py` (detect_setups call) |
| `decision.py` | `tests/test_decision.py`, reason codes di FINAL.md section 8.8 |
| `output.py` | `tests/test_output.py`, pre-output checklist di FINAL.md section 12 |
| `structure.py` | `tests/`, `setup.py` (filter_as_of di backtest) |
| `backtest.py` | `tests/test_backtest.py`, `tests/test_backtest_extended.py` |
| `cleaner.py` | `tests/test_cleaner.py`, `tests/test_cleaner_extended.py` |
| `merger.py` | `tests/test_merger.py`, `tests/test_merger_extended.py` |
| `risk.py` | `tests/test_risk.py`, `tests/test_risk_extended.py` |
| `engine.py` | `tests/test_engine_extended.py`, `tests/test_end_to_end.py` |
| `fetcher.py` | `tests/test_fetcher.py` |
| `market_context.py` | `tests/test_market_context.py` |
| `optimizer.py` | `tests/test_optimizer.py` |
| `patterns.py` | `tests/test_patterns.py` |
| `portfolio.py` | `tests/test_portfolio.py` |
| `scheduler.py` | `tests/test_scheduler.py` |
| `api.py` | `tests/test_api.py` |
| `BEI_Swing_Engine_v8.0_FINAL.md` | Modul terkait + `AGENTS.md` ini |

## Common Tasks

### Tambah indikator baru
1. Tambah fungsi di `indicators.py`.
2. Tambah ke `compute_all_indicators()` return dict.
3. Tambah row di `build_indicator_table()` di `output.py` (jangan melebihi 42 rows).
4. Tambah test di `tests/test_indicators.py`.

### Tambah setup type baru
1. Tambah fungsi `_detect_xxx()` di `setup.py`.
2. Tambah ke `detect_setups()` detector list (urutan = precedence).
3. Update `SETUP_ORDER` dan `SETUP_STATUS_ORDER`.
4. Tambah test di `tests/test_setup.py`.

### Ubah parameter locked
1. **JANGAN** tanpa konsultasi `BEI_Swing_Engine_v8.0_FINAL.md` section 5.
2. Jika diubah, update FINAL.md dan dokumentasikan alasannya.
3. Run full test suite untuk verifikasi.

### Tambah output format
1. Tambah `render_xxx()` di `output.py`.
2. Tambah branch di `engine.py` `run_analysis()` file writing section.
3. Tambah `--output` option di `cli.py` jika perlu.
4. Tambah test di `tests/test_output.py`.
