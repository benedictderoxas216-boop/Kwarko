@echo off
REM ================================================================
REM  KWARKO launcher for Windows - double-click this file to start.
REM  First run: creates a virtual environment and installs packages.
REM ================================================================
cd /d "%~dp0"

where python >/dev/null 2>nul
if errorlevel 1 (
    echo Python was not found. Install it from https://www.python.org/downloads/
    echo and tick "Add Python to PATH" during installation.
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
    echo Installing requirements - this only happens once...
    venv\Scripts\python.exe -m pip install --upgrade pip
    venv\Scripts\python.exe -m pip install -r requirements.txt
)

echo Starting KWARKO... your browser will open at http://localhost:8501
venv\Scripts\python.exe -m streamlit run app.py
pause
