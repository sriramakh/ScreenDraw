@echo off
echo ScreenDraw for Windows
echo =====================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

:: Install dependencies if needed
pip show pillow >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements_windows.txt
    echo.
)

:: Run with admin rights for global hotkeys
echo Starting ScreenDraw...
python screendraw_windows.py
