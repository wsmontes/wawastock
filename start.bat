@echo off
REM WawaStock - Streamlit Launcher (Windows)
REM Usage: start.bat

cd /d "%~dp0"

echo 🚀 Starting WawaStock Streamlit Interface...
echo.

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo ✓ Virtual environment activated
) else (
    echo ❌ Virtual environment not found!
    echo    Run: python -m venv venv
    echo    Then: venv\Scripts\activate.bat
    echo    Then: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check if streamlit is installed
where streamlit >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Streamlit not found! Installing...
    pip install streamlit
)

echo ✓ Starting Streamlit...
echo.

REM Open browser after 3 seconds
start /b timeout /t 3 /nobreak >nul && start http://localhost:8502

REM Run streamlit
streamlit run streamlit_app.py
