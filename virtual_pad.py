import vgamepad as vg
from decoder import ControllerState

class VirtualPad:
    def __init__(self, config=None):
        try:
            self.gamepad = vg.VX360Gamepad()
            print("Virtual Xbox 360 controller created successfully.")
        except Exception as e:
            print(f"Error creating virtual gamepad (ViGEmBus might not be installed): {e}")
            raise
            
        self.home_mapping = 'guide'
        if config and config.has_section('extra_buttons'):
            self.home_mapping = config.get('extra_buttons', 'home', fallback='guide').lower()
        
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
        self.gamepad.left_trigger(value=state.lt)
        self.gamepad.right_trigger(value=state.rt)
        
        # Sticks
        # Typical DInput Y-axis: 0 is Up, 255 is Down
        # XInput expects positive for Up, negative for Down
        lx_val = self._map_axis(state.lx, invert=False)
        ly_val = self._map_axis(state.ly, invert=True)
        rx_val = self._map_axis(state.rx, invert=False)
        ry_val = self._map_axis(state.ry, invert=True)
        
        self.gamepad.left_joystick(x_value=lx_val, y_value=ly_val)
        self.gamepad.right_joystick(x_value=rx_val, y_value=ry_val)
        
        # Buttons
        if state.a: self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        else: self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        
        if state.b: self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_B)
        else: self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_B)
        
        if state.x: self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_X)
        else: self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_X)
        
        if state.y: self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_Y)
        else: self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_Y)
        
        if state.lb: self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER)
        else: self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER)
        
        if state.rb: self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER)
        else: self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER)
        
        if state.select: self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK)
        else: self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK)
        
        if state.start: self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_START)
        else: self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_START)
        
        if self.home_mapping == 'guide':
            if state.home: self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE)
            else: self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE)
        
        if state.l3: self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)
        else: self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)
        
        if state.r3: self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB)
        else: self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB)
        
        # D-Pad
        if state.dpad_up: self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
        else: self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
        
        if state.dpad_down: self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        else: self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        
        if state.dpad_left: self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
        else: self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
        
        if state.dpad_right: self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)
        else: self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)
        
        self.gamepad.update()
