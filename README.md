# BEI Swing Engine v8.0

> Engine analisis teknikal deterministik untuk saham Indonesia (BEI/Bursa Efek Indonesia).
> Menghasilkan laporan swing-trading analysis dengan keputusan BUY/HOLD/SELL/WAIT/NO_SETUP.

[![CI](https://github.com/user/bei-swing-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/user/bei-swing-engine/actions)
[![Tests](https://img.shields.io/badge/tests-279%20passed-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-81%25-yellow)]()
[![Python](https://img.shields.io/badge/python-3.13%2B-blue)]()

---

## Daftar Isi

1. [Fitur Utama](#fitur-utama)
2. [Quick Start](#quick-start)
3. [Instalasi](#instalasi)
4. [Cara Pakai](#cara-pakai)
   - [CLI — Analisis Tunggal](#cli--analisis-tunggal)
   - [CLI — Screening Multi-Ticker](#cli--screening-multi-ticker)
   - [CLI — Backtest](#cli--backtest)
   - [CLI — Portfolio Backtest](#cli--portfolio-backtest)
   - [CLI — Optimizer](#cli--optimizer)
   - [CLI — Scheduler](#cli--scheduler)
   - [CSV Cleaner](#csv-cleaner)
   - [CSV Merger](#csv-merger)
   - [Web UI (Streamlit)](#web-ui-streamlit)
5. [Output Formats](#output-formats)
6. [MODE A/B/C](#mode-abc)
7. [Parameter Contract](#parameter-contract)
8. [Struktur Project](#struktur-project)
9. [Testing](#testing)
10. [FAQ](#faq)
11. [Disclaimer](#disclaimer)

---

## Fitur Utama

| Fitur | Deskripsi |
|---|---|
| **42-Row Indicator Contract** | 42 indikator teknikal, 6 kolom, 16 confluence factors dengan badge ✓/✗/○ |
| **6 Setup Types** | Breakout, Breakout+Retest, Pullback, Reversal, Continuation, Range |
| **Decision Engine** | G0-G6 gates, matriks NO_POSITION/EXISTING_POSITION/UNKNOWN, reason codes |
| **Risk Engine** | SL prioritas (struktural → S/R → 2×ATR), TP1/TP2, R/R ≥ 1.5, position sizing |
| **Backtest** | Walk-forward bar-by-bar, trade log, metrics (win rate, PF, expectancy, max DD) |
| **Portfolio Backtest** | Multi-ticker dengan alokasi modal (equal weight / risk-based), Sharpe ratio |
| **Walk-Forward Optimizer** | Grid search parameter, in-sample/out-of-sample validation |
| **CSV Cleaner** | Bersihkan CSV dari Yahoo/Investing/TradingView/RTI ke format standar |
| **CSV Merger** | Append data baru ke file cleaned yang sudah ada |
| **Yahoo Finance Fetcher** | Auto-download OHLCV untuk tickers BEI (BBRI.JK, ^JKSE, dll.) |
| **Scheduler** | Auto-fetch + analyze harian, notifikasi sinyal BUY/SELL via email |
| **Chart Patterns** | Double Top/Bottom, Head & Shoulders, Triangle, Wedge |
| **Web UI** | Streamlit: upload/fetch → analyze → report + charts interaktif |
| **Output** | Markdown, HTML, PDF (xhtml2pdf), Excel (openpyxl) |
| **Plotly Charts** | Equity curve, price + trade markers, drawdown, R-multiples |
| **Logging** | Structured logging dengan level (DEBUG/INFO/WARNING/ERROR) |

---

## Quick Start

```powershell
# 1. Clone / download project
cd C:\Opencode4

# 2. Buat virtual environment
python -m venv venv

# 3. Install dependencies
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# 4. Run analysis (contoh: TLKM)
.\venv\Scripts\python.exe run.py --data data-csv-yfinance-cleaned\TLKM.JK_cleaned.csv --params "MODE=A`nHORIZON=SWING`nDIRECTION=BOTH`nPOSITION=NO_POSITION`nMODAL=10000000`nRISK=2`nOUTPUT=Chat`nIHSG=None" --ihsg data-csv-yfinance-cleaned\IHSG-JKSE_cleaned.csv --output-dir output

# 5. Atau jalankan Web UI
.\venv\Scripts\python.exe -m streamlit run webui.py

# 6. Atau jalankan Chat AI
.\venv\Scripts\python.exe -m streamlit run chat_app.py

# 7. Atau jalankan dengan Docker
docker-compose up --build
```

---

## Instalasi

### Prasyarat
- **Python 3.11+** (direkomendasikan 3.13)
- **Windows** (PowerShell) — project ini di-develop dan diuji di Windows

### Dependencies

```
pandas, numpy, openpyxl, jinja2
xhtml2pdf, pypdf          # PDF generation
yfinance                  # Yahoo Finance fetcher
streamlit, plotly         # Web UI + charts
pytest, pytest-cov, flake8 # Testing + linting
```

### Install

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## Cara Pakai

### CLI — Analisis Tunggal

Analisis satu ticker dengan output Markdown:

```powershell
.\venv\Scripts\python.exe run.py `
  --data data-csv-yfinance-cleaned\TLKM.JK_cleaned.csv `
  --params "MODE=A`nHORIZON=SWING`nDIRECTION=BOTH`nPOSITION=NO_POSITION`nMODAL=10000000`nRISK=2`nOUTPUT=Chat`nIHSG=None" `
  --ihsg data-csv-yfinance-cleaned\IHSG-JKSE_cleaned.csv `
  --output-dir output
```

### CLI — Screening Multi-Ticker

Screening banyak ticker sekaligus (MODE=C, output ringkas):

```powershell
.\venv\Scripts\python.exe run.py `
  --glob --data "data-csv-yfinance-cleaned\*.JK_cleaned.csv" `
  --params "MODE=C`nHORIZON=SWING`nDIRECTION=BOTH`nPOSITION=NO_POSITION`nMODAL=10000000`nRISK=2`nOUTPUT=Chat`nIHSG=None" `
  --ihsg data-csv-yfinance-cleaned\IHSG-JKSE_cleaned.csv `
  --output-dir output
```

### CLI — Backtest

Walk-forward backtest untuk satu ticker:

```powershell
.\venv\Scripts\python.exe run.py `
  --data data-csv-yfinance-cleaned\TLKM.JK_cleaned.csv `
  --backtest --backtest-step 1 `
  --output-dir output
```

### CLI — Portfolio Backtest

Backtest multi-ticker dengan alokasi modal:

```powershell
.\venv\Scripts\python.exe run.py `
  --glob --data "data-csv-yfinance-cleaned\*.JK_cleaned.csv" `
  --portfolio --backtest-step 1 --allocation equal_weight `
  --params "MODE=A`nHORIZON=SWING`nDIRECTION=BOTH`nPOSITION=NO_POSITION`nMODAL=10000000`nRISK=2`nOUTPUT=Chat`nIHSG=None" `
  --output-dir output
```

### CLI — Optimizer

Walk-forward optimization parameter setup:

```powershell
.\venv\Scripts\python.exe optimizer_app.py `
  --data data-csv-yfinance-cleaned\TLKM.JK_cleaned.csv `
  --step 5 --windows 2 `
  --output-dir output
```

### CLI — Scheduler

Auto-fetch + analyze + notifikasi sinyal:

```powershell
# Run sekali
.\venv\Scripts\python.exe scheduler_app.py --tickers BBRI BBCA TLKM --period 1y --once

# Run recurring setiap 60 menit
.\venv\Scripts\python.exe scheduler_app.py --tickers BBRI BBCA --interval-min 60

# Dengan email notification
.\venv\Scripts\python.exe scheduler_app.py --tickers BBRI TLKM --email --smtp-host smtp.gmail.com --email-user user@gmail.com --email-pass apppass --email-to recipient@email.com
```

### CSV Cleaner

Bersihkan CSV mentah dari berbagai sumber:

```powershell
.\venv\Scripts\python.exe csv_cleaner_app.py BBRI-history.csv -o cleaned/
```

**Sumber yang didukung:** Yahoo Finance, Investing.com, TradingView, Google Finance, RTI Business, Stockbit, Custom CSV

**Proses cleaning:**
1. Auto-detect delimiter (`,` atau `;`)
2. Auto-detect column mapping (support alias multi-bahasa)
3. Auto-detect date format (ISO, MMM d yyyy, d MMM yyyy, DD/MM/YYYY, Unix timestamp, dll.)
4. Remove quotes, thousand separators, currency symbols
5. Sort ascending by date
6. Remove duplicates
7. Validate OHLC > 0 dan Low ≤ High
8. Output: `Date,Open,High,Low,Close,Volume`

### CSV Merger

Append data baru ke file cleaned yang sudah ada:

```powershell
.\venv\Scripts\python.exe csv_merger_app.py -e existing_cleaned.csv -n new_raw.csv -o merged/
```

### Web UI (Streamlit)

Antarmuka web interaktif:

```powershell
.\venv\Scripts\python.exe -m streamlit run webui.py
```

**5 Mode tersedia:**

| Mode | Fungsi |
|---|---|
| **Manual Upload** | Upload CSV → set parameter → run analysis → report + charts |
| **Yahoo Finance Fetch** | Input ticker + period → fetch → analyze → report |
| **Portfolio Backtest** | Multi-ticker backtest dengan charts (equity, drawdown, PnL) |
| **Cleaner Tool** | Upload raw CSV → clean → download |
| **Merger Tool** | Merge existing + new CSV → download |

---

## Output Formats

| `OUTPUT` | File | Format |
|---|---|---|
| Chat / Markdown | `.md` | Markdown report (default) |
| HTML | `.html` | HTML dengan tabel dan styling |
| PDF | `.pdf` | PDF dari HTML (xhtml2pdf + pypdf merge) |
| Excel | `.xlsx` | Spreadsheet dengan 42-row indicator table |

---

## MODE A/B/C

| MODE | Output |
|---|---|
| **A** | Full report: Executive Summary → Market Structure → Indicators (42 rows) → Setup → Trade Plan → Decision Trace → Disclaimer |
| **B** | Calc-only: Market Context, Structure, Indicators, Setup Status (tanpa decision/trade plan) |
| **C** | Screening: summary table only (Ticker, Thesis, Setup, Tradeability, Decision, Warnings) |

---

## Parameter Contract

```
MODE=A
HORIZON=SWING
DIRECTION=BOTH
POSITION=NO_POSITION
MODAL=10000000
RISK=2
OUTPUT=Chat
IHSG=None
```

| Parameter | Values | Default | Deskripsi |
|---|---|---|---|
| `MODE` | A / B / C | A | A=full, B=calc-only, C=screening |
| `HORIZON` | DAY / SWING / POSITION | SWING | DAY=1-5 hari, SWING=1-4 minggu, POSITION=>4 minggu |
| `DIRECTION` | LONG / SHORT / BOTH | BOTH | Arah trade yang diizinkan |
| `POSITION` | NO_POSITION / EXISTING_POSITION / UNKNOWN | UNKNOWN | Status posisi user |
| `MODAL` | angka (Rupiah) | 10000000 | Modal tersedia |
| `RISK` | angka (persen) | 2 | Risk percent per trade |
| `OUTPUT` | Chat / HTML / PDF / Excel | Chat | Format output |
| `IHSG` | None / uploaded | None | Data IHSG/JKSE diupload? |

**Shorthand:** `MODAL=10jt` = `MODAL=10000000`

---

## Struktur Project

```
C:\Opencode4\
├── BEI_Swing_Engine_v8.0_FINAL.md   # System prompt (sumber kebenaran)
├── run.py                            # Entry point CLI
├── webui.py                          # Streamlit Web UI
├── chat_app.py                       # Streamlit Chat AI interface
├── csv_cleaner_app.py                # Standalone CSV cleaner
├── csv_merger_app.py                 # Standalone CSV merger
├── scheduler_app.py                  # Standalone scheduler
├── optimizer_app.py                  # Standalone optimizer
├── api_server_app.py                 # Standalone REST API server
├── scheduler_config.json             # Scheduler config
├── requirements.txt
├── setup.cfg                         # flake8 config
├── Dockerfile                        # Docker image
├── docker-compose.yml                # Docker Compose services
├── .dockerignore                     # Docker ignore rules
├── .github/workflows/ci.yml          # GitHub Actions CI
├── AGENTS.md                         # Dokumentasi untuk coding agents
├── README.md                         # File ini
│
├── bei_swing_engine_v8/             # Engine package (21 modul + __init__)
│   ├── __init__.py
│   ├── api.py                        # REST API endpoints (FastAPI)
│   ├── backtest.py                   # Walk-forward backtest
│   ├── charts.py                     # Plotly visualization
│   ├── chat.py                       # Chat AI explainer
│   ├── cleaner.py                    # CSV cleaner
│   ├── cli.py                        # CLI interface
│   ├── data.py                       # Ingesti & validasi OHLCV
│   ├── decision.py                   # G0-G6 gates + decision matrices
│   ├── engine.py                     # Orkestrasi & multi-ticker
│   ├── fetcher.py                    # Yahoo Finance fetcher
│   ├── indicators.py                 # 42-row indicator contract
│   ├── logging_config.py             # Structured logging
│   ├── market_context.py             # IHSG regime
│   ├── merger.py                     # CSV merger
│   ├── optimizer.py                  # Walk-forward optimization
│   ├── output.py                     # Renderer MD/HTML/PDF/Excel
│   ├── patterns.py                   # Chart pattern detection
│   ├── portfolio.py                  # Portfolio backtest
│   ├── risk.py                       # Entry, SL, TP, R/R, position sizing
│   ├── scheduler.py                  # Auto-fetch + analyze scheduler
│   ├── setup.py                      # Deteksi 6 setup
│   └── structure.py                  # Swing, S/R, Fibonacci, BOS/CHoCH
│
├── tests/                            # 279 unit tests (30 file)
├── data-csv-yfinance-cleaned/        # Sample data (9 file)
└── output_test/                      # Sample output
```

---

## REST API

Jalankan API server:

```powershell
.\venv\Scripts\python.exe api_server_app.py --host 0.0.0.0 --port 8000
```

**Interactive API docs (Swagger UI):** http://localhost:8000/docs

**OpenAPI JSON schema:** http://localhost:8000/openapi.json

### Endpoints

| Method | Path | Tag | Description |
|---|---|---|---|
| GET | `/` | info | API info |
| GET | `/health` | info | Health check |
| POST | `/analyze` | analysis | Analyze uploaded CSV(s) |
| POST | `/screening` | analysis | Multi-ticker screening (MODE=C) |
| GET | `/fetch/{ticker}` | analysis | Fetch from Yahoo Finance and analyze |
| POST | `/backtest` | backtest | Walk-forward backtest |
| POST | `/portfolio` | backtest | Portfolio backtest |
| POST | `/clean` | data | Clean raw CSV |
| POST | `/merge` | data | Merge existing + new CSV |

### Examples

```bash
# Health check
curl http://localhost:8000/health

# Analyze CSV
curl -X POST http://localhost:8000/analyze -F "files=@TLKM.csv" -F "mode=A"

# Fetch and analyze from Yahoo Finance
curl "http://localhost:8000/fetch/BBRI?period=1y&mode=C"

# Multi-ticker screening
curl -X POST http://localhost:8000/screening -F "files=@BBRI.csv" -F "files=@TLKM.csv"
```

---

## Chat AI

Jalankan chat interface:

```powershell
.\venv\Scripts\python.exe -m streamlit run chat_app.py
```

Fitur:
- Chat dengan asisten analisis teknikal untuk saham Indonesia.
- Ketik ticker (contoh: `Analisis BBRI`) atau upload CSV.
- Screening multi-ticker (contoh: `Screening BBRI TLKM BBCA`).
- Penjelasan default pakai template deterministic (anti-hallucination).
- Toggle **LLM backend** di sidebar untuk menggunakan OpenAI API key — jika LLM gagal, otomatis fallback ke template.
- Engine Python selalu menghasilkan angka dan keputusan; chat AI hanya menjelaskan hasil.

---

## Docker

Jalankan seluruh stack dengan Docker Compose:

```powershell
# Build dan jalankan semua services
docker-compose up --build

# Jalankan service tertentu saja
docker-compose up webui    # Web UI di http://localhost:8501
docker-compose up chat     # Chat AI di http://localhost:8502
docker-compose up api      # REST API di http://localhost:8000
docker-compose up engine   # One-off analysis TLKM
```

**Services yang tersedia:**
| Service | Port | Deskripsi |
|---|---|---|
| `webui` | 8501 | Streamlit Web UI |
| `chat` | 8502 | Streamlit Chat AI |
| `api` | 8000 | FastAPI REST API |
| `engine` | — | CLI analysis one-off |

---

## Testing

```powershell
# Full test suite
.\venv\Scripts\python.exe -m pytest tests/ -v

# With coverage report
.\venv\Scripts\python.exe -m pytest tests/ --cov=bei_swing_engine_v8 --cov-report=term-missing

# HTML coverage report
.\venv\Scripts\python.exe -m pytest tests/ --cov=bei_swing_engine_v8 --cov-report=html

# Linting
.\venv\Scripts\python.exe -m flake8 bei_swing_engine_v8/ tests/ run.py webui.py chat_app.py csv_cleaner_app.py csv_merger_app.py scheduler_app.py api_server_app.py optimizer_app.py scripts/verify_final_compliance.py --count --statistics

# OpenAPI schema validation
.\venv\Scripts\python.exe -m pytest tests/test_api.py -k openapi -v
```

**Status:** 279 tests, all passing. Coverage: 81%. Linting: 0 errors.

---

## FAQ

### Q: Apakah engine ini memberikan rekomendasi investasi?
**Tidak.** Engine ini menghasilkan output analitis (BUY/SELL/WAIT) yang bersifat edukatif. Keputusan investasi dan risiko sepenuhnya tanggung jawab pengguna. Lihat [Disclaimer](#disclaimer).

### Q: Berapa banyak data yang dibutuhkan?
- Minimum: **20 bar** untuk analisis dasar
- Disarankan: **200+ bar** untuk setup TRIGGERED (SMA200 cap)
- Untuk optimasi: **500+ bar** per window

### Q: Bisakah pakai data dari sumber selain Yahoo Finance?
**Ya.** Gunakan CSV Cleaner untuk membersihkan CSV dari Investing.com, TradingView, RTI, atau sumber lain. Selama output formatnya `Date,Open,High,Low,Close,Volume`, engine bisa langsung pakai.

### Q: Bagaimana cara update data?
1. Download CSV baru dari Yahoo Finance (atau fetch via fetcher)
2. Gunakan CSV Merger untuk append ke file cleaned existing
3. Run engine dengan file merged

### Q: Apakah IHSG (market regime) wajib?
**Tidak.** IHSG adalah context opsional. Jika tidak diupload, Market Regime = `N/A — no IHSG/JKSE data uploaded`. Keputusan ticker tidak terpengaruh.

### Q: Parameter apa yang di-lock?
Locked parameters (tidak boleh diubah tanpa audit baru):
- Swing fractal N = 8
- ATR fallback multiplier = 2.0
- Minimum R/R = 1.5
- S/R tolerance = max(0.5% × Close, 0.5 × ATR14)
- Pullback zone tolerance = 0.5 × ATR14
- Breakout approach tolerance = 0.75 × ATR14

Lihat `BEI_Swing_Engine_v8.0_FINAL.md` section 5 untuk detail.

### Q: Bisakah engine dipakai untuk saham non-BEI?
Engine ini dirancang untuk BEI (ticker `.JK`), tapi secara teknis bisa dipakai untuk saham apapun selama data OHLCV tersedia. Namun parameter dan kontrak mungkin perlu penyesuaian.

### Q: Bagaimana cara scheduling otomatis?
Gunakan Scheduler:
```powershell
.\venv\Scripts\python.exe scheduler_app.py --create-config
# Edit scheduler_config.json
.\venv\Scripts\python.exe scheduler_app.py --config scheduler_config.json --interval-min 1440
```
Atau gunakan Windows Task Scheduler untuk menjalankan `scheduler_app.py --once` setiap hari.

---

## Disclaimer

> Analisa ini bersifat edukatif untuk pembelajaran analisis teknikal, BUKAN rekomendasi investasi atau ajakan untuk membeli/menjual efek. Keputusan investasi dan risiko sepenuhnya menjadi tanggung jawab pengguna. Hasil masa lalu tidak menjamin hasil di masa depan.

---

## License

Project ini dikembangkan untuk pembelajaran analisis teknikal. Bebas dipakai dan dimodifikasi untuk keperluan edukatif.

---

**BEI Swing Engine v8.0** — Deterministic, evidence-based swing trading analysis for Indonesian stocks.
