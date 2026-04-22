@echo off
setlocal
cd /d "%~dp0.."
set "ROOT=%CD%"
title LeadPilot API

if not exist "%ROOT%\.venv\Scripts\python.exe" (
  echo [FAIL] No venv at "%ROOT%\.venv". Run run.bat once from the repo root, or: python -m venv .venv
  pause
  exit /b 1
)

echo API: http://127.0.0.1:8000  ^|  JSON: /api/*  ^|  Docs: http://127.0.0.1:8000/docs
echo Leave this window open while developing. Close it to stop the API.
echo.

"%ROOT%\.venv\Scripts\python.exe" -m pip install -q -r "%ROOT%\requirements.txt"
if errorlevel 1 (
  echo [FAIL] pip install -r requirements.txt failed.
  pause
  exit /b 1
)

"%ROOT%\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
endlocal
