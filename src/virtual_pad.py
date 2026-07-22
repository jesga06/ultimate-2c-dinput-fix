"""
Virtual XInput Controller Interface (virtual_pad.py)
Uses vgamepad (communicating with the ViGEmBus Windows driver) to simulate
a virtual Xbox 360 controller. It forwards normal gamepad inputs and blocks
standard buttons if they have been custom-remapped to key/mouse events.
"""
import vgamepad as vg
from decoder import ControllerState
import math_utils
import logging

logger = logging.getLogger('virtual_pad')

BUTTON_MAP = {
    'a': vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    'b': vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    'x': vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    'y': vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    'lb': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    'rb': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    'select': vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    'start': vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    'home': vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
    'l3': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    'r3': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    'dpad_up': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    'dpad_down': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    'dpad_left': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    'dpad_right': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
}


class VirtualPad:
    """
    Simulates a virtual Xbox 360 gamepad based on parsed ControllerState.
    Controls analog stick mapping, digital button mapping, triggers, and D-pad.
    Blocks standard inputs when remapped to keys/mouse to avoid duplicate presses in-game.
    """

    def __init__(self, config=None):
        try:
            self.gamepad = vg.VX360Gamepad()
            print("Virtual Xbox 360 controller created successfully.")
            logger.info("Virtual Xbox 360 controller created successfully.")
        except Exception as e:
            msg = f"Failed to create virtual gamepad: {e}\nIs ViGEmBus installed?"
            print(msg)
            logger.error(msg)
            raise

        self.home_mapping = 'guide'
        self.blocked_buttons = set()
        self.rumble_callback = None
        
        # Register for force feedback notifications
        try:
            self.gamepad.register_notification(self._vgamepad_notification_handler)
        except Exception as e:
            print(f"Warning: Could not register vgamepad notifications: {e}")
            logger.warning(f"Could not register vgamepad notifications: {e}", exc_info=True)

        if config:
            self.reload_config(config)

    def set_rumble_callback(self, callback):
        """callback(left_motor: int, right_motor: int) -> 0-255"""
        self.rumble_callback = callback

    def _vgamepad_notification_handler(self, client, target, large_motor, small_motor, led_number, user_data):
        if self.rumble_callback:
            # large_motor and small_motor are 0-255
            self.rumble_callback(large_motor, small_motor)

    def reload_config(self, config):
        if logger:
            logger.debug("[ENTER] virtual_pad reload_config()")
        self.home_mapping = 'guide'
        self.blocked_buttons.clear()

        self.digital_lt = False
        self.digital_rt = False
        if config.has_section('settings'):
            if config.has_option('settings', 'digital_lt'):
                self.digital_lt = config.get(
                    'settings', 'digital_lt').lower() == 'true'
            if config.has_option('settings', 'digital_rt'):
                self.digital_rt = config.get(
                    'settings', 'digital_rt').lower() == 'true'

        self.lt_inner = 0.05
        self.lt_adz = 0.0
        self.lt_curve = 'linear'
        self.lt_power = 2.0
        
        self.rt_inner = 0.05
        self.rt_adz = 0.0
        self.rt_curve = 'linear'
        self.rt_power = 2.0

        if config.has_section('trigger_left'):
            self.lt_inner = config.getfloat('trigger_left', 'deadzone', fallback=self.lt_inner)
            self.lt_adz = config.getfloat('trigger_left', 'anti_deadzone', fallback=self.lt_adz)
            self.lt_curve = config.get('trigger_left', 'curve', fallback=self.lt_curve)
            self.lt_power = config.getfloat('trigger_left', 'exp_factor', fallback=self.lt_power)
            self.lt_rest_dz = config.getfloat('trigger_left', 'rest_deadzone', fallback=0.0)
            self.lt_sens = config.getfloat('trigger_left', 'sensitivity', fallback=1.0)

        if config.has_section('trigger_right'):
            self.rt_inner = config.getfloat('trigger_right', 'deadzone', fallback=self.rt_inner)
            self.rt_adz = config.getfloat('trigger_right', 'anti_deadzone', fallback=self.rt_adz)
            self.rt_curve = config.get('trigger_right', 'curve', fallback=self.rt_curve)
            self.rt_power = config.getfloat('trigger_right', 'exp_factor', fallback=self.rt_power)
            self.rt_rest_dz = config.getfloat('trigger_right', 'rest_deadzone', fallback=0.0)
            self.rt_sens = config.getfloat('trigger_right', 'sensitivity', fallback=1.0)

        self.ls_inner = 0.05
        self.ls_adz = 0.0
        self.ls_curve = 'linear'
        self.ls_power = 2.0
        
        self.rs_inner = 0.05
        self.rs_adz = 0.0
        self.rs_curve = 'linear'
        self.rs_power = 2.0

        if config.has_section('analog_left'):
            self.ls_inner = config.getfloat('analog_left', 'deadzone', fallback=self.ls_inner)
            self.ls_adz = config.getfloat('analog_left', 'anti_deadzone', fallback=0.0)
            self.ls_curve = config.get('analog_left', 'curve', fallback=self.ls_curve)
            self.ls_power = config.getfloat('analog_left', 'exp_factor', fallback=self.ls_power)
            self.ls_rest_dz = config.getfloat('analog_left', 'rest_deadzone', fallback=0.0)
            self.ls_sens = config.getfloat('analog_left', 'sensitivity', fallback=1.0)
            self.ls_circ_mode = config.get('analog_left', 'circularity_mode', fallback='disabled').lower()
            self.ls_circ_cx = config.getfloat('analog_left', 'circularity_center_x', fallback=0.0)
            self.ls_circ_cy = config.getfloat('analog_left', 'circularity_center_y', fallback=0.0)
            bounds_str = config.get('analog_left', 'circularity_bounds', fallback='')
            self.ls_circ_bounds = [float(x) for x in bounds_str.split(',')] if bounds_str else None
            
        if config.has_section('analog_right'):
            self.rs_inner = config.getfloat('analog_right', 'deadzone', fallback=self.rs_inner)
            self.rs_adz = config.getfloat('analog_right', 'anti_deadzone', fallback=0.0)
            self.rs_curve = config.get('analog_right', 'curve', fallback=self.rs_curve)
            self.rs_power = config.getfloat('analog_right', 'exp_factor', fallback=self.rs_power)
            self.rs_rest_dz = config.getfloat('analog_right', 'rest_deadzone', fallback=0.0)
            self.rs_sens = config.getfloat('analog_right', 'sensitivity', fallback=1.0)
            self.rs_circ_mode = config.get('analog_right', 'circularity_mode', fallback='disabled').lower()
            self.rs_circ_cx = config.getfloat('analog_right', 'circularity_center_x', fallback=0.0)
            self.rs_circ_cy = config.getfloat('analog_right', 'circularity_center_y', fallback=0.0)
            bounds_str = config.get('analog_right', 'circularity_bounds', fallback='')
            self.rs_circ_bounds = [float(x) for x in bounds_str.split(',')] if bounds_str else None

        # Load block preferences (default to block if mapped, i.e. True)
        block_prefs = {}
        if config.has_section('block_xinput'):
            for key, val in config.items('block_xinput'):
                # config values can be read as string, we check if it is
                # explicitly false
                block_prefs[key.lower()] = val.lower() != 'false'

        for section_name in ['layer_base', 'layer_shift', 'extra_buttons']:
            if config.has_section(section_name):
                for key, val in config.items(section_name):
                    key_lower = key.lower()
                    val_lower = val.lower()
                    if key_lower == 'home':
                        self.home_mapping = val_lower

                    # If a standard button/trigger is mapped, block it from being pressed on virtual pad
                    # unless explicitly opted out in block_xinput
                    if key_lower in ['a', 'b', 'x', 'y', 'lb', 'rb', 'lt', 'rt', 'select',
                                     'start', 'l3', 'r3', 'dpad_up', 'dpad_down', 'dpad_left', 'dpad_right', 'ls', 'rs']:
                        should_block = block_prefs.get(key_lower, True)
                        if should_block:
                            self.blocked_buttons.add(key_lower)


    def process(self, state: ControllerState):
        # Triggers
        lt_val = math_utils.process_trigger(state.lt, self.lt_inner, self.lt_adz, self.lt_curve, self.lt_power, getattr(self, 'lt_rest_dz', 0.0), getattr(self, 'lt_sens', 1.0))
        if getattr(self, 'digital_lt', False):
            lt_val = 1.0 if lt_val > 0 else 0.0

        rt_val = math_utils.process_trigger(state.rt, self.rt_inner, self.rt_adz, self.rt_curve, self.rt_power, getattr(self, 'rt_rest_dz', 0.0), getattr(self, 'rt_sens', 1.0))
        if getattr(self, 'digital_rt', False):
            rt_val = 1.0 if rt_val > 0 else 0.0

        if 'lt' in self.blocked_buttons:
            self.gamepad.left_trigger_float(value_float=0.0)
        else:
            self.gamepad.left_trigger_float(value_float=lt_val)

        if 'rt' in self.blocked_buttons:
            self.gamepad.right_trigger_float(value_float=0.0)
        else:
            self.gamepad.right_trigger_float(value_float=rt_val)

        # Sticks (Standard ControllerState polarity: positive UP)
        lx_val = state.lx
        ly_val = state.ly
        rx_val = state.rx
        ry_val = state.ry
        
        if 'ls' in self.blocked_buttons:
            lx_val, ly_val = 0.0, 0.0
        else:
            if getattr(self, 'ls_circ_mode', 'disabled') == 'before':
                lx_val, ly_val = math_utils.apply_circularity_correction(lx_val, ly_val, getattr(self, 'ls_circ_cx', 0.0), getattr(self, 'ls_circ_cy', 0.0), getattr(self, 'ls_circ_bounds', None))
                lx_val, ly_val = math_utils.process_analog_stick(lx_val, ly_val, self.ls_inner, self.ls_adz, self.ls_curve, self.ls_power, getattr(self, 'ls_rest_dz', 0.0), getattr(self, 'ls_sens', 1.0))
            elif getattr(self, 'ls_circ_mode', 'disabled') == 'after':
                lx_val, ly_val = math_utils.process_analog_stick(lx_val, ly_val, self.ls_inner, self.ls_adz, self.ls_curve, self.ls_power, getattr(self, 'ls_rest_dz', 0.0), getattr(self, 'ls_sens', 1.0))
                lx_val, ly_val = math_utils.apply_circularity_correction(lx_val, ly_val, getattr(self, 'ls_circ_cx', 0.0), getattr(self, 'ls_circ_cy', 0.0), getattr(self, 'ls_circ_bounds', None))
            else:
                lx_val, ly_val = math_utils.process_analog_stick(lx_val, ly_val, self.ls_inner, self.ls_adz, self.ls_curve, self.ls_power, getattr(self, 'ls_rest_dz', 0.0), getattr(self, 'ls_sens', 1.0))

        if 'rs' in self.blocked_buttons:
            rx_val, ry_val = 0.0, 0.0
        else:
            if getattr(self, 'rs_circ_mode', 'disabled') == 'before':
                rx_val, ry_val = math_utils.apply_circularity_correction(rx_val, ry_val, getattr(self, 'rs_circ_cx', 0.0), getattr(self, 'rs_circ_cy', 0.0), getattr(self, 'rs_circ_bounds', None))
                rx_val, ry_val = math_utils.process_analog_stick(rx_val, ry_val, self.rs_inner, self.rs_adz, self.rs_curve, self.rs_power, getattr(self, 'rs_rest_dz', 0.0), getattr(self, 'rs_sens', 1.0))
            elif getattr(self, 'rs_circ_mode', 'disabled') == 'after':
                rx_val, ry_val = math_utils.process_analog_stick(rx_val, ry_val, self.rs_inner, self.rs_adz, self.rs_curve, self.rs_power, getattr(self, 'rs_rest_dz', 0.0), getattr(self, 'rs_sens', 1.0))
                rx_val, ry_val = math_utils.apply_circularity_correction(rx_val, ry_val, getattr(self, 'rs_circ_cx', 0.0), getattr(self, 'rs_circ_cy', 0.0), getattr(self, 'rs_circ_bounds', None))
            else:
                rx_val, ry_val = math_utils.process_analog_stick(rx_val, ry_val, self.rs_inner, self.rs_adz, self.rs_curve, self.rs_power, getattr(self, 'rs_rest_dz', 0.0), getattr(self, 'rs_sens', 1.0))

        self.gamepad.left_joystick_float(x_value_float=lx_val, y_value_float=ly_val)
        self.gamepad.right_joystick_float(x_value_float=rx_val, y_value_float=ry_val)

        # Helper to conditionally press buttons
        def handle_btn(btn_name, is_pressed, vg_btn):
            if btn_name in self.blocked_buttons:
                self.gamepad.release_button(button=vg_btn)
                return
            if is_pressed:
                self.gamepad.press_button(button=vg_btn)
            else:
                self.gamepad.release_button(button=vg_btn)

        # Buttons
        handle_btn('a', state.a, vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        handle_btn('b', state.b, vg.XUSB_BUTTON.XUSB_GAMEPAD_B)
        handle_btn('x', state.x, vg.XUSB_BUTTON.XUSB_GAMEPAD_X)
        handle_btn('y', state.y, vg.XUSB_BUTTON.XUSB_GAMEPAD_Y)
        handle_btn('lb', state.lb, vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER)
        handle_btn('rb', state.rb, vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER)
        handle_btn('select', state.select, vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK)
        handle_btn('start', state.start, vg.XUSB_BUTTON.XUSB_GAMEPAD_START)

        # Home button logic is special since it defaults to guide mapping
        if self.home_mapping == 'guide':
            if state.home and 'home' not in self.blocked_buttons:
                self.gamepad.press_button(
                    button=vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE)
            else:
                self.gamepad.release_button(
                    button=vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE)
        else:
            self.gamepad.release_button(
                button=vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE)

        handle_btn('l3', state.l3, vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)
        handle_btn('r3', state.r3, vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB)

        # D-Pad
        handle_btn(
            'dpad_up',
            state.dpad_up,
            vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
        handle_btn(
            'dpad_down',
            state.dpad_down,
            vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        handle_btn(
            'dpad_left',
            state.dpad_left,
            vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
        handle_btn(
            'dpad_right',
            state.dpad_right,
            vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)

        self.gamepad.update()

    def press_gamepad_button(self, btn_name):
        btn = btn_name.lower().replace('gamepad:', '').strip()
        if btn == 'lt':
            self.gamepad.left_trigger_float(value_float=1.0)
            self.gamepad.update()
        elif btn == 'rt':
            self.gamepad.right_trigger_float(value_float=1.0)
            self.gamepad.update()
        elif btn in BUTTON_MAP:
            self.gamepad.press_button(button=BUTTON_MAP[btn])
            self.gamepad.update()

    def release_gamepad_button(self, btn_name):
        btn = btn_name.lower().replace('gamepad:', '').strip()
        if btn == 'lt':
            self.gamepad.left_trigger_float(value_float=0.0)
            self.gamepad.update()
        elif btn == 'rt':
            self.gamepad.right_trigger_float(value_float=0.0)
            self.gamepad.update()
        elif btn in BUTTON_MAP:
            self.gamepad.release_button(button=BUTTON_MAP[btn])
            self.gamepad.update()
