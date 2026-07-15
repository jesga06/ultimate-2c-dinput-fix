# 8BitDo Ultimate 2C DInput Fix

A wrapper that fixes the broken DInput mode of the 8BitDo Ultimate 2C Wireless Controller (2.4GHz) on Windows, restoring analog triggers and preserving the extra rear buttons.

The controller natively sends analog trigger data in its HID reports, but its HID descriptor incorrectly describes the reports, causing Windows and games to interpret the analog trigger values incorrectly. This application reads the raw USB HID reports, correctly parses the analog triggers and extra buttons, and exposes a Virtual Xbox 360 controller using `vgamepad` (ViGEmBus). It even lets you remap the extra buttons!

## Features
- **Analog Triggers:** Restores the missing analog functionality for LT and RT. (You paid for analog, hall effect triggers and you're getting them analog, hall effect triggers!)
- **Extra Buttons (L4/R4):** Lets you remap the extra rear buttons to keyboard or mouse actions. (configurable in `config.ini`)
- **Works like you were using XInput:** All other buttons are fully mapped properly into XInput standards. No need to use SteamInput!

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
- EXAMPLE: Special Keys (must match pynput `Key` enum names): `keyboard:space`, `keyboard:enter`, `keyboard:f13`, `keyboard:shift`

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
Leave the console window open. Windows will detect a new Xbox 360 controller, and your analog triggers will function in all their analog glory.

## EXTRAS

### AI NOTICE: 
Yes, this was programmed by a clanker.

No, the clanker did not do the fun part (the actual reverse engineering behind this hot mess).

No, I don't feel bad about it.

### NOTES:
Not sure whether or not this would work with other controllers that have similar issues. The VID and PID values are hardcoded in, but if you have a controller that has similar issues, just... well, open an issue!

I might make it so the program reads those IDs from file together with the remapping options and even write a small tutorial on how to find your controllers' IDs to use this tool on them!

And no, this tool does not disable the hardware L4/R4 remapping. I have no idea how to disable that. It does let you completely disable or remap the home button to something else though, so there's that!


### (maybe) TO-DOs:
* bundle all of this up into an executable for those who just want to use the damn thing they paid for
* let all keys be remapped?
* rescan config.ini on changes instead of on startup
* make the cmd minimize itself or just close to tray (and not exit, obviously)
* test whether this could work on other controllers and what would need to be done to adapt it

### TIMELINE OF EVENTS:

Stumbled upon a [reddit post](https://www.reddit.com/r/Controller/comments/1hu5faa/guide_for_8bitdo_ultimate_2c_wireless_controller/) with some tips about the Ultimate 2 family. Noticed that my controller could be used in Xinput or Dinput modes. Decided to test it out. 

Noticed that for some godforsaken reason the triggers didn't use analog polling when the controller was set to Dinput. Got pissed.

Used [this HID Descriptor Tool](https://usb.org/document-library/hid-descriptor-tool) to find out the VID and PID.

Used [this CLI tool](https://github.com/todbot/hidapitester) to read raw input to determine whether it was a firmware issue (the controller actually just wouldn't send analog data) or if it was windows being windows. 

Noticed the controller was actually sending analog data. "Windows being windows" theory didn't make sense because no tool correctly reported analog input. 

Decided to take a look into the descriptor to figure out how the values were being mapped. Found out the 8BitDo engineers are lazier than I am. Got even more pissed. 

Wrote a proof of concept script. Concept was proven. Wrote a prompt. AI pumped this out faster than anyone could have. Learned basic black-box reverse engineering in the process. Not pissed anymore.