@echo off
setlocal EnableDelayedExpansion
set "KILLED=0"
set "SEEN_PIDS= "

for %%P in (8000 5173 4173) do (
  for /f "tokens=5" %%A in ('netstat -ano ^| findstr /R /C:":%%P .*LISTENING"') do (
    set "PID=%%A"
    echo !SEEN_PIDS! | find " !PID! " >nul
    if errorlevel 1 (
      set "SEEN_PIDS=!SEEN_PIDS!!PID! "
      taskkill /F /T /PID !PID! >nul 2>&1
      if not errorlevel 1 (
        echo Stopped port %%P process PID !PID!
        set /a KILLED+=1
      )
    )
  )
)

if "!KILLED!"=="0" (
  echo No dev process found on ports 8000, 5173, or 4173.
) else (
  echo Stopped !KILLED! process^(es^).
)

endlocal
