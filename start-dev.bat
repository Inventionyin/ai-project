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

echo [Frontend] Starting frontend in foreground...
:: 前端在当前窗口前台运行，其日志将直接打印到此处
cd /d "%ROOT%ai-project_front_end"
npm run dev

endlocal
