import sys
import os
import unittest
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_ROOT)
sys.path.append(os.path.join(REPO_ROOT, "src"))

from src.backend_xinput import (
    XInputBackend, XINPUT_STATE, XINPUT_GAMEPAD, XINPUT_VIBRATION,
    XINPUT_GAMEPAD_A, XINPUT_GAMEPAD_B, XINPUT_GAMEPAD_GUIDE
)
from src.decoder import ControllerState

class TestXInputBackend(unittest.TestCase):

    @patch('ctypes.windll.LoadLibrary')
    def test_load_xinput_success(self, mock_load_lib):
        mock_dll = MagicMock()
        mock_load_lib.return_value = mock_dll

        backend = XInputBackend()
        self.assertIsNotNone(backend.xinput)

    def test_normalize_axis(self):
        backend = XInputBackend()
        self.assertAlmostEqual(backend._normalize_axis(0), 0.0)
        self.assertAlmostEqual(backend._normalize_axis(-32768), -1.0)
        self.assertAlmostEqual(backend._normalize_axis(32767), 1.0)

    @patch('ctypes.windll.LoadLibrary')
    def test_set_vibration(self, mock_load_lib):
        mock_dll = MagicMock()
        mock_load_lib.return_value = mock_dll
        backend = XInputBackend()
        backend.connected_slot = 0
        backend.XInputSetState = MagicMock()

        backend.set_vibration(0.5, 1.0)
        backend.XInputSetState.assert_called_once()
        args, _ = backend.XInputSetState.call_args
        self.assertEqual(args[0], 0)
        vib_struct = args[1]._obj
        self.assertEqual(vib_struct.wLeftMotorSpeed, 32767)
        self.assertEqual(vib_struct.wRightMotorSpeed, 65535)

    def test_capabilities(self):
        backend = XInputBackend()
        caps = backend.get_capabilities()
        self.assertIn('vibration', caps)
        self.assertIn('analog_triggers', caps)
        self.assertIn('guide_button', caps)

if __name__ == '__main__':
    unittest.main()
