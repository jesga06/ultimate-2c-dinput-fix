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
if sys.version_info[:2] not in ((3, 13), (3, 14)):
    print("WARNING: This script requires Python 3.13.x or 3.14.x. Other versions may fail to compile/load hidapi.")
import argparse
import threading
from logger_setup import setup_logger
from hid_reader import HIDReader, HIDReport, RawHIDReport
from decoder import Decoder

logger = None

# Enable Virtual Terminal Processing (ANSI escape codes) on Windows
if os.name == 'nt':
    os.system("")
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


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
        self.latest_reports = {} # { report_id: HIDReport }
        self.baselines = {} # { report_id: data }
        self.profile = {
            "name": "Custom Profile",
            "vid": "",
            "pid": "",
            "has_report_id": True,
            "reports": {}
        }

        self.layout = 'xbox'
        if os.path.exists('config.ini'):
            import configparser
            config = configparser.ConfigParser()
            config.read('config.ini')
            if config.has_section('controller') and config.has_option('controller', 'last_profile'):
                last_profile = config.get('controller', 'last_profile')
                if os.path.exists(last_profile):
                    try:
                        import json
                        with open(last_profile, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        if 'layout' in data:
                            self.layout = data['layout']
                    except:
                        pass

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

    def _data_handler(self, report: HIDReport):
        self.latest_reports[str(report.report_id)] = report

    def scan_devices(self, test_only=False):
        print("==================================================================")
        print("NOTICE: Please ensure your controller is set to DInput mode (not XInput).")
        print("If you just switched modes, select the option to rescan devices.")
        print("==================================================================\n")
        print("Scanning for HID devices...")
        if logger: logger.info("Scanning for HID devices...")
        
        while True:
            try:
                devices = HIDReader.get_all_devices()
            except Exception as e:
                print(f"Error scanning for devices: {e}")
                if logger: logger.error(f"Error scanning for devices: {e}")
                return False

            unique_devices = {}
            for d in devices:
                vid = d.get('vendor_id', 0)
                pid = d.get('product_id', 0)
                ident = f"{vid:04X}:{pid:04X}"
                if ident not in unique_devices:
                    unique_devices[ident] = {
                        'vid': vid,
                        'pid': pid,
                        'name': d.get('product_string', 'Unknown'),
                        'interfaces': []
                    }
                unique_devices[ident]['interfaces'].append(d)

            if not unique_devices:
                print("No HID devices found. Press Enter to rescan or 'q' to quit.")
                choice = input("Choice: ").strip().lower()
                if choice == 'q': return False
                continue

            dev_list = list(unique_devices.values())
            print("\nSelect your controller:")
            for i, d in enumerate(dev_list):
                print(f"[{i}] VID:{d['vid']:04X} PID:{d['pid']:04X} - {d['name']}")
            print(f"[{len(dev_list)}] Rescan for devices")
            print("Choice (or 'q' to quit): ", end="")
            sys.stdout.flush()

            import msvcrt
            typed_input = ""
            selected_group = None
            while selected_group is None:
                if msvcrt.kbhit():
                    char = msvcrt.getwche()
                    if char == '\r':
                        if typed_input == 'q': return False
                        try:
                            choice = int(typed_input)
                            if choice == len(dev_list):
                                break # Rescan
                            elif 0 <= choice < len(dev_list):
                                selected_group = dev_list[choice]
                            else:
                                print("\nInvalid choice. Try again.")
                                typed_input = ""
                        except ValueError:
                            print("\nInvalid input. Try again.")
                            typed_input = ""
                    else:
                        typed_input += char
                time.sleep(0.01)

            if selected_group is None:
                continue # Rescanning

            def make_handler(iface_num):
                def handler(report: RawHIDReport):
                    if not self.profile.get("has_report_id", True):
                        report.report_id = 0
                    if iface_num not in self.latest_reports:
                        self.latest_reports[iface_num] = {}
                    self.latest_reports[iface_num][str(report.report_id)] = report
                return handler

            self.latest_reports = {}

            if test_only:
                profile_path = f"profiles/{selected_group['vid']:04X}_{selected_group['pid']:04X}.json".lower()
                if not os.path.exists(profile_path):
                    print(f"\nError: No profile found for this device at {profile_path}.")
                    print("Please run the standard calibration first.")
                    return False
                with open(profile_path, 'r') as f:
                    self.profile = json.load(f)
                active_interfaces = set(self.profile.get("interfaces", []))
                
                self.device = selected_group
                self.readers = []
                for d in selected_group['interfaces']:
                    iface_num = d.get('interface_number', -1)
                    if iface_num in active_interfaces:
                        try:
                            reader = HIDReader(device_path=d['path'], auto_reconnect=False, interface_number=iface_num)
                            if reader.connect():
                                reader.set_callback(make_handler(iface_num))
                                import threading
                                t = threading.Thread(target=reader.start, daemon=True)
                                t.start()
                                self.readers.append((iface_num, reader))
                        except Exception:
                            pass
                return True

            opened_readers = []
            
            self.baselines = {}
            for d in selected_group['interfaces']:
                iface_num = d.get('interface_number', -1)
                try:
                    reader = HIDReader(device_path=d['path'], auto_reconnect=False, interface_number=iface_num)
                    if reader.connect():
                        reader.set_callback(make_handler(iface_num))
                        import threading
                        t = threading.Thread(target=reader.start, daemon=True)
                        t.start()
                        opened_readers.append((iface_num, reader, d))
                except Exception:
                    pass

            print("\n--- Stage 1: Interface Discovery ---")
            print("WARNING: Once the discovery timer starts, you must interact with all inputs.")
            print("Please prepare to press EVERY button at least once, press triggers to their full extent,")
            print("and move the sticks in all directions.")
            input("Press ENTER to start the 15-second discovery window...")
            print("\nDiscovery timer started! Go, interact with all inputs!")
            
            start_time = time.time()
            active_interfaces = set()
            
            time.sleep(1.0)
            initial_baselines = {}
            for iface, reps in self.latest_reports.items():
                initial_baselines[iface] = {}
                for r_id, r in reps.items():
                    initial_baselines[iface][r_id] = list(r.data)
            
            while time.time() - start_time < 15.0:
                if msvcrt.kbhit() and msvcrt.getwch() == '\r':
                    break
                
                for iface, reps in self.latest_reports.items():
                    if iface in active_interfaces: continue
                    for r_id, r in reps.items():
                        if iface in initial_baselines and r_id in initial_baselines[iface]:
                            base = initial_baselines[iface][r_id]
                            curr = list(r.data)
                            if len(curr) == len(base):
                                for i in range(len(curr)):
                                    if abs(curr[i] - base[i]) > 10:
                                        active_interfaces.add(iface)
                                        break
                time.sleep(0.01)

            print("\nDiscovery complete.")
            if not active_interfaces:
                print("No activity detected on any interface.")
                print("\n--- Stage 2: Manual Interface Selection ---")
                print("Please select which interfaces to enable for this controller.")
                for i, (iface_num, r, d) in enumerate(opened_readers):
                    print(f"[{i}] Interface: {iface_num} | Usage Page: {d.get('usage_page', 'N/A')} | Usage: {d.get('usage', 'N/A')}")
                
                print("Enter comma-separated choices (e.g. 0,1) or 'q' to quit: ")
                choices = input("Choices: ").strip().lower()
                if choices == 'q':
                    for _, r, _ in opened_readers: r.stop()
                    return False
                
                try:
                    selected_indices = [int(x.strip()) for x in choices.split(',') if x.strip()]
                    for idx in selected_indices:
                        if 0 <= idx < len(opened_readers):
                            active_interfaces.add(opened_readers[idx][0])
                except Exception:
                    pass

            if not active_interfaces:
                print("No interfaces selected. Quitting.")
                for _, r, _ in opened_readers: r.stop()
                return False

            print(f"\nActive interfaces selected: {list(active_interfaces)}")
            if logger: logger.info(f"Active interfaces selected: {list(active_interfaces)}")
            
            self.readers = []
            for iface_num, r, d in opened_readers:
                if iface_num in active_interfaces:
                    self.readers.append((iface_num, r))
                else:
                    r.stop()
                    
            self.device = selected_group # for compatibility
            self.profile["vid"] = f"{selected_group['vid']:04X}"
            self.profile["pid"] = f"{selected_group['pid']:04X}"
            self.profile["name"] = selected_group['name']
            self.profile["interfaces"] = list(active_interfaces)
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
        if not test_only:
            print("==================================================================")
            print("NOTICE: Please disable any 'no dead-zone' (raw/instant) joystick")
            print("configurations on your controller before starting calibration.")
            print("Immensely increased joystick sensitivity may disrupt calibration.")
            print("==================================================================\n")
        if not self.scan_devices(test_only=test_only):
            return

        if test_only:
            profile_path = f"profiles/{self.device.get('vid', 0):04X}_{self.device.get('pid', 0):04X}.json".lower()
            if "layout" in self.profile:
                self.layout = self.profile["layout"]

            try:
                self.test_mode(profile_path=profile_path)
            finally:
                for _, r in self.readers: r.stop()
            return

        remapping_targets = None
        profile_path = f"profiles/{self.profile['vid']}_{self.profile['pid']}.json".lower()
        if os.path.exists(profile_path):
            print("\nAn existing profile was found for this controller.")
            print("[1] Recalibrate Everything (Overwrite)")
            print("[2] Remap Specific Inputs")
            print("[3] Exit")
            choice = ""
            while choice not in ["1", "2", "3"]:
                choice = input("Choice [1-3]: ").strip()
            if choice == "3":
                for _, r in self.readers: r.stop()
                return
            elif choice == "2":
                try:
                    with open(profile_path, 'r', encoding='utf-8') as f:
                        old_profile = json.load(f)
                    
                    for k, v in old_profile.items():
                        if k not in ["name", "vid", "pid", "interfaces"]:
                            self.profile[k] = v
                            
                    all_standard = ["a", "b", "x", "y", "lb", "rb", "select", "start", "home", "lx", "ly", "rx", "ry", "l3", "r3", "lt", "rt", "dpad"]
                    mapped_inputs = []
                    for rep_id, rep_data in old_profile.get("reports", {}).items():
                        for in_name in rep_data.get("inputs", {}).keys():
                            mapped_inputs.append(in_name)
                    
                    mapped_inputs = sorted(list(set(mapped_inputs)))
                    unmapped_inputs = sorted([inp for inp in all_standard if inp not in mapped_inputs])
                    
                    print(f"\nCurrently Mapped Inputs: {', '.join(mapped_inputs) if mapped_inputs else 'None'}")
                    print(f"Currently Unmapped Standard Inputs: {', '.join(unmapped_inputs) if unmapped_inputs else 'None'}")
                    
                    print("\nEnter the names of the inputs you want to remap, separated by commas.")
                    print("Standard inputs: a, b, x, y, lb, rb, lt, rt, l3, r3, select, start, home, lx, ly, rx, ry, dpad")
                    print("(You can also enter extra button names, e.g. l4)")
                    inputs_str = input("Inputs to remap: ").strip().lower()
                    remapping_targets = [x.strip() for x in inputs_str.split(',') if x.strip()]
                    
                    if not remapping_targets:
                        print("No inputs selected. Exiting.")
                        for _, r in self.readers: r.stop()
                        return
                        
                    for rep_id, rep_data in self.profile.get("reports", {}).items():
                        if "inputs" in rep_data:
                            for t in remapping_targets:
                                if t in rep_data["inputs"]:
                                    del rep_data["inputs"][t]
                except Exception as e:
                    print(f"Failed to load existing profile: {e}")
                    print("Proceeding with full recalibration.")
                    remapping_targets = None

        if remapping_targets is None:
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
            print("\nDoes your controller constantly stream Gyroscope/Motion data?")
            print("[1] NO (Standard gamepads, or Gyro is disabled in D-Input mode) - RECOMMENDED")
            print("[2] YES (DualSense, Switch Pro, etc.)")
            report_choice = ""
            while report_choice not in ["1", "2"]:
                report_choice = input("Choice [1-2] (default 1): ").strip()
                if not report_choice:
                    report_choice = "1"
            self.profile["has_report_id"] = (report_choice == "2")
        elif "layout" in self.profile:
            self.layout = self.profile["layout"]

        print("\n--- Calibration Started ---")
        if logger: logger.info(f"Calibration Started for VID:{self.profile['vid']} PID:{self.profile['pid']} Layout:{self.layout}")
        print("Please DO NOT touch the controller for 2 seconds while we establish a baseline...")
        
        # Gather baselines over 2 seconds
        end_time = time.time() + 2.0
        while time.time() < end_time:
            for iface, reps in self.latest_reports.items():
                if iface not in self.baselines:
                    self.baselines[iface] = {}
                for rep_id, rep in reps.items():
                    self.baselines[iface][rep_id] = list(rep.data)
            time.sleep(0.01)

        try:
            self._calibrate_loop(remapping_targets)
        finally:
            for _, r in self.readers: r.stop()

    def _calibrate_loop(self, remapping_targets=None):
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
            ("lx", "axes", "Move the Left Stick RIGHT"),
            ("ly", "axes", "Move the Left Stick UP"),
            ("rx", "axes", "Move the Right Stick RIGHT"),
            ("ry", "axes", "Move the Right Stick UP"),
            ("l3", "stick_clicks", f"Press the Left Stick button ({labels['l3']}) 3 TIMES"),
            ("r3", "stick_clicks", f"Press the Right Stick button ({labels['r3']}) 3 TIMES"),
            ("lt", "triggers", f"Press the Left Trigger ({labels['lt']})"),
            ("rt", "triggers", f"Press the Right Trigger ({labels['rt']})"),
            ("dpad", "hat", "Press the D-Pad UP (Assuming standard Hat switch)")
        ]

        # Extra buttons
        if remapping_targets is None:
            num_extras = -1
            while num_extras < 0:
                user_input = input("\nHow many extra buttons (e.g., L4, R4) does this controller have? (or 'q' to quit): ").strip().lower()
                if user_input == 'q': return
                try: num_extras = int(user_input)
                except ValueError: pass

            for i in range(num_extras):
                name = ""
                while not name:
                    name = input(f"Enter a name for extra button {i + 1} (e.g., l4): ").strip().lower()
                steps.append((name, "buttons", f"Press the '{name}' extra button"))
        else:
            filtered_steps = [s for s in steps if s[0] in remapping_targets]
            standard_names = {s[0] for s in steps}
            for t in remapping_targets:
                if t not in standard_names:
                    filtered_steps.append((t, "buttons", f"Press the '{t}' extra button"))
            steps = filtered_steps

        i = 0
        while i < len(steps):
            name, cat, prompt = steps[i]
            if hasattr(self, "click_counts"): del self.click_counts
            if hasattr(self, "byte_history"): del self.byte_history
            if hasattr(self, "button_byte_history"): del self.button_byte_history

            print(f"\n[{i + 1}/{len(steps)}] {prompt}")
            print("To skip, PRESS 's' on your keyboard. To undo, PRESS 'u'.")

            time.sleep(0.5)
            for iface, reps in self.latest_reports.items():
                if iface not in self.baselines: self.baselines[iface] = {}
                for rep_id, rep in reps.items():
                    self.baselines[iface][rep_id] = list(rep.data)

            done = False
            undo = False

            import msvcrt
            while msvcrt.kbhit(): msvcrt.getwch()
            
            trigger_samples = []
            trigger_start = 0
            analog_fail_count = 0

            click_states = []
            last_click_time = 0

            while not done:
                if msvcrt.kbhit():
                    char = msvcrt.getwch().lower()
                    if char == 's':
                        print("\nSkipped.")
                        done = True
                        break
                    elif char == 'u':
                        undo = True
                        print("\nUndoing previous step.")
                        done = True
                        break

                diffs = []
                for iface, reps in list(self.latest_reports.items()):
                    for curr_report_id, latest_rep in list(reps.items()):
                        current = list(latest_rep.data)
                        if iface not in self.baselines or curr_report_id not in self.baselines[iface]:
                            if iface not in self.baselines: self.baselines[iface] = {}
                            self.baselines[iface][curr_report_id] = current
                            continue

                        base = self.baselines[iface][curr_report_id]
                        if len(current) != len(base): continue

                        for b_idx in range(len(current)):
                            if current[b_idx] != base[b_idx]:
                                diffs.append((iface, curr_report_id, b_idx, current[b_idx], base[b_idx]))

                if diffs:
                    if cat == "stick_clicks":
                        if not hasattr(self, "click_counts"):
                            self.click_counts = {}
                            self.byte_history = {}
                            self.last_click_time = 0

                        for iface, r_id, b_idx, curr_val, base_val in diffs:
                            full_id = f"{iface}_{r_id}"
                            byte_key = (full_id, b_idx)
                            if byte_key not in self.byte_history:
                                self.byte_history[byte_key] = {base_val}
                            self.byte_history[byte_key].add(curr_val)

                        # Exclude any byte already mapped to an axis, trigger, hat, or button
                        known_mapped_bytes = set()
                        for rep_id, rep_data in self.profile.get("reports", {}).items():
                            for in_name, in_cfg in rep_data.get("inputs", {}).items():
                                t = in_cfg.get("type")
                                if t in ("axis", "trigger", "hat"):
                                    known_mapped_bytes.add((rep_id, in_cfg.get("byte")))
                                    if in_cfg.get("length", 1) == 2:
                                        known_mapped_bytes.add((rep_id, in_cfg.get("byte")+1))

                        for iface, r_id, b_idx, curr_val, base_val in diffs:
                            full_id = f"{iface}_{r_id}"
                            byte_key = (full_id, b_idx)
                            if byte_key in known_mapped_bytes:
                                continue
                                
                            # Filter out analog noise (unmapped axes)
                            if len(self.byte_history[byte_key]) > 3:
                                continue
                            
                            changed_bits = curr_val ^ base_val
                            for bit in range(8):
                                bitmask = 1 << bit
                                if changed_bits & bitmask:
                                    # Prevent re-mapping already known buttons
                                    is_known = False
                                    for rep_data in self.profile.get("reports", {}).values():
                                        for in_cfg in rep_data.get("inputs", {}).values():
                                            if in_cfg.get("type") == "button" and in_cfg.get("byte") == b_idx and in_cfg.get("bitmask") == bitmask:
                                                is_known = True
                                    if is_known: continue
                                
                                    click_key = (full_id, b_idx, bitmask)
                                    if time.time() - self.last_click_time > 0.4:
                                        if click_key not in self.click_counts:
                                            self.click_counts[click_key] = 0
                                        self.click_counts[click_key] += 1
                                        self.last_click_time = time.time()
                                        print(f"  Click {self.click_counts[click_key]}/3 detected!")
                                        
                                        if self.click_counts[click_key] >= 3:
                                            if full_id not in self.profile["reports"]: self.profile["reports"][full_id] = {"inputs": {}}
                                            self.profile["reports"][full_id]["inputs"][name] = {"type": "button", "byte": b_idx, "bitmask": bitmask}
                                            print(f"Confirmed {name} at {full_id}, byte {b_idx}, mask {bitmask}")
                                            if logger: logger.info(f"Confirmed {name} at {full_id}, byte {b_idx}, mask {bitmask}")
                                            done = True
                                            break

                    elif cat == "buttons":
                        if not hasattr(self, "button_byte_history"):
                            self.button_byte_history = {}
                            
                        changed_bytes = []
                        for iface, r_id, b_idx, curr_val, base_val in diffs:
                            full_id = f"{iface}_{r_id}"
                            byte_key = (full_id, b_idx)
                            if byte_key not in self.button_byte_history:
                                self.button_byte_history[byte_key] = {base_val}
                            self.button_byte_history[byte_key].add(curr_val)
                            
                            changed_bits = curr_val ^ base_val
                            if changed_bits != 0:
                                changed_bytes.append((iface, r_id, b_idx, changed_bits))

                        # Exclude any byte already mapped to an axis, trigger, or hat
                        known_axis_bytes = set()
                        for rep_id, rep_data in self.profile.get("reports", {}).items():
                            for in_name, in_cfg in rep_data.get("inputs", {}).items():
                                if in_cfg.get("type") in ("axis", "trigger", "hat"):
                                    known_axis_bytes.add((rep_id, in_cfg.get("byte")))
                                    if in_cfg.get("length", 1) == 2:
                                        known_axis_bytes.add((rep_id, in_cfg.get("byte")+1))

                        known_bits = set()
                        for rep_id, rep_data in self.profile.get("reports", {}).items():
                            for in_name, in_cfg in rep_data.get("inputs", {}).items():
                                if in_cfg.get("type") == "button":
                                    known_bits.add((rep_id, in_cfg.get("byte"), in_cfg.get("bitmask")))

                        clean_changed = []
                        for iface, r_id, b_idx, changed_bits in changed_bytes:
                            full_id = f"{iface}_{r_id}"
                            byte_key = (full_id, b_idx)
                            if byte_key in known_axis_bytes:
                                continue
                                
                            # Filter out unmapped axes (analog noise)
                            if len(self.button_byte_history.get(byte_key, [])) > 3:
                                continue
                                
                            for bit in range(8):
                                bitmask = 1 << bit
                                if changed_bits & bitmask:
                                    if (full_id, b_idx, bitmask) not in known_bits:
                                        clean_changed.append((full_id, b_idx, bitmask))

                        if clean_changed:
                            full_id, b_idx, bit_mask = clean_changed[0]
                            if full_id not in self.profile["reports"]: self.profile["reports"][full_id] = {"inputs": {}}
                            self.profile["reports"][full_id]["inputs"][name] = {"type": "button", "byte": b_idx, "bitmask": bit_mask}
                            print(f"Detected {name} at {full_id}, byte {b_idx}, mask {bit_mask}")
                            if logger: logger.info(f"Detected {name} at {full_id}, byte {b_idx}, mask {bit_mask}")
                            done = True
                            
                    elif cat == "triggers":
                        if trigger_start == 0:
                            trigger_start = time.time()
                            print("Collecting analog data...")
                            
                        # Sample data
                        for iface, reps in self.latest_reports.items():
                            for curr_report_id, latest_rep in reps.items():
                                full_id = f"{iface}_{curr_report_id}"
                                trigger_samples.append((full_id, list(latest_rep.data)))
                                
                        if time.time() - trigger_start > 2.0:
                            # Analyze samples
                            unique_counts = {}
                            base_state = {}
                            for b_iface, b_reps in self.baselines.items():
                                for b_rid, b_data in b_reps.items():
                                    base_state[f"{b_iface}_{b_rid}"] = b_data
                            
                            for full_id, data in trigger_samples:
                                if full_id not in unique_counts:
                                    unique_counts[full_id] = [set() for _ in range(len(data))]
                                    if full_id in base_state:
                                        for byte_idx, b_val in enumerate(base_state[full_id]):
                                            if byte_idx < len(unique_counts[full_id]):
                                                unique_counts[full_id][byte_idx].add(b_val)
                                                
                                for byte_idx, val in enumerate(data):
                                    unique_counts[full_id][byte_idx].add(val)
                                    
                            best_full_id = None
                            best_byte = -1
                            max_uniques = 0
                            
                            for full_id, counts in unique_counts.items():
                                for byte_idx, u_set in enumerate(counts):
                                    # Exclude bytes already mapped as standard buttons
                                    is_button = False
                                    if full_id in self.profile.get("reports", {}):
                                        for in_name, in_cfg in self.profile["reports"][full_id].get("inputs", {}).items():
                                            if in_cfg.get("type") == "button" and in_cfg.get("byte") == byte_idx:
                                                is_button = True
                                                break
                                    if is_button: continue
                                    
                                    if len(u_set) > max_uniques:
                                        max_uniques = len(u_set)
                                        best_full_id = full_id
                                        best_byte = byte_idx
                                        
                            if max_uniques > 2:
                                if best_full_id not in self.profile["reports"]: self.profile["reports"][best_full_id] = {"inputs": {}}
                                self.profile["reports"][best_full_id]["inputs"][name] = {
                                    "type": "trigger", "byte": best_byte, "length": 1, "center": False, "is_analog": True,
                                    "range_confidence": round(min(1.0, max_uniques / 40.0), 3)
                                }
                                print(f"Detected Analog {name} at {best_full_id}, byte {best_byte} ({max_uniques} unique states)")
                                if logger: logger.info(f"Detected Analog {name} at {best_full_id}, byte {best_byte} ({max_uniques} unique states)")
                                done = True
                            else:
                                known_bits = set()
                                known_axis_bytes = set()
                                for rep_id, rep_data in self.profile.get("reports", {}).items():
                                    for in_name, in_cfg in rep_data.get("inputs", {}).items():
                                        if in_cfg.get("type") == "button":
                                            known_bits.add((rep_id, in_cfg.get("byte"), in_cfg.get("bitmask")))
                                        elif in_cfg.get("type") in ("axis", "trigger", "hat"):
                                            known_axis_bytes.add((rep_id, in_cfg.get("byte")))
                                            if in_cfg.get("length", 1) == 2:
                                                known_axis_bytes.add((rep_id, in_cfg.get("byte")+1))
                                                
                                found = False
                                best_full_id = None
                                best_byte = -1
                                best_mask = 0
                                
                                for full_id, counts in unique_counts.items():
                                    if found: break
                                    for byte_idx, u_set in enumerate(counts):
                                        if found: break
                                        if (full_id, byte_idx) in known_axis_bytes: continue
                                        if len(u_set) > 3: continue # noisy analog axis, skip
                                        
                                        for val in u_set:
                                            base_val = base_state[full_id][byte_idx]
                                            changed_bits = val ^ base_val
                                            if changed_bits == 0: continue
                                            
                                            for bit in range(8):
                                                bitmask = 1 << bit
                                                if (changed_bits & bitmask):
                                                    if (full_id, byte_idx, bitmask) not in known_bits:
                                                        best_full_id = full_id
                                                        best_byte = byte_idx
                                                        best_mask = bitmask
                                                        found = True
                                                        break
                                            if found: break
                                            
                                if found:
                                    print(f"\nFalling back to digital trigger detection for {name}.")
                                    if logger: logger.warning(f"Falling back to digital trigger detection for {name}.")
                                    if best_full_id not in self.profile["reports"]: self.profile["reports"][best_full_id] = {"inputs": {}}
                                    self.profile["reports"][best_full_id]["inputs"][name] = {"type": "button", "byte": best_byte, "bitmask": best_mask, "is_analog": False}
                                    print(f"Detected Digital {name} at {best_full_id}, byte {best_byte}, mask {best_mask}")
                                    if logger: logger.info(f"Detected Digital {name} at {best_full_id}, byte {best_byte}, mask {best_mask}")
                                    done = True
                                else:
                                    print("\nWARNING: No trigger signal detected!")
                                    print("Ensure your controller is in DInput mode, the correct interface was selected,")
                                    print("or press the trigger more firmly.")
                                    print("Press 's' to skip or 'u' to undo.")
                                    
                                    # DEBUG BLOCK
                                    if "--log" in sys.argv:
                                        debug_lines = []
                                        for dfull_id, dcounts in unique_counts.items():
                                            for dbyte_idx, d_u_set in enumerate(dcounts):
                                                if len(d_u_set) > 1:
                                                    dbase = base_state.get(dfull_id, [])
                                                    b_val = dbase[dbyte_idx] if dbyte_idx < len(dbase) else -1
                                                    is_axis = (dfull_id, dbyte_idx) in known_axis_bytes
                                                    debug_lines.append(f"Byte {dbyte_idx} (axis={is_axis}, base={b_val}): uniques={d_u_set}")
                                        if debug_lines:
                                            print("DEBUG INFO (Changes detected but rejected):")
                                            for line in debug_lines:
                                                print(f"  {line}")
                                        else:
                                            print("DEBUG INFO: No byte had more than 1 unique value during the 2-second window.")
                                        
                                    trigger_start = 0
                                    trigger_samples = []

                    elif cat == "axes":
                        button_bytes = set()
                        for rep_id, rep_data in self.profile.get("reports", {}).items():
                            for in_name, in_cfg in rep_data.get("inputs", {}).items():
                                if in_cfg.get("type") == "button":
                                    button_bytes.add((rep_id, in_cfg.get("byte")))

                        candidates = []
                        for iface, r_id, b_idx, curr_val, base_val in diffs:
                            full_id = f"{iface}_{r_id}"
                            if (full_id, b_idx) in button_bytes: continue
                            
                            amp8 = abs(curr_val - base_val)
                            if amp8 > 10:
                                candidates.append({'full_id': full_id, 'byte': b_idx, 'norm_amp': amp8 / 255.0, 'amp': amp8, 'curr': curr_val, 'base': base_val, 'type': '8bit'})
                                
                        if candidates:
                            candidates.sort(reverse=True, key=lambda x: x['norm_amp'])
                            top = candidates[0]
                            full_id = top['full_id']
                            best_idx = top['byte']
                            
                            cfg = {"type": "axis", "byte": best_idx, "length": 1, "center": True}
                            
                            # Signed Axis Detection
                            base_val = top['base']
                            if base_val < 15 or base_val > 240: cfg["signed"] = True
                            
                            # Inverted Axis Detection
                            curr_val = top['curr']
                            def get_signed_val(val):
                                if not cfg.get("signed", False): return val
                                return val - 256 if val >= 128 else val
                                
                            delta = get_signed_val(curr_val) - get_signed_val(base_val)
                            if name in ("lx", "rx") and delta < 0: cfg["invert"] = True
                            elif name in ("ly", "ry") and delta > 0: cfg["invert"] = True
                            
                            # Calibration Confidence Metrics
                            if not cfg.get("signed", False):
                                centeredness = 1.0 - (abs(base_val - 127.5) / 127.5)
                            else:
                                centeredness = 1.0 - (abs(get_signed_val(base_val)) / 128.0)
                            cfg["centeredness"] = round(max(0.0, min(1.0, centeredness)), 3)
                            cfg["range_confidence"] = round(min(1.0, top['amp'] / 127.0), 3)
                                    
                            if full_id not in self.profile["reports"]: self.profile["reports"][full_id] = {"inputs": {}}
                            self.profile["reports"][full_id]["inputs"][name] = cfg
                            print(f"Detected {name} at {full_id}, byte {best_idx}")
                            if logger: logger.info(f"Detected {name} at {full_id}, byte {best_idx}")
                            done = True

                    elif cat == "hat":
                        clean_hat_bytes = [d for d in diffs if ((d[4] & 0x0F) > 7) and ((d[3] & 0x0F) <= 7)]
                        if len(clean_hat_bytes) == 1:
                            iface, curr_report_id, b_idx, _, _ = clean_hat_bytes[0]
                            full_id = f"{iface}_{curr_report_id}"
                            if full_id not in self.profile["reports"]: self.profile["reports"][full_id] = {"inputs": {}}
                            self.profile["reports"][full_id]["inputs"]["dpad"] = {"type": "hat", "byte": b_idx}
                            print(f"Detected D-Pad hat at {full_id}, byte {b_idx}")
                            if logger: logger.info(f"Detected D-Pad hat at {full_id}, byte {b_idx}")
                            done = True
                            
                time.sleep(0.01)

            if undo:
                if i > 0:
                    i -= 1
                    prev_name, prev_cat, _ = steps[i]
                    for rep_id, rep_data in self.profile["reports"].items():
                        if "inputs" in rep_data and prev_name in rep_data["inputs"]:
                            del rep_data["inputs"][prev_name]
                continue

            print("Release the button/stick...")
            time.sleep(0.5)
            for iface, reps in self.latest_reports.items():
                if iface not in self.baselines: self.baselines[iface] = {}
                for rep_id, rep in reps.items():
                    self.baselines[iface][rep_id] = list(rep.data)
            i += 1

        self.save_profile()

    def save_profile(self):
        try:
            os.makedirs("profiles", exist_ok=True)
            filename = f"profiles/{
                self.profile['vid']}_{
                self.profile['pid']}.json".lower()
            with open(filename, 'w') as f:
                json.dump(self.profile, f, indent=4)
            print(f"\nProfile saved to {filename}")
            if logger: logger.info(f"Profile saved to {filename}")
        except Exception as e:
            print(f"\nFailed to save profile: {e}")
            if logger: logger.error(f"Failed to save profile: {e}")

    def _calibrate_rumble(self):
        print("\n--- Force Feedback / Vibration Setup ---")
        print("Do you want to configure rumble for this controller?")
        print("[1] Yes")
        print("[2] No (Skip)")
        
        choice = ""
        while choice not in ["1", "2"]:
            choice = input("Choice (default 2): ").strip()
            if not choice:
                choice = "2"
                
        if choice == "2":
            return
            
        print("\nTo configure rumble, you need the base hex payload that makes your controller vibrate.")
        print("Enter the hex payload (e.g., 00 01 08 00 00):")
        payload_str = input("Payload: ").strip()
        
        try:
            template = [int(x, 16) for x in payload_str.replace(",", " ").split()]
        except ValueError:
            print("Invalid hex format. Skipping rumble setup.")
            return
            
        if not template:
            print("Empty payload. Skipping rumble setup.")
            return

        print("\nNow we will figure out which bytes control the Left (Heavy) and Right (Light) motors.")
        print("I will send the payload repeatedly, changing one byte at a time.")
        
        import copy
        left_byte = -1
        right_byte = -1
        
        for i in range(len(template)):
            if template[i] == 0:
                print(f"\nTesting byte index {i}...")
                test_payload = copy.deepcopy(template)
                test_payload[i] = 255
                
                # Send it 3 times to make sure they feel it
                for _ in range(3):
                    for _, r in self.readers:
                        try:
                            r.device.write(test_payload)
                        except Exception:
                            pass
                    time.sleep(0.3)
                    
                print("Did the controller vibrate?")
                print("[1] Yes, Heavy Motor (Left)")
                print("[2] Yes, Light Motor (Right)")
                print("[3] Yes, Both / Unknown")
                print("[4] No")
                
                res = input("Choice [1-4]: ").strip()
                if res == "1":
                    left_byte = i
                elif res == "2":
                    right_byte = i
                elif res == "3":
                    if left_byte == -1:
                        left_byte = i
                    else:
                        right_byte = i
                
                # Turn it off
                for _, r in self.readers:
                    try:
                        r.device.write(template)
                    except Exception:
                        pass
                time.sleep(0.5)
                
        if left_byte != -1 or right_byte != -1:
            self.profile["rumble"] = {
                "template": template,
                "left_motor_byte": left_byte,
                "right_motor_byte": right_byte,
                "motor_scale": 255
            }
            print(f"\nRumble setup complete! Left motor byte: {left_byte}, Right motor byte: {right_byte}")
            if logger: logger.info(f"Rumble setup complete! Left: {left_byte}, Right: {right_byte}")
        else:
            print("\nRumble setup failed: No motor bytes identified.")

    def test_mode(self, is_temp=False, profile_path=None):
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
                for iface, reps in list(self.latest_reports.items()):
                    for rep in list(reps.values()):
                        state = decoder.decode(rep)
                for iface in self.latest_reports:
                    self.latest_reports[iface].clear()
                
                if not hasattr(decoder, 'state'):
                    # safeguard
                    state = decoder.state if hasattr(decoder, 'state') else decoder.decode(None)
                else:
                    state = decoder.state

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

                def get_grid(x_float, y_float):
                    # x, y are -1.0 to 1.0
                    x_float = max(-1.0, min(1.0, x_float))
                    y_float = max(-1.0, min(1.0, y_float))
                    cx = int(round(((x_float + 1.0) / 2.0) * (grid_size - 1)))
                    # y is inverted on screen vs joystick usually, but let's just display it
                    cy = int(round(((y_float + 1.0) / 2.0) * (grid_size - 1)))

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

                def get_trigger(val_float):
                    # val is 0.0 to 1.0
                    val_float = max(0.0, min(1.0, val_float))
                    h = int(round(val_float * grid_size))
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
                        state.lx:5.2f}, LY:{
                        state.ly:5.2f})   Right Stick (RX:{
                        state.rx:5.2f}, RY:{
                        state.ry:5.2f})   {lt_name}:{
                        state.lt:4.2f}   {rt_name}:{
                            state.rt:4.2f}")
                for i in range(grid_size):
                    print(
                        f"  {
                            l_grid[i]:<10}                    {
                            r_grid[i]:<10}                 {
                            lt_bar[i]}        {
                            rt_bar[i]}")

                if state.extra_inputs:
                    print("\nExtra Inputs:")
                    for name, val in state.extra_inputs.items():
                        if isinstance(val, bool):
                            print(f"{name.upper()}: {'[X]' if val else '[ ]'}", end="  ")
                        else:
                            print(f"{name.upper()}: {val}", end="  ")
                print("\n\033[J", end="")  # Clear remainder of screen below
                sys.stdout.flush()
                time.sleep(0.05)
        except KeyboardInterrupt:
            pass
        finally:
            if is_temp and os.path.exists(profile_path):
                os.remove(profile_path)
            print("\nExiting Test Mode.")


    def dump_raw_mode(self):
        print("\n--- Raw Delta Dump Mode ---")
        if not self.scan_devices():
            return

        # scan_devices already started self.readers and is populating self.latest_reports

        print("\nWaiting for initial baseline...")
        time.sleep(2)
        
        for iface, reps in self.latest_reports.items():
            self.baselines[iface] = {}
            for rep_id, rep in reps.items():
                self.baselines[iface][rep_id] = list(rep.data)
            
        print("Baseline established. Press buttons to see delta (Ctrl+C to quit)...")
        
        try:
            while True:
                diffs = []
                for iface, reps in list(self.latest_reports.items()):
                    for curr_report_id, latest_rep in list(reps.items()):
                        current = list(latest_rep.data)
                        if iface not in self.baselines:
                            self.baselines[iface] = {}
                        if curr_report_id not in self.baselines[iface]:
                            self.baselines[iface][curr_report_id] = current
                            continue
                        
                        base = self.baselines[iface][curr_report_id]
                        if len(current) != len(base):
                            continue
                            
                        for b_idx in range(len(current)):
                            if current[b_idx] != base[b_idx]:
                                changed_bits = current[b_idx] ^ base[b_idx]
                                diffs.append((iface, curr_report_id, b_idx, current[b_idx], base[b_idx], changed_bits))
                            
                if diffs:
                    print("\n--- Input Detected ---")
                    for iface, rep_id, b_idx, curr_val, base_val, changed_bits in diffs:
                        print(f"IFace: {iface} | Report: {rep_id} | Byte: {b_idx:02} | Base: {base_val:02X} -> Curr: {curr_val:02X} | Mask: {changed_bits:02X} ({bin(changed_bits)})")
                    time.sleep(0.2) # Debounce print
                    
                    for iface, reps in self.latest_reports.items():
                        for rep_id, rep in reps.items():
                            self.baselines[iface][rep_id] = list(rep.data)
                        
                time.sleep(0.01)
        except KeyboardInterrupt:
            print("\nExiting raw dump mode.")
        finally:
            for _, r in self.readers: r.stop()


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
    parser.add_argument(
        '--dump-raw',
        action='store_true',
        help='Bypass calibration and dump raw byte deltas on input')
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
    if args.dump_raw:
        calibrator.dump_raw_mode()
    else:
        calibrator.run(test_only=args.test_only)
