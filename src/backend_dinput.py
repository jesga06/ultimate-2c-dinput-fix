"""
DInput Backend (backend_dinput.py)
Implements DirectInput device polling using the existing HIDReader and Decoder.
"""
import time
import threading
import logging
from backend_base import BaseInputBackend
from hid_reader import HIDReader
from decoder import Decoder

logger = logging.getLogger('dinput_backend')

class DInputBackend(BaseInputBackend):
    def __init__(self, hid_map_path: str, vid: int, pid: int, req_ifaces: list = None):
        super().__init__()
        self.hid_map_path = hid_map_path
        self.target_vid = vid
        self.target_pid = pid
        self.req_ifaces = req_ifaces or []
        self.readers = []
        self.decoder = None
        self.is_running = False

    def get_capabilities(self) -> dict:
        return {
            'vibration': False,  # DInput vibration is unsupported
            'analog_triggers': True, # Depends on the descriptor, but we allow it
            'guide_button': True,
            'extra_buttons': True # Exposed natively in DInput
        }

    def initialize(self) -> bool:
        try:
            self.decoder = Decoder(self.hid_map_path)
            
            devices = HIDReader.get_all_devices()
            for d in devices:
                if d.get('vendor_id', 0) == self.target_vid and d.get('product_id', 0) == self.target_pid:
                    iface_num = d.get('interface_number', -1)
                    if self.req_ifaces and iface_num not in self.req_ifaces:
                        continue
                    reader = HIDReader(device_path=d['path'], interface_number=iface_num)
                    if reader.connect():
                        self.readers.append(reader)
                        
            if self.readers:
                logger.info(f"DInput backend initialized with {len(self.readers)} reader(s).")
                return True
        except Exception as e:
            logger.error(f"Failed to initialize DInput backend: {e}", exc_info=True)
            
        return False

    def get_connection_state(self) -> bool:
        return len(self.readers) > 0

    def shutdown(self):
        self.is_running = False
        for r in self.readers:
            r.stop()
        self.readers.clear()

    def set_vibration(self, left_motor: float, right_motor: float):
        # We don't support vibration in DInput right now
        pass

    def poll(self):
        if logger:
            logger.debug("[ENTER] backend_dinput poll loop started")
        if not self.readers:
            logger.warning("Cannot start polling without connected readers.")
            return

        self.is_running = True
        
        def _data_handler(report):
            if not self.is_running:
                return
            state = self.decoder.decode(report)
            if self.callback:
                self.callback(state)

        for r in self.readers:
            r.set_callback(_data_handler)
            threading.Thread(target=r.start, daemon=True).start()
            
        # DInput readers use their own polling threads, so this backend's poll() 
        # doesn't need to block in a loop, but we can just wait until shutdown.
        while self.is_running:
            time.sleep(1.0)
