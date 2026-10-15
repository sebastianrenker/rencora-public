@echo off
rem Rencora installer for Windows - double-click this file.
setlocal
cd /d "%~dp0"

echo.
echo === Rencora setup ===
echo.

rem Pick a supported Python (3.12 or 3.11). The "py" launcher comes with python.org installers.
set "PY="
py -3.12 -c "import sys" >nul 2>&1 && set "PY=py -3.12"
if not defined PY py -3.11 -c "import sys" >nul 2>&1 && set "PY=py -3.11"
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [ERROR] Python 3.11 or 3.12 was not found.
    echo Install Python 3.12 from https://www.python.org/downloads/windows/
    echo and tick "Add python.exe to PATH" during setup. Then run install.bat again.
    echo.
    pause
    exit /b 1
)
echo Using: %PY%

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment in .venv ...
    %PY% -m venv .venv || goto :fail
)

echo Installing packages - this can take a few minutes ...
".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail

echo Installing the Playwright browser (Chromium) ...
".venv\Scripts\python.exe" -m playwright install chromium || echo [WARN] Playwright browser not installed - web automation will not work.

echo.
echo === Done! ===
echo Start Rencora with start.bat (double-click).
echo On first start the browser opens the setup page where you enter your Gemini API key.
echo.
pause
exit /b 0

:fail
echo.
echo [ERROR] Setup failed - see the messages above.
pause
exit /b 1
