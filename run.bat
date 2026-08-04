@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo .venv not found. Run install.bat first.
    pause
    exit /b 1
)

set "CMD=%~1"
if "%CMD%"=="" set "CMD=serve"

echo Starting: vgtranslate %CMD% %2 %3 %4 %5 %6 %7 %8 %9
".venv\Scripts\python.exe" -m vgtranslate %CMD% %2 %3 %4 %5 %6 %7 %8 %9
pause
