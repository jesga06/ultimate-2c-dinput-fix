import sys
import os
import time
import argparse
import traceback

parser = argparse.ArgumentParser()
parser.add_argument('--debug', '-d', action='store_true')
args, _ = parser.parse_known_args()
IS_DEBUG = args.debug

if IS_DEBUG:
    def debug_excepthook(exc_type, exc_value, exc_traceback):
        print("[DEBUG TRACE]")
        traceback.print_exception(exc_type, exc_value, exc_traceback)
    sys.excepthook = debug_excepthook

import datetime
import threading
import hid

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
LOG_DIR = os.path.join(REPO_ROOT, "diagnostics_logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "06_guided_calibration.log")

class DualLogger:
    def __init__(self, filepath):
        self.terminal = sys.stdout
        self.error_terminal = sys.stderr
        self.log = open(filepath, "w", encoding="utf-8")
        self.closed = False

    def write(self, message):
        self.terminal.write(message)
        if not self.closed:
            try:
                self.log.write(message)
                self.log.flush()
            except ValueError:
                pass

    def write_err(self, message):
        self.error_terminal.write(message)
        if not self.closed:
            try:
                self.log.write(message)
                self.log.flush()
            except ValueError:
                pass

    def log_silent(self, message):
        if not self.closed:
            try:
                self.log.write(message + "\n")
                self.log.flush()
            except ValueError:
                pass

    def flush(self):
        self.terminal.flush()
        self.error_terminal.flush()
        if not self.closed:
            try:
                self.log.flush()
            except ValueError:
                pass

    def close(self):
        if not self.closed:
            self.log.close()
            self.closed = True

logger = DualLogger(LOG_FILE)
sys.stdout = logger

class StderrWrapper:
    def __init__(self, dual_logger):
        self.dual_logger = dual_logger
    def write(self, message):
        self.dual_logger.write_err(message)
    def flush(self):
        self.dual_logger.flush()

sys.stderr = StderrWrapper(logger)

def print_terminal_only(message, end="\n"):
    logger.terminal.write(message + end)
    logger.terminal.flush()

def main():
    print("=" * 70)
    print("   DIAGNOSTIC STEP 6: GUIDED INPUT CALIBRATION")
    print("=" * 70)
    print("This script will guide you through pressing every button and axis")
    print("on your controller one by one. It records exactly which bytes change")
    print("so the developer can perfectly map your specific controller.")
    print("-" * 70)
    print("[INSTRUCTIONS FOR USER]")
    print("1. Connect your controller to the PC.")
    print("2. Ensure no other applications (like Steam, Remappers) are running.")
    print("3. Read each on-screen prompt carefully before acting.")
    print("-" * 70)

    try:
        devices = hid.enumerate()
    except Exception as e:
        print(f"[ERROR] Failed to run hid.enumerate(). Details: {e}")
        sys.exit(1)

    if not devices:
        print("[ERROR] No HID devices connected or detected on this system.")
        sys.exit(1)

    print("\nAll HID devices detected on this system:")
    for idx, dev in enumerate(devices):
        mfg = dev.get('manufacturer_string', 'Unknown')
        prod = dev.get('product_string', 'Unknown')
        vid = dev.get('vendor_id', 0)
        pid = dev.get('product_id', 0)
        iface = dev.get('interface_number', -1)
        
        rec_str = ""
        if "controller" in str(prod).lower() or "microsoft" in str(prod).lower() or "microsoft" in str(mfg).lower():
            rec_str = " (Recommended for XInput)"
            
        print(f"  [{idx:2d}] VID:{vid:04X} PID:{pid:04X} - {prod} ({mfg}) [Iface {iface}]{rec_str}")

    print("\n[ACTION REQUIRED] Type the number of the controller you want to test and press ENTER.")
    selected_device = None
    while not selected_device:
        try:
            choice = input(f"Choice [0-{len(devices)-1}] (or 'q' to quit): ").strip()
        except KeyboardInterrupt:
            print("\nExiting.")
            sys.exit(0)
        if choice.lower() == 'q':
            print("Exiting.")
            sys.exit(0)
        try:
            idx = int(choice)
            if 0 <= idx < len(devices):
                selected_device = devices[idx]
        except ValueError:
            pass
        if not selected_device:
            print("Invalid choice. Please enter a valid number.")

    try:
        dev_handle = hid.device()
        dev_handle.open_path(selected_device['path'])
        dev_handle.set_nonblocking(True)
    except Exception as e:
        print(f"\n[ERROR] Failed to open device: {e}")
        sys.exit(1)

    print("\n[CONNECTED] Successfully opened controller interface.")
    
    # Background reader thread setup
    latest_state = {}
    state_lock = threading.Lock()
    running = True

    def reader_thread():
        while running:
            data = dev_handle.read(1024)
            if data:
                with state_lock:
                    latest_state[data[0]] = list(data)
            else:
                time.sleep(0.001)

    t = threading.Thread(target=reader_thread, daemon=True)
    t.start()

    # Step 1: Baseline
    print("\n" + "=" * 70)
    print("STEP 1: RESTING BASELINE")
    print("=" * 70)
    print("Place the controller on a flat surface.")
    print(">>> STATUS: DO NOT TOUCH ANYTHING <<<")
    print("Establishing baseline for 3 seconds...")
    
    # Clear any old packets
    time.sleep(0.5)
    with state_lock:
        latest_state.clear()
        
    time.sleep(2.5)
    
    with state_lock:
        baseline = {k: list(v) for k, v in latest_state.items()}
        
    if not baseline:
        print("[WARNING] No packets received automatically.")
        print("Your controller might only send data when buttons are pressed.")
        print("\n>>> ACTION REQUIRED: Please TAP any button (like 'A') ONCE,")
        print("    release it immediately, and DO NOT touch anything else.")
        
        while True:
            time.sleep(0.1)
            with state_lock:
                if latest_state:
                    break
                    
        print("[+] Data detected! Waiting 2 seconds for resting state to settle...")
        time.sleep(2.0)
        with state_lock:
            baseline = {k: list(v) for k, v in latest_state.items()}

    print("[+] Baseline Established:")
    for rid, data in baseline.items():
        hex_str = " ".join(f"{b:02X}" for b in data)
        print(f"  Report 0x{rid:02X}: {hex_str}")
        
    def compare_states(base, current):
        diffs = []
        for rid, curr_data in current.items():
            if rid not in base:
                diffs.append(f"New Report ID 0x{rid:02X} appeared.")
                continue
            base_data = base[rid]
            for i in range(min(len(base_data), len(curr_data))):
                if base_data[i] != curr_data[i]:
                    b_val = base_data[i]
                    c_val = curr_data[i]
                    delta = c_val - b_val
                    # Check for single bit toggle
                    xor_val = b_val ^ c_val
                    is_power_of_two = (xor_val != 0) and ((xor_val & (xor_val - 1)) == 0)
                    
                    if is_power_of_two:
                        # Find which bit flipped
                        bit_idx = 0
                        while (xor_val >> bit_idx) & 1 == 0:
                            bit_idx += 1
                        info = f"(Bit {bit_idx} Flipped | Mask 0x{xor_val:02X})"
                        classification = "[BUTTON-LIKE]"
                    else:
                        info = f"(Delta: {delta:+d})"
                        classification = "[AXIS-LIKE]"
                        
                    diffs.append(f"  {classification} Report 0x{rid:02X}, Byte {i:02d}: 0x{b_val:02X} -> 0x{c_val:02X} {info}")
        return diffs

    def prompt_input(name, is_axis=False):
        while True:
            print(f"\n---> TEST: {name} <---")
            if is_axis:
                print(f"1. Push the [{name}] axis exactly as requested and HOLD IT.")
            else:
                print(f"1. PRESS AND HOLD the [{name}] button.")
            print("2. While holding it, press [ENTER] on your keyboard.")
            print("   (Type 's' then [ENTER] to skip this input)")
            
            choice = input("Your action: ").strip().lower()
            if choice == 's':
                print(f"[SKIPPED] {name}")
                logger.log_silent(f"Input: {name} - SKIPPED")
                return
            
            with state_lock:
                current = {k: list(v) for k, v in latest_state.items()}
                
            diffs = compare_states(baseline, current)
            if not diffs:
                print("[!] No change detected from baseline. Make sure you are holding the input down.")
                print("    Try again.")
                continue
                
            print(f"[*] Change detected for {name}:")
            logger.log_silent(f"Input: {name}")
            for d in diffs:
                print(d)
                logger.log_silent(d)
                
            # Now wait for release
            print(f"\n1. RELEASE the [{name}] input.")
            print("2. Wait 1 second (DO NOT TOUCH ANYTHING).")
            print("3. Press [ENTER] on your keyboard.")
            input("Ready? Press [ENTER]: ")
            
            # Quick check if it returned to baseline
            with state_lock:
                current_released = {k: list(v) for k, v in latest_state.items()}
            rel_diffs = compare_states(baseline, current_released)
            if rel_diffs:
                print("[WARNING] Controller did not perfectly return to baseline (this is normal for axes).")
            print("[+] Verified release. Moving to next input...")
            break

    # Step 2: Standard Buttons
    print("\n" + "=" * 70)
    print("STEP 2: STANDARD BUTTONS")
    print("=" * 70)
    print("You will now be prompted to press standard gamepad buttons.")
    
    standard_buttons = [
        "A (South)", "B (East)", "X (West)", "Y (North)",
        "L1 (Left Bumper)", "R1 (Right Bumper)",
        "L2 (Left Trigger - Full Pull)", "R2 (Right Trigger - Full Pull)",
        "Select / View / Minus", "Start / Menu / Plus", "Home / Guide",
        "D-Pad UP", "D-Pad DOWN", "D-Pad LEFT", "D-Pad RIGHT"
    ]
    
    for btn in standard_buttons:
        prompt_input(btn)

    # Step 3: Extra Buttons
    print("\n" + "=" * 70)
    print("STEP 3: EXTRA BUTTONS (Paddles, C/Z, Macro keys)")
    print("=" * 70)
    print("If your controller has extra buttons (like back paddles),")
    print("we will test them now.")
    
    extra_count = 1
    while True:
        print(f"\n---> TEST: Extra Button #{extra_count} <---")
        print("1. PRESS AND HOLD an extra button (or type 's' to finish extra buttons).")
        print("2. While holding, press [ENTER] on your keyboard.")
        choice = input("Your action: ").strip().lower()
        if choice == 's':
            print("[FINISHED] Extra buttons phase.")
            break
            
        with state_lock:
            current = {k: list(v) for k, v in latest_state.items()}
        diffs = compare_states(baseline, current)
        
        if not diffs:
            print("[!] No change detected. Try again.")
            continue
            
        print(f"[*] Change detected for Extra Button #{extra_count}:")
        name = f"Extra_Button_{extra_count}"
        logger.log_silent(f"Input: {name}")
        for d in diffs:
            print(d)
            logger.log_silent(d)
            
        print(f"\n1. RELEASE the extra button.")
        print("2. Wait 1 second.")
        print("3. Press [ENTER] on your keyboard.")
        input("Ready? Press [ENTER]: ")
        extra_count += 1


    # Step 4: Joystick Clicks (L3 / R3)
    print("\n" + "=" * 70)
    print("STEP 4: JOYSTICK CLICKS (L3 / R3)")
    print("=" * 70)
    print("When clicking sticks, you might accidentally move the stick axis.")
    print("Try to click straight down without leaning the stick.")
    print("We will attempt to classify the button press vs axis drift.")
    
    prompt_input("L3 (Left Stick Click)")
    prompt_input("R3 (Right Stick Click)")


    # Step 5: Joystick Axes
    print("\n" + "=" * 70)
    print("STEP 5: JOYSTICK AXES")
    print("=" * 70)
    print("You will push the stick in a specific direction.")
    print("Since perfectly straight movement is hard, we look for the byte with")
    print("the largest [AXIS-LIKE] change.")
    
    prompt_input("Left Stick - STRAIGHT UP", is_axis=True)
    prompt_input("Left Stick - STRAIGHT RIGHT", is_axis=True)
    prompt_input("Right Stick - STRAIGHT UP", is_axis=True)
    prompt_input("Right Stick - STRAIGHT RIGHT", is_axis=True)


    # Cleanup
    running = False
    try:
        dev_handle.close()
    except:
        pass

    print("\n" + "=" * 70)
    print("   GUIDED CALIBRATION COMPLETED")
    print("=" * 70)
    print(f"All mapped inputs have been saved to:\n  {LOG_FILE}")
    print("=" * 70)

if __name__ == '__main__':
    try:
        main()
    finally:
        logger.close()
