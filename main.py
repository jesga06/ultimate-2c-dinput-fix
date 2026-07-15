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

def hide_console():
    # Hide the console window
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except:
        pass

def show_console():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 5) # SW_SHOW
    except:
        pass

import subprocess

def open_config(icon, item):
    try:
        subprocess.Popen([sys.executable, 'gui.py'])
    except Exception as e:
        print(f"Failed to open GUI: {e}")

def show_console_action(icon, item):
    show_console()

def write_status(state, device_name="None"):
    try:
        with open('status.json', 'w') as f:
            json.dump({"status": state, "device": device_name}, f)
    except Exception as e:
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
    dc.ellipse((8, 8, width-8, height-8), fill=(50, 150, 250))
    dc.rectangle((24, 24, width-24, height-24), fill=(255, 255, 255))
    return image

def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if os.path.exists(filename):
        config.read(filename)
    return config

def main():
    hide_console()
    write_status("Starting...")
    print("UR-XD Wrapper Starting...")
    
    config_file = 'config.ini'
    config = load_config(config_file)
    debug_mode = config.getboolean('debug', 'print_reports', fallback=False)

    try:
        mapper = Mapper(config)
        virtual_pad = VirtualPad(config)
    except Exception as e:
        print(f"Failed to initialize mapper or virtual pad: {e}")
        print("Please ensure ViGEmBus is installed.")
        show_console()
        time.sleep(5)
        sys.exit(1)

    print("Scanning for connected devices with profiles...")
    devices = HIDReader.get_all_devices()
    selected_device = None
    profile_path = None
    
    for d in devices:
        potential_profile = f"profiles/{d.vendor_id:04X}_{d.product_id:04X}.json".lower()
        if os.path.exists(potential_profile):
            selected_device = d
            profile_path = potential_profile
            break

    if not selected_device:
        print("No connected devices with a saved profile found.")
        print("Please run calibration.py to generate a profile for your controller.")
        show_console()
        time.sleep(5)
        sys.exit(1)

    print(f"Found matching profile: {profile_path}")
    reader = HIDReader(device=selected_device)
    if not reader.connect():
        write_status("Disconnected")
        show_console()
        time.sleep(5)
        sys.exit(1)

    write_status("Connected", selected_device.product_name)

    decoder = Decoder(profile_path)

    def data_handler(data):
        if debug_mode:
            print("RAW: " + " | ".join(f"{x:02X}" for x in data))
            
        state = decoder.decode(data)
        mapper.process(state)
        virtual_pad.process(state)

    reader.set_callback(data_handler)
    
    # Background config poller
    def config_poller():
        last_mtime = 0
        if os.path.exists(config_file):
            last_mtime = os.path.getmtime(config_file)
            
        while True:
            time.sleep(5) # Poll every 5 seconds
            try:
                if os.path.exists(config_file):
                    current_mtime = os.path.getmtime(config_file)
                    if current_mtime != last_mtime:
                        last_mtime = current_mtime
                        new_config = load_config(config_file)
                        mapper.reload_config(new_config)
                        virtual_pad.reload_config(new_config)
                        print("Config reloaded live!")
            except Exception as e:
                print(f"Error reloading config: {e}")

    t_poller = threading.Thread(target=config_poller, daemon=True)
    t_poller.start()
    
    t_reader = threading.Thread(target=reader.start, daemon=True)
    t_reader.start()

    print("App is running in the system tray.")
    
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

if __name__ == "__main__":
    main()
