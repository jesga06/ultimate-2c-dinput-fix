## [Planned Features (Sorted by what I want to do next)]
- **Complete Vibration Implementation:** Finalize the incomplete rumble code.
- **Vibration Diagnostic Test:** Diagnostic tool `07_vibration_test.py` to test and identify rumble payloads.
- **HidHide Integration (Double Input Fix)**: Automated integration with Nefarius HidHide to completely hide physical gamepads from other applications. Includes automatic executable whitelisting and dynamic cloaking that cleanly reverts its changes when the wrapper daemon closes.
- **Advanced Features & Ecosystem**: Input recording/playback, multi-controller sync, plugin system, and gamepad HID reverse engineering tools.
- **Profiles Tab Redesign (Validation & Diff):** Redesign and re-implement profile validation and side-by-side HID map diffing in a dedicated GUI view.
- **Analog-to-Mouse & WASD Mapping:** Support for high-frequency translation of stick deflection to mouse deltas or WASD keystrokes.
- **"Magic Packet" Initialization Handshakes:** Designing an optional, power-user feature mimicking our custom rumble setup. This allows users to inject custom USB Output or Feature reports upon connection, forcing restrictive controllers (e.g. DualSense Edge, Switch Pro) to wake up out of "Compatibility Mode" and expose their raw extra buttons and high-frequency telemetry.
- **Windows Startup Integration:** Registry integration to launch the wrapper daemon silently on boot.
- **Gyroscope Support:** Native support for capturing and translating gyroscope/motion telemetry (will take a while because I don't have a controller with gyro support).
- **DS4 Emulation:** Support for instantiating `vg.VDS4Gamepad()` for native PlayStation in-game prompts.
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
- **Circularity Calibration:** Added a circularity calibration module in the Tuning tab to mathematically correct and enforce perfect circular outputs for analog sticks.
- **Dynamic Shift-Key Selection:** The shift-key selection dropdown in the GUI now dynamically populates based on the specific device profile instead of using hardcoded buttons.
- **Specific Key Remapping Info:** Added an informational box to the Remapping tab to clarify specific key mappings.

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
- **GUI Lagginess Fix:** Applied a bandage fix to alleviate severe lagginess in the Graphical User Interface.
- **Silent Boot Argument:** Added a `--boot` argument to `main.py` which allows the wrapper daemon to start silently on boot (e.g. for Windows startup) without automatically opening the GUI.
- **Documentation Organization:** Restructured project documentation and added technical timelines for developers (and curious people).
- **Digital Trigger Fallback Detection:** Upgraded the calibration wizard's digital trigger fallback detection to intelligently isolate bitmasks and cross-reference unique byte states, making it far more accurate at detecting non-analog triggers.

## [2.1.0] - 2026-07-17
This release introduces major UI Customizations, Utilities, and Core Profile features.

### 🎮 User-Facing Changes
- **Customization Tab:** A brand new tab enabling Light/Dark mode toggling, dynamic theme switching (White, Orange, Red, Yellow, Green, Blue, Purple), and system font selection.
- **Profile Tab:** A centralized hub to validate your JSON configurations, generate interactive git-style profile comparisons (diffs) against system defaults, and export configurations directly.
- **Utilities Tab:** A powerful diagnostic workspace containing real-time polling rate monitors, synthetic throughput benchmarks, live input inspection, and a dynamic hardware latency estimator.
- **Advanced Analog Curves:** Implemented Cubic, Sigmoid, Bezier, and a Custom mathematical equation evaluator for joysticks and triggers.
- **Custom Curve UI:** Easily enter your own mathematical response formula (e.g. `x**power`) directly in the GUI and preview its shape instantly on the graph. Includes a `[?]` helper box detailing the syntax.
- **Trigger Sensitivity:** Analog triggers now have functional sensitivity sliders in the Tuning tab, matching the joysticks.
- **Calibration Confidence Engine:** The calibration wizard now grades your gamepad's structural integrity (circularity, deadzone sizes, center precision) at the end of the profile generation phase.
- **Export Math:** Quickly copy LaTeX representations of your generated response curves directly to your clipboard for sharing or graphing in Desmos.
- **Shift Key Bindings Fix:** Resolved an issue where shift key mappings failed to trigger. The mapping engine was corrected to read configuration settings from the proper `shift_layer` and `shift_mappings` sections instead of the incorrect `settings` and `layer_shift` sections.
- **Terminology Refactor:** Standardized files and labels to resolve "profile" ambiguity: hardware input descriptors (`{VID}_{PID}.json`) are now **HID maps**, user preferences/remaps (`{device-name}.json`) are **user profiles**, and general program settings (`config.ini`) are **wrapper configs**.
- **Interactive Dotted Curves:** Introduced a second type of custom response curve alongside fully custom ones, allowing users to define a set number of dots on the graph and drag them to shape the curves interactively.
- **Selective Community Map Downloads:** Integrated the live repository (`jesga06/UR-XD-community-HID-maps`). Instead of downloading a full ZIP, the app downloads only the index (`database.json`) first, then selectively fetches only the specific HID maps matching connected controllers.
- **Auto-Update Scheduler:** Added configuration options under UI Customization to check for community HID map updates periodically (1 to 30 days) independent of run frequency, including a status indicator and a "Force Update Now" button.
- **Version Number In UI:** Added version number to the GUI's dashboard.

### ⚙️ Under-the-Hood Changes
- **Dynamic Theme Interpolation:** Re-engineered GUI canvas drawing methods to automatically query the `ctk.ThemeManager.theme` for current accent colors. Automatically inverses hex codes to dynamically color raw input and processed output tracers.
- **Python `eval` Safe Context:** Created a localized, restricted dictionary environment to safely evaluate custom user mathematical strings without exposing `__builtins__`.
- **System Fonts Override:** Implemented a global intercept on CustomTkinter's `CTkFont` class to force all widgets to inherit the user's selected font dynamically.
- **Matplotlib Integration:** Integrated `matplotlib.backends.backend_tkagg` into the Utilities tab to handle real-time rendering of the generic oscilloscope without bogging down the main GUI loop.
- **Performance Fixes:** Optimized `update_position_loop` tick rates and removed expensive console standard output flushing to preserve high-frequency graphing performance.
- **`custom_eq` Parameter Routing:** Upgraded `math_utils.process_analog_stick` and `process_trigger` to natively accept and parse string equations down into `curves.evaluate_curve`.
- **Community Fetcher API:** Rewrote `community_fetcher.py` to request individual files from the GitHub raw content network. Added `fetch_database` and `fetch_maps_for_devices` to handle the phased selective download pipeline.
- **Persistent Update Tracking:** Added `db_last_updated` Unix timestamp and `db_update_interval_days` keys in `config.ini` under a new `[community]` section to maintain scheduling states across daemon launches.
- **Startup Bootstrapping:** Updated `main.py` to check for and fetch the community index file automatically if missing on startup, ensuring fallback mapping works correctly on clean installs.
- **Terminology Propagation:** Renamed validation and diagnostic modules (`validate_profile` → `validate_hid_map`, `diff_profiles` → `diff_hid_maps`) and local references throughout the codebase.
- **Corrected GUI Configuration Reference:** Updated the dashboard's "Validate HID Map" validation query to reference `self.daemon_config` rather than `self.config` to resolve config key lookup errors.
- **Synchronized HID Map Method Names:** Updated `gui.py`'s Profiles tab utility references to point to `validate_hid_map` and `diff_hid_maps` instead of their deprecated method names.
- **Commit Commenting:** I actually do commented atomic commits now. Even the commit that adds this line was commented. Learned to do so the hard way.

## [2.2.0] - Unreleased
### 🎮 User-Facing Changes
- **Circularity Calibration & Wizard Enhancements:**
  - Added a toggleable 45º diagonal reference line on response graphs.
  - Added a dashed circular bounds guide on crosshair displays mapping the 1.0 boundary in current theme colors (dark/light appearance matched).
  - Added an information overlay modal explaining circularity math and "Before" vs "After" processing configurations.
  - Guided wizard now actively tracks clockwise/counter-clockwise spins, requiring 3 full rotations in both directions before unlocking completion.
  - Integrated real-time velocity checking that flashes a warning ("Too Fast! Slow down.") if rotation speed is too high.
  - Refactored wizard completion to offer explicit "Apply Changes" and "Discard" options.
- **Hardware Chords & Input Suppression:**
  - Added a comprehensive Hardware Chords Builder to the Advanced Tab in the GUI. This allows mapping your controller's firmware chords (e.g. `LB + Start`) to synthesize virtual extra buttons upstream in the pipeline.
  - Implemented Input Suppression logic to prevent temporal bleeding. Constituent buttons used in chords are suppressed/consumed automatically, so the base action (e.g. `LB`) is not executed when a chord is triggered.
  - Integrated adjustable timing margins (0ms, 50ms, 100ms) for reliable chord execution.
- **XInput First Dual-Backend Architecture:**
  - Expanded the daemon to utilize a hot-swappable dual-backend abstraction (`backend_base.py`, `backend_xinput.py`, `backend_dinput.py`).
  - Implemented an XInput backend using `ctypes` bindings for `xinput1_4.dll` to natively read gamepads in XInput mode. This exposes hardware vibration/rumble directly without vendor-specific undocumented protocols.
  - Revamped the calibration wizard to offer a choice between "DInput (Full Calibration)", "XInput Setup", and an "Auto-Detect Mode".
  - Auto-Detect Mode seamlessly queries XInput states for specific simultaneous button presses (like `A + B`) to verify the operating mode.
  - When XInput is selected or auto-detected, the wizard explicitly prompts for extra buttons to save a profile rather than instantly terminating.
  - The wizard now intelligently auto-selects your controller and bypasses the device menu if only one HID device is connected.
  - Conditional GUI locking: Hardware Chords are actively editable when the controller is in XInput mode, but explicitly locked out when in DInput mode where physical extra buttons are normally available natively.
- **Warped Stick Correction:** Added a "Warp Threshold" slider (0-20%) that dynamically stretches weak thumbstick axes to reach 1.0 maximum deflection without hard-clipping.
- **Proportional Gamepad Test Dashboard & Layout Builder:** Added a responsive, auto-scaling gamepad layout dashboard mapping physical and extra buttons based on configured layout resources (Xbox, PlayStation, etc.). Includes an interactive drag-and-drop Layout Builder tool (`scratch/interactive_layout_builder.py`) equipped with a configurable background grid slider (5px to 20px) and automatic snap-to-grid alignment.
- **Interactive Recorder Save Targets:** Added explicit "Save Standard" and "Save Shift Map" buttons inside the mapping recorder to assign inputs to standard or shift layers.
- **Dynamic Color Legends:** tooltips now query the active interface theme (Purple, Red, Blue, etc.) to reference raw/processed indicators dynamically.
- **Digital Trigger response Graph:** The Tuning tab now displays trigger curves in digital mode as a clean step-function based on deadzone thresholds.
- **Tuning Graphs & Sensitivity Real-time Updates:** Bind sensitivity sliders to dynamically redraw stick and trigger graphs.
- **Retroactive Button Name Normalization:** Standardize all button names to uppercase client-side and retroactively across configuration settings.
- **Consolidated Batch Launchers & Tools Menu:**
  - Added absolute path locking (`cd /d "%~dp0"`) to `run_wrapper.bat` and `calibrate.bat` so end users can launch them via shortcuts or double-clicks without terminal errors.
  - Added an interactive `tools_and_diagnostics.bat` entry point grouping all auxiliary tools, debug launchers, live input visualizer (`src/calibration.py --test-only`), standalone Python utilities (such as the Interactive Layout Builder), dependency installation scripts, and individual diagnostic steps in a clean menu.
  - Cleaned up redundant standalone `.bat` files (`run_wrapper_debug.bat`, `calibrate_debug.bat`, `test_calibration.bat`, `install_requirements.bat`).
- **Community HID Map Name Clean-up:** Fixed an issue where the string " (Community HID Map)" was incorrectly appended to the device name when creating a new user profile.
- **Vertically Scrollable GUI Tabs:** Wrapped all GUI tabs (Dashboard, Profile, Remapping, Tuning, Advanced, Utilities, Customization) in vertical `CTkScrollableFrame` containers, ensuring all controls and diagnostics remain fully accessible and visible via scrolling regardless of window size.
- **Chords & Hardware Chords Master Tutorial, Ghost Text & Recording Fixes:** Refined the Advanced Tab tutorial card and interactive modal guide (`open_chords_guide_modal`) with clear descriptions, exact GUI field names, D-Pad placeholder text (`dpad_up`, `dpad_down`), and explicit Save Settings warnings. Fixed Hardware Chord action buttons not appearing in the Remapping tab, and upgraded the macro recorder modal with live gamepad polling, mouse click/scroll listeners, and quick-add buttons.
- **Hardware Chords Multi-Delimiter & Extra Button Release Tracking Fixes:** Fixed multi-button hardware chords (e.g. 3 D-Pad inputs) failing to match by supporting comma (`,`), plus (`+`), and space delimiters in `HardwareChordEngine`. Fixed extra button remap execution in `Mapper` by pre-populating all extra keys to `False` in `process()` so released extra buttons trigger `_release()` and clear `prev_state`. Added raw key string fallback handling to `_press()` and `_release()` and updated guide modals to document all available split delimiters.
- **Removal of Profiles Tab & Input Recording Utility:**
  - Removed the dedicated Profiles tab from the GUI and the "Input Recording & Playback" utility frame from the Utilities tab.
  - Decommissioned background state recording/playback routines from the daemon loop (`src/main.py`) and removed `src/state_record_play.py`.
  - These features were removed because they did not turn out as initially planned. They have been re-added to `workspace_ideas/to-do-list.md` for future architectural redesign and re-implementation.
- **Dashboard Extra Buttons Centering & Hardware Chord Telemetry Highlighting:** Centered the extra buttons row on the Dashboard tab within an anchored sub-container frame. Added real-time telemetry illumination for Hardware Chord action buttons when triggered in XInput mode, lighting up the active button chip in vibrant accent color.
- **Macros Engine Upgrades (Name-Based Remapping, Gamepad Outputs & Optional Triggers):**
  - Renamed standard chords to "Macros Engine" across the GUI, tutorials, and configuration labels.
  - Added support for referencing macros by name directly in the Remapping tab (e.g. `macro:MyMacro` or `MyMacro`).
  - Made input trigger chords optional for macros, allowing users to define standalone macros triggered solely via button remapping.
  - Expanded macro outputs to support gamepad button presses (`gamepad:a`, `gamepad:lb`, etc.) alongside KBM actions and delays.
  - Upgraded the macro recording modal (`[Rec]`) to record gamepad button presses and provide gamepad quick-add buttons when recording macro outputs.
  - Updated the Remapping tab info tooltip and added an interactive modal guide (`open_remapping_guide_modal`) documenting keyboard/mouse syntax, macro referencing (`macro:MyMacro`), input blocking, and Shift layer usage.

### ⚙️ Under-the-Hood Changes
- **Unified Verbose Debug Logging Expansion:** Expanded the `--debug` argument parsing and granular `logger.debug` tracing across all core processing scripts (`mapper.py`, `decoder.py`, `virtual_pad.py`, `hardware_chords.py`), backend scripts (`backend_dinput.py`, `backend_xinput.py`), and all 6 automated diagnostic scripts. Added full `sys.excepthook` stack trace injection for diagnostic scripts in debug mode.
- **Circularity On-Finish Callbacks:** Programmed an `on_finish` callback flow to refresh GUI plots and configuration states immediately when circularity changes are applied.
- **Hardware Chords Engine Unification:** Re-architected `main.py` pipeline sequence to `HardwareChordEngine -> Mapper -> VirtualPad`, ensuring synthesized extra buttons seamlessly enter the mapper as standard input vectors.
- **XInput API Ordinal Fetch:** Resolved a ctypes `AttributeError` by correctly loading the undocumented XInput guide button state via ordinal `#100` rather than passing an integer to `getattr`.
- **Diagnostic Test Coverage:** Implemented unit tests for the newly added `HardwareChordEngine` and modernized the `test_diagnostics.py` suite to correctly mock Cython `hidapi` imports across environments without drivers installed.
- **Profile Mode Specificity:** Upgraded `config_manager.py` to route backend-specific configurations automatically (e.g. loading `{device}_xinput.json` or `{device}_dinput.json` based on the active backend mode).
- **Diagonal Response Curve Math:** Refactored graph rendering to mathematically evaluate diagonal deflection vectors across warped stick corrections, circularity boundaries (before/after), deadzones, and sensitivities.
- **Dynamic Extra Button Parsing:** The GUI now parses `extra_buttons` directly from the active HID map dynamically at launch, properly recognizing all supported extra buttons from downloaded community profiles instead of failing to populate them when they aren't yet mapped in the user's config file.
- **Config Attribute Error Fix:** Fixed an `AttributeError` in `main.py` caused by accessing the `.config` attribute of `ControllerConfig` instead of `.data` when determining backend mode.
- **Console Spam Reduction:** Silenced the expected "Read failed instantly" print statements in `hid_reader.py` that occurred when gracefully ignoring locked system composite interfaces (like keyboards) during device discovery.
- **Dashboard Button Flickering:** Fixed an issue where the GUI dashboard buttons would continuously redraw and flicker as gray boxes due to constant fg_color updates.
- **UDP Button Broadcasting:** Fixed a bug in utilities_backend.py where live button state was excluded from the UDP payload, preventing the GUI from visually reflecting button presses.
- **Diagnostic Tool Arguments:** Changed the incorrect --debug parameter to the supported --log parameter in tools_and_diagnostics.bat, restoring functionality for the debug wrappers.
- **XInput Calibration Priority:** Updated the calibration wizards and diagnostic tools to highlight interfaces containing 'microsoft' or 'controller' in their name as the recommended endpoints to select for retrieving button data from XInput controllers.
- **Static Gray Box Fix:** Fixed a UI overlapping issue in CustomTkinter where `extra_frame` created a static gray box overlaying the dashboard buttons by packing it outside the main layout canvas.
- **XInput Controller Latching & Polling Resilience:**
  - Resolved a critical bug where `XInputGetStateEx` (ordinal 100) failures would break out of the polling thread on frame 1, causing XInput controllers to report connected while reading zero inputs. Added fallback to standard `XInputGetState` and failure thresholding before marking disconnected.
  - Implemented an automatic reconnection loop in `backend_xinput.py` that continuously retries slot binding when a controller drops instead of terminating the thread.
  - Locked slot initialization to prevent the daemon from latching onto the virtual Xbox 360 controller created by `vgamepad`.
  - Updated `VirtualPad` button blocking to check `layer_base` and `layer_shift` in addition to legacy `extra_buttons`.
  - Standardized stick Y-axis polarity across backends to positive-UP, preventing inverted stick input on virtual controllers.
  - Added `lt` and `rt` trigger support to `HardwareChordEngine`.
- **GUI Real-Time Telemetry Listener & Flickering Resolution:**
  - Added a UDP broadcast receiver thread to `gui.py` listening on port 9999 (plus standalone `XInputBackend` fallback), ensuring the dashboard buttons, tuning bars, and response curve cursors update in real time when XInput controllers are connected.
  - Eliminated GUI input flickering caused by concurrent thread contention between the daemon's UDP broadcast and the GUI's standalone background listener by introducing daemon stream priority.
  - Added a 0.39% (+/- 128 raw units) hardware rest noise snap in `backend_xinput.py` so untouched XInput sticks report clean `0.0` center alignment rather than uncentered noise (`0.00317`).
- **Circularity Calibration Y-Axis Fix:** Corrected inverted Y stick directions in `circularity_modal.py` by removing unnecessary Y-axis negation in `get_raw_input()`, ensuring raw inputs, center sampling, bounds calculation, and canvas rendering use positive-UP Y polarity consistent with standard controller telemetry.
- **GUI Tab Widget Duplication Fix:** Resolved a bug where refreshing tab layouts (e.g. calling `setup_remapping()` when updating hardware chords or shift triggers) packed duplicate `CTkScrollableFrame` containers into the tab without destroying previous instances. Added a child widget cleanup loop (`winfo_children().destroy()`) across all tab setup routines to eliminate split scrollbars and tab layout duplication.
- **Instant Response Curve Graph Redraws:** Fixed an issue where toggling "Digital Trigger Mode" or changing "Circularity Mode" in the Tuning tab did not visually update the response curve graph canvas unless the Reset button was pressed. Redraw callbacks now execute immediately upon toggling digital triggers or changing stick circularity options, while preserving custom stick warp thresholds.
