
---
### Activity: Created Theme Generator Script
* **Target Component/Module:** UI/Customization (Milestone 1)
* **Problem/Intent:** Need multiple color themes (red, blue, green, etc.) to support the planned Theme Customization feature, but the current UI only ships with a hardcoded purple_theme.json.
* **Underlying Logic & Thought Process:** Rather than manually creating all theme files, I wrote a Python script src/generate_themes.py that reads the original purple_theme.json, recursively replaces the specific purple hex codes with matched hover/dark variants of other colors, and outputs them into a new src/themes/ directory.
* **Algorithm & Control Flow:** The script loads the template JSON, iterates through a predefined dictionary mapping color names to their main/hover/dark variants, and recursively searches the dictionary tree. When it hits one of the three known purple hex strings, it replaces it.
* **Data Input & Expected Output:** Input is purple_theme.json. Output is 6 new JSON files (red, blue, green, yellow, orange, white) populated in src/themes/.
---

---
### Activity: Implemented UI Customization Setup in GUI
* **Target Component/Module:** UI/Customization (Milestone 1)
* **Problem/Intent:** Users need a visual way to change appearance modes, switch between the new color themes, and change fonts. The GUI also needs to read these settings on launch.
* **Underlying Logic & Thought Process:** Added a new 'Customization' tab in gui.py using CTkTabview.add. Created setup_customization() which provides OptionMenus for Appearance Mode (Dark/Light/System), Accent Theme (purple, red, blue, green, yellow, orange, white), and Font (Arial, Consolas, Courier New, Segoe UI, Tahoma). Bound these dropdowns to write directly to config.ini in a [UI] section. Finally, modified the global startup logic of gui.py to read config.ini via configparser and apply set_appearance_mode and set_default_color_theme before building the UI classes.
* **Algorithm & Control Flow:** During GUI __init__, the tab is built. If a dropdown changes, it reads the current config.ini, updates/adds the [UI] section, and saves it. At script startup (before App initializes), configparser reads config.ini and dynamically points ctk.set_default_color_theme() to the themes/ directory for the matching JSON.
* **Data Input & Expected Output:** Dropdown selection triggers config.ini modifications. Restarting the app reads those modifications and shifts the entire GUI's theme and mode.
---

---
### Activity: Implemented Analog Sensitivity Multipliers
* **Target Component/Module:** UI/Customization (Milestone 1) -> gui.py, math_utils.py, virtual_pad.py
* **Problem/Intent:** Users need the ability to fine-tune the raw sensitivity (scaling factor) of their joysticks and triggers, which is crucial for mouse-translation or oversensitive hardware.
* **Underlying Logic & Thought Process:** I added a new parameter sensitivity to process_analog_stick and process_trigger in math_utils.py that multiplies the final output magnitude. I updated gui.py to add a new sens_var slider to both the Stick and Trigger configuration panels in the 'Tuning' tab, ranging from 0.1 to 5.0. I then updated virtual_pad.py to parse this sensitivity key from the controller's JSON profile and pass it securely into the math engine during the main process() loop.
* **Algorithm & Control Flow:** In gui.py, adjusting the slider modifies config.ini in real time and re-draws the visual curve. In the daemon loop, virtual_pad.py reads ls_sens, rs_sens, lt_sens, and rt_sens during initialization. During process(), it feeds these values to math_utils which calculates final_mag * sensitivity before returning the simulated XInput state.
* **Data Input & Expected Output:** Input is a float slider [0.1, 5.0]. Output is a directly scaled gamepad axis output.
---

---
### Activity: Implemented Advanced Curves and LaTeX Export
* **Target Component/Module:** Core Profiles & Inputs (Milestone 2) -> curves.py, math_utils.py, gui.py
* **Problem/Intent:** Users requested advanced math curves (Cubic, Sigmoid, Bezier) and the ability to export the response curve formula to LaTeX for visualization in tools like Desmos.
* **Underlying Logic & Thought Process:** Created a new module curves.py that isolates curve evaluation logic and LaTeX formula generation. Refactored math_utils.py to call curves.evaluate_curve rather than hardcoding the logic. In gui.py, expanded the options in the curve option menu to include 'cubic', 'sigmoid', and 'bezier'. Added an 'Export Math' button next to the dropdowns which calls curves.export_to_latex() with current slider parameters, places the resulting string in the clipboard, and shows a message box. 
* **Algorithm & Control Flow:** When evaluate_curve is called, it normalizes inputs according to the requested math model (e.g., Sigmoid scales power into steepness and shifts the center, Bezier uses the power parameter to skew control points for a 1D cubic approximation). export_to_latex builds standard math notation strings matching the exact python implementation.
* **Data Input & Expected Output:** User selects a curve. Math engine processes x to y. User clicks export, getting a clipboard string formatted like y=adz+f((x-dz)/(1-dz))*(1-adz).
---

