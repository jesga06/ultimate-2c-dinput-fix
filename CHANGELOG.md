## [Planned Features]
- **Gyroscope Support:** Native support for capturing and translating gyroscope/motion telemetry.
- **DS4 Emulation:** Support for instantiating `vg.VDS4Gamepad()` for native PlayStation in-game prompts.
- **Analog-to-Mouse & WASD Mapping:** Support for high-frequency translation of stick deflection to mouse deltas or WASD keystrokes.
- **Windows Startup Integration:** Registry integration to launch the wrapper daemon silently on boot.
- **Built-in Community Profiles:** Auto-discovery database to bypass calibration for common VID/PIDs using pre-made templates.
- **"Magic Packet" Initialization Handshakes:** Designing an optional, power-user feature mimicking our custom rumble setup. This allows users to inject custom USB Output or Feature reports upon connection, forcing restrictive controllers (e.g. DualSense Edge, Switch Pro) to wake up out of "Compatibility Mode" and expose their raw extra buttons and high-frequency telemetry.
- **Vibration Diagnostic Test:** Diagnostic tool `07_vibration_test.py` to test and identify rumble payloads.
- **UI/Customization & Basic QoL**: Analog sensitivity slider, theme customization, and font changes.
- **Core Profiles & Inputs**: Calibration confidence, profile validator/comparison/export, new stick/trigger curves.
- **Utilities Tab**: Polling rate & latency monitors, built-in benchmark, generic input graph, and input inspector.
- **Advanced Features & Ecosystem**: Input recording/playback, multi-controller sync, plugin system, and reverse engineering tools.
- **GUI Optimization Pass**: Find out why this hot mess of a GUI is so damn laggy. 


## NOTES
This list orders updates from oldest-first to newest-last. For the most recent updates, scroll all the way down.

## [1.0.0] - 2026-07-15
This is the official 1.0.0 release of the universal HID-to-XInput wrapper. It brings the wrapper from a hardcoded script to a robust, user-friendly, and customizable daemon.

Here is a detailed breakdown of the latest changes, features, and improvements made to the project since the last commit, separated into what you'll notice when using the app, and the under-the-hood technical architecture changes.

### 🎮 User-Facing Changes

#### 1. Interactive Calibration Tool (`src/calibration.py`)
- **Universal Support:** You can now add support for almost *any* generic HID controller by running the calibration tool.

#### 2. Interactive Input Recording & Advanced Mouse Scroll
- **Interactive Remap Recorder:** You can click the "⏺ Record" button in the GUI to capture keyboard combos and mouse buttons instead of typing them. Left-click is ignored to allow clicking UI buttons safely.
- **Advanced Scroll Options:** Once a scroll gesture is recorded, you can configure:
  - **Mode Selector:** Choose between **One-shot** (scrolls $X$ notches once on button press) and **Continuous** (scrolls $X$ notches every $Y$ seconds when held).
  - **Interactive Notch Tester:** Physically scroll inside the tester area to set how many notches you want to map. Scrolling up adds notches, and scrolling down subtracts notches (clamped to a minimum of 1).
  - **Manual Repeat Interval:** Type in the custom speed in seconds.
- **Continuous Repeating Scrolls:** Mapped scrolls now smoothly repeat at your custom rate (default 20Hz) while holding down the gamepad button.

#### 3. Unified Verbose Debug Logging
- **Diagnostic Launchers:** Added `calibrate_debug.bat` and `run_wrapper_debug.bat` scripts to run the tools in debug mode with a single double-click.
- **Separate Overwritten Logs:** Running in debug mode generates fresh `wrapper.log` and `calibration.log` files. High-frequency HID data is rate-limited (every 0.5s) to prevent bloating log file sizes.
- **Inherited Process Logging:** The GUI automatically inherits the debug flag from the wrapper, appending its own logs directly into `wrapper.log` to provide a unified timeline.

