import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to python path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from decoder import ControllerState

class TestVirtualPadTunedOutputs(unittest.TestCase):
    @patch('vgamepad.VX360Gamepad')
    def test_virtual_pad_digital_trigger(self, mock_vx360):
        mock_gamepad = MagicMock()
        mock_vx360.return_value = mock_gamepad

        from virtual_pad import VirtualPad
        vpad = VirtualPad()
        vpad.digital_lt = True

        state = ControllerState()
        state.lt = 0.3

        vpad.process(state)

        # Since digital_lt is True and lt > 0, left_trigger_float should receive 1.0
        mock_gamepad.left_trigger_float.assert_called_with(value_float=1.0)

    @patch('vgamepad.VX360Gamepad')
    def test_virtual_pad_stick_deadzone(self, mock_vx360):
        mock_gamepad = MagicMock()
        mock_vx360.return_value = mock_gamepad

        from virtual_pad import VirtualPad
        vpad = VirtualPad()
        vpad.ls_inner = 0.2

        state = ControllerState()
        state.lx = 0.1
        state.ly = 0.0

        vpad.process(state)

        # Magnitude 0.1 is inside deadzone 0.2, so left_joystick should be (0, 0)
        mock_gamepad.left_joystick.assert_called_with(x_value=0, y_value=0)

    @patch('vgamepad.VX360Gamepad')
    def test_virtual_pad_right_stick_curve(self, mock_vx360):
        mock_gamepad = MagicMock()
        mock_vx360.return_value = mock_gamepad

        from virtual_pad import VirtualPad
        vpad = VirtualPad()
        vpad.rs_inner = 0.0
        vpad.rs_curve = 'aggressive'
        vpad.rs_power = 2.0

        state = ControllerState()
        state.rx = 0.5
        state.ry = 0.0

        vpad.process(state)

        # aggressive power 2.0 on 0.5 input gives 1.0 - (1.0 - 0.5)^2 = 0.75
        # 0.75 * 32767 = 24575
        args = mock_gamepad.right_joystick.call_args[1]
        self.assertAlmostEqual(args['x_value'], int(0.75 * 32767), delta=2)
        self.assertEqual(args['y_value'], 0)

if __name__ == '__main__':
    unittest.main()
