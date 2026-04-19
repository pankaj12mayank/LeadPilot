@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\activate.bat" call "%~dp0.venv\Scripts\activate.bat"
if exist "%~dp0venv\Scripts\activate.bat" call "%~dp0venv\Scripts\activate.bat"
python -m pip install -r "%~dp0requirements.txt" -q
python -m playwright install chromium 2>nul
python -m backend.main
if errorlevel 1 pause
