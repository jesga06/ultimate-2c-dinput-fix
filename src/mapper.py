"""
Input Mapper Engine (mapper.py)
This module maps gamepad input states to mouse and keyboard output actions.
It parses mapped actions (keys, mouse buttons, advanced scroll settings) and
uses pynput to simulate physical OS mouse and keyboard activity.
"""
from pynput.mouse import Controller as MouseController
from pynput.mouse import Button as MouseButton
from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Key, KeyCode
from decoder import ControllerState
import time


class Mapper:
    """
    Simulates keyboard and mouse actions from physical controller button states.
    Reads mappings from config.ini, tracks pressed states to trigger down/up actions,
    and manages repeating scroll events.
    """

    def __init__(self, config):
        self.mouse = MouseController()
        self.keyboard = KeyboardController()

        self.mappings = {}
        self.reload_config(config)
        self.prev_state = {}
        self.active_scrolls = {}
        self.last_scroll_time = 0

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
        elif mapping.startswith('mouse:scroll_'):
            parsed = self._parse_scroll_mapping(mapping)
            if parsed['mode'] == 'oneshot':
                self._do_scroll_parsed(parsed)
            else:
                self.active_scrolls[mapping] = parsed
                self._do_scroll_parsed(parsed)
        elif mapping.startswith('mouse:'):
            btn_name = mapping.split(':', 1)[1]
            if hasattr(MouseButton, btn_name):
                self.mouse.press(getattr(MouseButton, btn_name))
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
        elif mapping.startswith('mouse:scroll_'):
            if mapping in self.active_scrolls:
                del self.active_scrolls[mapping]
        elif mapping.startswith('mouse:'):
            btn_name = mapping.split(':', 1)[1]
            if hasattr(MouseButton, btn_name):
                self.mouse.release(getattr(MouseButton, btn_name))
        elif mapping.startswith('keyboard:'):
            keys = mapping.split(':', 1)[1].split('+')
            for key_name in reversed(keys):
                key_name = key_name.strip()
                try:
                    if hasattr(Key, key_name):
                        self.keyboard.release(getattr(Key, key_name))
                    else:
                        self.keyboard.release(KeyCode.from_char(key_name))
                except Exception:
                    pass

    def process(self, state: ControllerState):
        all_buttons = {}
        for btn_name in ['a', 'b', 'x', 'y', 'lb', 'rb', 'select', 'start',
                         'home', 'l3', 'r3', 'dpad_up', 'dpad_down', 'dpad_left', 'dpad_right']:
            all_buttons[btn_name] = getattr(state, btn_name)
        all_buttons['lt'] = state.lt > 0
        all_buttons['rt'] = state.rt > 0
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

        # Process continuous scrolling repeat
        if self.active_scrolls:
            now = time.time()
            for mapping, parsed in list(self.active_scrolls.items()):
                if now - parsed['last_run_time'] >= parsed['interval']:
                    self._do_scroll_parsed(parsed)
                    parsed['last_run_time'] = now

    def _parse_scroll_mapping(self, mapping):
        parts = mapping.split(':')
        direction = parts[1]
        mode = parts[2] if len(parts) > 2 else 'continuous'
        try:
            notches = int(parts[3]) if len(parts) > 3 else 1
        except ValueError:
            notches = 1
        try:
            interval = float(parts[4]) if len(parts) > 4 else 0.05
        except ValueError:
            interval = 0.05

        return {
            'direction': direction,
            'mode': mode,
            'notches': notches,
            'interval': interval,
            'last_run_time': time.time()
        }

    def _do_scroll_parsed(self, parsed):
        direction = parsed['direction']
        notches = parsed['notches']
        dx, dy = 0, 0
        if direction == 'scroll_up':
            dy = notches
        elif direction == 'scroll_down':
            dy = -notches
        elif direction == 'scroll_left':
            dx = -notches
        elif direction == 'scroll_right':
            dx = notches

        try:
            self.mouse.scroll(dx, dy)
        except Exception:
            pass
