@echo off
chcp 65001 >nul 2>&1
title BEI Swing Engine v8.0
cd /d "%~dp0"

echo ============================================
echo    BEI Swing Engine v8.0
echo ============================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo [Setup] Pertama kali: membuat virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [Error] Python tidak ditemukan.
        echo Install Python 3.11+ dari https://python.org
        echo Pastikan centang "Add Python to PATH" saat install.
        pause
        exit /b 1
    )
    echo [Setup] Menginstall dependencies...
    venv\Scripts\python.exe -m pip install -r requirements.txt
    echo [Setup] Selesai!
    echo.
)

:menu
echo Pilih mode:
echo.
echo   1. Web UI    ^| Analisis saham di browser (upload/fetch/analyze)
echo   2. Chat AI   ^| Chat dengan asisten analisis saham
echo   3. Scheduler ^| Auto-fetch harian + notifikasi sinyal BUY/SELL
echo   Q. Keluar
echo.
set /p choice="Pilihan: "

if /i "%choice%"=="1" goto webui
if /i "%choice%"=="2" goto chat
if /i "%choice%"=="3" goto scheduler
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
echo Ketik: Analisis BBRI atau Screening BBRI TLKM BBCA
echo Tekan Ctrl+C untuk berhenti.
echo.
venv\Scripts\python.exe -m streamlit run chat_app.py
goto menu

:scheduler
echo.
echo Scheduler: auto-fetch data + analyze + notifikasi sinyal BUY/SELL.
echo.
set /p tickers="Tickers (pisah spasi, contoh: BBRI BBCA TLKM): "
echo.
echo Pilih notifikasi:
echo   1. Tanpa notifikasi (simpan ke file saja)
echo   2. Email
echo   3. Telegram
echo   4. Webhook
echo.
set /p notify="Notifikasi (1-4): "

if "%notify%"=="1" (
    venv\Scripts\python.exe scheduler_app.py --tickers %tickers% --once
) else if "%notify%"=="2" (
    set /p smtp="SMTP host (contoh: smtp.gmail.com): "
    set /p user="Email: "
    set /p pass="App password: "
    set /p to="Kirim ke (email penerima): "
    venv\Scripts\python.exe scheduler_app.py --tickers %tickers% --once --email --smtp-host %smtp% --email-user %user% --email-pass %pass% --email-to %to%
) else if "%notify%"=="3" (
    set /p token="Telegram Bot Token: "
    set /p chat_id="Telegram Chat ID: "
    venv\Scripts\python.exe scheduler_app.py --tickers %tickers% --once --telegram --telegram-token %token% --telegram-chat %chat_id%
) else if "%notify%"=="4" (
    set /p url="Webhook URL: "
    venv\Scripts\python.exe scheduler_app.py --tickers %tickers% --once --webhook --webhook-url %url%
) else (
    echo Pilihan tidak valid. Menjalankan tanpa notifikasi.
    venv\Scripts\python.exe scheduler_app.py --tickers %tickers% --once
)
goto menu

:end
echo Terima kasih. Sampai jumpa!
timeout /t 2 >nul
