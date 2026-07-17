# Features List


## 🎮 Interactive Calibration Wizard (`src/calibration.py`)
Run calibration using `calibrate.bat` or `calibrate_debug.bat` to configure and profile a new gamepad.
* **Auto-Device Detection:** Detects and highlights physical gamepads automatically as soon as you press a button or move a stick.
* **Guided Step-by-Step Profiling:** Walks you through mapping buttons, bump triggers, analog stick axis offsets, and the D-Pad Hat switch.
* **Custom Extra Buttons:** Supports profiling a custom number of additional buttons (e.g. L4, R4, M1, M2 back paddles) with personalized names.
* **Profile Generation:** Automatically creates a device-specific JSON profile under the `profiles/` directory named after the device's Vendor ID (VID) and Product ID (PID).
* **Calibration-Time Visual Layout:** Choose your layout layout (Xbox, PlayStation, Nintendo) at the start of calibration. It will be stored in the device profile to customize future testing prompts.
* **Advanced High-Precision Axis Detection:** Automatically identifies 16-bit axes using a rolling 2-byte window and computes amplitudes to filter out diagonal axis noise.
* **Signed/Inverted Axis Detection:** Detects axis polarity and origin (signed vs unsigned) to prevent camera jumping.
* **Cross-Contamination Rejection:** Employs a multi-axis movement rejection heuristic (0.7 threshold) to avoid mapping digital trigger clicks as axis movement.
* **Robust Hat Switch Detection:** Filters neutral-to-direction transitions to map D-Pad inputs cleanly.
* **Gyro/Motion Sensor Filter:** Prompts users to identify if the controller streams telemetry continuously to filter out sensor drift.
* **Vibration/Rumble Probing:** Guided wizard (`_calibrate_rumble()`) to cycle through output bytes to detect rumble motor indices (currently disabled by default).

---

## 🔍 Flicker-Free Live Test Mode (`test_calibration.bat`)
Run the test tool directly using `test_calibration.bat` to verify your gamepad inputs.
* **Quick-Launch Test:** Launches directly into the testing panel for your calibrated controller, bypassing the setup wizard using the `--test-only` argument.
* **2D ASCII Thumbstick Visualizers:** Displays a 5x5 ASCII coordinate grid for the Left Stick (LS) and Right Stick (RS) in real-time, showing range, deadzones, and stick coordinates.
* **Analog Trigger Level-Bars:** Fills vertical meters (`█` / `▒`) showing trigger press pressure instead of simple integer readouts.
* **ANSI Zero-Flicker Updates:** Utilizes Windows Console Virtual Terminal Processing (ANSI escape codes) to update lines in-place, eliminating screen flashing.
* **Dynamic Button Prompts:** Test UI changes standard A/B/X/Y labels dynamically to fit the profile layout.

---

## ⚙️ Advanced Remapping GUI (`src/gui.py`)
Run the settings panel using `run_wrapper.bat` (and select "Open Config" in the system tray).
* **Interactive Recorder Modal:**
  * **Keyboard Combos:** Records complex multi-key combinations (e.g., `Ctrl + Shift + Alt + Z`) as you press them.
  * **Mouse Clicks:** Captures clicks for Middle, Left, Right, Mouse4, and Mouse5. Left-clicks inside the recorder are ignored for UI protection.
  * **Mouse Scroll Wheel:** Records scroll direction.
* **Mouse Scroll Remapping Customization:**
  * **Oneshot Mode:** Triggers exactly $X$ scroll notches on button press.
  * **Continuous Mode:** Repeats $X$ scroll notches every $Y$ seconds as long as the button is held.
  * **Interactive Notch Tester:** Scroll inside the tester box to set your notch tally (scrolling up adds notches, scrolling down subtracts, clamped to a minimum of 1).
  * **Reset Notches:** Instantly resets the tester counter back to 1.
* **Opt-Out XInput Blocking:**
  * Remapping a button to a keyboard/mouse action automatically blocks it on the virtual XInput pad to prevent double inputs in games.
  * A **"Block XInput"** checkbox column next to each remapped action lets you toggle this behavior on or off. Unchecking it allows sending both the virtual controller signal and the remapped keyboard/mouse signal simultaneously.
* **Tuning Tab (Sticks & Triggers):**
  * **Trigger Sensitivity:** Modify the sensitivity of analog triggers directly using sliders (values from 0.1 to 3.0) to fine-tune actuation limits.
  * **Digital Triggers Mode:** A "Digital Trigger Mode" checkbox forces analog trigger values to act as binary buttons (0 or 255) on the virtual pad immediately upon input.
  * **Analog Tuning Visualizer:** Displays real-time coordinate plotting with a 1.0 unit circular bounds grid and exact decimal labels for thumbsticks.
* **Live Connection Status:** Displays whether the background daemon is currently "Connected" or "Disconnected", along with the active controller's name.
* **Chords & Macros Studio (Advanced Tab):** Record sequences of gamepad inputs and output key/mouse events, choose between toggle (press) and hold execution, with integrated stuck-key protection.
* **Shift Layer Remapping:** Configure dynamic shift mappings and shift blocking for every button, expanding total layout mapping possibilities.
* **Transition Screen Overlay:** Smooth color-interpolated canvas fades (250ms in/out, 900ms hold) with randomized community quotes and a rotating vector loading spinner.

---

