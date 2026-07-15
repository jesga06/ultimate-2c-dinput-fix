from pynput.mouse import Controller as MouseController
from pynput.mouse import Button as MouseButton
from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Key, KeyCode
from decoder import ControllerState

class Mapper:
    def __init__(self, config):
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        
        # Read mappings from config or use defaults
        if config.has_section('extra_buttons'):
            self.l4_mapping = config.get('extra_buttons', 'l4', fallback='mouse4').lower()
            self.r4_mapping = config.get('extra_buttons', 'r4', fallback='mouse5').lower()
            self.home_mapping = config.get('extra_buttons', 'home', fallback='guide').lower()
        else:
            self.l4_mapping = 'mouse4'
            self.r4_mapping = 'mouse5'
            self.home_mapping = 'guide'
        
        self.prev_l4 = False
        self.prev_r4 = False
        self.prev_home = False
        
    def _press(self, mapping):
        if mapping == 'mouse4':
            self.mouse.press(MouseButton.x1)
        elif mapping == 'mouse5':
            self.mouse.press(MouseButton.x2)
        elif mapping.startswith('keyboard:'):
            key_name = mapping.split(':', 1)[1]
            try:
                # Try to get special key enum (e.g. F13)
                if hasattr(Key, key_name):
                    self.keyboard.press(getattr(Key, key_name))
                else:
                    self.keyboard.press(KeyCode.from_char(key_name))
            except Exception as e:
                print(f"Failed to press key {key_name}: {e}")
            
    def _release(self, mapping):
        if mapping == 'mouse4':
            self.mouse.release(MouseButton.x1)
        elif mapping == 'mouse5':
            self.mouse.release(MouseButton.x2)
        elif mapping.startswith('keyboard:'):
            key_name = mapping.split(':', 1)[1]
            try:
                if hasattr(Key, key_name):
                    self.keyboard.release(getattr(Key, key_name))
                else:
                    self.keyboard.release(KeyCode.from_char(key_name))
            except Exception as e:
                pass

    def process(self, state: ControllerState):
        if state.l4 != self.prev_l4:
            if state.l4:
                self._press(self.l4_mapping)
            else:
                self._release(self.l4_mapping)
            self.prev_l4 = state.l4
            
        if state.r4 != self.prev_r4:
            if state.r4:
                self._press(self.r4_mapping)
            else:
                self._release(self.r4_mapping)
            self.prev_r4 = state.r4

        if state.home != self.prev_home:
            if self.home_mapping != 'guide':
                if state.home:
                    self._press(self.home_mapping)
                else:
                    self._release(self.home_mapping)
            self.prev_home = state.home
