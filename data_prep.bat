@echo off
chcp 65001 >nul 2>&1
title Data Preparation Tool
cd /d "%~dp0"

echo ============================================
echo    Data Preparation Tool (Standalone)
echo    BEI Swing Engine v8.0
echo ============================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [Setup] Pertama kali: membuat virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [Error] Python tidak ditemukan.
        echo Install Python 3.11+ dari https://python.org
        pause
        exit /b 1
    )
    echo [Setup] Menginstall dependencies...
    venv\Scripts\python.exe -m pip install -r requirements.txt
    echo [Setup] Selesai!
    echo.
)

echo Starting Data Preparation Tool...
echo Buka http://localhost:8503 di browser.
echo Tekan Ctrl+C untuk berhenti.
echo.
venv\Scripts\python.exe -m streamlit run data_prep_app.py --server.port=8503 --server.address=localhost
pause
