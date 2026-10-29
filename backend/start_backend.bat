@echo off
TITLE MedQueue AI - FastAPI Backend Server
cd /d "%~dp0"

echo =========================================================
echo       MedQueue AI - FastAPI Backend Starter (Windows CMD)
echo =========================================================
echo.

REM Check if venv directory exists
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call "venv\Scripts\activate.bat"
) else (
    echo [INFO] Virtual environment not found in backend\venv.
    echo [INFO] Using available system Python...
)

REM Verify Python is accessible
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found on your system PATH!
    echo Please install Python 3.10+ from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

REM Check if dependencies need installation
if not exist "venv" (
    echo [TIP] To create a dedicated virtualenv, run:
    echo        python -m venv venv
    echo        call venv\Scripts\activate.bat
    echo        pip install -r requirements.txt
    echo.
)

echo [INFO] Launching FastAPI server with Uvicorn...
echo [INFO] Health-check: http://127.0.0.1:8000/health
echo [INFO] Swagger Docs: http://127.0.0.1:8000/docs
echo.

python run.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Backend failed to start.
    pause
)
