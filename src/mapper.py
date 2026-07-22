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
import threading
import math_utils
import logging

logger = logging.getLogger('mapper')

class Mapper:
    def __init__(self, config):
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        
        self.mappings = {'layer_base': {}, 'layer_shift': {}}
        self.chords = []
        self.active_layer = 'layer_base'
        self.shift_button = None
        self.shift_mode = 'hold'
        self.chord_mode = 'rollback'
        self.chord_timeout = 0.040
        
        self.prev_state = {}
        self.active_scrolls = {}
        self.last_scroll_time = 0
        self.active_holds = {}
        
        self.pending_inputs = {} # For delay buffer mode
        self.executed_chord_keys = set()
        
        # Mouse interpolation thread
        self.mouse_thread_active = True
        self.mouse_dx = 0.0
        self.mouse_dy = 0.0
        self.mouse_lock = threading.Lock()
        self.mouse_thread = threading.Thread(target=self._mouse_interpolation_loop, daemon=True)
        self.mouse_thread.start()

        # Analog WASD tracking
        self.wasd_state = {'w': False, 'a': False, 's': False, 'd': False}
        self.wasd_debounce_timers = {'w': 0, 'a': 0, 's': 0, 'd': 0}

        self.macro_executor = None # To be injected later

        self.reload_config(config)

    def reload_config(self, config):
        if logger:
            logger.debug(f"[ENTER] reload_config() - active_layer={self.active_layer}")
        self.mappings = {'layer_base': {}, 'layer_shift': {}}
        self.chords = []
        
        if config.has_section('settings'):
            self.chord_mode = config.get('settings', 'chord_mode', fallback='rollback').lower()

        if config.has_section('shift_layer'):
            self.shift_button = config.get('shift_layer', 'trigger_button', fallback=None)
            if self.shift_button:
                self.shift_button = self.shift_button.lower()
            self.shift_mode = config.get('shift_layer', 'mode', fallback='hold').lower()

        # Legacy extra_buttons to layer_base
        if config.has_section('extra_buttons'):
            for key, val in config.items('extra_buttons'):
                self.mappings['layer_base'][key.lower()] = val.lower()

        if config.has_section('layer_base'):
            for key, val in config.items('layer_base'):
                self.mappings['layer_base'][key.lower()] = val.lower()
                
        if config.has_section('shift_mappings'):
            for key, val in config.items('shift_mappings'):
                self.mappings['layer_shift'][key.lower()] = val.lower()

        # Extract Chords
        for layer in ['layer_base', 'layer_shift']:
            keys_to_remove = []
            for key, val in self.mappings[layer].items():
                if '+' in key:
                    chord_keys = set([k.strip() for k in key.split('+')])
                    self.chords.append({'keys': chord_keys, 'action': val, 'layer': layer})
                    keys_to_remove.append(key)
            for k in keys_to_remove:
                del self.mappings[layer][k]

    def _mouse_interpolation_loop(self):
        # Runs at 250Hz for smooth mouse movement
        while self.mouse_thread_active:
            with self.mouse_lock:
                dx, dy = self.mouse_dx, self.mouse_dy
            
            if dx != 0 or dy != 0:
                # pynput mouse.move requires integers
                self.mouse.move(int(dx), int(dy))
                
            time.sleep(1.0 / 250.0)

    def _execute_macro(self, macro_name):
        # We will integrate the Macro Executor here later
        if self.macro_executor:
            self.macro_executor.execute_or_toggle(macro_name)

    def _press(self, mapping):
        if not mapping:
            return

        if mapping.startswith('macro:'):
            self._execute_macro(mapping.split(':', 1)[1])
            return
        elif self.macro_executor and mapping in self.macro_executor.macros:
            self._execute_macro(mapping)
            return

        if mapping.startswith('gamepad:'):
            btn_name = mapping.split(':', 1)[1]
            if hasattr(self, 'virtual_pad') and self.virtual_pad:
                self.virtual_pad.press_gamepad_button(btn_name)
            return
        elif mapping in ['a', 'b', 'x', 'y', 'lb', 'rb', 'lt', 'rt', 'l3', 'r3', 'select', 'start', 'home', 'dpad_up', 'dpad_down', 'dpad_left', 'dpad_right']:
            if hasattr(self, 'virtual_pad') and self.virtual_pad:
                self.virtual_pad.press_gamepad_button(mapping)
            return

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
                    logger.error(f"Failed to press key {key_name}: {e}", exc_info=True)
        else:
            # Fallback for plain key strings without explicit keyboard: prefix
            keys = mapping.split('+')
            for key_name in keys:
                key_name = key_name.strip()
                try:
                    if hasattr(Key, key_name):
                        self.keyboard.press(getattr(Key, key_name))
                    else:
                        self.keyboard.press(KeyCode.from_char(key_name))
                except Exception as e:
                    logger.error(f"Failed to press key {key_name}: {e}", exc_info=True)

    def _release(self, mapping):
        if not mapping:
            return

        if mapping.startswith('macro:'):
            return
        elif self.macro_executor and mapping in self.macro_executor.macros:
            return

        if mapping.startswith('gamepad:'):
            btn_name = mapping.split(':', 1)[1]
            if hasattr(self, 'virtual_pad') and self.virtual_pad:
                self.virtual_pad.release_gamepad_button(btn_name)
            return
        elif mapping in ['a', 'b', 'x', 'y', 'lb', 'rb', 'lt', 'rt', 'l3', 'r3', 'select', 'start', 'home', 'dpad_up', 'dpad_down', 'dpad_left', 'dpad_right']:
            if hasattr(self, 'virtual_pad') and self.virtual_pad:
                self.virtual_pad.release_gamepad_button(mapping)
            return

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
                except Exception as e:
                    logger.error(f"Failed to release key {key_name}: {e}", exc_info=True)
        else:
            # Fallback for plain key strings without explicit keyboard: prefix
            keys = mapping.split('+')
            for key_name in reversed(keys):
                key_name = key_name.strip()
                try:
                    if hasattr(Key, key_name):
                        self.keyboard.release(getattr(Key, key_name))
                    else:
                        self.keyboard.release(KeyCode.from_char(key_name))
                except Exception as e:
                    logger.error(f"Failed to release key {key_name}: {e}", exc_info=True)

    def _process_wasd(self, x, y, threshold=0.5):
        now = time.time()
        target_w = y > threshold
        target_s = y < -threshold
        target_d = x > threshold
        target_a = x < -threshold

        def _update_wasd_key(key, target_state):
            if target_state and not self.wasd_state[key]:
                # Snap-back debounce: Ignore presses right after a release
                if now - self.wasd_debounce_timers[key] > 0.05:
                    self._press(f"keyboard:{key}")
                    self.wasd_state[key] = True
            elif not target_state and self.wasd_state[key]:
                self._release(f"keyboard:{key}")
                self.wasd_state[key] = False
                self.wasd_debounce_timers[key] = now

        _update_wasd_key('w', target_w)
        _update_wasd_key('s', target_s)
        _update_wasd_key('a', target_a)
        _update_wasd_key('d', target_d)

    def process(self, state: ControllerState):
        all_buttons = {}
        for btn_name in ['a', 'b', 'x', 'y', 'lb', 'rb', 'select', 'start',
                         'home', 'l3', 'r3', 'dpad_up', 'dpad_down', 'dpad_left', 'dpad_right']:
            all_buttons[btn_name] = getattr(state, btn_name)
        all_buttons['lt'] = state.lt > 0
        all_buttons['rt'] = state.rt > 0
        
        # Pre-populate all known extra buttons from mappings and prev_state to False
        extra_keys = set(self.mappings['layer_base'].keys()) | set(self.mappings['layer_shift'].keys()) | set(self.prev_state.keys())
        for k in extra_keys:
            if k not in all_buttons:
                all_buttons[k] = False
                
        # Now update with active extra_inputs (matching lowercase keys)
        for eb_name, eb_val in state.extra_inputs.items():
            eb_lower = eb_name.lower()
            if isinstance(eb_val, (float, int)):
                all_buttons[eb_lower] = eb_val > 0.1
            else:
                all_buttons[eb_lower] = bool(eb_val)

        # Handle Shift Transition
        if self.shift_button:
            shift_is_down = all_buttons.get(self.shift_button, False)
            shift_btn_prev = self.prev_state.get(self.shift_button, False)
            
            if shift_is_down != shift_btn_prev:
                old_layer = self.active_layer
                if self.shift_mode == 'toggle':
                    if shift_is_down:
                        self.active_layer = 'layer_shift' if self.active_layer == 'layer_base' else 'layer_base'
                else: # hold
                    self.active_layer = 'layer_shift' if shift_is_down else 'layer_base'
                if old_layer != self.active_layer and logger:
                    logger.debug(f"[MAPPER] Shift layer changed: {old_layer} -> {self.active_layer} (button={self.shift_button}, mode={self.shift_mode})")

        now = time.time()
        
        # Pre-process analog sticks
        ls_mapping = self.mappings[self.active_layer].get('ls')
        rs_mapping = self.mappings[self.active_layer].get('rs')
        
        lx, ly = state.lx, state.ly
        rx, ry = state.rx, state.ry
        
        # Mouse Accumulators
        mx, my = 0.0, 0.0
        
        if ls_mapping == 'mouse:movement':
            mx += lx * 15.0 # Base sensitivity
            my -= ly * 15.0 # Invert Y for screen space
        elif ls_mapping == 'keyboard:wasd':
            self._process_wasd(lx, ly)
            
        if rs_mapping == 'mouse:movement':
            mx += rx * 15.0
            my -= ry * 15.0
        elif rs_mapping == 'keyboard:wasd':
            self._process_wasd(rx, ry)
            
        with self.mouse_lock:
            self.mouse_dx, self.mouse_dy = mx, my

        # Process Buttons
        for btn, is_pressed in all_buttons.items():
            btn_lower = btn.lower()
            if btn_lower == self.shift_button and self.shift_mode == 'hold':
                self.prev_state[btn_lower] = is_pressed
                continue # Skip triggering standard actions for the shift button if it's held
                
            prev_pressed = self.prev_state.get(btn_lower, False)

            if is_pressed != prev_pressed:
                mapping = self.mappings[self.active_layer].get(btn_lower)
                
                if is_pressed:
                    # Delay Buffer Mode
                    if self.chord_mode == 'delay':
                        self.pending_inputs[btn_lower] = now
                    # Rollback Mode
                    else:
                        if mapping and mapping != 'guide':
                            self._press(mapping)
                            self.active_holds[btn_lower] = mapping
                        self.pending_inputs[btn_lower] = now # Track for chord completion anyway
                else:
                    if btn_lower in self.pending_inputs:
                        # Released before chord timeout (Delay mode only)
                        if self.chord_mode == 'delay':
                            if mapping and mapping != 'guide':
                                self._press(mapping)
                                self._release(mapping)
                        del self.pending_inputs[btn_lower]
                    
                    if btn_lower in self.executed_chord_keys:
                        self.executed_chord_keys.remove(btn_lower)
                    
                    # Release actual held mapping
                    if btn_lower in self.active_holds:
                        mapped_to_release = self.active_holds.pop(btn_lower)
                        self._release(mapped_to_release)

                self.prev_state[btn_lower] = is_pressed

        # Check Chords
        pressed_keys = list(self.pending_inputs.keys())
        for chord in self.chords:
            if chord['layer'] == self.active_layer and chord['keys'].issubset(pressed_keys):
                # Chord completed!
                if self.chord_mode == 'rollback':
                    # Rollback existing holds
                    for k in chord['keys']:
                        if k in self.active_holds:
                            self._release(self.active_holds.pop(k))
                            
                # Execute chord
                self._press(chord['action'])
                
                for k in chord['keys']:
                    self.active_holds[k] = chord['action'] # Tie the release to these keys
                    self.executed_chord_keys.add(k)
                    if k in self.pending_inputs:
                        del self.pending_inputs[k]
                        
        # Flush pending inputs (Delay Buffer mode)
        if self.chord_mode == 'delay':
            for btn, timestamp in list(self.pending_inputs.items()):
                if now - timestamp >= self.chord_timeout:
                    mapping = self.mappings[self.active_layer].get(btn)
                    if mapping and mapping != 'guide':
                        self._press(mapping)
                        self.active_holds[btn] = mapping
                    del self.pending_inputs[btn]

        # Process continuous scrolling repeat
        if self.active_scrolls:
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
            logger.error(f"Invalid special action format: {mapping}", exc_info=True)
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
