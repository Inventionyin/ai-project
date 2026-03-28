@echo off
setlocal enabledelayedexpansion
set "ROOT=%~dp0"

:: ====================== 目录检查 ======================
if not exist "%ROOT%ai-project-back-end\" (
  echo ERROR: 后端目录不存在: %ROOT%ai-project-back-end
  exit /b 1
)

if not exist "%ROOT%ai-project_front_end\" (
  echo ERROR: 前端目录不存在: %ROOT%ai-project_front_end
  exit /b 1
)

:: ====================== 启动信息 ======================
echo.
echo ==========================================================
echo AI 项目开发环境一键启动脚本
echo 后端地址: http://127.0.0.1:8000
echo 前端地址: http://127.0.0.1:5173
echo ==========================================================
echo.

:: ====================== 启动后端（后台运行） ======================
echo [启动] 后端服务...
start /b cmd /c ^"cd /d "%ROOT%ai-project-back-end" ^&^& ^
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat" ^&^& ^
py -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info ^|^| ^
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info^"

:: ====================== 等待后端端口就绪 ======================
echo [等待] 等待后端 8000 端口启动完成...
set "BACKEND_READY="
for /L %%i in (1,1,60) do (
    powershell -NoProfile -Command "if ((Test-NetConnection 127.0.0.1 -Port 8000).TcpTestSucceeded) { exit 0 } else { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        set "BACKEND_READY=1"
        goto BACKEND_OK
    )
    timeout /t 1 /nobreak >nul
)

:BACKEND_OK
if defined BACKEND_READY (
    echo [就绪] 后端服务已启动: http://127.0.0.1:8000
) else (
    echo [警告] 后端启动超时，继续启动前端...
)
echo.

:: ====================== 启动前端（前台运行） ======================
echo [启动] 前端服务...
cd /d "%ROOT%ai-project_front_end"
npm run dev

endlocal