@echo off
setlocal
cd /d "%~dp0"

set "FULL_EXTRAS=ocr,ocr-manga,mt-sugoi,tray"
set "LITE_EXTRAS=ocr,tray"
set "VENV_PY=.venv\Scripts\python.exe"

echo ==================================================
echo   vgtranslate installer
echo   Python 3.10+ required (from python.org)
echo ==================================================
echo.

if exist "%VENV_PY%" (
    echo Using existing .venv...
) else (
    echo Creating virtual environment...
    rem Prefer a Python that supports ALL extras (sugoi requires Python <=3.12)
    py -3.12 -m venv .venv 2>nul && goto :venv_ok
    py -3.11 -m venv .venv 2>nul && goto :venv_ok
    py -3.10 -m venv .venv 2>nul && goto :venv_ok
    py -3 -m venv .venv 2>nul && goto :venv_ok
    py -m venv .venv 2>nul && goto :venv_ok
    echo Could not create a virtual environment. Install Python 3.12 from python.org first.
    goto :fail
)

:venv_ok
for /f "tokens=1,2" %%a in ('"%VENV_PY%" -c "import sys;print(sys.version_info[0],sys.version_info[1])"') do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
echo Python in .venv: %PY_MAJOR%.%PY_MINOR%

set "EXTRAS=%LITE_EXTRAS%"
if "%PY_MAJOR%"=="3" if "%PY_MINOR%" LEQ 12 set "EXTRAS=%FULL_EXTRAS%"

if not "%~1"=="" set "EXTRAS=%~1"
if "%EXTRAS%"=="all" set "EXTRAS=%FULL_EXTRAS%"

echo Installing extras: [%EXTRAS%]
echo.
if not "%EXTRAS%"=="%FULL_EXTRAS%" (
    echo NOTE: mt-sugoi (neural JP-EN) and manga-ocr require Python 3.12 or older.
    echo To install the full set: install Python 3.12 from python.org, delete the
    echo .venv folder, and run install.bat all
    echo.
)

"%VENV_PY%" -m pip install --upgrade pip || goto :fail
"%VENV_PY%" -m pip install -e ".[%EXTRAS%]" || goto :fail

echo.
echo === Installed engines ===
"%VENV_PY%" -m vgtranslate status || goto :fail

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
