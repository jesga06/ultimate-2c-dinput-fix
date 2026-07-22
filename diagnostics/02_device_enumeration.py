import sys
import os
import time
import platform
import hid

# 1. Setup logging redirection to capture everything (both stdout/stderr)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
LOG_DIR = os.path.join(REPO_ROOT, "diagnostics_logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "02_device_enumeration.log")

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

def show_progress(message, duration_seconds=1.5):
    print(f"\n[WAIT] {message}")
    print(">>> STATUS: DO NOT TOUCH ANYTHING <<<")
    symbols = ["|", "/", "-", "\\"]
    start = time.time()
    i = 0
    while time.time() - start < duration_seconds:
        sys.stdout.write(f"\r[{symbols[i % len(symbols)]}] Working...")
        sys.stdout.flush()
        time.sleep(0.15)
        i += 1
    sys.stdout.write("\r[+] Completed.                      \n")
    sys.stdout.flush()

def main():
    print("=" * 60)
    print("   DIAGNOSTIC STEP 2: DEVICE ENUMERATION")
    print("=" * 60)
    print("This script will scan all USB/HID input devices connected to this PC.")
    print("It checks their details and tests whether they are locked by Windows")
    print("or another application (e.g., Steam Input).")
    print("-" * 60)
    
    # Read user instructions
    print("[INSTRUCTIONS FOR USER]")
    print("1. Ensure your controller is plugged in (wired or wireless dongle).")
    print("2. Close all other programs that may be using the controller")
    print("   (Steam, game launchers, other remapping tools).")
    print("-" * 60)
    
    show_progress("Scanning for HID devices", 2.0)
    
    try:
        devices = hid.enumerate()
    except Exception as e:
        print(f"[ERROR] Failed to run hid.enumerate(). Details: {e}")
        sys.exit(1)

    print(f"Total HID devices detected: {len(devices)}")
    print("-" * 60)
    
    # Check if any devices match saved profiles
    profiles_dir = os.path.join(REPO_ROOT, "profiles")
    known_profiles = {}  # (vid, pid) -> profile filename
    if os.path.isdir(profiles_dir):
        import re
        for fname in os.listdir(profiles_dir):
            m = re.match(r"([0-9a-fA-F]{4})_([0-9a-fA-F]{4})\.json", fname)
            if m:
                known_profiles[(int(m.group(1), 16), int(m.group(2), 16))] = fname

    profile_matches = []
    
    for idx, dev in enumerate(devices, 1):
        vid = dev.get('vendor_id', 0)
        pid = dev.get('product_id', 0)
        mfg = dev.get('manufacturer_string', 'Unknown')
        prod = dev.get('product_string', 'Unknown')
        iface = dev.get('interface_number', -1)
        path = dev.get('path', b'')
        
        # Decode path for logging/readability
        path_str = path.decode('utf-8', errors='replace') if isinstance(path, bytes) else str(path)
        
        print(f"\nDevice #{idx}:")
        print(f"  Manufacturer: {mfg}")
        print(f"  Product:      {prod}")
        print(f"  VID:PID:      {hex(vid)}:{hex(pid)} (decimal {vid}:{pid})")
        print(f"  Interface #:  {iface}")
        print(f"  Path:         {path_str}")
        
        # Check if this device has a saved profile
        if (vid, pid) in known_profiles:
            print(f"  *** HAS SAVED PROFILE: {known_profiles[(vid, pid)]} ***")
            profile_matches.append(dev)

        # Check for XInput / Xbox mode indicators
        is_xinput = (
            vid == 0x045E or
            "xbox" in str(prod).lower() or
            "xbox" in str(mfg).lower() or
            "x-input" in str(prod).lower() or
            "x-input" in str(mfg).lower() or
            "xinput" in str(prod).lower() or
            "xinput" in str(mfg).lower()
        )
        if is_xinput:
            print("  [! WARNING !] This device appears to be in XInput (Xbox) Mode.")
            print("  - DirectInput wrappers are usually not needed if your controller is already in XInput mode.")
            print("  - If this is a multi-mode controller (e.g. 8BitDo/Machenike) and you want to use this wrapper")
            print("    to map extra buttons or paddles, please switch the controller's physical mode switch")
            print("    or key-combination to D-Input (DirectInput), Android, or Nintendo Switch mode.")
            if "microsoft" in str(prod).lower() or "microsoft" in str(mfg).lower() or "controller" in str(prod).lower():
                print("  [RECOMMENDED] This specific endpoint has 'microsoft' or 'controller' in its name, so it is the most likely one to contain actual button data if you are calibrating.")

        # Attempt to open to check for exclusive locks
        try:
            h = hid.device()
            h.open_path(path)
            h.close()
            status = "[OK] Accessible (Not locked)"
            print(f"  Access Status: {status}")
        except OSError as e:
            # Classify lock
            usage_page = dev.get('usage_page', 0)
            usage = dev.get('usage', 0)
            
            is_kb_or_mouse = (
                (usage_page == 1 and usage in (2, 6)) or
                "keyboard" in str(mfg).lower() or
                "keyboard" in str(prod).lower() or
                "mouse" in str(mfg).lower() or
                "mouse" in str(prod).lower() or
                "kb" in str(prod).lower() or
                "ms" in str(prod).lower()
            )
            
            if is_kb_or_mouse:
                status = "[LOCKED] OS Exclusive Lock (Normal for system Keyboard/Mouse)"
            else:
                status = f"[LOCKED] Exclusive Lock / Error: {e}"
            
            print(f"  Access Status: {status}")
            
            if (vid, pid) in known_profiles:
                print("  WARNING: This profiled device is locked! Other software (like Steam or Windows) might be using it.")
                
    print("-" * 60)
    show_progress("Analyzing results", 1.0)
    
    print("\n[SUMMARY]")
    if profile_matches:
        print(f"SUCCESS: Found {len(profile_matches)} interface(s) matching saved profiles.")
        for idx, dev in enumerate(profile_matches, 1):
            path = dev.get('path', b'')
            path_str = path.decode('utf-8', errors='replace') if isinstance(path, bytes) else str(path)
            iface = dev.get('interface_number', -1)
            try:
                h = hid.device()
                h.open_path(path)
                h.close()
                print(f"  Interface {iface} (Path: {path_str}) is ACCESSIBLE.")
            except OSError as e:
                print(f"  Interface {iface} (Path: {path_str}) is LOCKED. Details: {e}")
    else:
        print("NOTICE: No devices matching any saved profiles were found.")
        print("Please check connection and ensure the controller is turned on.")
        
    print("=" * 60)
    print("   DEVICE ENUMERATION COMPLETED")
    print("=" * 60)
    print(f"A log of this scan has been saved to:\n  {LOG_FILE}")
    print("=" * 60)

if __name__ == '__main__':
    try:
        main()
    finally:
        logger.close()
