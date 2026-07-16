## V2 Architectural Refactor & The Machenike G5 Pro Crisis

* It became clear that the legacy `pywinusb` backend was inadequate. Windows' strict HID descriptor parsing was actively truncating input reports, blinding the wrapper to extra paddle bytes located at the end of payloads.

* We ripped out the legacy backend and migrated the transport layer to the low-level Cython `hidapi` library, which bypasses Windows' descriptor limitations and reads the full, raw packet (up to 1024 bytes).

* We decoupled the monolithic script into a modern, modular architecture: `hid_reader.py` (Transport), `decoder.py` (Metadata Parser), and `mapper.py` / `virtual_pad.py` (Consumers). 

* To escape the trap of hardcoding specific controller brands (like the 8BitDo Ultimate 2C), we engineered a generic, metadata-driven JSON profile schema capable of parsing 16-bit axes, signed boundaries, inverted polarities, and bitmasks natively.

## Building the Universal Calibrator

* We built `calibration.py` to allow users to generate these JSON profiles interactively by pressing buttons.

* We quickly learned that simple byte delta comparisons were not enough. Analog sticks constantly "shiver" and drift. We implemented amplitude thresholds and multi-byte checks to ensure diagonal movement didn't cause cross-contamination.

## The Composite HID Discovery (Machenike G5 Pro)

* When the user attempted to calibrate a Machenike G5 Pro, the calibrator went blind. It could map face buttons, but analog triggers and extra inputs were invisible.

* We pulled a raw transport log and realized the Machenike G5 Pro uses a "Composite HID" structure: it splits its telemetry across *multiple separate USB HID interfaces* simultaneously. The face buttons were on Interface 0, while triggers and paddles were broadcasting on Interface 1 or 2.

* We completely overhauled the wrapper to support concurrency. `calibration.py` and `main.py` were upgraded to spawn a background daemon thread for *every* discovered interface belonging to the controller.

* The JSON schema was upgraded to use a unified `interfaceNumber_reportId` composite key, seamlessly merging the fragmented telemetry back into a single `ControllerState`.

## The Phantom Axis & The "Magic Filter"

* Despite fixing the composite interface blindness, stick clicks (L3 / R3) became impossible to map. The tool kept throwing errors about "multiple axes moving."

* Analysis of the raw byte stream revealed a hardware quirk: physically pushing down on the stick caused a "phantom" unmapped axis (likely a gyro or a discarded 16-bit lower half) to fluctuate wildly.

* Because this phantom axis hadn't been mapped yet, the calibrator interpreted its rapid byte changes as a flood of digital "clicks". This instantly disqualified the input due to our cross-contamination safeguards.

* To solve this mathematically, we invented the **"Magic Filter"**: a dynamic heuristic that tracks the *number of unique values* a byte generates over a short window.
* A true digital button will only ever produce exactly 2 states (pressed and unpressed). An analog axis, however, will quickly sweep through 4, 5, or 10+ states.
* By instantly disqualifying any byte that accumulates >3 unique states, we perfectly filtered out the analog noise, allowing the single-bit stick click to be isolated and confirmed flawlessly.

## The Trigger Scope Leakage Bug

* With the noise gone, the tool sailed through calibration until the Left Trigger (LT) phase. Upon detecting the trigger, the script abruptly stated "Profile Saved" and terminated, skipping the Right Trigger and D-Pad entirely.

* A code trace revealed a classic Python scope leakage trap: inside the trigger logic, we used a nested `for i, val in enumerate(data):` loop to iterate over the controller's raw packet bytes.

* Because Python does not isolate `for` loop variables into a local block scope, that inner loop completely overwrote the outer calibration step counter `i` (which was tracking the user's progress through the 21 calibration prompts).

* The trigger payload was 64 bytes long, meaning `i` was overwritten to 63. The outer loop saw that `63 > 21` steps, assumed calibration was 300% complete, happily saved the profile, and exited.

* We simply renamed the inner loop iterator to `byte_idx`, sealing the leak.

## Success

* Following the deployment of the Magic Filter and the Scope Leakage fix, the calibrator mapped the entire Machenike G5 Pro composite layout perfectly on the first try. The V2 architecture was officially proven.
