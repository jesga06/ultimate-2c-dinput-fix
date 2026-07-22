@echo off
cd /d "%~dp0"
title "Universal Remapper & XInput from DInput Wrapper"
echo Starting UR-XD...

set PYTHON_CMD=python
if exist "venv\Scripts\python.exe" set PYTHON_CMD="venv\Scripts\python.exe"

%PYTHON_CMD% -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3, 13), (3, 14)) else 1)"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python 3.13.x or 3.14.x is required.
    pause
    exit /b 1
)

%PYTHON_CMD% src\main.py %*