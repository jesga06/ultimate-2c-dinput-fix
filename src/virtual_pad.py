"""
Virtual XInput Controller Interface (virtual_pad.py)
Uses vgamepad (communicating with the ViGEmBus Windows driver) to simulate
a virtual Xbox 360 controller. It forwards normal gamepad inputs and blocks
standard buttons if they have been custom-remapped to key/mouse events.
"""
import vgamepad as vg
from decoder import ControllerState


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
        except Exception as e:
            print(
                f"Error creating virtual gamepad (ViGEmBus might not be installed): {e}")
            raise

        self.home_mapping = 'guide'
        self.blocked_buttons = set()
        if config:
            self.reload_config(config)

    def reload_config(self, config):
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

        # Load block preferences (default to block if mapped, i.e. True)
        block_prefs = {}
        if config.has_section('block_xinput'):
            for key, val in config.items('block_xinput'):
                # config values can be read as string, we check if it is
                # explicitly false
                block_prefs[key.lower()] = val.lower() != 'false'

        if config.has_section('extra_buttons'):
            for key, val in config.items('extra_buttons'):
                key_lower = key.lower()
                val_lower = val.lower()
                if key_lower == 'home':
                    self.home_mapping = val_lower

                # If a standard button/trigger is mapped, block it from being pressed on virtual pad
                # unless explicitly opted out in block_xinput
                if key_lower in ['a', 'b', 'x', 'y', 'lb', 'rb', 'lt', 'rt', 'select',
                                 'start', 'l3', 'r3', 'dpad_up', 'dpad_down', 'dpad_left', 'dpad_right']:
                    should_block = block_prefs.get(key_lower, True)
                    if should_block:
                        self.blocked_buttons.add(key_lower)

    def _map_axis(self, value: int, invert: bool = False) -> int:
        # Invert the 0-255 range first if needed
        if invert:
            value = 255 - value

        # Map 0-255 cleanly to -32768 to +32767
        # 128 is treated as perfect center (0)
        if value <= 128:
            mapped = int((value / 128.0) * 32768) - 32768
        else:
            mapped = int(((value - 128) / 127.0) * 32767)

        if mapped > 32767:
            mapped = 32767
        elif mapped < -32768:
            mapped = -32768

        return mapped

    def process(self, state: ControllerState):
        # Triggers
        lt_val = state.lt
        if getattr(self, 'digital_lt', False):
            lt_val = 255 if state.lt > 0 else 0

        rt_val = state.rt
        if getattr(self, 'digital_rt', False):
            rt_val = 255 if state.rt > 0 else 0

        if 'lt' in self.blocked_buttons:
            self.gamepad.left_trigger(value=0)
        else:
            self.gamepad.left_trigger(value=lt_val)

        if 'rt' in self.blocked_buttons:
            self.gamepad.right_trigger(value=0)
        else:
            self.gamepad.right_trigger(value=rt_val)

        # Sticks
        lx_val = self._map_axis(state.lx, invert=False)
        ly_val = self._map_axis(state.ly, invert=True)
        rx_val = self._map_axis(state.rx, invert=False)
        ry_val = self._map_axis(state.ry, invert=True)

        self.gamepad.left_joystick(x_value=lx_val, y_value=ly_val)
        self.gamepad.right_joystick(x_value=rx_val, y_value=ry_val)

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
