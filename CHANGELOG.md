## [1.0.0] - 2026-07-15
This is the official 1.0.0 release of the universal HID-to-XInput wrapper. It brings the wrapper from a hardcoded script to a robust, user-friendly, and customizable daemon.

Here is a detailed breakdown of the latest changes, features, and improvements made to the project since the last commit, separated into what you'll notice when using the app, and the under-the-hood technical architecture changes.

## 🎮 User-Noticeable Changes

### 1. Interactive Calibration Tool (`src/calibration.py`)
- **Universal Support:** You can now add support for almost *any* generic HID controller by running the calibration tool.

### 2. Interactive Input Recording & Advanced Mouse Scroll
- **Interactive Remap Recorder:** You can click the "⏺ Record" button in the GUI to capture keyboard combos and mouse buttons instead of typing them. Left-click is ignored to allow clicking UI buttons safely.
- **Advanced Scroll Options:** Once a scroll gesture is recorded, you can configure:
  - **Mode Selector:** Choose between **One-shot** (scrolls $X$ notches once on button press) and **Continuous** (scrolls $X$ notches every $Y$ seconds when held).
  - **Interactive Notch Tester:** Physically scroll inside the tester area to set how many notches you want to map. Scrolling up adds notches, and scrolling down subtracts notches (clamped to a minimum of 1).
  - **Manual Repeat Interval:** Type in the custom speed in seconds.
- **Continuous Repeating Scrolls:** Mapped scrolls now smoothly repeat at your custom rate (default 20Hz) while holding down the gamepad button.

### 3. Unified Verbose Debug Logging
- **Diagnostic Launchers:** Added `calibrate_debug.bat` and `run_wrapper_debug.bat` scripts to run the tools in debug mode with a single double-click.
- **Separate Overwritten Logs:** Running in debug mode generates fresh `wrapper.log` and `calibration.log` files. High-frequency HID data is rate-limited (every 0.5s) to prevent bloating log file sizes.
- **Inherited Process Logging:** The GUI automatically inherits the debug flag from the wrapper, appending its own logs directly into `wrapper.log` to provide a unified timeline.

### 4. PolyForm Noncommercial License 1.0.0
- **Legal Protection:** Added a formal `LICENSE` file under the PolyForm Noncommercial License 1.0.0 framework, strictly prohibiting commercial usage of this software while allowing free personal copying and modifications (requires attribution to jesga06).

### 5. Fixed Calibration Wakeup Bug
- **Wakeup Fix:** Resolved an issue in the calibration setup phase where inputs from the physical controller were ignored, preventing calibration from proceeding.

### 6. Zero-Flicker Test Environment & ASCII Joysticks
- **Quick Test Script:** Added `test_calibration.bat` which launches the calibration tester instantly, bypassing the setup phase.
- **Fluid Terminal UI:** Replaced the subprocess-based console clearing with native Windows ANSI escape sequences, resulting in completely static and flicker-free live test outputs.
- **ASCII Joysticks & Triggers:** The test mode now features a 2D 5x5 ASCII grid visualization for both analog sticks, and a vertical meter for triggers, making it far easier to visualize physical deadzones and stick ranges than reading raw 0-255 integers.

### 7. Dynamic Visual Layouts
- **Custom Face Buttons:** You can now toggle the visual representation of your controller's face buttons across the entire application.
- **Supported Options:** Xbox (A/B/X/Y, LS/RS), PlayStation (X/O/■/▲, L3/R3), and Nintendo (B/A/Y/X, LS/RS).
- **GUI Integration:** A new dropdown in the GUI Dashboard tab allows you to switch layouts dynamically. The Remapping tab updates its labels on the fly.
- **Calibration Integration:** The command-line calibration wizard prompts you to select a visual button layout immediately after device selection, saving this preference directly to the generated device profile JSON. The wizard's prompts and the test mode will automatically use this layout.

### 8. Opt-Out XInput Button Blocking
- **Blocking Toggles:** A new "Block XInput" checkbox column has been added to the Remapping tab. It allows you to opt-out of blocking standard controller buttons on the virtual Xbox controller when they are mapped to keyboard/mouse actions (preventing double binding by default).
- **Trigger Blocking Support:** Analog triggers (`lt` and `rt`) can now also be blocked on the virtual gamepad when remapped to custom inputs, using the same opt-out checkbox state.

### 9. Digital Triggers & Instant Sensitivity (Opt-In)
- **Binary Trigger Conversion:** Added a "Digital Trigger" checkbox next to the analog triggers (`lt` and `rt`) to convert them to binary (either 0 or 255) inputs.
- **Hair-Trigger Responsiveness:** The digital trigger check threshold has been lowered to `> 0` (instead of `> 30`) to trigger instantly upon the slightest touch.

### 10. Quadrant GUI Remapping Panel & Size Increase
- **Visual Quadrants:** Split the remapping screen into four clean, categorized quadrants (Face Buttons, D-Pad, Shoulders & Sticks, System & Extras) using individual static frames.
- **Starting Dimensions:** Increased standard GUI starting window size to `900x700` (up from `650x500`) to guarantee that all mapping fields and checkbox columns fit comfortably without being cut off.

### 11. Smart HID Reconnection
- **Reconnection Loop:** If your physical controller becomes disconnected, the daemon enters a connection recovery loop for 20 seconds, scanning for a device with the exact same name to seamlessly reconnect.
- **Timeout Protection:** If the device is not reconnected within 20 seconds, the wrapper and GUI processes will exit cleanly.

---

## ⚙️ Technical & Developer Changes

### 1. Centralized Logger & Unified Logging Pipeline
- Built `src/logger_setup.py` to unify file/console logging formatting, debug level switching, and log file streams.
- Connected the subprocess IPC to carry argparse flags `--log` and `--append-log` from `src/main.py` to `src/gui.py`.

### 2. Independent Timers for Repeating Scrolls
- Modified `src/mapper.py` to parse complex serialized configurations (e.g. `mouse:scroll_up:continuous:3:0.25`).
- Uses individual timestamp trackers (`last_run_time`) stored per active mapping state inside the daemon loop to execute repeating scrolls at independent custom interval frequencies.

### 3. Robust Windows API Console Restoration
- Replaced the simple `SW_SHOW` flag in the console utility with `SW_RESTORE` combined with `SetForegroundWindow` to forcibly restore the hidden window even if hard-minimized in the taskbar.

### 4. Codebase Documentation (Docstrings)
- Added file-level and class-level docstrings across all modules (`src/main.py`, `src/gui.py`, `src/mapper.py`, `src/calibration.py`, `src/decoder.py`, `src/hid_reader.py`, and `src/virtual_pad.py`) to detail class structures and data models for future project contributors.

### 5. Folder Reorganization
- Reorganized the workspace by moving all Python code files into a dedicated `src/` directory, moving the proof of concept, and leaving user entry points and metadata in the root directory. Updated batch files and python pathing to support the change.
