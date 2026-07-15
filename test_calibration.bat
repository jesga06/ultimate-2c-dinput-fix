@echo off
cd /d "%~dp0"
python src\calibration.py --test-only
pause
