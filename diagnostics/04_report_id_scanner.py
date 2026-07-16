import sys
import os
import time
import datetime
import hid

# Setup logging redirection to capture everything
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
LOG_DIR = os.path.join(REPO_ROOT, "diagnostics_logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "04_report_id_scanner.log")

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

    def log_silent(self, message):
        """Silently write a message to the log file only."""
        if not self.closed:
            try:
                self.log.write(message + "\n")
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

def get_precise_timestamp():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def main():
    print("=" * 70)
    print("   DIAGNOSTIC STEP 4: REPORT ID & PACKET TOPOLOGY SCANNER")
    print("=" * 70)
    print("This script connects to your controller and scans")
    print("for all unique USB HID Report IDs and packet sizes it transmits.")
    print("-" * 70)
    print("[INSTRUCTIONS FOR USER]")
    print("1. Plug your controller into a USB port on this PC.")
    print("2. Ensure no other applications (like Steam, Remappers) are running.")
    print("3. When the scanning phase begins, press buttons, move sticks, and pull")
    print("   triggers continuously. This ensures we scan every possible report ID.")
    print("-" * 70)

    # Enumerate devices
    try:
        devices = hid.enumerate()
    except Exception as e:
        print(f"[ERROR] Failed to run hid.enumerate(). Details: {e}")
        sys.exit(1)

    if not devices:
        print("[ERROR] No HID devices connected or detected on this system.")
        sys.exit(1)

    # List all devices and let user pick
    print("\nAll HID devices detected on this system:")
    for idx, dev in enumerate(devices):
        mfg = dev.get('manufacturer_string', 'Unknown')
        prod = dev.get('product_string', 'Unknown')
        vid = dev.get('vendor_id', 0)
        pid = dev.get('product_id', 0)
        iface = dev.get('interface_number', -1)
        print(f"  [{idx:2d}] VID:{vid:04X} PID:{pid:04X} - {prod} ({mfg}) [Iface {iface}]")

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

    # Open selected device
    try:
        dev_handle = hid.device()
        dev_handle.open_path(selected_device['path'])
        dev_handle.set_nonblocking(True)
    except Exception as e:
        print(f"\n[ERROR] Failed to open device: {e}")
        print("Please verify connection and lock status.")
        sys.exit(1)

    mfg = selected_device.get('manufacturer_string', 'Unknown')
    prod = selected_device.get('product_string', 'Unknown')
    vid = selected_device.get('vendor_id', 0)
    pid = selected_device.get('product_id', 0)
    path = selected_device.get('path', b'')
    path_str = path.decode('utf-8', errors='replace') if isinstance(path, bytes) else str(path)

    print(f"\n[CONNECTED] Successfully opened controller interface:")
    print(f"  Device:       {prod} ({mfg})")
    print(f"  VID:PID:      {hex(vid)}:{hex(pid)}")
    print(f"  Path:         {path_str}")
    print("-" * 70)

    # Prompt user to prepare
    try:
        input("PREPARATION STEP: Please prepare to press buttons/sticks. Press Enter when ready to start...")
    except KeyboardInterrupt:
        print("\nExiting.")
        dev_handle.close()
        sys.exit(0)

    print("\nStarting 3-second preparation countdown...")
    for i in range(3, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1.0)

    print("\n" + "=" * 80)
    print("Please press buttons, triggers, and move joysticks continuously now so we can scan all reports. DO NOT TOUCH the USB connection or unplug the controller.")
    print("=" * 80 + "\n")

    unique_reports = {} # (report_id, length) -> count
    all_packets = [] # (timestamp, report_id, size)
    last_packets = {}
    
    start_time = time.time()
    duration = 10.0
    last_ui_update = 0.0

    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed >= duration:
                break
            
            # Read non-blocking
            data = dev_handle.read(1024)
            if data:
                report_id = data[0] if len(data) > 0 else None
                data_list = list(data)
                
                if report_id is not None and (report_id not in last_packets or last_packets[report_id] != data_list):
                    last_packets[report_id] = data_list
                    ts = get_precise_timestamp()
                    length = len(data)
                    
                    # Record packet
                    all_packets.append((ts, report_id, length))
                    
                    # Catalog unique combinations
                    key = (report_id, length)
                    unique_reports[key] = unique_reports.get(key, 0) + 1
                    
                    # Log packet silently to log file
                    hex_str = " ".join(f"{b:02X}" for b in data)
                    logger.log_silent(f"{ts} - Report ID: 0x{report_id:02X} (Length: {length}): {hex_str}")
            else:
                time.sleep(0.001)

            # Update terminal countdown (every 0.1 seconds to avoid excessive redraws)
            current_time = time.time()
            if current_time - last_ui_update >= 0.1:
                remaining = max(0.0, duration - elapsed)
                print_terminal_only(f"\r[SCANNING] Time remaining: {remaining:.1f}s | State Changes: {len(all_packets)} | Unique Report IDs: {len(unique_reports)}", end="")
                last_ui_update = current_time
    except KeyboardInterrupt:
        print("\n\n[WARNING] Scan interrupted by user.")
    finally:
        # Final terminal update to clear countdown line
        print_terminal_only("")
        dev_handle.close()

    # Log/Print results
    print("\n" + "=" * 70)
    print("                      REPORT ID SCAN SUMMARY")
    print("=" * 70)
    print(f"Total State Changes Captured: {len(all_packets)}")
    
    # Write summary header to log file silently as well
    logger.log_silent("\n" + "=" * 70)
    logger.log_silent("                      REPORT ID SCAN SUMMARY")
    logger.log_silent("=" * 70)
    logger.log_silent(f"Total State Changes Captured: {len(all_packets)}")

    if unique_reports:
        # Output table
        table_header = f"{'Report ID (Hex)':<18} | {'Report ID (Dec)':<18} | {'Packet Length':<15} | {'Count':<10}"
        table_separator = "-" * len(table_header)
        print(table_separator)
        print(table_header)
        print(table_separator)
        
        logger.log_silent(table_separator)
        logger.log_silent(table_header)
        logger.log_silent(table_separator)

        for (rep_id, length), count in sorted(unique_reports.items()):
            row_str = f"0x{rep_id:02X}{'':<14} | {rep_id:<18} | {length:<10} bytes | {count:<10}"
            print(row_str)
            logger.log_silent(row_str)

        print(table_separator)
        logger.log_silent(table_separator)
    else:
        no_data_str = "No state changes were captured. Please verify that the controller inputs were generated."
        print(no_data_str)
        logger.log_silent(no_data_str)

    # Save detailed packet list to log silently
    logger.log_silent("\nDetailed Packet Log:")
    logger.log_silent("-" * 70)
    for ts, rep_id, size in all_packets:
        logger.log_silent(f"{ts} - Report ID: 0x{rep_id:02X}, Size: {size} bytes")
    logger.log_silent("-" * 70)

    print(f"\nA complete log of this test has been saved to:\n  {LOG_FILE}")
    print("=" * 70)

if __name__ == '__main__':
    try:
        main()
    finally:
        logger.close()
