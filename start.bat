@echo off
rem Start Rencora (Windows) - double-click this file.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Rencora is not installed yet - run install.bat first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" run_headless.py --local --open
pause
