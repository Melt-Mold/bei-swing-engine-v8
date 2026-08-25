@echo off
chcp 65001 >nul 2>&1
title BEI Swing Engine v8.0
cd /d "%~dp0"

echo ============================================
echo    BEI Swing Engine v8.0 — Portable Mode
echo ============================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo [Setup] First run: creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [Error] Python tidak ditemukan. Install Python 3.11+ dari https://python.org
        pause
        exit /b 1
    )
    echo [Setup] Installing dependencies...
    venv\Scripts\python.exe -m pip install -r requirements.txt
    echo [Setup] Done!
    echo.
)

:menu
echo Pilih mode:
echo.
echo   1. Web UI           (browser, http://localhost:8501)
echo   2. Chat AI          (browser, http://localhost:8501)
echo   3. REST API         (http://localhost:8000/docs)
echo   4. Scheduler        (auto-fetch + analyze + notify)
echo   5. Analisis 1 Ticker (CLI)
echo   6. Screening Semua  (CLI)
echo   7. Backtest 1 Ticker (CLI)
echo   8. CSV Cleaner       (standalone)
echo   9. CSV Merger        (standalone)
echo   0. Update Data Yahoo (fetch 1y semua ticker)
echo   Q. Keluar
echo.
set /p choice="Pilihan: "

if /i "%choice%"=="1" goto webui
if /i "%choice%"=="2" goto chat
if /i "%choice%"=="3" goto api
if /i "%choice%"=="4" goto scheduler
if /i "%choice%"=="5" goto single
if /i "%choice%"=="6" goto screen
if /i "%choice%"=="7" goto backtest
if /i "%choice%"=="8" goto cleaner
if /i "%choice%"=="9" goto merger
if /i "%choice%"=="0" goto fetch
if /i "%choice%"=="Q" goto end
echo Pilihan tidak valid.
goto menu

:webui
echo.
echo Starting Web UI... Buka http://localhost:8501 di browser.
echo Tekan Ctrl+C untuk berhenti.
echo.
venv\Scripts\python.exe -m streamlit run webui.py
goto menu

:chat
echo.
echo Starting Chat AI... Buka http://localhost:8501 di browser.
echo Tekan Ctrl+C untuk berhenti.
echo.
venv\Scripts\python.exe -m streamlit run chat_app.py
goto menu

:api
echo.
echo Starting REST API... Buka http://localhost:8000/docs di browser.
echo Tekan Ctrl+C untuk berhenti.
echo.
venv\Scripts\python.exe api_server_app.py
goto menu

:scheduler
echo.
set /p tickers="Tickers (pisah spasi, contoh: BBRI BBCA TLKM): "
venv\Scripts\python.exe scheduler_app.py --tickers %tickers% --once
goto menu

:single
echo.
set /p csv="Path CSV (contoh: data-csv-yfinance-cleaned\TLKM.JK_cleaned.csv): "
venv\Scripts\python.exe run.py --data "%csv%" --params "MODE=A`nHORIZON=SWING`nDIRECTION=BOTH`nPOSITION=NO_POSITION`nMODAL=10000000`nRISK=2`nOUTPUT=Chat`nIHSG=None" --output-dir output
goto menu

:screen
echo.
venv\Scripts\python.exe run.py --glob --data "data-csv-yfinance-cleaned\*.JK_cleaned.csv" --params "MODE=C`nHORIZON=SWING`nDIRECTION=BOTH`nPOSITION=NO_POSITION`nMODAL=10000000`nRISK=2`nOUTPUT=Chat`nIHSG=None" --output-dir output
goto menu

:backtest
echo.
set /p csv="Path CSV (contoh: data-csv-yfinance-cleaned\TLKM.JK_cleaned.csv): "
venv\Scripts\python.exe run.py --data "%csv%" --backtest --output-dir output
goto menu

:cleaner
echo.
set /p input_csv="Path CSV mentah (download dari Yahoo): "
set /p out_dir="Output dir (contoh: data-csv-yfinance-cleaned): "
venv\Scripts\python.exe csv_cleaner_app.py "%input_csv%" -o "%out_dir%"
goto menu

:merger
echo.
set /p existing_csv="Path CSV existing (cleaned): "
set /p new_csv="Path CSV baru (raw): "
set /p out_dir="Output dir: "
venv\Scripts\python.exe csv_merger_app.py --existing "%existing_csv%" --new "%new_csv%" -o "%out_dir%"
goto menu

:fetch
echo.
echo Fetching data 1 year untuk semua ticker sample...
venv\Scripts\python.exe -c "from bei_swing_engine_v8.fetcher import fetch_and_save; [fetch_and_save(t, period='1y', output_dir='data-csv-yfinance-cleaned/') or print(f'{t} done') for t in ['BBCA','BBRI','BMRI','HRUM','ICBP','INDF','PTRO','TLKM','IHSG']]"
echo Done!
goto menu

:end
echo Terima kasih. Sampai jumpa!
timeout /t 2 >nul
