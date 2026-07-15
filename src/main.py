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
import os
import threading
import json
from hid_reader import HIDReader
from decoder import Decoder
from mapper import Mapper
from virtual_pad import VirtualPad

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

    try:
        mapper = Mapper(config)
        virtual_pad = VirtualPad(config)
    except Exception as e:
        logger.error(f"Failed to initialize mapper or virtual pad: {e}")
        logger.info("Please ensure ViGEmBus is installed.")
        show_console()
        time.sleep(5)
        sys.exit(1)

    logger.info("Scanning for connected devices with profiles...")
    devices = HIDReader.get_all_devices()
    selected_device = None
    profile_path = None

    for d in devices:
        potential_profile = f"profiles/{
            d.vendor_id:04X}_{
            d.product_id:04X}.json".lower()
        if os.path.exists(potential_profile):
            selected_device = d
            profile_path = potential_profile
            break

    if not selected_device:
        logger.warning("No connected devices with a saved profile found.")
        logger.info(
            "Please run calibration.py to generate a profile for your controller.")
        show_console()
        time.sleep(5)
        sys.exit(1)

    logger.info(f"Found matching profile: {profile_path}")
    reader = HIDReader(device=selected_device)
    if not reader.connect():
        write_status("Disconnected")
        show_console()
        time.sleep(5)
        sys.exit(1)

    write_status("Connected", selected_device.product_name)

    decoder = Decoder(profile_path)

    last_log_time = 0

    def data_handler(data):
        nonlocal last_log_time
        current_time = time.time()

        state = decoder.decode(data)

        if is_debug_mode and (current_time - last_log_time) >= 0.5:
            logger.debug("RAW: " + " | ".join(f"{x:02X}" for x in data))
            logger.debug(f"DECODED STATE: {state}")
            last_log_time = current_time

        mapper.process(state)
        virtual_pad.process(state)

    reader.set_callback(data_handler)

    # Background config poller
    def config_poller():
        last_mtime = 0
        if os.path.exists(config_file):
            last_mtime = os.path.getmtime(config_file)

        while True:
            time.sleep(5)  # Poll every 5 seconds
            try:
                if os.path.exists(config_file):
                    current_mtime = os.path.getmtime(config_file)
                    if current_mtime != last_mtime:
                        last_mtime = current_mtime
                        new_config = load_config(config_file)
                        mapper.reload_config(new_config)
                        virtual_pad.reload_config(new_config)
                        logger.info("Config reloaded live!")
            except Exception as e:
                logger.error(f"Error reloading config: {e}")

    t_poller = threading.Thread(target=config_poller, daemon=True)
    t_poller.start()

    t_reader = threading.Thread(target=reader.start, daemon=True)
    t_reader.start()

    logger.info("App is running in the system tray.")

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
