@echo off
chcp 65001 >nul 2>&1
title Copy BEI Swing Engine ke Drive/Folder Lain
cd /d "%~dp0"

echo ╔══════════════════════════════════════════════════════════╗
echo ║   COPY BEI SWING ENGINE v8.0 KE DRIVE/FOLDER LAIN       ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo Script ini akan copy project ke drive atau folder lain
echo TANPA venv (akan dibuat otomatis di komputer tujuan).
echo.
echo Contoh tujuan:
echo   E:\              (langsung ke root drive E)
echo   E:\BEI            (folder BEI di drive E)
echo   D:\Projects\BEI   (folder custom)
echo.
set /p dest="Masukkan folder tujuan (contoh: E:\BEI): "

REM Hapus backslash terakhir kalau ada
if "%dest:~-1%"=="\" set dest=%dest:~0,-1%

REM Cek apakah folder tujuan ada
if not exist "%dest%" (
    echo.
    echo Folder tujuan belum ada. Membuat folder: %dest%
    mkdir "%dest%"
    if errorlevel 1 (
        echo [ERROR] Tidak bisa membuat folder. Cek drive tujuan.
        pause
        exit /b 1
    )
)

echo.
echo ════════════════════════════════════════════════
echo  Mengcopy file ke: %dest%
echo ════════════════════════════════════════════════
echo.

REM Gunakan robocopy dengan exclude
robocopy "%~dp0" "%dest%" /E ^
    /XD venv .git __pycache__ .pytest_cache data-scheduled htmlcov ^
    /XF *.pyc *.pyo .coverage coverage.xml *.log ^
    /R:1 /W:1 /NFL /NDL /NP

echo.
echo ════════════════════════════════════════════════
echo  COPY SELESAI!
echo ════════════════════════════════════════════════
echo.
echo File sudah ada di: %dest%
echo.
echo ┌─────────────────────────────────────────────┐
echo │  CARA PAKAI DI KOMPUTER BARU:              │
echo │                                              │
echo │  1. Pastikan Python 3.11+ terinstall        │
echo │     Download: https://python.org            │
echo │     Centang "Add Python to PATH"             │
echo │                                              │
echo │  2. Buka folder: %dest%│
echo │                                              │
echo │  3. Double-click: start.bat                 │
echo │     (First run: auto-setup 5-10 menit)      │
echo │                                              │
echo │  4. Pilih mode:                              │
echo │     1 = Web UI (analisis di browser)        │
echo │     2 = Chat AI (chat dengan asisten)       │
echo │     3 = Scheduler (auto sinyal harian)      │
echo │                                              │
echo │  5. Untuk siapkan data CSV:                  │
echo │     Double-click: data_prep.bat              │
echo │                                              │
echo │  6. Untuk lihat hasil analisis:              │
echo │     Double-click: LIHAT_HASIL.bat            │
echo │                                              │
echo │  7. Baca panduan: MULAI_SINI.txt             │
echo │     atau docs\QUICK_GUIDE.md                 │
echo └─────────────────────────────────────────────┘
echo.
echo Folder tujuan: %dest%
echo.
echo Buka folder sekarang? (Y/N)
set /p open="> "
if /i "%open%"=="Y" explorer "%dest%"

pause
