import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Mock 'hid' module entirely before importing anything that requires it
sys.modules['hid'] = MagicMock()

# Add repo root and diagnostics dir to path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_ROOT)
sys.path.append(os.path.join(REPO_ROOT, "diagnostics"))

# Import the modules
import importlib
scanner_module = importlib.import_module("04_report_id_scanner")
baseline_module = importlib.import_module("05_baseline_logic_test")

class TestDiagnostics(unittest.TestCase):
    
    @patch('hid.enumerate')
    @patch('hid.device')
    @patch('builtins.input')
    @patch('time.sleep')
    @patch('time.time')
    def test_report_id_scanner(self, mock_time, mock_sleep, mock_input, mock_device_cls, mock_enumerate):
        # Setup mocks
        mock_enumerate.return_value = [
            {
                'path': b'mock_path_1',
                'vendor_id': 0x2DC8,
                'product_id': 0x301C,
                'manufacturer_string': '8BitDo',
                'product_string': '8BitDo Ultimate 2C',
                'interface_number': 0
            }
        ]
        
        mock_device = MagicMock()
        mock_device_cls.return_value = mock_device
        
        # User input choices:
        # 1. Select device index -> '0'
        # 2. Press Enter when ready... -> ''
        mock_input.side_effect = ['0', '']
        
        # Mock time sequence to advance 10.1 seconds
        time_sequence = [100.0]
        # Generate time values that increment
        for i in range(150):
            time_sequence.append(100.0 + (i * 0.1))
        mock_time.side_effect = time_sequence
        
        # Mock device read packets
        packets = [
            [0x01, 0x10, 0x20],
            [0x01, 0x15, 0x20],
            [0x02, 0x99],
            None,
            [0x01, 0x10, 0x20]
        ]
        mock_device.read.side_effect = packets + [None] * 200
        
        # Run main
        scanner_module.main()
            
        # Verify device was opened and closed
        mock_device_cls.return_value.open_path.assert_called_with(b'mock_path_1')
        mock_device_cls.return_value.close.assert_called()
        
        # The log file should exist
        log_path = os.path.join(REPO_ROOT, "diagnostics_logs", "04_report_id_scanner.log")
        self.assertTrue(os.path.exists(log_path))
        
        # Check log file content
        with open(log_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
            
        self.assertIn("REPORT ID SCAN SUMMARY", log_content)
        self.assertIn("0x01", log_content)
        self.assertIn("0x02", log_content)
        print("[PASS] 04_report_id_scanner logic test passed.")

    @patch('hid.enumerate')
    @patch('hid.device')
    @patch('builtins.input')
    @patch('time.sleep')
    @patch('time.time')
    def test_baseline_logic_test(self, mock_time, mock_sleep, mock_input, mock_device_cls, mock_enumerate):
        # Setup mocks
        mock_enumerate.return_value = [
            {
                'path': b'mock_path_1',
                'vendor_id': 0x2DC8,
                'product_id': 0x301C,
                'manufacturer_string': '8BitDo',
                'product_string': '8BitDo Ultimate 2C',
                'interface_number': 0
            }
        ]
        
        mock_device = MagicMock()
        mock_device_cls.return_value = mock_device
        
        # User input choices:
        # 1. Select device index -> '0'
        mock_input.side_effect = ['0']
        
        # Mock time sequence
        time_sequence = [100.0]
        for i in range(100):
            time_sequence.append(100.0 + (i * 0.25))
        mock_time.side_effect = time_sequence
        
        cal_packets = [[0x01, 0x80, 0x80, 0x00]] * 10
        test_packets = [
            [0x01, 0x80, 0x80, 0x00],
            [0x01, 0x80, 0x90, 0x00],
            [0x01, 0x80, 0x90, 0x00],
            [0x01, 0x80, 0x80, 0x00]
        ]
        
        # Create side effect that raises KeyboardInterrupt at the end
        def read_side_effect(*args, **kwargs):
            if cal_packets:
                return cal_packets.pop(0)
            if test_packets:
                return test_packets.pop(0)
            raise KeyboardInterrupt("Stop loop")
            
        mock_device.read.side_effect = read_side_effect
        
        # Run main
        baseline_module.main()
            
        # Verify device was opened and closed
        mock_device_cls.return_value.open_path.assert_called_with(b'mock_path_1')
        mock_device_cls.return_value.close.assert_called()
        
        # The log file should exist
        log_path = os.path.join(REPO_ROOT, "diagnostics_logs", "05_baseline_logic_test.log")
        self.assertTrue(os.path.exists(log_path))
        
        # Check log file content
        with open(log_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
            
        self.assertIn("Resting baseline established", log_content)
        self.assertIn("Byte 2 changed: 0x80 -> 0x90 (Delta: +16)", log_content)
        self.assertIn("Byte 2 returned to baseline: 0x80", log_content)
        print("[PASS] 05_baseline_logic_test logic test passed.")

if __name__ == '__main__':
    unittest.main()
