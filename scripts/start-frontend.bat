@echo off
setlocal
cd /d "%~dp0..\frontend"
set "FRONT=%CD%"

if not exist "%FRONT%\package.json" (
  echo [FAIL] frontend\package.json not found.
  pause
  exit /b 1
)

title LeadPilot Web
echo App: http://localhost:5173  ^(requires API on port 8000 for /api proxy^)
echo Leave this window open. Close it to stop Vite.
echo.

if not exist "%FRONT%\node_modules" (
  echo [..] npm install ...
  call npm install
  if errorlevel 1 (
    echo [FAIL] npm install failed.
    pause
    exit /b 1
  )
)

call npm run dev
pause
endlocal
