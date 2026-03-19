@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "VENV_PY=%ROOT_DIR%.venv\Scripts\python.exe"

echo Starting HomeFin for local testing...

if not exist "%BACKEND_DIR%\app\main.py" (
  echo [ERROR] Backend entry not found: "%BACKEND_DIR%\app\main.py"
  pause
  exit /b 1
)

if not exist "%FRONTEND_DIR%\index.html" (
  echo [ERROR] Frontend entry not found: "%FRONTEND_DIR%\index.html"
  pause
  exit /b 1
)

if not exist "%VENV_PY%" (
  echo [INFO] Creating virtual environment at "%ROOT_DIR%.venv"
  python -m venv "%ROOT_DIR%.venv"
)

"%VENV_PY%" -m pip install -r "%BACKEND_DIR%\requirements.txt"

start "HomeFin Backend" cmd /k "cd /d ""%BACKEND_DIR%"" && ""%VENV_PY%"" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

start "HomeFin Frontend" cmd /k "cd /d ""%FRONTEND_DIR%"" && python -m http.server 5500"

echo.
echo Backend:  http://localhost:8000/docs
echo Frontend: http://localhost:5500
echo.
echo Two new terminal windows were opened. Close them to stop services.

endlocal