---
### Activity: Implemented Calibration Confidence System
* **Target Component/Module:** Core Profiles & Inputs (Milestone 2) -> calibration.py
* **Problem/Intent:** Users need to know if their generated JSON profile is healthy or potentially broken due to stick drift or weak presses during the calibration phase.
* **Underlying Logic & Thought Process:** I injected statistical tracking into calibration.py's _calibrate_loop(). For triggers, I track the number of unique analog states seen in a 2-second polling window (max_uniques). If a trigger sees 40 distinct byte values, it is highly confident. For analog sticks, I measure how close the baseline/at-rest byte is to 127.5 (perfect center) to generate a centeredness score, and track the delta to maximum amplitude to generate a range_confidence score. These metrics are attached to the input dictionaries inside the JSON profile itself upon saving.
* **Algorithm & Control Flow:** For sticks, cfg['centeredness'] = 1 - abs(base_val - 127.5) / 127.5 and range_confidence = amp / 127.0. For triggers, range_confidence = max_uniques / 40.0. Capped at 1.0. The dict saves straight to profiles/.
* **Data Input & Expected Output:** Analog HID inputs. Expected output is centeredness and range_confidence float keys injected into the JSON mapping under axis/trigger inputs.
---

---
### Activity: Implemented Profile Validation and Diff Tool
* **Target Component/Module:** Core Profiles & Inputs (Milestone 2) -> profile_tools.py, gui.py
* **Problem/Intent:** Users need to know if a JSON profile they generated manually or via the calibrator is valid (no overlapping bitmasks or missing byte indices) and need to see the differences between two profiles to understand what changed.
* **Underlying Logic & Thought Process:** Created a standalone script profile_tools.py containing validate_profile() and diff_profiles(). The validator reads the JSON schema, iterates through all mapped bytes and their bitmasks across all input reports, and flags any overlap where two buttons try to read the same bit. The diff tool iterates across two JSON dictionaries and compares values, reporting missing mappings, added mappings, or changed values like deadzones or curves. I then linked these functions into the setup_profile tab in gui.py using CTkOptionMenu widgets to select the active files, triggering the functions on button press and routing output to a CTkTextbox.
* **Algorithm & Control Flow:** Validator maps (report_id, byte) -> [(input_name, bitmask, type)]. It bitwise ORs the masks, checking for mask & current_cumulative_mask to detect collision. Diff iterates through the union of all inputs across both profiles.
* **Data Input & Expected Output:** Selects two files from profiles/*.json. Output is formatted human-readable text into the GUI text box.
---

---
### Activity: Implemented Utilities Tab, Diagnostics Backend, and Input Inspector Graph
* **Target Component/Module:** Utilities (Milestone 3) -> utilities_backend.py, input_graph.py, gui.py, main.py
* **Problem/Intent:** Users need to see real-time performance metrics (software processing latency and polling rate) and visualize their analog inputs without relying on third-party websites like gamepad-tester.
* **Underlying Logic & Thought Process:** Created utilities_backend.py to act as a singleton monitor. In main.py, I hooked into the start and end of data_handler() to measure the exact time taken to process a single HID packet into an emulated state. A background thread inside the monitor writes rolling averages to diagnostics.json twice a second. gui.py reads this JSON to update the 'Utilities' UI. Furthermore, the monitor broadcasts the decoded analog state over UDP (localhost:9999) every frame. input_graph.py leverages matplotlib.animation to read this UDP stream without blocking, rendering real-time graphs of the sticks and triggers. Finally, added a built-in synthetic benchmark loop to gui.py that processes 10,000 dummy packets and computes the microsecond latency score.
* **Algorithm & Control Flow:** main.py hooks monitor.record_poll() and record_process(). UDP broadcast pushes {lx, ly, rx...}. matplotlib drains UDP buffer per frame and appends to collections.deque(maxlen=100). UI polls JSON on a 500ms after() loop.
* **Data Input & Expected Output:** HID processing times and live axis states. Outputs are visual graphs in a separate window and latency readouts in the UI.
---
