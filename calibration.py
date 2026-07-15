import time
import os
from hid_reader import HIDReader

previous_data = None

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def format_bits(byte_val):
    return f"{byte_val:08b}"

def calibration_handler(data):
    global previous_data
    
    # Ignore initial report to establish baseline
    if previous_data is None:
        previous_data = data
        return

    # Check if there's any change
    if data == previous_data:
        return
        
    clear_console()
    print("=== 8BitDo Ultimate 2C DInput Calibration ===")
    print("Press and release a button to see its mapping.")
    print("-" * 50)
    
    print(f"Raw Data: {' '.join(f'{x:02X}' for x in data)}")
    print("-" * 50)
    
    # We know that report ID is index 0.
    # Byte 1 is data[1], Byte 2 is data[2], etc.
    
    print("Changed Bytes:")
    for i in range(1, len(data)):
        if i >= len(previous_data):
            break
        
        if data[i] != previous_data[i]:
            diff_bits = data[i] ^ previous_data[i]
            print(f"Byte {i}: {data[i]:02X} (Bits: {format_bits(data[i])})")
            
            # Print which bits specifically changed
            for bit in range(8):
                if (diff_bits >> bit) & 1:
                    val = (data[i] >> bit) & 1
                    print(f"  -> Bit {bit} changed to {val}")
    
    previous_data = data

if __name__ == "__main__":
    reader = HIDReader()
    if reader.connect():
        reader.set_callback(calibration_handler)
        print("Calibration Tool Started.")
        print("Move the sticks and triggers slightly to establish a baseline, then press buttons.")
        try:
            reader.start()
        except KeyboardInterrupt:
            reader.stop()
