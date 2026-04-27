@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "ROOT=%CD%"
set "ERR=0"

echo.
echo ============================================================
echo   LeadPilot — full web stack ^(FastAPI + Vite^)
echo   Root: %ROOT%
echo ============================================================
echo   This script: venv, pip, DB init, then API + Vite in THIS window.
echo   LinkedIn pipeline ^(Playwright + Ollama^): run in a 2nd terminal ^(see below^).
echo   Ports 8000 ^(API^) / 5173 ^(UI^) — keep this window open; Ctrl+C stops both.
echo ============================================================
echo.
set "PYTHONPATH=%ROOT%"

REM ----- Critical: Python -----
where python >nul 2>&1
if errorlevel 1 (
  echo [FAIL] Python is not on PATH. Install Python 3.10+ from python.org and retry.
  set ERR=1
  goto :end
)
echo [OK] Found Python:
python --version

REM ----- Critical: Node.js / npm -----
where npm >nul 2>&1
if errorlevel 1 (
  echo [FAIL] npm is not on PATH. Install Node.js LTS ^(includes npm^) and retry.
  set ERR=1
  goto :end
)
echo [OK] Found npm:
call npm --version

REM ----- Virtual environment -----
if not exist "%ROOT%\.venv\Scripts\python.exe" (
  echo.
  echo [..] Creating virtual environment .venv ...
  python -m venv "%ROOT%\.venv"
  if errorlevel 1 (
    echo [FAIL] Could not create .venv ^(python -m venv failed^).
    set ERR=1
    goto :end
  )
  echo [OK] Virtual environment created.
) else (
  echo [OK] Virtual environment already exists: .venv
)
set "PY=%ROOT%\.venv\Scripts\python.exe"
call "%ROOT%\.venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [FAIL] Could not activate .venv\Scripts\activate.bat
  set ERR=1
  goto :end
)
echo [OK] Virtual environment activated.

REM ----- Runtime folders -----
echo.
echo [..] Ensuring runtime folders exist ...
mkdir "%ROOT%\backend" 2>nul
mkdir "%ROOT%\database" 2>nul
mkdir "%ROOT%\data" 2>nul
mkdir "%ROOT%\exports" 2>nul
mkdir "%ROOT%\sessions" 2>nul
mkdir "%ROOT%\logs" 2>nul
mkdir "%ROOT%\storage" 2>nul
mkdir "%ROOT%\storage\branding" 2>nul
"%PY%" -c "import config; config.ensure_data_dirs()" 2>nul
if errorlevel 1 (
  echo [WARN] config.ensure_data_dirs^(\^) reported an error ^(continuing^).
)
echo [OK] Folders ready ^(exports, sessions, logs, data, database, storage\branding, safe-capture paths^).

REM ----- Root .env -----
if not exist "%ROOT%\.env" (
  if exist "%ROOT%\.env.example" (
    echo [..] Creating .env from .env.example ...
    copy /y "%ROOT%\.env.example" "%ROOT%\.env" >nul
    echo [OK] Created .env ^(review secrets before production^).
  ) else (
    echo [WARN] No .env.example found; continuing without copying .env
  )
) else (
  echo [OK] .env already present.
)

REM ----- Optional scraper.env (legacy Selenium / leadpilot; same keys as .env) -----
if not exist "%ROOT%\scraper.env" (
  if exist "%ROOT%\scraper.env.example" (
    echo [..] Creating scraper.env from scraper.env.example ...
    copy /y "%ROOT%\scraper.env.example" "%ROOT%\scraper.env" >nul
    echo [OK] Created scraper.env ^(edit Chrome / LinkedIn keys as needed^).
  )
) else (
  echo [OK] scraper.env already present.
)

REM ----- Backend dependencies -----
echo.
echo [..] Installing Python dependencies ^(requirements.txt^) ...
"%PY%" -m pip install --upgrade pip -q
"%PY%" -m pip install -r "%ROOT%\requirements.txt"
if errorlevel 1 (
  echo [FAIL] pip install -r requirements.txt failed.
  set ERR=1
  goto :end
)
echo [OK] Backend dependencies installed.

REM ----- Import smoke test (root app re-export + merged leadpilot package) -----
echo.
echo [..] Verifying imports: app.main + leadpilot ...
cd /d "%ROOT%"
"%PY%" -c "import app.main; import backend.leadpilot; print('[OK] app.main and backend.leadpilot import successfully')"
if errorlevel 1 (
  echo [FAIL] Python import check failed. Fix errors above, then re-run run.bat
  set ERR=1
  goto :end
)

REM ----- Database files / schema -----
echo.
echo [..] Initializing database ^(SQLite + storage^) ...
"%PY%" "%ROOT%\scripts\init_database.py"
if errorlevel 1 (
  echo [FAIL] scripts\init_database.py failed.
  set ERR=1
  goto :end
)
echo [OK] Database initialized.

REM ----- Frontend dependencies -----
if not exist "%ROOT%\frontend\package.json" (
  echo [FAIL] frontend\package.json is missing. Clone or restore the frontend folder.
  set ERR=1
  goto :end
)
cd /d "%ROOT%\frontend"
if not exist "%ROOT%\frontend\node_modules" (
  echo.
  echo [..] Installing frontend dependencies ^(npm install^) ...
  call npm install
  if errorlevel 1 (
    echo [FAIL] npm install in frontend\ failed.
    set ERR=1
    cd /d "%ROOT%"
    goto :end
  )
  echo [OK] Frontend dependencies installed.
) else (
  echo [OK] Frontend node_modules already present.
)
if not exist "%ROOT%\frontend\.env" (
  if exist "%ROOT%\frontend\.env.example" (
    copy /y "%ROOT%\frontend\.env.example" "%ROOT%\frontend\.env" >nul
    echo [OK] Created frontend\.env from .env.example ^(dev proxy /api^).
  )
)
cd /d "%ROOT%"

REM ----- Start API + Vite in THIS window (reliable; avoids orphan / closing CMD windows) -----
echo.
echo   ----------------------------------------------------------------
echo   Web stack: API http://127.0.0.1:8000  ^|  UI http://localhost:5173
echo   ----------------------------------------------------------------
echo   LinkedIn lead pipeline ^(repo root, separate terminal^):
echo     .venv\Scripts\activate
echo     python main.py --help
echo     python main.py --keyword "role" --country "region" --max-leads 20
echo   Legacy Selenium ^(optional^: leadpilot_single.py or python -m backend.leadpilot
echo   Selenium: ChromeDriver is resolved by Selenium 4.6+ ^(pip install -U selenium^) — preflight can test.
echo   Ollama: start Ollama app or run  ollama serve  then  ollama pull your-model
echo   Optional API push: set LNN_BASE_URL=http://127.0.0.1:8000/api in .env or scraper.env
echo   Preflight only:  python -m backend.leadpilot.preflight
echo   ----------------------------------------------------------------
echo.
echo [..] Starting API + Vite in this window ^(Ctrl+C stops both^) ...
echo.
"%PY%" "%ROOT%\scripts\dev_server.py"
set ERR=%ERRORLEVEL%

echo.
echo ============================================================
echo   Dev servers stopped ^(exit code %ERR%^).
echo   To run again: double-click run.bat or run scripts\dev_server.py
echo ============================================================
goto :end

:end
if "%ERR%"=="1" (
  echo.
  echo ============================================================
  echo   STOPPED — fix the errors above, then run run.bat again.
  echo ============================================================
)
echo.
pause
endlocal
exit /b %ERR%