#### 4. PolyForm Noncommercial License 1.0.0
- **Legal Protection:** Added a formal `LICENSE` file under the PolyForm Noncommercial License 1.0.0 framework, strictly prohibiting commercial usage of this software while allowing free personal copying and modifications (requires attribution to jesga06).

#### 5. Fixed Calibration Wakeup Bug
- **Wakeup Fix:** Resolved an issue in the calibration setup phase where inputs from the physical controller were ignored, preventing calibration from proceeding.

#### 6. Zero-Flicker Test Environment & ASCII Joysticks
- **Quick Test Script:** Added `test_calibration.bat` which launches the calibration tester instantly, bypassing the setup phase.
- **Fluid Terminal UI:** Replaced the subprocess-based console clearing with native Windows ANSI escape sequences, resulting in completely static and flicker-free live test outputs.
- **ASCII Joysticks & Triggers:** The test mode now features a 2D 5x5 ASCII grid visualization for both analog sticks, and a vertical meter for triggers, making it far easier to visualize physical deadzones and stick ranges than reading raw 0-255 integers.

#### 7. Dynamic Visual Layouts
- **Custom Face Buttons:** You can now toggle the visual representation of your controller's face buttons across the entire application.
- **Supported Options:** Xbox (A/B/X/Y, LS/RS), PlayStation (X/O/■/▲, L3/R3), and Nintendo (B/A/Y/X, LS/RS).
- **GUI Integration:** A new dropdown in the GUI Dashboard tab allows you to switch layouts dynamically. The Remapping tab updates its labels on the fly.
- **Calibration Integration:** The command-line calibration wizard prompts you to select a visual button layout immediately after device selection, saving this preference directly to the generated device profile JSON. The wizard's prompts and the test mode will automatically use this layout.

#### 8. Opt-Out XInput Button Blocking
- **Blocking Toggles:** A new "Block XInput" checkbox column has been added to the Remapping tab. It allows you to opt-out of blocking standard controller buttons on the virtual Xbox controller when they are mapped to keyboard/mouse actions (preventing double binding by default).
- **Trigger Blocking Support:** Analog triggers (`lt` and `rt`) can now also be blocked on the virtual gamepad when remapped to custom inputs, using the same opt-out checkbox state.

#### 9. Digital Triggers & Instant Sensitivity (Opt-In)
- **Binary Trigger Conversion:** Added a "Digital Trigger" checkbox next to the analog triggers (`lt` and `rt`) to convert them to binary (either 0 or 255) inputs.
- **Hair-Trigger Responsiveness:** The digital trigger check threshold has been lowered to `> 0` (instead of `> 30`) to trigger instantly upon the slightest touch.

#### 10. Quadrant GUI Remapping Panel & Size Increase
- **Visual Quadrants:** Split the remapping screen into four clean, categorized quadrants (Face Buttons, D-Pad, Shoulders & Sticks, System & Extras) using individual static frames.
- **Starting Dimensions:** Increased standard GUI starting window size to `900x700` (up from `650x500`) to guarantee that all mapping fields and checkbox columns fit comfortably without being cut off.

#### 11. Smart HID Reconnection
- **Reconnection Loop:** If your physical controller becomes disconnected, the daemon enters a connection recovery loop for 20 seconds, scanning for a device with the exact same name to seamlessly reconnect.
- **Timeout Protection:** If the device is not reconnected within 20 seconds, the wrapper and GUI processes will exit cleanly.

### ⚙️ Under-the-Hood Changes

#### 1. Centralized Logger & Unified Logging Pipeline
- Built `src/logger_setup.py` to unify file/console logging formatting, debug level switching, and log file streams.
- Connected the subprocess IPC to carry argparse flags `--log` and `--append-log` from `src/main.py` to `src/gui.py`.

#### 2. Independent Timers for Repeating Scrolls
- Modified `src/mapper.py` to parse complex serialized configurations (e.g. `mouse:scroll_up:continuous:3:0.25`).
- Uses individual timestamp trackers (`last_run_time`) stored per active mapping state inside the daemon loop to execute repeating scrolls at independent custom interval frequencies.

