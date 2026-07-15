"""
HID Interface Reader (hid_reader.py)
Uses pywinusb to query, connect to, and read raw USB HID reports from gamepads.
Runs an asynchronous receiver loop in the background and delivers reports via callbacks.
"""
import pywinusb.hid as hid
import time


class HIDReader:
    """
    Manages connections to physical USB HID devices and listens to reports.
    Provides utility methods to list connected HID devices on Windows.
    """

    def __init__(self, vid=None, pid=None, device=None):
        self.vid = vid
        self.pid = pid
        self.device = device
        self.callback = None
        self._running = False

    @staticmethod
    def get_all_devices():
        return hid.find_all_hid_devices()

    def connect(self):
        if not self.device:
            if self.vid and self.pid:
                devices = hid.HidDeviceFilter(
                    vendor_id=self.vid, product_id=self.pid).get_devices()
                if not devices:
                    print(
                        f"Device VID:{
                            self.vid:04X} PID:{
                            self.pid:04X} not found.")
                    return False
                self.device = devices[0]
            else:
                print("No device provided and no VID/PID specified.")
                return False

        try:
            self.device.open()
            print(f"Connected to {self.device.product_name}")
            self._last_product_name = self.device.product_name
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
        while self._running:
            if self.device and self.device.is_plugged():
                time.sleep(0.1)
            else:
                target_name = getattr(self, '_last_product_name', None)
                if not target_name and self.device:
                    target_name = self.device.product_name

                if not target_name:
                    print("Lost device but no product name known. Exiting.")
                    break

                print(
                    f"Device disconnected. Waiting up to 20s for '{target_name}' to return...")
                timeout = 20
                start_wait = time.time()
                reconnected = False

                while time.time() - start_wait < timeout and self._running:
                    devices = hid.find_all_hid_devices()
                    for d in devices:
                        if getattr(d, 'product_name', '') == target_name:
                            try:
                                d.open()
                                self.device = d
                                if self.callback:
                                    self.device.set_raw_data_handler(
                                        self._data_handler)
                                print("Reconnected successfully.")
                                reconnected = True
                                break
                            except Exception:
                                pass
                    if reconnected:
                        break
                    time.sleep(1.0)

                if not reconnected:
                    print("Timeout reached, device not found. Exiting.")
                    import os
                    os._exit(0)
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
