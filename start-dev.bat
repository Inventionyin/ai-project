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

start "Backend - AI Project" cmd /k "cd /d ""%ROOT%ai-project-back-end"" && if exist "".venv\Scripts\activate.bat"" (call "".venv\Scripts\activate.bat"") && (py -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 || python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000)"
start "Frontend - AI Project" cmd /k "cd /d ""%ROOT%ai-project_front_end"" && npm run dev"

echo Backend and frontend windows started.
echo Backend: http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:5173
endlocal
