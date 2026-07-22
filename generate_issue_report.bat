@echo off
setlocal enabledelayedexpansion
title Automated Issue Reporter

echo ======================================================================
echo           AUTOMATED DIAGNOSTIC WIZARD
echo ======================================================================
echo This tool will run 6 diagnostic tests to analyze your controller and
echo system environment. At the end, it will package all logs into a single
echo file named 'issue_report.zip' in this directory.
echo.
echo Please follow the instructions on screen carefully.
echo ======================================================================
echo.

rem Check for previous zip file
if exist "issue_report.zip" (
    echo [INFO] Found a previous 'issue_report.zip'. Deleting it to start fresh...
    del /f /q "issue_report.zip"
    echo [OK] Previous report deleted.
    echo.
)

rem Check Python virtual environment
set PYTHON_CMD=venv\Scripts\python.exe
if not exist "%PYTHON_CMD%" (
    echo [ERROR] Python virtual environment was not found at:
    echo   %PYTHON_CMD%
    echo.
    echo Please ensure you have set up the virtual environment in this directory.
    echo.
    pause
    exit /b 1
)

echo [OK] Virtual environment detected.
echo.

rem Step 1: Environment Audit
echo ======================================================================
echo STEP 1: PC ENVIRONMENT AUDIT
echo ======================================================================
echo This step will automatically inspect your operating system, Python setup,
echo and virtual gamepad driver installations.
echo.
echo ">>> STATUS: DO NOT TOUCH ANYTHING during this step."
echo ======================================================================
pause
echo Running Step 1...
"%PYTHON_CMD%" diagnostics\01_environment_audit.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] Step 1 finished with non-zero exit code: %ERRORLEVEL%
)
echo.
echo [OK] Step 1 completed.
echo.

rem Step 2: Device Enumeration
echo ======================================================================
echo STEP 2: USB / HID DEVICE SCAN
echo ======================================================================
echo This step scans all connected USB and HID devices on your PC to check
echo if your controller is detected and accessible.
echo.
echo PREPARATION:
echo 1. Plug in your controller (wired or via wireless dongle).
echo 2. Close Steam, game launchers, and other controller mapping programs.
echo ======================================================================
pause
echo Running Step 2...
"%PYTHON_CMD%" diagnostics\02_device_enumeration.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] Step 2 finished with non-zero exit code: %ERRORLEVEL%
)
echo.
echo [OK] Step 2 completed.
echo.

rem Step 3: Raw HID Transport
echo ======================================================================
echo STEP 3: RAW CONTROLLER PACKET TEST
echo ======================================================================
echo This step tests direct communication with your controller. You will
echo see real-time packet information in a grid on the screen when you move
echo the joysticks or press buttons on the controller.
echo.
echo INSTRUCTIONS:
echo 1. Select the controller/interface when prompted by the script.
echo 2. Move the sticks and press buttons. You should see the numbers on
echo    screen changing rapidly.
echo 3. Once you see the numbers change, press Ctrl+C to stop the test.
echo 4. IMPORTANT: When you press Ctrl+C, Windows will ask:
echo      "Terminate batch job (Y/N)?"
echo    You MUST type N (for No) and press Enter to continue the wizard!
echo    If you type Y (for Yes), the diagnostics will stop early, and the
echo    zip report will NOT be created.
echo ======================================================================
pause
echo Running Step 3...
"%PYTHON_CMD%" diagnostics\03_raw_transport.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] Step 3 finished with non-zero exit code: %ERRORLEVEL%
)
echo.
echo [OK] Step 3 completed.
echo.

rem Step 4: Report ID Scanner
echo ======================================================================
echo STEP 4: REPORT ID / PACKET TOPOLOGY SCAN
echo ======================================================================
echo This step will scan your controller for all unique Report IDs and packet
echo sizes that it transmits.
echo.
echo INSTRUCTIONS:
echo 1. Select the controller/interface if prompted.
echo 2. Press Enter to start the countdown.
echo 3. Once the 10-second scan starts, press buttons, move sticks, and
echo    pull triggers CONTINUOUSLY until the scan finishes automatically.
echo ======================================================================
pause
echo Running Step 4...
"%PYTHON_CMD%" diagnostics\04_report_id_scanner.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] Step 4 finished with non-zero exit code: %ERRORLEVEL%
)
echo.
echo [OK] Step 4 completed.
echo.

rem Step 5: Baseline Logic Test
echo ======================================================================
echo STEP 5: CALIBRATION / INPUT LOGIC TEST
echo ======================================================================
echo This step establishes a resting baseline of your controller's bytes
echo and monitors real-time differences (deltas) as you press inputs.
echo.
echo INSTRUCTIONS:
echo 1. Select the controller/interface if prompted.
echo 2. Place the controller on a flat surface and DO NOT TOUCH IT or move
echo    any buttons for the first few seconds of calibration.
echo 3. After the baseline is established, press buttons and move joysticks.
echo    You should see statements indicating which bytes changed.
echo 4. When finished, press Ctrl+C to stop the test.
echo 5. IMPORTANT: When you press Ctrl+C, Windows will ask:
echo      "Terminate batch job (Y/N)?"
echo    You MUST type N (for No) and press Enter to continue the wizard!
echo    If you type Y (for Yes), the diagnostics will stop early, and the
echo    zip report will NOT be created.
echo ======================================================================
pause
echo Running Step 5...
"%PYTHON_CMD%" diagnostics\05_baseline_logic_test.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] Step 5 finished with non-zero exit code: %ERRORLEVEL%
)
echo.
echo [OK] Step 5 completed.
echo.

rem Step 6: Guided Calibration Test
echo ======================================================================
echo STEP 6: GUIDED INPUT CALIBRATION
echo ======================================================================
echo This step will guide you step-by-step to perfectly map your specific
echo controller's buttons and joysticks.
echo.
echo INSTRUCTIONS:
echo 1. Select the controller/interface if prompted.
echo 2. READ EVERY PROMPT CAREFULLY. You will be asked to press and hold
echo    specific buttons, and then press Enter on your keyboard.
echo 3. The script will wait until you complete each step. 
echo 4. If you do not have a requested button, you can skip it by typing 's'.
echo ======================================================================
pause
echo Running Step 6...
"%PYTHON_CMD%" diagnostics\06_guided_calibration.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] Step 6 finished with non-zero exit code: %ERRORLEVEL%
)
echo.
echo [OK] Step 6 completed.
echo.

rem Compress diagnostics_logs/ into issue_report.zip
echo ======================================================================
echo STEP 7: PACKAGING LOG FILES
echo ======================================================================
echo Packaging all generated log files from 'diagnostics_logs/' folder into
echo 'issue_report.zip' in the repository root.
echo.
powershell -Command "Compress-Archive -Path .\diagnostics_logs -DestinationPath .\issue_report.zip -Force"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to package the log files into a zip archive.
    echo Please ensure PowerShell is installed and accessible.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo                      SUCCESSFULLY COMPLETED!
echo ======================================================================
echo All 6 diagnostic steps have been executed and the log files packaged.
echo.
echo Location of report: .\issue_report.zip
echo.
echo PLEASE SEND THE 'issue_report.zip' FILE TO THE SUPPORT TEAM OR DEVELOPER.
echo ======================================================================
echo.
pause
