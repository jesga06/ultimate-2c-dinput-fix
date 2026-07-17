# Manual Calibration Guide

When you run the calibration tool (`python src/calibration.py`), the software attempts to automatically detect which HID interface on your controller carries the actual button/axis inputs. It does this by observing the inputs you press during the 15-second discovery stage.

However, if your controller has complex features (e.g. built-in mice, system keyboards, or firmware quirks) or if you want absolute control over which interfaces are read, you can skip the auto-discovery or use the manual fallback.

## When to use Manual Selection?
- The calibration tool says "No activity detected on any interface." even though you pressed buttons.
- You are missing certain "extra" buttons (e.g. back paddles) because they are sent on a *different* interface that wasn't detected.
- The controller sends "ghost" inputs on a specific interface that interferes with your gameplay.

## Finding the Correct Interfaces
During the manual selection stage, the tool will list all available interfaces for your controller:
```
[0] Interface: 0 | Usage Page: 1 | Usage: 4
[1] Interface: 1 | Usage Page: 1 | Usage: 5
[2] Interface: 2 | Usage Page: 65280 | Usage: 1
```

If you don't know which interfaces to use, you can test them:
1. Run the calibration tool with the raw dump flag: `python src/calibration.py --dump-raw`
2. Wait 2 seconds for the baseline to establish.
3. Press the problematic buttons (e.g. back paddles, extra face buttons).
4. Observe the console output. It will tell you exactly which `IFace` (Interface number) reported the change.
5. Note down all the interface numbers that report the buttons you care about.

## Overriding the Selection
When you run the standard calibration again and are presented with the Auto-Discovery prompt:
1. Simply press **ENTER** immediately without pressing any buttons on your controller.
2. Because no activity was detected, the tool will trigger the **Stage 2: Manual Interface Selection** fallback.
3. You will be prompted to enter comma-separated choices for the interfaces you want to enable.
4. Type the index numbers (the numbers in brackets `[ ]`, not the interface numbers themselves) that correspond to the interfaces you found in the raw dump mode.
5. Example: If you want to enable index `0` and index `2`, type `0,2` and press Enter.

The tool will now simultaneously read from all the interfaces you selected and merge their inputs into a single controller state!

## Troubleshooting Triggers
If you receive the warning `WARNING: No trigger signal detected!`:
- This means the script was unable to find a byte that smoothly ramps up in value when you press the trigger, and it also failed to detect a digital button press.
- Make sure your controller is set to **DInput mode**. Many controllers act entirely differently in XInput mode.
- If you have trigger stops enabled or your controller only has digital triggers (like the Nintendo Switch Pro controller), the tool should automatically detect them via the digital fallback. If it fails, press the trigger more firmly and ensure it's registering.
- Make sure the correct interface was selected! Some controllers send the analog trigger data on Interface 1, but digital button data on Interface 0. Use the raw dump mode to verify!
