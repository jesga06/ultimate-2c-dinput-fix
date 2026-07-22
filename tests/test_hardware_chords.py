import sys
import os
import time
import unittest
from unittest.mock import MagicMock

# Fallback mock 'hid' module ONLY if native hidapi DLL is missing in environment
try:
    import hid
except ImportError:
    sys.modules['hid'] = MagicMock()

# Add repo root and src dir to path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REPO_ROOT)
sys.path.append(os.path.join(REPO_ROOT, "src"))

from src.hardware_chords import HardwareChordEngine
from src.decoder import ControllerState
import configparser

class TestHardwareChords(unittest.TestCase):
    def setUp(self):
        self.config = configparser.ConfigParser()
        self.config.add_section('hardware_chords')
        
    def test_basic_chord_execution(self):
        self.config.set('hardware_chords', 'chord1', 'chord=lb+select; delayed=select; mode=auto; action=l4')
        engine = HardwareChordEngine(self.config)
        
        state = ControllerState()
        state.lb = True
        state.select = True
        
        # First process might hold it as pending if delay is used, but in 'auto' mode and 
        # since we don't have enough poll interval data, it might trigger immediately or hold.
        # Let's mock time and simulate the delay buffering
        engine.record_poll_interval()
        
        state_out = engine.process(state)
        
        # After processing a valid chord, constituent buttons should be suppressed (False)
        # and the action (l4) should be injected into extra_inputs
        self.assertFalse(state_out.lb)
        self.assertFalse(state_out.select)
        self.assertTrue(state_out.extra_inputs.get('l4', False))

if __name__ == '__main__':
    unittest.main()
