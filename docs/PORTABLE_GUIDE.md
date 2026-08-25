# Panduan Portable — BEI Swing Engine v8.0

> Cara copy project ke external drive atau folder lain dan menjalankannya di komputer mana saja.

---

## A. Copy ke External Drive

### Langkah 1: Siapkan External Drive
- USB flash drive (min 8GB) atau external HDD/SSD
- Colokkan ke komputer

### Langkah 2: Copy Project
1. Double-click **`COPY_KE_DRIVE.bat`** di folder `C:\Opencode4`
2. Masukkan tujuan, contoh: `E:\BEI`
3. Tunggu sampai selesai (2-5 menit)
4. Folder `E:\BEI` siap pakai

**Atau copy manual:**
- Copy seluruh folder `C:\Opencode4` ke `E:\BEI`
- **Jangan copy folder `venv\`** (akan dibuat otomatis)
- **Jangan copy folder `.git\`** (tidak perlu untuk penggunaan)

### Yang Di-copy oleh Script
```
✅ Semua file .py, .bat, .html, .txt, .md
✅ Folder: bei_swing_engine_v8/, scripts/, tests/, docs/
✅ Folder: data-csv-yfinance-cleaned/, data-csv-yfinance-5y/
✅ File config: requirements.txt, setup.cfg, scheduler_config.json
✅ Docker: Dockerfile, docker-compose.yml
❌ TIDAK: venv/ (auto-create di komputer baru)
❌ TIDAK: .git/ (tidak perlu)
❌ TIDAK: __pycache__/ (cache)
❌ TIDAK: data-scheduled/ (akan dibuat ulang)
```

---

## B. Pakai di Komputer Baru

### Syarat
- **Python 3.11+** harus terinstall
- Download dari: https://python.org
- Saat install, centang **"Add Python to PATH"**

### Langkah 1: Pertama Kali (Setup)
1. Buka folder `E:\BEI` (atau folder tujuan)
2. Double-click **`start.bat`**
3. Tunggu 5-10 menit (auto-create venv + install dependencies)
4. Menu muncul → pilih mode

### Langkah 2: Pilih Mode

| Pilihan | Mode | Penjelasan |
|---|---|---|
| 1 | Web UI | Analisis saham di browser. Upload CSV atau fetch dari Yahoo. |
| 2 | Chat AI | Chat dengan asisten. Ketik "Analisis BBRI" atau "Screening BBRI TLKM". |
| 3 | Scheduler | Auto-fetch data harian + kirim email sinyal BUY/SELL. |

### Langkah 3: Setup Email (Opsional)
1. Buka file **`scheduler_config.json`** dengan Notepad
2. Isi:
   ```json
   "email_user": "emailanda@gmail.com",
   "email_password": "app_password_16_char",
   "email_to": ["emailanda@gmail.com"]
   ```
3. Save file
4. Test: double-click `start.bat` → pilih 3 (Scheduler)

### Langkah 4: Siapkan Data (Opsional)
1. Double-click **`data_prep.bat`**
2. Browser terbuka di http://localhost:8503
3. Upload CSV dari Yahoo Finance
4. Clean + download

---

## C. Troubleshooting

| Masalah | Solusi |
|---|---|
| `Python tidak ditemukan` | Install Python 3.11+ dari python.org. Centang "Add to PATH". |
| `pip install error` | Cek koneksi internet. Restart, coba lagi. |
| `Port 8501 sudah digunakan` | Tutup aplikasi lain yang pakai port itu, atau ubah port di start.bat |
| `Yahoo Finance error` | Tunggu 1-2 menit, coba lagi. Yahoo kadang rate-limit. |
| `streamlit not found` | Jalankan: `venv\Scripts\python.exe -m pip install streamlit` |
| Hasil analisis kosong | Pastikan ada CSV di folder `data-csv-yfinance-cleaned/` |

---

## D. Struktur Folder di External Drive

```
E:\BEI\
├── MULAI_SINI.txt        ← Baca ini dulu
├── start.bat             ← Launcher utama
├── data_prep.bat         ← Tool data CSV
├── LIHAT_HASIL.bat       ← Buka folder output
├── COPY_KE_DRIVE.bat     ← Copy ke drive lain
├── index.html            ← Launcher visual
├── scheduler_config.json ← Setting email/ticker
│
├── docs/                 ← Panduan
├── data-csv-yfinance-cleaned/  ← Data saham
├── output/               ← Hasil analisis
├── bei_swing_engine_v8/  ← Engine (jangan diubah)
└── venv\                 ← Dibuat otomatis (first run)
```

---

## E. FAQ

**Q: Berapa besar space yang dibutuhkan?**
- Tanpa venv: ~50MB
- Dengan venv (setelah setup): ~500MB-1GB
- Dengan data 5 tahun: +2MB per ticker

**Q: Bisa jalan tanpa internet?**
- Analisis: **Ya**, kalau CSV sudah ada di folder data.
- Fetch data: **Tidak**, butuh internet untuk download dari Yahoo Finance.
- Scheduler: **Tidak**, butuh internet untuk auto-fetch.

**Q: Bisa copy ke cloud (Google Drive/Dropbox)?**
- **Tidak disarankan.** venv dan __pycache__ bisa rusak saat sync.
- Lebih baik copy ke local folder atau USB drive.

**Q: Bisa pakai di Mac/Linux?**
- Engine Python-nya bisa (cross-platform), tapi start.bat cuma untuk Windows.
- Di Mac/Linux, jalankan manual: `python -m streamlit run webui.py`

---

*Disclaimer: Analisis bersifat edukatif. BUKAN rekomendasi investasi.*
