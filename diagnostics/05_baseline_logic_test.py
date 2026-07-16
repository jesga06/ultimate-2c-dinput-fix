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
LOG_FILE = os.path.join(LOG_DIR, "05_baseline_logic_test.log")

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
    print("   DIAGNOSTIC STEP 5: BASELINE CALIBRATION & LOGIC TEST")
    print("=" * 70)
    print("This script establishes a resting baseline of your controller's bytes")
    print("and monitors real-time differences (deltas) as you press inputs.")
    print("-" * 70)
    print("[INSTRUCTIONS FOR USER]")
    print("1. Connect your controller to the PC.")
    print("2. Place the controller on a flat, stable surface.")
    print("3. DO NOT touch the controller, buttons, or joysticks during calibration.")
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

    # Prompt user for calibration resting baseline
    print("CALIBRATION STEP: Please place the controller on a flat surface and DO NOT TOUCH IT or move any buttons. This will establish a resting baseline. Starting in 3 seconds...")
    for i in range(3, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1.0)

    print("\n[CALIBRATING] Establishing resting baseline (running for 2 seconds)...")
    
    calibration_packets = {}  # report_id -> list of packet lists
    start_time = time.time()
    duration = 2.0
    
    while time.time() - start_time < duration:
        # Non-blocking read
        data = dev_handle.read(1024)
        if data:
            report_id = data[0]
            if report_id not in calibration_packets:
                calibration_packets[report_id] = []
            calibration_packets[report_id].append(list(data))
        else:
            time.sleep(0.001)

    # If no packets were received during the 2 seconds, wait for the first one
    if not calibration_packets:
        print("\n[INFO] No packets received during calibration.")
        print("Your controller likely only sends data when an input changes.")
        print(">>> PLEASE TAP ANY BUTTON ONCE AND RELEASE IT, THEN DO NOT TOUCH IT. <<<")
        
        # Wait until we get at least one packet
        while True:
            data = dev_handle.read(1024)
            if data:
                break
            time.sleep(0.005)
            
        print("[INFO] Data detected. Waiting 2 seconds for resting state to settle...")
        time.sleep(2.0)
        
        # Now drain the buffer and take the absolute latest packet for each report ID as the baseline
        while True:
            data = dev_handle.read(1024)
            if not data:
                break
            report_id = data[0]
            if report_id not in calibration_packets:
                calibration_packets[report_id] = []
            calibration_packets[report_id] = [list(data)] # Overwrite with the latest one

    # Compute baseline by averaging the packets
    baselines = {}
    last_packets = {}
    for report_id, packets in calibration_packets.items():
        num_packets = len(packets)
        packet_len = len(packets[0])
        baseline_packet = []
        for byte_idx in range(packet_len):
            avg_val = int(round(sum(p[byte_idx] for p in packets) / num_packets))
            baseline_packet.append(avg_val)
        baselines[report_id] = baseline_packet
        # Initialize last seen packet to baseline to detect first transition
        last_packets[report_id] = list(baseline_packet)

    # Print baseline hex row(s)
    print("\n[+] Resting baseline established successfully:")
    logger.log_silent("\nResting baseline established:")
    for report_id, baseline in baselines.items():
        hex_row = " ".join(f"{b:02X}" for b in baseline)
        print(f"  Report ID 0x{report_id:02X} ({len(baseline)} bytes): {hex_row}")
        logger.log_silent(f"  Report ID 0x{report_id:02X} ({len(baseline)} bytes): {hex_row}")

    print("\n" + "=" * 80)
    print("BASELINE ESTABLISHED: You can now press buttons and move joysticks. The script will print the exact changes relative to the baseline in real-time. Press Ctrl+C when you are finished.")
    print("=" * 80 + "\n")

    logger.log_silent("\nStarting real-time baseline comparison loop:")
    logger.log_silent("-" * 70)

    try:
        while True:
            data = dev_handle.read(1024)
            if data:
                ts = get_precise_timestamp()
                report_id = data[0]
                
                # Handle dynamic report IDs on the fly
                if report_id not in baselines:
                    baselines[report_id] = list(data)
                    last_packets[report_id] = list(data)
                    hex_row = " ".join(f"{b:02X}" for b in data)
                    print_terminal_only(f"[INFO] New Report ID 0x{report_id:02X} detected dynamically. Baseline: {hex_row}")
                    logger.log_silent(f"[{ts}] New Report ID 0x{report_id:02X} baseline established: {hex_row}")
                    continue

                baseline = baselines[report_id]
                last_packet = last_packets[report_id]

                # Adjust length dynamically if needed
                if len(data) != len(baseline):
                    if len(baseline) > len(data):
                        baseline = baseline[:len(data)]
                        last_packet = last_packet[:len(data)]
                    else:
                        baseline = baseline + [0] * (len(data) - len(baseline))
                        last_packet = last_packet + [0] * (len(data) - len(last_packet))
                    baselines[report_id] = baseline
                    last_packets[report_id] = last_packet

                # Check if this packet differs from the LAST SEEN packet to avoid console spamming
                if list(data) != last_packet:
                    for i in range(len(data)):
                        # If the byte value changed since the last packet
                        if data[i] != last_packet[i]:
                            # If it differs from the established baseline, print the delta
                            if data[i] != baseline[i]:
                                delta = data[i] - baseline[i]
                                delta_str = f"+{delta}" if delta > 0 else f"{delta}"
                                msg = f"Byte {i} changed: 0x{baseline[i]:02X} -> 0x{data[i]:02X} (Delta: {delta_str})"
                                print_terminal_only(msg)
                                logger.log_silent(f"[{ts}] Report ID 0x{report_id:02X} - {msg}")
                            else:
                                # It returned to the baseline value
                                msg = f"Byte {i} returned to baseline: 0x{baseline[i]:02X}"
                                print_terminal_only(msg)
                                logger.log_silent(f"[{ts}] Report ID 0x{report_id:02X} - {msg}")

                    # Update last packet state
                    last_packets[report_id] = list(data)
            else:
                # Small sleep to keep CPU utilization extremely low
                time.sleep(0.001)
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("   DIAGNOSTIC SESSION TERMINATED BY USER")
        print("=" * 70)
        print("Clean exit requested via Ctrl+C.")
        try:
            dev_handle.close()
            print("Device handle closed successfully.")
        except Exception as e:
            print(f"Error closing device: {e}")
        print(f"All delta events and logs have been silently saved to:\n  {LOG_FILE}")
        print("=" * 70)

if __name__ == '__main__':
    try:
        main()
    finally:
        logger.close()
