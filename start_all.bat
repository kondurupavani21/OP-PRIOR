@echo off
TITLE MedQueue AI — Full Stack Startup
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║         MedQueue AI — Full Stack Launcher            ║
echo  ║   Backend: FastAPI (port 8000)                       ║
echo  ║   Frontend: React/Vite (port 5173)                   ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo [INFO] Starting FastAPI backend in a new window...
start "MedQueue Backend" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\python.exe run.py"

timeout /t 3 /nobreak >nul

echo [INFO] Starting React frontend in a new window...
start "MedQueue Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo [INFO] Both servers are starting...
echo  Backend API:   http://127.0.0.1:8000
echo  Swagger Docs:  http://127.0.0.1:8000/docs
echo  Frontend App:  http://localhost:5173
echo.
pause