#### 3. Robust Windows API Console Restoration
- Replaced the simple `SW_SHOW` flag in the console utility with `SW_RESTORE` combined with `SetForegroundWindow` to forcibly restore the hidden window even if hard-minimized in the taskbar.

#### 4. Codebase Documentation (Docstrings)
- Added file-level and class-level docstrings across all modules (`src/main.py`, `src/gui.py`, `src/mapper.py`, `src/calibration.py`, `src/decoder.py`, `src/hid_reader.py`, and `src/virtual_pad.py`) to detail class structures and data models for future project contributors.

#### 5. Folder Reorganization
- Reorganized the workspace by moving all Python code files into a dedicated `src/` directory, moving the proof of concept, and leaving user entry points and metadata in the root directory. Updated batch files and python pathing to support the change.

#### 6. Safe Analog Stick Math (Overflow Fix)
- Resolved integer overflow bug where scaling the `0-255` raw range to XInput's `[-32768, 32767]` range produced exactly `+32768` at stick extremes, wrapping to `-32768` (hard down) in the ctypes bindings. Implemented Y-axis inversion *before* scaling and strictly clamped final values to standard boundaries.

#### 7. pywinusb Report ID Off-by-One Resolution
- Handled 0-indexed data array shifting when the Report ID byte is stripped by the HID driver, resolving an off-by-one error where stick and button data were parsed from offset channels.

#### 8. Configurable Xbox Guide Button Mapping
- Allowed passing the Home button state dynamically to the virtual gamepad mapping (`home = guide`), enabling remapping of the Xbox Guide button to keyboard/mouse actions without losing standard guide functionality by default.

## [2.0.0] - 2026-07-16
This is a major architectural release (v2.0.0) that breaks backward compatibility with old profiles, but fundamentally transforms the wrapper into a robust, profile-driven generic HID translation framework. It swaps out the legacy `pywinusb` backend for Cython's `hidapi`, introducing a high-frequency polling daemon thread and a fully generic, metadata-driven decoder layer. Furthermore, it introduces ***EXPERIMENTAL*** robust force feedback/rumble support for power users, a comprehensive automated diagnostic suite, dark purple custom GUI themes, and significant auto-reconnection and bug-fixing refinements.

