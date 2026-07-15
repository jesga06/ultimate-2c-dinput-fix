# Universal Remapper & XInput from DInput Wrapper & Fixer
Basically tries to fix DInput gamepads broken by bad descriptors.

A lightweight utility that fixes incorrect DirectInput (DInput) behaviors—like broken analog triggers—on various Windows controllers (e.g., 8BitDo Ultimate 2C) and adds support for custom back paddles, converting them into standard XInput controllers with fully customizable mouse/keyboard mapping.

Some controllers expose perfectly valid input data but advertise incorrect HID descriptors, causing Windows and games to interpret inputs incorrectly. UR-XD bypasses the incomplete/wrong descriptor data, correctly parses the analog triggers and extra buttons, and exposes the fixed gamepad as a Virtual Xbox 360 controller using `vgamepad` (ViGEmBus). It even lets you remap the extra buttons!

For a detailed list of recent updates, architectural changes, and bug fixes, see the [CHANGELOG.md](CHANGELOG.md).

### Supported today

- ✅ 8BitDo Ultimate 2C Wireless 2.4 GHz (literally what this whole project was built to fix)

### Potentially compatible

- ⚠️ Any HID controller whose descriptor does not match its reports
- ⚠️ Requires one-time calibration

## Features
- **Analog Triggers Fix:** Restores missing analog polling on controllers with broken DInput configurations (e.g. Hall Effect triggers that Windows treats as digital. You paid for analog triggers and you're getting them analog triggers!).
- **Visual GUI Configuration:** A simple, dark-mode visual interface to easily map buttons without manual file editing.
- **Universal Profiling:** Generate custom controller layout profiles (`profiles/`) for any generic HID controller using the interactive calibration tool. Includes a default profile for the 8BitDo Ultimate 2C.
- **Background System Tray Operation:** Quietly sits in your system tray and hides the command prompt window.
- **Full Button Remapping & Block:** Map *any* controller button (standard or extra paddle) to *any combination of* keyboard or mouse outputs; standard buttons are blocked from XInput when remapped to prevent double inputs. (Default config sets L4-R4 as Mouse4-Mouse 5, respectively. Home/Guide is set as ALT+UP)
- **Smart Reconnection:** Recover connection automatically if your physical controller gets disconnected, actively scanning for 20 seconds before closing safely.
- **Live Reloading:** Your mapping changes are applied instantly in the background without needing to restart the app.
- **And Much More!** Check out the full list of features in the [Features List](featurelist.md).

## Requirements
- Python 3
- [ViGEmBus](https://github.com/nefarius/ViGEmBus) driver installed.
- Required pip packages (see `requirements.txt`)

## Setup & Tutorial

### Step 1: Install Requirements
1. Install [Python 3.13](https://www.python.org/downloads/release/python-31314/) or higher.
2. Install the [ViGEmBus](https://github.com/nefarius/ViGEmBus) driver.
3. Install Python dependencies (run on PowerShell or CMD):
   ```powershell
   pip install -r requirements.txt
   ```

### Step 2: Calibrate Your Controller (One-time Setup)
If your controller doesn't have a profile generated yet:
1. Turn on your controller and run the **`calibrate.bat`** script (or run `python calibration.py` in PowerShell, be sure to **navigate to the scripts' folder** first!).
2. Press any button or move a joystick on the controller you want to use. The tool will auto-detect it. You can also select it manually by typing the number of the device in the prompt.
3. Follow the step-by-step CLI prompts (e.g., press A, push Left Stick Up, etc.) to baseline and map your device.
4. Once finished, a custom JSON profile will be saved in the `profiles/` directory.

### Step 3: Run the Background Daemon
To start intercepting inputs in the background:
1. Run the **`run_wrapper.bat`** script (or run `python main.py` in PowerShell).
2. The command prompt window will hide automatically.
3. A circular white and purple icon will appear in your **System Tray**.

### Step 4: Map Your Buttons
1. Right-click the system tray icon and select **Open Config**.
2. This opens the Configuration GUI window.
3. Go to the **Remapping** tab, type your desired mappings (e.g., `keyboard:space` or `mouse4`) next to the controller buttons, and press Enter.
4. The background daemon will pick up your changes within 5 seconds!

## Configuration Details
If you prefer editing configuration manually, you can customize the mappings for the extra buttons in `config.ini`. This uses the `pynput` library to simulate mouse and keyboard events.

### Mouse Mapping
You can map to mouse buttons. The defaults are the forward and backward buttons on standard gaming mice:
- `mouse4` (Backward / X1)
- `mouse5` (Forward / X2)

### Keyboard Mapping
You can also map to keyboard keys by prefixing the value with `keyboard:`.
- Letters/Numbers: `keyboard:a`, `keyboard:1`
- Special Keys (must match pynput `Key` enum names): `keyboard:space`, `keyboard:enter`, `keyboard:f13`, `keyboard:shift`
- **Key Combos:** You can chain multiple keys together with a `+` symbol (e.g. `keyboard:shift+o` or `keyboard:ctrl+alt+delete`). They will be pressed sequentially and released in reverse order.

Example `config.ini`:
```ini
[controller]
output = xinput

[extra_buttons]
l4 = mouse4
r4 = keyboard:f13
```

## Troubleshooting

- **No Virtual Controller Appears:** Ensure you have the [ViGEmBus](https://github.com/nefarius/ViGEmBus) driver installed and that it is functioning correctly.
- **Controller Not Detected by the App:** Make sure you have run the **`calibrate.bat`** script first to generate a profile for your specific controller.
- **Changes in GUI Aren't Applying:** Ensure that **`run_wrapper.bat`** (the background daemon) is actively running in your system tray. The GUI only modifies the settings; the daemon actually applies them.
- **Double Inputs in Games:** If you remap a standard button (like 'A'), the app blocks the original 'A' press from reaching the game to prevent double inputs. If you are still seeing double inputs, verify the background daemon is running and Steam Input is not interfering.
- **Calibration Tool Fails Due to Two Axes Moving:** Some controllers report movement on two separate axes simultaneously when squeezing a single trigger (due to hardware quirks). The calibration tool expects isolated movement. If this happens to you, the tool may misidentify the trigger axis. You may need to manually edit the resulting `profiles/` JSON file or use a different controller.
- **Tool doesn't work:**
   - Check whether you're actually using the Virtual Gamepad exposed by this tool, not your physical controller. The Virtual Gamepad will appear in Windows Device Settings as "Virtual Gamepad".
   - Check if you correctly installed the required dependencies with `pip install -r requirements.txt`.
   - Check if the daemon is actually running by looking for the system tray icon.
- **Still Facing Issues?** If you encounter an issue you cannot resolve, please use the **`calibrate_debug.bat`** or **`run_wrapper_debug.bat`** scripts to run the tools in debug mode. This will generate a verbose `calibration.log` or `wrapper.log` file in the same directory. Please open an issue on GitHub and attach these log files to help me fix the problem!


## LICENSE

This project is licensed under the PolyForm Noncommercial License 1.0.0.

You are free to use, modify and redistribute this software for noncommercial purposes under the terms of the license.

Commercial use is not permitted without explicit permission from the copyright holder.

## EXTRAS

### AI NOTICE: 
Yes, this was programmed by a clanker.

No, the clanker did not do the fun part (the actual reverse engineering behind this hot mess).

No, I don't feel bad about it.

### NOTES:
- No, this tool does not disable the hardware L4/R4 remapping. I have no idea how to disable that. 
   - It does let you completely disable or remap the home button to something else though, so there's that!
- It also does not let you remap special controller buttons like "turbo", a profile/mode switch, pairing button, the one you'd use to remap extra buttons, etc.
### (maybe) TO-DOs:
* [x] let all keys be remapped
* [x] rescan config.ini on changes instead of on startup
* [x] make the cmd minimize itself or just close to tray (did this and ended up adding a GUI too cause why not)
* [x] test whether this could work on other controllers and what would need to be done to adapt it (added the new calibration wizard to test this - VID and PID is not hardcoded in anymore!)
* [ ] bundle all of this up into a standalone `.exe` executable for those who just want to use the damn thing they paid for

### (fun) TIMELINE OF EVENTS THAT LED TO THIS PROJECT COMING TO LIFE:

Stumbled upon a [reddit post](https://www.reddit.com/r/Controller/comments/1hu5faa/guide_for_8bitdo_ultimate_2c_wireless_controller/) with some tips about the 8BitDo Ultimate 2 controller family. Noticed that my controller could be used in Xinput or Dinput modes. Decided to test it out. 

Noticed that for some godforsaken reason the triggers didn't use analog polling when the controller was set to Dinput. Got pissed.

Used [this USBView Tool](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/usbview) to find out the VID and PID.

Used [this CLI tool](https://github.com/todbot/hidapitester) to read raw input to determine whether it was a firmware issue (the controller actually just wouldn't send analog data) or if it was Windows being Windows. 

Noticed the controller was actually sending analog data. "Windows being Windows" theory didn't make sense because no tool correctly reported analog input. 

Decided to take a look into the descriptor to figure out how the values were being mapped. Found out the 8BitDo engineers are lazier than I am (The descriptors didn't properly map to what the controller actually outputs). Got even more pissed. 

Wrote a proof of concept script. Concept was proven. Wrote a prompt. AI pumped this out faster than anyone could have. Learned basic black-box reverse engineering in the process. Not pissed anymore.

Ended up feature-creeping this to the point where the name of this repository was outdated within hours of creation.
