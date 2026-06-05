@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo .venv\Scripts\python.exe was not found.
    echo Run this from a workspace that has the project virtual environment.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m streamlit run app\main.py

