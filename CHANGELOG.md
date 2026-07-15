# Changelog

Here is a detailed breakdown of all the changes, features, and improvements made to the project since the last commit, separated into what you'll notice when using the app, and the under-the-hood technical architecture changes.

## 🎮 User-Noticeable Changes

### 1. The New Configuration GUI
- **Modern Interface:** Added a simple, dark-mode graphical user interface (`gui.py`)
- **Live Connection Status:** The GUI features a Dashboard that displays real-time connection status of your controller (e.g., "Connected - 8BitDo Ultimate 2C").
- **Visual Remapping:** You can now visually remap *any* button (standard or extra paddle) directly from the GUI without ever touching a text file.

### 2. Silent System Tray Operation
- **No More Command Prompt:** When you run the application (`main.py`), the command prompt is now instantly hidden.
- **Taskbar Icon:** The app runs silently in the background as a system tray icon.
- **Easy Access:** You can right-click the tray icon to quickly launch the new Configuration GUI, show the debug console, or quit the application.

### 3. Live "On-The-Fly" Updates
- Changes made in the GUI (or manually in `config.ini`) are now applied **instantly**. The background app checks for updates every 5 seconds, meaning you no longer have to restart the script when tweaking your mappings!

### 4. Full Button Remapping
- **Remap Anything:** You are no longer limited to just remapping the back paddles. You can now map the 'A' button, D-Pad, Triggers, or any standard button to a Keyboard Key or Mouse Click.
- **Keyboard Key Combos:** You can chain multiple keys together with a `+` symbol (e.g. `keyboard:shift+o` or `keyboard:ctrl+alt+delete`). They will be pressed sequentially and released in reverse order.
- **Double-Input Prevention:** If you remap a standard button (like 'A'), the application intelligently **blocks** that button from being sent to the virtual Xbox controller, preventing conflicts in your games.

### 5. Interactive Calibration Tool (`calibration.py`)
- **Universal Support:** You can now add support for almost *any* generic generic HID controller by running the calibration tool.
- **Auto-Detect:** When picking a controller to calibrate, you can simply **press a button** on the controller instead of typing its index number to select it.
- **Robust Prompts:** The tool asks you to press each button step-by-step, automatically detecting which byte/bit corresponds to that button. It also safely ignores accidental double-inputs or joystick drift.
- **Error Handling:** The tool now gracefully handles invalid typos, allows you to type 'q' to quit, and prevents the "controller asleep" spam that previously flooded the terminal.

---

## ⚙️ Technical & Developer Changes

### 1. Architecture Overhaul: Dynamic Profiles
- The project has moved away from a hardcoded controller implementation. 
- Created a `profiles/` directory that stores JSON representations of a controller's HID structure (VID, PID, button masks, axis byte indices).
- `main.py` now scans connected USB devices and auto-selects the first one that has a matching JSON profile.

### 2. Decoder Rewrite (`decoder.py`)
- Rewrote the `Decoder` class to be completely generic. It now parses the active JSON profile to figure out how to translate a raw HID byte array into a unified `ControllerState` dataclass.
- Supports decoding standard buttons, Hat switches (D-pad), continuous axes (sticks/triggers), and an arbitrary number of dynamically defined "extra" buttons.

### 3. Split-Process GUI Architecture
- Implemented a dual-process architecture to avoid thread-locking issues between `pystray` (System Tray) and `tkinter` (GUI). 
- `main.py` runs the HID listener and tray icon on separate threads.
- `gui.py` runs as a completely independent process, spawned via `subprocess.Popen` from the tray menu. It modifies `config.ini`, which the daemon polls.
- Implemented a lightweight IPC (Inter-Process Communication) via a `status.json` file, allowing `main.py` to broadcast its connection state to the GUI.

### 4. Code Hardening & Exception Handling
- Added comprehensive `try...except` blocks across `main.py`, `calibration.py`, and `decoder.py` to gracefully handle corrupt JSON files, missing ViGEmBus drivers, and inaccessible USB devices.

### 5. Dependency Updates
- Added `pystray` and `Pillow` for system tray and icon management.
- Added `customtkinter` for the modern graphical user interface.
- Updated `requirements.txt` to reflect these new dependencies.
