import time
import configparser
import sys
import os
from hid_reader import HIDReader
from decoder import Decoder
from mapper import Mapper
from virtual_pad import VirtualPad

def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    # If the file doesn't exist, we just return empty config, fallbacks will be used
    if os.path.exists(filename):
        config.read(filename)
    return config

def main():
    print("8BitDo Ultimate 2C DInput Fix Starting...")
    config = load_config()
    debug_mode = config.getboolean('debug', 'print_reports', fallback=False)

    try:
        mapper = Mapper(config)
        virtual_pad = VirtualPad(config)
    except Exception as e:
        print("Failed to initialize mapper or virtual pad.")
        print("Please ensure ViGEmBus is installed.")
        sys.exit(1)

    reader = HIDReader()
    if not reader.connect():
        sys.exit(1)

    decoder = Decoder()

    def data_handler(data):
        if debug_mode:
            print("RAW: " + " | ".join(f"{x:02X}" for x in data))
            
        state = decoder.decode(data)
        mapper.process(state)
        virtual_pad.process(state)

    reader.set_callback(data_handler)
    
    print("App is running. Press Ctrl+C to exit.")
    try:
        reader.start()
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        reader.stop()

if __name__ == "__main__":
    main()
