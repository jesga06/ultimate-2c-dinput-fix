import sys
import os
import unittest
from unittest.mock import MagicMock

sys.modules['hid'] = MagicMock()

class DummyToplevel:
    pass

mock_ctk = MagicMock()
mock_ctk.CTkToplevel = DummyToplevel
sys.modules['customtkinter'] = mock_ctk

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_ROOT)
sys.path.append(os.path.join(REPO_ROOT, "src"))

from circularity_modal import CircularityCalibrationModal

class TestCircularityModal(unittest.TestCase):
    def test_get_raw_input_polarity(self):
        parent = MagicMock()
        state = MagicMock()
        state.lx = 0.5
        state.ly = 0.8
        state.rx = -0.3
        state.ry = -0.9
        parent.current_state = state
        
        # Test Left Stick
        left_modal = CircularityCalibrationModal.__new__(CircularityCalibrationModal)
        left_modal.parent = parent
        left_modal.is_left = True
        
        lx, ly = left_modal.get_raw_input()
        self.assertEqual(lx, 0.5)
        self.assertEqual(ly, 0.8, "Y stick direction for left stick must not be inverted (positive UP)")
        
        # Test Right Stick
        right_modal = CircularityCalibrationModal.__new__(CircularityCalibrationModal)
        right_modal.parent = parent
        right_modal.is_left = False
        
        rx, ry = right_modal.get_raw_input()
        self.assertEqual(rx, -0.3)
        self.assertEqual(ry, -0.9, "Y stick direction for right stick must not be inverted (positive UP)")

if __name__ == '__main__':
    unittest.main()
