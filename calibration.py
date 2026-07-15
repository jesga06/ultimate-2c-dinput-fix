import os
import json
import time
import sys
from hid_reader import HIDReader
from decoder import Decoder

def cls():
    os.system('cls' if os.name == 'nt' else 'clear')

class Calibrator:
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
        candidates = []
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
                    if diff > 15: # threshold for button press or joystick movement
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
                # System devices (keyboard/mouse) usually fail to open (Access Denied), which is good
                pass

        print("\nSelect a device to calibrate:")
        for i, d in enumerate(unique_devices):
            status = " (Listening for input...)" if d in opened_devices else " (Manual selection only)"
            print(f"[{i}] VID:{d.vendor_id:04X} PID:{d.product_id:04X} - {d.product_name}{status}")
            
        print("\n--> PRESS ANY BUTTON OR MOVE A STICK on your controller to auto-detect it.")
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
                print(f"\nAuto-detected: VID:{self.device.vendor_id:04X} PID:{self.device.product_id:04X} - {self.device.product_name}")
                break
                
            if msvcrt.kbhit():
                char = msvcrt.getwch()
                if char == '\r': # ENTER
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
                            print(f"Invalid choice. Please enter a number between 0 and {len(unique_devices)-1}.")
                            print("Choice: ", end="")
                            sys.stdout.flush()
                    except ValueError:
                        print("Invalid input. Please enter a valid number or 'q'.")
                        print("Choice: ", end="")
                        sys.stdout.flush()
                elif char in ('\b', '\x08'): # Backspace
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
        # Wait for the user to press a button and release it, detecting the exact byte/bit changed
        print(f"\n{prompt}")
        print("Waiting for input... (Press 's' to Skip, 'u' to Undo previous)")
        
        while sys.stdin in select_stdin(): pass # clear stdin buffer (rough)
        
        # We need a non-blocking input check for s/u, but standard python input() blocks.
        # For simplicity in this script, we'll prompt for 's' or 'u' before waiting for the controller, 
        # or we just assume they press the controller.
        # Actually, let's just wait for controller input. If they want to skip/undo, 
        # they can press a key on the keyboard.
        pass

    def run(self):
        if not self.scan_devices():
            return
            
        self.reader = HIDReader(device=self.device)
        if not self.reader.connect():
            return
            
        self.reader.set_callback(self._data_handler)
        
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
                print("\nError: No data received within 10 seconds. Make sure the controller is turned on and connected.")
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
        
        steps = [
            ("a", "buttons", "Press the 'A' button"),
            ("b", "buttons", "Press the 'B' button"),
            ("x", "buttons", "Press the 'X' button"),
            ("y", "buttons", "Press the 'Y' button"),
            ("lb", "buttons", "Press the Left Bumper (LB)"),
            ("rb", "buttons", "Press the Right Bumper (RB)"),
            ("select", "buttons", "Press the Select/Back button"),
            ("start", "buttons", "Press the Start button"),
            ("home", "buttons", "Press the Home/Guide button"),
            ("l3", "buttons", "Press the Left Stick button (L3)"),
            ("r3", "buttons", "Press the Right Stick button (R3)"),
            ("lx", "axes", "Move the Left Stick RIGHT"),
            ("ly", "axes", "Move the Left Stick UP"),
            ("rx", "axes", "Move the Right Stick RIGHT"),
            ("ry", "axes", "Move the Right Stick UP"),
            ("lt", "axes", "Press the Left Trigger (LT)"),
            ("rt", "axes", "Press the Right Trigger (RT)"),
            ("dpad", "hat", "Press the D-Pad UP (Assuming standard Hat switch)")
        ]
        
        # Extra buttons
        num_extras = -1
        while num_extras < 0:
            user_input = input("\nHow many extra buttons (Not counting Home/Guide. e.g., L4, R4) does this controller have? (or 'q' to quit): ").strip().lower()
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
                name = input(f"Enter a name for extra button {i+1} (e.g., l4, m1): ").strip().lower()
                if not name:
                    print("Name cannot be empty.")
            steps.append((name, "extra_buttons", f"Press the '{name}' extra button"))

        history = []
        i = 0
        while i < len(steps):
            name, cat, prompt = steps[i]
            
            print(f"\n[{i+1}/{len(steps)}] {prompt}")
            print("To skip, press ENTER on your keyboard. To undo, type 'u' and press ENTER.")
            
            # Update base data
            time.sleep(0.5)
            self.base_data = list(self.raw_data)
            
            if not self.base_data:
                print("No data received from controller. Make sure it's awake.")
                time.sleep(1)
                continue
                
            done = False
            skip = False
            undo = False
            
            import msvcrt
            
            while not done:
                # Check for keyboard input
                if msvcrt.kbhit():
                    char = msvcrt.getwche()
                    if char == '\r':
                        skip = True
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
                        diffs.append((b_idx, current[b_idx], self.base_data[b_idx]))
                        
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
                            # Often multiple bits might toggle if it's noisy. Let's just take the first changed bit.
                            bit_mask = mask & -mask # get lowest set bit
                            self.profile[cat][name] = {"byte": b_idx, "mask": bit_mask}
                            print(f"Detected {name} at byte {b_idx}, mask {bit_mask}")
                            done = True
                        elif len(changed_bytes) > 1:
                            print("\nMultiple buttons pressed simultaneously. Please press only one cleanly.")
                            time.sleep(1)
                            self.base_data = list(self.raw_data)
                            
                    elif cat == "axes":
                        # Look for amplitude change
                        amplitudes = []
                        for b_idx, curr_val, base_val in diffs:
                            amp = abs(curr_val - base_val)
                            if amp > 10: # threshold for noise
                                amplitudes.append((amp, b_idx))
                                
                        if amplitudes:
                            amplitudes.sort(reverse=True)
                            best_amp, best_idx = amplitudes[0]
                            
                            # Robustness: Check if there's cross-axis contamination
                            if len(amplitudes) > 1:
                                second_amp = amplitudes[1][0]
                                if second_amp > best_amp * 0.5: # If the second biggest change is > 50% of the biggest
                                    print(f"\nDetected movement on multiple axes. Please move ONLY the requested axis carefully.")
                                    time.sleep(1.5)
                                    self.base_data = list(self.raw_data)
                                    continue
                            
                            self.profile[cat][name] = {"byte": best_idx}
                            print(f"Detected {name} at byte {best_idx} (Amplitude: {best_amp})")
                            done = True
                            
                    elif cat == "hat":
                        # Assuming D-Pad changes a single byte
                        changed_bytes = [d for d in diffs if abs(d[1]-d[2]) > 0]
                        if len(changed_bytes) == 1:
                            b_idx = changed_bytes[0][0]
                            self.profile["buttons"]["dpad"] = {"byte": b_idx, "type": "hat"}
                            print(f"Detected D-Pad hat at byte {b_idx}")
                            done = True
                        elif len(changed_bytes) > 1:
                            print("\nMultiple bytes changed. Press only the D-Pad cleanly.")
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
            filename = f"profiles/{self.profile['vid']}_{self.profile['pid']}.json".lower()
            with open(filename, 'w') as f:
                json.dump(self.profile, f, indent=4)
            print(f"\nProfile saved to {filename}")
        except Exception as e:
            print(f"\nFailed to save profile: {e}")

    def test_mode(self):
        print("\n--- Test Mode ---")
        print("Press Ctrl+C to exit test mode.")
        
        # Save temp file for Decoder to load
        temp_path = "profiles/temp_test.json"
        try:
            os.makedirs("profiles", exist_ok=True)
            with open(temp_path, 'w') as f:
                json.dump(self.profile, f)
        except Exception as e:
            print(f"Error creating temp profile for test mode: {e}")
            return
            
        try:
            decoder = Decoder(temp_path)
        except Exception as e:
            print(f"Error initializing decoder for test mode: {e}")
            return
        
        try:
            while True:
                state = decoder.decode(self.raw_data)
                cls()
                print("--- LIVE TEST MODE (Ctrl+C to exit) ---")
                print(f"Profile: {self.profile['name']}")
                print("\nStandard Buttons:")
                for b in ['a', 'b', 'x', 'y', 'lb', 'rb', 'select', 'start', 'home', 'l3', 'r3']:
                    val = getattr(state, b)
                    print(f"{b.upper()}: {'[X]' if val else '[ ]'}", end="  ")
                print("\n\nD-Pad:")
                print(f"UP: {'[X]' if state.dpad_up else '[ ]'}  DOWN: {'[X]' if state.dpad_down else '[ ]'}  LEFT: {'[X]' if state.dpad_left else '[ ]'}  RIGHT: {'[X]' if state.dpad_right else '[ ]'}")
                print("\nAxes:")
                print(f"LX: {state.lx:3d}  LY: {state.ly:3d}   LT: {state.lt:3d}")
                print(f"RX: {state.rx:3d}  RY: {state.ry:3d}   RT: {state.rt:3d}")
                print("\nExtra Buttons:")
                for name, val in state.extra_buttons.items():
                    print(f"{name.upper()}: {'[X]' if val else '[ ]'}", end="  ")
                print("")
                time.sleep(0.05)
        except KeyboardInterrupt:
            pass
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            print("\nExiting Test Mode.")

def select_stdin():
    # Helper to flush stdin on windows, but it's not foolproof.
    pass

if __name__ == "__main__":
    calibrator = Calibrator()
    calibrator.run()