## 🖥️ Daemon Background Wrapper Process (`src/main.py`)
* **XInput Emulation:** Utilizes `vgamepad` to instantiate a virtual Xbox 360 controller on Windows, compatible with Steam and almost all PC games.
* **Tray Icon Application:** Runs quietly in the system tray, keeping your desktop clean.
* **Auto-Reloading Config:** A background thread polls `config.ini` every 5 seconds and updates the active mappings on-the-fly without needing a restart.
* **Tray Restore Utility:** The "Show Console" action uses native Windows API calls (`SW_RESTORE` + `SetForegroundWindow`) to bring the minimized CLI window back to the front immediately.
* **Smart Reconnection Loop:** If the physical controller is disconnected, the daemon enters a connection recovery loop, scanning for a connected device with the exact same name for up to 20 seconds. It will restore the connection automatically if found, or gracefully terminate all processes (including the GUI) if the timeout expires.
* **Composite HID Interface Support:** Captures and merges inputs from multi-interface USB devices (e.g. Machenike G5 Pro) concurrently, binding profiles to `interfaceNumber_reportId` keys.
* **Multi-Reader Concurrency:** Spawns distinct polling threads for each active HID reader matching the target controller profile interfaces.
* **True Radial Deadzone Math:** Computes response curves and deadzones directly on the stick vector magnitude instead of individual axes, yielding a perfectly circular range.
* **Smart Reconnection Guard:** Halts reconnection attempts if a controller fails immediately (under 2 seconds) due to persistent OS-level locks.

---

## 🩺 Automated Diagnostic Suite (`diagnostics/`)
A completely generic, foolproof, and automated diagnostic suite to troubleshoot any unknown HID controllers without needing to write custom code. Use `generate_issue_report.bat` to run the wizard.
* **Automated Issue Reporter Wizard:** Runs 6 sequential diagnostic tests and packages the results into a single `issue_report.zip` file for easy sharing with developers.
* **Environment Audit:** Automatically checks OS version, Python architecture, `vgamepad` driver status, and legacy `pywinusb` installations to prevent environmental conflicts.
* **Generic Device Enumeration:** Safely enumerates all HID devices, tests for exclusive OS-level security locks, matches devices against known JSON profiles, and warns if a controller is in standard XInput mode.
* **Raw Packet Visualizer:** Provides a real-time data grid showing the raw byte stream from the controller, bypassing any decoding logic.
* **Topology Scanner:** Actively listens to the controller to detect every unique `Report ID` and its corresponding packet length, logging the full network topology of the hardware.
* **Dynamic Baseline Logic Test:** Tests the core math engine's ability to establish resting baselines and calculate byte-level deltas in real-time, featuring smart fallback logic for controllers that only transmit packets on input changes.
* **Interactive Guided Calibration (`06_guided_calibration.py`):** 
  * A step-by-step foolproof wizard that prompts the user to press standard buttons, extra buttons, and joysticks.
  * Uses a background threading daemon so no packets are missed while waiting for the user to read instructions.
  * Integrates smart filtering to distinguish accidental analog axis drift from digital button presses (e.g., filtering out drift when clicking `L3`/`R3`).
  * Seamlessly handles silent "on-change-only" controllers via active prompting and buffer flushing.

---

## 🛠️ Diagnostics & Troubleshooting
* **Unification of Logs:** A logging setup module (`src/logger_setup.py`) coordinates wrapper log pipelines.
* **Comprehensive Daemon Logging:** Core scripts (`calibration.py`, `hid_reader.py`, `virtual_pad.py`, `decoder.py`, `mapper.py`) explicitly route errors, warnings, and state transitions to `wrapper.log` and `calibration.log` via module-level loggers, capturing background issues that would otherwise only print to a hidden terminal.
* **Diagnostic Delta Filtering:** Tools like `03_raw_transport.py` and `04_report_id_scanner.py` track and compare HID packets frame-by-frame, writing outputs *only* when a byte state changes, eliminating log file bloat.
* **Argparse Forwarding:** Launching the GUI from the tray forwards logs parameters (`--log` and `--append-log`), appending GUI logs into the wrapper's log for a sequential debugging timeline.
* **Log Overwrite Safety:** Fresh log files (`wrapper.log` and `calibration.log`) are generated cleanly on every new startup to prevent file bloat.
* **HID Rate Limiting:** Filters and rate-limits raw HID byte streams to 0.5-second logging intervals.

---

## ⚙️ Under-the-Hood & Developer Features
* **Cython `hidapi` Transport Backend:** Bypasses Windows' aggressive HID descriptor truncation issues by utilizing cython-based `hidapi`, enabling raw reads of payloads up to 1024 bytes.
* **Decoupled Architecture:** Strict separation between Transport (`RawHIDReport`), Parser (`decoder.py`), and Consumers (`VirtualPad`, `Mapper`).
* **Profile-Driven Metadata Parser:** Decodes inputs entirely dynamically by iterating over JSON configuration keys. Supports:
  - Multi-byte inputs (e.g., 16-bit little-endian values).
  - Signedness, inversion, scaling, deadzones, and bit shifting/masking.
* **Persistent State Engine:** Ensures `ControllerState` persists previously received values when the device transmits partial packets or alternate report IDs.
* **Experimental Force Feedback (Vibration) Architecture:** 
  - **Rumble Interception:** Callback notifications bound to `vgamepad` to capture incoming vibration instructions.
  - **Output Report Blaster:** `send_output_report()` wrapper utilizing `hidapi.write()` to communicate directly with physical gamepad rumble motors.
  - **Data-Driven Injection:** Dynamic replacement of intensity bytes inside a profile-configured rumble payload template.
  - **Interactive Rumble Probing:** Command-line procedure to identify rumble motor byte locations by pulsing each index (currently disabled by default).
