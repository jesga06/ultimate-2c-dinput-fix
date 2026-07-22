"""
XInput Backend (backend_xinput.py)
Implements native XInput polling and vibration support using ctypes.
"""
import ctypes
from ctypes.wintypes import WORD, DWORD, BYTE, SHORT
import time
import threading
import logging
from backend_base import BaseInputBackend
from decoder import ControllerState

logger = logging.getLogger('xinput_backend')

# XInput Structs
class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", WORD),
        ("bLeftTrigger", BYTE),
        ("bRightTrigger", BYTE),
        ("sThumbLX", SHORT),
        ("sThumbLY", SHORT),
        ("sThumbRX", SHORT),
        ("sThumbRY", SHORT),
    ]

class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", DWORD),
        ("Gamepad", XINPUT_GAMEPAD),
    ]

class XINPUT_VIBRATION(ctypes.Structure):
    _fields_ = [
        ("wLeftMotorSpeed", WORD),
        ("wRightMotorSpeed", WORD),
    ]

# XInput Button Constants
XINPUT_GAMEPAD_DPAD_UP          = 0x0001
XINPUT_GAMEPAD_DPAD_DOWN        = 0x0002
XINPUT_GAMEPAD_DPAD_LEFT        = 0x0004
XINPUT_GAMEPAD_DPAD_RIGHT       = 0x0008
XINPUT_GAMEPAD_START            = 0x0010
XINPUT_GAMEPAD_BACK             = 0x0020
XINPUT_GAMEPAD_LEFT_THUMB       = 0x0040
XINPUT_GAMEPAD_RIGHT_THUMB      = 0x0080
XINPUT_GAMEPAD_LEFT_SHOULDER    = 0x0100
XINPUT_GAMEPAD_RIGHT_SHOULDER   = 0x0200
XINPUT_GAMEPAD_A                = 0x1000
XINPUT_GAMEPAD_B                = 0x2000
XINPUT_GAMEPAD_X                = 0x4000
XINPUT_GAMEPAD_Y                = 0x8000
XINPUT_GAMEPAD_GUIDE            = 0x0400 # Undocumented, but usually works

