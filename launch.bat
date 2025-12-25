@echo off
REM Multi-Trisonica GUI Application Launcher
REM This script checks for Python 3.12, creates a virtual environment if needed,
REM installs dependencies, and launches the application.

echo ========================================
echo Multi-Trisonica GUI Launcher
echo ========================================
echo.

REM Check if Python 3.12 is installed
python --version 2>NUL | findstr /R "3\.12" >NUL
if errorlevel 1 (
    echo ERROR: Python 3.12 is required but not found.
    echo Please install Python 3.12 from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python 3.12 detected

REM Check if virtual environment exists
if not exist ".venv" (
    echo.
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Check if dependencies are installed
echo.
echo Checking dependencies...
python -c "import PyQt5" 2>NUL
if errorlevel 1 (
    echo Installing dependencies from requirements.txt...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed
) else (
    echo [OK] Dependencies already installed
)

REM Launch the application
echo.
echo ========================================
echo Launching Multi-Trisonica GUI...
echo ========================================
echo.
python main.py

REM If the application exits with an error, pause so user can see the error
if errorlevel 1 (
    echo.
    echo ========================================
    echo Application exited with an error
    echo ========================================
    pause
)
