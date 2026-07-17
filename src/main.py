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
    hid_map_path = None    # path to the {VID}_{PID}.json HID map
    device_name = "Unknown Device"

    # --- Community database auto-update ---
    # The last successful fetch time is stored in config.ini under [community] db_last_updated
    # (Unix timestamp float). The database is refreshed if it is missing OR older than the
    # configured interval. This check runs on every wrapper launch, but the network request
    # only fires once per interval, independent of how many times the wrapper has been run.
    DB_UPDATE_INTERVAL_DAYS = config.getfloat('community', 'db_update_interval_days', fallback=7.0)
    DB_UPDATE_INTERVAL_SECS = DB_UPDATE_INTERVAL_DAYS * 86400.0

    db_path = os.path.join("profiles", "community", "database.json")
    db_last_updated = config.getfloat('community', 'db_last_updated', fallback=0.0)
    time_since_update = time.time() - db_last_updated
    db_needs_update = (not os.path.exists(db_path)) or (time_since_update >= DB_UPDATE_INTERVAL_SECS)

    if db_needs_update:
        reason = "not found locally" if not os.path.exists(db_path) else f"last updated {time_since_update / 86400:.1f} days ago"
        logger.info(f"Community database {reason}. Refreshing...")
        try:
            import community_fetcher
            community_fetcher.fetch_database(logger=logger)
            # Persist the new update timestamp into config.ini
            if not config.has_section('community'):
                config.add_section('community')
            config.set('community', 'db_last_updated', str(time.time()))
            config.set('community', 'db_update_interval_days', str(DB_UPDATE_INTERVAL_DAYS))
            with open(config_file, 'w') as f:
                config.write(f)
            logger.info("Community database updated successfully.")
        except Exception as fe:
            logger.warning(f"Could not update community database: {fe}")
    else:
        logger.info(f"Community database is up to date (updated {time_since_update / 86400:.1f} days ago, interval: {DB_UPDATE_INTERVAL_DAYS:.0f} days).")


    for d in devices:
        vid = d.get('vendor_id', 0)
        pid = d.get('product_id', 0)
        # 1. Try to find a local HID map for this VID/PID
        potential_hid_map = f"profiles/{vid:04X}_{pid:04X}.json".lower()
        if os.path.exists(potential_hid_map):
            selected_vid = vid
            selected_pid = pid
            hid_map_path = potential_hid_map
            try:
                with open(hid_map_path, 'r') as f:
                    map_data = json.load(f)
                    device_name = map_data.get('name', "Unknown Device")
            except:
                pass
            break
        else:
            # 2. Fall back to the community HID map database
            if os.path.exists(db_path):
                try:
                    with open(db_path, 'r', encoding='utf-8') as f:
                        db = json.load(f)
                    vid_pid_str = f"{vid:04X}:{pid:04X}".upper()
                    for entry_name, entry_data in db.items():
                        if vid_pid_str in entry_data.get("aliases", []):
                            # hid_map_file is relative to the REPO root, basename goes to community dir
                            hid_map_filename = os.path.basename(entry_data.get("hid_map_file", ""))
                            comm_map = os.path.join("profiles", "community", hid_map_filename)
                            if not os.path.exists(comm_map):
                                # Map not cached yet — selectively download it now
                                logger.info(f"Downloading community HID map for {vid_pid_str}...")
                                try:
                                    import community_fetcher
                                    community_fetcher.fetch_maps_for_devices([(vid, pid)], logger=logger)
                                except Exception as fe:
                                    logger.warning(f"Could not auto-download community HID map: {fe}")
                            if os.path.exists(comm_map):
                                selected_vid = vid
                                selected_pid = pid
                                hid_map_path = comm_map
                                with open(hid_map_path, 'r', encoding='utf-8') as mf:
                                    map_data = json.load(mf)
                                    device_name = map_data.get('name', "Unknown Device") + " (Community HID Map)"
                                break
                except Exception:
                    pass
        if hid_map_path:
            break

    if not hid_map_path:
        logger.warning("No connected devices with a saved HID map found.")
        logger.info(
            "Please run calibration.py to generate a HID map for your controller.")
        show_console()
        time.sleep(5)
        sys.exit(1)

    logger.info(f"Found matching HID map: {hid_map_path} ({device_name})")

    # Initialize user profile — named after the device
    # The user profile ({device_name}.json) holds remaps, deadzones, curves, etc.
    sanitized_name = get_sanitized_filename(device_name)
    controller_config_file = os.path.join("profiles", sanitized_name)
    controller_config = ControllerConfig(controller_config_file)
    
    # Save last connected device info to wrapper config (config.ini)
    if not config.has_section('controller'):
        config.add_section('controller')
    config.set('controller', 'last_device', device_name)
    # 'last_profile' key retained for backwards compatibility; now stores the HID map path
    config.set('controller', 'last_profile', hid_map_path)
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

    from utilities_backend import monitor

    from state_record_play import StateRecorder, StatePlayer
    recorder = StateRecorder("recording.json")
    player = StatePlayer("recording.json")
    
    last_cmd_check = 0.0

    def data_handler(report: RawHIDReport):
        start_t = monitor.record_poll()
        nonlocal last_log_time, last_cmd_check
        current_time = time.time()
        
        if current_time - last_cmd_check > 0.1:
            last_cmd_check = current_time
            if os.path.exists("record_cmd.txt"):
                try:
                    with open("record_cmd.txt", "r") as f:
                        cmd = f.read().strip()
                    os.remove("record_cmd.txt")
                    if cmd == "record_start":
                        recorder.start()
                    elif cmd == "record_stop":
                        recorder.stop()
                    elif cmd == "play_start":
                        player.start()
                    elif cmd == "play_stop":
                        player.stop()
                except: pass

        if player.is_playing:
            playback_state_dict = player.get_current_state()
            if playback_state_dict:
                state = ControllerState(**playback_state_dict)
            else:
                state = decoder.decode(report)
        else:
            state = decoder.decode(report)

        if recorder.is_recording:
            recorder.record_event(state.__dict__)

        if is_debug_mode and (current_time - last_log_time) >= 0.5:
            logger.debug(f"RAW [{report.report_id:02X}]: {' | '.join(f'{x:02X}' for x in report.payload)}")
            logger.debug(f"DECODED STATE: {state}")
            last_log_time = current_time

        mapper.process(state)
        virtual_pad.process(state)
        
        monitor.record_process(start_t)
        monitor.broadcast_state(state)

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
