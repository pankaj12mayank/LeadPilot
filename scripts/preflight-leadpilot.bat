@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
set "PY=%CD%\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [FAIL] No venv. Run run.bat from repo root once, or: python -m venv .venv
  pause
  exit /b 1
)
title LeadPilot — leadpilot preflight
echo Running: python -m backend.leadpilot.preflight
echo.
"%PY%" -m backend.leadpilot.preflight
set ERR=%ERRORLEVEL%
echo.
if not "%ERR%"=="0" echo [FAIL] Preflight exit code %ERR%
pause
exit /b %ERR%
