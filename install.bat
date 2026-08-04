@echo off
setlocal
cd /d "%~dp0"

set "EXTRAS=ocr,ocr-manga,mt-sugoi,tray"
if not "%~1"=="" set "EXTRAS=%~1"
if "%EXTRAS%"=="all" set "EXTRAS=all"

echo ==================================================
echo   vgtranslate installer
echo   Python 3.12+ required (from python.org)
echo   Installing extras: [%EXTRAS%]
echo   (override with: install.bat all  or  install.bat ocr,tray)
echo ==================================================
echo.

if exist ".venv\Scripts\python.exe" (
    echo Using existing .venv...
) else (
    echo Creating virtual environment...
    py -3.12 -m venv .venv || py -3 -m venv .venv || py -m venv .venv || goto :fail
)

".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :fail
".venv\Scripts\python.exe" -m pip install -e ".[%EXTRAS%]" || goto :fail

echo.
echo === Installed engines ===
".venv\Scripts\python.exe" -m vgtranslate status || goto :fail

echo.
echo Installation complete. Double-click run.bat to start the server.
echo (run.bat tray for the tray icon; run.bat serve --detect-llm to probe LM Studio)
pause
exit /b 0

:fail
echo.
echo Installation FAILED. See the errors above.
pause
exit /b 1