### 🎮 User-Facing Changes
- **Interactive Rumble Calibration:** Added a guided wizard (`_calibrate_rumble()`) in `calibration.py` to identify Left (Heavy) and Right (Light) motor bytes by interactively vibrating the controller and prompting the user.
- **Interactive Guided Calibration:** The calibration wizard was refactored into a (hopefully) foolproof, step-by-step wizard. Prompts the user to press standard buttons, extra buttons, and joysticks. Includes a "Magic Filter" dynamic heuristic to mathematically eliminate analog axis and gyro noise during digital button/click calibration. Re-engineered stick click (`L3`/`R3`) calibration with a stateful debounce and 3-press confirmation requirement. Integrates a Manual Interface Selection fallback phase.
- **Manual Gyro/Motion Stream Query:** The calibration wizard now explicitly prompts whether a controller constantly streams gyroscope/motion data, avoiding auto-detection issues with noisy sensors.
- **Smart Parallel Calibration Wizard:** Refactored the auto-detector to spawn background threads listening to *all* discovered HID paths concurrently. You can now press a button on the controller during the menu to automatically choose your gamepad interface.
- **Fluid Float-based Tester Grid:** Reconfigured the ANSI visual test grid to correctly render the float-based joystick/trigger positions in real time.
- **Remapping Tab Upgrades:** Added dedicated "Shift Mapping" and "Shift Block" configurations natively next to every base button. Adjusted spacing for readability and added master `[?]` tooltips explaining the quadrants.
- **Analog Tuning Visuals:** Unclamped the visual joystick bounds, implementing a zoomed-out canvas overlay with a structural 1.0 unit circle. Added live decimal X and Y labels underneath the crosshair to display exact physical inputs.
- **Chords & Macros Studio:** The Advanced Tab now features a dedicated Macro Studio to record Gamepad trigger inputs and Keyboard/Mouse output sequences directly within the UI, including "Press" (Toggle) and "Hold" modes with stuck key prevention.
- **Shift Trigger Collision Safeguard:** Automatically warns, clears the base mapping, and blocks XInput if a user selects a Shift Layer trigger that is already mapped elsewhere.
- **Smooth Tab Transitions & Loading Overlay:** Introduced a polished, animated loading screen overlay when switching between tabs. Features color interpolation fades for backgrounds, text, and a custom Tkinter Canvas-drawn rotating spinner.
- **Randomized Loading Screen Quotes:** Shows a random and hopefully funny quote on every tab change. Acts like a small visual distraction while the GUI loads.
- **Automated Issue Reporter (`generate_issue_report.bat`):** A robust wizard that runs through 6 comprehensive diagnostic tests sequentially, culminating in an automatically zipped `issue_report.zip` package containing all generated logs.
- **Handshake Setup Guide:** Drafted an ***EXPERIMENTAL*** user guide (`HANDSHAKE_SETUP.md`) detailing how to sniff proprietary Magic Packets using Wireshark.
- **Advanced Analog Curves & Deadzones:** Mathematical engine for radial deadzones, exponential curves, and custom visual graphs in the GUI.
- **Action Layers & Shift Mode:** Architecture for layer-switching via modifier keys to double the available inputs.
- **Chorded Button Combinations:** Temporal input buffer to support multi-button press mappings (e.g. LB+RB).
- **Tuning Tab Expansion:** Renamed "Analog Tuning" to "Tuning" to reflect broader capabilities.
- **Trigger Sensitivity:** Added sensitivity sliders for analog triggers in the new Tuning tab.
- **Digital Triggers Relocated:** Moved the Digital Trigger Mode toggle from the Remapping tab to the Tuning tab for better organization alongside sensitivity controls.

