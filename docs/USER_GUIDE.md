# BEI Swing Engine v8.0 — User Guide

> Panduan lengkap untuk menggunakan BEI Swing Engine: CLI, Web UI, Chat AI, REST API, dan Scheduler.

## Daftar Isi

1. [Instalasi](#1-instalasi)
2. [Memahami Parameter](#2-memahami-parameter)
3. [CLI — Analisis Tunggal](#3-cli--analisis-tunggal)
4. [CLI — Screening Multi-Ticker](#4-cli--screening-multi-ticker)
5. [CLI — Backtest](#5-cli--backtest)
6. [CLI — Portfolio Backtest](#6-cli--portfolio-backtest)
7. [Web UI (Streamlit)](#7-web-ui-streamlit)
8. [Chat AI](#8-chat-ai)
9. [REST API](#9-rest-api)
10. [Scheduler Otomatis](#10-scheduler-otomatis)
11. [Memahami Laporan](#11-memahami-laporan)
12. [Output Formats](#12-output-formats)
13. [CSV Cleaner & Merger](#13-csv-cleaner--merger)
14. [FAQ](#14-faq)

---

## 1. Instalasi

### Prasyarat
- Python 3.11+ (direkomendasikan 3.13)
- Windows (PowerShell)

### Langkah Instalasi

```powershell
# 1. Clone atau download project
cd C:\Opencode4

# 2. Buat virtual environment
python -m venv venv

# 3. Install dependencies
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# 4. Test instalasi
.\venv\Scripts\python.exe -m pytest tests/ -q
```

### Verifikasi
```powershell
.\venv\Scripts\python.exe run.py --help
```

---

## 2. Memahami Parameter

Engine menerima parameter dalam format key-value:

| Parameter | Values | Default | Deskripsi |
|---|---|---|---|
| `MODE` | A / B / C | A | A=full analysis, B=calc-only, C=screening |
| `HORIZON` | DAY / SWING / POSITION | SWING | DAY=1-5 hari, SWING=1-4 minggu, POSITION=>4 minggu |
| `DIRECTION` | LONG / SHORT / BOTH | BOTH | Arah trade yang diizinkan |
| `POSITION` | NO_POSITION / EXISTING_POSITION / UNKNOWN | UNKNOWN | Status posisi Anda |
| `MODAL` | angka (Rupiah) | 10000000 | Modal tersedia |
| `RISK` | angka (persen) | 2 | Risk per trade dalam persen |
| `OUTPUT` | Chat / HTML / PDF / Excel | Chat | Format output |
| `IHSG` | None / uploaded | None | Apakah data IHSG diupload? |

### Shorthand
- `MODAL=10jt` = `MODAL=10000000`
- `MODAL=5jt` = `MODAL=5000000`

### MODE Penjelasan

| MODE | Isi Laporan | Cocok Untuk |
|---|---|---|
| **A** | Executive Summary, Market Context, Structure, Indicators (42 rows), Setup, Trade Plan, Decision Trace, Disclaimer | Analisis lengkap satu ticker |
| **B** | Market Context, Structure, Indicators, Setup Status (tanpa decision/trade plan) | Calc-only, riset tanpa rekomendasi |
| **C** | Screening summary table saja | Bandingkan banyak ticker sekaligus |

---

## 3. CLI — Analisis Tunggal

Analisis satu ticker dengan laporan lengkap (Mode A).

```powershell
.\venv\Scripts\python.exe run.py `
  --data data-csv-yfinance-cleaned\TLKM.JK_cleaned.csv `
  --params "MODE=A`nHORIZON=SWING`nDIRECTION=BOTH`nPOSITION=NO_POSITION`nMODAL=10000000`nRISK=2`nOUTPUT=Chat`nIHSG=None" `
  --ihsg data-csv-yfinance-cleaned\IHSG-JKSE_cleaned.csv `
  --output-dir output
```

### Parameter Penting
- `--data`: Path ke CSV file (format: Date,Open,High,Low,Close,Volume)
- `--params`: Parameter key-value dipisah dengan `` `n `` (newline)
- `--ihsg`: Path ke IHSG/JKSE CSV (opsional)
- `--output-dir`: Directory untuk output files

### Output
File `BEI_Swing_Engine_Report.md` diisi di `output/` directory.

### Contoh dengan Mode B (Calc-Only)
```powershell
.\venv\Scripts\python.exe run.py `
  --data data-csv-yfinance-cleaned\BBRI.JK_cleaned.csv `
  --params "MODE=B`nHORIZON=SWING`nDIRECTION=BOTH`nPOSITION=NO_POSITION`nMODAL=10000000`nRISK=2`nOUTPUT=Chat`nIHSG=None"
```

### Contoh dengan Output HTML
```powershell
.\venv\Scripts\python.exe run.py `
  --data data-csv-yfinance-cleaned\TLKM.JK_cleaned.csv `
  --params "MODE=A`nHORIZON=SWING`nDIRECTION=BOTH`nPOSITION=NO_POSITION`nMODAL=10000000`nRISK=2`nOUTPUT=HTML`nIHSG=None" `
  --output-dir output
```

---

## 4. CLI — Screening Multi-Ticker

Screening banyak ticker sekaligus dengan Mode C.

```powershell
.\venv\Scripts\python.exe run.py `
  --glob `
  --data "data-csv-yfinance-cleaned\*.JK_cleaned.csv" `
  --params "MODE=C`nHORIZON=SWING`nDIRECTION=BOTH`nPOSITION=NO_POSITION`nMODAL=10000000`nRISK=2`nOUTPUT=Chat`nIHSG=None" `
  --output-dir output
```

### Parallel Processing
Tambahkan `--parallel` untuk memproses multiple tickers secara paralel:
```powershell
.\venv\Scripts\python.exe run.py --glob --data "data-csv-yfinance-cleaned\*.JK_cleaned.csv" --params "MODE=C..." --parallel --output-dir output
```

### Output
File `BEI_Swing_Engine_Screening.md` berisi table summary semua ticker.

---

## 5. CLI — Backtest

Walk-forward backtest pada satu ticker.

```powershell
.\venv\Scripts\python.exe run.py `
  --data data-csv-yfinance-cleaned\TLKM.JK_cleaned.csv `
  --backtest `
  --output-dir output
```

### Custom Backtest Step
```powershell
.\venv\Scripts\python.exe run.py `
  --data data-csv-yfinance-cleaned\TLKM.JK_cleaned.csv `
  --backtest `
  --backtest-step 5 `
  --output-dir output
```

- `--backtest-step 1`: Analisis setiap bar (paling detail, paling lambat)
- `--backtest-step 5`: Analisis setiap 5 bar (lebih cepat, kurang detail)

### Output
File `BEI_Backtest_Report.md` berisi:
- Equity curve
- Trade log
- Metrics: win rate, profit factor, expectancy, max drawdown

---

## 6. CLI — Portfolio Backtest

Backtest multiple ticker dengan alokasi modal.

```powershell
.\venv\Scripts\python.exe run.py `
  --glob `
  --data "data-csv-yfinance-cleaned\*.JK_cleaned.csv" `
  --portfolio `
  --allocation equal_weight `
  --output-dir output
```

### Allocation Modes
- `equal_weight`: Modal dibagi rata ke setiap ticker
- `risk_based`: Modal dialokasikan berdasarkan risk per ticker

---

## 7. Web UI (Streamlit)

Interface grafis untuk analisis tanpa command line.

```powershell
.\venv\Scripts\python.exe -m streamlit run webui.py
```

Buka browser ke `http://localhost:8501`.

### Mode Input
1. **Manual Upload**: Upload CSV saham
2. **Yahoo Finance Fetch**: Download data langsung dari Yahoo Finance
3. **Portfolio Backtest**: Backtest multiple ticker
4. **Cleaner Tool**: Bersihkan CSV dari berbagai sumber
5. **Merger Tool**: Gabungkan data baru ke CSV existing

### Parameter di Sidebar
- MODE (A/B/C)
- HORIZON (DAY/SWING/POSITION)
- DIRECTION (LONG/SHORT/BOTH)
- POSITION (NO_POSITION/EXISTING_POSITION/UNKNOWN)
- MODAL (Rp)
- RISK (%)

---

## 8. Chat AI

Interface chat untuk analisis saham interaktif.

```powershell
.\venv\Scripts\python.exe -m streamlit run chat_app.py
```

Buka browser ke `http://localhost:8501`.

### Perintah yang Didukung

#### Analisis Ticker Tunggal
Ketik di chat:
```
Analisis BBRI
Cek TLKM
Analisa BBCA
```

#### Screening Multi-Ticker
```
Screening BBRI TLKM BBCA
Saring saham BMRI ICBP
Filter PTRO HRUM
```

#### Upload CSV
Klik tombol upload di chat area, pilih file CSV.

#### Pertanyaan Umum
```
Jelaskan reason code
Apa saja setup yang dideteksi?
Apa itu 42-row indicator contract?
Apa parameter yang di-lock?
```

### LLM Backend (Opsional)
Aktifkan di sidebar:
1. Toggle "Gunakan LLM explanation"
2. Masukkan OpenAI API Key
3. (Opsional) Ubah model atau base URL

Jika LLM gagal, otomatis fallback ke template deterministic.

---

## 9. REST API

REST API server untuk integrasi sistem.

```powershell
.\venv\Scripts\python.exe api_server_app.py --host 0.0.0.0 --port 8000
```

### Interactive Docs
- **Swagger UI:** http://localhost:8000/docs
- **OpenAPI JSON:** http://localhost:8000/openapi.json

### Endpoints

| Method | Path | Deskripsi |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/analyze` | Analyze uploaded CSV(s) |
| POST | `/screening` | Multi-ticker screening |
| GET | `/fetch/{ticker}` | Fetch dari Yahoo Finance + analyze |
| POST | `/backtest` | Walk-forward backtest |
| POST | `/portfolio` | Portfolio backtest |
| POST | `/clean` | Clean raw CSV |
| POST | `/merge` | Merge existing + new CSV |

### Contoh: Analyze CSV
```bash
curl -X POST http://localhost:8000/analyze \
  -F "files=@TLKM.csv" \
  -F "mode=A" \
  -F "modal=10000000" \
  -F "risk=2.0"
```

### Contoh: Fetch dari Yahoo Finance
```bash
curl "http://localhost:8000/fetch/BBRI?period=1y&mode=C"
```

### Contoh: Multi-Ticker Screening
```bash
curl -X POST http://localhost:8000/screening \
  -F "files=@BBRI.csv" \
  -F "files=@TLKM.csv" \
  -F "files=@BBCA.csv"
```

---

## 10. Scheduler Otomatis

Auto-fetch data, analyze, dan kirim notifikasi sinyal BUY/SELL.

### Run Once (Sekali)
```powershell
.\venv\Scripts\python.exe scheduler_app.py `
  --tickers BBRI BBCA TLKM `
  --period 1y `
  --once
```

### Run Recurring (Berulang)
```powershell
.\venv\Scripts\python.exe scheduler_app.py `
  --tickers BBRI BBCA `
  --interval-min 60
```
Berjalan setiap 60 menit sampai dihentikan (Ctrl+C).

### Config File
```powershell
# Buat config default
.\venv\Scripts\python.exe scheduler_app.py --create-config

# Edit scheduler_config.json sesuai kebutuhan
# Jalankan dengan config
.\venv\Scripts\python.exe scheduler_app.py --config scheduler_config.json
```

### Notifikasi

#### Email
```powershell
.\venv\Scripts\python.exe scheduler_app.py `
  --tickers BBRI TLKM --once `
  --email `
  --smtp-host smtp.gmail.com `
  --email-user user@gmail.com `
  --email-pass your_app_password `
  --email-to recipient@email.com
```

#### Telegram
```powershell
.\venv\Scripts\python.exe scheduler_app.py `
  --tickers BBRI TLKM --once `
  --telegram `
  --telegram-token 123456:ABC-DEF `
  --telegram-chat 987654321
```

#### Webhook (Discord/Slack)
```powershell
.\venv\Scripts\python.exe scheduler_app.py `
  --tickers BBRI TLKM --once `
  --webhook `
  --webhook-url https://hooks.slack.com/services/...
```

### Cron Harian (Windows Task Scheduler)
```powershell
schtasks /create /tn "BEI_Swing_Scheduler" /tr "C:\Opencode4\venv\Scripts\python.exe C:\Opencode4\scheduler_app.py --config C:\Opencode4\scheduler_config.json --once" /sc daily /st 09:00
```

### Output Files
Scheduler menulis ke `output/`:
- `signals_YYYY-MM-DD.json` — alerts terstruktur
- `signals_YYYY-MM-DD.md` — laporan readable

---

## 11. Memahami Laporan

### Struktur Laporan Mode A

| Section | Isi |
|---|---|
| 1. Executive Summary | Keputusan (BUY/HOLD/SELL/WAIT), thesis, setup, trade plan |
| 2. Market Context (IHSG) | Regime market (hanya jika IHSG diupload) |
| 3. Market Structure | Trend structure, swing highs/lows, S/R levels, Fibonacci |
| 4. Technical Indicators | 42-row table dengan 16 confluence badges |
| 5. Key Levels | Pivot points |
| 6. Pattern & Divergence | Chart patterns, divergence alerts |
| 7. Confluence & Conflict | Evidence state, confluence state |
| 8. Setup Status | Primary setup dengan detail |
| 9. Trading Plan | Entry, SL, TP1, TP2, R/R, position sizing |
| 10. Decision Trace | Gate-by-gate reasoning dengan reason codes |
| 11. Disclaimer | Edukatif, bukan rekomendasi investasi |

### Decision States

| Decision | Arti |
|---|---|
| **BUY** | Sinyal beli (LONG setup) atau sell short (SHORT setup) |
| **HOLD** | Tahan posisi existing (thesis masih intact) |
| **SELL** | Keluar posisi (structural invalidation atau opposing setup) |
| **WAIT** | Setup masih developing atau tradeability belum memenuhi |
| **NO_SETUP** | Tidak ada thesis atau setup yang valid |
| **INSUFFICIENT_DATA** | Data tidak cukup untuk analisis |

### Reason Codes

| Code | Arti |
|---|---|
| BUY-01 | Standard tradeable entry |
| BUY-02 | Tradeable entry with warnings |
| BUY-03 | Range-boundary entry under neutral structure |
| WAIT-01 | Setup developing/absent with live thesis |
| WAIT-02 | Untradeable economics (R/R < 1.5) |
| WAIT-03 | Evidence conflict |
| WAIT-04 | Entry displaced from trigger |
| WAIT-05 | Minimum evidence contract unmet |
| NOSETUP-01 | No thesis, no setup |
| NOSETUP-02 | Direction not permitted |
| HOLD-01 | Thesis intact, no warnings |
| HOLD-02 | Thesis intact, with warnings |
| HOLD-03 | Setup failed, thesis intact |
| SELL-01 | Structural invalidation |
| SELL-02 | Confirmed opposing setup |
| SELL-03 | Failed setup + opposing outcome |
| SELL-04 | New SHORT entry justified |

### 42-Row Indicator Table

Table memiliki 6 kolom:
```
Category | Indicator | Value | Signal | Interpretation | Standard / Reference
```

Dan 16 confluence factors dengan badge:
- `✓` = Bullish
- `✗` = Bearish
- `○` = Neutral
- (kosong) = Tidak ada badge

### Trade Plan

| Field | Arti |
|---|---|
| Entry | Harga masuk posisi |
| SL (Stop Loss) | Harga cut loss |
| TP1 | Target profit 1 |
| TP2 | Target profit 2 |
| R/R | Risk-to-reward ratio (minimum 1.5) |
| Lots | Jumlah lot berdasarkan modal dan risk |
| Position Size | Jumlah saham/shares |

---

## 12. Output Formats

| OUTPUT | File Extension | Cocok Untuk |
|---|---|---|
| Chat/Markdown | `.md` | Chat, GitHub, text editors |
| HTML | `.html` | Browser, web publishing |
| PDF | `.pdf` | Print, share, archive |
| Excel | `.xlsx` | Spreadsheet, data analysis |

```powershell
# Markdown (default)
OUTPUT=Chat

# HTML
OUTPUT=HTML

# PDF
OUTPUT=PDF

# Excel
OUTPUT=Excel
```

---

## 13. CSV Cleaner & Merger

### CSV Cleaner
Bersihkan CSV dari berbagai sumber ke format standar OHLCV.

```powershell
.\venv\Scripts\python.exe csv_cleaner_app.py BBRI-history.csv -o cleaned/
```

Supported sources:
- Yahoo Finance
- Investing.com
- TradingView
- RTI Business
- Dan sumber lain dengan format Date,Open,High,Low,Close,Volume

### CSV Merger
Gabungkan data baru ke CSV existing.

```powershell
.\venv\Scripts\python.exe csv_merger_app.py --existing BBRI_cleaned.csv --new BBRI_new.csv -o merged/
```

---

## 14. FAQ

### Q: Berapa banyak data yang dibutuhkan?
- **Minimum:** 20 bar untuk analisis dasar
- **Disarankan:** 200+ bar untuk setup TRIGGERED (SMA200 cap)
- **Untuk optimasi:** 500+ bar per window
- **Untuk 5-year dataset:** ~1200 bar (sudah tersedia di `data-csv-yfinance-5y/`)

### Q: Bisakah pakai data dari sumber selain Yahoo Finance?
**Ya.** Gunakan CSV Cleaner untuk membersihkan CSV dari Investing.com, TradingView, RTI, atau sumber lain. Selama output formatnya `Date,Open,High,Low,Close,Volume`, engine bisa langsung pakai.

### Q: Bagaimana cara update data?
1. Download CSV baru dari Yahoo Finance (atau fetch via fetcher)
2. Gunakan CSV Merger untuk append ke existing cleaned CSV
3. Atau gunakan Yahoo Finance Fetcher:
```powershell
.\venv\Scripts\python.exe -c "from bei_swing_engine_v8.fetcher import fetch_and_save; fetch_and_save('BBRI', period='1y', output_dir='data-csv-yfinance-cleaned/')"
```

### Q: Apakah engine ini memberikan rekomendasi investasi?
**Tidak.** Engine ini menghasilkan output analitis (BUY/SELL/WAIT) yang bersifat edukatif. Keputusan investasi dan risiko sepenuhnya tanggung jawab pengguna.

### Q: Apa parameter yang tidak boleh diubah?
Parameter locked (lihat FINAL.md section 5):
- Swing fractal N = 8
- ATR fallback multiplier = 2.0
- Minimum R/R = 1.5
- S/R tolerance = max(0.5% x Close, 0.5 x ATR14)
- S/R minimum touches = 2
- Range minimum duration = 20 bars
- Breakout approach tolerance = 0.75 x ATR14
- Pullback zone tolerance = 0.5 x ATR14

### Q: Bagaimana cara menjalankan dengan Docker?
```powershell
docker-compose up --build

# Service tertentu saja
docker-compose up webui    # Web UI di http://localhost:8501
docker-compose up chat     # Chat AI di http://localhost:8502
docker-compose up api      # REST API di http://localhost:8000
```

### Q: Performance engine seperti apa?
- Single ticker analysis (1203 bars): ~200ms
- find_swings: ~4ms (vectorized numpy)
- Backtest (step=1, 1203 bars): ~9 detik
- Backtest (step=5): ~2 detik

### Q: Bagaimana cara kontribusi atau melaporkan bug?
Lihat `AGENTS.md` untuk panduan development, dan gunakan GitHub Issues untuk bug reports.

---

## Quick Reference

| Task | Command |
|---|---|
| Analisis tunggal | `python run.py --data TLKM.csv --params "MODE=A..."` |
| Screening | `python run.py --glob --data "*.csv" --params "MODE=C..."` |
| Backtest | `python run.py --data TLKM.csv --backtest` |
| Web UI | `streamlit run webui.py` |
| Chat AI | `streamlit run chat_app.py` |
| REST API | `python api_server_app.py` |
| Scheduler | `python scheduler_app.py --tickers BBRI --once` |
| Tests | `python -m pytest tests/ -v` |
| Linting | `python -m flake8 bei_swing_engine_v8/ ...` |
| Compliance | `python scripts/verify_final_compliance.py --locked` |
| Docker | `docker-compose up --build` |

---

*BEI Swing Engine v8.0 — Deterministic swing trading analysis for Indonesian stocks.*
