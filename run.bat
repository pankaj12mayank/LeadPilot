@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "ROOT=%CD%"
set "ERR=0"

echo.
echo ============================================================
echo   LeadPilot - latest one-command runner
echo   Root: %ROOT%
echo ============================================================
echo   This now delegates to: python scripts\run_system.py
echo   It installs deps, initializes DB, and runs API + frontend.
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [FAIL] Python is not on PATH. Install Python 3.11+ and retry.
  set ERR=1
  goto :end
)

python "%ROOT%\scripts\run_system.py"
set ERR=%ERRORLEVEL%

echo.
echo ============================================================
echo   Runner stopped (exit code %ERR%).
echo   Frontend: http://localhost:5173
echo   Landing page URL: http://localhost:5173/
echo ============================================================

:end
echo.
pause
endlocal
exit /b %ERR%
