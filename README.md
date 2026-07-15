# 8BitDo Ultimate 2C DInput Fix

A wrapper to fix the 8BitDo Ultimate 2C Wireless Controller (2.4GHz) DInput mode on Windows. 

The controller natively sends analog trigger data in its HID reports, but its HID descriptor is incorrect, causing games and standard APIs to read them as digital buttons. This application reads the raw USB HID reports, correctly parses the analog triggers and extra buttons, and exposes a Virtual Xbox 360 controller using `vgamepad` (ViGEmBus).

## Features
- **Analog Triggers:** Restores the missing analog functionality for LT and RT.
- **Extra Buttons (L4/R4):** Re-maps the extra rear buttons to keyboard or mouse actions.
- **D-Pad & Analog Sticks:** Fully maps the D-Pad and sticks properly into XInput standards.

## Requirements
- Python 3
- [ViGEmBus](https://github.com/nefarius/ViGEmBus) driver installed.
- Required pip packages (see `requirements.txt`)

## Configuration & Button Mapping

You can customize the mappings for the extra buttons (L4 and R4) in `config.ini`. This uses the `pynput` library to simulate mouse and keyboard events.

### Mouse Mapping
You can map to mouse buttons. The defaults are the forward and backward buttons on standard gaming mice:
- `mouse4` (Backward / X1)
- `mouse5` (Forward / X2)

### Keyboard Mapping
You can also map to keyboard keys by prefixing the value with `keyboard:`.
- Letters/Numbers: `keyboard:a`, `keyboard:1`
- Special Keys (must match pynput `Key` enum names): `keyboard:space`, `keyboard:enter`, `keyboard:f13`, `keyboard:shift`

Example `config.ini`:
```ini
[controller]
output = xinput

[extra_buttons]
l4 = mouse4
r4 = keyboard:f13
```

## Running the Application
Simply run the script after installing the requirements:
```powershell
python main.py
```
Leave the console window open. Windows will detect a new Xbox 360 controller, and your analog triggers will function correctly in all games.