"""
Gamepad Calibration Tool (calibration.py)
This is an interactive command-line utility that guides users through profiling
their physical DirectInput gamepad. It detects button masks, axis offsets, and
generates a mapping profile in profiles/ to translate raw HID bytes into unified actions.
"""
import os
import json
import time
import sys
import argparse
from logger_setup import setup_logger
from hid_reader import HIDReader
from decoder import Decoder

logger = None

# Enable Virtual Terminal Processing (ANSI escape codes) on Windows
if os.name == 'nt':
    os.system("")


def cls():
    # Move cursor to home (top-left) instead of calling os.system('cls'),
    # which causes screen flickering.
    sys.stdout.write("\033[H")
    sys.stdout.flush()


class Calibrator:
    """
    Manages the step-by-step interactive command-line calibration flow.
    Identifies devices, baselines rest states, scans digital buttons,
    registers analog sticks/triggers, and saves the final JSON profile.
    """

    def __init__(self):
        self.device = None
        self.reader = None
        self.raw_data = []
        self.base_data = []
        self.profile = {
            "name": "Custom Profile",
            "vid": "",
            "pid": "",
            "buttons": {},
            "extra_buttons": {},
            "axes": {}
        }

        self.layout = 'xbox'
        if os.path.exists('config.ini'):
            import configparser
            config = configparser.ConfigParser()
            config.read('config.ini')
            if config.has_option('settings', 'layout'):
                self.layout = config.get('settings', 'layout')

    def get_layout_labels(self):
        if self.layout == 'playstation':
            return {
                'a': 'Cross (X) (Bottom)', 'b': 'Circle (O) (Right)', 'x': 'Square (■) (Left)', 'y': 'Triangle (▲) (Top)',
                'lb': 'L1', 'rb': 'R1', 'lt': 'L2', 'rt': 'R2', 'l3': 'L3', 'r3': 'R3', 'select': 'Share', 'start': 'Options'
            }
        elif self.layout == 'nintendo':
            return {
                'a': 'B (Bottom)', 'b': 'A (Right)', 'x': 'Y (Left)', 'y': 'X (Top)',
                'lb': 'L', 'rb': 'R', 'lt': 'ZL', 'rt': 'ZR', 'l3': 'LS', 'r3': 'RS', 'select': '-', 'start': '+'
            }
        else:
            return {
                'a': 'A (Bottom)', 'b': 'B (Right)', 'x': 'X (Left)', 'y': 'Y (Top)',
                'lb': 'LB', 'rb': 'RB', 'lt': 'LT', 'rt': 'RT', 'l3': 'LS', 'r3': 'RS', 'select': 'Select/Back', 'start': 'Start'
            }

    def get_test_labels(self):
        if self.layout == 'playstation':
            return {'a': 'X', 'b': 'O', 'x': '■', 'y': '▲', 'lb': 'L1', 'rb': 'R1', 'lt': 'L2',
                    'rt': 'R2', 'l3': 'L3', 'r3': 'R3', 'select': 'SHARE', 'start': 'OPTIONS'}
        elif self.layout == 'nintendo':
            return {'a': 'B', 'b': 'A', 'x': 'Y', 'y': 'X', 'lb': 'L', 'rb': 'R',
                    'lt': 'ZL', 'rt': 'ZR', 'l3': 'LS', 'r3': 'RS', 'select': '-', 'start': '+'}
        else:
            return {'a': 'A', 'b': 'B', 'x': 'X', 'y': 'Y', 'lb': 'LB', 'rb': 'RB', 'lt': 'LT',
                    'rt': 'RT', 'l3': 'LS', 'r3': 'RS', 'select': 'SELECT', 'start': 'START'}

    def _data_handler(self, data):
        self.raw_data = list(data)

    def scan_devices(self):
        print("Scanning for HID devices...")
        try:
            devices = HIDReader.get_all_devices()
        except Exception as e:
            print(f"Error scanning for devices: {e}")
            return False

        unique_devices = []
        seen = set()
        for d in devices:
            ident = f"{d.vendor_id:04X}:{d.product_id:04X}"
            if ident not in seen:
                seen.add(ident)
                unique_devices.append(d)

        if not unique_devices:
            print("No HID devices found.")
            return False

        # Try to open devices to listen for auto-detection
        baselines = {}
        detected_device = [None]

        def make_handler(dev):
            def handler(data):
                if detected_device[0] is not None:
                    return
                # Save baseline on first packet
                if dev not in baselines:
                    baselines[dev] = list(data)
                    return
                # Check for input activity
                base = baselines[dev]
                if len(data) != len(base):
                    return
                for idx in range(len(data)):
                    diff = abs(data[idx] - base[idx])
                    if diff > 15:  # threshold for button press or joystick movement
                        detected_device[0] = dev
                        break
            return handler

        opened_devices = []
        for d in unique_devices:
            try:
                d.open()
                d.set_raw_data_handler(make_handler(d))
                opened_devices.append(d)
            except Exception:
                # System devices (keyboard/mouse) usually fail to open (Access
                # Denied), which is good
                pass

        print("\nSelect a device to calibrate:")
        for i, d in enumerate(unique_devices):
            status = " (Listening for input...)" if d in opened_devices else " (Manual selection only)"
            print(
                f"[{i}] VID:{d.vendor_id:04X} PID:{d.product_id:04X} - {d.product_name}{status}")

        print(
            "\n--> PRESS ANY BUTTON OR MOVE A STICK on your controller to auto-detect it.")
        print("--> OR type the choice number below and press ENTER.")
        print("--> Press 'q' then ENTER to quit.")
        print("Choice: ", end="")
        sys.stdout.flush()

        self.device = None
        import msvcrt
        typed_input = ""

        while self.device is None:
            if detected_device[0] is not None:
                self.device = detected_device[0]
                print(
                    f"\nAuto-detected: VID:{
                        self.device.vendor_id:04X} PID:{
                        self.device.product_id:04X} - {
                        self.device.product_name}")
                break

            if msvcrt.kbhit():
                char = msvcrt.getwch()
                if char == '\r':  # ENTER
                    val = typed_input.strip().lower()
                    typed_input = ""
                    print()
                    if val == 'q':
                        print("Quitting calibration.")
                        break
                    try:
                        choice = int(val)
                        if 0 <= choice < len(unique_devices):
                            self.device = unique_devices[choice]
                            break
                        else:
                            print(
                                f"Invalid choice. Please enter a number between 0 and {
                                    len(unique_devices) - 1}.")
                            print("Choice: ", end="")
                            sys.stdout.flush()
                    except ValueError:
                        print("Invalid input. Please enter a valid number or 'q'.")
                        print("Choice: ", end="")
                        sys.stdout.flush()
                elif char in ('\b', '\x08'):  # Backspace
                    if len(typed_input) > 0:
                        typed_input = typed_input[:-1]
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                elif char.isalnum() or char in (' ', '-', '_'):
                    typed_input += char
                    sys.stdout.write(char)
                    sys.stdout.flush()

            time.sleep(0.01)

        # Close all opened listener devices
        for d in opened_devices:
            try:
                if d.is_opened():
                    d.close()
            except Exception:
                pass

        if not self.device:
            return False

        self.profile["vid"] = f"{self.device.vendor_id:04X}"
        self.profile["pid"] = f"{self.device.product_id:04X}"
        self.profile["name"] = self.device.product_name or "Unknown Device"
        return True

    def _wait_for_input(self, prompt, is_axis=False):
        # Wait for the user to press a button and release it, detecting the
        # exact byte/bit changed
        print(f"\n{prompt}")
        print("Waiting for input... (Press 's' to Skip, 'u' to Undo previous)")

        while sys.stdin in select_stdin():
            pass  # clear stdin buffer (rough)

        # We need a non-blocking input check for s/u, but standard python input() blocks.
        # For simplicity in this script, we'll prompt for 's' or 'u' before waiting for the controller,
        # or we just assume they press the controller.
        # Actually, let's just wait for controller input. If they want to skip/undo,
        # they can press a key on the keyboard.
        pass

    def run(self, test_only=False):
        if not self.scan_devices():
            return

        if test_only:
            profile_path = f"profiles/{
                self.device.vendor_id:04X}_{
                self.device.product_id:04X}.json".lower()
            if not os.path.exists(profile_path):
                print(
                    f"\nError: No profile found for this device at {profile_path}.")
                print("Please run the standard calibration first.")
                return

            with open(profile_path, 'r') as f:
                self.profile = json.load(f)

            if "layout" in self.profile:
                self.layout = self.profile["layout"]

            self.reader = HIDReader(device=self.device)
            if not self.reader.connect():
                print("Error: Failed to connect to controller.")
                return

            def _data_handler(data):
                self.raw_data = data
                if logger:
                    current_time = time.time()
                    if not hasattr(self, '_last_log_time'):
                        self._last_log_time = 0
                    if current_time - self._last_log_time >= 0.5:
                        logger.debug(
                            f"RAW: {' | '.join(f'{x:02X}' for x in data)}")
                        self._last_log_time = current_time

            self.reader.set_callback(_data_handler)
            import threading
            t = threading.Thread(target=self.reader.start, daemon=True)
            t.start()

            print("\nWaiting for initial data from the controller...")
            start_time = time.time()
            while not self.raw_data:
                if time.time() - start_time > 10.0:
                    print(
                        "\nError: No data received within 10 seconds. Make sure the controller is turned on and connected.")
                    self.reader.stop()
                    return
                time.sleep(0.1)

            try:
                self.test_mode(profile_path=profile_path)
            finally:
                self.reader.stop()
            return

        # Prompt for visual layout
        print("\nSelect the visual button layout for this controller:")
        print("[1] Xbox (A/B/X/Y)")
        print("[2] PlayStation (X/O/■/▲)")
        print("[3] Nintendo (B/A/Y/X)")
        layout_choice = ""
        while layout_choice not in ["1", "2", "3"]:
            layout_choice = input("Choice [1-3] (default 1): ").strip()
            if not layout_choice:
                layout_choice = "1"

        layout_map = {"1": "xbox", "2": "playstation", "3": "nintendo"}
        self.layout = layout_map[layout_choice]
        self.profile["layout"] = self.layout

        self.reader = HIDReader(device=self.device)
        if not self.reader.connect():
            print("Error: Failed to connect to controller.")
            return
        # Check for user input gracefully

        def _data_handler(data):
            self.raw_data = data
            if logger:
                # Log raw data periodically
                current_time = time.time()
                if not hasattr(self, '_last_log_time'):
                    self._last_log_time = 0
                if current_time - self._last_log_time >= 0.5:
                    logger.debug(
                        f"RAW: {' | '.join(f'{x:02X}' for x in data)}")
                    self._last_log_time = current_time

        self.reader.set_callback(_data_handler)

        # Start reading thread
        import threading
        t = threading.Thread(target=self.reader.start, daemon=True)
        t.start()

        # Wait for first report
        print("\nWaiting for initial data from the controller...")
        print("Please press a button or move a stick to wake it up if needed.")

        start_time = time.time()
        while not self.raw_data:
            if time.time() - start_time > 10.0:
                print(
                    "\nError: No data received within 10 seconds. Make sure the controller is turned on and connected.")
                self.reader.stop()
                return
            time.sleep(0.1)

        self.base_data = list(self.raw_data)

        print("\n--- Calibration Started ---")
        print("Please DO NOT touch the controller for 2 seconds while we establish a baseline...")
        time.sleep(2)
        self.base_data = list(self.raw_data)

        try:
            self._calibrate_loop()
        finally:
            self.reader.stop()

    def _calibrate_loop(self):
        # We will do a simpler approach:
        # For each button, record base state. Wait until a byte changes significantly.
        # For buttons, we look for a bit change.
        # For axes, we look for an amplitude change.

        labels = self.get_layout_labels()

        steps = [
            ("a", "buttons", f"Press the '{labels['a']}' button"),
            ("b", "buttons", f"Press the '{labels['b']}' button"),
            ("x", "buttons", f"Press the '{labels['x']}' button"),
            ("y", "buttons", f"Press the '{labels['y']}' button"),
            ("lb", "buttons", f"Press the '{labels['lb']}' bumper"),
            ("rb", "buttons", f"Press the '{labels['rb']}' bumper"),
            ("select", "buttons", f"Press the '{labels['select']}' button"),
            ("start", "buttons", f"Press the '{labels['start']}' button"),
            ("home", "buttons", "Press the Home/Guide button"),
            ("l3", "buttons", f"Press the Left Stick button ({labels['l3']})"),
            ("r3", "buttons",
             f"Press the Right Stick button ({labels['r3']})"),
            ("lx", "axes", "Move the Left Stick RIGHT"),
            ("ly", "axes", "Move the Left Stick UP"),
            ("rx", "axes", "Move the Right Stick RIGHT"),
            ("ry", "axes", "Move the Right Stick UP"),
            ("lt", "axes", f"Press the Left Trigger ({labels['lt']})"),
            ("rt", "axes", f"Press the Right Trigger ({labels['rt']})"),
            ("dpad", "hat", "Press the D-Pad UP (Assuming standard Hat switch)")
        ]

        # Extra buttons
        num_extras = -1
        while num_extras < 0:
            user_input = input(
                "\nHow many extra buttons (Not counting Home/Guide. e.g., L4, R4) does this controller have? (or 'q' to quit): ").strip().lower()
            if user_input == 'q':
                print("Quitting calibration.")
                return
            try:
                num_extras = int(user_input)
                if num_extras < 0:
                    print("Please enter a positive number or 0.")
            except ValueError:
                print("Invalid input. Please enter a valid number or 'q'.")

        for i in range(num_extras):
            name = ""
            while not name:
                name = input(
                    f"Enter a name for extra button {
                        i + 1} (e.g., l4, m1): ").strip().lower()
                if not name:
                    print("Name cannot be empty.")
            steps.append(
                (name, "extra_buttons", f"Press the '{name}' extra button"))


        i = 0
        while i < len(steps):
            name, cat, prompt = steps[i]

            print(f"\n[{i + 1}/{len(steps)}] {prompt}")
            print("To skip, press ENTER on your keyboard. To undo, PRESS 'u'.")

            # Update base data
            time.sleep(0.5)
            self.base_data = list(self.raw_data)

            if not self.base_data:
                print("No data received from controller. Make sure it's awake.")
                time.sleep(1)
                continue

            done = False
            undo = False

            import msvcrt

            while not done:
                # Check for keyboard input
                if msvcrt.kbhit():
                    char = msvcrt.getwche()
                    if char == '\r':
                        print("\nSkipped.")
                        done = True
                        break
                    elif char.lower() == 'u':
                        undo = True
                        print("\nUndoing previous step.")
                        done = True
                        break

                # Check controller data
                current = list(self.raw_data)
                if not current or len(current) != len(self.base_data):
                    time.sleep(0.01)
                    continue

                diffs = []
                for b_idx in range(len(current)):
                    if current[b_idx] != self.base_data[b_idx]:
                        diffs.append(
                            (b_idx, current[b_idx], self.base_data[b_idx]))

                if diffs:
                    if cat in ("buttons", "extra_buttons"):
                        # Look for bit changes
                        changed_bytes = []
                        for b_idx, curr_val, base_val in diffs:
                            changed_bits = curr_val ^ base_val
                            if changed_bits != 0:
                                changed_bytes.append((b_idx, changed_bits))

                        if len(changed_bytes) == 1:
                            b_idx, mask = changed_bytes[0]
                            # Only accept if it's a clean bit mask (power of 2) or we just take the XOR difference
                            # Often multiple bits might toggle if it's noisy.
                            # Let's just take the first changed bit.
                            bit_mask = mask & -mask  # get lowest set bit
                            self.profile[cat][name] = {
                                "byte": b_idx, "mask": bit_mask}
                            print(
                                f"Detected {name} at byte {b_idx}, mask {bit_mask}")
                            done = True
                        elif len(changed_bytes) > 1:
                            print(
                                "\nMultiple buttons pressed simultaneously. Please press only one cleanly.")
                            time.sleep(1)
                            self.base_data = list(self.raw_data)

                    elif cat == "axes":
                        # Look for amplitude change
                        amplitudes = []
                        for b_idx, curr_val, base_val in diffs:
                            amp = abs(curr_val - base_val)
                            if amp > 10:  # threshold for noise
                                amplitudes.append((amp, b_idx))

                        if amplitudes:
                            amplitudes.sort(reverse=True)
                            best_amp, best_idx = amplitudes[0]

                            # Robustness: Check if there's cross-axis
                            # contamination
                            if len(amplitudes) > 1:
                                second_amp = amplitudes[1][0]
                                if second_amp > best_amp * 0.5:  # If the second biggest change is > 50% of the biggest
                                    print(
                                        "\nDetected movement on multiple axes. Please move ONLY the requested axis carefully.")
                                    time.sleep(1.5)
                                    self.base_data = list(self.raw_data)
                                    continue

                            self.profile[cat][name] = {"byte": best_idx}
                            print(
                                f"Detected {name} at byte {best_idx} (Amplitude: {best_amp})")
                            done = True

                    elif cat == "hat":
                        # Assuming D-Pad changes a single byte
                        changed_bytes = [
                            d for d in diffs if abs(
                                d[1] - d[2]) > 0]
                        if len(changed_bytes) == 1:
                            b_idx = changed_bytes[0][0]
                            self.profile["buttons"]["dpad"] = {
                                "byte": b_idx, "type": "hat"}
                            print(f"Detected D-Pad hat at byte {b_idx}")
                            done = True
                        elif len(changed_bytes) > 1:
                            print(
                                "\nMultiple bytes changed. Press only the D-Pad cleanly.")
                            time.sleep(1)
                            self.base_data = list(self.raw_data)

                time.sleep(0.01)

            if undo:
                if i > 0:
                    i -= 1
                    # Remove from profile if exists
                    prev_name, prev_cat, _ = steps[i]
                    if prev_name in self.profile[prev_cat]:
                        del self.profile[prev_cat][prev_name]
                continue

            # Wait for release before next step
            print("Release the button/stick...")
            time.sleep(0.5)
            self.base_data = list(self.raw_data)
            i += 1

        self.save_profile()
        self.test_mode()

    def save_profile(self):
        try:
            os.makedirs("profiles", exist_ok=True)
            filename = f"profiles/{
                self.profile['vid']}_{
                self.profile['pid']}.json".lower()
            with open(filename, 'w') as f:
                json.dump(self.profile, f, indent=4)
            print(f"\nProfile saved to {filename}")
        except Exception as e:
            print(f"\nFailed to save profile: {e}")

    def test_mode(self, profile_path=None):
        print("\n--- Test Mode ---")
        print("Press Ctrl+C to exit test mode.")
        time.sleep(1.5)

        # Clear once before starting live updates
        os.system('cls' if os.name == 'nt' else 'clear')

        if not profile_path:
            # Save temp file for Decoder to load
            temp_path = "profiles/temp_test.json"
            try:
                os.makedirs("profiles", exist_ok=True)
                with open(temp_path, 'w') as f:
                    json.dump(self.profile, f)
            except Exception as e:
                print(f"Error creating temp profile for test mode: {e}")
                return
            profile_path = temp_path
            is_temp = True
        else:
            is_temp = False

        try:
            decoder = Decoder(profile_path)
        except Exception as e:
            print(f"Error initializing decoder for test mode: {e}")
            return

        try:
            while True:
                state = decoder.decode(self.raw_data)
                cls()
                test_labels = self.get_test_labels()
                print("--- LIVE TEST MODE (Ctrl+C to exit) ---")
                print(f"Profile: {self.profile['name']}")
                print("\nStandard Buttons:")
                for b in ['a', 'b', 'x', 'y', 'lb', 'rb',
                          'select', 'start', 'home', 'l3', 'r3']:
                    val = getattr(state, b)
                    lbl = test_labels.get(b, b.upper())
                    print(f"{lbl}: {'[X]' if val else '[ ]'}", end="  ")
                print("\n\nD-Pad:")
                print(
                    f"UP: {
                        '[X]' if state.dpad_up else '[ ]'}  DOWN: {
                        '[X]' if state.dpad_down else '[ ]'}  LEFT: {
                        '[X]' if state.dpad_left else '[ ]'}  RIGHT: {
                        '[X]' if state.dpad_right else '[ ]'}")
                print("\nAxes:")

                grid_size = 5

                def get_grid(x, y):
                    x = max(0, min(255, x))
                    y = max(0, min(255, y))
                    cx = int(round((x / 255.0) * (grid_size - 1)))
                    cy = int(round((y / 255.0) * (grid_size - 1)))

                    lines = []
                    for row in range(grid_size):
                        line = ""
                        for col in range(grid_size):
                            if row == cy and col == cx:
                                line += "O "
                            elif row == grid_size // 2 and col == grid_size // 2:
                                line += "+ "
                            else:
                                line += ". "
                        lines.append(line.rstrip())
                    return lines

                def get_trigger(val):
                    val = max(0, min(255, val))
                    h = int(round((val / 255.0) * grid_size))
                    lines = []
                    for row in range(grid_size):
                        if (grid_size - 1 - row) < h:
                            lines.append("█")
                        else:
                            lines.append("▒")
                    return lines

                l_grid = get_grid(state.lx, state.ly)
                r_grid = get_grid(state.rx, state.ry)
                lt_bar = get_trigger(state.lt)
                rt_bar = get_trigger(state.rt)

                lt_name = test_labels.get('lt', 'LT')
                rt_name = test_labels.get('rt', 'RT')

                print(
                    f"Left Stick (LX:{
                        state.lx:3d}, LY:{
                        state.ly:3d})   Right Stick (RX:{
                        state.rx:3d}, RY:{
                        state.ry:3d})   {lt_name}:{
                        state.lt:3d}   {rt_name}:{
                            state.rt:3d}")
                for i in range(grid_size):
                    print(
                        f"  {
                            l_grid[i]:<10}                    {
                            r_grid[i]:<10}                 {
                            lt_bar[i]}        {
                            rt_bar[i]}")

                if state.extra_buttons:
                    print("\nExtra Buttons:")
                    for name, val in state.extra_buttons.items():
                        print(
                            f"{name.upper()}: {'[X]' if val else '[ ]'}", end="  ")
                print("\n\033[J", end="")  # Clear remainder of screen below
                sys.stdout.flush()
                time.sleep(0.05)
        except KeyboardInterrupt:
            pass
        finally:
            if is_temp and os.path.exists(profile_path):
                os.remove(profile_path)
            print("\nExiting Test Mode.")


def select_stdin():
    # Helper to flush stdin on windows, but it's not foolproof.
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--log',
        action='store_true',
        help='Enable verbose debugging logs')
    parser.add_argument(
        '--test-only',
        action='store_true',
        help='Skip calibration and only run the input tester')
    args = parser.parse_args()

    # We pass append=False so it creates a fresh log file per execution
    logger = setup_logger(
        'calibration',
        'calibration.log',
        args.log,
        append=False)

    if args.log:
        logger.info("Calibration Tool started in debug mode")

    calibrator = Calibrator()
    calibrator.run(test_only=args.test_only)
