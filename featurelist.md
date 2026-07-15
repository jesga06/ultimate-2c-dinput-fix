# Features List


## 🎮 Interactive Calibration Wizard (`src/calibration.py`)
Run calibration using `calibrate.bat` or `calibrate_debug.bat` to configure and profile a new gamepad.
* **Auto-Device Detection:** Detects and highlights physical gamepads automatically as soon as you press a button or move a stick.
* **Guided Step-by-Step Profiling:** Walks you through mapping buttons, bump triggers, analog stick axis offsets, and the D-Pad Hat switch.
* **Custom Extra Buttons:** Supports profiling a custom number of additional buttons (e.g. L4, R4, M1, M2 back paddles) with personalized names.
* **Profile Generation:** Automatically creates a device-specific JSON profile under the `profiles/` directory named after the device's Vendor ID (VID) and Product ID (PID).
* **Calibration-Time Visual Layout:** Choose your layout layout (Xbox, PlayStation, Nintendo) at the start of calibration. It will be stored in the device profile to customize future testing prompts.

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
* **Digital Triggers Mode:**
  * A **"Digital Trigger"** checkbox next to `lt` and `rt` triggers forces the analog trigger values to act as binary buttons (either 0 or 255) on the virtual pad immediately upon input (hair-trigger mode, threshold > 0).
* **Visual Layout Selector:**
  * Switch between Xbox, PlayStation, and Nintendo Visual Layouts on the fly.
  * Dynamically translates the labels in the Remapping screen (e.g. changing "A" to "Cross (✖)" or "B") so you always know what physical button you are editing.
* **Live Connection Status:** Displays whether the background daemon is currently "Connected" or "Disconnected", along with the active controller's name.

---

## 🖥️ Daemon Background Wrapper Process (`src/main.py`)
* **XInput Emulation:** Utilizes `vgamepad` to instantiate a virtual Xbox 360 controller on Windows, compatible with Steam and almost all PC games.
* **Tray Icon Application:** Runs quietly in the system tray, keeping your desktop clean.
* **Auto-Reloading Config:** A background thread polls `config.ini` every 5 seconds and updates the active mappings on-the-fly without needing a restart.
* **Tray Restore Utility:** The "Show Console" action uses native Windows API calls (`SW_RESTORE` + `SetForegroundWindow`) to bring the minimized CLI window back to the front immediately.
* **Smart Reconnection Loop:** If the physical controller is disconnected, the daemon enters a connection recovery loop, scanning for a connected device with the exact same name for up to 20 seconds. It will restore the connection automatically if found, or gracefully terminate all processes (including the GUI) if the timeout expires.

---

## 🛠️ Diagnostics & Troubleshooting
* **Unification of Logs:** A logging setup module (`src/logger_setup.py`) coordinates wrapper log pipelines.
* **Argparse Forwarding:** Launching the GUI from the tray forwards logs parameters (`--log` and `--append-log`), appending GUI logs into the wrapper's log for a sequential debugging timeline.
* **Log Overwrite Safety:** Fresh log files (`wrapper.log` and `calibration.log`) are generated cleanly on every new startup to prevent file bloat.
* **HID Rate Limiting:** Filters and rate-limits raw HID byte streams to 0.5-second logging intervals.
