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

import platform
import datetime
import hid

# Setup logging redirection to capture startup, error, and exit outputs
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
LOG_DIR = os.path.join(REPO_ROOT, "diagnostics_logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "03_raw_transport.log")

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

def format_hex_grid(data, row_size=16):
    lines = []
    for i in range(0, len(data), row_size):
        chunk = data[i:i+row_size]
        hex_bytes = " ".join(f"{b:02X}" for b in chunk)
        # Pad the hex representation if it's the last incomplete row
        if len(chunk) < row_size:
            padding = "   " * (row_size - len(chunk))
            hex_bytes += padding
        ascii_chars = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        lines.append(f"{i:04X}: {hex_bytes}  |{ascii_chars}|")
    return "\n".join(lines)

def get_precise_timestamp():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def main():
    print("=" * 60)
    print("   DIAGNOSTIC STEP 3: RAW HID TRANSPORT")
    print("=" * 60)
    print("This script will interface directly with the raw HID device.")
    print("It reads raw input reports, formats them, and writes them to the log.")
    print("-" * 60)
    
    print("[INSTRUCTIONS FOR USER]")
    print("1. Connect your controller to the PC.")
    print("2. Ensure no games or other mapping tools are currently running.")
    print("-" * 60)

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

    # Open target/selected device
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

    print(f"\n[CONNECTED] Successfully opened target transport interface:")
    print(f"  Device:       {prod} ({mfg})")
    print(f"  VID:PID:      {hex(vid)}:{hex(pid)}")
    print(f"  Path:         {path_str}")
    print("-" * 60)
    print("Initializing read loop. Press Ctrl+C at any time to exit and save logs.")
    print("=" * 60)
    time.sleep(1.5)

    packet_count = 0
    last_packets = {}
    
    # Standby UI display
    os.system('cls' if os.name == 'nt' else 'clear')
    print_terminal_only("=" * 70)
    print_terminal_only("               Raw HID Transport Diagnostics UI")
    print_terminal_only("=" * 70)
    print_terminal_only(f"Device:       {prod} ({mfg})")
    print_terminal_only(f"VID:PID:      {hex(vid)}:{hex(pid)}")
    print_terminal_only("State Changes: 0 (Waiting for data...)")
    print_terminal_only("-" * 70)
    print_terminal_only("INSTRUCTIONS FOR TESTING CONTROLLER INPUT:")
    print_terminal_only("1. Press D-pad buttons (Up, Down, Left, Right).")
    print_terminal_only("2. Press action buttons (A, B, X, Y) or shoulder buttons (L, R, L2, R2).")
    print_terminal_only("3. Move the Left and Right analog sticks around.")
    print_terminal_only("-" * 70)
    print_terminal_only("Press Ctrl+C at any time to exit and save the log.")
    print_terminal_only("=" * 70)

    try:
        while True:
            # Read up to 1024 bytes
            data = dev_handle.read(1024)
            if data:
                report_id = data[0] if len(data) > 0 else None
                data_list = list(data)
                
                # Only process if data changed for this report ID
                if report_id is not None and (report_id not in last_packets or last_packets[report_id] != data_list):
                    last_packets[report_id] = data_list
                    packet_count += 1
                    ts = get_precise_timestamp()
                    
                    # Format to hex string for the log file
                    hex_str = " ".join(f"{b:02X}" for b in data)
                    # Silently log the raw bytes with timestamp
                    logger.log_silent(f"{ts}: {hex_str}")
                    
                    # Draw the terminal grid UI using ANSI cursor reset (no flicker)
                    logger.terminal.write("\033[H")  # Move cursor to top-left
                    print_terminal_only("=" * 70)
                    print_terminal_only("               Raw HID Transport Diagnostics UI")
                    print_terminal_only("=" * 70)
                    print_terminal_only(f"Device:       {prod} ({mfg})")
                    print_terminal_only(f"VID:PID:      {hex(vid)}:{hex(pid)}")
                    print_terminal_only(f"State Changes:{packet_count}")
                    print_terminal_only(f"Last Packet:  {len(data)} bytes at {ts}")
                    print_terminal_only("-" * 70)
                    print_terminal_only("INSTRUCTIONS FOR TESTING CONTROLLER INPUT:")
                    print_terminal_only("1. Press D-pad buttons (Up, Down, Left, Right).")
                    print_terminal_only("2. Press action buttons (A, B, X, Y) or shoulder buttons (L, R, L2, R2).")
                    print_terminal_only("3. Move the Left and Right analog sticks around.")
                    print_terminal_only("-" * 70)
                    print_terminal_only("Press Ctrl+C at any time to exit and save the log.")
                    print_terminal_only("-" * 70)
                    print_terminal_only("Hex Grid (16 bytes per row):")
                    print_terminal_only(format_hex_grid(data))
                    print_terminal_only("\033[J", end="")  # Clear any leftover lines below
            else:
                # Small sleep to keep CPU usage low
                time.sleep(0.001)
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("   DIAGNOSTIC SESSION TERMINATED BY USER")
        print("=" * 60)
        print("Clean exit requested via Ctrl+C.")
        try:
            dev_handle.close()
            print("Device handle closed successfully.")
        except Exception as e:
            print(f"Error closing device: {e}")
        print(f"All captured packets and diagnostic logs have been saved to:\n  {LOG_FILE}")
        print("=" * 60)

if __name__ == '__main__':
    try:
        main()
    finally:
        logger.close()