### ⚙️ Under-the-Hood Changes
- **Cython `hidapi` Backend:** Completely removed `pywinusb` dependencies and migrated to `hidapi`. This bypasses Windows' aggressive HID descriptor truncation issues, allowing the wrapper to access extra buttons on any byte offset (e.g. byte 11).
- **Composite HID Interface Support:** The parser and background reader now fully support composite USB devices that spread input data across multiple HID interfaces simultaneously (such as the Machenike G5 Pro). Profiles track inputs using `interfaceNumber_reportId` as a unique composite key.
- **Background Daemon Polling Loop:** Replaced legacy event-callback architecture with a high-performance background daemon thread performing non-blocking reads up to `MAX_HID_PACKET_SIZE = 1024` bytes.
- **Transport Abstraction (`RawHIDReport`):** Decoupled the transport layer completely from the decoder. Downstream systems now strictly consume `RawHIDReport` objects containing the report ID, timestamp, and the raw unsliced payload.
- **Metadata-Driven Parser (`decoder.py`):** Eliminated all hardcoded gamepad button assumptions (like checking `a, b, x, y` lists). The decoder now dynamically evaluates inputs based entirely on the profile's keys and metadata.
- **Rich Input Types & Math Engine:** The parser now supports 16-bit values (little-endian), signedness conversions, custom bit shifting, masking, deadzones, value scaling, and inversion.
- **Normalized Floats:** Normalized joysticks to `-1.0` to `1.0` and triggers to `0.0` to `1.0` directly in `ControllerState` instead of using `0-255` integers. `virtual_pad.py` maps these natively to `vgamepad` float functions.
- **Dynamic Configuration Schema:** Profiles now nest inputs under a unified `"inputs"` dictionary per report. Features optional `"has_report_id"` parsing fallback to cleanly support devices with or without report IDs.
- **Hidden JSON Quote Resource:** Transformed the raw `loading texts.txt` file into a structured, hidden JSON resource (`src/.loading_quotes.json`) and removed the original text file from the project root.
- **Canvas-based Custom Animations (`LoadingSpinner` & `LoadingOverlay`):** Implemented custom classes in `src/gui.py` to handle dynamic rendering, canvas arc rotation, and recursive background color discovery.
- **Color Interpolation Transitions:** Engineered mathematical color interpolation algorithms to fade background, text, and canvas colors smoothly between the main window's theme state and the greyed-out loading states, natively supporting Light/Dark appearance mode shifts.
- **Tabview Callback Hooking:** Intercepted `self.tabview._segmented_button_callback` and `self.tabview._segmented_button` configurations to run the transition screen sequentially (250ms fade-in, 900ms hold, 250ms fade-out) and debounce inputs.
- **Environment Audit (`01_environment_audit.py`):** Automatically checks OS version, Python architecture, `vgamepad` virtual bus driver status, and flags legacy `pywinusb` installations to prevent conflicts.
- **Generic Device Enumeration (`02_device_enumeration.py`):** Safely enumerates all HID devices, matching them against known JSON profiles in the `profiles/` directory. Tests for exclusive OS-level locks and provides troubleshooting context if a device is inaccessible.
- **Raw Packet Visualizer (`03_raw_transport.py`):** A real-time data grid showing the raw byte stream from the controller, bypassing any decoding logic.
- **Topology Scanner (`04_report_id_scanner.py`):** Actively listens to the controller for 10 seconds to detect every unique `Report ID` and its corresponding packet length, logging the full topology.
- **Dynamic Baseline Logic Test (`05_baseline_logic_test.py`):** Tests the core math engine's ability to establish resting baselines and calculate byte-level deltas in real-time. Includes smart fallback logic for controllers that only transmit packets on input changes.
- **Diagnostics Delta Filtering:** Upgraded `03_raw_transport.py` and `04_report_id_scanner.py` to strictly log packets upon state changes (byte transitions), eliminating redundant terminal spam and massive log files.
- **Comprehensive Daemon Logging:** Injected standard Python `logging` modules across `calibration.py`, `hid_reader.py`, `virtual_pad.py`, `decoder.py`, and `mapper.py`, seamlessly routing backend warnings, device discoveries, and module errors into `wrapper.log` and `calibration.log` rather than losing them in terminal output.
- **Robust Theme Pathing:** Configured the GUI to load `purple_theme.json` using absolute paths relative to the script directory (`os.path.dirname(os.path.abspath(__file__))`), ensuring successful loading regardless of the execution working directory.
- **Fixed Startup UnboundLocalError:** Resolved a startup crash in `main.py` where a redundant local `import os` statement inside the `finally` block shadowed the global `os` module, causing an `UnboundLocalError` when accessing file paths earlier in `main()`.
- **Rumble Translation Layer:** Connected virtual XInput rumble to raw HID output reports in `main.py` using a configurable output report template and scaling factors.
- **Raw Output Reports:** Added `send_output_report` to `hid_reader.py` for writing raw byte payloads back to the HID device.
- **Smart Reconnect Guard:** Added safety logic in `hid_reader.py` to prevent infinite reconnection loops if a device fails instantly (under 2 seconds) due to OS-level permission locks.
- **Calibration Quiet Reconnects:** Disable reconnect attempts (`auto_reconnect=False`) during calibration device scanning to avoid interfering with discovery.
- **Keyboard Input Buffering & Echo Fix:** Swapped `msvcrt.getwche` for `getwch` during step-by-step calibration to stop echoing keyboard inputs. Added buffer flushing to prevent phantom inputs (e.g. from Steam Input) from skipping calibration prompts.
- **Python Version Enforcement:** Added strict version checks in batch files and runtime warnings in python scripts to restrict usage to Python 3.13 or 3.14 (due to `hidapi` compilation issues on 3.15+).
- **Unicode Terminal Crash:** Reconfigured `sys.stdout` to UTF-8 in `calibration.py` to prevent `UnicodeEncodeError` when rendering ASCII block drawing characters (`\u2592`) in Windows console.
- **Attribute Access Corrected:** Fixed `AttributeError: 'dict' object has no attribute 'vendor_id'` in `calibration.py` by switching to dictionary `.get()` calls.
- **State Name Typo:** Fixed `AttributeError: 'ControllerState' object has no attribute 'extra_buttons'` in `mapper.py` by correcting it to `extra_inputs`.
- **Diagnostics Fix:** Fixed `TypeError: print_terminal_only() got an unexpected keyword argument 'end'` in `diagnostics/03_raw_transport.py`.
- **Calibration Device Selection Lock:** Fixed a bug in `calibration.py` where the selected controller's handle was left open after device scanning, causing subsequent connection attempts to fail with "Device already opened. Error: Failed to connect to controller.".
- **Double-Open Guard:** Added a check `is_opened()` to the HID device connection logic in `hid_reader.py` to safeguard against connection crashes if a device handle is already active.
- **Dependency Conflict Resolved:** Removed the conflicting ctypes `hid` package from `requirements.txt` to prevent it from shadowing the Cython `hidapi` module (both namespace under `import hid`).
- **Optimized Debug Logging:** Refactored raw HID logging in `calibration.py` to write to debug logs only when a packet's bytes actually change, preventing duplicate data from bloating logs.
- **16-bit (High Precision) Axis Detection:** The calibrator now automatically detects high-precision 16-bit axes (like racing wheels and premium gamepads) by sliding a 2-byte evaluation window across the payload. It computes true 16-bit amplitudes to successfully ignore minor diagonal cross-contamination.
- **Signed Axis Detection:** The tool now intelligently inspects the resting `base_val` of joysticks. If an axis rests at `0` (or `0xFF`/`0xFFFF` wrapping) instead of the traditional center (`127` or `32767`), it automatically tags the axis with `"signed": True`, preventing massive camera jumps when crossing the origin.
- **Inverted Axis Polarity Detection:** Standard HID conventions assume moving RIGHT increases X, and moving UP decreases Y. The calibrator now evaluates the physical input against these rules during the guided prompts. If the values move in the opposite direction, it automatically assigns `"invert": True`.
- **Robust Hat Switch Detection:** Improved D-Pad (Hat switch) heuristics to explicitly filter for valid neutral-to-direction transitions (where the baseline is `> 7` and the current state is `<= 7`), ignoring intermediary noisy frames.
- **Cross-Contamination Anti-False-Positives:** Increased the multi-axis movement rejection threshold from `0.5` to `0.7`. This prevents digital trigger clicks (which can jump 128 units instantly) from falsely triggering contamination errors during analog axis calibration.
- **Multi-Byte Button Bitmasking:** Fortified the button detection logic to isolate and prioritize true single-bit (power-of-2) changes when a controller "leaks" analog data across multiple bytes during a physical trigger or button press.
- **Zero Hardcoded Devices:** Completely eradicated all legacy hardcoded 8BitDo references, VID/PIDs, and brand-specific logic from both `src/` and the `diagnostics/` suite. Everything is now fully generic.
- **Independent Baselines per Report ID:** The wizard now tracks independent baselines for every unique report ID the controller broadcasts, avoiding cross-contamination from alternate short reports during calibration.
- **Dynamic Profile Generation:** The wizard automatically compiles the new metadata-rich JSON profile layout on save.
- **True Radial Math Overhaul:** Fixed diagonal dot tracking and deadzone clipping by applying response curves and anti-deadzone directly to the stick's magnitude/vector instead of individual X/Y axes, guaranteeing a perfectly circular output bound.
- **Strict Profile Interface Binding:** The daemon now explicitly restricts `hidapi` polling solely to the HID interfaces defined in the controller profile, cleanly ignoring auxiliary endpoints.
- **Multi-Reader Concurrency:** The daemon now loops through and spawns concurrent background threads for all matched HID readers simultaneously.
- **Profile Metadata Enhancement:** Profiles now explicitly store `"is_analog"` metadata for triggers (True for analog, False for digital fallbacks) to clearly indicate whether the hardware itself streams analog data.