class XInputBackend(BaseInputBackend):
    def __init__(self):
        super().__init__()
        self._load_xinput()
        self.connected_slot = -1
        self.is_running = False
        self._thread = None
        self.poll_rate_hz = 500
        self.last_packet_number = -1

    def _load_xinput(self):
        self.xinput = None
        dlls = ["xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"]
        for dll in dlls:
            try:
                self.xinput = ctypes.windll.LoadLibrary(dll)
                logger.info(f"Loaded XInput DLL: {dll}")
                break
            except Exception:
                pass
        
        if self.xinput:
            self.XInputGetState = getattr(self.xinput, "XInputGetState", None)
            if self.XInputGetState:
                self.XInputGetState.argtypes = [DWORD, ctypes.POINTER(XINPUT_STATE)]
                self.XInputGetState.restype = DWORD
            
            # XInputGetStateEx (ordinal 100) gets the Guide button
            self.XInputGetStateEx = getattr(self.xinput, (b"#100" if isinstance("#100", bytes) else 100), None)
            if self.XInputGetStateEx:
                self.XInputGetStateEx.argtypes = [DWORD, ctypes.POINTER(XINPUT_STATE)]
                self.XInputGetStateEx.restype = DWORD

            self.XInputSetState = getattr(self.xinput, "XInputSetState", None)
            if self.XInputSetState:
                self.XInputSetState.argtypes = [DWORD, ctypes.POINTER(XINPUT_VIBRATION)]
                self.XInputSetState.restype = DWORD
        else:
            logger.error("Failed to load any XInput DLL.")

    def get_capabilities(self) -> dict:
        return {
            'vibration': True,
            'analog_triggers': True,
            'guide_button': self.XInputGetStateEx is not None,
            'extra_buttons': False # Hardware Chords synthesize them
        }

    def initialize(self) -> bool:
        if not self.xinput:
            return False
        
        # Scan slots 0-3
        state = XINPUT_STATE()
        for i in range(4):
            if self.XInputGetState(i, ctypes.byref(state)) == 0:
                self.connected_slot = i
                logger.info(f"XInput controller found on slot {i}")
                return True
        return False

    def get_connection_state(self) -> bool:
        if self.connected_slot < 0 or not self.xinput:
            return False
        state = XINPUT_STATE()
        return self.XInputGetState(self.connected_slot, ctypes.byref(state)) == 0

    def shutdown(self):
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        self.set_vibration(0.0, 0.0)

    def set_vibration(self, left_motor: float, right_motor: float):
        if self.connected_slot >= 0 and self.XInputSetState:
            vib = XINPUT_VIBRATION()
            # Scale 0.0-1.0 to 0-65535
            vib.wLeftMotorSpeed = int(max(0.0, min(1.0, left_motor)) * 65535)
            vib.wRightMotorSpeed = int(max(0.0, min(1.0, right_motor)) * 65535)
            self.XInputSetState(self.connected_slot, ctypes.byref(vib))

    def _normalize_axis(self, value):
        if value < 0:
            return value / 32768.0
        return value / 32767.0

    def poll(self):
        if not self.initialize():
            logger.warning("No XInput controller connected.")
            return

        self.is_running = True
        sleep_interval = 1.0 / self.poll_rate_hz
        
        state = XINPUT_STATE()
        get_state_func = self.XInputGetStateEx if self.XInputGetStateEx else self.XInputGetState

        logger.info("XInput polling loop started.")
        while self.is_running:
            start_t = time.time()
            if get_state_func(self.connected_slot, ctypes.byref(state)) == 0:
                # Check if packet changed to avoid redundant processing if desired, 
                # but we usually just process state anyway to drive chords/macros timing
                
                gp = state.Gamepad
                cs = ControllerState()
                
                btns = gp.wButtons
                cs.dpad_up = bool(btns & XINPUT_GAMEPAD_DPAD_UP)
                cs.dpad_down = bool(btns & XINPUT_GAMEPAD_DPAD_DOWN)
                cs.dpad_left = bool(btns & XINPUT_GAMEPAD_DPAD_LEFT)
                cs.dpad_right = bool(btns & XINPUT_GAMEPAD_DPAD_RIGHT)
                
                cs.start = bool(btns & XINPUT_GAMEPAD_START)
                cs.select = bool(btns & XINPUT_GAMEPAD_BACK)
                cs.l3 = bool(btns & XINPUT_GAMEPAD_LEFT_THUMB)
                cs.r3 = bool(btns & XINPUT_GAMEPAD_RIGHT_THUMB)
                cs.lb = bool(btns & XINPUT_GAMEPAD_LEFT_SHOULDER)
                cs.rb = bool(btns & XINPUT_GAMEPAD_RIGHT_SHOULDER)
                cs.a = bool(btns & XINPUT_GAMEPAD_A)
                cs.b = bool(btns & XINPUT_GAMEPAD_B)
                cs.x = bool(btns & XINPUT_GAMEPAD_X)
                cs.y = bool(btns & XINPUT_GAMEPAD_Y)
                cs.home = bool(btns & XINPUT_GAMEPAD_GUIDE)
                
                cs.lt = gp.bLeftTrigger / 255.0
                cs.rt = gp.bRightTrigger / 255.0
                
                cs.lx = self._normalize_axis(gp.sThumbLX)
                cs.ly = self._normalize_axis(gp.sThumbLY)
                cs.rx = self._normalize_axis(gp.sThumbRX)
                cs.ry = self._normalize_axis(gp.sThumbRY)
                
                if self.callback:
                    self.callback(cs)
            else:
                # Disconnected
                self.is_running = False
                logger.info("XInput controller disconnected.")
                break
                
            elapsed = time.time() - start_t
            time.sleep(max(0, sleep_interval - elapsed))

    def start_polling_thread(self):
        self._thread = threading.Thread(target=self.poll, daemon=True)
        self._thread.start()
