"""
HID Interface Reader (hid_reader.py)
Uses hid (Cython hidapi) to query, connect to, and read raw USB HID reports from gamepads.
Runs an asynchronous receiver loop in the background and delivers reports via callbacks.
"""
import hid
import time
import threading
from dataclasses import dataclass
from typing import List
import logging

logger = logging.getLogger('hid_reader')

MAX_HID_PACKET_SIZE = 1024

@dataclass
class RawHIDReport:
    """
    Represents a single raw packet received from the HID device.
    """
    report_id: int
    payload: List[int]
    timestamp: float
    interface_number: int = -1

    @property
    def data(self) -> List[int]:
        return self.payload

HIDReport = RawHIDReport

class HIDReader:
    """
    Manages connections to physical USB HID devices and listens to reports using hidapi.
    """

    def __init__(self, device_path=None, auto_reconnect=True, interface_number=-1):
        self.device_path = device_path
        self.device = None
        self.callback = None
        self._running = False
        self._thread = None
        self._last_product_name = None
        self.auto_reconnect = auto_reconnect
        self._connected_time = 0
        self.interface_number = interface_number

    @staticmethod
    def get_all_devices():
        """Returns a list of dictionaries describing all connected HID devices."""
        return hid.enumerate()

    def connect(self):
        if not self.device_path:
            print("No device_path provided.")
            logger.error("No device_path provided.")
            return False

        try:
            self.device = hid.device()
            self.device.open_path(self.device_path)
            self.device.set_nonblocking(1)
            
            # Try to read product string (might not be available on all OS/devices)
            try:
                prod = self.device.get_product_string()
                self._last_product_name = prod
                # Only print if not silenced
            except Exception:
                self._last_product_name = "Unknown Device"
                
            self._connected_time = time.time()
            return True
        except Exception as e:
            self.device = None
            return False

    def set_callback(self, callback):
        self.callback = callback

    def start(self):
        if not self.device:
            print("Device not connected. Call connect() first.")
            logger.error("Device not connected. Call connect() first.")
            return
            
        self._running = True
        
        while self._running:
            try:
                # Read up to MAX_HID_PACKET_SIZE bytes
                # In non-blocking mode, this returns an empty list if no data is available
                data = self.device.read(MAX_HID_PACKET_SIZE)
                if data:
                    if self.callback:
                        # We pass the full unsliced payload. If the device uses report IDs,
                        # data[0] is the report ID. If not, data[0] is the first byte of the actual payload.
                        report_id = data[0]
                        report = RawHIDReport(report_id=report_id, payload=data, timestamp=time.time(), interface_number=self.interface_number)
                        self.callback(report)
                else:
                    # Sleep briefly to prevent high CPU usage in non-blocking mode
                    time.sleep(0.001)
                    
            except OSError as e:
                # Device disconnected or read failed
                if not self.auto_reconnect:
                    break
                    
                # If it failed immediately upon connecting, it's likely an OS permission issue (e.g. system keyboard)
                # Don't try to reconnect to avoid infinite loops.
                if time.time() - self._connected_time < 2.0:
                    logger.warning(f"Interface on {self._last_product_name} locked by OS (expected for system devices). Stopping thread.")
                    break
                    
                print(f"\nDevice '{self._last_product_name}' disconnected or read error: {e}")
                logger.error(f"Device '{self._last_product_name}' disconnected or read error: {e}")
                if not self._handle_disconnect():
                    break
            except ValueError as e:
                # hidapi raises ValueError if device is closed
                break

    def send_output_report(self, data: list[int]):
        """Sends a raw HID output report to the device."""
        if not self.device:
            return False
        try:
            bytes_written = self.device.write(data)
            if bytes_written == -1:
                print(f"Failed to write output report to device.")
                logger.error("Failed to write output report to device.")
                return False
            return True
        except Exception as e:
            print(f"Error writing to device: {e}")
            logger.error(f"Error writing to device: {e}")
            return False

    def _handle_disconnect(self):
        """Attempts to reconnect if the device is lost. Returns True if reconnected."""
        if not self._running:
            return False
            
        print(f"Waiting up to 20s for '{self._last_product_name}' to return...")
        logger.info(f"Waiting up to 20s for '{self._last_product_name}' to return...")
        try:
            self.device.close()
        except Exception:
            pass
        self.device = None
        
        timeout = 20
        start_wait = time.time()

        while time.time() - start_wait < timeout and self._running:
            devices = hid.enumerate()
            for d in devices:
                if d.get('product_string') == self._last_product_name:
                    self.device_path = d['path']
                    if self.connect():
                        print(f"Reconnected to {self._last_product_name} successfully.")
                        logger.info(f"Reconnected to {self._last_product_name} successfully.")
                        return True
            time.sleep(1.0)

        print("Timeout reached, device not found.")
        logger.error("Timeout reached, device not found.")
        return False

    def stop(self):
        self._running = False
        if self.device:
            self.device.close()
            self.device = None
            print("Device closed.")
            logger.info("Device closed.")

if __name__ == "__main__":
    def print_data(report: RawHIDReport):
        print(f"ID: {report.report_id:02X} | PAYLOAD: {' | '.join(f'{x:02X}' for x in report.payload)}")

    devices = HIDReader.get_all_devices()
    if not devices:
        print("No devices found.")
    else:
        # Just grab the first one for testing
        test_path = devices[0]['path']
        reader = HIDReader(device_path=test_path)
        if reader.connect():
            reader.set_callback(print_data)
            try:
                print("Reading data... Press Ctrl+C to stop.")
                reader.start()
            except KeyboardInterrupt:
                reader.stop()
