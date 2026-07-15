import pywinusb.hid as hid
import time
import threading

class HIDReader:
    def __init__(self, vid=0x2DC8, pid=0x301C):
        self.vid = vid
        self.pid = pid
        self.device = None
        self.callback = None
        self._running = False

    def connect(self):
        devices = hid.HidDeviceFilter(vendor_id=self.vid, product_id=self.pid).get_devices()
        if not devices:
            print(f"Device VID:{self.vid:04X} PID:{self.pid:04X} not found.")
            return False
        
        self.device = devices[0]
        try:
            self.device.open()
            print(f"Connected to {self.device.product_name}")
            return True
        except Exception as e:
            print(f"Failed to open device: {e}")
            return False

    def set_callback(self, callback):
        self.callback = callback
        if self.device:
            self.device.set_raw_data_handler(self._data_handler)

    def _data_handler(self, data):
        if self.callback:
            # First byte is Report ID (usually 0x01), pass the whole list
            self.callback(data)

    def start(self):
        self._running = True
        while self._running and self.device and self.device.is_plugged():
            time.sleep(0.1)
        self.stop()

    def stop(self):
        self._running = False
        if self.device and self.device.is_opened():
            self.device.close()
            print("Device closed.")

if __name__ == "__main__":
    def print_data(data):
        print(" | ".join(f"{x:02X}" for x in data))

    reader = HIDReader()
    if reader.connect():
        reader.set_callback(print_data)
        try:
            print("Reading data... Press Ctrl+C to stop.")
            reader.start()
        except KeyboardInterrupt:
            reader.stop()
