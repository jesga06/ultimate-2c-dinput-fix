"""
UR-XD Wrapper Daemon (main.py)
This is the background daemon that connects to the physical HID controller,
decodes its reports, maps extra buttons to keyboard/mouse actions, and forwards
gamepad controls to the ViGEmBus virtual XInput controller.
It runs as a system tray icon using pystray.
"""
import time
import configparser
import sys
if sys.version_info[:2] not in ((3, 13), (3, 14)):
    print("WARNING: This script requires Python 3.13.x or 3.14.x. Other versions may fail to compile/load hidapi.")
    # We do not exit immediately in case they somehow made it work, but we warn them.
import os
import threading
import json
from hid_reader import HIDReader, RawHIDReport
from decoder import Decoder
from mapper import Mapper
from virtual_pad import VirtualPad
from config_manager import ControllerConfig, get_sanitized_filename

import pystray
from PIL import Image, ImageDraw
import ctypes
import argparse
import subprocess
from logger_setup import setup_logger

is_debug_mode = False
logger = None


def hide_console():
    # Hide the console window
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass


def show_console():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


gui_processes = []


def open_config(icon, item):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        gui_path = os.path.join(script_dir, 'gui.py')
        cmd = [sys.executable, gui_path]
        if is_debug_mode:
            cmd.extend(['--log', '--append-log'])
        p = subprocess.Popen(cmd)
        gui_processes.append(p)
    except Exception as e:
        if logger:
            logger.error(f"Failed to open GUI: {e}")
        else:
            print(f"Failed to open GUI: {e}")


def show_console_action(icon, item):
    show_console()


def write_status(state, device_name="None"):
    try:
        with open('status.json', 'w') as f:
            json.dump({"status": state, "device": device_name}, f)
    except Exception as e:
        if logger:
            logger.error(f"Error writing status.json: {e}")
        else:
            print(f"Error writing status.json: {e}")


def quit_app(icon, item):
    icon.stop()
    write_status("Disconnected")
    os._exit(0)


def create_image():
    # Generate a simple icon
    width = 64
    height = 64
    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.ellipse((8, 8, width - 8, height - 8), fill=(175, 0, 250))
    dc.rectangle((24, 24, width - 24, height - 24), fill=(255, 255, 255))
    return image


def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if os.path.exists(filename):
        config.read(filename)
    return config


