@echo off
setlocal

cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1

if not exist ".venv\Scripts\python.exe" (
  echo .venv\Scripts\python.exe was not found.
  echo Run this from C:\reository\21EMAStructure after creating the virtual environment.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m src.cli.oratek %*
set EXIT_CODE=%ERRORLEVEL%

echo.
echo OraTek CLI exited with code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
