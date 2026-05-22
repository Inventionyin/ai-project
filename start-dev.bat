@echo off
setlocal
set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%ai-project-back-end"
set "FRONTEND_DIR=%ROOT%ai-project_front_end"
if "%DATABASE_URL%"=="" set "DATABASE_URL=postgresql+asyncpg://postgres:123456@localhost:5432/ai_test_platform"
set "DRY_RUN=0"

if /I "%~1"=="--help" (
  echo Usage: start-dev.bat [--dry-run]
  echo.
  echo Starts local backend on 8000 and frontend dev server on 5173.
  echo DATABASE_URL can be provided by environment; otherwise local ai_test_platform is used.
  exit /b 0
)

if /I "%~1"=="-h" (
  echo Usage: start-dev.bat [--dry-run]
  exit /b 0
)

if /I "%~1"=="--dry-run" set "DRY_RUN=1"

if not exist "%BACKEND_DIR%\" (
  echo Backend directory not found: %BACKEND_DIR%
  exit /b 1
)

if not exist "%FRONTEND_DIR%\" (
  echo Frontend directory not found: %FRONTEND_DIR%
  exit /b 1
)

if "%DRY_RUN%"=="1" (
  echo [DryRun] Backend directory: %BACKEND_DIR%
  echo [DryRun] Frontend directory: %FRONTEND_DIR%
  echo [DryRun] DATABASE_URL: %DATABASE_URL%
  echo [DryRun] Would check Docker/PostgreSQL, run alembic migrations, install frontend deps if missing, then start backend/frontend.
  exit /b 0
)

where docker >nul 2>&1
if errorlevel 1 (
  echo [Check] Docker not found in PATH. Please install Docker Desktop or ensure PostgreSQL is already reachable.
) else (
  docker info >nul 2>&1
  if errorlevel 1 (
    echo [Check] Docker is installed but daemon is not ready.
  ) else (
    echo [Check] Docker daemon is reachable.
  )
)

where psql >nul 2>&1
if errorlevel 1 (
  echo [Check] psql not found, skip local postgres command check.
) else (
  psql -h localhost -p 5432 -U postgres -d postgres -c "select 1" >nul 2>&1
  if errorlevel 1 (
    echo [Check] PostgreSQL local probe failed on localhost:5432 as user postgres.
  ) else (
    echo [Check] PostgreSQL local probe succeeded.
  )
)

set "PYTHON_CMD=python"
if exist "%BACKEND_DIR%\.venv\Scripts\python.exe" (
  set "PYTHON_CMD=%BACKEND_DIR%\.venv\Scripts\python.exe"
) else (
  where py >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py"
)

echo [Backend] Applying local database migrations...
cd /d "%BACKEND_DIR%"
set "PYTHONPATH=."
%PYTHON_CMD% -m alembic upgrade head
if errorlevel 1 (
  echo [Backend] Database migration failed.
  exit /b 1
)

if not exist "%FRONTEND_DIR%\node_modules\" (
  echo [Frontend] node_modules not found, running npm ci...
  cd /d "%FRONTEND_DIR%"
  npm ci
  if errorlevel 1 (
    echo [Frontend] npm ci failed.
    exit /b 1
  )
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
start /b cmd /c "cd /d ""%BACKEND_DIR%"" && set DATABASE_URL=%DATABASE_URL% && if exist "".venv\Scripts\activate.bat"" (call "".venv\Scripts\activate.bat"") && (py -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info || python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info)"

echo [Frontend] Starting frontend in foreground...
:: 前端在当前窗口前台运行，其日志将直接打印到此处
cd /d "%FRONTEND_DIR%"
npm run dev

endlocal
