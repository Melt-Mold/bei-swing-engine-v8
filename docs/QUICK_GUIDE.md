# BEI Swing Engine v8.0 — Quick Guide

> Cheat sheet untuk penggunaan harian. Untuk detail lengkap, lihat `docs/USER_GUIDE.md`.

---

## A. 5 Perintah yang Paling Sering Dipakai

### 1. Analisis 1 Ticker (Mode A — Lengkap)
```powershell
.\venv\Scripts\python.exe run.py --data data-csv-yfinance-cleaned\TLKM.JK_cleaned.csv --params "MODE=A`nHORIZON=SWING`nDIRECTION=BOTH`nPOSITION=NO_POSITION`nMODAL=10000000`nRISK=2`nOUTPUT=Chat`nIHSG=None" --ihsg data-csv-yfinance-cleaned\IHSG-JKSE_cleaned.csv --output-dir output
```

### 2. Screening Semua Saham
```powershell
.\venv\Scripts\python.exe run.py --glob --data "data-csv-yfinance-cleaned\*.JK_cleaned.csv" --params "MODE=C`nHORIZON=SWING`nDIRECTION=BOTH`nPOSITION=NO_POSITION`nMODAL=10000000`nRISK=2`nOUTPUT=Chat`nIHSG=None" --output-dir output
```

### 3. Backtest 1 Ticker
```powershell
.\venv\Scripts\python.exe run.py --data data-csv-yfinance-cleaned\TLKM.JK_cleaned.csv --backtest --output-dir output
```

### 4. Web UI (Browser)
```powershell
.\venv\Scripts\python.exe -m streamlit run webui.py
```
Buka: http://localhost:8501

### 5. Chat AI (Browser)
```powershell
.\venv\Scripts\python.exe -m streamlit run chat_app.py
```
Buka: http://localhost:8501 — Ketik: `Analisis BBRI` atau `Screening BBRI TLKM BBCA`

---

## B. Cara Baca Decision (3 Detik)

| Decision | Arti | Tindakan |
|---|---|---|
| **BUY** | Setup triggered, tradeable, R/R >= 1.5 | Buka posisi sesuai direction |
| **SELL** | Exit posisi (invalidation atau opposing setup) | Tutup posisi |
| **HOLD** | Thesis intact, tahan posisi | Tidak ada aksi |
| **WAIT** | Setup masih developing atau untradeable | Tunggu konfirmasi |
| **NO_SETUP** | Tidak ada setup valid | Tidak trade |
| **INSUFFICIENT_DATA** | Data kurang dari 20 bar | Tambah data |

---

## C. Parameter Default yang Aman

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

**Ubah hanya kalau perlu:**
- `POSITION=EXISTING_POSITION` kalau Anda sudah punya saham
- `DIRECTION=LONG` kalau mau long only
- `RISK=1` kalau mau lebih konservatif
- `OUTPUT=HTML` atau `PDF` kalau mau laporan visual

---

## D. Update Data Harian

### Opsi 1: Fetch Otomatis (Rekomendasi)
```powershell
.\venv\Scripts\python.exe -c "from bei_swing_engine_v8.fetcher import fetch_and_save; fetch_and_save('BBRI', period='1y', output_dir='data-csv-yfinance-cleaned/')"
```

### Opsi 2: Scheduler Otomatis + Notifikasi
```powershell
.\venv\Scripts\python.exe scheduler_app.py --tickers BBRI BBCA TLKM --once
```

### Opsi 3: Download Manual + Clean
1. Download CSV dari https://finance.yahoo.com/quote/BBRI.JK/history
2. Clean:
```powershell
.\venv\Scripts\python.exe csv_cleaner_app.py BBRI-download.csv -o data-csv-yfinance-cleaned/
```
3. Merge ke existing:
```powershell
.\venv\Scripts\python.exe csv_merger_app.py --existing data-csv-yfinance-cleaned\BBRI.JK_cleaned.csv --new BBRI-download.csv -o data-csv-yfinance-cleaned/
```

---

## E. Trade Plan di Laporan

Kalau decision BUY/SELL, laporan punya:
```
Entry: Rp 2.610 | SL: Rp 2.600 | TP1: Rp 2.780 | TP2: Rp 3.205 | R/R: 17.41
```
- **Entry**: Harga masuk
- **SL**: Stop loss (cut loss kalau tembus)
- **TP1**: Target profit 1 (ambil sebagian)
- **TP2**: Target profit 2 (ambil sisanya)
- **R/R**: Risk/reward ratio (harus >= 1.5)

---

## F. Quick Troubleshooting

| Masalah | Solusi |
|---|---|
| `ModuleNotFoundError` | `.\venv\Scripts\python.exe -m pip install -r requirements.txt` |
| `UnicodeEncodeError` saat print | Set `$env:PYTHONIOENCODING='utf-8'` |
| Data kurang dari 200 bar | Setup maksimal CONFIRMED, tradeability UNTRADEABLE |
| Yahoo Finance error/rate limit | Tunggu 1-2 menit, coba lagi |
| Hasil screening kosong | Pastikan CSV ada di `data-csv-yfinance-cleaned/` |
| Chat AI tidak respon | Cek koneksi internet (butuh fetch data) |

---

## G. Docker (Alternatif)

```powershell
docker-compose up --build          # Semua services
docker-compose up webui             # Web UI di :8501
docker-compose up chat              # Chat AI di :8502
docker-compose up api               # REST API di :8000
```

---

## H. Portable (External Drive)

Double-click `start.bat` di folder project. Akan auto-setup venv kalau belum ada, lalu jalankan menu.

---

*Disclaimer: Analisis bersifat edukatif. Keputusan investasi dan risiko tanggung jawab pengguna.*
