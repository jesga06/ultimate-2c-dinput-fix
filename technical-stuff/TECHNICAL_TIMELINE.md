# Technical Timeline: Initial Discovery & Reverse Engineering

## 1. Initial Investigation
- **Operating Modes Breakdown:**
  - **XInput Mode:** Exposed analog triggers natively, but left hardware back paddle buttons (`L4` and `R4`) completely unmappable by software.
  - **DirectInput (DInput) Mode:** Exposed `L4` and `R4` as independent button inputs, but forced analog triggers (`LT` and `RT`) to operate as digital buttons in Windows.
- **API Capability Verification:** Verified that the DirectInput API natively supports analog trigger axes.
- **USB Descriptor Extraction:** Used `USBView` to analyze the gamepad USB hierarchy, identifying Vendor ID `0x2DC8` and Product ID `0x301C` (8BitDo Ultimate 2C Wireless).
- **Report Descriptor Analysis:** Utilized `hidapitester` via PowerShell to extract raw HID report descriptors from the DInput interface.
- **Initial Hypothesis:** Assumed controller firmware was stripping/discarding analog trigger telemetry before sending packets to the host.

## 2. Raw Data Capture & Manual Decoding
- **Continuous Byte Streaming:** Executed `hidapitester --read-input-forever` to capture raw 16-byte HID input reports in real time.
- **Isolated Input Testing:** Manipulated individual controls in isolation (e.g., slowly deflecting thumbsticks horizontally, gradual trigger squeezes) to isolate active bytes.
- **Baseline Alignment:** Identified that neutral/centered analog axes defaulted to `0x7F` or `0x0F`.
- **Payload Schema Mapping:** Manually decoded the complete 16-byte HID report layout:
  - **Byte 1:** General button activity flag.
  - **Byte 2:** Standard face buttons and shoulder buttons (`A`, `B`, `X`, `Y`, `LB`, `RB`).
  - **Byte 3:** System buttons (`Start`, `Select`, `Home`), stick clicks (`L3`, `R3`), and digital trigger state bits.
  - **Byte 4:** D-Pad directional hat switch state.
  - **Bytes 5–8:** 8-bit analog coordinates for Left Stick (`LX`, `LY`) and Right Stick (`RX`, `RY`).
  - **Bytes 9–10:** Smooth, unclipped 8-bit analog values (`0–255`) for Right Trigger (`RT`) and Left Trigger (`LT`), respectively.
  - **Bytes 11–16:** Static/unused payload padding (remained constant across testing, confirming a 10-byte effective payload).
- **Conclusion:** Disproved the firmware limitation hypothesis. The controller hardware actively transmits smooth analog trigger data, but invalid/incomplete HID descriptors cause Windows to misinterpret the stream. This revelation inspired the creation of this wrapper project.