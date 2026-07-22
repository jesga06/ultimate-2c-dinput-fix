@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

:MENU
cls
echo ======================================================================
echo           ULTIMATE-2C DINPUT FIX - TOOLS AND DIAGNOSTICS
echo ======================================================================
echo.
echo  PRIMARY DIAGNOSTICS AND SETUP
echo  [1] Run Full Issue Reporter (Generates issue_report.zip)
echo  [2] Install / Repair Python Dependencies
echo.
echo  CALIBRATION AND TESTING
echo  [3] Launch Calibration Wizard
echo  [4] Test Calibrated Input (Live ASCII Visualizer)
echo.
echo  DEBUG MODE LAUNCHERS
echo  [5] Launch Wrapper in Debug Mode (Console Output)
echo  [6] Launch Calibration Wizard in Debug Mode
echo.
echo  DEVELOPER AND UTILITY TOOLS
echo  [7] Launch Interactive Layout Builder (CustomTkinter GUI)
echo  [8] Run Individual Diagnostic Script
echo.
echo  [0] Exit
echo.
echo ======================================================================
set /p CHOICE="Select an option [0-8]: "

if "%CHOICE%"=="1" goto ISSUE_REPORT
if "%CHOICE%"=="2" goto INSTALL_REQS
if "%CHOICE%"=="3" goto CALIBRATE
if "%CHOICE%"=="4" goto TEST_CALIBRATION
if "%CHOICE%"=="5" goto WRAPPER_DEBUG
if "%CHOICE%"=="6" goto CALIBRATE_DEBUG
if "%CHOICE%"=="7" goto LAYOUT_BUILDER
if "%CHOICE%"=="8" goto INDIVIDUAL_DIAG
if "%CHOICE%"=="0" exit /b 0

echo Invalid choice. Please try again.
timeout /t 2 >nul
goto MENU

:CALIBRATE
cls
if exist "calibrate.bat" (
    call calibrate.bat
) else (
    set PYTHON_CMD=python
    if exist "venv\Scripts\python.exe" set PYTHON_CMD=venv\Scripts\python.exe
    "%PYTHON_CMD%" src\calibration.py
    pause
)
goto MENU

:TEST_CALIBRATION
cls
echo Starting Live Input Test Visualizer...
set PYTHON_CMD=python
if exist "venv\Scripts\python.exe" set PYTHON_CMD=venv\Scripts\python.exe
"%PYTHON_CMD%" src\calibration.py --test-only
pause
goto MENU

:ISSUE_REPORT
cls
if exist "generate_issue_report.bat" (
    call generate_issue_report.bat
) else (
    echo [ERROR] generate_issue_report.bat not found.
    pause
)
goto MENU

:INSTALL_REQS
cls
echo Installing / repairing dependencies from requirements.txt...
set PYTHON_CMD=python
if exist "venv\Scripts\python.exe" set PYTHON_CMD=venv\Scripts\python.exe

"%PYTHON_CMD%" -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Installation failed! Please check your Python environment.
) else (
    echo.
    echo Dependencies installed successfully.
)
pause
goto MENU

:WRAPPER_DEBUG
cls
echo Starting Wrapper in Debug Mode...
set PYTHON_CMD=python
if exist "venv\Scripts\python.exe" set PYTHON_CMD=venv\Scripts\python.exe
"%PYTHON_CMD%" src\main.py --debug
pause
goto MENU

:CALIBRATE_DEBUG
cls
echo Starting Calibration in Debug Mode...
set PYTHON_CMD=python
if exist "venv\Scripts\python.exe" set PYTHON_CMD=venv\Scripts\python.exe
"%PYTHON_CMD%" src\calibration.py --debug
pause
goto MENU

:LAYOUT_BUILDER
cls
echo Starting Interactive Layout Builder...
set PYTHON_CMD=python
if exist "venv\Scripts\python.exe" set PYTHON_CMD=venv\Scripts\python.exe
if exist "technical-stuff\interactive_layout_builder.py" (
    "%PYTHON_CMD%" technical-stuff\interactive_layout_builder.py
) else (
    echo [ERROR] technical-stuff\interactive_layout_builder.py not found.
)
pause
goto MENU

:INDIVIDUAL_DIAG
cls
echo ======================================================================
echo                   INDIVIDUAL DIAGNOSTIC SCRIPTS
echo ======================================================================
echo  [1] 01_environment_audit.py
echo  [2] 02_device_enumeration.py
echo  [3] 03_raw_transport.py
echo  [4] 04_report_id_scanner.py
echo  [5] 05_baseline_logic_test.py
echo  [6] 06_guided_calibration.py
echo  [0] Back to Main Menu
echo ======================================================================
set /p DIAG_CHOICE="Select a script to run [0-6]: "

set PYTHON_CMD=python
if exist "venv\Scripts\python.exe" set PYTHON_CMD=venv\Scripts\python.exe

if "%DIAG_CHOICE%"=="1" "%PYTHON_CMD%" diagnostics\01_environment_audit.py & pause & goto INDIVIDUAL_DIAG
if "%DIAG_CHOICE%"=="2" "%PYTHON_CMD%" diagnostics\02_device_enumeration.py & pause & goto INDIVIDUAL_DIAG
if "%DIAG_CHOICE%"=="3" "%PYTHON_CMD%" diagnostics\03_raw_transport.py & pause & goto INDIVIDUAL_DIAG
if "%DIAG_CHOICE%"=="4" "%PYTHON_CMD%" diagnostics\04_report_id_scanner.py & pause & goto INDIVIDUAL_DIAG
if "%DIAG_CHOICE%"=="5" "%PYTHON_CMD%" diagnostics\05_baseline_logic_test.py & pause & goto INDIVIDUAL_DIAG
if "%DIAG_CHOICE%"=="6" "%PYTHON_CMD%" diagnostics\06_guided_calibration.py & pause & goto INDIVIDUAL_DIAG
if "%DIAG_CHOICE%"=="0" goto MENU

echo Invalid choice.
timeout /t 2 >nul
goto INDIVIDUAL_DIAG

