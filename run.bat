@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

REM ----- Optional virtual environment (common layouts) -----
set "_VENV_ACT="
if exist "%~dp0.venv\Scripts\activate.bat" (
  call "%~dp0.venv\Scripts\activate.bat"
  set "_VENV_ACT=1"
) else if exist "%~dp0venv\Scripts\activate.bat" (
  call "%~dp0venv\Scripts\activate.bat"
  set "_VENV_ACT=1"
) else if exist "%~dp0env\Scripts\activate.bat" (
  call "%~dp0env\Scripts\activate.bat"
  set "_VENV_ACT=1"
)
if not defined _VENV_ACT (
  echo.
  echo [i] No virtual environment found at .venv, venv, or env.
  echo     Using Python from PATH. Create one with:  python -m venv .venv
  echo.
)

where python >nul 2>&1
if errorlevel 1 (
  echo [X] Python was not found on PATH. Install Python 3 and retry.
  pause
  exit /b 1
)

:menu
cls
echo.
echo   LeadPilot  ^|  Windows launcher
echo   ================================
echo   1. Run Lead Capture   ^(Playwright + backend\main.py^)
echo   2. Open Dashboard     ^(Streamlit^)
echo   3. Export CSV         ^(SQLite safe captures -^> configured CSV path^)
echo   4. Exit
echo.
set "choice="
set /p "choice=Choose [1-4]: "
if "!choice!"=="" goto menu
if "!choice!"=="1" goto opt_capture
if "!choice!"=="2" goto opt_dashboard
if "!choice!"=="3" goto opt_export
if "!choice!"=="4" goto :eof
echo Invalid choice. Use 1, 2, 3, or 4.
timeout /t 2 /nobreak >nul
goto menu

:opt_capture
echo.
echo --- Lead Capture ---
python -m pip install -r "%~dp0requirements.txt" -q
if errorlevel 1 (
  echo [X] pip install failed. Check network and requirements.txt
  pause
  goto menu
)
echo Ensuring Playwright Chromium...
python -m playwright install chromium
if errorlevel 1 (
  echo [!] Playwright browser install had a problem; capture may still work if browsers exist.
)
python -m backend.main
if errorlevel 1 echo [X] Capture exited with an error.
pause
goto menu

:opt_dashboard
echo.
echo --- Dashboard ---
python -m pip install -r "%~dp0requirements.txt" -q
if errorlevel 1 (
  echo [X] pip install failed.
  pause
  goto menu
)
python -c "import streamlit" 2>nul
if errorlevel 1 (
  echo [X] Streamlit is not installed. From repo root:  python -m pip install streamlit
  pause
  goto menu
)
python -m streamlit run "%~dp0frontend\streamlit_dashboard.py"
if errorlevel 1 echo [X] Streamlit exited with an error.
pause
goto menu

:opt_export
echo.
echo --- Export CSV ---
python -m pip install -r "%~dp0requirements.txt" -q
if errorlevel 1 (
  echo [X] pip install failed.
  pause
  goto menu
)
python -m backend.export_safe_csv
if errorlevel 1 echo [X] Export failed.
pause
goto menu
