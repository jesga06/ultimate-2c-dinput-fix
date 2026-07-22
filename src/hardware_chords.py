"""
Hardware Chords Engine (hardware_chords.py)
Unified engine for Hardware Chords (firmware-remapped combinations) and standard software chords.
Implements Input Suppression (consuming constituent buttons) and adaptive delay buffering.
"""
import time
import logging
from decoder import ControllerState

logger = logging.getLogger('hardware_chords')

class HardwareChordEngine:
    def __init__(self, config=None):
        self.chords = []
        self.pending_inputs = {}
        self.executed_chords = set()
        self.last_report_time = 0
        self.poll_intervals = []
        self.avg_poll_interval = 0.004 # Default 4ms (250Hz)
        
        self.impossible_states = []
        
        if config:
            self.reload_config(config)

    def reload_config(self, config):
        self.chords.clear()
        self.impossible_states.clear()
        self.pending_inputs.clear()
        self.executed_chords.clear()
        
        if config.has_section('hardware_chords'):
            for key, val in config.items('hardware_chords'):
                # Format expected (for this example, assuming val is JSON string or dict)
                # But since configparser stores strings, let's parse standard string format:
                # "chord=lb+select; delayed=select; mode=auto; action=l4"
                parts = dict(p.strip().split('=') for p in val.split(';') if '=' in p)
                if 'chord' in parts and 'action' in parts:
                    chord_keys = set(parts['chord'].lower().split('+'))
                    delay_mode = parts.get('mode', 'auto').lower()
                    delayed_member = parts.get('delayed', '').lower()
                    
                    try:
                        manual_delay = float(delay_mode.replace('ms', '')) / 1000.0 if delay_mode != 'auto' else 0.0
                    except ValueError:
                        if logger:
                            logger.error(f"Invalid delay format: {delay_mode}", exc_info=True)
                        manual_delay = 0.0
                        
                    self.chords.append({
                        'keys': chord_keys,
                        'delayed': delayed_member,
                        'mode': delay_mode,
                        'manual_delay': manual_delay,
                        'action': parts['action'].lower()
                    })
                    
        # Support for impossible hat states e.g., Left+Right (0x08)
        # Since we use boolean dpad fields, "left+right" would be:
        # "chord=dpad_left+dpad_right; action=m1"
        # We can handle them identically as chords without delay, or very short delay.

    def _get_button_state(self, state: ControllerState, btn: str) -> bool:
        if hasattr(state, btn):
            val = getattr(state, btn)
            if isinstance(val, (float, int)):
                return val > 0.1
            return bool(val)
        if btn in state.extra_inputs:
            val = state.extra_inputs[btn]
            if isinstance(val, (float, int)):
                return val > 0.1
            return bool(val)
        return False

    def _set_button_state(self, state: ControllerState, btn: str, val: bool):
        if hasattr(state, btn):
            current = getattr(state, btn)
            if isinstance(current, float):
                setattr(state, btn, 1.0 if val else 0.0)
            else:
                setattr(state, btn, val)
        else:
            state.extra_inputs[btn] = val

    def record_poll_interval(self):
        now = time.time()
        if self.last_report_time > 0:
            delta = now - self.last_report_time
            if delta < 0.1: # ignore large pauses
                self.poll_intervals.append(delta)
                if len(self.poll_intervals) > 50:
                    self.poll_intervals.pop(0)
                self.avg_poll_interval = sum(self.poll_intervals) / len(self.poll_intervals)
        self.last_report_time = now

    def process(self, state: ControllerState) -> ControllerState:
        now = time.time()
        
        # Track currently pressed buttons for this frame
        current_pressed = set()
        for btn in ['a', 'b', 'x', 'y', 'lb', 'rb', 'select', 'start', 'home', 'l3', 'r3', 'dpad_up', 'dpad_down', 'dpad_left', 'dpad_right', 'lt', 'rt']:
            if self._get_button_state(state, btn):
                current_pressed.add(btn)
        for btn, is_pressed in state.extra_inputs.items():
            if is_pressed:
                current_pressed.add(btn)
                
        # Handle releases for pending and executed chords
        for btn in list(self.pending_inputs.keys()):
            if btn not in current_pressed:
                del self.pending_inputs[btn]
                
        # Clean up executed chords if ANY key is released
        for chord_idx in list(self.executed_chords):
            chord = self.chords[chord_idx]
            if not chord['keys'].issubset(current_pressed):
                self.executed_chords.remove(chord_idx)

        # Check chords
        for i, chord in enumerate(self.chords):
            keys = chord['keys']
            delayed_btn = chord['delayed']
            
            # If the chord is already active, enforce Input Suppression
            if i in self.executed_chords:
                for k in keys:
                    self._set_button_state(state, k, False)
                self._set_button_state(state, chord['action'], True)
                continue
                
            # If all constituent keys are pressed NOW
            if keys.issubset(current_pressed):
                # Trigger Chord!
                self.executed_chords.add(i)
                for k in keys:
                    self._set_button_state(state, k, False)
                    if k in self.pending_inputs:
                        del self.pending_inputs[k]
                self._set_button_state(state, chord['action'], True)
                continue

            # If delayed button is pressed but other keys are NOT yet pressed
            if delayed_btn and delayed_btn in current_pressed:
                if delayed_btn not in self.pending_inputs:
                    self.pending_inputs[delayed_btn] = now
                
                # Check timeout
                elapsed = now - self.pending_inputs[delayed_btn]
                target_delay = chord['manual_delay'] if chord['mode'] != 'auto' else max(0.002, min(0.032, self.avg_poll_interval * 2))
                
                if elapsed < target_delay:
                    # Hold the button (suppress it temporarily)
                    self._set_button_state(state, delayed_btn, False)
                else:
                    # Timeout exceeded, let the button through naturally
                    pass
                    
        return state
