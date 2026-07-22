@echo off
cd /d "%~dp0"
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo Installation failed! Please check your Python/pip installation.
    pause
    exit /b %errorlevel%
)
echo.
echo Dependencies installed successfully.
pause
