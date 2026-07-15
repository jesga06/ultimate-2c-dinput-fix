from pynput.mouse import Controller as MouseController
from pynput.mouse import Button as MouseButton
from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Key, KeyCode
from decoder import ControllerState

class Mapper:
    def __init__(self, config):
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        
        self.mappings = {}
        self.reload_config(config)
        self.prev_state = {}
        
    def reload_config(self, config):
        self.mappings = {}
        if config.has_section('extra_buttons'):
            for key, val in config.items('extra_buttons'):
                self.mappings[key.lower()] = val.lower()
        
    def _press(self, mapping):
        if mapping == 'mouse4':
            self.mouse.press(MouseButton.x1)
        elif mapping == 'mouse5':
            self.mouse.press(MouseButton.x2)
        elif mapping.startswith('keyboard:'):
            keys = mapping.split(':', 1)[1].split('+')
            for key_name in keys:
                key_name = key_name.strip()
                try:
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
            keys = mapping.split(':', 1)[1].split('+')
            for key_name in reversed(keys):
                key_name = key_name.strip()
                try:
                    if hasattr(Key, key_name):
                        self.keyboard.release(getattr(Key, key_name))
                    else:
                        self.keyboard.release(KeyCode.from_char(key_name))
                except Exception as e:
                    pass

    def process(self, state: ControllerState):
        # Build a dict of all current button states (standard + extra)
        all_buttons = {}
        for btn_name in ['a', 'b', 'x', 'y', 'lb', 'rb', 'select', 'start', 'home', 'l3', 'r3', 'dpad_up', 'dpad_down', 'dpad_left', 'dpad_right']:
            all_buttons[btn_name] = getattr(state, btn_name)
        all_buttons.update(state.extra_buttons)
        
        for btn, is_pressed in all_buttons.items():
            btn_lower = btn.lower()
            prev_pressed = self.prev_state.get(btn_lower, False)
            
            if is_pressed != prev_pressed:
                # If there's a mapping for this button in config.ini, use it
                # We also assume 'guide' is handled by virtual_pad, not here.
                mapping = self.mappings.get(btn_lower)
                if mapping and mapping != 'guide':
                    if is_pressed:
                        self._press(mapping)
                    else:
                        self._release(mapping)
                self.prev_state[btn_lower] = is_pressed