def main():
    """
    Main entry point for the wrapper daemon.
    Initializes virtual controllers, starts the HID reader thread,
    launches the configuration file poller, and runs the system tray icon loop.
    """
    global is_debug_mode, logger

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--log',
        action='store_true',
        help='Enable verbose debugging logs')
    parser.add_argument(
        '--boot',
        action='store_true',
        help='Indicate wrapper was called by system initialization (prevents GUI auto-open)')
    args = parser.parse_args()

    is_debug_mode = args.log
    logger = setup_logger('main', 'wrapper.log', is_debug_mode)

    hide_console()
    write_status("Starting...")
    logger.info("UR-XD Wrapper Starting...")

    config_file = 'config.ini'
    config = load_config(config_file)
    # debug_mode from config.ini is overridden by --log if desired, or we just
    # use is_debug_mode
    if not is_debug_mode:
        is_debug_mode = config.getboolean(
            'debug', 'print_reports', fallback=False)
        if is_debug_mode:
            logger = setup_logger('main', 'wrapper.log', is_debug_mode)

    logger.info("Scanning for connected devices with profiles...")
    devices = HIDReader.get_all_devices()
    selected_vid = None
    selected_pid = None
    profile_path = None
    profile_name = "Unknown Device"

    for d in devices:
        vid = d.get('vendor_id', 0)
        pid = d.get('product_id', 0)
        potential_profile = f"profiles/{vid:04X}_{pid:04X}.json".lower()
        if os.path.exists(potential_profile):
            selected_vid = vid
            selected_pid = pid
            profile_path = potential_profile
            try:
                with open(profile_path, 'r') as f:
                    prof_data = json.load(f)
                    profile_name = prof_data.get('name', "Unknown Device")
            except:
                pass
            break

    if not profile_path:
        logger.warning("No connected devices with a saved profile found.")
        logger.info(
            "Please run calibration.py to generate a profile for your controller.")
        show_console()
        time.sleep(5)
        sys.exit(1)

    logger.info(f"Found matching profile: {profile_path} ({profile_name})")

    # Initialize controller config
    sanitized_name = get_sanitized_filename(profile_name)
    controller_config_file = os.path.join("profiles", sanitized_name)
    controller_config = ControllerConfig(controller_config_file)
    
    # Save last_device to global config
    if not config.has_section('controller'):
        config.add_section('controller')
    config.set('controller', 'last_device', profile_name)
    config.set('controller', 'last_profile', profile_path)
    with open(config_file, 'w') as f:
        config.write(f)

    try:
        mapper = Mapper(controller_config)
        virtual_pad = VirtualPad(controller_config)
        
        # Initialize Macro Executor and inject it into mapper
        from macro_executor import MacroExecutor
        macro_executor = MacroExecutor(mapper)
        mapper.macro_executor = macro_executor
        
    except Exception as e:
        logger.error(f"Failed to initialize mapper or virtual pad: {e}")
        logger.info("Please ensure ViGEmBus is installed.")
        show_console()
        time.sleep(5)
        sys.exit(1)
    
    # Load profile to check for interface restriction
    req_ifaces = []
    try:
        with open(profile_path, 'r') as f:
            profile_data = json.load(f)
            if "interfaces" in profile_data:
                req_ifaces = profile_data["interfaces"]
            else:
                req_iface = profile_data.get('interface_number', -1)
                if req_iface != -1:
                    req_ifaces.append(req_iface)
    except Exception as e:
        logger.error(f"Failed to parse profile to check interface: {e}")

    readers = []
    connected_names = []
    
    for d in devices:
        if d.get('vendor_id', 0) == selected_vid and d.get('product_id', 0) == selected_pid:
            iface_num = d.get('interface_number', -1)
            if req_ifaces and iface_num not in req_ifaces:
                continue
            reader = HIDReader(device_path=d['path'], interface_number=iface_num)
            if reader.connect():
                readers.append(reader)
                connected_names.append(d.get('product_string', 'Unknown'))
                
    if not readers:
        write_status("Disconnected")
        show_console()
        time.sleep(5)
        sys.exit(1)

    write_status("Connected", connected_names[0] if connected_names else "Unknown")

    decoder = Decoder(profile_path)

    def rumble_callback(left_motor, right_motor):
        if not hasattr(decoder, "profile") or "rumble" not in decoder.profile:
            return
            
        rumble_cfg = decoder.profile["rumble"]
        template = list(rumble_cfg.get("template", []))
        if not template:
            return
            
        lm_byte = rumble_cfg.get("left_motor_byte", -1)
        rm_byte = rumble_cfg.get("right_motor_byte", -1)
        
        # Scale 0.0-1.0 to 0-255
        lm_val = int(left_motor * 255)
        rm_val = int(right_motor * 255)
        
        if lm_byte >= 0 and lm_byte < len(template):
            template[lm_byte] = lm_val
        if rm_byte >= 0 and rm_byte < len(template):
            template[rm_byte] = rm_val
            
        for r in readers:
            r.send_output_report(template)

    virtual_pad.set_rumble_callback(rumble_callback)

    last_log_time = 0

    def data_handler(report: RawHIDReport):
        nonlocal last_log_time
        current_time = time.time()

        state = decoder.decode(report)

        if is_debug_mode and (current_time - last_log_time) >= 0.5:
            logger.debug(f"RAW [{report.report_id:02X}]: {' | '.join(f'{x:02X}' for x in report.payload)}")
            logger.debug(f"DECODED STATE: {state}")
            last_log_time = current_time

        mapper.process(state)
        virtual_pad.process(state)

    for r in readers:
        r.set_callback(data_handler)
        threading.Thread(target=r.start, daemon=True).start()

    logger.info("Running daemon in background...")
    # Background config poller
    def config_poller():
        last_mtime = 0
        if os.path.exists(controller_config_file):
            last_mtime = os.path.getmtime(controller_config_file)

        while True:
            time.sleep(5)  # Poll every 5 seconds
            try:
                if os.path.exists(controller_config_file):
                    current_mtime = os.path.getmtime(controller_config_file)
                    if current_mtime != last_mtime:
                        last_mtime = current_mtime
                        controller_config.load()
                        mapper.reload_config(controller_config)
                        virtual_pad.reload_config(controller_config)
                        macro_executor.load_macros()
                        logger.info("Controller config reloaded live!")
            except Exception as e:
                logger.error(f"Error reloading config: {e}")

    t_poller = threading.Thread(target=config_poller, daemon=True)
    t_poller.start()

    t_reader = threading.Thread(target=reader.start, daemon=True)
    t_reader.start()

    logger.info("App is running in the system tray.")

    # Automatically open GUI on initialization unless --boot is specified
    if not args.boot:
        logger.info("Auto-opening GUI...")
        open_config(None, None)

    # Setup tray icon
    image = create_image()
    menu = pystray.Menu(
        pystray.MenuItem('Open Config', open_config),
        pystray.MenuItem('Show Console', show_console_action),
        pystray.MenuItem('Quit', quit_app)
    )
    icon = pystray.Icon("dinput_wrapper", image, "UR-XD Wrapper", menu)

    try:
        icon.run()
    except KeyboardInterrupt:
        pass
    finally:
        reader.stop()
        write_status("Disconnected")
        for p in gui_processes:
            try:
                p.terminate()
            except Exception:
                pass
        os._exit(0)


if __name__ == "__main__":
    main()
