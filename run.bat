@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if /I "%~1"=="capture" goto safe_capture
if /I "%~1"=="dashboard" goto streamlit_dash

echo.
echo   LeadPilot — starting API + Vite (React)
echo   Browser: http://localhost:5173   API: http://127.0.0.1:8000/docs
echo   Stop: Ctrl+C here and close the API window
echo   Alternative: from repo root run  npm install  then  npm run dev  (single terminal)
echo.

echo Installing Python requirements (quiet)...
python -m pip install -r requirements.txt -q
if errorlevel 1 (
  echo Pip failed. Is Python on PATH?
  pause
  goto :eof
)

echo Starting API in a new window...
start "LeadPilot API" cmd /k "%~dp0scripts\start-api.bat"
echo Waiting 2 seconds for API...
timeout /t 2 /nobreak >nul

cd /d "%~dp0frontend"
if not exist package.json (
  echo ERROR: frontend folder missing.
  pause
  goto :eof
)
if not exist node_modules (
  echo npm install...
  call npm install
  if errorlevel 1 (
    echo npm install failed.
    pause
    goto :eof
  )
)
if not exist .env (
  if exist .env.example (
    echo Creating frontend\.env from .env.example
    copy /y .env.example .env
  )
)

call npm run dev
if errorlevel 1 pause
goto :eof

:safe_capture
echo.
echo   LeadPilot — Safe manual capture (Playwright, one lead at a time)
echo   Profile: sessions\playwright_user_data\safe_capture
echo   DB: database\safe_leads.db   CSV: exports\safe_leads.csv
echo.
python -m pip install -r requirements.txt -q
if errorlevel 1 (
  echo Pip failed. Is Python on PATH?
  pause
  goto :eof
)
echo Ensuring Playwright browser binaries...
python -m playwright install chromium
if errorlevel 1 (
  echo Playwright install failed.
  pause
  goto :eof
)
python -m backend.safe_capture_cli
if errorlevel 1 pause
goto :eof

:streamlit_dash
echo.
echo   LeadPilot — Streamlit dashboard (safe captures)
echo.
python -m pip install -r requirements.txt -q
if errorlevel 1 (
  echo Pip failed. Is Python on PATH?
  pause
  goto :eof
)
python -m streamlit run "%~dp0frontend\streamlit_dashboard.py"
if errorlevel 1 pause
goto :eof
