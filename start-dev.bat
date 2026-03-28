@echo off
setlocal
set "ROOT=%~dp0"

if not exist "%ROOT%ai-project-back-end\" (
  echo Backend directory not found: %ROOT%ai-project-back-end
  exit /b 1
)

if not exist "%ROOT%ai-project_front_end\" (
  echo Frontend directory not found: %ROOT%ai-project_front_end
  exit /b 1
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
:: 使用 start /b 在当前窗口后台运行后端
start /b cmd /c "cd /d ""%ROOT%ai-project-back-end"" && if exist "".venv\Scripts\activate.bat"" (call "".venv\Scripts\activate.bat"") && (py -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info || python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info)"

<<<<<<< HEAD
echo [Backend] Waiting for 127.0.0.1:8000 to be ready...
set "BACKEND_READY="
for /L %%i in (1,1,60) do (
  powershell -NoProfile -Command "if ((Test-NetConnection -ComputerName 127.0.0.1 -Port 8000).TcpTestSucceeded) { exit 0 } else { exit 1 }" >nul 2>nul
  if not errorlevel 1 (
    set "BACKEND_READY=1"
    goto backend_ready
  )
  timeout /t 1 >nul
)
:backend_ready
if "%BACKEND_READY%"=="1" (
  echo [Backend] Ready on 127.0.0.1:8000
) else (
  echo [Backend] Warning: 127.0.0.1:8000 not ready, starting frontend anyway
)

=======
>>>>>>> 0f64092fd6c7abac3f72736aa6652163d25e1b0b
echo [Frontend] Starting frontend in foreground...
:: 前端在当前窗口前台运行，其日志将直接打印到此处
cd /d "%ROOT%ai-project_front_end"
npm run dev

endlocal
