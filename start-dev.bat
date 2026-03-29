@echo off
setlocal
set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%ai-project-back-end"
set "FRONTEND_DIR=%ROOT%ai-project_front_end"
set "BACKEND_VENV=%BACKEND_DIR%\.venv"
set "BACKEND_PY=%BACKEND_VENV%\Scripts\python.exe"

if not exist "%BACKEND_DIR%\" (
  echo Backend directory not found: %BACKEND_DIR%
  exit /b 1
)

if not exist "%FRONTEND_DIR%\" (
  echo Frontend directory not found: %FRONTEND_DIR%
  exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed or not in PATH.
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo npm is not installed or not in PATH.
  exit /b 1
)

if not exist "%BACKEND_PY%" (
  echo [Backend] Creating virtual environment...
  python -m venv "%BACKEND_VENV%"
  if errorlevel 1 exit /b 1
)

echo [Backend] Checking Python dependencies...
"%BACKEND_PY%" -c "import asyncpg, uvicorn" >nul 2>nul
if errorlevel 1 (
  echo [Backend] Installing requirements...
  "%BACKEND_PY%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
  if errorlevel 1 exit /b 1
)

if not exist "%FRONTEND_DIR%\node_modules\.bin\vite.cmd" (
  echo [Frontend] Installing npm dependencies...
  cd /d "%FRONTEND_DIR%"
  npm install
  if errorlevel 1 exit /b 1
)

echo.
echo ==========================================================
echo [System] Starting AI Project - Development Mode
echo [System] All logs (Backend, Frontend, k6) will show below.
echo [System] Backend:  http://127.0.0.1:8000
echo [System] Frontend: http://127.0.0.1:5173
echo ==========================================================
echo.

echo [Backend] Starting background process...
start /b powershell -NoProfile -ExecutionPolicy Bypass -Command "$env:PYTHONPATH='%BACKEND_VENV%\Lib\site-packages;%BACKEND_DIR%'; Set-Location '%BACKEND_DIR%\app'; & '%BACKEND_PY%' -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info"

echo [Frontend] Starting frontend in foreground...
cd /d "%FRONTEND_DIR%"
npm run dev

endlocal
