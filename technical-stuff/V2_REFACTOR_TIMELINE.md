# Technical Timeline: V2 Architectural Refactor & Universal Framework

## 1. V2 Architectural Refactor & "Universal" Crisis
- **Backend Limitations:** The legacy `pywinusb` backend was inadequate due to Windows' strict HID descriptor parsing, which actively truncated input reports and blinded the wrapper to extra paddle bytes located at the end of payloads.
- **Cython `hidapi` Migration:** Replaced the legacy backend with the low-level Cython `hidapi` library, bypassing Windows descriptor limitations to read raw HID payloads (up to 1024 bytes).
- **Modular Pipeline Decoupling:** Decoupled the monolithic script into a modern, modular architecture:
  - `src/hid_reader.py` (Transport)
  - `src/decoder.py` (Metadata Parser)
  - `src/mapper.py` / `src/virtual_pad.py` (Input Consumers)
- **Generic Profile Engine:** Replaced hardcoded controller brand logic (e.g. 8BitDo Ultimate 2C) with a generic, metadata-driven JSON profile schema capable of natively parsing 16-bit axes, signed boundaries, inverted polarities, and bitmasks.

## 2. Building the Universal Calibrator
- **Interactive Profiler:** Built `src/calibration.py` to allow users to generate custom controller JSON profiles interactively via guided prompts.
- **Noise & Jitter Handling:** Identified that simple byte delta comparisons failed due to analog stick shiver and hardware jitter. Implemented amplitude thresholds and multi-byte checks to ensure diagonal stick movements did not trigger false cross-contamination errors.

## 3. The Composite HID Discovery (Machenike G5 Pro)
- **Interface Blindness:** During calibration of a Machenike G5 Pro, standard face buttons mapped correctly, but analog triggers and back paddles failed to register.
- **Transport Analysis:** Inspected raw packet logs and discovered that the Machenike G5 Pro uses a Composite HID architecture, splitting telemetry across multiple USB HID interfaces simultaneously (standard buttons on Interface 0; analog triggers and paddles strictly on Interface 2).
- **Concurrent Daemon Architecture:** Upgraded `src/calibration.py` and `src/main.py` to spawn concurrent background polling threads for every active HID interface associated with a controller.
- **Composite Key Schema:** Enhanced the JSON profile schema to use a unified `interfaceNumber_reportId` composite key, merging fragmented interface streams into a single `ControllerState`.

## 4. The Phantom Axis & The "Magic Filter"
- **Stick Click Calibration Failure:** Despite resolving composite interface handling, stick clicks (`L3` / `R3`) failed calibration due to "multiple axes moving" errors.
- **Hardware Quirk Isolation:** Raw byte analysis revealed that physically depressing the thumbstick caused an unmapped "phantom" axis (such as a gyro sensor or lower 16-bit byte) to fluctuate rapidly.
- **False Positive Elimination:** Because the phantom axis was unmapped, its rapid state changes were misinterpreted as digital button clicks, triggering cross-contamination blocks.
- **The "Magic Filter" Heuristic:** Developed a dynamic mathematical filter tracking the number of unique byte values within a sliding window:
  - **Digital Buttons:** Produce strictly 2 states (pressed vs. unpressed).
  - **Analog Noise / Axes:** Rapidly sweep across 4, 5, or 10+ unique states.
- **Resolution:** By instantly filtering out any byte generating >3 unique states during digital button prompts, analog noise was eliminated, allowing single-bit stick clicks to isolate and calibrate reliably.

## 5. Architectural Verification
- **First-Pass Success:** Applying the Magic Filter enabled the calibration wizard to map the entire Machenike G5 Pro composite layout perfectly on the first attempt, confirming the stability of the V2 architecture.
