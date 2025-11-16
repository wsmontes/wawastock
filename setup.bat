@echo off
REM WawaStock - Setup Script (Windows)
REM This script sets up the Python virtual environment and installs all dependencies

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ========================================================
echo      WawaStock - Setup ^& Installation Script
echo ========================================================
echo.

REM Check Python version
echo [INFO] Checking Python installation...

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.8 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation!
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Found Python %PYTHON_VERSION%
echo.

REM Check pip
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pip is not available!
    echo.
    echo Please reinstall Python with pip included.
    pause
    exit /b 1
)

echo [OK] pip is available
echo.

REM Remove old virtual environment if broken
if exist "venv\" (
    echo [INFO] Found existing virtual environment...
    
    venv\Scripts\python.exe --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARNING] Virtual environment appears broken. Removing...
        rmdir /s /q venv
    ) else (
        echo [OK] Virtual environment is working. Skipping creation...
        set SKIP_VENV_CREATE=1
    )
)

REM Create virtual environment
if not exist "venv\" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    
    echo [OK] Virtual environment created
) else (
    if not defined SKIP_VENV_CREATE (
        echo [OK] Using existing virtual environment
    )
)

echo.

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment!
    pause
    exit /b 1
)

echo [OK] Virtual environment activated
echo.

REM Upgrade pip
echo [INFO] Upgrading pip, setuptools, and wheel...
python -m pip install --upgrade pip setuptools wheel --quiet

if %errorlevel% neq 0 (
    echo [WARNING] Failed to upgrade pip/setuptools/wheel ^(continuing anyway...^)
) else (
    echo [OK] pip, setuptools, and wheel upgraded
)

echo.

REM Install requirements
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found!
    pause
    exit /b 1
)

echo [INFO] Installing Python packages from requirements.txt...
echo.

python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install some packages!
    echo.
    echo Common fixes:
    echo   1. Check your internet connection
    echo   2. Try: pip install --upgrade pip
    echo   3. Try installing packages individually
    pause
    exit /b 1
)

echo.
echo [OK] All packages installed successfully!
echo.

REM Create directories
echo [INFO] Creating data directories...
if not exist "data\parquet" mkdir data\parquet
if not exist "data\processed" mkdir data\processed
if not exist "logs" mkdir logs

echo [OK] Data directories created
echo.

REM Test imports
echo [INFO] Testing critical imports...

python -c "import sys; packages = [('pandas', 'pandas'), ('numpy', 'numpy'), ('backtrader', 'backtrader'), ('streamlit', 'streamlit'), ('plotly', 'plotly'), ('yfinance', 'yfinance'), ('duckdb', 'duckdb')]; errors = []; [(__import__(m), print(f'  [OK] {n}')) if not errors.append(n) if True else None for n, m in [(name, mod) for name, mod in packages] if not __import__(mod)]; sys.exit(1) if errors else None" 2>nul

if %errorlevel% neq 0 (
    python -c "import pandas, numpy, backtrader, streamlit, plotly, yfinance, duckdb; print('  [OK] All packages')"
    if %errorlevel% neq 0 (
        echo [ERROR] Some packages failed to import!
        pause
        exit /b 1
    )
)

echo.
echo [OK] All critical packages imported successfully!
echo.

REM Summary
echo ========================================================
echo               Setup Complete! [OK]
echo ========================================================
echo.
echo Next steps:
echo.
echo   1. Start the application:
echo      start.bat
echo.
echo   2. Or manually activate the environment:
echo      venv\Scripts\activate.bat
echo.
echo   3. Run CLI commands:
echo      python main.py recipe sample --symbol AAPL
echo.
echo   4. Run Streamlit interface:
echo      streamlit run streamlit_app.py
echo.
echo [OK] Virtual environment is ready to use!
echo.
pause
