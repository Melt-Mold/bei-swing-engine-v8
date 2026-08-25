@echo off
REM Buka folder output di Windows Explorer
cd /d "%~dp0"
if not exist "output" (
    mkdir output
)
explorer "output"
